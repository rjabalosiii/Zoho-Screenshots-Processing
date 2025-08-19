from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, Tuple
import re, io, os
from PIL import Image
from ..config import USE_GCVISION, GOOGLE_APPLICATION_CREDENTIALS

router = APIRouter()

# --- helpers (same as before)... BANK_PATTERNS / AMOUNT_RX / LAST4_RX / normalize_amount / detect_bank / detect_last4 ---

def _ocr_google_vision(image_bytes: bytes) -> Tuple[str, float, str]:
    try:
        from google.cloud import vision
    except Exception as e:
        raise HTTPException(500, f"Google Vision package not available: {e}")

    # quick credential sanity
    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not gac or not os.path.exists(gac):
        raise HTTPException(500, f"Vision credentials not found. GOOGLE_APPLICATION_CREDENTIALS='{gac}'")

    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    ctx = vision.ImageContext(language_hints=["en", "fil", "tl"])
    resp = client.document_text_detection(image=image, image_context=ctx)

    if resp.error.message:
        # surface real Vision error
        raise HTTPException(502, f"Vision error: {resp.error.message}")

    text = resp.full_text_annotation.text if resp.full_text_annotation else ""
    confs = []
    try:
        for page in resp.full_text_annotation.pages:
            for block in page.blocks:
                if hasattr(block, "confidence"):
                    confs.append(block.confidence)
    except Exception:
        pass
    conf = sum(confs)/len(confs) if confs else 0.90
    return text, float(conf), "en,fil,tl"

def _ocr_naive(_: bytes) -> Tuple[str, float, str]:
    return "", 0.10, "none"

def do_ocr(image_bytes: bytes) -> Tuple[str, float, str]:
    return _ocr_google_vision(image_bytes) if USE_GCVISION else _ocr_naive(image_bytes)

class RouteBody(BaseModel):
    bank_name: Optional[str] = None
    account_last4: Optional[str] = None

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        content = await file.read()
        # upscale tiny screenshots a bit
        if len(content) < 150_000:
            img = Image.open(io.BytesIO(content)).convert("RGB")
            w, h = img.size
            if max(w, h) < 1200:
                scale = max(1.5, 1200 / max(w, h))
                img = img.resize((int(w*scale), int(h*scale)))
                buf = io.BytesIO(); img.save(buf, format="JPEG", quality=90)
                content = buf.getvalue()

        text, confidence, _ = do_ocr(content)
        bank = detect_bank(text or "")
        last4 = detect_last4(text or "")
        amount = normalize_amount(text or "")
        return {
            "text": text, "confidence": round(confidence, 3),
            "bank_name": bank, "account_last4": last4,
            "amount_guess": amount, "filename": file.filename, "bytes": len(content)
        }
    except HTTPException:
        raise
    except Exception as e:
        # show exact backend reason instead of generic 500
        raise HTTPException(500, f"OCR pipeline error: {e}")

# optional quick diag route (remove after debugging)
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
    return {"needs_choice": True, "connection_id": None, "confidence": 0.5}
