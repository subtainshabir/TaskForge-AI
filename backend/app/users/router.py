from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import UserResponse
from app.db.session import get_db
from app.models.user import User
from app.models.user_settings import UserSettings
from app.users.schemas import ProfileUpdateRequest, UserSettingsResponse, UserSettingsUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


def _get_or_create_settings(db: Session, user: User) -> UserSettings:
    settings = db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    ).scalar_one_or_none()
    if settings is None:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/me", response_model=UserResponse)
def read_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if payload.name is not None:
        current_user.name = payload.name
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/settings", response_model=UserSettingsResponse)
def read_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSettings:
    return _get_or_create_settings(db, current_user)


@router.patch("/me/settings", response_model=UserSettingsResponse)
def update_settings(
    payload: UserSettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSettings:
    settings = _get_or_create_settings(db, current_user)
    if payload.theme is not None:
        settings.theme = payload.theme
    db.commit()
    db.refresh(settings)
    return settings