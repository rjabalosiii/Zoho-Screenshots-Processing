# Multi-company Zoho Books Journal Uploader (FastAPI scaffold)

This is a minimal backend scaffold for your Lovable front end. It supports:
- Connecting multiple Zoho Books organizations via OAuth
- Caching each org's Chart of Accounts
- Uploading screenshots, running OCR (stub), parsing fields, and routing to the correct org
- Creating mapping rules that learn over time
- Posting balanced journal entries into the selected Zoho Books org

## How to run

1. `cd backend`
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in your Zoho OAuth app credentials
5. `uvicorn app.main:app --reload`

Open http://localhost:8000/docs for the interactive API.

## Notes
- OCR is a stub. Replace with Google Vision or AWS Textract. Keep raw text for audit.
- All posting to Zoho requires the org_id in the header and the valid access token for that connection.
- The database is SQLite for simplicity. You can switch to Postgres by changing `DATABASE_URL`.
