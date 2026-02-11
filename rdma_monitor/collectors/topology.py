"""Topology collector for RDMA networks.

Discovers switch connectivity, LID/GID tables, and subnet layout.
"""

import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from rdma_monitor.collectors.base import BaseCollector
from rdma_monitor.utils.network_detector import RDMADevice, NetworkType

logger = logging.getLogger(__name__)


def _run(cmd: list[str], timeout: int = 30) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""


class TopologyCollector(BaseCollector):
    name = "topology"

    def _collect_ib_topology(self) -> dict[str, Any]:
        """Collect IB fabric topology using iblinkinfo / ibnetdiscover."""
        topo: dict[str, Any] = {}

        # ibnetdiscover
        output = _run(["ibnetdiscover"])
        if output:
            switches: list[str] = []
            hcas: list[str] = []
            for line in output.splitlines():
                if line.startswith("Switch"):
                    switches.append(line.strip())
                elif line.startswith("Ca"):
                    hcas.append(line.strip())
            topo["switches_count"] = len(switches)
            topo["hcas_count"] = len(hcas)
            topo["switches"] = switches[:50]   # cap output size
            topo["hcas"] = hcas[:50]

        # iblinkinfo (connection map)
        output = _run(["iblinkinfo"])
        if output:
            links: list[dict[str, str]] = []
            for line in output.splitlines():
                line = line.strip()
                if not line:
                    continue
                links.append({"raw": line[:200]})
            topo["links_count"] = len(links)
            topo["links_sample"] = links[:30]

        # SM info
        output = _run(["sminfo"])
        if output:
            topo["subnet_manager"] = output

        return topo

    def _collect_roce_topology(self) -> dict[str, Any]:
        """Collect RoCE topology — GID table, DCQCN settings, neighbors."""
        topo: dict[str, Any] = {}

        # Show rdma devices and their links
        output = _run(["rdma", "link", "show"])
        if output:
            topo["rdma_links"] = output.splitlines()

        return topo

    def _collect_gid_table(self, dev: RDMADevice) -> list[dict[str, str]]:
        """Read GID table for a device/port."""
        gids: list[dict[str, str]] = []
        gid_dir = Path(f"/sys/class/infiniband/{dev.name}/ports/{dev.port}/gids")
        if not gid_dir.is_dir():
            # Fallback: rdma resource show cm_id
            return gids
        for entry in sorted(gid_dir.iterdir(), key=lambda p: p.name):
            if not entry.name.isdigit():
                continue
            try:
                gid_val = entry.read_text().strip()
                if gid_val and gid_val != "0000:0000:0000:0000:0000:0000:0000:0000":
                    gid_type_path = Path(
                        f"/sys/class/infiniband/{dev.name}/ports/{dev.port}"
                        f"/gid_attrs/types/{entry.name}"
                    )
                    gid_type = ""
                    try:
                        gid_type = gid_type_path.read_text().strip()
                    except (FileNotFoundError, PermissionError):
                        pass
                    gids.append({
                        "index": entry.name,
                        "gid": gid_val,
                        "type": gid_type,
                    })
            except (PermissionError, OSError):
                pass
        return gids

    def _collect_lid_info(self, dev: RDMADevice) -> dict[str, Any]:
        """Read LID information for IB devices."""
        info: dict[str, Any] = {}
        base = Path(f"/sys/class/infiniband/{dev.name}/ports/{dev.port}")
        for attr in ("lid", "sm_lid", "sm_sl"):
            p = base / attr
            try:
                info[attr] = p.read_text().strip()
            except (FileNotFoundError, PermissionError):
                pass
        return info

    def _collect_pkey_table(self, dev: RDMADevice) -> list[str]:
        """Read partition key table."""
        pkeys: list[str] = []
        pkey_dir = Path(f"/sys/class/infiniband/{dev.name}/ports/{dev.port}/pkeys")
        if not pkey_dir.is_dir():
            return pkeys
        for entry in sorted(pkey_dir.iterdir(), key=lambda p: p.name):
            try:
                val = entry.read_text().strip()
                if val and val != "0x0000":
                    pkeys.append(val)
            except (PermissionError, OSError):
                pass
        return pkeys

    def collect(self) -> dict[str, Any]:
        result: dict[str, Any] = {"devices": {}}

        has_ib = any(d.net_type == NetworkType.INFINIBAND for d in self.devices)
        has_roce = any(d.net_type == NetworkType.ROCE for d in self.devices)

        if has_ib:
            result["ib_fabric"] = self._collect_ib_topology()
        if has_roce:
            result["roce_fabric"] = self._collect_roce_topology()

        for dev in self.devices:
            key = f"{dev.name}/{dev.port}"
            dev_topo: dict[str, Any] = {
                "gid_table": self._collect_gid_table(dev),
            }
            if dev.net_type == NetworkType.INFINIBAND:
                dev_topo["lid_info"] = self._collect_lid_info(dev)
            dev_topo["pkeys"] = self._collect_pkey_table(dev)
            result["devices"][key] = dev_topo

        return result
