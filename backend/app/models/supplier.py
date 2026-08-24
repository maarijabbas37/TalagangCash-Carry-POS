"""
Suppliers — Phase 3.

Deliberately minimal: name, phone, address notes, active flag. No credit
terms, no payment-due tracking, no supplier categories. The store's own
paper register + signature process (per the Phase 3 design discussion)
stays offline; this system's job is just to know which supplier a
purchase came from and let the owner see that supplier's history.
"""
import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Supplier {self.name}>"
