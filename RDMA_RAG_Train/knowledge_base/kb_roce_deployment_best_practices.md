---
title: "RoCE Deployment Best Practices - Complete Guide"
category: kb
tags:
  - roce
  - rocev2
  - deployment
  - best-practices
  - dcb
  - pfc
  - ecn
  - ets
  - network-design
  - cumulus
  - sonic
  - onyx
  - lossless
  - data-center
---

# RoCE Deployment Best Practices - Complete Guide

## 1. Introduction

RDMA over Converged Ethernet (RoCE) enables RDMA transport over Ethernet networks.
RoCEv2 (routable RoCE) encapsulates IB transport over UDP/IP (destination port 4791),
making it routable across L3 networks. Deploying RoCE at scale requires careful network
design, switch configuration, NIC tuning, and host-level settings to achieve lossless or
near-lossless behavior.

This guide covers end-to-end RoCE deployment from physical topology through monitoring,
with production-ready configurations for Cumulus Linux, SONiC, and NVIDIA ONYX switches.

---

## 2. Network Design Principles

### 2.1 Leaf-Spine Topology

RoCE deployments should use a leaf-spine (Clos) fabric:

```
         ┌─────────┐   ┌─────────┐
         │ Spine-1  │   │ Spine-2  │
         └────┬─────┘   └────┬─────┘
              │               │
     ┌────────┼───────────────┼────────┐
     │        │               │        │
┌────┴───┐ ┌──┴─────┐ ┌──────┴┐ ┌─────┴──┐
│ Leaf-1 │ │ Leaf-2 │ │ Leaf-3│ │ Leaf-4 │
└──┬──┬──┘ └──┬──┬──┘ └──┬──┬─┘ └──┬──┬──┘
   │  │       │  │       │  │      │  │
  Servers   Servers    Servers   Servers
```

**Key design rules:**

- **Equal-Cost Multi-Path (ECMP):** Use BGP or OSPF with ECMP across all spine links.
- **Symmetric bandwidth:** Every leaf connects to every spine with equal link capacity.
- **Oversubscription ratio:** For RDMA-heavy workloads, target 1:1 or at most 2:1.
- **MTU consistency:** Configure jumbo frames (MTU 9216) end-to-end — on every NIC,
  switch port, and routed interface in the path.

### 2.2 PFC Storm Domain and Failure Isolation

Priority Flow Control (PFC) is a hop-by-hop mechanism. A slow receiver can back-pressure
through the entire fabric via PFC PAUSE frames. This is known as a **PFC storm** or
**head-of-line blocking** propagation.

**Mitigation strategies:**

1. **Limit PFC to the access (leaf-to-host) tier only.** Use ECN end-to-end and disable
   PFC on spine-to-leaf links where possible.
2. **PFC watchdog:** Enable PFC watchdog timers on all switches to detect and break PFC
   storms by dropping traffic on a stuck priority after a timeout.
3. **Separate failure domains:** Each leaf-pair or rack is an independent PFC domain.
   A storm in Rack-A should not propagate to Rack-B via the spine.
4. **Use lossy RoCE with ECN as the primary congestion signal.** PFC acts as a safety
   net, not the primary congestion control.

### 2.3 MTU Planning

```
# Recommended MTU hierarchy
# NIC:     9000 bytes (payload)
# Switch:  9216 bytes (accounts for L2 headers, VLAN tags)
# Routed:  9216 bytes on all L3 interfaces

# Verify end-to-end MTU with ping
ping -M do -s 8972 <remote_ip>    # 8972 + 28 (IP+ICMP) = 9000
```

### 2.4 Addressing and Routing

- Use **/31** or **/30** point-to-point links between leaf and spine.
- Assign loopback addresses for BGP router-IDs.
- Advertise host subnets from leaf switches.
- Enable BFD (Bidirectional Forwarding Detection) for sub-second failover.

```
# Example BGP unnumbered on Cumulus
auto swp1
iface swp1
    mtu 9216

router bgp 65001
  bgp router-id 10.0.0.1
  neighbor swp1 interface remote-as external
  address-family ipv4 unicast
    network 10.0.0.1/32
    maximum-paths 64
```

---

## 3. Data Center Bridging (DCB) Overview

DCB is a suite of IEEE standards enabling lossless Ethernet:

| Standard   | Name                          | Purpose                                    |
|-----------|-------------------------------|--------------------------------------------|
| 802.1Qbb  | Priority Flow Control (PFC)   | Per-priority PAUSE frames                  |
| 802.1Qaz  | Enhanced Transmission Select  | Bandwidth allocation per traffic class      |
| 802.1Qau  | Congestion Notification (QCN) | L2 congestion feedback (rarely used)       |
| —         | DCBX                          | Discovery and capability exchange           |
| RFC 3168  | ECN                           | End-to-end congestion notification          |

For RoCE, the critical components are: **PFC + ETS + ECN + DCBX**.

---

## 4. Switch Configuration

### 4.1 Priority and Traffic Class Mapping

RoCE traffic must be mapped to a dedicated priority and traffic class (TC):

- **Priority 3** is the most common choice for RoCE (NVIDIA recommendation).
- **Priority 4** is an alternative used in some environments.
- All other traffic runs on default priority 0 (best effort).

The mapping chain:

```
Application → DSCP/PCP → Switch Priority → Traffic Class → Queue
```

