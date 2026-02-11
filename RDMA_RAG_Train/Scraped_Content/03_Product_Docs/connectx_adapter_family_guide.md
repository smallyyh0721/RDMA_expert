---
title: "NVIDIA/Mellanox ConnectX Adapter Family Complete Guide"
category: product_docs
tags:
  - connectx
  - network_adapters
  - NIC
  - HCA
  - InfiniBand
  - Ethernet
  - RDMA
  - mellanox
  - nvidia
  - VPI
  - SmartNIC
  - PCIe
  - offload
version: "2024.1"
---

# NVIDIA/Mellanox ConnectX Adapter Family Complete Guide

## 1. Overview

The ConnectX family of network adapters from NVIDIA (formerly Mellanox Technologies) represents
the industry-leading line of Host Channel Adapters (HCAs) and Network Interface Cards (NICs) for
high-performance computing, cloud, storage, and enterprise networking. Spanning multiple
generations from ConnectX-3 through ConnectX-8, each generation has introduced significant
advances in bandwidth, offload capabilities, and intelligent networking features.

ConnectX adapters support two primary fabric technologies:

- **InfiniBand (IB)**: A lossless, low-latency fabric used extensively in HPC and AI/ML clusters.
- **Ethernet**: The ubiquitous networking standard, enhanced with RDMA over Converged Ethernet
  (RoCE) for high-performance workloads.

Many ConnectX generations offer **VPI (Virtual Protocol Interconnect)** capability, allowing a
single adapter to operate in either InfiniBand or Ethernet mode, selectable per port.

### Key Capabilities Across Generations

All ConnectX adapters share a core set of RDMA and networking capabilities:

- Native RDMA (InfiniBand Verbs) support
- RoCE v1 and/or RoCE v2 support (Ethernet modes)
- SR-IOV (Single Root I/O Virtualization) for hardware-based network virtualization
- Stateless offloads (checksum, LSO/LRO, RSS)
- Hardware timestamping for PTP (Precision Time Protocol)
- PCIe connectivity to host CPUs

Each generation extends these capabilities with additional offloads, higher speeds, and
advanced features.

---

## 2. ConnectX-3 (CX3)

### 2.1 Introduction

ConnectX-3 was the first adapter in the ConnectX family to support FDR InfiniBand (56 Gb/s) and
40 Gigabit Ethernet. Released around 2012, it became the workhorse adapter for many HPC clusters
and early cloud deployments.

### 2.2 Specifications

| Specification          | Details                                      |
|------------------------|----------------------------------------------|
| **Part Number Prefix** | MCX353A, MCX354A, MCX341A, MCX342A           |
| **InfiniBand Speeds**  | SDR (10G), DDR (20G), QDR (40G), FDR (56G)   |
| **Ethernet Speeds**    | 10GbE, 40GbE                                 |
| **Port Configuration** | Single-port and dual-port options             |
| **PCIe Generation**    | PCIe 3.0 x8                                  |
| **VPI Support**        | Yes (different SKUs for IB-only, Eth-only, VPI) |
| **RDMA Support**       | IB Verbs, RoCE v1                            |
| **SR-IOV**             | Up to 126 Virtual Functions per port          |
| **Form Factor**        | Half-height, half-length (HHHL) PCIe card     |
| **Max MTU**            | 9600 bytes (Ethernet), 4096 bytes (IB)        |
| **Connector**          | QSFP (56G IB / 40GbE), SFP+ (10GbE)         |
| **Power Consumption**  | ~12W typical                                 |

### 2.3 Key Features

- **FDR InfiniBand**: 56 Gb/s signaling rate per port, providing 54.5 Gb/s effective data rate
  after encoding overhead (64b/66b).
- **40GbE**: Four lanes of 10G Ethernet aggregated into a single 40GbE link via QSFP connectors.
- **RoCE v1**: Layer 2 RDMA over Converged Ethernet, enabling RDMA on Ethernet without IP routing.
- **Hardware Offloads**: Checksum offload (IPv4/IPv6, TCP/UDP), TCP Segmentation Offload (TSO),
  Large Receive Offload (LRO), Receive Side Scaling (RSS).
- **SR-IOV**: Hardware-based virtualization enabling direct assignment of virtual functions to VMs.
- **MPI Offload**: Hardware support for MPI tag matching.
- **GPUDirect RDMA**: Support for direct data path between GPU memory and the network adapter,
  bypassing host CPU memory (requires NVIDIA GPU with appropriate driver support).

### 2.4 Common Part Numbers

| Part Number    | Configuration                          |
|----------------|----------------------------------------|
| MCX353A-FCAT   | Dual-port FDR IB, VPI, QSFP            |
| MCX354A-FCBT   | Dual-port FDR IB / 40GbE VPI, QSFP     |
| MCX341A-XCAN   | Single-port 10GbE, SFP+                |
| MCX342A-XCQN   | Dual-port 10GbE, SFP+                  |

### 2.5 Firmware and Driver Support

- **MLNX_OFED**: Supported up to MLNX_OFED 4.9-x LTS series. Not supported in MLNX_OFED 5.x+.
- **Inbox Drivers**: Linux kernel mlx4 driver family (mlx4_core, mlx4_en, mlx4_ib).
- **Firmware**: ConnectX-3 firmware version 2.42.5000 and later.

### 2.6 Limitations

- No RoCE v2 support (only RoCE v1, which is non-routable Layer 2).
- No hardware flow steering for advanced packet classification.
- No ASAP2 (Accelerated Switching and Packet Processing) offload.
- PCIe 3.0 x8 provides a theoretical 7.88 GB/s, which is sufficient for FDR but becomes a
  bottleneck for higher speeds.

---

## 3. ConnectX-3 Pro (CX3 Pro)

### 3.1 Introduction

ConnectX-3 Pro was an evolutionary upgrade over ConnectX-3, adding critical RoCE enhancements
and additional offload capabilities. It was designed to bridge the gap between ConnectX-3 and
the upcoming ConnectX-4 generation.

### 3.2 Specifications

| Specification          | Details                                      |
|------------------------|----------------------------------------------|
| **Part Number Prefix** | MCX311A, MCX312A, MCX313A, MCX314A            |
| **InfiniBand Speeds**  | SDR, DDR, QDR, FDR (56G)                     |
| **Ethernet Speeds**    | 10GbE, 40GbE                                 |
| **Port Configuration** | Single-port and dual-port options             |
| **PCIe Generation**    | PCIe 3.0 x8                                  |
| **VPI Support**        | Yes                                          |
| **RDMA Support**       | IB Verbs, RoCE v1, **RoCE v2**               |
| **SR-IOV**             | Up to 126 Virtual Functions per port          |
| **Form Factor**        | HHHL PCIe card                               |
| **Connector**          | QSFP, SFP+                                   |
| **Power Consumption**  | ~14W typical                                 |

