from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.persistent_group import (
    CreatePersistentGroupRequest,
    JoinPersistentGroupRequest,
    PersistentGroupListResponse,
    PersistentGroupResponse,
    UpdatePersistentGroupStatusRequest,
)
from app.services.persistent_group_service import (
    build_persistent_group_response,
    create_persistent_group,
    get_persistent_group,
    join_persistent_group,
    list_user_persistent_groups,
    update_persistent_group_status,
)


router = APIRouter(
    prefix="/groups",
    tags=["Persistent Travel Groups"],
)


@router.post(
    "",
    response_model=PersistentGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    data: CreatePersistentGroupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a persistent group with the creator as its first member."""

    group = create_persistent_group(
        db=db,
        user=current_user,
        journey_id=data.journey_id,
    )

    return build_persistent_group_response(
        db=db,
        group=group,
    )


@router.get(
    "",
    response_model=PersistentGroupListResponse,
)
def list_my_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List persistent groups that contain the current user."""

    groups = list_user_persistent_groups(
        db=db,
        user=current_user,
    )

    return PersistentGroupListResponse(
        groups=[
            build_persistent_group_response(
                db=db,
                group=group,
            )
            for group in groups
        ]
    )


@router.get(
    "/{group_id}",
    response_model=PersistentGroupResponse,
)
def get_group(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a group when the current user is a member."""

    group = get_persistent_group(
        db=db,
        group_id=group_id,
        user=current_user,
    )

    return build_persistent_group_response(
        db=db,
        group=group,
    )


@router.post(
    "/{group_id}/members",
    response_model=PersistentGroupResponse,
)
def join_group(
    group_id: UUID,
    data: JoinPersistentGroupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Join a forming group with an owned journey."""

    group = join_persistent_group(
        db=db,
        group_id=group_id,
        user=current_user,
        journey_id=data.journey_id,
    )

    return build_persistent_group_response(
        db=db,
        group=group,
    )


@router.patch(
    "/{group_id}/status",
    response_model=PersistentGroupResponse,
)
def change_group_status(
    group_id: UUID,
    data: UpdatePersistentGroupStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change group status through the service's lifecycle rules."""

    group = update_persistent_group_status(
        db=db,
        group_id=group_id,
        user=current_user,
        new_status=data.status,
    )

    return build_persistent_group_response(
        db=db,
        group=group,
    )