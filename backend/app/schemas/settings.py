from pydantic import BaseModel


class StoreSettingsOut(BaseModel):
    """
    Receipt/business identity only — deliberately not a general settings
    endpoint. Nothing here is sensitive; scoped to authenticated users
    only because there's no reason for it to be public, not because the
    values themselves need protecting.
    """
    store_name: str
    store_address: str
    store_phone: str
