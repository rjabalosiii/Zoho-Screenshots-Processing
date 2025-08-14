import hashlib
def id_key(bank: str, date: str, amount: float, reference: str, account_last4: str) -> str:
    payload = f"{bank or ''}|{date or ''}|{amount or 0}|{reference or ''}|{account_last4 or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