### 4.2 PFC Configuration

Enable PFC **only** on the RoCE priority. Never enable PFC on all priorities.

**PFC parameters:**
- `pfc_en`: bitmap of priorities with PFC enabled
- For priority 3: `pfc_en = 0,0,0,1,0,0,0,0` (bit 3 set)
- For priority 4: `pfc_en = 0,0,0,0,1,0,0,0` (bit 4 set)

### 4.3 ETS (Enhanced Transmission Selection)

ETS allocates bandwidth guarantees per traffic class:

```
# Typical ETS allocation for RoCE on priority 3
# TC0 (best effort):  50% bandwidth, priorities: 0,1,2,4,5,6,7
# TC3 (RoCE):         50% bandwidth, priorities: 3

# Adjust based on workload mix
# Storage-heavy: TC3 = 70%, TC0 = 30%
# Balanced:      TC3 = 50%, TC0 = 50%
# Compute-heavy: TC3 = 30%, TC0 = 70%
```

### 4.4 ECN Marking Thresholds

ECN (Explicit Congestion Notification) is the **primary** congestion signal for RoCE.
Switches mark packets with CE (Congestion Experienced) when queue depth exceeds a
threshold.

**Recommended ECN thresholds:**

| Parameter      | Value         | Description                              |
|---------------|---------------|------------------------------------------|
| Min threshold  | 150 KB        | Start marking ECN at this queue depth     |
| Max threshold  | 1500 KB       | Mark 100% of packets above this depth     |
| Probability    | 100%          | Mark probability at max threshold         |

These thresholds may need tuning based on:
- Link speed (25G vs 100G vs 200G vs 400G)
- Buffer size available per port
- Number of flows and congestion patterns

### 4.5 WRED (Weighted Random Early Detection)

WRED drops packets probabilistically before the queue is full, preventing tail drops.
For RoCE traffic classes with PFC enabled, WRED typically operates alongside ECN:

- Below min threshold: no action
- Between min and max: probabilistic ECN marking (not drop, since PFC prevents loss)
- Above max: PFC PAUSE triggers

For non-RoCE traffic classes, WRED provides early drop to prevent buffer hogging.

---

## 5. Cumulus Linux Switch Configuration

### 5.1 Complete RoCE Configuration

```bash
# /etc/cumulus/datapath/traffic.conf on Cumulus Linux 4.x / 5.x

# === Priority to Traffic Class Mapping ===
# Map priority 3 to TC3, everything else to TC0
traffic.priority_group_to_traffic_class = [0,0,0,3,0,0,0,0]

# === PFC ===
# Enable PFC on priority 3 only
pfc.priority_list = [3]
pfc.port.set = swp1-48

# PFC watchdog - detect and recover from PFC storms
pfc.watchdog.enabled = true
pfc.watchdog.timeout = 100       # milliseconds
pfc.watchdog.polling_interval = 50

# === ETS ===
# TC0: 50% bandwidth (best effort)
# TC3: 50% bandwidth (RoCE)
traffic.ets.tc_bw_percent = [50,0,0,50,0,0,0,0]
traffic.ets.tc_max_bw_percent = [100,0,0,100,0,0,0,0]

# === ECN ===
# Enable ECN on TC3
traffic.ecn.enable = true
traffic.ecn.tc_list = [3]
traffic.ecn.red.min_threshold_bytes = 153600    # 150 KB
traffic.ecn.red.max_threshold_bytes = 1536000   # 1500 KB
traffic.ecn.red.probability = 100

# === Buffer Allocation ===
# Allocate sufficient buffers for lossless traffic
traffic.port_buffer.lossless.size = 2097152     # 2 MB per port
traffic.port_buffer.lossy.size = 1048576        # 1 MB per port
```

```bash
# Apply the configuration
sudo systemctl restart switchd

# Verify PFC counters
ethtool -S swp1 | grep pfc
#   pfc0_rx_pause: 0
#   pfc0_tx_pause: 0
#   pfc3_rx_pause: 142
#   pfc3_tx_pause: 87

# Verify ECN counters
ethtool -S swp1 | grep ecn
#   ecn_marked: 4521
```

### 5.2 DCBX Configuration on Cumulus

```bash
# Configure DCBX in non-willing mode (switch pushes config to NIC)
# /etc/lldpd.d/dcbx.conf

configure ports swp1-48 med policy application RoCE \
    priority 3 vlan-id 0

# Alternatively, use lldptool
lldptool -Ti swp1 -V ETS-CFG \
    willing=no \
    up2tc=0:0,1:0,2:0,3:3,4:0,5:0,6:0,7:0 \
    tsa=0:ets,3:ets \
    tcbw=50,0,0,50,0,0,0,0

lldptool -Ti swp1 -V PFC \
    willing=no \
    enabled=0,0,0,1,0,0,0,0

# Verify DCBX negotiation
lldptool -ti swp1 -V ETS-CFG
lldptool -ti swp1 -V PFC
```

### 5.3 Cumulus NVUE Configuration (Cumulus 5.x+)

```bash
# Using NVUE (NVIDIA User Experience) CLI
nv set qos roce enable on
nv set qos roce mode lossless

# This single command sets up:
# - PFC on priority 3
# - ECN marking on TC3
# - ETS bandwidth allocation
# - Trust DSCP mode
# - Buffer allocation

nv config apply

# Verify
nv show qos roce
nv show interface swp1 qos
```

