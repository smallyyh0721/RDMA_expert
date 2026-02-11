---
title: "Common RDMA Error Codes Reference"
category: troubleshooting
tags: [rdma, errors, error_codes, debugging, wc_status]
---

# Common RDMA Error Codes Reference

## 1. Work Completion Status Codes (ibv_wc_status)

### IBV_WC_SUCCESS (0)
- **Description**: Operation completed successfully
- **Action**: Normal - process the completion

### IBV_WC_LOC_LEN_ERR (1) - Local Length Error
- **Description**: Receive buffer too small for incoming message
- **Root causes**:
  - Posted receive buffer is shorter than the incoming Send message
  - For UD: forgot to account for 40-byte GRH header
  - Scatter list total length < message size
- **Resolution**:
  - Increase receive buffer size
  - For UD: add 40 bytes to buffer for GRH
  - Check that all scatter entries are correctly sized

### IBV_WC_LOC_QP_OP_ERR (2) - Local QP Operation Error
- **Description**: Internal QP consistency error
- **Root causes**:
  - Posting a WR that violates QP configuration
  - WR opcode not valid for this QP type (e.g., RDMA Read on UC)
  - Too many scatter/gather entries
  - Invalid number of RDMA Read/Atomics outstanding
- **Resolution**:
  - Verify QP type supports the operation
  - Check max_send_sge, max_recv_sge limits
  - Check max_rd_atomic setting

### IBV_WC_LOC_PROT_ERR (4) - Local Protection Error
- **Description**: Local memory access violation
- **Root causes**:
  - Using wrong lkey in scatter/gather list
  - Buffer address outside registered MR range
  - MR doesn't have required access flags (e.g., LOCAL_WRITE for receive)
  - MR belongs to different PD than QP
- **Resolution**:
  - Verify lkey matches the MR that covers the buffer
  - Check MR address range covers the entire buffer
  - Ensure MR has IBV_ACCESS_LOCAL_WRITE for receive buffers
  - Verify QP and MR are in the same PD

### IBV_WC_WR_FLUSH_ERR (5) - Work Request Flushed
- **Description**: WR was in the queue when QP transitioned to Error state
- **Root causes**:
  - Previous error moved QP to ERR state
  - All subsequent WRs get flushed with this status
  - QP was reset while WRs were pending
- **Resolution**:
  - Find the root error (first non-SUCCESS CQE before the flush)
  - Drain all CQEs, then transition QP back: ERR → RESET → INIT → RTR → RTS
  - Re-post receives before transitioning to RTR

### IBV_WC_BAD_RESP_ERR (7) - Bad Response Error
- **Description**: Unexpected transport layer response
- **Root causes**:
  - Protocol error between endpoints
  - Corrupted response
  - Software bug in remote side
- **Resolution**:
  - Check remote side for errors
  - Verify both sides have matching QP configurations

### IBV_WC_REM_INV_REQ_ERR (9) - Remote Invalid Request
- **Description**: Remote side received an invalid request
- **Root causes**:
  - RDMA Write/Read to invalid remote address
  - Invalid rkey
  - Operation length exceeds remote MR
  - Atomics to non-aligned address
- **Resolution**:
  - Verify remote address + rkey are correct and current
  - Check that remote MR is still registered
  - Ensure atomic ops are 8-byte aligned

### IBV_WC_REM_ACCESS_ERR (10) - Remote Access Error
- **Description**: Remote side denied access
- **Root causes**:
  - Remote MR doesn't have REMOTE_WRITE flag for RDMA Write
  - Remote MR doesn't have REMOTE_READ flag for RDMA Read
  - Remote MR doesn't have REMOTE_ATOMIC flag for atomics
  - rkey doesn't match any valid MR on remote
- **Resolution**:
  - Register remote MR with appropriate access flags:
    - `IBV_ACCESS_REMOTE_WRITE` for RDMA Write targets
    - `IBV_ACCESS_REMOTE_READ` for RDMA Read targets
    - `IBV_ACCESS_REMOTE_ATOMIC` for atomic targets
  - Exchange fresh rkeys if MR was re-registered

### IBV_WC_REM_OP_ERR (11) - Remote Operation Error
- **Description**: Remote side encountered an error processing the request
- **Root causes**:
  - Remote QP in error state
  - Remote HCA internal error
  - Remote responder resource exhaustion
- **Resolution**:
  - Check remote QP state
  - Check remote dmesg for hardware errors

### IBV_WC_RETRY_EXC_ERR (12) - Retry Count Exceeded
- **Description**: Failed to get ACK after all retries (RC only)
- **Root causes**:
  - Remote side is unreachable (link down, process crashed)
  - Remote QP was destroyed or reset
  - Network path changed (after SM re-route)
  - Timeout too short for the network
  - Remote side too slow to respond
- **Resolution**:
  - Check remote side is alive and QP is in RTS
  - Increase retry_cnt (max 7) in QP attributes
  - Increase timeout value (exponential: 4.096μs × 2^timeout)
  - Check network connectivity: `ibping`, `ibtracert`

### IBV_WC_RNR_RETRY_EXC_ERR (13) - RNR Retry Exceeded
- **Description**: Remote has no receive buffers posted, retries exhausted
- **Root causes**:
  - Remote side not posting receive WRs fast enough
  - Remote side hasn't posted any receives
  - SRQ ran out of receives
  - Application too slow processing completions
