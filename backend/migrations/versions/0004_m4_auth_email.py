"""email verifications, deliveries, and verified_at

Revision ID: 0004_m4_auth_email
Revises: 0003_m3_notifications
Create Date: 2026-08-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_m4_auth_email"
down_revision: Union[str, None] = "0003_m3_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE users SET email_verified_at = created_at WHERE is_verified IS TRUE AND email_verified_at IS NULL"
    )

    op.create_table(
        "email_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("otp_hash", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(40), nullable=False, server_default="REGISTRATION"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_ip", sa.String(45), nullable=True),
        sa.Column("send_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_email_verifications_email_purpose", "email_verifications", ["email", "purpose"])

    op.create_table(
        "email_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email_type", sa.String(80), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="QUEUED"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
    )
    op.create_index("ix_email_deliveries_status", "email_deliveries", ["status"])
    op.create_index("uq_email_deliveries_idempotency", "email_deliveries", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_email_deliveries_idempotency", table_name="email_deliveries")
    op.drop_index("ix_email_deliveries_status", table_name="email_deliveries")
    op.drop_table("email_deliveries")
    op.drop_index("ix_email_verifications_email_purpose", table_name="email_verifications")
    op.drop_table("email_verifications")
    op.drop_column("users", "email_verified_at")
