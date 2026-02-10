---
title: "RFC 5041 - Direct Data Placement Protocol (DDP) Specification"
category: specifications
tags:
  - DDP
  - RFC 5041
  - iWARP
  - RDMA
  - data-placement
  - tagged-buffer
  - untagged-buffer
  - protocol
source: "IETF RFC 5041 (October 2007), https://www.rfc-editor.org/rfc/rfc5041"
---

# RFC 5041 - Direct Data Placement Protocol (DDP) Specification

## 1. Overview

The Direct Data Placement Protocol (DDP) enables an Upper Layer Protocol
(ULP) -- typically RDMAP (RFC 5040) -- to place data directly into
upper-layer buffers without intermediate copying. DDP operates over a
reliable transport protocol, such as MPA/TCP (RFC 5044) or SCTP (RFC 4960).

DDP provides two fundamental buffer models:
- **Tagged Buffer Model**: Data is placed at a specified offset in a buffer
  identified by a Steering Tag (STag).
- **Untagged Buffer Model**: Data is placed into the next available buffer
  in a named queue.

### 1.1 Protocol Stack Position

```
+-------------------------------------------+
|         RDMAP / Upper Layer Protocol      |
+-------------------------------------------+
|   DDP (Direct Data Placement Protocol)    |  <-- RFC 5041 (this spec)
+-------------------------------------------+
|              LLP Adaptation               |
|   MPA/TCP (RFC 5044) or SCTP (RFC 4960)  |
+-------------------------------------------+
|              Transport (TCP/SCTP)         |
+-------------------------------------------+
|                    IP                     |
+-------------------------------------------+
```

### 1.2 Key Concepts

- **DDP Segment**: The unit of data transfer in DDP. A single DDP message
  may be split into multiple DDP segments for transmission.
- **DDP Message**: A complete upper-layer data unit. Composed of one or
  more DDP segments.
- **Placement**: The act of writing received data directly into the
  destination buffer without intermediate buffering.

## 2. DDP Segments

### 2.1 Segment Structure

Each DDP segment consists of a DDP header followed by payload data.
The DDP header format depends on whether the segment carries tagged
or untagged data.

### 2.2 Tagged Buffer DDP Header (14 bytes)

Used for RDMA Write and RDMA Read Response operations.

```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |T|L|  Rsvd   | DV|             Reserved                        |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                      Steering Tag (STag)                      |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                                                               |
 +                     Tagged Offset (TO)                        +
 |                          (64 bits)                            |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

 Total header size: 14 bytes (112 bits)
```

**Field Descriptions:**

| Field    | Bits | Offset | Description                                    |
|----------|------|--------|------------------------------------------------|
| T        | 1    | 0      | Tagged flag: 1 = Tagged buffer model           |
| L        | 1    | 1      | Last flag: 1 = Last segment of DDP message     |
| Rsvd     | 4    | 2      | Reserved, must be zero                         |
| DV       | 2    | 6      | DDP Version: 01 = Version 1                    |
| Reserved | 8    | 8      | Reserved, must be zero                         |
| STag     | 32   | 16     | Steering Tag identifying the target buffer     |
| TO       | 64   | 48     | Tagged Offset: byte offset into the buffer     |

**T flag = 1**: Indicates this is a Tagged Buffer segment. The receiver
uses the STag and TO to determine where to place the payload data.

**L flag**: When set to 1, indicates this is the last (or only) segment
of a DDP message. The receiver uses this to determine message boundaries.

**DDP Version (DV)**: Must be 01 (binary) for DDP version 1. Receivers
MUST validate this field.

### 2.3 Untagged Buffer DDP Header (18 bytes)

Used for Send, Send with Invalidate, and Terminate operations.

```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |T|L|  Rsvd   | DV|             Reserved                        |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                     Reserved (32 bits)                        |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    Queue Number (QN)                          |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                  Message Sequence Number (MSN)                |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |                    Message Offset (MO)                        |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

 Total header size: 18 bytes (144 bits)
```

