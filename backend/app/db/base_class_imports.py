"""
Single place that imports every model so Alembic's target_metadata
(and any Base.metadata.create_all call) always sees the full schema.
Import this module, not individual model modules, when you need
"all models registered".
"""
from app.models.user import User, Counter  # noqa: F401
from app.models.product import Product, ProductPriceHistory  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.inventory import InventoryMovement  # noqa: F401
from app.models.sale import Sale, SaleItem, BillSequence  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.supplier import Supplier  # noqa: F401
from app.models.purchase import Purchase, PurchaseItem, PurchasePayment  # noqa: F401
