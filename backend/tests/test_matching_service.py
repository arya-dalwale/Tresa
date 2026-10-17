from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from app.models.journey import Journey
from app.services.matching_service import (
    calculate_destination_distance,
    calculate_luggage_compatibility,
    calculate_origin_proximity,
    calculate_time_compatibility,
    find_candidate_journeys,
)


def test_find_candidate_journeys_returns_matching_journeys():
    db = Mock()

    journey = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=datetime.now(timezone.utc),
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    candidate = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=datetime.now(timezone.utc),
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    db.scalars.return_value.all.return_value = [candidate]

    result = find_candidate_journeys(db, journey)

    assert result == [candidate]


def test_calculate_destination_distance_returns_distance():
    db = Mock()

    journey = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=datetime.now(timezone.utc),
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    candidate = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=datetime.now(timezone.utc),
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    db.scalar.return_value = 0.0

    result = calculate_destination_distance(
        db,
        journey,
        candidate,
    )

    assert result == 0.0
    db.scalar.assert_called_once()


def test_calculate_time_compatibility_same_time():
    departure_time = datetime(
        2026,
        10,
        17,
        10,
        0,
        tzinfo=timezone.utc,
    )

    journey = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=departure_time,
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    candidate = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=departure_time,
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    result = calculate_time_compatibility(
        journey,
        candidate,
    )

    assert result == 1.0


def test_calculate_time_compatibility_decreases_with_time_difference():
    departure_time = datetime(
        2026,
        10,
        17,
        10,
        0,
        tzinfo=timezone.utc,
    )

    journey = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=departure_time,
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    candidate = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=departure_time + timedelta(minutes=30),
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    result = calculate_time_compatibility(
        journey,
        candidate,
    )

    assert result == 0.5


def test_calculate_time_compatibility_returns_zero_at_max_difference():
    departure_time = datetime(
        2026,
        10,
        17,
        10,
        0,
        tzinfo=timezone.utc,
    )

    journey = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=departure_time,
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    candidate = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=departure_time + timedelta(minutes=60),
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    result = calculate_time_compatibility(
        journey,
        candidate,
    )

    assert result == 0.0


def test_calculate_origin_proximity_same_origin():
    db = Mock()

    departure_time = datetime(
        2026,
        10,
        17,
        10,
        0,
        tzinfo=timezone.utc,
    )

    journey = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=departure_time,
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    candidate = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=departure_time,
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    db.scalar.return_value = 0.0

    result = calculate_origin_proximity(
        db,
        journey,
        candidate,
    )

    assert result == 1.0
    db.scalar.assert_called_once()


def test_calculate_origin_proximity_at_search_radius():
    db = Mock()

    departure_time = datetime(
        2026,
        10,
        17,
        10,
        0,
        tzinfo=timezone.utc,
    )

    journey = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=departure_time,
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    candidate = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=departure_time,
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    db.scalar.return_value = 10_000.0

    result = calculate_origin_proximity(
        db,
        journey,
        candidate,
    )

    assert result == 0.0
    db.scalar.assert_called_once()


def test_calculate_luggage_compatibility_same_luggage():
    journey = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=datetime.now(timezone.utc),
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    candidate = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=datetime.now(timezone.utc),
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    result = calculate_luggage_compatibility(
        journey,
        candidate,
    )

    assert result == 1.0


def test_calculate_luggage_compatibility_one_level_difference():
    journey = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=datetime.now(timezone.utc),
        passengers=1,
        luggage="small",
        radius_km=10.0,
        status="planned",
    )

    candidate = Journey(
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=datetime.now(timezone.utc),
        passengers=1,
        luggage="medium",
        radius_km=10.0,
        status="planned",
    )

    result = calculate_luggage_compatibility(
        journey,
        candidate,
    )

    assert result == 0.5