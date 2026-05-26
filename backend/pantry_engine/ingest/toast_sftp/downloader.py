from __future__ import annotations

import os
from pathlib import Path

from pantry_engine.ingest.toast_sftp.client import LocalSftpDownloader, ToastSftpClient
from pantry_engine.ingest.toast_sftp.config import ToastSftpConfig


def get_toast_downloader(config: ToastSftpConfig):
    """Real SFTP client, or local folder tree when ``TOAST_SFTP_LOCAL_ROOT`` is set."""
    local_root = os.environ.get("TOAST_SFTP_LOCAL_ROOT", "").strip()
    if local_root:
        root = Path(local_root).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"TOAST_SFTP_LOCAL_ROOT is not a directory: {root}")
        return LocalSftpDownloader(root, config.export_id)
    return ToastSftpClient(config)