### 3.3 Key Enhancements Over ConnectX-3

- **RoCE v2 Support**: The most significant addition. RoCE v2 encapsulates RDMA in UDP/IP packets,
  enabling routing of RDMA traffic across Layer 3 networks. This was critical for data center
  deployments requiring RDMA across subnets.
- **Enhanced RoCE Offloads**: Hardware-based congestion management for RoCE, including ECN
  (Explicit Congestion Notification) generation and processing.
- **Improved Stateless Offloads**: Enhanced VXLAN and NVGRE tunnel offloads for overlay networks.
- **Hardware Timestamping**: Improved PTP (IEEE 1588) hardware timestamping accuracy.
- **Enhanced Virtualization**: Better SR-IOV performance with hardware-level QoS per VF.

### 3.4 Common Part Numbers

| Part Number     | Configuration                         |
|-----------------|---------------------------------------|
| MCX311A-XCAT    | Single-port 10GbE, SFP+               |
| MCX312A-XCBT    | Dual-port 10GbE, SFP+                 |
| MCX313A-BCBT    | Dual-port 40/56GbE VPI, QSFP          |
| MCX314A-BCBT    | Dual-port 40/56G VPI, QSFP            |

### 3.5 Migration Considerations

ConnectX-3 Pro uses the same **mlx4** driver family as ConnectX-3. This means it shares the
same driver stack and management tools, making migration straightforward. However, users should
note that the mlx4 driver has been in maintenance mode since MLNX_OFED 5.0, with active
development focused on the mlx5 driver used by ConnectX-4 and later.

---

## 4. ConnectX-4 (CX4)

### 4.1 Introduction

ConnectX-4 represented a major generational leap, introducing 100 Gigabit Ethernet and EDR
InfiniBand (100 Gb/s). It also introduced the **mlx5** driver architecture that continues to
be used in all subsequent ConnectX generations.

### 4.2 Specifications

| Specification          | Details                                      |
|------------------------|----------------------------------------------|
| **Part Number Prefix** | MCX455A, MCX456A, MCX453A, MCX454A            |
| **InfiniBand Speeds**  | EDR (100G), FDR (56G), QDR, DDR, SDR          |
| **Ethernet Speeds**    | 100GbE, 50GbE, 40GbE, 25GbE, 10GbE, 1GbE    |
| **Port Configuration** | Single-port and dual-port                     |
| **PCIe Generation**    | PCIe 3.0 x16                                 |
| **VPI Support**        | Yes                                          |
| **RDMA Support**       | IB Verbs, RoCE v1, RoCE v2                   |
| **SR-IOV**             | Up to 1024 Virtual Functions                  |
| **Form Factor**        | HHHL PCIe card, OCP 2.0                       |
| **Max MTU**            | 9216 bytes (Ethernet)                         |
| **Connector**          | QSFP28 (100G), QSFP (40/56G)                 |
| **Power Consumption**  | ~16-20W typical                              |

### 4.3 Key Features

- **100 Gigabit Ethernet**: Four lanes of 25G NRZ signaling for 100GbE using QSFP28 connectors.
- **EDR InfiniBand**: 100 Gb/s per port, doubling the bandwidth of FDR.
- **VPI Flexibility**: Each port can independently operate in InfiniBand or Ethernet mode.
- **PCIe 3.0 x16**: Full x16 PCIe 3.0 lane width provides ~15.75 GB/s of host bandwidth,
  sufficient for a single 100G port with headroom.
- **ASAP2 (Accelerated Switching and Packet Processing)**: Hardware offload for Open vSwitch
  (OVS) flow processing, enabling line-rate virtual switching.
- **Enhanced SR-IOV**: Up to 1024 VFs with hardware-based switching between VFs.
- **Hardware Flow Steering**: Programmable hardware flow tables for packet classification.
- **Overlay Network Offloads**: VXLAN, NVGRE, and Geneve encapsulation/decapsulation in hardware.
- **RoCE Enhancements**: Hardware-based ECN, PFC (Priority Flow Control), and congestion
  management for RoCE v2.
- **GPUDirect RDMA**: Continued support with improved performance for GPU-NIC data paths.
- **Message Rate**: Up to 200 million messages per second.

### 4.4 Common Part Numbers

| Part Number    | Configuration                            |
|----------------|------------------------------------------|
| MCX455A-ECAT   | Single-port 100GbE, QSFP28               |
| MCX456A-ECAT   | Dual-port 100GbE, QSFP28                 |
| MCX453A-FCAT   | Single-port EDR IB (100G) VPI, QSFP28    |
| MCX454A-FCAT   | Dual-port EDR IB (100G) VPI, QSFP28      |
| MCX455A-FCAT   | Single-port EDR IB VPI, QSFP28           |

### 4.5 Driver Architecture

ConnectX-4 introduced the **mlx5** driver family:

- **mlx5_core**: Core driver handling firmware communication, resource management, and PCIe.
- **mlx5_ib**: InfiniBand/RoCE verbs driver, exposing IB verbs to user-space applications.
- **mlx5_en**: Ethernet netdev driver for standard networking.

The mlx5 driver architecture supports:
- Devlink interface for device management
- Switchdev mode for hardware-offloaded OVS
- XDP (eXpress Data Path) for programmable packet processing
- TC (Traffic Control) flower offloads

### 4.6 ASAP2 Technology

ASAP2 (Accelerated Switching and Packet Processing) is a key innovation introduced with
ConnectX-4. It offloads Open vSwitch (OVS) datapath processing to the NIC hardware:

1. **E-Switch (Embedded Switch)**: Hardware switch inside the NIC that forwards packets between
   VFs (virtual functions) and the uplink (physical port).
2. **Switchdev Mode**: The Linux kernel switchdev model exposes the hardware E-Switch through
   standard Linux networking tools (tc, bridge, etc.).
3. **TC Flower Offload**: OVS flow rules are translated to TC flower rules and programmed into
   the NIC hardware for line-rate switching.
4. **Benefits**: Near-zero CPU overhead for virtual switching, consistent latency, and full
   line-rate forwarding regardless of the number of flows.

---

## 5. ConnectX-4 Lx (CX4 Lx)

### 5.1 Introduction

ConnectX-4 Lx is an Ethernet-only variant of ConnectX-4, optimized for cloud and enterprise
deployments that do not require InfiniBand support. It offers cost-effective 25GbE and 50GbE
connectivity.

### 5.2 Specifications

