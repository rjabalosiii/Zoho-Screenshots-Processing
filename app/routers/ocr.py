# app/routers/ocr.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, Tuple
import re, io, os
from PIL import Image
from ..config import USE_GCVISION

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

AMOUNT_RX = re.compile(r"(?:PHP|₱|Php|php)?\s*([0-9]{1,3}(?:[, ]?[0-9]{3})*(?:\.[0-9]{2})?)")
LAST4_RX  = re.compile(r"(?:Acct(?:ount)?(?:\s*No\.?)?|ending\s+in|xxxx|\*{2,}|Acct\s*#?)\D*([0-9]{4})", re.I)

def normalize_amount(text: str) -> Optional[float]:
    nums = []
    # remove thousands separators to make float() simple
    clean = text.replace(",", "").replace(" ", "")
    for m in AMOUNT_RX.finditer(clean):
        try:
            nums.append(float(m.group(1)))
        except Exception:
            pass
    return max(nums) if nums else None

def detect_bank(text: str) -> Optional[str]:
    for rx, label in BANK_PATTERNS:
        if re.search(rx, text, flags=re.I):
            return label
    return None

def detect_last4(text: str) -> Optional[str]:
    m = LAST4_RX.search(text)
    return m.group(1) if m else None

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

    # document_text_detection is better for screenshots with layout
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
    # fallback when Vision is disabled
    return "", 0.10, "none"

def do_ocr(image_bytes: bytes) -> Tuple[str, float, str]:
    return _ocr_google_vision(image_bytes) if USE_GCVISION else _ocr_naive(image_bytes)

# ------------------------------ Routes ------------------------------------

class RouteBody(BaseModel):
    bank_name: Optional[str] = None
    account_last4: Optional[str] = None

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        content = await file.read()

        # Light pre-processing: upscale small screenshots to help OCR a bit
        if len(content) < 150_000:
            img = Image.open(io.BytesIO(content)).convert("RGB")
            w, h = img.size
            if max(w, h) < 1200:
                scale = max(1.5, 1200 / max(w, h))
                img = img.resize((int(w*scale), int(h*scale)))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=90)
                content = buf.getvalue()

        text, confidence, _ = do_ocr(content)
        bank   = detect_bank(text or "")
        last4  = detect_last4(text or "")
        amount = normalize_amount(text or "")

        return {
            "text": text,
            "confidence": round(confidence, 3),
            "bank_name": bank,
            "account_last4": last4,
            "amount_guess": amount,
            "filename": file.filename,
            "bytes": len(content),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"OCR pipeline error: {e}")

# Diagnostics (remove in prod if you like)
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
    # for now, always force a company pick until you add bank->company rules
    return {"needs_choice": True, "connection_id": None, "confidence": 0.5}
