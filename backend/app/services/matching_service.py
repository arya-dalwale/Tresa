from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.journey import Journey


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