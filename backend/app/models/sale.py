"""
Sales — Phase 2 core.

Design notes:
- bill_number is assigned via BillSequence (a single-row table locked
  with SELECT ... FOR UPDATE inside the SAME transaction as the sale).
  Deliberately NOT a Postgres native SEQUENCE: a sequence's advancement
  does not roll back with the transaction, so a failed sale (e.g.
  insufficient stock) would still burn a number and leave a visible gap.
  The locked-counter approach ties the number reservation to the same
  transaction as everything else — a rollback undoes the reservation too.
- SaleItem stores product_name and unit_price as a SNAPSHOT at sale time.
  Product.name or Product.sale_price changing later must never alter a
  historical sale (spec section 14/19/70.3/70.4).
- discount_user_id records who applied the discount (both roles are
  currently allowed to discount without a cap — see AuditLog for the
  companion DISCOUNT_APPLIED entry that makes this reviewable later).
- Sale has no soft-delete / edit path. Completed sales are immutable
  (spec 70.2) — corrections happen via a future CustomerReturn (Phase 4),
  never by editing this row.

Phase 2 architecture review amendment: Payment is deliberately modeled as
a ONE-TO-MANY relationship from Sale (see app/models/payment.py) even
though Phase 2's UI and service layer only ever create exactly one
Payment per Sale. There is no UNIQUE(sale_id) constraint on Payment — the
absence of that constraint is the whole point: split payments (part cash,
part QR) become a service-layer change in a future phase, not a schema
migration, because the schema was never narrowed to assume one payment.
"""
import enum
import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    QR = "QR"


class BillSequence(Base):
    """Single-row counter table. Locked with FOR UPDATE when issuing a bill number."""
    __tablename__ = "bill_sequence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Sale(Base, TimestampMixin):
    __tablename__ = "sales"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)

    counter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("counters.id"), nullable=False)
    cashier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    net_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    counter: Mapped["Counter"] = relationship("Counter")  # noqa: F821
    cashier: Mapped["User"] = relationship("User", foreign_keys=[cashier_id])  # noqa: F821
    items: Mapped[list["SaleItem"]] = relationship("SaleItem", back_populates="sale", order_by="SaleItem.id")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="sale", order_by="Payment.created_at")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Sale #{self.bill_number} total={self.net_total}>"


class SaleItem(Base, TimestampMixin):
    __tablename__ = "sale_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)

    # Snapshots — historical sales must never shift when the product changes.
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    sale: Mapped["Sale"] = relationship("Sale", back_populates="items")
    product: Mapped["Product"] = relationship("Product")  # noqa: F821

    def __repr__(self) -> str:
        return f"<SaleItem {self.product_name} x{self.quantity}>"
