import uuid

import pytest
from pydantic import ValidationError

from app.schemas.journey_preferences import (
    ConversationPreference,
    FoodPreference,
    JourneyPreferenceBase,
    JourneyPreferenceCreate,
    JourneyPreferenceResponse,
    MusicPreference,
    SmokingPreference,
    TravelStylePreference,
)


def test_all_preference_fields_are_optional():
    preferences = JourneyPreferenceBase()

    assert preferences.smoking is None
    assert preferences.music is None
    assert preferences.conversation is None
    assert preferences.food is None
    assert preferences.travel_style is None


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("smoking", "smoker", SmokingPreference.SMOKER),
        ("smoking", "non_smoker", SmokingPreference.NON_SMOKER),
        ("smoking", "no_preference", SmokingPreference.NO_PREFERENCE),
        ("music", "quiet", MusicPreference.QUIET),
        ("music", "music", MusicPreference.MUSIC),
        ("music", "no_preference", MusicPreference.NO_PREFERENCE),
        (
            "conversation",
            "quiet",
            ConversationPreference.QUIET,
        ),
        (
            "conversation",
            "social",
            ConversationPreference.SOCIAL,
        ),
        (
            "conversation",
            "no_preference",
            ConversationPreference.NO_PREFERENCE,
        ),
        ("food", "veg", FoodPreference.VEG),
        ("food", "non_veg", FoodPreference.NON_VEG),
        ("food", "no_preference", FoodPreference.NO_PREFERENCE),
        (
            "travel_style",
            "relaxed",
            TravelStylePreference.RELAXED,
        ),
        (
            "travel_style",
            "balanced",
            TravelStylePreference.BALANCED,
        ),
        (
            "travel_style",
            "fast",
            TravelStylePreference.FAST,
        ),
        (
            "travel_style",
            "no_preference",
            TravelStylePreference.NO_PREFERENCE,
        ),
    ],
)
def test_valid_preference_values_are_accepted(
    field,
    value,
    expected,
):
    preferences = JourneyPreferenceBase(**{field: value})

    assert getattr(preferences, field) == expected


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("smoking", "sometimes"),
        ("music", "very_loud"),
        ("conversation", "silent"),
        ("food", "vegan_only"),
        ("travel_style", "extreme"),
    ],
)
def test_invalid_preference_values_are_rejected(
    field,
    invalid_value,
):
    with pytest.raises(ValidationError):
        JourneyPreferenceBase(**{field: invalid_value})


def test_journey_preference_create_accepts_uuid_and_optional_fields():
    journey_id = uuid.uuid4()

    preferences = JourneyPreferenceCreate(
        journey_id=journey_id,
        smoking="non_smoker",
        food="veg",
    )

    assert preferences.journey_id == journey_id
    assert preferences.smoking == SmokingPreference.NON_SMOKER
    assert preferences.food == FoodPreference.VEG
    assert preferences.music is None
    assert preferences.conversation is None
    assert preferences.travel_style is None


def test_journey_preference_create_requires_journey_id():
    with pytest.raises(ValidationError):
        JourneyPreferenceCreate(smoking="smoker")


def test_journey_preference_response_contains_identifiers():
    preference_id = uuid.uuid4()
    journey_id = uuid.uuid4()

    response = JourneyPreferenceResponse(
        id=preference_id,
        journey_id=journey_id,
        music="quiet",
    )

    assert response.id == preference_id
    assert response.journey_id == journey_id
    assert response.music == MusicPreference.QUIET


def test_journey_preference_response_requires_identifiers():
    with pytest.raises(ValidationError):
        JourneyPreferenceResponse()