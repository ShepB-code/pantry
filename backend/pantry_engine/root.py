from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Pantry repository root (parent of ``backend/``)."""
    override = os.environ.get("PANTRY_REPO_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]
