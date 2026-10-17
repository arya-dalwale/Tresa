from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class SmokingPreference(str, Enum):
    SMOKER = "smoker"
    NON_SMOKER = "non_smoker"
    NO_PREFERENCE = "no_preference"


class MusicPreference(str, Enum):
    QUIET = "quiet"
    MUSIC = "music"
    NO_PREFERENCE = "no_preference"


class ConversationPreference(str, Enum):
    QUIET = "quiet"
    SOCIAL = "social"
    NO_PREFERENCE = "no_preference"


class FoodPreference(str, Enum):
    VEG = "veg"
    NON_VEG = "non_veg"
    NO_PREFERENCE = "no_preference"


class TravelStylePreference(str, Enum):
    RELAXED = "relaxed"
    BALANCED = "balanced"
    FAST = "fast"
    NO_PREFERENCE = "no_preference"


class JourneyPreferenceBase(BaseModel):
    smoking: SmokingPreference | None = None
    music: MusicPreference | None = None
    conversation: ConversationPreference | None = None
    food: FoodPreference | None = None
    travel_style: TravelStylePreference | None = None


class JourneyPreferenceCreate(JourneyPreferenceBase):
    journey_id: UUID


class JourneyPreferenceResponse(JourneyPreferenceBase):
    id: UUID
    journey_id: UUID