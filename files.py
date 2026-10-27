import os, uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.core.config import settings

MAGIC_SIGNATURES = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}
async def save_upload(upload: UploadFile) -> tuple[str, int, str]:
    original = Path(upload.filename or "upload").name
    ext = Path(original).suffix.lower()
    if ext not in settings.allowed_extensions_set:
        raise HTTPException(415, detail=f"File extension not allowed: {ext or '(none)'}")
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{ext}"
    target = Path(settings.STORAGE_DIR) / stored
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    total = 0
    first_chunk = b""
    try:
        with target.open("wb") as f:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk: break
                if not first_chunk: first_chunk = chunk[:16]
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(413, detail=f"File exceeds {settings.MAX_FILE_SIZE_MB} MB limit")
                f.write(chunk)
        signature = MAGIC_SIGNATURES.get(ext)
        if signature and not any(first_chunk.startswith(s) for s in signature):
            raise HTTPException(415, detail="File content does not match its extension")
        return stored, total, upload.content_type or "application/octet-stream"
    except Exception:
        target.unlink(missing_ok=True)
        raise
