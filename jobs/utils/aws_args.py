from __future__ import annotations

import os
import sys


def option(name: str, default: str | None = None) -> str:
    flag = f"--{name}"
    for index, value in enumerate(sys.argv):
        if value == flag and index + 1 < len(sys.argv):
            return sys.argv[index + 1]
        if value.startswith(f"{flag}="):
            return value.split("=", 1)[1]

    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required option or environment variable: {name}")
    return value


def optional_option(name: str, default: str) -> str:
    return option(name, default)


def list_option(name: str, default: str) -> list[str]:
    return [item.strip() for item in option(name, default).split(",") if item.strip()]
