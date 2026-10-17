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