| Specification          | Details                                      |
|------------------------|----------------------------------------------|
| **Part Number Prefix** | MCX4111A, MCX4121A, MCX4131A                  |
| **InfiniBand Speeds**  | Not supported                                |
| **Ethernet Speeds**    | 50GbE, 40GbE, 25GbE, 10GbE, 1GbE            |
| **Port Configuration** | Single-port and dual-port                     |
| **PCIe Generation**    | PCIe 3.0 x8                                  |
| **VPI Support**        | No (Ethernet only)                           |
| **RDMA Support**       | RoCE v1, RoCE v2                             |
| **SR-IOV**             | Up to 1024 Virtual Functions                  |
| **Form Factor**        | HHHL PCIe card, OCP 2.0, M.2                 |
| **Connector**          | SFP28 (25G), QSFP28 (50G split to 2x25G)    |
| **Power Consumption**  | ~8-12W typical                               |

### 5.3 Key Features

- **25GbE Native Support**: Single-lane 25G NRZ signaling per SFP28 port.
- **50GbE**: Dual-lane 25G NRZ for 50GbE via QSFP28 or dual SFP28.
- **Lower Power**: Significantly lower power consumption compared to ConnectX-4 full.
- **Cost-Effective**: Targeted at cloud and web-scale deployments requiring high density.
- **Same mlx5 Driver**: Uses the identical mlx5 driver stack as ConnectX-4.
- **All Ethernet Offloads**: VXLAN, Geneve, checksum, TSO, LRO, RSS, hardware timestamping.
- **ASAP2**: Full ASAP2 support for OVS offload.
- **PXE Boot and UEFI**: Network boot support for bare-metal provisioning.
- **OCP 2.0 Form Factor**: Available in OCP (Open Compute Project) mezzanine form factor for
  OCP-compatible servers.

### 5.4 Common Part Numbers

| Part Number      | Configuration                       |
|------------------|-------------------------------------|
| MCX4111A-ACAT    | Single-port 25GbE, SFP28            |
| MCX4111A-XCAT    | Single-port 10GbE, SFP+             |
| MCX4121A-ACAT    | Dual-port 25GbE, SFP28              |
| MCX4121A-XCAT    | Dual-port 10GbE, SFP+               |
| MCX4131A-BCAT    | Single-port 40/50GbE, QSFP28        |

### 5.5 Use Cases

- **Cloud Data Centers**: High-density 25GbE connectivity for compute nodes.
- **Web-Scale Infrastructure**: Cost-effective networking for large-scale web services.
- **Virtualization Hosts**: SR-IOV and ASAP2 for efficient VM networking.
- **Container Hosts**: RDMA device plugin support for Kubernetes with RoCE.

---

## 6. ConnectX-5 (CX5)

### 6.1 Introduction

ConnectX-5 pushed the performance envelope to 100 Gb/s Ethernet and introduced 200 Gb/s
InfiniBand (HDR100). It brought major advances in message rate, GPUDirect capabilities, and
introduced support for NVIDIA SHARP (Scalable Hierarchical Aggregation and Reduction Protocol).

### 6.2 Specifications

| Specification          | Details                                       |
|------------------------|-----------------------------------------------|
| **Part Number Prefix** | MCX555A, MCX556A, MCX515A, MCX516A             |
| **InfiniBand Speeds**  | HDR100 (100G per port), EDR (100G)             |
| **Ethernet Speeds**    | 100GbE, 50GbE, 40GbE, 25GbE, 10GbE           |
| **Port Configuration** | Single-port and dual-port                      |
| **PCIe Generation**    | PCIe 3.0 x16 / PCIe 4.0 x16 (different SKUs)  |
| **VPI Support**        | Yes                                           |
| **RDMA Support**       | IB Verbs, RoCE v1, RoCE v2                    |
| **SR-IOV**             | Up to 1024 Virtual Functions                   |
| **Form Factor**        | HHHL PCIe card, OCP 2.0, OCP 3.0              |
| **Connector**          | QSFP28 (100G), QSFP56 (HDR IB 200G)           |
| **Power Consumption**  | ~18-22W typical                                |
| **Message Rate**       | Up to 200 Mpps                                 |

### 6.3 Key Features

- **200 Gb/s InfiniBand (HDR)**: Using QSFP56 connectors with PAM4 signaling at 50G per lane.
  Note: ConnectX-5 supports HDR100 (single port 100G IB) or dual HDR100 ports. Full HDR 200G
  per port requires ConnectX-6.
- **100GbE**: Continued support for 100 Gigabit Ethernet with QSFP28.
- **PCIe 4.0 Support**: Some SKUs support PCIe Gen 4.0, doubling host bandwidth to ~31.5 GB/s
  with x16 lanes.
- **SHARP (Scalable Hierarchical Aggregation and Reduction Protocol)**: In-network computing
  that offloads MPI collective operations (allreduce, barrier, broadcast) to the network
  infrastructure. SHARP performs data aggregation at each switch level, dramatically reducing
  the data volume traversing the network for collective operations.
- **Enhanced GPUDirect RDMA**: Improved peer-to-peer data movement between NIC and GPU with
  lower latency.
- **GPUDirect Async**: Allows GPU-initiated network operations without CPU involvement.
- **Tag Matching Offload**: Hardware offload for MPI tag matching, reducing host CPU overhead
  for MPI point-to-point operations.
- **Signature Handover**: Hardware-based end-to-end data integrity (T10-DIF / PI) for storage
  applications.
- **NVMEoF Offloads**: Hardware acceleration for NVMe over Fabrics operations.
- **Multi-Host Support**: Ability to share a single adapter across multiple hosts (socket direct).
- **Relaxed Ordering**: PCIe relaxed ordering support for improved throughput with GPUDirect.

### 6.4 ConnectX-5 Ex

ConnectX-5 Ex is an extended version with additional features:

- PCIe 4.0 x16 support (vs PCIe 3.0 in standard CX5)
- Enhanced cryptographic capabilities
- Additional host interfaces

### 6.5 Common Part Numbers

| Part Number    | Configuration                                |
|----------------|----------------------------------------------|
| MCX555A-ECAT   | Single-port 100GbE, QSFP28, PCIe 3.0 x16     |
| MCX556A-ECAT   | Dual-port 100GbE, QSFP28, PCIe 3.0 x16       |
| MCX556A-EDAT   | Dual-port 100GbE, QSFP28, PCIe 4.0 x16       |
| MCX515A-CCAT   | Single-port HDR100 IB, QSFP56                 |
| MCX516A-CDAT   | Dual-port HDR100 IB, QSFP56, PCIe 4.0         |
| MCX515A-GCAT   | Single-port HDR IB, QSFP56 (Socket Direct)    |

