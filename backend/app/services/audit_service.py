from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit_log(db: Session, *, action: str, username: str, description: str) -> AuditLog:
    log = AuditLog(type_action=action, username=username, description=description)
    db.add(log)
    db.flush()
    return log
