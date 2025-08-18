# app/zoho.py
import os
import httpx
from datetime import datetime, timedelta
from sqlmodel import Session
from .models import ZohoConnection
from .config import ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REDIRECT_URI

# ----- Data center & endpoints -----
# If you ever use a non-.com Zoho account, set ZOHO_DC to: eu, in, com.au, or jp
DC = os.getenv("ZOHO_DC", "com").strip()

# OAuth host stays on accounts.zoho.<dc>
OAUTH_DOMAIN = f"https://accounts.zoho.{DC}"

# ✅ Use the recommended zohoapis.com host for API calls
# Books v3 base path:
API_BASE = f"https://www.zohoapis.{DC}/books/v3"


def auth_url(state: str) -> str:
    """
    Build the user consent URL for OAuth.
    """
    # Scopes come from env (e.g., ZohoBooks.fullaccess.all) via config
    from .config import ZOHO_SCOPES
    return (
        f"{OAUTH_DOMAIN}/oauth/v2/auth?response_type=code"
        f"&client_id={ZOHO_CLIENT_ID}"
        f"&scope={ZOHO_SCOPES}"
        f"&redirect_uri={ZOHO_REDIRECT_URI}"
        f"&access_type=offline"
        f"&state={state}"
        f"&prompt=consent"
    )


async def exchange_code_for_tokens(code: str) -> dict:
    """
    OAuth code -> access_token + refresh_token
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OAUTH_DOMAIN}/oauth/v2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": ZOHO_CLIENT_ID,
                "client_secret": ZOHO_CLIENT_SECRET,
                "redirect_uri": ZOHO_REDIRECT_URI,
                "code": code,
            },
            timeout=30.0,
        )
    resp.raise_for_status()
    return resp.json()


async def refresh_access_token(conn: ZohoConnection, session: Session) -> ZohoConnection:
    """
    Ensure we have a fresh access_token for the given connection.
    """
    if conn.expires_at and conn.expires_at > datetime.utcnow() + timedelta(seconds=60):
        return conn

    if not conn.refresh_token:
        raise RuntimeError("Missing refresh_token on ZohoConnection.")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OAUTH_DOMAIN}/oauth/v2/token",
            data={
                "grant_type": "refresh_token",
                "client_id": ZOHO_CLIENT_ID,
                "client_secret": ZOHO_CLIENT_SECRET,
                "refresh_token": conn.refresh_token,
            },
            timeout=30.0,
        )
    resp.raise_for_status()
    data = resp.json()

    conn.access_token = data.get("access_token")
    expires_in = int(data.get("expires_in", 3600))
    conn.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    session.add(conn)
    session.commit()
    session.refresh(conn)
    return conn


async def get_accounts(org_id: str, access_token: str) -> list:
    """
    Fetch Chart of Accounts for the org.
    """
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE}/chartofaccounts",
            headers=headers,
            params={"organization_id": org_id},
            timeout=30.0,
        )
    # Better error visibility (surface Zoho's message)
    if resp.status_code >= 400:
        raise httpx.HTTPStatusError(
            f"{resp.status_code} from Zoho: {resp.text}",
            request=resp.request,
            response=resp,
        )
    data = resp.json()
    # Zoho sometimes uses slightly different keys; handle both
    return data.get("chartofaccounts", []) or data.get("chart_of_accounts", []) or []


async def post_journal(org_id: str, access_token: str, payload: dict) -> dict:
    """
    Create a journal entry.
    payload must include:
      - date (YYYY-MM-DD)
      - reference_number (optional)
      - notes (optional)
      - line_items: [{account_id, debit_or_credit, amount}, ...]
    """
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/journalentries",
            headers=headers,
            params={"organization_id": org_id},
            json=payload,
            timeout=30.0,
        )
    if resp.status_code >= 400:
        raise httpx.HTTPStatusError(
            f"{resp.status_code} from Zoho: {resp.text}",
            request=resp.request,
            response=resp,
        )
    return resp.json()
