# RDMA知识测试题集

根据提供的技术文档整理的35道RDMA知识测试题，涵盖基础概念、故障排查、工具使用和性能优化。

---

ID：1  
Question：RDMA操作模型的核心特点是什么？请列举至少3个关键特性。  
Answer：1) 绕过CPU和内核的直接内存访问；2) 应用程序内存与NIC之间的零拷贝数据传输；3) 需要正确的内存注册和保护域配置；4) 基于完成队列(CQ)的异步操作模型。  
Source：RDMA_Troubleshooting_Guide.md (Introduction章节 - Key Concepts部分)

---

ID：2  
Question：当`ibstat`显示端口状态为"Down"时，应按什么顺序排查物理层问题？请列出至少4个诊断步骤。  
Answer：1) 物理检查线缆连接；2) 使用`ethtool -m <device>`检查光模块状态；3) 使用`ibqueryerrors --details`检查错误计数器；4) 检查核日志`dmesg | grep -i link`；5) 验证端口是否被管理性禁用(`cat /sys/class/infiniband/mlx5_0/ports/1/state`)；6) 检查SM状态(仅InfiniBand)。  
Source：RDMA_Troubleshooting_Guide.md (Symptom 1: Link Not Coming Up章节)

---

ID：3  
Question：`ibqueryerrors`工具中标记为`[EXCEEDS]`的错误计数器表示什么？请解释Symbol Errors、LinkErrorRecovery和ExcessiveBufferOverrun这三种错误的典型原因。  
Answer：`[EXCEEDS]`表示该错误计数器超过预设阈值，需要立即关注。Symbol Errors通常由物理层问题引起(劣质线缆/光模块)；LinkErrorRecovery表示链路训练失败(速率/模式不匹配)；ExcessiveBufferOverrun表示网络拥塞或缓冲区不足。  
Source：RDMA_Troubleshooting_Guide.md (ibqueryerrors工具详解) 和 rdma_core_data.json (ibqueryerrors专家分析)

---

ID：4  
Question：RDMA性能排查的三阶段方法论是什么？每个阶段的典型耗时和核心目标是什么？  
Answer：Phase 1初始评估(5-10分钟)：验证基础连通性、快速健康检查、SM状态验证；Phase 2详细调查(10-30分钟)：分析错误模式、检查配置、建立性能基线；Phase 3深度分析(30+分钟)：捕获系统状态、复现问题、分析时空模式。  
Source：RDMA_Troubleshooting_Guide.md (Troubleshooting Methodology章节)

---

ID：5  
Question：在RoCEv2网络中，高延迟(>10μs)的5个常见原因及对应解决方案是什么？  
Answer：1) NUMA局部性差 → 使用numactl绑定到相同NUMA节点；2) 队列深度过低 → 增加应用层队列深度；3) 中断开销高 → 启用轮询模式(`cq_poll_mode=1`)；4) 网络拥塞 → 启用PFC/ECN；5) MTU不匹配 → 统一设置MTU(如2048)。  
Source：RDMA_Troubleshooting_Guide.md (Symptom 2: High Latency章节)

---

ID：6  
Question：`mlnx_tune`工具提供的low-latency性能配置文件主要优化哪些系统参数？请列举至少4个优化领域。  
Answer：1) 内核参数(内存限制、缓冲区大小)；2) CPU管理(NUMA节点绑定、CPU隔离)；3) 中断配置(中断亲和性、中断节流)；4) 内存管理(大页内存启用)；5) 队列深度优化(针对低延迟工作负载减少队列深度)。  
Source：mlnx_tools_data.json (mlnx_tune专家分析) 和 RDMA_Troubleshooting_Guide.md (mlnx_tune工具使用)

---

ID：7  
Question：libibverbs库中创建QP(队列对)前必须按什么顺序分配资源？请说明资源依赖关系。  
Answer：资源分配顺序：1) PD(Protection Domain) → 2) MR(Memory Region) → 3) CQ(Completion Queue) → 4) QP(Queue Pair)。依赖关系：QP需要PD和CQ，MR需要PD，所有资源最终依赖ibv_context(设备上下文)。  
Source：rdma_core_data.json (libibverbs专家洞察 - 资源分配层次)

---

