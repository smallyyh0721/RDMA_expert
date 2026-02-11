# MLNX Tools Documentation

This document provides comprehensive documentation for Mellanox RDMA tools, including Python tools, shell scripts, and performance testing utilities.

---

## Python Tools

### mlnx_dump_parser

**Description:** Parse and analyze MLNX_OFED dump files for comprehensive diagnostics

**Category:** Dump Analysis

**Source File:** tools/mlnx_dump_parser

#### Key Classes
- DumpParser
- SectionParser
- ErrorAnalyzer

#### Key Functions
- parse_dump_file
- extract_kernel_log
- analyze_errors
- generate_report

#### Usage Examples
```bash
mlnx_dump_parser dump.txt  # Parse dump file
mlnx_dump_parser -v dump.txt  # Verbose output
mlnx_dump_parser -o report.html dump.txt  # Generate HTML report
mlnx_dump_parser --kernel-only dump.txt  # Parse only kernel logs
```

#### Expert Notes
Expert Analysis:
- Processes comprehensive dump files containing kernel logs, hardware state, and configuration
- Identifies hardware errors, driver issues, and configuration problems
- Provides structured analysis with error categorization
- Critical for post-mortem analysis after system crashes
- Supports multiple dump formats from different OFED versions
- Can correlate errors across different subsystems
- Generates actionable recommendations

Key Analysis Capabilities:
- Kernel error message parsing and classification
- Hardware register state interpretation
- Driver version compatibility checking
- Performance anomaly detection
- Resource exhaustion identification

#### Diagnostic Patterns
- Hardware fault detection: PCIe errors, thermal throttling
- Driver issues: Timeout, panic, memory corruption
- Configuration problems: MTU mismatch, flow control
- Performance bottlenecks: High CPU, latency spikes
- Resource leaks: Memory, handles, interrupts

#### Common Issues
- Dump file corrupted: Check file integrity and size
- Incomplete dump: May indicate system crash during dump creation
- Version mismatch: Ensure parser supports OFED version

---

### mlnx_perf

**Description:** Comprehensive performance monitoring and analysis for Mellanox adapters

**Category:** Performance Analysis

**Source File:** tools/mlnx_perf

#### Key Classes
- PerformanceCollector
- MetricsAnalyzer
- ThresholdMonitor

#### Key Functions
- collect_metrics
- analyze_throughput
- detect_anomalies
- export_data

#### Usage Examples
```bash
mlnx_perf -d mlx5_0  # Monitor device mlx5_0
mlnx_perf -i 1 -d mlx5_0  # 1-second interval
mlnx_perf -t 3600 -o perf.csv  # Collect for 1 hour
mlnx_perf --latency -d mlx5_0  # Focus on latency metrics
```

#### Expert Notes
Expert Analysis:
- Real-time performance monitoring with granular metrics
- Supports multiple collection intervals for different time scales
- Implements anomaly detection based on statistical analysis
- Can export data for external analysis (CSV, JSON)
- Integrates with hardware performance counters
- Provides baseline comparison for performance regression detection

Key Metrics:
- Throughput: Bytes/packets per second
- Latency: Average, P50, P95, P99
- CPU utilization: Per-core, interrupt context
- Queue depths: Send/Receive queue utilization
- Error rates: Packet loss, retries
- Buffer utilization: Headroom, pressure

Advanced Features:
- Correlation analysis between metrics
- Threshold-based alerting
- Historical trend analysis
- Multi-node comparison

#### Diagnostic Patterns
- Throughput degradation: Link issues, congestion
- Latency spikes: Queue depth, interrupt storms
- CPU utilization: Excessive interrupts, polling
- Buffer exhaustion: Headroom depletion, pressure

#### Common Issues
- Missing metrics: Check counter support on hardware
- High overhead: Reduce collection frequency
- Permission denied: Needs access to performance counters

---

### mlnx_qos

**Description:** Configure and analyze Quality of Service for RDMA networks

**Category:** QoS Management

**Source File:** tools/mlnx_qos

#### Key Classes
- QoSConfigurator
- PriorityManager
- FlowControlAnalyzer

#### Key Functions
- configure_pfc
- set_priority_flow_control
- configure_ets
- analyze_qos_config

#### Usage Examples
```bash
mlnx_qos -i eth0 -p 3,4  # Enable PFC on priorities 3,4
mlnx_qos -i eth0 -e 50:30:20  # ETS bandwidth allocation
mlnx_qos -i eth0 --show  # Show current QoS config
mlnx_qos -i eth0 --validate  # Validate QoS configuration
```

