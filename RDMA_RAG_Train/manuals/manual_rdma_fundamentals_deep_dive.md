---
title: "RDMA Fundamentals Deep Dive: From Zero to Verbs"
category: blogs
tags:
  - RDMA
  - InfiniBand
  - RoCE
  - iWARP
  - verbs
  - kernel bypass
  - zero-copy
  - high-performance networking
  - libibverbs
  - queue pair
  - completion queue
  - memory region
---

# RDMA Fundamentals Deep Dive: From Zero to Verbs

## Introduction: Why Does RDMA Exist?

If you have ever profiled a high-performance application and found that the CPU spends
more time copying data between buffers and processing interrupts than doing actual
computation, you have experienced the fundamental problem that RDMA was designed to
solve.

Remote Direct Memory Access (RDMA) is a technology that allows one computer to directly
read from or write to the memory of another computer without involving either computer's
operating system in the data path. That single sentence contains three revolutionary
ideas that took decades to refine:

1. **Kernel Bypass** -- The application talks directly to the network hardware, skipping
   the entire kernel networking stack (socket layer, TCP/IP, driver queues).
2. **Zero-Copy** -- Data moves directly between application memory and the network
   adapter. There is no intermediate copy into kernel buffers.
3. **CPU Offload** -- The network adapter (called an HCA in InfiniBand or a RNIC in
   iWARP/RoCE) handles segmentation, reassembly, reliability, and ordering in hardware.
   The CPU is free to do other work.

These three properties combine to deliver latencies under 1 microsecond, bandwidths
exceeding 400 Gb/s per port, and near-zero CPU utilization for data movement. RDMA is
the backbone of modern HPC clusters, AI/ML training infrastructure, and high-frequency
trading networks.

This article is a tutorial-style deep dive into every fundamental concept you need to
understand RDMA programming. We will start from traditional networking, explain why it
is slow, and then systematically build up the RDMA programming model.

---

## Part 1: How Traditional Networking Works (And Why It Is Slow)

### The Classic Send/Receive Path

Consider a simple TCP send from Application A to Application B:

```
  Application A                              Application B
  +-----------+                              +-----------+
  | send()    |                              | recv()    |
  +-----+-----+                              +-----+-----+
        |                                          ^
        v                                          |
  +-----+-----+                              +-----+-----+
  | Socket     |   <-- copy from user        | Socket     |  <-- copy to user
  | Layer      |       buffer to kernel      | Layer      |      buffer from kernel
  +-----+-----+                              +-----+-----+
        |                                          ^
        v                                          |
  +-----+-----+                              +-----+-----+
  | TCP        |   <-- segmentation,         | TCP        |  <-- reassembly,
  | Layer      |       checksums,            | Layer      |      ACK generation,
  +-----+-----+       retransmit timers      +-----+-----+      reordering
        |                                          ^
        v                                          |
  +-----+-----+                              +-----+-----+
  | IP Layer   |   <-- routing lookup        | IP Layer   |
  +-----+-----+                              +-----+-----+
        |                                          ^
        v                                          |
  +-----+-----+                              +-----+-----+
  | Driver     |   <-- DMA to NIC            | Driver     |  <-- interrupt,
  | + NIC      |       ring buffer           | + NIC      |      DMA from NIC
  +-----------+                              +-----------+
```

Count the problems:

1. **Two memory copies per side.** On the sender, data is copied from the application
   buffer into a kernel socket buffer. On the receiver, data is copied from the kernel
   buffer back to the application buffer. That is four copies for one message.

2. **Context switches.** Each `send()` and `recv()` is a system call that requires a
   transition from user mode to kernel mode and back. Each costs roughly 1-5
   microseconds on modern hardware.

3. **Interrupt overhead.** Each incoming packet (or batch of packets) triggers a hardware
   interrupt, which interrupts whatever the CPU was doing, saves state, runs the ISR,
   schedules softirq processing, and eventually wakes up the receiving application.

4. **Protocol processing.** TCP checksum calculation, sequence number management,
   congestion window updates, retransmission timer management -- all done in software
   on the CPU.

5. **Memory bandwidth waste.** The data touches main memory multiple times: application
   buffer -> socket buffer -> DMA buffer -> wire -> DMA buffer -> socket buffer ->
   application buffer. On a modern server with DDR5 running at 4800 MT/s, memory
   bandwidth is precious, and wasting it on copies means less bandwidth for actual
   computation.

For a 100 Gb/s link, saturating the line with TCP requires multiple CPU cores dedicated
solely to networking. For a 400 Gb/s link, it becomes impractical.

### What If We Could Skip All of That?

RDMA eliminates every single one of those problems:

