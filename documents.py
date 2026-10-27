from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
    Query,
    BackgroundTasks,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User, Role
from app.models.document import Document, DocumentShare
from app.schemas.documents import DocumentOut
from app.services.files import save_upload
from app.services.audit import log_action
from app.core.config import settings


router = APIRouter(prefix="/documents", tags=["Documents"])


def can_read(db: Session, doc: Document, user: User) -> bool:
    if user.role == Role.ADMIN or doc.owner_id == user.id:
        return True

    share = db.scalar(
        select(DocumentShare).where(
            DocumentShare.document_id == doc.id,
            DocumentShare.shared_with_user_id == user.id,
        )
    )
    return bool(share)


def _upload_notice(email: str, filename: str):
    import logging

    logging.getLogger("document_api").info(
        "Upload notification queued for %s (%s)",
        email,
        filename,
    )


@router.post(
    "/upload",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stored, size, content_type = await save_upload(file)

    doc = Document(
        original_filename=Path(file.filename or stored).name,
        stored_filename=stored,
        content_type=content_type,
        size_bytes=size,
        owner_id=user.id,
    )

    try:
        db.add(doc)
        db.flush()

        log_action(
            db,
            user.id,
            "document.uploaded",
            doc.id,
            doc.original_filename,
        )

        db.commit()
        db.refresh(doc)

    except Exception:
        db.rollback()
        (Path(settings.STORAGE_DIR) / stored).unlink(missing_ok=True)
        raise

    background_tasks.add_task(
        _upload_notice,
        user.email,
        doc.original_filename,
    )

    return doc


@router.post(
    "/upload-multiple",
    response_model=list[DocumentOut],
    status_code=status.HTTP_201_CREATED,
)
async def upload_multiple(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required",
        )

    created = []
    saved_paths = []

    try:
        for file in files:
            stored, size, content_type = await save_upload(file)
            saved_paths.append(Path(settings.STORAGE_DIR) / stored)

            doc = Document(
                original_filename=Path(file.filename or stored).name,
                stored_filename=stored,
                content_type=content_type,
                size_bytes=size,
                owner_id=user.id,
            )

            db.add(doc)
            db.flush()

            log_action(
                db,
                user.id,
                "document.uploaded",
                doc.id,
                doc.original_filename,
            )

            created.append(doc)

        db.commit()

        for doc in created:
            db.refresh(doc)

        return created

    except Exception:
        db.rollback()

        for path in saved_paths:
            path.unlink(missing_ok=True)

        raise

    finally:
        for file in files:
            await file.close()


@router.get("", response_model=list[DocumentOut])
def list_documents(
    q: str | None = None,
    sort: str = Query(
        "newest",
        pattern="^(newest|oldest|name)$",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    shared_ids = select(DocumentShare.document_id).where(
        DocumentShare.shared_with_user_id == user.id
    )

    stmt = select(Document).where(
        or_(
            Document.owner_id == user.id,
            Document.id.in_(shared_ids),
        )
    )

    if user.role == Role.ADMIN:
        stmt = select(Document)

    if q:
        stmt = stmt.where(
            Document.original_filename.ilike(f"%{q}%")
        )

    if sort == "oldest":
        stmt = stmt.order_by(Document.created_at.asc())
    elif sort == "name":
        stmt = stmt.order_by(Document.original_filename.asc())
    else:
        stmt = stmt.order_by(Document.created_at.desc())

    return list(
        db.scalars(stmt.offset(skip).limit(limit)).all()
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = db.get(Document, document_id)

    if not doc:
        raise HTTPException(404, detail="Document not found")

    if not can_read(db, doc, user):
        raise HTTPException(
            403,
            detail="You do not have access to this document",
        )

    return doc


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = db.get(Document, document_id)

    if not doc:
        raise HTTPException(404, detail="Document not found")

    if not can_read(db, doc, user):
        raise HTTPException(
            403,
            detail="You do not have access to this document",
        )

    if user.id != doc.owner_id and user.role != Role.ADMIN:
        share = db.scalar(
            select(DocumentShare).where(
                DocumentShare.document_id == doc.id,
                DocumentShare.shared_with_user_id == user.id,
            )
        )

        if not share or not share.can_download:
            raise HTTPException(
                403,
                detail="Download permission not granted",
            )

    path = Path(settings.STORAGE_DIR) / doc.stored_filename

    if not path.is_file():
        raise HTTPException(404, detail="Stored file is missing")

    log_action(db, user.id, "document.downloaded", doc.id)
    db.commit()

    return FileResponse(
        path,
        media_type=doc.content_type,
        filename=doc.original_filename,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = db.get(Document, document_id)

    if not doc:
        raise HTTPException(404, detail="Document not found")

    if doc.owner_id != user.id and user.role != Role.ADMIN:
        raise HTTPException(
            403,
            detail="Only the owner or admin can delete this document",
        )

    path = Path(settings.STORAGE_DIR) / doc.stored_filename

    log_action(
        db,
        user.id,
        "document.deleted",
        doc.id,
        doc.original_filename,
    )

    db.delete(doc)
    db.commit()
    path.unlink(missing_ok=True)

    return None
