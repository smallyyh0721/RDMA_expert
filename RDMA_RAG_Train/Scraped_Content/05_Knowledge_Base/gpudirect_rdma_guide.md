---
title: "GPUDirect RDMA Setup and Usage Guide"
category: kb
tags: [gpudirect, rdma, gpu, nccl, cuda, ai, ml]
---

# GPUDirect RDMA Setup and Usage Guide

## 1. Overview

GPUDirect RDMA enables direct data transfer between GPU memory and a network adapter (NIC/HCA) without going through the CPU or system memory. This eliminates two memory copies and significantly reduces latency for GPU-to-GPU communication.

### Data Path Comparison

```
Without GPUDirect RDMA:
  GPU mem → PCIe → System mem (CPU copy) → PCIe → NIC → Network
  Latency: ~10-20 μs, CPU involved

With GPUDirect RDMA:
  GPU mem → PCIe → NIC → Network
  Latency: ~2-5 μs, zero CPU involvement
```

## 2. Requirements

### 2.1 Hardware
- NVIDIA GPU (Kepler or later, compute capability ≥ 3.5)
- NVIDIA ConnectX-3 Pro or later NIC
- GPU and NIC should be on the same PCIe root complex (ideally same switch)
- PCIe ACS must be disabled on bridges between GPU and NIC

### 2.2 Software
- NVIDIA GPU driver (≥ 418.40)
- CUDA toolkit (≥ 10.0)
- MLNX_OFED (≥ 4.5)
- nvidia-peermem kernel module (replaces legacy nv_peer_mem)

## 3. Setup

### 3.1 Install nvidia-peermem
```bash
# With MLNX_OFED >= 5.1, nvidia-peermem is included
sudo modprobe nvidia-peermem

# Verify loaded
lsmod | grep nvidia_peermem
dmesg | grep peermem
# Should show: "nvidia-peermem: module loaded"

# For older setups (nv_peer_mem - deprecated)
git clone https://github.com/Mellanox/nv_peer_memory.git
cd nv_peer_memory && make && sudo insmod nv_peer_mem.ko

# Make persistent
echo "nvidia-peermem" >> /etc/modules-load.d/gpudirect.conf
```

### 3.2 Verify GPU-NIC Topology
```bash
nvidia-smi topo -m
# Example output:
#         GPU0  GPU1  mlx5_0  mlx5_1  CPU Affinity
# GPU0     X     NV4   PIX     SYS     0-15
# GPU1    NV4     X    SYS     PIX     16-31
# mlx5_0  PIX    SYS    X      SYS     0-15
# mlx5_1  SYS    PIX   SYS      X     16-31

# Key: PIX = same PCIe switch (BEST for GPUDirect)
#      PHB = same PCIe host bridge (good)
#      SYS = crosses NUMA/socket boundary (suboptimal)
#      NV = NVLink (GPU-to-GPU only)
```

### 3.3 Disable PCIe ACS
```bash
# ACS (Access Control Services) prevents peer-to-peer PCIe transactions
# Must be disabled on all bridges between GPU and NIC

# Find bridges
lspci -t  # shows PCIe topology tree

# Disable ACS on each bridge
for bdf in $(lspci -d "*:*" -PP | grep "PCI bridge" | awk '{print $1}'); do
    setpci -s "$bdf" ECAP_ACS+6.w=0000 2>/dev/null
done

# Or at boot via kernel parameter:
# pcie_acs_override=downstream,multifunction
```

### 3.4 IOMMU Considerations
```bash
# For GPUDirect RDMA, use passthrough mode
# Kernel cmdline: iommu=pt
# This is critical - without it, GPUDirect performance degrades significantly
```

## 4. NCCL Configuration for Multi-Node GPU Training

### 4.1 Key NCCL Environment Variables

