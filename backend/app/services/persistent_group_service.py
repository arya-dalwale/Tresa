from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.matching import (
    calculate_directional_match,
    is_eligible_candidate,
)
from app.models.group_member import GroupMember
from app.models.journey import Journey
from app.models.travel_group import TravelGroup
from app.models.user import User
from app.schemas.persistent_group import (
    PersistentGroupMemberResponse,
    PersistentGroupResponse,
)
from app.services.journey_service import get_journey


MAX_GROUP_SIZE = 5
MAX_GROUP_PASSENGERS = 5
MIN_GROUP_COMPATIBILITY = 0.60
OPEN_GROUP_STATUSES = ("forming", "active")


def _get_owned_journey(
    db: Session,
    journey_id: UUID,
    user: User,
) -> Journey:
    """Retrieve a journey and verify that the user owns it."""

    journey = get_journey(db=db, journey_id=journey_id)

    if journey is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journey not found",
        )

    if journey.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this journey",
        )

    if journey.status not in ("planned", "active"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only planned or active journeys can join a group",
        )

    return journey


def _ensure_journey_not_in_open_group(
    db: Session,
    journey_id: UUID,
) -> None:
    """Prevent a journey from joining multiple open groups."""

    existing_member = db.scalar(
        select(GroupMember.id)
        .join(
            TravelGroup,
            TravelGroup.id == GroupMember.group_id,
        )
        .where(
            GroupMember.journey_id == journey_id,
            TravelGroup.status.in_(OPEN_GROUP_STATUSES),
        )
        .limit(1)
    )

    if existing_member is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This journey already belongs to an open group",
        )


def _get_group_members(
    db: Session,
    group_id: UUID,
) -> list[GroupMember]:
    """Return group members in stable join order."""

    statement = (
        select(GroupMember)
        .where(GroupMember.group_id == group_id)
        .order_by(
            GroupMember.joined_at.asc(),
            GroupMember.id.asc(),
        )
    )

    return list(db.scalars(statement).all())


def build_persistent_group_response(
    db: Session,
    group: TravelGroup,
) -> PersistentGroupResponse:
    """Build a response from the persisted group and member records."""

    members = _get_group_members(db, group.id)

    return PersistentGroupResponse(
        id=group.id,
        created_by=group.created_by,
        status=group.status,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=[
            PersistentGroupMemberResponse(
                id=member.id,
                user_id=member.user_id,
                journey_id=member.journey_id,
                passengers=member.passengers,
                joined_at=member.joined_at,
            )
            for member in members
        ],
        group_size=len(members),
        total_passengers=sum(
            member.passengers for member in members
        ),
    )


def create_persistent_group(
    db: Session,
    user: User,
    journey_id: UUID,
) -> TravelGroup:
    """Create a forming group and automatically add its creator."""

    journey = _get_owned_journey(
        db=db,
        journey_id=journey_id,
        user=user,
    )

    _ensure_journey_not_in_open_group(
        db=db,
        journey_id=journey.id,
    )

    if journey.passengers > MAX_GROUP_PASSENGERS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The journey exceeds the group passenger limit",
        )

    group = TravelGroup(
        created_by=user.id,
        status="forming",
    )

    try:
        db.add(group)
        db.flush()

        db.add(
            GroupMember(
                group_id=group.id,
                user_id=user.id,
                journey_id=journey.id,
                passengers=journey.passengers,
            )
        )

        db.commit()
        db.refresh(group)

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create the group due to a data conflict",
        ) from exc

    return group


def join_persistent_group(
    db: Session,
    group_id: UUID,
    user: User,
    journey_id: UUID,
) -> TravelGroup:
    """Add an owned journey after checking group limits and compatibility."""

    group = db.get(TravelGroup, group_id)

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel group not found",
        )

    if group.status != "forming":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only groups in forming status can accept members",
        )

    journey = _get_owned_journey(
        db=db,
        journey_id=journey_id,
        user=user,
    )

    current_members = _get_group_members(db, group.id)

    if any(member.user_id == user.id for member in current_members):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already a member of this group",
        )

    if any(member.journey_id == journey.id for member in current_members):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This journey is already a member of this group",
        )

    if len(current_members) >= MAX_GROUP_SIZE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The group has reached its member limit",
        )

    current_passengers = sum(
        member.passengers for member in current_members
    )

    if current_passengers + journey.passengers > MAX_GROUP_PASSENGERS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The group would exceed the passenger limit",
        )

    _ensure_journey_not_in_open_group(
        db=db,
        journey_id=journey.id,
    )

    for member in current_members:
        existing_journey = db.get(Journey, member.journey_id)

        if existing_journey is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An existing group journey could not be found",
            )

        # Reuse the current matching eligibility rules in both directions.
        existing_score, existing_breakdown = calculate_directional_match(
            db=db,
            journey=existing_journey,
            candidate=journey,
        )

        new_score, new_breakdown = calculate_directional_match(
            db=db,
            journey=journey,
            candidate=existing_journey,
        )

        if not is_eligible_candidate(
            score=existing_score,
            breakdown=existing_breakdown,
        ) or not is_eligible_candidate(
            score=new_score,
            breakdown=new_breakdown,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The journey does not meet matching eligibility rules",
            )

        pairwise_score = (existing_score + new_score) / 2.0

        if pairwise_score < MIN_GROUP_COMPATIBILITY:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The journey is not compatible with every "
                    "existing group member"
                ),
            )

    try:
        db.add(
            GroupMember(
                group_id=group.id,
                user_id=user.id,
                journey_id=journey.id,
                passengers=journey.passengers,
            )
        )

        db.commit()
        db.refresh(group)

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to join the group due to a membership conflict",
        ) from exc

    return group


def get_persistent_group(
    db: Session,
    group_id: UUID,
    user: User,
) -> TravelGroup:
    """Retrieve a group only when the user is one of its members."""

    group = db.get(TravelGroup, group_id)

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel group not found",
        )

    membership = db.scalar(
        select(GroupMember.id).where(
            GroupMember.group_id == group.id,
            GroupMember.user_id == user.id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    return group


def list_user_persistent_groups(
    db: Session,
    user: User,
) -> list[TravelGroup]:
    """List groups that contain the authenticated user's membership."""

    statement = (
        select(TravelGroup)
        .join(
            GroupMember,
            GroupMember.group_id == TravelGroup.id,
        )
        .where(GroupMember.user_id == user.id)
        .order_by(TravelGroup.created_at.desc())
    )

    return list(db.scalars(statement).all())


def update_persistent_group_status(
    db: Session,
    group_id: UUID,
    user: User,
    new_status: str,
) -> TravelGroup:
    """Allow the creator to perform supported lifecycle transitions."""

    group = db.get(TravelGroup, group_id)

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel group not found",
        )

    if group.created_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the group creator can change its status",
        )

    allowed_transitions = {
        "forming": {"active", "cancelled"},
        "active": {"completed", "cancelled"},
        "completed": set(),
        "cancelled": set(),
    }

    if new_status == group.status:
        return group

    if new_status not in allowed_transitions.get(group.status, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot change group status from "
                f"{group.status} to {new_status}"
            ),
        )

    group.status = new_status

    try:
        db.commit()
        db.refresh(group)

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to update the group status",
        ) from exc

    return group