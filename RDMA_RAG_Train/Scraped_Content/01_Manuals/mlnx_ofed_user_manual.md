---
title: "MLNX_OFED Installation and Administration Manual"
category: manuals
tags: [ofed, drivers, installation, mlnx_ofed, configuration]
---

# MLNX_OFED Installation and Administration Manual

## 1. Overview

MLNX_OFED (Mellanox OpenFabrics Enterprise Distribution) is NVIDIA's proprietary driver package for Mellanox/NVIDIA network adapters. It provides user-space and kernel-space drivers for InfiniBand and Ethernet (RoCE) functionality, surpassing the inbox drivers shipped with Linux distributions.

### 1.1 Package Components

| Component | Description |
|-----------|-------------|
| mlx5_core | Core kernel driver for ConnectX-4+ and BlueField |
| mlx5_ib | InfiniBand/RoCE kernel driver |
| mlx4_core | Core kernel driver for ConnectX-3/Pro |
| mlx4_ib | IB driver for ConnectX-3/Pro |
| mlx4_en | Ethernet driver for ConnectX-3/Pro |
| libibverbs | User-space verbs library |
| libmlx5 | User-space provider for mlx5 devices |
| libmlx4 | User-space provider for mlx4 devices |
| librdmacm | RDMA Connection Manager library |
| ibverbs-utils | Verbs diagnostic tools (ibv_devinfo, ibv_devices) |
| infiniband-diags | IB diagnostic tools (ibstat, perfquery, ibnetdiscover) |
| opensm | OpenSM Subnet Manager |
| mstflint | Firmware burning tool |
| mft | Mellanox Firmware Tools |
| perftest | RDMA performance testing tools |
| rdma-core | Core RDMA user-space libraries |
| ucx | Unified Communication X framework |
| openmpi | Open MPI with RDMA support |
| srptools | SRP initiator tools |
| ibacm | IB Address and Connection Manager |

### 1.2 Version History and Support Matrix

| MLNX_OFED Version | Kernel Support | Key Features |
|--------------------|----------------|--------------|
| 5.x | 4.x - 5.x kernels | ConnectX-5/6 full support |
| 23.04 | 5.4 - 6.2 kernels | ConnectX-7 support, enhanced ODP |
| 23.07 | 5.4 - 6.4 kernels | BlueField-3 enhancements |
| 23.10 | 5.4 - 6.5 kernels | ConnectX-7 crypto offload |
| 24.01 | 5.4 - 6.6 kernels | ConnectX-8 initial support |
| 24.04 | 5.4 - 6.8 kernels | Enhanced DPDK integration |
| 24.07 | 5.15 - 6.9 kernels | Improved GPUDirect |
| 24.10 | 5.15 - 6.10 kernels | Latest stable |

## 2. Pre-Installation Requirements

### 2.1 Hardware Requirements

- Supported NVIDIA/Mellanox adapter (ConnectX-3 or later)
- PCIe slot matching adapter requirements (Gen3/Gen4/Gen5)
- Minimum 2GB RAM for compilation
- 1GB free disk space

### 2.2 Software Requirements

```bash
# Required packages for Ubuntu/Debian
sudo apt-get install -y python3 gcc make \
    linux-headers-$(uname -r) \
    autoconf automake libtool pkg-config \
    libltdl-dev lsof pciutils

# Required packages for RHEL/CentOS
sudo yum install -y python3 gcc make \
    kernel-devel-$(uname -r) kernel-headers-$(uname -r) \
    autoconf automake libtool rpm-build \
    pciutils createrepo
```

### 2.3 Verify Hardware Present

```bash
# Check PCI devices
lspci | grep -i mellanox
# Example output:
# 3b:00.0 Ethernet controller: Mellanox Technologies MT28800 Family [ConnectX-5 Ex]
# 3b:00.1 Ethernet controller: Mellanox Technologies MT28800 Family [ConnectX-5 Ex]

# More detail
lspci -vvv -s 3b:00.0 | grep -E "LnkSta|Width|Speed"
```

## 3. Installation

### 3.1 Using mlnxofedinstall Script

```bash
# Download and extract MLNX_OFED
tar xzf MLNX_OFED_LINUX-24.01-0.3.3.1-ubuntu22.04-x86_64.tgz
cd MLNX_OFED_LINUX-24.01-0.3.3.1-ubuntu22.04-x86_64

# Standard installation
sudo ./mlnxofedinstall

# Installation with all user-space packages
sudo ./mlnxofedinstall --all

# Installation for specific adapter only (ETH mode)
sudo ./mlnxofedinstall --without-fw-update --dpdk

# Force installation (override kernel check)
sudo ./mlnxofedinstall --force

# Add kernel support
sudo ./mlnxofedinstall --add-kernel-support

# Install with DPDK support
sudo ./mlnxofedinstall --dpdk --upstream-libs

# Skip firmware update
sudo ./mlnxofedinstall --without-fw-update

# Uninstall
sudo ./mlnxofedinstall --uninstall
```