| Problem               | TCP/IP                        | RDMA                            |
|------------------------|-------------------------------|----------------------------------|
| Memory copies          | 2-4 per message               | 0 (true zero-copy)              |
| Context switches       | 1-2 per send/recv             | 0 (userspace doorbell)          |
| Interrupts             | Per-packet or batched          | Optional (polling mode)         |
| Protocol processing    | CPU (TCP stack)               | NIC hardware                    |
| Latency                | 10-50+ microseconds           | 0.5-2 microseconds             |
| CPU utilization        | Multiple cores at line rate    | Near zero at line rate          |

---

## Part 2: The RDMA Programming Model -- Verbs

### What Are Verbs?

The RDMA programming interface is called "verbs." This name comes from the original
InfiniBand specification, which described operations in terms of verb-object pairs
(e.g., "post a send work request"). The open-source implementation is called
**libibverbs**, and it is part of the rdma-core package on Linux.

Verbs are NOT sockets. You do not call `send()` or `recv()`. Instead, you:

1. Allocate and configure hardware resources (protection domains, memory regions,
   queue pairs, completion queues).
2. Post work requests to queues.
3. Poll for completions.

The programming model is asynchronous and queue-based. You submit work and check for
results later. This is fundamentally different from the synchronous socket API.

### The Verbs API Layers

```
+-------------------------------------------------------+
|              Application Code                          |
+-------------------------------------------------------+
|              libibverbs  (userspace library)            |
+-------------------------------------------------------+
|              Provider library (libmlx5, librxe, etc.)  |
+-------------------------------------------------------+
|              Kernel driver (via /dev/infiniband/uverbsN)|
|              (only for slow-path operations)           |
+-------------------------------------------------------+
|              Hardware (HCA / RNIC)                      |
+-------------------------------------------------------+
```

The critical insight: **slow-path** operations (creating QPs, registering memory, etc.)
go through the kernel. **Fast-path** operations (posting work requests, polling
completions) go directly from userspace to hardware via memory-mapped doorbell
registers. No system calls on the data path.

---

## Part 3: Key RDMA Abstractions

### The Big Picture

Before diving into each abstraction, here is how they fit together:

```
+------------------------------------------------------------------+
|  Application                                                      |
|                                                                    |
|  ibv_context (device handle)                                       |
|  +--------------------------------------------------------------+ |
|  | Protection Domain (PD)                                        | |
|  | +------------------+  +------------------+                    | |
|  | | Memory Region 1  |  | Memory Region 2  |  ...              | |
|  | | (MR)             |  | (MR)             |                    | |
|  | +------------------+  +------------------+                    | |
|  |                                                                | |
|  | +---------------------------+                                  | |
|  | | Queue Pair (QP)           |     +--------------------+      | |
|  | | +----------+ +----------+ |     | Completion Queue    |      | |
|  | | | Send Q   | | Recv Q   | |---->| (CQ)               |      | |
|  | | | (SQ)     | | (RQ)     | |     | +----------------+ |      | |
|  | | +----------+ +----------+ |     | | Work Completion | |      | |
|  | +---------------------------+     | | (WC) entries    | |      | |
|  |                                    | +----------------+ |      | |
|  | +---------------------------+     +--------------------+      | |
|  | | Shared Receive Queue (SRQ)|                                  | |
|  | +---------------------------+                                  | |
|  +--------------------------------------------------------------+ |
+------------------------------------------------------------------+
```

Let us walk through each abstraction in detail.

### 3.1 Device Context (ibv_context)

The device context represents an open handle to an RDMA device. You get one by calling
`ibv_open_device()`. It is analogous to a file descriptor for a network device.

```c
struct ibv_device **dev_list = ibv_get_device_list(&num_devices);
struct ibv_context *ctx = ibv_open_device(dev_list[0]);
```

The context is the root object from which everything else is created.

### 3.2 Protection Domain (PD)

A Protection Domain is a security and isolation boundary. All resources that will
interact must belong to the same PD. Think of it as a namespace: a QP in PD-A cannot
access a Memory Region registered in PD-B.

```c
struct ibv_pd *pd = ibv_alloc_pd(ctx);
```

PDs serve several purposes:

- **Isolation between applications.** Two processes on the same machine can each have
  their own PD, and neither can access the other's memory registrations.
- **Isolation within an application.** A database might use separate PDs for different
  tenants to prevent cross-tenant memory access.
- **Associate MRs with QPs.** The QP and the MR must share a PD, or the hardware will
  reject the operation.

In most simple applications, you create a single PD and use it for everything.

### 3.3 Memory Region (MR)

This is where RDMA gets its "direct memory access" power. A Memory Region tells the
RDMA hardware: "This range of virtual memory is safe to DMA to/from. Here are the
access permissions."

```c
struct ibv_mr *mr = ibv_reg_mr(
    pd,
    buffer,              // pointer to memory
    buffer_size,         // size in bytes
    IBV_ACCESS_LOCAL_WRITE |
    IBV_ACCESS_REMOTE_WRITE |
    IBV_ACCESS_REMOTE_READ
);
// mr->lkey  -- local key (for local operations)
// mr->rkey  -- remote key (for remote operations)
```

