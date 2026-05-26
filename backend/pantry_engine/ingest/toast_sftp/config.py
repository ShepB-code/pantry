from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToastSftpConfig:
    """Credentials for Toast automated nightly data exports (SFTP).

    See: https://doc.toasttab.com/doc/platformguide/downloading_data_export_files.html
    """

    host: str
    port: int
    username: str
    export_id: str
    private_key_path: Path
    item_selection_filename: str = "ItemSelectionDetails.csv"

    @classmethod
    def from_env(cls) -> ToastSftpConfig:
        local_root = os.environ.get("TOAST_SFTP_LOCAL_ROOT", "").strip()
        export_id = os.environ.get("TOAST_SFTP_EXPORT_ID", "local_dev").strip()

        if local_root:
            return cls(
                host="local",
                port=0,
                username="local",
                export_id=export_id,
                private_key_path=Path(local_root).expanduser().resolve(),
            )

        missing: list[str] = []
        host = os.environ.get("TOAST_SFTP_HOST", "").strip()
        username = os.environ.get("TOAST_SFTP_USERNAME", "").strip()
        export_id = os.environ.get("TOAST_SFTP_EXPORT_ID", "").strip()
        key_path = os.environ.get("TOAST_SFTP_PRIVATE_KEY_PATH", "").strip()

        if not host:
            missing.append("TOAST_SFTP_HOST")
        if not username:
            missing.append("TOAST_SFTP_USERNAME")
        if not export_id:
            missing.append("TOAST_SFTP_EXPORT_ID")
        if not key_path:
            missing.append("TOAST_SFTP_PRIVATE_KEY_PATH")

        if missing:
            raise ValueError(
                "Toast SFTP is not configured. Set: "
                + ", ".join(missing)
                + " — or TOAST_SFTP_LOCAL_ROOT for local simulation. See backend/.env.example."
            )

        port = int(os.environ.get("TOAST_SFTP_PORT", "22"))
        path = Path(key_path).expanduser()
        if not path.is_file():
            raise ValueError(f"TOAST_SFTP_PRIVATE_KEY_PATH does not exist: {path}")

        return cls(
            host=host,
            port=port,
            username=username,
            export_id=export_id,
            private_key_path=path,
        )

    def remote_item_selection_path(self, business_date_yyyymmdd: str) -> str:
        """SFTP path: ``{export_id}/{YYYYMMDD}/ItemSelectionDetails.csv``."""
        return (
            f"{self.export_id}/{business_date_yyyymmdd}/"
            f"{self.item_selection_filename}"
        )
