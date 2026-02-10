---
title: "RoCE vs InfiniBand vs iWARP - Comprehensive Comparison"
category: blogs
tags: [roce, infiniband, iwarp, comparison, rdma, networking]
---

# RoCE vs InfiniBand vs iWARP - Comprehensive Comparison

## 1. Protocol Stack Overview

```
        RoCE v1        RoCE v2        InfiniBand       iWARP
      ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────┐
      │ IB Verbs │  │ IB Verbs │  │   IB Verbs   │  │ IB Verbs │
      ├──────────┤  ├──────────┤  ├──────────────┤  ├──────────┤
      │ IB Trans │  │ IB Trans │  │  IB Transport│  │  RDMAP   │
      ├──────────┤  ├──────────┤  ├──────────────┤  ├──────────┤
      │   GRH    │  │   UDP    │  │   IB Link    │  │   DDP    │
      ├──────────┤  ├──────────┤  ├──────────────┤  ├──────────┤
      │          │  │   IP     │  │              │  │   MPA    │
      │ Ethernet │  ├──────────┤  │  IB Physical │  ├──────────┤
      │          │  │ Ethernet │  │              │  │   TCP    │
      └──────────┘  └──────────┘  └──────────────┘  ├──────────┤
                                                     │   IP     │
                                                     ├──────────┤
                                                     │ Ethernet │
                                                     └──────────┘
```

## 2. Feature Comparison

| Feature | InfiniBand | RoCE v2 | iWARP |
|---------|-----------|---------|-------|
| **Transport** | Native IB | UDP/IP | TCP/IP |
| **Layer** | L1-L4 (full stack) | L2-L3 (over Ethernet) | L4 (over TCP) |
| **Routable** | Via IB routers | Yes (IP routing) | Yes (IP routing) |
| **ECMP** | Adaptive routing | Yes (UDP entropy) | Yes (TCP) |
| **Loss Handling** | Credit-based (lossless) | PFC + ECN (lossless ETH) | TCP retransmission |
| **Congestion** | Credit-based FC | DCQCN (ECN-based) | TCP congestion |
| **Latency** | ~0.6 μs | ~1.0 μs | ~3-5 μs |
| **Bandwidth** | Up to 800 Gbps (XDR) | Up to 400 Gbps | Up to 100 Gbps |
| **CPU Overhead** | Lowest | Low | Moderate (TCP) |
| **Operations** | Send, Write, Read, Atomic | Send, Write, Read, Atomic | Send, Write, Read |
| **Multicast** | Native IB multicast | IP multicast | Limited |
| **QoS** | SL/VL (15 levels) | DSCP (64 values) | TCP DSCP |
| **Subnet Mgmt** | SM required | Standard IP | Standard IP |
| **Max QPs** | Millions | Millions | Thousands (TCP) |
| **Connection Setup** | IB CM / RDMA CM | RDMA CM | TCP + MPA handshake |
| **MTU** | 256-4096 (IB MTU) | Limited by ETH MTU | Limited by ETH MTU |
| **Fabric Mgmt** | UFM, opensm | Standard NMS | Standard NMS |
| **In-network** | SHARP (AllReduce) | Limited | None |
| **Cost** | Higher (IB switches) | Lower (ETH switches) | Lowest |

## 3. Network Requirements

### InfiniBand
- Dedicated IB switches (Quantum, NDR)
- Subnet Manager (opensm or UFM)
- IB cables (QSFP, OSFP)
- Separate from Ethernet infrastructure

### RoCE v2
- DCB-capable Ethernet switches
- PFC configuration per priority
- ECN marking at switches
- DCBX for auto-negotiation
- Careful buffer sizing for headroom

### iWARP
- Standard Ethernet switches (no DCB required)
- Standard TCP/IP networking
- No special switch configuration
- Works over WAN/Internet (theoretically)

## 4. When to Choose Which

### Choose InfiniBand When:
- Maximum performance is critical (AI/ML training clusters)
- You need in-network computing (SHARP for AllReduce)
- Building dedicated HPC or AI infrastructure
- Budget allows for IB switches
- Latency below 1μs is required
- You need predictable, credit-based flow control

### Choose RoCE v2 When:
- You want RDMA over existing Ethernet infrastructure
- Converging storage and compute on one fabric
- Building cloud or multi-tenant environments
- Cost optimization is important
- You have DCB-capable switches already
- Good network engineering team for lossless config

### Choose iWARP When:
- Simplest deployment (no DCB needed)
- RDMA over unreliable networks
- Limited switch management capability
- Windows environments (strong Microsoft support)
- Small-scale deployments
- WAN RDMA scenarios (rare)

## 5. Industry Adoption Trends

- **AI/ML clusters**: InfiniBand dominates (NVIDIA DGX, cloud AI)
- **Cloud/hyperscaler**: RoCE v2 growing (Azure, Google, Meta)
- **Enterprise storage**: RoCE v2 and iWARP
- **HPC**: InfiniBand traditional, RoCE growing
- **Windows storage**: SMB Direct over iWARP or RoCE

## 6. Performance Deep Dive

### Latency Breakdown

```
InfiniBand RC Send (2-byte):
  Software overhead:  ~0.2 μs
  PCIe DMA:           ~0.1 μs
  Wire time:          ~0.05 μs
  Switch latency:     ~0.1 μs (per hop)
  Total (1 switch):   ~0.6 μs

RoCE v2 RC Send (2-byte):
  Software overhead:  ~0.2 μs
  PCIe DMA:           ~0.1 μs
  UDP/IP processing:  ~0.1 μs
  Wire time:          ~0.05 μs
  Switch latency:     ~0.3 μs (Ethernet switch)
  Total (1 switch):   ~1.0 μs

iWARP Send (2-byte):
  Software overhead:  ~0.5 μs
  TCP processing:     ~1.0 μs
  PCIe DMA:           ~0.1 μs
  Wire time:          ~0.05 μs
  Switch latency:     ~0.3 μs
  Total (1 switch):   ~3.0 μs
```

### Bandwidth Scaling
- InfiniBand: Linear with port count (NDR 400G per port)
- RoCE: Linear up to switch buffer limits, then PFC may throttle
- iWARP: Limited by TCP overhead, typically < 100Gbps per connection

## 7. Migration Paths

### InfiniBand → RoCE v2
- Same verbs API (application code unchanged)
- Need to configure lossless Ethernet (PFC, ECN)
- Change address resolution (IB SM → ARP/DNS)
- Replace IB switches with DCB-capable Ethernet switches
- May need to tune for slightly higher latency

### iWARP → RoCE v2
- Same verbs API
- Need to configure lossless Ethernet
- Connection model changes (TCP → RDMA CM)
- Better scalability (more QPs, no TCP state)

### Any → InfiniBand
- Same verbs API
- Need IB infrastructure
- Subnet Manager setup
- Potentially redesign network topology
