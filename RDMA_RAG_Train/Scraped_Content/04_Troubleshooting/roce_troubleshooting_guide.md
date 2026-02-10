---
title: "RoCE Troubleshooting Guide - Complete Diagnostic Reference"
category: troubleshooting
tags:
  - roce
  - rocev2
  - dcb
  - pfc
  - ecn
  - dcbx
  - congestion
  - lossless
  - networking
  - mellanox
  - nvidia
  - troubleshooting
  - diagnostics
  - flowchart
---

# RoCE Troubleshooting Guide

## 1. Overview

RDMA over Converged Ethernet (RoCE) enables RDMA transport over Ethernet networks. RoCE v2
encapsulates RDMA packets in UDP/IP, allowing L3 routing. Unlike InfiniBand, RoCE depends on
Ethernet-layer lossless behavior (PFC) and congestion management (ECN/DCQCN) for reliable
high-performance operation. This guide provides systematic troubleshooting procedures for RoCE
deployments.

### 1.1 RoCE Versions

| Feature        | RoCE v1         | RoCE v2          |
|----------------|-----------------|-------------------|
| Encapsulation  | Ethernet frame  | UDP/IP/Ethernet   |
| Routable       | No (L2 only)    | Yes (L3 capable)  |
| UDP Dest Port  | N/A             | 4791              |
| GID type       | MAC-based       | IPv4/IPv6-based   |
| Default DSCP   | N/A             | 26 (CS3)          |

### 1.2 Diagnostic Flowchart - Top-Level

```
RoCE Issue Reported
       |
       v
  Can you ping the remote host?
       |
    Yes |          No
       |           |---> Check L2/L3 connectivity (Section 2)
       v
  Does ibv_devinfo show active port?
       |
    Yes |          No
       |           |---> Check driver/firmware (Section 3)
       v
  Can rdma_client/rdma_server connect?
       |
    Yes |          No
       |           |---> Check GID table, routing (Section 4)
       v
  Is performance acceptable?
       |
    Yes |          No
       |           |---> Check PFC/ECN/congestion (Section 5-8)
       v
  Issue resolved or requires deeper analysis
```

---

## 2. RoCE v2 Connectivity Issues

### 2.1 Basic Connectivity Verification

#### Step 1: Verify RDMA Device State

```bash
# List RDMA devices
$ rdma dev
1: mlx5_0: node_type ca fw 20.35.1012 node_guid 0c42:a103:00a7:5e4c
   sm_lid 0 port_cnt 1 state PORT_ACTIVE

# Detailed device info
$ ibv_devinfo
hca_id: mlx5_0
  transport:          InfiniBand (0)
  fw_ver:             20.35.1012
  node_guid:          0c42:a103:00a7:5e4c
  sys_image_guid:     0c42:a103:00a7:5e4c
  vendor_id:          0x02c9
  vendor_part_id:     4123
  hw_ver:             0x0
  phys_port_cnt:      1
    port: 1
      state:          PORT_ACTIVE (4)
      max_mtu:        4096 (5)
      active_mtu:     1024 (3)
      sm_lid:         0
      port_lid:       0
      lmc:            0x00
      link_layer:     Ethernet
```

If the port state is not PORT_ACTIVE:
- Check physical cable connection
- Verify link partner is up: `ethtool <interface>`
- Check for driver errors in dmesg

#### Step 2: Verify Network Interface State

```bash
# Check interface status
$ ip link show ens1f0
2: ens1f0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 9000 qdisc mq state UP ...
    link/ether 0c:42:a1:a7:5e:4c brd ff:ff:ff:ff:ff:ff

# Verify IP configuration
$ ip addr show ens1f0
2: ens1f0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 9000 qdisc mq state UP ...
    inet 192.168.1.10/24 brd 192.168.1.255 scope global ens1f0
    inet6 fe80::e42:a1ff:fea7:5e4c/64 scope link

# Test basic connectivity
$ ping -I ens1f0 192.168.1.20
PING 192.168.1.20 (192.168.1.20) from 192.168.1.10 ens1f0: 56(84) bytes of data.
64 bytes from 192.168.1.20: icmp_seq=1 ttl=64 time=0.043 ms
```

#### Step 3: Verify RoCE Traffic Can Flow

```bash
# On server side
$ rping -s -v -C 10

# On client side
$ rping -c -v -C 10 -a 192.168.1.20
ping data: rdma-ping-0: ABCDEF...
ping data: rdma-ping-1: BCDEFG...
...

# Alternative: use rdma_server/rdma_client
# Server
$ rdma_server

# Client
$ rdma_client -s 192.168.1.20
rdma_client: start
rdma_client: end 0
```

### 2.2 RoCE v2 Mode Verification

```bash
# Check current RoCE mode
$ cma_roce_mode -d mlx5_0 -p 1
RoCE v2

# Or via sysfs
$ cat /sys/bus/pci/devices/0000:04:00.0/infiniband/mlx5_0/ports/1/gid_attrs/types/0
RoCE v2

# Set RoCE v2 mode if needed
$ cma_roce_mode -d mlx5_0 -p 1 -m 2
```

### 2.3 Firewall and Port Issues

RoCE v2 uses UDP destination port 4791. Ensure firewalls allow this:

```bash
# Check for iptables rules blocking RoCE
$ iptables -L -n | grep 4791

# Allow RoCE v2 traffic
$ iptables -I INPUT -p udp --dport 4791 -j ACCEPT
$ iptables -I INPUT -p udp --sport 4791 -j ACCEPT

# For nftables
$ nft add rule inet filter input udp dport 4791 accept
```

---

## 3. GID Table Issues

### 3.1 Understanding GID Table Entries

The GID (Global Identifier) table maps network addresses to RDMA device endpoints. For RoCE v2,
GIDs are based on IPv4/IPv6 addresses.

```bash
# Display GID table
$ ibv_devinfo -v | grep GID
      GID[  0]:   fe80:0000:0000:0000:0e42:a1ff:fea7:5e4c
      GID[  1]:   0000:0000:0000:0000:0000:ffff:c0a8:010a

# More readable format using rdma tool
$ rdma resource show cm_id
$ show_gids
DEV     PORT  INDEX  GID                                     IPv4            VER   DEV
---     ----  -----  ---                                     ----            ---   ---
mlx5_0  1     0      fe80:0000:0000:0000:0e42:a1ff:fea7:5e4c                v2    ens1f0
mlx5_0  1     1      0000:0000:0000:0000:0000:ffff:c0a8:010a 192.168.1.10   v2    ens1f0
```

