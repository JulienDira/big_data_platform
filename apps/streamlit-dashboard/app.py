from __future__ import annotations

import base64
import hashlib
import os
import secrets
from urllib.parse import urlencode

import requests
import streamlit as st


SYMBOLS = ("BTCUSDC", "ETHUSDC", "SOLUSDC")
INTERVALS = ("1s", "1m", "15m", "1h")


def config(name: str, default: str | None = None) -> str:
    value = st.secrets.get(name, os.getenv(name, default))
    if not value:
        st.stop()
    return str(value)


def api_base_url() -> str:
    return config("API_BASE_URL").rstrip("/")


def cognito_domain() -> str:
    return config("COGNITO_DOMAIN").rstrip("/")


def redirect_uri() -> str:
    return config("COGNITO_REDIRECT_URI")


def code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def auth_url() -> str:
    verifier = secrets.token_urlsafe(48)
    state = secrets.token_urlsafe(24)
    st.session_state["pkce_verifier"] = verifier
    st.session_state["oauth_state"] = state
    params = {
        "client_id": config("COGNITO_CLIENT_ID"),
        "response_type": "code",
        "scope": st.secrets.get("COGNITO_SCOPES", "openid email profile"),
        "redirect_uri": redirect_uri(),
        "state": state,
        "code_challenge": code_challenge(verifier),
        "code_challenge_method": "S256",
    }
    return f"{cognito_domain()}/oauth2/authorize?{urlencode(params)}"


def exchange_code(code: str, state: str) -> None:
    if state != st.session_state.get("oauth_state"):
        st.error("Authentication state mismatch.")
        st.stop()
    response = requests.post(
        f"{cognito_domain()}/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "client_id": config("COGNITO_CLIENT_ID"),
            "code": code,
            "redirect_uri": redirect_uri(),
            "code_verifier": st.session_state["pkce_verifier"],
        },
        headers={"content-type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    response.raise_for_status()
    token = response.json()
    st.session_state["access_token"] = token["access_token"]
    st.query_params.clear()


def ensure_token() -> str:
    token = st.session_state.get("access_token")
    if token:
        return token

    code = st.query_params.get("code")
    state = st.query_params.get("state")
    if code and state:
        exchange_code(str(code), str(state))
        return st.session_state["access_token"]

    st.title("Market dashboard")
    st.link_button("Sign in", auth_url())
    st.stop()


def api_get(path: str, token: str, params: dict[str, str] | None = None) -> dict:
    response = requests.get(
        f"{api_base_url()}{path}",
        params=params or {},
        headers={"authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def render_latest(token: str, symbol: str, interval: str) -> None:
    payload = api_get(
        "/metrics/latest",
        token,
        {"symbol": symbol, "interval": interval},
    )
    item = payload["item"]
    cols = st.columns(4)
    cols[0].metric("Close", item.get("close"))
    cols[1].metric("RSI 14", item.get("rsi_14"))
    cols[2].metric("MACD", item.get("macd"))
    cols[3].metric("Updated", item.get("updated_at"))
    st.dataframe([item], use_container_width=True)


def render_history(token: str, symbol: str, interval: str) -> None:
    payload = api_get(
        "/metrics/history",
        token,
        {"symbol": symbol, "interval": interval, "limit": "100"},
    )
    st.dataframe(payload["items"], use_container_width=True)


def render_signals(token: str, symbol: str) -> None:
    payload = api_get("/signals", token, {"symbol": symbol, "limit": "100"})
    st.dataframe(payload["items"], use_container_width=True)


def render_daily_summary(token: str, symbol: str) -> None:
    payload = api_get("/daily-summary", token, {"symbol": symbol, "limit": "100"})
    st.dataframe(payload["items"], use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Market dashboard", layout="wide")
    token = ensure_token()
    st.title("Market dashboard")

    with st.sidebar:
        symbol = st.selectbox("Symbol", SYMBOLS)
        interval = st.selectbox("Interval", INTERVALS, index=1)
        if st.button("Sign out"):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()

    latest_tab, history_tab, signals_tab, daily_tab = st.tabs(
        ["Latest", "History", "Signals", "Daily"]
    )
    with latest_tab:
        render_latest(token, symbol, interval)
    with history_tab:
        render_history(token, symbol, interval)
    with signals_tab:
        render_signals(token, symbol)
    with daily_tab:
        render_daily_summary(token, symbol)


if __name__ == "__main__":
    main()
