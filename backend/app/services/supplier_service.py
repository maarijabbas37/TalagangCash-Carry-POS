"""
Supplier business logic. Mirrors product_service.create_product()'s
shape: create, write an audit entry, commit.
"""
import json
import uuid

from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.supplier import SupplierCreate
from app.services.audit_service import record as record_audit
from sqlalchemy.orm import Session


def create_supplier(db: Session, data: SupplierCreate, created_by: User) -> Supplier:
    supplier = Supplier(
        id=uuid.uuid4(),
        name=data.name,
        phone=data.phone,
        address_notes=data.address_notes,
    )
    db.add(supplier)
    db.flush()

    record_audit(
        db,
        user=created_by,
        action="SUPPLIER_CREATED",
        entity_type="supplier",
        entity_id=supplier.id,
        new_value=json.dumps({"name": supplier.name}, default=str),
    )

    db.commit()
    db.refresh(supplier)
    return supplier
