import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    old_value: str | None
    new_value: str | None
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
