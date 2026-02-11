---
title: "RDMA Verbs API Programming Manual - Complete libibverbs Reference"
category: manuals
tags:
  - rdma
  - verbs
  - libibverbs
  - ibv_post_send
  - ibv_post_recv
  - ibv_poll_cq
  - queue_pair
  - completion_queue
  - memory_registration
  - protection_domain
  - shared_receive_queue
  - address_handle
  - programming
  - API
source: "libibverbs API documentation, RDMA programming best practices, kernel verbs interface"
---

# RDMA Verbs API Programming Manual

## 1. Introduction to RDMA Verbs

The RDMA Verbs API, exposed through the `libibverbs` library, is the foundational user-space interface for programming RDMA (Remote Direct Memory Access) operations. Verbs provide a transport-independent abstraction that works across InfiniBand, RoCE (RDMA over Converged Ethernet), and iWARP fabrics.

The Verbs API follows a resource hierarchy model:

```
Device (ibv_device / ibv_context)
  |
  +-- Protection Domain (ibv_pd)
  |     |
  |     +-- Memory Region (ibv_mr)
  |     +-- Queue Pair (ibv_qp)
  |     +-- Shared Receive Queue (ibv_srq)
  |     +-- Address Handle (ibv_ah)
  |     +-- Memory Window (ibv_mw)
  |
  +-- Completion Queue (ibv_cq)
  +-- Completion Channel (ibv_comp_channel)
```

### 1.1 Header Files and Linking

```c
#include <infiniband/verbs.h>

/* Link with: -libverbs */
/* Optional extended verbs: */
#include <infiniband/verbs_exp.h>
```

### 1.2 Compilation

```bash
gcc -o rdma_app rdma_app.c -libverbs
# With RDMA-CM:
gcc -o rdma_app rdma_app.c -libverbs -lrdmacm
```

---

## 2. Device Operations

### 2.1 ibv_get_device_list - Enumerate RDMA Devices

```c
struct ibv_device **ibv_get_device_list(int *num_devices);
```

Returns a NULL-terminated list of available RDMA devices. The caller must free the list with `ibv_free_device_list()` but must not free individual device pointers.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| num_devices | int* | Output: number of devices found (can be NULL) |

**Return Value:** Array of `ibv_device*` pointers, NULL-terminated. Returns NULL on failure.

**Example:**

```c
int num_devices;
struct ibv_device **dev_list = ibv_get_device_list(&num_devices);
if (!dev_list) {
    fprintf(stderr, "Failed to get device list: %s\n", strerror(errno));
    return -1;
}

for (int i = 0; i < num_devices; i++) {
    printf("Device %d: %s\n", i, ibv_get_device_name(dev_list[i]));
    printf("  GUID: %016llx\n",
           (unsigned long long)ibv_get_device_guid(dev_list[i]));
    printf("  Node type: %d\n", dev_list[i]->node_type);
    printf("  Transport: %d\n", dev_list[i]->transport_type);
}
```

**Common Pitfall:** Forgetting to call `ibv_free_device_list()` causes a resource leak. However, you must open the device context *before* freeing the list if you need to use a device.

### 2.2 ibv_open_device - Open Device Context

```c
struct ibv_context *ibv_open_device(struct ibv_device *device);
```

Opens a device and returns a context used for all subsequent operations on that device. Each call creates a new independent context.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| device | struct ibv_device* | Device to open from ibv_get_device_list() |

**Return Value:** `ibv_context*` on success, NULL on failure with errno set.

**Key errno values:**

| errno | Description |
|-------|-------------|
| ENOENT | Device not found or driver not loaded |
| EACCES | Insufficient permissions (/dev/infiniband/uverbs*) |
| ENOMEM | Insufficient kernel memory |

**Example:**

```c
struct ibv_context *ctx = ibv_open_device(dev_list[0]);
if (!ctx) {
    fprintf(stderr, "Failed to open device: %s\n", strerror(errno));
    ibv_free_device_list(dev_list);
    return -1;
}

/* Now safe to free the device list */
ibv_free_device_list(dev_list);
dev_list = NULL;  /* Good practice */
```

### 2.3 ibv_query_device - Query Device Capabilities

```c
int ibv_query_device(struct ibv_context *context,
                     struct ibv_device_attr *device_attr);
```

Queries the device for its capabilities and limits. Essential for determining maximum resource counts and supported features.

**Key fields in ibv_device_attr:**

| Field | Type | Description |
|-------|------|-------------|
| max_qp | int | Maximum number of Queue Pairs |
| max_qp_wr | int | Maximum WRs per QP |
| max_sge | int | Maximum SGEs per WR |
| max_cq | int | Maximum number of CQs |
| max_cqe | int | Maximum CQEs per CQ |
| max_mr | int | Maximum number of MRs |
| max_mr_size | uint64_t | Maximum MR size |
| max_pd | int | Maximum Protection Domains |
| max_qp_rd_atom | int | Max outstanding RDMA reads/atomics as target |
| max_qp_init_rd_atom | int | Max outstanding RDMA reads/atomics as initiator |
| atomic_cap | enum ibv_atomic_cap | Atomic operation capabilities |
| max_srq | int | Maximum SRQs |
| max_srq_wr | int | Maximum WRs per SRQ |
| phys_port_cnt | uint8_t | Number of physical ports |

**Example:**

```c
struct ibv_device_attr dev_attr;
int ret = ibv_query_device(ctx, &dev_attr);
if (ret) {
    fprintf(stderr, "Failed to query device: %s\n", strerror(ret));
    return -1;
}

printf("Max QPs: %d\n", dev_attr.max_qp);
printf("Max QP WRs: %d\n", dev_attr.max_qp_wr);
printf("Max SGEs: %d\n", dev_attr.max_sge);
printf("Max CQs: %d\n", dev_attr.max_cq);
printf("Max CQEs: %d\n", dev_attr.max_cqe);
printf("Max MRs: %d\n", dev_attr.max_mr);
printf("Max MR size: %lu\n", dev_attr.max_mr_size);
printf("Atomic cap: %d\n", dev_attr.atomic_cap);
printf("Physical ports: %d\n", dev_attr.phys_port_cnt);
```

### 2.4 ibv_query_port - Query Port Attributes

```c
int ibv_query_port(struct ibv_context *context, uint8_t port_num,
                   struct ibv_port_attr *port_attr);
```

**Key fields in ibv_port_attr:**

| Field | Type | Description |
|-------|------|-------------|
| state | enum ibv_port_state | Port state (Active, Init, Down, etc.) |
| max_mtu | enum ibv_mtu | Maximum supported MTU |
| active_mtu | enum ibv_mtu | Currently active MTU |
| lid | uint16_t | Local Identifier (InfiniBand) |
| sm_lid | uint16_t | Subnet Manager LID |
| gid_tbl_len | int | Number of GID table entries |
| pkey_tbl_len | int | Number of partition key entries |
| active_speed | uint8_t | Active link speed |
| active_width | uint8_t | Active link width |
| link_layer | uint8_t | Link layer type (IB or Ethernet) |

**Port states:**

| State | Value | Description |
|-------|-------|-------------|
| IBV_PORT_NOP | 0 | Reserved |
| IBV_PORT_DOWN | 1 | Logical link is down |
| IBV_PORT_INIT | 2 | Link initialized, no SM yet |
| IBV_PORT_ARMED | 3 | SM has configured port |
| IBV_PORT_ACTIVE | 4 | Port is fully active |
| IBV_PORT_ACTIVE_DEFER | 5 | Not defined in all implementations |

**Example:**

