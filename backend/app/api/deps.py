"""
Shared FastAPI dependencies: DB session, current-user resolution, and
role-based access guards.

Role enforcement lives here (not scattered per-route) so the section-4
permission matrix has exactly one place to read and change.
"""
import uuid
from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import RoleName, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_raw)
    except (ValueError, TypeError, AttributeError):
        raise credentials_exception from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_owner(current_user: User = Depends(get_current_user)) -> User:
    """
    Use this dependency on any endpoint restricted to Owner per spec
    section 4 (change sale price, stock adjustment, supplier payment,
    user management, settings, full reports, etc).
    """
    if current_user.role != RoleName.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires owner privileges.",
        )
    return current_user
