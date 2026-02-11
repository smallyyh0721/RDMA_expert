# RDMA Core Documentation

This document provides comprehensive documentation for RDMA core tools, libraries, and code analysis.

---

## Tools

### ibstat

**Description:** Query and display InfiniBand device and port status information

**Category:** Device Status

**Source File:** infiniband-diags/ibstat.c

#### Key Functions
- ca_dump
- port_dump
- ca_stat

#### Usage Examples
```bash
ibstat  # Show all devices and ports
ibstat -l  # List all IB devices only
ibstat -s  # Short format
ibstat -p  # Show port list with GUIDs
ibstat mlx5_0 1  # Show specific device and port
```

#### Expert Notes
Expert Analysis:
- Uses UMAD (User MAD) library to query device information
- Displays comprehensive device state including firmware/hardware versions
- Critical for initial device validation
- Shows LID (Local Identifier), SM (Subnet Manager) information, and link state
- Port state machine: Down → Initializing → Armed → Active

#### Common Issues
- Device not found: Check if kernel modules are loaded (ib_uverbs, hw driver)
- Permission denied: Verify /dev/infiniband/uverbs* permissions
- Port down: Check cable, switch configuration, SM status

#### Error Codes
- EACCES - Permission denied accessing device
- ENODEV - Device not found
- EINVAL - Invalid parameter

---

### ibqueryerrors

**Description:** Query and analyze error counters across the fabric

**Category:** Error Analysis

**Source File:** infiniband-diags/ibqueryerrors.c

#### Key Functions
- query_cap_mask
- print_errors
- print_results
- check_threshold
- print_port_config

#### Usage Examples
```bash
ibqueryerrors  # Query all ports with errors exceeding threshold
ibqueryerrors -s 1,2,3  # Suppress specific error types
ibqueryerrors -G 0x506b00000000a  # Query specific port GUID
ibqueryerrors --data  # Include data counters for error ports
ibqueryerrors --details  # Include detailed error breakdown
ibqueryerrors -k  # Clear errors after reading
ibqueryerrors --switch  # Query switches only
```

#### Expert Notes
Expert Analysis:
- Uses Performance Management Agent (PMA) queries via GSI (General Service Interface)
- Queries PortCounters (standard) and PortCountersExt (extended) attributes
- Implements threshold-based error detection (configurable via /etc/ibdiag.conf/error_thresholds)
- Can query all ports or specific port GUIDs
- Supports error clearing after read (-k, -K flags)
- Provides detailed error breakdown including:
  * Symbol errors: Physical layer issues
  * Link recovery errors: Link instability
  * Excessive buffer overruns: Congestion
  * VL15 dropped: Unroutable packets
- Critical for identifying physical layer and fabric issues
- Integrates with ibnetdiscover for fabric topology
- Can suppress common errors for cleaner output

#### Common Issues
- PMA query failures: Check if device supports Performance Management
- High symbol errors: Usually indicates cabling or transceiver issues
- Link recovery errors: Link training failures, check speed/mode negotiation
- Timeouts: SM may be down, check subnet manager status

#### Error Codes
- ETIMEDOUT - MAD query timeout
- EIO - I/O error during query
- ENOTSUP - Hardware doesn't support requested operation

---

### ibnetdiscover

**Description:** Discover and map InfiniBand fabric topology

**Category:** Topology Discovery

**Source File:** infiniband-diags/ibnetdiscover.c

#### Key Functions
- ibnd_discover_fabric
- ibnd_iter_nodes

#### Usage Examples
```bash
ibnetdiscover  # Discover entire fabric
ibnetdiscover --load-cache fabric.cache  # Load from cache
ibnetdiscover -G 0x506b00000000a  # Discover around specific port
ibnetdiscover -H 3  # Limit discovery to 3 hops
```

#### Expert Notes
Expert Analysis:
- Performs SMP (Subnet Management Protocol) queries to build fabric map
- Discovers all CAs (Channel Adapters), switches, and routers
- Maps GUID (Globally Unique Identifier) to LID mappings
- Identifies port connections and link states
- Can save/load fabric topology cache for faster subsequent scans
- Critical for understanding fabric layout and troubleshooting routing
- Shows path information between nodes
- Supports limited scope discovery around a specific node

#### Common Issues
- Discovery timeout: Increase timeout with -o option
- Partial discovery: SM may be down or fabric partitioned
- Permission denied: Need root access for some operations

#### Error Codes
- See manual page for detailed error codes

---

### perfquery

**Description:** Query performance counters for detailed analysis

**Category:** Performance Monitoring

**Source File:** infiniband-diags/perfquery.c

#### Key Functions
- perf_query_via
- mad_decode_field

#### Usage Examples
```bash
perfquery 1 0  # Query port 1 of lid 0
perfquery --all  # Query all counters
perfquery -x 0x3f  # Reset counters
perfquery -e  # Query extended counters
```

