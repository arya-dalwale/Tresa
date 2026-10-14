from datetime import datetime, timezone
from unittest.mock import Mock

from app.models.journey import Journey
from app.services.matching_service import find_candidate_journeys


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