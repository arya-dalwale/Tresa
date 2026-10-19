import uuid

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.journey_preference import JourneyPreference


def test_journey_preference_table_name():
    assert JourneyPreference.__tablename__ == "journey_preferences"


def test_journey_preference_columns():
    expected_columns = {
        "id",
        "journey_id",
        "smoking",
        "music",
        "conversation",
        "food",
        "travel_style",
        "created_at",
        "updated_at",
    }

    actual_columns = set(JourneyPreference.__table__.columns.keys())

    assert actual_columns == expected_columns


def test_journey_preference_primary_key():
    primary_key_columns = [
        column.name
        for column in JourneyPreference.__table__.primary_key.columns
    ]

    assert primary_key_columns == ["id"]


def test_journey_preference_id_is_uuid():
    id_column = JourneyPreference.__table__.c.id

    assert isinstance(id_column.type, UUID)
    assert id_column.primary_key is True
    assert callable(id_column.default.arg)


def test_journey_id_is_uuid_and_not_nullable():
    journey_id_column = JourneyPreference.__table__.c.journey_id

    assert isinstance(journey_id_column.type, UUID)
    assert journey_id_column.nullable is False


def test_journey_id_foreign_key_references_journeys():
    journey_id_column = JourneyPreference.__table__.c.journey_id

    foreign_key_targets = {
        foreign_key.target_fullname
        for foreign_key in journey_id_column.foreign_keys
    }

    assert "journeys.id" in foreign_key_targets


def test_journey_id_is_unique_and_indexed():
    journey_id_column = JourneyPreference.__table__.c.journey_id

    assert journey_id_column.unique is True
    assert journey_id_column.index is True


def test_preference_fields_are_optional_strings():
    preference_fields = [
        "smoking",
        "music",
        "conversation",
        "food",
        "travel_style",
    ]

    for field_name in preference_fields:
        column = JourneyPreference.__table__.c[field_name]

        assert isinstance(column.type, String)
        assert column.type.length == 20
        assert column.nullable is True


def test_created_at_timestamp_configuration():
    column = JourneyPreference.__table__.c.created_at

    assert isinstance(column.type, DateTime)
    assert column.type.timezone is True
    assert column.nullable is False
    assert callable(column.default.arg)


def test_updated_at_timestamp_configuration():
    column = JourneyPreference.__table__.c.updated_at

    assert isinstance(column.type, DateTime)
    assert column.type.timezone is True
    assert column.nullable is False
    assert callable(column.default.arg)
    assert column.onupdate is not None
    assert callable(column.onupdate.arg)


def test_journey_preference_python_defaults_are_configured():
    table = JourneyPreference.__table__

    assert callable(table.c.id.default.arg)
    assert callable(table.c.created_at.default.arg)
    assert callable(table.c.updated_at.default.arg)