"""Restaurant-scoped paths under ``data/toast/``."""

from __future__ import annotations

import os
from pathlib import Path

from pantry_engine.root import repo_root

TOAST_DATA_ROOT = repo_root() / "data" / "toast"


def location_slug(location_id: str | None = None) -> str:
    if location_id:
        return location_id.strip()
    return os.environ.get("PANTRY_DEFAULT_LOCATION_ID", "perilla").strip() or "perilla"


def xtrachef_dir(location_id: str | None = None) -> Path:
    return TOAST_DATA_ROOT / "xtraCHEF" / location_slug(location_id)


def pos_dir(location_id: str | None = None) -> Path:
    """Restaurant POS folder: ``data/toast/pos/{location_id}/``."""
    return TOAST_DATA_ROOT / "pos" / location_slug(location_id)


def pos_year_dir(year: int, location_id: str | None = None) -> Path:
    """Legacy POS folder: ``data/toast/pos/{year}/{location_id}/``."""
    return TOAST_DATA_ROOT / "pos" / str(year) / location_slug(location_id)