### 6.6 SHARP Technology Details

SHARP is one of the most significant innovations introduced with ConnectX-5 and Spectrum-2/
Quantum switches:

1. **In-Network Aggregation**: Instead of sending all data to a root node for reduction,
   SHARP performs partial reductions at each switch hop.
2. **Supported Operations**: SUM, MIN, MAX, AND, OR, XOR on various data types (INT8, INT16,
   INT32, INT64, FP16, BF16, FP32, FP64).
3. **MPI Integration**: Transparent integration with MPI_Allreduce, MPI_Reduce, MPI_Barrier,
   and MPI_Bcast through the SHARP library.
4. **Performance**: Can reduce allreduce latency by 2-8x and bandwidth consumption by up to
   N-fold (where N is the number of nodes) compared to host-based algorithms.
5. **NCCL Integration**: SHARP is integrated with NVIDIA NCCL for deep learning collective
   operations, significantly accelerating distributed training.

---

## 7. ConnectX-5 Ex

### 7.1 Specifications

| Specification          | Details                                      |
|------------------------|----------------------------------------------|
| **Part Number Prefix** | MCX562A                                       |
| **InfiniBand Speeds**  | HDR100 (100G per port)                        |
| **Ethernet Speeds**    | 100GbE, 50GbE, 25GbE                         |
| **PCIe Generation**    | PCIe 4.0 x16                                 |
| **VPI Support**        | Yes                                          |
| **Form Factor**        | HHHL, OCP 3.0                                |
| **Connector**          | QSFP28, QSFP56                               |

### 7.2 Key Differentiators from ConnectX-5

- PCIe Gen 4.0 native support across all SKUs
- Socket Direct technology for multi-host configurations
- Enhanced NVMe-oF target offload capabilities
- Improved tag matching performance

---

## 8. ConnectX-6 (CX6)

### 8.1 Introduction

ConnectX-6 was the first adapter to deliver 200 Gb/s per port, supporting both HDR InfiniBand
and 200GbE. It doubled the per-port bandwidth of ConnectX-5 and introduced enhanced in-network
computing capabilities.

### 8.2 Specifications

| Specification          | Details                                        |
|------------------------|------------------------------------------------|
| **Part Number Prefix** | MCX653105A, MCX653106A, MCX654105A, MCX654106A |
| **InfiniBand Speeds**  | HDR (200G), HDR100 (100G)                       |
| **Ethernet Speeds**    | 200GbE, 100GbE, 50GbE, 40GbE, 25GbE, 10GbE    |
| **Port Configuration** | Single-port 200G or dual-port 200G              |
| **PCIe Generation**    | PCIe 3.0 x16 / PCIe 4.0 x16                    |
| **VPI Support**        | Yes                                            |
| **RDMA Support**       | IB Verbs, RoCE v1, RoCE v2                     |
| **SR-IOV**             | Up to 1024 Virtual Functions                    |
| **Form Factor**        | HHHL PCIe card, OCP 3.0                         |
| **Connector**          | QSFP56 (200G HDR IB / 200GbE)                  |
| **Power Consumption**  | ~22-28W typical                                 |
| **Message Rate**       | Up to 215 Mpps                                  |

### 8.3 Key Features

- **200 Gb/s HDR InfiniBand**: Four lanes of 50G PAM4 signaling for 200 Gb/s per port using
  QSFP56 connectors.
- **200GbE**: Four lanes of 50G PAM4 for 200 Gigabit Ethernet per port.
- **Dual-Port 200G**: Up to 400 Gb/s aggregate bandwidth with dual-port configurations.
- **SHARP v2**: Enhanced in-network computing with improved collective operation support,
  additional data types, and better scalability.
- **Enhanced ASAP2**: Improved OVS offload with more flow table entries and additional match
  and action types.
- **Advanced RoCE**: Hardware-based adaptive routing for RoCE, congestion control enhancements.
- **Socket Direct**: Multi-host adapter support for NUMA-optimized configurations where a
  single adapter card serves multiple CPU sockets.
- **PCIe 4.0**: Native PCIe Gen 4.0 support in appropriate SKUs, providing sufficient host
  bandwidth for dual 200G ports.
- **Improved GPUDirect**: Enhanced GPUDirect RDMA and GPUDirect Storage paths.

### 8.4 Common Part Numbers

| Part Number       | Configuration                             |
|-------------------|-------------------------------------------|
| MCX653105A-ECAT   | Single-port HDR100 IB (100G), QSFP56      |
| MCX653106A-HDAT   | Single-port HDR IB (200G), QSFP56, PCIe 4.0 |
| MCX654105A-HCAT   | Dual-port HDR100 IB (100G), QSFP56        |
| MCX654106A-HCAT   | Dual-port HDR (200G), QSFP56              |
| MCX653105A-EFAT   | Single-port 100GbE VPI, QSFP56            |

---

## 9. ConnectX-6 Dx (CX6 Dx)

### 9.1 Introduction

ConnectX-6 Dx is an Ethernet-focused variant of ConnectX-6 that adds hardware-accelerated
security and data-at-rest protection features. It is the first ConnectX adapter with inline
cryptographic acceleration for IPsec and TLS.

### 9.2 Specifications

| Specification          | Details                                       |
|------------------------|-----------------------------------------------|
| **Part Number Prefix** | MCX623105A, MCX623106A, MCX623102A             |
| **InfiniBand Speeds**  | Not supported (Ethernet only)                  |
| **Ethernet Speeds**    | 100GbE, 50GbE, 25GbE, 10GbE                   |
| **Port Configuration** | Single-port and dual-port 100G/25G             |
| **PCIe Generation**    | PCIe 4.0 x16                                  |
| **VPI Support**        | No (Ethernet only)                            |
| **RDMA Support**       | RoCE v1, RoCE v2                              |
| **SR-IOV**             | Up to 1024 Virtual Functions                   |
| **Form Factor**        | HHHL, OCP 3.0                                 |
| **Connector**          | QSFP56 (100G/port), SFP28 (25G/port)          |
| **Power Consumption**  | ~18-22W typical                                |

### 9.3 Key Security Features

- **Inline IPsec Acceleration**: Hardware offload for IPsec encryption/decryption at line rate.
  Supports AES-GCM-128/256, AES-CBC, and AES-CTR. Offloads ESP (Encapsulating Security Payload)
  processing including encryption, authentication, anti-replay, and SA (Security Association)
  management. Up to thousands of concurrent IPsec tunnels.

