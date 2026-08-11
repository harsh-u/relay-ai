"""add similarity and matched_question to decision_log

Revision ID: 23cb326a311d
Revises: 289ea9e6769c
Create Date: 2026-08-11 15:12:03.512211

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "23cb326a311d"
down_revision: str | Sequence[str] | None = "289ea9e6769c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("decision_log", sa.Column("similarity", sa.Float(), nullable=True))
    op.add_column("decision_log", sa.Column("matched_question", sa.Text(), nullable=True))
    # Reviewing a conversation's decision history filters on all three plus
    # orders by created_at - same hot-path-index pattern already applied to
    # conversation_messages.
    op.create_index(
        "ix_decision_log_scope_created_at",
        "decision_log",
        ["tenant_id", "business_id", "conversation_id", "created_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_decision_log_scope_created_at", table_name="decision_log")
    op.drop_column("decision_log", "matched_question")
    op.drop_column("decision_log", "similarity")
