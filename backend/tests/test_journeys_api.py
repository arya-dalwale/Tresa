from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def register_and_login():
    email = f"journey_test_{datetime.now(timezone.utc).timestamp()}@test.com"
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

    return login_response.json()["access_token"]


def journey_payload():
    return {
        "origin": {
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
        "destination": {
            "latitude": 19.0760,
            "longitude": 72.8777,
        },
        "departure_time": (
            datetime.now(timezone.utc) + timedelta(days=1)
        ).isoformat(),
        "passengers": 1,
        "luggage": "medium",
        "radius_km": 10,
    }


def test_create_journey():
    token = register_and_login()

    response = client.post(
        "/journeys",
        json=journey_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201

    data = response.json()

    assert "id" in data
    assert data["passengers"] == 1
    assert data["luggage"] == "medium"
    assert data["radius_km"] == 10


def test_get_journeys():
    token = register_and_login()

    create_response = client.post(
        "/journeys",
        json=journey_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert create_response.status_code == 201

    response = client.get(
        "/journeys",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_journey_by_id():
    token = register_and_login()

    create_response = client.post(
        "/journeys",
        json=journey_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert create_response.status_code == 201

    journey_id = create_response.json()["id"]

    response = client.get(
        f"/journeys/{journey_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == journey_id


def test_update_journey():
    token = register_and_login()

    create_response = client.post(
        "/journeys",
        json=journey_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert create_response.status_code == 201

    journey_id = create_response.json()["id"]

    response = client.patch(
        f"/journeys/{journey_id}",
        json={
            "passengers": 2,
            "luggage": "large",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == journey_id
    assert data["passengers"] == 2
    assert data["luggage"] == "large"


def test_delete_journey():
    token = register_and_login()

    create_response = client.post(
        "/journeys",
        json=journey_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert create_response.status_code == 201

    journey_id = create_response.json()["id"]

    response = client.delete(
        f"/journeys/{journey_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204


def test_journey_requires_authentication():
    response = client.get("/journeys")

    assert response.status_code == 401


def test_create_journey_requires_authentication():
    response = client.post(
        "/journeys",
        json=journey_payload(),
    )

    assert response.status_code == 401