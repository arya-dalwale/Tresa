from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.journey import Journey
from app.models.journey_preference import JourneyPreference
from app.services.preference_service import calculate_preference_compatibility


MATCHING_WEIGHTS = {
    "route": 0.30,
    "destination": 0.25,
    "time": 0.20,
    "origin_proximity": 0.10,
    "preferences": 0.10,
    "luggage": 0.05,
}


def find_candidate_journeys(
    db: Session,
    journey: Journey,
) -> list[Journey]:
    """
    Find active/planned journeys whose origins are within
    the target journey's search radius.

    The target journey itself is excluded.
    """

    statement = (
        select(Journey)
        .where(
            Journey.id != journey.id,
            Journey.status.in_(["planned", "active"]),
            Journey.origin.ST_DWithin(
                journey.origin,
                journey.radius_km * 1000,
            ),
        )
    )

    return list(db.scalars(statement).all())


def calculate_destination_distance(
    db: Session,
    journey: Journey,
    candidate: Journey,
) -> float:
    """
    Calculate the distance in meters between the two destinations.
    """

    statement = select(
        Journey.destination.ST_Distance(candidate.destination)
    ).where(
        Journey.id == journey.id
    )

    distance_meters = db.scalar(statement)

    if distance_meters is None:
        raise ValueError("Unable to calculate destination distance")

    return float(distance_meters)


def calculate_time_compatibility(
    journey: Journey,
    candidate: Journey,
    max_difference_minutes: int = 60,
) -> float:
    """
    Calculate departure-time compatibility.

    Same departure time = 1.0.

    Difference equal to or greater than max_difference_minutes = 0.0.

    Differences in between are linearly scaled between 1.0 and 0.0.
    """

    if not isinstance(journey.departure_time, datetime):
        raise ValueError("Journey departure_time must be a datetime")

    if not isinstance(candidate.departure_time, datetime):
        raise ValueError("Candidate departure_time must be a datetime")

    difference_seconds = abs(
        (
            journey.departure_time
            - candidate.departure_time
        ).total_seconds()
    )

    difference_minutes = difference_seconds / 60

    if difference_minutes >= max_difference_minutes:
        return 0.0

    score = 1.0 - (
        difference_minutes / max_difference_minutes
    )

    return max(0.0, min(1.0, score))


def calculate_origin_proximity(
    db: Session,
    journey: Journey,
    candidate: Journey,
) -> float:
    """
    Calculate origin proximity.

    Same origin = 1.0.

    Origin at or beyond the search radius = 0.0.

    The score decreases linearly as distance increases.
    """

    statement = select(
        Journey.origin.ST_Distance(candidate.origin)
    ).where(
        Journey.id == journey.id
    )

    distance_meters = db.scalar(statement)

    if distance_meters is None:
        raise ValueError("Unable to calculate origin distance")

    max_distance_meters = journey.radius_km * 1000

    if max_distance_meters <= 0:
        raise ValueError("Journey radius_km must be greater than zero")

    if distance_meters >= max_distance_meters:
        return 0.0

    score = 1.0 - (
        distance_meters / max_distance_meters
    )

    return max(0.0, min(1.0, score))


def calculate_luggage_compatibility(
    journey: Journey,
    candidate: Journey,
) -> float:
    """
    Calculate luggage compatibility.

    Same luggage level = 1.0.

    One level difference = 0.5.

    Maximum level difference = 0.0.
    """

    luggage_levels = {
        "small": 0,
        "medium": 1,
        "large": 2,
    }

    journey_level = luggage_levels.get(journey.luggage)
    candidate_level = luggage_levels.get(candidate.luggage)

    if journey_level is None:
        raise ValueError(
            f"Invalid journey luggage value: {journey.luggage}"
        )

    if candidate_level is None:
        raise ValueError(
            f"Invalid candidate luggage value: {candidate.luggage}"
        )

    difference = abs(
        journey_level - candidate_level
    )

    if difference == 0:
        return 1.0

    if difference == 1:
        return 0.5

    return 0.0


def calculate_preference_score(
    journey_preferences: JourneyPreference | None,
    candidate_preferences: JourneyPreference | None,
) -> float:
    """
    Calculate preference compatibility between two journeys.

    Preference conflicts contribute 0.0 to the preference score
    but do not automatically reject the candidate.
    """

    return calculate_preference_compatibility(
        journey_preferences,
        candidate_preferences,
    )


def normalize_score(score: float) -> float:
    """
    Validate that a matching component score is normalized
    between 0.0 and 1.0.
    """

    if not 0.0 <= score <= 1.0:
        raise ValueError(
            "Matching component score must be between 0.0 and 1.0: "
            f"{score}"
        )

    return float(score)


def calculate_weighted_score(
    component_scores: dict[str, float | None],
) -> float:
    """
    Calculate the final weighted compatibility score.

    Unavailable components are represented by None and are excluded
    from both the numerator and denominator.

    The remaining component weights are renormalized proportionally.

    Route overlap is currently unavailable because the Journey
    contract does not contain route/polyline/waypoint data.
    """

    weighted_total = 0.0
    available_weight = 0.0

    for component, weight in MATCHING_WEIGHTS.items():
        score = component_scores.get(component)

        if score is None:
            continue

        normalized_score = normalize_score(score)

        weighted_total += normalized_score * weight
        available_weight += weight

    if available_weight == 0.0:
        raise ValueError(
            "At least one matching component must be available"
        )

    final_score = weighted_total / available_weight

    return max(
        0.0,
        min(1.0, final_score),
    )


def calculate_match_score(
    component_scores: dict[str, float | None],
) -> float:
    """
    Calculate the final V1 matching score.

    Route overlap is excluded when unavailable and the remaining
    weights are renormalized.
    """

    return calculate_weighted_score(
        component_scores
    )


def rank_candidates(
    candidates: list[tuple[UUID, float]],
) -> list[tuple[UUID, float]]:
    """
    Rank candidates from highest compatibility score to lowest.

    Equal scores remain tied and preserve their original order.
    """

    return sorted(
        candidates,
        key=lambda candidate: -candidate[1],
    )