---
title: "RFC 5040 - Remote Direct Memory Access Protocol (RDMAP) Specification"
category: specifications
tags:
  - RDMAP
  - RFC 5040
  - iWARP
  - RDMA
  - protocol
  - transport
  - direct-memory-access
source: "IETF RFC 5040 (October 2007), https://www.rfc-editor.org/rfc/rfc5040"
---

# RFC 5040 - Remote Direct Memory Access Protocol (RDMAP) Specification

## 1. Overview

The Remote Direct Memory Access Protocol (RDMAP) provides a mechanism for
Upper Layer Protocols (ULPs) to transfer data with minimal involvement of
the host CPU. RDMAP operates over the Direct Data Placement Protocol (DDP,
RFC 5041) which in turn operates over a reliable transport such as MPA/TCP
(RFC 5044) or SCTP (RFC 4960). Together, these protocols form the iWARP
suite.

RDMAP enables:
- Zero-copy data transfer between application buffers
- Kernel bypass for data placement
- Protocol offload to RDMA-capable NICs (RNICs)
- Reduced latency and CPU overhead for data-intensive operations

### 1.1 Protocol Stack Position

```
+-------------------------------------------+
|         Upper Layer Protocol (ULP)        |
+-------------------------------------------+
|    RDMAP (Remote Direct Memory Access)    |  <-- RFC 5040 (this spec)
+-------------------------------------------+
|   DDP (Direct Data Placement Protocol)    |  <-- RFC 5041
+-------------------------------------------+
|      MPA (Marker PDU Aligned Framing)     |  <-- RFC 5044
+-------------------------------------------+
|              TCP / SCTP                   |
+-------------------------------------------+
|                  IP                       |
+-------------------------------------------+
|             Link Layer                    |
+-------------------------------------------+
```

### 1.2 Key Design Principles

1. **Asynchronous Operation**: RDMAP operations are asynchronous; the
   initiator posts a request and receives a completion notification when
   the operation finishes.

2. **Tagged and Untagged Buffer Models**: Data can be placed into
   explicitly identified (tagged) remote buffers or into anonymous
   (untagged) receive buffers.

3. **Protection Domain Separation**: Memory regions are protected using
   Steering Tags (STags) that combine authorization and addressing.

4. **Ordering Guarantees**: RDMAP provides well-defined ordering semantics
   between different operation types.

## 2. Protocol Architecture

### 2.1 Endpoints and Streams

An RDMAP Stream is a full-duplex communication channel between two RDMAP
endpoints. Each endpoint is associated with:

- **Send Queue (SQ)**: Queue for outbound operations (Send, RDMA Write,
  RDMA Read Request).
- **Receive Queue (RQ)**: Queue for inbound Send operations.
- **Completion Queue (CQ)**: Queue for operation completion notifications.

An RDMAP endpoint maps to a single DDP connection, which in turn maps to a
single MPA/TCP or SCTP association.

### 2.2 Memory Registration

Before any RDMA operation can access local or remote memory, the memory
region must be registered with the RNIC:

1. **Memory Region**: A contiguous or non-contiguous block of virtual
   memory registered for RDMA access.
2. **Steering Tag (STag)**: A 32-bit handle used to identify and authorize
   access to a registered memory region.
3. **Tagged Offset (TO)**: A 64-bit offset within the memory region
   identified by the STag.

The STag contains:
```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    Steering Tag (STag)                        |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    Bits 31-8: STag Index (24 bits) - implementation-defined
    Bits  7-0: STag Key  (8 bits)   - rotation key for validation
```

### 2.3 Protection and Access Control

Each memory registration yields:
- **Local Access Rights**: Read/Write permissions for the local endpoint.
- **Remote Access Rights**: Read/Write permissions for remote endpoints.
- **Protection Domain (PD)**: Logical grouping that restricts which QPs
  can access which memory regions.

Access validation on every RDMA operation checks:
1. STag validity (registered and not invalidated)
2. Access rights (read vs. write permission)
3. Bounds checking (offset + length within region)
4. Protection domain match (PD of QP matches PD of memory region)

## 3. RDMAP Message Types

RDMAP defines six message types, each identified by an opcode in the
RDMAP control field:

