import uuid

from app.models.user import User


def test_user_model_structure():
    assert User.__tablename__ == "users"

    columns = User.__table__.columns

    assert "id" in columns
    assert "email" in columns
    assert "password_hash" in columns
    assert "is_active" in columns
    assert "role" in columns
    assert "created_at" in columns
    assert "updated_at" in columns


def test_user_model_primary_key():
    column = User.__table__.columns["id"]

    assert column.primary_key is True
    assert column.nullable is False


def test_user_model_email_constraints():
    column = User.__table__.columns["email"]

    assert column.nullable is False
    assert column.unique is True
    assert column.type.length == 255


def test_user_model_password_hash():
    column = User.__table__.columns["password_hash"]

    assert column.nullable is False
    assert column.type.length == 255


def test_user_model_defaults():
    is_active = User.__table__.columns["is_active"]
    role = User.__table__.columns["role"]

    assert is_active.nullable is False
    assert role.nullable is False
    assert role.type.length == 20


def test_user_id_type():
    column = User.__table__.columns["id"]

    assert column.type.python_type is uuid.UUID