When you register memory, the following happens:

1. The kernel pins the pages (prevents them from being swapped out).
2. The kernel translates virtual addresses to physical addresses.
3. The translation table is programmed into the HCA.
4. The HCA returns an **lkey** (local key) and an **rkey** (remote key).

The **lkey** is used in local work requests (send, recv) to tell the hardware which MR
contains the data. The **rkey** is communicated to the remote side and used in RDMA
Read/Write operations to authorize direct memory access.

**Critical performance note:** Memory registration is expensive (milliseconds). It
involves pinning pages, building translation tables, and programming the HCA. Do not
register and deregister memory on the critical path. Register once at startup and reuse.

#### Access Flags

| Flag                       | Meaning                                           |
|----------------------------|---------------------------------------------------|
| IBV_ACCESS_LOCAL_WRITE     | HCA can write to this MR (needed for recv)        |
| IBV_ACCESS_REMOTE_WRITE   | Remote QPs can RDMA Write to this MR              |
| IBV_ACCESS_REMOTE_READ    | Remote QPs can RDMA Read from this MR             |
| IBV_ACCESS_REMOTE_ATOMIC  | Remote QPs can perform atomics on this MR         |
| IBV_ACCESS_MW_BIND        | Memory windows can be bound to this MR            |
| IBV_ACCESS_ON_DEMAND      | Use On-Demand Paging (no pinning)                 |

### 3.4 Queue Pair (QP)

The Queue Pair is the fundamental communication endpoint in RDMA. Every QP consists of
two queues:

- **Send Queue (SQ):** Where you post work requests for outgoing operations (send,
  RDMA write, RDMA read, atomic).
- **Receive Queue (RQ):** Where you post receive buffers for incoming send operations.

```c
struct ibv_qp_init_attr qp_init_attr = {
    .send_cq = cq,
    .recv_cq = cq,          // can be the same or different CQ
    .cap = {
        .max_send_wr = 128,  // max outstanding send work requests
        .max_recv_wr = 128,  // max outstanding recv work requests
        .max_send_sge = 4,   // max scatter-gather entries per send WR
        .max_recv_sge = 4,   // max scatter-gather entries per recv WR
        .max_inline_data = 64 // max inline data size
    },
    .qp_type = IBV_QPT_RC   // Reliable Connected
};
struct ibv_qp *qp = ibv_create_qp(pd, &qp_init_attr);
```

#### QP Types

RDMA supports several QP types, each with different semantics:

| QP Type | Name                    | Connection | Reliability | Operations Supported           |
|---------|-------------------------|------------|-------------|-------------------------------|
| RC      | Reliable Connected      | Yes        | Yes         | Send, RDMA R/W, Atomic       |
| UC      | Unreliable Connected    | Yes        | No          | Send, RDMA Write              |
| UD      | Unreliable Datagram     | No         | No          | Send only                     |
| XRC     | Extended Reliable Conn. | Yes        | Yes         | Send, RDMA R/W, Atomic       |
| DC      | Dynamic Connected       | Dynamic    | Yes         | Send, RDMA R/W, Atomic       |

**RC (Reliable Connected)** is the most commonly used type. It provides in-order,
reliable delivery with hardware-level retransmission. One QP connects to exactly one
remote QP, forming a dedicated channel.

**UD (Unreliable Datagram)** is used when you need to communicate with many peers from
a single QP (e.g., for service discovery, multicast). Messages are limited to a single
MTU (typically 4096 bytes for IB, 1024 for RoCE). There is no reliability or ordering
guarantee.

**DC (Dynamic Connected)** is a Mellanox/NVIDIA extension that combines the best of RC
and UD: one QP can talk to many remote QPs (like UD), but it supports all RC operations
including RDMA Read/Write and atomics. Connections are established transparently per
message.

### 3.5 Completion Queue (CQ)

The Completion Queue is where the hardware reports that work requests have completed
(or failed). Every QP must be associated with at least one CQ (one for the SQ and one
for the RQ; they can be the same CQ).

```c
struct ibv_cq *cq = ibv_create_cq(ctx, cq_size, NULL, NULL, 0);
```

When you post a work request and it completes, the hardware places a Work Completion
(WC) entry into the CQ. You then poll the CQ to retrieve these completions.

CQs are the feedback mechanism of the entire RDMA system. Without polling the CQ, you
have no idea whether your operations succeeded or failed.

### 3.6 Work Request (WR) and Work Completion (WC)

A **Work Request (WR)** is a descriptor that tells the hardware what to do. You post
WRs to the SQ or RQ of a QP.

