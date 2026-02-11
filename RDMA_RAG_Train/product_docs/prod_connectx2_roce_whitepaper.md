# ConnectX-2 EN with RoCE

**Technology Brief - April 2010**
© Copyright 2010. Mellanox Technologies

## Overview

The two commonly known RDMA (remote DMA) technologies are InfiniBand and iWARP (Internet Wide Area RDMA Protocol). InfiniBand has enjoyed significant success to date in HPC applications. iWARP solutions over Ethernet have seen limited success because of implementation and deployment challenges.

Recent enhancements to the Ethernet data link layer under the umbrella of IEEE data center Bridging (DCB) open significant opportunities to proliferate the use of RDMA technology into mainstream data center applications.

## DCB Standards

The proposed DCB standards include:
- **IEEE 802.1Qbb** – Priority-based flow control
- **802.1Qau** – Congestion Notification  
- **802.1Qaz** – Enhanced Transmission Selection (ETS)
- **DCB Capability Exchange**

The lossless delivery features in DCB, enabled by Priority-based Flow Control (PFC), are analogous to those in InfiniBand data link layer.

## RDMA over Converged Ethernet (RoCE)

The IBTA (InfiniBand Trade Association) has recently released a specification called **RDMA over Converged Ethernet (RoCE, pronounced as "Rocky")** that applies InfiniBand-based native RDMA transport services over Ethernet.

ConnectX-2 EN with RoCE (RDMA over Ethernet) implements the RoCE standard to deliver InfiniBand-like ultra low latency and high scalability over Ethernet fabrics.

## How ConnectX-2 RoCE Works

### Transport Layer
ConnectX-2 EN with RoCE uses the InfiniBand transport layer, as defined in the IBTA RoCE specification. The adaptation from InfiniBand data link to Ethernet data link is straightforward because the InfiniBand transport layer was designed ground up to be data link layer agnostic.

The InfiniBand transport layer expects certain services from the data link layer related to lossless delivery of packets, and these are delivered by a PFC enabled Ethernet data link layer.

ConnectX-2 EN with RoCE inherits a rich set of transport services beyond those required to support OFA verbs including connected and unconnected modes, reliable and unreliable services.

### Network Layer
ConnectX-2 EN with RoCE relies on an InfiniBand defined GRH (Global Route Header) based Network Layer. The GRH carries GID (Global Identifier) which is equivalent to IPv6 addressing and can be adapted to IPv4 addressing.

### Data Link Layer
At data link layer level, standard layer 2 Ethernet services are needed:
- **802.1Qbb Priority flow control (PFC)** or **802.3x Pause** at a minimum to ensure lossless packet delivery
- **802.1Qau congestion notification** is desirable but not mandatory
- **802.1Qaz (ETS)** and other Ethernet practices provide a way to implement QoS
- An IEEE assigned Ethertype is used to indicate that packet is of type RoCE

## Converged Traffic

A RoCE packet is identified by an Ethertype number in the L2 header. This allows differentiation among different packet types to occur low in the stack and allows different types of Ethernet traffic, including RDMA traffic, to simultaneously co-exist on a single physical Ethernet wire.

ConnectX-2 EN with RoCE uses linear look up on destination queue pair number (DQPN) in transport header to de-multiplex traffic into queue pairs.

## Management

ConnectX-2 EN with RoCE does not require an SM (InfiniBand subnet manager), and can operate using standard Ethernet network management practices for:
- L2 address assignments
- L2 topology discovery
- Switch filtering database (FDB) configuration

### QoS Management
For RoCE can be accomplished using Ethernet management practices for **802.1Qaz (ETS)**. PFC priority configuration and negotiation with PFC-capable switches can be done:
- **Statically** using VLANs (associating RDMA traffic to VLANs in hosts and assigning high PFC priority to those VLANs in switches)
- **Dynamically** using DCB exchange protocols between NIC and switch

ConnectX-2 EN with RoCE supports both modes of PFC configuration.

### Performance Monitoring
Performance monitoring, baseboard and device management can be done by using standard SNMP/RMON MIBs.

## ConnectX-2 EN with RoCE Advantages

### 1. Efficient Implementation
ConnectX-2 EN with RoCE utilizes advances in Ethernet (DCB) to enable efficient and low cost implementations of RDMA over Ethernet.

### 2. Low CPU Overhead
ConnectX-2 EN RDMA traffic can be classified at the data link layer which is faster and requires less CPU overhead.

### 3. Ultra-Low Latency
ConnectX-2 EN with RoCE delivers **1.3 usec application to application latency**, which is 1/10th of other industry standard implementations over Ethernet.

Benchmarking with popular financial services applications show more than 60% lower latency applicable to capital market data processing and trade executions.

### 4. Full RDMA Features
ConnectX-2 EN with RoCE supports the entire breath of RDMA and low latency features:
- Reliable connected service
- Datagram service  
- RDMA and send/receive semantics
- Atomic operations
- User level multicast
- User level I/O access
- Kernel bypass
- Zero copy

### 5. Proven Software Stack
The OFA verbs used by ConnectX-2 EN with RoCE are based on InfiniBand and have been proven in large scale deployments with multiple ISV applications, both in HPC and EDC sectors.

Such applications can now be seamlessly offered over ConnectX-2 EN with RoCE without any porting effort required.

### 6. Familiar Network Management
ConnectX-2 EN with RoCE based network management is the same as that for any Ethernet and DCB-based network management, eliminating the need for IT managers to learn new technologies.

## Target Applications

Based on discussion above, it is obvious that ConnectX-2 EN with RoCE comes with many advantages and holds promise to enable widespread deployment of RDMA technologies in mainstream data center applications.

Some examples of target applications are:
- Financial services
- Business intelligence  
- Data warehousing
- Cloud computing
- Web 2.0

## Conclusion

ConnectX-2 EN with RoCE adapters based on IBTA RoCE specification are available today from Mellanox Technologies and have been demonstrated to deliver end to end application level latencies of as low as 1.3 microseconds.

Mellanox and other industry leaders are collaborating on growing ecosystem of RoCE-based adapters and independent software vendor applications that capitalize on the benefits of ConnectX-2 EN with RoCE.