```c
struct ibv_port_attr port_attr;
int ret = ibv_query_port(ctx, 1, &port_attr);  /* port_num is 1-based */
if (ret) {
    fprintf(stderr, "Failed to query port 1: %s\n", strerror(ret));
    return -1;
}

if (port_attr.state != IBV_PORT_ACTIVE) {
    fprintf(stderr, "Port 1 is not active (state=%d)\n", port_attr.state);
    return -1;
}

printf("Port LID: %d\n", port_attr.lid);
printf("Active MTU: %d\n", 128 << port_attr.active_mtu);
printf("Link layer: %s\n",
       port_attr.link_layer == IBV_LINK_LAYER_INFINIBAND ? "InfiniBand" :
       port_attr.link_layer == IBV_LINK_LAYER_ETHERNET ? "Ethernet" : "Unknown");
```

### 2.5 ibv_query_gid - Query GID Table

```c
int ibv_query_gid(struct ibv_context *context, uint8_t port_num,
                  int index, union ibv_gid *gid);
```

Retrieves a specific GID entry. GID index 0 is the default GID based on the port GUID. For RoCE, GIDs correspond to IP addresses and the GID index selection determines the RoCE version (v1 vs v2).

```c
union ibv_gid my_gid;
ibv_query_gid(ctx, 1, 0, &my_gid);
printf("GID: %02x%02x:%02x%02x:%02x%02x:%02x%02x:"
       "%02x%02x:%02x%02x:%02x%02x:%02x%02x\n",
       my_gid.raw[0], my_gid.raw[1], my_gid.raw[2], my_gid.raw[3],
       my_gid.raw[4], my_gid.raw[5], my_gid.raw[6], my_gid.raw[7],
       my_gid.raw[8], my_gid.raw[9], my_gid.raw[10], my_gid.raw[11],
       my_gid.raw[12], my_gid.raw[13], my_gid.raw[14], my_gid.raw[15]);
```

### 2.6 ibv_close_device - Close Device Context

```c
int ibv_close_device(struct ibv_context *context);
```

Closes a device context. All resources associated with the context must be freed before calling this function.

**Important:** Closing a device context without first destroying all QPs, CQs, MRs, PDs, etc. will result in a resource leak in the kernel.

---

## 3. Protection Domains

### 3.1 ibv_alloc_pd - Allocate Protection Domain

```c
struct ibv_pd *ibv_alloc_pd(struct ibv_context *context);
```

A Protection Domain (PD) groups resources for access control. QPs can only access MRs registered in the same PD. PDs enable isolation between different applications or security contexts sharing the same RDMA device.

**Return Value:** `ibv_pd*` on success, NULL on failure.

**Example:**

```c
struct ibv_pd *pd = ibv_alloc_pd(ctx);
if (!pd) {
    fprintf(stderr, "Failed to allocate PD: %s\n", strerror(errno));
    return -1;
}
```

**Common Pitfall:** Creating multiple PDs when one would suffice wastes kernel resources. Most applications need only a single PD. Use multiple PDs only when you need access isolation between different security domains.

### 3.2 ibv_dealloc_pd - Deallocate Protection Domain

```c
int ibv_dealloc_pd(struct ibv_pd *pd);
```

Deallocates a PD. All MRs, QPs, SRQs, and AHs associated with the PD must be destroyed first.

**Return Value:** 0 on success, errno on failure. Returns EBUSY if resources are still attached.

---

## 4. Memory Registration

### 4.1 ibv_reg_mr - Register Memory Region

```c
struct ibv_mr *ibv_reg_mr(struct ibv_pd *pd, void *addr, size_t length,
                          int access);
```

Registers a contiguous block of virtual memory for use with RDMA operations. Registration pins the memory (prevents swapping) and creates a mapping between virtual and physical addresses for DMA.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| pd | struct ibv_pd* | Protection domain to register in |
| addr | void* | Start of memory region |
| length | size_t | Length in bytes |
| access | int | Bitwise OR of access flags |

**Access Flags:**

| Flag | Value | Description |
|------|-------|-------------|
| IBV_ACCESS_LOCAL_WRITE | (1 << 0) | Allow local writes (required for receive buffers) |
| IBV_ACCESS_REMOTE_WRITE | (1 << 1) | Allow RDMA Write from remote QP |
| IBV_ACCESS_REMOTE_READ | (1 << 2) | Allow RDMA Read from remote QP |
| IBV_ACCESS_REMOTE_ATOMIC | (1 << 3) | Allow atomic operations from remote QP |
| IBV_ACCESS_MW_BIND | (1 << 4) | Allow Memory Window binding |
| IBV_ACCESS_ZERO_BASED | (1 << 5) | Use zero-based addressing |
| IBV_ACCESS_ON_DEMAND | (1 << 6) | On-Demand Paging |
| IBV_ACCESS_HUGETLB | (1 << 7) | Register using huge pages |
| IBV_ACCESS_RELAXED_ORDERING | (1 << 20) | Allow relaxed ordering (PCIe) |

**Return Value:** `ibv_mr*` on success with lkey and rkey populated. NULL on failure.

**Key fields in ibv_mr:**

| Field | Type | Description |
|-------|------|-------------|
| lkey | uint32_t | Local key for local operations |
| rkey | uint32_t | Remote key shared with peer for RDMA ops |
| addr | void* | Registered address |
| length | size_t | Registered length |

**Example:**

```c
/* Allocate aligned buffer */
size_t buf_size = 4096;
void *buf = NULL;
posix_memalign(&buf, sysconf(_SC_PAGESIZE), buf_size);
memset(buf, 0, buf_size);

/* Register for local write and remote read/write */
struct ibv_mr *mr = ibv_reg_mr(pd, buf, buf_size,
    IBV_ACCESS_LOCAL_WRITE |
    IBV_ACCESS_REMOTE_WRITE |
    IBV_ACCESS_REMOTE_READ);
if (!mr) {
    fprintf(stderr, "Failed to register MR: %s\n", strerror(errno));
    free(buf);
    return -1;
}

printf("MR registered: lkey=0x%x, rkey=0x%x\n", mr->lkey, mr->rkey);
```

**Common Pitfalls:**

1. Forgetting IBV_ACCESS_LOCAL_WRITE for receive buffers causes silent failures.
2. Not page-aligning buffers reduces performance.
3. Registering memory without first increasing ulimit for locked memory (`ulimit -l unlimited`).
4. Re-registering the same memory repeatedly instead of registering once and reusing.

**Key errno values:**

| errno | Description |
|-------|-------------|
| ENOMEM | Insufficient resources (check ulimit -l) |
| EINVAL | Invalid access flags or parameters |
| EFAULT | Invalid memory address |

### 4.2 ibv_dereg_mr - Deregister Memory Region

```c
int ibv_dereg_mr(struct ibv_mr *mr);
```

Deregisters a memory region. The MR must not be in use by any active WR on any QP. After deregistration, the lkey and rkey are no longer valid and the memory is unpinned.

**Return Value:** 0 on success, errno on failure.

**Common Pitfall:** Deregistering an MR while WRs referencing it are still pending on a QP causes undefined behavior. Always ensure all WRs complete before deregistering.

---

## 5. Completion Queues

### 5.1 ibv_create_comp_channel - Create Completion Channel

```c
struct ibv_comp_channel *ibv_create_comp_channel(struct ibv_context *context);
```

Creates a completion event channel for event-driven CQ notification. The channel provides a file descriptor that can be used with `poll()`, `select()`, or `epoll()` for integration with event loops.

**Example:**

```c
struct ibv_comp_channel *comp_chan = ibv_create_comp_channel(ctx);
if (!comp_chan) {
    fprintf(stderr, "Failed to create completion channel: %s\n",
            strerror(errno));
    return -1;
}
/* comp_chan->fd can be used with poll/epoll */
```

### 5.2 ibv_create_cq - Create Completion Queue

```c
struct ibv_cq *ibv_create_cq(struct ibv_context *context, int cqe,
                              void *cq_context,
                              struct ibv_comp_channel *channel,
                              int comp_vector);
```

