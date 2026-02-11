# RDMA Troubleshooting Guide
## Expert-Level Diagnostic Methodology and Solutions

**Version:** 1.0  
**Last Updated:** January 2026  
**Target Audience:** System administrators, RDMA engineers, Network operators  

---

**Table of Contents**
1. [Introduction](#introduction)
2. [Troubleshooting Methodology](#troubleshooting-methodology)
3. [Common Symptoms and Solutions](#common-symptoms-and-solutions)
4. [Tool Usage Guide](#tool-usage-guide)
5. [Advanced Diagnostics](#advanced-diagnostics)
6. [Case Studies](#case-studies)
7. [Quick Reference](#quick-reference)


## Introduction

This guide provides expert-level troubleshooting methodologies for RDMA (Remote Direct Memory Access) networks. It covers both InfiniBand and RoCE (RDMA over Converged Ethernet) fabrics, with a focus on Mellanox/NVIDIA hardware and rdma-core software stack.

### Scope

This guide covers:
- **InfiniBand Fabrics:** SDR, DDR, QDR, FDR, EDR, HDR, NDR
- **RoCE Networks:** RoCEv1 and RoCEv2
- **Hardware:** Mellanox/NVIDIA ConnectX series adapters and Spectrum switches
- **Software Stack:** rdma-core, MLNX_OFED, infiniband-diags, mlnx-tools

### Prerequisites

Before diving into troubleshooting, ensure you have:
1. Root access or appropriate permissions for RDMA device access
2. Basic understanding of RDMA concepts (verbs, QPs, completion queues)
3. Familiarity with Linux system administration
4. Access to subnet management (if using InfiniBand)

### Key Concepts

**RDMA Operation Model:**
- Direct Memory Access bypasses CPU and kernel
- Zero-copy data transfer between application memory and NIC
- Requires proper memory registration and protection domains
- Asynchronous operation model with completion queues

**Fabric Layers:**
1. **Physical Layer:** Cables, transceivers, PHY
2. **Link Layer:** MAC, flow control, error detection
3. **Network Layer:** Routing (InfiniBand) or IP (RoCE)
4. **Transport Layer:** Reliable Connection (RC), Unreliable Datagram (UD), etc.
5. **Application Layer:** libibverbs API

### When to Use This Guide

Use this guide when:
- RDMA applications fail to establish connections
- Performance is below expected benchmarks
- Error counters are increasing
- Fabric is unstable with frequent link flaps
- Need to optimize configuration for specific workloads


## Troubleshooting Methodology

Effective RDMA troubleshooting follows a systematic approach to isolate issues quickly.

### Phase 1: Initial Assessment (5-10 minutes)

#### 1.1 Verify Basic Connectivity
```bash
# Check if devices are visible
ibstat -l
rdma link show

# Verify link states
ibstat
iblinkinfo

# Check if kernel modules are loaded
lsmod | grep ib
lsmod | grep mlx5
```

#### 1.2 Quick Health Check
```bash
# Query error counters (ibqueryerrors)
ibqueryerrors

# If errors found, investigate
ibqueryerrors --details

# Check for device errors in kernel logs
dmesg | grep -i mlx5
dmesg | grep -i rdma
```

#### 1.3 Verify Subnet Manager (InfiniBand only)
```bash
# Check SM status
sminfo

# Verify SM can reach all nodes
saquery -n
```

### Phase 2: Detailed Investigation (10-30 minutes)

#### 2.1 Analyze Error Patterns
Map error types to potential causes:

| Error Type | Likely Cause | Diagnostic Tool |
|------------|-------------|----------------|
| Symbol Errors | Physical layer issues (cable, transceiver) | ibqueryerrors, iblinkinfo |
| Link Recovery Errors | Link training failures | iblinkinfo, dmesg |
| Excess Buffer Overruns | Congestion, insufficient buffering | ibqueryerrors, perfquery |
| Local PHY Errors | Transceiver issues | ibqueryerrors, ethtool |
| Discards | Resource exhaustion | perfquery, ibqueryerrors |

#### 2.2 Check Configuration
```bash
# Verify MTU and link configuration
iblinkinfo -s

# Check QoS configuration (RoCE)
mlnx_qos -i eth0 --show

# Verify GID configuration
show_gids

# Check CPU affinity
mlnx_affinity -d mlx5_0
```

#### 2.3 Performance Baseline
```bash
# Get baseline performance counters
perfquery 1 0 --all

# Monitor over time (5 minutes)
watch -n 1 'perfquery 1 0 --all'

# Collect detailed metrics
mlnx_perf -d mlx5_0 -i 5 -t 60
```

### Phase 3: Deep Dive (30+ minutes)

#### 3.1 Capture System State
```bash
# Complete device dump
ibdiagnet -v

# Collect fabric topology
ibnetdiscover --save-cache fabric.cache

# Capture kernel logs
dmesg -T > kernel_logs.txt

# Capture hardware counters
show_counters -p 1 -d 10 > counters.log
```

#### 3.2 Reproduce Issue
If possible, reproduce the issue while collecting data:
```bash
# Start continuous monitoring
ibqueryerrors -o error_monitor.log &
mlnx_perf -d mlx5_0 -i 1 -t 300 &

# Run workload
# ... [your RDMA application] ...

# Stop monitoring
killall ibqueryerrors mlnx_perf
```

#### 3.3 Analyze Patterns
Look for:
- Temporal patterns (time of day, workload-related)
- Spatial patterns (specific nodes, ports, switches)
- Correlation with other events (system updates, network changes)

### Decision Tree

```
Start
  │
  ├─ Is any link down?
  │   └─ Yes → Check physical layer (cables, transceivers, power)
  │   └─ No → Continue
  │
  ├─ Are error counters increasing?
  │   ├─ Symbol errors → Physical layer
  │   ├─ Link recovery → Link training
  │   ├─ Buffer overruns → Congestion
  │   └─ Discards → Resource limits
  │
  ├─ Is performance degraded?
  │   ├─ Latency high → Check QoS, congestion, interrupt handling
  │   ├─ Throughput low → Check MTU, queue depths, PCIe bandwidth
  │   └─ CPU high → Check affinity, polling vs interrupts
  │
  └─ Are connections failing?
      ├─ Timeout → Check routing, SM, network path
      └─ Rejected → Check permissions, configuration mismatch
```

### Documentation Template

Use this template to document your investigation:

```
Issue Title: [Brief description]
Date: [YYYY-MM-DD]
Reporter: [Name]

Environment:
- Hardware: [Adapter model, switch model]
- Software: [rdma-core version, MLNX_OFED version, kernel version]
- Fabric type: [InfiniBand/RoCEv1/RoCEv2]
- Link speed: [SDR/DDR/QDR/FDR/EDR/HDR/NDR]

Symptoms:
- [List observed symptoms]

Initial Findings:
- [Results from Phase 1]

Detailed Investigation:
- [Results from Phase 2]
- Error analysis
- Configuration review
- Performance baseline

Deep Dive:
- [Results from Phase 3]
- Pattern analysis
- Reproduction steps

Root Cause:
- [Identified root cause]

Resolution:
- [Actions taken]
- [Verification steps]

Lessons Learned:
- [What could be done differently]
```


## Common Symptoms and Solutions

### Symptom 1: Link Not Coming Up

**Symptoms:**
- `ibstat` shows port state as "Down"
- `iblinkinfo` shows "LinkDown"
- No traffic can be sent/received

**Diagnostic Steps:**
```bash
# Check physical connection
ibstat -p

# Check transceiver status
ethtool -m mlx5_0

# Check for errors
ibqueryerrors --details

# Check kernel logs
dmesg | grep -i link
dmesg | grep -i mlx5
```

**Possible Causes and Solutions:**

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| Cable disconnected | Physical inspection | Reconnect cable |
| Transceiver failure | `ethtool -m` shows errors | Replace transceiver |
| Speed mismatch | `iblinkinfo` shows different speeds on each end | Set matching speed: `rdma link set dev mlx5_0 speed edr` |
| SM not running (IB) | `sminfo` fails | Start subnet manager |
| Port disabled | `ibstat` shows "PortDown" state | Enable port: `rdma link set dev mlx5_0 state up` |
| Firmware issue | Check firmware version | Update firmware: `mstflint -d <device> -i fw.bin burn` |

**Advanced Troubleshooting:**
```bash
# Check port physical state
cat /sys/class/infiniband/mlx5_0/ports/1/phys_state

# Check link width
cat /sys/class/infiniband/mlx5_0/ports/1/rate

# Check if port is administratively up
cat /sys/class/infiniband/mlx5_0/ports/1/state
```

---

### Symptom 2: High Latency

**Symptoms:**
- Applications report slow response times
- Latency measurements show >10μs for RDMA
- Performance is inconsistent

**Diagnostic Steps:**
```bash
# Measure latency
ib_write_lat -d mlx5_0 -s 4096

# Check queue depths
perfquery 1 0 --data

# Check CPU affinity
mlnx_affinity -d mlx5_0

# Check interrupt distribution
show_irq_affinity.sh

# Check for congestion
ibqueryerrors --details | grep -i overrun
```

**Possible Causes and Solutions:**

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| Poor NUMA locality | CPU and device on different NUMA nodes | Bind to same NUMA: `numactl --cpunodebind=0 --membind=0 ./app` |
| Queue depth too low | `perfquery` shows low queue utilization | Increase queue depth in application |
| Interrupt overhead | High CPU in interrupt context | Enable polling: `modprobe mlx5_core cq_poll_mode=1` |
| Congestion | Buffer overrun errors increasing | Enable PFC/ECN: `mlnx_qos -i eth0 -p 3,4` |
| Suboptimal MTU | Fragmentation overhead | Set MTU to match network: `rdma link set dev mlx5_0 mtu 2048` |

**Advanced Optimization:**
```bash
# Tune for low latency
mlnx_tune --profile low-latency

# Enable kernel bypass
echo 1 > /sys/module/mlx5_core/parameters/qp_stateless

# Set CPU isolation
isolcpus=4-7 in kernel command line
echo 4 > /sys/bus/pci/devices/0000:00:00.0/local_cpus
```

**Code-Level Optimization:**
```c
// Use inline data for small messages
struct ibv_send_wr wr = {
    .opcode = IBV_WR_SEND,
    .send_flags = IBV_SEND_INLINE,  // Inline for < 32 bytes
    .sg_list = &sge,
    .num_sge = 1
};

// Minimize queue depth for low latency
qp_init_attr.cap.max_send_wr = 16;
qp_init_attr.cap.max_recv_wr = 16;

// Use polling instead of events
ibv_req_notify_cq(cq, 0);
while (ibv_poll_cq(cq, 1, &wc) == 0);
```

---

### Symptom 3: Low Throughput

**Symptoms:**
- Cannot achieve expected bandwidth (e.g., <80% of theoretical)
- Throughput varies significantly
- Performance degrades over time

**Diagnostic Steps:**
```bash
# Measure throughput
ib_write_bw -d mlx5_0 -s 1048576 -i 5

# Check PCIe bandwidth
lspci -s <device> -vvv | grep -i lnksta

# Check for errors
ibqueryerrors

# Check buffer utilization
perfquery 1 0 --data

# Verify MTU
iblinkinfo -s
```

**Possible Causes and Solutions:**

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| MTU mismatch | `iblinkinfo` shows different MTU | Set consistent MTU: `rdma link set dev mlx5_0 mtu 2048` |
| PCIe bottleneck | `lspci` shows lower PCIe speed | Check PCIe slot speed, ensure Gen3/Gen4 |
| Insufficient queue depth | Queue full errors | Increase queue depth in application |
| Poor CPU distribution | `mpstat` shows unbalanced load | Optimize RSS/affinity: `mlnx_affinity --optimize` |
| Suboptimal message size | Small messages → overhead | Use larger messages (>4KB) |
| PCIe NUMA mismatch | Device and memory on different nodes | Use local NUMA node |

**Advanced Optimization:**
```bash
# Tune for high throughput
mlnx_tune --profile throughput

# Enable huge pages
echo 1024 > /proc/sys/vm/nr_hugepages
mount -t hugetlbfs nodev /dev/hugepages

# Optimize PCIe
echo performance > /sys/devices/pci0000:00/0000:00:00.0/power/control

# Increase send/receive buffers
echo 65536 > /proc/sys/net/core/rmem_max
echo 65536 > /proc/sys/net/core/wmem_max
```

**Code-Level Optimization:**
```c
// Use multiple QPs for parallelism
for (int i = 0; i < num_qps; i++) {
    qp[i] = create_qp(pd, cq);
}

// Optimize send/receive queue depths
qp_init_attr.cap.max_send_wr = 1024;
qp_init_attr.cap.max_recv_wr = 1024;
qp_init_attr.cap.max_send_sge = 4;
qp_init_attr.cap.max_recv_sge = 4;

// Register large memory regions
mr = ibv_reg_mr(pd, buffer, buffer_size,
    IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_WRITE);

// Use inline threshold properly
if (msg_size < INLINE_THRESHOLD) {
    wr.send_flags |= IBV_SEND_INLINE;
}
```

---

### Symptom 4: Connection Failures

**Symptoms:**
- Applications fail to establish RDMA connections
- Connection timeouts
- Connection rejected errors

**Diagnostic Steps:**
```bash
# Check if destination is reachable
ibping <dest_lid>

# Check routing (InfiniBand)
saquery -p | grep <dest_lid>

# Check GIDs (RoCE)
show_gids

# Check firewall rules
iptables -L -n

# Check application errors
dmesg | grep -i ibv
```

**Possible Causes and Solutions:**

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| Destination unreachable | `ibping` times out | Check fabric topology, SM routing |
| Invalid GID | `show_gids` shows wrong IP/GID | Configure correct IP: `ip addr add` |
| Firewall blocking | `iptables` shows REJECT | Open RDMA ports: 4791, 17990-17999 |
| Permission denied | `dmesg` shows permission errors | Fix /dev/infiniband permissions |
| Wrong QP type | Application uses incompatible QP type | Match QP types on both ends |
| SM misconfiguration | `saquery` fails | Fix SM configuration |

**Advanced Troubleshooting:**
```bash
# Trace route to destination
ibtracert <src_lid> <dest_lid>

# Check path records
saquery -p | grep <dest_gid>

# Verify connection state
rdma link show
rdma dev show

# Test with libibverbs example
cd /usr/lib/rdma-core/examples
./rc_pingpong <server_ip> <client_ip>
```

**Code-Level Debugging:**
```c
// Enable verbose error reporting
int rc = ibv_create_qp(pd, &qp_init_attr);
if (rc) {
    fprintf(stderr, "Failed to create QP: %s (%d)\n",
            strerror(errno), errno);
    // Common errors:
    // EAGAIN - Resource limit reached
    // EINVAL - Invalid parameters
    // ENOMEM - Out of memory
    return -1;
}

// Check QP state
struct ibv_qp_attr qp_attr;
struct ibv_qp_init_attr qp_init_attr;
ibv_query_qp(qp, &qp_attr, IBV_QP_STATE, &qp_init_attr);
printf("QP State: %d\n", qp_attr.qp_state);

// Check connection status
int fd = rdma_create_id(event_channel, &cm_id, NULL, RDMA_PS_TCP);
if (fd < 0) {
    perror("rdma_create_id");
    // Check: Is rdma_cm module loaded?
    // lsmod | grep rdma_cm
}
```

---

### Symptom 5: Increasing Error Counters

**Symptoms:**
- `ibqueryerrors` shows increasing error counts
- Performance degrades over time
- Link flaps intermittently

**Diagnostic Steps:**
```bash
# Get error summary
ibqueryerrors

# Get detailed breakdown
ibqueryerrors --details

# Monitor over time
watch -n 5 'ibqueryerrors --details'

# Check for hardware errors
dmesg | grep -i error
```

**Error Analysis Matrix:**

| Error Counter | Meaning | Likely Cause | Action |
|---------------|---------|--------------|--------|
| Symbol Errors | Physical layer signal issues | Bad cable, transceiver, or connector | Replace cable/transceiver |
| Link Recovery | Link training failures | Speed/mode mismatch, cable issues | Check link configuration |
| Excess Buffer Overruns | Congestion, insufficient buffering | Network congestion | Enable PFC/ECN |
| Local PHY Errors | Transceiver issues | Overheating, failing transceiver | Check temperature, replace transceiver |
| Discards | Resource exhaustion | Queue full, buffer full | Increase queue depth |
| VL15 Dropped | Unroutable packets | SM routing issues | Check SM configuration |

**Root Cause Analysis Example:**

```
Scenario: Increasing symbol errors on Port 1

Step 1: Identify pattern
- Errors increasing at steady rate
- Only on one port
- Other ports on same switch are fine

Step 2: Check physical layer
- Inspect cable: No visible damage
- Check transceiver: Temperature normal
- Try different cable: Errors stop

Conclusion: Bad cable
Resolution: Replace cable
```

**Preventive Measures:**
```bash
# Set up monitoring
ibqueryerrors -o /var/log/rdma_errors.log &

# Configure alerts in /etc/ibdiag.conf/error_thresholds
symbol_error_permissive: 100
link_error_recovery_permissive: 10

# Regular health checks
cat > /etc/cron.daily/rdma_health.sh << 'EOF'
#!/bin/bash
ibqueryerrors | mail -s "RDMA Error Report" admin@example.com
EOF
chmod +x /etc/cron.daily/rdma_health.sh
```


## Tool Usage Guide

This section provides detailed usage instructions for key RDMA diagnostic tools.

### infiniband-diags Tools

#### ibstat - Device Status Query

**Purpose:** Query and display InfiniBand device and port status

**Basic Usage:**
```bash
# List all devices
ibstat -l

# Show all devices and ports
ibstat

# Show specific device
ibstat mlx5_0

# Show specific port
ibstat mlx5_0 1

# Short format
ibstat -s

# Show port GUIDs
ibstat -p
```

**Output Interpretation:**
```
CA 'mlx5_0'
        CA type: MT4115
        Number of ports: 2
        Firmware version: 16.31.1012
        Hardware version: 0
        Node GUID: 0x506b00000000a
        System image GUID: 0x506b00000000a

        Port 1:
                State: Active
                Physical state: LinkUp
                Rate: 100
                Base lid: 1
                LMC: 0
                SM lid: 0
                Capability mask: 0x07610868
                Max MTU: 2048
                Active MTU: 2048
                QPN_vl0: 0x000003
                SM SL: 0
                PIC: 0x2
                GID index: 0
                Pkey index: 0
                Link layer: InfiniBand
```

**Expert Tips:**
- Check `State` and `Physical state` to verify link status
- Compare `Rate` with expected speed (100=HDR, 50=EDR, 25=FDR, etc.)
- Verify `Max MTU` vs `Active MTU` - mismatch indicates MTU issue
- Check `SM lid` - 0 means no SM detected (InfiniBand only)

---

#### ibqueryerrors - Error Counter Analysis

**Purpose:** Query and analyze error counters across the fabric

**Basic Usage:**
```bash
# Query all ports with errors exceeding threshold
ibqueryerrors

# Query specific port by GUID
ibqueryerrors -G 0x506b00000000a

# Query with detailed breakdown
ibqueryerrors --details

# Query switches only
ibqueryerrors --switch

# Include data counters for error ports
ibqueryerrors --data

# Suppress specific error types
ibqueryerrors -s 1,2,3

# Clear errors after reading
ibqueryerrors -k

# Query with timeout
ibqueryerrors -o 10
```

**Understanding Output:**
```
0x506b00000000a "Switch-1" (Port 1):
        SymbolErrors[1]: 0 (Threshold: 100)
        LinkErrorRecovery[2]: 5 (Threshold: 10) [EXCEEDS]
        LinkDowned[3]: 0 (Threshold: 10)
        ExcessiveBufferOverrun[5]: 1234 (Threshold: 100) [EXCEEDS]
        LocalLinkIntegrityErrors[6]: 0 (Threshold: 10)
        RcvErrors[8]: 0 (Threshold: 10)
        XmtDiscards[9]: 56 (Threshold: 50) [EXCEEDS]
        RcvConstraintErrors[10]: 0 (Threshold: 10)
        XmtConstraintErrors[11]: 0 (Threshold: 10)
        XmitWait[12]: 0 (Threshold: 10)
```

**Expert Tips:**
- Errors marked `[EXCEEDS]` need immediate attention
- `LinkErrorRecovery` indicates link training issues
- `ExcessiveBufferOverrun` suggests congestion
- Use `--details` to get breakdown of specific errors
- Configure thresholds in `/etc/ibdiag.conf/error_thresholds`

**Error Counter Reference:**
```
[1] SymbolErrors: Physical layer signal integrity
[2] LinkErrorRecovery: Link training failures
[3] LinkDowned: Link went down
[5] ExcessiveBufferOverrun: Congestion
[6] LocalLinkIntegrityErrors: Link layer errors
[8] RcvErrors: Receive errors
[9] XmtDiscards: Transmit discards
[10] RcvConstraintErrors: Receive constraint violations
[11] XmtConstraintErrors: Transmit constraint violations
[12] XmitWait: Transmit waiting
```

---

#### ibnetdiscover - Fabric Topology Discovery

**Purpose:** Discover and map InfiniBand fabric topology

**Basic Usage:**
```bash
# Discover entire fabric
ibnetdiscover

# Save topology to cache
ibnetdiscover --save-cache fabric.cache

# Load from cache (faster)
ibnetdiscover --load-cache fabric.cache

# Discover around specific port
ibnetdiscover -G 0x506b00000000a

# Limit discovery hops
ibnetdiscover -H 3

# Discover only switches
ibnetdiscover --switch
```

**Output Format:**
```
# Topology file for
# Generated on: ...

Ca   0x506b00000000a[1] "Node-1" ...
        Ca   0x506b00000000b[1] "Node-2" ...
                Port 1: "SWITCH-1/U1"
        Sw   0x506b00000000c[8]" "SWITCH-1"
```

**Expert Tips:**
- Use `--save-cache` for faster subsequent queries
- Limit hops with `-H` for large fabrics
- Cache files are human-readable for manual inspection

---

### mlnx-tools

#### mlnx_perf - Performance Monitoring

**Purpose:** Real-time performance monitoring and analysis

**Basic Usage:**
```bash
# Monitor device with 1-second interval
mlnx_perf -d mlx5_0 -i 1

# Collect for 60 seconds, export to CSV
mlnx_perf -d mlx5_0 -t 60 -o perf.csv

# Focus on latency metrics
mlnx_perf --latency -d mlx5_0

# Monitor multiple devices
mlnx_perf -d mlx5_0 -d mlx5_1
```

**Key Metrics:**
- Throughput: Bytes/packets per second
- Latency: Average, P50, P95, P99
- CPU utilization: Per-core
- Queue depths: Send/Receive queues
- Error rates: Packet loss, retries

---

#### mlnx_qos - QoS Configuration

**Purpose:** Configure Quality of Service for RDMA networks

**Basic Usage:**
```bash
# Enable PFC on priorities 3,4
mlnx_qos -i eth0 -p 3,4

# Configure ETS bandwidth allocation
mlnx_qos -i eth0 -e 50:30:20

# Show current QoS configuration
mlnx_qos -i eth0 --show

# Validate QoS configuration
mlnx_qos -i eth0 --validate
```

**QoS Concepts:**
- **PFC:** Priority Flow Control for lossless delivery
- **ETS:** Enhanced Transmission Selection for bandwidth allocation
- **DCBX:** DCB exchange for auto-configuration

---

#### mlnx_tune - System Optimization

**Purpose:** Optimize system parameters for RDMA performance

**Basic Usage:**
```bash
# Apply low-latency profile
mlnx_tune --profile low-latency

# Enable NUMA-aware tuning
mlnx_tune --numa-aware 1

# Show current tuning status
mlnx_tune --show

# Revert previous changes
mlnx_tune --rollback
```

**Optimization Areas:**
- Kernel parameters (memory limits, buffers)
- CPU management (NUMA, affinity)
- Interrupt configuration
- Memory management (huge pages)


## Advanced Diagnostics

### Performance Profiling

#### Collecting Performance Metrics

**Baseline Collection:**
```bash
# Collect 10-minute baseline
mlnx_perf -d mlx5_0 -i 1 -t 600 -o baseline.csv

# Export for analysis
python << 'EOF'
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('baseline.csv')
df.plot(x='timestamp', y=['throughput', 'latency'])
plt.savefig('baseline.png')
EOF
```

**Correlation Analysis:**
```bash
# Collect multiple metrics simultaneously
(
  mlnx_perf -d mlx5_0 -i 1 -t 300 &
  ibqueryerrors -o errors.log &
  mpstat 1 300 > cpu.log &
) &
wait

# Analyze correlations
python << 'EOF'
# Correlate errors with performance drops
# Identify bottlenecks
# Generate recommendations
EOF
```

---

### Kernel Debugging

#### RDMA Subsystem Debugging

**Enable RDMA Debug:**
```bash
# Enable RDMA debugging
echo 0xffffffff > /sys/module/rdma_core/parameters/debug_level

# Enable mlx5 debugging
echo 1 > /sys/module/mlx5_core/parameters/debug_mask

# Enable Verbs debugging
echo 1 > /sys/module/ib_core/parameters/debug_level

# Monitor kernel logs
dmesg -w | tee rdma_debug.log
```

**Common Kernel Messages:**
```
# Memory registration errors
mlx5_core 0000:04:00.0: Failed to register MR: Invalid argument
→ Check memory alignment and access flags

# QP creation failures
ib_core: create_qp: Invalid parameter
→ Verify QP initialization attributes

# Completion queue errors
mlx5_core 0000:04:00.0: CQ completion error
→ Check completion queue handling in application
```

---

### Hardware-Level Diagnostics

#### Transceiver Diagnostics
```bash
# Check transceiver information
ethtool -m mlx5_0

# Check temperature
ethtool -m mlx5_0 | grep Temperature

# Check optical power
ethtool -m mlx5_0 | grep 'Power'

# Replace if out of spec
mstconfig -d <device> -y SET_INT_MODERATION=0
```

#### Firmware Diagnostics
```bash
# Check firmware version
mstflint -d <device> q

# Query firmware capabilities
mstflint -d <device> -i fw.bin --query

# Update firmware
mstflint -d <device> -i fw.bin --burn

# Reset to factory defaults
mstflint -d <device> --reset
```

---

### Network Capture and Analysis

#### Packet Capture
```bash
# Capture RDMA traffic (requires Mellanox OFED)
tcpdump -i eth0 -w rdma.pcap port 4791

# Analyze with Wireshark
wireshark rdma.pcap

# Filter for specific verbs
wireshark -Y "ibv.opcode == 0x12"
```

#### Flow Analysis
```bash
# Trace RDMA flows
rdma netns exec <netns> rdma link show

# Monitor connection events
rdma monitor

# Analyze QP states
rdma qp show
```


## Case Studies

### Case Study 1: Intermittent Connection Failures in RoCEv2 Cluster

**Problem:**
- 100-node RoCEv2 cluster
- Random connection failures
- Failure rate: 5-10%
- No pattern in time or location

**Investigation:**

Phase 1: Initial Assessment
```bash
# Check link states
ibstat -l
# Result: All links up

# Check error counters
ibqueryerrors
# Result: Minimal errors across all nodes

# Check GIDs
show_gids
# Result: All GIDs configured correctly
```

Phase 2: Deep Dive
```bash
# Monitor during failures
ibqueryerrors -o errors.log &
mlnx_perf -d mlx5_0 -i 1 -t 600 &

# Reproduce issue
# Run workload for 10 minutes

# Analyze patterns
grep -i timeout errors.log
# Found: Timeouts correlate with high traffic periods
```

Phase 3: Root Cause Analysis
```bash
# Check switch configuration
show_gids
# Result: All GIDs correct

# Check network path
ibtracert <src> <dest>
# Result: Path changes dynamically

# Check routing table
saquery -p
# Result: Multiple paths causing route flapping
```

**Root Cause:**
- Load balancing causing route flapping
- ECMP (Equal Cost Multi-Path) not properly configured for RDMA

**Solution:**
```bash
# Disable ECMP for RDMA traffic
mlnx_qos -i eth0 --route-mode static

# Pin routes
ip route add <dest> dev eth0

# Validate
ibtracert <src> <dest>
# Result: Stable path
```

**Result:**
- Connection failures reduced to <0.1%
- Performance improved by 15%
- System stable for 30 days

---

### Case Study 2: High Latency in InfiniBand Fabric

**Problem:**
- HDR InfiniBand fabric
- Latency spikes to 50-100μs (baseline: 2-5μs)
- Affects 20% of nodes
- Correlates with high load periods

**Investigation:**

Phase 1: Initial Assessment
```bash
# Measure latency
ib_write_lat -d mlx5_0 -s 4096
# Result: 8-12μs average, spikes to 50μs

# Check error counters
ibqueryerrors
# Result: High buffer overrun counts

# Check queue depths
perfquery 1 0 --data
# Result: Queue utilization >90%
```

Phase 2: Detailed Investigation
```bash
# Monitor queue depths
watch -n 1 'perfquery 1 0 --data | grep Queue'

# Check CPU affinity
mlnx_affinity -d mlx5_0
# Result: Poor affinity, interrupts on all cores

# Check NUMA locality
numactl -H
# Result: CPU and device on different NUMA nodes
```

Phase 3: Optimization
```bash
# Optimize affinity
mlnx_affinity -d mlx5_0 --optimize

# Bind to NUMA
numactl --cpunodebind=0 --membind=0 ./application

# Tune for low latency
mlnx_tune --profile low-latency
```

**Root Cause:**
- Poor NUMA locality causing cache thrashing
- Unbalanced interrupt distribution
- Queue depths too high for latency-sensitive workload

**Solution:**
```bash
# Optimize NUMA
echo 0 > /sys/bus/pci/devices/0000:04:00.0/numa_node
echo 4-7 > /sys/bus/pci/devices/0000:04:00.0/local_cpus

# Reduce queue depths
# Application changes: max_send_wr=16, max_recv_wr=16

# Enable polling
modprobe mlx5_core cq_poll_mode=1
```

**Result:**
- Average latency: 2-3μs
- Spikes eliminated (<5μs)
- CPU utilization reduced by 30%
- Performance consistent under load

---

### Case Study 3: Symbol Errors on ConnectX-5 Adapter

**Problem:**
- ConnectX-5 adapter
- Increasing symbol errors
- Error rate: 100-200 errors/hour
- Only on one port

**Investigation:**

Phase 1: Physical Layer Check
```bash
# Check transceiver
ethtool -m mlx5_0
# Result: No errors reported

# Check cable
# Visual inspection: No visible damage
# Try different cable: Errors persist

# Check switch port
# Error rate same on switch port
```

Phase 2: Detailed Analysis
```bash
# Monitor error pattern
watch -n 5 'ibqueryerrors --details'

# Check environmental factors
sensors
# Result: Temperature normal (45°C)

# Check PCIe
lspci -s <device> -vvv
# Result: PCIe Gen3 x8 (expected Gen3 x8)
```

Phase 3: Swap Test
```bash
# Swap transceiver
# Result: No change

# Swap port on switch
# Result: No change

# Swap adapter
# Result: Errors follow adapter
```

**Root Cause:**
- Defective hardware (adapter port)
- Issue with specific port on adapter

**Solution:**
```bash
# RMA adapter
# Contact vendor for replacement

# Temporary workaround
# Use other port on same adapter

# Verify replacement
ibqueryerrors
# Result: No errors after 24 hours
```

**Result:**
- Adapter replaced under warranty
- Symbol errors eliminated
- System stable


## Quick Reference

### Common Commands

```bash
# Device Status
ibstat                    # Show device status
rdma link show             # Show RDMA links
rdma dev show             # Show RDMA devices

# Error Analysis
ibqueryerrors              # Query error counters
ibqueryerrors --details    # Detailed error breakdown
show_counters              # Show all counters

# Topology
ibnetdiscover             # Discover fabric
iblinkinfo                # Link information
ibtracert <lid> <lid>    # Trace route

# Performance
perfquery <lid> <port>    # Performance counters
mlnx_perf -d <dev>        # Monitor performance
ib_write_lat -d <dev>       # Latency test
ib_write_bw -d <dev>        # Throughput test

# Configuration
mlnx_qos -i <dev> --show  # Show QoS
mlnx_tune --show           # Show tuning
rdma link set dev <dev> mtu 2048  # Set MTU
```

### Error Codes Reference

| Error Code | Meaning | Common Cause | Action |
|------------|---------|--------------|--------|
| EAGAIN | Resource temporarily unavailable | Resource limits, retry needed | Retry operation, check limits |
| EINVAL | Invalid argument | Invalid parameters | Check input parameters |
| ENOMEM | Out of memory | Insufficient memory | Free memory, increase limits |
| EACCES | Permission denied | Insufficient permissions | Check file permissions |
| ETIMEDOUT | Operation timed out | Timeout occurred | Increase timeout, check network |
| ECONNREFUSED | Connection refused | Connection rejected | Check firewall, configuration |
| ENODEV | No such device | Device not found | Check device status |

### Performance Targets

| Metric | Target | Good | Needs Investigation |
|--------|--------|-------|-------------------|
| Latency (RDMA) | <5μs | 1-10μs | >10μs |
| Throughput (HDR) | >90 Gbps | >80 Gbps | <80 Gbps |
| CPU Utilization | <30% | <50% | >50% |
| Error Rate | 0 | <0.001% | >0.01% |
| Link Uptime | 99.999% | >99.9% | <99.9% |

### Contact Information

**Vendor Support:**
- Mellanox/NVIDIA: https://developer.nvidia.com/networking
- Linux RDMA: https://github.com/linux-rdma/rdma-core

**Community Resources:**
- RDMA mailing list: linux-rdma@vger.kernel.org
- OFED mailing list: ofiw@lists.openfabrics.org

**Documentation:**
- RDMA Core: https://linux-rdma.readthedocs.io/
- Mellanox Docs: https://docs.nvidia.com/

---

**Document Revision History:**
- v1.0 (2026-01-30): Initial release

**Contributors:**
- RDMA Engineering Team
- Network Operations Team
- Customer Support Team
