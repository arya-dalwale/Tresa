from datetime import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.journey import Journey


def get_journey_by_id(
    db: Session,
    journey_id: uuid.UUID,
) -> Journey | None:
    """Return a journey by its ID."""

    statement = select(Journey).where(
        Journey.id == journey_id
    )

    return db.scalar(statement)


def get_journeys_by_user(
    db: Session,
    user_id: uuid.UUID,
) -> list[Journey]:
    """Return all journeys created by a user."""

    statement = (
        select(Journey)
        .where(Journey.user_id == user_id)
        .order_by(Journey.created_at.desc())
    )

    return list(db.scalars(statement).all())


def get_active_journeys(
    db: Session,
) -> list[Journey]:
    """Return journeys that are currently planned or active."""

    statement = (
        select(Journey)
        .where(
            Journey.status.in_(["planned", "active"])
        )
        .order_by(Journey.departure_time.asc())
    )

    return list(db.scalars(statement).all())


def get_journeys_by_departure_time(
    db: Session,
    start_time: datetime,
    end_time: datetime,
) -> list[Journey]:
    """Return journeys departing within a given time range."""

    statement = (
        select(Journey)
        .where(
            Journey.departure_time >= start_time,
            Journey.departure_time <= end_time,
        )
        .order_by(Journey.departure_time.asc())
    )

    return list(db.scalars(statement).all())


def create_journey(
    db: Session,
    journey: Journey,
) -> Journey:
    """Persist a new journey and return it."""

    db.add(journey)
    db.commit()
    db.refresh(journey)

    return journey


def update_journey(
    db: Session,
    journey: Journey,
) -> Journey:
    """Persist changes to an existing journey."""

    db.commit()
    db.refresh(journey)

    return journey


def delete_journey(
    db: Session,
    journey: Journey,
) -> None:
    """Delete a journey."""

    db.delete(journey)
    db.commit()