Creates a Completion Queue. CQs receive work completions indicating that posted WRs have completed (successfully or with error).

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| context | struct ibv_context* | Device context |
| cqe | int | Minimum number of CQ entries (actual may be larger) |
| cq_context | void* | User-defined context returned in events |
| channel | struct ibv_comp_channel* | Completion channel for notifications (can be NULL) |
| comp_vector | int | Completion vector for interrupt affinity (0 to num_comp_vectors-1) |

**Return Value:** `ibv_cq*` on success, NULL on failure.

**Example:**

```c
/* Create CQ with 256 entries, no event channel (polling mode) */
struct ibv_cq *cq = ibv_create_cq(ctx, 256, NULL, NULL, 0);
if (!cq) {
    fprintf(stderr, "Failed to create CQ: %s\n", strerror(errno));
    return -1;
}

/* Create CQ with event notification */
struct ibv_cq *event_cq = ibv_create_cq(ctx, 256, NULL, comp_chan, 0);
if (!event_cq) {
    fprintf(stderr, "Failed to create event CQ: %s\n", strerror(errno));
    return -1;
}
```

**Sizing Considerations:**

- For a QP with send and receive WRs, you need enough CQ entries for all outstanding WRs.
- If send and receive share a CQ: cqe >= send_wr + recv_wr.
- The actual CQ size may be rounded up to the next power of 2 by the driver.
- Overflowing a CQ (posting more WRs than CQ entries) causes a CQ overrun error which is fatal.

### 5.3 ibv_poll_cq - Poll Completion Queue

```c
int ibv_poll_cq(struct ibv_cq *cq, int num_entries, struct ibv_wc *wc);
```

Polls for completions on a CQ. This is a non-blocking call that returns immediately with zero or more completions.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| cq | struct ibv_cq* | CQ to poll |
| num_entries | int | Max number of completions to return |
| wc | struct ibv_wc* | Array of work completions to fill |

**Return Value:** Number of completions found (0 to num_entries), or negative value on failure.

**ibv_wc (Work Completion) fields:**

| Field | Type | Description |
|-------|------|-------------|
| wr_id | uint64_t | User-defined ID from the posted WR |
| status | enum ibv_wc_status | Completion status |
| opcode | enum ibv_wc_opcode | Type of completed operation |
| byte_len | uint32_t | Number of bytes transferred (receive only) |
| qp_num | uint32_t | QP number that completed |
| src_qp | uint32_t | Source QP number (UD only) |
| imm_data | __be32 | Immediate data (network byte order) |
| wc_flags | unsigned int | Completion flags |
| pkey_index | uint16_t | P_Key index (valid for GSI QPs) |
| slid | uint16_t | Source LID (IB only) |
| sl | uint8_t | Service Level |

**Completion Status Codes:**

| Status | Value | Description |
|--------|-------|-------------|
| IBV_WC_SUCCESS | 0 | Operation completed successfully |
| IBV_WC_LOC_LEN_ERR | 1 | Local length error |
| IBV_WC_LOC_QP_OP_ERR | 2 | Local QP operation error |
| IBV_WC_LOC_EEC_OP_ERR | 3 | Local EE context operation error |
| IBV_WC_LOC_PROT_ERR | 4 | Local protection error (wrong lkey/rkey) |
| IBV_WC_WR_FLUSH_ERR | 5 | WR flushed (QP in error state) |
| IBV_WC_MW_BIND_ERR | 6 | Memory window bind error |
| IBV_WC_BAD_RESP_ERR | 7 | Bad response error |
| IBV_WC_LOC_ACCESS_ERR | 8 | Local access error |
| IBV_WC_REM_INV_REQ_ERR | 9 | Remote invalid request error |
| IBV_WC_REM_ACCESS_ERR | 10 | Remote access error (bad rkey/permissions) |
| IBV_WC_REM_OP_ERR | 11 | Remote operation error |
| IBV_WC_RETRY_EXC_ERR | 12 | Retry counter exceeded (connectivity issue) |
| IBV_WC_RNR_RETRY_EXC_ERR | 13 | RNR retry counter exceeded (no recv posted) |
| IBV_WC_LOC_RDD_VIOL_ERR | 14 | Local RDD violation error |
| IBV_WC_REM_INV_RD_REQ_ERR | 15 | Remote invalid RD request |
| IBV_WC_REM_ABORT_ERR | 16 | Remote aborted error |
| IBV_WC_INV_EECN_ERR | 17 | Invalid EE context number |
| IBV_WC_INV_EEC_STATE_ERR | 18 | Invalid EE context state |
| IBV_WC_FATAL_ERR | 19 | Fatal error |
| IBV_WC_RESP_TIMEOUT_ERR | 20 | Response timeout error |
| IBV_WC_GENERAL_ERR | 21 | General error |

**Polling Patterns:**

```c
/* Pattern 1: Simple busy-polling */
struct ibv_wc wc;
int completions;
do {
    completions = ibv_poll_cq(cq, 1, &wc);
} while (completions == 0);

if (completions < 0) {
    fprintf(stderr, "Poll CQ failed\n");
    return -1;
}

if (wc.status != IBV_WC_SUCCESS) {
    fprintf(stderr, "Work completion error: %s (%d)\n",
            ibv_wc_status_str(wc.status), wc.status);
    return -1;
}

/* Pattern 2: Batch polling */
#define MAX_POLL_CQ 16
struct ibv_wc wc_array[MAX_POLL_CQ];
int total = 0;
int ne;

do {
    ne = ibv_poll_cq(cq, MAX_POLL_CQ, wc_array);
    if (ne < 0) {
        fprintf(stderr, "Poll CQ failed\n");
        break;
    }
    for (int i = 0; i < ne; i++) {
        if (wc_array[i].status != IBV_WC_SUCCESS) {
            fprintf(stderr, "WC error on wr_id %lu: %s\n",
                    wc_array[i].wr_id,
                    ibv_wc_status_str(wc_array[i].status));
        }
        total++;
    }
} while (total < expected_completions);
```

### 5.4 ibv_req_notify_cq - Request CQ Notification

```c
int ibv_req_notify_cq(struct ibv_cq *cq, int solicited_only);
```

Arms the CQ for event notification. After calling this, the next completion added to the CQ will trigger a notification on the associated completion channel.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| cq | struct ibv_cq* | CQ to arm |
| solicited_only | int | 0 = notify on any completion; 1 = only solicited completions |

**Return Value:** 0 on success, non-zero on failure.

**Event-Driven Completion Pattern:**

```c
/* Step 1: Arm CQ for notification */
ibv_req_notify_cq(cq, 0);

/* Step 2: Wait for event */
struct ibv_cq *ev_cq;
void *ev_ctx;
int ret = ibv_get_cq_event(comp_chan, &ev_cq, &ev_ctx);
if (ret) {
    fprintf(stderr, "Failed to get CQ event\n");
    return -1;
}

/* Step 3: Acknowledge the event */
ibv_ack_cq_events(ev_cq, 1);

/* Step 4: Re-arm CQ BEFORE polling to avoid race */
ibv_req_notify_cq(ev_cq, 0);

/* Step 5: Poll all completions */
struct ibv_wc wc;
while (ibv_poll_cq(ev_cq, 1, &wc) > 0) {
    /* Process completion */
    if (wc.status != IBV_WC_SUCCESS) {
        fprintf(stderr, "Error: %s\n", ibv_wc_status_str(wc.status));
    }
}
```

**Critical Ordering Note:** You MUST re-arm the CQ (step 4) BEFORE polling (step 5) to avoid missing completions that arrive between polling and re-arming. Completions that arrive after arming but before polling will be caught by the poll.

### 5.5 ibv_destroy_cq

```c
int ibv_destroy_cq(struct ibv_cq *cq);
```

Destroys a CQ. The CQ must not be associated with any QP. All CQ events must be acknowledged before destruction.

---

## 6. Queue Pairs

### 6.1 ibv_create_qp - Create Queue Pair

```c
struct ibv_qp *ibv_create_qp(struct ibv_pd *pd,
                              struct ibv_qp_init_attr *qp_init_attr);
```

