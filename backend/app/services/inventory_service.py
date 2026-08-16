"""
The single choke point for every stock change in the system (spec section
15/42; Phase 2 architecture review §1/§6).

adjust_stock() does NOT commit — callers (sale_service, the opening-stock
route) control the transaction boundary so a sale's stock decrements and
the Sale/SaleItem/Payment rows it belongs to either all land together or
none do (spec section 10: "the sale must be atomic").

Two independent layers protect against negative stock, deliberately not
just one:
  1. Row locking (SELECT ... FOR UPDATE) + an application-level check
     here, which produces the friendly "Insufficient stock" error.
  2. A DB-level CHECK constraint on products.current_stock (see the
     model and migration 0003), which is what actually makes it
     IMPOSSIBLE — not just unlikely — for a future bug or an overlooked
     code path to write negative stock. If this function's check were
     ever accidentally bypassed, Postgres itself would still reject the
     UPDATE. The friendly error above is UX; the CHECK constraint is the
     real guarantee.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.inventory import InventoryMovement, MovementType
from app.models.product import Product
from app.models.user import User
from app.schemas.inventory import ReconciliationReport, StockDiscrepancy


def adjust_stock(
    db: Session,
    product_id: uuid.UUID,
    quantity_delta: Decimal,
    movement_type: MovementType,
    user: User,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> Product:
    """
    Locks the product row (SELECT ... FOR UPDATE) so two counters
    decrementing the same product concurrently serialize on this row
    instead of racing (spec section 42). Raises HTTP 409 with the exact
    "Insufficient stock" message on a would-be-negative result — but see
    module docstring: the DB CHECK constraint is the real backstop, this
    is the friendly early exit.
    """
    product = db.query(Product).filter(Product.id == product_id).with_for_update().first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    new_stock = Decimal(str(product.current_stock)) + quantity_delta

    if new_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Insufficient stock for '{product.name}'. Available quantity: {product.current_stock}.",
        )

    movement = InventoryMovement(
        id=uuid.uuid4(),
        product_id=product.id,
        quantity=quantity_delta,
        movement_type=movement_type,
        reference_type=reference_type,
        reference_id=reference_id,
        user_id=user.id,
        notes=notes,
    )
    product.current_stock = new_stock
    db.add(movement)
    db.add(product)
    return product


def record_opening_stock(db: Session, product_id: uuid.UUID, quantity: Decimal, user: User, notes: str | None) -> Product:
    """
    Owner-only bridge until Phase 3 (purchases) exists — see
    app/models/inventory.py module docstring.

    Phase 2 architecture review amendment 2, explicitly: this is
    INITIALIZATION/MIGRATION stock, not a recurring inventory-entry
    mechanism, and it must not become a way to quietly paper over
    physical/system discrepancies. Enforced here by:
      - route-level require_owner (employees cannot call this at all —
        the specific gap the amendment calls out)
      - always writing BOTH an InventoryMovement (reason: OPENING_STOCK,
        distinct from STOCK_ADJUSTMENT) AND an AuditLog entry, so any
        use of this endpoint is reviewable exactly like any other
        sensitive action
      - notes field always available for the owner to record WHY
        (e.g. "initial catalog setup, 12-Aug-2026")
    What this function deliberately does NOT do: silently reconcile
    against the ledger, or offer a "just fix the number" shortcut. If the
    owner is using this weeks after go-live to explain away a shrinkage
    problem rather than to onboard a genuinely new product, that's a
    process problem no code guard can fully prevent — but the audit trail
    at least makes it visible after the fact, which is the point.
    """
    product = adjust_stock(
        db,
        product_id=product_id,
        quantity_delta=quantity,
        movement_type=MovementType.OPENING_STOCK,
        user=user,
        reference_type="opening_stock",
        notes=notes,
    )
    db.add(
        AuditLog(
            id=uuid.uuid4(),
            user_id=user.id,
            action="OPENING_STOCK_RECORDED",
            entity_type="product",
            entity_id=product.id,
            old_value=None,
            new_value=str(quantity),
            notes=notes or "Opening stock entry (pre-Phase-3 initialization bridge).",
        )
    )
    db.commit()
    db.refresh(product)
    return product


def reconcile_stock(db: Session, product_id: uuid.UUID | None = None) -> ReconciliationReport:
    """
    Phase 2 architecture review §1 (mandatory): recomputes stock from the
    inventory_movements ledger (SUM of all movements per product) and
    compares it against products.current_stock. Any mismatch means the
    fast-read cache and the source-of-truth ledger have drifted — which
    should be structurally impossible given adjust_stock()'s invariant,
    but this is exactly the tool to CATCH it if that invariant is ever
    violated (a raw SQL fix, a bug, a manual DB edit under pressure during
    an incident). This is the direct answer to the store's real,
    pre-existing problem: "system says 10 but rack says 4" becoming
    invisible (spec section 26).

    Read-only. Does not correct anything — correction is a deliberate,
    audited STOCK_ADJUSTMENT action (Phase 3+), never an automatic side
    effect of running a report.
    """
    query = db.query(
        Product.id,
        Product.name,
        Product.current_stock,
        func.coalesce(func.sum(InventoryMovement.quantity), 0).label("ledger_stock"),
    ).outerjoin(InventoryMovement, InventoryMovement.product_id == Product.id)

    if product_id is not None:
        query = query.filter(Product.id == product_id)

    rows = query.group_by(Product.id, Product.name, Product.current_stock).all()

    discrepancies: list[StockDiscrepancy] = []
    for row in rows:
        current = Decimal(str(row.current_stock))
        ledger = Decimal(str(row.ledger_stock))
        if current != ledger:
            discrepancies.append(
                StockDiscrepancy(
                    product_id=row.id,
                    product_name=row.name,
                    current_stock=current,
                    ledger_stock=ledger,
                    difference=current - ledger,
                )
            )

    return ReconciliationReport(
        checked_at=datetime.now(timezone.utc),
        products_checked=len(rows),
        discrepancies=discrepancies,
    )
