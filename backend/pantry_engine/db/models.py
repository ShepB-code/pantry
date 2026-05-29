from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class LocationRecord(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)


class InventoryItemRecord(Base):
    """Catalog (xtraCHEF) + operational state per location."""

    __tablename__ = "inventory_items"

    location_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("locations.id"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    name_source: Mapped[str | None] = mapped_column(String(32))
    catalog_name: Mapped[str | None] = mapped_column(String(512))
    catalog_source: Mapped[str | None] = mapped_column(String(32))
    category: Mapped[str | None] = mapped_column(String(128))
    unit: Mapped[str | None] = mapped_column(String(32))
    vendor_name: Mapped[str | None] = mapped_column(String(256))
    on_hand: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    par_level: Mapped[float | None] = mapped_column(Float)
    last_count_source: Mapped[str | None] = mapped_column(String(32))
    last_counted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MenuItemRecord(Base):
    __tablename__ = "menu_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["location_id", "direct_inventory_item_id"],
            ["inventory_items.location_id", "inventory_items.id"],
            name="fk_menu_items_direct_inventory",
        ),
    )

    location_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("locations.id"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str | None] = mapped_column(String(128))
    menu_group: Mapped[str | None] = mapped_column(String(128))
    direct_inventory_item_id: Mapped[str | None] = mapped_column(String(128))
    direct_qty_per_serving: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecipeLineRecord(Base):
    __tablename__ = "recipe_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["location_id", "menu_item_id"],
            ["menu_items.location_id", "menu_items.id"],
        ),
        ForeignKeyConstraint(
            ["location_id", "inventory_item_id"],
            ["inventory_items.location_id", "inventory_items.id"],
        ),
        UniqueConstraint(
            "location_id",
            "menu_item_id",
            "inventory_item_id",
            name="uq_recipe_line",
        ),
    )

    location_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    menu_item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    inventory_item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    qty_per_serving: Mapped[float] = mapped_column(Float, nullable=False)
    waste_factor: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class PosSalesDailyRecord(Base):
    __tablename__ = "pos_sales_daily"
    __table_args__ = (
        ForeignKeyConstraint(
            ["location_id", "menu_item_id"],
            ["menu_items.location_id", "menu_items.id"],
        ),
        UniqueConstraint(
            "location_id",
            "business_date",
            "menu_item_id",
            name="uq_pos_sales_daily",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[str] = mapped_column(String(64), ForeignKey("locations.id"))
    business_date: Mapped[date] = mapped_column(Date, nullable=False)
    menu_item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuickCountSessionRecord(Base):
    __tablename__ = "quick_count_sessions"
    __table_args__ = (
        UniqueConstraint("location_id", "session_date", name="uq_quick_count_session"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[str] = mapped_column(String(64), ForeignKey("locations.id"))
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    item_count: Mapped[int | None] = mapped_column(Integer)
    submitted_count: Mapped[int | None] = mapped_column(Integer)

    lines: Mapped[list[QuickCountLineRecord]] = relationship(back_populates="session")


class QuickCountLineRecord(Base):
    __tablename__ = "quick_count_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["location_id", "inventory_item_id"],
            ["inventory_items.location_id", "inventory_items.id"],
        ),
        UniqueConstraint("session_id", "inventory_item_id", name="uq_quick_count_line"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quick_count_sessions.id"), nullable=False
    )
    location_id: Mapped[str] = mapped_column(String(64), nullable=False)
    inventory_item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    expected: Mapped[float] = mapped_column(Float, nullable=False)
    actual: Mapped[float] = mapped_column(Float, nullable=False)
    flags: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session: Mapped[QuickCountSessionRecord] = relationship(back_populates="lines")


class IngestionRunRecord(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "source",
            "business_date",
            name="uq_ingestion_run",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[str] = mapped_column(String(64), ForeignKey("locations.id"))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    business_date: Mapped[date] = mapped_column(Date, nullable=False)
    filename: Mapped[str | None] = mapped_column(String(512))
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
