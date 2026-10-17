from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import UUID

import pytest

from app.models.journey import Journey
from app.models.journey_preference import JourneyPreference
from app.services.matching_service import (
    MATCHING_WEIGHTS,
    calculate_destination_distance,
    calculate_luggage_compatibility,
    calculate_match_score,
    calculate_origin_proximity,
    calculate_preference_score,
    calculate_time_compatibility,
    find_candidate_journeys,
    rank_candidates,
)


def create_test_journey(
    journey_id=None,
    user_id=None,
    status="planned",
    radius_km=10.0,
    luggage="medium",
    departure_time=None,
):
    journey = Journey(
        id=journey_id,
        user_id=user_id,
        origin="SRID=4326;POINT(73.8567 18.5204)",
        destination="SRID=4326;POINT(73.8567 18.5204)",
        departure_time=departure_time
        or datetime.now(timezone.utc),
        passengers=1,
        luggage=luggage,
        radius_km=radius_km,
        status=status,
    )

    return journey


def test_find_candidate_journeys():
    db = Mock()

    target_journey = create_test_journey()

    candidate_one = create_test_journey()
    candidate_two = create_test_journey()

    db.scalars.return_value.all.return_value = [
        candidate_one,
        candidate_two,
    ]

    candidates = find_candidate_journeys(
        db,
        target_journey,
    )

    assert candidates == [
        candidate_one,
        candidate_two,
    ]

    db.scalars.assert_called_once()


def test_calculate_destination_distance():
    db = Mock()

    target_journey = create_test_journey()
    candidate_journey = create_test_journey()

    db.scalar.return_value = 5000.0

    distance = calculate_destination_distance(
        db,
        target_journey,
        candidate_journey,
    )

    assert distance == 5000.0


def test_calculate_time_compatibility_same_time():
    departure_time = datetime.now(timezone.utc)

    journey = create_test_journey(
        departure_time=departure_time,
    )

    candidate = create_test_journey(
        departure_time=departure_time,
    )

    score = calculate_time_compatibility(
        journey,
        candidate,
    )

    assert score == 1.0


def test_calculate_time_compatibility_30_minutes():
    departure_time = datetime.now(timezone.utc)

    journey = create_test_journey(
        departure_time=departure_time,
    )

    candidate = create_test_journey(
        departure_time=departure_time + timedelta(minutes=30),
    )

    score = calculate_time_compatibility(
        journey,
        candidate,
    )

    assert score == 0.5


def test_calculate_time_compatibility_60_minutes():
    departure_time = datetime.now(timezone.utc)

    journey = create_test_journey(
        departure_time=departure_time,
    )

    candidate = create_test_journey(
        departure_time=departure_time + timedelta(minutes=60),
    )

    score = calculate_time_compatibility(
        journey,
        candidate,
    )

    assert score == 0.0


def test_calculate_origin_proximity_same_origin():
    db = Mock()

    journey = create_test_journey(
        radius_km=10.0,
    )

    candidate = create_test_journey()

    db.scalar.return_value = 0.0

    score = calculate_origin_proximity(
        db,
        journey,
        candidate,
    )

    assert score == 1.0


def test_calculate_origin_proximity_at_search_radius():
    db = Mock()

    journey = create_test_journey(
        radius_km=10.0,
    )

    candidate = create_test_journey()

    db.scalar.return_value = 10000.0

    score = calculate_origin_proximity(
        db,
        journey,
        candidate,
    )

    assert score == 0.0


def test_calculate_luggage_compatibility_same():
    journey = create_test_journey(
        luggage="medium",
    )

    candidate = create_test_journey(
        luggage="medium",
    )

    score = calculate_luggage_compatibility(
        journey,
        candidate,
    )

    assert score == 1.0


def test_calculate_luggage_compatibility_one_level_difference():
    journey = create_test_journey(
        luggage="small",
    )

    candidate = create_test_journey(
        luggage="medium",
    )

    score = calculate_luggage_compatibility(
        journey,
        candidate,
    )

    assert score == 0.5


def test_matching_weights_include_preferences():
    assert MATCHING_WEIGHTS["preferences"] == 0.10


def test_preference_score_same_preferences():
    journey_preferences = JourneyPreference(
        smoking="non_smoker",
        music="quiet",
        conversation="social",
        food="veg",
        travel_style="balanced",
    )

    candidate_preferences = JourneyPreference(
        smoking="non_smoker",
        music="quiet",
        conversation="social",
        food="veg",
        travel_style="balanced",
    )

    score = calculate_preference_score(
        journey_preferences,
        candidate_preferences,
    )

    assert score == 1.0


