import os

from fastapi import HTTPException, UploadFile

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))


async def read_vcf_text(file: UploadFile) -> str:
    """Read an uploaded VCF as text, enforcing a size limit and UTF-8 encoding."""
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"VCF file exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
        )
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="VCF file must be UTF-8 text.")
