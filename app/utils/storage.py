import os, boto3, uuid, pathlib
from ..config import S3_BUCKET, S3_REGION

def save_bytes(content: bytes, filename: str) -> str:
    if S3_BUCKET and S3_REGION:
        s3 = boto3.client('s3', region_name=S3_REGION)
        key = f"uploads/{uuid.uuid4().hex}_{filename}"
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=content, ContentType='application/octet-stream')
        return f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"
    pathlib.Path("./uploads").mkdir(parents=True, exist_ok=True)
    dest = pathlib.Path("./uploads") / f"{uuid.uuid4().hex}_{filename}"
    dest.write_bytes(content)
    return str(dest)