#### Expert Notes
Expert Analysis:
- Manages PFC (Priority Flow Control) for lossless Ethernet
- Configures ETS (Enhanced Transmission Selection) for bandwidth allocation
- Supports DCB (Data Center Bridging) standards
- Critical for RoCEv2 performance in congested networks
- Can validate QoS configuration for correctness
- Provides QoS monitoring and statistics

Key Concepts:
- PFC: Per-priority pause frames for lossless delivery
- ETS: Bandwidth allocation across priorities
- DCBX: DCB exchange protocol for auto-configuration
- Priority: Traffic classification and marking

Configuration Strategies:
- Lossless priorities: Enable PFC for RDMA traffic
- Bandwidth allocation: Use ETS for fair sharing
- Buffer sizing: Match PFC timeout with buffer depth
- Congestion management: ECN marking and CNP processing

#### Diagnostic Patterns
- Packet loss in lossless priority: PFC misconfiguration
- Throughput degradation: ETS bandwidth starvation
- Head-of-line blocking: Priority not isolated
- Buffer overflow: Insufficient PFC buffer

#### Common Issues
- PFC storms: Enable PFC watchdog
- DCBX negotiation failure: Check switch configuration
- QoS not applied: Verify hardware support

---

### mlnx_tune

**Description:** Optimize system parameters for maximum RDMA performance

**Category:** System Tuning

**Source File:** tools/mlnx_tune

#### Key Classes
- SystemTuner
- ParameterOptimizer
- ProfileManager

#### Key Functions
- tune_kernel_params
- optimize_cpu_affinity
- configure_interrupts
- apply_profile

#### Usage Examples
```bash
mlnx_tune --profile low-latency  # Apply low-latency profile
mlnx_tune --numa-aware 1  # Enable NUMA-aware tuning
mlnx_tune --show  # Show current tuning status
mlnx_tune --rollback  # Revert previous changes
```

#### Expert Notes
Expert Analysis:
- Automatically optimizes kernel and system parameters for RDMA
- Manages CPU affinity for NUMA-aware processing
- Configures interrupt distribution for load balancing
- Supports tuning profiles for different workloads
- Validates changes and provides rollback capability
- Addresses common performance bottlenecks

Key Optimization Areas:

1. Kernel Parameters:
   - Memory limits (ulimit -l)
   - TCP buffer sizes
   - Congestion control algorithms
   - Huge pages

2. CPU Management:
   - NUMA node binding
   - CPU isolation for interrupt handling
   - Thread affinity for application threads
   - Core isolation for latency-sensitive workloads

3. Interrupt Configuration:
   - IRQ affinity
   - Interrupt moderation
   - RSS (Receive Side Scaling)
   - RPS/RFS (Receive Packet Steering/Flow Steering)

4. Memory Management:
   - Transparent Huge Pages
   - Memory registration caching
   - DMA buffer alignment

#### Diagnostic Patterns
- High CPU on interrupt context: Improve interrupt distribution
- Cache thrashing: Improve NUMA locality
- Memory registration overhead: Enable huge pages
- Context switching: Improve thread affinity

#### Common Issues
- No performance improvement: Verify workload matches profile
- System instability: Revert changes using --rollback
- Conflicts with other services: Exclude affected services

---

### mlx_fs_dump

**Description:** Dump and analyze file system state for RDMA-enabled file systems

**Category:** File System Analysis

**Source File:** tools/mlx_fs_dump

#### Key Classes
- FSDumper
- InodeAnalyzer
- LayoutVisualizer

#### Key Functions
- dump_filesystem
- analyze_inodes
- visualize_layout
- check_consistency

#### Usage Examples
```bash
mlx_fs_dump /mnt/rdma  # Dump file system
mlx_fs_dump -v /mnt/rdma  # Verbose dump
mlx_fs_dump --analyze /mnt/rdma  # Analyze only
mlx_fs_dump --visualize /mnt/rdma  # Generate visualization
```

#### Expert Notes
Expert Analysis:
- Dumps file system metadata for RDMA-aware file systems
- Analyzes inode allocation and data layout
- Visualizes file system structure for optimization
- Detects file system anomalies and corruption
- Useful for performance optimization of RDMA storage

Key Analysis Areas:
- Inode distribution: Identify fragmentation
- Block allocation: Optimize for sequential access
- Journal analysis: Check for performance issues
- Extent mapping: Visualize data locality

Use Cases:
- Performance analysis: Identify suboptimal layouts
- Capacity planning: Understand allocation patterns
- Debugging: Trace file system issues
- Optimization: Reorganize data for better performance

