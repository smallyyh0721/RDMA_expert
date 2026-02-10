---
title: "Data Center Bridging - PFC, ETS, ECN, DCQCN Specification"
category: specifications
tags: [dcb, pfc, ets, ecn, dcqcn, lossless, ethernet, congestion]
---

# Data Center Bridging (DCB) - PFC, ETS, ECN, DCQCN

## 1. Overview

Data Center Bridging (DCB) is a set of IEEE 802.1 standards that enhance Ethernet for data center use, particularly enabling lossless Ethernet required by RoCE.

Key components:
- **PFC** (802.1Qbb): Priority-based Flow Control
- **ETS** (802.1Qaz): Enhanced Transmission Selection
- **DCBX** (802.1Qaz): DCB Capability Exchange Protocol
- **CN** (802.1Qau): Congestion Notification (QCN)

## 2. Priority-based Flow Control (PFC) - IEEE 802.1Qbb

### 2.1 Concept

PFC extends Ethernet PAUSE frames to operate on a per-priority basis. Instead of pausing all traffic, PFC can selectively pause individual traffic classes.

Standard 802.3x PAUSE: Stops ALL traffic on the link
PFC: Stops only specific priority classes (0-7)

### 2.2 PFC Frame Format

```
+---------------------------+
| Destination MAC:          |
|   01:80:C2:00:00:01       |  (well-known PAUSE address)
+---------------------------+
| Source MAC                 |
+---------------------------+
| EtherType: 0x8808         |  (MAC Control)
+---------------------------+
| MAC Control OpCode: 0x0101|  (PFC)
+---------------------------+
| Priority Enable Vector    |  16 bits (bit per priority)
|  Bit 0 = Priority 0       |
|  Bit 1 = Priority 1       |
|  ...                       |
|  Bit 7 = Priority 7       |
+---------------------------+
| Time[0]                   |  16 bits (pause duration for pri 0)
| Time[1]                   |  16 bits (pause duration for pri 1)
| ...                        |
| Time[7]                   |  16 bits (pause duration for pri 7)
+---------------------------+
| Pad (to 64 bytes min)     |
+---------------------------+
| FCS                        |
+---------------------------+
```

Pause duration: In units of 512 bit-times
- At 10G: 1 quanta = 512 / 10,000,000,000 = 51.2 ns
- At 100G: 1 quanta = 512 / 100,000,000,000 = 5.12 ns
- Max value 0xFFFF = 65535 quanta

### 2.3 PFC Headroom Calculation

The switch must reserve enough buffer to absorb in-flight packets after PFC PAUSE is sent:

```
Headroom = (Cable_delay + Switch_pipeline_delay + MTU) × Speed

Cable_delay = cable_length × propagation_delay_per_meter
  (fiber: ~5ns/m, copper: ~5ns/m)

Switch_pipeline_delay = time for switch to react to threshold
  (typically 2-5 μs)

Example for 100G, 300m cable, 9000B MTU:
  Cable_RTT = 300m × 5ns/m × 2 = 3000 ns = 3 μs
  Pipeline = 3 μs (typical)
  MTU = 9000B × 8b / 100Gbps = 720 ns

  Headroom = (3 + 3 + 0.72) μs × 100Gbps / 8
           = 6.72 μs × 12.5 GB/s
           = 84 KB per priority per port
```

### 2.4 PFC Deadlock

PFC can cause deadlocks in networks with circular buffer dependencies:

```
  Switch A ──PFC──> Switch B
      ▲                │
      │     PFC        │
      └────────── Switch C

  Circular dependency: A waits for B, B waits for C, C waits for A
```

**Mitigation strategies:**
1. **PFC watchdog**: Detect stuck PFC state, drop after timeout
2. **Limit PFC scope**: Only enable on specific priorities
3. **Use ECN/DCQCN**: Reduce congestion before PFC fires
4. **Separate lossy/lossless**: Keep lossy traffic on unpausable priorities

### 2.5 PFC Configuration Examples

```bash
# NVIDIA/Mellanox NIC
mlnx_qos -i eth0 --pfc=0,0,0,1,0,0,0,0   # PFC on priority 3 only

# Cumulus Linux switch
sudo bash -c 'echo "pfc.3.tx_en = on" >> /etc/cumulus/switchd.conf'
sudo bash -c 'echo "pfc.3.rx_en = on" >> /etc/cumulus/switchd.conf'

# SONiC switch
sudo config interface pfc priority add Ethernet0 3

# Arista EOS
interface Ethernet1
   priority-flow-control priority 3 no-drop

# Cisco Nexus
interface ethernet 1/1
  priority-flow-control mode on
  priority-flow-control watch-dog-interval on
```

## 3. Enhanced Transmission Selection (ETS) - IEEE 802.1Qaz

### 3.1 Concept

