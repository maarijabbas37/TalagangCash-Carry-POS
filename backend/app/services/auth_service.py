"""
Business logic for authentication. Kept out of the route handler per
spec section 52 ("business logic belongs in services, not route handlers").
"""
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.user import User


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def issue_token_for_user(user: User) -> str:
    return create_access_token(subject=str(user.id), extra_claims={"role": user.role.value})