| Opcode | Message Type              | DDP Tagged | Direction       |
|--------|---------------------------|------------|-----------------|
| 0000b  | RDMA Write                | Tagged     | Initiator->Tgt  |
| 0001b  | RDMA Read Request         | Tagged     | Initiator->Tgt  |
| 0010b  | RDMA Read Response        | Tagged     | Target->Init    |
| 0011b  | Send                      | Untagged   | Initiator->Tgt  |
| 0100b  | Send with Invalidate      | Untagged   | Initiator->Tgt  |
| 0101b  | Send with Solicited Event | Untagged   | Initiator->Tgt  |
| 0110b  | Send w/ SE and Invalidate | Untagged   | Initiator->Tgt  |
| 0111b  | Terminate                 | Untagged   | Either->Either  |
| 1000b- | Reserved                  | -          | -               |
| 1111b  |                           |            |                 |

### 3.1 RDMAP Header Format

The RDMAP header is carried within the DDP header. It occupies the first
byte of the DDP header's RDMAP Control field.

```
  Byte 0 of DDP Header (RDMAP Control):
  +---+---+---+---+---+---+---+---+
  | RV(2) |  Opcode (4)  | RSV(2) |
  +---+---+---+---+---+---+---+---+
    Bits 7-6: RDMAP Version (RV) = 01 (version 1)
    Bits 5-2: RDMAP Opcode
    Bits 1-0: Reserved (must be zero)
```

#### 3.1.1 RDMAP Version Field

The RDMAP Version (RV) field is 2 bits and MUST be set to 01 (binary) for
RDMAP version 1. Receivers MUST validate this field and generate an error
if a different version is received.

### 3.2 RDMA Write

RDMA Write places data directly into a tagged buffer at the remote peer
without consuming a receive WQE at the target.

**Wire Format (DDP Tagged Message):**
```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |T|L| RDMAP Ctrl| Reserved      |          STag                 |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |               STag (continued)                                |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                                                               |
 +                     Tagged Offset (TO)                        +
 |                          (64 bits)                            |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                                                               |
 +                        Payload Data                           +
 |                                                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

 T = Tagged flag (1 for RDMA Write)
 L = Last flag (1 for last segment of message)
 RDMAP Ctrl: Version=01, Opcode=0000
```

**Semantics:**
- The initiator specifies the remote STag, Tagged Offset, and data length.
- Data is placed directly into the remote buffer without involving the
  remote ULP until completion.
- No receive WQE is consumed at the target.
- The target does NOT generate a completion event for RDMA Write unless
  it is followed by a Send with completion signaling.
- Multiple RDMA Writes may be in flight simultaneously.

**Ordering:**
- RDMA Write data placement completes in order relative to other RDMA
  Writes on the same stream.
- An RDMA Write is guaranteed to be visible to a subsequent Send that
  arrives on the same stream.

### 3.3 RDMA Read Request and Response

RDMA Read allows the initiator to read data from a remote tagged buffer.
This is a two-phase operation:

1. **RDMA Read Request**: Sent from initiator to target, specifying the
   remote buffer to read from and the local buffer to place data into.
2. **RDMA Read Response**: Sent from target to initiator, carrying the
   requested data.

#### 3.3.1 RDMA Read Request Format

```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |T|L| RDMAP Ctrl|  Reserved     |                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               +
 |                    DDP Queue Number                           |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    DDP Message Sequence Number                |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    DDP Message Offset                         |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    Sink STag (local buffer)                   |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                                                               |
 +                  Sink Tagged Offset (64 bits)                 +
 |                                                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    Read Message Size (32 bits)                |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    Source STag (remote buffer)                |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                                                               |
 +                Source Tagged Offset (64 bits)                 +
 |                                                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

 T = 0 (Untagged - Read Request uses DDP untagged model)
 L = 1 (Read Request is a single-segment message)
 RDMAP Ctrl: Version=01, Opcode=0001
```

**Field Descriptions:**
- **Sink STag**: STag of the initiator's local buffer where data will be
  placed (the "sink" of the read data).
- **Sink Tagged Offset**: Starting offset in the initiator's local buffer.
- **Read Message Size**: Number of bytes to read (32-bit, max 2^32 - 1).
- **Source STag**: STag of the target's buffer to read from.
- **Source Tagged Offset**: Starting offset in the target's buffer.