```c
// Send Work Request
struct ibv_send_wr wr = {
    .wr_id      = unique_id,       // application-defined ID
    .sg_list    = &sge,            // scatter-gather list
    .num_sge    = 1,               // number of scatter-gather entries
    .opcode     = IBV_WR_SEND,     // operation type
    .send_flags = IBV_SEND_SIGNALED // request completion notification
};

struct ibv_sge sge = {
    .addr   = (uint64_t)buffer,    // address within MR
    .length = message_size,         // data length
    .lkey   = mr->lkey             // local key of the MR
};
```

A **Work Completion (WC)** is the result of a completed WR:

```c
struct ibv_wc wc;
int n = ibv_poll_cq(cq, 1, &wc);
if (n > 0) {
    if (wc.status == IBV_WC_SUCCESS) {
        // Success! wc.wr_id tells us which WR completed
        // wc.opcode tells us what type of completion
        // wc.byte_len tells us how many bytes were received (for recv)
    } else {
        // Error: wc.status contains the error code
        fprintf(stderr, "WC error: %s\n", ibv_wc_status_str(wc.status));
    }
}
```

### 3.7 Scatter-Gather Entry (SGE)

A Scatter-Gather Entry describes a contiguous region of registered memory. Each WR can
reference multiple SGEs, allowing you to gather data from (or scatter data to) multiple
non-contiguous memory regions in a single operation.

```
Work Request
+-----------+
| SGE[0]    | --> [ buffer_A, offset 0, 1024 bytes, lkey_A ]
| SGE[1]    | --> [ buffer_B, offset 512, 2048 bytes, lkey_B ]
| SGE[2]    | --> [ buffer_A, offset 4096, 512 bytes, lkey_A ]
+-----------+

On the wire, this becomes one contiguous message:
[1024 bytes from A][2048 bytes from B][512 bytes from A]
```

This is extremely powerful for protocols that have headers and payloads in different
buffers -- you can send them as one message without copying them together first.

### 3.8 Address Handle (AH)

An Address Handle encapsulates the routing information needed to reach a remote port.
It is primarily used with Unreliable Datagram (UD) QPs, where each send can go to a
different destination.

```c
struct ibv_ah_attr ah_attr = {
    .dlid          = remote_lid,      // destination Local ID (IB)
    .sl            = 0,               // service level
    .src_path_bits = 0,
    .port_num      = 1,
    .is_global     = 1,               // use GRH (required for RoCE)
    .grh = {
        .dgid = remote_gid,           // destination GID
        .sgid_index = gid_index,
        .hop_limit  = 64,
        .traffic_class = 0
    }
};
struct ibv_ah *ah = ibv_create_ah(pd, &ah_attr);
```

For RC and UC QPs, the addressing information is embedded in the QP state during the
connection setup phase, so AHs are not needed for those types.

### 3.9 Shared Receive Queue (SRQ)

A Shared Receive Queue is a pool of receive buffers that multiple QPs can share. Without
SRQ, if you have 1000 connections, each QP needs its own receive buffers -- say 100
buffers per QP. That is 100,000 receive buffers total.

With SRQ, all 1000 QPs share a single pool of, say, 2000 buffers. The hardware pulls
from this shared pool as messages arrive on any of the connected QPs.

```c
struct ibv_srq_init_attr srq_attr = {
    .attr = {
        .max_wr  = 2000,  // max receive work requests in the SRQ
        .max_sge = 1       // max scatter-gather entries per WR
    }
};
struct ibv_srq *srq = ibv_create_srq(pd, &srq_attr);

// When creating QPs, attach them to the SRQ:
qp_init_attr.srq = srq;
```

SRQ is essential for scalable RDMA applications. Without it, memory consumption grows
linearly with the number of connections.

---

## Part 4: RDMA Operations

RDMA supports four categories of operations, each with different semantics and use cases.

### 4.1 Send / Receive

This is the two-sided operation. The sender posts a Send WR, and the receiver must have
previously posted a Receive WR with a buffer large enough to hold the incoming data.

```
  Sender                              Receiver
  +--------+                          +--------+
  | Post   |                          | Post   |
  | Send   |  --- data on wire --->   | Recv   |  (must be posted BEFORE send)
  | WR     |                          | WR     |
  +--------+                          +--------+
      |                                    |
      v                                    v
  Send CQ:                            Recv CQ:
  "Send completed"                    "Recv completed, N bytes received"
```

Key points:
- The receiver MUST post a receive buffer before the sender sends. If no receive buffer
  is available, the behavior depends on the QP type (RNR NAK for RC, packet drop for UD).
- The sender does not need to know the receiver's memory layout.
- Both sides get a completion.
- Maximum message size: unlimited for RC (hardware segments), single MTU for UD.

### 4.2 RDMA Write

This is a one-sided operation. The sender writes data directly into the receiver's
memory at a specified address, without any involvement from the receiver's CPU.

