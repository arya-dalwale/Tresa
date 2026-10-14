"""create profiles table

Revision ID: 4afe40301476
Revises: 5e54375427e5
Create Date: 2026-10-15 02:13:52.779930

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4afe40301476"
down_revision: Union[str, Sequence[str], None] = "5e54375427e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the profiles table."""

    op.create_table(
        "profiles",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "full_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "phone_number",
            sa.String(length=20),
            nullable=True,
        ),
        sa.Column(
            "bio",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "profile_photo_url",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    """Drop the profiles table."""

    op.drop_table("profiles")