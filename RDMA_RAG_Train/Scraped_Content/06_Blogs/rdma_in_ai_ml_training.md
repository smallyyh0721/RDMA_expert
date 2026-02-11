---
title: "RDMA's Role in AI/ML Distributed Training"
category: blogs
tags: [rdma, ai, ml, nccl, gpudirect, training, distributed]
---

# RDMA's Role in AI/ML Distributed Training

## 1. Why RDMA Matters for LLM Training

Modern large language models (GPT-4 class, Llama 70B+, etc.) require thousands of GPUs training in parallel. The interconnect between GPUs is often the bottleneck:

- **Model size**: 175B parameters = ~350GB in fp16 → doesn't fit on one GPU
- **Gradient synchronization**: All GPUs must share gradients every iteration
- **Communication volume**: AllReduce of 350GB+ per training step
- **Frequency**: Every few hundred milliseconds

RDMA provides:
- **Low latency** (~1μs vs 10-50μs for TCP): Faster gradient sync
- **High bandwidth** (200-400 Gbps): More data per second
- **Zero CPU involvement**: CPU freed for computation
- **GPUDirect RDMA**: GPU-to-GPU without CPU copies

## 2. Parallelism Strategies and Communication

### 2.1 Data Parallelism
- Each GPU has full model copy, processes different data
- **Communication**: AllReduce of gradients (size = model parameters)
- **RDMA benefit**: High bandwidth AllReduce

### 2.2 Model Parallelism (Tensor Parallel)
- Model layers split across GPUs
- **Communication**: AllReduce/AllGather within each layer
- **RDMA benefit**: Ultra-low latency for tight coupling

### 2.3 Pipeline Parallelism
- Different layers on different GPUs
- **Communication**: Point-to-point activation transfers
- **RDMA benefit**: Low latency for pipeline bubbles

### 2.4 Expert Parallelism (MoE)
- Different experts on different GPUs
- **Communication**: All-to-All for token routing
- **RDMA benefit**: Efficient scatter/gather

## 3. Collective Operations

### 3.1 AllReduce
```
GPU0: [A0]     After AllReduce:  GPU0: [A0+B0+C0+D0]
GPU1: [B0]  ─────────────────>  GPU1: [A0+B0+C0+D0]
GPU2: [C0]                      GPU2: [A0+B0+C0+D0]
GPU3: [D0]                      GPU3: [A0+B0+C0+D0]
```
Used for: Gradient averaging in data parallelism

### 3.2 AllGather
```
GPU0: [A]      After AllGather:  GPU0: [A, B, C, D]
GPU1: [B]  ──────────────────>  GPU1: [A, B, C, D]
GPU2: [C]                       GPU2: [A, B, C, D]
GPU3: [D]                       GPU3: [A, B, C, D]
```
Used for: Collecting full tensors after ReduceScatter

### 3.3 ReduceScatter
```
GPU0: [A0,A1,A2,A3]   After RS:   GPU0: [A0+B0+C0+D0]
GPU1: [B0,B1,B2,B3] ──────────>  GPU1: [A1+B1+C1+D1]
GPU2: [C0,C1,C2,C3]               GPU2: [A2+B2+C2+D2]
GPU3: [D0,D1,D2,D3]               GPU3: [A3+B3+C3+D3]
```
Used for: ZeRO optimizer (DeepSpeed), FSDP (PyTorch)

### 3.4 All-to-All
```
GPU0: [A0,A1,A2,A3]   After A2A:  GPU0: [A0,B0,C0,D0]
GPU1: [B0,B1,B2,B3] ──────────>  GPU1: [A1,B1,C1,D1]
GPU2: [C0,C1,C2,C3]               GPU2: [A2,B2,C2,D2]
GPU3: [D0,D1,D2,D3]               GPU3: [A3,B3,C3,D3]
```
Used for: Mixture of Experts routing, sequence parallelism

## 4. NCCL (NVIDIA Collective Communications Library)

### 4.1 NCCL Architecture with RDMA

```
┌──────────────────────────────────────┐
│           Application (PyTorch)       │
│           torch.distributed           │
├──────────────────────────────────────┤
│              NCCL Library             │
│  ┌──────┐  ┌──────┐  ┌──────────┐  │
│  │NVLink│  │ PCIe │  │RDMA (IB/ │  │
│  │      │  │      │  │  RoCE)   │  │
│  └──────┘  └──────┘  └──────────┘  │
├──────────────────────────────────────┤
│     NVLink     │   GPUDirect RDMA    │
│  (intra-node)  │   (inter-node)      │
└──────────────────────────────────────┘
```

### 4.2 NCCL Transport Selection
- **Intra-node**: NVLink (900 GB/s on NVSwitch systems)
- **Inter-node**: RDMA via IB or RoCE (200-400 Gbps per rail)
- **Fallback**: TCP/IP sockets (when RDMA unavailable)

