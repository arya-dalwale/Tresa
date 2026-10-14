import uuid

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}@tresa.com"


def test_register_user():
    email = unique_email("auth-test")

    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == email
    assert data["is_active"] is True
    assert data["role"] == "user"
    assert "password" not in data
    assert "password_hash" not in data


def test_login_user():
    email = unique_email("auth-login")

    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert login_response.status_code == 200

    data = login_response.json()

    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["email"] == email
    assert data["user"]["is_active"] is True
    assert data["user"]["role"] == "user"


def test_login_with_wrong_password():
    email = unique_email("auth-wrong-password")

    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "WrongPassword123",
        },
    )

    assert login_response.status_code == 401


def test_register_duplicate_email():
    email = unique_email("auth-duplicate")

    first_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123",
        },
    )

    assert second_response.status_code == 409