```bash
# Enable RDMA (IB/RoCE) for inter-node communication
export NCCL_IB_DISABLE=0              # 0 = enable IB/RoCE

# Select specific HCA
export NCCL_IB_HCA=mlx5_0            # Or mlx5_0,mlx5_1 for multi-rail
export NCCL_IB_HCA=mlx5               # Wildcard: use all mlx5 devices

# GPUDirect RDMA level
export NCCL_NET_GDR_LEVEL=5           # 5 = PIX (same PCIe switch)
# Values: 0=LOC, 1=SYS, 2=PHB, 3=PXB, 4=PIX, 5=PIX

# GPUDirect RDMA read/write
export NCCL_NET_GDR_READ=1            # 1 = use GDR for reads

# Number of IB channels
export NCCL_IB_QPS_PER_CONNECTION=4   # QPs per connection

# Traffic class (for RoCE QoS)
export NCCL_IB_TC=106                 # DSCP 26 = ToS 106

# GID index (for RoCE v2)
export NCCL_IB_GID_INDEX=3            # Use RoCE v2 GID

# Timeout
export NCCL_IB_TIMEOUT=23             # IB timeout

# Retry count
export NCCL_IB_RETRY_CNT=7            # Max retries

# Socket interface for OOB communication
export NCCL_SOCKET_IFNAME=eth0

# Debug
export NCCL_DEBUG=INFO                # INFO, WARN, TRACE
export NCCL_DEBUG_SUBSYS=NET          # Focus on network debug
```

### 4.2 Multi-Rail Configuration
```bash
# Use all available NICs
export NCCL_IB_HCA=mlx5_0,mlx5_1,mlx5_2,mlx5_3

# Or auto-detect
export NCCL_IB_HCA=mlx5

# For DGX-like systems with 8 GPUs and 8 NICs:
# Each GPU is paired with a NIC on the same PCIe switch
# NCCL automatically selects the closest NIC for each GPU
```

## 5. Testing GPUDirect RDMA

### 5.1 Basic Test with perftest
```bash
# Server
ib_write_bw -d mlx5_0 --use_cuda=0   # Use GPU 0

# Client
ib_write_bw -d mlx5_0 --use_cuda=0 <server_ip>

# Compare with non-GPUDirect (CPU memory)
ib_write_bw -d mlx5_0 <server_ip>
```

### 5.2 NCCL Tests
```bash
# Install nccl-tests
git clone https://github.com/NVIDIA/nccl-tests.git
cd nccl-tests && make CUDA_HOME=/usr/local/cuda NCCL_HOME=/usr

# Run all-reduce test
mpirun -np 8 --hostfile hosts \
  -x NCCL_IB_DISABLE=0 \
  -x NCCL_DEBUG=INFO \
  ./build/all_reduce_perf -b 8 -e 128M -f 2 -g 1
```

### 5.3 nvbandwidth
```bash
# Test GPU-to-GPU and GPU-to-NIC bandwidth
nvbandwidth --testcase=device_to_device
nvbandwidth --testcase=host_to_device
```

## 6. Troubleshooting

### 6.1 GPUDirect Not Working
```bash
# Check nvidia-peermem loaded
lsmod | grep nvidia_peermem
# If not: modprobe nvidia-peermem

# Check GPU driver
nvidia-smi

# Check dmesg for errors
dmesg | grep -i "peermem\|gpu\|nv_peer"

# Verify GPU and NIC on same PCIe tree
nvidia-smi topo -m
# If SYS: GPUDirect will still work but slowly (via CPU bounce)
```

### 6.2 Poor GPUDirect Performance
```bash
# Check PCIe ACS
lspci -vvv | grep -i "ACSCtl"
# ACS must be disabled

# Check IOMMU mode
dmesg | grep -i iommu
# Should be passthrough mode (iommu=pt)

# Check BAR size
nvidia-smi -q | grep "BAR1"
# Should be large enough for workload

# Check GPU-NIC affinity
nvidia-smi topo -m
# PIX or PHB is required for good performance
```