ETS defines how bandwidth is allocated across traffic classes (TCs) when there is contention.

### 3.2 Transmission Selection Algorithms

| Algorithm | Behavior |
|-----------|----------|
| Strict Priority | Always served first (can starve lower) |
| ETS (Weighted) | Bandwidth shared by configured weights |
| Vendor Specific | Implementation-defined |

### 3.3 Traffic Class Mapping

```
Priority → Traffic Class → Queue → Scheduling

Example mapping:
  Priority 0 → TC0 (Best Effort)     → 50% BW (ETS)
  Priority 1 → TC0 (Best Effort)     →
  Priority 2 → TC0 (Best Effort)     →
  Priority 3 → TC3 (RoCE/Lossless)   → 50% BW (ETS)
  Priority 4 → TC0 (Best Effort)     →
  Priority 5 → TC0 (Best Effort)     →
  Priority 6 → TC6 (Management)      → Strict Priority
  Priority 7 → TC0 (Best Effort)     →
```

### 3.4 ETS Configuration

```bash
# NVIDIA NIC: Assign bandwidth weights
mlnx_qos -i eth0 --tsa=ets,ets,ets,ets,ets,ets,strict,ets \
    --tcbw=13,13,13,25,12,12,0,12

# Cumulus Linux
nv set qos egress-queue-mapping default-global switch-priority 3 traffic-class 3
nv set qos egress-scheduler default-global traffic-class 3 mode dwrr
nv set qos egress-scheduler default-global traffic-class 3 bw-percent 50

# SONiC
# /etc/sonic/qos.json configuration
```

## 4. DCBX - DCB Capability Exchange Protocol

### 4.1 Overview

DCBX runs over LLDP (Link Layer Discovery Protocol) to negotiate DCB parameters between directly connected devices.

### 4.2 DCBX Modes

| Mode | Behavior |
|------|----------|
| Willing | Accept peer's configuration |
| Non-willing | Insist on local configuration |
| CEE (legacy) | Pre-standard Cisco/Intel/NVIDIA format |
| IEEE | Standard IEEE 802.1Qaz |

### 4.3 DCBX TLVs

- **ETS Configuration TLV**: Priority-to-TC mapping, BW allocation
- **ETS Recommendation TLV**: Suggested configuration
- **PFC Configuration TLV**: PFC-enabled priorities
- **Application Priority TLV**: Protocol-to-priority mapping

### 4.4 DCBX Configuration

```bash
# View DCBX state
lldptool -t -i eth0 -V IEEE-DCBX
lldptool -t -i eth0 -V PFC
lldptool -t -i eth0 -V ETS-CFG

# Set willing mode
lldptool -T -i eth0 -V IEEE-DCBX willing=yes

# Disable DCBX (use manual config)
lldptool -T -i eth0 -V IEEE-DCBX enableTx=no

# On Mellanox NIC, DCBX mode:
mlnx_qos -i eth0 --dcbx=os  # OS-controlled DCBX
mlnx_qos -i eth0 --dcbx=fw  # Firmware-controlled DCBX
```

## 5. ECN (Explicit Congestion Notification) - RFC 3168

### 5.1 ECN in IP Header

ECN uses 2 bits in the IPv4 TOS field (or IPv6 Traffic Class):

```
IPv4 TOS byte:
  +---+---+---+---+---+---+---+---+
  |     DSCP (6 bits)    |ECN| ECN|
  +---+---+---+---+---+---+---+---+
                          ECT  CE
```

| ECN Field | Binary | Meaning |
|-----------|--------|---------|
| Not-ECT | 00 | Not ECN-Capable Transport |
| ECT(1) | 01 | ECN-Capable Transport |
| ECT(0) | 10 | ECN-Capable Transport |
| CE | 11 | Congestion Experienced |

### 5.2 ECN at Switches (RED/WRED)

Switches mark packets with CE when queue depth exceeds thresholds:

```
Marking Probability
  1.0 ┤                    ╱────────
      │                   ╱
      │                  ╱
      │                 ╱
  0.0 ┤────────────────╱
      └────────────────┬──────┬────── Queue Depth
                     Kmin    Kmax

  Below Kmin: No marking (0% probability)
  Between Kmin and Kmax: Linear increase
  Above Kmax: Mark all (100% probability)
```

### 5.3 Switch ECN Configuration

```bash
# Cumulus Linux
nv set qos roce enable on  # Auto-configures ECN for RoCE

# Manual ECN config on Cumulus
nv set qos congestion-control default-global traffic-class 3 ecn enable
nv set qos congestion-control default-global traffic-class 3 min-threshold 150KB
nv set qos congestion-control default-global traffic-class 3 max-threshold 1500KB

# SONiC ECN config
sudo ecnconfig -p AZURE_LOSSLESS -gmin 150000 -gmax 1500000 -gdrop 100

# Arista EOS
random-detect ecn minimum-threshold 150 kbytes maximum-threshold 1500 kbytes
```

