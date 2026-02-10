"""Base class for all RDMA metric collectors."""

import abc
import logging
import time
from typing import Any

from rdma_monitor.utils.network_detector import RDMADevice

logger = logging.getLogger(__name__)


class BaseCollector(abc.ABC):
    """Abstract base for metric collectors.

    Subclasses must implement ``collect()`` which returns a dict of metrics.
    The dict is later serialized to JSON and exported to Prometheus.
    """

    name: str = "base"

    def __init__(self, devices: list[RDMADevice]):
        self.devices = devices

    @abc.abstractmethod
    def collect(self) -> dict[str, Any]:
        """Collect metrics and return a structured dict."""
        ...

    def safe_collect(self) -> dict[str, Any]:
        """Wrapper that catches exceptions so one collector cannot crash the
        whole monitor loop."""
        try:
            start = time.monotonic()
            data = self.collect()
            elapsed = time.monotonic() - start
            data["_collector"] = self.name
            data["_collect_time_ms"] = round(elapsed * 1000, 2)
            return data
        except Exception:
            logger.exception("Collector %s failed", self.name)
            return {"_collector": self.name, "_error": True}
