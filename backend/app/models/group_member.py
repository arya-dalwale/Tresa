import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "travel_groups.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journeys.id"),
        nullable=False,
    )

    passengers: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint(
            "passengers >= 1",
            name="ck_group_members_passengers_min",
        ),
        UniqueConstraint(
            "group_id",
            "user_id",
            name="uq_group_members_group_user",
        ),
        UniqueConstraint(
            "group_id",
            "journey_id",
            name="uq_group_members_group_journey",
        ),
        Index(
            "ix_group_members_group_id",
            "group_id",
        ),
        Index(
            "ix_group_members_user_id",
            "user_id",
        ),
        Index(
            "ix_group_members_journey_id",
            "journey_id",
        ),
    )