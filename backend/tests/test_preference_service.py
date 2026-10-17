from app.models.journey_preference import JourneyPreference
from app.services.preference_service import calculate_preference_compatibility


def create_preferences(**overrides) -> JourneyPreference:
    values = {
        "smoking": "non_smoker",
        "music": "quiet",
        "conversation": "social",
        "food": "veg",
        "travel_style": "balanced",
    }
    values.update(overrides)
    return JourneyPreference(**values)


def test_same_specific_values_return_full_score():
    journey = create_preferences()
    candidate = create_preferences()

    score = calculate_preference_compatibility(journey, candidate)

    assert score == 1.0


def test_no_preference_on_either_side_is_full_compatibility():
    journey = create_preferences(smoking="no_preference")
    candidate = create_preferences(smoking="smoker")

    score = calculate_preference_compatibility(journey, candidate)

    assert score == 1.0


def test_conflicting_specific_values_score_zero_for_that_field():
    journey = create_preferences(smoking="non_smoker")
    candidate = create_preferences(smoking="smoker")

    score = calculate_preference_compatibility(journey, candidate)

    assert score == 0.8


def test_all_conflicting_preferences_return_zero():
    journey = create_preferences(
        smoking="non_smoker",
        music="quiet",
        conversation="quiet",
        food="veg",
        travel_style="relaxed",
    )

    candidate = create_preferences(
        smoking="smoker",
        music="music",
        conversation="social",
        food="non_veg",
        travel_style="fast",
    )

    score = calculate_preference_compatibility(journey, candidate)

    assert score == 0.0


def test_missing_preference_record_is_treated_as_no_preference():
    journey = create_preferences()

    score = calculate_preference_compatibility(journey, None)

    assert score == 1.0


def test_partial_conflicts_are_averaged_across_all_five_fields():
    journey = create_preferences(
        smoking="non_smoker",
        music="quiet",
        conversation="social",
        food="veg",
        travel_style="balanced",
    )

    candidate = create_preferences(
        smoking="smoker",
        music="music",
        conversation="social",
        food="veg",
        travel_style="fast",
    )

    score = calculate_preference_compatibility(journey, candidate)

    assert score == 0.4