---

## 6. SONiC Switch Configuration

### 6.1 QoS Configuration via config_db.json

```json
{
    "DSCP_TO_TC_MAP": {
        "AZURE": {
            "0": "0",
            "1": "0",
            "2": "0",
            "3": "0",
            "4": "0",
            "5": "0",
            "6": "0",
            "7": "0",
            "8": "0",
            "9": "0",
            "10": "0",
            "11": "0",
            "12": "0",
            "13": "0",
            "14": "0",
            "15": "0",
            "16": "0",
            "17": "0",
            "18": "0",
            "19": "0",
            "20": "0",
            "21": "0",
            "22": "0",
            "23": "0",
            "24": "3",
            "25": "3",
            "26": "3",
            "27": "0",
            "28": "0",
            "29": "0",
            "30": "0",
            "31": "0",
            "32": "0",
            "33": "0",
            "34": "0",
            "35": "0",
            "36": "0",
            "37": "0",
            "38": "0",
            "39": "0",
            "40": "0",
            "41": "0",
            "42": "0",
            "43": "0",
            "44": "0",
            "45": "0",
            "46": "0",
            "47": "0",
            "48": "0",
            "49": "0",
            "50": "0",
            "51": "0",
            "52": "0",
            "53": "0",
            "54": "0",
            "55": "0",
            "56": "0",
            "57": "0",
            "58": "0",
            "59": "0",
            "60": "0",
            "61": "0",
            "62": "0",
            "63": "0"
        }
    },
    "TC_TO_PRIORITY_GROUP_MAP": {
        "AZURE": {
            "0": "0",
            "1": "0",
            "2": "0",
            "3": "3",
            "4": "0",
            "5": "0",
            "6": "0",
            "7": "0"
        }
    },
    "TC_TO_QUEUE_MAP": {
        "AZURE": {
            "0": "0",
            "1": "1",
            "2": "2",
            "3": "3",
            "4": "4",
            "5": "5",
            "6": "6",
            "7": "7"
        }
    },
    "PFC_PRIORITY_TO_PRIORITY_GROUP_MAP": {
        "AZURE": {
            "0": "0",
            "1": "0",
            "2": "0",
            "3": "3",
            "4": "0",
            "5": "0",
            "6": "0",
            "7": "0"
        }
    },
    "PORT_QOS_MAP": {
        "Ethernet0": {
            "dscp_to_tc_map": "AZURE",
            "tc_to_queue_map": "AZURE",
            "tc_to_pg_map": "AZURE",
            "pfc_to_pg_map": "AZURE",
            "pfc_enable": "3"
        }
    },
    "WRED_PROFILE": {
        "AZURE_LOSSLESS": {
            "ecn": "ecn_all",
            "green_min_threshold": "153600",
            "green_max_threshold": "1536000",
            "green_drop_probability": "5",
            "yellow_min_threshold": "153600",
            "yellow_max_threshold": "1536000",
            "yellow_drop_probability": "5",
            "red_min_threshold": "153600",
            "red_max_threshold": "1536000",
            "red_drop_probability": "5"
        }
    },
    "QUEUE": {
        "Ethernet0|3": {
            "wred_profile": "AZURE_LOSSLESS",
            "scheduler": "scheduler.0"
        }
    },
    "SCHEDULER": {
        "scheduler.0": {
            "type": "DWRR",
            "weight": "50"
        }
    },
    "BUFFER_POOL": {
        "ingress_lossless_pool": {
            "size": "12766208",
            "type": "ingress",
            "mode": "dynamic"
        },
        "egress_lossless_pool": {
            "size": "12766208",
            "type": "egress",
            "mode": "dynamic"
        }
    },
    "BUFFER_PROFILE": {
        "ingress_lossless_profile": {
            "pool": "ingress_lossless_pool",
            "size": "0",
            "dynamic_th": "3",
            "xon": "18432",
            "xoff": "165888"
        }
    },
    "BUFFER_PG": {
        "Ethernet0|3-4": {
            "profile": "ingress_lossless_profile"
        }
    }
}
```

### 6.2 SONiC CLI Commands

```bash
# Apply RoCE QoS configuration
sudo config qos reload

# Verify PFC status
show pfc counters
#   Port       PFC0    PFC1    PFC2    PFC3    PFC4    PFC5    PFC6    PFC7
#   ---------  ------  ------  ------  ------  ------  ------  ------  ------
#   Ethernet0  0       0       0       142     0       0       0       0

# Verify buffer allocation
show buffer_pool
show buffer_pg

# Verify ECN/WRED profile
show ecn

# PFC watchdog configuration
sudo config pfcwd start --action drop Ethernet0 200 --restoration-time 400

# Check PFC watchdog status
show pfcwd stats
show pfcwd config
```

---

## 7. NVIDIA ONYX Switch Configuration

### 7.1 Complete RoCE Configuration