### 3.2 Common GID Table Problems

**Problem: Empty GID table**

```bash
# Check if interface has IP address
$ ip addr show ens1f0
# If no IP assigned, GID table will be empty for RoCE v2

# Solution: assign IP address
$ ip addr add 192.168.1.10/24 dev ens1f0
```

**Problem: Wrong GID index used**

Applications connecting with wrong GID index will fail. For RoCE v2 over IPv4,
you typically need the GID entry that contains the IPv4-mapped IPv6 address
(::ffff:x.x.x.x format).

```bash
# Find the correct GID index for a given IP
$ show_gids | grep 192.168.1.10
mlx5_0  1     1      0000:0000:0000:0000:0000:ffff:c0a8:010a 192.168.1.10   v2    ens1f0

# Use GID index 1 for this IP address
# In perftest:
$ ib_write_bw -d mlx5_0 -x 1 192.168.1.20
```

**Problem: GID type is RoCE v1 instead of v2**

```bash
# Check GID type
$ cat /sys/class/infiniband/mlx5_0/ports/1/gid_attrs/types/0
IB/RoCE v1

# Change to RoCE v2 for all GIDs
$ cma_roce_mode -d mlx5_0 -p 1 -m 2

# Verify
$ cat /sys/class/infiniband/mlx5_0/ports/1/gid_attrs/types/0
RoCE v2
```

### 3.3 GID Table and Network Namespaces

When using containers or network namespaces, GID entries may not be populated properly.

```bash
# In the container/namespace, verify the RDMA device is visible
$ rdma dev show
$ ibv_devinfo

# Check if the GID table has entries matching the container's IP
$ show_gids

# If GID table is empty, ensure RDMA device is properly assigned to namespace
$ rdma system show netns
netns shared
# 'shared' mode means RDMA devices are visible in all namespaces
# 'exclusive' mode means each namespace gets its own RDMA devices
```

---

## 4. PFC Configuration Verification

### 4.1 Understanding Priority Flow Control for RoCE

RoCE requires a lossless Ethernet fabric. Priority Flow Control (PFC) provides per-priority
pause frames, allowing RoCE traffic on a specific priority to be lossless while other
traffic classes remain lossy.

**Standard RoCE PFC Configuration:**
- Priority 3 (or 4): Lossless for RoCE traffic
- All other priorities: Lossy (default Ethernet behavior)

### 4.2 Verifying PFC with mlnx_qos

```bash
# Check current QoS configuration
$ mlnx_qos -i ens1f0
Priority trust state: dscp
Enabled TC:    0,1,2,3,4,5,6,7
PFC configuration:
        priority:  0   1   2   3   4   5   6   7
        enabled:   0   0   0   1   0   0   0   0
tc: 0 ratelimit: unlimited, tsa: ets, bw: 12%
tc: 1 ratelimit: unlimited, tsa: ets, bw: 12%
tc: 2 ratelimit: unlimited, tsa: ets, bw: 12%
tc: 3 ratelimit: unlimited, tsa: ets, bw: 64%
tc: 4 ratelimit: unlimited, tsa: ets, bw: 0%
tc: 5 ratelimit: unlimited, tsa: ets, bw: 0%
tc: 6 ratelimit: unlimited, tsa: ets, bw: 0%
tc: 7 ratelimit: unlimited, tsa: ets, bw: 0%
```

**Setting PFC for Priority 3:**

```bash
# Enable trust mode to DSCP
$ mlnx_qos -i ens1f0 --trust dscp

# Enable PFC on priority 3
$ mlnx_qos -i ens1f0 --pfc 0,0,0,1,0,0,0,0

# Set traffic class bandwidth allocation
$ mlnx_qos -i ens1f0 -t ets -e 12,12,12,64,0,0,0,0

# Map DSCP 26 to priority 3 (for RoCE CNP)
$ mlnx_qos -i ens1f0 --dscp2prio set,26,3
```

### 4.3 Verifying PFC with lldptool

```bash
# Check PFC status via LLDP
$ lldptool -ti ens1f0 -V PFC
PFC
        willing: yes
        enabled: 0,0,0,1,0,0,0,0
        delay:   32768
        MBC:     no

# Check ETS configuration
$ lldptool -ti ens1f0 -V ETS-CFG
ETS Configuration TLV
        Willing: yes
        CBS:     not supported
        MAX_TCS: 8
        PRIO_MAP: 0:0 1:1 2:2 3:3 4:4 5:5 6:6 7:7
        TC Bandwidth: 12% 12% 12% 64% 0% 0% 0% 0%
        TSA_MAP: 0:ets 1:ets 2:ets 3:ets 4:strict 5:strict 6:strict 7:strict
```

### 4.4 Verifying PFC Frame Counters

```bash
# Check PFC pause frame counters
$ ethtool -S ens1f0 | grep pause
     rx_pause: 0
     rx_pause_duration: 0
     tx_pause: 0
     tx_pause_duration: 0
     rx_pause_transition: 0

# Per-priority pause counters
$ ethtool -S ens1f0 | grep prio
     rx_prio0_pause: 0
     rx_prio0_pause_duration: 0
     rx_prio1_pause: 0
     rx_prio1_pause_duration: 0
     rx_prio2_pause: 0
     rx_prio2_pause_duration: 0
     rx_prio3_pause: 1523
     rx_prio3_pause_duration: 48736
     tx_prio3_pause: 2847
     tx_prio3_pause_duration: 91104
     rx_prio4_pause: 0
     ...
```

If you see rx_prio3_pause incrementing but no tx_prio3_pause, the remote side is
congested but not responding. If both increment, PFC is working bidirectionally.

### 4.5 PFC Diagnostic Flowchart

```
PFC Not Working?
       |
       v
  Check mlnx_qos -i <iface>
  Is trust mode set to 'dscp'?
       |
    No |          Yes
       |           |
  Set trust dscp   v
       |      Is PFC enabled on correct priority?
       |           |
       |        No |          Yes
       |           |           |
       |      Enable PFC       v
       |           |      Check switch-side PFC config
       |           |           |
       |           |      PFC enabled on switch?
       |           |           |
       |           |        No |          Yes
       |           |           |           |
       |           |      Configure switch   v
       |           |           |      Check DCBX negotiation
       |           |           |           |
       v           v           v           v
       Retry and verify with ethtool -S counters
```

