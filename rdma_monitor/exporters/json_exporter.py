"""JSON snapshot exporter.

Periodically saves all collected metrics to timestamped JSON files.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JsonExporter:
    """Writes metric snapshots to JSON files on disk."""

    def __init__(self, snapshot_dir: str = "./snapshots"):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._latest_path = self.snapshot_dir / "latest.json"

    def save(self, data: dict[str, Any]) -> Path:
        """Save a snapshot and update the ``latest.json`` symlink/copy.

        Returns:
            Path to the written snapshot file.
        """
        ts = datetime.now(timezone.utc)
        filename = f"rdma_snapshot_{ts.strftime('%Y%m%dT%H%M%SZ')}.json"
        filepath = self.snapshot_dir / filename

        snapshot = {
            "timestamp": ts.isoformat(),
            "epoch": time.time(),
            "data": data,
        }

        with open(filepath, "w") as fh:
            json.dump(snapshot, fh, indent=2, default=str)

        # Overwrite latest.json for easy access
        with open(self._latest_path, "w") as fh:
            json.dump(snapshot, fh, indent=2, default=str)

        logger.info("Saved snapshot to %s", filepath)
        return filepath

    def get_latest(self) -> dict[str, Any] | None:
        """Read and return the latest snapshot, or None."""
        if not self._latest_path.is_file():
            return None
        with open(self._latest_path, "r") as fh:
            return json.load(fh)

    def cleanup(self, max_files: int = 1000) -> int:
        """Remove oldest snapshots if count exceeds *max_files*.

        Returns number of files removed.
        """
        files = sorted(
            self.snapshot_dir.glob("rdma_snapshot_*.json"),
            key=lambda p: p.stat().st_mtime,
        )
        removed = 0
        while len(files) > max_files:
            oldest = files.pop(0)
            oldest.unlink()
            removed += 1
        if removed:
            logger.info("Cleaned up %d old snapshots", removed)
        return removed
