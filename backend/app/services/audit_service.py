"""
Thin, generic helper for writing to the audit_logs table. Deliberately
does not commit — callers write the audit row in the SAME transaction as
the change it's describing, so it's impossible for an action to succeed
while its audit entry silently fails (or vice versa).
"""
import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def record(
    db: Session,
    user: User,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    notes: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        id=uuid.uuid4(),
        user_id=user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        notes=notes,
    )
    db.add(entry)
    return entry
