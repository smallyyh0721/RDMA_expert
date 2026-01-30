# RDMA Fault Case Collection

> This document compiles typical RDMA (Remote Direct Memory Access) network fault cases, covering both RoCE and InfiniBand technology stacks, from physical layer to application layer scenarios.

---

## Case ID : 001

**Error** : 全网或特定区域流量彻底停滞，RoCE吞吐降为0，应用程序出现超时。

**Root cause** : 在二层网络中存在物理环路，或在链路故障触发重路由时，PFC（Priority Flow Control）暂停帧形成了首尾相接的"信用循环"，导致缓冲区永远无法释放，形成PFC死锁（PFC Deadlock）。

**Action plan** :
1. 开启交换机PFC Watchdog（PFCWD）功能
2. 配置死锁恢复时间（Recovery Time）和检测窗口
3. 检查LACP或堆叠配置是否存在配置冲突导致的逻辑环路
4. 使用命令`ethtool -S`检查`rx_pfc_control_frames`指标，确认受影响端口的PFC帧计数是否持续、同步高速增长

---

## Case ID : 002

**Error** : 用户收到`IBV_WC_RETRY_EXC_ERR`（Error 12），QP（Queue Pair）状态变为Error。

**Root cause** : 发送端在规定时间内未收到接收端的ACK确认。常见原因包括：
- 物理链路质量问题：光纤损坏、模块过热导致的位错误
- MTU不一致：中间交换机丢弃了大包（报文大于1500但小于4200）
- ACK Timeout设值过小：在高延迟跨网段通信中，响应回包慢

**Action plan** :
1. 更换光纤线缆，检查光模块状态
2. 对齐全链路MTU配置，确保端到端一致
3. 通过`ibv_modify_qp`调大`timeout`参数
4. 使用`rdma res show qp`检查QP状态
5. 使用`ethtool -S`检查`rx_crc_errors`或`rx_symbol_errors`是否大于0

---

## Case ID : 003

**Error** : 某单台服务器故障导致与其连接的交换机下所有服务器性能同时下降（Victim Flow现象）。

**Root cause** : 接收端服务器的PCIe带宽瓶颈或内存带宽饱和，导致网卡接收队列溢出，被迫向交换机发送大量PFC暂停帧，污染了整个二层网络，形成慢接收方/反压风暴（Slow Receiver / PFC Storm）。

**Action plan** :
1. 检查服务器是否开启了CPU节能模式（C-States），建议调至Performance模式
2. 优化应用程序的Buffer管理
3. 部署ECN（Explicit Congestion Notification）以替代部分PFC职能
4. 使用`ethtool -S`检查故障节点`tx_pfc_control_frames`指标是否极高
5. 检查上游节点`rx_pfc_control_frames`计数是否大量增加

---

## Case ID : 004

**Error** : `ibv_rc_pingpong`无法建立连接，或者只能在同子网通，跨路由不通。

**Root cause** : RoCE v2封装在UDP报文内。如果GID索引选错，会尝试以L2 RoCE v1发包，导致跨路由通信失败。

**Action plan** :
1. 使用`ibv_devinfo -v`检查`GID[index]`类型，确保为RoCE v2而非RoCE v1
2. 在代码中明确指定`gid_index`为支持RoCE v2的索引（通常是3或5）
3. 检查中间路由器/防火墙对UDP 4791端口的放行策略
4. 抓包确认目标UDP端口4791是否被防火墙拦截

---

## Case ID : 005

**Error** : 网络吞吐剧烈波动（锯齿状），无法达到满速。

**Root cause** : 交换机侧ECN触发门限设置得比WRED（加权随机早期检测）丢包门限还要高。导致在标记ECN之前已经发生了物理丢包，触发了RDMA昂贵的重传机制，形成ECN与WRED阈值冲突。

**Action plan** :
1. 确保ECN Threshold < WRED Drop Threshold
2. 建议ECN Kmin设为总Buffer的20%左右
3. 使用交换机命令`display qos queue statistics`检查ECN标记包数
4. 使用`ethtool`检查主机端`rp_cnp_handled`指标是否快速上升

---

## Case ID : 006

**Error** : 大规模分布式任务启动失败，提示无法创建新的Queue Pair。

**Root cause** : 每个QP都要占用一定的非分页内存（Pinned Memory）。在万节点规模下，如果全连接通信（All-to-All），内存需求会超过系统限制，导致QP资源耗尽（QP Resource Exhaustion）。

**Action plan** :
1. 启用Dynamically Connected Transport（DCT）协议（Mellanox特有）
2. 使用共享接收队列（SRQ）减少连接开销
3. 使用`rdma res show qp`检查QP数量是否接近硬件上限
4. 检查系统日志是否显示"Cannot allocate memory"

---

## Case ID : 007

**Error** : 服务器死机或网卡在系统中消失。

**Root cause** : 在大数据包连续写（RDMA Write）时，PCIe总线因竞争或信号质量问题导致事务超时，触发PCIe致命错误（PCIe Completion Timeout）。

**Action plan** :
1. 更新主板BIOS到最新版本
2. 禁用PCIe的ASPM电源管理
3. 检查网卡是否插在推荐的x16插槽
4. 使用`dmesg`检查是否显示"PCIe fatal error"或"Completion Timeout"
5. 使用`lspci -vvv`检查Status是否显示"UncorrErr+"

---

## Case ID : 008

**Error** : 计算结果错误，但网络没有任何重传报错。

**Root cause** : 极罕见情况下，交换机背板缓存发生位翻转且未被CRC捕获，导致RDMA读/写数据损坏（Silent Data Corruption）。

**Action plan** :
1. 启用端到端数据校验（如应用层增加CRC32）
2. 检查网卡的Relaxed Ordering设置，确保数据写入顺序一致性
3. 使用应用层校验位（CheckSum）验证数据完整性
4. 使用`ethtool -S`检查`rx_crc_errors`是否为0（为0时仍可能存在静默数据损坏）

---

## Case ID : 009

**Error** : 融合部署模式下，存储节点作为计算节点提供块设备服务时，fio测试出现严重性能波动，即使绑定空闲CPU也无法解决。

**Root cause** : RDMA网卡产生大量软中断（si），与业务进程抢占CPU资源。操作系统不会自动将软中断调度到空闲核心，导致网卡软中断CPU争用。

**Action plan** :
1. 通过`/proc/interrupts`定位高中断号
2. 将中断绑定到空闲CPU（如将252号中断绑定到CPU 20）：
   ```bash
   echo 20 > /proc/irq/252/smp_affinity_list
   ```
3. 验证性能测试数据是否恢复正常

---

## Case ID : 010

**Error** : InfiniBand链路出现CRC（循环冗余校验）错误计数增加。

**Root cause** : 物理链路质量问题，可能由光纤损坏、光模块故障或端口污染导致。

**Action plan** :
1. 检查并清洁光纤连接器
2. 更换光模块
3. 检查交换机端口状态
4. 使用`ibstat`检查物理层错误计数

---

## Case ID : 011

**Error** : `ibdev2netdev`显示网卡接口处于Down状态。

**Root cause** : 驱动加载异常或云初始化脚本未执行。

**Action plan** :
1. CentOS/Rocky/BaiduLinux系统执行：
   ```bash
   bash /var/lib/cloud/scripts/per-boot/bcc_elastic_net_centos_cloudinit.sh
   ```
2. Ubuntu系统执行：
   ```bash
   bash /var/lib/cloud/scripts/per-boot/bcc_elastic_net_ubuntu_cloudinit.sh
   ```
3. 检查驱动加载状态并重新加载网卡驱动

---

## Case ID : 012

**Error** : 服务器在训练过程中频繁重启，日志显示"Caterr"、"CPU Rst Out"。

**Root cause** : 系统自带RoCE模块的网卡驱动存在缺陷，导致CPU处理数据时发生软锁。

**Action plan** :
1. 升级网卡驱动到最新版本
2. 更新网卡固件
3. 禁用有问题的内核模块
4. 检查Atlas 800T A2服务器的驱动兼容性列表

---

## Case ID : 013

**Error** : 新集群部署后报告"RDMA device not found"错误。

**Root cause** : 使用通用方法安装驱动未正确配置内核模块，依赖关系未解决。

**Action plan** :
1. 使用发行版特定的包管理器安装驱动（如yum/apt）
2. 确保所有依赖正确解析
3. 检查驱动安装日志确认模块加载状态
4. 使用`lsmod | grep mlx`验证驱动是否加载

---

## Case ID : 014

**Error** : 网卡功能异常，性能下降。

**Root cause** : 固件版本与驱动或操作系统不兼容。

**Action plan** :
1. 查询固件状态：
   ```bash
   mlxfwmanager -status -i <interface_name>
   ```
2. 更新固件：
   ```bash
   mlxfwmanager -update
   ```
3. 检查固件与驱动的兼容性矩阵
4. 必要时降级到稳定版本

---

## Case ID : 015

**Error** : Pod无法找到网络连接，VF分配失败。

**Root cause** :
1. 测试Pod部署在`openshift-sriov-network-operator`命名空间
2. 但`SriovIBNetwork`资源配置目标为`default`命名空间
3. 导致网络附着定义（NAD）无法被找到

**Action plan** :
1. 确保Pod和网络配置的命名空间一致
2. 检查`SriovNetwork`和`SriovIBNetwork`的资源配置
3. 验证NAD（Network Attachment Definition）是否正确创建
4. 重新部署Pod到正确的命名空间

---

## Case ID : 016

**Error** : VF成功分配到Pod，但RDMA工作负载无法运行，节点进入不可调度状态。

**Root cause** : `SriovNetwork`对象未包含`rdma metaPlugin`，导致SR-IOV RDMA CNI无法启用。

**Action plan** :
1. 在SriovNetwork配置中添加metaPlugins：
   ```yaml
   spec:
     metaPlugins: |
       {
         "type": "rdma"
       }
   ```
2. 重新应用配置并重启相关Pod
3. 验证RDMA设备是否正确暴露给Pod

---

## Case ID : 017

**Error** : 两台IB弹性云服务器RDMA通信异常。

**Root cause** : Pkey（Partition Key）不一致导致通信隔离。

**Action plan** :
1. 检查Pkey是否一致：
   ```bash
   cat /sys/class/infiniband/mlx5_0/ports/1/pkeys/* | grep -v "0x0000"
   ```
2. 确保两台服务器Pkey完全一致
3. 关闭防火墙：
   ```bash
   service firewalld stop
   ```
4. 检查IB子网管理器配置

---

## Case ID : 018

**Error** : `rping`命令失败，客户端显示`RDMA_CM_EVENT_UNREACHABLE`，但`ibv_rc_pingpong`工作正常。

**Root cause** : RoCEv2需要特定的网络配置，包括正确的PFC（Priority Flow Control）配置、ECN（Explicit Congestion Notification）启用、正确的MTU设置（建议大于1500）。

**Action plan** :
1. 检查交换机PFC配置是否正确启用
2. 验证端到端ECN配置
3. 确认Jumbo Frames支持（MTU > 1500）
4. 检查路由配置确保跨子网可达
5. 使用`rdma link show`检查链路状态

---

## Case ID : 019

**Error** : 180ms RTT链路下，NCCL AllReduce性能抖动，超过200ms时训练任务直接挂掉。

**Root cause** :
1. 高延迟导致RDMA超时
2. 跨国带宽不稳定（40Gbps未压缩梯度不够用）
3. 链路利用率仅30%

**Action plan** :
1. 调整NCCL超时参数：
   ```bash
   export NCCL_IB_TIMEOUT=22
   export NCCL_ASYNC_ERROR_HANDLING=1
   ```
