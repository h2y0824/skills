# CUDA → 寒武纪 MLU 对照表

> 依据：Cambricon BANG C Developer Guide 4.7.2、BANG C/C++ 编程指南 1.7.0、CNRT 6.5.x、
> mlu-ops master（CNToolkit 3.7.2 文档集）。不同版本可能新增/改名接口；以目标机头文件为准。
> 本文用 ✅ 标记在文档中直接核对过的映射，用 ⚠️ 标记“概念相近但不能直接替换”的映射。

## 目录

1. [执行模型](#1-执行模型)
2. [主机运行时 API](#2-主机运行时-api)
3. [内存与地址空间](#3-内存与地址空间)
4. [Kernel、同步与原子](#4-kernel同步与原子)
5. [数学库与生态](#5-数学库与生态)
6. [工具链](#6-工具链)
7. [语义差异清单](#7-语义差异清单)
8. [移植工作表](#8-移植工作表)

---

## 1. 执行模型

| CUDA | MLU / BANG C | 说明 |
|---|---|---|
| kernel launch `<<<grid, block>>>` | `Kernel<<<dim, ktype, queue>>>(...)` ✅ | `dim` 是 **task grid**，不是 CUDA grid |
| `thread` | 无直接对应 | 一个 Task 内没有多线程；并行靠 `__bang_*` 向量指令 |
| `block` | 无直接对应 | 硬件按 Task 调度到 MLU Core，可能多轮迭代/展开 |
| `gridDim` / `blockDim` | `taskDim` / `taskDimX/Y/Z` ⚠️ | 只对应“任务规模”的三维形状，不等于 CUDA 线程数 |
| `blockIdx` / `threadIdx` | `taskId` / `taskIdX/Y/Z` ⚠️ | 每个 Task 一个 ID；没有 threadIdx |
| `warp` / warp shuffle | 无 | 向量指令一次处理 128B；跨 lane 交换需重排/查表 |
| `__syncthreads()` | `__sync()`（核内）或 `__sync_cluster()`（核间） ⚠️ | 语义不同：前者同步指令流，后者同步 Cluster 内 4 MLU + 1 MPU |
| cooperative groups | `__sync_cluster()` / `__sync_all()` / `__sync_all_ipu()` ⚠️ | 没有 grid-wide 协作组对象；只有硬件同步原语 |
| CUDA thread block cluster | `cnrtFuncTypeUnionN` ⚠️ | MLU Cluster 是硬件拓扑；Union 任务让 N 个 Cluster 协同，不是用户自定义 cluster |
| `cudaLaunchKernel` | 无公开的 CNRT 等价接口（文档未见） | `<<<>>>` 由 cncc 解析；启动代码必须交给 cncc 编译 |
| dynamic parallelism | 无直接对应 | 主机侧循环启动，或设备侧把工作拆成 Task |

**关键推论**

- 不要用 `threadIdx` 的思维写 kernel。先按“每个 Task 处理一个 tile”设计，再选择 tile 大小和 `taskDim`。
- `taskDim` 与实际物理核数的关系由任务类型、硬件空闲情况和驱动展开决定。不要用 `taskDim` 推断 `coreDim`。
- `coreDim`、`clusterDim`、`coreId`、`clusterId` 是**硬件拓扑**内建变量，不是启动参数。

---

## 2. 主机运行时 API

### 2.1 设备与初始化

| CUDA | CNRT / CNDrv | 备注 |
|---|---|---|
| `cudaGetDeviceCount` | `cnrtGetDeviceCount` ✅ | |
| `cudaSetDevice` | `cnrtSetDevice` ✅ | 只设置设备；Shared Context 可能尚未激活 |
| `cudaGetDevice` | `cnrtGetDevice` ✅ | |
| `cudaDeviceReset` | `cnrtDeviceReset` ✅ | 会销毁当前线程 Shared Context 下的资源 |
| `cudaDeviceSynchronize` | `cnrtSyncDevice` ✅ | 等待该设备所有 Queue |
| `cudaDeviceGetAttribute` | `cnrtDeviceGetAttribute` ✅ | 属性枚举不同，需查 `cnrt.h` |
| （无） | `cnInit()`（CNDrv） ✅ | CNRT 隐式初始化；CNDrv 必须显式 `cnInit()` |
| （无） | `cnCtxGetCurrent()` ✅ | 获取 CNRT 初始化时创建的 Shared Context |

### 2.2 内存

| CUDA | CNRT | 备注 |
|---|---|---|
| `cudaMalloc` | `cnrtMalloc` ✅ | |
| `cudaFree` | `cnrtFree` ✅ | |
| `cudaHostAlloc` / `cudaMallocHost` | `cnrtHostMalloc` ✅ | 页锁定主机内存 |
| `cudaFreeHost` | `cnrtFreeHost` ✅ | |
| `cudaMemcpy` | `cnrtMemcpy(dst, src, size, dir)` ✅ | 同步 |
| `cudaMemcpyAsync` | `cnrtMemcpyAsync(dst, src, size, queue, dir)` ✅ | **queue 在 dir 之前**，与 `cnrtMemcpy` 不同 |
| `cudaMemcpy2D` | `cnrtMemcpy2D` ✅ | 参数结构不同，查头文件 |
| `cudaMemcpy3D` | `cnrtMemcpy3D` ✅ | |
| `cudaMemcpyToSymbol` | `cnrtMemcpyToSymbol` ✅ | 用于 `__mlu_device__` 全局变量 |
| `cudaMemcpyFromSymbol` | `cnrtMemcpyFromSymbol` ✅ | |
| `cudaMemset` | ⚠️ CNRT 文档未列出 `cnrtMemset` | 设备侧用 `__bang_write_zero` / `__nramset`；或主机准备缓冲区；或查版本头文件 |
| `cudaMallocManaged` | ⚠️ 无 drop-in；CNRT 提供 VMM（`cnrtMmap`、`cnMemCreate` 等） | 统一内存语义不等价，CE 平台还涉及缓存一致性 |
| `cudaHostRegister` | ⚠️ 未在本次资料中核实 | 查 `cnrt.h` 或改用 `cnrtHostMalloc` |

### 2.3 Queue / Stream

| CUDA | CNRT | 备注 |
|---|---|---|
| `cudaStream_t` | `cnrtQueue_t` ✅ | |
| `cudaStreamCreate` | `cnrtQueueCreate` ✅ | |
| `cudaStreamCreateWithFlags` | `cnrtQueueCreateWithPriority` / 查版本 | 没有完全同名 flags 接口 |
| `cudaStreamDestroy` | `cnrtQueueDestroy` ✅ | |
| `cudaStreamSynchronize` | `cnrtQueueSync` ✅ | |
| `cudaStreamQuery` | `cnrtQueueQuery` ✅ | 完成返回 `cnrtSuccess`，未完成返回 `cnrtErrorNotReady` |
| `cudaStreamWaitEvent` | `cnrtQueueWaitNotifier` ✅ | Queue 上后续任务等待 notifier |
| 默认 stream | 默认 Queue（句柄传 `0` 或 `NULL`） ✅ | 每设备、每主机线程一个；库管理，不能 `cnrtQueueDestroy` |
| `cudaStreamAddCallback` | 未在本次资料中核实 | 查版本 API |

Queue 内部是**顺序执行**的；跨 Queue 的依赖必须显式用 `cnrtQueueWaitNotifier` 建立。

### 2.4 Event / Notifier

| CUDA | CNRT | 备注 |
|---|---|---|
| `cudaEvent_t` | `cnrtNotifier_t` ✅ | |
| `cudaEventCreate` | `cnrtNotifierCreate` ✅ | |
| `cudaEventCreateWithFlags` | `cnrtNotifierCreateWithFlags` ✅ | flags 名称不同 |
| `cudaEventDestroy` | `cnrtNotifierDestroy` ✅ | |
| `cudaEventRecord` | `cnrtPlaceNotifier` ✅ | 记录 Queue 中当前未完成的任务 |
| `cudaEventSynchronize` | `cnrtWaitNotifier` ✅ | 阻塞主机线程 |
| `cudaEventQuery` | `cnrtQueryNotifier` ✅ | |
| `cudaStreamWaitEvent` | `cnrtQueueWaitNotifier` ✅ | 跨 Queue 依赖 |
| `cudaEventElapsedTime` | `cnrtNotifierElapsedTime` ✅（文档：毫秒）/ `cnrtNotifierDuration`（官方样例按微秒使用） ⚠️ | 两者都存在且单位说明不完全一致；选定一个并在目标机验证 |
| IPC event | `cnrtIpcGetNotifierHandle` / `cnrtIpcOpenNotifierHandle` ⚠️ | 跨进程同步；名称需按版本核对 |

### 2.5 错误处理

| CUDA | CNRT | 备注 |
|---|---|---|
| `cudaGetLastError` | `cnrtGetLastError` ✅ | |
| `cudaPeekAtLastError` | ⚠️ 查版本 | |
| `cudaError_t` | `cnrtRet_t` ✅ | 成功为 `cnrtSuccess` |
| `cudaGetErrorString` | ⚠️ 查版本 | CNDrv 有 `cnGetErrorString` |

`CNRT_CHECK(expr)` 是官方样例常用的宏：把返回值打印成文件/行号/错误码后退出。生产环境应改为可恢复的错误处理。

### 2.6 Graph / 高级特性

| CUDA | MLU | 备注 |
|---|---|---|
| CUDA Graph | CNRT TaskTopo / QueueCapture ⚠️ | 概念相近，API 完全不同；见 CNRT 文档第 6.5.14 节 |
| L2 persistence | CNRT L2 Cache 管理 / `cnrtCacheOperation` ⚠️ | 语义和粒度不同 |
| IPC memory | CNRT VMM / IPC 接口 ⚠️ | 查版本 |
| VMM | `cnrtMmap`、`cnrtMunmap`、`cnMemCreate`、`cnMemAddressReserve` ⚠️ | 概念对应；具体归属（CNRT/CNDrv）和签名需核对 |

---

## 3. 内存与地址空间

| CUDA | BANG C | 位置 | 关键差异 |
|---|---|---|---|
| `__global__` 指针指向的 global memory | 普通设备指针（GDRAM） | 片外，所有 Core 共享 | 主机侧 `cnrtMalloc` 分配 |
| `__device__` 全局变量 | `__mlu_device__` ✅ | GDRAM 全局 | 必须声明在全局作用域；不自动初始化；用 `cnrtMemcpyToSymbol` 访问 |
| `__constant__` | `__mlu_const__` ✅ | GDRAM，经 L2 加速 | 不是小容量片上常量区；必须全局作用域；不自动初始化 |
| `__shared__` | `__mlu_shared__` ✅ | **SRAM，Cluster 共享** | 生存期为整个 Kernel，不是每 block 私有；不自动初始化；多核访问需同步 |
| 寄存器 | GPR | 片上 | 最大 48 bit；标量专用 |
| 可编程 shared/L1 | 无直接对应 | — | MLU 的片上缓冲是显式 NRAM/WRAM/SRAM，不是自动缓存 |
| 局部数组 | `__nram__` / `__wram__` / `__ldram__` | 片上或片外 | 普通栈数组不能用于向量/张量指令 |
| texture / surface | 无直接对应 | — | 查表用 `__bang_lut_s32/s16`；图像类用 CNNL/mlu-ops |
| `cudaMemcpyToSymbol` | `cnrtMemcpyToSymbol` ✅ | — | 只对 `__mlu_device__` 等全局符号 |

### 地址空间修饰符速记

| 修饰符 | 位置 | 生存期 | 谁能访问 | 典型用途 |
|---|---|---|---|---|
| `__nram__` | NRAM（每 MLU Core 私有） | 一个 Task | 本 Core | 向量/张量计算的输入输出 |
| `__wram__` | WRAM（每 MLU Core 私有） | 一个 Task | 本 Core | 卷积核、矩阵乘的 B 矩阵 |
| `__ldram__` | LDRAM（每 Core 私有，片外） | 一个 Task | 本 Core | 放不下的私有数据 |
| `__mlu_shared__` | SRAM（Cluster 共享） | 整个 Kernel | Cluster 内所有 Core + MPU | Cluster 内数据交换、多核协作 |
| `__mlu_const__` | GDRAM（全局常量） | 上下文 | 所有 Task | 只读常量、LUT |
| `__mlu_device__` | GDRAM（全局变量） | 上下文 | 所有 Task | 跨 Task 通信、原子目标、符号拷贝 |

**默认对齐**：以上数组起始地址默认 **64B 对齐**；可用 `__attribute__((aligned(N)))` 提高，N 必须是 ≥64 的 2 的幂。

---

## 4. Kernel、同步与原子

### 4.1 Kernel 修饰符

| CUDA | BANG C | 说明 |
|---|---|---|
| `__global__` | `__mlu_entry__` ✅ | Kernel 入口；只能主机侧调用；无返回值；异步执行 |
| `__device__` 函数 | `__mlu_func__` ✅ | 设备侧函数，默认内联 |
| `__host__ __device__` | `__mlu_host__` + `__mlu_func__` ✅ | 两侧可调用 |
| 编译器内建 | `__mlu_builtin__` ✅ | 一般不用手写 |
| （mlu-ops 风格） | `__mlu_global__` ⚠️ | 官方示例/算子库也用它做入口；新代码优先 `__mlu_entry__`，不要盲目重写已有代码 |

### 4.2 同步

| CUDA | BANG C | 范围 | 用途 |
|---|---|---|---|
| `__syncthreads()` | `__sync()` ✅ | 一个 Core 内所有指令流 | 最稳妥的核内全同步 |
| （细粒度） | `__sync_compute()` ✅ | Compute 流 | 只等计算完成 |
| （细粒度） | `__sync_io()` ✅ | IO 流 | 只等片外搬运完成 |
| （细粒度） | `__sync_move()` ✅ | Move 流 | 只等片上搬运完成 |
| （细粒度） | `__sync_io_move_compute()` ✅ | IO+Move+Compute | 三条流一起等 |
| `__syncthreads()`（跨 block 不保证） | `__sync_cluster()` ✅ | 1 MPU + 4 MLU（376/372 等） | Cluster 内全同步 |
| cooperative groups | `__sync_all_ipu()` / `__sync_all_mpu()` / `__sync_all()` ✅ | 所有参与 Kernel 的 Core | 全局同步，代价最高 |
| `__syncwarp()` | 无 | — | 没有 warp 概念 |

**选择原则**：能 `__sync_compute` 就不 `__sync`，能 `__sync_cluster` 就不 `__sync_all`。同步范围越大，越容易把并行性吃掉。

### 4.3 原子

| CUDA | BANG C | 约束 |
|---|---|---|
| `atomicAdd` | `__bang_atomic_add` ✅ | `dst` 在 NRAM；`src1` 在 `__mlu_device__`（GDRAM）；`src2` 在 NRAM 或标量；`src1` 按元素类型对齐 |
| `atomicMax/Min` | `__bang_atomic_max` / `_min` 及 `_number_` / `_nan_` 变体 ✅ | 按类型/架构支持不同 |
| `atomicAnd/Or/Xor` | `__bang_atomic_and/or/xor` ✅ | |
| `atomicCAS` | ⚠️ 查版本 | 不要假设存在 |
| `atomicExch` | `__bang_atomic_exch`（查版本） ⚠️ | |
| `__threadfence()` | ⚠️ 无直接同名；用同步原语/内存序接口，查版本 | |

原子操作属于 IO 流，代价高；能用“每 Task 写 workspace，最后统一归约”就不要用全局原子。

---

## 5. 数学库与生态

| GPU 生态 | MLU 对应 | 说明 |
|---|---|---|
| cuBLAS | CNNL 的 BLAS/矩阵接口 ✅ | `cnnlMatMul`、`cnnlBatchMatMul`、`cnnlAxpy`、`cnnlScale`、`cnnlOpTensor`；没有 `cnnlGemm` 同名接口 |
| cuDNN | CNNL ✅ | `cnnlConvolutionForward/BackwardData/BackwardFilter`、`cnnlPoolingForward/Backward`、`cnnlActivationForward/Backward`、`cnnlSoftmaxForward/Backward`、`cnnlBatchNorm*`、`cnnlRNN*`、`cnnlLrn`、`cnnlFusedDropout` 等 |
| cuSPARSE | CNNL 稀疏接口 / mlu-ops ⚠️ | 按算子查 CNNL Op List；不保证一一对应 |
| NCCL | CNCL ⚠️ | 集合通信概念对应；API 名称以 CNCL 版本文档为准 |
| CUB / Thrust | mlu-ops / BANG C 模板 ⚠️ | 没有 STL 式设备算法库；归约/扫描/排序需用 BANG C 或 mlu-ops 现成算子 |
| TensorRT | MagicMind ⚠️ | 寒武纪推理引擎；模型转换流程不同，需单独评估 |
| CUDA Math API | BANG C 数学库 / `libdevice` ⚠️ | 函数名和精度可能不同；注意 fast-math 差异 |
| NPP | CNNL / mlu-ops ⚠️ | 图像预处理需逐算子确认 |
| NVTX | CNPerf 标注接口 ⚠️ | 查版本 |

> CNNL 的具体签名、描述符设置和 `_v2` 版本差异较大。迁移时先查目标版本的 CNNL Developer Guide 或 `cnnl.h`，不要照搬网上示例。

---

## 6. 工具链

| CUDA | MLU | 说明 |
|---|---|---|
| `nvcc` | `cncc` ✅ | 编译 `.mlu`；`--bang-mlu-arch=` 指定架构 |
| `nvcc -arch=sm_XX` | `--bang-mlu-arch=mtp_372` ✅ | 单架构；多架构用 `--bang-arch=compute_XX` 生成 fatbin |
| `nvcc -G -g` | `cncc -g`（仅 `-O0`） ✅ | 调试构建 |
| `nvcc -O3` | `cncc -O3` ✅ | **cncc 默认 -O0**，性能代码必须显式加 |
| `cuda-gdb` | `cngdb` ✅ | CNGDB 调试器 |
| Nsight Compute | `cnperf-cli record --pmu` / `--kernel_profiling` ✅ | 单算子 PMU 分析 |
| Nsight Systems | `cnperf-cli record` + `cnperf-cli timechart` ✅ | E2E timeline |
| `nvidia-smi` | `cnmon info` ✅ | 设备/温度/功耗/利用率 |
| `nvprof` | `cnperf-cli` ✅ | |
| `compute-sanitizer` | 无完全等价工具 ⚠️ | 用 CNGDB + core dump 环境变量（`CN_CORE_DUMP_*`） |
| `cuobjdump` / `nvdisasm` | CNBin/CNFatbin 产物 ⚠️ | 设备 ELF/fatbin；具体 dump 工具查 CNToolkit |
| `cuda-memcheck` | ⚠️ 无同名工具 | 越界通常表现为结果错误/崩溃；用边界检查和 CNGDB |

---

## 7. 语义差异清单

1. **并行粒度**：CUDA 用 thread；MLU 用 Task + 向量指令。逐线程移植会得到极慢的标量代码。
2. **片上内存管理**：CUDA 的 shared/L1 是自动的；MLU 的 NRAM/WRAM/SRAM 要显式声明和搬运。
3. **同步语义**：`__syncthreads()` 只同步一个 block；`__sync()` 同步一个 Core 的指令流；`__sync_cluster()` 同步一个 Cluster 的 5 个核。不要互换。
4. **`__constant__`**：MLU 的 `__mlu_const__` 在 GDRAM，不是片上常量缓存；小常量应尽量编译期展开或放 NRAM。
5. **统一内存**：没有 `cudaMallocManaged` 的 drop-in；需要显式拷贝或 VMM，CE 平台还要处理缓存一致性。
6. **浮点归约顺序**：多 Task 归约的累加顺序与 CUDA 不同，浮点结果可能有差异；验收标准要提前定。
7. **Kernel 异步**：`<<<>>>` 返回不等于执行完；忘记 `cnrtQueueSync` 会读到旧数据。
8. **默认优化级别**：cncc 默认 `-O0`，与 nvcc 默认优化行为不同。
9. **架构绑定**：设备目标文件不跨架构；必须显式指定 `--bang-mlu-arch`，或用 fatbin。
10. **设备侧 C++ 限制**：不支持函数指针；不支持设备侧全局变量动态初始化；不支持 `extern` 修饰设备侧全局变量/函数。模板和 lambda 的支持范围也以版本文档为准。
11. **主机启动代码**：`<<<>>>` 只有 cncc 能解析；包含启动语句的文件不能直接交给 g++。
12. **数组初始化**：`__nram__`、`__wram__`、`__ldram__`、`__mlu_shared__`、`__mlu_const__`、`__mlu_device__` 的数组都**不会自动初始化**，必须显式写值。

---

## 8. 移植工作表

对每个 CUDA 文件/函数填写下表，能显著减少“漏改”：

| CUDA 资产 | 类型 | 对应 MLU 实现 | 切分方式 | 内存 | 同步 | 尾块 | 状态 |
|---|---|---|---|---|---|---|---|
| `foo_kernel` | elementwise | `foo_block.mlu` | 按元素均分，tile 128B 对齐 | NRAM 双缓冲 | 无/`__sync` | 标量循环 | 待迁 |
| `bar_kernel` | reduction | `bar_block.mlu` + workspace | 按行/按块 | NRAM + GDRAM workspace | `__sync_cluster` | 掩码/边界 | 待迁 |
| `cublasSgemm` | 库调用 | `cnnlMatMul` | — | — | Queue 顺序 | — | 待迁 |
| `cudnnConvolutionForward` | 库调用 | `cnnlConvolutionForward` | — | — | Queue 顺序 | — | 待迁 |
| `ncclAllReduce` | 通信 | CNCL AllReduce | — | — | — | — | 待核对 |
| `torch.cuda` | Python | `torch_mlu` / `.to("mlu")` | — | — | `torch.mlu.synchronize()` | — | 待核对 |

配套清单：

- [ ] 所有 `__global__` / `__device__` / `__constant__` / `__shared__` 已替换
- [ ] 所有 `threadIdx` / `blockIdx` / `blockDim` / `gridDim` 已替换
- [ ] 所有 `cuda*` / `cublas*` / `cudnn*` / `nccl*` 已替换或标记
- [ ] 所有 kernel 启动点已由 cncc 编译
- [ ] 每个 kernel 的 tile 大小、尾块、越界检查已确认
- [ ] 所有异步拷贝后都有正确的 `__sync` / Queue 同步
- [ ] 构建系统已移除 nvcc/CUDA language，加入 cncc 与 CNRT/CNNL 链接
- [ ] 目标架构、CNToolkit/CNNL 版本已记录
