---
title: "RoCE v1 and RoCE v2 Protocol Specification"
category: specifications
tags: [roce, rocev1, rocev2, specification, protocol, udp, ethernet]
---

# RoCE v1 and RoCE v2 Protocol Specification

## 1. Overview

RDMA over Converged Ethernet (RoCE) enables RDMA transport over Ethernet networks. Two versions exist:

- **RoCE v1**: Layer 2 protocol using a dedicated EtherType (0x8915). Same-subnet only.
- **RoCE v2**: Layer 3 routable protocol encapsulated in UDP/IP (port 4791).

Both carry InfiniBand transport headers (BTH, RETH, AETH, etc.) over Ethernet instead of InfiniBand link layer.

## 2. RoCE v1 Protocol

### 2.1 Packet Format

```
+------------------+
| Ethernet Header  |  14 bytes (or 18 with VLAN tag)
|  Dst MAC (6B)    |
|  Src MAC (6B)    |
|  EtherType=0x8915|  (or 802.1Q + EtherType)
+------------------+
| GRH              |  40 bytes (Global Route Header - IB format)
|  IPv6 format     |
|  Src GID (16B)   |
|  Dst GID (16B)   |
+------------------+
| BTH              |  12 bytes (Base Transport Header)
|  OpCode (8b)     |
|  Pad/TVer (8b)   |
|  P_Key (16b)     |
|  Dst QP (24b)    |
|  PSN (24b)       |
+------------------+
| Payload-specific |  (RETH, AETH, ImmDt, etc.)
| headers          |
+------------------+
| Payload Data     |  0 - MTU bytes
+------------------+
| ICRC             |  4 bytes (Invariant CRC)
+------------------+
| FCS              |  4 bytes (Ethernet Frame Check)
+------------------+
```

### 2.2 GID Format in RoCE v1

The GID (Global Identifier) in RoCE v1 uses IPv6 format:
- **Bytes 0-7**: Subnet prefix (default: fe80:0000:0000:0000)
- **Bytes 8-15**: Interface ID (derived from MAC via EUI-64)

```
GID = fe80::xxxx:xxff:fexx:xxxx
      (where xx comes from MAC address with EUI-64 transformation)
```

### 2.3 RoCE v1 Limitations

- **Not routable**: L2 only, cannot cross IP subnets
- **Requires same VLAN/broadcast domain**
- **No ECMP**: Cannot leverage multi-path routing
- **GRH always present**: Unlike native IB where GRH is optional for local

## 3. RoCE v2 Protocol

### 3.1 Packet Format

```
+------------------+
| Ethernet Header  |  14 bytes (or 18 with VLAN)
|  Dst MAC (6B)    |
|  Src MAC (6B)    |
|  EtherType       |  0x0800 (IPv4) or 0x86DD (IPv6)
+------------------+
| IP Header        |  20 bytes (IPv4) or 40 bytes (IPv6)
|  Protocol=17(UDP)|
|  Src IP          |
|  Dst IP          |
|  DSCP/TC         |  (for QoS)
|  ECN bits        |  (for congestion)
+------------------+
| UDP Header       |  8 bytes
|  Src Port        |  (entropy for ECMP, based on QP)
|  Dst Port=4791   |  (IANA assigned RoCEv2 port)
|  Length           |
|  Checksum=0      |  (disabled; ICRC provides integrity)
+------------------+
| BTH              |  12 bytes (Base Transport Header)
|  OpCode (8b)     |
|  SE/M/Pad (8b)   |
|  P_Key (16b)     |
|  Dst QP (24b)    |
|  A/PSN (32b)     |
+------------------+
| Payload-specific |  (RETH, AETH, etc.)
+------------------+
| Payload Data     |
+------------------+
| ICRC             |  4 bytes
+------------------+
| FCS              |  4 bytes
+------------------+
```

### 3.2 UDP Source Port (Flow Entropy)

The UDP source port provides entropy for ECMP load balancing:

```
UDP_src_port = hash(src_qp, dst_qp) | 0xC000
```

- Bits 15-14 are set to `11` (range 0xC000-0xFFFF)
- This avoids conflicting with well-known ports
- The hash ensures different QP pairs take different ECMP paths
- Configurable via: `echo N > /sys/class/net/ethX/ecmp_hash`

### 3.3 DSCP and Traffic Class Mapping

RoCE v2 uses DSCP (Differentiated Services Code Point) in the IP header for QoS:

