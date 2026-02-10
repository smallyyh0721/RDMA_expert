"""Main RDMA Monitor orchestrator.

Coordinates device discovery, collector scheduling, exporting, and
AI analysis in a single event loop.
"""

import json
import logging
import signal
import sys
import threading
import time
from typing import Any

from rdma_monitor.utils.config_loader import load_config
from rdma_monitor.utils.network_detector import discover_devices, RDMADevice
from rdma_monitor.collectors.base import BaseCollector
from rdma_monitor.collectors.performance import PerformanceCollector
from rdma_monitor.collectors.topology import TopologyCollector
from rdma_monitor.collectors.configuration import ConfigurationCollector
from rdma_monitor.collectors.congestion import CongestionCollector
from rdma_monitor.collectors.link_status import LinkStatusCollector
from rdma_monitor.exporters.prometheus_exporter import PrometheusExporter
from rdma_monitor.exporters.json_exporter import JsonExporter
from rdma_monitor.analysis.llm_analyzer import LLMAnalyzer
from rdma_monitor.analysis.dify_client import DifyClient

logger = logging.getLogger("rdma_monitor")


def _setup_logging(cfg: dict) -> None:
    general = cfg.get("general", {})
    level_str = general.get("log_level", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)
    log_file = general.get("log_file", "")

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