- **Resolution**:
  - Ensure remote posts receive WRs before data arrives
  - Use SRQ with adequate depth
  - Increase rnr_retry count (7 = infinite retry)
  - Increase min_rnr_timer on remote QP
  - Profile remote application for CQ processing delays

### IBV_WC_FATAL_ERR (19) - Fatal Error
- **Description**: Unrecoverable hardware error
- **Root causes**:
  - Hardware malfunction
  - Firmware crash
  - Driver bug
- **Resolution**:
  - Check dmesg for hardware errors
  - Reset the HCA: `mlxfwreset`
  - Update firmware
  - Contact NVIDIA support

## 2. Asynchronous Events (ibv_event_type)

| Event | Description | Severity |
|-------|------------|----------|
| IBV_EVENT_CQ_ERR | CQ overrun | Critical |
| IBV_EVENT_QP_FATAL | QP fatal error | Critical |
| IBV_EVENT_QP_REQ_ERR | QP request error | Error |
| IBV_EVENT_QP_ACCESS_ERR | QP access error | Error |
| IBV_EVENT_COMM_EST | Communication established | Info |
| IBV_EVENT_SQ_DRAINED | SQ drained | Info |
| IBV_EVENT_PATH_MIG | Path migrated | Info |
| IBV_EVENT_PATH_MIG_ERR | Path migration error | Error |
| IBV_EVENT_DEVICE_FATAL | HCA fatal error | Critical |
| IBV_EVENT_PORT_ACTIVE | Port became active | Info |
| IBV_EVENT_PORT_ERR | Port went down | Error |
| IBV_EVENT_LID_CHANGE | LID changed (SM reconfiguration) | Info |
| IBV_EVENT_PKEY_CHANGE | PKey table changed | Info |
| IBV_EVENT_SM_CHANGE | SM changed | Info |
| IBV_EVENT_SRQ_ERR | SRQ error | Critical |
| IBV_EVENT_SRQ_LIMIT_REACHED | SRQ low watermark | Warning |
| IBV_EVENT_GID_CHANGE | GID table changed | Info |

### CQ Overrun (IBV_EVENT_CQ_ERR)
- CQ is full, new completions cannot be added
- **Fix**: Increase CQ size or poll more frequently
- Once overrun, CQ is unusable - must destroy and recreate

### QP Fatal (IBV_EVENT_QP_FATAL)
- Hardware error on QP - moved to ERR state automatically
- **Fix**: Drain completions, reset QP, reconnect

## 3. Common errno Values from Verbs Calls

| errno | Name | Common Cause |
|-------|------|-------------|
| ENOMEM | Out of memory | Too many MRs, QPs, or CQs; memlock limit |
| EINVAL | Invalid argument | Wrong parameter value |
| ENOSYS | Not supported | Operation not supported by device |
| EPERM | Permission denied | Missing capability (CAP_NET_RAW for raw QPs) |
| EBUSY | Resource busy | Trying to destroy resource with active references |
| EAGAIN | Try again | Temporary resource shortage |
| EFAULT | Bad address | Invalid user-space pointer |
| ENODEV | No such device | Device removed or not found |

### ENOMEM Troubleshooting
```bash
# Check memlock limit
ulimit -l
# Fix: set to unlimited in /etc/security/limits.conf

# Check system memory
cat /proc/meminfo | grep -E "MemFree|Locked|Huge"

# Check RDMA resource usage
rdma resource show
cat /sys/class/infiniband/mlx5_0/resource_tracker/*
```

## 4. Kernel dmesg Error Patterns

```bash
# Common mlx5 error messages and meanings:

# "mlx5_core: mlx5_cmd_comp_handler:191:(pid N): err(timeout)"
# → Firmware command timeout - may need firmware update or NIC reset

# "mlx5_core: mlx5_health_check_fatal_sensors:..."
# → Hardware health check failure - check temperature, power

# "mlx5_core: mlx5_pagealloc_stop:..."
# → Page allocation failure - system under memory pressure

# "mlx5_ib: mlx5_ib_post_send: bad opcode"
# → Application posting invalid operation type

# "mlx5_core: syndrome (0x...)"
# → Hardware syndrome code - decode with vendor documentation

# "roce: addr_handler: Could not find sgid entry"
# → GID table doesn't have entry for the IP address being used
# → Fix: Check IP configuration on RDMA interface

# Monitor in real-time
dmesg -w | grep -i mlx5
```

## 5. Debugging Methodology

### Step 1: Identify the error
```bash
# Poll CQ and check status
ibv_poll_cq(cq, 1, &wc);
if (wc.status != IBV_WC_SUCCESS) {
    printf("Error: %s (%d) on QP %u\n",
        ibv_wc_status_str(wc.status), wc.status, wc.qp_num);
}
```

### Step 2: Check QP state
```bash
# From application:
struct ibv_qp_attr attr;
struct ibv_qp_init_attr init_attr;
ibv_query_qp(qp, &attr, IBV_QP_STATE, &init_attr);
# attr.qp_state should be IBV_QPS_RTS for normal operation
```

### Step 3: Check system state
```bash
dmesg | tail -50          # Kernel messages
ibstat                     # Port state
rdma resource show         # Resource usage
cat /proc/interrupts | grep mlx5  # IRQ delivery
```

### Step 4: Check network
```bash
ibping -S                  # server (IB)
ibping -L <lid>           # client (IB)
# For RoCE: ping the IP, check ethtool -S for drops
```