---

## 5. ECN Setup Validation

### 5.1 ECN Configuration Overview

Explicit Congestion Notification (ECN) is essential for RoCE v2 congestion management.
When a switch detects congestion, it marks packets with ECN CE (Congestion Experienced) bits.
The receiver generates CNP (Congestion Notification Packets) back to the sender, which
reduces its sending rate via DCQCN.

### 5.2 Enabling ECN on the NIC

```bash
# Enable ECN on the NIC for TC 3 (traffic class 3)
# Check current ECN settings
$ sysctl -a | grep ecn
net.ipv4.tcp_ecn = 0

# For RoCE, ECN is configured at the NIC level, not via sysctl
# Enable ECN for RoCE on specific TC
$ echo 1 > /sys/class/net/ens1f0/ecn/roce_np/enable/3
$ echo 1 > /sys/class/net/ens1f0/ecn/roce_rp/enable/3

# Verify
$ cat /sys/class/net/ens1f0/ecn/roce_np/enable/3
1
$ cat /sys/class/net/ens1f0/ecn/roce_rp/enable/3
1
```

### 5.3 ECN Parameters for DCQCN

```bash
# View current DCQCN parameters
$ cat /sys/class/net/ens1f0/ecn/roce_rp/dce_tcp_g/3
1019

$ cat /sys/class/net/ens1f0/ecn/roce_rp/dce_tcp_rtt/3
1

$ cat /sys/class/net/ens1f0/ecn/roce_rp/rate_reduce_monitor_period/3
4

$ cat /sys/class/net/ens1f0/ecn/roce_rp/initial_alpha_value/3
1023

$ cat /sys/class/net/ens1f0/ecn/roce_rp/clamp_tgt_rate/3
0

# Key DCQCN tuning parameters:
# - dce_tcp_g: Weight of new ECN sample vs history (higher = more reactive)
# - dce_tcp_rtt: RTT in microseconds for rate calculation
# - rate_reduce_monitor_period: Interval between rate reductions
# - initial_alpha_value: Starting congestion factor (0-1023)
# - clamp_tgt_rate: If 1, clamp target rate to current rate on CNP receipt
```

### 5.4 Verifying ECN Marking on Switches

ECN must be enabled on every switch hop. Without ECN marking, DCQCN cannot function.

```bash
# Check if ECN-marked packets are being received (CNP counters)
$ ethtool -S ens1f0 | grep cnp
     rx_roce_cnps: 0
     tx_roce_cnps: 0

# If tx_roce_cnps is 0 and you expect congestion:
# 1. ECN marking not enabled on switches
# 2. DSCP marking is wrong (switch ECN thresholds keyed to wrong DSCP)
# 3. No actual congestion (check queue depths)
```

### 5.5 ECN Troubleshooting Flowchart

```
Congestion but no rate reduction?
       |
       v
  Check rx_roce_cnps counter on sender
       |
  Counter = 0?
       |
    Yes |          No
       |           |
       v           v
  Check tx_roce_cnps on receiver  -->  ECN is working, check DCQCN params
       |
  Counter = 0?
       |
    Yes |          No
       |           |
       v           v
  Receiver not generating CNPs    Receiver generating CNPs but sender not getting them
       |                                  |
       v                                  v
  Check ECN enable on NIC          Check network path / ACL / priority mapping
  (roce_np/enable)
       |
  Enabled?
       |
    Yes |          No
       |           |
       v           v
  Check if ECN CE bits          Enable ECN: echo 1 > .../roce_np/enable/<tc>
  are set on incoming pkts
  (tcpdump/switch counters)
       |
  CE bits not set?
       |
       v
  Configure ECN marking on switches (see Section 7)
```

---

## 6. DSCP/Priority Mapping Problems

### 6.1 DSCP to Priority Mapping

RoCE v2 uses DSCP values in the IP header to indicate traffic priority. The NIC maps DSCP
to internal priority, which then maps to a traffic class (TC).

**Default RoCE DSCP mappings:**
- DSCP 26 (0x1a): RoCE data traffic
- DSCP 48 (0x30): CNP (Congestion Notification Packets)

```bash
# View current DSCP-to-priority mapping
$ mlnx_qos -i ens1f0 --dscp2prio show
DSCP  Priority
----  --------
0     0
...
26    3
...
48    6
...

# Set DSCP 26 to priority 3
$ mlnx_qos -i ens1f0 --dscp2prio set,26,3

# Set CNP DSCP 48 to priority 6
$ mlnx_qos -i ens1f0 --dscp2prio set,48,6
```

### 6.2 Trust Mode Configuration

The NIC can classify packets based on PCP (VLAN priority) or DSCP.

```bash
# Check current trust mode
$ mlnx_qos -i ens1f0
Priority trust state: dscp

# If trust mode is 'pcp', DSCP mappings are ignored
# Change to DSCP trust
$ mlnx_qos -i ens1f0 --trust dscp

# For PCP-based classification (VLAN environments)
$ mlnx_qos -i ens1f0 --trust pcp
```

### 6.3 Setting DSCP on RoCE Traffic

```bash
# Set the default DSCP for RoCE CM (Connection Manager) traffic
$ echo 106 > /sys/class/infiniband/mlx5_0/tc/1/traffic_class
# Value 106 = (DSCP 26 << 2) | ECT(0) = 0x6a = 106

# Or using rdma tool
$ rdma resource show qp

# For applications using rdma-core, set TOS in QP attributes:
# qp_attr.ah_attr.grh.traffic_class = (dscp << 2)
```

### 6.4 DSCP Mapping Mismatch Diagnosis

```bash
# Capture RoCE packets and verify DSCP marking
$ tcpdump -i ens1f0 -nn udp port 4791 -v 2>&1 | head -20
# Look for "tos 0x68" which is DSCP 26 with ECT(0)
# tos 0x68 = DSCP 26 (0x1a << 2 = 0x68)

# If DSCP is wrong, check:
# 1. Application TOS setting
# 2. NIC default TOS override
# 3. Switch DSCP rewriting rules

# Common DSCP/TOS values for RoCE:
# DSCP 26 = TOS 0x68 (with ECN bits 00) or 0x6a (ECN ECT(0))
# DSCP 48 = TOS 0xc0 (CNP traffic)
```