2. 启用梯度压缩（8-bit量化）
3. 使用ECN优先级+8MB分片并行传输
4. 效果：训练效率提升2.6倍，链路利用率提升至70%

---

## Case ID : 020

**Error** : 网络性能骤降，出现拥塞丢包。

**Root cause** : 多级PFC配置不当导致PFC风暴（Pause Frame Storm）和死锁。

**Action plan** :
1. 优化MMU水线配置
2. 在Leaf-Spine之间部署PFC，但核心不感知RDMA流量
3. 启用ECN替代部分PFC功能
4. 使用DCQCN拥塞控制算法
5. 配置PFC死锁检测和恢复机制

---

## Case ID : 021

**Error** : 大量incast场景下，PFC回压传播到发送端，导致吞吐量下降。

**Root cause** : 传统PFC无法区分慢接收端和网络拥塞。

**Action plan** :
1. 实现接收端驱动的流量准入控制（Receiver-driven Traffic Admission）
2. 配置基于CTS（Clear-to-Send）的流控机制
3. 在交换机上为CTS包配置高优先级队列
4. 优化应用程序的缓冲区管理策略

---

## Case ID : 022

**Error** : RDMA注册失败或内存分配错误。

**Root cause** :
1. 部分环境需要root权限进行RDMA注册
2. eRDMA环境对可注册内存总量有限制

**Action plan** :
1. 以root权限运行程序
2. 降低`MOONCAKE_GLOBAL_SEGMENT_SIZE`值
3. 减少HiCache分配的Host内存（因需全量注册RDMA）
4. 检查系统`ulimit -l`内存锁定限制

---

## Case ID : 023

**Error** : Pod中无法发现RDMA设备。

**Root cause** :
1. 设备插件未正确识别RDMA设备
2. SR-IOV Device Plugin配置错误

**Action plan** :
1. 检查`rdma metaPlugin`配置
2. 验证`sriov-device-plugin`日志
3. 确认`SriovNetworkNodePolicy`中正确声明`rdma`资源
4. 重启设备插件和相应Pod

---

## Case ID : 024

**Error** : NCCL训练出现`Watchdog caught collective operation timeout`错误，AllReduce操作卡死。

**Root cause** :
1. 交换机未启用PFC（Priority Flow Control）优先级3
2. 未配置ECN（Explicit Congestion Notification）
3. RoCE网络存在丢包（>0.001%即导致性能断崖）

**Action plan** :
1. 临时规避（不推荐生产环境）：
   ```bash
   export NCCL_IB_DISABLE=1  # 回退到TCP，性能损失50%+
   ```
2. 正确做法：配置无损网络
   ```bash
   # 交换机侧（以华为CE6865为例）
   interface 10GE1/0/1
    priority-flow-control priority 3 enable
    priority-flow-control deadlock-detect enable
    priority-flow-control deadlock-recovery-time 1500
   ```
3. 使用`ethtool -S eth0 | grep -E "drop|error"`检查网卡丢包
4. 使用`rdma link show | grep -A 5 "pfc"`检查PFC状态
5. 设置NCCL调试环境变量：`export NCCL_DEBUG=INFO`

---

## Case ID : 025

**Error** : 2节点训练正常，4节点以上必卡死，`dmesg`出现`nv_peer_mem: DMA mapping failed`。

**Root cause** :
1. `nv_peer_mem`模块与Mellanox驱动版本不兼容
2. 多GPU NUMA亲和性错误（GPU与网卡不在同一NUMA节点）

**Action plan** :
1. 方案1 - 禁用GPU Direct（临时）：
   ```bash
   export NCCL_NET_GDR_LEVEL=0
   ```
2. 方案2 - 修复驱动（推荐）：
   ```bash
   # 卸载旧驱动
   rmmod nv_peer_mem
   # 重装匹配版本（需与OFED版本对齐）
   rpm -ivh nvidia-peer-memory-1.2-1.x86_64.rpm
   ```
3. 方案3 - 强制NUMA绑定：
   ```bash
   numactl --cpunodebind=0 --membind=0 python train.py
   ```
4. 检查GPU Direct状态：`lsmod | grep nv_peer_mem`
5. 检查NUMA拓扑：`numactl --hardware`和`nvidia-smi topo -m`

---

## Case ID : 026

**Error** : 多节点训练突然全部卡死，无错误日志，交换机端口状态显示`PFC pause frames sent > 10^6`。

**Root cause** :
1. 网络拓扑存在微环路（Micro-loop）
2. 多台交换机同时触发PFC，形成死锁环

**Action plan** :
1. 短期：重启交换机解除死锁（业务中断）
2. 长期：
   - 启用交换机PFC死锁检测（Deadlock Detection）
   - 部署DCQCN拥塞控制（替代纯PFC）
   - 优化拓扑避免环路（Spine-Leaf架构需严格设计）
3. 交换机侧检查PFC计数：`show priority-flow-control interface`
4. 服务器侧查看CNP风暴：`cnstat`

---

## Case ID : 027

**Error** : 设置`NCCL_IB_DISABLE=1`无效，仍尝试使用IB，PyTorch 1.12 + NCCL 2.12.9组合。

**Root cause** : PyTorch静态链接了旧版NCCL，环境变量被忽略。

**Action plan** :
1. 方案1 - 强制指定NCCL库路径：
   ```bash
   export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libnccl.so.2
   ```
2. 方案2 - 重编译PyTorch（推荐）：
   ```bash
   # 在编译时指定NCCL_ROOT
   python setup.py install --nccl_root=/usr/local/nccl
   ```
3. 验证PyTorch使用的NCCL版本

---

## Case ID : 028

**Error** : Ceph + RDMA环境下，小文件写入（4KB）性能比TCP高17%，但大文件写入（1MB）性能反而下降30%。

**Root cause** :
1. 每个OSD连接创建独立QP（Queue Pair）
2. 100 OSD集群产生10,000+ QP，导致网卡SRAM溢出
3. 内存注册（Memory Registration）开销随IO大小线性增长

**Action plan** :
1. Ceph配置优化（ceph.conf）：
   ```ini
   [osd]
   ms_async_rdma_device_name = mlx5_0
   ms_async_rdma_qp_count = 8    # 限制QP数量（默认64）
   ms_async_rdma_cq_size = 8192  # 增大CQ避免溢出
   
   [global]
   bluestore_cache_size_hdd = 4G
   bluestore_cache_size_ssd = 8G
   ```
2. 查看QP数量：
   ```bash
   cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/*_qp*
   ```
3. 监控内存注册延迟：
   ```bash
   perf record -e ib_umem_get -a sleep 10
   ```

---

## Case ID : 029

**Error** : 大量小文件创建（`touch file_{1..10000}`）性能骤降，`strace`显示`llapi_file_create`卡在`ibv_post_send`。

**Root cause** :
1. MDS与客户端间RDMA连接未复用
2. 元数据操作（create/unlink）触发频繁QP创建/销毁

**Action plan** :
1. Lustre客户端优化：
   ```bash
   # 增加LNet连接缓存
   lctl set_param lnet.peers=2048
   
   # 启用RDMA连接复用
   mount -t lustre -o rdma,connect_timeout=30s MGS:/fs /mnt/lustre
   ```
2. MDS侧优化（需重启）：
   ```bash
   lctl set_param mdt.*.connect_timeout=60
   ```

---

## Case ID : 030

**Error** : 网络看似正常（ping无丢包），但存储写入延迟从100μs飙升至10ms。

**Root cause** :
1. RDMA对丢包极度敏感：0.001%丢包率导致性能下降90%
2. 重传机制简单（Go-Back-N），单包丢失需重传整个窗口

**Action plan** :
1. 物理层：更换光模块/线缆（QSFP28需AOC或DAC）
2. 网络层：
   - 启用PFC + ECN构建无损网络
   - 部署DCQCN拥塞控制（Intel E810网卡原生支持）
3. 应用层：
   - 增大MTU至9000（Jumbo Frame）
   - 调整RDMA窗口大小：`ibv_modify_qp(qp, &attr, IBV_QP_TIMEOUT)`
4. 检查网卡错误计数：
   ```bash
   ibstat mlx5_0 | grep -E "errors|retrans"
   ```
5. 实时监控丢包：
   ```bash
   watch -n 1 'cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/port_rcv_errors'
   ```

---

## Case ID : 031

**Error** : 单节点性能达标，多节点扩展性差，`perf`显示`remote memory access`占比>40%。

**Root cause** :
1. 存储进程绑定到NUMA Node 0
2. RDMA网卡插在PCIe Slot（NUMA Node 1）
3. 每次RDMA操作触发跨NUMA内存访问

**Action plan** :
1. 方案1 - 进程绑定到网卡所在NUMA：
   ```bash
   numactl --cpunodebind=1 --membind=1 ceph-osd -i 0
   ```
2. 方案2 - BIOS级优化（推荐）：
   - 启用ACS（Access Control Services）避免PCIe重映射
   - 设置PCIe插槽与CPU直连（避免跨CPU访问）
3. 查看网卡NUMA亲和性：
   ```bash
   cat /sys/class/infiniband/mlx5_0/device/numa_node
   ```
4. 查看进程NUMA绑定：
   ```bash
   numastat -p $(pgrep ceph-osd)
   ```
5. 可视化拓扑：
   ```bash
   lstopo-no-graphics --whole-io
   ```

---

## Case ID : 032

**Error** : Dell Z9332F-ON 100G RoCEv2网络配置后性能不达标。

**Root cause** : DCQCN（Data Center Quantized Congestion Notification）配置不完整或参数设置不当。

**Action plan** :
1. ECN配置：
   ```cisco
   wred ECN
   random-detect color green minimum-threshold 500 maximum-threshold 1500 drop-probability 20
   random-detect ecn
   ```
2. 系统级QoS配置：
   ```cisco
   system qos
   buffer-statistics-tracking
   pfc-max-buffer-size 17408
   pfc-shared-buffer-size 10240
   ```
3. 启用PFC：
   ```cisco
   class-map type network-qos cPFC3
   match qos-group 3
   
   policy-map type network-qos PocPFC3
   class cPFC3
   pause
   pfc-cos 3
   ```
4. 接口应用配置：
   ```cisco
   interface range ethernet1/1/1:1-1/1/32:5
   mtu 9216
   flowcontrol receive off
   flowcontrol transmit off
   priority-flow-control mode on
   service-policy input type network-qos PocPFC3
   trust-map dscp rDSCP
   ```
5. 关键参数说明：
   - ECN水线：min 500 KB, max 1500 KB，drop-probability 20%
   - PFC Buffer：最大17408 KB，共享10240 KB
   - DSCP映射：RoCE流量DSCP 26 → QoS Group 3

---

## Case ID : 033

**Error** : AI训练集群长距离传输（支持100km）性能不稳定。

**Root cause** : 静态ECN配置无法适应不同流量模式，导致带宽浪费或拥塞。

**Action plan** :
1. PFC基础配置：
   ```bash
   # 全局启用PFC优先级3
   dcb pfc
   priority 3
   
   # 端口启用PFC（手动模式）
   dcb pfc enable mode manual
   
   # PFC死锁检测（15ms检测，15ms恢复）
   dcb pfc deadlock-detect timer 15
   dcb pfc deadlock-recovery timer 15
   ```
2. AI-ECN高级配置：
   ```bash
   # 启用AI-ECN服务
   ai-service
   ai-ecn
   ai-ecn enable
   assign queue 3
   
   # 验证AI-ECN状态
   display ai-ecn calculated state
   ```
3. 效果：AI算法动态调整ECN阈值，适应不同流量模式

---

## Case ID : 034

**Error** : 400G Spine + 100G Leaf架构下承载大模型训练RDMA流量性能不达标。

