"""
Supplier endpoints. Both roles can create/view — same flat pattern as
product creation, not a sensitive action on its own.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.supplier import SupplierCreate, SupplierOut
from app.services.supplier_service import create_supplier

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.post("", response_model=SupplierOut, status_code=201)
def add_supplier(data: SupplierCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SupplierOut:
    return create_supplier(db, data, created_by=user)


@router.get("", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[SupplierOut]:
    return db.query(Supplier).filter(Supplier.is_active.is_(True)).order_by(Supplier.name).all()


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> SupplierOut:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    return supplier
