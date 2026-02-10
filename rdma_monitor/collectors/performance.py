"""Performance metrics collector for RDMA devices.

Reads hardware counters from sysfs and perfquery to report throughput,
packet rates, and error counters.
"""

import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from rdma_monitor.collectors.base import BaseCollector
from rdma_monitor.utils.network_detector import RDMADevice, NetworkType

logger = logging.getLogger(__name__)

# Counters available under /sys/class/infiniband/<dev>/ports/<port>/counters/
_PERF_COUNTERS = [
    "port_xmit_data",
    "port_rcv_data",
    "port_xmit_packets",
    "port_rcv_packets",
    "port_unicast_xmit_packets",
    "port_unicast_rcv_packets",
    "port_multicast_xmit_packets",
    "port_multicast_rcv_packets",
]

_HW_COUNTERS = [
    "rx_write_requests",
    "rx_read_requests",
    "rx_atomic_requests",
    "out_of_sequence",
    "duplicate_request",
    "rx_icrc_encapsulated",
    "np_cnp_sent",
    "np_ecn_marked_roce_packets",
    "rp_cnp_handled",
    "rp_cnp_ignored",
]


def _read_sysfs_counter(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (FileNotFoundError, PermissionError, ValueError):
        return None


def _run(cmd: list[str], timeout: int = 10) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""


class PerformanceCollector(BaseCollector):
    name = "performance"

    def __init__(self, devices: list[RDMADevice]):
        super().__init__(devices)
        self._prev_counters: dict[str, dict[str, int]] = {}
        self._prev_ts: float = 0

    def _read_counters(self, dev: RDMADevice) -> dict[str, int | None]:
        base = Path(f"/sys/class/infiniband/{dev.name}/ports/{dev.port}")
        counters: dict[str, int | None] = {}

        # Standard counters
        for c in _PERF_COUNTERS:
            counters[c] = _read_sysfs_counter(base / "counters" / c)

        # HW counters (may not exist on all cards)
        hw_dir = base / "hw_counters"
        if hw_dir.is_dir():
            for c in _HW_COUNTERS:
                counters[c] = _read_sysfs_counter(hw_dir / c)

        return counters

    def _compute_rates(self, key: str, current: dict[str, int | None],
                       elapsed: float) -> dict[str, float]:
        rates: dict[str, float] = {}
        prev = self._prev_counters.get(key, {})
        if not prev or elapsed <= 0:
            return rates
        for counter_name, cur_val in current.items():
            if cur_val is None:
                continue
            prev_val = prev.get(counter_name)
            if prev_val is None:
                continue
            delta = cur_val - prev_val
            if delta < 0:
                # Counter wrapped
                delta = cur_val
            rates[f"{counter_name}_per_sec"] = round(delta / elapsed, 2)
        return rates

    def _perfquery(self, dev: RDMADevice) -> dict[str, Any]:
        """Run perfquery for extended counters (IB only)."""
        if dev.net_type != NetworkType.INFINIBAND:
            return {}
        output = _run(["perfquery", "-x", "-d", dev.name, "-P", str(dev.port)])
        if not output:
            return {}
        result: dict[str, Any] = {}
        for line in output.splitlines():
            m = re.match(r"(\w[\w\s]+\w)\.*:\s*(\d+)", line)
            if m:
                key = m.group(1).strip().replace(" ", "_").lower()
                result[key] = int(m.group(2))
        return result

    def _ethtool_stats(self, dev: RDMADevice) -> dict[str, Any]:
        """Read ethtool -S stats for RoCE devices."""
        if dev.net_type != NetworkType.ROCE or not dev.netdev:
            return {}
        output = _run(["ethtool", "-S", dev.netdev])
        if not output:
            return {}
        stats: dict[str, Any] = {}
        for line in output.splitlines():
            m = re.match(r"\s+(\S+):\s+(\d+)", line)
            if m:
                stats[m.group(1)] = int(m.group(2))
        return stats

    def collect(self) -> dict[str, Any]:
        now = time.monotonic()
        elapsed = now - self._prev_ts if self._prev_ts > 0 else 0
        result: dict[str, Any] = {"devices": {}}

        for dev in self.devices:
            key = f"{dev.name}/{dev.port}"
            counters = self._read_counters(dev)
            rates = self._compute_rates(key, {k: v for k, v in counters.items() if v is not None}, elapsed)

            dev_data: dict[str, Any] = {
                "counters": {k: v for k, v in counters.items() if v is not None},
                "rates": rates,
            }

            # Type-specific extended stats
            if dev.net_type == NetworkType.INFINIBAND:
                pq = self._perfquery(dev)
                if pq:
                    dev_data["perfquery"] = pq
            elif dev.net_type == NetworkType.ROCE:
                es = self._ethtool_stats(dev)
                if es:
                    dev_data["ethtool_stats"] = es

            result["devices"][key] = dev_data

            # Store for next rate computation
            self._prev_counters[key] = {
                k: v for k, v in counters.items() if v is not None
            }

        self._prev_ts = now
        return result
