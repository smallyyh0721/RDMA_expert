---
title: "Linux Networking Stack for RDMA"
category: web_content
tags: [linux, networking, rdma, mlx5, devlink, sysfs, configuration]
---

# Linux Networking Stack for RDMA

## 1. RDMA Subsystem in Linux

### 1.1 Key sysfs Paths
```bash
# RDMA devices
/sys/class/infiniband/              # All RDMA devices (mlx5_0, mlx5_1, ...)
/sys/class/infiniband/mlx5_0/
├── board_id
├── fw_ver                          # Firmware version
├── hca_type                        # HCA type string
├── hw_rev                          # Hardware revision
├── node_desc                       # Node description
├── node_guid                       # Node GUID
├── node_type                       # CA or Switch
├── sys_image_guid
└── ports/
    └── 1/
        ├── cap_mask               # Capability mask
        ├── gid_attrs/             # GID attributes
        ├── gids/                  # GID table entries
        │   ├── 0                  # Link-local GID
        │   ├── 1                  # RoCE v2 IPv4 GID
        │   └── ...
        ├── hw_counters/           # Hardware counters
        │   ├── duplicate_request
        │   ├── implied_nak_seq_err
        │   ├── local_ack_timeout_err
        │   ├── out_of_buffer
        │   ├── out_of_sequence
        │   ├── packet_seq_err
        │   └── resp_local_length_error
        ├── lid                    # Local ID (IB)
        ├── link_layer             # InfiniBand or Ethernet
        ├── phys_state             # Physical state
        ├── pkeys/                 # Partition key table
        ├── rate                   # Port rate
        ├── sm_lid                 # SM LID
        ├── sm_sl                  # SM service level
        └── state                  # Port state

# Network devices
/sys/class/net/eth0/
├── device/
│   ├── numa_node                  # NUMA node
│   ├── local_cpulist              # Local CPU list
│   ├── sriov_numvfs               # Current VF count
│   └── sriov_totalvfs             # Max VF count
├── mtu
├── speed
├── operstate
└── statistics/
```

### 1.2 rdma Tool (iproute2)
```bash
# List RDMA devices
rdma dev show

# Show RDMA links
rdma link show

# Show resources (QPs, CQs, MRs, PDs)
rdma resource show

# Detailed QP info
rdma resource show qp

# Show statistics
rdma statistic show

# Show RDMA namespaces
rdma system show netns

# Set netns mode
rdma system set netns shared    # All namespaces see all devices
rdma system set netns exclusive # Each namespace gets own devices
```

## 2. ethtool for RDMA NICs

```bash
# Driver and firmware info
ethtool -i eth0
# driver: mlx5_core
# version: 24.01-0.3.3
# firmware-version: 22.37.1014

# Link status
ethtool eth0

# All statistics (includes RDMA counters)
ethtool -S eth0

# Key RDMA-related counters:
ethtool -S eth0 | grep -E "rx_vport_rdma|tx_vport_rdma"   # RDMA traffic
ethtool -S eth0 | grep -E "roce"                           # RoCE specific
ethtool -S eth0 | grep -E "pfc"                            # PFC frames
ethtool -S eth0 | grep -E "ecn|cnp"                        # ECN/CNP
ethtool -S eth0 | grep -E "out_of_buffer|discard|drop"     # Drops

# Module/transceiver info
ethtool --module-info eth0

# FEC status
ethtool --show-fec eth0

# Ring buffer sizes
ethtool -g eth0

# Interrupt coalescing
ethtool -c eth0

# Flow steering rules
ethtool -n eth0
ethtool -N eth0 flow-type udp4 dst-port 4791 action 3  # Steer RoCE
```

## 3. devlink (Device Management)

```bash
# Show devices
devlink dev show

# Device info
devlink dev info pci/0000:3b:00.0

# Health reporters
devlink health show pci/0000:3b:00.0
devlink health diagnose pci/0000:3b:00.0 reporter fw
devlink health diagnose pci/0000:3b:00.0 reporter fw_fatal

# eSwitch mode (for SR-IOV switchdev)
devlink dev eswitch show pci/0000:3b:00.0
devlink dev eswitch set pci/0000:3b:00.0 mode switchdev

# Device parameters
devlink dev param show pci/0000:3b:00.0
devlink dev param set pci/0000:3b:00.0 name flow_steering_mode \
    value "smfs" cmode runtime

# Port management
devlink port show
devlink port function show pci/0000:3b:00.0/1  # VF representor
```

