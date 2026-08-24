"""
Purchases — Phase 3: stock receiving from suppliers.

Design notes (mirrors the Sale/SaleItem/Payment shape from Phase 2 on
the inbound side, deliberately — same review-approved patterns, not a
new architecture):

- PurchaseItem stores product_name as a SNAPSHOT (same reasoning as
  SaleItem.product_name: a purchase's historical record must not shift
  if the product is later renamed). unit_cost is NOT a snapshot in the
  same sense — it IS the authoritative cost for that batch, and doubles
  as a FIFO cost layer for a future profit-reporting phase (ordered by
  Purchase.created_at). No separate CostLayer table — that would just
  be duplicating this data for a consumer that doesn't exist yet.

- PurchasePayment is 1:N from Purchase (never a single amount_paid
  column), same reasoning as Payment being 1:N from Sale: the store
  normally pays cash in full at receiving, but "we do not normally pay
  advances" leaves room for the exception (partial payment now, rest
  later). outstanding is computed on read, never stored — same
  discipline as the Phase 2 reconciliation report.

- mismatch_acknowledged: approved decision — any nonzero difference
  between computed_total and invoice_total must be an enforced backend
  gate (409 on save), not just a passive UI warning. This column
  persists WHETHER a discrepancy was reviewed and knowingly accepted,
  so it's answerable later even after the purchase is saved.

- No internal sequential purchase number (approved decision) — the
  supplier's own invoice_number + invoice_date + created_at are what
  identify a purchase for the store's records. Purchases don't get a
  customer-facing printed receipt the way sales do, so there's no
  BillSequence-equivalent need here.

- Purchase is immutable once saved — same principle as Sale (spec
  70.2). Corrections go through a STOCK_ADJUSTMENT movement (already
  defined, Owner-only, already audited), never by editing this row.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Purchase(Base, TimestampMixin):
    __tablename__ = "purchases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)

    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    invoice_total: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    computed_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    mismatch_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    received_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    supplier: Mapped["Supplier"] = relationship("Supplier")  # noqa: F821
    received_by: Mapped["User"] = relationship("User", foreign_keys=[received_by_user_id])  # noqa: F821
    items: Mapped[list["PurchaseItem"]] = relationship(
        "PurchaseItem", back_populates="purchase", order_by="PurchaseItem.id"
    )
    payments: Mapped[list["PurchasePayment"]] = relationship(
        "PurchasePayment", back_populates="purchase", order_by="PurchasePayment.paid_at"
    )

    @property
    def amount_paid(self) -> Decimal:
        """Computed on read from payments — never stored, same discipline
        as the Phase 2 reconciliation report (don't persist derived state)."""
        return sum((Decimal(str(p.amount)) for p in self.payments), Decimal("0.00"))

    @property
    def outstanding(self) -> Decimal:
        reference_total = Decimal(str(self.invoice_total)) if self.invoice_total is not None else Decimal(str(self.computed_total))
        return reference_total - self.amount_paid

    def __repr__(self) -> str:
        return f"<Purchase {self.invoice_number or self.id} supplier={self.supplier_id}>"


class PurchaseItem(Base, TimestampMixin):
    __tablename__ = "purchase_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchases.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)

    product_name: Mapped[str] = mapped_column(String(200), nullable=False)  # snapshot
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)  # actually counted, not invoice-claimed
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    purchase: Mapped["Purchase"] = relationship("Purchase", back_populates="items")
    product: Mapped["Product"] = relationship("Product")  # noqa: F821

    def __repr__(self) -> str:
        return f"<PurchaseItem {self.product_name} x{self.quantity} @ {self.unit_cost}>"


class PurchasePayment(Base, TimestampMixin):
    __tablename__ = "purchase_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchases.id"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    purchase: Mapped["Purchase"] = relationship("Purchase", back_populates="payments")
    user: Mapped["User"] = relationship("User")  # noqa: F821

    def __repr__(self) -> str:
        return f"<PurchasePayment {self.amount} purchase={self.purchase_id}>"