#### 3.3.2 RDMA Read Response Format

The RDMA Read Response is a DDP Tagged Message carrying the data:

```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |T|L| RDMAP Ctrl| Reserved      |          Sink STag            |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |          Sink STag (cont)     |                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               +
 |                   Sink Tagged Offset (64 bits)                |
 +                                                               +
 |                                                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                                                               |
 +                       Payload Data                            +
 |                                                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

 T = 1 (Tagged)
 L = 1 for last segment, 0 otherwise
 RDMAP Ctrl: Version=01, Opcode=0010
```

The Sink STag and Sink Tagged Offset are copied from the Read Request,
allowing the initiator RNIC to place data directly without ULP involvement.

**Ordering:**
- RDMA Read Responses are delivered in the order the corresponding Read
  Requests were issued.
- The initiator may have multiple outstanding Read Requests (up to the
  negotiated IRDMA depth).

### 3.4 Send

Send transfers data from the initiator to the target, consuming a receive
WQE at the target. The target ULP must have pre-posted a receive buffer.

**Wire Format (DDP Untagged Message):**
```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |T|L| RDMAP Ctrl| Reserved      |                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               +
 |                    DDP Queue Number (QN)                      |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    DDP Message Sequence Number (MSN)          |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    DDP Message Offset (MO)                    |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                                                               |
 +                        Payload Data                           +
 |                                                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

 T = 0 (Untagged)
 L = 1 for last segment, 0 otherwise
 RDMAP Ctrl: Version=01, Opcode=0011
 QN = 0 for Send Queue, 1 for Read Request Queue
```

**Semantics:**
- The receiver MUST have a pre-posted receive WQE.
- Data is placed into the next available receive buffer at the target.
- A completion is generated at the target when the entire Send message
  has been received and placed.
- The maximum Send size is limited by the receive buffer size.

### 3.5 Send with Invalidate

Send with Invalidate combines a Send operation with STag invalidation at
the target. This is an optimization for protocols that advertise STags via
Send and want to reclaim them efficiently.

**Wire Format:**
Same as Send, but with RDMAP Opcode = 0100 and an additional Invalidate
STag field:

```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |T|L| RDMAP Ctrl| Reserved      |                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               +
 |                    DDP Queue Number (QN)                      |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    DDP Message Sequence Number (MSN)          |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    DDP Message Offset (MO)                    |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                  Invalidate STag (32 bits)                    |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                                                               |
 +                        Payload Data                           +
 |                                                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

 RDMAP Ctrl: Version=01, Opcode=0100
```

**Semantics:**
- The Invalidate STag field specifies the STag to be invalidated at the
  target upon delivery of this message.
- The invalidation occurs atomically with the Send completion at the target.
- If the STag is invalid or not owned by the remote peer, an error is
  generated.

### 3.6 Send with Solicited Event

Send with Solicited Event (SE) is identical to Send but sets the Solicited
Event flag, which can trigger an interrupt or notification at the receiver
even if the receiver has armed its CQ for solicited events only.

- **Opcode 0101**: Send with Solicited Event
- **Opcode 0110**: Send with Solicited Event and Invalidate

This mechanism allows the receiver to reduce interrupt overhead by only
processing interrupts for messages explicitly marked as solicited.

### 3.7 Terminate Message

The Terminate message is used to signal a fatal error to the remote peer
and initiate connection teardown.

**Wire Format:**
```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |T|L| RDMAP Ctrl| Reserved      |                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               +
 |                    DDP Queue Number (QN = 2)                  |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    DDP Message Sequence Number (MSN)          |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    DDP Message Offset (MO)                    |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 | Layer | EType |                Error Code                     |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                                                               |
 +               Terminated DDP Segment (optional, up to         +
 |                  28 bytes of the offending segment)            |
 +                                                               +
 |                                                               |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

 RDMAP Ctrl: Version=01, Opcode=0111
 QN = 2 (Terminate Queue)
```

#### 3.7.1 Terminate Header Fields

**Layer (4 bits):**
| Value | Layer              |
|-------|--------------------|
| 0x0   | RDMAP              |
| 0x1   | DDP                |
| 0x2   | LLP (Lower Layer)  |

