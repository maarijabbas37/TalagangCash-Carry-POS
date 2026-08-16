"""
Inventory endpoints.

opening-stock is Owner-only (Phase 2 review amendment 2: employees must
never be able to call this — it's initialization/migration stock, not a
normal entry mechanism). reconciliation is Owner-only too, since it's a
diagnostic view of a business-sensitive problem (shrinkage/discrepancy),
not something a cashier needs mid-shift.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_owner
from app.models.inventory import InventoryMovement
from app.models.product import Product
from app.models.user import User
from app.schemas.inventory import InventoryMovementOut, OpeningStockIn, ReconciliationReport
from app.schemas.product import ProductOut
from app.services.inventory_service import record_opening_stock, reconcile_stock

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.post("/opening-stock", response_model=ProductOut, status_code=201)
def add_opening_stock(
    data: OpeningStockIn, db: Session = Depends(get_db), owner: User = Depends(require_owner)
) -> ProductOut:
    return record_opening_stock(db, data.product_id, data.quantity, owner, data.notes)


@router.get("/{product_id}", response_model=list[InventoryMovementOut])
def get_movements(
    product_id: uuid.UUID,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[InventoryMovementOut]:
    """Recent movement history for one product — the answer to
    'why does the system say we have N of this?' (spec section 16)."""
    return (
        db.query(InventoryMovement)
        .filter(InventoryMovement.product_id == product_id)
        .order_by(InventoryMovement.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/reconciliation/report", response_model=ReconciliationReport)
def get_reconciliation_report(
    product_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _owner: User = Depends(require_owner),
) -> ReconciliationReport:
    """
    Phase 2 architecture review §1 (mandatory): compares ledger-derived
    stock against products.current_stock and surfaces any mismatch.
    Read-only — does not correct anything.
    """
    return reconcile_stock(db, product_id)