**Field Descriptions:**

| Field    | Bits | Byte Offset | Description                              |
|----------|------|-------------|------------------------------------------|
| T        | 1    | 0.0         | Tagged flag: 0 = Untagged buffer model   |
| L        | 1    | 0.1         | Last flag: 1 = Last segment of message   |
| Rsvd     | 4    | 0.2-0.5     | Reserved, must be zero                   |
| DV       | 2    | 0.6-0.7     | DDP Version: 01 = Version 1             |
| Reserved | 8    | 1           | Reserved byte                            |
| Reserved | 32   | 2-5         | Reserved, must be zero                   |
| QN       | 32   | 6-9         | Queue Number identifying target queue    |
| MSN      | 32   | 10-13       | Message Sequence Number                  |
| MO       | 32   | 14-17       | Message Offset within the message        |

**T flag = 0**: Indicates this is an Untagged Buffer segment.

### 2.4 Queue Numbers (QN)

DDP defines the following Queue Numbers for use with RDMAP:

| QN Value | Queue Purpose                     | Used By                  |
|----------|-----------------------------------|--------------------------|
| 0        | Send Queue (SQ)                   | Send, Send w/ Invalidate |
| 1        | RDMA Read Request Queue           | RDMA Read Request        |
| 2        | Terminate Queue                   | Terminate Message        |
| 3+       | Reserved for future use           | -                        |

### 2.5 Message Sequence Number (MSN)

The MSN is a 32-bit counter that identifies each message within a queue.
It starts at 0 and increments by 1 for each new message posted to a
given queue. The MSN is used by the receiver to:

1. Identify which receive buffer to use for data placement.
2. Detect duplicate or missing messages.

MSN wrapping: The MSN wraps around at 2^32 - 1 back to 0. Implementations
must use modular arithmetic for MSN comparisons.

### 2.6 Message Offset (MO)

The MO field specifies the byte offset within the destination buffer where
the payload data of this segment should be placed. For a multi-segment
message:

- First segment: MO = 0
- Subsequent segments: MO = cumulative offset of previously sent data

This allows out-of-order segment processing when the underlying transport
supports it (e.g., SCTP).

## 3. Tagged Buffer Model

### 3.1 Concept

The Tagged Buffer Model allows the sender to specify exactly where data
should be placed in the receiver's memory. The sender provides:

1. **STag**: Identifies the registered memory region at the receiver.
2. **Tagged Offset (TO)**: Byte offset within the memory region.
3. **Payload Length**: Determined by the segment size.

### 3.2 Data Placement Rules

For Tagged Buffer segments, data placement follows these rules:

1. The receiver validates the STag:
   - STag must be valid and not invalidated.
   - STag must be associated with this DDP connection.
   - Access rights must permit the operation (write access for RDMA Write,
     read access for RDMA Read).
   - The STag must be in the correct Protection Domain.

2. Bounds checking:
   - TO must be within the registered region: `base_addr <= TO`
   - TO + payload_length must not exceed region bounds:
     `TO + payload_length <= base_addr + region_length`

3. Data is placed at virtual address `TO` in the memory region.

4. For multi-segment messages, each segment carries its own TO, allowing
   the receiver to place data without tracking message state (beyond
   verifying the L flag for message completion).

### 3.3 Tagged Offset Calculation

For a DDP message split into N segments:
```
Segment 0: TO = initial_TO
Segment 1: TO = initial_TO + segment_0_payload_length
Segment 2: TO = initial_TO + segment_0_payload_length + segment_1_payload_length
...
Segment i: TO = initial_TO + sum(segment_j_payload_length for j < i)
```

The sender computes the TO for each segment. The receiver can place each
segment independently without buffering or reordering.

### 3.4 Multi-Segment Tagged Message Example

An RDMA Write of 8192 bytes with 2048-byte FPDU size:

