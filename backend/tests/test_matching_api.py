from datetime import datetime, timedelta, timezone
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.models.journey import Journey


client = TestClient(app)


# ==========================================================
# TEST HELPERS
# ==========================================================

def register_and_login() -> str:
    """Register a unique test user and return the access token."""
    email = f"matching_test_{uuid.uuid4().hex}@test.com"
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


def unique_origin() -> tuple[float, float]:
    """Generate an isolated latitude/longitude for test data."""
    value = uuid.uuid4().int

    latitude = round((value % 9000) / 100 - 45, 4)
    longitude = round(((value >> 16) % 28000) / 100 - 140, 4)

    return latitude, longitude


def journey_payload(
    origin: tuple[float, float],
    destination: tuple[float, float],
    departure_time: str,
    radius_km: float = 10.0,
    passengers: int = 1,
) -> dict:
    """Create a Journey API request payload."""
    return {
        "origin": {
            "latitude": origin[0],
            "longitude": origin[1],
        },
        "destination": {
            "latitude": destination[0],
            "longitude": destination[1],
        },
        "departure_time": departure_time,
        "passengers": passengers,
        "luggage": "medium",
        "radius_km": radius_km,
    }


def create_journey(
    token: str,
    payload: dict,
) -> dict:
    """Create a journey through the existing authenticated API."""
    response = client.post(
        "/journeys",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_matching_scenario() -> dict:
    """
    Create a target journey and two eligible candidates.

    Candidate one has the same destination as the target.
    Candidate two has a farther destination and should score lower.
    All three journeys are created in an isolated geographic area.
    """
    target_token = register_and_login()
    candidate_one_token = register_and_login()
    candidate_two_token = register_and_login()

    base_latitude, base_longitude = unique_origin()

    target_destination = (
        base_latitude + 1.0,
        base_longitude + 1.0,
    )

    departure_time = (
        datetime.now(timezone.utc) + timedelta(days=2)
    ).isoformat()

    target = create_journey(
        target_token,
        journey_payload(
            origin=(base_latitude, base_longitude),
            destination=target_destination,
            departure_time=departure_time,
        ),
    )

    candidate_one = create_journey(
        candidate_one_token,
        journey_payload(
            origin=(base_latitude + 0.001, base_longitude),
            destination=target_destination,
            departure_time=departure_time,
        ),
    )

    candidate_two = create_journey(
        candidate_two_token,
        journey_payload(
            origin=(base_latitude + 0.002, base_longitude),
            destination=(
                target_destination[0] + 0.04,
                target_destination[1],
            ),
            departure_time=departure_time,
        ),
    )

    return {
        "token": target_token,
        "target_id": target["id"],
        "candidate_one_id": candidate_one["id"],
        "candidate_two_id": candidate_two["id"],
    }


# ==========================================================
# AUTHENTICATION AND AUTHORIZATION
# ==========================================================

def test_matches_require_authentication():
    response = client.get(
        f"/journeys/{uuid.uuid4()}/matches"
    )

    assert response.status_code == 401


def test_missing_journey_returns_404():
    token = register_and_login()

    response = client.get(
        f"/journeys/{uuid.uuid4()}/matches",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_non_owner_cannot_access_journey_matches():
    owner_token = register_and_login()
    other_user_token = register_and_login()

    base_latitude, base_longitude = unique_origin()

    departure_time = (
        datetime.now(timezone.utc) + timedelta(days=2)
    ).isoformat()

    target = create_journey(
        owner_token,
        journey_payload(
            origin=(base_latitude, base_longitude),
            destination=(
                base_latitude + 1.0,
                base_longitude + 1.0,
            ),
            departure_time=departure_time,
        ),
    )

    response = client.get(
        f"/journeys/{target['id']}/matches",
        headers={
            "Authorization": f"Bearer {other_user_token}",
        },
    )

    assert response.status_code == 403


# ==========================================================
# PAGINATION VALIDATION
# ==========================================================

def test_matches_reject_invalid_limit():
    token = register_and_login()

    response = client.get(
        f"/journeys/{uuid.uuid4()}/matches?limit=101",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_matches_reject_negative_offset():
    token = register_and_login()

    response = client.get(
        f"/journeys/{uuid.uuid4()}/matches?offset=-1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


# ==========================================================
# EMPTY RESULTS
# ==========================================================

def test_no_eligible_candidates_returns_empty_arrays():
    token = register_and_login()

    base_latitude, base_longitude = unique_origin()

    departure_time = (
        datetime.now(timezone.utc) + timedelta(days=2)
    ).isoformat()

    target = create_journey(
        token,
        journey_payload(
            origin=(base_latitude, base_longitude),
            destination=(
                base_latitude + 1.0,
                base_longitude + 1.0,
            ),
            departure_time=departure_time,
            radius_km=2.0,
        ),
    )

    response = client.get(
        f"/journeys/{target['id']}/matches",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["matches"] == []
    assert response.json()["groups"] == []


# ==========================================================
# INDIVIDUAL MATCHES, RANKING, AND PRIVACY
# ==========================================================

def test_matches_are_ranked_highest_score_first():
    scenario = create_matching_scenario()

    response = client.get(
        f"/journeys/{scenario['target_id']}/matches",
        headers={
            "Authorization": f"Bearer {scenario['token']}",
        },
    )

    assert response.status_code == 200

    matches = response.json()["matches"]

    match_ids = [match["journey_id"] for match in matches]
    scores = [
        match["compatibility_score"]
        for match in matches
    ]

    assert scenario["candidate_one_id"] in match_ids
    assert scenario["candidate_two_id"] in match_ids
    assert scores == sorted(scores, reverse=True)

    candidate_one_index = match_ids.index(
        scenario["candidate_one_id"]
    )
    candidate_two_index = match_ids.index(
        scenario["candidate_two_id"]
    )

    assert scores[candidate_one_index] > scores[candidate_two_index]


def test_match_response_is_privacy_safe():
    scenario = create_matching_scenario()

    response = client.get(
        f"/journeys/{scenario['target_id']}/matches",
        headers={
            "Authorization": f"Bearer {scenario['token']}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    for match in data["matches"]:
        assert "origin" not in match
        assert "destination" not in match

        assert "origin_distance_km" in match
        assert "score_breakdown" in match

        breakdown = match["score_breakdown"]

        assert breakdown["route"] is None
        assert 0.0 <= match["compatibility_score"] <= 1.0

        for field in (
            "destination",
            "time",
            "origin_proximity",
            "preferences",
            "luggage",
        ):
            assert 0.0 <= breakdown[field] <= 1.0


# ==========================================================
# GROUP INTEGRATION
# ==========================================================

def test_matching_response_includes_recommended_groups():
    scenario = create_matching_scenario()

    response = client.get(
        f"/journeys/{scenario['target_id']}/matches",
        headers={
            "Authorization": f"Bearer {scenario['token']}",
        },
    )

    assert response.status_code == 200

    groups = response.json()["groups"]

    assert groups, "Expected at least one compatible group"

    group = groups[0]

    assert 2 <= group["group_size"] <= 5
    assert 2 <= group["total_passengers"] <= 5
    assert 0.60 <= group["group_compatibility_score"] <= 1.0

    member_ids = [
        member["journey_id"]
        for member in group["members"]
    ]

    assert group["member_journey_ids"] == member_ids
    assert scenario["target_id"] in member_ids
    assert len(member_ids) == len(set(member_ids))

    for member in group["members"]:
        assert "origin" not in member
        assert "destination" not in member


# ==========================================================
# PAGINATION
# ==========================================================

def test_matches_support_limit_and_offset():
    scenario = create_matching_scenario()

    response = client.get(
        f"/journeys/{scenario['target_id']}/matches?limit=1&offset=1",
        headers={
            "Authorization": f"Bearer {scenario['token']}",
        },
    )

    assert response.status_code == 200

    matches = response.json()["matches"]

    assert len(matches) == 1
    assert matches[0]["journey_id"] == scenario["candidate_two_id"]


# ==========================================================
# EDGE CASES
# ==========================================================

def test_completed_and_cancelled_candidates_are_excluded():
    target_token = register_and_login()
    completed_token = register_and_login()
    cancelled_token = register_and_login()

    base_latitude, base_longitude = unique_origin()

    destination = (
        base_latitude + 1.0,
        base_longitude + 1.0,
    )

    departure_time = (
        datetime.now(timezone.utc) + timedelta(days=2)
    ).isoformat()

    target = create_journey(
        target_token,
        journey_payload(
            origin=(base_latitude, base_longitude),
            destination=destination,
            departure_time=departure_time,
        ),
    )

    completed = create_journey(
        completed_token,
        journey_payload(
            origin=(base_latitude + 0.001, base_longitude),
            destination=destination,
            departure_time=departure_time,
        ),
    )

    cancelled = create_journey(
        cancelled_token,
        journey_payload(
            origin=(base_latitude + 0.002, base_longitude),
            destination=destination,
            departure_time=departure_time,
        ),
    )

    completed_update = client.patch(
        f"/journeys/{completed['id']}",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {completed_token}"},
    )

    cancelled_update = client.patch(
        f"/journeys/{cancelled['id']}",
        json={"status": "cancelled"},
        headers={"Authorization": f"Bearer {cancelled_token}"},
    )

    assert completed_update.status_code == 200
    assert cancelled_update.status_code == 200

    response = client.get(
        f"/journeys/{target['id']}/matches",
        headers={"Authorization": f"Bearer {target_token}"},
    )

    assert response.status_code == 200

    match_ids = {
        match["journey_id"]
        for match in response.json()["matches"]
    }

    assert completed["id"] not in match_ids
    assert cancelled["id"] not in match_ids

    for group in response.json()["groups"]:
        group_member_ids = {
            member["journey_id"]
            for member in group["members"]
        }
        assert completed["id"] not in group_member_ids
        assert cancelled["id"] not in group_member_ids


def test_matches_support_candidates_without_profiles():
    scenario = create_matching_scenario()

    response = client.get(
        f"/journeys/{scenario['target_id']}/matches",
        headers={"Authorization": f"Bearer {scenario['token']}"},
    )

    assert response.status_code == 200

    matches = response.json()["matches"]
    assert matches

    candidate_ids = {
        scenario["candidate_one_id"],
        scenario["candidate_two_id"],
    }

    candidate_matches = [
        match
        for match in matches
        if match["journey_id"] in candidate_ids
    ]

    assert len(candidate_matches) == 2

    for match in candidate_matches:
        assert match["full_name"] is None
        assert match["profile_photo_url"] is None


def test_origin_distance_uses_actual_postgis_distance():
    scenario = create_matching_scenario()

    with SessionLocal() as db:
        target = db.get(
            Journey,
            uuid.UUID(scenario["target_id"]),
        )
        candidate = db.get(
            Journey,
            uuid.UUID(scenario["candidate_one_id"]),
        )

        assert target is not None
        assert candidate is not None

        expected_distance_meters = db.scalar(
            select(
                Journey.origin.ST_Distance(candidate.origin)
            ).where(
                Journey.id == target.id
            )
        )

        assert expected_distance_meters is not None

        expected_distance_km = float(
            expected_distance_meters
        ) / 1000.0

    response = client.get(
        f"/journeys/{scenario['target_id']}/matches",
        headers={"Authorization": f"Bearer {scenario['token']}"},
    )

    assert response.status_code == 200

    candidate_match = next(
        match
        for match in response.json()["matches"]
        if match["journey_id"] == scenario["candidate_one_id"]
    )

    assert candidate_match["origin_distance_km"] == pytest.approx(
        expected_distance_km,
        abs=1e-9,
    )


# ==========================================================
# ADDITIONAL API CONTRACT AND REGRESSION TESTS
# ==========================================================

def test_matches_accept_limit_minimum_boundary():
    scenario = create_matching_scenario()

    response = client.get(
        f"/journeys/{scenario['target_id']}/matches?limit=1&offset=0",
        headers={
            "Authorization": f"Bearer {scenario['token']}",
        },
    )

    assert response.status_code == 200
    assert len(response.json()["matches"]) <= 1
    assert len(response.json()["groups"]) <= 1


def test_matches_accept_limit_maximum_boundary():
    scenario = create_matching_scenario()

    response = client.get(
        f"/journeys/{scenario['target_id']}/matches?limit=100&offset=0",
        headers={
            "Authorization": f"Bearer {scenario['token']}",
        },
    )

    assert response.status_code == 200
    assert len(response.json()["matches"]) <= 100
    assert len(response.json()["groups"]) <= 100


def test_individual_match_response_fields_follow_contract():
    scenario = create_matching_scenario()

    response = client.get(
        f"/journeys/{scenario['target_id']}/matches",
        headers={
            "Authorization": f"Bearer {scenario['token']}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert set(data.keys()) == {"matches", "groups"}
    assert data["matches"]

    match = data["matches"][0]

    assert set(match.keys()) == {
        "journey_id",
        "user_id",
        "full_name",
        "profile_photo_url",
        "departure_time",
        "passengers",
        "luggage",
        "origin_distance_km",
        "compatibility_score",
        "score_breakdown",
    }

    assert set(match["score_breakdown"].keys()) == {
        "route",
        "destination",
        "time",
        "origin_proximity",
        "preferences",
        "luggage",
    }


def test_matching_api_openapi_documents_pagination_and_auth():
    openapi = app.openapi()

    path = "/journeys/{journey_id}/matches"

    assert path in openapi["paths"]

    operation = openapi["paths"][path]["get"]

    parameters = {
        parameter["name"]: parameter
        for parameter in operation["parameters"]
        if parameter["in"] == "query"
    }

    assert "limit" in parameters
    assert parameters["limit"]["schema"]["default"] == 20
    assert parameters["limit"]["schema"]["minimum"] == 1
    assert parameters["limit"]["schema"]["maximum"] == 100

    assert "offset" in parameters
    assert parameters["offset"]["schema"]["default"] == 0
    assert parameters["offset"]["schema"]["minimum"] == 0

    assert operation.get("security")