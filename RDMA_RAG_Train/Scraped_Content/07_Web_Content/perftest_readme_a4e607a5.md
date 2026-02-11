---
title: "perftest README"
source: "https://raw.githubusercontent.com/linux-rdma/perftest/master/README"
category: web_content
tags: [perftest, benchmarking, readme]
scraped_at: "2026-02-10T01:52:41.490221+00:00"
---

# perftest README

> **Source:** [https://raw.githubusercontent.com/linux-rdma/perftest/master/README](https://raw.githubusercontent.com/linux-rdma/perftest/master/README)
> **Category:** web_content
> **Tags:** perftest, benchmarking, readme

---

Open Fabrics Enterprise Distribution (OFED)
Performance Tests README
===============================================================================
Table of Contents
===============================================================================
1. Overview
2. Installation
3. Notes on Testing Methodology
4. Test Descriptions
5. Running Tests
6. Known Issues
===============================================================================
1. Overview
===============================================================================
This is a collection of tests written over uverbs intended for use as a
performance micro-benchmark. The tests may be used for HW or SW tuning
as well as for functional testing.
The collection contains a set of bandwidth and latency benchmark such as:
\* Send - ib\_send\_bw and ib\_send\_lat
\* RDMA Read - ib\_read\_bw and ib\_read\_lat
\* RDMA Write - ib\_write\_bw and ib\_write\_lat
\* RDMA Atomic - ib\_atomic\_bw and ib\_atomic\_lat
\* Native Ethernet (when working with MOFED2) - raw\_ethernet\_bw, raw\_ethernet\_lat
Please post results/observations to the openib-general mailing list.
See "Contact Us" at http://openib.org/mailman/listinfo/openib-general and
http://www.openib.org.
===============================================================================
2. Installation
===============================================================================
-After cloning the repository a perftest directory should appear in your current
directory
-Cloning example :
git clone , In our situation its --> git clone https://github.com/linux-rdma/perftest.git
-After cloning, Follow this commands:
-cd perftest/
-./autogen.sh
-./configure Note:If you want to install in a specific directory use the optional flag --prefix= , e.g: ./configure --prefix=
-make
-make install
-All of the tests will appear in the perftest directory and in the install directory.
===============================================================================
3. Notes on Testing Methodology
===============================================================================
- The benchmarks use the CPU cycle counter to get time stamps without context
switch. Some CPU architectures (e.g., Intel's 80486 or older PPC) do not
have such capability.
- The latency benchmarks measure round-trip time but report half of that as one-way
latency. This means that the results may not be accurate for asymmetrical configurations.
- On all unidirectional bandwidth benchmarks, the client measures the bandwidth.
On bidirectional bandwidth benchmarks, each side measures the bandwidth of
the traffic it initiates, and at the end of the measurement period, the server
reports the result to the client, who combines them together.
- Latency tests report minimum, median and maximum latency results.
The median latency is typically less sensitive to high latency variations,
compared to average latency measurement.
Typically, the first value measured is the maximum value, due to warmup effects.
- Long sampling periods have very limited impact on measurement accuracy.
The default value of 1000 iterations is pretty good.
Note that the program keeps data structures with memory footprint proportional
to the number of iterations. Setting a very high number of iteration may
have negative impact on the measured performance which are not related to
the devices under test.
If a high number of iterations is strictly necessary, it is recommended to
use the -N flag (No Peak).
- Bandwidth benchmarks may be run for a number of iterations, or for a fixed duration.
Use the -D flag to instruct the test to run for the specified number of seconds.
The --run\_infinitely flag instructs the program to run until interrupted by
the user, and print the measured bandwidth every 5 seconds.
- The "-H" option in latency benchmarks dumps a histogram of the results.
See xgraph, ygraph, r-base (http://www.r-project.org/), PSPP, or other
statistical analysis programs.
\*\*\* IMPORTANT NOTE:
When running the benchmarks over an Infiniband fabric,
a Subnet Manager must run on the switch or on one of the
nodes in your fabric, prior to starting the benchmarks.
Architectures tested: i686, x86\_64, ia64
===============================================================================
4. Benchmarks Description
===============================================================================
The benchmarks generate a synthetic stream of operations, which is very useful
for hardware and software benchmarking and analysis.
The benchmarks are not designed to emulate any real application traffic.
Real application traffic may be affected by many parameters, and hence
might not be predictable based only on the results of those benchmarks.
ib\_send\_lat latency test with send transactions
ib\_send\_bw bandwidth test with send transactions
ib\_write\_lat latency test with RDMA write transactions
ib\_write\_bw bandwidth test with RDMA write transactions
ib\_read\_lat latency test with RDMA read transactions
ib\_read\_bw bandwidth test with RDMA read transactions
ib\_atomic\_lat latency test with atomic transactions
ib\_atomic\_bw bandwidth test with atomic transactions
Raw Ethernet interface benchmarks:
raw\_ethernet\_send\_lat latency test over raw Ethernet interface
raw\_ethernet\_send\_bw bandwidth test over raw Ethernet interface
===============================================================================
5. Running Tests
===============================================================================
Prerequisites:
kernel 2.6
(kernel module) matches libibverbs
(kernel module) matches librdmacm
(kernel module) matches libibumad
(kernel module) matches libmath (lm)
(linux kernel module) matches pciutils (lpci).
Server: ./
Client: ./
o  is IPv4 or IPv6 address. You can use the IPoIB
address if IPoIB is configured.
o --help lists the available
\*\*\* IMPORTANT NOTE:
The SAME OPTIONS must be passed to both server and client.
Common Options to all tests:
----------------------------
-h, --help Display this help message screen
-p, --port= Listen on/connect to port  (default: 18515)
-R, --rdma\_cm Connect QPs with rdma\_cm and run test on those QPs
-z, --comm\_rdma\_cm Communicate with rdma\_cm module to exchange data - use regular QPs
-m, --mtu= QP Mtu size (default: active\_mtu from ibv\_devinfo)
-c, --connection= Connection type RC/UC/UD/XRC/DC/SRD (default RC).
-d, --ib-dev= Use IB device  (default: first device found)
-i, --ib-port= Use network port  of IB device (default: 1)
-s, --size= Size of message to exchange (default: 1)
-a, --all Run sizes from 2 till 2^23
-n, --iters= Number of exchanges (at least 100, default: 1000)
-x, --gid-index= Test uses GID with GID index taken from command
-V, --version Display version number
-e, --events Sleep on CQ events (default poll)
-F, --CPU-freq Do not fail even if cpufreq\_ondemand module
-I, --inline\_size= Max size of message to be sent in inline mode
-u, --qp-timeout= QP timeout = (4 uSec)\*(2^timeout) (default: 14)
-S, --sl= Service Level (default 0)
-r, --rx-depth= Receive queue depth (default 600)
Options for latency tests:
--------------------------
-C, --report-cycles Report times in CPU cycle units
-H, --report-histogram Print out all results (Default: summary only)
-U, --report-unsorted Print out unsorted results (default sorted)
Options for BW tests:
---------------------
-b, --bidirectional Measure bidirectional bandwidth (default uni)
-N, --no peak-bw Cancel peak-bw calculation (default with peak-bw)
-Q, --cq-mod Generate Cqe only after  completion
-t, --tx-depth= Size of tx queue (default: 128)
-O, --dualport Run test in dual-port mode (2 QPs). Both ports must be active (default OFF)
-D, --duration= Run test for  period of seconds
-f, --margin= When in Duration, measure results within margins (default: 2)
-l, --post\_list=

 Post list of send WQEs of

 size (instead of single post)
--recv\_post\_list=

 Post list of receive WQEs of

 size (instead of single post)
-q, --qp= Num of QPs running in the process (default: 1)
--run\_infinitely Run test until interrupted by user, print results every 5 seconds
SEND tests (ib\_send\_lat or ib\_send\_bw) flags:
---------------------------------------------
-r, --rx-depth= Size of receive queue (default: 512 in BW test)
-g, --mcg= Send messages to multicast group with  qps attached to it
-M, --MGID= In multicast, uses  as the group MGID
WRITE latency (ib\_write\_lat) flags:
-----------------------------------
--write\_with\_imm Use write-with-immediate verb instead of write
ATOMIC tests (ib\_atomic\_lat or ib\_atomic\_bw) flags:
---------------------------------------------------
-A, --atomic\_type= type of atomic operation from {CMP\_AND\_SWAP,FETCH\_AND\_ADD}
-o, --outs= Number of outstanding read/atomic requests - also on READ tests
Options for raw\_ethernet\_send\_bw:
---------------------------------
-B, --source\_mac source MAC address by this format XX:XX:XX:XX:XX:XX (default take the MAC address form GID)
-E, --dest\_mac destination MAC address by this format XX:XX:XX:XX:XX:XX \*\*MUST\*\* be entered
-J, --server\_ip server ip address by this format X.X.X.X (using to send packets with IP header)
-j, --client\_ip client ip address by this format X.X.X.X (using to send packets with IP header)
-K, --server\_port server udp port number (using to send packets with UDP header)
-k, --client\_port client udp port number (using to send packets with UDP header)
-Z, --server choose server side for the current machine (--server/--client must be selected)
-P, --client choose client side for the current machine (--server/--client must be selected)
----------------------------------------------
Special feature detailed explanation in tests:
----------------------------------------------
1. Usage of post\_list feature (-l, --post\_list=

 and --recv\_post\_list=

)
In this case, each QP will prepare

 WQEs (instead of 1), and will chain them to each other.
In chaining we mean allocating  array, and setting 'next' pointer of each WQE in the array
to point to the following element in the array. the last WQE in the array will point to NULL.
In this case, when posting the first WQE in the list, will instruct the HW to post all of those WQEs.
Which means each post send/recv will post  messages.
This feature is good if we want to know the maximum message rate of QPs in a single process.
Since we are limited to SW posts (for example, on post\_send ~ 10 Mpps, since we have ~ 500 ns between
each SW post\_send), we can see the true HW message rate when setting  of 64 (for example)
since it's not depended on SW limitations.
2. RDMA Connected Mode (CM)
You can add the "-R" flag to all tests to connect the QPs from each side with the rdma\_cm library.
In this case, the library will connect the QPs and will use the IPoIB interface for doing it.
It helps when you don't have Ethernet connection between the 2 nodes.
You must supply the IPoIB interface as the server IP.
3. Multicast support in ib\_send\_lat and in ib\_send\_bw
Send tests have built in feature of testing multicast performance, in verbs level.
You can use "-g" to specify the number of QPs to attach to this multicast group.
"-M" flag allows you to choose the multicast group address.
4. GPUDirect usage:
As of perftest release 25.07 the build system automatically
detects the location of cuda.h. Passing CUDA\_H\_PATH to the configure
script is therefore no longer required. The variable is still accepted
for backward-compatibility but its usage is not recommended.
The variable will depracted in the 25.10 release.
For perftest releases earlier than 25.07 you must still provide the path to
cuda.h explicitly during configuration, for example:
./autogen.sh && ./configure CUDA\_H\_PATH=/usr/local/cuda/include/cuda.h && make -j
Thus --use\_cuda= flag will be available to add to a command line:
./ib\_write\_bw -d ib\_dev --use\_cuda= -a
CUDA DMA-BUF requierments:
1) CUDA Toolkit 11.7 or later.
2) NVIDIA Open-Source GPU Kernel Modules version 515 or later.
installation instructions: http://us.download.nvidia.com/XFree86/Linux-x86\_64/515.43.04/README/kernel\_open.html
3) Configuration / Usage:
export the following environment variables:
1- export LD\_LIBRARY\_PATH.
e.g: export LD\_LIBRARY\_PATH=/usr/local/cuda/lib64:$LD\_LIBRARY\_PATH
2- export LIBRARY\_PATH.
e.g: export LIBRARY\_PATH=/usr/local/cuda/lib64:$LIBRARY\_PATH
perform compilation as decribe in the begining of section 4 (GPUDirect usage).
To use dma-buf, along with use\_cuda , use\_cuda\_dmabuf flag should be used.
e.g: ib\_send\_bw -d mlx5\_0 --use\_cuda=0 --use\_cuda\_dmabuf
CUDA Runtime API support:
To use the --gpu\_touch option in Perftest, you must build Perftest with support for the CUDA Runtime API (libcudart).
Run the configure script with the following flags:
./configure --enable-cudart
For releases earlier than 25.07:
./configure CUDA\_H\_PATH=/usr/local/cuda/include/cuda.h --enable-cudart
Note: Ensure that your NVIDIA CUDA Compiler (nvcc) version is compatible with your GCC version. Incompatibility between nvcc and gcc can cause build or runtime issues.
5. AES\_XTS (encryption/decryption)
In perftest repository there are two files as follow:
1) gen\_data\_enc\_key.c
2) encrypt\_credentials.c
gen\_data\_enc\_key.c file should be compiled with the following command:
#gcc gen\_data\_enc\_key.c -o gen\_data\_enc\_key -lcrypto
encrypt\_credentials.c file should be compiled with the following command:
#gcc encrypt\_credentials.c -o encrypt\_credentials -lcrypto
You must provide the plaintext credentials and the kek in seperate files in hex format.
for example:
credential\_file:
0x00
0x00
0x00
0x00
0x10
etc..
kek\_file:
0x00
0x00
0x11
0x22
0x55
etc..
Notes:
1) You should run the encrypt\_credentials program and give paths as parameters
to the plaintext credential\_file, kek\_file and the path you want the encrypted
credentials to be in (credentials\_file first).
for example:
#./encrypt\_credentials /credential\_file /kek\_file
/encrypted\_credentials\_file\_name
The output of this is a text file that you must provide its path
as a parameter to the perftest application with --credentials\_path
2)Both encrypt\_credentials.c and gen\_data\_enc\_key.c should be compiled
before using the perftest application.
3)gen\_data\_enc\_key.c compiled program path must be provided to the perftest
application with --data\_enc\_key\_app\_path  and the kek file should be
provided with --kek\_path
4) This feature supported only on RC qp type, and on ib\_write\_bw, ib\_read\_bw,
ib\_send\_bw, ib\_read\_lat, ib\_send\_lat.
5) You should load the kek and credentials you want to the device in the following way:
#sudo mlxreg -d  --reg\_name CRYPTO\_OPERATIONAL --set "credential[0]
=0x00000000,credential[1]=0x10000000,credential[2]=0x10000000,
credential[3]=0x10000000,credential[4]=0x10000000,credential[5]=0x10000000
,credential[6]=0x10000000,credential[7]=0x10000000,credential[8]=0x10000000
,credential[9]=0x10000000,kek[0]=0x00001122,kek[1]=0x55556633,kek[2]=0x33447777,kek[3]=0x22337777"
6. Payload modification
Using the --payload\_file\_path you can pass a text file, which contains a pattern,
as a parameter to perftest, and use the pattern as the payload of the RDMA verb.
You must provide the pattern in DWORD's seperated by comma and in hex format.
for example:
0xddccbbaa,0xff56f00d,0xffffffff,0x21ab025b, etc...
Notes:
1) Perftest parse the pattern and save it in LE format.
2) The feature available for ib\_write\_bw, ib\_read\_bw, ib\_send\_bw, ib\_read\_lat and ib\_send\_lat.
3) 0 size pattern is not allow.
===============================================================================
7. Known Issues
===============================================================================
1. Multicast support in ib\_send\_lat and in ib\_send\_bw is not stable.
The benchmark program may hang or exhibit other unexpected behavior.
2. Bidirectional support in ib\_send\_bw test, when running in UD or UC mode.
In rare cases, the benchmark program may hang.
perftest-2.3 release includes a feature for hang detection, which will exit test after 2 mins in those situations.
3. Different versions of perftest may not be compatible with each other.
Please use the same perftest version on both sides to ensure consistency of benchmark results.
4. Test version 5.3 and above won't work with previous versions of perftest. As well as 5.70 and above.
5. This perftest package won't compile on MLNX\_OFED-2.1 due to API changes in MLNX\_OFED-2.2
In order to compile it properly, please do:
./configure --disable-verbs\_exp
make
6. In the x390x platform virtualized environment the results shown by package test applications can be incorrect.
7. perftest-2.3 release includes support for dualport VPI test - port1-Ethernet , port2-IB. (in addition to Eth:Eth, IB:IB)
Currently, running dualport when port1-IB , port2-Ethernet still not working.
8. If GPUDirect is not working, (e.g. you see "Couldn't allocate MR" error message), consider disabling Scatter to CQE feature. Set the environmental variable MLX5\_SCATTER\_TO\_CQE=0. E.g.:
MLX5\_SCATTER\_TO\_CQE=0 ./ib\_write\_bw -d ib\_dev --use\_cuda= -a
9. When using high number of qps (>2K) with message size larger than 8KB, BW may degrade. perftest will set the polling batch to 64.
In higher scales, consider using --cqe\_poll to set the number of CQE's that polled every iteration to be higher than default value.
