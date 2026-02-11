# Ethernet Protocols for RDMA

## Overview

This document covers Ethernet protocols and features essential for RDMA deployments, particularly RoCE (RDMA over Converged Ethernet).

## Table of Contents

1. [IEEE 802.1Qbb - Priority Flow Control (PFC)](#ieee-8021qbb)
2. [IEEE 802.1Qau - Congestion Notification](#ieee-8021qau)
3. [IEEE 802.1Qaz - Enhanced Transmission Selection](#ieee-8021qaz)
4. [IEEE 802.3x - Pause Frames](#ieee-8023x)
5. [VLAN Tagging (IEEE 802.1Q)](#vlan-tagging)
6. [MTU and Jumbo Frames](#mtu-and-jumbo-frames)
7. [DSCP Tagging](#dscp-tagging)
8. [Link Aggregation (LAG)](#link-aggregation)

---

## IEEE 802.1Qbb - Priority Flow Control (PFC)

### Overview

Priority Flow Control (PFC) is a mechanism for managing frame-based lossless Ethernet traffic. It's critical for RoCE networks.

### How PFC Works

PFC allows individual priority flows within a physical link to be paused/resumed independently:

```
[PFC-enabled Switch]
         / | \
   [Port] ─── Priority 0: Normal traffic (not paused)
         |    Priority 1: Normal traffic (not paused)
         |    Priority 2: Normal traffic (not paused)
         |    Priority 3: RDMA traffic (PAUSED when congested)
         |    Priority 4: Normal traffic (not paused)
         |    Priority 5: Normal traffic (not paused)
         |    Priority 6: Normal traffic (not paused)
         |    Priority 7: Normal traffic (not paused)
```

### PFC Frame Format

PFC uses Ethernet control frames (opcode 0x0101):

```
Destination MAC: 01:80:C2:00:00:01
Source MAC: [Sender MAC]
EtherType: 0x8808
Class Enable Vector: 0x[8 bits for 8 priorities]
Time: 2 * 512 * queue_id
```

### Configuration on Mellanox Switches

```bash
# Enable PFC on specific port
interface ethernet 1/1/1
priority-flow-control on
priority-flow-control rx on
priority-flow-control tx on
priority-pfc 3 on  # Enable priority 3 for RDMA
```

### Configuration on Host (Linux)

```bash
# Show current PFC settings
ethtool -a | grep pause
# Enable PFC on NIC
ethtool -s eth0 tx off rx off
# Set PFC priority
ethtool -A eth0 pause rx 3 tx 3
```

### Best Practices

1. **Map RDMA traffic to dedicated priority** (typically priority 3)
2. **Ensure consistent PFC priority** across fabric
3. **Configure buffer sizes** appropriately on switches
4. **Monitor PFC statistics** for congestion events
5. **Test with traffic generation** to validate configuration

---

## IEEE 802.1Qau - Congestion Notification (CN)

### Overview

Explicit Congestion Notification (CN) provides end-to-end congestion feedback for lossless Ethernet networks.

### CN Operation

1. **CN Detection** - Switch detects congestion
2. **CN Marking** - Switch marks packets as experiencing congestion
3. **CNM Generation** - Switch sends Congestion Notification Message
4. **CN Reception** - Receiver processes CNM and responds
5. **Rate Reduction** - Sender reduces transmission rate

### CNM Frame Format

```
Destination MAC: 01:80:C2:00:00:01 (Multicast)
Source MAC: [Switch MAC]
EtherType: 0x8808
Opcode: CNM (0x01)
Q: Queue experiencing congestion
Q_offset: Offset to first bit set
ECN bits: CNP (experience), ECT (CE threshold)
```

### CNP vs ECT

| Indicator | Meaning | Action |
|-----------|----------|--------|
| CNP=0, ECT=0 | No congestion | Continue normal rate |
| CNP=1, ECT=0 | Experiencing congestion | Reduce rate |
| CNP=0, ECT=1 | CE threshold exceeded | Reduce rate more aggressively |
| CNP=1, ECT=1 | Both conditions | Maximum rate reduction |

### Configuration

**Mellanox Switch:**
```bash
# Enable ECN
interface ethernet 1/1/1
dcbx priority-flow-control on
dcbx priority-flow-control mode pfc
dcbx priority-ecn on  # Enable ECN marking
```

**Host Configuration:**
```bash
# Set DCB mode
dcbtool sc eth0 pfc

# View ECN status
ethtool -a eth0 | grep -i ecn
```

---

## IEEE 802.1Qaz - Enhanced Transmission Selection (ETS)

### Overview

ETS allocates bandwidth among different traffic classes using a weighted scheduling algorithm.

### ETS Principles

```
[Traffic Class 0] ───┐
                     │
[Traffic Class 1] ───┤── [Scheduler] ─── [Physical Link]
                     │
[Traffic Class 2] ───┤
                     │
[Traffic Class 3] ───┘

Each class gets guaranteed minimum bandwidth based on weights
Excess bandwidth allocated fairly
```

### ETS Configuration

**Weight Assignment:**
- **Weights** are typically 0-100 (or 0-100%)
- **Higher weight** = more guaranteed bandwidth
- **Strict Priority** for classes with same weight

**Example Configuration:**
```
Priority 0 (Management): Weight 10
Priority 1 (Voice): Weight 20
Priority 2 (Video): Weight 30
Priority 3 (RDMA): Weight 40
Remaining: Weight 0 (best effort)
```

**Mellanox Switch:**
```bash
interface ethernet 1/1/1
dcbx priority-ets on
dcbx priority-ets algorithm strict
dcbx priority-group-weight 3 40  # RDMA gets 40% of bandwidth
```

---

## IEEE 802.3x - Pause Frames

### Overview

Classic flow control mechanism that pauses the entire link.

### Pause Frame Format

```
MAC Control: 01:80:C2:00:00:01 (Multicast)
Opcode: 0x0001 (PAUSE)
Time: 65535 * pause_quanta (in units of 512 bit times)
```

### Limitations for RDMA

**Why Pause is Inadequate:**
- Pauses ALL traffic on link (not priority-specific)
- Causes head-of-line blocking
- Indiscriminately affects all applications
- Poor for multi-tenant or multi-traffic scenarios

**When to Use Pause:**
- Simple networks with single traffic class
- Legacy equipment not supporting PFC
- Non-RDMA traffic where latency is not critical

### PFC vs Pause

| Feature | Pause | PFC |
|---------|-------|-----|
| Granularity | Entire link | Per priority |
| Impact | All traffic | Single priority |
| Complexity | Simple | Complex |
| RDMA Suitability | Poor | Excellent |
| Multi-tenant | No | Yes |

---

## VLAN Tagging (IEEE 802.1Q)

### Overview

Virtual LANs segment broadcast domains and enable multiple logical networks over same physical infrastructure.

### VLAN Frame Format

```
[Dest MAC][Src MAC][0x8100][Priority/CFI][VLAN ID (12 bits)][EtherType][Payload][FCS]
          0x8100 indicates tagged frame
```

### VLAN Types

1. **Access VLAN** - Single VLAN per port
2. **Trunk VLAN** - Multiple VLANs allowed
3. **Native VLAN** - Untagged traffic assigned to VLAN
4. **Q-in-Q** - Multiple VLAN tags

### VLAN for RDMA

**Best Practices:**
1. **Dedicated VLAN** for RDMA traffic isolation
2. **Tagless for pure RDMA** if no other protocols
3. **Q-in-Q for mixed traffic** (RDMA + storage + management)
4. **Match VLAN IDs** across fabric
5. **Configure spanning-tree** properly for loop prevention

**Configuration Example:**
```bash
# On Mellanox switch
interface ethernet 1/1/1
vlan protocol 802.1q
vlan add 100 untagged  # RDMA VLAN
```

---

## MTU and Jumbo Frames

### Standard MTU Values

| Speed | Standard MTU | Jumbo MTU | Max Efficiency |
|-------|--------------|-----------|---------------|
| 1G | 1500 | 9000 | ~85% |
| 10G | 9000 | 9000-16384 | ~95% |
| 25G | 9000 | 9000-16384 | ~95% |
| 40G | 9000 | 9000-16384 | ~95% |
| 100G | 9000 | 9000-16384 | ~95% |

### Jumbo Frames Benefits for RDMA

1. **Reduced Per-Packet Overhead** - Fewer packets for same data
2. **Higher Throughput** - More data in flight
3. **Lower CPU Interrupts** - Fewer packets processed
4. **Better Efficiency** - Maximizes link utilization

### Configuration

**Switch:**
```bash
interface ethernet 1/1/1
mtu 9216  # 9KB jumbo frames
```

**Host:**
```bash
ip link set eth0 mtu 9000
# Verify
ip link show eth0
```

**Mellanox NIC:**
```bash
# Query supported MTU
ibv_devinfo -v

# Set MTU
ip link set ib0 mtu 9000
```

### MTU Considerations

**Consistent MTU:**
- All hosts must use same MTU
- Switches must be configured consistently
- Mismatch causes packet drops

**Path MTU:**
- Minimum MTU across path limits all connections
- InfiniBand has 2048 MTU by default
- Ethernet typically 1500 (standard) or 9000+ (jumbo)

---

## DSCP Tagging

### Overview

Differentiated Services Code Point (DSCP) is used for QoS marking at Layer 3.

### DSCP Frame

```
[IP Header]... [DSCP (6 bits)][ECN (2 bits)][IP Header continues...]
```

### DSCP Values

| Class | PHB | Code Points |
|-------|-----|------------|
| Best Effort | 0 | 0 |
| Bulk | 1 | 8, 16, 24 |
| Bronze | 2 | 32 |
| Silver | 3 | 40, 48, 56 |
| Gold | 4 | 64, 72, 80 |
| Platinum | 5 | 96, 104, 112, 120, 128 |
| Network Control | 6 | 136, 144, 152, 160, 168 |
| Voice | 7 | 176, 184, 192 |
| Video | 5 | 224, 232, 240 |
| RDMA | - | Use custom value (e.g., 46) |

### DSCP to PFC Mapping

Many switches map DSCP values to PFC priorities:

**Example Mapping:**
```
DSCP 46 → PFC Priority 3 (RDMA)
DSCP 8 → PFC Priority 1 (Storage)
DSCP 0 → PFC Priority 0 (Best Effort)
```

**Configuration:**
```bash
# Set DSCP on Mellanox switch
dcbx priority-pgid on
dcbx priority-dscp2pfc 46 3  # Map DSCP 46 to PFC 3

# Set DSCP on host (Linux)
tc qdisc add dev eth0 root handle 10: mqprio num 2
tc filter add dev eth0 parent 10:0 protocol ip handle 42 fw flowid 42 flow ipproto ipv6 dst 2001:db8::1
tc filter add dev eth0 parent 10:0 protocol ip handle 43 fw flowid 43 flow map to 42 action skbedit dscp 46
```

---

## Link Aggregation (LAG)

### Overview

LAG combines multiple physical links into single logical link for increased bandwidth and redundancy.

### LAG Types

1. **Static LAG** - Manual configuration
2. **LACP** - IEEE 802.3ad (dynamic)
3. **MLNX OS specific** - Proprietary bonding

### LAG Algorithms

| Algorithm | Description | Use Case |
|-----------|-------------|----------|
| Round Robin | Distribute evenly | Good for single flow |
| XOR | Hash-based | Better distribution |
| Static | Manual mapping | Predictable distribution |
| LACP | Dynamic negotiation | Automatic failover |

### LAG for RDMA

**Considerations:**
1. **Hash Distribution** - Ensure flows distributed evenly
2. **Failover Time** - Should be sub-100ms for RDMA
3. **Bandwidth Additive** - Multiple links for more bandwidth
4. **Complexity** - Increases troubleshooting complexity

**Configuration Example:**
```bash
# On Mellanox switch
interface ethernet 1/1/1
interface ethernet 1/1/2
interface ethernet 1/1/3
interface ethernet 1/1/4

# Create LAG
channel group 1 1/1/1-4 mode 802.3ad lacp
channel group 1 type trunk
```

---

## Data Center Bridging (DCB)

### DCB Components

DCB is a suite of IEEE 802.1 standards for Ethernet enhancements in data centers:

1. **802.1Qbb** - Priority Flow Control (PFC)
2. **802.1Qau** - Congestion Notification (CN)
3. **802.1Qaz** - Enhanced Transmission Selection (ETS)
4. **802.1Qat** - Data Center Bridging Exchange (DCBX)

### DCBX Operation

DCBX enables switches and hosts to exchange DCB capabilities:

1. **Discovery** - Identify DCB-capable peers
2. **Capability Exchange** - Share supported features
3. **Configuration Sync** - Ensure consistent settings
4. **Error Detection** - Mismatch alerts

### DCB Verification

```bash
# On Mellanox switch
dcbx check

# Expected output:
# DCBX: On
# PFC: On
# ETS: On
# CN: On
# ...
```

---

## Cable Specifications

### Twinax Cable

```
    SFP+ Cage
    ┌─────────┐
    │         │
    │  Transceiver Module (SFP28/SFP56)
    │  ┌─────┐
    │  │  RX  │  Fiber
    │  │  TX  │  Connection
    │  └─────┘
    │         │
    └─────────┘

Pinout: 4 differential pairs
Distance: Up to 100m (OM4), 550m (OS2)
Speed: 25G, 50G, 100G
```

### DAC Cable

```
    [Copper]
    ┌─────────┐
    │  Direct Attach
    │  Copper (Twinax)
    │  Connection
    └─────────┘

Pinout: 4 differential pairs
Distance: Up to 7m (passive), 15m (active)
Speed: 25G, 50G, 100G, 200G
```

### AOC Cable

```
[Active Optical Cable]
    ┌─────────┐
    │  Direct Attach
    │  Fiber + Electronics
    │  Connection
    └─────────┘

Distance: Up to 150m
Speed: 40G, 100G, 200G, 400G
```

### Selection Guide

| Cable Type | Speed | Distance | Cost | Use Case |
|-----------|-------|----------|-------|-----------|
| DAC (Passive) | 25G-100G | <7m | Low | Top-of-rack connections |
| DAC (Active) | 25G-100G | <15m | Medium | Rack-to-rack |
| AOC | 40G-400G | <150m | Medium | Moderate distance |
| Fiber + SFP+ | Up to 400G | 100m+ | High | Long distance |

---

## Monitoring Ethernet for RDMA

### Key Metrics

1. **PFC Pause Events** - How often PFC is triggered
2. **ECN Marked Packets** - Congestion notification rate
3. **CRC Errors** - Physical layer issues
4. **FCS Errors** - Frame integrity
5. **Symbol Errors** - Signal integrity
6. **Discarded Frames** - Buffer overruns

### Collection Tools

**Per-Interface:**
```bash
# Show interface statistics
ethtool -S eth0

# Show PFC statistics
ethtool -a eth0 | grep -i pause

# Show error statistics
ethtool -S eth0
```

**Fabric-Wide:**
```bash
# Mellanox switch
show interfaces ethernet 1/1/x statistics

# Key metrics:
# rx_pause_prio_3 - PFC pause count for priority 3
# tx_ecn - ECN marked packets
# rx_crc - CRC errors
# rx_symbol_err - Symbol errors
```

---

## Troubleshooting Ethernet Issues

### Common Problems

**PFC Not Working:**
1. Verify PFC enabled on both ends
2. Check priority mapping matches
3. Ensure buffer sizes are adequate
4. Look for ECN misconfiguration

**Packet Loss:**
1. Check PFC buffer depth
2. Verify MTU consistency
3. Look for oversubscribed links
4. Examine CRC error rate

**Congestion:**
1. Monitor PFC pause frequency
2. Check ECN marking rate
3. Verify ETS configuration
4. Review bandwidth allocation

**Performance Issues:**
1. Verify jumbo frames enabled
2. Check LACP/LAG status
3. Confirm VLAN configuration
4. Validate DSCP to PFC mapping

### Debug Commands

```bash
# Show detailed interface info
ethtool -i eth0

# Dump switch port configuration
dcbx show interface ethernet 1/1/1

# Show Mellanox statistics
sminfo -p

# Packet capture for analysis
tcpdump -i eth0 -w capture.pcap
```

---

## References

1. IEEE 802.1Qbb-2011 Standard
2. IEEE 802.1Qau-2010 Standard
3. IEEE 802.1Qaz-2011 Standard
4. IEEE 802.3ad-2008 Standard
5. Mellanox DCB Configuration Guide
6. NVIDIA Spectrum Switch User Manual