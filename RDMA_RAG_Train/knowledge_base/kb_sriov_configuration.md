---
title: "SR-IOV Configuration Guide for RDMA"
category: kb
tags: [sriov, vf, connectx, kvm, kubernetes, virtualization]
---

# SR-IOV Configuration Guide for RDMA

## 1. Overview

Single Root I/O Virtualization (SR-IOV) allows a single PCIe device to appear as multiple virtual devices (VFs - Virtual Functions), each assignable to a VM or container with near-native performance.

For RDMA: Each VF gets its own RDMA device, GID table, and QP space.

## 2. Prerequisites

### 2.1 BIOS Settings
- Enable VT-d (Intel) / AMD-Vi (AMD)
- Enable SR-IOV in BIOS PCIe settings

### 2.2 Kernel Parameters
```bash
# /etc/default/grub
GRUB_CMDLINE_LINUX="intel_iommu=on iommu=pt"
# For AMD: amd_iommu=on iommu=pt

sudo update-grub && sudo reboot

# Verify IOMMU enabled
dmesg | grep -i iommu
# Should see: "DMAR: IOMMU enabled"
```

### 2.3 Firmware Configuration
```bash
sudo mst start
# Enable SR-IOV
sudo mstconfig -d /dev/mst/mt4119_pciconf0 set SRIOV_EN=1
# Set max VFs (firmware level)
sudo mstconfig -d /dev/mst/mt4119_pciconf0 set NUM_OF_VFS=16
# Requires cold reboot
sudo reboot
```

## 3. VF Creation and Configuration

### 3.1 Create VFs
```bash
# Check max VFs supported
cat /sys/class/net/enp59s0f0/device/sriov_totalvfs
# Output: 127 (typical for ConnectX-5/6)

# Create VFs
echo 8 > /sys/class/net/enp59s0f0/device/sriov_numvfs

# Verify
lspci | grep -i mellanox | grep Virtual
# 3b:00.2 Ethernet controller: Mellanox ... [ConnectX-5 Virtual Function]
# 3b:00.3 Ethernet controller: Mellanox ... [ConnectX-5 Virtual Function]
# ...

# Verify RDMA VF devices
ibv_devinfo
# Should show mlx5_2, mlx5_3, etc. for VFs
```

### 3.2 VF Configuration
```bash
# Set VF MAC address
ip link set enp59s0f0 vf 0 mac 00:11:22:33:44:55

# Set VF VLAN
ip link set enp59s0f0 vf 0 vlan 100

# Enable trust mode (REQUIRED for RDMA on VF)
ip link set enp59s0f0 vf 0 trust on

# Set VF link state
ip link set enp59s0f0 vf 0 state enable

# Rate limiting (Mbps)
ip link set enp59s0f0 vf 0 max_tx_rate 25000  # 25Gbps
ip link set enp59s0f0 vf 0 min_tx_rate 10000  # 10Gbps guaranteed

# View all VF settings
ip link show enp59s0f0
```

### 3.3 Make VFs Persistent
```bash
# /etc/rc.local or systemd service
echo 8 > /sys/class/net/enp59s0f0/device/sriov_numvfs
ip link set enp59s0f0 vf 0 trust on
ip link set enp59s0f0 vf 1 trust on
# ... etc

# Or via udev rule:
# /etc/udev/rules.d/82-sriov.rules
ACTION=="add", SUBSYSTEM=="net", ENV{ID_NET_DRIVER}=="mlx5_core", \
  ATTR{device/sriov_numvfs}="8"
```

## 4. KVM/QEMU Passthrough

### 4.1 Bind VF to vfio-pci
```bash
# Get VF PCI address
lspci | grep -i mellanox | grep Virtual
# 3b:00.2 ...

# Unbind from mlx5_core
echo 0000:3b:00.2 > /sys/bus/pci/devices/0000:3b:00.2/driver/unbind

# Bind to vfio-pci
echo "15b3 1018" > /sys/bus/pci/drivers/vfio-pci/new_id
echo 0000:3b:00.2 > /sys/bus/pci/drivers/vfio-pci/bind
```

### 4.2 Attach to VM (QEMU)
```bash
qemu-system-x86_64 \
  -device vfio-pci,host=3b:00.2 \
  -m 8192 \
  -smp 4 \
  ...
```

### 4.3 Attach to VM (libvirt)
```xml
<!-- Add to VM XML -->
<hostdev mode='subsystem' type='pci' managed='yes'>
  <source>
    <address domain='0x0000' bus='0x3b' slot='0x00' function='0x2'/>
  </source>
</hostdev>
```

## 5. Kubernetes SR-IOV

### 5.1 SR-IOV Network Operator
```yaml
# SriovNetworkNodePolicy
apiVersion: sriovnetwork.openshift.io/v1
kind: SriovNetworkNodePolicy
metadata:
  name: rdma-policy
  namespace: sriov-network-operator
spec:
  nodeSelector:
    feature.node.kubernetes.io/network-sriov.capable: "true"
  resourceName: rdma_vf
  numVfs: 8
  nicSelector:
    vendor: "15b3"
    deviceID: "101e"  # ConnectX-6 Dx
  deviceType: netdevice
  isRdma: true
```

### 5.2 Pod Spec with SR-IOV RDMA
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: rdma-pod
  annotations:
    k8s.v1.cni.cncf.io/networks: rdma-network
spec:
  containers:
  - name: rdma-app
    image: my-rdma-app
    securityContext:
      capabilities:
        add: ["IPC_LOCK"]
    resources:
      requests:
        nvidia.com/rdma_vf: 1
        hugepages-2Mi: 1Gi
        memory: 4Gi
      limits:
        nvidia.com/rdma_vf: 1
        hugepages-2Mi: 1Gi
        memory: 4Gi
    volumeMounts:
    - name: hugepage
      mountPath: /dev/hugepages
  volumes:
  - name: hugepage
    emptyDir:
      medium: HugePages
```

## 6. VF LAG (Link Aggregation with VFs)

```bash
# Bond PFs first
ip link add bond0 type bond mode 802.3ad
ip link set enp59s0f0 master bond0
ip link set enp59s0f1 master bond0

# Then create VFs on the bond
echo 4 > /sys/class/net/enp59s0f0/device/sriov_numvfs

# VFs will automatically support LAG failover
```

## 7. Switchdev Mode (OVS Hardware Offload)

```bash
# Switch to switchdev mode (eswitch mode)
devlink dev eswitch set pci/0000:3b:00.0 mode switchdev

# This creates VF representor ports for OVS offload
# VF representors appear as: enp59s0f0_0, enp59s0f0_1, ...

# Add representors to OVS bridge
ovs-vsctl add-br br0
ovs-vsctl add-port br0 enp59s0f0_0
ovs-vsctl add-port br0 enp59s0f0_1

# OVS flows will be offloaded to NIC hardware
# Check offload status
ovs-appctl dpctl/dump-flows type=offloaded
tc filter show dev enp59s0f0_0 ingress
```