**Error Type (EType, 4 bits) for RDMAP Layer:**
| Value | Error Type            |
|-------|-----------------------|
| 0x0   | Local Catastrophic    |
| 0x1   | Remote Protection     |
| 0x2   | Remote Operation      |

**Error Codes for RDMAP Remote Protection Errors (Layer=0, EType=1):**
| Code   | Description                                        |
|--------|----------------------------------------------------|
| 0x0001 | Invalid STag                                       |
| 0x0002 | Base/Bounds Violation                              |
| 0x0003 | Access Rights Violation                            |
| 0x0004 | STag Not Associated with RDMAP Stream              |
| 0x0005 | TO Wrap                                            |
| 0x0006 | Invalid RDMAP Version                              |
| 0x0009 | STag Cannot Be Invalidated                         |

**Error Codes for RDMAP Remote Operation Errors (Layer=0, EType=2):**
| Code   | Description                                        |
|--------|----------------------------------------------------|
| 0x0005 | Invalid Read Request Opcode                        |
| 0x0006 | Unexpected Opcode                                  |

#### 3.7.2 Terminate Semantics

1. When an endpoint detects a fatal error, it MUST send a Terminate
   message before closing the connection.
2. The Terminate message includes up to 28 bytes of the offending DDP
   segment header to aid in diagnostics.
3. After sending a Terminate, the endpoint enters the Terminate state
   and MUST NOT send any further data messages.
4. After receiving a Terminate, the endpoint MUST abort all outstanding
   operations and close the connection.

## 4. Operation Semantics

### 4.1 Work Request Processing

Operations are submitted to the RNIC via Work Queue Elements (WQEs)
posted to the Send Queue (SQ) or Receive Queue (RQ).

**Send Queue WQE Types:**
1. Send / Send with Invalidate / Send with SE
2. RDMA Write
3. RDMA Read Request
4. Bind Memory Window (local operation)
5. Invalidate STag (local operation)

**Receive Queue WQE Types:**
1. Receive (provides buffer for incoming Send messages)

### 4.2 Ordering Rules

RDMAP defines strict ordering rules between operations:

```
Notation: A -> B means "A completes before B starts at the target"

1. Send -> Send (ordered)
2. RDMA Write -> Send (ordered: write data visible before send completes)
3. RDMA Write -> RDMA Write (ordered on same stream)
4. RDMA Read Response -> Send (ordered)
5. Send -> RDMA Read Request (NOT ordered at target)
6. RDMA Write -> RDMA Read Request (NOT ordered at target)
```

**The Fence Indicator:**
The ULP may set a Fence indicator on a Work Request to ensure all
previously posted RDMA Read operations complete before this Work Request
is issued. This is critical for read-after-read and write-after-read
dependencies.

### 4.3 Completion Semantics

**Initiator Completions:**
| Operation        | Local Completion Meaning                          |
|------------------|---------------------------------------------------|
| Send             | Data has been sent; local buffer may be reused     |
| RDMA Write       | Data has been sent; local buffer may be reused     |
| RDMA Read        | Data has been received into local buffer            |

**Target Completions:**
| Operation        | Target Completion Meaning                          |
|------------------|---------------------------------------------------|
| Send Received    | Data placed in receive buffer; buffer consumed      |
| RDMA Write       | No completion at target (silent data placement)     |
| RDMA Read Req    | No completion at target (handled by RNIC)           |

### 4.4 Zero-Length Operations

RDMAP supports zero-length messages for all operation types:
- **Zero-length Send**: Delivers a completion with no data payload.
  Still consumes a receive WQE at the target.
- **Zero-length RDMA Write**: Acts as a no-op but maintains ordering.
- **Zero-length RDMA Read**: Returns a completion with no data.

## 5. ULP Interface

### 5.1 Connection Establishment

RDMAP relies on the underlying transport for connection establishment.
The ULP interface includes:

```
rdmap_connect(local_addr, remote_addr, private_data) -> stream_handle
rdmap_accept(listen_handle, private_data) -> stream_handle
rdmap_reject(listen_handle, private_data)
rdmap_disconnect(stream_handle)
```