### 6.5 Priority to Traffic Class Mapping

```bash
# View priority-to-TC mapping
$ mlnx_qos -i ens1f0
...
Priority to Traffic Class mapping:
        priority:  0   1   2   3   4   5   6   7
        tc:        0   1   2   3   4   5   6   7

# Ensure priority 3 maps to TC 3 (which should be lossless)
# If using fewer TCs:
$ mlnx_qos -i ens1f0 -p 0,0,0,3,0,0,6,0
# Maps priority 3 -> TC3, priority 6 -> TC6, rest -> TC0
```

---

## 7. DCBX Negotiation Failures

### 7.1 Understanding DCBX

Data Center Bridging Capability Exchange (DCBX) automatically negotiates PFC, ETS, and
application priority settings between NICs and switches. DCBX runs over LLDP.

### 7.2 Checking DCBX Status

```bash
# Check DCBX mode
$ lldptool -ti ens1f0 -V IEEE-DCBX
IEEE DCBX Supported
Oper version: IEEE DCBX
Max version: IEEE DCBX

# Check DCBX operational status
$ lldptool get-lldp -i ens1f0 adminStatus
adminStatus=rxtx

# View received DCBX TLVs from switch
$ lldptool -ti ens1f0 -V PFC -c
PFC Configuration TLV
        Willing: no
        Enabled: 0,0,0,1,0,0,0,0
        MBC: no
        delay: 32768
```

### 7.3 Common DCBX Issues

**Problem: DCBX version mismatch**

```bash
# NIC is using IEEE DCBX but switch uses CEE DCBX
$ lldptool -ti ens1f0 -V IEEE-DCBX
IEEE DCBX not supported

# Fix: Set NIC to match switch DCBX version
# For CEE mode:
$ lldptool set-lldp -i ens1f0 -V CEE-DCBX mode=enable
```

**Problem: Willing bit configuration**

```bash
# If NIC willing=yes and switch willing=yes, there is no clear leader
# Best practice: switch willing=no (switch is authoritative), NIC willing=yes

# Set NIC as willing (accept switch configuration)
$ lldptool -Ti ens1f0 -V PFC willing=yes

# View current willing state
$ lldptool -ti ens1f0 -V PFC
PFC
        willing: yes
```

**Problem: LLDP frames not being received**

```bash
# Check if LLDP frames are being received
$ lldptool -t -i ens1f0 -V sysName
System Name TLV
        My-Switch-Hostname

# If empty or no output, LLDP is not reaching the NIC
# Check:
# 1. Switch LLDP is enabled on the port
# 2. No LLDP filtering on intermediate devices
# 3. LLDP daemon is running: systemctl status lldpad
```

### 7.4 Disabling DCBX for Manual Configuration

In many deployments, DCBX is disabled and PFC/ETS are configured manually on both ends:

```bash
# Disable DCBX on NIC
$ mlnx_qos -i ens1f0 --dcbx_mode=manual

# Or via lldptool
$ lldptool set-lldp -i ens1f0 adminStatus=disabled

# Then configure PFC/ETS manually
$ mlnx_qos -i ens1f0 --trust dscp
$ mlnx_qos -i ens1f0 --pfc 0,0,0,1,0,0,0,0
```

---

## 8. Switch-Side PFC/ETS Configuration

### 8.1 NVIDIA Cumulus Linux

```bash
# Configure PFC on priority 3
$ sudo vi /etc/cumulus/datapath/traffic.conf
# Set:
# pfc.port_group_list = [ROCE]
# pfc.ROCE.port_set = swp1-swp32
# pfc.ROCE.cos_list = [3]
# pfc.ROCE.xoff_size = 18000
# pfc.ROCE.xon_delta = 18000
# pfc.ROCE.tx_enable = true
# pfc.ROCE.rx_enable = true

# Apply configuration
$ sudo systemctl restart switchd

# Verify PFC status
$ sudo mlnx_qos -i swp1
# Should show PFC enabled on priority 3

# Configure ECN
# In /etc/cumulus/datapath/traffic.conf:
# ecn_red.port_group_list = [ROCE]
# ecn_red.ROCE.port_set = swp1-swp32
# ecn_red.ROCE.cos_list = [3]
# ecn_red.ROCE.min_threshold_bytes = 150000
# ecn_red.ROCE.max_threshold_bytes = 1500000
# ecn_red.ROCE.ecn_enable = true
# ecn_red.ROCE.red_enable = false
# ecn_red.ROCE.probability = 100
```

### 8.2 NVIDIA ONYX (Mellanox)

```
## Enable DCBX
switch (config)# dcb priority-flow-control enable force

## Configure PFC on priority 3
switch (config)# dcb priority-flow-control priority 3 enable

## Configure ETS bandwidth allocation
switch (config)# traffic-class 3 bandwidth 50

## Configure ECN for RoCE
switch (config)# ecn enable
switch (config)# ecn absolute-threshold tc 3 min 150 max 1500

## Verify PFC
switch# show dcb priority-flow-control
Priority  Enabled
--------  -------
0         no
1         no
2         no
3         yes
4         no
5         no
6         no
7         no

## Verify ECN
switch# show ecn details
```

### 8.3 SONiC

```bash
# Configure PFC using SONiC CLI
$ sudo config qos reload

# Edit /etc/sonic/qos.json or use config_db
$ redis-cli -n 4 HSET "PORT_QOS_MAP|Ethernet0" "pfc_enable" "3"
$ redis-cli -n 4 HSET "PORT_QOS_MAP|Ethernet0" "dscp_to_tc_map" "AZURE"

# Configure WRED/ECN profile
$ redis-cli -n 4 HSET "WRED_PROFILE|AZURE_LOSSLESS" \
  "ecn" "ecn_all" \
  "green_min_threshold" "250000" \
  "green_max_threshold" "2500000" \
  "green_drop_probability" "5"

# Verify PFC
$ show pfc counters
Port      PFC0    PFC1    PFC2    PFC3    PFC4    PFC5    PFC6    PFC7
--------  ------  ------  ------  ------  ------  ------  ------  ------
Ethernet0 0       0       0       4523    0       0       0       0

# Verify ECN
$ show ecn
Profile: AZURE_LOSSLESS
-----------------------  --------
ecn                      ecn_all
green_min_threshold       250000
green_max_threshold       2500000
green_drop_probability    5
```

