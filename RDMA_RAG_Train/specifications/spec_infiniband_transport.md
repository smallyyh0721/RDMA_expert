---
title: "InfiniBand Architecture Transport Layer Specification"
category: specifications
tags: [infiniband, transport, qp, rc, uc, ud, xrc, specification]
---

# InfiniBand Architecture Transport Layer Specification

## 1. Overview

The InfiniBand Architecture (IBA) defines a switched fabric network providing high-bandwidth, low-latency communication. The transport layer manages end-to-end reliable delivery of messages between Queue Pairs (QPs).

## 2. Transport Types

### 2.1 Reliable Connection (RC)

- **Connection-oriented**: One-to-one QP association
- **Reliable**: Hardware retransmission on packet loss
- **Ordered delivery**: PSN-based sequencing
- **Supports**: Send, RDMA Write, RDMA Read, Atomics
- **Max message size**: 2GB (via multi-packet messages)
- **ACK-based flow control**
- **Use cases**: Most RDMA applications, storage, RPC

Properties:
| Property | Value |
|----------|-------|
| Connection | 1:1 QP pair |
| Reliability | Full (HW retransmission) |
| Ordering | Strict PSN ordering |
| Operations | Send, Write, Read, Atomic |
| Max msg size | 2^31 bytes |
| ACK | Required |
| NAK types | PSN Seq Error, RNR NAK, Remote Op Error |

### 2.2 Unreliable Connection (UC)

- **Connection-oriented**: One-to-one QP
- **Unreliable**: No ACKs, no retransmission
- **Supports**: Send, RDMA Write (no Read, no Atomics)
- **Silently drops**: Out-of-order or duplicate packets
- **Use cases**: Streaming data where loss is acceptable

### 2.3 Unreliable Datagram (UD)

- **Connectionless**: One QP can communicate with many
- **Unreliable**: No ACKs, no retransmission
- **Supports**: Send only (no RDMA operations)
- **Max message size**: MTU (single packet only)
- **Requires Address Handle (AH)** for each destination
- **Use cases**: Service discovery, multicast, CM exchanges

Key characteristics:
- QP number 0 is reserved for Subnet Management Interface (SMI/QP0)
- QP number 1 is reserved for General Services Interface (GSI/QP1)
- Supports multicast group membership
- Each receive WQE gets 40-byte GRH prepended

### 2.4 Extended Reliable Connection (XRC)

- **Connection-oriented with sharing**: Multiple SQs share one RQ
- **Reliable**: Full ACK-based reliability
- **Reduces resource usage**: N processes need N SQs but only 1 SRQ per node-pair
- **Supports**: All RC operations
- **Use cases**: MPI with many processes per node

XRC resource model:
```
Node A (N processes)        Node B (N processes)
  SQ1 ─────────────┐
  SQ2 ──────────────┤──────> XRC SRQ (shared)
  SQ3 ──────────────┤         │
  ...               │         ├──> Process 1
  SQN ──────────────┘         ├──> Process 2
                              └──> Process N

Without XRC: N*N QPs needed between two N-process nodes
With XRC: N SQs + 1 SRQ per direction
```

### 2.5 Dynamically Connected (DC)

- **NVIDIA extension** (not standard IBA)
- **Connectionless with RC semantics**: Reliable but no persistent connection
- **On-demand connection**: DCT (target) accepts from any DCI (initiator)
- **Massive scalability**: One DCI can reach all DCTs
- **Supports**: Send, RDMA Write, RDMA Read, Atomics
- **Use cases**: Large-scale fabrics, key-value stores

## 3. Queue Pair (QP) Architecture

### 3.1 QP Components