| DSCP Value | Priority | Typical Use |
|-----------|----------|-------------|
| 0 (BE) | 0 | Best effort (default) |
| 26 (AF31) | 3 | RoCE traffic (common) |
| 34 (AF41) | 4 | RoCE traffic (alternative) |
| 46 (EF) | 5 | CNP (Congestion Notification Packets) |

Configuration:
```bash
# Set default RoCE ToS (DSCP 26 = ToS 104, DSCP 34 = ToS 136)
echo 106 > /sys/kernel/config/rdma_cm/mlx5_0/ports/1/default_roce_tos

# Map DSCP to priority at NIC
mlnx_qos -i eth0 --trust=dscp
mlnx_qos -i eth0 --dscp2prio=set,26,3

# Verify
cat /sys/kernel/config/rdma_cm/mlx5_0/ports/1/default_roce_tos
```

### 3.4 ECN Bits

ECN uses 2 bits in the IP header (bits 6-7 of the TOS/Traffic Class field):

| ECN Bits | Meaning |
|----------|---------|
| 00 | Not ECN-Capable |
| 01 | ECT(1) - ECN Capable |
| 10 | ECT(0) - ECN Capable |
| 11 | CE - Congestion Experienced |

```bash
# Enable ECN on mlx5
echo 1 > /sys/class/net/eth0/ecn/roce_np/enable/3   # NP (notification point) for prio 3
echo 1 > /sys/class/net/eth0/ecn/roce_rp/enable/3   # RP (reaction point) for prio 3
```

## 4. InfiniBand Transport Headers

Both RoCE v1 and v2 carry IB transport headers. Key headers:

### 4.1 BTH (Base Transport Header) - 12 bytes

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|    OpCode     |S|M|Pad| TVer  |        Partition Key          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Reserved   |          Destination QP                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|A|  Reserved |           Packet Sequence Number                |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

**OpCode values (common):**
| OpCode | Value | Description |
|--------|-------|-------------|
| RC Send First | 0x00 | RC Send (first packet) |
| RC Send Middle | 0x01 | RC Send (middle) |
| RC Send Last | 0x02 | RC Send (last) |
| RC Send Only | 0x04 | RC Send (single packet) |
| RC RDMA Write First | 0x06 | RDMA Write (first) |
| RC RDMA Write Only | 0x0A | RDMA Write (single) |
| RC RDMA Read Request | 0x0C | RDMA Read |
| RC RDMA Read Response | 0x10 | RDMA Read reply |
| RC Acknowledge | 0x11 | ACK |
| RC Atomic | 0x12 | CmpSwap/FetchAdd |
| RC Send Only w/ Imm | 0x05 | Send with immediate data |
| RC RDMA Write w/ Imm | 0x0B | Write with immediate |
| UD Send Only | 0x64 | UD send |

### 4.2 RETH (RDMA Extended Transport Header) - 16 bytes

Used with RDMA Read/Write operations:
```
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Virtual Address (64 bits)                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Remote Key (32 bits)                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    DMA Length (32 bits)                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### 4.3 AETH (ACK Extended Transport Header) - 4 bytes

```
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Syndrome      |       Message Sequence Number                 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

Syndrome values:
- 0x00-0x1F: ACK (credits available)
- 0x20-0x3F: RNR NAK (receiver not ready)
- 0x60: PSN Sequence Error
- 0x61: Invalid Request
- 0x62: Remote Access Error
- 0x63: Remote Operational Error
- 0x64: Invalid RD Request

## 5. ICRC (Invariant CRC)

The ICRC covers all IB transport headers and payload, but excludes fields that change hop-by-hop:

**Excluded from ICRC (replaced with 0xFF):**
- IP header fields (TTL, TOS/DSCP)
- UDP header
- GRH Flow Label and Hop Limit (RoCE v1)
- BTH resv8a field

**ICRC calculation:**
```
ICRC = CRC-32C over:
  [modified_headers] + [BTH] + [payload_headers] + [payload]
```

## 6. GID Table and Address Resolution

### 6.1 GID Table

Each RDMA port maintains a GID table mapping IP addresses to GIDs:

```bash
# View GID table
ibv_devinfo -v | grep GID
# Or
rdma link show
cat /sys/class/infiniband/mlx5_0/ports/1/gids/*

# GID table format for RoCE v2:
# Index 0: fe80::... (link-local, RoCE v1 compatible)
# Index 1: ::ffff:192.168.1.10 (IPv4-mapped, RoCE v2)
# Index 2: 2001:db8::1 (IPv6, RoCE v2)
```

### 6.2 GID Types

