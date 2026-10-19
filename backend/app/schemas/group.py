from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class GroupMember(BaseModel):
    """Public, minimal representation of one journey in a recommendation."""

    journey_id: UUID
    user_id: UUID
    passengers: int = Field(ge=1, le=5)


class GroupRecommendation(BaseModel):
    """A compatible group containing the requesting journey and candidates."""

    members: list[GroupMember] = Field(min_length=2, max_length=5)
    group_score: float = Field(ge=0.0, le=1.0)
    total_passengers: int = Field(ge=2, le=5)

    @model_validator(mode="after")
    def validate_group_contract(self) -> "GroupRecommendation":
        journey_ids = [member.journey_id for member in self.members]
        user_ids = [member.user_id for member in self.members]

        if len(journey_ids) != len(set(journey_ids)):
            raise ValueError("A group cannot contain duplicate journeys")
        if len(user_ids) != len(set(user_ids)):
            raise ValueError("A group cannot contain duplicate users")

        actual_passengers = sum(member.passengers for member in self.members)
        if actual_passengers != self.total_passengers:
            raise ValueError(
                "total_passengers must equal the sum of member passengers"
            )
        return self


class GroupRecommendationsResponse(BaseModel):
    """Container schema for a list of group recommendations."""

    recommendations: list[GroupRecommendation]