```
                    ┌─────────────────┐
                    │   Queue Pair    │
                    │                 │
  Work Requests──> │  ┌───────────┐  │
  (ibv_post_send)  │  │ Send Queue│  │ ──> Packets out
                    │  │   (SQ)    │  │
                    │  └───────────┘  │
                    │                 │
  Work Requests──> │  ┌───────────┐  │
  (ibv_post_recv)  │  │ Recv Queue│  │ <── Packets in
                    │  │   (RQ)    │  │
                    │  └───────────┘  │
                    │                 │
                    │  QP Context:    │
                    │  - State        │
                    │  - Transport    │
                    │  - Peer QPN     │
                    │  - PSN          │
                    │  - MTU          │
                    │  - Retry count  │
                    │  - RNR retry    │
                    │  - Timeout      │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │ Completion Queue │
                    │      (CQ)       │
                    │ ┌─────────────┐ │
                    │ │    CQEs     │ │
                    │ └─────────────┘ │
                    └─────────────────┘
```

### 3.2 QP State Machine

```
    ┌─────────┐   ibv_create_qp()
    │  RESET  │ ◄─────────────────
    └────┬────┘
         │ ibv_modify_qp(INIT)
         │ Set: P_Key, Port, Access flags
         ▼
    ┌─────────┐
    │  INIT   │  Can post receives
    └────┬────┘
         │ ibv_modify_qp(RTR)
         │ Set: Dest QPN, PSN, AH, Path MTU, RQ PSN
         │      Max dest RD atomic, Min RNR timer
         ▼
    ┌─────────┐
    │   RTR   │  Ready to Receive (can receive, not send)
    └────┬────┘
         │ ibv_modify_qp(RTS)
         │ Set: SQ PSN, Timeout, Retry count, RNR retry, Max RD atomic
         ▼
    ┌─────────┐
    │   RTS   │  Ready to Send (full operation)
    └────┬────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│  SQD  │ │  ERR  │  (error or explicit transition)
│(drain)│ │       │
└───┬───┘ └───┬───┘
    │         │
    └────┬────┘
         │ ibv_modify_qp(RESET) or destroy
         ▼
    ┌─────────┐
    │  RESET  │
    └─────────┘
```

**State transition requirements:**

| Transition | Required Attributes |
|-----------|-------------------|
| RESET→INIT | qp_state, pkey_index, port_num, qp_access_flags |
| INIT→RTR | qp_state, path_mtu, dest_qp_num, rq_psn, ah_attr, max_dest_rd_atomic, min_rnr_timer |
| RTR→RTS | qp_state, sq_psn, timeout, retry_cnt, rnr_retry, max_rd_atomic |
| RTS→SQD | qp_state |
| Any→ERR | qp_state |
| Any→RESET | qp_state |

## 4. Work Queue Element (WQE) Format

### 4.1 Send WQE

A Send WQE consists of:

1. **Control Segment** (16 bytes):
   - OpCode, WQE index, DS (descriptor size)
   - Completion flags (signaled, solicited, fence)

2. **Address/Data Segments** (16 bytes each):
   - For Send: scatter-gather list (lkey, addr, length)
   - For RDMA Write: RETH (remote addr, rkey, length) + SGL
   - For RDMA Read: RETH only
   - For Atomic: Atomic ETH (remote addr, rkey, compare, swap/add)

### 4.2 Receive WQE

A Receive WQE consists of:
- **Scatter list**: Buffer addresses where incoming data will be placed
- Each entry: (lkey, local_addr, length)
- Must have enough space for incoming message + GRH (for UD)

## 5. Completion Queue Entry (CQE) Format

A CQE contains:

| Field | Description |
|-------|-------------|
| wr_id | Work request ID (user-set, 64-bit) |
| status | Completion status (success or error code) |
| opcode | Operation type |
| vendor_err | Vendor-specific error code |
| byte_len | Bytes transferred |
| qp_num | QP number |
| src_qp | Source QP (UD only) |
| pkey_index | Partition key index |
| slid | Source LID (IB only) |
| sl | Service Level |
| dlid_path_bits | DLID path bits |
| wc_flags | Flags (GRH present, immediate data, etc.) |
| imm_data | Immediate data (if present) |

### 5.1 Completion Status Codes

