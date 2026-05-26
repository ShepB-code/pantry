"""Add catalog_name to inventory_items (source system label).

Revision ID: 002
Revises: 001
Create Date: 2026-05-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inventory_items",
        sa.Column("catalog_name", sa.String(512), nullable=True),
    )
    op.add_column(
        "inventory_items",
        sa.Column("catalog_source", sa.String(32), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE inventory_items SET catalog_name = name, catalog_source = 'xtrachef' "
            "WHERE catalog_name IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("inventory_items", "catalog_source")
    op.drop_column("inventory_items", "catalog_name")