**Root cause** : Leaf交换机PFC水线配置不当，不同端口类型（25G/100G/400G）需要差异化配置。

**Action plan** :
1. Leaf交换机关键配置：
   ```h3c
   interface FourHundredGigE1/0/17
   priority-flow-control deadlock enable
   priority-flow-control enable
   priority-flow-control no-drop dot1p 5
   
   # 精细化的PFC水线配置（400G端口）
   priority-flow-control dot1p 5 headroom 9000
   priority-flow-control dot1p 5 reserved-buffer 56
   priority-flow-control dot1p 5 ingress-buffer static 13000
   priority-flow-control dot1p 5 ingress-threshold-offset 100
   
   # ECN配置（WRED + ECN）
   qos wred queue 5 low-limit 4000 high-limit 8000 discard-probability 20
   qos trust dscp
   ```
2. AI ECN分布式模式：
   ```h3c
   netanalysis rocev2 mode bidir
   netanalysis rocev2 ai-ecn enable
   
   ai-service
   ai ai-ecn enable mode distributed
   ai-ecn
   queue 5 enable
   queue 6 enable
   ```

---

## Case ID : 035

**Error** : Arista交换机已启用PFC，但NCCL AllReduce出现hang，抓包发现PFC pause帧未触发。

**Root cause** : 交换机接口默认不信任入向DSCP，导致RoCE流量被放入错误队列，无法触发CoS 3的PFC。

**Action plan** :
1. 正确配置：
   ```eos
   interface Ethernet1
      mtu 9216
      flowcontrol receive off
      flowcontrol transmit off
      priority-flow-control mode on
      qos trust dscp  // 必须配置！
      dcbx application priority application RoCE priority 3
   ```
2. 教训：DSCP→Traffic Class→Priority的映射链条必须完整且正确
3. 验证DSCP信任状态：`show qos maps dscp-cos`

---

## Case ID : 036

**Error** : 华为云ALM-52004告警：IB交换机端口状态从Active变为Down，或Symbol Error计数超过100。

**Root cause** :
1. 交换机端口故障
2. 线缆断开或光模块损坏
3. 对端设备故障
4. 端口被禁用

**Action plan** :
1. 查看端口错误计数：
   ```bash
   ibqueryerrors -c  // 超过阈值会显示FAILED
   ```
2. 典型错误输出分析：
   - `SymbolErrors = 3121`：物理层信号完整性问题（光模块/光纤）
   - `RcvSwRelayErrors = 48545`：路由表错误（DLID/VL映射问题）
   - `XmtDiscards = 9789`：拥塞或链路故障导致的TX丢弃
3. 检查光模块功率：
   ```bash
   smpquery -C mlx4_0 -P 1 PT
   ```
4. 更换故障硬件（光模块/光纤/线缆）

---

## Case ID : 037

**Error** : `ibstat`显示端口反复LinkUp/LinkDown，`symbol_error`持续增长。

**Root cause** :
1. 光学问题：光模块故障、光纤弯曲半径过小、连接器污染
2. 电气问题：铜缆质量差、电磁干扰
3. 固件bug：Mellanox SB7800早期3.10.5000固件存在稳定性问题

**Action plan** :
1. 查看物理状态：
   ```bash
   ibstat | grep -A5 "Port 1:"
   # 关注: Physical state: Polling/LinkUp
   #       State: Down/Active 状态抖动
   ```
2. 错误计数分析：
   | 计数器 | 含义 | 阈值 |
   |--------|------|------|
   | SymbolErrors | 物理层误码 | > 10 |
   | LinkErrorRecovery | 链路恢复次数 | > 5 |
   | LinkDowned | 链路失败次数 | > 1 |
   | RcvSwRelayErrors | 交换机转发错误 | > 100 |
   | XmtDiscards | 发送丢弃 | > 100 |
3. 固件降级到稳定版本3.10.4400
4. 更换光模块/光纤/铜缆

---

## Case ID : 038

**Error** : Mellanox SN2010升级固件后交换机无法启动，卡在`Loading SX core:[FAILED]`。

**Root cause** : 固件与Bootloader兼容性问题，温度监控模块初始化失败。

**Action plan** :
1. 进入Bootloader救援模式
2. 切换启动分区（如存在备用镜像）：
   ```bash
   image boot next  // 如果3.10.4400在备用分区
   ```
3. 若无法恢复，需通过JTAG或U盘重新刷写固件
4. 错误日志分析：
   - `Failed to access MTECR, status=4`：温度监控寄存器访问失败
   - `PCI probe failed`：PCI初始化失败

---

## Case ID : 039

**Error** : 100台GPU服务器的千亿参数训练，Spine-Leaf架构下整集群通信中断。

**Root cause** :
1. 某节点网卡驱动异常（CPU高负载导致软中断处理延迟）
2. 网卡接收队列满，持续向上游发送PFC Pause帧（XOFF）
3. Leaf交换机缓存被占满，向Spine发送Pause
4. Spine向所有Leaf传播Pause，整集群通信中断
5. PFC是基于端口的，而非基于流（Flow-based），导致不公平降速

**Action plan** :
1. 配置PFC死锁检测（华为CE系列）：
   ```bash
   dcb pfc deadlock-detect timer 15  // 15ms无数据流则判定死锁
   dcb pfc deadlock-recovery timer 15  // 15ms恢复时间
   ```
2. 限制死锁次数（1分钟内超过20次则自动关闭PFC）：
   ```bash
   priority-flow-control deadlock auto-recovery threshold 20
   ```
3. 结合ECN降低PFC依赖（ECN是端到端的，不会像PFC那样传播风暴）

---

## Case ID : 040

**Error** : 千卡集群Ring算法跨机架通信时NCCL AllReduce hang住，小规模（单Leaf内）正常。

**Root cause** :
1. 拓扑感知缺失：调度器将Ring拓扑分配到非连续机架
2. Spine层拥塞：Ring算法跨Spine多次，流量在Spine层冲突
3. ECN水线配置不当：交换机ECN阈值过高，未及时标记拥塞

**Action plan** :
1. 查看实际拓扑路径：
   ```bash
   ibtracert <dest_lid>  // 查看路由路径
   ```
2. 检查交换机拥塞计数：
   ```bash
   show interface ethernet | grep -E "pause|ecn|discard"
   ```
3. 临时规避：强制Tree算法（牺牲带宽换稳定性）
   ```bash
   export NCCL_ALGO=TREE
   ```
4. 根本解决：
   - 配置Slurm/Kubernetes拓扑感知调度，确保Ring尽量在Leaf内闭合
   - 调整Spine层ECN水线（min-threshold降至64KB）
   - 使用NCCL 2.18+的CTran（Custom Transport）替代默认Ring

---

## Case ID : 041

**Error** : DCQCN部署下，特定流量模式导致死锁，CNP被Pause阻塞形成循环依赖。

**Root cause** :
1. 交换机A端口1收到Pause，停止发送
2. 但交换机A的接收端仍在向该端口发送CNP（Congestion Notification Packet）
3. CNP被Pause阻塞，堆积在交换机A内部
4. CNP属于高优先级队列（CoS 7），堵塞后触发对上游发送Pause
5. 循环依赖：A等B发数据，B等A发CNP，形成死锁

**Action plan** :
1. 升级固件至3.10.4400+
2. 配置CNP的严格优先级队列独立缓存，与数据队列隔离
3. 启用`no-drop`仅对RoCE数据队列，CNP队列允许丢包
4. 查看PFC死锁计数器（NVIDIA交换机）：
   ```bash
   show interface priority-flow-control | grep -i deadlock
   ```
5. 查看CNP发送/接收统计：
   ```bash
   show counters roce  // 观察CNP_pkt计数是否异常停滞
   ```

---

## Case ID : 042

**Error** : x86服务器+CX6网卡连接到Broadcom交换机，RDMA写操作丢包。

**Root cause** : Broadcom芯片的Headroom Buffer分配不足，无法容纳往返时延内的数据。

**Action plan** :
1. Broadcom交换机配置：
   ```cisco
   system qos
   pfc-max-buffer-size 17408
   pfc-shared-buffer-size 10240
   priority-flow-control headroom 9000  // 必须足够大以容纳往返时延内的数据
   ```
2. Headroom计算原理：
   ```
   Headroom = (MTU + 帧间隙) × 往返跳数 × 2
   对于100G链路，10us RTT，最大缓存需求约 125KB
   ```

---

## Case ID : 043

**Error** : OpenStack Neutron+Open vSwitch SR-IOV环境下，虚拟机内RDMA流量正常，但物理网络出现随机丢包。

**Root cause** : SDN控制器下发的DCBX配置与网卡实际配置不一致，导致PFC配置不匹配。

**Action plan** :
1. 方案1 - 在网卡侧强制信任交换机配置（禁用本地DCBX）：
   ```bash
   mlxconfig -d /dev/mst/mt4119_pciconf0 set DCBX_IEEE=0 DCBX_CEE=0 DCBX_VER=1
   ```
2. 方案2 - 在交换机侧禁用DCBX，静态配置PFC：
   ```bash
   interface eth1
    no dcbx enable
    priority-flow-control mode on
   ```
3. 检查交换机PFC配置和网卡PFC配置是否一致：
   ```bash
   mlnx_qos -i ib0
   ```

---

## Case ID : 044

**Error** : 同一RoCE网络承载vSAN存储和NCCL训练，AI训练对延迟敏感，PFC导致GPU利用率波动。

**Root cause** : 存储突发流量（Burst）触发PFC，暂停训练流量，导致存储流量与AI训练流量冲突。

**Action plan** :
1. 分类映射：
   ```cisco
   class-map type queuing AI_TRAFFIC
   match dscp af32  // DSCP 28 (AI训练)
   
   class-map type queuing STORAGE_TRAFFIC
   match dscp af11  // DSCP 10 (存储)
   ```
2. 策略配置（AI流量严格优先，存储流量加权轮询）：
   ```cisco
   policy-map type queuing QoS_POLICY
   class AI_TRAFFIC
   priority level 1  // 严格优先
   class STORAGE_TRAFFIC
   bandwidth remaining percent 30
   ```
3. 为不同流量类型配置独立的PFC队列

---

## Case ID : 045

**Error** : 新部署的400G端口频繁出现Symbol Error，更换光模块和光纤无效。

**Root cause** : AOC（Active Optical Cable）线缆的预加重（Pre-emphasis）参数与交换机SerDes不匹配。

**Action plan** :
1. 方案1 - 调整交换机SerDes参数（需要进入诊断模式）：
   ```bash
   diag
   port <port_num> serdes tx_preemphasis <value>
   ```
2. 方案2 - 更换为经厂商认证的AOC线缆（如Mellanox MCP7Y系列）
3. 检查端口信号完整性：
   ```bash
   show interface transceiver detail
   ```

---

## Case ID : 046

**Error** : NCCL训练出现`Got completion with error 12, opcode 0, len 0, vendor err 129 (Recv)`，环境为香港-硅谷专线，RTT 180ms。

**Root cause** :
- Error 12：`IBV_WC_RETRY_EXC_ERR`（传输重试次数超限）
- Vendor Err 129：Mellanox设备特定错误码，表示对端无响应
- Opcode 0：RDMA Send操作
- 触发条件：当RTT > 200ms时，NCCL默认超时（4.096µs × 2^20 ≈ 4.3秒）不足

**Action plan** :
1. 调整NCCL超时参数：
   ```bash
   export NCCL_IB_TIMEOUT=22  # 4.096µs × 2^22 ≈ 17.2秒
   export NCCL_IB_RETRY_CNT=7 # 默认重试7次
   export NCCL_ASYNC_ERROR_HANDLING=1 # 快速失败
   ```
