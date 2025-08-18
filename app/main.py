from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import oauth_zoho, companies, accounts, rules, ocr, books

# ✅ import init_db
from .db import init_db

app = FastAPI(title="Zoho Multi-company Journal Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ run init_db at startup so tables exist
@app.on_event("startup")
def _init():
    init_db()

app.include_router(oauth_zoho.router, prefix="/oauth/zoho", tags=["oauth"])
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(rules.router, prefix="/rules", tags=["rules"])
app.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
app.include_router(books.router, prefix="/books", tags=["books"])

@app.get("/health")
def health():
    return {"ok": True}
