import os
from dotenv import load_dotenv

load_dotenv()

ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID", "")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET", "")
ZOHO_REDIRECT_URI = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:8000/oauth/zoho/callback")
ZOHO_SCOPES = os.getenv("ZOHO_SCOPES", "ZohoBooks.fullaccess.all")
APP_SECRET = os.getenv("APP_SECRET", "devsecret")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

USE_GCVISION = os.getenv("USE_GCVISION", "0") == "1"
S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("S3_REGION")
