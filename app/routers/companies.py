from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from ..db import get_session, init_db
from ..models import ZohoConnection
from ..schemas import CompanyOut

router = APIRouter()

@router.get("", response_model=list[CompanyOut])
def list_companies(session: Session = Depends(get_session)):
    conns = session.exec(select(ZohoConnection)).all()
    return [CompanyOut(id=c.id, org_id=c.org_id or "", org_name=c.org_name) for c in conns]

@router.post("/pick")
def set_org(connection_id: int, org_id: str, org_name: str | None = None, session: Session = Depends(get_session)):
    conn = session.get(ZohoConnection, connection_id)
    if not conn:
        return {"error": "connection not found"}
    conn.org_id = org_id
    conn.org_name = org_name
    session.add(conn)
    session.commit()
    return {"ok": True}
