---
title: "RDMA Performance Troubleshooting Guide"
category: troubleshooting
tags: [rdma, performance, tuning, pcie, numa, troubleshooting]
---

# RDMA Performance Troubleshooting Guide

## 1. Performance Testing Baseline

### 1.1 perftest Suite

```bash
# Bandwidth tests (server | client)
ib_write_bw -d mlx5_0 -s 65536 --report_gbits    # RDMA Write
ib_read_bw -d mlx5_0 -s 65536 --report_gbits      # RDMA Read
ib_send_bw -d mlx5_0 -s 65536 --report_gbits      # Send/Recv

# Latency tests
ib_write_lat -d mlx5_0 -s 2                        # RDMA Write lat
ib_read_lat -d mlx5_0 -s 2                         # RDMA Read lat
ib_send_lat -d mlx5_0 -s 2                         # Send/Recv lat

# Multi-QP bandwidth
ib_write_bw -d mlx5_0 -q 8 -s 65536 --report_gbits <server>

# Bidirectional
ib_write_bw -d mlx5_0 -b -s 65536 --report_gbits <server>
```

### 1.2 Expected Bandwidth

| Adapter | Link Speed | Expected ib_write_bw | Expected ib_read_bw |
|---------|-----------|---------------------|---------------------|
| ConnectX-5 | 100 Gbps | ~96 Gbps | ~96 Gbps |
| ConnectX-6 | 200 Gbps | ~190 Gbps | ~190 Gbps |
| ConnectX-6 Dx | 100 Gbps | ~96 Gbps | ~96 Gbps |
| ConnectX-7 | 400 Gbps | ~380 Gbps | ~380 Gbps |

### 1.3 Expected Latency

| Scenario | RDMA Write | RDMA Read |
|----------|-----------|-----------|
| Back-to-back | ~0.6 μs | ~1.2 μs |
| Through 1 switch | ~0.8 μs | ~1.5 μs |
| Through 2 switches | ~1.0 μs | ~1.8 μs |

## 2. PCIe Bottleneck Detection

### 2.1 Check PCIe Configuration

```bash
# Check link speed and width
lspci -vvv -s 3b:00.0 | grep -E "LnkCap|LnkSta"
# LnkCap: Speed 16GT/s, Width x16    ← Capability
# LnkSta: Speed 16GT/s, Width x16    ← Actual (should match)

# Expected PCIe throughput:
# Gen3 x16: ~128 Gbps (15.75 GB/s)
# Gen4 x16: ~256 Gbps (31.5 GB/s)
# Gen5 x16: ~512 Gbps (63 GB/s)

# If LnkSta speed < LnkCap speed:
#   → Check motherboard slot (physical x16 but wired x8?)
#   → Reseat the card
#   → Update BIOS/firmware
```

### 2.2 Check MPS and MRRS

```bash
lspci -vvv -s 3b:00.0 | grep -E "MaxPayload|MaxReadReq"
# MaxPayload 256 bytes, MaxReadReq 512 bytes

# For best RDMA performance:
# MaxPayload: 256 (minimum acceptable)
# MaxReadReq: 4096 (for large RDMA reads)

# Set MRRS (requires root)
setpci -s 3b:00.0 68.w=5936  # Example: set to 4096
# Better: use mstconfig
mstconfig -d <device> set MAX_READ_REQUEST=4096
```

### 2.3 PCIe ACS (Access Control Services)

```bash
# ACS can degrade peer-to-peer performance (GPUDirect)
lspci -vvv -s <bridge_device> | grep ACSCtl

# Disable ACS for GPUDirect RDMA
# For each PCIe bridge in the path:
setpci -s <bridge> ECAP_ACS+6.w=0000
```

## 3. NUMA Topology Optimization

### 3.1 Check NUMA Node

```bash
# Which NUMA node is the NIC on?
cat /sys/class/net/eth0/device/numa_node
# Output: 0   (or 1 for second socket)

# Full NUMA topology
numactl --hardware
lscpu | grep NUMA

# CPU list on same NUMA node
cat /sys/class/net/eth0/device/local_cpulist
# Output: 0-15,32-47 (example for socket 0 HT-enabled)
```

### 3.2 Pin Application to NIC's NUMA Node

```bash
# Run on same NUMA node as NIC
numactl --cpunodebind=0 --membind=0 ./my_rdma_app

# Or with taskset for CPU affinity
taskset -c 0-15 ./my_rdma_app

# perftest with CPU affinity
numactl --cpunodebind=0 ib_write_bw -d mlx5_0 <server>
```

**Cross-NUMA penalty**: Running RDMA application on different NUMA node than NIC adds 50-100ns latency and can reduce bandwidth by 20-40%.

### 3.3 IRQ Affinity

```bash
# Check current IRQ affinity
cat /proc/interrupts | grep mlx5

# Set IRQ affinity to local CPUs
# Using MLNX_OFED script:
set_irq_affinity_cpulist.sh 0-15 eth0

# Or set_irq_affinity.sh (auto-detect local CPUs)
set_irq_affinity.sh eth0

# Manual:
echo 1 > /proc/irq/<irq_num>/smp_affinity_list
```

## 4. Memory Configuration

### 4.1 Huge Pages

```bash
# Check current huge pages
cat /proc/meminfo | grep Huge

# Allocate 2MB huge pages
echo 4096 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# Allocate 1GB huge pages (at boot via kernel cmdline)
# hugepagesz=1G hugepages=16

# Mount hugetlbfs
mount -t hugetlbfs nodev /dev/hugepages

# Verify
grep Huge /proc/meminfo
```