### 3.2 Using Package Manager

```bash
# For Ubuntu - add MLNX_OFED repository
sudo apt-get install mlnx-ofed-all

# For RHEL/CentOS
sudo yum install mlnx-ofed-all

# Individual packages
sudo apt-get install libibverbs1 librdmacm1 ibverbs-providers \
    rdma-core infiniband-diags perftest
```

### 3.3 Post-Installation

```bash
# Restart the RDMA stack
sudo /etc/init.d/openibd restart

# Or with systemd
sudo systemctl restart openibd

# Verify installation
ofed_info -s
# Output: MLNX_OFED_LINUX-24.01-0.3.3.1

# Check loaded modules
lsmod | grep mlx
# mlx5_ib               421888  0
# mlx5_core            1835008  1 mlx5_ib
# ib_uverbs             163840  2 mlx5_ib,rdma_ucm
# ib_core               413696  8 ...

# Verify devices
ibv_devinfo
```

## 4. Configuration

### 4.1 rdma.conf - RDMA Subsystem Configuration

Location: `/etc/rdma/rdma.conf`

```ini
# Load IPoIB module
IPOIB_LOAD=yes

# Load SRP module (SCSI RDMA Protocol)
SRP_LOAD=no

# Load iSER module (iSCSI Extensions for RDMA)
ISER_LOAD=no

# Load RDS module (Reliable Datagram Sockets)
RDS_LOAD=no

# Load NFSoRDMA modules
XPRTRDMA_LOAD=no
SVCRDMA_LOAD=no

# Load user access CM module
UCM_LOAD=yes

# Load RDMA CM module
RDMA_CM_LOAD=yes

# Load RDMA user-space CM
RDMA_UCM_LOAD=yes
```

### 4.2 mlx5 Module Parameters

```bash
# View current parameters
cat /sys/module/mlx5_core/parameters/*

# Key parameters (set via modprobe.d):
# /etc/modprobe.d/mlx5.conf

# Enable/disable SR-IOV
options mlx5_core num_of_groups=4

# Set debug level
options mlx5_core debug_mask=0x1

# Configure flow steering mode
options mlx5_core flow_steering_mode=smfs

# Probe VFs
options mlx5_core probe_vf=1
```

### 4.3 Network Interface Configuration

```bash
# Set MTU (9000 for jumbo frames, important for RDMA)
ip link set dev eth0 mtu 9000

# Persistent MTU (Netplan - Ubuntu)
# /etc/netplan/01-rdma.yaml
network:
  version: 2
  ethernets:
    enp59s0f0:
      mtu: 9000
      addresses:
        - 192.168.1.10/24

# Enable RoCE on the interface
cma_roce_mode -d mlx5_0 -p 1 2  # 1=RoCEv1, 2=RoCEv2

# Set RoCE TOS (for DSCP-based QoS)
echo 106 > /sys/kernel/config/rdma_cm/mlx5_0/ports/1/default_roce_tos
```

### 4.4 Firmware Configuration with mstconfig

```bash
# Start MST service
sudo mst start

# Show current configuration
sudo mstconfig -d /dev/mst/mt4119_pciconf0 query

# Enable SR-IOV
sudo mstconfig -d /dev/mst/mt4119_pciconf0 set SRIOV_EN=1 NUM_OF_VFS=16

# Set link type
sudo mstconfig -d /dev/mst/mt4119_pciconf0 set LINK_TYPE_P1=ETH LINK_TYPE_P2=ETH

# Enable RoCE
sudo mstconfig -d /dev/mst/mt4119_pciconf0 set ROCE_CC_PRIO_MASK_P1=255

# After mstconfig changes, cold reboot required
sudo reboot
```

### 4.5 QoS Configuration with mlnx_qos

```bash
# Show current QoS settings
mlnx_qos -i eth0

# Set trust mode to DSCP
mlnx_qos -i eth0 --trust=dscp

# Configure PFC on priority 3
mlnx_qos -i eth0 --pfc=0,0,0,1,0,0,0,0

# Configure ETS (bandwidth allocation per TC)
mlnx_qos -i eth0 --tsa=ets,ets,ets,ets,ets,ets,ets,ets \
    --tcbw=12,12,12,14,12,12,12,14

# Map DSCP to priority
mlnx_qos -i eth0 --dscp2prio=set,26,3
```

## 5. SR-IOV Configuration

### 5.1 Enable SR-IOV

```bash
# 1. Enable in firmware
mst start
mstconfig -d /dev/mst/mt4119_pciconf0 set SRIOV_EN=1 NUM_OF_VFS=16
# Reboot required

# 2. Enable in BIOS (VT-d / IOMMU)
# Check IOMMU is enabled
dmesg | grep -i iommu

# 3. Add kernel parameters
# /etc/default/grub
GRUB_CMDLINE_LINUX="intel_iommu=on iommu=pt"
sudo update-grub && sudo reboot

# 4. Create VFs
echo 8 > /sys/class/net/enp59s0f0/device/sriov_numvfs

# 5. Verify VFs
lspci | grep -i mellanox | grep Virtual
ibv_devinfo  # Should show VF devices
```