Creates a Queue Pair. A QP consists of a Send Queue (SQ) and a Receive Queue (RQ), each associated with a CQ.

**ibv_qp_init_attr fields:**

| Field | Type | Description |
|-------|------|-------------|
| qp_context | void* | User-defined context |
| send_cq | struct ibv_cq* | CQ for send completions |
| recv_cq | struct ibv_cq* | CQ for receive completions |
| srq | struct ibv_srq* | Shared Receive Queue (NULL if not used) |
| cap.max_send_wr | uint32_t | Max outstanding send WRs |
| cap.max_recv_wr | uint32_t | Max outstanding receive WRs |
| cap.max_send_sge | uint32_t | Max scatter/gather entries per send WR |
| cap.max_recv_sge | uint32_t | Max scatter/gather entries per recv WR |
| cap.max_inline_data | uint32_t | Max inline data size in bytes |
| qp_type | enum ibv_qp_type | QP transport type |
| sq_sig_all | int | If 1, all send WRs generate completions |

**QP Types:**

| Type | Description |
|------|-------------|
| IBV_QPT_RC | Reliable Connected - guaranteed delivery, in-order |
| IBV_QPT_UC | Unreliable Connected - no ack/retry, in-order |
| IBV_QPT_UD | Unreliable Datagram - connectionless, out-of-order |
| IBV_QPT_RAW_PACKET | Raw Ethernet packet QP |
| IBV_QPT_XRC_SEND | Extended Reliable Connected - send side |
| IBV_QPT_XRC_RECV | Extended Reliable Connected - receive side |

**Example - RC QP creation:**

```c
struct ibv_qp_init_attr qp_init_attr = {
    .send_cq = cq,
    .recv_cq = cq,       /* Can use same CQ for send and receive */
    .srq = NULL,          /* No shared receive queue */
    .cap = {
        .max_send_wr = 128,
        .max_recv_wr = 128,
        .max_send_sge = 1,
        .max_recv_sge = 1,
        .max_inline_data = 64,
    },
    .qp_type = IBV_QPT_RC,
    .sq_sig_all = 0,      /* Selective signaling */
};

struct ibv_qp *qp = ibv_create_qp(pd, &qp_init_attr);
if (!qp) {
    fprintf(stderr, "Failed to create QP: %s\n", strerror(errno));
    return -1;
}

printf("QP created: qp_num=0x%x\n", qp->qp_num);

/* qp_init_attr.cap now contains the actual capabilities granted */
printf("Actual max_send_wr: %d\n", qp_init_attr.cap.max_send_wr);
printf("Actual max_recv_wr: %d\n", qp_init_attr.cap.max_recv_wr);
printf("Actual max_inline_data: %d\n", qp_init_attr.cap.max_inline_data);
```

**Inline Data:** Setting max_inline_data allows small messages to be sent without referencing an MR. The data is copied directly into the WQE (Work Queue Element) in the send queue. This avoids a PCIe read by the NIC and can improve latency. Typical optimal inline sizes are 64-256 bytes.

### 6.2 ibv_modify_qp - Modify Queue Pair State

```c
int ibv_modify_qp(struct ibv_qp *qp, struct ibv_qp_attr *attr,
                  int attr_mask);
```

Modifies QP attributes, primarily used to transition the QP through its state machine. A QP must be transitioned through specific states before it can send or receive data.

**QP State Machine:**

```
RESET --> INIT --> RTR --> RTS --> SQD --> RTS
  |         |       |       |       |
  +----<----+---<---+---<---+---<---+-- (Error) --> RESET
```

**States:**

| State | Description |
|-------|-------------|
| RESET | Initial state after creation |
| INIT | Basic configuration set, can post receives |
| RTR | Ready to Receive - can receive but not send |
| RTS | Ready to Send - fully operational |
| SQD | Send Queue Drained - for graceful QP modification |
| SQE | Send Queue Error |
| ERR | Error state |

#### 6.2.1 RESET to INIT Transition

```c
struct ibv_qp_attr attr = {
    .qp_state = IBV_QPS_INIT,
    .pkey_index = 0,
    .port_num = 1,            /* Physical port number (1-based) */
    .qp_access_flags = IBV_ACCESS_LOCAL_WRITE |
                        IBV_ACCESS_REMOTE_READ |
                        IBV_ACCESS_REMOTE_WRITE,
};

int flags = IBV_QP_STATE | IBV_QP_PKEY_INDEX |
            IBV_QP_PORT | IBV_QP_ACCESS_FLAGS;

int ret = ibv_modify_qp(qp, &attr, flags);
if (ret) {
    fprintf(stderr, "Failed to modify QP to INIT: %s\n", strerror(ret));
    return -1;
}
```

**After INIT:** You can (and should) post receive WRs before transitioning to RTR.

#### 6.2.2 INIT to RTR Transition

This is where you configure the connection to the remote QP.

```c
struct ibv_qp_attr attr = {
    .qp_state = IBV_QPS_RTR,
    .path_mtu = IBV_MTU_4096,       /* Or IBV_MTU_1024, IBV_MTU_2048 */
    .dest_qp_num = remote_qpn,       /* Remote QP number */
    .rq_psn = remote_psn,            /* Remote Packet Sequence Number */
    .max_dest_rd_atomic = 16,         /* Max outstanding RDMA Read/Atomic as responder */
    .min_rnr_timer = 12,             /* Min RNR NAK timer (12 = ~0.01ms) */
    .ah_attr = {
        .is_global = 0,              /* 1 for RoCE or cross-subnet IB */
        .dlid = remote_lid,          /* Remote LID (IB only) */
        .sl = 0,                     /* Service Level */
        .src_path_bits = 0,
        .port_num = 1,
    },
};

/* For RoCE or GRH (Global Routing Header): */
attr.ah_attr.is_global = 1;
attr.ah_attr.grh.dgid = remote_gid;       /* Remote GID */
attr.ah_attr.grh.sgid_index = gid_index;  /* Local GID index */
attr.ah_attr.grh.flow_label = 0;
attr.ah_attr.grh.hop_limit = 64;
attr.ah_attr.grh.traffic_class = 0;

int flags = IBV_QP_STATE | IBV_QP_AV | IBV_QP_PATH_MTU |
            IBV_QP_DEST_QPN | IBV_QP_RQ_PSN |
            IBV_QP_MAX_DEST_RD_ATOMIC | IBV_QP_MIN_RNR_TIMER;

int ret = ibv_modify_qp(qp, &attr, flags);
if (ret) {
    fprintf(stderr, "Failed to modify QP to RTR: %s\n", strerror(ret));
    return -1;
}
```

**MTU Values:**

| Enum | Bytes |
|------|-------|
| IBV_MTU_256 | 256 |
| IBV_MTU_512 | 512 |
| IBV_MTU_1024 | 1024 |
| IBV_MTU_2048 | 2048 |
| IBV_MTU_4096 | 4096 |

**min_rnr_timer values (selected):**

| Value | Timeout |
|-------|---------|
| 0 | 655.36 ms |
| 1 | 0.01 ms |
| 12 | 0.01 ms |
| 14 | 2.56 ms |
| 20 | 40.96 ms |
| 31 | 491.52 ms |

#### 6.2.3 RTR to RTS Transition

```c
struct ibv_qp_attr attr = {
    .qp_state = IBV_QPS_RTS,
    .timeout = 14,              /* Local ACK timeout = 4.096us * 2^14 ~= 67ms */
    .retry_cnt = 7,             /* Retry count (max 7) */
    .rnr_retry = 7,             /* RNR retry count (7 = infinite) */
    .sq_psn = local_psn,        /* Local Packet Sequence Number */
    .max_rd_atomic = 16,        /* Max outstanding RDMA Read/Atomic as initiator */
};

int flags = IBV_QP_STATE | IBV_QP_TIMEOUT | IBV_QP_RETRY_CNT |
            IBV_QP_RNR_RETRY | IBV_QP_SQ_PSN | IBV_QP_MAX_QP_RD_ATOM;

int ret = ibv_modify_qp(qp, &attr, flags);
if (ret) {
    fprintf(stderr, "Failed to modify QP to RTS: %s\n", strerror(ret));
    return -1;
}
```

