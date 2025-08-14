from fastapi import FastAPI
from .routers import oauth_zoho, companies, accounts, rules, ocr, books

app = FastAPI(title="Zoho Multi-company Journal Backend")

app.include_router(oauth_zoho.router, prefix="/oauth/zoho", tags=["oauth"])
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(rules.router, prefix="/rules", tags=["rules"])
app.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
app.include_router(books.router, prefix="/books", tags=["books"])

@app.get("/health")
def health():
    return {"ok": True}
