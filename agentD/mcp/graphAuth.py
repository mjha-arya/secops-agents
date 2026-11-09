"""App-only Microsoft Graph auth (client-credentials) for the Defender Alert MCP server.

This is app-only, not delegated: there's no interactive sign-in step. It uses the shared
"SecOps - Microsoft Graph Access" app registration (00000000-0000-0000-0000-000000000000), which
needs SecurityAlert.Read.All and SecurityIncident.Read.All (application) consented before this
works - see ../memory/appRegistration.md for the exact needs_human steps.

Set one of these before running:
    SECOPS_GRAPH_CLIENT_SECRET                              simplest, least preferred
    SECOPS_GRAPH_CERT_PATH + SECOPS_GRAPH_CERT_THUMBPRINT    preferred: a PEM private key file
                                                              kept outside OneDrive, not a secret
                                                              string in the environment
"""
import functools
import os
from pathlib import Path

import msal

TENANT_ID = os.environ.get("SECOPS_TENANT_ID", "00000000-0000-0000-0000-000000000000")
CLIENT_ID = os.environ.get("SECOPS_GRAPH_CLIENT_ID", "00000000-0000-0000-0000-000000000000")
SCOPE = ["https://graph.microsoft.com/.default"]  # app-only: permissions come from the app's consent, not scope


class AuthError(RuntimeError):
    """Credentials are missing or the tenant rejected them; the message tells the human what to fix."""


def _client_credential() -> str | dict:
    secret = os.environ.get("SECOPS_GRAPH_CLIENT_SECRET")
    if secret:
        return secret
    cert_path, thumbprint = os.environ.get("SECOPS_GRAPH_CERT_PATH"), os.environ.get("SECOPS_GRAPH_CERT_THUMBPRINT")
    if cert_path and thumbprint:
        return {"thumbprint": thumbprint, "private_key": Path(cert_path).read_text(encoding="utf-8")}
    raise AuthError(
        "Set SECOPS_GRAPH_CLIENT_SECRET, or SECOPS_GRAPH_CERT_PATH + SECOPS_GRAPH_CERT_THUMBPRINT "
        "(preferred). See agents/agentD/memory/appRegistration.md for how to provision either."
    )


@functools.lru_cache(maxsize=1)
def _app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=_client_credential(),
    )


def get_token() -> str:
    # MSAL caches the app-only token in memory on the ConfidentialClientApplication instance and
    # refreshes silently when it's near expiry, so this is cheap to call per-request.
    result = _app().acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in result:
        raise AuthError(f"{result.get('error')}: {result.get('error_description')}")
    return result["access_token"]


def check() -> None:
    token = get_token()
    print(
        f"Got an app-only token for client {CLIENT_ID} ({len(token)} chars). "
        "This confirms the credential works, not that SecurityAlert.Read.All / "
        "SecurityIncident.Read.All are consented - try a real call (e.g. get_alert) for that."
    )


if __name__ == "__main__":
    check()
