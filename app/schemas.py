from typing import Optional, List
from pydantic import BaseModel

class CompanyOut(BaseModel):
    id: int
    org_id: str
    org_name: Optional[str]

class AccountOut(BaseModel):
    account_id: str
    name: str
    code: Optional[str] = None
    type: Optional[str] = None

class OCRResult(BaseModel):
    bank_name: Optional[str]
    account_last4: Optional[str]
    text: str
    confidence: float

class RouteRequest(BaseModel):
    bank_name: Optional[str]
    account_last4: Optional[str]

class RouteResponse(BaseModel):
    connection_id: Optional[int]
    confidence: float
    needs_choice: bool

class JournalIn(BaseModel):
    connection_id: int
    date: str
    amount: float
    reference: Optional[str] = None
    debit_account_id: str
    credit_account_id: str
    currency: Optional[str] = "PHP"
    notes: Optional[str] = None
