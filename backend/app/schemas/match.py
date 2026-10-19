from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.group import GroupMember


class MatchScoreBreakdown(BaseModel):
    """Normalized matching component scores."""

    route: None = None
    destination: float = Field(ge=0.0, le=1.0)
    time: float = Field(ge=0.0, le=1.0)
    origin_proximity: float = Field(ge=0.0, le=1.0)
    preferences: float = Field(ge=0.0, le=1.0)
    luggage: float = Field(ge=0.0, le=1.0)


class IndividualMatchResponse(BaseModel):
    """Privacy-safe representation of an individual journey match."""

    journey_id: UUID
    user_id: UUID
    full_name: str | None = None
    profile_photo_url: str | None = None
    departure_time: datetime
    passengers: int = Field(ge=1, le=5)
    luggage: str
    origin_distance_km: float = Field(ge=0.0)
    compatibility_score: float = Field(ge=0.0, le=1.0)
    score_breakdown: MatchScoreBreakdown


class RecommendedGroupResponse(BaseModel):
    """Public response representation of a recommended group."""

    members: list[GroupMember] = Field(min_length=2, max_length=5)
    group_size: int = Field(ge=2, le=5)
    total_passengers: int = Field(ge=2, le=5)
    group_compatibility_score: float = Field(ge=0.0, le=1.0)
    member_journey_ids: list[UUID] = Field(min_length=2, max_length=5)

    @model_validator(mode="after")
    def validate_group_response(self) -> "RecommendedGroupResponse":
        if self.group_size != len(self.members):
            raise ValueError(
                "group_size must equal the number of members"
            )

        actual_ids = [member.journey_id for member in self.members]

        if self.member_journey_ids != actual_ids:
            raise ValueError(
                "member_journey_ids must match the member journey IDs"
            )

        actual_passengers = sum(
            member.passengers for member in self.members
        )

        if actual_passengers != self.total_passengers:
            raise ValueError(
                "total_passengers must equal the sum of member passengers"
            )

        return self


class MatchesResponse(BaseModel):
    """Individual match results and recommended groups."""

    matches: list[IndividualMatchResponse]
    groups: list[RecommendedGroupResponse]