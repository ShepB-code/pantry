from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Protocol

from pantry_engine.ingest.toast_sftp.config import ToastSftpConfig


class SftpDownloader(Protocol):
    def download(self, remote_path: str, local_path: Path) -> None:
        ...

    def list_business_dates(self, export_id: str) -> list[date]:
        ...


class ToastSftpClient:
    """Downloads files from Toast nightly export SFTP (AWS Transfer family)."""

    def __init__(self, config: ToastSftpConfig) -> None:
        self.config = config

    @property
    def export_id(self) -> str:
        return self.config.export_id

    def download(self, remote_path: str, local_path: Path) -> None:
        import paramiko

        local_path.parent.mkdir(parents=True, exist_ok=True)
        key = self._load_private_key()
        transport = paramiko.Transport((self.config.host, self.config.port))
        try:
            transport.connect(username=self.config.username, pkey=key)
            sftp = paramiko.SFTPClient.from_transport(transport)
            if sftp is None:
                raise RuntimeError("Failed to open SFTP session")
            try:
                sftp.get(remote_path, str(local_path))
            finally:
                sftp.close()
        finally:
            transport.close()

    def list_business_dates(self, export_id: str | None = None) -> list[date]:
        import paramiko

        export_id = export_id or self.config.export_id
        key = self._load_private_key()
        transport = paramiko.Transport((self.config.host, self.config.port))
        try:
            transport.connect(username=self.config.username, pkey=key)
            sftp = paramiko.SFTPClient.from_transport(transport)
            if sftp is None:
                raise RuntimeError("Failed to open SFTP session")
            try:
                names = sftp.listdir(export_id)
            finally:
                sftp.close()
        finally:
            transport.close()

        dates: list[date] = []
        for name in names:
            if len(name) == 8 and name.isdigit():
                dates.append(
                    date(int(name[0:4]), int(name[4:6]), int(name[6:8]))
                )
        return sorted(dates)

    def download_item_selection(self, business_date: date, local_path: Path) -> None:
        remote = self.config.remote_item_selection_path(
            business_date.strftime("%Y%m%d")
        )
        self.download(remote, local_path)

    def _load_private_key(self):
        import paramiko

        path = str(self.config.private_key_path)
        loaders = (
            paramiko.RSAKey.from_private_key_file,
            paramiko.ECDSAKey.from_private_key_file,
            paramiko.Ed25519Key.from_private_key_file,
        )
        last_error: Exception | None = None
        for loader in loaders:
            try:
                return loader(path)
            except Exception as exc:
                last_error = exc
                continue
        raise ValueError(
            f"Could not load SSH private key at {path}: {last_error}"
        ) from last_error


class LocalSftpDownloader:
    """Test double: reads from a local directory tree mimicking Toast SFTP layout."""

    def __init__(self, fixture_root: Path, export_id: str) -> None:
        self.fixture_root = fixture_root
        self._export_id = export_id

    @property
    def export_id(self) -> str:
        return self._export_id

    def download(self, remote_path: str, local_path: Path) -> None:
        source = self.fixture_root / remote_path
        if not source.is_file():
            raise FileNotFoundError(remote_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(source.read_bytes())

    def list_business_dates(self, export_id: str) -> list[date]:
        root = self.fixture_root / export_id
        if not root.is_dir():
            return []
        dates: list[date] = []
        for child in root.iterdir():
            if child.is_dir() and len(child.name) == 8 and child.name.isdigit():
                dates.append(
                    date(
                        int(child.name[0:4]),
                        int(child.name[4:6]),
                        int(child.name[6:8]),
                    )
                )
        return sorted(dates)

    def download_item_selection(self, business_date: date, local_path: Path) -> None:
        remote = (
            f"{self.export_id}/{business_date.strftime('%Y%m%d')}/"
            "ItemSelectionDetails.csv"
        )
        self.download(remote, local_path)
