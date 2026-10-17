import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JourneyPreference(Base):
    __tablename__ = "journey_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journeys.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    smoking: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    music: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    conversation: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    food: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    travel_style: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )