from sqlalchemy.orm import Session
from app.models.document import AuditLog

def log_action(db: Session, actor_id: int | None, action: str, document_id: int | None = None, detail: str | None = None):
    db.add(AuditLog(actor_user_id=actor_id, action=action, document_id=document_id, detail=detail))
