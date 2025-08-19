# app/routers/ocr.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, Tuple
import re
import io
import os

from ..config import USE_GCVISION

router = APIRouter()

# --- Helpers ---------------------------------------------------------------

BANK_PATTERNS = [
    (r"\b(BDO|Banco De Oro)\b", "BDO"),
    (r"\b(BPI|Bank of the Philippine Islands)\b", "BPI"),
    (r"\b(UnionBank|Union Bank)\b", "UnionBank"),
    (r"\b(Metrobank|Metropolitan Bank)\b", "Metrobank"),
    (r"\b(Security Bank)\b", "Security Bank"),
    (r"\b(LandBank|Land Bank)\b", "LandBank"),
    (r"\b(PNB|Philippine National Bank)\b", "PNB"),
    (r"\b(China Bank|Chinabank)\b", "China Bank"),
]

AMOUNT_RX = re.compile(r"(?:PHP|₱|Php|php)?\s*([0-9]{1,3}(?:[, ]?[0-9]{3})*(?:\.[0-9]{2})?)")
LAST4_RX = re.compile(r"(?:Acct(?:ount)?(?:\s*No\.?)?|\bxxxx|\b\*{2,}|ending\s+in|Acct\s*#?)\D*([0-9]{4})", re.I)

def normalize_amount(text: str) -> Optional[float]:
    # Return the largest money-like number (usually the transfer amount)
    cands = []
    for m in AMOUNT_RX.finditer(text.replace(",", "")):
        try:
            cands.append(float(m.group(1)))
        except Exception:
            pass
    return max(cands) if cands else None

def detect_bank(text: str) -> Optional[str]:
    for rx, label in BANK_PATTERNS:
        if re.search(rx, text, re.I):
            return label
    return None

def detect_last4(text: str) -> Optional[str]:
    m = LAST4_RX.search(text)
    return m.group(1) if m else None

# --- Google Vision / OCR ---------------------------------------------------

def _ocr_google_vision(image_bytes: bytes) -> Tuple[str, float, str]:
    """
    Returns (full_text, confidence_estimate, language_hint_used)
    """
    try:
        from google.cloud import vision
    except Exception as e:
        raise HTTPException(500, f"Google Vision not installed: {e}")

    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)

    # Hints: English + Filipino/Tagalog
    # Vision uses BCP-47; 'fil' is Filipino, 'tl' Tagalog; both are safe hints.
    image_context = vision.ImageContext(language_hints=["en", "fil", "tl"])

    response = client.document_text_detection(image=image, image_context=image_context)
    if response.error.message:
        raise HTTPException(502, f"Vision error: {response.error.message}")

    full_text = response.full_text_annotation.text if response.full_text_annotation else ""
    # Confidence heuristic: average block confidence if available
    confs = []
    try:
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                if hasattr(block, "confidence"):
                    confs.append(block.confidence)
    except Exception:
        pass
    conf = sum(confs) / len(confs) if confs else 0.90  # default optimistic
    return full_text, float(conf), "en,fil,tl"

def _ocr_naive(image_bytes: bytes) -> Tuple[str, float, str]:
    # Minimal fallback: we don't run Tesseract here to keep the image lean.
    # Just return empty and low confidence so UI prompts manual input.
    return "", 0.10, "none"

def do_ocr(image_bytes: bytes) -> Tuple[str, float, str]:
    if USE_GCVISION:
        return _ocr_google_vision(image_bytes)
    return _ocr_naive(image_bytes)

# --- Routes ----------------------------------------------------------------

class RouteBody(BaseModel):
    bank_name: Optional[str] = None
    account_last4: Optional[str] = None

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    # Read bytes
    content = await file.read()

    # (Optional) quick pre-processing: upscale small screenshots
    # to help OCR; Vision doesn't need much, but upscaling helps tiny text.
    if len(content) < 150_000:
        try:
            from PIL import Image
            import io as _io
            img = Image.open(_io.BytesIO(content)).convert("RGB")
            w, h = img.size
            if max(w, h) < 1200:
                scale = max(1.5, 1200 / max(w, h))
                img = img.resize((int(w*scale), int(h*scale)))
                buf = _io.BytesIO()
                img.save(buf, format="JPEG", quality=90)
                content = buf.getvalue()
        except Exception:
            pass

    text, confidence, lang = do_ocr(content)
    bank = detect_bank(text or "")
    last4 = detect_last4(text or "")
    amount = normalize_amount(text or "")

    return {
        "text": text,
        "confidence": round(confidence, 3),
        "language": lang,
        "bank_name": bank,
        "account_last4": last4,
        "amount_guess": amount,
        "filename": file.filename,
        "bytes": len(content)
    }

@router.post("/route")
async def route(body: RouteBody):
    """
    Heuristic: if we already know a bank->company rule (not implemented here),
    this would return that connection_id. For now we just signal if user must pick.
    """
    # Minimal behavior: force a pick until your /rules/bank is used.
    needs_choice = True
    return {"needs_choice": needs_choice, "connection_id": None, "confidence": 0.5}
