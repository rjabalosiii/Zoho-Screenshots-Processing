# app/routers/ocr.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, Tuple
import os, io, re
from datetime import datetime
from PIL import Image
from ..config import USE_GCVISION  # assumes your config sets GOOGLE_APPLICATION_CREDENTIALS when GCP_SA_JSON exists

router = APIRouter()

# ----------------------- Heuristics & regex helpers -----------------------

BANK_PATTERNS = [
    (r"\b(BDO|Banco\s*De\s*Oro)\b", "BDO"),
    (r"\b(BPI|Bank\s*of\s*the\s*Philippine\s*Islands)\b", "BPI"),
    (r"\b(Union\s*Bank|UnionBank)\b", "UnionBank"),
    (r"\b(Metrobank|Metropolitan\s*Bank)\b", "Metrobank"),
    (r"\b(Security\s*Bank)\b", "Security Bank"),
    (r"\b(Land\s*Bank|LandBank)\b", "LandBank"),
    (r"\b(PNB|Philippine\s*National\s*Bank)\b", "PNB"),
    (r"\b(China\s*Bank|Chinabank)\b", "China Bank"),
]

# money / accounts / dates
AMOUNT_RX = re.compile(r"(?:PHP|₱|Php|php)?\s*([0-9]{1,3}(?:[, ]?[0-9]{3})*(?:\.[0-9]{2})?)")
LAST4_RX  = re.compile(r"(?:Acct(?:ount)?(?:\s*No\.?)?|ending\s+in|xxxx|\*{2,}|Acct\s*#?)\D*([0-9]{4})", re.I)
DATE_RX   = re.compile(
    r"\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|[A-Z][a-z]{2,9}\s+\d{1,2},\s*\d{4})\b"
)

AMOUNT_KEYS = ("amount", "amt", "amnt", "total", "php", "transfer amount", "payment", "paid")

def detect_bank(text: str) -> Optional[str]:
    for rx, label in BANK_PATTERNS:
        if re.search(rx, text, flags=re.I):
            return label
    return None

def detect_last4(text: str) -> Optional[str]:
    m = LAST4_RX.search(text)
    return m.group(1) if m else None

def extract_reference(text: str) -> Optional[str]:
    # Normalize a bit
    t = re.sub(r"[^\w\s:/#-]", " ", text)
    low = t.lower()

    # Common “reference” cues
    for key in ("reference", "ref no", "ref#", "ref no.", "transaction reference", "txn id", "transaction no", "pid"):
        m = re.search(rf"{re.escape(key)}\s*(?:number|no\.?|#|:)?\s*([A-Z0-9\-_/]{{5,}})", low, re.I)
        if m:
            return m.group(1).upper()

    # Generic token patterns like FT-XXXX, PID-XXXX, etc.
    m = re.search(r"\b([A-Z]{2,5}-[A-Z0-9]{5,})\b", text)
    return m.group(1) if m else None

def extract_date(text: str) -> Optional[str]:
    m = DATE_RX.search(text)
    if not m:
        return None
    s = m.group(1)
    # Try to normalize to YYYY-MM-DD
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return s  # fallback

def extract_amount(text: str) -> Optional[float]:
    """
    Prefer numbers near amount-like keywords; fallback to largest money-looking number.
    """
    cleaned = text.replace(",", "")
    lower = cleaned.lower()
    best = None

    # 1) keyword proximity
    for key in AMOUNT_KEYS:
        for m in re.finditer(rf"{re.escape(key)}\s*[:=]?\s*(?:php|₱)?\s*([0-9]+(?:\.[0-9]{{2}})?)", lower, re.I):
            try:
                val = float(m.group(1))
                best = val if best is None or val > best else best
            except Exception:
                pass
    if best is not None:
        return best

    # 2) generic amounts
    for m in AMOUNT_RX.finditer(cleaned):
        try:
            val = float(m.group(1))
            best = val if best is None or val > best else best
        except Exception:
            pass
    return best

# --------------------------- OCR engines ----------------------------------

def _ocr_google_vision(image_bytes: bytes) -> Tuple[str, float, str]:
    try:
        from google.cloud import vision
    except Exception as e:
        raise HTTPException(500, f"Google Vision package not available: {e}")

    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not gac or not os.path.exists(gac):
        raise HTTPException(500, f"Vision credentials not found. GOOGLE_APPLICATION_CREDENTIALS='{gac}'")

    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    ctx   = vision.ImageContext(language_hints=["en", "fil", "tl"])
    # Better for screenshots with layout
    resp = client.document_text_detection(image=image, image_context=ctx)

    if resp.error.message:
        raise HTTPException(502, f"Vision error: {resp.error.message}")

    full_text = resp.full_text_annotation.text if resp.full_text_annotation else ""

    confs = []
    try:
        for page in resp.full_text_annotation.pages:
            for block in page.blocks:
                if hasattr(block, "confidence"):
                    confs.append(block.confidence)
    except Exception:
        pass
    conf = sum(confs)/len(confs) if confs else 0.90
    return full_text, float(conf), "en,fil,tl"

def _ocr_naive(_: bytes) -> Tuple[str, float, str]:
    return "", 0.10, "none"

def do_ocr(image_bytes: bytes) -> Tuple[str, float, str]:
    return _ocr_google_vision(image_bytes) if USE_GCVISION else _ocr_naive(image_bytes)

# ------------------------------ Routes ------------------------------------

class RouteBody(BaseModel):
    bank_name: Optional[str] = None
    account_last4: Optional[str] = None

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """
    Upload an image; returns OCR text and best-guess structured fields.
    """
    try:
        content = await file.read()

        # Light pre-processing: upscale very small screenshots to help OCR
        if len(content) < 150_000:
            img = Image.open(io.BytesIO(content)).convert("RGB")
            w, h = img.size
            if max(w, h) < 1200:
                scale = max(1.5, 1200 / max(w, h))
                img = img.resize((int(w * scale), int(h * scale)))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=90)
                content = buf.getvalue()

        text, confidence, _ = do_ocr(content)

        bank   = detect_bank(text or "")
        last4  = detect_last4(text or "")
        amount = extract_amount(text or "")
        refno  = extract_reference(text or "")
        date_  = extract_date(text or "")

        return {
            "text": text,
            "confidence": round(confidence, 3),
            "bank_name": bank,
            "account_last4": last4,
            "amount_guess": amount,
            "reference_guess": refno,
            "date_guess": date_,
            "filename": file.filename,
            "bytes": len(content),
        }
    except HTTPException:
        raise
    except Exception as e:
        # surface exact reason instead of generic 500
        raise HTTPException(500, f"OCR pipeline error: {e}")

# Diagnostics (safe to keep during setup; remove later if desired)
@router.get("/_diag")
def ocr_diag():
    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    return {
        "use_gcvision": USE_GCVISION,
        "gac_path": gac,
        "gac_exists": bool(gac and os.path.exists(gac)),
    }

@router.post("/route")
async def route(_: RouteBody):
    """
    Placeholder routing: always ask user to pick a company until
    /rules/bank is implemented to remember bank->connection_id.
    """
    return {"needs_choice": True, "connection_id": None, "confidence": 0.5}
