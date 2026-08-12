"""add owner_user_id to tenants

Revision ID: b5d6cc39e5bf
Revises: 7715c376e007
Create Date: 2026-08-12 16:41:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5d6cc39e5bf"
down_revision: str | Sequence[str] | None = "7715c376e007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("tenants", sa.Column("owner_user_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_tenants_owner_user_id"), "tenants", ["owner_user_id"], unique=False)
    op.create_foreign_key(
        "fk_tenants_owner_user_id_users",
        "tenants",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_tenants_owner_user_id_users", "tenants", type_="foreignkey")
    op.drop_index(op.f("ix_tenants_owner_user_id"), table_name="tenants")
    op.drop_column("tenants", "owner_user_id")