#### Expert Notes
Expert Analysis:
- Low-level performance counter queries via PMA
- Can query individual counters or all counters
- Supports extended counters on newer hardware
- Essential for performance baseline and trend analysis
- Can reset counters for clean measurement
- Provides raw counter values for external analysis tools

#### Common Issues
- Counter not supported: Hardware may not implement specific counter
- Read errors: Check device supports Performance Management class

#### Error Codes
- EAGAIN - Counter not supported
- ENOTSUP - Extended counters not available

---

### iblinkinfo

**Description:** Display detailed link information including speed, width, and state

**Category:** Link Analysis

**Source File:** infiniband-diags/iblinkinfo.c

#### Key Functions
- print_port_config
- get_max_msg

#### Usage Examples
```bash
iblinkinfo  # Show all links
iblinkinfo -G 0x506b00000000a  # Show specific port
iblinkinfo -s  # Short format
```

#### Expert Notes
Expert Analysis:
- Shows comprehensive link configuration and state
- Displays link speed (SDR/DDR/QDR/FDR/EDR/HDR/NDR)
- Shows link width (1x, 2x, 4x, 8x, 12x)
- Physical state and logical state
- Link layer (InfiniBand, RoCE, iWARP)
- Remote port information
- Critical for verifying link configuration and identifying mismatched settings

#### Common Issues
- Speed mismatch: Check both ends negotiate same speed
- Width mismatch: Verify cable and transceiver capabilities
- Link down: Check physical connections and SM

#### Error Codes
- See manual page for detailed error codes

---

### ibping

**Description:** Test connectivity to InfiniBand ports using MAD ping

**Category:** Connectivity Test

**Source File:** infiniband-diags/ibping.c

#### Key Functions
- ping_via
- send_mad

#### Usage Examples
```bash
ibping 1  # Ping LID 1
ibping -G 0x506b00000000a  # Ping specific GUID
ibping -c 10 1  # Send 10 pings
```

#### Expert Notes
Expert Analysis:
- Layer 1/2 ping using Subnet Management Packets
- Unlike ICMP ping, tests at InfiniBand protocol layer
- Can test connectivity before IP is configured
- Measures round-trip time at IB layer
- Essential for isolating IB layer vs IP layer issues

#### Common Issues
- Timeout: Port may be down or unreachable
- No response: Check if SM assigns LID to target

#### Error Codes
- See manual page for detailed error codes

---

### ibtracert

**Description:** Trace route between InfiniBand endpoints

**Category:** Routing Analysis

**Source File:** infiniband-diags/ibtracert.c

#### Key Functions
- trace_route
- print_hop

#### Usage Examples
```bash
ibtracert 1 2  # Trace from LID 1 to LID 2
ibtracert -G 0x506b00000000a 0x506b00000000b  # Trace by GUID
```

#### Expert Notes
Expert Analysis:
- Similar to traceroute but for InfiniBand
- Shows path hops and each hop's information
- Helps identify routing issues and loops
- Useful for understanding SM routing decisions
- Can trace between any two GUIDs in the fabric

#### Common Issues
- No route: SM routing may be misconfigured
- Path changes: SM may be rebalancing load

#### Error Codes
- See manual page for detailed error codes

---

### saquery

**Description:** Query Subnet Administrator for fabric information

**Category:** Subnet Administration

**Source File:** infiniband-diags/saquery.c

#### Key Functions
- sa_query
- sa_get_handle

#### Usage Examples
```bash
saquery  # Show SM information
saquery -G 0x506b00000000a  # Query specific node
saquery -p  # Show port records
```

#### Expert Notes
Expert Analysis:
- Queries SM (Subnet Manager) for administrative information
- Accesses PathRecords, NodeRecords, etc.
- Critical for understanding SM's view of the fabric
- Can query for routing information, GID mappings, etc.
- Essential when troubleshooting SM-related issues

#### Common Issues
- SA query failures: SM may be down or unreachable
- Timeout: SM overloaded or network partitioned

#### Error Codes
- See manual page for detailed error codes

---

## Libraries

### libibverbs

**Description:** Userspace Verbs API for RDMA operations

#### Key Headers
- `<infiniband/verbs.h>`
- `<infiniband/driver.h>`

#### Main Structures
- struct ibv_context
- struct ibv_pd
- struct ibv_mr
- struct ibv_qp
- struct ibv_cq
- struct ibv_comp_channel
- struct ibv_srq
- struct ibv_ah
- struct ibv_wc

#### API Functions
- ibv_get_device_list
- ibv_open_device
- ibv_alloc_pd
- ibv_reg_mr
- ibv_create_qp
- ibv_create_cq
- ibv_post_send
- ibv_post_recv
- ibv_poll_cq
- ibv_req_notify_cq
- ibv_create_ah
- ibv_destroy_ah

