---
title: "Ethernet Fundamentals - Complete Technical Reference"
category: web_content
tags:
  - ethernet
  - networking
  - layer2
  - 802.3
  - FEC
  - SerDes
  - PAM4
  - NRZ
  - PHY
  - flow-control
  - PFC
  - VLAN
  - jumbo-frames
  - RDMA
  - RoCE
  - data-center
---

# Ethernet Fundamentals - Complete Technical Reference

## 1. Introduction

Ethernet is the dominant Layer 2 networking technology in modern data centers and the
foundation upon which RDMA over Converged Ethernet (RoCE) operates. Understanding
Ethernet at a deep level is essential for anyone deploying or troubleshooting RDMA
workloads. This document provides a comprehensive reference covering frame formats,
addressing, speed evolution, physical layer technologies, flow control mechanisms,
and VLAN tagging.

## 2. Ethernet Frame Format

### 2.1 Standard Ethernet II (DIX) Frame

The Ethernet II frame is the most widely used frame format in modern networks.

```
+----------+-----+--------+--------+-----------+---------+-----+----------+
| Preamble | SFD | Dst MAC| Src MAC| EtherType | Payload | FCS | IFG      |
| 7 bytes  | 1B  | 6 bytes| 6 bytes| 2 bytes   | 46-1500 | 4B  | 12 bytes |
+----------+-----+--------+--------+-----------+---------+-----+----------+
```

#### Preamble (7 bytes)
- Pattern: `10101010` repeated 7 times (0xAA)
- Purpose: Clock synchronization for the receiving NIC
- Allows the receiver PLL (Phase-Locked Loop) to lock onto the sender's clock
- Not included in frame size calculations
- At 10 Gbps, the preamble takes approximately 5.6 nanoseconds

#### Start Frame Delimiter - SFD (1 byte)
- Pattern: `10101011` (0xAB)
- Marks the end of the preamble and the beginning of the frame
- The final `11` bit pattern distinguishes it from the preamble

#### Destination MAC Address (6 bytes)
- The target hardware address
- If the least significant bit of the first byte is 0, it is a unicast address
- If the least significant bit of the first byte is 1, it is a multicast address
- All bits set to 1 (FF:FF:FF:FF:FF:FF) indicates a broadcast

#### Source MAC Address (6 bytes)
- The sender's hardware address
- Always a unicast address (least significant bit of first byte is 0)
- Must not be broadcast or multicast

#### EtherType / Length (2 bytes)
- Values >= 0x0600 (1536): Indicates the protocol of the payload (Ethernet II)
- Values <= 0x05DC (1500): Indicates the payload length (IEEE 802.3)
- Common EtherTypes:
  - `0x0800` - IPv4
  - `0x0806` - ARP
  - `0x86DD` - IPv6
  - `0x8100` - 802.1Q VLAN tagged frame
  - `0x88A8` - 802.1ad QinQ (S-Tag / Service VLAN)
  - `0x8915` - RoCEv1 (RDMA over Converged Ethernet version 1)
  - `0x88CC` - LLDP (Link Layer Discovery Protocol)
  - `0x8809` - Slow Protocols (LACP, OAM)
  - `0x88F7` - PTP (Precision Time Protocol, IEEE 1588)

#### Payload (46-1500 bytes)
- Minimum 46 bytes (frames shorter are padded to meet minimum frame size of 64 bytes)
- Maximum 1500 bytes for standard Ethernet (MTU - Maximum Transmission Unit)
- Maximum 9000-9216 bytes for jumbo frames (vendor-dependent)
- Contains the encapsulated upper-layer protocol data

#### Frame Check Sequence - FCS (4 bytes)
- CRC-32 checksum computed over Dst MAC, Src MAC, EtherType, and Payload
- Polynomial: x^32 + x^26 + x^23 + x^22 + x^16 + x^12 + x^11 + x^10 + x^8 + x^7 + x^5 + x^4 + x^2 + x + 1
- Detects bit errors in transmission
- Frames with FCS errors are silently discarded (no retransmission at L2)
- Monitoring FCS/CRC errors is critical for RDMA troubleshooting:

```bash
# Check for CRC errors on Linux
ethtool -S eth0 | grep -i crc
ethtool -S eth0 | grep -i fcs

# For Mellanox/NVIDIA NICs
ethtool -S eth0 | grep rx_crc_errors_phy
```

#### Inter-Frame Gap - IFG (12 bytes)
- Minimum idle time between frames
- 96 bit-times at any speed
- At 10 Gbps: 9.6 nanoseconds
- At 100 Gbps: 0.96 nanoseconds

### 2.2 Frame Size Summary