```
! NVIDIA ONYX (Mellanox Onyx) Configuration

! Enable DCB globally
dcb priority-flow-control enable force

! Configure PFC on priority 3
dcb priority-flow-control priority 3 enable

! Configure ETS
dcb ets tc 0 bw-percent 50
dcb ets tc 3 bw-percent 50
dcb ets tc 0 prio 0,1,2,4,5,6,7
dcb ets tc 3 prio 3

! Configure ECN on TC3
traffic ecn enable
traffic ecn tc 3 min-absolute 150 max-absolute 1500

! Trust DSCP on all ports
interface ethernet 1/1-1/32
  dcb trust dscp
  mtu 9216
exit

! PFC watchdog
pfc-watchdog enable
pfc-watchdog timeout 100
pfc-watchdog polling-interval 50
pfc-watchdog action drop

! Configure DSCP-to-priority mapping
traffic dscp-map dscp 26 priority 3
traffic dscp-map dscp 24 priority 3

! DCBX configuration
dcbx mode cee
dcbx willing off

! Verify configuration
show dcb priority-flow-control
show dcb ets
show dcb ecn
show interface ethernet 1/1 counters pfc
```

### 7.2 ONYX Monitoring Commands

```
! Show PFC counters per port
show interface ethernet 1/1 counters pfc

! Show ECN counters
show interface ethernet 1/1 counters ecn

! Show buffer utilization
show buffers port ethernet 1/1

! Show congestion watermarks
show interface ethernet 1/1 counters watermark

! What Just Happened (WJH) - see section 11
what-just-happened enable
show what-just-happened forwarding
show what-just-happened buffer
```

---

## 8. NIC Configuration

### 8.1 Trust Mode: DSCP vs PCP

The NIC must be configured to trust the correct QoS marking:

- **DSCP (recommended):** Trust the DSCP field in the IP header. Works across L3
  boundaries. This is the standard for RoCEv2.
- **PCP:** Trust the 802.1Q VLAN priority bits. Only works within a single L2 domain.

```bash
# Set trust mode to DSCP on ConnectX NIC
mlnx_qos -i eth0 --trust=dscp

# Verify trust mode
mlnx_qos -i eth0
# Trust state: dscp

# Set trust mode to PCP (if needed for L2-only environments)
mlnx_qos -i eth0 --trust=pcp
```

### 8.2 Traffic Class Mapping

Map DSCP values to traffic classes and priorities on the NIC:

```bash
# Map DSCP 26 (AF31) to priority 3, traffic class 3
# DSCP 26 = 011010 in binary, corresponds to CS3/AF31

mlnx_qos -i eth0 --dscp2prio set,26,3

# Set PFC on priority 3
mlnx_qos -i eth0 --pfc 0,0,0,1,0,0,0,0

# Configure ETS bandwidth
mlnx_qos -i eth0 --tc_bw 50,0,0,50,0,0,0,0

# Map priorities to traffic classes
mlnx_qos -i eth0 --up2tc 0,0,0,3,0,0,0,0

# Full mlnx_qos output example:
mlnx_qos -i eth0
# Priority trust state: dscp
# dcbx mode: OS controlled
# PFC configuration:
#     priority    0   1   2   3   4   5   6   7
#     enabled     0   0   0   1   0   0   0   0
# tc: 0 ratelimit: unlimited, tsa: ets, bw: 50%
# tc: 1 ratelimit: unlimited, tsa: strict
# tc: 2 ratelimit: unlimited, tsa: strict
# tc: 3 ratelimit: unlimited, tsa: ets, bw: 50%
# tc: 4 ratelimit: unlimited, tsa: strict
# tc: 5 ratelimit: unlimited, tsa: strict
# tc: 6 ratelimit: unlimited, tsa: strict
# tc: 7 ratelimit: unlimited, tsa: strict
```

### 8.3 Setting RDMA CM TOS (cma_roce_tos)

The RDMA Connection Manager must stamp the correct DSCP/TOS value on RoCE packets:

```bash
# Set TOS for RDMA CM connections
# DSCP 26 = TOS 104 (26 << 2 = 104)
echo 104 > /sys/kernel/config/rdma_cm/mlx5_0/ports/1/default_roce_tos

# Alternatively, set via cma_roce_tos module parameter
echo "options rdma_cm cma_roce_tos=104" > /etc/modprobe.d/rdma_cm.conf

# For applications using rdma_cm, set TOS programmatically:
# rdma_set_option(cm_id, RDMA_OPTION_ID, RDMA_OPTION_ID_TOS, &tos, sizeof(tos));

# Verify the setting
cat /sys/kernel/config/rdma_cm/mlx5_0/ports/1/default_roce_tos
# 104
```

### 8.4 NIC ECN Settings

Enable ECN generation and reaction on the NIC:

```bash
# Enable ECN on the NIC (ConnectX-5 and later)
# Using sysfs
echo 1 > /sys/class/net/eth0/ecn/roce_np/enable/3
echo 1 > /sys/class/net/eth0/ecn/roce_rp/enable/3

# The NIC implements DCQCN (Data Center QCN) as the congestion control algorithm
# Key DCQCN parameters:
#   - CNP DSCP value (default: 48, which is CS6)
#   - Rate reduction on CNP receipt
#   - Rate increase timer
#   - Alpha update factor

# View current ECN/congestion control settings
cat /sys/class/net/eth0/ecn/roce_np/enable/3   # NP = Notification Point
cat /sys/class/net/eth0/ecn/roce_rp/enable/3   # RP = Reaction Point
```

### 8.5 Firmware-Level Configuration with mstconfig

