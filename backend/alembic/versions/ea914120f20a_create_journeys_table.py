"""create journeys table

Revision ID: ea914120f20a
Revises: 4afe40301476
Create Date: 2026-10-15 02:51:29.275516

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = "ea914120f20a"
down_revision: Union[str, Sequence[str], None] = "4afe40301476"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "journeys",

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
            "origin",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeogFromText",
                name="geography",
                nullable=False,
            ),
            nullable=False,
        ),

        sa.Column(
            "destination",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeogFromText",
                name="geography",
                nullable=False,
            ),
            nullable=False,
        ),

        sa.Column(
            "departure_time",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "passengers",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),

        sa.Column(
            "luggage",
            sa.String(length=20),
            server_default=sa.text("'medium'"),
            nullable=False,
        ),

        sa.Column(
            "radius_km",
            sa.Double(),
            server_default=sa.text("10.0"),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'planned'"),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.CheckConstraint(
            "passengers >= 1",
            name="ck_journeys_passengers_min",
        ),

        sa.CheckConstraint(
            "radius_km > 0",
            name="ck_journeys_radius_positive",
        ),

        sa.CheckConstraint(
            "luggage IN ('small', 'medium', 'large')",
            name="ck_journeys_luggage_allowed",
        ),

        sa.CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'cancelled')",
            name="ck_journeys_status_allowed",
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_journeys_departure_time",
        "journeys",
        ["departure_time"],
        unique=False,
    )

    op.create_index(
        "ix_journeys_destination_gist",
        "journeys",
        ["destination"],
        unique=False,
        postgresql_using="gist",
    )

    op.create_index(
        "ix_journeys_origin_gist",
        "journeys",
        ["origin"],
        unique=False,
        postgresql_using="gist",
    )

    op.create_index(
        "ix_journeys_status",
        "journeys",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f("ix_journeys_user_id"),
        "journeys",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_journeys_user_id"),
        table_name="journeys",
    )

    op.drop_index(
        "ix_journeys_status",
        table_name="journeys",
    )

    op.drop_index(
        "ix_journeys_origin_gist",
        table_name="journeys",
        postgresql_using="gist",
    )

    op.drop_index(
        "ix_journeys_destination_gist",
        table_name="journeys",
        postgresql_using="gist",
    )

    op.drop_index(
        "ix_journeys_departure_time",
        table_name="journeys",
    )

    op.drop_table("journeys")