```
Minimum frame size on wire: 64 bytes (excl. preamble, SFD, IFG)
Maximum frame size on wire: 1518 bytes (standard) or 1522 bytes (802.1Q tagged)
Minimum payload: 46 bytes
Maximum payload (MTU): 1500 bytes (standard), 9000+ bytes (jumbo)

Total overhead per frame on wire (including preamble, SFD, IFG):
  Preamble (7) + SFD (1) + Frame (64-1518) + IFG (12) = 84-1538 bytes
```

### 2.3 IEEE 802.3 Frame Format

The 802.3 frame differs slightly from Ethernet II:

```
+----------+-----+--------+--------+--------+------+---------+-----+
| Preamble | SFD | Dst MAC| Src MAC| Length | LLC  | Payload | FCS |
| 7 bytes  | 1B  | 6 bytes| 6 bytes| 2 bytes| 3-5B | var     | 4B  |
+----------+-----+--------+--------+--------+------+---------+-----+
```

- The Length field replaces EtherType (values <= 1500)
- LLC (Logical Link Control) header follows with DSAP, SSAP, and Control fields
- SNAP (Sub-Network Access Protocol) may extend LLC for protocol identification
- Ethernet II is overwhelmingly dominant in modern networks

## 3. MAC Addressing

### 3.1 MAC Address Format

A MAC (Media Access Control) address is a 48-bit (6-byte) identifier:

```
Format: XX:XX:XX:YY:YY:YY
        |------| |------|
         OUI     NIC-specific

Example: 00:1A:2B:3C:4D:5E
         B0:26:28:FF:FE:12  (NVIDIA/Mellanox ConnectX)
```

### 3.2 Address Types

#### Unicast
- Least significant bit of the first octet is 0
- Identifies a single network interface
- Example: `00:1A:2B:3C:4D:5E` (first octet 0x00, binary: 00000000, LSB=0)

#### Multicast
- Least significant bit of the first octet is 1
- Delivered to a group of interfaces
- Example: `01:00:5E:00:00:01` (first octet 0x01, binary: 00000001, LSB=1)
- IPv4 multicast maps to MAC: 01:00:5E + lower 23 bits of IP multicast address
- IPv6 multicast maps to MAC: 33:33 + lower 32 bits of IPv6 multicast address

#### Broadcast
- All bits set: `FF:FF:FF:FF:FF:FF`
- Delivered to all interfaces on the L2 segment
- ARP requests use broadcast destination

### 3.3 OUI (Organizationally Unique Identifier)

The first 3 bytes of a MAC address identify the manufacturer:

```
Common OUI assignments:
  00:02:C9  - Mellanox Technologies (legacy)
  B8:CE:F6  - Mellanox Technologies
  B0:26:28  - NVIDIA (ConnectX series)
  04:3F:72  - NVIDIA/Mellanox
  7C:FE:90  - Intel Corporation
  3C:FD:FE  - Intel Corporation (Ethernet server adapters)
  00:50:56  - VMware
  00:15:5D  - Microsoft Hyper-V
  52:54:00  - QEMU/KVM virtual NIC
  E4:43:4B  - Broadcom
```

### 3.4 Locally Administered Addresses

- Second least significant bit of the first octet set to 1
- Indicates the address is not globally unique
- Used for virtual interfaces, containers, VMs
- Example: `02:xx:xx:xx:xx:xx` or `06:xx:xx:xx:xx:xx`

```bash
# View MAC address on Linux
ip link show eth0
# Output: link/ether b0:26:28:a1:b2:c3 brd ff:ff:ff:ff:ff:ff

# View MAC address of RDMA device
cat /sys/class/infiniband/mlx5_0/node_guid
cat /sys/class/infiniband/mlx5_0/ports/1/gid_attrs/ndevs/0
```

## 4. Ethernet Speed Evolution

### 4.1 Historical Speeds

| Speed    | Standard      | Year | Medium            | Notes                    |
|----------|---------------|------|-------------------|--------------------------|
| 10 Mbps  | 802.3         | 1983 | Coax (10BASE5)    | Original Ethernet        |
| 10 Mbps  | 802.3i        | 1990 | Twisted pair      | 10BASE-T                 |
| 100 Mbps | 802.3u        | 1995 | Twisted pair      | Fast Ethernet            |
| 1 Gbps   | 802.3z        | 1998 | Fiber             | Gigabit Ethernet         |
| 1 Gbps   | 802.3ab       | 1999 | Cat5e copper      | 1000BASE-T               |
| 10 Gbps  | 802.3ae       | 2002 | Fiber             | 10 Gigabit Ethernet      |
| 10 Gbps  | 802.3an       | 2006 | Cat6a copper      | 10GBASE-T                |
| 40 Gbps  | 802.3ba       | 2010 | Fiber/copper      | 4x10G lanes              |
| 100 Gbps | 802.3ba       | 2010 | Fiber             | 10x10G or 4x25G lanes   |
| 25 Gbps  | 802.3by       | 2016 | Fiber/copper      | Single lane              |
| 50 Gbps  | 802.3cd       | 2018 | Fiber/copper      | Single lane (PAM4)       |
| 200 Gbps | 802.3bs       | 2017 | Fiber             | 4x50G lanes             |
| 400 Gbps | 802.3bs       | 2017 | Fiber             | 8x50G or 4x100G lanes   |
| 100 Gbps | 802.3ck       | 2022 | Copper/fiber      | Single lane 100G         |
| 200 Gbps | 802.3ck       | 2022 | Copper/fiber      | 2x100G lanes            |
| 400 Gbps | 802.3ck       | 2022 | Copper/fiber      | 4x100G lanes            |
| 800 Gbps | 802.3df       | 2024 | Fiber             | 8x100G lanes            |