ID：8  
Question：如何区分InfiniBand链路状态机中的"Armed"和"Active"状态？这两个状态分别表示什么含义？  
Answer："Armed"状态表示物理链路已训练完成且准备好，但等待子网管理器(SM)配置(分配LID等)；"Active"状态表示链路完全运行，已获得SM配置，可以传输数据。状态机顺序：Down → Initializing → Armed → Active。  
Source：rdma_core_data.json (ibstat.c专家代码分析 - 端口状态机解释)

---

ID：9  
Question：使用`ibnetdiscover`工具时，为什么建议使用`--save-cache`选项？在大型fabric中如何优化发现过程？  
Answer：`--save-cache`将拓扑保存到缓存文件，后续查询可使用`--load-cache`快速加载，避免重复扫描。大型fabric优化：1) 限制跳数(-H选项)；2) 围绕特定节点发现(-G选项)；3) 使用缓存加速；4) 避免在业务高峰期执行全网扫描。  
Source：RDMA_Troubleshooting_Guide.md (ibnetdiscover工具使用) 和 rdma_core_data.json (ibnetdiscover专家分析)

---

ID：10  
Question：RoCEv2网络中连接失败的4个常见原因及诊断命令是什么？  
Answer：1) 目标不可达 → `ibping <dest_lid>`；2) GID配置错误 → `show_gids`；3) 防火墙阻塞 → `iptables -L -n`(检查4791, 17990-17999端口)；4) 权限问题 → `dmesg | grep -i ibv`(检查/dev/infiniband权限)。  
Source：RDMA_Troubleshooting_Guide.md (Symptom 4: Connection Failures章节)

---

ID：11  
Question：RDMA性能目标参考值：HDR网络的预期吞吐量、可接受延迟范围、以及错误率阈值分别是多少？  
Answer：HDR网络吞吐量目标：>90 Gbps(优秀)，>80 Gbps(良好)，<80 Gbps需调查；延迟目标：<5μs(优秀)，1-10μs(良好)，>10μs需调查；错误率：0(目标)，<0.001%(可接受)，>0.01%(需调查)。  
Source：RDMA_Troubleshooting_Guide.md (Quick Reference - Performance Targets表格)

---

ID：12  
Question：`mlnx_qos`工具配置PFC(优先级流控)时，为什么需要同时考虑缓冲区大小和PFC超时时间？不当配置会导致什么问题？  
Answer：PFC暂停帧发送后，发送端会停止传输直到收到恢复帧。如果缓冲区深度不足以容纳PFC超时时间内可能到达的流量，会导致缓冲区溢出和丢包。不当配置可能引发PFC风暴(级联暂停)或缓冲区耗尽。最佳实践：缓冲区深度 > (链路带宽 × PFC超时时间)。  
Source：mlnx_tools_data.json (mlnx_qos专家分析 - QoS配置策略)

---

ID：13  
Question：在libibverbs应用中，什么情况下应使用`IBV_SEND_INLINE`标志？其硬件限制是什么？  
Answer：对于小消息(通常<64字节，具体取决于硬件)，使用IBV_SEND_INLINE可避免内存注册开销，直接通过doorbell写入数据。硬件限制：不同设备有不同inline阈值(如ConnectX-5为224字节)，超过阈值会导致发送失败。应通过`ibv_query_device().max_inline_data`查询设备能力。  
Source：RDMA_Troubleshooting_Guide.md (Symptom 2代码级优化) 和 rdma_core_data.json (libibverbs专家洞察)

---

ID：14  
Question：当`ibqueryerrors`显示"VL15 Dropped"计数器增加时，表示什么问题？如何排查？  
Answer：VL15(Virtual Lane 15)用于子网管理流量，"VL15 Dropped"增加表示SM路由问题或不可路由的数据包。排查步骤：1) 检查SM状态`sminfo`；2) 验证路由表`saquery -p`；3) 使用`ibtracert`追踪路径；4) 检查交换机配置是否阻塞管理流量。  
Source：RDMA_Troubleshooting_Guide.md (Symptom 5错误分析矩阵)

---

ID：15  
Question：RDMA应用中"高CPU利用率但低吞吐量"的3个典型原因及优化方法是什么？  
Answer：1) 中断风暴 → 优化IRQ亲和性(`mlnx_affinity --optimize`)或启用轮询；2) 内存注册开销 → 使用大页内存和MR缓存；3) PCIe带宽瓶颈 → 检查`lspci -vvv | grep LnkSta`确认PCIe协商速率，确保使用Gen3/Gen4 x8或更高。  
Source：RDMA_Troubleshooting_Guide.md (Symptom 3: Low Throughput) 和 mlnx_tools_data.json (mlnx_perf诊断模式)

