from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_name: str
    phone_number: str | None = None
    bio: str | None = None
    profile_photo_url: str | None = None


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    is_active: bool
    role: str
    profile: ProfileResponse | None = None


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    phone_number: str | None = Field(
        default=None,
        max_length=20,
    )
    bio: str | None = Field(
        default=None,
        max_length=500,
    )
    profile_photo_url: str | None = Field(
        default=None,
        max_length=500,
    )