#### Diagnostic Patterns
- Fragmentation: Non-contiguous block allocation
- Journal overhead: Excessive journaling activity
- Extent fragmentation: Poor locality
- Inode exhaustion: Approaching limits

#### Common Issues
- Cannot mount: File system may be corrupted
- Slow dump: File system is large and fragmented
- Permission denied: Need root access

---

## Shell Scripts

### show_counters

**Description:** Display comprehensive hardware and software counters for Mellanox devices

**Category:** Monitoring

**Source File:** tools/show_counters

#### Key Functions
- display_port_counters
- show_error_counters
- list_performance_counters
- display_buffer_stats

#### Usage Examples
```bash
show_counters  # Show all counters
show_counters -p 1  # Show port 1 only
show_counters -e  # Show error counters only
show_counters -d 5  # Show delta every 5 seconds
```

#### Expert Notes
Expert Analysis:
- Shows raw counter values from hardware
- Provides human-readable formatting with units
- Supports filtering by counter type
- Can show delta between measurements
- Essential for baseline establishment and trend analysis

Counter Categories:

1. Port Counters:
   - Link state and configuration
   - Speed and width
   - Physical layer statistics

2. Error Counters:
   - Symbol errors (physical layer)
   - CRC errors (link layer)
   - Discards (resource exhaustion)
   - Overruns (congestion)

3. Performance Counters:
   - Bytes/packets transmitted/received
   - Unicast/multicast/broadcast
   - Throughput metrics

4. Buffer Counters:
   - Queue depth
   - Buffer utilization
   - Headroom

#### Diagnostic Output
Typical Output Structure:
```
Port 1 (GUID: 0x506b00000000a):
  State: Active
  Speed: 100 Gbps (HDR)
  Width: 4x
  
  Port Counters:
    Xmit Bytes: 1234567890123 (1.12 TB)
    Rcv Bytes: 9876543210987 (8.99 TB)
    Xmit Pkts: 1234567890
    Rcv Pkts: 9876543210
    
  Error Counters:
    Symbol Errors: 0
    Link Recovery Errors: 0
    Xmit Discards: 123
    Rcv Errors: 45
    
  Buffer Counters:
    Xmit Queue Depth: 42/256
    Rcv Queue Depth: 78/512
    Headroom: 1024/4096
```

#### Integration Points
- perfquery: Similar PMA-based queries
- ibqueryerrors: Error counter analysis
- ethtool: General NIC statistics
- sysfs: Direct counter access

---

### show_gids

**Description:** Display GID (Global Identifier) information for all ports

**Category:** Configuration

**Source File:** tools/show_gids

#### Key Functions
- enumerate_gids
- display_gid_details
- check_gid_consistency
- show_roce_version

#### Usage Examples
```bash
show_gids  # Show all GIDs
show_gids -d mlx5_0  # Show specific device
show_gids -p 1  # Show port 1 only
show_gids --check  # Check GID consistency
```

#### Expert Notes
Expert Analysis:
- Shows all GIDs configured on each port
- Displays GID type (IPv4, IPv6, IB)
- Shows index and state of each GID
- Critical for RoCE configuration and troubleshooting
- Identifies GID conflicts and inconsistencies

GID Types:
- 0x0000: IPv4 address-based GID
- 0x0001: IPv6 address-based GID
- 0x0002: IB partition key-based GID
- 0x8000+: RoCEv2 link-local GID

Key Information:
- GID index: Used for QP configuration
- State: Active/inactive/invalid
- Type: IPv4/IPv6/IB partition
- Associated LID: For IB fabrics

#### Diagnostic Output
Typical Output Structure:
```
Device: mlx5_0
  Port 1 (GUID: 0x506b00000000a):
    GID[0]: fe80::0000:0000:0000:0000 (RoCEv2 Link-local)
    GID[1]: 192.168.1.100 (IPv4)
    GID[2]: 2001:db8::1 (IPv6)
    GID[8]: 0xfe80000000000000:0000:506b:0000:000a (IB Partition)
    LID: 0x0001
  
  Port 2 (GUID: 0x506b00000000b):
    GID[0]: fe80::0000:0000:0000:0001 (RoCEv2 Link-local)
    GID[1]: 192.168.2.100 (IPv4)
    GID[2]: 2001:db8::2 (IPv6)
```

#### Integration Points
- rdma link: Manage GID configuration
- ip addr: Manage IP addresses (for RoCE)
- ibv_devinfo: Query device capabilities
- sysfs: GID state management

---

### mlnx_affinity

