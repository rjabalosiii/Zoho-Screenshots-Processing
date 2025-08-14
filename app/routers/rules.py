from fastapi import APIRouter, Depends
from sqlmodel import Session
from ..db import get_session
from ..models import BankOrgRule, MappingRule

router = APIRouter()

@router.post("/bank")
def add_bank_rule(bank_name: str, account_last4: str, connection_id: int, session: Session = Depends(get_session)):
    rule = BankOrgRule(bank_name=bank_name.lower(), account_last4=account_last4, connection_id=connection_id)
    session.add(rule)
    session.commit()
    return {"ok": True, "id": rule.id}

@router.post("/mapping")
def add_mapping(pattern: str, debit_account_id: str, credit_account_id: str, connection_id: int, session: Session = Depends(get_session)):
    rule = MappingRule(pattern=pattern.lower(), debit_account_id=debit_account_id, credit_account_id=credit_account_id, connection_id=connection_id)
    session.add(rule)
    session.commit()
    return {"ok": True, "id": rule.id}