During connection establishment, the following parameters are negotiated:
- **IRDMA (Inbound RDMA Read Depth)**: Maximum number of outstanding
  incoming RDMA Read Requests. Typical values: 1, 4, 16, 32.
- **ORDMA (Outbound RDMA Read Depth)**: Maximum number of outstanding
  outgoing RDMA Read Requests.
- **Private Data**: Opaque data exchanged during connection setup
  (up to 512 bytes for MPA).

### 5.2 Memory Registration Interface

```
register_memory(pd, virtual_addr, length, access_flags) -> (stag, key)
    access_flags: LOCAL_READ | LOCAL_WRITE | REMOTE_READ | REMOTE_WRITE

deregister_memory(stag)

allocate_stag(pd) -> stag
    Creates an STag for later binding

bind_memory_window(stag, base_mr_stag, offset, length, access) -> bound_stag
    Binds a memory window to a subset of a memory region

invalidate_stag(stag)
    Invalidates an STag, making it unusable
```

### 5.3 Data Transfer Interface

```
post_send(stream, sge_list, num_sge, flags) -> wr_id
    flags: SIGNALED | SOLICITED | INVALIDATE(stag)

post_rdma_write(stream, sge_list, remote_stag, remote_offset, flags) -> wr_id
    flags: SIGNALED | FENCE

post_rdma_read(stream, local_sge, remote_stag, remote_offset, length, flags) -> wr_id
    flags: SIGNALED | FENCE

post_receive(stream, sge_list, num_sge) -> wr_id
```

### 5.4 Completion Interface

```
poll_cq(cq_handle) -> completion_entry
    completion_entry: {wr_id, status, opcode, length, src_qp, flags}

arm_cq(cq_handle, solicited_only)
    solicited_only: if true, only notify on solicited completions

wait_for_completion(cq_handle, timeout) -> completion_entry
```

### 5.5 Scatter/Gather Elements (SGE)

Each data transfer operation uses a scatter/gather list:

```
struct sge {
    uint64_t  addr;       // Virtual address of the buffer
    uint32_t  length;     // Length of the buffer segment
    uint32_t  stag;       // STag for memory access validation
};
```

Multiple SGEs can be chained for a single operation, enabling
scatter (receive) and gather (send) of non-contiguous buffers.

## 6. Protocol State Machine

### 6.1 RDMAP Stream States

```
                    +----------+
                    |  IDLE    |
                    +----+-----+
                         |
                    connect/accept
                         |
                    +----v-----+
                    | RUNNING  |<---+
                    +----+-----+    |
                         |          |
              error or   |    normal data
              terminate  |    transfer
                         |          |
                    +----v-----+    |
                    |TERMINATING|---+
                    +----+-----+     (only if error
                         |           is recoverable -
                    connection        not in RDMAP)
                    closed
                         |
                    +----v-----+
                    |  CLOSED  |
                    +----------+
```

**State Descriptions:**

1. **IDLE**: Initial state. No RDMAP operations allowed.
2. **RUNNING**: Normal operating state. All RDMAP operations allowed.
3. **TERMINATING**: Error detected. Terminate message sent or received.
   No new operations; outstanding operations completing with errors.
4. **CLOSED**: Connection fully closed. All resources released.

### 6.2 State Transitions

| Current State | Event                | Action              | Next State   |
|---------------|----------------------|----------------------|-------------|
| IDLE          | Connect success      | Enable operations    | RUNNING     |
| RUNNING       | Normal operation     | Process messages     | RUNNING     |
| RUNNING       | Local error          | Send Terminate       | TERMINATING |
| RUNNING       | Receive Terminate    | Abort operations     | TERMINATING |
| RUNNING       | Graceful disconnect  | Drain operations     | CLOSED      |
| TERMINATING   | All ops completed    | Close connection     | CLOSED      |
| TERMINATING   | Timeout              | Force close          | CLOSED      |

### 6.3 Error Handling State Machine

When an error is detected:

1. **Mark stream as error**: No new WQEs accepted.
2. **Send Terminate**: If the error is reportable to the remote peer.
3. **Flush SQ**: Complete all outstanding SQ WQEs with error status.
4. **Flush RQ**: Complete all outstanding RQ WQEs with error status.
5. **Notify ULP**: Generate an asynchronous error event.
6. **Wait for drain**: Allow ULP to poll all error completions.
7. **Close connection**: Release all stream resources.

