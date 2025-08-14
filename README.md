# Zoho Multi-company Journal Uploader (FastAPI)

## Run locally
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then edit .env
uvicorn app.main:app --reload
```
Open http://localhost:8000/docs

## Deploy (Railway/Render)
- Ensure `Procfile` exists (it does)
- Set env vars from `.env.example`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