2. 启用梯度压缩（8-bit量化）
3. 使用ECN优先级+8MB分片并行传输

---

## Case ID : 047

**Error** : NCCL训练出现`Got completion from peer with error 4, opcode 32601, len 32600, vendor err 81 (Send)`。

**Root cause** :
- Error 4：`IBV_WC_LOC_PROT_ERR`（本地保护错误）
- Vendor Err 81：内存保护密钥（RKey）不匹配或内存越界
- Opcode 32601：变形非法操作码（通常表示WR已损坏）

**Action plan** :
1. 检查内存注册（Memory Registration）的RKey是否正确
2. 验证发送数据长度是否超过MR限制
3. 检查QP状态是否正常
4. 重新注册内存区域并更新RKey

---

## Case ID : 048

**Error** : NCCL AllReduce 1800秒超时，`Watchdog caught collective operation timeout: WorkNCCL(OpType=ALLREDUCE, Timeout(ms)=1800000) ran for 1800995 milliseconds before timing out.`

**Root cause** :
- Timeout(ms)=1800000：默认30分钟超时阈值
- 实际运行时间1800995ms：超过阈值995ms触发
- OpType=ALLREDUCE：发生在全局梯度同步阶段
- 当错误出现在epoch边界（如`finish 890000`后），通常是Checkpoint保存导致网络中断

**Action plan** :
1. 检查Checkpoint保存是否导致网络中断
2. 调整NCCL超时参数：
   ```bash
   export NCCL_IB_TIMEOUT=22
   ```
3. 优化Checkpoint策略，避免与AllReduce冲突
4. 检查存储系统状态

---

## Case ID : 049

**Error** : ConnectX-6 Lx + RHEL 9.3/9.4 + Lenovo SR655 v3环境下，驱动加载失败，报错`wait_func:1151:(pid 20): QUERY_ISSI(0x10a) timeout`和`probe of 0000:21:00.0 failed with error -110`。

**Root cause** :
- Error -110：`ETIMEDOUT`（连接超时）
- QUERY_ISSI(0x10a)：查询InfiniBand子网服务接口固件命令
- 触发条件：BIOS版本2.14.1与SR-IOV冲突（Dell PowerEdge 15G AMD平台）
- 固件预初始化超过120秒

**Action plan** :
1. 升级或降级BIOS版本，解决与SR-IOV的冲突
2. 检查固件状态：
   ```bash
   mlxfwmanager -status
   ```
3. 如果固件卡在校准状态，尝试重新刷写固件
4. 禁用SR-IOV临时测试：
   ```bash
   mlxconfig -d /dev/mst/mt4119_pciconf0 set SRIOV_EN=0
   ```

---

## Case ID : 050

**Error** : SR-IOV场景下创建8个VF时，第7-8个VF初始化失败，报错`ENABLE_HCA(0x104) timeout`。

**Root cause** :
- ENABLE_HCA(0x104)：启用主机通道适配器命令失败
- VF数量：创建8个VF时，第7-8个VF失败（前6个成功）
- PCI差异：失败VF的PCI槽位号与前6个不同（`type 7f class 0xffffff`）

**Action plan** :
1. 检查BIOS中SR-IOV配置是否支持8个VF
2. 确认PCIe插槽是否有足够的资源分配
3. 尝试减少VF数量或更换PCIe插槽
4. 更新主板BIOS和网卡固件
5. 检查系统日志确认资源分配失败原因

---

## Case ID : 051

**Error** : 驱动日志显示`MANAGE_PAGES(0x108) timeout`和`failed reclaiming pages: err -110`。

**Root cause** : hairpin流队列未销毁导致内存泄漏（CVE-2021-47246）。

**Action plan** :
1. 升级内核到修复版本
2. 重启网卡驱动释放内存
3. 检查hairpin流配置：
   ```bash
   ethtool -S <interface> | grep hairpin
   ```
4. 监控内存使用情况：
   ```bash
   cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/*page*
   ```

---

## Case ID : 052

**Error** : UFM告警Alarm ID 110：Symbol Error计数超过200（Warning阈值）。

**Root cause** :
- Symbol Errors = 3121：物理层信号完整性问题（光模块/光纤）
- RcvSwRelayErrors = 48545：路由表错误（DLID/VL映射问题）
- XmtDiscard = 9789：拥塞或链路故障导致的TX丢弃

**Action plan** :
1. 检查告警阈值配置：
   | Alarm ID | 名称 | 严重级别 | 默认阈值 |
   |:--------:|------|:-------:|:-------:|
   | 110 | Symbol Error | Warning | 200 |
   | 111 | Link Error Recovery | Minor | 1 |
   | 112 | Link Downed | Critical | 1 |
   | 115 | Port Receive Switch Relay Errors | Minor | 999 |
   | 116 | Port Xmit Discards | Minor | 200 |
   | 120 | Excessive Buffer Overrun Errors | Minor | 100 |
2. 使用`ibqueryerrors -c`扫描全网络，标记超阈值端口
3. 使用`perfquery -x <lid> <port>`查看具体端口扩展计数器
4. 更换故障硬件（光模块/光纤/线缆）

---

## Case ID : 053

**Error** : Lustre文件系统RDMA超时，日志显示`Timed out tx for 10.10.0.29@o2ib: 0 seconds`和`recovery failed with -110/-113`。

**Root cause** :
- Error -110：`ETIMEDOUT`（连接超时）
- Error -113：`EHOSTUNREACH`（主机不可达）
- TX Timeout：10秒无响应触发
- 队列状态：`transmit queue 13 timed out`，队列头尾指针均为0（完全阻塞）
- RQN 0xc01049：Receive Queue Number，当前队列大小为0（接收缓冲区耗尽）

**Action plan** :
1. 检查物理链路状态：
   ```bash
   ibstat | grep -E "state|rate"
   ```
2. 检查对端节点状态和网络连通性
3. 重启Lustre客户端或重新挂载文件系统
4. 调整LNet超时参数：
   ```bash
   lctl set_param lnet.transaction_timeout=30
   ```

---

## Case ID : 054

**Error** : SoftRoCE与硬件RoCE不兼容，客户端报错`Failed status 12: wr_id 0 syndrom 0x81`，服务端卡在`Waiting for client`。

**Root cause** :
- Status 12：`IBV_WC_RETRY_EXC_ERR`
- Syndrom 0x81：SoftRoCE（rxe）与硬件RoCE（mlx5）协议版本不匹配

**Action plan** :
1. 统一使用硬件RoCE或SoftRoCE，避免混用
2. 如果必须使用SoftRoCE，确保版本兼容
3. 检查RoCE类型：
   ```bash
   ibv_devinfo -v | grep "transport type"
   ```
4. 在测试环境中统一配置

---

## Case ID : 055

**Error** : `ib_write_bw`跨CIDR失败，客户端报错`Failed status 12: wr_id 0 syndrom 0x81`，服务端报错`Couldn't read remote address`。

**Root cause** :
- GID：`10.16.255.11` vs `10.22.01.10`（不同子网）
- QPN：0x01bf（客户端）↔ 0x00c8（服务端）
- PSN：0xa7999c（客户端起始包序列号）
- 跨子网路由配置不正确

**Action plan** :
1. 检查路由配置确保跨子网可达
2. 使用正确的GID索引（RoCEv2）：
   ```bash
   ib_write_bw -d mlx5_0 -x 3  # 使用GID索引3
   ```
3. 检查防火墙是否放行UDP 4791端口
4. 验证网络连通性：
   ```bash
   ping <remote_ip>
   traceroute <remote_ip>
   ```

---

## Case ID : 056

**Error** : `Local QP Operation Error (12): Transport Retry Counter Exceeded`

**Root cause** : The requester sent a packet but never received an ACK/NACK after multiple retries. Common causes include:
1. **Physical Link Issues**: Run `ibstat` or `ibv_devinfo`. Ensure the state is `PORT_ACTIVE`
2. **MTU Mismatch**: If the host MTU is 4200 but the switch port is 1500, small handshake packets pass, but large data packets are dropped
3. **Congestion/PFC**: If the network is heavily congested and PFC (Priority Flow Control) is not working, packets are dropped, leading to retries

**Action plan** :
1. Align MTU across the fabric (Host, Switch, and Storage). Use `ibv_devinfo -v` to check `active_mtu`
2. Ensure **PFC** and **ECN** are enabled on the switch for the specific RoCE priority (usually Priority 3 or 4)
3. Check physical link status with `ibstat` or `ibv_devinfo`

---

## Case ID : 057

**Error** : `Local Length Error (1)`

**Root cause** : The application tried to send or receive data that didn't fit the allocated buffer.
1. **Sender Side**: The message size exceeds the maximum supported by the HCA port (check `max_msg_sz` in `ibv_devinfo`)
2. **Receiver Side**: The posted Receive Work Request (WR) buffer is smaller than the incoming message

**Action plan** :
1. Verify the application's `ibv_post_recv` buffer size matches the `ibv_post_send` size
2. Check for memory corruption where the length variable might have been overwritten
3. Validate buffer sizes against `max_msg_sz` in `ibv_devinfo` output

---

## Case ID : 058

**Error** : Network-wide hang where traffic stops across multiple nodes. No specific RDMA error; applications simply time out or "hang."

**Root cause** : PFC Deadlock & Pause Frame Storm. A loop in the network or a faulty NIC sends a constant stream of Pause frames, causing a "storm." If one port is constantly sending Pause frames, it's pushing back on the whole network.

**Action plan** :
1. Check Switch Counters: Look for `Pause Frames` on switch ports
2. Enable **PFC Watchdog** on the switches. This will "punish" a port that sends pause frames for too long by dropping its traffic or shutting the port
3. Ensure the network topology is non-blocking (e.g., Clos/Leaf-Spine)
4. Check for circular dependencies in the network topology

---

## Case ID : 059

**Error** : `Remote Access Error (10)` or `Remote Operation Error`

**Root cause** : R_Key / L_Key Violation (`IBV_WC_REM_ACCESS_ERR`). The remote side rejected the RDMA operation because it didn't have permission to access that memory.
1. **Invalid Key**: The `r_key` (Remote Key) sent by the requester does not match the key generated during memory registration (`ibv_reg_mr`) on the responder
2. **Permission Mismatch**: You tried to do an `RDMA_WRITE` to a region registered only for `RDMA_READ`

**Action plan** :
1. Ensure `r_key` exchange happens correctly between client and server
2. Check `access_flags` during `ibv_reg_mr` (e.g., must include `IBV_ACCESS_REMOTE_WRITE`)
3. Verify memory region permissions match the intended RDMA operations

---

## Case ID : 060

**Error** : `rdma_connect` fails with `Connection Refused` or times out

**Root cause** : GID Mismatch (RoCE v1 vs v2). Connection fails during the "connection manager" (rdma_cm) phase.
1. **RoCE Version**: One node is using RoCE v1 (Layer 2) and the other v2 (Layer 3/UDP)
2. **GID Index**: RoCE v2 usually uses a specific GID index (e.g., Index 3 for IPv4)

**Action plan** :
1. Explicitly set the GID index in your application or system config
2. Use `cat /sys/class/infiniband/<dev>/ports/1/gids/3` to verify the IP-to-GID mapping
3. Run `show_gids` to check RoCE version and GID index
4. Ensure both ends use consistent RoCE versions

---

## Case ID : 061

**Error** : `Work Request Flushed Error (13)`

**Root cause** : QP State "Sticky" in Error State. Once a Queue Pair (QP) hits an error, it stops processing all future requests. When one Work Request fails (e.g., Retry Exceeded), the HCA flushes all *other* pending requests in that queue. The QP transitions to the `ERR` state and stays there.

