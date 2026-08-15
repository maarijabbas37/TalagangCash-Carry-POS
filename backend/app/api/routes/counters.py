"""
Counter lookup — needed by Phase 2's POS (a sale must reference a valid
counter) and by user creation (default_counter_id).

Any authenticated user can list counters: both Owner and Employee need to
know which counters exist to operate the POS, and a counter itself isn't
sensitive information (unlike products' cost data or user accounts).
Only active counters are returned — a deactivated counter shouldn't be
selectable for a new sale.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import Counter, User
from app.schemas.auth import CounterOut

router = APIRouter(prefix="/api/counters", tags=["counters"])


@router.get("", response_model=list[CounterOut])
def list_counters(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[CounterOut]:
    return db.query(Counter).filter(Counter.is_active.is_(True)).order_by(Counter.code).all()