### 5.2 VF Configuration

```bash
# Set VF MAC address
ip link set enp59s0f0 vf 0 mac 00:11:22:33:44:55

# Set VF VLAN
ip link set enp59s0f0 vf 0 vlan 100

# Set VF rate (Mbps)
ip link set enp59s0f0 vf 0 max_tx_rate 10000

# Enable VF trust mode (needed for RDMA in VF)
ip link set enp59s0f0 vf 0 trust on

# Set VF link state
ip link set enp59s0f0 vf 0 state enable

# View VF configuration
ip link show enp59s0f0
```

## 6. DPDK Integration

### 6.1 DPDK with mlx5

```bash
# Install DPDK (if not included in MLNX_OFED)
sudo apt-get install dpdk dpdk-dev libdpdk-dev

# mlx5 PMD requires:
# - libibverbs
# - libmlx5
# - rdma-core

# No need to bind to vfio-pci or igb_uio!
# mlx5 DPDK PMD uses bifurcated driver model

# Huge pages setup
echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
mkdir -p /dev/hugepages
mount -t hugetlbfs nodev /dev/hugepages

# Test with DPDK testpmd
dpdk-testpmd -a 3b:00.0 -- -i --rxq=4 --txq=4 --nb-cores=4
```

## 7. GPUDirect RDMA

### 7.1 Setup

```bash
# Install nvidia-peermem (MLNX_OFED >= 5.1)
sudo modprobe nvidia-peermem

# Verify
lsmod | grep nvidia_peermem
dmesg | grep peermem

# For older setups (nv_peer_mem)
sudo modprobe nv_peer_mem

# Check GPU-NIC topology
nvidia-smi topo -m
# Look for PIX/PHB connections (same PCIe switch = best)
```

## 8. Monitoring and Diagnostics

### 8.1 ofed_info

```bash
ofed_info -s           # Short version string
ofed_info              # Full package listing
ofed_info -n           # OFED internal version
```

### 8.2 Device Information

```bash
# List RDMA devices
ibv_devices
rdma link show
rdma dev show

# Detailed device info
ibv_devinfo -v
ibv_devinfo -d mlx5_0

# Port state and counters
ibstat
ibstatus
```

### 8.3 Performance Testing

```bash
# Bandwidth test (server)
ib_write_bw -d mlx5_0

# Bandwidth test (client)
ib_write_bw -d mlx5_0 192.168.1.10

# Latency test
ib_write_lat -d mlx5_0          # server
ib_write_lat -d mlx5_0 192.168.1.10  # client

# With specific options
ib_write_bw -d mlx5_0 -s 65536 --report_gbits -q 4 -F 192.168.1.10
```

### 8.4 ethtool Counters

```bash
# All counters
ethtool -S eth0

# Key RDMA-related counters
ethtool -S eth0 | grep -E "rx_vport|tx_vport|roce|pfc|pause|discard|error"

# Driver info
ethtool -i eth0

# Module/transceiver info
ethtool --module-info eth0
ethtool --show-fec eth0
```

## 9. Troubleshooting

### 9.1 Common Issues

**Driver not loading:**
```bash
dmesg | grep mlx5
# Check for firmware mismatch, unsupported kernel, missing dependencies
modinfo mlx5_core  # Verify module exists
```

**No RDMA devices:**
```bash
ls /sys/class/infiniband/
# If empty, check:
lsmod | grep ib_
# Ensure ib_core, mlx5_ib are loaded
sudo modprobe mlx5_ib
```

**Performance issues:**
```bash
# Check PCIe
lspci -vvv -s 3b:00.0 | grep -E "LnkSta|MaxPayload|MaxReadReq"
# Ensure Gen4 x16 for ConnectX-6+

# Check NUMA
cat /sys/class/net/eth0/device/numa_node
# Run applications on same NUMA node

# Check IRQ affinity
cat /proc/interrupts | grep mlx5
set_irq_affinity_cpulist.sh 0-7 eth0
```

## 10. Kernel Module Management

```bash
# Load specific modules
sudo modprobe mlx5_core
sudo modprobe mlx5_ib
sudo modprobe rdma_ucm
sudo modprobe ib_uverbs

# Unload (order matters)
sudo modprobe -r mlx5_ib
sudo modprobe -r mlx5_core

# Blacklist inbox drivers (if conflicting)
# /etc/modprobe.d/blacklist-inbox.conf
blacklist mlx5_core
blacklist mlx5_ib

# Then load OFED versions
sudo /etc/init.d/openibd restart
```