### 4.3 Key NCCL Algorithms

| Algorithm | When Used | Communication Pattern |
|-----------|----------|----------------------|
| Ring | Small-medium messages | Ring around GPUs |
| Tree | Large messages | Binary tree reduction |
| CollNet (SHARP) | IB with SHARP switches | In-network reduction |

## 5. SHARP (Scalable Hierarchical Aggregation and Reduction Protocol)

### 5.1 Concept
SHARP offloads collective operations (AllReduce) to the InfiniBand switch network:

```
Without SHARP:                    With SHARP:
GPU0 ──data──> GPU1              GPU0 ──data──> Switch
GPU1 ──data──> GPU2              GPU1 ──data──> Switch (reduces in-place)
GPU2 ──data──> GPU3              GPU2 ──data──> Switch
GPU3 ──data──> GPU0              GPU3 ──data──> Switch
(ring: 2(N-1) steps)             Switch ──result──> All GPUs
                                 (tree: 2*logN steps)
```

### 5.2 SHARP Benefits
- Reduces AllReduce traffic by 2x (no forwarding through GPUs)
- Reduces latency (fewer hops)
- Available on Quantum InfiniBand switches
- Supported by NCCL (CollNet transport)

## 6. Network Topologies for AI Clusters

### 6.1 Fat-Tree (Most Common)
```
         ┌───Spine───┐
        ╱ │    │    │ ╲
       ╱  │    │    │  ╲
    Leaf  Leaf Leaf Leaf
    ║║    ║║   ║║   ║║
   GPU   GPU  GPU  GPU
   nodes nodes nodes nodes
```
- Full bisection bandwidth
- Non-blocking
- Used in: NVIDIA DGX SuperPOD

### 6.2 Rail-Optimized
```
Rail 0: GPU0 ─── NIC0 ─── Switch0 ─── NIC0 ─── GPU0 (remote)
Rail 1: GPU1 ─── NIC1 ─── Switch1 ─── NIC1 ─── GPU1 (remote)
Rail 2: GPU2 ─── NIC2 ─── Switch2 ─── NIC2 ─── GPU2 (remote)
...
```
- Each GPU has dedicated NIC and switch rail
- Reduces cross-rail traffic
- Simpler buffer management

### 6.3 Dragonfly
- Groups of switches connected locally (full mesh)
- Groups connected globally (partial mesh)
- Used in: Large HPC systems (> 10K nodes)

## 7. Bandwidth Requirements

### 7.1 Calculation Example

For a 70B parameter model with data parallelism:
```
Parameters: 70B × 2 bytes (fp16) = 140 GB
AllReduce volume: 2 × 140 GB × (N-1)/N ≈ 280 GB (for large N)
Training iteration: ~200ms compute

Required bandwidth to overlap communication:
  280 GB / 200ms = 1.4 TB/s total
  Per GPU (8 GPUs/node): 1.4 / 8 = 175 GB/s = 1.4 Tbps per NIC

→ This is why 8× 200Gbps NICs per node (DGX A100) or
  8× 400Gbps NICs per node (DGX H100) are needed
```

### 7.2 Interconnect Hierarchy

```
DGX H100 Node:
  Intra-GPU:   NVLink 4.0 → 900 GB/s bidirectional
  GPU-NIC:     PCIe Gen5 x16 → 63 GB/s per NIC
  Inter-node:  8× ConnectX-7 400G → 400 GB/s total

DGX A100 Node:
  Intra-GPU:   NVLink 3.0 → 600 GB/s
  GPU-NIC:     PCIe Gen4 x16 → 31.5 GB/s per NIC
  Inter-node:  8× ConnectX-6 200G → 200 GB/s total
```

## 8. Configuration for Training Clusters

### 8.1 Environment Variables Summary
```bash
# NCCL over RDMA
export NCCL_IB_DISABLE=0
export NCCL_IB_HCA=mlx5
export NCCL_NET_GDR_LEVEL=5
export NCCL_NET_GDR_READ=1

# Performance tuning
export NCCL_ALGO=Ring,Tree
export NCCL_PROTO=Simple,LL,LL128
export NCCL_IB_QPS_PER_CONNECTION=4
export NCCL_IB_TC=106
export NCCL_CROSS_NIC=0
export NCCL_SOCKET_IFNAME=eth0

# SHARP (if available)
export NCCL_COLLNET_ENABLE=1
export SHARP_COLL_LOG_LEVEL=3

# Debugging
export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=INIT,NET
```

### 8.2 PyTorch Distributed Training
```python
import torch.distributed as dist

# Initialize with NCCL backend (uses RDMA automatically)
dist.init_process_group(backend='nccl')

# NCCL will auto-detect and use:
# 1. NVLink for intra-node
# 2. RDMA (IB/RoCE) for inter-node
# 3. GPUDirect RDMA for GPU-to-GPU across nodes
```