```bash
# Check current firmware settings
mstconfig -d /dev/mst/mt4121_pciconf0 query

# Key RoCE-related firmware settings:
# ROCE_CC_PRIO_MASK_P1  - Bitmask of priorities for congestion control
# CNP_DSCP_P1           - DSCP value for CNP packets
# CNP_802P_PRIO_P1      - 802.1p priority for CNP packets

# Set congestion control on priority 3
mstconfig -d /dev/mst/mt4121_pciconf0 set ROCE_CC_PRIO_MASK_P1=8

# Set CNP DSCP to 48 (CS6)
mstconfig -d /dev/mst/mt4121_pciconf0 set CNP_DSCP_P1=48

# Requires firmware reset
mlxfwreset -d /dev/mst/mt4121_pciconf0 reset
```

---

## 9. Linux Kernel and Host Settings

### 9.1 ECN Sysctl Settings

```bash
# Enable ECN negotiation for TCP (not directly for RDMA, but for coexistence)
sysctl -w net.ipv4.tcp_ecn=1

# Values:
# 0 = Disable ECN
# 1 = Enable ECN when requested by incoming connections
# 2 = Always request ECN on outgoing connections (recommended)
# 3 = Request ECN and cache ECN capability

# For RoCE-specific ECN, the NIC firmware handles ECN marking/reaction
# The kernel sysctl is for TCP traffic sharing the same network
```

### 9.2 Memory and RDMA Settings

```bash
# Increase locked memory limits for RDMA
# /etc/security/limits.conf
* soft memlock unlimited
* hard memlock unlimited

# Or for specific users
rdma_user soft memlock unlimited
rdma_user hard memlock unlimited

# Increase the maximum number of memory regions
sysctl -w vm.max_map_count=1048576

# Increase socket buffer sizes for better performance
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
sysctl -w net.core.rmem_default=16777216
sysctl -w net.core.wmem_default=16777216

# TCP tuning (for TCP traffic coexisting with RoCE)
sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sysctl -w net.ipv4.tcp_wmem="4096 87380 16777216"
```

### 9.3 IRQ Affinity and CPU Pinning

```bash
# Set IRQ affinity for the RDMA NIC
# Use the NVIDIA-provided script
/usr/sbin/set_irq_affinity_cpulist.sh 0-15 eth0

# Alternatively, set manually per completion vector
# Find IRQ numbers
cat /proc/interrupts | grep mlx5

# Pin each IRQ to a specific CPU
echo 1 > /proc/irq/52/smp_affinity   # CPU 0
echo 2 > /proc/irq/53/smp_affinity   # CPU 1
echo 4 > /proc/irq/54/smp_affinity   # CPU 2

# Verify affinity
cat /proc/irq/52/smp_affinity_list
# 0
```

### 9.4 Hugepages Configuration

```bash
# Allocate hugepages for RDMA memory registration
# 2MB hugepages
echo 4096 > /proc/sys/vm/nr_hugepages

# Or set in sysctl.conf for persistence
sysctl -w vm.nr_hugepages=4096

# 1GB hugepages (set via kernel boot parameter)
# GRUB: hugepagesz=1G hugepages=8

# Mount hugetlbfs
mount -t hugetlbfs none /dev/hugepages

# Verify
cat /proc/meminfo | grep Huge
# HugePages_Total:    4096
# HugePages_Free:     4096
# HugePages_Rsvd:        0
# Hugepagesize:       2048 kB
```

### 9.5 Persistent Configuration Script

```bash
#!/bin/bash
# /usr/local/bin/configure_roce.sh
# Run at boot to configure RoCE settings

NIC="eth0"
DSCP=26
TOS=$((DSCP << 2))  # 104
PRIORITY=3
RDMA_DEV="mlx5_0"

echo "Configuring RoCE on ${NIC} (${RDMA_DEV})..."

# Trust DSCP
mlnx_qos -i ${NIC} --trust=dscp

# PFC on priority 3
mlnx_qos -i ${NIC} --pfc 0,0,0,1,0,0,0,0

# ETS bandwidth allocation
mlnx_qos -i ${NIC} --tc_bw 50,0,0,50,0,0,0,0

# Priority to TC mapping
mlnx_qos -i ${NIC} --up2tc 0,0,0,3,0,0,0,0

# DSCP to priority mapping
mlnx_qos -i ${NIC} --dscp2prio set,${DSCP},${PRIORITY}

# Set RDMA CM TOS
mkdir -p /sys/kernel/config/rdma_cm/${RDMA_DEV}/ports/1
echo ${TOS} > /sys/kernel/config/rdma_cm/${RDMA_DEV}/ports/1/default_roce_tos

# Enable ECN on the NIC for priority 3
echo 1 > /sys/class/net/${NIC}/ecn/roce_np/enable/${PRIORITY} 2>/dev/null
echo 1 > /sys/class/net/${NIC}/ecn/roce_rp/enable/${PRIORITY} 2>/dev/null

# IRQ affinity
/usr/sbin/set_irq_affinity_cpulist.sh 0-15 ${NIC}

# Kernel settings
sysctl -w net.ipv4.tcp_ecn=1
sysctl -w vm.max_map_count=1048576
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216

echo "RoCE configuration complete on ${NIC}"
```

