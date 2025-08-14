from fastapi import APIRouter, Depends
from sqlmodel import Session
from ..db import get_session
from ..models import ZohoConnection
from ..zoho import refresh_access_token, get_accounts

router = APIRouter()

@router.get("")
async def list_accounts(connection_id: int, session: Session = Depends(get_session)):
    conn = session.get(ZohoConnection, connection_id)
    if not conn or not conn.org_id:
        return {"error": "invalid connection"}
    conn = await refresh_access_token(conn, session)
    accounts = await get_accounts(conn.org_id, conn.access_token)
    out = []
    for a in accounts:
        out.append({
            "account_id": a.get("account_id") or a.get("account_id".upper(), ""),
            "name": a.get("account_name") or a.get("name", ""),
            "code": a.get("account_code") or a.get("code", ""),
            "type": a.get("account_type") or a.get("type", ""),
        })
    return out