#### Expert Insights
Expert Insights on libibverbs:

1. Architecture Overview:
   - Provider model: Hardware-specific implementations (mlx5, rxe, etc.)
   - Asynchronous operation model: Queue-based processing
   - Zero-copy capability: Direct hardware access

2. Key Design Patterns:
   - Resource allocation: PD → MR → QP → CQ hierarchy
   - Work Requests: Send/Receive/Read/Write/Atomic operations
   - Completion handling: Polling vs Event-driven

3. Performance Considerations:
   - Memory registration overhead: Use MR caching for hot paths
   - Queue sizing: Balance between latency and throughput
   - CPU affinity: Bind threads to specific NUMA nodes
   - Doorbell batching: Reduce MMIO writes

4. Common Pitfalls:
   - Memory alignment: Ensure proper buffer alignment
   - SGE limits: Check max_sge per device
   - Completion processing: Don't block in completion handler
   - Resource cleanup: Proper destruction order matters

---

### librdmacm

**Description:** RDMA Connection Manager for RDMA CM protocol

#### Key Headers
- `<rdma/rdma_cma.h>`
- `<rdma/rsocket.h>`

#### Main Structures
- struct rdma_cm_id
- struct rdma_event_channel

#### API Functions
- rdma_create_id
- rdma_bind_addr
- rdma_listen
- rdma_connect
- rdma_accept
- rdma_reject
- rdma_disconnect
- rdma_get_cm_event
- rdma_ack_cm_event
- rdma_resolve_addr
- rdma_resolve_route

#### Expert Insights
Expert Insights on librdmacm:

1. Connection Model:
   - Client-Server paradigm similar to TCP sockets
   - Asynchronous event-driven architecture
   - Works over both InfiniBand and RoCE

2. Event Handling:
   - RDMA_CM_EVENT_ADDR_RESOLVED: Address resolution complete
   - RDMA_CM_EVENT_ROUTE_RESOLVED: Route determination complete
   - RDMA_CM_EVENT_ESTABLISHED: Connection established
   - RDMA_CM_EVENT_DISCONNECTED: Remote disconnected
   - RDMA_CM_EVENT_REJECTED: Connection rejected

3. Connection States:
   - IDLE → ADDR_RESOLVED → ROUTE_RESOLVED → CONNECT → ESTABLISHED
   - Proper state machine handling is critical

4. Integration with Verbs:
   - rdma_cm_id contains a verbs structure
   - QP can be accessed via id->qp
   - PD and CQ are created by CM by default

5. Performance:
   - Connection setup overhead is significant
   - Reuse connections when possible
   - Consider RDMA-aware socket API (rsocket) for socket-like API

---

### libibumad

**Description:** Userspace MAD (Management Datagram) library

#### Key Headers
- `<infiniband/umad.h>`

#### Main Structures
- struct umad_port
- struct umad_ca
- struct ibmad_port

#### API Functions
- umad_init
- umad_get_ca
- umad_get_port
- umad_alloc
- umad_send
- umad_recv
- umad_free

#### Expert Insights
Expert Insights on libibumad:

1. Purpose:
   - Direct access to Subnet Management Packets
   - Low-level fabric management
   - Basis for all infiniband-diags tools

2. MAD Classes:
   - SMI (Subnet Management Interface): Port 0, QP 0
   - GSI (General Service Interface): Port 1, QP 1
   - SA (Subnet Administrator): Queries to SM

3. Usage Patterns:
   - Must open specific CA and port
   - Packet format: MAD header + attribute-specific data
   - Method codes: Get, Set, Trap, etc.

4. Common Operations:
   - NodeInfo query (Attribute ID 0x11)
   - PortInfo query (Attribute ID 0x15)
   - Performance Management queries (Class 0x04)

5. Performance:
   - Each MAD is a synchronous operation
   - Can batch operations for efficiency
   - Consider using libibmad for higher-level access

---

## Code Analysis

### infiniband-diags/ibstat.c

**Functionality:** Device and port status query and display

#### Key Algorithms
- UMAD library initialization
- CA (Channel Adapter) enumeration
- Port information extraction
- State machine interpretation

#### Data Structures
- umad_ca_t - CA information structure
- umad_port_t - Port information structure
- Port state arrays (port_state_str, port_phy_state_str)

#### Expert Code Snippets

```c
// Expert analysis: Port state interpretation
// From ibstat.c, shows state machine mapping
static const char * const port_state_str[] = {
    "???",
    "Down",
    "Initializing",
    "Armed",
    "Active"
};

// Expert insight: This is the InfiniBand link state machine
// Down → Initializing → Armed → Active
// Each state represents a specific link establishment phase
// - Down: No physical link
// - Initializing: Physical link training
// - Armed: Link ready, waiting for SM configuration
// - Active: Fully operational, can transfer data
// Understanding this is critical for link troubleshooting
```

