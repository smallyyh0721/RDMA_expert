---
title: "RDMA Storage Protocols Guide - NVMe-oF, iSER, SRP"
category: kb
tags: [storage, nvmeof, iser, srp, nfs, rdma, spdk]
---

# RDMA Storage Protocols Guide

## 1. NVMe over Fabrics (NVMe-oF) with RDMA

### 1.1 Overview
NVMe-oF extends the NVMe protocol across a network fabric. RDMA transport provides the lowest latency (< 10μs) compared to TCP transport (~30-50μs).

### 1.2 Target Configuration (Server)
```bash
# Load modules
modprobe nvmet
modprobe nvmet-rdma

# Create subsystem
mkdir -p /sys/kernel/config/nvmet/subsystems/nvme-target-1
echo 1 > /sys/kernel/config/nvmet/subsystems/nvme-target-1/attr_allow_any_host

# Add namespace (NVMe device)
mkdir -p /sys/kernel/config/nvmet/subsystems/nvme-target-1/namespaces/1
echo /dev/nvme0n1 > /sys/kernel/config/nvmet/subsystems/nvme-target-1/namespaces/1/device_path
echo 1 > /sys/kernel/config/nvmet/subsystems/nvme-target-1/namespaces/1/enable

# Create RDMA port
mkdir -p /sys/kernel/config/nvmet/ports/1
echo 192.168.1.10 > /sys/kernel/config/nvmet/ports/1/addr_traddr
echo rdma > /sys/kernel/config/nvmet/ports/1/addr_trtype
echo 4420 > /sys/kernel/config/nvmet/ports/1/addr_trsvcid
echo ipv4 > /sys/kernel/config/nvmet/ports/1/addr_adrfam

# Link subsystem to port
ln -s /sys/kernel/config/nvmet/subsystems/nvme-target-1 \
    /sys/kernel/config/nvmet/ports/1/subsystems/nvme-target-1
```

### 1.3 Initiator (Client) Connection
```bash
# Install nvme-cli
apt install nvme-cli

# Discover targets
nvme discover -t rdma -a 192.168.1.10 -s 4420

# Connect
nvme connect -t rdma -n nvme-target-1 -a 192.168.1.10 -s 4420

# Verify
nvme list
lsblk  # New nvme device should appear

# Disconnect
nvme disconnect -n nvme-target-1
```

### 1.4 Performance Tuning
```bash
# Multiple I/O queues (match CPU cores)
nvme connect -t rdma -n nvme-target-1 -a 192.168.1.10 -s 4420 \
    -i 8 -Q 128  # 8 queues, 128 queue depth each

# Check RDMA statistics
cat /sys/class/nvme-fabrics/ctl/nvme*/transport
```

## 2. iSER (iSCSI Extensions for RDMA)

### 2.1 Overview
iSER carries iSCSI protocol over RDMA, replacing the TCP transport with RDMA for zero-copy data transfer.

### 2.2 Target Setup (using targetcli)
```bash
# Install
apt install targetcli-fb

# Configure
targetcli
> /backstores/block create disk0 /dev/sdb
> /iser create iqn.2024.com.example:target1
> /iser/iqn.2024.com.example:target1/tpg1/luns create /backstores/block/disk0
> /iser/iqn.2024.com.example:target1/tpg1/portals create 192.168.1.10
> exit
```

### 2.3 Initiator Setup
```bash
# Install
apt install open-iscsi

# Discover
iscsiadm -m discovery -t st -p 192.168.1.10:3260

# Set transport to iSER
iscsiadm -m node -T iqn.2024.com.example:target1 -p 192.168.1.10 \
    --op update -n iface.transport_name -v iser

# Login
iscsiadm -m node -T iqn.2024.com.example:target1 -p 192.168.1.10 --login

# Verify
cat /sys/class/iscsi_connection/connection*/transport_name
# Should show "iser"
```

## 3. SRP (SCSI RDMA Protocol)

### 3.1 Overview
SRP carries SCSI commands directly over RDMA. Primarily used in InfiniBand environments.

### 3.2 Target Setup
```bash
# Using Linux SCSI target (LIO)
modprobe ib_srpt

targetcli
> /backstores/block create disk0 /dev/sdb
> /srpt create <target_port_guid>
> /srpt/<target>/luns create /backstores/block/disk0
> exit
```

### 3.3 Initiator Setup
```bash
modprobe ib_srp

# Discover SRP targets
srp_daemon -o -e -c

# Connect (auto-discover)
srp_daemon -e -c -o -d /dev/infiniband/umad0

# Verify
lsblk  # New SCSI device should appear
```

## 4. NFS over RDMA (NFSoRDMA)

### 4.1 Server Setup
```bash
# Load server RDMA transport
modprobe svcrdma

# Export filesystem
echo "/export *(rw,no_root_squash)" >> /etc/exports
exportfs -ra

# Enable RDMA transport on NFS server
echo rdma 20049 > /proc/fs/nfsd/portlist

# Verify
cat /proc/fs/nfsd/portlist
# Should show: rdma 20049
```

### 4.2 Client Mount
```bash
# Load client RDMA transport
modprobe xprtrdma

# Mount with RDMA transport
mount -t nfs -o rdma,port=20049,vers=4.1 192.168.1.10:/export /mnt/nfs

# Verify RDMA is being used
cat /proc/mounts | grep rdma
# Or check:
nfsstat -m | grep proto
# Should show: proto=rdma
```

## 5. SMB Direct (Windows RDMA)

SMB Direct uses RDMA for SMB3 file sharing (Windows Server 2012+):
- Automatic: Windows detects RDMA-capable NICs and uses SMB Direct
- Zero-copy file transfers
- Works with RoCE and iWARP NICs
- Requires: Network Direct capable NIC driver

## 6. SPDK with RDMA

### 6.1 SPDK NVMe-oF Target
```bash
# Build SPDK
git clone https://github.com/spdk/spdk && cd spdk
./configure --with-rdma
make

# Setup hugepages and bind NVMe devices
scripts/setup.sh

# Start NVMe-oF target
build/bin/nvmf_tgt &

# Configure via RPC
scripts/rpc.py nvmf_create_transport -t rdma -u 16384
scripts/rpc.py bdev_nvme_attach_controller -b Nvme0 -t PCIe -a 0000:04:00.0
scripts/rpc.py nvmf_create_subsystem nqn.2024.io.spdk:cnode1
scripts/rpc.py nvmf_subsystem_add_ns nqn.2024.io.spdk:cnode1 Nvme0n1
scripts/rpc.py nvmf_subsystem_add_listener nqn.2024.io.spdk:cnode1 \
    -t rdma -a 192.168.1.10 -s 4420
```

## 7. Performance Comparison

| Protocol | Transport | Latency (4K read) | IOPS (4K) | Bandwidth |
|----------|-----------|-------------------|-----------|-----------|
| NVMe-oF | RDMA | 5-10 μs | 1M+ | Line rate |
| NVMe-oF | TCP | 30-50 μs | 500K | Near line rate |
| iSER | RDMA | 15-25 μs | 400K | Good |
| iSCSI | TCP | 50-100 μs | 200K | Moderate |
| SRP | RDMA | 10-20 μs | 600K | Good |
| NFS | RDMA | 20-40 μs | 300K | Good |
| NFS | TCP | 80-150 μs | 100K | Moderate |
