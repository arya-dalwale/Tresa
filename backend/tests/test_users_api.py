import uuid

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}@tresa.com"


def create_test_user():
    email = unique_email("users-api")
    password = "TestPassword123"

    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return email, {
        "Authorization": f"Bearer {token}",
    }


def test_get_my_profile_requires_authentication():
    response = client.get("/users/me")

    assert response.status_code == 401


def test_get_my_profile_without_profile():
    email, headers = create_test_user()

    response = client.get(
        "/users/me",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == email
    assert data["is_active"] is True
    assert data["role"] == "user"
    assert data["profile"] is None


def test_create_my_profile():
    email, headers = create_test_user()

    response = client.patch(
        "/users/me",
        headers=headers,
        json={
            "full_name": "Arya Dalwale",
            "phone_number": "9876543210",
            "bio": "Computer Engineering student",
            "profile_photo_url": "https://example.com/profile.jpg",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == email
    assert data["profile"]["full_name"] == "Arya Dalwale"
    assert data["profile"]["phone_number"] == "9876543210"
    assert data["profile"]["bio"] == "Computer Engineering student"
    assert (
        data["profile"]["profile_photo_url"]
        == "https://example.com/profile.jpg"
    )


def test_update_my_profile():
    email, headers = create_test_user()

    create_response = client.patch(
        "/users/me",
        headers=headers,
        json={
            "full_name": "Arya Dalwale",
            "phone_number": "9876543210",
            "bio": "Initial bio",
        },
    )

    assert create_response.status_code == 200

    update_response = client.patch(
        "/users/me",
        headers=headers,
        json={
            "full_name": "Arya Updated",
            "bio": "Updated bio",
        },
    )

    assert update_response.status_code == 200

    data = update_response.json()

    assert data["email"] == email
    assert data["profile"]["full_name"] == "Arya Updated"
    assert data["profile"]["bio"] == "Updated bio"
    assert data["profile"]["phone_number"] == "9876543210"


def test_create_profile_requires_full_name():
    _, headers = create_test_user()

    response = client.patch(
        "/users/me",
        headers=headers,
        json={
            "bio": "Profile without a name",
        },
    )

    assert response.status_code == 422