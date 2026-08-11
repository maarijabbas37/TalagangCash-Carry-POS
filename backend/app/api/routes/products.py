"""
Product master endpoints.

Per spec section 4 permission table, Employee has "Add Product: Limited"
and "Change Sale Price: ❌". Phase 1 interpretation (documented, not
silently assumed): employees can CREATE new products (they receive
purchases and need to add unlisted items on the spot, per section 17's
workflow) but cannot change the price of an EXISTING product via this
endpoint — that requires the dedicated /price endpoint, which is
owner-only. If the store's actual practice differs, this is the seam to
adjust.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_owner
from app.models.product import Product
from app.models.user import User
from app.schemas.product import PriceUpdate, ProductCreate, ProductOut, ProductUpdate
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
    data: ProductCreate, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> ProductOut:
    return create_product(db, data)


@router.put("/{product_id}", response_model=ProductOut)
def edit_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ProductOut:
    product = _get_product_or_404(db, product_id)
    return update_product(db, product, data)


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


@router.get("/{product_id}/price-history")
def price_history(
    product_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    product = _get_product_or_404(db, product_id)
    return product.price_history