- **Inline TLS Acceleration**: Hardware offload for TLS/DTLS record processing. Supports
  TLS 1.2 and TLS 1.3 with AES-GCM-128/256. Offloads symmetric encryption/decryption of
  TLS records while leaving handshake to software. Transparent to applications using standard
  kTLS (kernel TLS) interface.

- **Inline MACsec**: Hardware-based IEEE 802.1AE MACsec encryption for Layer 2 security.

- **Secure Boot and Firmware Signing**: Hardware root of trust with signed firmware updates.

- **Connection Tracking**: Hardware-accelerated connection tracking for stateful firewall
  offload.

### 9.4 Advanced Networking Features

- **Enhanced ASAP2**: Full connection tracking offload enabling stateful NAT and firewall rules
  in hardware.
- **Regex Acceleration**: Hardware regex engine for deep packet inspection (DPI) at line rate.
- **Programmable Pipeline**: Enhanced programmable packet processing pipeline for custom offloads.
- **Advanced Tunneling**: GTP-U (GPRS Tunneling Protocol - User plane) offload for 5G/telecom
  workloads.
- **Flow Metering and Policing**: Hardware-based rate limiting and traffic policing per flow.
- **Hairpin Queues**: Internal loopback queues for packet recirculation without host CPU.

### 9.5 Common Part Numbers

| Part Number       | Configuration                           |
|-------------------|-----------------------------------------|
| MCX623105AN-VDAT  | Single-port 200GbE, QSFP56, crypto     |
| MCX623106AN-CDAT  | Dual-port 100GbE, QSFP56, crypto       |
| MCX621102AN-ADAT  | Dual-port 25GbE, SFP28, crypto         |

---

## 10. ConnectX-6 Lx (CX6 Lx)

### 10.1 Introduction

ConnectX-6 Lx is a cost-optimized, Ethernet-only adapter designed for mainstream cloud and
enterprise deployments. It provides 25GbE and 50GbE connectivity with the full ConnectX-6
feature set at a lower price point.

### 10.2 Specifications

| Specification          | Details                                      |
|------------------------|----------------------------------------------|
| **Part Number Prefix** | MCX631102A, MCX631432A                        |
| **InfiniBand Speeds**  | Not supported                                |
| **Ethernet Speeds**    | 50GbE, 25GbE, 10GbE, 1GbE                   |
| **Port Configuration** | Single-port and dual-port                     |
| **PCIe Generation**    | PCIe 4.0 x8                                  |
| **VPI Support**        | No (Ethernet only)                           |
| **RDMA Support**       | RoCE v2                                      |
| **SR-IOV**             | Up to 512 Virtual Functions                   |
| **Form Factor**        | HHHL, OCP 3.0, M.2                           |
| **Connector**          | SFP28 (25G), SFP56 (50G)                     |
| **Power Consumption**  | ~6-10W typical                               |

### 10.3 Key Features

- **Low Power**: Extremely efficient, as low as 6W for single-port 25G configurations.
- **Compact Form Factors**: Available in HHHL PCIe, OCP 3.0, and M.2 form factors.
- **Full Offload Suite**: Supports VXLAN/Geneve offload, ASAP2, hardware timestamping,
  RoCE v2, and SR-IOV despite the lower price point.
- **Cloud Optimized**: Designed for hyperscale data centers with high-density, low-power
  requirements.
- **Secure Boot**: Hardware root of trust with firmware signature verification.

### 10.4 Common Part Numbers

| Part Number       | Configuration                          |
|-------------------|----------------------------------------|
| MCX631102AN-ADAT  | Dual-port 25GbE, SFP28, PCIe 4.0 x8   |
| MCX631432AN-ADAB  | Quad-port 25GbE (OCP 3.0)              |

---

## 11. ConnectX-7 (CX7)

### 11.1 Introduction

ConnectX-7 delivers 400 Gb/s per port, supporting NDR InfiniBand (400 Gb/s) and 400GbE. It
represents a significant leap in both raw bandwidth and intelligent offload capabilities,
targeting next-generation AI/ML, HPC, and cloud infrastructure.

### 11.2 Specifications

| Specification          | Details                                        |
|------------------------|------------------------------------------------|
| **Part Number Prefix** | MCX750, MCX751, MCX752, MCX755                  |
| **InfiniBand Speeds**  | NDR (400G), HDR (200G)                          |
| **Ethernet Speeds**    | 400GbE, 200GbE, 100GbE, 50GbE, 25GbE           |
| **Port Configuration** | Single 400G or dual 200G or quad 100G            |
| **PCIe Generation**    | PCIe 5.0 x32 (via bifurcation: 2x x16)          |
| **VPI Support**        | Yes (IB and Ethernet SKUs)                       |
| **RDMA Support**       | IB Verbs, RoCE v2                               |
| **SR-IOV**             | Up to 2048 Virtual Functions                     |
| **Form Factor**        | HHHL, OCP 3.0, FHHL (full-height)               |
| **Connector**          | QSFP-DD (400G), OSFP (400G), QSFP56 (200G)      |
| **Power Consumption**  | ~25-35W typical                                  |
| **Message Rate**       | Up to 400+ Mpps                                  |

### 11.3 Key Features

- **NDR InfiniBand (400G)**: Next Data Rate InfiniBand using PAM4 signaling at 100G per lane,
  four lanes for 400 Gb/s per port.
- **400GbE**: Native 400 Gigabit Ethernet using QSFP-DD or OSFP connectors.
- **PCIe 5.0**: First ConnectX adapter with PCIe Gen 5.0 support, providing up to ~63 GB/s
  of host bandwidth with x32 (bifurcated 2x x16) configurations. This is essential to feed
  400G ports without bottlenecking.
- **Enhanced Cryptographic Offloads**: Full inline IPsec, TLS 1.3, and MACsec acceleration
  at 400G line rate.
- **Advanced ASAP2**: Significantly expanded flow table capacity and additional match/action
  types for complex network virtualization scenarios.
- **SHARP v3**: Third generation of in-network computing with expanded data type support
  and improved aggregation performance.
- **GPUDirect RDMA and Storage**: Optimized data paths for both GPU memory access and
  NVMe-oF storage access.
- **Enhanced Connection Tracking**: Millions of concurrent tracked connections in hardware.
- **Programmable Packet Processing**: Extended programmability for custom protocol offloads.
- **Precision Timing**: Sub-nanosecond PTP hardware timestamping accuracy.
- **Telemetry**: Rich per-flow and per-queue telemetry counters in hardware.
- **Multi-Host**: Enhanced Socket Direct support with PCIe 5.0.

### 11.4 NDR InfiniBand Details

NDR (Next Data Rate) InfiniBand specifications:

| Parameter          | Value                                          |
|--------------------|------------------------------------------------|
| Data Rate (per lane) | 100 Gb/s (PAM4 signaling)                     |
| Lanes per Port     | 4 (4x NDR = 400 Gb/s)                          |
| Encoding           | PAM4 with FEC (RS-FEC)                          |
| Cable Connectors   | QSFP-DD, OSFP                                  |
| Reach (copper)     | Up to 2m (DAC)                                  |
| Reach (AOC)        | Up to 30m                                       |
| Reach (SMF)        | Up to 10km                                      |
| Sub-rates          | NDR200 (2x), NDR100 (1x)                        |

### 11.5 Common Part Numbers

| Part Number         | Configuration                             |
|---------------------|-------------------------------------------|
| MCX75510AAS-NEAT    | Single-port NDR400 IB, OSFP, PCIe 5.0     |
| MCX755106AS-HEAT    | Dual-port NDR200 IB, QSFP-DD, PCIe 5.0    |
| MCX750110AS-BNAT    | Single-port 400GbE, QSFP-DD, PCIe 5.0     |
| MCX752106AS-BEAT    | Dual-port 200GbE, QSFP-DD, PCIe 5.0       |

### 11.6 PCIe 5.0 Bandwidth Analysis

| Configuration       | PCIe Bandwidth | Network Bandwidth | Headroom |
|---------------------|----------------|-------------------|----------|
| 1x 400G, x16 Gen 5  | ~63 GB/s       | ~50 GB/s          | 26%      |
| 2x 200G, x32 Gen 5  | ~126 GB/s      | ~50 GB/s          | 152%     |
| 1x 400G, x16 Gen 4  | ~31.5 GB/s     | ~50 GB/s          | -37% (!) |

As shown, PCIe 5.0 is essential for ConnectX-7 to avoid host-side bottlenecks with 400G ports.

---

## 12. ConnectX-8 SuperNIC

### 12.1 Introduction

ConnectX-8 is NVIDIA's latest generation network adapter, branded as a **SuperNIC**. It supports
800 Gb/s of network bandwidth and introduces a new paradigm of network-compute convergence,
positioning the NIC as an active participant in distributed computing rather than just a data
transport device. ConnectX-8 is designed specifically for AI supercomputing infrastructure.

### 12.2 Specifications

| Specification          | Details                                        |
|------------------------|------------------------------------------------|
| **Part Number Prefix** | MCX800 series (various SKUs)                    |
| **InfiniBand Speeds**  | XDR (800G), NDR (400G)                          |
| **Ethernet Speeds**    | 800GbE, 400GbE, 200GbE, 100GbE                  |
| **Port Configuration** | Single 800G, dual 400G                           |
| **PCIe Generation**    | PCIe 6.0 x32                                    |
| **VPI Support**        | Yes                                            |
| **RDMA Support**       | IB Verbs, RoCE v2                               |
| **SR-IOV**             | Up to 4096 Virtual Functions                     |
| **Form Factor**        | FHFL (full-height full-length), OCP 3.0          |
| **Connector**          | OSFP-XD (800G), QSFP-DD (400G)                  |
| **Power Consumption**  | ~40-55W typical                                  |
| **Message Rate**       | 800+ Mpps                                        |

### 12.3 Key Features

- **800 Gb/s Bandwidth**: Eight lanes of 100G PAM4 signaling for 800 Gb/s per port, or
  next-generation 200G-per-lane signaling for XDR InfiniBand.
- **XDR InfiniBand**: Next-generation InfiniBand data rate following NDR.
- **PCIe 6.0**: First adapter supporting PCIe Gen 6.0 with PAM4 signaling, providing ~128 GB/s
  per x16 link (x32 via bifurcation for ~256 GB/s).
- **SuperNIC Capabilities**:
  - **Network-Compute Co-processing**: The adapter can participate in computation, not just
    data transport.
  - **Advanced Congestion Control**: Sophisticated multi-bit ECN and receiver-driven congestion
    management tuned for AI workloads.
  - **Telemetry and Observability**: Deep per-flow telemetry with hardware-based anomaly
    detection.
  - **Isolation and QoS**: Fine-grained traffic isolation for multi-tenant AI clouds.
- **Enhanced GPUDirect**: Purpose-built for NVIDIA Grace-Hopper and Blackwell GPU architectures
  with optimized NVLink-to-network bridging.
- **Full Crypto Suite**: Inline IPsec, TLS, MACsec, and AES-XTS for storage at 800G line rate.
- **SHARP v4**: Next generation in-network computing with broader operation support and
  tighter GPU integration.
- **RoCE Enhancements**: Advanced adaptive routing, spray-based load balancing, and hardware
  congestion control algorithms optimized for AI/ML traffic patterns.
- **NVIDIA Spectrum-X Integration**: Designed to work optimally with Spectrum-X Ethernet
  platforms for AI networking.

### 12.4 SuperNIC vs Traditional NIC

| Feature                 | Traditional NIC     | ConnectX-8 SuperNIC |
|-------------------------|---------------------|---------------------|
| Primary Role            | Data transport       | Network-compute      |
| Congestion Control      | Basic ECN            | Multi-bit, adaptive  |
| Telemetry               | Basic counters       | Per-flow analytics   |
| AI Optimization         | Generic              | Purpose-built        |
| GPU Integration         | GPUDirect RDMA       | Deep NVLink bridge   |
| Isolation               | SR-IOV/VF level      | Fine-grained QoS     |

### 12.5 XDR InfiniBand

XDR (eXtreme Data Rate) is the InfiniBand generation following NDR:

| Parameter          | Value                                          |
|--------------------|------------------------------------------------|
| Data Rate (per lane) | 200 Gb/s (next-gen PAM4)                       |
| Lanes per Port     | 4 (4x XDR = 800 Gb/s) or 8x100G               |
| Target Latency     | Sub-microsecond                                 |
| Cable Connectors   | OSFP-XD, next-gen connectors                    |

---

## 13. Generation Comparison Matrix

### 13.1 Bandwidth and Speed Comparison

| Generation  | Max IB Speed | Max Eth Speed | PCIe Gen | PCIe Width | Max Ports |
|-------------|-------------|---------------|----------|------------|-----------|
| CX-3        | FDR (56G)   | 40GbE         | 3.0      | x8         | 2         |
| CX-3 Pro    | FDR (56G)   | 40GbE         | 3.0      | x8         | 2         |
| CX-4        | EDR (100G)  | 100GbE        | 3.0      | x16        | 2         |
| CX-4 Lx     | N/A         | 50GbE         | 3.0      | x8         | 2         |
| CX-5        | HDR100(100G)| 100GbE        | 3.0/4.0  | x16        | 2         |
| CX-5 Ex     | HDR100(100G)| 100GbE        | 4.0      | x16        | 2         |
| CX-6        | HDR (200G)  | 200GbE        | 3.0/4.0  | x16        | 2         |
| CX-6 Dx     | N/A         | 200GbE        | 4.0      | x16        | 2         |
| CX-6 Lx     | N/A         | 50GbE         | 4.0      | x8         | 2         |
| CX-7        | NDR (400G)  | 400GbE        | 5.0      | x16/x32    | 2         |
| CX-8        | XDR (800G)  | 800GbE        | 6.0      | x32        | 2         |

