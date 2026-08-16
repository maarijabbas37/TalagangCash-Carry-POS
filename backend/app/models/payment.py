"""
Payment — separate table, separate module, from Sale (spec section 25's
own blueprint: SALES → SALE_ITEMS → PAYMENTS as distinct entities).

Phase 2 architecture review amendment (#5): NO UNIQUE constraint on
sale_id. Phase 2's service layer creates exactly one Payment per Sale —
that is a service-layer/business-rule fact for THIS phase, not a schema
constraint. A future split-payment phase adds a second Payment row and a
service-layer check that sum(payments.amount) == sale.net_total; it does
not require touching this table's shape.

payment_reference (amendment #4): nullable, unused in Phase 2 (QR stays
manual-confirm-only, no gateway). Exists now so a future phase that adds
real reference-number capture (or reconciliation against JazzCash/
Easypaisa statements) is a data-entry change, not a migration.
"""
import uuid

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.sale import PaymentMethod


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=False, index=True)

    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="payment_method"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # Cash-only fields; NULL for QR.
    amount_received: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    change_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # QR-only field (amendment #4); NULL for cash, NULL for QR in Phase 2
    # too since there's no gateway to produce a real reference from yet.
    payment_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    counter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("counters.id"), nullable=False)

    sale: Mapped["Sale"] = relationship("Sale", back_populates="payments")  # noqa: F821
    user: Mapped["User"] = relationship("User")  # noqa: F821
    counter: Mapped["Counter"] = relationship("Counter")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Payment {self.payment_method} {self.amount} sale={self.sale_id}>"
