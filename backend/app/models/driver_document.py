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


class DriverDocument(Base):
    __tablename__ = "driver_documents"

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

    document_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # Reference to a privately stored file, not a public URL.
    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Store only the last four characters when needed.
    # Do not store full sensitive document numbers in plain text.
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
            "document_type IN ('identity', 'driving_license')",
            name="ck_driver_documents_type_allowed",
        ),
        CheckConstraint(
            "status IN ('pending', 'under_review', 'verified', "
            "'rejected', 'suspended', 'expired')",
            name="ck_driver_documents_status_allowed",
        ),
        Index(
            "ix_driver_documents_driver_id",
            "driver_id",
        ),
        Index(
            "ix_driver_documents_status",
            "status",
        ),
        Index(
            "ix_driver_documents_expiry_date",
            "expiry_date",
        ),
    )