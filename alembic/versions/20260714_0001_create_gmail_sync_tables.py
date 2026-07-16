"""create Gmail OAuth and email synchronization tables

Revision ID: 20260714_0001
Revises:
Create Date: 2026-07-14 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260714_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria contas Google, states OAuth e mensagens com idempotência."""

    op.create_table(
        "google_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email_address", sa.String(length=320), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "scopes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_google_accounts")),
        sa.UniqueConstraint(
            "email_address",
            name=op.f("uq_google_accounts_email_address"),
        ),
    )
    op.create_table(
        "oauth_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauth_states")),
        sa.UniqueConstraint("state_hash", name=op.f("uq_oauth_states_state_hash")),
    )
    op.create_index(
        op.f("ix_oauth_states_expires_at"),
        "oauth_states",
        ["expires_at"],
        unique=False,
    )
    op.create_table(
        "email_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("google_account_id", sa.Uuid(), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=False),
        sa.Column("provider_thread_id", sa.String(length=255), nullable=False),
        sa.Column("sender", sa.String(length=998), nullable=False),
        sa.Column(
            "recipients",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=998), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processed', 'ignored')",
            name=op.f("ck_email_messages_email_message_status"),
        ),
        sa.ForeignKeyConstraint(
            ["google_account_id"],
            ["google_accounts.id"],
            name=op.f("fk_email_messages_google_account_id_google_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_messages")),
        sa.UniqueConstraint(
            "google_account_id",
            "provider_message_id",
            name="uq_email_messages_account_provider_message",
        ),
    )
    op.create_index(
        op.f("ix_email_messages_body_hash"),
        "email_messages",
        ["body_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_messages_google_account_id"),
        "email_messages",
        ["google_account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_messages_provider_thread_id"),
        "email_messages",
        ["provider_thread_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_messages_received_at"),
        "email_messages",
        ["received_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove as tabelas da Fase 2 na ordem segura."""

    op.drop_index(op.f("ix_email_messages_received_at"), table_name="email_messages")
    op.drop_index(
        op.f("ix_email_messages_provider_thread_id"),
        table_name="email_messages",
    )
    op.drop_index(
        op.f("ix_email_messages_google_account_id"),
        table_name="email_messages",
    )
    op.drop_index(op.f("ix_email_messages_body_hash"), table_name="email_messages")
    op.drop_table("email_messages")
    op.drop_index(op.f("ix_oauth_states_expires_at"), table_name="oauth_states")
    op.drop_table("oauth_states")
    op.drop_table("google_accounts")
