# RDMA Networking Fundamentals

## Table of Contents

1. [Network Layers and RDMA](#network-layers-and-rdma)
2. [TCP/IP vs RDMA](#tcpip-vs-rdma)
3. [Network Topologies](#network-topologies)
4. [Fabric Management](#fabric-management)
5. [Performance Considerations](#performance-considerations)

---

## Network Layers and RDMA

### Traditional Networking Stack

```
Application Layer  →  High overhead, kernel involvement
Transport Layer    →  TCP adds latency, retransmission
Network Layer     →  IP routing decisions
Data Link Layer  →  Ethernet MAC addressing
Physical Layer    →  PHY signaling
```

### RDMA Network Stack

```
Application Layer  →  Direct access (RDMA verbs)
Transport Layer    →  Bypass TCP/UDP (kernel bypass)
Network Layer     →  IP/InfiniBand routing
Data Link Layer  →  Ethernet/InfiniBand
Physical Layer    →  PHY signaling
```

### Key Differences

| Feature | TCP/IP | RDMA |
|---------|--------|------|
| Data Path | Through kernel | Direct memory access |
| CPU Overhead | High (copies, context switches) | Low (kernel bypass) |
| Latency | High (protocol overhead) | Microsecond latency |
| Reliability | Retransmissions | Hardware ACK/NACK |
| Flow Control | TCP window size | Credit-based (QP) |

---

## TCP/IP vs RDMA

### TCP/IP Characteristics

**Advantages:**
- Universal compatibility
- Works over any IP network
- Automatic congestion control
- Reliability through retransmission

**Disadvantages:**
- High CPU overhead
- Multiple memory copies
- Protocol processing overhead
- Limited by kernel schedulers

### RDMA Characteristics

**Advantages:**
- Kernel bypass (zero-copy)
- Direct memory access
- Sub-microsecond latency
- Hardware offload

**Disadvantages:**
- Requires specialized hardware (RDMA-capable NICs)
- Network must support lossless operation
- More complex programming model
- Limited to specific transports (IB, RoCE, iWARP)

### When to Use Each

| Use Case | Recommended Protocol |
|----------|-------------------|
| General Internet traffic | TCP/IP |
| High-performance HPC | RDMA |
- Remote direct memory access | RDMA |
| Low-latency trading | RDMA |
| Standard web traffic | TCP/IP |
| Storage protocols (iSCSI) | TCP/IP |
- Storage protocols (NVMe-oF) | RDMA |
| File sharing (NFS, SMB) | TCP/IP |

---

## Network Topologies

### Fat Tree

```
    [Switch]
       / | \
   [H1] [H2] [H3]
```

**Characteristics:**
- Single central switch
- Simple to manage
- Limited scalability
- Potential bottleneck at root switch
- Lower cost for small deployments

### Spine-Leaf

```
[Spine1] [Spine2]
   /  \     /   \
[Leaf1] [Leaf2] [Leaf3] [Leaf4]
   |       |       |       |
  [H1]   [H2]   [H3]   [H4]
```

**Characteristics:**
- Scalable architecture
- Equal path lengths (ECMP)
- High bandwidth
- Complex cabling
- Higher cost for large deployments
- Ideal for AI/ML training clusters

### Clos/Fat-Tree

```
      [Spine Layer]
         /   |   \
    [Leaf1] [Leaf2] [Leaf3]
      |     |     |
   [Agg1] [Agg2] [Agg3]
     /  |  \ /  |  \
  [H1] [H2] [H3] [H4] [H5] [H6]
```

**Characteristics:**
- Combines fat-tree with spine-leaf
- Better scalability than pure fat-tree
- Reduces oversubscription
- Common in modern data centers
- Optimal for RoCE/lossless Ethernet

### Full Mesh

```
[H1] ──┼─── [H2]
 │    │
 ├─┼─ [H3] ─┼─ [H4]
 │    │
[H5] ─┼─── [H6]
```

**Characteristics:**
- Maximum bandwidth
- Every host directly connected
- Highest cost and complexity
- Limited scalability
- Used in small, high-performance clusters

### RDMA Topology Considerations

1. **Path Diversity** - Multiple paths for reliability
2. **Equal Cost Multipathing (ECMP)** - Balanced load distribution
3. **Low Latency** - Minimize hop count
4. **Lossless Transport** - PFC/ECN for congestion management
5. **Jumbo Frames** - 9000+ MTU for RDMA efficiency

---

## Fabric Management

### InfiniBand Subnet Manager (SM)

**Purpose:**
- Discover and configure IB fabric
- Assign LIDs (Local Identifiers)
- Manage partition keys
- Route computation

**Components:**
- **SM** - Central manager process
- **SMA** - Subnet Management Agent
- **SLM** - Subnet Manager

**Redundancy:**
- Standby SM for failover
- Automatic takeover detection
- State synchronization

### Ethernet Fabric Management

**Key Concepts:**

1. **VLANs** - Layer 2 segmentation
2. **Spanning Tree Protocol (STP)** - Loop prevention
3. **Link Aggregation (LAG)** - Bandwidth aggregation
4. **LACP** - Link Aggregation Control Protocol
5. **LLDP** - Link Layer Discovery Protocol

**RoCE Considerations:**
- PFC configuration across fabric
- ECN marking and response
- DSCP-based QoS
- MTU consistency (jumbo frames)

### Fabric Discovery Tools

**ibdiagnet:**
- Comprehensive fabric analysis
- Loop detection
- Performance analysis
- Path verification

**infiniband-diags:**
- Real-time monitoring
- Performance counters
- Error tracking

**sminfo:**
- SM information
- Port states
- Routing tables

---

## Performance Considerations

### Latency Components

1. **Processing Latency** - NIC processing time
2. **Serialization Latency** - Time to put bits on wire
3. **Propagation Latency** - Wire travel time
4. **Queuing Latency** - Time in switch buffers
5. **Software Latency** - Application/kernel processing

**Total Latency = Sum of all components**

### Bandwidth Optimization

**Factors:**
- Link speed (25G, 40G, 100G, 200G, 400G)
- Number of lanes
- Encoding efficiency
- MTU size

**Optimization Techniques:**
1. **Jumbo Frames** - 9000+ MTU reduces header overhead
2. **Parallel Connections** - Multiple QPs per connection
3. **Inline Data** - Reduce descriptor overhead
4. **Memory Alignment** - 64-byte alignment for RDMA

### Congestion Management

**Why Congestion Matters:**
- Packet loss destroys RDMA performance
- Retransmissions are expensive
- Head-of-line blocking
- TCP incast collapse equivalent

**RoCE Congestion Control:**

1. **PFC (Priority Flow Control)**
   - Pause traffic per priority
   - 802.1Qbb standard
   - Configurable per switch port

2. **ECN (Explicit Congestion Notification)**
   - Mark packets as experiencing congestion
   - 802.1Qau standard
   - End-to-end feedback

3. **DCQCN (Data Center Quantized Congestion Notification)**
   - Combine PFC and ECN
   - Rate limiting at source
   - Fast convergence

### NUMA Awareness

**Non-Uniform Memory Access (NUMA):**
- CPUs have different memory access speeds
- Local vs remote memory accesses
- Critical for RDMA performance

**Best Practices:**
1. Register memory on local NUMA node
2. Pin memory to specific CPU cores
3. Use `numactl` for process affinity
4. Minimize cross-socket communication

### CPU Affinity

**Purpose:**
- Reduce context switching
- Improve cache locality
- Ensure consistent core assignment

**Implementation:**
```c
#include <pthread.h>
#include <sched.h>

cpu_set_t cpuset;
CPU_ZERO(&cpuset);
CPU_SET(core_id, &cpuset);
pthread_setaffinity_np(pthread_self(), &cpuset);
```

---

## Monitoring and Troubleshooting

### Key Metrics

1. **Throughput** - MB/s or GB/s
2. **Latency** - Microseconds or nanoseconds
3. **Packets Per Second (PPS)** - Load measurement
4. **Error Rate** - CRC errors, symbol errors
5. **Retransmissions** - Unsuccessful transmissions

### Common Issues

**High Latency:**
- Check for congested links
- Verify PFC configuration
- Examine MTU mismatches
- Review switch buffer sizes

**Packet Loss:**
- Insufficient PFC buffer
- ECN not properly configured
- Oversubscribed links
- Cable/fiber issues

**Low Throughput:**
- Incorrect MTU (small frames)
- Single path (no ECMP)
- Suboptimal routing
- CPU bottlenecks

### Diagnostic Tools

**Per-Node Tools:**
- `ibstat` - Port statistics
- `perfquery` - Performance counters
- `ibroute` - Routing information

**Fabric-Wide Tools:**
- `ibdiagnet` - Comprehensive analysis
- `opensm` - SM information
- `ibswitch` - Switch configuration

---

## Best Practices

1. **Use Appropriate Topology**
   - Spine-leaf for scalability
   - Redundant paths for reliability

2. **Configure Lossless Transport**
   - Enable PFC on all switches
   - Configure ECN marking and response
   - Implement DCQCN or similar

3. **Optimize MTU**
   - Use jumbo frames (9000+)
   - Consistent across fabric
   - Match host and switch settings

4. **Monitor Continuously**
   - Collect performance metrics
   - Set alerts on degradation
   - Regular fabric health checks

5. **Plan for Growth**
   - Scalable design
   - Modular expansion
   - Documentation of configurations

---

## References

1. InfiniBand Trade Association (IBTA) Specifications
2. IEEE 802.1Qbb (Priority Flow Control)
3. IEEE 802.1Qau (Congestion Notification)
4. IEEE 802.1Qaz (Enhanced Transmission Selection)
5. NVIDIA Network Documentation
6. Linux RDMA Documentation