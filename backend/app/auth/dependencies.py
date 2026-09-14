from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import TokenExpiredError, TokenInvalidError, decode_access_token
from app.db.session import get_db
from app.models.user import User

_WWW_AUTHENTICATE = {"WWW-Authenticate": "Bearer"}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=_WWW_AUTHENTICATE,
    )


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if authorization is None:
        raise _unauthorized("Not authenticated")

    scheme, _, token = authorization.partition(" ")
    if not token or scheme.lower() != "bearer":
        raise _unauthorized("Invalid authentication scheme")

    try:
        payload = decode_access_token(token)
    except TokenExpiredError:
        raise _unauthorized("Token has expired")
    except TokenInvalidError:
        raise _unauthorized("Could not validate credentials")

    subject = payload.get("sub")
    if subject is None:
        raise _unauthorized("Could not validate credentials")

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise _unauthorized("Could not validate credentials")

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized("Could not validate credentials")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user