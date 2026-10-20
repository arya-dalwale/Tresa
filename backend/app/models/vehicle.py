import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="CASCADE"),
        nullable=False,
    )

    manufacturer: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    color: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    registration_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    seating_capacity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    verification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
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

    __table_args__ = (
        UniqueConstraint(
            "registration_number",
            name="uq_vehicles_registration_number",
        ),
        CheckConstraint(
            "seating_capacity >= 1",
            name="ck_vehicles_seating_capacity_min",
        ),
        CheckConstraint(
            "verification_status IN "
            "('pending', 'under_review', 'verified', "
            "'rejected', 'suspended', 'expired')",
            name="ck_vehicles_verification_status_allowed",
        ),
        Index(
            "ix_vehicles_driver_id",
            "driver_id",
        ),
        Index(
            "ix_vehicles_verification_status",
            "verification_status",
        ),
    )