### 4.2 Data Center Relevant Speeds

Modern data center RDMA deployments primarily use:

- **25 GbE**: Entry-level RDMA, single lane NRZ. ConnectX-4 and later.
- **100 GbE**: Mainstream RDMA, 4x25G NRZ or 2x50G PAM4. ConnectX-5/6.
- **200 GbE**: High-performance RDMA, 4x50G PAM4. ConnectX-6.
- **400 GbE**: Next-gen RDMA, 4x100G PAM4. ConnectX-7, BlueField-3.
- **800 GbE**: Emerging, 8x100G PAM4. ConnectX-8.

## 5. Auto-Negotiation

### 5.1 Purpose

Auto-negotiation (IEEE 802.3 Clause 28 for BASE-T, Clause 73 for backplane/DAC)
allows two link partners to automatically negotiate:
- Speed (highest common speed)
- Duplex mode (full or half)
- Flow control capabilities (PAUSE, PFC)
- FEC mode (RS-FEC, FC-FEC, or none)

### 5.2 Priority Resolution

When both partners support multiple speeds, the highest common speed is selected.
Priority order (highest to lowest):
1. 400GBASE-CR4 / 200GBASE-CR4 / 100GBASE-CR4
2. 100GBASE-CR2
3. 50GBASE-CR
4. 25GBASE-CR
5. 40GBASE-CR4
6. 10GBASE-T / 10GBASE-CR
7. 1000BASE-T

### 5.3 Auto-Negotiation for Copper DAC

For direct-attach copper (DAC) cables commonly used in RDMA deployments:

```bash
# Check auto-negotiation status
ethtool eth0 | grep -i "auto-negotiation"

# Force speed and disable auto-negotiation (use with caution)
ethtool -s eth0 speed 100000 duplex full autoneg off

# Enable auto-negotiation
ethtool -s eth0 autoneg on

# Check advertised and supported link modes
ethtool eth0 | grep -A 20 "Supported link modes"
```

### 5.4 Full Duplex vs Half Duplex

- **Half Duplex**: Send OR receive, not both. Uses CSMA/CD. Obsolete in data centers.
- **Full Duplex**: Simultaneous send and receive. All modern data center links.
- RDMA requires full-duplex operation.
- At 1 Gbps and above, only full duplex is supported.

## 6. IEEE 802.3 Standards for Data Centers

### 6.1 802.3ae - 10 Gigabit Ethernet (2002)

- First Ethernet standard to be full-duplex only
- No CSMA/CD, no half-duplex mode
- Key PHY types:
  - 10GBASE-SR: 850nm MMF, up to 300m (OM3) or 400m (OM4)
  - 10GBASE-LR: 1310nm SMF, up to 10km
  - 10GBASE-ER: 1550nm SMF, up to 40km
- Uses 64b/66b line encoding (replaces 8b/10b, more efficient)
- Single-lane SerDes at 10.3125 Gbaud

### 6.2 802.3ba - 40/100 Gigabit Ethernet (2010)

- 40 GbE: 4 lanes x 10G (NRZ)
- 100 GbE: 10 lanes x 10G or 4 lanes x 25G (NRZ)
- Key PHY types:
  - 40GBASE-SR4: 4x 850nm MMF, up to 100m (OM3) / 150m (OM4)
  - 40GBASE-CR4: 4x copper DAC, up to 5-7m
  - 40GBASE-LR4: 4x 1310nm CWDM SMF, up to 10km
  - 100GBASE-SR4: 4x 850nm MMF, up to 70m (OM3) / 100m (OM4)
  - 100GBASE-CR4: 4x copper DAC, up to 5m
  - 100GBASE-LR4: 4x 1310nm CWDM SMF, up to 10km

### 6.3 802.3by - 25 Gigabit Ethernet (2016)

