from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def register_and_login():
    email = f"group_test_{uuid4().hex}@test.com"
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


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def journey_payload(passengers=1):
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
        "passengers": passengers,
        "luggage": "medium",
        "radius_km": 10,
    }


def create_journey(token, passengers=1):
    response = client.post(
        "/journeys",
        json=journey_payload(passengers),
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    return response.json()


def create_group(token, journey_id):
    response = client.post(
        "/groups",
        json={"journey_id": journey_id},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    return response.json()


def test_groups_require_authentication():
    response = client.get("/groups")

    assert response.status_code == 401


def test_create_group_adds_creator_as_first_member():
    token = register_and_login()
    journey = create_journey(token)

    response = client.post(
        "/groups",
        json={"journey_id": journey["id"]},
        headers=auth_headers(token),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["status"] == "forming"
    assert data["created_by"] is not None
    assert data["group_size"] == 1
    assert data["total_passengers"] == 1
    assert len(data["members"]) == 1
    assert data["members"][0]["journey_id"] == journey["id"]


def test_create_group_rejects_another_users_journey():
    owner_token = register_and_login()
    other_token = register_and_login()

    journey = create_journey(owner_token)

    response = client.post(
        "/groups",
        json={"journey_id": journey["id"]},
        headers=auth_headers(other_token),
    )

    assert response.status_code == 403


def test_group_member_can_retrieve_group_details():
    token = register_and_login()
    journey = create_journey(token)
    group = create_group(token, journey["id"])

    response = client.get(
        f"/groups/{group['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == group["id"]
    assert response.json()["group_size"] == 1


def test_non_member_cannot_retrieve_group():
    owner_token = register_and_login()
    other_token = register_and_login()

    journey = create_journey(owner_token)
    group = create_group(owner_token, journey["id"])

    response = client.get(
        f"/groups/{group['id']}",
        headers=auth_headers(other_token),
    )

    assert response.status_code == 403


def test_user_can_join_a_compatible_forming_group():
    owner_token = register_and_login()
    joining_token = register_and_login()

    owner_journey = create_journey(owner_token)
    joining_journey = create_journey(joining_token)

    group = create_group(owner_token, owner_journey["id"])

    response = client.post(
        f"/groups/{group['id']}/members",
        json={"journey_id": joining_journey["id"]},
        headers=auth_headers(joining_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == group["id"]
    assert data["group_size"] == 2
    assert data["total_passengers"] == 2

    member_journey_ids = {
        member["journey_id"] for member in data["members"]
    }

    assert owner_journey["id"] in member_journey_ids
    assert joining_journey["id"] in member_journey_ids


def test_join_group_rejects_a_journey_owned_by_another_user():
    owner_token = register_and_login()
    journey_owner_token = register_and_login()
    other_token = register_and_login()

    owner_journey = create_journey(owner_token)
    foreign_journey = create_journey(journey_owner_token)

    group = create_group(owner_token, owner_journey["id"])

    response = client.post(
        f"/groups/{group['id']}/members",
        json={"journey_id": foreign_journey["id"]},
        headers=auth_headers(other_token),
    )

    assert response.status_code == 403


def test_user_cannot_join_the_same_group_twice():
    token = register_and_login()

    first_journey = create_journey(token)
    second_journey = create_journey(token)

    group = create_group(token, first_journey["id"])

    response = client.post(
        f"/groups/{group['id']}/members",
        json={"journey_id": second_journey["id"]},
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_journey_cannot_join_two_open_groups():
    first_token = register_and_login()
    second_token = register_and_login()

    first_journey = create_journey(first_token)
    second_journey = create_journey(second_token)

    first_group = create_group(
        first_token,
        first_journey["id"],
    )

    second_group = create_group(
        second_token,
        second_journey["id"],
    )

    response = client.post(
        f"/groups/{second_group['id']}/members",
        json={"journey_id": first_journey["id"]},
        headers=auth_headers(first_token),
    )

    assert response.status_code == 409

    # The original group should remain intact.
    original_response = client.get(
        f"/groups/{first_group['id']}",
        headers=auth_headers(first_token),
    )

    assert original_response.status_code == 200
    assert original_response.json()["group_size"] == 1


def test_group_creator_can_activate_and_complete_group():
    owner_token = register_and_login()
    joining_token = register_and_login()

    owner_journey = create_journey(owner_token)
    joining_journey = create_journey(joining_token)

    group = create_group(owner_token, owner_journey["id"])

    join_response = client.post(
        f"/groups/{group['id']}/members",
        json={"journey_id": joining_journey["id"]},
        headers=auth_headers(joining_token),
    )

    assert join_response.status_code == 200

    active_response = client.patch(
        f"/groups/{group['id']}/status",
        json={"status": "active"},
        headers=auth_headers(owner_token),
    )

    assert active_response.status_code == 200
    assert active_response.json()["status"] == "active"

    completed_response = client.patch(
        f"/groups/{group['id']}/status",
        json={"status": "completed"},
        headers=auth_headers(owner_token),
    )

    assert completed_response.status_code == 200
    assert completed_response.json()["status"] == "completed"


def test_non_creator_cannot_change_group_status():
    owner_token = register_and_login()
    joining_token = register_and_login()

    owner_journey = create_journey(owner_token)
    joining_journey = create_journey(joining_token)

    group = create_group(owner_token, owner_journey["id"])

    join_response = client.post(
        f"/groups/{group['id']}/members",
        json={"journey_id": joining_journey["id"]},
        headers=auth_headers(joining_token),
    )

    assert join_response.status_code == 200

    response = client.patch(
        f"/groups/{group['id']}/status",
        json={"status": "active"},
        headers=auth_headers(joining_token),
    )

    assert response.status_code == 403


def test_completed_group_cannot_be_reactivated():
    token = register_and_login()
    journey = create_journey(token)
    group = create_group(token, journey["id"])

    # Cancel a forming group, then verify its terminal status.
    cancel_response = client.patch(
        f"/groups/{group['id']}/status",
        json={"status": "cancelled"},
        headers=auth_headers(token),
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    reactivate_response = client.patch(
        f"/groups/{group['id']}/status",
        json={"status": "active"},
        headers=auth_headers(token),
    )

    assert reactivate_response.status_code == 409