| Status | Value | Description |
|--------|-------|-------------|
| IBV_WC_SUCCESS | 0 | Operation completed successfully |
| IBV_WC_LOC_LEN_ERR | 1 | Local length error |
| IBV_WC_LOC_QP_OP_ERR | 2 | Local QP operation error |
| IBV_WC_LOC_EEC_OP_ERR | 3 | Local EEC operation error |
| IBV_WC_LOC_PROT_ERR | 4 | Local protection error |
| IBV_WC_WR_FLUSH_ERR | 5 | WR flushed (QP in error state) |
| IBV_WC_MW_BIND_ERR | 6 | Memory window bind error |
| IBV_WC_BAD_RESP_ERR | 7 | Bad response error |
| IBV_WC_LOC_ACCESS_ERR | 8 | Local access error |
| IBV_WC_REM_INV_REQ_ERR | 9 | Remote invalid request |
| IBV_WC_REM_ACCESS_ERR | 10 | Remote access error |
| IBV_WC_REM_OP_ERR | 11 | Remote operation error |
| IBV_WC_RETRY_EXC_ERR | 12 | Retry count exceeded |
| IBV_WC_RNR_RETRY_EXC_ERR | 13 | RNR retry count exceeded |
| IBV_WC_LOC_RDD_VIOL_ERR | 14 | Local RDD violation |
| IBV_WC_REM_INV_RD_REQ_ERR | 15 | Remote invalid RD request |
| IBV_WC_REM_ABORT_ERR | 16 | Remote aborted |
| IBV_WC_INV_EECN_ERR | 17 | Invalid EECN |
| IBV_WC_INV_EEC_STATE_ERR | 18 | Invalid EEC state |
| IBV_WC_FATAL_ERR | 19 | Fatal error |
| IBV_WC_RESP_TIMEOUT_ERR | 20 | Response timeout |
| IBV_WC_GENERAL_ERR | 21 | General error |

## 6. RDMA Operations

### 6.1 Send/Receive

```
Sender                          Receiver
  │                                │
  │ ibv_post_send(SEND)            │ ibv_post_recv(buffer)
  │ ─────────────────────────────> │
  │          data packet           │
  │ <───────────────────────────── │
  │            ACK                 │
  │                                │
  CQE generated                    CQE generated
  (send completed)                 (receive completed)
```

### 6.2 RDMA Write

```
Writer                          Remote
  │                                │
  │ ibv_post_send(RDMA_WRITE)      │ (no action needed)
  │ ─────────────────────────────> │
  │  data + remote addr/rkey       │
  │ <───────────────────────────── │
  │            ACK                 │
  │                                │
  CQE generated                    NO CQE (silent write)
  (write completed)                (data appears in memory)
```

### 6.3 RDMA Write with Immediate

Same as RDMA Write, but receiver gets a CQE with immediate data.
Consumes a receive WQE on the remote side.

### 6.4 RDMA Read

```
Reader                          Remote
  │                                │
  │ ibv_post_send(RDMA_READ)       │ (no action needed)
  │ ─────────────────────────────> │
  │     read request (RETH)        │
  │ <───────────────────────────── │
  │     read response (data)       │
  │                                │
  CQE generated                    NO CQE
  (data in local buffer)
```

### 6.5 Atomic Operations

**Compare and Swap:**
```
CAS(remote_addr, compare_val, swap_val):
  if (*remote_addr == compare_val)
      *remote_addr = swap_val
  return original_value
```

**Fetch and Add:**
```
FAA(remote_addr, add_val):
  old = *remote_addr
  *remote_addr += add_val
  return old
```

Both are 64-bit operations, guaranteed atomic by the HCA.

## 7. Flow Control

### 7.1 Credit-Based Flow Control (IB)

InfiniBand uses credit-based flow control at the link layer:

- **Virtual Lanes (VLs)**: Up to 16 virtual lanes per link (VL0-VL15)
- **VL15**: Management traffic (always available)
- **Credit units**: Based on buffer allocation
- **Each VL has separate credits**

Flow:
1. Receiver advertises buffer credits per VL
2. Sender decrements credits on each packet sent
3. When credits reach 0, sender stops
4. Receiver sends credit updates as buffers are freed

