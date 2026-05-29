"""Ensure ``pantry_eda`` (data_analysis notebooks lib) is importable."""

from __future__ import annotations

import sys
from pathlib import Path

from pantry_engine.root import repo_root


def ensure_pantry_eda_path() -> None:
    lib_path = repo_root() / "data_analysis" / "notebooks" / "lib"
    if str(lib_path) not in sys.path:
        sys.path.append(str(lib_path))