---

ID：16  
Question：`show_gids`工具输出中，GID类型0x0000、0x0001和0x8000+分别代表什么？为什么RoCEv2需要配置link-local GID？  
Answer：0x0000=IPv4地址GID，0x0001=IPv6地址GID，0x8000+=RoCEv2 link-local GID。RoCEv2需要link-local GID(通常为fe80::/10)用于邻居发现和路径解析，即使配置了全局IPv6地址，link-local GID仍是RoCEv2操作的基础。  
Source：mlnx_tools_data.json (show_gids专家分析 - GID类型说明)

---

ID：17  
Question：在NUMA系统中，RDMA性能优化的"三同原则"是什么？如何验证设备与CPU的NUMA局部性？  
Answer："三同原则"：CPU、内存、PCIe设备位于同一NUMA节点。验证方法：1) `numactl -H`查看NUMA拓扑；2) `cat /sys/class/infiniband/mlx5_0/device/numa_node`查看设备NUMA节点；3) `lscpu`查看CPU NUMA分布；4) 使用`mlnx_affinity -d mlx5_0`检查当前亲和性配置。  
Source：RDMA_Troubleshooting_Guide.md (Symptom 2/3 NUMA优化) 和 mlnx_tools_data.json (mlnx_affinity专家分析)

---

ID：18  
Question：使用`perfquery`工具时，`--all`和`-e`参数的区别是什么？什么情况下需要重置计数器？  
Answer：`--all`查询所有标准性能计数器；`-e`查询扩展计数器(64位，需要硬件支持)。重置计数器场景：1) 建立新的性能基线前；2) 排除历史累积值干扰；3) 测试特定工作负载影响。使用`perfquery -x 0x3f`重置计数器(需注意某些计数器不可重置)。  
Source：rdma_core_data.json (perfquery专家分析) 和 RDMA_Troubleshooting_Guide.md (perfquery工具使用)

---

ID：19  
Question：librdmacm连接建立过程中的关键事件序列是什么？应用层应如何正确处理RDMA_CM_EVENT_REJECTED事件？  
Answer：事件序列：RDMA_CM_EVENT_ADDR_RESOLVED → RDMA_CM_EVENT_ROUTE_RESOLVED → RDMA_CM_EVENT_CONNECT_REQUEST(服务端) / RDMA_CM_EVENT_ESTABLISHED(客户端)。处理REJECTED事件：1) 检查`event->status`获取拒绝原因；2) 释放cm_id资源；3) 记录日志用于诊断；4) 根据策略决定重试或失败退出。常见拒绝原因：权限不足、QP类型不匹配、资源耗尽。  
Source：rdma_core_data.json (librdmacm专家洞察 - 事件处理)

---

ID：20  
Question：RDMA故障排查文档中推荐的"问题记录模板"应包含哪7个关键部分？为什么"模式分析"对根因定位至关重要？  
Answer：7个关键部分：问题标题、环境信息、症状描述、初步发现(Phase 1)、详细调查(Phase 2)、深度分析(Phase 3)、根因与解决方案。模式分析重要性：通过时空模式(时间规律、特定节点/端口、与系统事件关联)可区分偶发故障与系统性问题，避免"治标不治本"，例如符号错误仅出现在特定端口表明硬件问题而非配置问题。  
Source：RDMA_Troubleshooting_Guide.md (Documentation Template章节 和 Phase 3: Deep Dive模式分析)

---

ID：21  
Question：在RDMA操作模型中，数据传输通过哪两个关键组件实现应用内存与网卡之间的直接交互，从而绕过CPU和内核？  
Answer：通过**内存注册（Memory Registration, MR）**和**保护域（Protection Domain, PD）**实现。应用首先注册内存区域(MR)到特定的保护域(PD)，创建队列对(QP)和完成队列(CQ)，然后通过发送/接收工作请求(WR)直接让网卡访问内存，实现零拷贝(Zero-copy)传输。  
Source：RDMA_Troubleshooting_Guide.md（Introduction章节 - Key Concepts）

---

ID：22  
Question：`ibstat`工具显示端口状态为"Armed"，这代表什么含义？它与"Active"状态有何区别？  
Answer：**Armed状态**表示物理链路已就绪，但正在等待子网管理器(SM)完成配置；**Active状态**表示链路完全可操作，可以传输数据。状态机顺序为：Down → Initializing → Armed → Active。  
Source：rdma_core_data.json（ibstat.c代码分析部分）

