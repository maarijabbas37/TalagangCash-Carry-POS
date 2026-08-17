"""
Store identity for receipts — single source of truth so the frontend
never hardcodes STORE_NAME/ADDRESS/PHONE separately from the backend's
.env (spec section 56: "do not hardcode store-specific values").
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.settings import StoreSettingsOut

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=StoreSettingsOut)
def get_store_settings(_user: User = Depends(get_current_user)) -> StoreSettingsOut:
    return StoreSettingsOut(
        store_name=settings.STORE_NAME,
        store_address=settings.STORE_ADDRESS,
        store_phone=settings.STORE_PHONE,
    )