**Timeout Formula:** The local ACK timeout is `4.096 us * 2^timeout`. A value of 0 means infinite timeout (no retransmission).

| timeout | Actual Timeout |
|---------|---------------|
| 0 | Infinite |
| 8 | ~1 ms |
| 14 | ~67 ms |
| 17 | ~536 ms |
| 20 | ~4.3 s |
| 31 | ~8796 s |

**retry_cnt:** Number of times the sender retransmits a packet before reporting an error. Maximum value is 7.

**rnr_retry:** Number of times to retry when receiving an RNR NAK (receiver has no posted receive buffer). Value 7 means infinite retries.

#### 6.2.4 Complete QP State Transition Helper

```c
int modify_qp_to_init(struct ibv_qp *qp, int port) {
    struct ibv_qp_attr attr = {
        .qp_state = IBV_QPS_INIT,
        .pkey_index = 0,
        .port_num = port,
        .qp_access_flags = IBV_ACCESS_LOCAL_WRITE |
                            IBV_ACCESS_REMOTE_READ |
                            IBV_ACCESS_REMOTE_WRITE |
                            IBV_ACCESS_REMOTE_ATOMIC,
    };
    return ibv_modify_qp(qp, &attr,
        IBV_QP_STATE | IBV_QP_PKEY_INDEX |
        IBV_QP_PORT | IBV_QP_ACCESS_FLAGS);
}

int modify_qp_to_rtr(struct ibv_qp *qp, uint32_t remote_qpn,
                      uint16_t remote_lid, union ibv_gid *remote_gid,
                      uint32_t remote_psn, int port, int gid_idx) {
    struct ibv_qp_attr attr = {
        .qp_state = IBV_QPS_RTR,
        .path_mtu = IBV_MTU_4096,
        .dest_qp_num = remote_qpn,
        .rq_psn = remote_psn,
        .max_dest_rd_atomic = 16,
        .min_rnr_timer = 12,
        .ah_attr = {
            .dlid = remote_lid,
            .sl = 0,
            .src_path_bits = 0,
            .port_num = port,
        },
    };

    if (remote_gid) {
        attr.ah_attr.is_global = 1;
        attr.ah_attr.grh.dgid = *remote_gid;
        attr.ah_attr.grh.sgid_index = gid_idx;
        attr.ah_attr.grh.flow_label = 0;
        attr.ah_attr.grh.hop_limit = 64;
        attr.ah_attr.grh.traffic_class = 0;
    }

    return ibv_modify_qp(qp, &attr,
        IBV_QP_STATE | IBV_QP_AV | IBV_QP_PATH_MTU |
        IBV_QP_DEST_QPN | IBV_QP_RQ_PSN |
        IBV_QP_MAX_DEST_RD_ATOMIC | IBV_QP_MIN_RNR_TIMER);
}

int modify_qp_to_rts(struct ibv_qp *qp, uint32_t local_psn) {
    struct ibv_qp_attr attr = {
        .qp_state = IBV_QPS_RTS,
        .timeout = 14,
        .retry_cnt = 7,
        .rnr_retry = 7,
        .sq_psn = local_psn,
        .max_rd_atomic = 16,
    };
    return ibv_modify_qp(qp, &attr,
        IBV_QP_STATE | IBV_QP_TIMEOUT | IBV_QP_RETRY_CNT |
        IBV_QP_RNR_RETRY | IBV_QP_SQ_PSN | IBV_QP_MAX_QP_RD_ATOM);
}
```

### 6.3 ibv_query_qp - Query QP Attributes

```c
int ibv_query_qp(struct ibv_qp *qp, struct ibv_qp_attr *attr,
                 int attr_mask, struct ibv_qp_init_attr *init_attr);
```

Queries current QP attributes. Useful for debugging QP state issues.

```c
struct ibv_qp_attr attr;
struct ibv_qp_init_attr init_attr;
ibv_query_qp(qp, &attr, IBV_QP_STATE | IBV_QP_CUR_STATE, &init_attr);
printf("QP state: %d\n", attr.qp_state);
```

### 6.4 ibv_destroy_qp

```c
int ibv_destroy_qp(struct ibv_qp *qp);
```

Destroys a QP. Outstanding WRs will be flushed with IBV_WC_WR_FLUSH_ERR status. The QP must be removed from any multicast groups first.

---

## 7. Posting Work Requests

### 7.1 ibv_post_send - Post Send Work Request

```c
int ibv_post_send(struct ibv_qp *qp, struct ibv_send_wr *wr,
                  struct ibv_send_wr **bad_wr);
```

Posts one or more send WRs to the send queue. WRs are chained via the `next` pointer. The QP must be in RTS state.

**ibv_send_wr fields:**

| Field | Type | Description |
|-------|------|-------------|
| wr_id | uint64_t | User-defined ID returned in completion |
| next | struct ibv_send_wr* | Next WR in chain (NULL for last) |
| sg_list | struct ibv_sge* | Scatter/Gather list |
| num_sge | int | Number of SGEs |
| opcode | enum ibv_wr_opcode | Operation type |
| send_flags | unsigned int | Send flags |
| imm_data | __be32 | Immediate data (for SEND_WITH_IMM/RDMA_WRITE_WITH_IMM) |
| wr.rdma.remote_addr | uint64_t | Remote virtual address (for RDMA) |
| wr.rdma.rkey | uint32_t | Remote memory key (for RDMA) |
| wr.atomic.remote_addr | uint64_t | Remote address (for atomics) |
| wr.atomic.rkey | uint32_t | Remote key (for atomics) |
| wr.atomic.compare_add | uint64_t | Compare value or add value |
| wr.atomic.swap | uint64_t | Swap value |

**Opcodes:**

| Opcode | QP Types | Description |
|--------|----------|-------------|
| IBV_WR_SEND | RC, UC, UD | Send data to remote receive buffer |
| IBV_WR_SEND_WITH_IMM | RC, UC, UD | Send with 32-bit immediate data |
| IBV_WR_RDMA_WRITE | RC, UC | Write to remote memory (no remote CPU involvement) |
| IBV_WR_RDMA_WRITE_WITH_IMM | RC, UC | Write with immediate data (generates recv completion) |
| IBV_WR_RDMA_READ | RC | Read from remote memory |
| IBV_WR_ATOMIC_CMP_AND_SWP | RC | 64-bit compare and swap |
| IBV_WR_ATOMIC_FETCH_AND_ADD | RC | 64-bit fetch and add |
| IBV_WR_SEND_WITH_INV | RC | Send with invalidation of remote MR key |
| IBV_WR_LOCAL_INV | RC | Local invalidation of MR key |
| IBV_WR_BIND_MW | RC, UC | Bind memory window |

**Send Flags:**

| Flag | Description |
|------|-------------|
| IBV_SEND_FENCE | Wait for previous RDMA Read/Atomic to complete |
| IBV_SEND_SIGNALED | Generate completion for this WR |
| IBV_SEND_SOLICITED | Set solicited bit (triggers solicited notification) |
| IBV_SEND_INLINE | Send data inline (copy data to WQE, no MR needed) |
| IBV_SEND_IP_CSUM | Offload IP checksum calculation |

**ibv_sge (Scatter/Gather Element):**

| Field | Type | Description |
|-------|------|-------------|
| addr | uint64_t | Virtual address of data |
| length | uint32_t | Length of data |
| lkey | uint32_t | Local key from ibv_reg_mr |

#### 7.1.1 SEND Operation Example