- Single-lane 25G (NRZ at 25.78125 Gbaud)
- PHY types:
  - 25GBASE-SR: 850nm MMF, up to 70m (OM3) / 100m (OM4)
  - 25GBASE-CR: Copper DAC, up to 5m
  - 25GBASE-CR-S: Copper DAC, short reach, reduced power
- Popular for server-to-ToR connections in early RDMA deployments

### 6.4 802.3bs - 200/400 Gigabit Ethernet (2017)

- 200 GbE: 4 lanes x 50G (PAM4)
- 400 GbE: 8 lanes x 50G (PAM4) or 4 lanes x 100G (PAM4)
- Key PHY types:
  - 200GBASE-SR4: 4x 850nm MMF PAM4
  - 200GBASE-CR4: 4x copper DAC PAM4, up to 3m
  - 200GBASE-DR4: 4x 1310nm SMF, up to 500m
  - 200GBASE-FR4: 4x 1310nm CWDM SMF, up to 2km
  - 200GBASE-LR4: 4x 1310nm CWDM SMF, up to 10km
  - 400GBASE-SR8: 8x 850nm MMF PAM4
  - 400GBASE-DR4: 4x 1310nm SMF, up to 500m
  - 400GBASE-FR4: 4x 1310nm CWDM SMF, up to 2km

### 6.5 802.3ck - 100/200/400G per Lane (2022)

- 100G per electrical lane
- 200 GbE: 2 lanes x 100G
- 400 GbE: 4 lanes x 100G
- Key PHY types:
  - 100GBASE-CR: Single-lane copper DAC, up to 2m
  - 200GBASE-CR2: 2-lane copper DAC
  - 400GBASE-CR4: 4-lane copper DAC
- Enables higher-density connections with fewer lanes
- Critical for ConnectX-7 and BlueField-3 deployments

### 6.6 802.3df - 800 Gigabit Ethernet (2024)

- 800 GbE: 8 lanes x 100G (PAM4)
- PHY types under development and standardization:
  - 800GBASE-DR8: 8x 1310nm SMF
  - 800GBASE-SR8: 8x 850nm MMF
- Uses OSFP or QSFP-DD800 form factor
- Targets AI/ML training cluster interconnects

## 7. Forward Error Correction (FEC)

### 7.1 Why FEC is Needed

At high speeds (25G+), the bit error rate (BER) of the physical channel increases.
FEC adds redundant data to detect and correct bit errors without retransmission.
This is critical for RDMA because:
- RDMA has no built-in L2 retransmission (unlike TCP)
- Even a single bit error causes packet drop, leading to RDMA transport retries
- FEC corrects errors transparently, maintaining link quality

### 7.2 FEC Types

#### FC-FEC (Firecode FEC / Clause 74 / BASE-R FEC)
- Also called Firecode or Clause 74 FEC
- Correction capability: Corrects burst errors up to 11 bits
- Latency overhead: ~50-100 nanoseconds
- Used at: 10G (optional), 25G, 40G
- Encoding: Uses Hamming-like code
- Lower correction capability but lower latency

#### RS-FEC (Reed-Solomon FEC / Clause 91 / Clause 108)
- Also called Clause 91 (for 25G/100G) or Clause 108 (for 50G/100G/200G/400G)
- Correction capability: Can correct up to ~7 symbol errors per codeword
- Latency overhead: ~100-200 nanoseconds
- Used at: 25G (recommended), 50G+, 100G+, 200G+, 400G+
- RS(528,514) for Clause 91, RS(544,514) for Clause 108
- Mandatory for PAM4-based links (50G+ per lane)

### 7.3 When to Use Which FEC

| Speed       | Recommended FEC    | Notes                                    |
|-------------|--------------------|------------------------------------------|
| 10G         | None or FC-FEC     | Typically not needed                     |
| 25G NRZ     | RS-FEC (Clause 91) | Recommended for all 25G links            |
| 50G PAM4    | RS-FEC (Clause 108)| Mandatory                                |
| 100G NRZ    | RS-FEC (Clause 91) | 4x25G lanes                              |
| 100G PAM4   | RS-FEC (Clause 108)| 2x50G or 1x100G lanes                   |
| 200G PAM4   | RS-FEC (Clause 108)| Mandatory                                |
| 400G PAM4   | RS-FEC (Clause 108)| Mandatory                                |

### 7.4 FEC Monitoring

```bash
# Check FEC mode on NVIDIA NICs
ethtool --show-fec eth0

# Set FEC mode
ethtool --set-fec eth0 encoding rs

# Monitor FEC corrected/uncorrected errors
ethtool -S eth0 | grep -i fec
# Example output:
#   rx_fec_corrected_blocks_phy: 1523456
#   rx_fec_uncorrectable_blocks_phy: 0

# High corrected count is normal; uncorrectable errors indicate link problems
# Rule of thumb: uncorrectable > 0 means potential cable/optic issue

# Check FEC statistics via mlx5
ethtool -S eth0 | grep -E "(fec|corrected|uncorrect)"
```