**Action plan** :
1. Applications must detect the error, destroy the QP, and recreate it
2. Or transition it back to `INIT` -> `RTR` -> `RTS`
3. Implement proper error handling in the application to detect QP errors

---

## Case ID : 062

**Error** : NCCL Timeout Error 12 with Vendor Error 129 (Cross-Datacenter)

**Root cause** :
- **Error Code 12**: `IBV_WC_RETRY_EXC_ERR` - Transport retry counter exceeded
- **Vendor Error 129**: Mellanox-specific code indicating no response from peer after maximum retries
- **Opcode 0**: RDMA Send operation
- **RTT 180ms**: Default NCCL timeout (4.096µs × 2^20 ≈ 4.3 seconds) insufficient for 180ms RTT with packet loss

**Action plan** :
1. Increase timeout for long-distance links:
   ```bash
   export NCCL_IB_TIMEOUT=22  # 4.096µs × 2^22 ≈ 17.2 seconds (default is 18 ≈ 1.07s)
   export NCCL_IB_RETRY_CNT=13  # Increase from default 7
   export NCCL_ASYNC_ERROR_HANDLING=1  # Fast fail on unrecoverable errors
   export NCCL_IB_AR_THRESHOLD=0  # Disable adaptive routing for stability
   ```
2. Prevention: Always calculate timeout as: `Timeout > RTT_max × retry_count × 2`

---

## Case ID : 063

**Error** : Symbol Error Storm (Physical Layer Degradation)

**Root cause** :
- **SymbolErrors 3121**: Physical layer signal integrity issues (31x threshold)
- **LinkErrorRecovery 45**: Link has recovered 45 times (unstable)
- **RcvSwRelayErrors 48545**: Switch forwarding errors (routing table corruption)

**Action plan** :
1. Check physical state: `ibstat | grep -A10 "Port 1:"`
2. Check optical power levels: `smpquery -C mlx5_0 -P 1 PT`
3. Isolate the issue: Move cable to different port - if errors follow, it's the cable
4. Replace AOC cable with vendor-certified model (Mellanox MCP7Y00 series)
5. Clean fiber connectors with IPA (Isopropyl Alcohol) wipes
6. Check bend radius (minimum 30mm for fiber)

---

## Case ID : 064

**Error** : mlx5_core Driver Command Timeout (-110)

**Root cause** :
- **Error -110**: `ETIMEDOUT` - Kernel driver command timeout
- **QUERY_ISSI(0x10a)**: Query InfiniBand Subnet Service Interface firmware command
- **120000 MS**: 120 seconds firmware initialization timeout
- **PID 20**: Kernel thread (kworker)
- BIOS SR-IOV initialization bug with AMD EPYC platforms

**Action plan** :
1. Check BIOS version: `dmidecode -t bios | grep Version`
2. Check SR-IOV settings: `lspci -vvvs 0000:21:00.0 | grep -i sriov`
3. Disable SR-IOV in BIOS or kernel: `mlx5_core.num_vfs=0`
4. Downgrade BIOS to 2.13.x or upgrade to 2.15+
5. Firmware recovery if needed: `echo 1 > /sys/bus/pci/devices/0000:21:00.0/remove && echo 1 > /sys/bus/pci/rescan`

---

## Case ID : 065

**Error** : PFC Deadlock with CNP Reflection Attack

**Root cause** : Improper QoS configuration where CNP (Priority 7) shares buffers with RoCE data (Priority 3). When PFC triggers on Priority 3, it blocks Priority 7 in shared buffer architectures.

**Action plan** :
1. Enable PFC Deadlock Detection:
   ```bash
   dcb pfc deadlock-detect enable
   dcb pfc deadlock-detect interval 15
   dcb pfc deadlock-recovery interval 15
   dcb pfc deadlock-auto-recovery
   ```
2. Configure Strict Priority Queuing for CNP (allow drops for CNP traffic)
3. Never enable PFC on CNP traffic class

---

## Case ID : 066

**Error** : Local Protection Error (Vendor Err 81) - MR Mismatch

**Root cause** :
- **Error 4**: `IBV_WC_LOC_PROT_ERR` - Local Protection Error
- **Vendor Err 81**: Memory Region (MR) protection key mismatch or out-of-bounds access
- **Opcode 32601**: Invalid opcode (garbage value) - indicates WR structure corruption
- **Len 32600**: Mismatched length (likely buffer overflow)

**Action plan** :
1. Use GPU Direct RDMA correctly with proper registration sequence
2. Pin GPU memory to prevent migration: `cudaMemAdvise(gpu_buf, size, cudaMemAdviseSetReadMostly, 0)`
3. Verify nvidia_peermem or nvidia_p2p module loaded: `lsmod | grep nvidia`
4. Disable PCIe relaxed ordering if unsupported: `mlxconfig -d /dev/mst/mt4115_pciconf0 set PCI_WR_ORDERING=1`

---

## Case ID : 067

**Error** : SoftRoCE vs Hardware RoCE Incompatibility (Syndrom 0x81)

**Root cause** :
- **Status 12**: `IBV_WC_RETRY_EXC_ERR`
- **Syndrom 0x81**: SoftRoCE specific error - protocol version mismatch between software and hardware implementation
- SoftRoCE implements RoCEv2 protocol differently than hardware (especially header formats and CRC handling)

**Action plan** :
1. Disable SoftRoCE: `modprobe -r rxe && echo "blacklist rxe" >> /etc/modprobe.d/blacklist-rdma.conf`
2. Configure only hardware devices
3. Force specific device: `export MLX5_SINGLE_THREADED=1`
4. Standardize on hardware RoCE for production

---

## Case ID : 068

**Error** : RNR Retry Exceeded (Receive Not Ready)

**Root cause** :
- **Status 13**: `IBV_WC_RNR_RETRY_EXC_ERR` - RNR NAK retry counter exceeded
- **RNR**: Receiver Not Ready - Receiver has no Receive WR posted on the QP
- Storage server cannot post Receive WRs fast enough to keep up with incoming write requests

**Action plan** :
1. Increase RNR retry count: `attr.rnr_retry = 7` and `export NCCL_IB_RNR_RETRY=7`
2. Use batched receive posting (`ibv_post_recv` with burst of 16-32 WRs)
3. Increase SRQ size: `attr.attr.max_wr = 8192`
4. Tune interrupt affinity: `echo 20-23 > /sys/class/infiniband/mlx5_0/irq_affinity_hint`

---

## Case ID : 069

**Error** : Adaptive Routing Timeout (NCCL AllReduce Hang)

**Root cause** : Adaptive Routing (AR) causes packet spraying across multiple paths. While good for throughput, it breaks RC QPs' in-order delivery assumptions. NCCL uses RC QPs by default.

**Action plan** :
1. Disable Adaptive Routing: `export NCCL_IB_AR_THRESHOLD=0`
2. Force ordered delivery: `export NCCL_IB_TC=64` and `export NCCL_IB_SL=0`
3. Use DC QPs (Datagram) instead of RC: `export NCCL_IB_QPS_PER_CONNECTION=4`
4. Ensure Ring algorithm closes within same Leaf switch

---

## Case ID : 070

**Error** : Firmware Version Incompatibility (Link Training Failure)

**Root cause** :
- **Reason 0x80000020**: Link training sequence failed between NIC and switch
- **MTECR**: Memory-mapped Temperature Error Configuration Register inaccessible
- **Status 4**: Bus error (PCIe transaction failed)
- Firmware 3.10.5000 introduced new link training parameters incompatible with older NIC firmware

**Action plan** :
1. Emergency downgrade: `image boot next` or `mlxfwmanager -u <old_firmware.bin> -y`
2. Recovery via serial console to switch bootloader
3. Upgrade NIC firmware to 14.25.xxx or higher before switch upgrade
4. Follow vendor HCL (Hardware Compatibility List)

---

## Case ID : 071

**Error** : Multi-Path Routing Asymmetry (vSAN Performance Drop)

**Root cause** : VMkernel routing table uses different paths for TX and RX due to ECMP (Equal-Cost Multi-Path) hashing. Server A→B goes via Spine 1, B→A goes via Spine 2. Spine 2 has congestion but ECN marks are lost or not acted upon by VMware's RoCE stack.

**Action plan** :
1. Force symmetric routing: `ip route <vSAN_subnet> <next_hop> no-ecmp`
2. Use consistent hashing: `port-channel load-balance src-dst-ip`
3. Tune ECN thresholds: Lower thresholds to trigger earlier
4. Disable NIC teaming for RDMA uplinks (use active/passive instead of LACP)

---

## Case ID : 072

**Error** : GPU Memory Eviction (Peer-to-Peer Breakdown)

**Root cause** :
- **Vendor Err 0x88**: NVIDIA-specific, indicates GPU memory page eviction
- **CUDA error**: GPU context lost, likely due to watchdog or OOM killer
- **BAR1**: GPU Base Address Register 1 (memory-mapped IO) deallocated
- Linux OOM killer or GPU watchdog timer triggers during long RDMA transfers (>10 seconds)

**Action plan** :
1. Disable GPU watchdog: `export CUDA_LAUNCH_BLOCKING=0` and `export NCCL_P2P_LEVEL=SYS`
2. Lock GPU memory: `torch.cuda.empty_cache()` and `tensor = tensor.pin_memory()`
3. Kernel parameters: `vm.swappiness=10` and `vm.zone_reclaim_mode=0`
4. Enable GPU persistence: `/usr/bin/nvidia-persistence-mode --enable`

---

## Case ID : 073

**Error** : Checksum Offload Mismatch (Silent Data Corruption)

**Root cause** : RoCEv2 uses UDP checksum (optional in hardware). If NIC calculates wrong checksum (hardware bug) or switch rewrites UDP header without updating checksum, receiver NIC drops packet silently OR delivers corrupted data.

**Action plan** :
1. Disable checksum offload: `ethtool -K eth0 rx-checksumming off tx-checksumming off`
2. Update firmware: CX-5 to 16.32.xxxx or higher
3. Force checksum validation in application using RDMA with Immediate Data
4. Monitor for `rx_crc_errors` in `ethtool -S`

---

## Case ID : 074

**Error** : Port state shows `State: Down` or `State: Initializing`

**Root cause** :
1. **Physical connection issues**: Optical module/cable failure, port not properly inserted
2. **Subnet Manager not running**: IB network lacks SM (OpenSM) → port stuck at `Initializing`
3. **Switch port disabled**: Switch-side port is `admin down`

**Action plan** :
1. Check physical link: `ethtool eth1 | grep "Link detected"`
2. Check SM status: `systemctl status opensm`
3. Restart port: `ibportstate -D 0x0002c90300abcdef1234 -P 1 -S down && sleep 2 && ibportstate -D 0x0002c90300abcdef1234 -P 1 -S up`
4. Replace optical module if CRC errors > 0

---

## Case ID : 075

**Error** : PCIe Link Degradation (Gen4→Gen3)

**Root cause** :
- Motherboard PCIe slot insufficient power
- BIOS PCIe settings error (e.g., forced Gen3)
- Gold finger oxidation/poor contact

**Action plan** :
1. Confirm current link state: `lspci -vvv -s 04:00.0 | grep -A 10 "LnkCap\|LnkSta"`
2. Check BIOS settings: Ensure Gen4 is enabled
3. Check NIC temperature: `sensors | grep -i mellanox`
4. Replace PCIe slot (prefer CPU direct slot)
5. Verify: `ib_write_bw -d mlx5_0 --report_gbits` should show >180 Gb/s for 200G NIC

---

## Case ID : 076

**Error** : Driver/Firmware Version Mismatch

**Root cause** :
- OFED driver requires specific firmware version
- Firmware downgraded without同步 updating driver

