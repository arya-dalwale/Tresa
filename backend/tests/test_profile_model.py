import uuid

from app.models.profile import Profile


def test_profile_model_structure():
    assert Profile.__tablename__ == "profiles"

    columns = Profile.__table__.columns

    assert "id" in columns
    assert "user_id" in columns
    assert "full_name" in columns
    assert "phone_number" in columns
    assert "bio" in columns
    assert "profile_photo_url" in columns
    assert "created_at" in columns
    assert "updated_at" in columns


def test_profile_model_primary_key():
    column = Profile.__table__.columns["id"]

    assert column.primary_key is True
    assert column.nullable is False
    assert column.type.python_type is uuid.UUID


def test_profile_user_id_constraints():
    column = Profile.__table__.columns["user_id"]

    assert column.nullable is False
    assert column.unique is True
    assert column.type.python_type is uuid.UUID

    foreign_keys = list(column.foreign_keys)

    assert len(foreign_keys) == 1
    assert str(foreign_keys[0].target_fullname) == "users.id"


def test_profile_full_name_constraints():
    column = Profile.__table__.columns["full_name"]

    assert column.nullable is False
    assert column.type.length == 100


def test_profile_optional_fields():
    phone_number = Profile.__table__.columns["phone_number"]
    bio = Profile.__table__.columns["bio"]
    profile_photo_url = Profile.__table__.columns["profile_photo_url"]

    assert phone_number.nullable is True
    assert phone_number.type.length == 20

    assert bio.nullable is True
    assert bio.type.length == 500

    assert profile_photo_url.nullable is True
    assert profile_photo_url.type.length == 500


def test_profile_timestamps():
    created_at = Profile.__table__.columns["created_at"]
    updated_at = Profile.__table__.columns["updated_at"]

    assert created_at.nullable is False
    assert updated_at.nullable is False

    assert created_at.type.timezone is True
    assert updated_at.type.timezone is True