```bash
# Create systemd service for persistent configuration
# /etc/systemd/system/roce-config.service
[Unit]
Description=Configure RoCE Settings
After=network-online.target rdma.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/configure_roce.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

---

## 10. DCBX Configuration

### 10.1 Willing vs Non-Willing Mode

DCBX (Data Center Bridging Capability Exchange Protocol) negotiates DCB parameters
between the switch and NIC via LLDP:

- **Willing mode (NIC):** The NIC accepts parameters from the switch. This is simpler
  but requires the switch to be correctly configured.
- **Non-willing mode (NIC):** The NIC pushes its own parameters. Used when the NIC
  configuration must take precedence.
- **Recommended:** Configure the switch as non-willing (authoritative) and the NIC as
  willing, OR disable DCBX and use firmware/OS-controlled mode.

```bash
# Check DCBX mode on the NIC
mlnx_qos -i eth0
# dcbx mode: OS controlled  (or: firmware / willing)

# Set to OS-controlled mode (disables DCBX negotiation)
mlnx_qos -i eth0 --dcbx_mode=os

# Set NIC to willing mode (accept switch parameters)
lldptool -Ti eth0 -V ETS-CFG willing=yes
lldptool -Ti eth0 -V PFC willing=yes

# Set NIC to non-willing mode
lldptool -Ti eth0 -V ETS-CFG willing=no
lldptool -Ti eth0 -V PFC willing=no

# Verify DCBX state
lldptool -ti eth0 -V ETS-CFG
lldptool -ti eth0 -V PFC
```

### 10.2 Firmware-Controlled vs OS-Controlled DCBX

```bash
# Firmware-controlled (default):
# - NIC firmware handles DCBX negotiation
# - Settings persist across reboots
# - Limited to what firmware supports

# OS-controlled:
# - lldpad daemon manages DCBX
# - More flexibility
# - Requires lldpad to be running

# Set firmware-controlled DCBX
mstconfig -d /dev/mst/mt4121_pciconf0 set DCBX_IEEE_P1=1

# Set OS-controlled DCBX
mlnx_qos -i eth0 --dcbx_mode=os
systemctl enable lldpad
systemctl start lldpad
```

---

## 11. Monitoring and Troubleshooting

### 11.1 What Just Happened (WJH)

NVIDIA What Just Happened is a diagnostic feature on Spectrum switches that records
dropped/discarded packets with reasons:

```bash
# On NVIDIA Cumulus with WJH support
what-just-happened poll forwarding
# #  Timestamp            sPort  dPort  VLAN  sMAC              dMAC              EthType  Src IP:Port  Dst IP:Port  IP Proto  Drop Reason
# 1  2024-01-15 10:23:45  swp1   swp2   100   aa:bb:cc:dd:ee:01 aa:bb:cc:dd:ee:02 IPv4     10.0.1.1:0   10.0.2.1:0   UDP       PFC_PAUSE_storm_detected

what-just-happened poll buffer
# #  Timestamp            sPort  dPort  VLAN  sMAC              dMAC              EthType  Src IP:Port  Dst IP:Port  IP Proto  Drop Reason
# 1  2024-01-15 10:23:46  swp1   swp2   100   aa:bb:cc:dd:ee:01 aa:bb:cc:dd:ee:02 IPv4     10.0.1.1:0   10.0.2.1:4791 UDP      buffer_congestion_TC3

# Enable WJH streaming to a collector
what-just-happened streaming enable
what-just-happened streaming collector 10.0.0.100 port 5555 proto udp
```

### 11.2 sFlow Monitoring

```bash
# Configure sFlow on Cumulus
# /etc/hsflowd.conf
sflow {
  sampling = 1000
  polling = 30
  collector {
    ip = 10.0.0.100
    udpport = 6343
  }
  pcap {
    dev = swp1
    speed = 100000
  }
}

# On SONiC
sudo config sflow enable
sudo config sflow collector add collector1 10.0.0.100 6343
sudo config sflow interface enable Ethernet0
sudo config sflow polling-interval 30
```

### 11.3 Essential Monitoring Commands

```bash
# === Host-side monitoring ===

# Check RDMA device status
rdma dev
rdma link
ibstat

# Show RoCE counters
ethtool -S eth0 | grep -E "rx_pci_signal|tx_pause|rx_pause|pfc|ecn|cnp"

# Check for PFC events on the NIC
ethtool -S eth0 | grep pfc
# rx_pfc_pause_duration_3: 145000
# tx_pfc_pause_duration_3: 23000
# rx_pfc_pause_storm_warning_3: 0

# Monitor RDMA traffic
rdma stat show

# perfquery for InfiniBand counters (also works for RoCE)
perfquery -x

# Detailed port counters
perfquery -x -l

# === Application-level monitoring ===

# ib_write_bw test between two nodes
# Server:
ib_write_bw -d mlx5_0 --report_gbits -D 10 --tos 104

# Client:
ib_write_bw -d mlx5_0 --report_gbits -D 10 --tos 104 <server_ip>

# Expected output for 100GbE:
# BW average: 97.XX Gbps
# MsgRate:    XX,XXX,XXX messages/sec
```

### 11.4 PFC Storm Detection and Recovery

```bash
# Monitor for PFC storms
watch -n 1 'ethtool -S eth0 | grep pfc'

# If PFC counters are increasing rapidly on a port, a PFC storm may be occurring.
# Check the switch PFC watchdog:

# On Cumulus:
cat /cumulus/switchd/run/memory/pfc_watchdog/swp1

# On SONiC:
show pfcwd stats

# Emergency: disable PFC on the affected port
mlnx_qos -i eth0 --pfc 0,0,0,0,0,0,0,0