**Action plan** :
1. Check current versions: `ofed_info -s`, `mlxfwmanager --query`, `ibstat | grep "Firmware ver"`
2. Upgrade firmware: `mlxfwmanager --update -y`
3. Or downgrade driver: `./mlnxofedinstall --version 5.4-3.0.3.0`
4. Check compatibility matrix at https://network.nvidia.com/support/firmware/

---

## Case ID : 077

**Error** : nv_peer_mem Module Loading Failure (GPUDirect RDMA)

**Root cause** :
1. **CUDA 12.2+ deprecated nv_peer_mem**: Use `nvidia-peermem` instead
2. **NVIDIA driver incompatible with OFED version**
3. **Unified Memory (UVM) conflict**

**Action plan** :
1. For CUDA 12.2+: Use nvidia-peermem
   ```bash
   rmmod nv_peer_mem 2>/dev/null
   modprobe nvidia-peermem
   echo "nvidia-peermem" > /etc/modules-load.d/nvidia-peermem.conf
   ```
2. Disable UVM: `nvidia-smi -pm 1`
3. Verify GDR: `ib_write_bw -d mlx5_0 --report_gbits --use-gdr` should show "GDR: enabled"

---

## Case ID : 078

**Error** : PFC Not Enabled Causing RoCE Packet Loss

**Root cause** :
- RoCE requires lossless network, but switch PFC priority 3 not enabled
- 0.001% packet loss rate causes RDMA performance to drop off a cliff

**Action plan** :
1. Check PFC status: `ethtool -a eth1`
2. Enable PFC on server: `ethtool -A eth1 rx on tx on`
3. Enable PFC on switch:
   ```bash
   interface ethernet 1/1
     priority-flow-control priority 3 enable
     priority-flow-control deadlock-detect enable
     priority-flow-control deadlock-recovery-time 1500
   ```
4. Verify: `ib_write_bw -d mlx5_0 -s 1048576 -t 60` should show <0.0001% loss rate

---

## Case ID : 079

**Error** : GID Index Mismatch (RoCEv2 Connection Failure)

**Root cause** :
- Multi-NIC/multi-IP environment, RDMA_CM automatically selects wrong GID
- GID index 3 usually corresponds to RoCEv2 (IPv4), index 0 corresponds to RoCEv1 (IPv6)

**Action plan** :
1. View GID table: `show_gids mlx5_0`
2. Force specify GID index: `ib_write_bw -d mlx5_0 -R -g 3 192.168.1.100`
3. NCCL environment variable: `export NCCL_IB_GID_INDEX=3`
4. Bind specific IP: `export NCCL_SOCKET_IFNAME=eth1`
5. Disable IPv6: `sysctl -w net.ipv6.conf.all.disable_ipv6=1`

---

## Case ID : 080

**Error** : MTU Mismatch Causing Fragmentation Packet Loss

**Root cause** :
- Inconsistent MTU settings between both ends (e.g., one end 9000, one end 1500)
- Large packets trigger IP fragmentation, but RoCE does not support fragmentation

**Action plan** :
1. Check MTU: `cat /sys/class/net/eth1/mtu` and `ip link show eth1 | grep mtu`
2. Unified MTU=9000 (Jumbo Frame): `ip link set eth1 mtu 9000`
3. Switch side sync config: `interface ethernet 1/1; mtu 9216`
4. Verify: `ping -s 8972 -M do 192.168.1.101` (8972 = 9000 - 28(IP+ICMP header))

---

## Case ID : 081

**Error** : IBV_WC_RETRY_EXC_ERR (QP Retry Exceeded)

**Root cause** :
1. **Network packet loss**: PFC not enabled/configured incorrectly
2. **QP attribute mismatch**: Both ends QP `max_send_wr`/`max_recv_wr` inconsistent
3. **Remote end not responding**: Peer process crashed/firewall blocking

**Action plan** :
1. Check QP status: `ibv_devinfo -v | grep -A 20 "port"`
2. Extend timeout test: `ib_write_bw -d mlx5_0 -T 22 192.168.1.100`
3. Check firewall: `iptables -L -n | grep 18515`
4. Increase QP retry count: `export NCCL_IB_TIMEOUT=22` and `export NCCL_IB_RETRY_CNT=7`

---

## Case ID : 082