---

ID：23  
Question：使用`ibqueryerrors`时发现某端口`ExcessiveBufferOverrun`计数器值持续增加且超过阈值，这通常指示什么类型的问题？应如何排查？  
Answer：这通常指示**网络拥塞(Congestion)**问题。排查步骤：1) 使用`mlnx_qos`检查PFC(优先级流控制)是否正确配置；2) 使用`perfquery`查看队列深度；3) 检查是否启用了ECN(显式拥塞通知)；4) 使用`mlnx_perf`监控吞吐量与延迟的关联。  
Source：RDMA_Troubleshooting_Guide.md（Symptom 5: Increasing Error Counters章节）

---

ID：24  
Question：在HDR InfiniBand网络中，应用观察到RDMA延迟不稳定（出现50-100μs峰值，基线为2-5μs），且`ibqueryerrors`显示高队列利用率(>90%)。在代码层面应如何优化？  
Answer：应**减少队列深度(Queue Depth)**以降低延迟。具体修改：在创建QP时设置`qp_init_attr.cap.max_send_wr = 16`和`max_recv_wr = 16`（而非高吞吐场景的1024）。同时建议：1) 使用轮询(polling)代替中断；2) 设置`IBV_SEND_INLINE`标志处理小于32字节的消息；3) 确保CPU和网卡位于同一NUMA节点。  
Source：mlnx_tools_data.json（latency_test专家见解部分）和RDMA_Troubleshooting_Guide.md（Case Study 2章节）

---

ID：25  
Question：在使用`librdmacm`库建立RDMA连接时，`RDMA_CM_EVENT_ROUTE_RESOLVED`事件表示什么阶段已完成？如果后续收到`RDMA_CM_EVENT_REJECTED`，可能的原因是什么？  
Answer：`RDMA_CM_EVENT_ROUTE_RESOLVED`表示**路由解析完成**。收到`RDMA_CM_EVENT_REJECTED`可能原因包括：1) 对端应用拒绝了连接请求；2) 防火墙配置阻止了RDMA端口(4791或17990-17999)；3) 双方QP类型不匹配；4) GID配置错误或权限不足。  
Source：rdma_core_data.json（librdmacm部分）

---

ID：26  
Question：`iblinkinfo`显示某链路速度为100 Gbps，链路宽度为4x，但`ibstat`显示Active MTU为1024而Max MTU为2048。这可能对性能产生什么影响？如何修复？  
Answer：**MTU不匹配**会导致大数据包分片，增加开销，降低吞吐率。修复方法：运行`rdma link set dev mlx5_0 mtu 2048`（或 network-scripts配置）使两端MTU一致。建议在部署前使用`iblinkinfo -s`验证全Fabric的MTU配置。  
Source：RDMA_Troubleshooting_Guide.md（Symptom 3: Low Throughput章节）

---

ID：27  
Question：`mlnx_tune`工具的`--profile low-latency`参数主要优化哪些方面？与之相对的`throughput`配置文件有何关键区别？  
Answer：**low-latency配置**重点优化：1) 减少中断延迟(启用polling模式)；2) 最小化队列深度；3) CPU核心隔离(isolcpus)；4) 内核参数调整。**throughput配置**则侧重：1) 启用透明大页(Transparent Huge Pages)；2) 增加缓冲区大小(rmem_max/wmem_max)；3) 优化PCIe电源管理；4) 使用更大的队列深度(1024+)。  
Source：mlnx_tools_data.json（mlnx_tune工具描述）

---

ID：28  
Question：通过`ethtool -m mlx5_0`检查光模块时发现温度过高(>85°C)，同时`ibqueryerrors`显示`Symbol Errors`和`LocalLinkIntegrityErrors`增加。这可能是什么问题？如何解决？  
Answer：**物理层硬件故障**- 光收发器(Transceiver)过热或损坏。解决：1) 更换故障光模块；2) 检查机房散热；3) 临时可尝试降低端口速率(`rdma link set speed edr`)；4) 更换后使用`ibqueryerrors -k`清除历史错误计数。  
Source：RDMA_Troubleshooting_Guide.md（Symptom 1: Link Not Coming Up章节）

---

