"""Link status collector for RDMA devices.

Monitors physical link state, speed negotiation, error rates, cable info,
and link flap detection.
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


class LinkStatusCollector(BaseCollector):
    name = "link_status"

    def __init__(self, devices: list[RDMADevice]):
        super().__init__(devices)
        # Track previous states for flap detection
        self._prev_states: dict[str, str] = {}
        self._flap_counts: dict[str, int] = {}

    def _read_link_state(self, dev: RDMADevice) -> dict[str, str]:
        """Read link state, physical state, and speed from sysfs."""
        base = Path(f"/sys/class/infiniband/{dev.name}/ports/{dev.port}")
        info: dict[str, str] = {}
        for attr in ("state", "phys_state", "rate", "link_layer"):
            val = _read_sysfs(base / attr)
            if val is not None:
                info[attr] = val
        return info

    def _check_link_flap(self, key: str, current_state: str) -> bool:
        """Return True if the link has changed state since last check."""
        prev = self._prev_states.get(key)
        self._prev_states[key] = current_state
        if prev is not None and prev != current_state:
            self._flap_counts[key] = self._flap_counts.get(key, 0) + 1
            return True
        return False

    def _ibstatus_info(self, dev: RDMADevice) -> dict[str, str]:
        """Parse ibstatus output for a device."""
        output = _run(["ibstatus", f"{dev.name}:{dev.port - 1}"])
        if not output:
            output = _run(["ibstatus", dev.name])
        if not output:
            return {}
        info: dict[str, str] = {}
        for line in output.splitlines():
            m = re.match(r"\s*([\w\s]+\w)\s*:\s*(.+)", line)
            if m:
                key = m.group(1).strip().replace(" ", "_").lower()
                info[key] = m.group(2).strip()
        return info

    def _cable_info(self, dev: RDMADevice) -> dict[str, str]:
        """Read cable/transceiver info via mlxcable or ethtool."""
        info: dict[str, str] = {}

        # Try mlxcable (Mellanox)
        output = _run(["mlxcable", "-d", dev.name])
        if output:
            for line in output.splitlines():
                m = re.match(r"\s*([\w\s]+\w)\s*:\s*(.+)", line)
                if m:
                    info[m.group(1).strip()] = m.group(2).strip()
            return info

        # Fallback: ethtool module info (RoCE)
        if dev.netdev:
            output = _run(["ethtool", "-m", dev.netdev])
            if output:
                for line in output.splitlines():
                    m = re.match(r"\s*([\w\s/]+\w)\s*:\s*(.+)", line)
                    if m:
                        info[m.group(1).strip()] = m.group(2).strip()

        return info

    def _symbol_ber_errors(self, dev: RDMADevice) -> dict[str, int]:
        """Read symbol error and BER-related counters."""
        base = Path(f"/sys/class/infiniband/{dev.name}/ports/{dev.port}")
        counters: dict[str, int] = {}
        for name in ("symbol_error", "link_error_recovery", "link_downed",
                      "port_rcv_errors", "port_rcv_remote_physical_errors",
                      "local_link_integrity_errors"):
            val = _read_sysfs(base / "counters" / name)
            if val is not None:
                try:
                    counters[name] = int(val)
                except ValueError:
                    pass
        return counters

    def _netdev_carrier(self, dev: RDMADevice) -> dict[str, str]:
        """Check Linux netdev carrier state."""
        if not dev.netdev:
            return {}
        info: dict[str, str] = {}
        carrier = _read_sysfs(Path(f"/sys/class/net/{dev.netdev}/carrier"))
        if carrier is not None:
            info["carrier"] = "up" if carrier == "1" else "down"
        operstate = _read_sysfs(Path(f"/sys/class/net/{dev.netdev}/operstate"))
        if operstate is not None:
            info["operstate"] = operstate
        speed = _read_sysfs(Path(f"/sys/class/net/{dev.netdev}/speed"))
        if speed is not None:
            info["speed_mbps"] = speed
        mtu = _read_sysfs(Path(f"/sys/class/net/{dev.netdev}/mtu"))
        if mtu is not None:
            info["mtu"] = mtu
        return info

    def collect(self) -> dict[str, Any]:
        result: dict[str, Any] = {"devices": {}}

        for dev in self.devices:
            key = f"{dev.name}/{dev.port}"
            link_state = self._read_link_state(dev)
            current_state = link_state.get("state", "unknown")
            flapped = self._check_link_flap(key, current_state)

            dev_data: dict[str, Any] = {
                "link_state": link_state,
                "link_flap_detected": flapped,
                "total_flap_count": self._flap_counts.get(key, 0),
                "error_counters": self._symbol_ber_errors(dev),
            }

            ibst = self._ibstatus_info(dev)
            if ibst:
                dev_data["ibstatus"] = ibst

            cable = self._cable_info(dev)
            if cable:
                dev_data["cable_info"] = cable

            if dev.net_type == NetworkType.ROCE:
                netdev_info = self._netdev_carrier(dev)
                if netdev_info:
                    dev_data["netdev"] = netdev_info

            result["devices"][key] = dev_data

        return result
