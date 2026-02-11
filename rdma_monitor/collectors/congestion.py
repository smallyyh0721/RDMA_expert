"""Congestion monitoring collector for RDMA networks.

Tracks ECN counters, PFC frames, CNP packets, buffer usage, and
congestion-control parameters for both IB and RoCE.
"""

import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from rdma_monitor.collectors.base import BaseCollector
from rdma_monitor.utils.network_detector import RDMADevice, NetworkType

logger = logging.getLogger(__name__)


def _run(cmd: list[str], timeout: int = 10) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""


def _read_sysfs(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


# HW counters related to congestion (mlx5)
_CONGESTION_HW_COUNTERS = [
    "np_cnp_sent",
    "np_ecn_marked_roce_packets",
    "rp_cnp_handled",
    "rp_cnp_ignored",
    "rx_icrc_encapsulated",
    "out_of_sequence",
    "out_of_buffer",
    "packet_seq_err",
    "implied_nak_seq_err",
    "local_ack_timeout_err",
    "resp_local_length_error",
    "rnr_nak_retry_err",
    "req_cqe_error",
    "resp_cqe_error",
]

# Standard error counters related to congestion
_ERROR_COUNTERS = [
    "port_xmit_discards",
    "port_xmit_wait",
    "port_rcv_errors",
    "port_rcv_constraint_errors",
    "port_xmit_constraint_errors",
    "excessive_buffer_overrun_errors",
    "local_link_integrity_errors",
    "VL15_dropped",
    "symbol_error",
]


class CongestionCollector(BaseCollector):
    name = "congestion"

    def _read_hw_congestion_counters(self, dev: RDMADevice) -> dict[str, int]:
        hw_dir = Path(
            f"/sys/class/infiniband/{dev.name}/ports/{dev.port}/hw_counters"
        )
        counters: dict[str, int] = {}
        if not hw_dir.is_dir():
            return counters
        for name in _CONGESTION_HW_COUNTERS:
            val = _read_sysfs(hw_dir / name)
            if val is not None:
                try:
                    counters[name] = int(val)
                except ValueError:
                    pass
        return counters

    def _read_error_counters(self, dev: RDMADevice) -> dict[str, int]:
        cnt_dir = Path(
            f"/sys/class/infiniband/{dev.name}/ports/{dev.port}/counters"
        )
        counters: dict[str, int] = {}
        for name in _ERROR_COUNTERS:
            val = _read_sysfs(cnt_dir / name)
            if val is not None:
                try:
                    counters[name] = int(val)
                except ValueError:
                    pass
        return counters

    def _pfc_stats(self, dev: RDMADevice) -> dict[str, Any]:
        """Read PFC (Priority Flow Control) counters for RoCE."""
        if not dev.netdev:
            return {}
        output = _run(["ethtool", "-S", dev.netdev])
        if not output:
            return {}
        pfc: dict[str, int] = {}
        for line in output.splitlines():
            line = line.strip()
            if "pfc" in line.lower() or "pause" in line.lower() or "buffer" in line.lower():
                m = re.match(r"(\S+):\s+(\d+)", line)
                if m:
                    pfc[m.group(1)] = int(m.group(2))
        return pfc

    def _ecn_config(self, dev: RDMADevice) -> dict[str, str]:
        """Read ECN / DCQCN configuration from sysfs or mlnx_qos."""
        config: dict[str, str] = {}

        # Try mlnx_qos (Mellanox-specific)
        if dev.netdev:
            output = _run(["mlnx_qos", "-i", dev.netdev])
            if output:
                config["mlnx_qos"] = output[:2000]

        # Try reading ECN setting from tc
        if dev.netdev:
            output = _run(["tc", "-s", "qdisc", "show", "dev", dev.netdev])
            if output:
                config["tc_qdisc"] = output[:2000]

        return config

    def _ib_congestion(self) -> dict[str, Any]:
        """Read IB-specific congestion info via perfquery / vendstat."""
        info: dict[str, Any] = {}
        output = _run(["perfquery", "-x"])
        if output:
            for line in output.splitlines():
                m = re.match(r"(\w[\w\s]+\w)\.*:\s*(\d+)", line)
                if m:
                    key = m.group(1).strip().replace(" ", "_").lower()
                    if any(kw in key for kw in ("discard", "error", "drop",
                                                 "wait", "congestion", "buffer")):
                        info[key] = int(m.group(2))
        return info

    def collect(self) -> dict[str, Any]:
        result: dict[str, Any] = {"devices": {}}

        has_ib = any(d.net_type == NetworkType.INFINIBAND for d in self.devices)
        if has_ib:
            ib_cong = self._ib_congestion()
            if ib_cong:
                result["ib_fabric_congestion"] = ib_cong

        for dev in self.devices:
            key = f"{dev.name}/{dev.port}"
            dev_data: dict[str, Any] = {
                "hw_counters": self._read_hw_congestion_counters(dev),
                "error_counters": self._read_error_counters(dev),
            }

            if dev.net_type == NetworkType.ROCE:
                pfc = self._pfc_stats(dev)
                if pfc:
                    dev_data["pfc_stats"] = pfc
                ecn = self._ecn_config(dev)
                if ecn:
                    dev_data["ecn_config"] = ecn

            result["devices"][key] = dev_data

        return result