```c
/* Prepare scatter/gather entry */
struct ibv_sge sge = {
    .addr = (uintptr_t)mr->addr,
    .length = message_size,
    .lkey = mr->lkey,
};

/* Prepare send work request */
struct ibv_send_wr wr = {
    .wr_id = 1,
    .next = NULL,
    .sg_list = &sge,
    .num_sge = 1,
    .opcode = IBV_WR_SEND,
    .send_flags = IBV_SEND_SIGNALED,
};

struct ibv_send_wr *bad_wr;
int ret = ibv_post_send(qp, &wr, &bad_wr);
if (ret) {
    fprintf(stderr, "ibv_post_send failed: %s\n", strerror(ret));
    return -1;
}
```

#### 7.1.2 RDMA Write Example

```c
struct ibv_sge sge = {
    .addr = (uintptr_t)local_mr->addr,
    .length = data_size,
    .lkey = local_mr->lkey,
};

struct ibv_send_wr wr = {
    .wr_id = 2,
    .next = NULL,
    .sg_list = &sge,
    .num_sge = 1,
    .opcode = IBV_WR_RDMA_WRITE,
    .send_flags = IBV_SEND_SIGNALED,
    .wr.rdma = {
        .remote_addr = remote_addr,  /* Remote virtual address */
        .rkey = remote_rkey,         /* Remote memory key */
    },
};

struct ibv_send_wr *bad_wr;
int ret = ibv_post_send(qp, &wr, &bad_wr);
```

#### 7.1.3 RDMA Read Example

```c
struct ibv_sge sge = {
    .addr = (uintptr_t)local_buffer,
    .length = read_size,
    .lkey = local_mr->lkey,
};

struct ibv_send_wr wr = {
    .wr_id = 3,
    .next = NULL,
    .sg_list = &sge,
    .num_sge = 1,
    .opcode = IBV_WR_RDMA_READ,
    .send_flags = IBV_SEND_SIGNALED,
    .wr.rdma = {
        .remote_addr = remote_addr,
        .rkey = remote_rkey,
    },
};

struct ibv_send_wr *bad_wr;
int ret = ibv_post_send(qp, &wr, &bad_wr);
```

#### 7.1.4 Atomic Compare and Swap Example

```c
/* Target must be 8-byte aligned */
struct ibv_sge sge = {
    .addr = (uintptr_t)local_buffer,  /* Result stored here */
    .length = 8,
    .lkey = local_mr->lkey,
};

struct ibv_send_wr wr = {
    .wr_id = 4,
    .next = NULL,
    .sg_list = &sge,
    .num_sge = 1,
    .opcode = IBV_WR_ATOMIC_CMP_AND_SWP,
    .send_flags = IBV_SEND_SIGNALED,
    .wr.atomic = {
        .remote_addr = remote_addr,    /* Must be 8-byte aligned */
        .rkey = remote_rkey,
        .compare_add = expected_value, /* Compare with this value */
        .swap = new_value,             /* Replace with this if equal */
    },
};

struct ibv_send_wr *bad_wr;
int ret = ibv_post_send(qp, &wr, &bad_wr);
```

#### 7.1.5 Inline Send Example

```c
char small_msg[] = "Hello RDMA!";
struct ibv_sge sge = {
    .addr = (uintptr_t)small_msg,
    .length = sizeof(small_msg),
    .lkey = 0,  /* lkey not needed for inline */
};

struct ibv_send_wr wr = {
    .wr_id = 5,
    .next = NULL,
    .sg_list = &sge,
    .num_sge = 1,
    .opcode = IBV_WR_SEND,
    .send_flags = IBV_SEND_SIGNALED | IBV_SEND_INLINE,
};

struct ibv_send_wr *bad_wr;
ibv_post_send(qp, &wr, &bad_wr);
```

**Important:** Inline data does not require memory registration. The data is copied into the WQE. The buffer can be reused immediately after ibv_post_send returns.

#### 7.1.6 Selective Signaling

When `sq_sig_all` is 0 in QP creation, you can choose which WRs generate completions:

```c
/* Post N-1 unsignaled WRs, then 1 signaled */
for (int i = 0; i < batch_size; i++) {
    struct ibv_send_wr wr = {
        .wr_id = i,
        .sg_list = &sge,
        .num_sge = 1,
        .opcode = IBV_WR_SEND,
        .send_flags = (i == batch_size - 1) ? IBV_SEND_SIGNALED : 0,
    };
    ibv_post_send(qp, &wr, &bad_wr);
}
/* Only one completion for the entire batch */
```

**Warning:** With selective signaling, you must still track send queue depth. The send queue holds all WRs (signaled and unsignaled) until the next signaled WR completes. Posting too many unsignaled WRs will overflow the send queue.

#### 7.1.7 UD QP Send (with Address Handle)

```c
struct ibv_sge sge = {
    .addr = (uintptr_t)(buf + 40), /* Leave 40-byte GRH space */
    .length = message_size,
    .lkey = mr->lkey,
};

struct ibv_send_wr wr = {
    .wr_id = 6,
    .sg_list = &sge,
    .num_sge = 1,
    .opcode = IBV_WR_SEND,
    .send_flags = IBV_SEND_SIGNALED,
    .wr.ud = {
        .ah = ah,                    /* Address Handle */
        .remote_qpn = remote_qpn,
        .remote_qkey = remote_qkey,
    },
};

struct ibv_send_wr *bad_wr;
ibv_post_send(qp, &wr, &bad_wr);
```

### 7.2 ibv_post_recv - Post Receive Work Request

```c
int ibv_post_recv(struct ibv_qp *qp, struct ibv_recv_wr *wr,
                  struct ibv_recv_wr **bad_wr);
```

Posts one or more receive WRs to the receive queue. The QP must be in at least INIT state. Receive WRs must be posted before the remote side sends data.

**ibv_recv_wr fields:**

| Field | Type | Description |
|-------|------|-------------|
| wr_id | uint64_t | User-defined ID |
| next | struct ibv_recv_wr* | Next WR in chain |
| sg_list | struct ibv_sge* | Scatter list for incoming data |
| num_sge | int | Number of SGEs |

**Example:**

```c
struct ibv_sge sge = {
    .addr = (uintptr_t)recv_buf,
    .length = buf_size,
    .lkey = recv_mr->lkey,
};

struct ibv_recv_wr wr = {
    .wr_id = 100,
    .next = NULL,
    .sg_list = &sge,
    .num_sge = 1,
};

struct ibv_recv_wr *bad_wr;
int ret = ibv_post_recv(qp, &wr, &bad_wr);
if (ret) {
    fprintf(stderr, "ibv_post_recv failed: %s\n", strerror(ret));
    return -1;
}
```

**Batch Posting Pattern:**

```c
#define NUM_RECV_WRS 64

struct ibv_sge sge[NUM_RECV_WRS];
struct ibv_recv_wr wr[NUM_RECV_WRS];

for (int i = 0; i < NUM_RECV_WRS; i++) {
    sge[i].addr = (uintptr_t)(recv_buf + i * buf_size);
    sge[i].length = buf_size;
    sge[i].lkey = recv_mr->lkey;

    wr[i].wr_id = i;
    wr[i].next = (i < NUM_RECV_WRS - 1) ? &wr[i + 1] : NULL;
    wr[i].sg_list = &sge[i];
    wr[i].num_sge = 1;
}

struct ibv_recv_wr *bad_wr;
int ret = ibv_post_recv(qp, &wr[0], &bad_wr);
if (ret) {
    fprintf(stderr, "Failed to post recv WRs, first bad: wr_id=%lu\n",
            bad_wr->wr_id);
}
```

**Common Pitfalls:**

1. The receive buffer must include IBV_ACCESS_LOCAL_WRITE in its MR access flags.
2. For UD QPs, the receive buffer must be at least message_size + 40 bytes (for the GRH).
3. Not posting enough receive WRs before the remote side sends causes RNR NAKs.
4. Each receive WR is consumed exactly once; you must repost after each completion.

---

## 8. Shared Receive Queues

### 8.1 ibv_create_srq - Create Shared Receive Queue

