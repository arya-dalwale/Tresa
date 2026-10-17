from app.models.journey_preference import JourneyPreference


PREFERENCE_FIELDS = (
    "smoking",
    "music",
    "conversation",
    "food",
    "travel_style",
)


def calculate_preference_compatibility(
    journey_preferences: JourneyPreference | None,
    candidate_preferences: JourneyPreference | None,
) -> float:
    """
    Calculate preference compatibility between two journeys.

    Compatibility rules:
    - Same specific value: 1.0
    - Either side is no_preference: 1.0
    - Conflicting specific values: 0.0

    The final score is the average of the five preference fields.

    Missing preference records are treated as having no preference
    for all fields.
    """

    scores: list[float] = []

    for field in PREFERENCE_FIELDS:
        journey_value = (
            getattr(journey_preferences, field)
            if journey_preferences is not None
            else None
        )

        candidate_value = (
            getattr(candidate_preferences, field)
            if candidate_preferences is not None
            else None
        )

        if (
            journey_value is None
            or candidate_value is None
            or journey_value == "no_preference"
            or candidate_value == "no_preference"
        ):
            scores.append(1.0)
        elif journey_value == candidate_value:
            scores.append(1.0)
        else:
            scores.append(0.0)

    return sum(scores) / len(scores)