**Error** : Memory Registration Failure (Couldn't allocate MR)

**Root cause** :
- **ulimit limit**: Regular user `memlock` limit too low
- **/proc/sys/vm/max_map_count insufficient**: MR count exceeded
- **HugePage not configured**: Large memory registration requires HugePage

**Action plan** :
1. Increase memlock limit in `/etc/security/limits.conf`:
   ```
   * soft memlock unlimited
   * hard memlock unlimited
   ```
2. Increase max_map_count: `echo 262144 > /proc/sys/vm/max_map_count`
3. Configure HugePage: `echo 2048 > /proc/sys/vm/nr_hugepages`
4. Verify: `ulimit -l` should show unlimited

---

## Case ID : 083

**Error** : QP Creation Failure (Failed to modify QP to RTR)

**Root cause** :
- **QP count exceeded**: Single NIC default QP limit 8192
- **CQ size insufficient**: Completion Queue overflow
- **NUMA not affine**: QP created on wrong NUMA node

**Action plan** :
1. Increase QP limit: `echo 16384 > /sys/module/mlx5_core/parameters/log_num_qp`
2. NUMA binding: `numactl --cpunodebind=0 --membind=0 ib_write_bw -d mlx5_0 192.168.1.100`
3. Ceph optimization: `ms_async_rdma_qp_count = 8` and `ms_async_rdma_cq_size = 8192`

---

## Case ID : 084

**Error** : PFC Deadlock (Network-wide Hang with No Logs)

**Root cause** :
- Network topology has micro-loop
- Multiple switches trigger PFC simultaneously, forming deadlock ring

**Action plan** :
1. Detect PFC storm on switch: `show priority-flow-control deadlock-detection status`
2. Monitor CNP on server: `cnstat -i eth1`
3. Topology analysis: `ibdiagnet -v -r`
4. Enable PFC deadlock detection:
   ```bash
   interface ethernet 1/1
     priority-flow-control deadlock-detect enable
     priority-flow-control deadlock-recovery-time 1500
   ```
5. Deploy DCQCN congestion control

---

## Case ID : 085

**Error** : DCQCN Parameters Not Optimized Causing Performance Fluctuation

**Root cause** :
- DCQCN default parameters not suitable for AI training traffic patterns
- Switch ECN marking threshold too low, triggering congestion notification too early

**Action plan** :
1. Adjust switch ECN threshold:
   ```bash
   dcb buffer pool roce
     pool-size 50%
     ecn-marking-threshold 20000
     ecn-drop-threshold 30000
   ```
2. Adjust NIC DCQCN parameters:
   ```bash
   echo 1 > /sys/module/mlx5_core/parameters/dcqcn_cca_param_valid
   echo 1000000 > /sys/module/mlx5_core/parameters/dcqcn_rp_time_reset
   echo 1000 > /sys/module/mlx5_core/parameters/dcqcn_rp_byte_reset
   ```
3. Verify: `ib_write_bw -d mlx5_0 -t 300` for 300 seconds to observe bandwidth stability

---

## Case ID : 086

**Error** : NCCL Timeout (Cross-subnet IP Selection Error)

**Root cause** :
- Multi-NIC environment, NCCL automatically selects non-RDMA dedicated NIC
- Cross-subnet communication triggers routing, increased latency causes timeout

**Action plan** :
1. Force specify RDMA NIC IP: `export NCCL_SOCKET_IFNAME=eth1`
2. Disable IB capability for non-RDMA NICs:
   ```bash
   echo 0 > /sys/class/infiniband/mlx5_bond_0/ports/1/gid_attrs/roce/enable
   echo 0 > /sys/class/infiniband/mlx5_2/ports/1/gid_attrs/roce/enable
   ```
3. Increase timeout: `export NCCL_IB_TIMEOUT=22` and `export NCCL_IB_RETRY_CNT=14`

---

## Case ID : 087

**Error** : NCCL QP Count Explosion (Multi-node Training Hang)

**Root cause** :
- Each GPU↔GPU connection creates independent QP
- 8 nodes × 8 GPU = 64 GPU → 64×63=4032 QP/node
- Exceeds NIC QP limit (default 8192) but CQ overflow occurs first

**Action plan** :
1. Limit QP count: `export NCCL_IB_QPS_PER_CONNECTION=4` and `export NCCL_MAX_NCHANNELS=4`
2. Increase CQ size: `echo 16384 > /sys/module/mlx5_core/parameters/log_num_cq`
3. Upgrade to NCCL 2.18+ for QP sharing feature

---

## Case ID : 088

**Error** : NCCL Conflict with Firewall

**Root cause** :
- Firewall blocks RDMA_CM port (4791) or dynamic ports (18515+)
- SELinux prevents RDMA operations

**Action plan** :
1. Open RDMA ports:
   ```bash
   firewall-cmd --permanent --add-port=4791/tcp
   firewall-cmd --permanent --add-port=4791/udp
   firewall-cmd --permanent --add-port=18515-18615/tcp
   firewall-cmd --reload
   ```
2. Disable firewall: `systemctl stop firewalld && systemctl disable firewalld`
3. SELinux: `setsebool -P allow_rdma 1` or `setenforce 0`

---

## Case ID : 089

**Error** : Ceph RDMA QP Count Explosion

**Root cause** :
- Ceph async messenger creates independent QP for each OSD connection
- 100 OSD cluster → 10,000+ QP → NIC SRAM overflow
- Memory registration overhead grows linearly with IO size

**Action plan** :
1. ceph.conf optimization:
   ```ini
   [global]
   ms_type = async
   ms_async_rdma_device_name = mlx5_0
   
   [osd]
   ms_async_rdma_qp_count = 8
   ms_async_rdma_cq_size = 8192
   bluestore_cache_size_hdd = 4G
   bluestore_cache_size_ssd = 8G
   ```
2. Restart OSD: `systemctl restart ceph-osd@0`

---

## Case ID : 090

**Error** : Lustre LNet Timeout (Metadata Operation Hang)

**Root cause** :
- MDS and client RDMA connection not reused
- Metadata operations (create/unlink) trigger frequent QP create/destroy
- Default 10 second timeout insufficient for large-scale metadata operations

**Action plan** :
1. Increase LNet connection cache: `lctl set_param lnet.peers=2048`
2. Extend timeout: `lctl set_param timeout=30`
3. Enable RDMA connection reuse: `mount -t lustre -o rdma,connect_timeout=30s MGS:/fs /mnt/lustre`
4. MDS side: `lctl set_param mdt.*.connect_timeout=60` and `lctl set_param mdt.*.max_rpcs_in_flight=1024`

---

## Case ID : 091

**Error** : Vitastor RDMA 32KB+ Performance Cliff

**Root cause** :
- Vitastor default inline threshold too low (128 bytes)
- 32KB IO triggers PCIe round-trip, increasing latency
- RDMA inline data not enabled

**Action plan** :
1. Increase inline threshold: `echo 2048 > /sys/module/mlx5_core/parameters/log_max_inline_data`
2. Vitastor config:
   ```json
   {
     "immediate_commit": "all",
     "rdma_inline_size": 2048
   }
   ```
3. Verify: `ib_send_lat -d mlx5_0 -s 32768` should show <5μs latency

---

## Case ID : 092

**Error** : ibdiagnet Fabric-wide Diagnosis

**Root cause** : Need to quickly locate fault points in 100-node cluster performance degradation

**Action plan** :
1. Full network scan (execute on SM node): `ibdiagnet -v -r --timeout 300`
2. Key output file analysis:
   - `ibdiagnet2.sm.log`: SM status - `grep -i "error\|warning" ibdiagnet2.sm.log`
   - `ibdiagnet2.net_dump`: Error port list
   - `ibdiagnet2.db_csv`: Full topology - `awk -F',' '$10>0 {print $1,$2,$10}' ibdiagnet2.db_csv`
3. Error type identification:
   - `symbol_error > 0` → Physical layer issue (optical module/cable)
   - `link_downed > 10` → Link frequent UP/DOWN (jitter)
   - `port_rcv_errors > 0` → Packet loss (PFC/ECN config issue)

---

## Case ID : 093

**Error** : Switch Telemetry Real-time Monitoring

**Root cause** : Production environment needs 7×24 hour buffer watermark monitoring

**Action plan** :
1. Enable gRPC Telemetry on switch:
   ```bash
   telemetry server
   telemetry destination-profile prometheus
     collector 10.0.0.100 port 50051 protocol grpc
   telemetry sensor-group buffer_group
     sensor-path /spectrum/buffer/usage
     sensor-path /spectrum/port/statistics
   telemetry subscription buffer_sub
     sensor-group buffer_group sample-interval 1000
     destination-profile prometheus
   ```
2. Prometheus scrape config for switch
3. Grafana dashboard key metrics:
   - `buffer_usage_percent > 80%` → Alert
   - `pfc_pause_frames_tx_rate > 1000/s` → PFC storm
   - `port_xmit_wait > 1000000` → Congestion

---

## Case ID : 094

**Error** : Port Status Abnormal (State: Down / Initializing)

**Root cause** :
1. **Physical connection problem**: Optical module/cable failure, port not inserted tightly
2. **Subnet manager not running**: IB network missing SM (OpenSM) → port stuck at `Initializing`
3. **Switch port disabled**: Switch-side port is `admin down`

**Action plan** :
1. Check physical link: `ethtool eth1 | grep "Link detected"` (RoCE scenario) or `cat /sys/class/infiniband/mlx5_0/ports/1/phys_state`
2. Check SM status: `systemctl status opensm` and `opensm -g`
3. Switch side check: `show interface ethernet 1/1 status` (RoCE) or `ibcheckerrors -e` (IB network)
4. Start SM: `systemctl start opensm`
5. Restart port: `ibportstate -D 0x0002c90300abcdef1234 -P 1 -S down && sleep 2 && ibportstate -D 0x0002c90300abcdef1234 -P 1 -S up`
6. Replace optical module if CRC errors > 0 and continue to grow

---

## Case ID : 095

**Error** : PCIe Link Downgrade (Gen4→Gen3)

**Root cause** :
- Motherboard PCIe slot insufficient power supply
- BIOS PCIe settings error (e.g., forced Gen3)
- Gold finger oxidation/poor contact

**Action plan** :
1. Confirm current link state: `lspci -vvv -s 04:00.0 | grep -A 10 "LnkCap\|LnkSta"`
2. Check BIOS settings: Enter BIOS → Advanced → PCIe Configuration → Confirm Gen4 enabled
3. Check NIC temperature: `sensors | grep -i mellanox`
4. Replace PCIe slot (prefer CPU direct slot)
5. BIOS set PCIe to Gen4 forced mode
6. Clean gold finger and reinsert
7. Verify: `ib_write_bw -d mlx5_0 --report_gbits` should show >180 Gb/s for 200G NIC

---

## Case ID : 096

**Error** : Driver/Firmware Version Mismatch

**Root cause** :
- OFED driver requires specific firmware version
- Firmware downgraded without同步 updating driver

**Action plan** :
1. Check current versions: `ofed_info -s`, `mlxfwmanager --query`, `ibstat | grep "Firmware ver"`
2. Check compatibility matrix: https://network.nvidia.com/support/firmware/
3. Solution 1 - Upgrade firmware (recommended): `mlxfwmanager --update -y`
4. Solution 2 - Downgrade driver (temporary):
   ```bash
   ./mlnxofedinstall --uninstall
   ./mlnxofedinstall --version 5.4-3.0.3.0
   ```

---

## Case ID : 097

**Error** : nv_peer_mem Module Loading Failure (GPUDirect RDMA)

**Root cause** :
1. **CUDA 12.2+ deprecated nv_peer_mem**: Use `nvidia-peermem` instead
2. **NVIDIA driver and OFED version incompatible**
3. **Unified Memory (UVM) conflict**

**Action plan** :
1. Check module status: `lsmod | grep -E "nv_peer|nvidia_peer"` and `modinfo nvidia-peermem`
2. Check GPU-NIC NUMA affinity: `nvidia-smi topo -m` and `cat /sys/class/infiniband/mlx5_0/device/numa_node`
3. Check UVM status: `nvidia-smi -q | grep "Unified Memory"`
4. Solution 1 - Use nvidia-peermem for CUDA 12.2+ (recommended):
   ```bash
   rmmod nv_peer_mem 2>/dev/null
   modprobe nvidia-peermem
   echo "nvidia-peermem" > /etc/modules-load.d/nvidia-peermem.conf
   ```
5. Solution 2 - Disable UVM: `nvidia-smi -pm 1`
6. Verify GDR: `ib_write_bw -d mlx5_0 --report_gbits --use-gdr` should show "GDR: enabled"

---

## Case ID : 098

**Error** : PFC Not Enabled Causing RoCE Packet Loss

**Root cause** :
- RoCE requires lossless network, but switch PFC priority 3 not enabled
- 0.001% packet loss rate causes RDMA performance to drop off a cliff

**Action plan** :
1. Check PFC status on NIC: `ethtool -a eth1`
2. Check switch PFC: `show dcb priority-flow-control interface ethernet 1/1`
3. Detect packet loss: `watch -n 1 'cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/port_rcv_errors'`
4. Enable PFC on server: `ethtool -A eth1 rx on tx on`
5. Enable PFC on switch (Mellanox Spectrum example):
   ```bash
   interface ethernet 1/1
     priority-flow-control priority 3 enable
     priority-flow-control deadlock-detect enable
     priority-flow-control deadlock-recovery-time 1500
   ```
6. Verify: `ib_write_bw -d mlx5_0 -s 1048576 -t 60` should show <0.0001% loss rate

---

## Case ID : 099

**Error** : GID Index Mismatch (RoCEv2 Connection Failure)

**Root cause** :
- Multi-NIC/multi-IP environment, RDMA_CM automatically selects wrong GID
- GID index 3 usually corresponds to RoCEv2 (IPv4), index 0 corresponds to RoCEv1 (IPv6)

**Action plan** :
1. View GID table: `show_gids`
   ```
   DEV     PORT    INDEX   GID                                     IPv4            VER
   mlx5_0  1       0       fe80::2ecf:6eff:fe12:3456               -               v1
   mlx5_0  1       3       0000:0000:0000:0000:0000:ffff:c0a8:0164 192.168.1.100   v2
   ```
2. Force specify GID index test: `ib_write_bw -d mlx5_0 -R -g 3 192.168.1.100`
3. Solution 1 - NCCL environment variable: `export NCCL_IB_GID_INDEX=3`
4. Solution 2 - Bind specific IP: `export NCCL_SOCKET_IFNAME=eth1`
5. Solution 3 - Disable IPv6: `sysctl -w net.ipv6.conf.all.disable_ipv6=1`
6. Verify: `NCCL_DEBUG=INFO python train.py 2>&1 | grep "GID"` should show consistent GID

---

## Case ID : 100

**Error** : MTU Mismatch Causing Fragmentation Packet Loss

**Root cause** :
- Inconsistent MTU settings between both ends (e.g., one end 9000, one end 1500)
- Large packets trigger IP fragmentation, but RoCE does not support fragmentation

**Action plan** :
1. Check MTU: `cat /sys/class/net/eth1/mtu` and `ip link show eth1 | grep mtu`
2. Check switch MTU: `show interface ethernet 1/1 | grep MTU`
3. Unified set MTU=9000 (Jumbo Frame):
   ```bash
   ip link set eth1 mtu 9000
   ```
4. Permanent config in `/etc/network/interfaces`:
   ```
   auto eth1
   iface eth1 inet static
       address 192.168.1.100
       netmask 255.255.255.0
       mtu 9000
   ```
5. Switch side sync config: `interface ethernet 1/1; mtu 9216`
6. Verify: `ping -s 8972 -M do 192.168.1.101` (8972 = 9000 - 28(IP+ICMP header))

---

## Case ID : 101

**Error** : IBV_WC_RETRY_EXC_ERR (QP Retry Exceeded)

**Root cause** :
1. **Network packet loss**: PFC not enabled/configured incorrectly
2. **QP attribute mismatch**: Both ends QP `max_send_wr`/`max_recv_wr` inconsistent
3. **Remote end not responding**: Peer process crashed/firewall blocking

**Action plan** :
1. Check QP status: `ibv_devinfo -v | grep -A 20 "port"` and `cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/*_qp*`
2. Extend timeout test: `ib_write_bw -d mlx5_0 -T 22 192.168.1.100`
3. Check firewall: `iptables -L -n | grep 18515`
4. Solution 1 - Fix network lossless config (fundamental solution): Enable PFC + ECN
5. Solution 2 - Increase QP retry count: `export NCCL_IB_TIMEOUT=22` and `export NCCL_IB_RETRY_CNT=7`
6. Solution 3 - Check peer status: `ps aux | grep ib_write_bw`

---

## Case ID : 102

**Error** : Memory Registration Failure (Couldn't allocate MR)

**Root cause** :
- **ulimit limit**: Regular user `memlock` limit too low
- **/proc/sys/vm/max_map_count insufficient**: MR count exceeded
- **HugePage not configured**: Large memory registration requires HugePage

**Action plan** :
1. Check memlock limit: `ulimit -l` (usually 64KB for regular user, should be ≥65536)
2. Check max_map_count: `cat /proc/sys/vm/max_map_count` (default 65530, RDMA recommends ≥262144)
3. Check HugePage: `grep Huge /proc/meminfo`
4. Solution 1 - Increase memlock limit (recommended): Add to `/etc/security/limits.conf`:
   ```
   * soft memlock unlimited
   * hard memlock unlimited
   ```
5. Solution 2 - Increase max_map_count: `echo 262144 > /proc/sys/vm/max_map_count` and add `vm.max_map_count=262144` to `/etc/sysctl.conf`
6. Solution 3 - Configure HugePage: `echo 2048 > /proc/sys/vm/nr_hugepages` and add `vm.nr_hugepages=2048` to `/etc/sysctl.conf`
7. Verify: `ulimit -l` should show unlimited, and `ib_write_bw` should succeed for regular user

---

## Case ID : 103

**Error** : QP Creation Failure (Failed to modify QP to RTR)

**Root cause** :
- **QP count exceeded**: Single NIC default QP limit 8192
- **CQ size insufficient**: Completion Queue overflow
- **NUMA not affine**: QP created on wrong NUMA node

**Action plan** :
1. Check QP count: `cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/*_qp*` or `ibdev2netdev -v | grep mlx5_0`
2. Check NUMA affinity: `numactl --hardware` and `cat /sys/class/infiniband/mlx5_0/device/numa_node`
3. Solution 1 - Increase QP limit (requires driver restart): `echo 16384 > /sys/module/mlx5_core/parameters/log_num_qp`
4. Solution 2 - NUMA binding: `numactl --cpunodebind=0 --membind=0 ib_write_bw -d mlx5_0 192.168.1.100`
5. Solution 3 - Ceph scenario optimization: `ms_async_rdma_qp_count = 8` and `ms_async_rdma_cq_size = 8192`

---

## Case ID : 104

**Error** : PFC Deadlock (Network-wide Hang with No Logs)

**Root cause** :
- Network topology has micro-loop
- Multiple switches trigger PFC simultaneously, forming deadlock ring

**Action plan** :
1. Switch side detect PFC storm: `show priority-flow-control deadlock-detection status`
2. Server side monitor CNP: `cnstat -i eth1`
3. Topology analysis: `ibdiagnet -v -r` and check `ibdiagnet2.db_csv` for loops
4. Short-term: Restart switch to break deadlock (service interruption)
5. Long-term solutions:
   - Enable PFC deadlock detection:
     ```bash
     interface ethernet 1/1
       priority-flow-control deadlock-detect enable
       priority-flow-control deadlock-recovery-time 1500
     ```
   - Deploy DCQCN congestion control
   - Optimize topology (Spine-Leaf architecture avoid loops)

---

## Case ID : 105

**Error** : DCQCN Parameters Not Optimized Causing Performance Fluctuation

**Root cause** :
- DCQCN default parameters not suitable for AI training traffic patterns
- Switch ECN marking threshold too low, triggering congestion notification too early

**Action plan** :
1. Monitor buffer watermark: `show interface ethernet 1/1 buffer-usage`
2. Monitor CNP: `cnstat -i eth1 -t 10`
3. Check DCQCN parameters: `cat /sys/module/mlx5_core/parameters/dcqcn_*`
4. Adjust switch ECN threshold (Spectrum example):
   ```bash
   dcb buffer pool roce
     pool-size 50%
     ecn-marking-threshold 20000
     ecn-drop-threshold 30000
   ```
5. Adjust NIC DCQCN parameters:
   ```bash
   echo 1 > /sys/module/mlx5_core/parameters/dcqcn_cca_param_valid
   echo 1000000 > /sys/module/mlx5_core/parameters/dcqcn_rp_time_reset
   echo 1000 > /sys/module/mlx5_core/parameters/dcqcn_rp_byte_reset
   ```
6. Verify: `ib_write_bw -d mlx5_0 -t 300` for 300 seconds to observe bandwidth stability

---

## Case ID : 106

**Error** : NCCL Timeout (Cross-subnet IP Selection Error)

**Root cause** :
- Multi-NIC environment, NCCL automatically selects non-RDMA dedicated NIC
- Cross-subnet communication triggers routing, increased latency causes timeout

**Action plan** :
1. Check NCCL selected IP: `NCCL_DEBUG=INFO python train.py 2>&1 | grep "NET/IB : Using"`
2. Check routing table: `ip route get 192.168.1.101`
3. Solution 1 - Force specify RDMA NIC IP: `export NCCL_SOCKET_IFNAME=eth1` and `export NCCL_IB_DISABLE=0`
4. Solution 2 - Disable IB capability for non-RDMA NICs:
   ```bash
   echo 0 > /sys/class/infiniband/mlx5_bond_0/ports/1/gid_attrs/roce/enable
   echo 0 > /sys/class/infiniband/mlx5_2/ports/1/gid_attrs/roce/enable
   ```
5. Solution 3 - Increase timeout (temporary workaround): `export NCCL_IB_TIMEOUT=22` and `export NCCL_IB_RETRY_CNT=14`
6. Verify: NCCL should only use RDMA NIC

---

## Case ID : 107

**Error** : NCCL QP Count Explosion (Multi-node Training Hang)

**Root cause** :
- Each GPU↔GPU connection creates independent QP
- 8 nodes × 8 GPU = 64 GPU → 64×63=4032 QP/node
- Exceeds NIC QP limit (default 8192) but CQ overflow occurs first

**Action plan** :
1. Monitor QP/CQ usage: `watch -n 1 'cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/*_qp*'`
2. NCCL debug: `export NCCL_DEBUG=INFO` and `export NCCL_NET_TRACE=1`
3. Solution 1 - Limit QP count (critical!): `export NCCL_IB_QPS_PER_CONNECTION=4` and `export NCCL_MAX_NCHANNELS=4`
4. Solution 2 - Increase CQ size: `echo 16384 > /sys/module/mlx5_core/parameters/log_num_cq`
5. Solution 3 - Use NCCL 2.18+ QP sharing feature
6. Verify: Monitor QP count should be <4096

---

## Case ID : 108

**Error** : NCCL Conflict with Firewall

**Root cause** :
- Firewall blocks RDMA_CM port (4791) or dynamic ports (18515+)
- SELinux prevents RDMA operations

**Action plan** :
1. Check firewall: `iptables -L -n | grep -E "4791|18515"` and `firewall-cmd --list-all`
2. Check SELinux: `getenforce` and `ausearch -m avc -ts recent | grep rdma`
3. Solution 1 - Open RDMA ports:
   ```bash
   firewall-cmd --permanent --add-port=4791/tcp
   firewall-cmd --permanent --add-port=4791/udp
   firewall-cmd --permanent --add-port=18515-18615/tcp
   firewall-cmd --reload
   ```
4. Solution 2 - Disable firewall (test environment): `systemctl stop firewalld && systemctl disable firewalld`
5. Solution 3 - SELinux: `setsebool -P allow_rdma 1` or `setenforce 0`
6. Verify: `ib_write_bw -d mlx5_0 -R 192.168.1.101` should succeed

---

## Case ID : 109

**Error** : Ceph RDMA QP Count Explosion

**Root cause** :
- Ceph async messenger creates independent QP for each OSD connection
- 100 OSD cluster → 10,000+ QP → NIC SRAM overflow
- Memory registration overhead grows linearly with IO size

**Action plan** :
1. Check QP count: `cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/*_qp*`
2. Monitor memory registration latency: `perf record -e ib_umem_get -a sleep 10 && perf report`
3. ceph.conf optimization:
   ```ini
   [global]
   ms_type = async
   ms_async_rdma_device_name = mlx5_0
   
   [osd]
   ms_async_rdma_qp_count = 8
   ms_async_rdma_cq_size = 8192
   bluestore_cache_size_hdd = 4G
   bluestore_cache_size_ssd = 8G
   ```
4. Restart OSD: `systemctl restart ceph-osd@0`

---

## Case ID : 110

**Error** : Lustre LNet Timeout (Metadata Operation Hang)

**Root cause** :
- MDS and client RDMA connection not reused
- Metadata operations (create/unlink) trigger frequent QP create/destroy
- Default 10 second timeout insufficient for large-scale metadata operations

**Action plan** :
1. Client optimization:
   - Increase LNet connection cache: `lctl set_param lnet.peers=2048`
   - Extend timeout: `lctl set_param timeout=30`
   - Enable RDMA connection reuse: `mount -t lustre -o rdma,connect_timeout=30s MGS:/fs /mnt/lustre`
2. MDS side optimization: `lctl set_param mdt.*.connect_timeout=60` and `lctl set_param mdt.*.max_rpcs_in_flight=1024`
3. Verify: `time touch /mnt/lustre/file_{1..10000}`

---

## Case ID : 111

**Error** : Vitastor RDMA 32KB+ Performance Cliff

**Root cause** :
- Vitastor default inline threshold too low (128 bytes)
- 32KB IO triggers PCIe round-trip, increasing latency
- RDMA inline data not enabled

**Action plan** :
1. Increase inline threshold: `echo 2048 > /sys/module/mlx5_core/parameters/log_max_inline_data`
2. Vitastor config:
   ```json
   {
     "immediate_commit": "all",
     "rdma_inline_size": 2048
   }
   ```
3. Verify inline effective: `ib_send_lat -d mlx5_0 -s 32768` should show <5μs latency

---

## Case ID : 112

**Error** : ibdiagnet Fabric-wide Diagnosis

**Root cause** : Need to quickly locate fault points in 100-node cluster performance degradation

**Action plan** :
1. Full network scan (execute on SM node): `ibdiagnet -v -r --timeout 300`
2. Key output file analysis:
   - `ibdiagnet2.sm.log`: SM status - `grep -i "error\|warning" ibdiagnet2.sm.log`
   - `ibdiagnet2.net_dump`: Error port list
   - `ibdiagnet2.db_csv`: Full topology - `awk -F',' '$10>0 {print $1,$2,$10}' ibdiagnet2.db_csv`
3. Error type identification:
   - `symbol_error > 0` → Physical layer issue (optical module/cable)
   - `link_downed > 10` → Link frequent UP/DOWN (jitter)
   - `port_rcv_errors > 0` → Packet loss (PFC/ECN config issue)

---

## Case ID : 113

**Error** : Switch Telemetry Real-time Monitoring

**Root cause** : Production environment needs 7×24 hour buffer watermark monitoring

**Action plan** :
1. Enable gRPC Telemetry on switch:
   ```bash
   telemetry server
   telemetry destination-profile prometheus
     collector 10.0.0.100 port 50051 protocol grpc
   telemetry sensor-group buffer_group
     sensor-path /spectrum/buffer/usage
     sensor-path /spectrum/port/statistics
   telemetry subscription buffer_sub
     sensor-group buffer_group sample-interval 1000
     destination-profile prometheus
   ```
2. Prometheus configuration (prometheus.yml):
   ```yaml
   scrape_configs:
     - job_name: 'spectrum'
       static_configs:
         - targets: ['10.0.0.1:50051']
   ```
3. Grafana dashboard key metrics:
   - `buffer_usage_percent > 80%` → Alert
   - `pfc_pause_frames_tx_rate > 1000/s` → PFC storm
   - `port_xmit_wait > 1000000` → Congestion

---

## Appendix: Quick Reference - Diagnostic Commands

### Device and Link Status
| Command | Purpose |
|---------|---------|
| `ibv_devinfo` | Show RDMA device detailed information |
| `ibstat` / `ibstatus` | Check port status and rate |
| `ibnetdiscover` | Discover network topology |
| `rdma link show` | View RDMA link status |
| `rdma statistic show` | View error counters |

### Performance Testing
| Command | Purpose |
|---------|---------|
| `ib_write_lat` / `ib_write_bw` | RDMA latency/bandwidth test |
| `ib_send_lat` / `ib_send_bw` | Send operation latency/bandwidth test |
| `ib_read_lat` / `ib_read_bw` | Read operation latency/bandwidth test |
| `ibv_rc_pingpong` | RC connection test |

### Resource Viewing
| Command | Purpose |
|---------|---------|
| `rdma res show qp` | View QP resources |
| `rdma res show mr` | View MR resources |
| `rdma res show cq` | View CQ resources |
| `ulimit -l` | Check memory lock limit |

### Error Diagnosis
| Command | Purpose |
|---------|---------|
| `ibqueryerrors -c` | Scan entire network for errors |
| `perfquery -x <lid> <port>` | View port extended counters |
| `ibtracert <src_lid> <dst_lid>` | Route tracing |
| `ethtool -S <interface>` | View NIC statistics |
| `dmesg \| grep -i mlx` | View driver logs |

### Key Error Codes
| Error Code | Macro Definition | Meaning |
|:----------:|------------------|---------|
| 4 | `IBV_WC_LOC_PROT_ERR` | Local protection error |
| 5 | `IBV_WC_WR_FLUSH_ERR` | WR flush error |
| 9 | `IBV_WC_REM_INV_REQ_ERR` | Remote invalid request |
| 12 | `IBV_WC_RETRY_EXC_ERR` | Retry count exceeded |

### Kernel Error Codes
| Error Code | Definition | Trigger Scenario |
|:----------:|------------|------------------|
| -110 | `ETIMEDOUT` | Firmware command timeout |
| -113 | `EHOSTUNREACH` | Host unreachable |
| -22 | `EINVAL` | Parameter error |

---

*Document Generated: 2026-01-29*
*Total Cases: 113*
*Coverage: Physical Layer, Driver Layer, Network Layer, Application Layer Faults*
