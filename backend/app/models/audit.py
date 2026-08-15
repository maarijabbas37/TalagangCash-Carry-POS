"""
Immutable audit log (spec section 39). Services only ever INSERT here —
no route updates or deletes a row.

Introduced in the Phase 1 fixes (not Phase 2): once product edits and
price changes are restricted to the Owner, "restricted" on its own isn't
enough — the spec's own standard is that the owner can always answer
"who changed this, when, old value, new value" (section 28). This table
is that answer. Kept intentionally generic (action/entity_type/entity_id)
so later phases (sales, inventory, cash) reuse it instead of inventing
parallel logs.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # e.g. PRODUCT_UPDATED, PRICE_CHANGED
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "product"
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Deliberately created_at only, no updated_at — an audit row that could
    # be "updated" would defeat the point of an immutable log.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped["User"] = relationship("User")  # noqa: F821

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.entity_type}={self.entity_id}>"