| GID Type | Description | RoCE Version |
|----------|-------------|--------------|
| IB/RoCE v1 | EUI-64 derived from MAC | v1 |
| RoCE v2 IPv4 | ::ffff:a.b.c.d format | v2 |
| RoCE v2 IPv6 | Full IPv6 address | v2 |

### 6.3 Address Resolution

For RoCE v2, address resolution uses standard ARP/ND:
1. Application specifies GID (contains IP) of remote
2. Stack resolves IP to MAC via ARP/ND
3. Ethernet header constructed with resolved MAC
4. IP header uses addresses from GID

## 7. Congestion Control (DCQCN)

### 7.1 DCQCN Algorithm (Data Center QCN)

DCQCN combines ECN marking (at switch) with rate adjustment (at NIC):

**At the Switch (Congestion Point):**
1. Monitor queue depth per priority
2. When queue exceeds threshold, mark packets with CE bit
3. Marking probability increases with queue depth (WRED-like)

**At the Receiver (Notification Point):**
1. Receive packet with CE marking
2. Generate CNP (Congestion Notification Packet) back to sender
3. CNP is a special RoCEv2 packet with OpCode 0x81

**At the Sender (Reaction Point):**
1. Receive CNP
2. Reduce sending rate using alpha parameter
3. Gradually increase rate using timer-based recovery
4. Rate = Rate * (1 - alpha/2)

### 7.2 CNP (Congestion Notification Packet) Format

```
+------------------+
| Ethernet Header  |
| IP Header        |  DSCP = 48 (CS6) typically
| UDP Header       |  Dst Port = 4791
+------------------+
| BTH              |  OpCode = 0x81 (CNP)
|  Dst QP = 0      |  (or original QP)
+------------------+
| CNP Payload      |  16 bytes
|  Faded QP (24b)  |
|  Reserved        |
+------------------+
| ICRC             |
+------------------+
```

## 8. RoCE v1 vs v2 Comparison

| Feature | RoCE v1 | RoCE v2 |
|---------|---------|---------|
| Layer | L2 | L3 (IP/UDP) |
| EtherType | 0x8915 | 0x0800/0x86DD |
| Routable | No | Yes |
| ECMP Support | No | Yes (UDP src port entropy) |
| Subnet Crossing | No | Yes |
| IP Header | No (uses GRH) | Yes (IPv4 or IPv6) |
| UDP Port | N/A | 4791 |
| QoS | PCP (802.1p) | DSCP |
| ECN/Congestion | Limited | Full DCQCN |
| Switch Requirements | DCB-capable L2 | L3 router with ECN |
| Multicast | Ethernet multicast | IP multicast |
| MTU Overhead | 14+40+12 = 66B | 14+20+8+12 = 54B (IPv4) |
| GID Resolution | MAC-based | ARP/ND-based |
| Industry Adoption | Legacy | Standard |

## 9. MTU Considerations

### 9.1 Effective RDMA MTU

The RDMA MTU (IB MTU) is smaller than Ethernet MTU due to headers:

```
For RoCE v2 over IPv4:
  Ethernet Header:    14 bytes (+ 4 if VLAN tagged)
  IPv4 Header:        20 bytes
  UDP Header:          8 bytes
  BTH:                12 bytes
  ICRC:                4 bytes
  Total overhead:     58 bytes (62 with VLAN)

  Ethernet MTU 9000 → RDMA payload ≈ 8942 bytes → IB MTU 4096 (nearest standard)
  Ethernet MTU 1500 → RDMA payload ≈ 1442 bytes → IB MTU 1024 (nearest standard)
```

Standard IB MTU values: 256, 512, 1024, 2048, 4096

### 9.2 Configuring MTU

```bash
# Set Ethernet MTU
ip link set dev eth0 mtu 9000

# IB MTU is automatically negotiated in QP setup
# Can be queried:
ibv_devinfo -d mlx5_0 | grep active_mtu
```

## 10. Multicast over RoCE

### 10.1 RoCE v1 Multicast

- Uses Ethernet multicast MAC addresses
- GID to MAC mapping follows IB specification
- Multicast GID prefix: FF00::/8

### 10.2 RoCE v2 Multicast

- Uses IP multicast (IGMP for IPv4, MLD for IPv6)
- Multicast group = IP multicast address
- Switch must support IGMP snooping
- Joins via standard `ibv_attach_mcast()` API

```bash
# Example: Join multicast group
# In application code:
ibv_attach_mcast(qp, &mgid, mlid);
```