## 6. DCQCN (Data Center QCN) - RoCE Congestion Control

### 6.1 Architecture

DCQCN is an end-to-end congestion control for RoCE, combining ECN with rate-based control:

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Sender  │    │  Switch  │    │ Receiver │
│  (RP)    │──>│   (CP)   │──>│  (NP)    │
│          │    │          │    │          │
│Rate adj. │    │ECN mark  │    │Generate  │
│on CNP rx │    │on congest│    │CNP on CE │
└──────────┘    └──────────┘    └──────────┘
     ▲                               │
     │         CNP packet             │
     └───────────────────────────────┘
```

**Roles:**
- **CP (Congestion Point)**: Switch that marks packets with ECN
- **NP (Notification Point)**: Receiver that generates CNPs on seeing CE
- **RP (Reaction Point)**: Sender that adjusts rate on receiving CNPs

### 6.2 DCQCN Algorithm Details

**Rate Decrease (on CNP reception):**
```
alpha = (1 - g) * alpha + g  # g is gain factor (typically 1/256)
Rate_target = Rate * (1 - alpha/2)
Rate = Rate_target
```

**Rate Increase (timer-based, no CNP):**
```
Timer fires every T microseconds:
  if byte_counter >= B:
    // Additive increase
    Rate_target += R_AI  # (additive increase constant)
    Rate = (Rate_target + Rate) / 2
    byte_counter = 0

  // Hyper increase after F timer firings without CNP
  if timer_count >= F:
    Rate_target += R_HAI  # (hyper additive increase)
    Rate = (Rate_target + Rate) / 2
```

### 6.3 DCQCN Parameters (mlx5)

```bash
# View current DCQCN parameters
cat /sys/class/net/eth0/ecn/roce_rp/*
cat /sys/class/net/eth0/ecn/roce_np/*

# Enable ECN/DCQCN for priority 3
echo 1 > /sys/class/net/eth0/ecn/roce_np/enable/3
echo 1 > /sys/class/net/eth0/ecn/roce_rp/enable/3

# Key RP (Reaction Point) parameters:
# Rate reduction on CNP (initial alpha)
echo 1024 > /sys/class/net/eth0/ecn/roce_rp/init_alpha/3  # 0-1023

# Decrease factor
echo 1 > /sys/class/net/eth0/ecn/roce_rp/dcqcn_G/3  # gain factor

# Timer period (microseconds)
echo 55 > /sys/class/net/eth0/ecn/roce_rp/dcqcn_T/3

# Additive increase rate (Mbps)
echo 5 > /sys/class/net/eth0/ecn/roce_rp/rate_to_set_on_first_cnp/3

# Key NP (Notification Point) parameters:
# CNP generation interval
echo 0 > /sys/class/net/eth0/ecn/roce_np/min_time_between_cnps/3  # microseconds
echo 1 > /sys/class/net/eth0/ecn/roce_np/cnp_dscp/3  # DSCP for CNPs
```

## 7. Complete RoCE QoS Pipeline

```
Application
    │
    │ DSCP in ToS (e.g., 26)
    ▼
NIC egress
    │ Trust mode: DSCP or PCP
    │ Map DSCP → Priority (e.g., 26 → 3)
    │ Map Priority → TC (e.g., 3 → TC3)
    ▼
802.1Q VLAN tag
    │ PCP = Priority (3)
    ▼
Switch ingress
    │ Trust DSCP or PCP
    │ Map to internal TC
    │ Buffer allocation per TC
    │ ECN marking if congested
    │ PFC PAUSE if buffer critical
    ▼
Switch egress
    │ ETS scheduling
    │ Strict priority or weighted
    ▼
Remote NIC ingress
    │ PFC if buffer full
    │ ECN → generate CNP
    │ Deliver to QP
    ▼
Application
```

## 8. Monitoring DCB State

```bash
# NIC-side
mlnx_qos -i eth0                    # Full QoS state
ethtool -S eth0 | grep pfc          # PFC counters
ethtool -S eth0 | grep pause        # Pause frame counters
ethtool -S eth0 | grep ecn          # ECN counters
ethtool -S eth0 | grep cnp          # CNP counters

# Key counters:
#  rx_pfc_pri3_pause   - PFC frames received for pri 3
#  tx_pfc_pri3_pause   - PFC frames sent for pri 3
#  rx_pci_signal_target_abort - potential PFC storm indicator
#  rx_ecn_marked_pkts  - ECN CE-marked packets received

# Switch-side (Cumulus)
nv show qos counters
ethtool -S swp1 | grep pfc

# LLDP/DCBX status
lldpctl
lldptool -t -i eth0 -V PFC
```