# Then investigate the root cause:
# - Misconfigured PFC on a host (e.g., PFC enabled on wrong priority)
# - Slow host/NIC not draining packets
# - Software bug causing NIC to not process completions
```

---

## 12. Failure Domain Design

### 12.1 Rack-Level Isolation

```
Rack A (PFC Domain A)        Rack B (PFC Domain B)
┌──────────────────┐         ┌──────────────────┐
│  ┌────────────┐  │         │  ┌────────────┐  │
│  │  Leaf-A1   │──┼────┐    │──│  Leaf-B1   │  │
│  └────────────┘  │    │    │  └────────────┘  │
│  ┌────────────┐  │    │    │  ┌────────────┐  │
│  │  Leaf-A2   │──┼──┐ │    │──│  Leaf-B2   │  │
│  └────────────┘  │  │ │    │  └────────────┘  │
│                  │  │ │    │                  │
│  Host-A1         │  │ ├────┼──Spine-1         │
│  Host-A2         │  └─┤    │  Spine-2         │
│  Host-A3         │    └────┼──                │
└──────────────────┘         └──────────────────┘

PFC is enabled only on leaf-to-host links.
Spine-to-leaf links use ECN only (no PFC) or PFC with strict watchdog.
```

### 12.2 Design Recommendations

1. **PFC scope:** Enable PFC only on access ports (leaf-to-host).
   On fabric ports (leaf-to-spine), rely on ECN + deep buffers.
2. **Buffer headroom:** Allocate enough buffer on each switch port for PFC to
   absorb in-flight data:
   ```
   Headroom = Link_Speed × RTT + MTU
   For 100GbE, 1μs RTT: ~12.5 KB + 9 KB = ~22 KB per port per priority
   ```
3. **Max fabric hops:** Limit to 5 hops (host → leaf → spine → leaf → host)
   for predictable latency.
4. **Separate RoCE from general traffic** using VLANs or VRFs where possible.

---

## 13. Scale Considerations

### 13.1 Buffer Planning at Scale

```
# Per-switch buffer calculation
# Spectrum-2 (SN3700): ~42 MB shared buffer
# Spectrum-3 (SN4700): ~64 MB shared buffer

# Buffer per port per priority:
# = Total_Buffer / (Num_Ports × Num_Lossless_Priorities)
# = 42 MB / (32 × 1) = ~1.3 MB per port (Spectrum-2, 32×100G)

# For larger port counts (64×100G or 128×25G), buffer per port decreases.
# Monitor buffer utilization and adjust headroom accordingly.
```

### 13.2 Connection Scaling

```bash
# RoCE uses QPs (Queue Pairs) like InfiniBand
# Each QP consumes NIC resources (memory, cache entries)

# ConnectX-6 Dx: supports millions of QPs
# But practical limits depend on:
# - Memory for WQEs (Work Queue Elements)
# - Completion queue entries
# - Address handle cache

# For large-scale deployments (1000+ nodes):
# - Use SRQ (Shared Receive Queue) to reduce memory usage
# - Use XRC (Extended Reliable Connected) for many-to-many patterns
# - Consider UD (Unreliable Datagram) for discovery/control plane
# - DC (Dynamically Connected) transport for extreme scaling

# Check current QP usage
cat /sys/class/infiniband/mlx5_0/ports/1/counters/port_rcv_data
rdma res show qp
rdma res show qp | wc -l
```

### 13.3 Multi-Subnet RoCE

```bash
# RoCEv2 is routable across L3 subnets
# Requirements:
# 1. DSCP must be preserved across routers
# 2. ECN bits must not be cleared
# 3. PFC domains are per-subnet (PFC does NOT cross L3 boundaries)
# 4. GID table must have correct entries for each subnet

# Verify GID table
rdma resource show cm_id
ibv_devinfo -v | grep GID

# Show GID table
for i in $(seq 0 15); do
  cat /sys/class/infiniband/mlx5_0/ports/1/gids/$i 2>/dev/null
done
```

---

## 14. Adaptive Routing

### 14.1 Overview

Adaptive routing dynamically selects paths based on congestion, improving fabric
utilization. NVIDIA Spectrum switches support adaptive routing:

```
# On Spectrum switches (Cumulus)
nv set router adaptive-routing enable on

# Verify
nv show router adaptive-routing
```

### 14.2 Interaction with RoCE

Adaptive routing can reorder packets. RoCE (IB transport) is sensitive to
out-of-order delivery. Modern ConnectX NICs handle moderate reordering, but:

- Enable **packet reordering tolerance** on the NIC firmware
- Use with caution and test thoroughly
- Ensure the NIC firmware supports AR-aware RoCE

---

## 15. Validation and Testing

### 15.1 End-to-End Validation Checklist

```bash
# 1. Verify MTU end-to-end
ping -M do -s 8972 <remote_ip>

# 2. Verify PFC is working
# Run ib_write_bw and check that PFC counters increment (not drops)
ethtool -S eth0 | grep -E "pfc|drop"

# 3. Verify ECN marking
# Run a congestion-inducing workload and check ECN counters
ethtool -S eth0 | grep ecn

# 4. Verify DSCP marking
# Capture packets and check DSCP value
tcpdump -i eth0 -nn -v udp port 4791 | head -5
# Should show: tos 0x68 (DSCP 26 = 0x1a, shifted left 2 = 0x68)

