"""
User management — Owner only (spec section 4: "Manage users — Owner ✅ /
Employee ❌").

Phase 1 fix: default_counter_id is now validated against the counters
table BEFORE the insert is attempted. Previously a bogus counter UUID
would only surface as a raw FK IntegrityError at commit time, which then
got no friendly-message treatment — this closes that gap (spec section 48
"never expose raw stack traces").
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_owner
from app.core.security import hash_password
from app.models.user import Counter, User
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _owner: User = Depends(require_owner)) -> list[UserOut]:
    return db.query(User).order_by(User.username).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate, db: Session = Depends(get_db), _owner: User = Depends(require_owner)
) -> UserOut:
    if data.default_counter_id is not None:
        counter = db.get(Counter, data.default_counter_id)
        if counter is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected counter does not exist.",
            )

    user = User(
        username=data.username,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
        default_counter_id=data.default_counter_id,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        msg = str(exc.orig).lower()
        detail = (
            "A user with this username already exists."
            if "username" in msg
            else "Unable to save user due to a data conflict."
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    db.refresh(user)
    return user