### 8.4 Cisco Nexus

```
! Enable DCBX
switch(config)# feature dcbx

! Define class map for RoCE
switch(config)# class-map type qos match-all ROCE_TRAFFIC
switch(config-cmap-qos)# match dscp 26

! Define policy map
switch(config)# policy-map type qos ROCE_QOS
switch(config-pmap-qos)# class ROCE_TRAFFIC
switch(config-pmap-qos-c)# set qos-group 3

! Enable PFC
switch(config)# class-map type queuing match-any c-out-8q-q3
switch(config-cmap-que)# match qos-group 3

switch(config)# policy-map type queuing ROCE_QUEUING
switch(config-pmap-que)# class type queuing c-out-8q-q3
switch(config-pmap-que-c)# priority level 1
switch(config-pmap-que-c)# bandwidth remaining percent 50
switch(config-pmap-que-c)# pause no-drop

! Apply to interface
switch(config)# interface Ethernet1/1
switch(config-if)# service-policy type qos input ROCE_QOS
switch(config-if)# service-policy type queuing output ROCE_QUEUING
switch(config-if)# priority-flow-control mode on

! Verify PFC
switch# show interface Ethernet1/1 priority-flow-control
Port                Mode     Oper(VL bmap)
---------           -------  -------------
Ethernet1/1         on       8 (0x8)

! Configure ECN/WRED
switch(config)# policy-map type queuing ROCE_QUEUING
switch(config-pmap-que)# class type queuing c-out-8q-q3
switch(config-pmap-que-c)# random-detect minimum-threshold 150 kbytes
switch(config-pmap-que-c)# random-detect maximum-threshold 1500 kbytes
switch(config-pmap-que-c)# random-detect ecn
```

### 8.5 Arista EOS

```
! Enable PFC on priority 3
switch(config)# priority-flow-control all
switch(config)# priority-flow-control priority 3 no-drop

! Configure DSCP-to-TC mapping
switch(config)# qos map dscp 26 traffic-class 3

! Configure ECN
switch(config)# qos profile ROCE
switch(config-qos-profile)# tx-queue 3
switch(config-qos-profile-tx)# no-drop
switch(config-qos-profile-tx)# ecn minimum-threshold 150 kbytes
switch(config-qos-profile-tx)# ecn maximum-threshold 1500 kbytes

! Apply QoS profile to interface
switch(config)# interface Ethernet1
switch(config-if)# qos profile ROCE

! Verify PFC
switch# show priority-flow-control
Interface          Admin    Priorities
---------          -----    ----------
Ethernet1          on       3

! Verify ECN
switch# show qos interface Ethernet1
```

---

## 9. Congestion Diagnosis

### 9.1 Detecting Congestion

```bash
# Check for pause frames (indicates congestion)
$ ethtool -S ens1f0 | grep -E "(pause|discard|overflow)"
     rx_pause: 0
     tx_pause: 0
     rx_prio3_pause: 14523
     rx_prio3_pause_duration: 464736
     tx_prio3_pause: 28471
     tx_prio3_pause_duration: 911040
     rx_prio3_discard: 0
     rx_out_of_buffer: 0
     rx_if_down_packets: 0

# Check CNP (Congestion Notification Packet) counters
$ ethtool -S ens1f0 | grep cnp
     rx_roce_cnps: 45231
     tx_roce_cnps: 12847

# Non-zero rx_roce_cnps on sender: sender is being told to slow down
# Non-zero tx_roce_cnps on receiver: receiver is generating CNPs to senders
```

### 9.2 PFC Storm Detection

A PFC storm occurs when one device continuously sends PFC pause frames, potentially
causing a "deadlock" across the network.

```bash
# Monitor PFC pause frames over time
$ watch -n 1 'ethtool -S ens1f0 | grep prio3_pause'

# If rx_prio3_pause is incrementing rapidly and continuously:
# This indicates a PFC storm

# Check for PFC watchdog (if supported)
$ ethtool -S ens1f0 | grep pfc_stall
     tx_pfc_stall_warning: 0
     tx_pfc_stall_critical: 0

# Enable PFC watchdog on switch (vendor-specific)
# Cumulus: pfc_watchdog.enable = true in traffic.conf
# SONiC: pfcwd start --action drop
```

### 9.3 CNP Generation and DCQCN Tuning

```bash
# View CNP-related counters
$ ethtool -S ens1f0 | grep -i cnp
     rx_roce_cnps: 45231
     tx_roce_cnps: 12847

# DCQCN Rate Limiter parameters (sender-side)
$ cat /sys/class/net/ens1f0/ecn/roce_rp/dce_tcp_g/3
1019
# Higher value = more aggressive rate reduction on ECN

$ cat /sys/class/net/ens1f0/ecn/roce_rp/rate_reduce_monitor_period/3
4
# Period in microseconds between rate reductions

$ cat /sys/class/net/ens1f0/ecn/roce_rp/clamp_tgt_rate/3
0
# 0 = target rate can recover; 1 = clamped to reduced rate

# Notification Point (receiver-side) parameters
$ cat /sys/class/net/ens1f0/ecn/roce_np/cnp_dscp/3
48
# DSCP value used for CNP packets

$ cat /sys/class/net/ens1f0/ecn/roce_np/min_time_between_cnps/3
4
# Minimum time between CNP generation in microseconds
```

### 9.4 DCQCN Tuning Recommendations

For low-latency workloads (storage):
```bash
# More aggressive congestion response
$ echo 1023 > /sys/class/net/ens1f0/ecn/roce_rp/initial_alpha_value/3
$ echo 1019 > /sys/class/net/ens1f0/ecn/roce_rp/dce_tcp_g/3
$ echo 1 > /sys/class/net/ens1f0/ecn/roce_rp/clamp_tgt_rate/3
```

For high-throughput workloads (AI/ML):
```bash
# Less aggressive congestion response, preserve throughput
$ echo 512 > /sys/class/net/ens1f0/ecn/roce_rp/initial_alpha_value/3
$ echo 64 > /sys/class/net/ens1f0/ecn/roce_rp/dce_tcp_g/3
$ echo 0 > /sys/class/net/ens1f0/ecn/roce_rp/clamp_tgt_rate/3
$ echo 8 > /sys/class/net/ens1f0/ecn/roce_rp/rate_reduce_monitor_period/3
```

