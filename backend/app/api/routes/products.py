"""
Product master endpoints.

Phase 1 fix (was previously a gap flagged in audit): general product
edits — including is_active — are now Owner-only. Employees can still
CREATE new products (per spec section 17's purchase-receiving workflow;
"Add Product: Employee Limited" in the permission table), but cannot
alter an existing product's identity, barcode, internal code, or active
status. Every create/edit/price-change writes an AuditLog entry (see
app/services/product_service.py) — this endpoint being restricted only
matters if the restriction is also reviewable.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_owner
from app.models.product import Product
from app.models.user import User
from app.schemas.product import PriceHistoryOut, PriceUpdate, ProductCreate, ProductOut, ProductUpdate
from app.services.product_service import change_product_price, create_product, update_product

router = APIRouter(prefix="/api/products", tags=["products"])


def _get_product_or_404(db: Session, product_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


@router.get("", response_model=list[ProductOut])
def search_products(
    q: str | None = Query(default=None, description="Matches name, barcode, or internal code"),
    limit: int = Query(default=25, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[ProductOut]:
    """
    Fast product search for POS (spec section 63: search must feel
    instantaneous; never load the whole catalog into the browser).
    Always paginated/limited.
    """
    query = db.query(Product).filter(Product.is_active.is_(True))
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Product.name.ilike(like), Product.barcode == q, Product.internal_code == q)
        )
    return query.order_by(Product.name).limit(limit).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> ProductOut:
    return _get_product_or_404(db, product_id)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def add_product(
    data: ProductCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ProductOut:
    """Any authenticated user (Owner or Employee) — see module docstring."""
    return create_product(db, data, created_by=user)


@router.put("/{product_id}", response_model=ProductOut)
def edit_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
) -> ProductOut:
    """
    Owner-only (Phase 1 fix). Covers name/barcode/internal_code/unit/
    reorder_level/is_active — all treated as "sensitive product
    information" per the audit finding. Sale price is intentionally
    excluded from this schema entirely; it only ever changes via the
    dedicated /price endpoint below so a price-history row is guaranteed.
    """
    product = _get_product_or_404(db, product_id)
    return update_product(db, product, data, changed_by=owner)


@router.put("/{product_id}/price", response_model=ProductOut)
def change_price(
    product_id: uuid.UUID,
    data: PriceUpdate,
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
) -> ProductOut:
    """Owner-only, per spec section 4. Always creates a price-history row."""
    product = _get_product_or_404(db, product_id)
    return change_product_price(db, product, data.new_price, changed_by=owner)


@router.get("/{product_id}/price-history", response_model=list[PriceHistoryOut])
def price_history(
    product_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    product = _get_product_or_404(db, product_id)
    return product.price_history
