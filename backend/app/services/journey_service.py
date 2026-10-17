from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.journey import Journey
from app.schemas.journey import JourneyCreate, JourneyUpdate


def location_to_wkt(latitude: float, longitude: float) -> WKTElement:
    """
    Convert latitude/longitude into a PostGIS POINT.

    PostGIS POINT format:
    POINT(longitude latitude)
    """
    return WKTElement(
        f"POINT({longitude} {latitude})",
        srid=4326,
    )


def create_journey(
    db: Session,
    user_id: UUID,
    data: JourneyCreate,
) -> Journey:
    journey = Journey(
        user_id=user_id,
        origin=location_to_wkt(
            data.origin.latitude,
            data.origin.longitude,
        ),
        destination=location_to_wkt(
            data.destination.latitude,
            data.destination.longitude,
        ),
        departure_time=data.departure_time,
        passengers=data.passengers,
        luggage=data.luggage.value,
        radius_km=data.radius_km,
        status="planned",
    )

    db.add(journey)
    db.commit()
    db.refresh(journey)

    return journey


def get_user_journeys(
    db: Session,
    user_id: UUID,
) -> list[Journey]:
    statement = (
        select(Journey)
        .where(Journey.user_id == user_id)
        .order_by(Journey.departure_time.asc())
    )

    return list(db.scalars(statement).all())


def get_journey(
    db: Session,
    journey_id: UUID,
) -> Journey | None:
    return db.get(Journey, journey_id)


def update_journey(
    db: Session,
    journey: Journey,
    data: JourneyUpdate,
) -> Journey:
    update_data = data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    if "origin" in update_data:
        origin = update_data.pop("origin")

        journey.origin = location_to_wkt(
            origin.latitude,
            origin.longitude,
        )

    if "destination" in update_data:
        destination = update_data.pop("destination")

        journey.destination = location_to_wkt(
            destination.latitude,
            destination.longitude,
        )

    for field, value in update_data.items():
        if hasattr(value, "value"):
            value = value.value

        setattr(journey, field, value)

    db.commit()
    db.refresh(journey)

    return journey


def delete_journey(
    db: Session,
    journey: Journey,
) -> None:
    db.delete(journey)
    db.commit()