```
Segment 0: T=1, L=0, STag=0x1234, TO=0x0000_0000_0000_1000, payload=2048B
Segment 1: T=1, L=0, STag=0x1234, TO=0x0000_0000_0000_1800, payload=2048B
Segment 2: T=1, L=0, STag=0x1234, TO=0x0000_0000_0000_2000, payload=2048B
Segment 3: T=1, L=1, STag=0x1234, TO=0x0000_0000_0000_2800, payload=2048B
```

## 4. Untagged Buffer Model

### 4.1 Concept

The Untagged Buffer Model is used when the receiver pre-posts receive
buffers without the sender knowing the buffer addresses. The receiver
assigns buffers to incoming messages based on the Queue Number and
Message Sequence Number.

### 4.2 Buffer Assignment

The receive side maintains a queue of posted receive buffers for each
Queue Number. When an untagged message arrives:

1. The QN identifies which receive queue to use.
2. The MSN identifies which specific buffer in the queue.
3. The MO specifies the offset within that buffer.

Buffer assignment: `buffer = receive_queue[QN].buffer[MSN % queue_depth]`

### 4.3 Data Placement Rules

For Untagged Buffer segments:

1. The receiver uses QN to select the appropriate receive queue.
2. The MSN identifies the destination buffer.
3. Data is placed at offset MO within the identified buffer.
4. Bounds checking: `MO + payload_length <= buffer_size`
5. When the L flag is set, the message is complete and a completion
   is generated to the ULP.

### 4.4 Buffer Consumption

Untagged buffers are consumed in MSN order:
- Each new Send message increments the MSN.
- The receive buffer associated with that MSN is consumed.
- The ULP must post new receive buffers to replenish the queue.
- If no receive buffer is available when a message arrives, the
  connection is terminated with an error.

### 4.5 Multi-Segment Untagged Message Example

A Send of 6000 bytes with 2048-byte FPDU size:

```
Segment 0: T=0, L=0, QN=0, MSN=47, MO=0,    payload=2048B
Segment 1: T=0, L=0, QN=0, MSN=47, MO=2048,  payload=2048B
Segment 2: T=0, L=1, QN=0, MSN=47, MO=4096,  payload=1904B
```

All three segments target the same buffer (MSN=47), at different offsets.

## 5. Message Framing

### 5.1 DDP over MPA/TCP

When DDP operates over MPA/TCP (RFC 5044), DDP segments are encapsulated
in MPA Framed Protocol Data Units (FPDUs).

**FPDU Structure:**
```
 +-------------------+-------------------+------+-----+-----+
 | MPA Header (2B)   | DDP Header        | ULP  | PAD | CRC |
 | (FPDU Length)      | (14B or 18B)      | Data |     | (4B)|
 +-------------------+-------------------+------+-----+-----+
```

**MPA Header:**
```
  0                   1
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |        FPDU Length (16 bits)  |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

 FPDU Length: Total length of DDP header + ULP data + PAD (excludes
              the MPA header itself and the CRC).
```

**Padding:**
MPA requires FPDUs to be 4-byte aligned. Padding of 0-3 bytes is added
after the payload data. Padding bytes MUST be zero.

**CRC-32c:**
A 4-byte CRC-32c (Castagnoli) covers the entire FPDU including MPA header,
DDP header, ULP data, and padding. This provides end-to-end data integrity.

CRC polynomial: 0x1EDC6F41 (iSCSI polynomial, Castagnoli)

### 5.2 MPA Markers

MPA optionally inserts markers at fixed intervals in the TCP byte stream
to enable the receiver to locate FPDU boundaries without parsing the
entire stream.

**Marker Format:**
```
  0                   1                   2                   3
  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 |          FPDU Pointer (16 bits)           |    Reserved (16)  |
 +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

 FPDU Pointer: Offset from the marker to the start of the FPDU that
               contains (or follows) this marker. This enables the
               receiver to find FPDU boundaries even after TCP
               segment loss and retransmission.
```

