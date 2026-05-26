from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pantry_engine.root import repo_root


@dataclass(frozen=True)
class IngestPaths:
    """Standard directories for file-based ingestion."""

    root: Path

    @classmethod
    def from_repo(cls, root: Path | None = None) -> IngestPaths:
        base = (root or repo_root()) / "data" / "ingest"
        return cls(root=base)

    @property
    def runs_db(self) -> Path:
        return self.root / "ingestion_runs.db"

    @property
    def toast_pos_inbox(self) -> Path:
        return self.root / "inbox" / "toast-pos"

    @property
    def toast_pos_archive(self) -> Path:
        return self.root / "archive" / "toast-pos"

    @property
    def toast_pos_failed(self) -> Path:
        return self.root / "failed" / "toast-pos"

    def toast_pos_canonical_dir(self, year: int) -> Path:
        """Where EDA and legacy loaders expect POS CSVs."""
        return repo_root() / "data" / "toast" / "pos" / str(year)

    def ensure_dirs(self) -> None:
        for path in (
            self.toast_pos_inbox,
            self.toast_pos_archive,
            self.toast_pos_failed,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def inbox_filename(self, business_date_iso: str) -> str:
        return f"ItemSelectionDetails_{business_date_iso}.csv"

    def canonical_filename(self, business_date_iso: str) -> str:
        return f"ItemSelectionDetails_{business_date_iso}.csv"
