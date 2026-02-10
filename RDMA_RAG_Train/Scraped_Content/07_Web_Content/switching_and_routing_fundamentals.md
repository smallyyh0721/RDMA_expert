---
title: "Switching and Routing Fundamentals for Data Centers"
category: web_content
tags: [switching, routing, bgp, ecmp, leaf-spine, datacenter]
---

# Switching and Routing Fundamentals for Data Centers

## 1. Layer 2 Switching

### 1.1 MAC Learning and Forwarding
- **Learning**: Switch records source MAC + ingress port
- **Flooding**: Unknown destination → send to all ports
- **Forwarding**: Known destination → send to specific port
- **Aging**: Entries timeout after configurable period (default ~300s)

### 1.2 VLAN (IEEE 802.1Q)
- **Purpose**: Logical segmentation of L2 broadcast domains
- **Tagging**: 4-byte tag in Ethernet frame (TPID 0x8100 + PCP + DEI + VID)
- **VID range**: 1-4094
- **Trunk ports**: Carry multiple VLANs (tagged)
- **Access ports**: Single VLAN (untagged)

### 1.3 Spanning Tree Protocol (STP/RSTP)
- Prevents L2 loops by blocking redundant paths
- RSTP (802.1w): Rapid convergence (~1-2 seconds)
- **RDMA impact**: STP convergence causes traffic disruption
- **Modern alternative**: Use L3 leaf-spine instead of L2 STP

## 2. Layer 3 Routing

### 2.1 Static Routing
```bash
ip route add 10.0.0.0/24 via 192.168.1.1
```

### 2.2 OSPF (Open Shortest Path First)
- Link-state protocol
- Fast convergence
- Area-based hierarchy
- Commonly used in campus and smaller DC networks

### 2.3 BGP (Border Gateway Protocol)
- Path-vector protocol
- Standard for DC underlay in modern leaf-spine
- eBGP between leaf and spine (different ASN per switch)
- **RFC 7938**: Use of BGP in large-scale data centers

```
Spine (AS 65000)    Spine (AS 65001)
    │       │           │       │
    │  eBGP │           │ eBGP  │
    │       │           │       │
Leaf(AS65100) Leaf(AS65101) Leaf(AS65102)
```

### 2.4 ECMP (Equal-Cost Multi-Path)
- Multiple equal-cost paths to same destination
- Traffic distributed across paths via hash
- Hash typically based on: src/dst IP, src/dst port, protocol
- **Critical for RoCE**: UDP src port provides entropy for ECMP
- **Typical**: 64-128 ECMP paths in leaf-spine DC

## 3. Leaf-Spine Architecture (Clos Network)

### 3.1 Design
```
    Spine 1     Spine 2     Spine 3     Spine 4
     │ │ │ │    │ │ │ │    │ │ │ │    │ │ │ │
     └─┼─┼─┼────┘ │ │ │    │ │ │ │    │ │ │ │
       └─┼─┼──────┘ │ │    │ │ │ │    │ │ │ │
         └─┼────────┘ │    │ │ │ │    │ │ │ │
           └──────────┘    │ │ │ │    │ │ │ │
    (full mesh between every leaf and every spine)

    Leaf 1     Leaf 2     Leaf 3     Leaf 4
    ║║║║       ║║║║       ║║║║       ║║║║
   Servers    Servers    Servers    Servers
```

### 3.2 Properties
- **Non-blocking**: Any-to-any full bandwidth (with enough spines)
- **Predictable latency**: Max 2 hops (leaf → spine → leaf)
- **Scalable**: Add spines for bandwidth, add leaves for ports
- **ECMP**: All spine paths active simultaneously

### 3.3 Oversubscription
```
Oversubscription ratio = Server bandwidth / Uplink bandwidth

Example:
  Leaf: 48 × 25G server ports = 1200G total
  Uplinks: 6 × 100G to spines = 600G total
  Oversubscription: 1200/600 = 2:1

For RDMA workloads: 1:1 (non-oversubscribed) is recommended
```

## 4. QoS (Quality of Service)

### 4.1 Traffic Classification
- **DSCP marking**: 6-bit field in IP header (64 values)
- **802.1p PCP**: 3-bit field in VLAN tag (8 priorities)
- **Mapping**: DSCP → Priority → Traffic Class → Queue

### 4.2 Scheduling
| Algorithm | Behavior |
|-----------|----------|
| Strict Priority | Drain high-priority queue first |
| WRR (Weighted Round Robin) | Proportional bandwidth sharing |
| DWRR (Deficit WRR) | Byte-aware WRR |
| WFQ (Weighted Fair Queuing) | Fair per-flow scheduling |

### 4.3 For RDMA
- RoCE traffic on dedicated priority (e.g., priority 3)
- PFC enabled only on RDMA priority
- ECN marking for congestion notification
- ETS for bandwidth guarantee

## 5. Link Aggregation (LAG)

### 5.1 802.3ad LACP
```bash
# Linux bonding with LACP
ip link add bond0 type bond mode 802.3ad
ip link set eth0 master bond0
ip link set eth1 master bond0

# LACP settings
echo layer3+4 > /sys/class/net/bond0/bonding/xmit_hash_policy
```

### 5.2 MLAG / VPC (Multi-chassis LAG)
- Two switches appear as one to servers
- Provides redundancy and bandwidth
- **RDMA consideration**: RoCE over bond works with ConnectX-5+ (RoCE LAG feature)

## 6. MTU (Maximum Transmission Unit)

### 6.1 Standard vs Jumbo Frames
| MTU | Name | Use Case |
|-----|------|----------|
| 1500 | Standard | Default Ethernet |
| 9000 | Jumbo | RDMA, storage, HPC |
| 9216 | Extended | Some vendors' max |

### 6.2 RDMA MTU Considerations
- **Jumbo frames (9000)** strongly recommended for RDMA
- Must be configured end-to-end (NIC + all switches + remote NIC)
- IB MTU values: 256, 512, 1024, 2048, 4096
- Ethernet MTU 9000 → IB MTU 4096 (max)
- Ethernet MTU 1500 → IB MTU 1024

### 6.3 Path MTU Discovery
```bash
# Test path MTU
ping -M do -s 8972 <dest>  # 8972 + 28 = 9000

# If packet too large error: some hop has smaller MTU
tracepath <dest>  # shows MTU at each hop
```

## 7. Important Protocols for RDMA Networks

### 7.1 ARP/ND
- Resolves IP → MAC for RoCE
- GID table in RDMA populated from ARP entries
- Gratuitous ARP important for failover

### 7.2 LLDP (Link Layer Discovery Protocol)
- Carries DCBX TLVs for PFC/ETS negotiation
- Must be enabled on all RDMA-carrying links

### 7.3 IGMP (Internet Group Management Protocol)
- Manages multicast group membership
- Important for RDMA multicast (UD QPs)
- IGMP snooping on switches prevents multicast flooding