**Description:** Configure and verify CPU affinity for RDMA operations

**Category:** CPU Affinity

**Source File:** tools/mlnx_affinity

#### Key Functions
- set_irq_affinity
- set_rss_affinity
- show_affinity
- optimize_affinity

#### Usage Examples
```bash
mlnx_affinity -d mlx5_0  # Show current affinity
mlnx_affinity -d mlx5_0 --optimize  # Auto-optimize
mlnx_affinity -d mlx5_0 --irq 0-3  # Set IRQ affinity
mlnx_affinity -d mlx5_0 --rss 0-3  # Set RSS affinity
```

#### Expert Notes
Expert Analysis:
- Manages CPU affinity for interrupts and RSS
- Optimizes NUMA locality for RDMA operations
- Supports automatic affinity optimization
- Critical for high-performance RDMA applications

Affinity Layers:

1. Interrupt Affinity:
   - MSI-X vectors to CPU mapping
   - Balances interrupt load across cores
   - Reduces cache thrashing

2. RSS Affinity:
   - Receive flow steering to CPUs
   - Consistent hashing for flow distribution
   - Improves cache locality

3. Application Affinity:
   - Thread to NUMA node binding
   - Memory to NUMA node allocation
   - CPU core isolation

NUMA Considerations:
- Keep RDMA operations local to NUMA node
- Use local PCIe devices
- Allocate memory from local node
- Minimize cross-NUMA traffic

#### Diagnostic Output
Typical Output Structure:
```
Device: mlx5_0
  NUMA Node: 0
  
  Interrupt Affinity:
    IRQ 128: CPU 0-3
    IRQ 129: CPU 4-7
    IRQ 130: CPU 8-11
    IRQ 131: CPU 12-15
  
  RSS Affinity:
    Indirection Table:
      Queue 0 -> CPU 0
      Queue 1 -> CPU 1
      Queue 2 -> CPU 2
      Queue 3 -> CPU 3
  
  Optimization Status:
    NUMA Local: YES
    Affinity Balanced: YES
    Cache Locality: OPTIMAL
```

#### Integration Points
- irqbalance: Interrupt balancing daemon
- numactl: NUMA control
- taskset: CPU affinity
- rdma-core: Verbs API uses affinity

---

### set_irq_affinity.sh

**Description:** Set interrupt affinity for specific IRQs or devices

**Category:** System Configuration

**Source File:** tools/set_irq_affinity.sh

#### Key Functions
- get_irq_list
- set_affinity
- verify_affinity
- save_config

#### Usage Examples
```bash
./set_irq_affinity.sh 128 0-3  # Set IRQ 128 to CPUs 0-3
./set_irq_affinity.sh mlx5_0 0-7  # Set all IRQs for device
./set_irq_affinity.sh -a 0-15  # Set affinity automatically
./set_irq_affinity.sh --persist 128 0-3  # Persist across reboot
```

#### Expert Notes
Expert Analysis:
- Sets CPU mask for specific IRQs
- Can set affinity for all IRQs of a device
- Supports comma-separated CPU lists
- Persists configuration across reboots (optional)

Usage Patterns:
- Single IRQ: set_irq_affinity.sh 128 0-3
- All IRQs of device: set_irq_affinity.sh mlx5_0 0-7
- Multiple IRQs: set_irq_affinity.sh 128,129,130 0-3

CPU Mask Format:
- Single CPU: 0
- Range: 0-3
- Comma-separated: 0,1,2,3
- Hex mask: 0xF (CPUs 0-3)

#### Diagnostic Output
```
Setting IRQ affinity for mlx5_0:
  IRQ 128 -> 0-3 (OK)
  IRQ 129 -> 0-3 (OK)
  IRQ 130 -> 4-7 (OK)
  IRQ 131 -> 4-7 (OK)
  
Verification:
  IRQ 128: 0-3
  IRQ 129: 0-3
  IRQ 130: 4-7
  IRQ 131: 4-7
  All affinities verified
```

