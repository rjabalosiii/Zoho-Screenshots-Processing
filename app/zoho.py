import httpx
from datetime import datetime, timedelta
from sqlmodel import Session
from .models import ZohoConnection
from .config import ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REDIRECT_URI

OAUTH_DOMAIN = "https://accounts.zoho.com"
API_BASE = "https://books.zoho.com/api/v3"

def auth_url(state: str) -> str:
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
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{OAUTH_DOMAIN}/oauth/v2/token", data={
            "grant_type": "authorization_code",
            "client_id": ZOHO_CLIENT_ID,
            "client_secret": ZOHO_CLIENT_SECRET,
            "redirect_uri": ZOHO_REDIRECT_URI,
            "code": code,
        })
    resp.raise_for_status()
    return resp.json()

async def refresh_access_token(conn: ZohoConnection, session: Session) -> ZohoConnection:
    if conn.expires_at and conn.expires_at > datetime.utcnow() + timedelta(seconds=60):
        return conn
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{OAUTH_DOMAIN}/oauth/v2/token", data={
            "grant_type": "refresh_token",
            "client_id": ZOHO_CLIENT_ID,
            "client_secret": ZOHO_CLIENT_SECRET,
            "refresh_token": conn.refresh_token,
        })
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
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/chartofaccounts", headers=headers, params={"organization_id": org_id})
    resp.raise_for_status()
    data = resp.json()
    return data.get("chartofaccounts", []) or data.get("chart_of_accounts", []) or []

async def post_journal(org_id: str, access_token: str, payload: dict) -> dict:
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_BASE}/journalentries", headers=headers, params={"organization_id": org_id}, json=payload)
    resp.raise_for_status()
    return resp.json()