### 7.5 FEC and Latency Impact

FEC adds latency to every frame:
- FC-FEC: ~50 ns additional latency
- RS-FEC (Clause 91): ~100 ns additional latency
- RS-FEC (Clause 108): ~120-150 ns additional latency

For ultra-low-latency RDMA applications (HFT), FEC latency can be significant.
However, disabling FEC on PAM4 links will cause unacceptable error rates.

## 8. Lane Speeds and SerDes

### 8.1 NRZ (Non-Return-to-Zero) Signaling

- Binary signaling: Two voltage levels (0 and 1)
- One bit per symbol (baud rate = bit rate before encoding)
- Used for lane speeds up to 25G (with 64b/66b encoding: 25.78125 Gbaud)
- Simple, proven technology
- Electrical lane speeds: 1G, 10G, 25G

### 8.2 PAM4 (Pulse Amplitude Modulation, 4-level)

- Four voltage levels: 0, 1, 2, 3 (encoding 2 bits per symbol)
- Two bits per symbol (baud rate = bit rate / 2)
- Used for lane speeds of 50G and above
- 50G PAM4: 26.5625 Gbaud
- 100G PAM4: 53.125 Gbaud
- More susceptible to noise than NRZ (requires FEC)
- Reduced signal-to-noise ratio: ~9.5 dB penalty vs NRZ

### 8.3 SerDes (Serializer/Deserializer)

SerDes is the interface between the MAC and the PHY that converts parallel data to
serial and vice versa.

```
Lane speed evolution:
  Generation 1: 10G NRZ   (10.3125 Gbaud) - 802.3ae (10G), 802.3ba (40G/100G)
  Generation 2: 25G NRZ   (25.78125 Gbaud) - 802.3by (25G), 802.3ba (100G)
  Generation 3: 50G PAM4  (26.5625 Gbaud)  - 802.3cd (50G), 802.3bs (200G/400G)
  Generation 4: 100G PAM4 (53.125 Gbaud)   - 802.3ck (100G/200G/400G)
  Generation 5: 200G PAM4 (106.25 Gbaud)   - 802.3df (800G), future 1.6T

Speed construction:
  25 GbE  = 1 x 25G NRZ
  50 GbE  = 1 x 50G PAM4  or 2 x 25G NRZ
  100 GbE = 4 x 25G NRZ   or 2 x 50G PAM4  or 1 x 100G PAM4
  200 GbE = 4 x 50G PAM4  or 2 x 100G PAM4
  400 GbE = 8 x 50G PAM4  or 4 x 100G PAM4
  800 GbE = 8 x 100G PAM4 or 4 x 200G PAM4 (future)
```

## 9. PHY Types

### 9.1 Naming Convention

The PHY type name follows the pattern: `[Speed]BASE-[Encoding][Reach][Lanes]`

```
Examples:
  100GBASE-CR4
  |   |    || |
  |   |    || +-- 4 lanes
  |   |    |+---- C = Copper
  |   |    +----- R = Short reach (typically DAC)
  |   +---------- BASE = Baseband signaling
  +-------------- 100G = Speed

  100GBASE-SR4
  |   |    || |
  |   |    || +-- 4 lanes
  |   |    |+---- S = Short reach (multimode fiber)
  |   |    +----- R = LAN PHY
  |   +---------- BASE = Baseband signaling
  +-------------- 100G = Speed
```

### 9.2 Common PHY Types for RDMA

#### BASE-CR (Copper, Short Reach - DAC)
- Direct Attach Copper (DAC) cables
- Passive: up to 3-5m (speed dependent)
- Active: up to 7m
- Lowest cost, lowest latency
- Most common for intra-rack RDMA connections
- Examples: 25GBASE-CR, 100GBASE-CR4, 200GBASE-CR4, 400GBASE-CR4

#### BASE-SR (Short Reach - Multimode Fiber)
- Uses multimode fiber (MMF) with 850nm VCSEL lasers
- Reach: 70-400m depending on fiber type (OM3/OM4/OM5) and speed
- Most common for inter-rack connections within a data center
- Examples: 25GBASE-SR, 100GBASE-SR4, 200GBASE-SR4

#### BASE-LR (Long Reach - Single-Mode Fiber)
- Uses single-mode fiber (SMF) with 1310nm lasers
- Reach: up to 10km
- Used for connections between data center buildings
- Higher cost than SR
- Examples: 100GBASE-LR4, 400GBASE-LR4

