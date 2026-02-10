---
title: "InfiniBand Troubleshooting Guide"
category: troubleshooting
tags: [infiniband, troubleshooting, diagnostics, opensm, ibdiag]
---

# InfiniBand Troubleshooting Guide

## 1. Link Issues

### 1.1 Check Port State

```bash
# Quick port status
ibstat
# Example output:
# CA 'mlx5_0'
#     CA type: MT4123
#     Number of ports: 1
#     Port 1:
#         State: Active          ← Should be Active
#         Physical state: LinkUp ← Should be LinkUp
#         Rate: 200 (4X HDR)
#         Base lid: 1
#         LMC: 0
#         SM lid: 1
#         Capability mask: 0x2651e848

# More detail
ibstatus
ibv_devinfo -d mlx5_0
```

### 1.2 Common Port States

| State | Physical State | Meaning | Action |
|-------|---------------|---------|--------|
| Down | Polling | No link partner detected | Check cable, remote port |
| Down | Disabled | Port admin disabled | `ibportstate -D 0 1 enable` |
| Init | LinkUp | Link up, no SM config | Check SM is running |
| Active | LinkUp | Normal operation | OK |
| Armed | LinkUp | SM partially configured | Wait or restart SM |

### 1.3 Link Speed/Width Issues

```bash
# Check current speed
ibstat | grep -E "Rate|Width"

# Expected speeds:
# EDR = 100G (4X 25G)
# HDR = 200G (4X 50G per lane, PAM4)
# NDR = 400G (4X 100G per lane)

# If speed lower than expected:
# Check cable quality
ibdiagnet --cable_info

# Force link speed (debug only)
ibportstate -D 0 1 speed 5  # FDR
ibportstate -D 0 1 speed 10 # EDR

# Check if width negotiated correctly
# x4 is normal, x1 or x2 indicates cable or connector issue
```

## 2. Subnet Manager Issues

### 2.1 Check SM Status

```bash
# Is SM running?
sminfo
# Output: sminfo: sm lid 1 sm guid 0x..., activity count ... state MASTER

# SM status query
opensm --help  # verify installed
systemctl status opensm

# View SM log
tail -f /var/log/opensm.log

# List all SMs in fabric
saquery -s  # query SA for SM records
```

### 2.2 Common SM Problems

**SM not starting:**
```bash
# Check if another SM is master
sminfo
# Check opensm config
cat /etc/opensm/opensm.conf | grep -v "^#"

# Start with debug
opensm -d 2 -f /tmp/opensm.log
```

**SM flapping (frequent handovers):**
```bash
# Check for multiple SMs with same priority
saquery -s
# Adjust priority in /etc/opensm/opensm.conf:
# sm_priority 15  (higher = more likely to be master, range 0-15)

# Check for network instability causing SM re-sweeps
grep -c "sweep" /var/log/opensm.log
```

**Nodes not discovered:**
```bash
# Run topology discovery
ibnetdiscover > /tmp/topo.txt
# Check all expected nodes are listed

# Trace path to missing node
ibtracert <src_lid> <dst_lid>

# Check for disabled ports on switches
ibswitches
ibportstate <switch_guid> <port> query
```

## 3. Error Counter Analysis

### 3.1 Reading Error Counters

```bash
# All error counters for a port
perfquery -x <lid> <port>

# All ports on local HCA
perfquery -x

# All errors across entire fabric
ibqueryerrors

# Extended counters
perfquery -x -X <lid> <port>
```

### 3.2 Error Counter Reference

| Counter | Significance | Common Cause |
|---------|-------------|--------------|
| SymbolErrors | Signal integrity issues | Bad cable, dirty connector |
| LinkRecovers | Link error recovery events | Marginal cable, EMI |
| LinkDowned | Link went down | Cable disconnect, port issue |
| RcvErrors | Packets with errors received | Cable, signal integrity |
| RcvRemPhysErrors | Remote physical errors | Remote port/cable issue |
| XmtDiscards | Packets discarded on transmit | Congestion, buffer full |
| XmtConstraintErrors | VL/pkey violations | Config error |
| RcvConstraintErrors | VL/pkey violations | Config error |
| LocalLinkIntegrityErr | Local link integrity | Bad cable/connector |
| ExcBufOverrunErrors | Buffer overrun | Congestion |
| VL15Dropped | Management packets dropped | SM overload |

### 3.3 Interpreting Errors

```bash
# High SymbolErrors + LinkRecovers:
#   → Cable quality issue, replace cable
#   → Clean connectors with IPA wipe
#   → Check for minimum bend radius violations

# XmtDiscards increasing:
#   → Congestion at this port
#   → Check routing (traffic imbalance)
#   → Verify adaptive routing is enabled

# RcvErrors without SymbolErrors:
#   → Possible MTU mismatch
#   → Check pkey membership

# Clear counters (after diagnostics)
perfquery -R <lid> <port>  # Reset counters
```

