from fastapi import APIRouter, UploadFile, File, Depends
from sqlmodel import Session, select
import hashlib
from ..db import get_session
from ..models import Upload, BankOrgRule
from ..schemas import OCRResult, RouteRequest, RouteResponse
from ..utils.storage import save_bytes
from ..config import USE_GCVISION

router = APIRouter()

def _extract_bank_and_last4(text: str):
    t = (text or "").lower()
    bank = None
    if "bpi" in t: bank = "BPI"
    if "bdo" in t: bank = "BDO"
    last4 = None
    return bank, last4

@router.post("/upload", response_model=OCRResult)
async def upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
    content = await file.read()
    sha = hashlib.sha256(content).hexdigest()
    file_url = save_bytes(content, file.filename)

    text = ""
    conf = 0.85

    if USE_GCVISION:
        try:
            from google.cloud import vision
            client = vision.ImageAnnotatorClient()
            image = vision.Image(content=content)
            resp = client.document_text_detection(image=image)
            if resp and resp.full_text_annotation and resp.full_text_annotation.text:
                text = resp.full_text_annotation.text
                conf = 0.9
        except Exception:
            text = ""
            conf = 0.7

    if not text:
        text = "STUB OCR TEXT"
        conf = 0.7

    bank_name, account_last4 = _extract_bank_and_last4(text)

    up = Upload(filename=file.filename, content_type=file.content_type, sha256=sha, bank_guess=bank_name, ocr_text=text, ocr_conf=conf)
    session.add(up)
    session.commit()

    return OCRResult(bank_name=bank_name, account_last4=account_last4, text=text, confidence=conf)

@router.post("/route", response_model=RouteResponse)
def route(req: RouteRequest, session: Session = Depends(get_session)):
    rule = session.exec(select(BankOrgRule).where(BankOrgRule.bank_name == (req.bank_name or '').lower(), BankOrgRule.account_last4 == (req.account_last4 or ''))).first()
    if rule:
        return RouteResponse(connection_id=rule.connection_id, confidence=0.95, needs_choice=False)
    return RouteResponse(connection_id=None, confidence=0.5, needs_choice=True)