# 5. Run perftest suite
ib_write_bw -d mlx5_0 --report_gbits --tos 104
ib_write_lat -d mlx5_0 --tos 104
ib_read_bw -d mlx5_0 --report_gbits --tos 104
ib_send_bw -d mlx5_0 --report_gbits --tos 104

# 6. Verify DCBX negotiation
lldptool -ti eth0 -V ETS-CFG
lldptool -ti eth0 -V PFC
```

### 15.2 Performance Baselines

```
# Expected performance for ConnectX-6 (HDR100 / 100GbE)
# ib_write_bw:  ~97 Gbps (line rate)
# ib_write_lat: ~1.3 μs (small messages)
# ib_read_bw:   ~97 Gbps
# ib_read_lat:  ~1.8 μs
# ib_send_bw:   ~97 Gbps

# Expected performance for ConnectX-7 (NDR200 / 200GbE)
# ib_write_bw:  ~195 Gbps
# ib_write_lat: ~1.0 μs
# ib_read_bw:   ~195 Gbps
# ib_read_lat:  ~1.5 μs

# If performance is significantly below these baselines, check:
# - PCIe generation/width (lspci -vvv | grep Width)
# - NUMA affinity (numactl --hardware; ensure NIC and CPU are on same node)
# - IRQ affinity
# - CPU power management (set to performance mode)
# - MTU configuration
```

---

## 16. Common Pitfalls and Troubleshooting

### 16.1 Frequent Issues

| Issue | Symptom | Resolution |
|-------|---------|------------|
| DSCP not set | All RoCE traffic in best-effort queue | Set cma_roce_tos and verify with tcpdump |
| PFC on wrong priority | Lossless behavior not working | Verify mlnx_qos shows PFC on correct priority |
| MTU mismatch | Packet drops, reduced throughput | Verify MTU on every hop with ping -M do |
| DCBX conflict | NIC and switch disagree on settings | Set one side willing, other non-willing |
| ECN not enabled | No congestion signaling, PFC storms | Enable ECN on switch and NIC |
| Wrong trust mode | DSCP markings ignored | Set mlnx_qos --trust=dscp |
| NUMA misalignment | 50% or worse performance | Pin application to same NUMA node as NIC |
| PCIe bottleneck | Throughput capped below line rate | Check lspci for PCIe Gen4 x16 |

### 16.2 Diagnostic Flowchart

```
Performance Issue?
├── Check: ib_write_bw shows < 90% line rate?
│   ├── Yes → Check PCIe (lspci -vvv)
│   │   ├── Width < x16 → Reseat card or check BIOS
│   │   └── Width OK → Check NUMA (numactl)
│   │       ├── Different NUMA node → Pin to correct node
│   │       └── Same NUMA → Check IRQ affinity
│   └── No → Check latency
│       ├── ib_write_lat > 3 μs → Check PFC storms
│       └── ib_write_lat OK → Application-level issue
│
├── Packet Drops?
│   ├── ethtool -S shows rx_*_discards → PFC not working
│   │   ├── Check mlnx_qos PFC config
│   │   └── Check switch PFC config
│   └── Switch shows drops → ECN thresholds too high
│       └── Lower ECN min/max thresholds
│
└── Connection Failures?
    ├── rdma_resolve_addr fails → Check routing/ARP
    ├── rdma_resolve_route fails → Check GID table
    └── QP transitions fail → Check firewalls (UDP 4791)
```

---

## 17. Reference: DSCP Values for RoCE

| DSCP Value | DSCP Name | TOS Byte | Common Use |
|-----------|-----------|----------|------------|
| 0         | BE        | 0x00     | Best effort (default) |
| 24        | CS3       | 0x60     | RoCE (alternative) |
| 26        | AF31      | 0x68     | RoCE (NVIDIA recommended) |
| 32        | CS4       | 0x80     | RoCE (alternative) |
| 34        | AF41      | 0x88     | RoCE (alternative) |
| 46        | EF        | 0xB8     | Voice/low-latency (avoid for RoCE) |
| 48        | CS6       | 0xC0     | CNP packets |

---

## 18. Summary Configuration Matrix

| Component | Setting | Value |
|-----------|---------|-------|
| NIC Trust | Mode | DSCP |
| NIC PFC | Priority 3 | Enabled |
| NIC ETS | TC0:TC3 | 50:50 |
| NIC DSCP | Mapping | DSCP 26 → Priority 3 |
| NIC TOS | cma_roce_tos | 104 |
| Switch PFC | Priority 3 | Enabled |
| Switch ETS | TC0:TC3 | 50:50 |
| Switch ECN | TC3 min/max | 150KB / 1500KB |
| Switch Trust | Mode | DSCP |
| Switch MTU | All ports | 9216 |
| Switch PFC WD | Timeout | 100ms |
| Host ECN | tcp_ecn | 1 |
| Host Memory | memlock | unlimited |
| Host MTU | NIC | 9000 |

---

*This guide covers NVIDIA/Mellanox ConnectX-5, ConnectX-6, ConnectX-6 Dx, ConnectX-7,
and BlueField DPUs with Spectrum-1/2/3/4 switches running Cumulus Linux, SONiC, or
NVIDIA ONYX. Always refer to the latest NVIDIA DOCA/OFED documentation for
firmware-specific parameters.*