```c
struct ibv_srq *ibv_create_srq(struct ibv_pd *pd,
                                struct ibv_srq_init_attr *srq_init_attr);
```

Creates a Shared Receive Queue that can be shared among multiple QPs. SRQs are essential for scalability when managing many connections, as they allow a single pool of receive buffers instead of per-QP buffers.

**ibv_srq_init_attr fields:**

| Field | Type | Description |
|-------|------|-------------|
| srq_context | void* | User context |
| attr.max_wr | uint32_t | Max outstanding WRs in SRQ |
| attr.max_sge | uint32_t | Max SGEs per WR |
| attr.srq_limit | uint32_t | Low watermark for SRQ event (0 = disabled) |

**Example:**

```c
struct ibv_srq_init_attr srq_init_attr = {
    .attr = {
        .max_wr = 1024,
        .max_sge = 1,
        .srq_limit = 100,  /* Generate event when WRs drop below 100 */
    },
};

struct ibv_srq *srq = ibv_create_srq(pd, &srq_init_attr);
if (!srq) {
    fprintf(stderr, "Failed to create SRQ: %s\n", strerror(errno));
    return -1;
}

/* Create QP using SRQ */
struct ibv_qp_init_attr qp_attr = {
    .send_cq = cq,
    .recv_cq = cq,
    .srq = srq,    /* Attach SRQ */
    .cap = {
        .max_send_wr = 128,
        .max_recv_wr = 0,   /* Receive WRs come from SRQ */
        .max_send_sge = 1,
        .max_recv_sge = 0,
    },
    .qp_type = IBV_QPT_RC,
};
```

### 8.2 ibv_post_srq_recv - Post Receive to SRQ

```c
int ibv_post_srq_recv(struct ibv_srq *srq, struct ibv_recv_wr *recv_wr,
                      struct ibv_recv_wr **bad_recv_wr);
```

Posts receive WRs to the SRQ instead of individual QPs.

```c
struct ibv_sge sge = {
    .addr = (uintptr_t)buf,
    .length = buf_size,
    .lkey = mr->lkey,
};

struct ibv_recv_wr wr = {
    .wr_id = (uint64_t)(uintptr_t)buf,  /* Use buffer address as wr_id */
    .sg_list = &sge,
    .num_sge = 1,
};

struct ibv_recv_wr *bad_wr;
ibv_post_srq_recv(srq, &wr, &bad_wr);
```

### 8.3 ibv_modify_srq - Modify SRQ (Set Limit)

```c
struct ibv_srq_attr srq_attr = {
    .srq_limit = 50,  /* New low watermark */
};
ibv_modify_srq(srq, &srq_attr, IBV_SRQ_LIMIT);
```

### 8.4 ibv_destroy_srq

```c
int ibv_destroy_srq(struct ibv_srq *srq);
```

Destroys the SRQ. All QPs using this SRQ must be destroyed first.

---

## 9. Address Handles (UD QPs)

### 9.1 ibv_create_ah - Create Address Handle

```c
struct ibv_ah *ibv_create_ah(struct ibv_pd *pd,
                              struct ibv_ah_attr *attr);
```

Creates an Address Handle for use with UD (Unreliable Datagram) QPs. AHs describe the path to a remote destination.

**ibv_ah_attr fields:**

| Field | Type | Description |
|-------|------|-------------|
| dlid | uint16_t | Destination LID (IB) |
| sl | uint8_t | Service Level |
| src_path_bits | uint8_t | Source path bits (for LMC) |
| port_num | uint8_t | Local port number |
| is_global | uint8_t | Use GRH (required for RoCE) |
| grh.dgid | union ibv_gid | Destination GID |
| grh.sgid_index | uint8_t | Source GID index |
| grh.flow_label | uint32_t | Flow label |
| grh.hop_limit | uint8_t | Hop limit (TTL) |
| grh.traffic_class | uint8_t | Traffic class |

**Example for InfiniBand:**

```c
struct ibv_ah_attr ah_attr = {
    .dlid = remote_lid,
    .sl = 0,
    .src_path_bits = 0,
    .port_num = 1,
    .is_global = 0,
};

struct ibv_ah *ah = ibv_create_ah(pd, &ah_attr);
if (!ah) {
    fprintf(stderr, "Failed to create AH: %s\n", strerror(errno));
    return -1;
}
```

**Example for RoCE:**

```c
struct ibv_ah_attr ah_attr = {
    .sl = 0,
    .port_num = 1,
    .is_global = 1,
    .grh = {
        .dgid = remote_gid,
        .sgid_index = gid_index,
        .flow_label = 0,
        .hop_limit = 64,
        .traffic_class = 0,
    },
};

struct ibv_ah *ah = ibv_create_ah(pd, &ah_attr);
```

### 9.2 ibv_destroy_ah

```c
int ibv_destroy_ah(struct ibv_ah *ah);
```

---

## 10. Extended Verbs (ibv_create_cq_ex, ibv_create_qp_ex)

### 10.1 ibv_create_cq_ex - Extended CQ Creation

```c
struct ibv_cq_ex *ibv_create_cq_ex(struct ibv_context *context,
                                    struct ibv_cq_init_attr_ex *cq_attr);
```

The extended CQ provides additional capabilities including timestamps, completion flags, and more efficient polling through a "next" iterator model.

```c
struct ibv_cq_init_attr_ex cq_attr_ex = {
    .cqe = 256,
    .cq_context = NULL,
    .channel = comp_chan,
    .comp_vector = 0,
    .wc_flags = IBV_WC_EX_WITH_BYTE_LEN |
                IBV_WC_EX_WITH_COMPLETION_TIMESTAMP,
};

struct ibv_cq_ex *cq_ex = ibv_create_cq_ex(ctx, &cq_attr_ex);
```

**Extended CQ Polling:**

```c
struct ibv_poll_cq_attr poll_attr = {};
int ret = ibv_start_poll(cq_ex, &poll_attr);
if (ret == ENOENT) {
    /* No completions available */
    return 0;
}

do {
    uint64_t wr_id = cq_ex->wr_id;
    int status = cq_ex->status;
    uint32_t byte_len = ibv_wc_read_byte_len(cq_ex);
    uint64_t timestamp = ibv_wc_read_completion_ts(cq_ex);
    /* Process completion */
} while (ibv_next_poll(cq_ex) == 0);

ibv_end_poll(cq_ex);
```

---

## 11. Common Programming Patterns

### 11.1 Complete RC Client-Server Setup

```c
/* ===== Common Resource Setup ===== */
struct rdma_resources {
    struct ibv_context      *ctx;
    struct ibv_pd           *pd;
    struct ibv_mr           *mr;
    struct ibv_cq           *cq;
    struct ibv_qp           *qp;
    struct ibv_comp_channel *comp_chan;
    void                    *buf;
    size_t                   buf_size;
    struct ibv_port_attr     port_attr;
    union ibv_gid            gid;
};

int setup_resources(struct rdma_resources *res, const char *dev_name) {
    int num_devices;
    struct ibv_device **dev_list = ibv_get_device_list(&num_devices);
    if (!dev_list) return -1;

    /* Find requested device */
    struct ibv_device *ib_dev = NULL;
    for (int i = 0; i < num_devices; i++) {
        if (!strcmp(ibv_get_device_name(dev_list[i]), dev_name)) {
            ib_dev = dev_list[i];
            break;
        }
    }
    if (!ib_dev) {
        ibv_free_device_list(dev_list);
        return -1;
    }

    res->ctx = ibv_open_device(ib_dev);
    ibv_free_device_list(dev_list);
    if (!res->ctx) return -1;

    ibv_query_port(res->ctx, 1, &res->port_attr);
    ibv_query_gid(res->ctx, 1, 0, &res->gid);

    res->pd = ibv_alloc_pd(res->ctx);
    if (!res->pd) return -1;

    res->buf_size = 4096;
    res->buf = malloc(res->buf_size);
    memset(res->buf, 0, res->buf_size);

    res->mr = ibv_reg_mr(res->pd, res->buf, res->buf_size,
        IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_READ |
        IBV_ACCESS_REMOTE_WRITE);
    if (!res->mr) return -1;

    res->cq = ibv_create_cq(res->ctx, 128, NULL, NULL, 0);
    if (!res->cq) return -1;

    struct ibv_qp_init_attr qp_attr = {
        .send_cq = res->cq,
        .recv_cq = res->cq,
        .cap = {
            .max_send_wr = 64,
            .max_recv_wr = 64,
            .max_send_sge = 1,
            .max_recv_sge = 1,
            .max_inline_data = 64,
        },
        .qp_type = IBV_QPT_RC,
    };

    res->qp = ibv_create_qp(res->pd, &qp_attr);
    if (!res->qp) return -1;

    return 0;
}

void cleanup_resources(struct rdma_resources *res) {
    if (res->qp)   ibv_destroy_qp(res->qp);
    if (res->cq)   ibv_destroy_cq(res->cq);
    if (res->mr)   ibv_dereg_mr(res->mr);
    if (res->pd)   ibv_dealloc_pd(res->pd);
    if (res->ctx)  ibv_close_device(res->ctx);
    if (res->buf)  free(res->buf);
}
```