---

## 10. Packet Drops Analysis

### 10.1 Key ethtool Counters for RoCE

```bash
# Comprehensive drop counter analysis
$ ethtool -S ens1f0 | grep -E "(drop|discard|error|overflow|pause)"

# Critical counters explained:

# rx_prio{N}_discard - Packets dropped on ingress for priority N
# Non-zero = PFC not working or buffer overflow
$ ethtool -S ens1f0 | grep rx_prio.*discard
     rx_prio0_discard: 0
     rx_prio1_discard: 0
     rx_prio2_discard: 0
     rx_prio3_discard: 0    # Should be 0 for lossless priority
     rx_prio4_discard: 156
     rx_prio5_discard: 0
     rx_prio6_discard: 0
     rx_prio7_discard: 0

# rx_pause_* / tx_pause_* - PFC pause frame counts
$ ethtool -S ens1f0 | grep -E "^     [rt]x_prio[0-7]_pause:"
     rx_prio0_pause: 0
     rx_prio3_pause: 12453
     tx_prio0_pause: 0
     tx_prio3_pause: 8921

# rx_out_of_buffer - NIC ran out of receive buffers
# Indicates NIC cannot process packets fast enough
$ ethtool -S ens1f0 | grep rx_out_of_buffer
     rx_out_of_buffer: 0

# tx_dropped - Packets dropped on transmit
$ ethtool -S ens1f0 | grep tx_dropped
     tx_dropped: 0

# rx_discards_phy - Physical layer discards
$ ethtool -S ens1f0 | grep rx_discards_phy
     rx_discards_phy: 0
```

### 10.2 Interpreting Counter Combinations

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| rx_prio3_discard > 0 | PFC not configured or not working | Check PFC config on both ends |
| rx_out_of_buffer > 0 | NIC buffer exhaustion | Increase ring buffer, check IRQ affinity |
| tx_prio3_pause high, rx_prio3_discard = 0 | Normal PFC operation under load | May indicate congestion upstream |
| rx_prio3_pause high, no CNPs | ECN not enabled on switches | Enable ECN on switch fabric |
| tx_dropped > 0 | Transmit queue full | Check for PFC backpressure or QP stalls |
| rx_discards_phy > 0 | Physical layer issues | Check cables, transceivers |

### 10.3 Monitoring Counters Over Time

```bash
# Create a monitoring script
$ cat > /tmp/roce_monitor.sh << 'EOF'
#!/bin/bash
IFACE=$1
INTERVAL=${2:-5}
while true; do
    echo "=== $(date) ==="
    ethtool -S $IFACE | grep -E "(rx_prio[0-7]_discard|rx_prio[0-7]_pause|tx_prio[0-7]_pause|rx_out_of_buffer|rx_roce_cnps|tx_roce_cnps|tx_dropped)"
    echo ""
    sleep $INTERVAL
done
EOF
chmod +x /tmp/roce_monitor.sh
$ /tmp/roce_monitor.sh ens1f0 2

# Sample output:
=== Mon Jan 15 10:23:45 UTC 2024 ===
     rx_prio3_discard: 0
     rx_prio3_pause: 14523
     tx_prio3_pause: 28471
     rx_out_of_buffer: 0
     rx_roce_cnps: 45231
     tx_roce_cnps: 12847
     tx_dropped: 0
```

### 10.4 Per-Queue Statistics

```bash
# View per-queue counters (mlx5)
$ ethtool -S ens1f0 | grep -E "^     (rx|tx)[0-9]+_"
     rx0_packets: 1234567
     rx0_bytes: 987654321
     rx0_csum_complete: 1234567
     rx1_packets: 2345678
     ...
     tx0_packets: 3456789
     tx0_bytes: 876543210
     tx1_packets: 4567890
     ...

# Check for queue imbalance (sign of poor RSS/IRQ affinity)
# All queues should have roughly equal packet counts
```

---

## 11. MTU Mismatch Issues

### 11.1 MTU Configuration for RoCE

RoCE performs best with jumbo frames (MTU 9000). MTU must be consistent across the
entire path: NIC -> switches -> NIC.

```bash
# Check current MTU
$ ip link show ens1f0 | grep mtu
2: ens1f0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 9000 qdisc mq ...

# Set MTU
$ ip link set ens1f0 mtu 9000

# Verify MTU on RDMA device
$ ibv_devinfo | grep mtu
      max_mtu:  4096 (5)
      active_mtu: 4096 (5)
# Note: IB MTU 4096 corresponds to Ethernet MTU 4148+ (IB header overhead)
```

### 11.2 Diagnosing MTU Mismatch

```bash
# Test path MTU
$ ping -M do -s 8972 -c 3 -I ens1f0 192.168.1.20
# 8972 = 9000 - 20 (IP header) - 8 (ICMP header)
# If this fails, MTU is not 9000 on some hop

# Reduce size until it works to find actual path MTU
$ ping -M do -s 1472 -c 3 -I ens1f0 192.168.1.20
# 1472 = 1500 - 20 - 8

# Check MTU on switch ports (example for Cumulus)
$ net show interface swp1 | grep MTU
```

### 11.3 MTU and RoCE Performance Impact

```bash
# Test with different MTU values
# With MTU 1500 (default Ethernet)
$ ib_write_bw -d mlx5_0 -m 1024 192.168.1.20
# With MTU 9000 (jumbo frames)
$ ib_write_bw -d mlx5_0 -m 4096 192.168.1.20

# Expected performance difference:
# MTU 1500: ~90% of line rate for large messages
# MTU 9000: ~98%+ of line rate for large messages
# Small message latency is not significantly affected by MTU
```

---

## 12. RoCE over LAG/Bonding

### 12.1 RoCE LAG Support

RoCE over LAG (Link Aggregation Group) allows RDMA traffic over bonded interfaces.
This requires hardware support (mlx5 RoCE LAG).

```bash
# Check if RoCE LAG is supported
$ cat /sys/class/net/bond0/bonding/mode
802.3ad (LACP)

# Verify RoCE LAG is active
$ rdma dev show
1: mlx5_bond_0: node_type ca fw 20.35.1012 ...

# The RDMA device name changes to mlx5_bond_0 when LAG is active
```

