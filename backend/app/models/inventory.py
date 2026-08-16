"""
Inventory ledger — source of truth for stock (spec section 15).

Product.current_stock is a synchronized fast-read cache; this table is
the ledger it's derived from. adjust_stock() (app/services/
inventory_service.py) is the ONLY place that writes both — see that
module's docstring for the enforcement discussion and its trade-offs.

Full movement-type enum is defined now (Phase 2 review requirement) even
though Phase 2 only ever emits SALE and OPENING_STOCK — so Phase 3+
(purchases, returns, packing) don't need a migration just to add enum
values, only to add the code paths that emit them.
"""
import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class MovementType(str, enum.Enum):
    OPENING_STOCK = "OPENING_STOCK"
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    CUSTOMER_RETURN = "CUSTOMER_RETURN"
    SUPPLIER_RETURN = "SUPPLIER_RETURN"
    STOCK_ADJUSTMENT = "STOCK_ADJUSTMENT"
    PACKING_IN = "PACKING_IN"
    PACKING_OUT = "PACKING_OUT"


class InventoryMovement(Base, TimestampMixin):
    __tablename__ = "inventory_movements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )

    # Signed: positive = stock in, negative = stock out. NUMERIC (not
    # integer) because unit can be kg/litre with fractional amounts.
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)

    movement_type: Mapped[MovementType] = mapped_column(Enum(MovementType, name="movement_type"), nullable=False)

    # Loosely-typed pointer to whatever caused this movement (a Sale today,
    # a future Purchase/CustomerReturn/etc). Deliberately not a hard FK —
    # the referenced table varies by movement_type. This is a documented
    # trade-off: we lose DB-level referential integrity on this one column
    # in exchange for one unified ledger instead of N parallel movement
    # tables (spec section 16 wants "explain why stock = X" answerable
    # from one place).
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped["Product"] = relationship("Product")  # noqa: F821

    def __repr__(self) -> str:
        return f"<InventoryMovement {self.movement_type} {self.quantity} product={self.product_id}>"
