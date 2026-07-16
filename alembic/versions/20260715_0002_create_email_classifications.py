"""create email classifications

Revision ID: 20260715_0002
Revises: 20260714_0001
Create Date: 2026-07-15 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260715_0002"
down_revision: str | None = "20260714_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_classifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("requires_reply", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("risk_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name=op.f("ck_email_classifications_confidence_range")),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'critical')", name=op.f("ck_email_classifications_classification_priority")),
        sa.ForeignKeyConstraint(["email_id"], ["email_messages.id"], name=op.f("fk_email_classifications_email_id_email_messages"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_classifications")),
        sa.UniqueConstraint("email_id", name=op.f("uq_email_classifications_email_id")),
    )
    op.create_index(op.f("ix_email_classifications_category"), "email_classifications", ["category"], unique=False)
    op.create_index(op.f("ix_email_classifications_priority"), "email_classifications", ["priority"], unique=False)
    op.create_index(op.f("ix_email_classifications_requires_reply"), "email_classifications", ["requires_reply"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_email_classifications_requires_reply"), table_name="email_classifications")
    op.drop_index(op.f("ix_email_classifications_priority"), table_name="email_classifications")
    op.drop_index(op.f("ix_email_classifications_category"), table_name="email_classifications")
    op.drop_table("email_classifications")
