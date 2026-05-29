"""Current MVP schema — inventory, menu, recipes, POS sales, quick count, ingestion.

Revision ID: 001
Revises:
Create Date: 2026-05-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
    )
    op.create_table(
        "inventory_items",
        sa.Column("location_id", sa.String(64), sa.ForeignKey("locations.id"), primary_key=True),
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("name_source", sa.String(32)),
        sa.Column("catalog_name", sa.String(512)),
        sa.Column("catalog_source", sa.String(32)),
        sa.Column("category", sa.String(128)),
        sa.Column("unit", sa.String(32)),
        sa.Column("vendor_name", sa.String(256)),
        sa.Column("on_hand", sa.Float(), nullable=False, server_default="0"),
        sa.Column("par_level", sa.Float()),
        sa.Column("last_count_source", sa.String(32)),
        sa.Column("last_counted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "menu_items",
        sa.Column("location_id", sa.String(64), sa.ForeignKey("locations.id"), primary_key=True),
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("category", sa.String(128)),
        sa.Column("menu_group", sa.String(128)),
        sa.Column("direct_inventory_item_id", sa.String(128)),
        sa.Column("direct_qty_per_serving", sa.Float()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["location_id", "direct_inventory_item_id"],
            ["inventory_items.location_id", "inventory_items.id"],
            name="fk_menu_items_direct_inventory",
        ),
    )
    op.create_table(
        "recipe_lines",
        sa.Column("location_id", sa.String(64), primary_key=True),
        sa.Column("menu_item_id", sa.String(128), primary_key=True),
        sa.Column("inventory_item_id", sa.String(128), primary_key=True),
        sa.Column("qty_per_serving", sa.Float(), nullable=False),
        sa.Column("waste_factor", sa.Float(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["location_id", "menu_item_id"],
            ["menu_items.location_id", "menu_items.id"],
        ),
        sa.ForeignKeyConstraint(
            ["location_id", "inventory_item_id"],
            ["inventory_items.location_id", "inventory_items.id"],
        ),
        sa.UniqueConstraint(
            "location_id", "menu_item_id", "inventory_item_id", name="uq_recipe_line"
        ),
    )
    op.create_table(
        "pos_sales_daily",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("location_id", sa.String(64), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("menu_item_id", sa.String(128), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["location_id", "menu_item_id"],
            ["menu_items.location_id", "menu_items.id"],
        ),
        sa.UniqueConstraint(
            "location_id", "business_date", "menu_item_id", name="uq_pos_sales_daily"
        ),
    )
    op.create_table(
        "quick_count_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("location_id", sa.String(64), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("item_count", sa.Integer()),
        sa.Column("submitted_count", sa.Integer()),
        sa.UniqueConstraint("location_id", "session_date", name="uq_quick_count_session"),
    )
    op.create_table(
        "quick_count_lines",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("quick_count_sessions.id"), nullable=False),
        sa.Column("location_id", sa.String(64), nullable=False),
        sa.Column("inventory_item_id", sa.String(128), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("expected", sa.Float(), nullable=False),
        sa.Column("actual", sa.Float(), nullable=False),
        sa.Column("flags", sa.Text()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["location_id", "inventory_item_id"],
            ["inventory_items.location_id", "inventory_items.id"],
        ),
        sa.UniqueConstraint("session_id", "inventory_item_id", name="uq_quick_count_line"),
    )
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("location_id", sa.String(64), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("filename", sa.String(512)),
        sa.Column("file_sha256", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("row_count", sa.Integer()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "location_id", "source", "business_date", name="uq_ingestion_run"
        ),
    )


def downgrade() -> None:
    op.drop_table("ingestion_runs")
    op.drop_table("quick_count_lines")
    op.drop_table("quick_count_sessions")
    op.drop_table("pos_sales_daily")
    op.drop_table("recipe_lines")
    op.drop_table("menu_items")
    op.drop_table("inventory_items")
    op.drop_table("locations")
