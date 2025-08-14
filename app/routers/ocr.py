from fastapi import APIRouter, UploadFile, File, Depends
from sqlmodel import Session, select
import hashlib
from ..db import get_session
from ..models import Upload, BankOrgRule
from ..schemas import OCRResult, RouteRequest, RouteResponse

router = APIRouter()

@router.post("/upload", response_model=OCRResult)
async def upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
    content = await file.read()
    sha = hashlib.sha256(content).hexdigest()
    # TODO: call real OCR. For now we return a stub.
    text = "STUB OCR TEXT"
    bank_name = "BPI"
    account_last4 = "1234"
    up = Upload(filename=file.filename, content_type=file.content_type, sha256=sha, bank_guess=bank_name, ocr_text=text, ocr_conf=0.9)
    session.add(up)
    session.commit()
    return OCRResult(bank_name=bank_name, account_last4=account_last4, text=text, confidence=0.9)

@router.post("/route", response_model=RouteResponse)
def route(req: RouteRequest, session: Session = Depends(get_session)):
    fingerprint = f"{(req.bank_name or '').lower()}:{req.account_last4 or ''}"
    rule = session.exec(select(BankOrgRule).where(BankOrgRule.bank_name == (req.bank_name or '').lower(), BankOrgRule.account_last4 == (req.account_last4 or ''))).first()
    if rule:
        return RouteResponse(connection_id=rule.connection_id, confidence=0.95, needs_choice=False)
    return RouteResponse(connection_id=None, confidence=0.5, needs_choice=True)