```
  Writer                               Target
  +--------+                          +--------+
  | Post   |                          |        |
  | RDMA   |  --- data on wire --->   | Memory |  (no CPU involvement!)
  | Write  |                          | Region |
  | WR     |                          |        |
  +--------+                          +--------+
      |
      v
  Send CQ:
  "RDMA Write completed"

  (NO completion on the target side -- it never knew!)
```

Key points:
- The writer must know the remote address and rkey (exchanged out-of-band).
- No receive buffer is needed on the target.
- No completion is generated on the target side. The target's CPU is completely
  uninvolved.
- To notify the target, use **RDMA Write with Immediate Data**. This is an RDMA Write
  that also consumes a receive buffer on the target and generates a receive completion,
  carrying a 32-bit immediate value.

### 4.3 RDMA Read

Another one-sided operation. The initiator reads data from the target's memory.

```
  Reader                               Target
  +--------+                          +--------+
  | Post   |  --- RDMA Read Req -->   |        |
  | RDMA   |                          | Memory |  (no CPU involvement!)
  | Read   |  <-- data response ---   | Region |
  | WR     |                          |        |
  +--------+                          +--------+
      |
      v
  Send CQ:
  "RDMA Read completed, data is in local buffer"
```

Key points:
- The initiator specifies both a remote address/rkey (source) and a local address/lkey
  (destination).
- Data flows from remote to local.
- No completion on the target side.
- RDMA Read is only supported on RC (not UC or UD).

### 4.4 Atomic Operations

RDMA supports two atomic operations that execute on the target's memory atomically:

- **Compare-and-Swap (CAS):** If the value at the target address equals `compare_value`,
  replace it with `swap_value`. Return the original value.
- **Fetch-and-Add (FAA):** Add `add_value` to the value at the target address. Return
  the original value.

```c
// Compare-and-Swap
wr.opcode = IBV_WR_ATOMIC_CMP_AND_SWP;
wr.wr.atomic.remote_addr = remote_addr;
wr.wr.atomic.rkey = remote_rkey;
wr.wr.atomic.compare_add = expected_value;
wr.wr.atomic.swap = new_value;

// Fetch-and-Add
wr.opcode = IBV_WR_ATOMIC_FETCH_AND_ADD;
wr.wr.atomic.remote_addr = remote_addr;
wr.wr.atomic.rkey = remote_rkey;
wr.wr.atomic.compare_add = add_value;
```

Atomics operate on 8-byte aligned, 8-byte values. They are essential for building
distributed locks, counters, and consensus protocols without any involvement from the
target's CPU.

### Operations Summary

```
+------------------+--------+--------+---------+--------+
| Operation        |   RC   |   UC   |   UD    |   DC   |
+------------------+--------+--------+---------+--------+
| Send/Recv        |  Yes   |  Yes   |  Yes    |  Yes   |
| RDMA Write       |  Yes   |  Yes   |   No    |  Yes   |
| RDMA Write+Imm   |  Yes   |  Yes   |   No    |  Yes   |
| RDMA Read        |  Yes   |   No   |   No    |  Yes   |
| Atomic CAS       |  Yes   |   No   |   No    |  Yes   |
| Atomic FAA       |  Yes   |   No   |   No    |  Yes   |
+------------------+--------+--------+---------+--------+
```

---

## Part 5: Connection-Oriented vs. Connectionless

### Connection-Oriented (RC, UC, XRC, DC)

For RC QPs, a connection must be established before data can flow. This involves
exchanging QP information (QP number, LID, GID, PSN) between the two endpoints and
transitioning the QP through a state machine (covered in the next section).

Connection establishment can be done:
1. **Out-of-band:** Using TCP sockets, shared files, etc. The applications exchange
   QP metadata themselves.
2. **RDMA CM (rdma_cm):** A library that provides a connection manager similar to TCP's
   listen/accept model, built on top of IB communication management (CM) messages or
   RDMA over IP.

### Connectionless (UD)

UD QPs do not require connection setup. Any UD QP can send to any other UD QP by
specifying the destination via an Address Handle. This is similar to UDP in traditional
networking.

The trade-off:
- **UD advantages:** O(1) resources per endpoint (one QP talks to N peers), faster
  "connection" setup, multicast support.
- **UD disadvantages:** Limited to single-MTU messages, no reliability, no RDMA
  Read/Write, 40-byte GRH header overhead in receive buffer.

---

## Part 6: The QP State Machine

Every QP has a state, and it must transition through specific states before it can send
or receive data. Understanding this state machine is critical for RDMA programming.