Marker interval: Every 512 bytes in the TCP byte stream (configurable
during MPA negotiation). Markers are inserted transparently and removed
by the receiver before DDP processing.

### 5.3 DDP over SCTP

When DDP operates over SCTP (RFC 5043), each DDP segment is carried in
a single SCTP DATA chunk. SCTP provides:
- Message framing (no markers needed)
- Ordered or unordered delivery
- Multi-streaming
- CRC-32c at the SCTP layer

**SCTP Payload Structure:**
```
 +-------------------+-------------------+
 | DDP Header        | ULP Payload Data  |
 | (14B or 18B)      |                   |
 +-------------------+-------------------+
```

No MPA framing, padding, or CRC is needed since SCTP provides these
services natively.

### 5.4 Maximum Segment Size

The maximum DDP segment payload is constrained by:

1. **MPA FPDU size**: Limited by the MULPDU (Maximum ULP Data Unit)
   negotiated during MPA startup. Default: 65535 bytes.
2. **TCP MSS**: The MPA FPDU must fit within TCP segments efficiently.
3. **Path MTU**: For optimal performance, FPDUs should align with the
   path MTU to avoid IP fragmentation.

Typical maximum DDP segment payload sizes:
- 1500-byte Ethernet MTU: ~1432 bytes (after TCP/IP/MPA overhead)
- 9000-byte jumbo frames: ~8932 bytes
- With SCTP: Limited by SCTP DATA chunk size

## 6. Buffer Advertisement

### 6.1 STag Advertisement

Before a remote peer can perform RDMA Write or RDMA Read to a memory
region, the STag and Tagged Offset must be communicated to the remote
peer. This is done via ULP-specific mechanisms, typically through Send
messages.

**Advertisement Flow:**
```
  Endpoint A                        Endpoint B
      |                                  |
      |  Register memory region          |
      |  -> get STag 0x1234             |
      |                                  |
      |  Send(STag=0x1234, TO=0x1000,   |
      |       Length=8192)              |
      |--------------------------------->|
      |                                  |  Store STag info
      |                                  |
      |  RDMA Write(STag=0x1234,        |
      |       TO=0x1000, data)          |
      |<---------------------------------|
      |                                  |
      |  Send with Invalidate            |
      |  (invalidate STag 0x1234)        |
      |--------------------------------->|
      |                                  |
```

### 6.2 Receive Buffer Management

For untagged (Send) operations, the receiver must manage receive buffers:

1. **Pre-posting**: The ULP posts receive WQEs before any Send messages
   arrive. Each WQE provides a buffer (or scatter/gather list) for
   one incoming Send message.

2. **Buffer sizing**: The receive buffer must be large enough for the
   maximum expected Send message. If the incoming message exceeds the
   buffer size, the connection is terminated.

3. **Queue depth**: The receive queue must have enough buffers to avoid
   starvation. If a Send arrives and no receive buffer is available,
   the connection is terminated.

4. **Shared Receive Queue (SRQ)**: Multiple connections can share a pool
   of receive buffers, improving memory efficiency for servers with
   many connections.

## 7. Data Placement Rules

### 7.1 Placement Ordering

DDP guarantees the following placement ordering:

1. **Within a message**: All segments of a message are placed before the
   message completion is signaled. The L flag in the last segment
   triggers the completion.

2. **Between messages on the same queue**: Messages are completed in
   MSN order for untagged buffers.

3. **Between tagged and untagged**: A tagged message (RDMA Write) is
   guaranteed to be placed before a subsequent untagged message (Send)
   on the same connection, if the RDMA Write was sent first.

### 7.2 Atomic Placement

DDP does NOT guarantee atomic placement at the byte level during transfer.
A partially received RDMA Write may have some bytes placed while others
are not yet received. However:

- Message completion (L flag processing) is atomic.
- A completion is generated only after ALL segments of a message have
  been successfully placed.
- If an error occurs during placement, the connection is terminated.

### 7.3 Placement and Memory Ordering

