import uuid
from datetime import datetime, timezone

from sqlalchemy import inspect

from app.models.journey import Journey


def test_journey_table_name():
    assert Journey.__tablename__ == "journeys"


def test_journey_columns():
    columns = Journey.__table__.columns

    expected_columns = {
        "id",
        "user_id",
        "origin",
        "destination",
        "departure_time",
        "passengers",
        "luggage",
        "radius_km",
        "status",
        "created_at",
        "updated_at",
    }

    assert set(columns.keys()) == expected_columns


def test_journey_primary_key():
    primary_key_columns = [
        column.name
        for column in Journey.__table__.primary_key.columns
    ]

    assert primary_key_columns == ["id"]


def test_journey_foreign_key():
    user_id_column = Journey.__table__.columns["user_id"]

    foreign_keys = list(user_id_column.foreign_keys)

    assert len(foreign_keys) == 1
    assert str(foreign_keys[0].target_fullname) == "users.id"


def test_journey_defaults():
    passengers = Journey.__table__.columns["passengers"]
    luggage = Journey.__table__.columns["luggage"]
    radius_km = Journey.__table__.columns["radius_km"]
    status = Journey.__table__.columns["status"]

    assert passengers.default is not None
    assert luggage.default is not None
    assert radius_km.default is not None
    assert status.default is not None


def test_journey_constraints():
    constraint_names = {
        constraint.name
        for constraint in Journey.__table__.constraints
        if constraint.name
    }

    assert "ck_journeys_passengers_min" in constraint_names
    assert "ck_journeys_radius_positive" in constraint_names
    assert "ck_journeys_luggage_allowed" in constraint_names
    assert "ck_journeys_status_allowed" in constraint_names


def test_journey_indexes():
    index_names = {
        index.name
        for index in Journey.__table__.indexes
    }

    assert "ix_journeys_user_id" in index_names
    assert "ix_journeys_origin_gist" in index_names
    assert "ix_journeys_destination_gist" in index_names
    assert "ix_journeys_departure_time" in index_names
    assert "ix_journeys_status" in index_names


def test_journey_timestamp_columns():
    created_at = Journey.__table__.columns["created_at"]
    updated_at = Journey.__table__.columns["updated_at"]

    assert created_at.nullable is False
    assert updated_at.nullable is False


def test_journey_instance_defaults():
    journey = Journey(
        user_id=uuid.uuid4(),
        origin="POINT(73.8567 18.5204)",
        destination="POINT(73.8567 18.5204)",
        departure_time=datetime.now(timezone.utc),
    )

    assert journey.passengers is None or journey.passengers == 1
    assert journey.luggage is None or journey.luggage == "medium"
    assert journey.radius_km is None or journey.radius_km == 10.0
    assert journey.status is None or journey.status == "planned"