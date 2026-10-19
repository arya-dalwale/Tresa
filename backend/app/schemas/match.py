from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.group import GroupRecommendation


class MatchScoreBreakdown(BaseModel):
    route: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    destination: float = Field(
        ge=0.0,
        le=1.0,
    )
    time: float = Field(
        ge=0.0,
        le=1.0,
    )
    origin_proximity: float = Field(
        ge=0.0,
        le=1.0,
    )
    preferences: float = Field(
        ge=0.0,
        le=1.0,
    )
    luggage: float = Field(
        ge=0.0,
        le=1.0,
    )


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    journey_id: UUID
    user_id: UUID

    full_name: str | None = None
    profile_photo_url: str | None = None

    departure_time: datetime
    passengers: int
    luggage: str

    origin_distance_km: float = Field(
        ge=0.0,
    )

    compatibility_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    score_breakdown: MatchScoreBreakdown


class MatchListResponse(BaseModel):
    journey_id: UUID

    matches: list[MatchResponse]
    groups: list[GroupRecommendation]

    total: int

    limit: int = Field(
        ge=1,
        le=100,
    )

    offset: int = Field(
        ge=0,
    )