```
                    ibv_create_qp()
                         |
                         v
                    +---------+
                    |  RESET  |
                    +---------+
                         |
                    ibv_modify_qp(INIT)
                    Set: port, pkey, access flags
                         |
                         v
                    +---------+
                    |  INIT   | <-- Can post receive WRs here
                    +---------+
                         |
                    ibv_modify_qp(RTR)
                    Set: dest QPN, PSN, path (LID/GID),
                         MTU, max_dest_rd_atomic
                         |
                         v
                    +---------+
                    |   RTR   | <-- Ready to Receive
                    +---------+     Can receive but not send
                         |
                    ibv_modify_qp(RTS)
                    Set: timeout, retry_cnt, rnr_retry,
                         sq_psn, max_rd_atomic
                         |
                         v
                    +---------+
                    |   RTS   | <-- Ready to Send
                    +---------+     Fully operational!
                        / \
                       /   \
                      v     v
                 +------+ +------+
                 | SQD  | | ERR  |
                 +------+ +------+
                    |
                    v
                 +------+
                 | SQE  |
                 +------+
```

### State Descriptions

| State | Name                    | Description                                      |
|-------|-------------------------|--------------------------------------------------|
| RESET | Reset                   | Initial state after creation. Nothing works.      |
| INIT  | Initialized             | Can post receive WRs. Cannot send or receive.    |
| RTR   | Ready to Receive        | Can receive messages. Cannot send.                |
| RTS   | Ready to Send           | Fully operational. Can send and receive.          |
| SQD   | Send Queue Drained      | Send queue is being drained (for QP modification) |
| SQE   | Send Queue Error        | Send queue error (recoverable to RTS)             |
| ERR   | Error                   | Unrecoverable error. Must destroy and recreate.  |

### Transition Details

**RESET -> INIT:**
```c
struct ibv_qp_attr attr = {
    .qp_state        = IBV_QPS_INIT,
    .pkey_index      = 0,
    .port_num        = 1,
    .qp_access_flags = IBV_ACCESS_REMOTE_WRITE |
                       IBV_ACCESS_REMOTE_READ  |
                       IBV_ACCESS_REMOTE_ATOMIC
};
ibv_modify_qp(qp, &attr,
    IBV_QP_STATE | IBV_QP_PKEY_INDEX |
    IBV_QP_PORT  | IBV_QP_ACCESS_FLAGS);
```

**INIT -> RTR:**
This is where you specify the remote side's information:
```c
struct ibv_qp_attr attr = {
    .qp_state              = IBV_QPS_RTR,
    .path_mtu              = IBV_MTU_4096,
    .dest_qp_num           = remote_qpn,
    .rq_psn                = remote_psn,
    .max_dest_rd_atomic    = 16,
    .min_rnr_timer         = 12,
    .ah_attr               = {
        .dlid          = remote_lid,
        .sl            = 0,
        .src_path_bits = 0,
        .is_global     = 1,
        .grh           = { .dgid = remote_gid, ... }
    }
};
ibv_modify_qp(qp, &attr,
    IBV_QP_STATE | IBV_QP_AV | IBV_QP_PATH_MTU |
    IBV_QP_DEST_QPN | IBV_QP_RQ_PSN |
    IBV_QP_MAX_DEST_RD_ATOMIC | IBV_QP_MIN_RNR_TIMER);
```

**RTR -> RTS:**
```c
struct ibv_qp_attr attr = {
    .qp_state      = IBV_QPS_RTS,
    .timeout       = 14,     // ~67 seconds
    .retry_cnt     = 7,      // max retries
    .rnr_retry     = 7,      // max RNR retries (7 = infinite)
    .sq_psn        = local_psn,
    .max_rd_atomic = 16
};
ibv_modify_qp(qp, &attr,
    IBV_QP_STATE | IBV_QP_TIMEOUT |
    IBV_QP_RETRY_CNT | IBV_QP_RNR_RETRY |
    IBV_QP_SQ_PSN | IBV_QP_MAX_QP_RD_ATOMIC);
```

### Important Notes on the State Machine

1. **Post receives in INIT state.** You should post receive buffers before transitioning
   to RTR. Otherwise, there is a window where the remote side could send a message and
   find no receive buffer (causing an RNR NAK).

2. **Both sides must reach RTR before either can receive.** The transition is:
   Side A: RESET->INIT->RTR->RTS, Side B: RESET->INIT->RTR->RTS. If using out-of-band
   exchange, the typical pattern is:
   - Both sides: create QP, move to INIT, post receives.
   - Exchange QP info (QPN, GID, PSN).
   - Both sides: move to RTR, then RTS.

3. **PSN (Packet Sequence Number)** is the starting sequence number. It can be random
   but must be communicated to the remote side.

---

## Part 7: The Completion Model

### Polling vs. Event-Driven

RDMA supports two models for retrieving completions:

#### Polling (Busy-Waiting)

```c
struct ibv_wc wc;
while (1) {
    int n = ibv_poll_cq(cq, 1, &wc);
    if (n > 0) {
        // Process completion
        handle_completion(&wc);
    } else if (n < 0) {
        // CQ error
        break;
    }
    // n == 0: no completion yet, keep polling
}
```

**Pros:** Lowest possible latency. No interrupt overhead. Completion is detected within
nanoseconds of arrival.