#### BASE-DR (Data Center Reach - Single-Mode Fiber)
- Designed specifically for data center use
- Uses single-mode fiber (SMF) with 1310nm lasers
- Reach: up to 500m
- Single fiber per lane (parallel SMF)
- Examples: 100GBASE-DR, 400GBASE-DR4, 800GBASE-DR8

#### BASE-FR (Far Reach)
- Uses single-mode fiber (SMF) with CWDM wavelengths
- Reach: up to 2km
- Multiple wavelengths over a single fiber pair
- Examples: 400GBASE-FR4

### 9.3 PHY Reach Summary

| PHY Type      | Medium | Reach       | Wavelength | Typical Use           |
|---------------|--------|-------------|------------|-----------------------|
| BASE-CR       | DAC    | 1-7m        | N/A        | Intra-rack            |
| BASE-SR       | MMF    | 70-400m     | 850nm      | Inter-rack (building) |
| BASE-DR       | SMF    | 500m        | 1310nm     | Data center backbone  |
| BASE-FR       | SMF    | 2km         | 1310nm CWDM| Campus/inter-building |
| BASE-LR       | SMF    | 10km        | 1310nm     | Metro/inter-building  |
| BASE-ER       | SMF    | 40km        | 1550nm     | Metro/long-haul       |

## 10. Ethernet Flow Control

### 10.1 IEEE 802.3x PAUSE (Global Flow Control)

The original Ethernet flow control mechanism:

- Sends a PAUSE frame to the link partner to stop ALL traffic
- Destination MAC: `01:80:C2:00:00:01` (well-known multicast)
- EtherType: `0x8808` (MAC Control)
- Contains a pause duration in quanta (1 quantum = 512 bit-times)
- Maximum pause time: 65535 quanta

```
PAUSE Frame Format:
+--------+--------+-----------+---------+--------------+------+-----+
| Dst MAC| Src MAC| EtherType | OpCode  | Pause Time   | Pad  | FCS |
| 6B     | 6B     | 0x8808    | 0x0001  | 2 bytes      | 42B  | 4B  |
+--------+--------+-----------+---------+--------------+------+-----+
```

**Problems with 802.3x PAUSE for RDMA:**
- Pauses ALL traffic on the link (all priorities, all traffic classes)
- Creates head-of-line blocking
- Cannot distinguish between RDMA traffic and best-effort traffic
- If storage traffic triggers PAUSE, it also pauses RDMA and vice versa

### 10.2 IEEE 802.1Qbb Priority-based Flow Control (PFC)

PFC extends PAUSE to operate on individual priority levels:

- Sends per-priority PAUSE frames
- Can pause up to 8 traffic classes independently (priorities 0-7)
- Allows RDMA traffic to be lossless while other traffic remains lossy
- Essential for RoCEv2 deployments requiring lossless Ethernet

```
PFC Frame Format:
+--------+--------+-----------+---------+----------+----+------+-----+
| Dst MAC| Src MAC| EtherType | OpCode  | Priority | T0 | ...  | FCS |
| 6B     | 6B     | 0x8808    | 0x0101  | Enable   | 2B | T7   | 4B  |
|        |        |           |         | Vector   |    | (2B) |     |
+--------+--------+-----------+---------+----------+----+------+-----+
```

- Priority Enable Vector: 8 bits, one per priority (1=enabled, 0=disabled)
- T0-T7: Pause duration for each priority (in quanta)

#### Typical RDMA PFC Configuration

```
Priority mapping for RDMA:
  Priority 3 (or 4): RDMA/RoCEv2 traffic - PFC enabled (lossless)
  Priority 0: Best-effort traffic - PFC disabled (lossy)
  Priority 6: Network control - PFC disabled (lossy)

# Configure PFC on NVIDIA NIC using mlnx_qos
mlnx_qos -i eth0 --pfc 0,0,0,1,0,0,0,0

# This enables PFC on priority 3 only
# Format: --pfc p0,p1,p2,p3,p4,p5,p6,p7

# Verify PFC configuration
mlnx_qos -i eth0

# Monitor PFC counters
ethtool -S eth0 | grep pfc
# tx_pfc_pause_storm_warning: 0
# rx_prio3_pause: 15234
# tx_prio3_pause: 8921
# rx_prio3_pause_duration: 234567
```

### 10.3 DCBX (Data Center Bridging Capability Exchange)

DCBX is the protocol used to automatically negotiate DCB settings between peers:
- Uses LLDP (Link Layer Discovery Protocol) as transport
- Negotiates: PFC, ETS (Enhanced Transmission Selection), Application Priority
- Two versions: CEE (Converged Enhanced Ethernet, pre-standard) and IEEE

```bash
# Check DCBX status on NVIDIA NIC
mlnx_qos -i eth0

# Enable DCBX in willing mode (accept switch settings)
mlnx_qos -i eth0 --dcbx_mode firmware

# Check LLDP/DCBX neighbors
lldptool -t -i eth0 -V PFC
lldptool -t -i eth0 -V ETS-CFG
lldptool -t -i eth0 -V APP
```