### 12.2 LAG Configuration Requirements

```bash
# Both ports must be on the same HCA (dual-port NIC)
$ ibv_devinfo
hca_id: mlx5_0
  ...
  phys_port_cnt: 2

# Create bond interface
$ ip link add bond0 type bond mode 802.3ad
$ ip link set ens1f0 master bond0
$ ip link set ens1f1 master bond0
$ ip link set bond0 up
$ ip addr add 192.168.1.10/24 dev bond0

# Verify LACP negotiation
$ cat /proc/net/bonding/bond0
Bonding Mode: IEEE 802.3ad Dynamic link aggregation
...
802.3ad info
LACP rate: fast
...
Slave Interface: ens1f0
MII Status: up
Speed: 100000 Mbps
...
Slave Interface: ens1f1
MII Status: up
Speed: 100000 Mbps
```

### 12.3 Troubleshooting RoCE LAG

```bash
# Problem: RDMA device not showing as bond device
# Check if both ports are on same HCA
$ ls /sys/class/infiniband/
mlx5_0  mlx5_1
# If mlx5_0 and mlx5_1 are on different PCIe devices, LAG won't work

# Verify same HCA
$ cat /sys/class/infiniband/mlx5_0/device/resource
$ cat /sys/class/infiniband/mlx5_1/device/resource

# Problem: Bond mode not supported
# Only mode 1 (active-backup), mode 2 (balance-xor), and mode 4 (802.3ad) are supported
# Mode 0 (balance-rr) is NOT supported for RoCE LAG

# Problem: TX hashing not optimal
# For LACP, ensure hash policy includes L3+L4
$ echo "layer3+4" > /sys/class/net/bond0/bonding/xmit_hash_policy

# Check GID table for bond interface
$ show_gids | grep bond
mlx5_bond_0  1  0  fe80::...  v2  bond0
mlx5_bond_0  1  1  ::ffff:192.168.1.10  192.168.1.10  v2  bond0
```

### 12.4 RoCE LAG Failover Testing

```bash
# Start RDMA traffic
$ ib_write_bw -d mlx5_bond_0 -D 60 192.168.1.20 &

# Simulate link failure
$ ip link set ens1f0 down

# Monitor bond status
$ cat /proc/net/bonding/bond0
# Should show one slave down, traffic continues on remaining slave

# Check for dropped packets during failover
$ ethtool -S bond0 | grep drop

# Restore link
$ ip link set ens1f0 up
```

---

## 13. Advanced Diagnostics

### 13.1 RoCE Packet Capture

```bash
# Capture RoCE v2 packets (UDP port 4791)
$ tcpdump -i ens1f0 -nn udp port 4791 -c 100 -w /tmp/roce_capture.pcap

# Analyze with tshark
$ tshark -r /tmp/roce_capture.pcap -V | head -100

# Filter for specific RoCE operations
# RDMA Write
$ tshark -r /tmp/roce_capture.pcap -Y "infiniband.opcode == 0x0a"
# RDMA Read Request
$ tshark -r /tmp/roce_capture.pcap -Y "infiniband.opcode == 0x0c"
# Send
$ tshark -r /tmp/roce_capture.pcap -Y "infiniband.opcode == 0x04"
# CNP
$ tshark -r /tmp/roce_capture.pcap -Y "infiniband.opcode == 0x81"
```

### 13.2 Hardware Diagnostic Commands

```bash
# NIC self-test
$ ethtool -t ens1f0
The test result is PASS
The results of the test are:

# Module/transceiver info
$ ethtool --module-info ens1f0
        Identifier                                : 0x11 (QSFP28)
        Extended identifier                       : 0xcc
        Power class                               : 3.5 W max
        Connector                                 : 0x23 (No separable connector)
        Transceiver type                          : 100G Ethernet: 100G CR4
        ...
        Module temperature                        : 35.50 degrees C
        Module voltage                            : 3.2804 V
        Laser tx bias current (Channel 1)         : 7.452 mA
        Laser tx bias current (Channel 2)         : 7.500 mA
        Laser tx bias current (Channel 3)         : 7.384 mA
        Laser tx bias current (Channel 4)         : 7.524 mA

# FEC (Forward Error Correction) stats
$ ethtool --show-fec ens1f0
FEC parameters for ens1f0:
Configured FEC encodings: Auto
Active FEC encoding: RS

# FEC error counters
$ ethtool -S ens1f0 | grep fec
     rx_corrected_bits_phy: 123456
     rx_err_lane_0_phy: 0
     rx_err_lane_1_phy: 0
     rx_err_lane_2_phy: 0
     rx_err_lane_3_phy: 0
```

### 13.3 devlink Health Reporters

```bash
# Check NIC health status
$ devlink health show pci/0000:04:00.0
pci/0000:04:00.0:
  reporter fw
    state healthy error 0 recover 0
  reporter fw_fatal
    state healthy error 0 recover 0
  reporter vnic
    state healthy error 0 recover 0

# Get detailed health report
$ devlink health diagnose pci/0000:04:00.0 reporter vnic
```

### 13.4 Kernel Log Analysis

```bash
# Check for RoCE-related kernel messages
$ dmesg | grep -iE "(roce|rdma|mlx5|ib_|infiniband)" | tail -30

# Common error patterns:
# "mlx5_core: timeout waiting for firmware" - FW hang
# "failed to create roce gid table" - GID table initialization failure
# "PFC stall detected" - PFC storm warning
# "mlx5_ib: mlx5_ib_post_send failed" - QP posting error
# "Couldn't connect to remote" - CM connection failure
```

---

## 14. End-to-End Troubleshooting Checklist

### 14.1 New RoCE Deployment Checklist

```
[ ] 1. NIC firmware updated to latest stable version
[ ] 2. mlx5 driver version matches firmware requirements
[ ] 3. Interface UP with correct IP and MTU 9000
[ ] 4. Trust mode set to DSCP: mlnx_qos -i <iface> --trust dscp
[ ] 5. PFC enabled on correct priority: mlnx_qos -i <iface> --pfc 0,0,0,1,0,0,0,0
[ ] 6. DSCP-to-priority mapping set: mlnx_qos --dscp2prio set,26,3
[ ] 7. ECN enabled on NIC for correct TC
[ ] 8. Switch ports configured: PFC, ECN, DSCP trust, correct queuing
[ ] 9. End-to-end MTU verified: ping -M do -s 8972
[ ] 10. RoCE connectivity verified: rping -c -a <remote_ip>
[ ] 11. Performance validated: ib_write_bw -d mlx5_0 <remote_ip>
[ ] 12. PFC counters verified: ethtool -S | grep prio3_pause
[ ] 13. No drops on lossless priority: ethtool -S | grep prio3_discard (should be 0)
```

