from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class ZohoConnection(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: str = ""
    org_name: Optional[str] = None
    zoho_user_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AccountCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    connection_id: int = Field(index=True)
    account_id: str
    name: str
    code: Optional[str] = None
    type: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BankOrgRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bank_name: str
    account_last4: str
    alt_fingerprint: Optional[str] = None
    connection_id: int
    confidence_floor: float = 0.85
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MappingRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pattern: str
    debit_account_id: str
    credit_account_id: str
    tax_code: Optional[str] = None
    connection_id: int
    confidence_floor: float = 0.85
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Upload(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    content_type: Optional[str] = None
    sha256: Optional[str] = None
    bank_guess: Optional[str] = None
    ocr_text: Optional[str] = None
    ocr_conf: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    upload_id: int
    connection_id: Optional[int] = Field(default=None, index=True)
    date: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = "PHP"
    reference: Optional[str] = None
    payer: Optional[str] = None
    payee: Optional[str] = None
    status: str = "pending"
    idempotency_key: Optional[str] = None
    books_journal_id: Optional[str] = None
    notes: Optional[str] = None