## 4. tc (Traffic Control) for RDMA Offload

```bash
# Add ingress qdisc
tc qdisc add dev eth0 ingress

# Add flower classifier with hardware offload
tc filter add dev eth0 protocol ip parent ffff: \
    flower dst_ip 192.168.1.0/24 ip_proto udp dst_port 4791 \
    action mirred egress redirect dev eth1 \
    skip_sw   # skip_sw = offload to hardware

# Check offloaded filters
tc filter show dev eth0 ingress
tc -s filter show dev eth0 ingress  # with stats

# Hardware offload statistics
tc -s -d filter show dev eth0 ingress
```

## 5. System Configuration for RDMA

### 5.1 Huge Pages
```bash
# 2MB huge pages
echo 4096 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
# Persistent: add to /etc/sysctl.conf
vm.nr_hugepages = 4096

# 1GB huge pages (boot-time only)
# Kernel cmdline: hugepagesz=1G hugepages=16
```

### 5.2 Memory Locking
```bash
# /etc/security/limits.conf
*    soft    memlock    unlimited
*    hard    memlock    unlimited
```

### 5.3 IRQ Affinity
```bash
# MLNX_OFED script
set_irq_affinity.sh eth0           # Auto-detect local CPUs
set_irq_affinity_cpulist.sh 0-15 eth0  # Specific CPUs

# Manual
echo 1 > /proc/irq/123/smp_affinity_list  # Pin IRQ 123 to CPU 1
```

### 5.4 CPU Governor
```bash
# Set performance governor
cpupower frequency-set -g performance
# Or:
echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### 5.5 Kernel Parameters
```bash
# /etc/sysctl.conf for RDMA workloads
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.rmem_default = 16777216
net.core.wmem_default = 16777216
net.core.netdev_max_backlog = 250000
vm.zone_reclaim_mode = 0
kernel.numa_balancing = 0
```

## 6. mlx5 Driver Architecture

```
User Space:
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Application  │  │  DPDK PMD    │  │  libfabric   │
│ (libibverbs) │  │  (mlx5)      │  │  (mlx5 prov) │
├──────────────┤  └──────┬───────┘  └──────┬───────┘
│ libmlx5      │         │                 │
│ (user prov)  │         │                 │
└──────┬───────┘         │                 │
       │                 │                 │
═══════╪═════════════════╪═════════════════╪═══════ (kernel boundary)
       │                 │                 │
┌──────┴───────┐         │                 │
│ ib_uverbs    │         │                 │
│ (char device)│         │                 │
├──────────────┤         │                 │
│ mlx5_ib      │    ┌────┴────┐            │
│ (IB driver)  │    │ (uio/   │            │
├──────────────┤    │  mmap)  │            │
│ mlx5_core    │────┘         │            │
│ (core driver)│──────────────┘            │
├──────────────┤                           │
│ mlx5_en      │                           │
│ (net driver) │                           │
└──────┬───────┘                           │
       │                                   │
       ├── mlx5_flow_steering              │
       ├── mlx5_eswitch                    │
       ├── mlx5_devlink                    │
       └── mlx5_pci                        │
```

## 7. Useful Commands Quick Reference

| Task | Command |
|------|---------|
| List RDMA devices | `rdma dev show` or `ibv_devices` |
| Device details | `ibv_devinfo -d mlx5_0` |
| Port state | `ibstat` or `rdma link show` |
| GID table | `rdma link show` |
| All counters | `ethtool -S eth0` |
| RDMA resources | `rdma resource show` |
| QoS config | `mlnx_qos -i eth0` |
| Driver info | `ethtool -i eth0` |
| FW version | `ethtool -i eth0` or `mstflint -d <dev> q` |
| PCIe info | `lspci -vvv -s <bdf>` |
| NUMA node | `cat /sys/class/net/eth0/device/numa_node` |
| Health | `devlink health show` |
| Module info | `ethtool --module-info eth0` |
| SR-IOV VFs | `cat /sys/class/net/eth0/device/sriov_numvfs` |
