# app/config.py
import os
from pathlib import Path
from textwrap import dedent

# Core app settings
APP_SECRET = os.getenv("APP_SECRET", "change_me")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Zoho OAuth
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID", "")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET", "")
ZOHO_REDIRECT_URI = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:8000/oauth/zoho/callback")
ZOHO_SCOPES = os.getenv("ZOHO_SCOPES", "ZohoBooks.fullaccess.all")
ZOHO_DC = os.getenv("ZOHO_DC", "com")

# OCR / Google Vision
USE_GCVISION = os.getenv("USE_GCVISION", "0") == "1"
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

# If user provided the JSON content as an env var, write it to /tmp and point the SDK to it.
GCP_SA_JSON = os.getenv("GCP_SA_JSON", "").strip()
if USE_GCVISION and not GOOGLE_APPLICATION_CREDENTIALS and GCP_SA_JSON:
    TMP = Path("/tmp/gcp_sa.json")
    TMP.write_text(GCP_SA_JSON)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(TMP)
    GOOGLE_APPLICATION_CREDENTIALS = str(TMP)
