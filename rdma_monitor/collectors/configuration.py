"""Configuration collector for RDMA devices.

Reads device parameters, firmware info, and kernel module settings.
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


class ConfigurationCollector(BaseCollector):
    name = "configuration"

    def _read_fw_info(self, dev: RDMADevice) -> dict[str, str]:
        """Read firmware version and board ID from sysfs."""
        info: dict[str, str] = {}
        base = Path(f"/sys/class/infiniband/{dev.name}")
        for attr in ("fw_ver", "board_id", "hca_type", "hw_rev", "node_guid",
                      "sys_image_guid", "node_desc"):
            p = base / attr
            try:
                info[attr] = p.read_text().strip()
            except (FileNotFoundError, PermissionError):
                pass
        return info

    def _read_port_attrs(self, dev: RDMADevice) -> dict[str, str]:
        """Read per-port attributes from sysfs."""
        attrs: dict[str, str] = {}
        base = Path(f"/sys/class/infiniband/{dev.name}/ports/{dev.port}")
        for attr in ("state", "phys_state", "rate", "link_layer", "cap_mask"):
            p = base / attr
            try:
                attrs[attr] = p.read_text().strip()
            except (FileNotFoundError, PermissionError):
                pass
        return attrs

    def _mlxconfig(self, dev: RDMADevice) -> dict[str, str]:
        """Read Mellanox device configuration via mlxconfig."""
        output = _run(["mlxconfig", "-d", dev.name, "query"])
        if not output:
            return {}
        config: dict[str, str] = {}
        for line in output.splitlines():
            m = re.match(r"\s*(\w[\w_]*)\s+([\w/\-\.]+)", line)
            if m:
                config[m.group(1)] = m.group(2)
        return config

    def _kernel_module_params(self) -> dict[str, dict[str, str]]:
        """Read mlx5_core and rdma_cm module parameters."""
        params: dict[str, dict[str, str]] = {}
        for module in ("mlx5_core", "rdma_cm", "ib_core", "rdma_ucm"):
            mod_dir = Path(f"/sys/module/{module}/parameters")
            if not mod_dir.is_dir():
                continue
            mod_params: dict[str, str] = {}
            for p in mod_dir.iterdir():
                try:
                    mod_params[p.name] = p.read_text().strip()
                except (PermissionError, OSError):
                    pass
            if mod_params:
                params[module] = mod_params
        return params

    def _rdma_system(self) -> dict[str, str]:
        """Read rdma system netns mode and other global settings."""
        info: dict[str, str] = {}
        output = _run(["rdma", "system", "show"])
        if output:
            info["rdma_system"] = output
        return info

    def _ethtool_config(self, dev: RDMADevice) -> dict[str, Any]:
        """Read ethtool ring/coalesce/features for RoCE netdevs."""
        if not dev.netdev:
            return {}
        config: dict[str, Any] = {}

        for flag, section in [("-g", "ring"), ("-c", "coalesce"), ("-k", "offload")]:
            output = _run(["ethtool", flag, dev.netdev])
            if output:
                section_data: dict[str, str] = {}
                for line in output.splitlines():
                    m = re.match(r"(\S[\S\s]*\S)\s*:\s*(.+)", line)
                    if m:
                        section_data[m.group(1).strip()] = m.group(2).strip()
                if section_data:
                    config[section] = section_data

        return config

    def collect(self) -> dict[str, Any]:
        result: dict[str, Any] = {"devices": {}}
        result["kernel_modules"] = self._kernel_module_params()
        result.update(self._rdma_system())

        for dev in self.devices:
            key = f"{dev.name}/{dev.port}"
            dev_cfg: dict[str, Any] = {
                "firmware": self._read_fw_info(dev),
                "port_attrs": self._read_port_attrs(dev),
            }
            mlx = self._mlxconfig(dev)
            if mlx:
                dev_cfg["mlxconfig"] = mlx
            if dev.net_type == NetworkType.ROCE:
                eth_cfg = self._ethtool_config(dev)
                if eth_cfg:
                    dev_cfg["ethtool"] = eth_cfg
            result["devices"][key] = dev_cfg

        return result