### 13.2 Feature Comparison

| Feature            | CX3 | CX3P | CX4 | CX4Lx | CX5 | CX6 | CX6Dx | CX6Lx | CX7 | CX8 |
|--------------------|-----|------|-----|-------|-----|-----|-------|-------|-----|-----|
| IB Verbs           |  Y  |  Y   |  Y  |  N    |  Y  |  Y  |  N    |  N    |  Y  |  Y  |
| RoCE v1            |  Y  |  Y   |  Y  |  Y    |  Y  |  Y  |  Y    |  N    |  Y  |  Y  |
| RoCE v2            |  N  |  Y   |  Y  |  Y    |  Y  |  Y  |  Y    |  Y    |  Y  |  Y  |
| SR-IOV             |  Y  |  Y   |  Y  |  Y    |  Y  |  Y  |  Y    |  Y    |  Y  |  Y  |
| ASAP2              |  N  |  N   |  Y  |  Y    |  Y  |  Y  |  Y    |  Y    |  Y  |  Y  |
| SHARP              |  N  |  N   |  N  |  N    |  Y  |  Y  |  N    |  N    |  Y  |  Y  |
| IPsec Offload      |  N  |  N   |  N  |  N    |  N  |  N  |  Y    |  N    |  Y  |  Y  |
| TLS Offload        |  N  |  N   |  N  |  N    |  N  |  N  |  Y    |  N    |  Y  |  Y  |
| Conn Tracking      |  N  |  N   |  N  |  N    |  N  |  N  |  Y    |  N    |  Y  |  Y  |
| GPUDirect RDMA     |  Y  |  Y   |  Y  |  Y    |  Y  |  Y  |  Y    |  Y    |  Y  |  Y  |
| GPUDirect Storage  |  N  |  N   |  N  |  N    |  Y  |  Y  |  Y    |  Y    |  Y  |  Y  |
| Tag Matching       |  N  |  N   |  N  |  N    |  Y  |  Y  |  N    |  N    |  Y  |  Y  |
| PTP Timestamping   |  N  |  Y   |  Y  |  Y    |  Y  |  Y  |  Y    |  Y    |  Y  |  Y  |
| OCP Form Factor    |  N  |  N   |  Y  |  Y    |  Y  |  Y  |  Y    |  Y    |  Y  |  Y  |

### 13.3 Driver Compatibility

| Generation     | Linux Driver | Windows Driver | MLNX_OFED Support     |
|----------------|-------------|----------------|------------------------|
| CX-3 / CX-3 Pro | mlx4       | WinOF          | Up to 4.9-x LTS       |
| CX-4 and later | mlx5        | WinOF-2        | 5.x and later (current)|

---

## 14. Form Factor Reference

### 14.1 PCIe Card Form Factors

| Form Factor | Dimensions           | Typical Use                |
|-------------|----------------------|----------------------------|
| HHHL        | Half-Height Half-Length (6.6 x 16.8 cm) | Standard servers |
| FHHL        | Full-Height Half-Length (12.0 x 16.8 cm) | High-port-count |
| FHFL        | Full-Height Full-Length (12.0 x 31.2 cm) | High-power, multi-port |
| LP          | Low-Profile (6.4 x 16.8 cm) | 1U/2U servers    |

### 14.2 OCP (Open Compute Project) Form Factors

| Standard | Description                               |
|----------|-------------------------------------------|
| OCP 2.0  | Mezzanine card for OCP servers, PCIe 3.0  |
| OCP 3.0  | Small form factor (SFF), PCIe 4.0/5.0     |

### 14.3 Connector Types

| Connector | Speeds Supported                          |
|-----------|-------------------------------------------|
| SFP+      | 10GbE                                     |
| SFP28     | 25GbE, 10GbE                              |
| SFP56     | 50GbE, 25GbE                              |
| QSFP      | 40GbE, FDR IB (56G)                       |
| QSFP28    | 100GbE, EDR IB (100G)                     |
| QSFP56    | 200GbE, HDR IB (200G)                     |
| QSFP-DD   | 400GbE, NDR IB (400G)                     |
| OSFP      | 400GbE, NDR IB (400G), 800GbE             |
| OSFP-XD   | 800GbE, XDR IB (800G)                     |

---

## 15. Firmware and Management

### 15.1 Firmware Management Tools

- **mlxfwmanager**: Command-line tool for querying and updating firmware across all ConnectX
  generations (CX4+).
- **mlxconfig**: Tool for querying and modifying NIC configuration parameters stored in NV
  (non-volatile) memory.
- **mlxdump**: Low-level diagnostic tool for firmware debugging.
- **mstflint**: Open-source firmware burning tool (legacy, but still available).

### 15.2 Common mlxconfig Parameters

```
# Query current configuration
mlxconfig -d /dev/mst/mt4125_pciconf0 query

# Enable SR-IOV
mlxconfig -d /dev/mst/mt4125_pciconf0 set SRIOV_EN=1 NUM_OF_VFS=16

# Set link type (Ethernet or InfiniBand) for VPI adapters
mlxconfig -d /dev/mst/mt4125_pciconf0 set LINK_TYPE_P1=ETH LINK_TYPE_P2=IB

# Enable RoCE
mlxconfig -d /dev/mst/mt4125_pciconf0 set ROCE_CC_PRIO_MASK_P1=255

# Enable PCI relaxed ordering
mlxconfig -d /dev/mst/mt4125_pciconf0 set PCI_WR_ORDERING=1
```

### 15.3 Device Identification

Each ConnectX generation uses a unique PCI Device ID:

| Generation  | PCI Vendor:Device  | mlx5 Internal Name |
|-------------|--------------------|--------------------|
| CX-3        | 15b3:1003          | N/A (mlx4)         |
| CX-3 Pro    | 15b3:1007          | N/A (mlx4)         |
| CX-4        | 15b3:1013          | mt4115             |
| CX-4 Lx     | 15b3:1015          | mt4117             |
| CX-5        | 15b3:1017          | mt4119             |
| CX-5 Ex     | 15b3:1019          | mt4121             |
| CX-6        | 15b3:101b          | mt4123             |
| CX-6 Dx     | 15b3:101d          | mt4125             |
| CX-6 Lx     | 15b3:101f          | mt4127             |
| CX-7        | 15b3:1021          | mt4129             |
| CX-8        | 15b3:1023          | mt4131 (tentative) |