### 10.4 PFC Storm Prevention

PFC storms can deadlock the network if a device continuously sends PFC frames:

```bash
# Enable PFC storm prevention on NVIDIA NICs
ethtool --set-priv-flags eth0 pfcStormPrevention on

# Check PFC watchdog status
ethtool --show-priv-flags eth0 | grep pfc

# Monitor for PFC storms
ethtool -S eth0 | grep pfc_stall
```

## 11. VLANs

### 11.1 IEEE 802.1Q VLAN Tagging

802.1Q inserts a 4-byte VLAN tag into the Ethernet frame:

```
Standard frame:
+--------+--------+-----------+---------+-----+
| Dst MAC| Src MAC| EtherType | Payload | FCS |
+--------+--------+-----------+---------+-----+

802.1Q tagged frame:
+--------+--------+------+------+-----------+---------+-----+
| Dst MAC| Src MAC| TPID | TCI  | EtherType | Payload | FCS |
|        |        |0x8100| 2B   |           |         |     |
+--------+--------+------+------+-----------+---------+-----+

TCI (Tag Control Information) breakdown:
  Bits 15-13: PCP (Priority Code Point) - 3 bits (0-7)
  Bit 12:     DEI (Drop Eligible Indicator) - 1 bit
  Bits 11-0:  VID (VLAN Identifier) - 12 bits (0-4095)
```

- TPID: Tag Protocol Identifier = 0x8100
- PCP: Used for QoS priority (maps to traffic classes for PFC/ETS)
- VID: VLAN ID (0 = priority tagged only, 1 = default, 4095 = reserved)
- Usable VLAN range: 1-4094

### 11.2 PCP to RDMA Priority Mapping

The PCP field is critical for RDMA because it determines which traffic class
the frame belongs to, and therefore whether PFC applies:

```
PCP Value | Default Traffic Type | RDMA Usage
----------|---------------------|------------------
0         | Best Effort (BE)    | Default/non-RDMA
1         | Background (BK)     | Low priority
2         | Excellent Effort    | Standard traffic
3         | Critical Apps (CA)  | Often used for RoCEv2
4         | Video (VI)          | Sometimes used for RoCEv2
5         | Voice (VO)          | High priority
6         | Internetwork Ctrl   | Network control
7         | Network Control     | Highest priority
```

### 11.3 VLAN Configuration for RDMA

```bash
# Create VLAN interface for RDMA
ip link add link eth0 name eth0.100 type vlan id 100

# Set VLAN egress priority mapping (skb priority -> PCP)
ip link set eth0.100 type vlan egress-qos-map 0:0 3:3 4:4

# Set VLAN ingress priority mapping (PCP -> skb priority)
ip link set eth0.100 type vlan ingress-qos-map 0:0 3:3 4:4

# Bring up the VLAN interface
ip link set eth0.100 up
ip addr add 192.168.100.1/24 dev eth0.100

# Verify VLAN configuration
cat /proc/net/vlan/eth0.100

# For RoCE over VLAN, the RDMA GID table automatically
# includes GIDs for VLAN interfaces
ibv_devinfo -v | grep GID
```

### 11.4 QinQ (802.1ad / Double Tagging)

QinQ adds a second VLAN tag (S-Tag) for service provider networks:

```
+--------+--------+------+------+------+------+-----------+---------+-----+
| Dst MAC| Src MAC| S-TPID| S-TCI| C-TPID| C-TCI| EtherType | Payload| FCS |
|        |        |0x88A8|      |0x8100|      |           |        |     |
+--------+--------+------+------+------+------+-----------+---------+-----+
```

- S-Tag (Service Tag): Outer tag, TPID = 0x88A8
- C-Tag (Customer Tag): Inner tag, TPID = 0x8100
- Not commonly used for RDMA but may be encountered in multi-tenant environments

## 12. Jumbo Frames

### 12.1 Definition and Purpose

Jumbo frames are Ethernet frames with an MTU larger than the standard 1500 bytes:
- Typical jumbo MTU: 9000 or 9216 bytes
- Maximum frame size on wire: 9022 bytes (9000 + 14 header + 4 FCS + 4 VLAN)
- Reduces per-packet overhead for large data transfers
- Critical for RDMA performance

### 12.2 Why Jumbo Frames Matter for RDMA

- Larger MTU means fewer packets for the same data volume
- Fewer packets = fewer completions = less CPU overhead
- Larger RDMA messages can be sent in fewer WQEs
- Typical RDMA performance improvement: 10-30% with jumbo frames
- RDMA PMTU (Path MTU) discovery uses IB-level mechanisms

