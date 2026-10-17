from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.journey import Journey


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
    Find active/planned journeys within the target journey's
    geographic search radius.

    The geographic filtering is performed by PostGIS.
    """

    distance_meters = journey.radius_km * 1000

    statement = (
        select(Journey)
        .where(
            Journey.id != journey.id,
            Journey.status.in_(["planned", "active"]),
        )
        .where(
            Journey.origin.ST_DWithin(
                journey.origin,
                distance_meters,
            )
        )
    )

    return list(db.scalars(statement).all())


def calculate_destination_distance(
    db: Session,
    journey: Journey,
    candidate: Journey,
) -> float:
    """
    Calculate the distance in meters between two journey destinations.

    The distance calculation is performed by PostGIS using
    geography coordinates.
    """

    statement = select(
        Journey.destination.ST_Distance(
            candidate.destination,
        )
    ).where(Journey.id == journey.id)

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
    Calculate departure-time compatibility between two journeys.

    Returns a score between 0.0 and 1.0.

    1.0 = same departure time
    0.0 = difference is equal to or greater than the
          configured maximum difference.
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
    Calculate origin proximity between two journeys.

    Returns a score between 0.0 and 1.0.

    1.0 = same origin
    0.0 = candidate is at or beyond the journey's search radius.

    The geographic distance is calculated by PostGIS.
    """

    statement = select(
        Journey.origin.ST_Distance(
            candidate.origin,
        )
    ).where(Journey.id == journey.id)

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