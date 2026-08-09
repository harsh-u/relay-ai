"""use clock_timestamp for tenant and business created_at

Revision ID: d4811736457c
Revises: d2935664026c
Create Date: 2026-08-09 19:56:31.395971

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4811736457c"
down_revision: str | Sequence[str] | None = "d2935664026c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # now() is frozen for the duration of a transaction, so two rows
    # inserted in the same transaction get an identical created_at,
    # breaking "newest first" ordering. clock_timestamp() advances on
    # every call, matching answered_questions.created_at.
    op.alter_column(
        "tenants",
        "created_at",
        server_default=sa.text("clock_timestamp()"),
    )
    op.alter_column(
        "businesses",
        "created_at",
        server_default=sa.text("clock_timestamp()"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "businesses",
        "created_at",
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "tenants",
        "created_at",
        server_default=sa.text("now()"),
    )