### 12.3 Configuring Jumbo Frames

```bash
# Set MTU on the interface
ip link set eth0 mtu 9000

# Verify MTU
ip link show eth0 | grep mtu

# For VLAN interface, set on both parent and VLAN
ip link set eth0 mtu 9000
ip link set eth0.100 mtu 9000

# Persistent configuration (varies by distro)
# For RHEL/CentOS (NetworkManager):
nmcli connection modify eth0 802-3-ethernet.mtu 9000

# For Ubuntu (netplan):
# /etc/netplan/01-netcfg.yaml:
#   ethernets:
#     eth0:
#       mtu: 9000

# Verify end-to-end MTU with ping
ping -M do -s 8972 192.168.1.2
# -M do: prohibit fragmentation
# -s 8972: 8972 payload + 20 IP header + 8 ICMP header = 9000

# Check RDMA device MTU
cat /sys/class/infiniband/mlx5_0/ports/1/phys_state
ibv_devinfo | grep active_mtu
# 1: 256 bytes
# 2: 512 bytes
# 3: 1024 bytes
# 4: 2048 bytes
# 5: 4096 bytes (IB 4K MTU, corresponds to ~4K RDMA payload)
```

### 12.4 MTU Considerations

- ALL devices in the L2 path must support the same MTU
- Switches, routers, NICs, virtual switches all must be configured
- Mismatched MTU causes packet drops (silent data loss for RDMA)
- RDMA Path MTU is separate from IP MTU but related
- Default Ethernet MTU of 1500 works but is suboptimal for RDMA

```bash
# Troubleshoot MTU issues
# Check for fragmentation (should be 0 for RDMA)
ethtool -S eth0 | grep frag

# Check for drops due to oversized frames
ethtool -S eth0 | grep -i "too_long\|oversize\|jabber"

# Trace path MTU
tracepath 192.168.1.2
```

## 13. Ethernet for RDMA: Key Considerations

### 13.1 RoCEv1 vs RoCEv2 Ethernet Requirements

| Feature           | RoCEv1          | RoCEv2              |
|-------------------|-----------------|----------------------|
| Ethernet frame    | Native Ethernet | UDP/IP/Ethernet      |
| EtherType         | 0x8915          | 0x0800 (IPv4)        |
| Routing           | L2 only         | L3 routable          |
| VLAN required     | Optional        | Optional             |
| PFC required      | Yes             | Recommended (or ECN) |
| ECN support       | No              | Yes (DCQCN)          |
| GID type          | RoCE v1 GID     | RoCE v2 GID (IPv4/6) |

### 13.2 Lossless Ethernet Requirements for RDMA

For reliable RDMA operation over Ethernet:

1. **PFC** must be configured on the correct priority
2. **ETS** should allocate sufficient bandwidth to the RDMA traffic class
3. **DCBX** should be configured consistently between NIC and switch
4. **ECN** (Explicit Congestion Notification) with DCQCN is recommended
5. **FEC** must be properly configured for the link speed
6. **Jumbo frames** (MTU 9000) are strongly recommended
7. **Cable quality** must support the link speed without excessive FEC corrections

### 13.3 Monitoring Ethernet Health for RDMA

```bash
# Comprehensive NIC health check
ethtool eth0                           # Link status, speed, duplex
ethtool -S eth0 | grep -i error       # All error counters
ethtool -S eth0 | grep -i drop        # All drop counters
ethtool -S eth0 | grep -i pause       # Pause frame counters
ethtool -S eth0 | grep -i fec         # FEC counters
ethtool -S eth0 | grep -i pfc         # PFC counters
ethtool --show-fec eth0               # FEC mode
ethtool -m eth0                        # Transceiver diagnostics (DOM)

# Check link flapping
dmesg | grep -i "link.*up\|link.*down"
journalctl -u NetworkManager | grep -i link

# Physical layer diagnostics for NVIDIA NICs
mlxlink -d /dev/mst/mt4125_pciconf0 -m  # Module info
mlxlink -d /dev/mst/mt4125_pciconf0 -e  # Eye opening
mlxlink -d /dev/mst/mt4125_pciconf0 -c  # Counters
```

## 14. Summary

Ethernet is the physical and data-link layer foundation for RoCE-based RDMA networks.
Key takeaways for RDMA practitioners:

- Understand frame formats for packet capture analysis
- MAC addressing is important for GID resolution in RoCEv2
- Choose the right speed and PHY type for your deployment
- FEC is mandatory at 50G+ and critical for RDMA reliability
- PFC provides per-priority flow control essential for lossless RDMA
- VLANs with proper PCP mapping enable QoS for RDMA traffic classes
- Jumbo frames (MTU 9000) significantly improve RDMA performance
- Monitor FCS errors, FEC corrections, and PFC counters for health