ID：29  
Question：使用`ibnetdiscover`发现Fabric拓扑时，为什么要使用`--save-cache`选项？在什么情况下需要限制发现跳数(`-H`参数)？  
Answer：**缓存优势**：对于大型Fabric，缓存拓扑避免重复SMP(子网管理协议)查询，提高后续工具(如`ibqueryerrors`)的速度。**限制跳数场景**：在部分网络分区或大型多跳Fabric中，限制跳数(-H 3)可快速定位局部拓扑，减少发现时间，避免跨分区超时。  
Source：rdma_core_data.json（ibnetdiscover部分）

---

ID：30  
Question：在RoCEv2网络中，使用`mlnx_qos`启用PFC(Priority Flow Control)时，为什么通常选择优先级3和4？ETS(增强传输选择)的作用是什么？  
Answer：**选择3和4**是因为这些是DCB(Data Center Bridging)标准中为RDMA流量保留的无损优先级(Lossless Priorities)。**ETS作用**：在拥塞时按权重(如50:30:20)分配带宽，确保关键流量获得最小带宽保证，防止低优先级流量饿死高优先级RDMA流量。  
Source：mlnx_tools_data.json（mlnx_qos工具描述）

---

ID：31  
Question：在调用`ibv_create_qp()`创建队列对时返回`EAGAIN`错误码，这与`EINVAL`有何区别？分别应如何处理？  
Answer：**EAGAIN**：资源临时不可用(如达到QP数量上限)，应检查`ulimit -l`内存限制，稍后重试或释放资源。**EINVAL**：参数无效(如无效的QP类型或超出设备能力)，应检查`struct ibv_qp_init_attr`中的`cap`配置(如max_sge)是否超过设备最大限制(`ibv_devinfo`查询)。  
Source：rdma_core_data.json（libibverbs部分）和RDMA_Troubleshooting_Guide.md（Error Codes Reference章节）

---

ID：32  
Question：`mlnx_affinity`命令输出显示"NUMA Local: NO"，这对RDMA性能意味着什么？应该使用什么命令修复？  
Answer：**性能影响**：网卡和CPU位于不同NUMA节点，导致内存访问跨NUMA(inter-node)，延迟增加(比本地访问高~20-30ns)，带宽降低。**修复命令**：运行`mlnx_affinity -d mlx5_0 --optimize`自动优化，或使用`numactl --cpunodebind=0 --membind=0`绑定应用到网卡所在NUMA节点(0)。  
Source：mlnx_tools_data.json（mlnx_affinity工具描述和诊断输出）

---

ID：33  
Question：根据案例研究，100节点的RoCEv2集群出现5-10%的随机连接超时，经`ibtracert`发现路径动态变化。这是什么原因导致的？最终解决方案是什么？  
Answer：**根因**：ECMP(等价多路径)负载均衡导致路由抖动(route flapping)。**解决方案**：禁用RDMA流量的ECMP，使用静态路由绑定(`mlnx_qos --route-mode static`或`ip route add`固定路径)，确保RDMA连接使用稳定的路径传输。  
Source：RDMA_Troubleshooting_Guide.md（Case Study 1章节）

---

ID：34  
Question：在高吞吐RDMA应用中，为什么建议启用透明大页(Transparent Huge Pages)？在代码中如何优化内存注册开销？  
Answer：**THP优势**：减少TLB(转换后备缓冲器)未命中，提高内存注册速度，减少页表遍历开销。**代码优化**：1) 使用内存注册缓存(Memory Registration Cache)复用MR；2) 对大缓冲区(>1MB)使用`ibv_reg_mr`一次性注册而非多次小块注册；3) 确保缓冲区按页对齐。  
Source：mlnx_tools_data.json（mlnx_tune专家笔记）和rdma_core_data.json（libibverbs专家见解）

---

ID：35  
Question：根据故障排除方法论，执行`ibstat`后应紧接着执行哪个命令进行快速健康检查？如果该命令显示XmtDiscards(发送丢弃)错误，下一步应该查询什么？  
Answer：紧接着应执行`ibqueryerrors`进行错误计数器扫描。如果显示**XmtDiscards**，下一步应使用`perfquery 1 0 --data`或`ibqueryerrors --details`查询**PortXmitDiscardDetails**属性，获取丢弃原因细分(如信用耗尽、队列满等)。  
Source：RDMA_Troubleshooting_Guide.md（Phase 1: Initial Assessment和ibqueryerrors工具使用章节）