## 7. Completion and Error Handling

### 7.1 Completion Queue Entry (CQE) Fields

```
struct cqe {
    uint64_t  wr_id;          // Work Request ID from original post
    uint32_t  status;         // Completion status code
    uint32_t  opcode;         // Operation type that completed
    uint32_t  byte_len;       // Number of bytes transferred
    uint32_t  invalidated_stag; // STag invalidated (for Send w/ Inv)
    uint32_t  flags;          // Completion flags
};
```

### 7.2 Completion Status Codes

| Status Code | Name                          | Description                      |
|-------------|-------------------------------|----------------------------------|
| 0x00        | SUCCESS                       | Operation completed successfully |
| 0x01        | LOC_LEN_ERR                   | Local length error               |
| 0x02        | LOC_QP_OP_ERR                 | Local QP operation error         |
| 0x03        | LOC_PROT_ERR                  | Local protection error           |
| 0x04        | WR_FLUSH_ERR                  | Work request flushed (error)     |
| 0x05        | REM_ACCESS_ERR                | Remote access error              |
| 0x06        | REM_OP_ERR                    | Remote operation error           |
| 0x07        | REM_INV_REQ_ERR               | Remote invalid request error     |
| 0x08        | RETRY_EXC_ERR                 | Transport retry counter exceeded |
| 0x09        | RNR_RETRY_EXC_ERR             | RNR retry counter exceeded       |
| 0x0A        | INV_STAG_ERR                  | Invalid STag on invalidate       |
| 0x0B        | BASE_BOUNDS_ERR               | Base/bounds violation            |
| 0x0C        | ACCESS_ERR                    | Access rights violation          |

### 7.3 Asynchronous Error Events

In addition to completion errors, RDMAP generates asynchronous events:

| Event                | Description                                    |
|----------------------|------------------------------------------------|
| STREAM_ERROR         | Fatal stream error (connection lost)           |
| SRQ_LIMIT_REACHED    | Shared Receive Queue dropped below threshold   |
| CQ_ERROR             | Completion Queue overflow or access error       |
| LOCAL_CATASTROPHIC   | Unrecoverable local hardware error             |
| PORT_ERROR           | Physical port error                            |

### 7.4 Error Propagation

Errors propagate through the following chain:
```
  Hardware Error Detection
         |
         v
  Terminate Message (if remote error)
         |
         v
  Connection moved to ERROR state
         |
         v
  Outstanding WQEs flushed with WR_FLUSH_ERR
         |
         v
  Asynchronous Event to ULP
         |
         v
  ULP polls CQ to drain error completions
         |
         v
  ULP destroys QP and releases resources
```

## 8. RDMA Read Depth Negotiation

### 8.1 IRD and ORD

The RDMA Read operation requires the target to allocate resources for
generating Read Responses. To limit resource consumption:

- **IRD (Inbound Read Depth)**: Maximum number of outstanding inbound
  RDMA Read Requests an endpoint can handle simultaneously. This is
  the responder's resource allocation.

- **ORD (Outbound Read Depth)**: Maximum number of outstanding outbound
  RDMA Read Requests an endpoint will issue simultaneously. This is
  the requester's self-imposed limit.

**Negotiation Rule**: The initiator's ORD must not exceed the target's
IRD. This is negotiated during connection establishment via MPA private
data or ULP-specific mechanisms.

### 8.2 Typical Values

| Deployment          | IRD/ORD | Use Case                         |
|---------------------|---------|----------------------------------|
| Storage (iSER)      | 16-32   | Multiple outstanding I/O reads   |
| NFS-RDMA            | 4-8     | Moderate read parallelism        |
| Custom ULP          | 1       | Simple request/response          |
| High-performance    | 64-128  | Maximum read parallelism         |

## 9. Security Considerations

### 9.1 Memory Protection

RDMAP provides multiple layers of memory protection:

1. **STag Validation**: Every remote access requires a valid STag.
   STags are large (32-bit) and unpredictable when properly generated.