class RDMAMonitor:
    """Top-level monitor that ties everything together."""

    def __init__(self, config_path: str | None = None):
        self.cfg = load_config(config_path)
        _setup_logging(self.cfg)

        self._running = False
        self._devices: list[RDMADevice] = []
        self._collectors: list[BaseCollector] = []
        self._prometheus: PrometheusExporter | None = None
        self._json_exporter: JsonExporter | None = None
        self._llm: LLMAnalyzer | None = None
        self._dify: DifyClient | None = None

        # Timestamps for interval tracking
        self._last_snapshot_time: float = 0
        self._last_llm_time: float = 0
        self._last_dify_time: float = 0

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _discover(self) -> None:
        net_cfg = self.cfg.get("network", {})
        mode = net_cfg.get("mode", "auto")
        device_filter = net_cfg.get("devices", []) or None
        self._devices = discover_devices(force_mode=mode, device_filter=device_filter)
        if not self._devices:
            logger.warning(
                "No RDMA devices found. The monitor will start but "
                "collectors will produce empty data."
            )

    def _init_collectors(self) -> None:
        coll_cfg = self.cfg.get("collectors", {})
        mapping: list[tuple[str, type[BaseCollector]]] = [
            ("performance", PerformanceCollector),
            ("topology", TopologyCollector),
            ("configuration", ConfigurationCollector),
            ("congestion", CongestionCollector),
            ("link_status", LinkStatusCollector),
        ]
        for name, cls in mapping:
            if coll_cfg.get(name, {}).get("enabled", True):
                self._collectors.append(cls(self._devices))
                logger.info("Enabled collector: %s", name)

    def _init_prometheus(self) -> None:
        prom_cfg = self.cfg.get("prometheus", {})
        if not prom_cfg.get("enabled", True):
            return
        self._prometheus = PrometheusExporter(
            prefix=prom_cfg.get("metric_prefix", "rdma"),
            host=prom_cfg.get("host", "0.0.0.0"),
            port=prom_cfg.get("port", 9090),
        )
        self._prometheus.start()

    def _init_json_exporter(self) -> None:
        general = self.cfg.get("general", {})
        snapshot_dir = general.get("snapshot_dir", "./snapshots")
        self._json_exporter = JsonExporter(snapshot_dir=snapshot_dir)

    def _init_llm(self) -> None:
        llm_cfg = self.cfg.get("llm", {})
        if not llm_cfg.get("enabled", False):
            return
        self._llm = LLMAnalyzer(
            api_url=llm_cfg.get("api_url", "https://api.openai.com/v1/chat/completions"),
            api_key=llm_cfg.get("api_key", ""),
            model=llm_cfg.get("model", "gpt-4"),
            max_tokens=llm_cfg.get("max_tokens", 2048),
            system_prompt=llm_cfg.get("system_prompt", ""),
        )

    def _init_dify(self) -> None:
        dify_cfg = self.cfg.get("dify", {})
        if not dify_cfg.get("enabled", False):
            return
        self._dify = DifyClient(
            api_url=dify_cfg.get("api_url", "http://localhost/v1"),
            api_key=dify_cfg.get("api_key", ""),
            workflow_id=dify_cfg.get("workflow_id", ""),
            input_mapping=dify_cfg.get("input_mapping"),
        )

    # ------------------------------------------------------------------
    # Collection loop
    # ------------------------------------------------------------------

    def _collect_all(self) -> dict[str, Any]:
        """Run every enabled collector and merge results."""
        all_data: dict[str, Any] = {}
        for collector in self._collectors:
            data = collector.safe_collect()
            all_data[collector.name] = data
        return all_data

    def _maybe_save_snapshot(self, data: dict[str, Any], now: float) -> None:
        interval = self.cfg.get("general", {}).get("snapshot_interval", 30)
        if self._json_exporter and (now - self._last_snapshot_time) >= interval:
            self._json_exporter.save(data)
            self._json_exporter.cleanup()
            self._last_snapshot_time = now

    def _maybe_llm_analyze(self, data: dict[str, Any], now: float) -> None:
        interval = self.cfg.get("llm", {}).get("analysis_interval", 60)
        if self._llm and (now - self._last_llm_time) >= interval:
            # Run in a background thread to avoid blocking the main loop
            thread = threading.Thread(
                target=self._run_llm_analysis, args=(data,), daemon=True
            )
            thread.start()
            self._last_llm_time = now

    def _run_llm_analysis(self, data: dict[str, Any]) -> None:
        try:
            result = self._llm.analyze(data)  # type: ignore[union-attr]
            if result.get("success"):
                logger.info("LLM analysis result:\n%s", result.get("analysis", ""))
                # Save analysis alongside snapshots
                if self._json_exporter:
                    analysis_path = (
                        self._json_exporter.snapshot_dir / "latest_analysis.json"
                    )
                    with open(analysis_path, "w") as fh:
                        json.dump(result, fh, indent=2, default=str)
            else:
                logger.warning("LLM analysis failed: %s", result.get("error"))
        except Exception:
            logger.exception("LLM analysis thread error")

    def _maybe_push_dify(self, data: dict[str, Any], now: float) -> None:
        interval = self.cfg.get("dify", {}).get("push_interval", 60)
        if self._dify and (now - self._last_dify_time) >= interval:
            thread = threading.Thread(
                target=self._run_dify_push, args=(data,), daemon=True
            )
            thread.start()
            self._last_dify_time = now

    def _run_dify_push(self, data: dict[str, Any]) -> None:
        try:
            result = self._dify.push_to_workflow(data)  # type: ignore[union-attr]
            if result.get("success"):
                logger.info("Dify workflow triggered: %s", result.get("workflow_run_id"))
            else:
                logger.warning("Dify push failed: %s", result.get("error"))
        except Exception:
            logger.exception("Dify push thread error")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Initialize all subsystems and enter the main monitoring loop."""
        logger.info("Starting RDMA Network Monitor v1.0.0")

        self._discover()
        self._init_collectors()
        self._init_prometheus()
        self._init_json_exporter()
        self._init_llm()
        self._init_dify()

        self._running = True

        # Register signal handlers for graceful shutdown
        def _handle_signal(signum, frame):
            logger.info("Received signal %d, shutting down...", signum)
            self._running = False

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        poll_interval = self.cfg.get("general", {}).get("poll_interval", 10)
        logger.info("Entering main loop (poll every %ds)", poll_interval)

        while self._running:
            loop_start = time.monotonic()
            now = time.time()

            try:
                data = self._collect_all()

                # Export to Prometheus
                if self._prometheus:
                    self._prometheus.update_all(data)

                # JSON snapshot
                self._maybe_save_snapshot(data, now)

                # LLM analysis
                self._maybe_llm_analyze(data, now)

                # Dify push
                self._maybe_push_dify(data, now)

            except Exception:
                logger.exception("Error in main monitor loop")

            elapsed = time.monotonic() - loop_start
            sleep_time = max(0, poll_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

        logger.info("RDMA Monitor stopped.")

    def stop(self) -> None:
        self._running = False
