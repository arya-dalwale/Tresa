from datetime import datetime, timedelta, timezone
import uuid
from unittest.mock import Mock

from app.models.journey import Journey
from app.repositories.journey_repository import (
    create_journey,
    delete_journey,
    get_active_journeys,
    get_journey_by_id,
    get_journeys_by_departure_time,
    get_journeys_by_user,
    update_journey,
)


def create_test_journey(
    user_id: uuid.UUID | None = None,
) -> Journey:
    return Journey(
        id=uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=datetime.now(timezone.utc),
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )


def test_get_journey_by_id():
    db = Mock()
    journey = create_test_journey()

    db.scalar.return_value = journey

    result = get_journey_by_id(db, journey.id)

    assert result == journey
    db.scalar.assert_called_once()


def test_get_journeys_by_user():
    db = Mock()
    user_id = uuid.uuid4()

    journey_one = create_test_journey(user_id)
    journey_two = create_test_journey(user_id)

    db.scalars.return_value.all.return_value = [
        journey_one,
        journey_two,
    ]

    result = get_journeys_by_user(db, user_id)

    assert result == [journey_one, journey_two]
    db.scalars.assert_called_once()


def test_get_active_journeys():
    db = Mock()

    planned_journey = create_test_journey()
    active_journey = create_test_journey()
    active_journey.status = "active"

    db.scalars.return_value.all.return_value = [
        planned_journey,
        active_journey,
    ]

    result = get_active_journeys(db)

    assert result == [
        planned_journey,
        active_journey,
    ]
    db.scalars.assert_called_once()


def test_get_journeys_by_departure_time():
    db = Mock()

    start_time = datetime(
        2026,
        10,
        17,
        10,
        0,
        tzinfo=timezone.utc,
    )

    end_time = start_time + timedelta(hours=2)

    journey = create_test_journey()
    journey.departure_time = start_time + timedelta(hours=1)

    db.scalars.return_value.all.return_value = [journey]

    result = get_journeys_by_departure_time(
        db,
        start_time,
        end_time,
    )

    assert result == [journey]
    db.scalars.assert_called_once()


def test_create_journey():
    db = Mock()
    journey = create_test_journey()

    result = create_journey(db, journey)

    assert result == journey
    db.add.assert_called_once_with(journey)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(journey)


def test_update_journey():
    db = Mock()
    journey = create_test_journey()

    result = update_journey(db, journey)

    assert result == journey
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(journey)


def test_delete_journey():
    db = Mock()
    journey = create_test_journey()

    result = delete_journey(db, journey)

    assert result is None
    db.delete.assert_called_once_with(journey)
    db.commit.assert_called_once()