The interaction between DDP data placement and CPU memory ordering is
implementation-dependent. Typical RNICs ensure:

1. DMA writes are visible to the CPU before completion is signaled.
2. Memory barriers or cache invalidation are performed as needed.
3. Completion queue entries are written after all data is placed.

## 8. Error Handling

### 8.1 Error Categories

DDP errors fall into two categories:

**Tagged Buffer Errors:**
| Error Code | Name                          | Description                     |
|------------|-------------------------------|---------------------------------|
| 0x00       | Tagged Buffer Not In Valid St | STag not valid                  |
| 0x01       | Tagged Buffer Base/Bounds     | Access outside registered region|
| 0x02       | STag Not Associated           | STag not bound to this conn     |
| 0x03       | TO Wrap                       | TO + length wraps past 2^64     |
| 0x04       | Invalid DDP Version           | DV field not 01                 |

**Untagged Buffer Errors:**
| Error Code | Name                          | Description                     |
|------------|-------------------------------|---------------------------------|
| 0x01       | No Buffer Available           | No receive buffer for QN/MSN    |
| 0x02       | Invalid MSN Range             | MSN outside valid window        |
| 0x03       | Invalid MO                    | MO + length > buffer size       |
| 0x04       | Invalid QN                    | QN not recognized               |
| 0x05       | Invalid DDP Version           | DV field not 01                 |

### 8.2 Error Reporting

When DDP detects an error:

1. DDP reports the error to RDMAP.
2. RDMAP sends a Terminate message to the remote peer (see RFC 5040
   Section 3.7).
3. The DDP connection is moved to the error state.
4. No further data placement occurs.
5. Outstanding operations are completed with error status.

### 8.3 Error Recovery

DDP does not provide error recovery mechanisms. All errors are fatal
to the connection. The ULP must:

1. Detect the error via completion status or asynchronous event.
2. Clean up resources associated with the failed connection.
3. Optionally establish a new connection and retry operations.

## 9. Connection Semantics

### 9.1 Connection Lifecycle

A DDP connection follows this lifecycle:

```
  +----------+
  |  IDLE    |  No DDP operations allowed
  +----+-----+
       |
  LLP connection established
       |
  +----v-----+
  | CONNECTED|  DDP operations allowed
  +----+-----+
       |
  Error or graceful shutdown
       |
  +----v-----+
  | CLOSING  |  Drain outstanding operations
  +----+-----+
       |
  All operations complete
       |
  +----v-----+
  |  CLOSED  |  Resources released
  +----------+
```

### 9.2 Connection Establishment

DDP connection establishment is handled by the underlying LLP:

**MPA/TCP:**
1. TCP three-way handshake
2. MPA startup handshake (Request/Reply frames)
3. DDP connection active

**SCTP:**
1. SCTP INIT/INIT-ACK/COOKIE-ECHO/COOKIE-ACK
2. DDP adaptation layer negotiation
3. DDP connection active

### 9.3 Graceful Shutdown

DDP graceful shutdown:
1. ULP requests shutdown.
2. Drain all outstanding operations (wait for completions).
3. Close the underlying LLP connection.
4. Release all DDP resources.

### 9.4 Abortive Shutdown

DDP abortive shutdown (on error):
1. Error detected (local or via Terminate message).
2. Immediately stop data placement.
3. Flush all outstanding operations with error status.
4. Close the underlying LLP connection.
5. Release all DDP resources.

## 10. Protocol Constants and Limits

### 10.1 Fixed Values

| Constant             | Value      | Description                        |
|----------------------|------------|------------------------------------|
| DDP Version          | 1 (01b)   | Current DDP protocol version       |
| Tagged Header Size   | 14 bytes   | Size of tagged DDP header          |
| Untagged Header Size | 18 bytes   | Size of untagged DDP header        |
| Send QN              | 0          | Queue Number for Send operations   |
| Read Request QN      | 1          | Queue Number for RDMA Read Req     |
| Terminate QN         | 2          | Queue Number for Terminate         |
| STag Size            | 32 bits    | Size of Steering Tag               |
| TO Size              | 64 bits    | Size of Tagged Offset              |
| MSN Size             | 32 bits    | Size of Message Sequence Number    |
| MO Size              | 32 bits    | Size of Message Offset             |

