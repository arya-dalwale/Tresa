from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


GroupStatus = Literal[
    "forming",
    "active",
    "completed",
    "cancelled",
]

GroupStatusUpdate = Literal[
    "active",
    "completed",
    "cancelled",
]


class CreatePersistentGroupRequest(BaseModel):
    """Create a persistent group using the authenticated user's journey."""

    journey_id: UUID


class JoinPersistentGroupRequest(BaseModel):
    """Join a group using a journey owned by the authenticated user."""

    journey_id: UUID


class UpdatePersistentGroupStatusRequest(BaseModel):
    """Request a supported group lifecycle transition."""

    status: GroupStatusUpdate


class PersistentGroupMemberResponse(BaseModel):
    """Public representation of a persisted group member."""

    id: UUID
    user_id: UUID
    journey_id: UUID
    passengers: int = Field(ge=1, le=5)
    joined_at: datetime


class PersistentGroupResponse(BaseModel):
    """Persistent group details and current membership."""

    id: UUID
    created_by: UUID
    status: GroupStatus
    created_at: datetime
    updated_at: datetime
    members: list[PersistentGroupMemberResponse] = Field(
        min_length=1,
        max_length=5,
    )
    group_size: int = Field(ge=1, le=5)
    total_passengers: int = Field(ge=1, le=5)


class PersistentGroupListResponse(BaseModel):
    """Groups associated with the authenticated user."""

    groups: list[PersistentGroupResponse]