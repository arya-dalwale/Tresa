from sqlalchemy import text

from app.database.session import SessionLocal, engine


def test_database_engine_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_database_session_connection():
    session = SessionLocal()

    try:
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    finally:
        session.close()


def test_database_session_is_closed():
    session = SessionLocal()

    session.close()

    assert session.is_active is True
    assert session.in_transaction() is False