### 7.2 Service Level to VL Mapping

```
SL (Service Level) ──> SL-to-VL mapping table ──> VL (Virtual Lane)

Configured by Subnet Manager via SLtoVLMapping MAD
```

### 7.3 RNR NAK (Receiver Not Ready)

When a Send arrives but no Receive WQE is posted:
1. Receiver sends RNR NAK with timer value
2. Sender waits for the specified time
3. Sender retransmits
4. After `rnr_retry` exhausted → IBV_WC_RNR_RETRY_EXC_ERR

RNR timer values: 655ms, 10ms, 20ms, 30ms, ... (encoded in 5 bits)

## 8. Partition Keys (P_Keys)

- Every QP is assigned a P_Key (16-bit)
- Communication only allowed between matching P_Keys
- Bit 15 = membership type (Full=1, Limited=0)
- Full members can communicate with any member
- Limited members can only communicate with Full members
- Default P_Key: 0xFFFF

## 9. Memory Regions and Protection

### 9.1 Protection Domain (PD)

- Groups QPs, MRs, and MWs
- Cross-PD access is not allowed
- Created with `ibv_alloc_pd()`

### 9.2 Memory Region (MR)

- Maps virtual memory to HCA-accessible memory
- Returns `lkey` (local key) and `rkey` (remote key)
- Access flags: `IBV_ACCESS_LOCAL_WRITE`, `IBV_ACCESS_REMOTE_WRITE`, `IBV_ACCESS_REMOTE_READ`, `IBV_ACCESS_REMOTE_ATOMIC`

### 9.3 Keys (lkey/rkey)

- **lkey**: Used locally in scatter-gather entries
- **rkey**: Shared with remote side for RDMA Read/Write
- Key contains: index (24 bits) + key (8 bits)
- The 8-bit key portion changes with each re-registration (for security)

## 10. InfiniBand Link Layer

### 10.1 Link Speeds

| Rate | Signal Rate | Effective per Lane | x4 Width | x12 Width |
|------|-------------|-------------------|----------|-----------|
| SDR | 2.5 Gbps | 2.0 Gbps | 8 Gbps | 24 Gbps |
| DDR | 5.0 Gbps | 4.0 Gbps | 16 Gbps | 48 Gbps |
| QDR | 10 Gbps | 8.0 Gbps | 32 Gbps | 96 Gbps |
| FDR-10 | 10.3125 Gbps | 10 Gbps | 40 Gbps | 120 Gbps |
| FDR | 14.0625 Gbps | 13.64 Gbps | 54.5 Gbps | 163.6 Gbps |
| EDR | 25.78125 Gbps | 25 Gbps | 100 Gbps | 300 Gbps |
| HDR | 50 Gbps (PAM4) | 50 Gbps | 200 Gbps | 600 Gbps |
| NDR | 100 Gbps (PAM4) | 100 Gbps | 400 Gbps | 1.2 Tbps |
| XDR | 200 Gbps | 200 Gbps | 800 Gbps | 2.4 Tbps |

### 10.2 Subnet Components

| Component | Description |
|-----------|-------------|
| HCA | Host Channel Adapter (NIC equivalent) |
| TCA | Target Channel Adapter |
| Switch | InfiniBand switch |
| Router | Connects IB subnets |
| SM | Subnet Manager (topology discovery, LID assignment, routing) |
| SA | Subnet Administrator (path queries, service records) |
| PM | Performance Manager (counter monitoring) |
| BM | Baseboard Manager (node management) |

### 10.3 Addressing

- **LID** (Local ID): 16-bit, assigned by SM, local to subnet
- **GID** (Global ID): 128-bit, globally unique, IPv6 format
- **GUID** (Global Unique ID): 64-bit, factory-assigned
  - Node GUID: per HCA
  - Port GUID: per port
- **QPN** (Queue Pair Number): 24-bit, identifies QP on a port

Path specification: (SLID, DLID, SL) for intra-subnet, (SGID, DGID) for inter-subnet