**Cons:** Burns 100% CPU on one core. Suitable for latency-critical paths (storage,
trading) where you dedicate a core to polling.

#### Event-Driven (Interrupt-Based)

```c
// Create CQ with a completion channel
struct ibv_comp_channel *channel = ibv_create_comp_channel(ctx);
struct ibv_cq *cq = ibv_create_cq(ctx, cq_size, NULL, channel, 0);

// Arm the CQ for notification
ibv_req_notify_cq(cq, 0);

// Wait for event (blocks until a completion arrives)
struct ibv_cq *ev_cq;
void *ev_ctx;
ibv_get_cq_event(channel, &ev_cq, &ev_ctx);

// Acknowledge the event
ibv_ack_cq_events(ev_cq, 1);

// Re-arm for next notification
ibv_req_notify_cq(cq, 0);

// Now poll the CQ (there may be multiple completions)
struct ibv_wc wc_array[16];
int n;
do {
    n = ibv_poll_cq(cq, 16, wc_array);
    for (int i = 0; i < n; i++) {
        handle_completion(&wc_array[i]);
    }
} while (n > 0);
```

**Pros:** CPU-efficient. The thread sleeps until a completion arrives.

**Cons:** Higher latency (interrupt processing takes microseconds). Must re-arm the CQ
after each notification.

#### Hybrid Approach

Many high-performance applications use a hybrid: poll for a while, and if no completions
arrive within a timeout, switch to event-driven mode. When a completion arrives via
interrupt, switch back to polling.

```c
while (running) {
    int found = 0;
    // Poll for up to 1000 iterations
    for (int i = 0; i < 1000; i++) {
        int n = ibv_poll_cq(cq, 16, wc_array);
        if (n > 0) {
            found = 1;
            process_completions(wc_array, n);
            break;
        }
    }
    if (!found) {
        // Switch to event-driven
        ibv_req_notify_cq(cq, 0);
        // Check once more (race condition avoidance)
        int n = ibv_poll_cq(cq, 16, wc_array);
        if (n > 0) {
            process_completions(wc_array, n);
        } else {
            ibv_get_cq_event(channel, &ev_cq, &ev_ctx);
            ibv_ack_cq_events(ev_cq, 1);
        }
    }
}
```

### Selective Signaling

By default, every completed send WR generates a Work Completion in the CQ. But CQ
processing has overhead. For high-throughput applications, you can use **selective
signaling**: only request a completion every N operations.

```c
for (int i = 0; i < batch_size; i++) {
    wr[i].send_flags = (i == batch_size - 1) ? IBV_SEND_SIGNALED : 0;
}
```

When the signaled WR completes, you know all previous unsignaled WRs also completed
(because RC guarantees in-order completion).

**Warning:** You MUST signal at least once before the SQ fills up. If you post more
unsignaled WRs than the SQ depth without a signaled WR completing, the SQ will overflow
and the QP will transition to an error state.

A common pattern: signal every `sq_depth / 2` WRs.

### Inline Sends

For very small messages (typically <= 64-256 bytes, depending on the HCA), you can use
**inline sends**. Instead of the HCA DMA-reading the data from the MR, the CPU writes
the data directly into the Work Queue Element (WQE) in the HCA's send queue.

```c
wr.send_flags = IBV_SEND_SIGNALED | IBV_SEND_INLINE;
```

Benefits:
- Eliminates one DMA read (the HCA does not need to fetch data from memory).
- The buffer can be reused immediately after `ibv_post_send()` returns (no need to wait
  for completion).
- Slightly lower latency for small messages.

The trade-off: more CPU work (the CPU copies data into the WQE), and it only works for
small messages. The maximum inline size is reported by `ibv_query_device()` and can also
be set per-QP during creation.

---

## Part 8: Putting It All Together

### The Lifecycle of an RDMA Application

Here is the complete sequence for a simple RC Send/Recv application:

```
1. Open device:           ctx = ibv_open_device(dev)
2. Allocate PD:           pd = ibv_alloc_pd(ctx)
3. Register memory:       mr = ibv_reg_mr(pd, buf, size, flags)
4. Create CQ:             cq = ibv_create_cq(ctx, depth, ...)
5. Create QP:             qp = ibv_create_qp(pd, &init_attr)
6. Move QP to INIT:       ibv_modify_qp(qp, &init_attr)
7. Post receive buffers:  ibv_post_recv(qp, &recv_wr, &bad_wr)
8. Exchange QP info:      (out-of-band: TCP, RDMA CM, etc.)
9. Move QP to RTR:        ibv_modify_qp(qp, &rtr_attr)
10. Move QP to RTS:       ibv_modify_qp(qp, &rts_attr)
11. Post send:            ibv_post_send(qp, &send_wr, &bad_wr)
12. Poll for completions: ibv_poll_cq(cq, n, wc_array)
13. Cleanup:              ibv_destroy_qp, ibv_dereg_mr, ibv_dealloc_pd, etc.
```