### 11.2 Connection Exchange via TCP (Out-of-Band)

```c
struct conn_info {
    uint32_t qp_num;
    uint16_t lid;
    uint32_t psn;
    union ibv_gid gid;
    uint64_t addr;
    uint32_t rkey;
};

/* Exchange connection info via TCP socket */
int exchange_conn_info(int sock, struct conn_info *local,
                       struct conn_info *remote) {
    if (write(sock, local, sizeof(*local)) != sizeof(*local))
        return -1;
    if (read(sock, remote, sizeof(*remote)) != sizeof(*remote))
        return -1;
    return 0;
}
```

### 11.3 Cleanup Order

Resources must be destroyed in reverse order of creation:

```
1. Destroy QPs           (ibv_destroy_qp)
2. Destroy SRQs          (ibv_destroy_srq)
3. Destroy AHs           (ibv_destroy_ah)
4. Destroy CQs           (ibv_destroy_cq)
5. Destroy comp channels (ibv_destroy_comp_channel)
6. Deregister MRs        (ibv_dereg_mr)
7. Deallocate PDs        (ibv_dealloc_pd)
8. Close device          (ibv_close_device)
9. Free device list      (ibv_free_device_list)
```

---

## 12. Performance Best Practices

### 12.1 Polling vs Event-Driven

- **Busy polling** (`ibv_poll_cq` in a loop): Lowest latency, highest CPU usage. Best for latency-critical paths.
- **Event-driven** (`ibv_req_notify_cq` + `ibv_get_cq_event`): Lower CPU usage, higher latency due to interrupt overhead. Best for idle or low-throughput paths.
- **Hybrid**: Use polling for a time window, then switch to event-driven if no completions arrive.

### 12.2 Inline Data

Use inline sends for messages smaller than max_inline_data (typically 64-256 bytes). This eliminates the NIC's PCIe read of the data buffer.

### 12.3 Selective Signaling

Use unsignaled sends to reduce CQ processing overhead. Signal every Nth send WR. Keep track of send queue depth to avoid overflow.

### 12.4 Memory Registration

- Register memory once and reuse.
- Use huge pages for large registrations (reduces page table overhead).
- Consider On-Demand Paging (ODP) for dynamic workloads.
- Page-align all buffers.

### 12.5 Doorbell Batching

Post multiple WRs in a single `ibv_post_send` call (chain them via `next` pointer). This reduces doorbell writes to the NIC.

### 12.6 CQ Moderation

Some drivers support CQ moderation to coalesce completions and reduce interrupts:

```c
struct ibv_modify_cq_attr cq_mod = {
    .cq_count = 16,    /* Generate event after 16 completions */
    .cq_period = 100,  /* Or after 100 microseconds */
};
/* Note: CQ moderation is driver-specific */
```

---

## 13. Error Handling and Debugging

### 13.1 Async Events

```c
struct ibv_async_event event;
int ret = ibv_get_async_event(ctx, &event);
if (ret == 0) {
    switch (event.event_type) {
    case IBV_EVENT_CQ_ERR:
        fprintf(stderr, "CQ error\n");
        break;
    case IBV_EVENT_QP_FATAL:
        fprintf(stderr, "QP fatal error\n");
        break;
    case IBV_EVENT_QP_REQ_ERR:
        fprintf(stderr, "QP request error\n");
        break;
    case IBV_EVENT_QP_ACCESS_ERR:
        fprintf(stderr, "QP access error\n");
        break;
    case IBV_EVENT_PORT_ACTIVE:
        fprintf(stderr, "Port active\n");
        break;
    case IBV_EVENT_PORT_ERR:
        fprintf(stderr, "Port error\n");
        break;
    case IBV_EVENT_LID_CHANGE:
        fprintf(stderr, "LID change\n");
        break;
    case IBV_EVENT_SM_CHANGE:
        fprintf(stderr, "SM change\n");
        break;
    case IBV_EVENT_SRQ_LIMIT_REACHED:
        fprintf(stderr, "SRQ limit reached - post more WRs!\n");
        break;
    case IBV_EVENT_SRQ_ERR:
        fprintf(stderr, "SRQ error\n");
        break;
    default:
        fprintf(stderr, "Unknown event: %d\n", event.event_type);
    }
    ibv_ack_async_event(&event);
}
```

### 13.2 Debugging Tips

1. **IBV_WC_RETRY_EXC_ERR**: Usually indicates connectivity problems (wrong LID/GID, port down, wrong PSN). Verify:
   - Port state is ACTIVE on both sides.
   - LID/GID exchanged correctly.
   - MTU is consistent.
   - QP state transitions completed successfully.

2. **IBV_WC_RNR_RETRY_EXC_ERR**: Remote side has no posted receive buffers. Ensure:
   - Receive WRs are posted before the remote sends.
   - rnr_retry is set to 7 (infinite) during development.
   - SRQ has enough WRs.

3. **IBV_WC_REM_ACCESS_ERR**: Remote access violation. Check:
   - rkey is correct and current.
   - Remote MR has the required access flags.
   - Address is within the registered MR range.

4. **IBV_WC_LOC_PROT_ERR**: Local protection error. Check:
   - lkey is correct.
   - Buffer is within the registered MR range.
   - MR has IBV_ACCESS_LOCAL_WRITE for receive buffers.

5. **Enable debug output:**

```bash
# Verbose libibverbs debug
export LIBIBVERBS_DEBUG=1
export MLX5_DEBUG=1

# Check kernel logs
dmesg | grep -i "mlx\|rdma\|infiniband"
```

### 13.3 Common Error Patterns

```
Error: "Failed to register MR: Cannot allocate memory"
Fix: ulimit -l unlimited (or set in /etc/security/limits.conf)

Error: "Failed to modify QP to RTR: Invalid argument"
Fix: Check dest_qp_num, remote LID/GID, path_mtu compatibility

Error: "Failed to create QP: No space left on device"
Fix: Too many QPs created, check ibv_query_device max_qp

Error: "ibv_post_send: Invalid argument"
Fix: Check that QP is in RTS state, WR parameters valid
```

---

## 14. Thread Safety

The Verbs API has the following thread-safety guarantees:

- **ibv_post_send** and **ibv_post_recv**: Thread-safe for different QPs. Concurrent posts to the same QP require external synchronization.
- **ibv_poll_cq**: Thread-safe per CQ. Concurrent polling of the same CQ is safe but not recommended for performance.
- **Resource creation/destruction**: Thread-safe (serialized internally).
- **ibv_req_notify_cq** + **ibv_poll_cq**: Safe to call from different threads on the same CQ.

Best practice: Assign each thread its own set of QPs and CQs to avoid contention.
