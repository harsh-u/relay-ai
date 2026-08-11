"""add indexes for conversation message retention and hot-path reads

Revision ID: 289ea9e6769c
Revises: d4811736457c
Create Date: 2026-08-11 12:49:41.011854

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "289ea9e6769c"
down_revision: str | Sequence[str] | None = "d4811736457c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Every read is scoped to one (tenant_id, business_id, conversation_id)
    # and orders by created_at - previously served by three separate
    # single-column indexes, not one covering index.
    op.create_index(
        "ix_conversation_messages_scope_created_at",
        "conversation_messages",
        ["tenant_id", "business_id", "conversation_id", "created_at"],
    )
    # Retention purges filter on created_at alone, across every row.
    op.create_index(
        "ix_conversation_messages_created_at",
        "conversation_messages",
        ["created_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_conversation_messages_created_at", table_name="conversation_messages")
    op.drop_index("ix_conversation_messages_scope_created_at", table_name="conversation_messages")
