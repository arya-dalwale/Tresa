from datetime import datetime
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
    Find candidate journeys that:
    - are not the target journey
    - have planned or active status
    - are within the target journey's search radius
    """

    radius_meters = journey.radius_km * 1000

    statement = (
        select(Journey)
        .where(
            Journey.id != journey.id,
            Journey.status.in_(["planned", "active"]),
            Journey.origin.ST_DWithin(
                journey.origin,
                radius_meters,
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
    Calculate the distance between the destinations
    of the target journey and candidate journey in meters.
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

    Same departure time = 1.0
    Difference >= max_difference_minutes = 0.0
    Values between them are linearly scaled.
    """

    if not isinstance(journey.departure_time, datetime):
        raise ValueError("Journey departure_time must be a datetime")

    if not isinstance(candidate.departure_time, datetime):
        raise ValueError("Candidate departure_time must be a datetime")

    difference_minutes = abs(
        (
            journey.departure_time - candidate.departure_time
        ).total_seconds()
    ) / 60

    if difference_minutes == 0:
        return 1.0

    if difference_minutes >= max_difference_minutes:
        return 0.0

    return 1.0 - (
        difference_minutes / max_difference_minutes
    )


def calculate_origin_proximity(
    db: Session,
    journey: Journey,
    candidate: Journey,
) -> float:
    """
    Calculate origin proximity score.

    Same origin = 1.0
    At or beyond search radius = 0.0
    Closer origins receive a higher score.
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
        raise ValueError("Journey radius must be greater than zero")

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

    Same luggage size = 1.0
    One level difference = 0.5
    Maximum difference = 0.0
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

    difference = abs(journey_level - candidate_level)

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