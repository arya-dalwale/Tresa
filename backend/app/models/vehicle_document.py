import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VehicleDocument(Base):
    __tablename__ = "vehicle_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
    )

    document_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # Reference to private file storage, not a public URL.
    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Avoid storing full sensitive document numbers in plain text.
    document_number_last4: Mapped[str | None] = mapped_column(
        String(4),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    issue_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    expiry_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    provider_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
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

    __table_args__ = (
        CheckConstraint(
            "document_type IN "
            "('rc', 'insurance', 'puc', 'permit', 'fitness')",
            name="ck_vehicle_documents_type_allowed",
        ),
        CheckConstraint(
            "status IN ('pending', 'under_review', 'verified', "
            "'rejected', 'suspended', 'expired')",
            name="ck_vehicle_documents_status_allowed",
        ),
        Index(
            "ix_vehicle_documents_vehicle_id",
            "vehicle_id",
        ),
        Index(
            "ix_vehicle_documents_status",
            "status",
        ),
        Index(
            "ix_vehicle_documents_expiry_date",
            "expiry_date",
        ),
    )