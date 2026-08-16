"""
Product master + price history — Phase 1, extended in Phase 2.

Design notes:
- barcode and internal_code are both nullable but each individually unique
  when present (partial unique indexes), per spec section 13: "a product
  may have a company barcode OR an internal store code, both can exist."
  Postgres allows multiple NULLs under a unique constraint by default, so
  a plain UNIQUE constraint on a nullable column already behaves correctly
  here — no partial index trickery needed.
- sale_price lives on Product as the CURRENT price (fast path for POS/
  search), while ProductPriceHistory is an append-only log. The current
  price is never mutated in place without also inserting a history row —
  that invariant is enforced in the service layer (app/services/
  product_service.py), not the DB, since Postgres can't easily enforce
  "every UPDATE creates a companion INSERT elsewhere" via constraints alone.
- All money fields use NUMERIC(12, 2), never float, per spec section 40/57.
- Deliberately excludes expiry/manufacturing/category/brand/description
  per spec section 13 — do not add these without a spec change.

Phase 2 addition — current_stock:
- A SYNCHRONIZED, DERIVED value, not the source of truth. The source of
  truth is the inventory_movements ledger (app/models/inventory.py).
  current_stock only ever changes inside inventory_service.adjust_stock(),
  which locks this row and writes a companion movement in the SAME
  transaction. That invariant is enforced in the service layer, same
  trade-off as sale_price above — deliberately not a DB trigger per the
  Phase 2 architecture review ("do not add a trigger unless genuinely
  necessary").
- The CHECK constraint below IS a DB-level guarantee, independent of the
  service layer: even a future application bug or a concurrent path that
  forgets to check stock cannot make current_stock negative — Postgres
  itself rejects the UPDATE. This is the amendment-6 requirement ("must
  not allow ... a future application bug to create negative stock") — row
  locking prevents races, but only a constraint prevents a logic error.
"""
import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("current_stock >= 0", name="ck_products_current_stock_non_negative"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    internal_code: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="pcs")  # pcs / kg / litre
    sale_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    reorder_level: Mapped[int] = mapped_column(default=15, nullable=False)
    current_stock: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    price_history: Mapped[list["ProductPriceHistory"]] = relationship(
        "ProductPriceHistory", back_populates="product", order_by="ProductPriceHistory.created_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<Product {self.name}>"


class ProductPriceHistory(Base, TimestampMixin):
    """
    Append-only. A row is inserted every time sale_price changes.
    Historical sales must reference the price at time of sale independently
    (SaleItem.unit_price, added in Phase 2) — this table is for explaining
    "why is the price what it is today", not for recalculating old sales.
    """
    __tablename__ = "product_price_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    old_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    new_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="price_history")

    def __repr__(self) -> str:
        return f"<PriceHistory {self.product_id} {self.old_price}->{self.new_price}>"
