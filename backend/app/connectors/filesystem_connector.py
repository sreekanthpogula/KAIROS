from __future__ import annotations

from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, Field

from app.connectors.base import BaseConnector, ConnectorDocument, ConnectorError


class FilesystemConfig(BaseModel):
    root_path: str = Field(description="Directory to scan (recursively)")
    glob_pattern: str = Field(default="**/*", description="Glob pattern relative to root_path")
    max_files: int = Field(default=100, description="Safety cap on how many files to pull in one run")


class FilesystemConnector(BaseConnector):
    """Pulls every matching file from a local or mounted directory (a
    network share, a synced cloud-drive folder, a Docker volume — anything
    that shows up as a normal filesystem path)."""

    connector_type = "filesystem"
    display_name = "Local Filesystem"
    description = "Recursively scans a directory and ingests every matching file."
    direction = "pull"

    @classmethod
    def config_schema(cls) -> dict:
        return FilesystemConfig.model_json_schema()

    def list_documents(self, config: dict) -> Iterator[ConnectorDocument]:
        try:
            cfg = FilesystemConfig.model_validate(config)
        except Exception as exc:
            raise ConnectorError(f"Invalid filesystem connector config: {exc}") from exc

        root = Path(cfg.root_path)
        if not root.exists():
            raise ConnectorError(f"root_path does not exist: {cfg.root_path}")
        if not root.is_dir():
            raise ConnectorError(f"root_path is not a directory: {cfg.root_path}")

        count = 0
        for path in sorted(root.glob(cfg.glob_pattern)):
            if not path.is_file():
                continue
            if count >= cfg.max_files:
                break
            yield ConnectorDocument(
                filename=path.name,
                content=path.read_bytes(),
                source_uri=f"file://{path.resolve().as_posix()}",
                source_system="filesystem-connector",
                metadata={"relative_path": str(path.relative_to(root))},
            )
            count += 1
