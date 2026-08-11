"""add source_conversation_id to answered_questions

Revision ID: c9be39d31433
Revises: 23cb326a311d
Create Date: 2026-08-11 16:04:22.884716

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9be39d31433"
down_revision: str | Sequence[str] | None = "23cb326a311d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "answered_questions",
        sa.Column("source_conversation_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("answered_questions", "source_conversation_id")