2. **Bounds Checking**: Access must be within the registered region
   boundaries.

3. **Access Rights**: Separate read and write permissions per registration.

4. **Protection Domains**: QP must be in the same PD as the memory region.

5. **STag Lifetime**: STags can be invalidated to revoke access at any time.

### 9.2 Denial of Service Considerations

- Connection-oriented nature limits attack surface.
- Resource exhaustion via RDMA Read (IRD/ORD limits mitigate).
- Memory registration limits prevent unbounded resource consumption.
- STag guessing attacks mitigated by 32-bit STag space and PD matching.

### 9.3 Network Security

RDMAP relies on the underlying transport (TCP/SCTP) for:
- Authentication (IPsec, TLS)
- Encryption (IPsec ESP, TLS)
- Integrity protection

RDMAP itself does not provide encryption or authentication beyond
STag-based access control.

## 10. Implementation Considerations

### 10.1 RNIC Offload

A fully offloaded RDMAP implementation handles the following in hardware:
- DDP segment reassembly
- STag validation and data placement
- Completion generation
- Read Response generation
- Terminate handling

### 10.2 Software Implementation

A software RDMAP implementation must:
- Manage STag tables efficiently (hash tables or radix trees)
- Implement zero-copy data paths where possible
- Handle out-of-order DDP segments (if underlying transport allows)
- Implement proper locking for multi-threaded access

### 10.3 Performance Tuning Parameters

| Parameter                | Typical Range | Impact                        |
|--------------------------|---------------|-------------------------------|
| IRD/ORD                  | 1-128         | Read parallelism              |
| Max Send Size            | 1KB-1MB       | Message throughput            |
| Max Receive Buffers      | 64-4096       | Receive queue depth           |
| SQ Depth                 | 64-4096       | Outstanding operations        |
| CQ Depth                 | 128-16384     | Completion batching           |
| Max SGE per WR           | 1-32          | Scatter/gather capability     |
| Inline Data Threshold    | 0-256 bytes   | Small message optimization    |

## 11. Relationship to Other Protocols

### 11.1 RDMAP vs. InfiniBand RDMA

| Feature              | RDMAP (iWARP)           | InfiniBand RDMA         |
|----------------------|-------------------------|-------------------------|
| Transport            | TCP/SCTP                | InfiniBand reliable     |
| Network              | IP/Ethernet             | InfiniBand fabric       |
| Connection Setup     | TCP 3-way + MPA         | CM REQ/REP/RTU          |
| Flow Control         | TCP congestion control  | Credit-based + ECN      |
| Ordering             | TCP-ordered             | PSN-ordered             |
| Loss Recovery        | TCP retransmission      | Go-back-N or selective  |
| Max Message Size     | 2^32 - 1 bytes          | 2^31 - 1 bytes          |
| Multicast            | Not supported           | Supported (UD)          |

### 11.2 RDMAP vs. RoCE

| Feature              | RDMAP (iWARP)           | RoCE v2                 |
|----------------------|-------------------------|-------------------------|
| Transport            | TCP                     | UDP/IP                  |
| Lossless Requirement | No (TCP retransmits)    | Yes (PFC/ECN)           |
| Congestion Control   | TCP CC                  | DCQCN / TIMELY          |
| CPU Overhead         | Higher (TCP state)      | Lower (simpler headers) |
| Latency              | Higher (TCP processing) | Lower (fewer layers)    |
| Routability          | Full IP routing         | Full IP routing (v2)    |
| Connection Setup     | TCP + MPA handshake     | CM over UD              |

## 12. References

- RFC 5040: A Remote Direct Memory Access Protocol Specification
- RFC 5041: Direct Data Placement over Reliable Transports
- RFC 5044: Marker PDU Aligned Framing for TCP Specification
- RFC 5042: Direct Data Placement Protocol (DDP) / Remote Direct Memory
  Access Protocol (RDMAP) Security
- RFC 5043: Stream Control Transmission Protocol (SCTP) Direct Data
  Placement (DDP) Adaptation
- RFC 6580: IANA Registries for the Remote Direct Data Placement (RDDP)
  Protocols
- RFC 6581: Enhanced Remote Direct Memory Access (RDMA) Connection
  Establishment
