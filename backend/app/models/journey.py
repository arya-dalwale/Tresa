import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geography
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Journey(Base):
    __tablename__ = "journeys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    origin: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )

    destination: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )

    departure_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    passengers: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    luggage: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
    )

    radius_km: Mapped[float] = mapped_column(
        nullable=False,
        default=10.0,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="planned",
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
        CheckConstraint("passengers >= 1", name="ck_journeys_passengers_min"),
        CheckConstraint(
            "radius_km > 0",
            name="ck_journeys_radius_positive",
        ),
        CheckConstraint(
            "luggage IN ('small', 'medium', 'large')",
            name="ck_journeys_luggage_allowed",
        ),
        CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'cancelled')",
            name="ck_journeys_status_allowed",
        ),
        Index("ix_journeys_origin_gist", "origin", postgresql_using="gist"),
        Index("ix_journeys_destination_gist", "destination", postgresql_using="gist"),
        Index("ix_journeys_departure_time", "departure_time"),
        Index("ix_journeys_status", "status"),
    )