### 14.2 Performance Troubleshooting Checklist

```
[ ] 1. MTU set to 9000 on all path segments
[ ] 2. Correct NUMA node affinity for application
[ ] 3. IRQ affinity set to local NUMA node
[ ] 4. PCIe link speed and width at expected values
[ ] 5. No PFC pause storms
[ ] 6. ECN/DCQCN tuned for workload type
[ ] 7. No rx_out_of_buffer drops
[ ] 8. Ring buffers sized appropriately
[ ] 9. CPU not bottlenecked (check CPU utilization)
[ ] 10. No thermal throttling on NIC
```

### 14.3 Common Failure Scenarios and Solutions

**Scenario 1: Connection Timeout**
```
Symptom: rdma_resolve_addr or rdma_resolve_route times out
Root Cause: GID table empty or incorrect, routing issue
Fix:
  1. Verify IP address assigned to interface
  2. Check show_gids output
  3. Verify routing table: ip route get <remote_ip>
  4. Check ARP resolution: ip neigh show
```

**Scenario 2: Performance Degradation Under Load**
```
Symptom: Bandwidth drops when multiple flows active
Root Cause: PFC pauses causing head-of-line blocking
Fix:
  1. Check PFC counters: ethtool -S | grep pause
  2. Verify ECN is enabled end-to-end
  3. Check switch buffer allocation
  4. Tune DCQCN parameters for workload
```

**Scenario 3: Intermittent Packet Loss on Lossless Priority**
```
Symptom: rx_prio3_discard incrementing slowly
Root Cause: Misconfigured switch port, DCBX resetting config
Fix:
  1. Verify PFC on every switch hop
  2. Check DCBX is stable (not flapping)
  3. Monitor switch buffer utilization
  4. Check for microbursts exceeding PFC headroom
```

**Scenario 4: RoCE Works Initially Then Stops**
```
Symptom: RDMA connections fail after some time
Root Cause: PFC watchdog triggered, GID table change, link flap
Fix:
  1. Check dmesg for link events
  2. Verify GID table: show_gids
  3. Check PFC watchdog status on switches
  4. Monitor link stability: ethtool -S | grep link_down
```

**Scenario 5: One-Way Traffic Works, Reverse Does Not**
```
Symptom: RDMA write works A->B but not B->A
Root Cause: Asymmetric PFC/QoS configuration
Fix:
  1. Verify PFC enabled on BOTH directions
  2. Check DSCP trust on both NICs
  3. Verify switch config is symmetric
  4. Check for asymmetric routing
```

---

## 15. Useful Commands Quick Reference

| Task | Command |
|------|---------|
| Check RDMA devices | `rdma dev show` |
| Device details | `ibv_devinfo -v` |
| GID table | `show_gids` |
| PFC config | `mlnx_qos -i <iface>` |
| PFC counters | `ethtool -S <iface> \| grep prio` |
| CNP counters | `ethtool -S <iface> \| grep cnp` |
| Drop counters | `ethtool -S <iface> \| grep discard` |
| Buffer drops | `ethtool -S <iface> \| grep rx_out_of_buffer` |
| RoCE mode | `cma_roce_mode -d <dev> -p 1` |
| Link status | `ethtool <iface>` |
| Module info | `ethtool --module-info <iface>` |
| NIC health | `devlink health show pci/<bdf>` |
| DCBX status | `lldptool -ti <iface> -V PFC` |
| Trust mode | `mlnx_qos -i <iface> \| grep trust` |
| Capture RoCE | `tcpdump -i <iface> udp port 4791` |
| Test connectivity | `rping -c -a <ip>` |
| Test bandwidth | `ib_write_bw -d <dev> <ip>` |
| Test latency | `ib_write_lat -d <dev> <ip>` |
| Kernel logs | `dmesg \| grep mlx5` |
| NIC FW version | `ethtool -i <iface>` |

---

## 16. Log Collection for Support Cases

When opening a support case, collect the following:

```bash
#!/bin/bash
# RoCE diagnostic collection script
OUTDIR="/tmp/roce_diag_$(date +%Y%m%d_%H%M%S)"
mkdir -p $OUTDIR

# System info
uname -a > $OUTDIR/uname.txt
lspci -vvv > $OUTDIR/lspci.txt
dmesg > $OUTDIR/dmesg.txt

# RDMA info
rdma dev show > $OUTDIR/rdma_dev.txt 2>&1
ibv_devinfo -v > $OUTDIR/ibv_devinfo.txt 2>&1
show_gids > $OUTDIR/gids.txt 2>&1

# Network config
ip addr show > $OUTDIR/ip_addr.txt
ip route show > $OUTDIR/ip_route.txt
ip link show > $OUTDIR/ip_link.txt

# QoS config
for iface in $(rdma link show | awk -F/ '{print $2}' | awk '{print $1}'); do
    mlnx_qos -i $iface > $OUTDIR/mlnx_qos_${iface}.txt 2>&1
    ethtool -S $iface > $OUTDIR/ethtool_S_${iface}.txt 2>&1
    ethtool -i $iface > $OUTDIR/ethtool_i_${iface}.txt 2>&1
    ethtool $iface > $OUTDIR/ethtool_${iface}.txt 2>&1
done

# Driver and firmware
modinfo mlx5_core > $OUTDIR/modinfo.txt 2>&1
mst status > $OUTDIR/mst_status.txt 2>&1

# Health reports
for dev in $(ls /sys/bus/pci/drivers/mlx5_core/); do
    [[ $dev == 0* ]] && devlink health show pci/$dev > $OUTDIR/health_${dev}.txt 2>&1
done

# Package it
tar czf ${OUTDIR}.tar.gz -C /tmp $(basename $OUTDIR)
echo "Diagnostics saved to ${OUTDIR}.tar.gz"
```
