from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LuggageType(str, Enum):
    small = "small"
    medium = "medium"
    large = "large"


class JourneyStatus(str, Enum):
    planned = "planned"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class LocationInput(BaseModel):
    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
    )


class JourneyCreate(BaseModel):
    origin: LocationInput
    destination: LocationInput
    departure_time: datetime
    passengers: int = Field(
        default=1,
        ge=1,
    )
    luggage: LuggageType = LuggageType.medium
    radius_km: float = Field(
        default=10.0,
        ge=2.0,
        le=25.0,
    )

    @field_validator("departure_time")
    @classmethod
    def validate_departure_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "departure_time must include timezone information"
            )

        return value


class JourneyUpdate(BaseModel):
    origin: LocationInput | None = None
    destination: LocationInput | None = None
    departure_time: datetime | None = None
    passengers: int | None = Field(
        default=None,
        ge=1,
    )
    luggage: LuggageType | None = None
    radius_km: float | None = Field(
        default=None,
        ge=2.0,
        le=25.0,
    )
    status: JourneyStatus | None = None

    @field_validator("departure_time")
    @classmethod
    def validate_departure_time(cls, value: datetime | None):
        if value is None:
            return value

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "departure_time must include timezone information"
            )

        return value


class JourneyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID

    origin: LocationInput
    destination: LocationInput

    departure_time: datetime
    passengers: int
    luggage: LuggageType
    radius_km: float
    status: JourneyStatus

    created_at: datetime
    updated_at: datetime