#### Integration Points
- /proc/irq/*/smp_affinity_list - Current affinity
- irqbalance: Dynamic balancing
- systemd: Service persistence
- udev: Automatic configuration

---

### show_irq_affinity.sh

**Description:** Display current interrupt affinity for all IRQs or specific devices

**Category:** Monitoring

**Source File:** tools/show_irq_affinity.sh

#### Key Functions
- list_all_irqs
- filter_by_device
- display_affinity
- summarize_distribution

#### Usage Examples
```bash
./show_irq_affinity.sh  # Show all IRQs
./show_irq_affinity.sh mlx5_0  # Show device IRQs
./show_irq_affinity.sh -s  # Show summary
./show_irq_affinity.sh -d  # Show detailed info
```

#### Expert Notes
Expert Analysis:
- Shows interrupt distribution across CPUs
- Can filter by device or IRQ range
- Provides summary statistics
- Useful for verifying affinity configuration

Display Modes:
- All IRQs: Complete system view
- Device-specific: Filter by device name
- Summary: CPU utilization summary
- Detailed: Full IRQ information

#### Diagnostic Output
```
Summary Interrupt Distribution:
CPU 0: 12543 interrupts
CPU 1: 12345 interrupts
CPU 2: 12789 interrupts
CPU 3: 12456 interrupts
...

Device: mlx5_0
  IRQ 128: 0-3 (5123 interrupts)
  IRQ 129: 0-3 (4892 interrupts)
  IRQ 130: 4-7 (5012 interrupts)
  IRQ 131: 4-7 (5234 interrupts)
  
Total interrupts: 20261
Distribution: BALANCED
```

#### Integration Points
- set_irq_affinity.sh: Modify affinity
- /proc/interrupts: Raw interrupt data
- irqbalance: Dynamic balancing
- mpstat: CPU utilization

---

## Performance Tools

### bandwidth_test

**Description:** Test and measure RDMA bandwidth between endpoints

#### Metrics Collected
- Throughput (bytes/sec)
- Message rate (messages/sec)
- CPU utilization
- Latency distribution

#### Output Format
- CSV
- JSON
- Plain text

#### Expert Insights
Expert Analysis:
- Measures theoretical and achievable bandwidth
- Tests different message sizes (1B to 4MB)
- Identifies MTU and efficiency issues
- Can test bidirectional performance

Key Variables:
- Message size: Small messages → overhead dominated
- QP type: RC vs UC vs UD
- Number of QPs: Parallelism
- CPU binding: NUMA locality

Performance Factors:
- PCIe bandwidth: Bottleneck for small messages
- Network bandwidth: Limit for large messages
- CPU overhead: Processing cost
- DMA efficiency: Memory to hardware transfer

#### Tuning Recommendations
- Use large messages (>4KB) for throughput
- Bind to local NUMA node
- Use multiple QPs for parallelism
- Enable SRQ for receiver scaling
- Optimize send/receive queue depths

---

### latency_test

**Description:** Measure RDMA latency with various parameters

#### Metrics Collected
- Average latency
- P50/P95/P99 latency
- Latency jitter
- Latency distribution

#### Output Format
- Histogram
- Statistics
- Raw data

#### Expert Insights
Expert Analysis:
- Measures one-way and round-trip latency
- Tests different message sizes
- Identifies latency outliers
- Can test under load

Latency Components:

1. Processing:
   - Send/Receive queue overhead
   - Work request processing
   - Completion processing

2. Transmission:
   - Wire time (message size / bandwidth)
   - Serialization delay
   - Network propagation

3. Reception:
   - Interrupt processing
   - Completion queue polling
   - Buffer copy (if needed)

Optimization Targets:
- Sub-microsecond: Ideal for RDMA
- 1-10 μs: Good performance
- 10-100 μs: Acceptable for most workloads
- >100 μs: Investigate bottlenecks

#### Tuning Recommendations
- Use polling for low latency (avoid interrupts)
- Minimize queue depths
- Use CPU isolation for critical threads
- Enable kernel bypass
- Optimize NUMA locality
- Use inline data for small messages

---

### stress_test

**Description:** Stress test RDMA connections and identify limits

#### Metrics Collected
- Error rates
- Connection stability
- Resource utilization
- Failure points

#### Output Format
- Log file
- Real-time console

#### Expert Insights
Expert Analysis:
- Finds system limits and failure points
- Tests under extreme conditions
- Identifies resource exhaustion
- Validates reliability

Stress Dimensions:

1. Connection Load:
   - Number of QPs
   - Connection rate
   - Concurrent operations

2. Data Load:
   - Maximum bandwidth
   - Maximum message rate
   - Sustained load duration

3. Resource Load:
   - Memory registration
   - Queue depth
   - Buffer utilization

Failure Modes:
- Out of memory: Registration limits
- Connection timeout: Resource exhaustion
- Queue full: Inadequate depth
- Hardware errors: Overheating, faults

#### Tuning Recommendations
- Increase memory limits (ulimit -l)
- Optimize queue depths
- Use resource pooling
- Implement connection reuse
- Monitor and log all errors

---

*End of MLNX Tools Documentation*