### 10.2 Implementation Limits

| Parameter                  | Minimum  | Typical    | Maximum       |
|----------------------------|----------|------------|---------------|
| Max DDP Message Size       | 1 byte   | 1 MB       | 2^32 - 1 bytes|
| Max DDP Segment Payload    | 1 byte   | 1-8 KB     | MULPDU        |
| Max Receive Queue Depth    | 1        | 128-4096   | Impl-defined  |
| Max STags per Connection   | 1        | 1000s      | Impl-defined  |
| Max Outstanding Reads      | 1        | 4-32       | Impl-defined  |
| MSN Wrap                   | -        | -          | 2^32 - 1      |

## 11. Security Considerations

### 11.1 Memory Safety

DDP's direct data placement model creates security considerations:

1. **STag Exposure**: STags must be treated as capabilities. Leaking an
   STag to an unauthorized party grants memory access.

2. **Bounds Enforcement**: Implementation MUST enforce bounds checking
   on every segment to prevent buffer overflows.

3. **PD Isolation**: Protection Domains prevent cross-connection memory
   access even if an STag is known.

4. **STag Invalidation**: The ability to invalidate STags provides
   revocation of access rights.

### 11.2 Connection Security

DDP relies on the underlying transport for:
- Authentication of endpoints
- Encryption of data in transit
- Protection against replay attacks
- Connection hijacking prevention

For MPA/TCP, IPsec or TLS can provide these services.
For SCTP, DTLS or IPsec can be used.

### 11.3 Denial of Service

Potential DoS vectors:
- Exhausting receive buffers (mitigated by flow control)
- Excessive RDMA Read Requests (mitigated by IRD limits)
- STag validation overhead (mitigated by efficient data structures)
- Memory registration exhaustion (mitigated by implementation limits)

## 12. Implementation Notes

### 12.1 Hardware Offload

A hardware DDP implementation typically includes:

1. **Segment Parser**: Extracts DDP header fields from incoming segments.
2. **STag Cache**: Caches frequently used STag-to-physical-address
   translations.
3. **DMA Engine**: Performs direct data placement via PCI DMA.
4. **Completion Generator**: Generates CQEs when messages complete.
5. **Error Detector**: Validates all header fields and access rights.

### 12.2 Software Implementation

A software DDP implementation must handle:

1. **Buffer management**: Efficient mapping of QN/MSN to buffer addresses.
2. **Segment reassembly**: Tracking partially received messages.
3. **Copy avoidance**: Using techniques like page remapping or
   scatter/gather I/O to minimize copies.
4. **Locking**: Protecting shared data structures in multi-threaded
   environments.

### 12.3 Performance Considerations

| Factor                    | Impact on Performance                     |
|---------------------------|-------------------------------------------|
| Segment size              | Larger segments reduce header overhead     |
| STag cache hit rate       | Critical for tagged operations             |
| Receive buffer pre-post   | Must keep ahead of incoming messages       |
| CQ polling frequency      | Trade-off: latency vs. CPU utilization     |
| FPDU alignment to MTU     | Reduces IP fragmentation                   |

## 13. References

- RFC 5041: Direct Data Placement over Reliable Transports
- RFC 5040: A Remote Direct Memory Access Protocol Specification
- RFC 5044: Marker PDU Aligned Framing for TCP Specification
- RFC 5043: Stream Control Transmission Protocol (SCTP) Direct Data
  Placement (DDP) Adaptation
- RFC 5042: Direct Data Placement Protocol (DDP) / Remote Direct Memory
  Access Protocol (RDMAP) Security
- RFC 4960: Stream Control Transmission Protocol