---

## 16. Performance Tuning Guidelines

### 16.1 PCIe Configuration

- Ensure the adapter is installed in a PCIe slot matching its generation and width.
- Verify PCIe link speed and width using `lspci -vvv` or `mlxlink`.
- Enable PCIe relaxed ordering for GPUDirect workloads.
- For NUMA-aware deployments, install the adapter in a slot connected to the same NUMA node
  as the target CPU and GPU.

### 16.2 IRQ Affinity

- Use `mlnx_affinity` or `set_irq_affinity.sh` to bind NIC interrupts to appropriate CPU cores.
- For NUMA-optimal performance, bind interrupts to cores on the same NUMA node as the PCIe slot.
- Avoid sharing interrupt cores with application threads.

### 16.3 Ring Buffer and Queue Configuration

```bash
# Query current ring buffer sizes
ethtool -g <interface>

# Set ring buffer sizes (example: 8192 entries)
ethtool -G <interface> rx 8192 tx 8192

# Query number of combined channels (queues)
ethtool -l <interface>

# Set number of combined channels
ethtool -L <interface> combined 16
```

### 16.4 RoCE Tuning

- Enable PFC (Priority Flow Control) on the specific priority used by RoCE traffic.
- Configure ECN thresholds on the switch for the RoCE priority.
- Set appropriate DSCP/priority mapping.
- Enable adaptive retransmission timeout.

```bash
# Set DSCP mapping for RoCE
cma_roce_tos -d mlx5_0 -t 106

# Verify RoCE mode
cat /sys/class/infiniband/mlx5_0/ports/1/gid_attrs/types/0
```

### 16.5 GPUDirect RDMA Configuration

```bash
# Verify GPUDirect RDMA is working
nvidia-smi topo -m

# Check RDMA-GPU peer relationship
cat /sys/kernel/mm/memory_peers/nv_mem/version

# Set PCIe relaxed ordering (improves GPUDirect throughput)
mlxconfig -d /dev/mst/mt4125_pciconf0 set PCI_WR_ORDERING=1
```

---

## 17. Troubleshooting

### 17.1 Link Issues

```bash
# Check link state
mlxlink -d /dev/mst/mt4125_pciconf0 -p 1

# Query physical port counters
ethtool -S <interface> | grep -E "rx_error|tx_error|rx_discard"

# Check cable diagnostics
mlxlink -d /dev/mst/mt4125_pciconf0 -p 1 --cable --ddm
```

### 17.2 Performance Issues

```bash
# Check PCIe link
lspci -s <bdf> -vvv | grep -E "LnkCap|LnkSta|Width|Speed"

# Check for PCIe errors
lspci -s <bdf> -vvv | grep -E "CESta|UESta"

# Verify NUMA locality
cat /sys/class/net/<interface>/device/numa_node

# Check for firmware errors
dmesg | grep -i mlx5
```

### 17.3 RDMA Issues

```bash
# List RDMA devices
ibv_devices
rdma link show

# Query device capabilities
ibv_devinfo -d mlx5_0

# Test RDMA connectivity
# Server:
ib_write_bw -d mlx5_0
# Client:
ib_write_bw -d mlx5_0 <server_ip>

# Check GID table (for RoCE)
ibv_devinfo -d mlx5_0 -v | grep GID
```

---

## 18. Lifecycle and Support Status

| Generation  | Status         | MLNX_OFED Support | Notes                        |
|-------------|----------------|--------------------|-----------------------------|
| CX-3        | End of Life     | Up to 4.9-x        | mlx4 driver, no new features |
| CX-3 Pro    | End of Life     | Up to 4.9-x        | mlx4 driver, no new features |
| CX-4        | Mature          | 5.x, 23.x, 24.x   | Active bug fixes only        |
| CX-4 Lx     | Mature          | 5.x, 23.x, 24.x   | Active bug fixes only        |
| CX-5        | Active          | 5.x, 23.x, 24.x   | Full support                 |
| CX-5 Ex     | Active          | 5.x, 23.x, 24.x   | Full support                 |
| CX-6        | Active          | 5.x, 23.x, 24.x   | Full support                 |
| CX-6 Dx     | Active          | 5.x, 23.x, 24.x   | Full support, security focus |
| CX-6 Lx     | Active          | 5.x, 23.x, 24.x   | Full support                 |
| CX-7        | Current Gen     | 24.x               | Full support, latest features|
| CX-8        | Next Gen        | Future releases     | Early access / planned       |

---

## 19. Ordering Guide

### 19.1 Part Number Naming Convention

ConnectX part numbers follow a structured naming scheme:

```
MCX [Gen] [Ports] [Speed] [Variant] - [Protocol] [Form] [Crypto] [Rev]
```

Where:
- **Gen**: Generation digit (4=CX4, 5=CX5, 6=CX6, 7=CX7)
- **Ports**: Number of ports
- **Speed**: Speed class code
- **Protocol**: E=Ethernet, F=IB, B=VPI (both)
- **Form**: C=PCIe, D=OCP

### 19.2 Recommended Configurations by Use Case

| Use Case                    | Recommended Adapter        | Reason                      |
|-----------------------------|----------------------------|-----------------------------|
| AI/ML Training Cluster       | CX-7 NDR IB               | Maximum bandwidth, SHARP     |
| Cloud Compute (standard)     | CX-6 Lx 25GbE             | Cost-effective, full offloads|
| Cloud Compute (high perf)    | CX-6 Dx 100GbE            | Crypto offload, conn tracking|
| HPC Cluster                  | CX-7 NDR IB               | Best IB performance          |
| Storage (NVMe-oF)            | CX-6 Dx or CX-7           | Storage offloads, integrity  |
| Telecom/NFV                  | CX-6 Dx                   | GTP-U, crypto, conn tracking |
| Web-Scale / CDN              | CX-6 Lx 25GbE             | Low power, high density      |
| Financial Services           | CX-7 400GbE               | Ultra-low latency, PTP       |

---

## 20. References

- NVIDIA Networking Product Documentation: https://docs.nvidia.com/networking/
- MLNX_OFED Release Notes and User Guides
- ConnectX Adapter Cards Firmware Release Notes
- NVIDIA DOCA SDK Documentation
- InfiniBand Trade Association: https://www.infinibandta.org/
- PCIe Specifications: PCI-SIG (https://pcisig.com/)