### Resource Cleanup Order

Resources must be destroyed in reverse order of creation. The rule: destroy children
before parents.

```
ibv_destroy_qp(qp);        // QP uses CQ, MR, PD
ibv_destroy_cq(cq);        // CQ uses context
ibv_destroy_srq(srq);      // if using SRQ
ibv_dereg_mr(mr);          // MR uses PD
ibv_dealloc_pd(pd);        // PD uses context
ibv_close_device(ctx);     // context uses device
ibv_free_device_list(list); // device list
```

---

## Part 9: Common Pitfalls for Beginners

### Pitfall 1: Forgetting to Post Receives

The most common beginner mistake. If the remote side sends data and there is no receive
buffer posted, the behavior depends on the QP type:
- **RC:** The hardware sends an RNR (Receiver Not Ready) NAK. The sender retries up to
  `rnr_retry` times, then the QP moves to ERROR state.
- **UD:** The packet is silently dropped.

Always post receive buffers before moving to RTR.

### Pitfall 2: Not Checking WC Status

Every work completion has a status field. If `wc.status != IBV_WC_SUCCESS`, the QP has
entered an error state (for RC). Common errors:
- `IBV_WC_LOC_LEN_ERR` -- Local length error (receive buffer too small).
- `IBV_WC_LOC_PROT_ERR` -- Local protection error (wrong lkey/rkey or access flags).
- `IBV_WC_REM_ACCESS_ERR` -- Remote access error (invalid rkey or address).
- `IBV_WC_RETRY_EXC_ERR` -- Retry count exceeded (remote unreachable or too slow).
- `IBV_WC_RNR_RETRY_EXC_ERR` -- RNR retry exceeded (remote has no receive buffers).

### Pitfall 3: Memory Registration Misuse

- Registering memory on the hot path -- MR registration takes milliseconds.
- Creating thousands of small MRs instead of a few large ones -- each MR consumes HCA
  resources.
- Forgetting `IBV_ACCESS_LOCAL_WRITE` on receive buffers -- the HCA cannot write
  received data into the buffer.
- Not pinning hugepages -- standard pages can lead to many translation entries.

### Pitfall 4: CQ Overflow

If the CQ is full and a new completion arrives, the CQ overflows. This is a fatal error:
the CQ enters an error state, and all associated QPs move to ERROR.

Prevention: Make the CQ large enough. The CQ must be at least as large as the total
number of outstanding signaled WRs across all QPs that share it.

### Pitfall 5: QP and CQ Sizing

The `max_send_wr` and `max_recv_wr` values you request may be rounded up by the driver.
Always check the returned values in the `ibv_qp_init_attr` structure after QP creation.

---

## Part 10: Performance Tuning Quick Reference

| Technique                | When to Use                      | Expected Impact              |
|--------------------------|----------------------------------|-------------------------------|
| Inline sends             | Messages < 64-256 bytes          | ~100-200 ns latency savings  |
| Selective signaling      | High-throughput workloads         | 2-3x throughput increase     |
| SRQ                      | >100 connections                  | 10-100x memory savings       |
| CQ polling               | Latency-critical paths            | ~1-3 us latency savings      |
| Batched WR posting       | High message rates                | Fewer doorbell rings         |
| Large MTU (4096)         | Bulk data transfer                | Higher bandwidth efficiency  |
| Multiple SGEs            | Scattered data                    | Avoids copy-to-contiguous    |
| Hugepages                | Large memory registrations        | Fewer translation entries    |

---

## Conclusion

RDMA is not just "fast networking" -- it is a fundamentally different programming model
that moves data between machines the way DMA moves data within a machine. The learning
curve is steep because you are essentially programming a co-processor (the HCA) using
a queue-based asynchronous interface.

The key takeaways:

1. **RDMA bypasses the kernel, copies zero times, and offloads protocol processing to
   hardware.** This is what gives it sub-microsecond latency and near-zero CPU usage.

2. **The verbs API is queue-based and asynchronous.** You post work requests and poll
   for completions. There are no blocking send/recv calls on the fast path.

3. **Resources have strict relationships.** PD -> MR, PD -> QP, QP -> CQ. Understand
   these relationships and you understand the programming model.

4. **The QP state machine (RESET->INIT->RTR->RTS) must be followed precisely.** Miss a
   required attribute in a transition and the QP will refuse to move.

5. **One-sided operations (RDMA Read/Write, Atomics) are the killer feature.** They
   allow computation on remote data without involving the remote CPU at all.

Master these fundamentals, and you have the foundation for building storage systems,
distributed databases, AI training frameworks, and financial trading platforms that
operate at the speed of the network, not the speed of the software stack.

---

*Next in this series: "RoCE vs InfiniBand vs iWARP: Choosing Your RDMA Transport" and
"RDMA Programming Patterns and Anti-Patterns."*
