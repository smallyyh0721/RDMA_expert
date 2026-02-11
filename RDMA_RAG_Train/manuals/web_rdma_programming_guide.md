# NVIDIA RDMA Programming Guide

## Overview

This document contains comprehensive RDMA programming examples and reference material from NVIDIA RDMA Aware Programming User Manual v1.7.

## Table of Contents

1. [RDMA_RC Example Using IBV Verbs](#rdma-rc-example)
2. [Multicast Example Using RDMA_CM and IBV Verbs](#multicast-example)
3. [Automatic Path Migration (APM)](#automatic-path-migration)
4. [Shared Receive Queue (SRQ) Example](#shared-receive-queue-example)
5. [Cross-Channel Communications Support](#cross-channel-communications)

---

## RDMA RC Example Using IBV Verbs

This example demonstrates a reliable connected (RC) RDMA application using IBV Verbs API.

### Synopsis

The example shows how to perform following operations using VPI Verbs API:
- Send
- Receive
- RDMA Read
- RDMA Write

### Features Demonstrated

- Device list enumeration and selection
- Queue Pair (QP) creation and management
- Memory Region (MR) registration
- Completion Queue (CQ) management
- TCP socket-based connection establishment
- Client and server modes
- Kernel bypass (zero-copy data transfer)

### Code Structure

```c
/* Compile command */
gcc -Wall -I/usr/local/ofed/include -O2 -o RDMA_RC_example -L/usr/local/ofed/lib64 -L/usr/local/ofed/lib -libverbs RDMA_RC_example.c
```

### Key Functions

**Connection Management:**
- `sock_connect()` - Establish TCP socket connection
- `connect_qp()` - Connect Queue Pairs

**Resource Management:**
- `resources_create()` - Allocate and initialize resources
- `resources_destroy()` - Cleanup and deallocate resources

**QP State Transitions:**
- `modify_qp_to_init()` - RESET → INIT
- `modify_qp_to_rtr()` - INIT → Ready to Receive (RTR)
- `modify_qp_to_rts()` - RTR → Ready to Send (RTS)

**Data Operations:**
- `post_send()` - Post send/receive/rdma requests
- `post_receive()` - Post receive request
- `poll_completion()` - Poll completion queue

---

## Multicast Example Using RDMA_CM and IBV Verbs

### Usage

Both sender and receiver applications can be run using this example.

### Command Line Options

```bash
# Receiver (-m is multicast address, often IP of receiver)
./mc -m 192.168.1.12

# Sender (-s is sender flag)
./mc -s -m 192.168.1.12
```

### Key Features

- **Mellanox on Command Line Adapter (MOCL)** for multicast operations
- **Join** to multicast groups
- **Send** to multiple receivers
- **Receive** from multiple senders
- **Leave** multicast groups

---

## Automatic Path Migration (APM)

### Overview

APM allows migration of cable/network paths without service interruption. Critical for high-availability deployments.

### How It Works

1. **Query alternate port details** - Discover available path options
2. **Load alternate path** - Program hardware to use alternate path
3. **Trigger migration** - Manually or automatically fail over to alternate port
4. **Monitor migration events** - Asynchronous notification of path changes

### Key APIs

```c
// Query device capabilities
ibv_query_device(ctx->id->verbs, &dev_attr);

// Check for APM support
if (!(dev_attr.device_cap_flags | IBV_DEVICE_AUTO_PATH_MIG)) {
    printf("Device does not support auto path migration!");
    return -1;
}
```

---

## Shared Receive Queue (SRQ) Example

### Overview

Demonstrates shared receive queue that can be used by multiple Queue Pairs (QPs) simultaneously.

### Benefits

- **Resource sharing** - Multiple QPs share one receive queue
- **Efficient data transfers** - Reduces memory overhead
- **Scalable implementations** - Simplifies multi-connection scenarios

---

## Cross-Channel Communications Support

### Overview

Cross-Channel allows work requests to be posted to multiple QPs with completion notification on any of them.

### Key Concepts

| Term | Description |
| --- | --- |
| Cross Channel supported QP | QP that allows send_enable, recv_enable, wait, and reduction tasks |
| Managed send QP | Work requests in corresponding send queues must be explicitly enabled |
| Managed receive QP | Work requests in corresponding receive queues must be explicitly enabled |
| Master Queue | Queue that uses send_enable and/or recv_enable work requests to enable tasks |
| Wait task (n) | Task completes when n completion tasks appear in specified completion queue |
| Send Enable task (n) | Enables next n send tasks in specified send queue |
| Receive Enable task | Enables to next n send tasks in specified receive queue |
| Reduction operation | Data reduction operation to be executed by HCA on specified data |

### Usage Model

1. Create completion queues with ignore-overrun bit
2. Create and configure QPs with appropriate flags
3. Post task lists for compound operations
4. Check appropriate queue for compound operation completion
5. Destroy resources when done

---

## Extended Atomics Support

### Supported Hardware

- **ConnectX-2/ConnectX-3** devices support read-modify-write operations on regions sized as multiples of 64 bits with 64-bit alignment
- **ConnectX-IB and later hardware** support multi-field fetch-and-add, masked compare-and-swap operations
- **Natural word alignment** - Data returned in host's natural word size regardless of field arrangement

### Multi-Field Operations

**Fetch & Add** (Fetch-and-add):
```
struct {
    struct {
        // Compare value
        uint64_t  compare_val;
        uint64_t  swap_val;
        uint64_t  swap_mask;
    } masked_atomics;
} op;
```

**Compare & Swap**:
```
struct {
    struct {
        uint64_t    compare_val;
        uint64_t  add_val;
        uint64_t    field_boundary;
    } cmp_swap;
} masked_atomics;
```

### Memory Registration

```
// Register memory regions
ibv_reg_mr(pd, buf, size, IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_READ | IBV_ACCESS_REMOTE_WRITE);

// Use extended atoms for larger operations
ibv_exp_reg_mr(pd, buf, size, &attr, IBV_EXP_ATOMIC_INLINE);
```

---

## User-Mode Memory Registration (UMR)

### Overview

UMR allows creation of memory keys for non-contiguous memory regions.

### Memory Region Formats

1. **Regular Structure** - Base address, stride, extent, element count, repeat count
2. **Indirect Memory** - Array of memory regions with regular structure
3. **Interleaved Memory** - Multiple regions interleaved using repeat structure

### Key Benefits

- **Concatenation** - Combine arbitrary contiguous regions
- **Flexibility** - Support non-contiguous memory patterns
- **Efficiency** - Single key for complex multi-region operations

---

## Additional Resources

### NVIDIA Documentation Links

- **Main Documentation**: https://docs.nvidia.com/networking/display/RDMAAwareProgrammingv17
- **Linux RDMA**: https://github.com/linux-rdma/rdma-core
- **InfiniBand Verbs**: https://www.kernel.org/doc/html/latest/infiniband/ib_verbs.html

---

## Topics Covered

### Core Concepts
- RDMA verbs API and programming model
- Queue Pair management and state transitions
- Memory registration and access patterns
- Completion queue management
- Connection management

### Advanced Features
- Automatic Path Migration (APM)
- Cross-Channel Communications
- Shared Receive Queues (SRQ)
- Extended atomic operations
- User-Mode Memory Registration

### Applications
- High-performance data transfer
- Multi-connection management
- Lossless network communication
- Congestion management integration

---

## Notes

This guide is extracted from NVIDIA's comprehensive RDMA programming documentation and serves as a reference for developers working with:
- ConnectX adapter cards
- BlueField DPUs  
- Spectrum switches
- MLNX-OFED software stack

For detailed information, refer to the complete NVIDIA RDMA Aware Programming User Manual.