### 4.2 Memory Locking (ulimit)

```bash
# RDMA requires locked memory for MR registration
# Check current limit
ulimit -l
# Should be "unlimited" for RDMA workloads

# Set in /etc/security/limits.conf:
*    soft    memlock    unlimited
*    hard    memlock    unlimited

# Or for specific user:
rdma_user    soft    memlock    unlimited
rdma_user    hard    memlock    unlimited
```

### 4.3 Memory Registration Performance

```bash
# Register large MRs (fewer is better than many small ones)
# Each ibv_reg_mr() call is expensive (pins pages, creates HW entries)

# Use ODP (On-Demand Paging) to avoid upfront registration cost:
struct ibv_mr *mr = ibv_reg_mr(pd, addr, len,
    IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_ON_DEMAND);

# Check ODP support
ibv_devinfo -v | grep odp
```

## 5. Application-Level Tuning

### 5.1 QP Depth

```bash
# Insufficient QP depth causes pipeline stalls
# Rule of thumb:
#   SQ depth = BDP / msg_size
#   BDP (Bandwidth-Delay Product) = Bandwidth × RTT

# Example: 100Gbps, 2μs RTT, 4KB messages:
#   BDP = 100Gbps × 2μs = 25,000 bytes
#   QP depth = 25,000 / 4,096 ≈ 7 → use at least 16-32

# For maximum bandwidth, use 128-512 SQ entries
```

### 5.2 Inline Data

```bash
# Inline sends avoid memory registration for small messages
# Saves one DMA read (the HCA reads data from WQE directly)
# Effective for messages < 64-256 bytes

# In perftest:
ib_write_lat -d mlx5_0 -I 64 <server>  # 64 bytes inline

# In code:
qp_init_attr.cap.max_inline_data = 64;
```

### 5.3 Selective Signaling

```bash
# Don't signal every completion (reduces CQE processing overhead)
# Signal every Nth WQE:
# send_wr.send_flags = 0;  // unsignaled (most WQEs)
# send_wr.send_flags = IBV_SEND_SIGNALED;  // every Nth

# Typical: signal every 16-64 WQEs
# CAUTION: Must track signaled WQEs to avoid SQ overflow
```

### 5.4 CQ Polling vs Events

```bash
# Polling mode: Best latency, highest CPU usage
while (ibv_poll_cq(cq, 1, &wc) == 0);  # busy-wait

# Event mode: Lower CPU usage, higher latency
ibv_req_notify_cq(cq, 0);  # arm CQ
poll(fd, ...);               # wait for event
ibv_get_cq_event(channel, &cq, &ctx);
ibv_poll_cq(cq, 16, wc);    # drain CQ
ibv_ack_cq_events(cq, 1);

# Hybrid: poll for a while, then switch to events
// Adaptive polling
for (int i = 0; i < 1000; i++) {
    n = ibv_poll_cq(cq, 16, wc);
    if (n > 0) break;
}
if (n == 0) { /* switch to event mode */ }
```

## 6. Common Performance Problems

### 6.1 Symptom: Low Bandwidth

| Check | Command | Expected |
|-------|---------|----------|
| Link speed | `ibstat` / `ethtool eth0` | Max speed |
| PCIe width | `lspci -vvv` | x16 |
| NUMA affinity | `cat .../numa_node` | Same node |
| MTU | `ip link show` | 9000 (jumbo) |
| Message size | perftest -s | 65536+ for BW |
| QP depth | - | 128+ |
| CPU frequency | `cat /proc/cpuinfo` | Max freq |

### 6.2 Symptom: High Latency

| Check | Command | Expected |
|-------|---------|----------|
| Polling mode | - | Not event-driven |
| NUMA | `numactl` | Local |
| C-states | `/sys/devices/system/cpu/*/cpufreq` | Disabled |
| Interrupt coalescing | `ethtool -c` | Off for low-lat |
| CPU power saving | `cpupower` | Performance governor |

```bash
# Disable CPU power saving
cpupower frequency-set -g performance

# Disable C-states
echo 0 > /sys/devices/system/cpu/cpu0/cpuidle/state*/disable

# Kernel cmdline for minimal latency:
# processor.max_cstate=0 intel_idle.max_cstate=0 idle=poll
```

### 6.3 Symptom: Bandwidth Degrades Over Time

```bash
# Check for PFC storms
ethtool -S eth0 | grep pfc
# Rapidly increasing tx_pause_* = PFC being triggered = congestion

# Check ECN marking
ethtool -S eth0 | grep ecn

# Check for thermal throttling
mstconfig -d /dev/mst/mt4119_pciconf0 query | grep -i temp
sensors  # if lm-sensors installed

# Check for retransmissions (RC transport)
cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/duplicate_request
cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/out_of_sequence
```

## 7. Network-Level Performance Checks

```bash
# RoCE: Verify lossless configuration end-to-end
# On NIC:
mlnx_qos -i eth0  # Check PFC, ETS, trust mode

# On each switch hop:
# Verify PFC counters not increasing (means PFC is working)
# Verify ECN marking is configured
# Verify buffer allocation is sufficient

# Check for packet drops
ethtool -S eth0 | grep -E "drop|discard|error"

# Should all be 0 during normal operation:
# rx_out_of_buffer: 0
# rx_discards_phy: 0
# tx_errors_phy: 0
```
