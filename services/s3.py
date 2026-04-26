import uuid
import os
import config

# ── Local fallback when AWS keys are not configured ──────
LOCAL_UPLOAD_DIR = "local_uploads"


def _local_save(file_bytes: bytes, filename: str) -> str:
    os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4()}_{filename}"
    path = os.path.join(LOCAL_UPLOAD_DIR, unique_name)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return f"local://{path}"


async def upload_file_to_s3(file_bytes: bytes, filename: str) -> str:
    """
    Upload file to AWS S3.
    Falls back to local disk if AWS keys are not set (for development).
    """
    if not config.AWS_ACCESS_KEY_ID or config.AWS_ACCESS_KEY_ID.startswith("PUT_"):
        print("[S3] AWS not configured — saving locally.")
        return _local_save(file_bytes, filename)

    try:
        import boto3
        s3 = boto3.client(
            "s3",
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=config.AWS_REGION,
        )
        key = f"submissions/{uuid.uuid4()}_{filename}"
        s3.put_object(
            Bucket=config.S3_BUCKET,
            Key=key,
            Body=file_bytes,
            ContentType="application/octet-stream",
        )
        url = f"https://{config.S3_BUCKET}.s3.{config.AWS_REGION}.amazonaws.com/{key}"
        print(f"[S3] Uploaded: {url}")
        return url
    except Exception as e:
        print(f"[S3] Error: {e} — falling back to local save.")
        return _local_save(file_bytes, filename)