## 4. Routing Diagnostics

### 4.1 Path Tracing

```bash
# Trace path between two LIDs
ibtracert <src_lid> <dst_lid>

# Trace by GID
ibtracert -G <src_gid> <dst_gid>

# Trace path from local port
ibtracert 0 <dst_lid>
```

### 4.2 Forwarding Table Inspection

```bash
# Dump LFT (Linear Forwarding Table) from a switch
dump_lfts <switch_lid>

# Multicast forwarding tables
dump_mfts <switch_lid>

# Full routing analysis
ibdiagnet --routing

# Check for routing loops
ibdiagnet --routing --check_duplicated_guids
```

### 4.3 Routing Algorithm Selection (opensm.conf)

```ini
# OpenSM routing algorithms:
# routing_engine min-hop          # Default, shortest path
# routing_engine updn             # Up/Down for non-minimal topologies
# routing_engine fat-tree         # Optimized for fat-tree topologies
# routing_engine dfsssp           # Dead-Free Single Source Shortest Path
# routing_engine torus-2QoS       # Optimized for torus topologies
# routing_engine ar-updn          # Adaptive routing with UPDN
```

## 5. Performance Diagnostics

### 5.1 Bandwidth Testing

```bash
# Server side
ib_write_bw -d mlx5_0

# Client side (specify server IP/hostname)
ib_write_bw -d mlx5_0 <server>

# Expected results (approximate):
# EDR (100G): ~12.0 GB/s (96 Gbps)
# HDR (200G): ~24.0 GB/s (192 Gbps)
# NDR (400G): ~48.0 GB/s (384 Gbps)

# Multiple QPs for better throughput
ib_write_bw -d mlx5_0 -q 4 <server>

# With specific message size
ib_write_bw -d mlx5_0 -s 65536 --report_gbits <server>
```

### 5.2 Latency Testing

```bash
# Server
ib_write_lat -d mlx5_0

# Client
ib_write_lat -d mlx5_0 <server>

# Expected latency:
# Same switch: 0.6-1.0 μs
# 1 hop: 1.0-1.5 μs
# Multiple hops: add ~0.1-0.3 μs per hop

# RDMA Read latency (more meaningful for apps)
ib_read_lat -d mlx5_0 <server>
```

### 5.3 Fabric-wide Performance

```bash
# ibdiagnet comprehensive check
ibdiagnet

# This checks:
# - Topology validation
# - Link error counters
# - Routing validity
# - Speed/width consistency
# - Partition key consistency
# - Credit loops
# Generates report in /tmp/ibdiagnet2/
```

## 6. Partition Key Issues

```bash
# Check partition membership
saquery -P  # List all partitions

# Check which pkeys a port has
smpquery pkeys <lid> <port>

# Verify IPoIB partitions
cat /sys/class/infiniband/mlx5_0/ports/1/pkeys/*

# Common issue: QP uses pkey not in port's pkey table
# Fix: Add pkey via SM configuration (opensm partitions.conf)
```

## 7. MPI Debugging

```bash
# Common MPI over IB issues:

# 1. Check IB devices visible
ibv_devinfo

# 2. Test basic connectivity
ibping -S  # server
ibping -L <remote_lid>  # client

# 3. OpenMPI RDMA settings
mpirun --mca btl openib,self -np 4 --hostfile hosts ./my_app
# Debug:
mpirun --mca btl_base_verbose 100 --mca btl openib,self ...

# 4. MVAPICH2 settings
export MV2_USE_RDMA_CM=1
export MV2_IBA_HCA=mlx5_0
mpirun -np 4 -hostfile hosts ./my_app
```

## 8. Quick Reference: Diagnostic Commands

| Command | Purpose |
|---------|---------|
| `ibstat` | Port state, speed, LID |
| `ibstatus` | Port state summary |
| `ibv_devinfo` | RDMA device details |
| `ibv_devices` | List RDMA devices |
| `sminfo` | Subnet Manager info |
| `ibnetdiscover` | Fabric topology |
| `ibswitches` | List switches |
| `iblinkinfo` | All link states |
| `perfquery` | Port performance counters |
| `ibqueryerrors` | Fabric-wide errors |
| `ibtracert` | Trace path |
| `ibping` | IB-level ping |
| `ibdiagnet` | Comprehensive fabric diagnostics |
| `saquery` | Subnet Administrator queries |
| `smpquery` | Subnet Management queries |
| `ibportstate` | Port state control |
| `dump_lfts` | Forwarding table dump |
| `opensm` | Subnet Manager daemon |
| `ibcacheedit` | Edit ibdiagnet cache |
