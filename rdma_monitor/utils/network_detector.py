"""Auto-detect RDMA network type (InfiniBand vs RoCE) and enumerate devices."""

import logging
import subprocess
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class NetworkType(Enum):
    INFINIBAND = "ib"
    ROCE = "roce"
    UNKNOWN = "unknown"


@dataclass
class RDMADevice:
    """Represents a single RDMA-capable device / port."""
    name: str                           # e.g. mlx5_0
    port: int = 1
    net_type: NetworkType = NetworkType.UNKNOWN
    netdev: str = ""                    # e.g. ib0, eth0, enp3s0f0
    state: str = ""                     # e.g. ACTIVE, DOWN
    phys_state: str = ""               # e.g. LinkUp
    rate: str = ""                      # e.g. 100 Gb/sec
    gid_count: int = 0
    extra: dict = field(default_factory=dict)


def _run(cmd: list[str], timeout: int = 10) -> str:
    """Run a subprocess and return stdout; return empty string on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except FileNotFoundError:
        logger.debug("Command not found: %s", cmd[0])
    except subprocess.TimeoutExpired:
        logger.warning("Command timed out: %s", " ".join(cmd))
    except Exception as exc:
        logger.warning("Command failed (%s): %s", " ".join(cmd), exc)
    return ""


def _detect_type_from_sysfs(device_name: str, port: int) -> NetworkType:
    """Read link_layer from /sys to determine IB vs Ethernet (RoCE)."""
    sysfs_path = Path(f"/sys/class/infiniband/{device_name}/ports/{port}/link_layer")
    try:
        layer = sysfs_path.read_text().strip().lower()
        if layer == "infiniband":
            return NetworkType.INFINIBAND
        if layer in ("ethernet", "eth"):
            return NetworkType.ROCE
    except (FileNotFoundError, PermissionError):
        pass
    return NetworkType.UNKNOWN


def _detect_type_from_ibstat(device_name: str) -> NetworkType:
    """Fallback: parse ibstat output to guess link type."""
    output = _run(["ibstat", device_name])
    if not output:
        return NetworkType.UNKNOWN
    if "Link layer: InfiniBand" in output:
        return NetworkType.INFINIBAND
    if "Link layer: Ethernet" in output:
        return NetworkType.ROCE
    # If ibstat works at all the device is IB-capable
    if "State:" in output:
        return NetworkType.INFINIBAND
    return NetworkType.UNKNOWN


def _parse_ibstat_device(device_name: str, port: int) -> dict:
    """Parse ibstat for a specific device and extract useful fields."""
    output = _run(["ibstat", device_name])
    info: dict = {}
    if not output:
        return info

    current_port: Optional[int] = None
    for line in output.splitlines():
        line = line.strip()
        m = re.match(r"Port\s+(\d+):", line)
        if m:
            current_port = int(m.group(1))
            continue
        if current_port == port or (current_port is None and port == 1):
            if line.startswith("State:"):
                info["state"] = line.split(":", 1)[1].strip()
            elif line.startswith("Physical state:"):
                info["phys_state"] = line.split(":", 1)[1].strip()
            elif line.startswith("Rate:"):
                info["rate"] = line.split(":", 1)[1].strip()
    return info


def _get_netdev_for_rdma(device_name: str, port: int) -> str:
    """Map an RDMA device/port to its Linux netdev name."""
    # Try rdma link show
    output = _run(["rdma", "link", "show"])
    if output:
        for line in output.splitlines():
            # e.g. "link mlx5_0/1 state ACTIVE physical_state LINK_UP netdev ib0"
            if f"{device_name}/{port}" in line:
                m = re.search(r"netdev\s+(\S+)", line)
                if m:
                    return m.group(1)
    # Fallback: sysfs
    ndev_path = Path(
        f"/sys/class/infiniband/{device_name}/ports/{port}/gid_attrs/ndevs/0"
    )
    try:
        return ndev_path.read_text().strip()
    except (FileNotFoundError, PermissionError):
        pass
    return ""


def discover_devices(force_mode: str = "auto",
                     device_filter: list[str] | None = None) -> list[RDMADevice]:
    """Discover RDMA devices on this host.

    Args:
        force_mode: "auto", "ib", or "roce".
        device_filter: If non-empty, only return devices whose names are in
                       this list.

    Returns:
        List of RDMADevice objects.
    """
    devices: list[RDMADevice] = []

    # Primary method: list devices via sysfs
    ib_class = Path("/sys/class/infiniband")
    dev_names: list[str] = []
    if ib_class.is_dir():
        dev_names = [d.name for d in ib_class.iterdir() if d.is_dir()]
    else:
        # Fallback: ibstat -l
        output = _run(["ibstat", "-l"])
        if output:
            dev_names = [n.strip() for n in output.splitlines() if n.strip()]

    if not dev_names:
        # Final fallback: rdma link show
        output = _run(["rdma", "link", "show"])
        if output:
            for line in output.splitlines():
                m = re.match(r"\s*link\s+(\S+)/", line)
                if m and m.group(1) not in dev_names:
                    dev_names.append(m.group(1))

    if device_filter:
        dev_names = [d for d in dev_names if d in device_filter]

    for dname in sorted(set(dev_names)):
        # Discover ports
        ports_dir = Path(f"/sys/class/infiniband/{dname}/ports")
        port_nums = [1]
        if ports_dir.is_dir():
            port_nums = sorted(
                int(p.name) for p in ports_dir.iterdir() if p.name.isdigit()
            )

        for port in port_nums:
            # Determine network type
            if force_mode == "ib":
                net_type = NetworkType.INFINIBAND
            elif force_mode == "roce":
                net_type = NetworkType.ROCE
            else:
                net_type = _detect_type_from_sysfs(dname, port)
                if net_type == NetworkType.UNKNOWN:
                    net_type = _detect_type_from_ibstat(dname)

            ibinfo = _parse_ibstat_device(dname, port)
            netdev = _get_netdev_for_rdma(dname, port)

            dev = RDMADevice(
                name=dname,
                port=port,
                net_type=net_type,
                netdev=netdev,
                state=ibinfo.get("state", ""),
                phys_state=ibinfo.get("phys_state", ""),
                rate=ibinfo.get("rate", ""),
            )
            devices.append(dev)
            logger.info(
                "Discovered %s/%d  type=%s  netdev=%s  state=%s  rate=%s",
                dname, port, net_type.value, netdev, dev.state, dev.rate,
            )

    if not devices:
        logger.warning("No RDMA devices discovered on this host.")
    return devices
