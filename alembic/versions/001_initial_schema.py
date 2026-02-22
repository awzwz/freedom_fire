"""Initial schema — all FIRE tables.

Revision ID: 001
Revises: None
Create Date: 2025-02-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Offices
    op.create_table(
        "offices",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
    )

    # Managers
    op.create_table(
        "managers",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("position", sa.String(50), nullable=False),
        sa.Column(
            "office_id", sa.Integer, sa.ForeignKey("offices.id"), nullable=False
        ),
        sa.Column(
            "skills", ARRAY(sa.String(20)), nullable=False, server_default="{}"
        ),
        sa.Column("current_load", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("idx_managers_office", "managers", ["office_id"])

    # Tickets
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("guid", sa.String(100), unique=True, nullable=False),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("birth_date", sa.Date, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("attachments", sa.String(500), nullable=True),
        sa.Column("segment", sa.String(20), nullable=False),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("region", sa.String(200), nullable=True),
        sa.Column("city", sa.String(200), nullable=True),
        sa.Column("street", sa.String(200), nullable=True),
        sa.Column("building", sa.String(50), nullable=True),
        sa.Column("client_lat", sa.Float, nullable=True),
        sa.Column("client_lon", sa.Float, nullable=True),
        sa.Column(
            "geo_status", sa.String(20), nullable=False, server_default="pending"
        ),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("idx_tickets_segment", "tickets", ["segment"])
    op.create_index("idx_tickets_city", "tickets", ["city"])

    # Ticket Analytics
    op.create_table(
        "ticket_analytics",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "ticket_id",
            sa.Integer,
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("ticket_type", sa.String(50), nullable=False),
        sa.Column("sentiment", sa.String(20), nullable=False),
        sa.Column("priority_score", sa.Integer, nullable=False),
        sa.Column("language", sa.String(5), nullable=False, server_default="RU"),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("llm_model", sa.String(50), nullable=True),
        sa.Column(
            "processed_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_analytics_type", "ticket_analytics", ["ticket_type"])
    op.create_index("idx_analytics_language", "ticket_analytics", ["language"])

    # Assignments
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "ticket_id",
            sa.Integer,
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "manager_id",
            sa.Integer,
            sa.ForeignKey("managers.id"),
            nullable=False,
        ),
        sa.Column(
            "office_id",
            sa.Integer,
            sa.ForeignKey("offices.id"),
            nullable=False,
        ),
        sa.Column("distance_km", sa.Float, nullable=True),
        sa.Column("assignment_reason", sa.Text, nullable=True),
        sa.Column("fallback_used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "assigned_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_assignments_manager", "assignments", ["manager_id"])
    op.create_index("idx_assignments_office", "assignments", ["office_id"])

    # Round Robin State
    op.create_table(
        "round_robin_state",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("rr_key", sa.String(500), unique=True, nullable=False),
        sa.Column("counter", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("round_robin_state")
    op.drop_table("assignments")
    op.drop_table("ticket_analytics")
    op.drop_table("tickets")
    op.drop_table("managers")
    op.drop_table("offices")
