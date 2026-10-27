from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User, Role
from app.models.document import Document, DocumentShare
from app.schemas.documents import ShareCreate, ShareOut
from app.services.audit import log_action

router = APIRouter(prefix="/sharing", tags=["Document sharing"])
@router.post("/{document_id}", response_model=ShareOut, status_code=201)
def share_document(document_id: int, payload: ShareCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = db.get(Document, document_id)
    if not doc: raise HTTPException(404, detail="Document not found")
    if doc.owner_id != user.id and user.role not in (Role.ADMIN, Role.MANAGER):
        raise HTTPException(403, detail="Only owner, manager, or admin can share this document")
    target = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not target: raise HTTPException(404, detail="Target user not found")
    if target.id == user.id: raise HTTPException(400, detail="Cannot share a document with yourself")
    share = db.scalar(select(DocumentShare).where(DocumentShare.document_id == doc.id, DocumentShare.shared_with_user_id == target.id))
    if share:
        share.can_download = payload.can_download
    else:
        share = DocumentShare(document_id=doc.id, shared_with_user_id=target.id, can_download=payload.can_download)
        db.add(share)
    log_action(db, user.id, "document.shared", doc.id, f"shared with user {target.id}")
    db.commit(); db.refresh(share)
    return share

@router.delete("/{document_id}/{target_user_id}", status_code=204)
def revoke_share(document_id: int, target_user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = db.get(Document, document_id)
    if not doc: raise HTTPException(404, detail="Document not found")
    if doc.owner_id != user.id and user.role != Role.ADMIN: raise HTTPException(403, detail="Only owner or admin can revoke sharing")
    share = db.scalar(select(DocumentShare).where(DocumentShare.document_id == document_id, DocumentShare.shared_with_user_id == target_user_id))
    if not share: raise HTTPException(404, detail="Share not found")
    db.delete(share); log_action(db, user.id, "document.share_revoked", doc.id); db.commit()
    return None