```c
// Expert analysis: CA device enumeration
// From ibstat.c, shows device discovery process
device_list = umad_get_ca_device_list();
if (!device_list && errno)
    IBPANIC("can't list IB device names");

if (umad_sort_ca_device_list(&device_list, 0))
    IBWARN("can't sort list IB device names");

// Expert insight: 
// 1. Gets list of all CAs from /sys/class/infiniband
// 2. Sorts by device name for consistent ordering
// 3. Each CA can have multiple ports
// 4. Must handle cases where device list is empty
// This pattern is used across all infiniband-diags tools
```

#### Performance Notes
Performance Characteristics:
- Single pass enumeration: O(N) where N = number of CAs
- No network traffic: All data from /sys filesystem
- Fast operation: < 10ms for typical systems
- Thread-safe: Uses file-based enumeration

Optimization Opportunities:
- Cache device list for repeated queries
- Parallelize port queries across devices
- Use inotify for device change detection

---

### infiniband-diags/ibqueryerrors.c

**Functionality:** Error counter query and threshold-based analysis

#### Key Algorithms
- PMA (Performance Management Agent) queries
- Threshold-based error filtering
- Extended counter support detection
- Error detail extraction

#### Data Structures
- ibnd_node_t - Fabric node representation
- ibnd_port_t - Port information
- thresholds array - Error threshold values

#### Expert Code Snippets

```c
// Expert analysis: PMA query with error handling
// From ibqueryerrors.c, shows robust MAD query pattern
if (!pma_query_via(pc, portid, portnum, ibd_timeout, attr_id, ibmad_port)) {
    IBWARN("%s query failed on %s, %s port %d", attr_name,
           node_name, portid2str(portid), portnum);
    summary.pma_query_failures++;
    return 0;
}

// Expert insight:
// 1. Uses libibmad's pma_query_via for Performance Management queries
// 2. Tracks query failures separately (important for diagnostics)
// 3. Returns 0 on failure to allow continuation
// 4. Timeout is configurable (ibd_timeout)
// This pattern demonstrates defensive programming in diagnostic tools
```

```c
// Expert analysis: Threshold checking for extended counters
// From ibqueryerrors.c, shows capability-aware counter handling
if (htonl(cap_mask2) & IB_PM_IS_ADDL_PORT_CTRS_EXT_SUP) {
    mad_decode_field(pce, ext_i, (void *)&val64);
    if (exceeds_threshold(ext_i, val64)) {
        unit = conv_cnt_human_readable(val64, &val, 0);
        *n += snprintf(str + *n, size - *n,
                      " [%s == %" PRIu64 " (%5.3f%s)]",
                      mad_field_name(ext_i), val64, val, unit);
        is_exceeds = 1;
    }
}

// Expert insight:
// 1. Checks hardware capability mask before using extended counters
// 2. Extended counters provide 64-bit values (vs 32-bit standard)
// 3. Converts to human-readable units (K/M/G/T)
// 4. Format: [CounterName == value (readable unit)]
// This pattern is essential for supporting different hardware generations
```

```c
// Expert analysis: Error detail query for specific error types
// From ibqueryerrors.c, shows hierarchical error investigation
if (i == IB_PC_XMT_DISCARDS_F && details) {
    n += query_and_dump(str + n, sizeof(buf) - n, portid,
                        node_name, portnum,
                        "PortXmitDiscardDetails",
                        IB_GSI_PORT_XMIT_DISCARD_DETAILS,
                        IB_PC_RCV_LOCAL_PHY_ERR_F,
                        IB_PC_RCV_ERR_LAST_F);
}

// Expert insight:
// 1. Only queries detailed counters when main counter has errors
// 2. Details provide breakdown of discard reasons
// 3. Uses GSI class for extended attributes
// 4. Field range specifies which details to extract
// This hierarchical approach saves time and provides focused diagnostics
```

#### Performance Notes
Performance Characteristics:
- Sequential port queries: O(P) where P = number of ports
- Network round-trip per query: ~1-10ms depending on distance
- Extended counters add ~50% overhead when supported
- Can use ALL_PORT_SELECT to reduce queries (if hardware supports)

Optimization Opportunities:
- Cache fabric topology to avoid rediscovery
- Use ALL_PORT_SELECT for switch queries (when available)
- Limit scope to specific nodes with -G option
- Parallelize queries for large fabrics
- Use cached fabric data with --load-cache

Critical Bottlenecks:
- SM interaction for path records (if using -s skip-sl)
- Fabric scan time for large networks
- Extended counter queries on older hardware

---

*End of RDMA Core Documentation*