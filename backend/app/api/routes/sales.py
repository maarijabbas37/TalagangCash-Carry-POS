"""
POS sale endpoints.

POST /api/sales is the one endpoint in the whole system where getting
the transaction boundary right matters most — see app/services/
sale_service.py for the atomic flow. Every other route here is read-only
and side-effect-free by construction (see get_sale's docstring), which is
what makes reprint safe.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.sale import Sale
from app.models.user import User
from app.schemas.sale import SaleCreate, SaleOut
from app.services.sale_service import create_sale, get_sale, get_sale_by_bill_number

router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.post("", response_model=SaleOut, status_code=201)
def checkout(data: SaleCreate, db: Session = Depends(get_db), cashier: User = Depends(get_current_user)) -> SaleOut:
    """Any authenticated user (Owner or Employee) — both roles run POS."""
    return create_sale(db, data, cashier)


@router.get("/{sale_id}", response_model=SaleOut)
def get_sale_detail(sale_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> SaleOut:
    """Receipt data. Calling this again (reprint) never creates anything — read-only."""
    return get_sale(db, sale_id)


@router.get("/by-bill-number/{bill_number}", response_model=SaleOut)
def get_sale_by_number(bill_number: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> SaleOut:
    """Cashiers reference bills by their human-facing number, not a UUID."""
    return get_sale_by_bill_number(db, bill_number)


@router.get("", response_model=list[SaleOut])
def list_sales(
    counter_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=25, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[SaleOut]:
    """Basic listing — groundwork for Phase 7 reporting, not built out yet."""
    query = db.query(Sale)
    if counter_id:
        query = query.filter(Sale.counter_id == counter_id)
    return query.order_by(Sale.created_at.desc()).limit(limit).all()