def test_preference_score_conflicting_preferences():
    journey_preferences = JourneyPreference(
        smoking="non_smoker",
        music="quiet",
        conversation="social",
        food="veg",
        travel_style="balanced",
    )

    candidate_preferences = JourneyPreference(
        smoking="smoker",
        music="music",
        conversation="quiet",
        food="non_veg",
        travel_style="fast",
    )

    score = calculate_preference_score(
        journey_preferences,
        candidate_preferences,
    )

    assert score == 0.0


def test_preference_score_no_preference():
    journey_preferences = JourneyPreference(
        smoking="no_preference",
        music="quiet",
        conversation="social",
        food="veg",
        travel_style="balanced",
    )

    candidate_preferences = JourneyPreference(
        smoking="smoker",
        music="quiet",
        conversation="social",
        food="veg",
        travel_style="balanced",
    )

    score = calculate_preference_score(
        journey_preferences,
        candidate_preferences,
    )

    assert score == 1.0


def test_perfect_match_score_without_route():
    component_scores = {
        "route": None,
        "destination": 1.0,
        "time": 1.0,
        "origin_proximity": 1.0,
        "preferences": 1.0,
        "luggage": 1.0,
    }

    score = calculate_match_score(component_scores)

    assert score == 1.0


def test_partial_match_score_without_route():
    component_scores = {
        "route": None,
        "destination": 0.8,
        "time": 0.6,
        "origin_proximity": 0.4,
        "preferences": 1.0,
        "luggage": 0.5,
    }

    expected_score = (
        (0.8 * 0.25)
        + (0.6 * 0.20)
        + (0.4 * 0.10)
        + (1.0 * 0.10)
        + (0.5 * 0.05)
    ) / 0.70

    score = calculate_match_score(component_scores)

    assert score == pytest.approx(expected_score)


def test_zero_compatibility_score():
    component_scores = {
        "route": None,
        "destination": 0.0,
        "time": 0.0,
        "origin_proximity": 0.0,
        "preferences": 0.0,
        "luggage": 0.0,
    }

    score = calculate_match_score(component_scores)

    assert score == 0.0


def test_missing_route_overlap_is_excluded_and_weights_are_renormalized():
    component_scores = {
        "route": None,
        "destination": 1.0,
        "time": 1.0,
        "origin_proximity": 1.0,
        "preferences": 1.0,
        "luggage": 1.0,
    }

    score = calculate_match_score(component_scores)

    available_weight = (
        MATCHING_WEIGHTS["destination"]
        + MATCHING_WEIGHTS["time"]
        + MATCHING_WEIGHTS["origin_proximity"]
        + MATCHING_WEIGHTS["preferences"]
        + MATCHING_WEIGHTS["luggage"]
    )

    assert available_weight == pytest.approx(0.70)
    assert score == 1.0


def test_score_always_between_zero_and_one():
    test_scores = [
        {
            "route": None,
            "destination": 0.0,
            "time": 0.0,
            "origin_proximity": 0.0,
            "preferences": 0.0,
            "luggage": 0.0,
        },
        {
            "route": None,
            "destination": 0.5,
            "time": 0.75,
            "origin_proximity": 0.25,
            "preferences": 1.0,
            "luggage": 0.5,
        },
        {
            "route": None,
            "destination": 1.0,
            "time": 1.0,
            "origin_proximity": 1.0,
            "preferences": 1.0,
            "luggage": 1.0,
        },
    ]

    for component_scores in test_scores:
        score = calculate_match_score(component_scores)

        assert 0.0 <= score <= 1.0


def test_rank_candidates_highest_to_lowest():
    candidate_one = UUID("00000000-0000-0000-0000-000000000001")
    candidate_two = UUID("00000000-0000-0000-0000-000000000002")
    candidate_three = UUID("00000000-0000-0000-0000-000000000003")

    candidates = [
        (candidate_one, 0.40),
        (candidate_two, 0.90),
        (candidate_three, 0.70),
    ]

    ranked = rank_candidates(candidates)

    assert ranked == [
        (candidate_two, 0.90),
        (candidate_three, 0.70),
        (candidate_one, 0.40),
    ]


def test_rank_candidates_equal_scores_are_deterministic():
    candidate_one = UUID("00000000-0000-0000-0000-000000000001")
    candidate_two = UUID("00000000-0000-0000-0000-000000000002")

    candidates = [
        (candidate_two, 0.80),
        (candidate_one, 0.80),
    ]

    ranked = rank_candidates(candidates)

    assert ranked == [
        (candidate_one, 0.80),
        (candidate_two, 0.80),
    ]


def test_invalid_component_score_is_rejected():
    component_scores = {
        "route": None,
        "destination": 1.2,
        "time": 1.0,
        "origin_proximity": 1.0,
        "preferences": 1.0,
        "luggage": 1.0,
    }

    with pytest.raises(ValueError):
        calculate_match_score(component_scores)