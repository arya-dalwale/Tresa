from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.profile import Profile
from app.models.user import User
from app.schemas.user import (
    ProfileResponse,
    UserMeResponse,
    UserProfileUpdate,
)


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserMeResponse,
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.scalar(
        select(Profile).where(Profile.user_id == current_user.id)
    )

    return UserMeResponse(
        id=str(current_user.id),
        email=current_user.email,
        is_active=current_user.is_active,
        role=current_user.role,
        profile=(
            ProfileResponse.model_validate(profile)
            if profile is not None
            else None
        ),
    )


@router.patch(
    "/me",
    response_model=UserMeResponse,
)
def update_my_profile(
    request: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.scalar(
        select(Profile).where(Profile.user_id == current_user.id)
    )

    if profile is None:
        if request.full_name is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="full_name is required when creating a profile",
            )

        profile = Profile(
            user_id=current_user.id,
            full_name=request.full_name,
            phone_number=request.phone_number,
            bio=request.bio,
            profile_photo_url=request.profile_photo_url,
        )

        db.add(profile)

    else:
        if request.full_name is not None:
            profile.full_name = request.full_name

        if request.phone_number is not None:
            profile.phone_number = request.phone_number

        if request.bio is not None:
            profile.bio = request.bio

        if request.profile_photo_url is not None:
            profile.profile_photo_url = request.profile_photo_url

    db.commit()
    db.refresh(profile)

    return UserMeResponse(
        id=str(current_user.id),
        email=current_user.email,
        is_active=current_user.is_active,
        role=current_user.role,
        profile=ProfileResponse.model_validate(profile),
    )