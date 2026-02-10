"""Prometheus exporter for RDMA metrics.

Flattens the nested metric dicts from collectors into Prometheus gauges
and serves them via an HTTP endpoint.
"""

import logging
import threading
from typing import Any

from prometheus_client import Gauge, start_http_server, CollectorRegistry

logger = logging.getLogger(__name__)


class PrometheusExporter:
    """Dynamically creates and updates Prometheus gauges from collector data."""

    def __init__(self, prefix: str = "rdma", host: str = "0.0.0.0", port: int = 9090):
        self.prefix = prefix
        self.host = host
        self.port = port
        self.registry = CollectorRegistry()
        self._gauges: dict[str, Gauge] = {}
        self._lock = threading.Lock()
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        start_http_server(self.port, addr=self.host, registry=self.registry)
        self._started = True
        logger.info("Prometheus exporter listening on %s:%d", self.host, self.port)

    def _get_or_create_gauge(self, metric_name: str, labels: list[str],
                              doc: str = "") -> Gauge:
        with self._lock:
            if metric_name not in self._gauges:
                self._gauges[metric_name] = Gauge(
                    metric_name,
                    doc or metric_name,
                    labels,
                    registry=self.registry,
                )
            return self._gauges[metric_name]

    def _flatten(self, data: dict, path: str = "",
                 labels: dict[str, str] | None = None,
                 result: list[tuple[str, dict[str, str], float]] | None = None
                 ) -> list[tuple[str, dict[str, str], float]]:
        """Recursively flatten a nested dict into (metric_name, labels, value) tuples."""
        if result is None:
            result = []
        if labels is None:
            labels = {}

        for key, value in data.items():
            # Skip internal keys
            if key.startswith("_"):
                continue

            current_path = f"{path}_{key}" if path else key

            if key == "devices" and isinstance(value, dict):
                for dev_key, dev_data in value.items():
                    if isinstance(dev_data, dict):
                        new_labels = {**labels, "device": dev_key}
                        self._flatten(dev_data, path, new_labels, result)
                continue

            if isinstance(value, dict):
                self._flatten(value, current_path, labels, result)
            elif isinstance(value, (int, float)):
                metric_name = f"{self.prefix}_{current_path}"
                # Sanitize metric name
                metric_name = metric_name.replace("/", "_").replace("-", "_")
                metric_name = metric_name.replace(".", "_").replace(" ", "_")
                result.append((metric_name, labels, float(value)))
            elif isinstance(value, list):
                # Export list lengths as metrics
                metric_name = f"{self.prefix}_{current_path}_count"
                metric_name = metric_name.replace("/", "_").replace("-", "_")
                result.append((metric_name, labels, float(len(value))))

        return result

    def update(self, collector_name: str, data: dict[str, Any]) -> None:
        """Update Prometheus metrics from a collector's output."""
        flat = self._flatten(data, path=collector_name)
        for metric_name, labels, value in flat:
            label_keys = sorted(labels.keys())
            try:
                gauge = self._get_or_create_gauge(metric_name, label_keys)
                if label_keys:
                    gauge.labels(**labels).set(value)
                else:
                    gauge.set(value)
            except Exception:
                logger.debug("Failed to export metric %s", metric_name, exc_info=True)

    def update_all(self, all_data: dict[str, dict[str, Any]]) -> None:
        """Update metrics from all collectors at once.

        Args:
            all_data: mapping of collector_name -> collector output dict
        """
        for collector_name, data in all_data.items():
            self.update(collector_name, data)
