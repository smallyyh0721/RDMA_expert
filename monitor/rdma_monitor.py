#!/usr/bin/env python3
"""
RDMA Network Monitor - Comprehensive monitoring for RDMA environments.

Collects:
  1. RDMA device status (ibstat, rdma link)
  2. RDMA error counters (ibqueryerrors, perfquery)
  3. Network interface counters (ethtool, /sys/class/net)
  4. RDMA fabric topology (ibnetdiscover, iblinkinfo)
  5. QoS and PFC counters
  6. PCIe and hardware health

Output: JSON report written to --output path (default: stdout).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s: {cmd}"
    except Exception as e:
        return -1, "", str(e)


# ---------------------------------------------------------------------------
# 1. RDMA Device Status
# ---------------------------------------------------------------------------

def collect_rdma_device_status():
    """Collect RDMA device and port status via ibstat and rdma link."""
    results = {}

    # ibstat
    rc, out, err = run_cmd("ibstat")
    if rc == 0:
        results["ibstat_raw"] = out
        results["ibstat"] = parse_ibstat(out)
    else:
        results["ibstat_error"] = err or "ibstat not available"

    # rdma link show
    rc, out, err = run_cmd("rdma link show")
    if rc == 0:
        results["rdma_link_raw"] = out
    else:
        results["rdma_link_error"] = err or "rdma command not available"

    # rdma dev show
    rc, out, err = run_cmd("rdma dev show")
    if rc == 0:
        results["rdma_dev_raw"] = out

    # ibv_devinfo
    rc, out, err = run_cmd("ibv_devinfo")
    if rc == 0:
        results["ibv_devinfo_raw"] = out

    return results


def parse_ibstat(text):
    """Parse ibstat output into structured data."""
    devices = []
    current_ca = None
    current_port = None

    for line in text.splitlines():
        line_s = line.strip()
        if line_s.startswith("CA '"):
            if current_ca and current_port:
                current_ca["ports"].append(current_port)
            if current_ca:
                devices.append(current_ca)
            ca_name = line_s.split("'")[1]
            current_ca = {"name": ca_name, "properties": {}, "ports": []}
            current_port = None
        elif line_s.startswith("Port ") and line_s.endswith(":"):
            if current_port and current_ca:
                current_ca["ports"].append(current_port)
            port_num = line_s.split()[1].rstrip(":")
            current_port = {"port_number": port_num, "properties": {}}
        elif ":" in line_s:
            key, _, val = line_s.partition(":")
            key = key.strip()
            val = val.strip()
            if current_port is not None:
                current_port["properties"][key] = val
            elif current_ca is not None:
                current_ca["properties"][key] = val

    if current_ca and current_port:
        current_ca["ports"].append(current_port)
    if current_ca:
        devices.append(current_ca)

    return devices


# ---------------------------------------------------------------------------
# 2. RDMA Error & Performance Counters
# ---------------------------------------------------------------------------

def collect_rdma_counters():
    """Collect RDMA error and performance counters."""
    results = {}

    # ibqueryerrors - fabric-wide error counters
    rc, out, err = run_cmd("ibqueryerrors --details", timeout=60)
    if rc == 0:
        results["ibqueryerrors_raw"] = out
        results["ibqueryerrors_has_errors"] = bool(out.strip())
    else:
        results["ibqueryerrors_error"] = err or "ibqueryerrors not available"

    # perfquery - local port performance counters
    rc, out, err = run_cmd("perfquery --all")
    if rc == 0:
        results["perfquery_raw"] = out
        results["perfquery"] = parse_perfquery(out)
    else:
        results["perfquery_error"] = err or "perfquery not available"

    # Extended counters
    rc, out, err = run_cmd("perfquery -x --all")
    if rc == 0:
        results["perfquery_extended_raw"] = out

    return results


def parse_perfquery(text):
    """Parse perfquery output into key-value pairs."""
    counters = {}
    for line in text.splitlines():
        line_s = line.strip()
        if not line_s or line_s.startswith("#"):
            continue
        parts = line_s.split(":", 1)
        if len(parts) == 2:
            key = parts[0].strip().rstrip(".")
            val = parts[1].strip()
            counters[key] = val
    return counters


# ---------------------------------------------------------------------------
# 3. Network Interface Counters
# ---------------------------------------------------------------------------

def collect_network_counters():
    """Collect network interface counters from sysfs, ethtool, ip."""
    results = {}

    # Discover RDMA-capable interfaces
    rdma_devices = discover_rdma_netdevs()
    results["rdma_netdevs"] = rdma_devices

    for netdev in rdma_devices:
        dev_stats = {}

        # sysfs statistics
        sysfs_stats = read_sysfs_counters(netdev)
        if sysfs_stats:
            dev_stats["sysfs_counters"] = sysfs_stats

        # ethtool -S (NIC-level counters)
        rc, out, err = run_cmd(f"ethtool -S {netdev}")
        if rc == 0:
            dev_stats["ethtool_stats"] = parse_ethtool_stats(out)

        # ethtool -i (driver info)
        rc, out, err = run_cmd(f"ethtool -i {netdev}")
        if rc == 0:
            dev_stats["driver_info"] = parse_kv_output(out)

        # ethtool (link settings)
        rc, out, err = run_cmd(f"ethtool {netdev}")
        if rc == 0:
            dev_stats["link_settings"] = parse_kv_output(out)

        # ip -s link show
        rc, out, err = run_cmd(f"ip -s link show {netdev}")
        if rc == 0:
            dev_stats["ip_stats_raw"] = out

        # PFC counters (mlnx_qos if available)
        rc, out, err = run_cmd(f"mlnx_qos -i {netdev} --show")
        if rc == 0:
            dev_stats["qos_config_raw"] = out

        results[netdev] = dev_stats

    return results


def discover_rdma_netdevs():
    """Discover network interfaces associated with RDMA devices."""
    netdevs = []

    # Method 1: rdma link show
    rc, out, err = run_cmd("rdma link show")
    if rc == 0:
        for line in out.splitlines():
            m = re.search(r'netdev\s+(\S+)', line)
            if m:
                netdevs.append(m.group(1))

    # Method 2: scan sysfs for mlx5 devices
    if not netdevs:
        rc, out, err = run_cmd(
            "ls -d /sys/class/net/*/device/infiniband 2>/dev/null"
        )
        if rc == 0:
            for path in out.splitlines():
                parts = path.split("/")
                if len(parts) >= 5:
                    netdevs.append(parts[4])

    # Method 3: fallback to all non-loopback interfaces
    if not netdevs:
        sysnet = Path("/sys/class/net")
        if sysnet.exists():
            for d in sysnet.iterdir():
                if d.name != "lo":
                    netdevs.append(d.name)

    return sorted(set(netdevs))


def read_sysfs_counters(netdev):
    """Read counters from /sys/class/net/<dev>/statistics/."""
    stats_dir = Path(f"/sys/class/net/{netdev}/statistics")
    if not stats_dir.exists():
        return None
    counters = {}
    for f in stats_dir.iterdir():
        try:
            counters[f.name] = int(f.read_text().strip())
        except (ValueError, PermissionError):
            pass
    return counters


def parse_ethtool_stats(text):
    """Parse ethtool -S output into dict."""
    stats = {}
    for line in text.splitlines():
        line_s = line.strip()
        if ":" in line_s:
            key, _, val = line_s.partition(":")
            key = key.strip()
            val = val.strip()
            try:
                stats[key] = int(val)
            except ValueError:
                stats[key] = val
    return stats


def parse_kv_output(text):
    """Generic key: value parser."""
    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key:
                result[key] = val
    return result


# ---------------------------------------------------------------------------
# 4. RDMA Fabric Topology
# ---------------------------------------------------------------------------

def collect_rdma_topology():
    """Collect RDMA fabric topology for later diagnosis."""
    results = {}

    # ibnetdiscover - full fabric topology
    rc, out, err = run_cmd("ibnetdiscover", timeout=120)
    if rc == 0:
        results["ibnetdiscover_raw"] = out
        results["ibnetdiscover"] = parse_ibnetdiscover(out)
    else:
        results["ibnetdiscover_error"] = err or "ibnetdiscover not available"

    # iblinkinfo - link speed/width/state for all links
    rc, out, err = run_cmd("iblinkinfo", timeout=60)
    if rc == 0:
        results["iblinkinfo_raw"] = out
    else:
        results["iblinkinfo_error"] = err or "iblinkinfo not available"

    # show_gids - GID table
    rc, out, err = run_cmd("show_gids 2>/dev/null || ibv_devinfo -v 2>/dev/null")
    if rc == 0:
        results["gid_info_raw"] = out

    # Subnet manager info
    rc, out, err = run_cmd("saquery")
    if rc == 0:
        results["saquery_raw"] = out
    else:
        results["saquery_error"] = err or "saquery not available"

    # sminfo
    rc, out, err = run_cmd("sminfo")
    if rc == 0:
        results["sminfo_raw"] = out

    return results


def parse_ibnetdiscover(text):
    """Parse ibnetdiscover output into node and link lists."""
    nodes = []
    links = []
    for line in text.splitlines():
        line_s = line.strip()
        if not line_s or line_s.startswith("#"):
            continue
        # Switch/CA lines
        if line_s.startswith("Switch") or line_s.startswith("Ca"):
            nodes.append(line_s)
        # Connection lines contain port numbers and GUIDs
        elif re.match(r'^\[', line_s):
            links.append(line_s)
    return {"node_count": len(nodes), "link_count": len(links),
            "nodes": nodes, "links": links}


# ---------------------------------------------------------------------------
# 5. Hardware Health (PCIe, temperature, firmware)
# ---------------------------------------------------------------------------

def collect_hardware_health():
    """Collect hardware health indicators."""
    results = {}

    # mlx5 devices in sysfs
    rc, out, err = run_cmd(
        "ls /sys/class/infiniband/ 2>/dev/null"
    )
    if rc == 0 and out:
        devices = out.split()
        results["ib_devices"] = devices

        for dev in devices:
            dev_info = {}

            # Firmware version
            fw_path = f"/sys/class/infiniband/{dev}/fw_ver"
            if os.path.exists(fw_path):
                try:
                    dev_info["fw_ver"] = Path(fw_path).read_text().strip()
                except PermissionError:
                    pass

            # Board ID
            board_path = f"/sys/class/infiniband/{dev}/board_id"
            if os.path.exists(board_path):
                try:
                    dev_info["board_id"] = Path(board_path).read_text().strip()
                except PermissionError:
                    pass

            # HCA type
            hca_path = f"/sys/class/infiniband/{dev}/hca_type"
            if os.path.exists(hca_path):
                try:
                    dev_info["hca_type"] = Path(hca_path).read_text().strip()
                except PermissionError:
                    pass

            # PCIe info via lspci
            rc2, out2, _ = run_cmd(
                f"cat /sys/class/infiniband/{dev}/device/uevent 2>/dev/null"
            )
            if rc2 == 0:
                dev_info["uevent"] = parse_kv_output(
                    out2.replace("=", ": ")
                )

            # mst status (Mellanox Software Tools)
            rc2, out2, _ = run_cmd(f"mst status 2>/dev/null")
            if rc2 == 0:
                dev_info["mst_status"] = out2

            results[dev] = dev_info

    # dmesg for recent mlx5 errors
    rc, out, err = run_cmd(
        "dmesg | grep -i 'mlx5\\|rdma\\|infiniband' | tail -50"
    )
    if rc == 0:
        results["dmesg_rdma"] = out

    return results


# ---------------------------------------------------------------------------
# 6. System Context
# ---------------------------------------------------------------------------

def collect_system_context():
    """Collect system-level context relevant to RDMA."""
    results = {}

    # Kernel version
    rc, out, _ = run_cmd("uname -r")
    if rc == 0:
        results["kernel"] = out

    # OFED version
    rc, out, _ = run_cmd("ofed_info -s 2>/dev/null")
    if rc == 0:
        results["ofed_version"] = out

    # Loaded RDMA kernel modules
    rc, out, _ = run_cmd("lsmod | grep -E 'mlx|rdma|ib_'")
    if rc == 0:
        results["rdma_modules"] = out

    # NUMA topology
    rc, out, _ = run_cmd("numactl --hardware 2>/dev/null")
    if rc == 0:
        results["numa_topology"] = out

    # IRQ affinity for mlx devices
    rc, out, _ = run_cmd(
        "grep mlx /proc/interrupts 2>/dev/null | head -20"
    )
    if rc == 0:
        results["mlx_interrupts"] = out

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_full_collection():
    """Run all collectors and return a unified report."""
    report = {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hostname": os.uname().nodename,
            "collector_version": "1.0.0",
        },
        "system_context": collect_system_context(),
        "rdma_device_status": collect_rdma_device_status(),
        "rdma_counters": collect_rdma_counters(),
        "network_counters": collect_network_counters(),
        "rdma_topology": collect_rdma_topology(),
        "hardware_health": collect_hardware_health(),
    }
    return report


def main():
    parser = argparse.ArgumentParser(
        description="RDMA Network Monitor - collect counters, topology, and health data"
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--sections", default="all",
        help=(
            "Comma-separated list of sections to collect: "
            "device,counters,network,topology,hardware,system (default: all)"
        ),
    )
    parser.add_argument(
        "--interval", type=int, default=0,
        help="Continuous monitoring interval in seconds (0 = one-shot)"
    )
    parser.add_argument(
        "--count", type=int, default=0,
        help="Number of collection rounds (0 = infinite when interval > 0)"
    )
    args = parser.parse_args()

    sections = set(args.sections.split(",")) if args.sections != "all" else {
        "device", "counters", "network", "topology", "hardware", "system"
    }

    iteration = 0
    while True:
        report = {"metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hostname": os.uname().nodename,
            "collector_version": "1.0.0",
            "iteration": iteration,
        }}

        if "system" in sections:
            report["system_context"] = collect_system_context()
        if "device" in sections:
            report["rdma_device_status"] = collect_rdma_device_status()
        if "counters" in sections:
            report["rdma_counters"] = collect_rdma_counters()
        if "network" in sections:
            report["network_counters"] = collect_network_counters()
        if "topology" in sections:
            report["rdma_topology"] = collect_rdma_topology()
        if "hardware" in sections:
            report["hardware_health"] = collect_hardware_health()

        output = json.dumps(report, indent=2, default=str)

        if args.output:
            out_path = Path(args.output)
            if args.interval > 0:
                stem = out_path.stem
                suffix = out_path.suffix or ".json"
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                final_path = out_path.parent / f"{stem}_{ts}{suffix}"
            else:
                final_path = out_path
            final_path.parent.mkdir(parents=True, exist_ok=True)
            final_path.write_text(output)
            print(f"Report written to {final_path}", file=sys.stderr)
        else:
            print(output)

        iteration += 1
        if args.interval <= 0:
            break
        if 0 < args.count <= iteration:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
