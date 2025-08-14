from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from ..db import get_session
from ..models import ZohoConnection
from ..schemas import JournalIn
from ..zoho import refresh_access_token, post_journal

router = APIRouter()

@router.post("/journal")
async def post_journal_entry(payload: JournalIn, session: Session = Depends(get_session)):
    conn = session.get(ZohoConnection, payload.connection_id)
    if not conn or not conn.org_id:
        raise HTTPException(status_code=400, detail="Invalid connection")
    conn = await refresh_access_token(conn, session)
    journal_payload = {
        "date": payload.date,
        "reference_number": payload.reference or "",
        "notes": payload.notes or "",
        "line_items": [
            {"account_id": payload.credit_account_id, "debit_or_credit": "credit", "amount": payload.amount},
            {"account_id": payload.debit_account_id, "debit_or_credit": "debit", "amount": payload.amount}
        ]
    }
    data = await post_journal(conn.org_id, conn.access_token, journal_payload)
    return {"ok": True, "zoho_response": data}
