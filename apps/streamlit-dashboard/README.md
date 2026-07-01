# Streamlit Dashboard

Streamlit Cloud wiring for the AWS POC dashboard.

The app authenticates through Cognito Hosted UI and calls API Gateway with the
returned bearer token. It does not read AWS data services directly and does not
use AWS access keys.

Required Streamlit secrets:

```toml
API_BASE_URL = "https://..."
COGNITO_DOMAIN = "https://..."
COGNITO_CLIENT_ID = "..."
COGNITO_REDIRECT_URI = "https://<streamlit-app>.streamlit.app"
COGNITO_SCOPES = "openid email profile"
```
