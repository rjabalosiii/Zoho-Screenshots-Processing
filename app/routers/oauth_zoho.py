from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session
from ..db import get_session, init_db
from ..zoho import auth_url, exchange_code_for_tokens
from ..models import ZohoConnection
from datetime import datetime, timedelta
import secrets

router = APIRouter()

@router.get("/start")
def start():
    state = secrets.token_urlsafe(16)
    url = auth_url(state)
    return {"authorize_url": url, "state": state}

@router.get("/callback")
async def callback(code: str, state: str, session: Session = Depends(get_session)):
    # In production validate state against session store
    data = await exchange_code_for_tokens(code)
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_in = int(data.get("expires_in", 3600))
    conn = ZohoConnection(
        org_id="",  # Fill after a whoami/org pick step
        org_name=None,
        zoho_user_id=None,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
    )
    session.add(conn)
    session.commit()
    session.refresh(conn)
    return {"connection_id": conn.id, "message": "Connected. Call /companies/pick to set org_id."}
