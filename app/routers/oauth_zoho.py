from fastapi import APIRouter, Depends
from sqlmodel import Session
from datetime import datetime, timedelta
import secrets
from ..db import get_session
from ..zoho import auth_url, exchange_code_for_tokens
from ..models import ZohoConnection

router = APIRouter()

@router.get("/start")
def start():
    state = secrets.token_urlsafe(16)
    url = auth_url(state)
    return {"authorize_url": url, "state": state}

@router.get("/callback")
async def callback(code: str, state: str, session: Session = Depends(get_session)):
    data = await exchange_code_for_tokens(code)
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_in = int(data.get("expires_in", 3600))
    conn = ZohoConnection(
        org_id="",
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
    )
    session.add(conn)
    session.commit()
    session.refresh(conn)
    return {"connection_id": conn.id, "message": "Connected. Call /companies/pick to set org_id."}
