---
title: "PCIe Fundamentals for NIC/HCA Understanding"
category: web_content
tags: [pcie, bus, dma, performance, numa, hardware]
---

# PCIe Fundamentals for NIC/HCA Understanding

## 1. PCIe Generations and Speeds

| PCIe Gen | Signal Rate | Per-Lane Bandwidth | x16 Bandwidth | Encoding |
|----------|------------|-------------------|---------------|----------|
| Gen 1.0 | 2.5 GT/s | 250 MB/s | 4 GB/s | 8b/10b |
| Gen 2.0 | 5.0 GT/s | 500 MB/s | 8 GB/s | 8b/10b |
| Gen 3.0 | 8.0 GT/s | ~1 GB/s | ~16 GB/s | 128b/130b |
| Gen 4.0 | 16.0 GT/s | ~2 GB/s | ~32 GB/s | 128b/130b |
| Gen 5.0 | 32.0 GT/s | ~4 GB/s | ~64 GB/s | 128b/130b |
| Gen 6.0 | 64.0 GT/s | ~8 GB/s | ~128 GB/s | 242b/256b (PAM4) |

### NIC PCIe Requirements

| Adapter | Link Speed | Required PCIe | PCIe BW |
|---------|-----------|--------------|---------|
| ConnectX-5 | 100G | Gen3 x16 or Gen4 x8 | 16/16 GB/s |
| ConnectX-6 | 200G | Gen4 x16 | 32 GB/s |
| ConnectX-6 Dx | 100G | Gen4 x8 | 16 GB/s |
| ConnectX-7 | 400G | Gen5 x16 | 64 GB/s |
| ConnectX-8 | 800G | Gen5/6 x16 | 64-128 GB/s |

## 2. PCIe Configuration Parameters

### 2.1 MPS (Max Payload Size)
- Maximum data in single TLP (Transaction Layer Packet)
- Values: 128, 256, 512, 1024, 2048, 4096 bytes
- Negotiated as minimum of device and root complex capability
- Higher = better throughput (fewer headers)

### 2.2 MRRS (Max Read Request Size)
- Maximum data requested in single read
- Values: 128, 256, 512, 1024, 2048, 4096 bytes
- Affects RDMA read performance significantly
- Set to 4096 for best RDMA performance

### 2.3 Checking PCIe Configuration
```bash
# Full PCIe details
lspci -vvv -s <bdf>

# Quick check for speed and width
lspci -vvv -s 3b:00.0 | grep -E "LnkCap|LnkSta|MaxPayload|MaxReadReq"

# Example output:
# LnkCap: Speed 16GT/s (Gen4), Width x16
# LnkSta: Speed 16GT/s, Width x16    ← Should match LnkCap
# DevCtl: MaxPayload 256 bytes, MaxReadReq 4096 bytes
```

## 3. DMA (Direct Memory Access)

### 3.1 How RDMA Uses DMA
1. Application registers memory region with `ibv_reg_mr()`
2. Driver pins pages and creates DMA mapping (IOVA → physical address)
3. NIC DMAs data directly to/from application buffer
4. No CPU involvement in data movement

### 3.2 IOMMU and DMA
```bash
# IOMMU translates device DMA addresses
# Modes:
# - Off: Device uses physical addresses directly
# - Passthrough (iommu=pt): IOVA = physical (fastest)
# - Full: IOVA translated via page tables (secure, slower)

# For RDMA performance: use passthrough
# Kernel cmdline: intel_iommu=on iommu=pt
```

## 4. NUMA Topology

### 4.1 Understanding NUMA
```
  Socket 0              Socket 1
  ┌────────────┐       ┌────────────┐
  │ CPU cores  │       │ CPU cores  │
  │  0-15      │       │  16-31     │
  │            │       │            │
  │ Memory     │       │ Memory     │
  │ Controller │       │ Controller │
  └─────┬──────┘       └─────┬──────┘
        │ PCIe root           │ PCIe root
        │                     │
    ┌───┴───┐             ┌───┴───┐
    │NIC    │             │NIC    │
    │mlx5_0 │             │mlx5_1 │
    └───────┘             └───────┘
```

### 4.2 Finding NUMA Node
```bash
# NIC's NUMA node
cat /sys/class/net/eth0/device/numa_node

# NIC's local CPUs
cat /sys/class/net/eth0/device/local_cpulist

# Full topology
numactl --hardware
lstopo  # graphical/text topology (hwloc)
```

### 4.3 NUMA Impact on RDMA
- **Local access**: Memory and CPU on same NUMA node as NIC → optimal
- **Remote access**: Cross-NUMA adds ~50-100ns latency, 20-40% bandwidth loss
- **Always**: Pin RDMA applications to NIC's NUMA node

## 5. MSI/MSI-X Interrupts

### 5.1 Interrupt Modes
- **Legacy INT#**: Single interrupt, shared, high overhead
- **MSI**: Up to 32 interrupts, message-based
- **MSI-X**: Up to 2048 interrupts, per-queue steering

### 5.2 RDMA and Interrupts
```bash
# Modern NICs use MSI-X: one interrupt per completion queue
# View IRQ assignments
cat /proc/interrupts | grep mlx5

# Set IRQ affinity for RDMA performance
# Pin each IRQ to a local CPU
set_irq_affinity.sh eth0
```

## 6. PCIe Troubleshooting for RDMA

### 6.1 Width/Speed Mismatch
```bash
# If LnkSta shows x8 but LnkCap shows x16:
# → Physical slot may be x8 electrically
# → Card not fully seated
# → Damaged pins

# If Speed is lower than capability:
# → Check BIOS PCIe settings
# → Try different slot
# → Firmware update on NIC or motherboard
```

### 6.2 PCIe Errors
```bash
# Check for PCIe errors
lspci -vvv -s 3b:00.0 | grep -i "error\|correctable\|fatal"

# AER (Advanced Error Reporting)
dmesg | grep -i "aer\|pcie.*error"

# Common PCIe errors affecting RDMA:
# - Correctable errors: May indicate marginal signal quality
# - Uncorrectable non-fatal: Performance impact
# - Uncorrectable fatal: Device stops working
```

### 6.3 Bandwidth Testing
```bash
# Calculate theoretical max:
# Gen4 x16: 16 lanes × 16GT/s × 128/130 = 31.5 GB/s each direction

# Test actual with RDMA:
ib_write_bw -d mlx5_0 -s 1048576 --report_gbits <server>

# If significantly below theoretical:
# 1. Check PCIe width/speed (LnkSta)
# 2. Check MPS/MRRS
# 3. Check NUMA affinity
# 4. Check for PCIe errors
# 5. Check CPU frequency scaling
```

## 7. PCIe ACS (Access Control Services)

### Purpose
ACS controls peer-to-peer PCIe transactions (device-to-device without going through CPU).

### Impact on RDMA
- **GPUDirect RDMA**: Requires ACS disabled between GPU and NIC
- **P2P DMA**: ACS forces traffic through root complex, adding latency

```bash
# Check ACS status
lspci -vvv -s <bridge_bdf> | grep ACSCtl

# Disable ACS
setpci -s <bridge_bdf> ECAP_ACS+6.w=0000

# Or via kernel parameter:
# pcie_acs_override=downstream,multifunction
```
