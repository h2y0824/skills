# 资料来源、版本与核实状态

> 本 skill 的所有技术结论都来自下列资料。写代码前请先确认目标机的版本；本页标注了哪些是直接核实的、哪些需要本机核对。

## 1. 官方入口

### 1.1 本 skill 依据的三个入口

| 资料 | 版本 | 链接 |
|---|---|---|
| Cambricon BANG C Developer Guide | BANG C 4.7.2 / CNToolkit 3.7.2 / SDK 1.15.0 | https://www.cambricon.com/docs/sdk_1.15.0/cntoolkit_3.7.2/cambricon_bang_c_4.7.2/index.html |
| Cambricon BANG C/C++ 编程指南 | 1.7.0 / CNToolkit 3.7.2 / SDK 1.15.0 | https://www.cambricon.com/docs/sdk_1.15.0/cntoolkit_3.7.2/programming_guide_1.7.0/index.html |
| mlu-ops 算子库 | master（2026-11 抓取） | https://github.com/Cambricon/mlu-ops |

### 1.2 相关文档（来自 mlu-ops README）

| 资料 | 链接 |
|---|---|
| MLU-OPS 用户手册 | https://www.cambricon.com/docs/sdk_1.15.0/cambricon_bang_c_ops_0.9.0/user_guide/index.html |
| CNNL Developer Guide（1.21.1） | https://www.cambricon.com/docs/sdk_1.15.0/cambricon_cnnl_1.21.1/developer_guide/index.html |
| CNRT Developer Guide（6.5.2） | https://www.cambricon.com/docs/sdk_1.13.0/cntoolkit_3.5.2/cnrt_6.5.2/index.html |
| CNDrv Developer Guide（2.5.2） | https://www.cambricon.com/docs/sdk_1.13.0/cntoolkit_3.5.2/cndrv_2.5.2/index.html |
| CNGDB Developer Guide（3.5.0） | https://www.cambricon.com/docs/sdk_1.13.0/cntoolkit_3.5.2/cngdb_3.5.0/index.html |
| Libdevice Developer Guide（4.5.1） | https://www.cambricon.com/docs/sdk_1.13.0/cntoolkit_3.5.2/libdevice_4.5.1/index.html |
| MLU 架构调优指南 | https://www.cambricon.com/docs/sdk_1.13.0/cntoolkit_3.5.2/cntoolkit_tuning_0.4.1/index.html |
| 寒武纪开发者社区 | https://developer.cambricon.com/ |
| SDK 下载 | https://sdk.cambricon.com/download |

### 1.3 文档内已抓取的具体页面

`_research/text/` 下保存了以下页面的文本（由官方 HTML 转换）：

- 编程指南：`prog_intro`、`prog_hw`、`prog_model`、`prog_samples`、`prog_cncc`、`prog_cnbin`、`prog_runtime`、`prog_compat`、`prog_perf`、`prog_best`、`prog_cppext`、`prog_cppsupport`、`prog_env`、`prog_appendix`
- BANG C 内建函数：`bang_memcpy1d`、`bang_memset1d`、`bang_atomic`、`bang_ai`、`bang_control`、`bang_discrete_move`、`bang_intercore`、`bang_intracore`、`bang_matmul`、`bang_vecop`、`bang_vecmove`、`bang_veccmp`、`bang_scalarconv`、`bang_addrpred`、`bang_appendix`
- `_doc_toc.txt`：两个文档的完整目录
- `_research/mluops/`：README、`kernel.h`、`abs_block.mlu`、`abs.cpp`、`unary_op_3pipeline.h`、`BANG-C-OPS-Develop-Guide.md`

---

## 2. 版本矩阵

编写代码前必须确认：

| 项 | 获取方式 | 影响 |
|---|---|---|
| 板卡/芯片型号 | `cnmon info` | 决定架构和容量 |
| 架构标识 | 文档/`cnmon`/厂商告知 | `--bang-mlu-arch=mtp_xxx` 必填 |
| CNToolkit 版本 | `cncc --version` | 编译选项、内建函数支持范围 |
| CNRT 版本 | `$NEUWARE_HOME` 下库版本 | API 名称/签名 |
| CNNL 版本 | `cnnl.h` 或库版本 | 算子覆盖、`_v2` 接口 |
| 驱动版本 | `cnmon info` | mlu-ops 要求 ≥ v6.0.3 |
| torch_mlu | `python3 -c "import torch_mlu; print(torch_mlu.__version__)"` | 是否走框架路线 |

已知的 mlu-ops 要求：CNToolkit ≥ v4.1.0、CNNL ≥ v1.28.0、驱动 ≥ v6.0.3。

---

## 3. 已核实的事实

以下是直接来自官方文档/源码、可以较高置信度使用的结论。使用时仍建议对照目标版本。

### 3.1 编译与工具

- `cncc` 编译 `.mlu`；`--bang-mlu-arch=` 指定单架构；`--bang-arch=` 生成 fatbin。
- `cncc` 默认优化级别是 `-O0`；`-O3` 需显式开启。
- `-g` 只能与 `-O0` 配合。
- `-S` / `--bang-device-only` / `--bang-host-only` / `--bang-fatbin-only` 存在。
- `__BANG_ARCH__` 是数值宏（如 372）。
- `__MLU_NRAM_SIZE__` / `__MLU_SRAM_SIZE__` / `__MLU_WRAM_SIZE__` 单位是 KB。
- 设备端产物是 CNBin（ELF）；多架构是 CNFatbin。
- 工具链：`cngdb`（调试）、`cnperf-cli`（性能）、`cnmon`（设备监控）。

### 3.2 运行时

- CNRT 隐式初始化；CNDrv 需要 `cnInit()`。
- `cnrtGetDeviceCount`、`cnrtSetDevice`、`cnrtGetDevice`、`cnrtDeviceReset`、`cnrtSyncDevice`。
- `cnrtMalloc` / `cnrtFree` / `cnrtHostMalloc` / `cnrtFreeHost`。
- `cnrtMemcpy(dst, src, size, dir)`；`cnrtMemcpyAsync(dst, src, size, queue, dir)`。
- `cnrtMemcpy2D` / `cnrtMemcpy3D`；`cnrtMemcpyToSymbol` / `cnrtMemcpyFromSymbol`。
- `cnrtQueueCreate` / `cnrtQueueDestroy` / `cnrtQueueSync` / `cnrtQueueQuery`。
- `cnrtNotifierCreate` / `cnrtNotifierDestroy` / `cnrtPlaceNotifier` / `cnrtWaitNotifier` / `cnrtQueryNotifier` / `cnrtQueueWaitNotifier`。
- `cnrtNotifierElapsedTime`（文档：毫秒）、`cnrtNotifierDuration`（官方样例按微秒使用）。
- 默认 Queue 不能销毁；每设备/每主机线程一个。
- `cnrtGetLastError` 存在。

### 3.3 执行模型

- Kernel 启动语法 `Kernel<<<dim, ktype, queue>>>(...)`。
- `cnrtFunctionType_t` 取值含 `cnrtFuncTypeBlock`、`cnrtFuncTypeUnion1/2/4/8`（mlu-ops 还定义了 Union16 宏）。
- `taskId` 线性编号；`taskDim = taskDimX * taskDimY * taskDimZ`；`taskId = taskIdZ*taskDimY*taskDimX + taskIdY*taskDimX + taskIdX`。
- Union 约束：起始物理 Cluster ID 被 N 整除；至少 N 个 Cluster 空闲；`taskDimX % (N * coreDim) == 0`；最小并行度 `clusterDim*coreDim`。
- 372 每 Cluster 4 MLU Core + 1 Memory Core；322 的 `CORE_DIM` 为 1。
- Kernel 异步执行；`<<<>>>` 后需同步。

### 3.4 内存

- 地址空间：`__nram__`、`__wram__`、`__ldram__`、`__mlu_shared__`、`__mlu_const__`、`__mlu_device__`。
- 默认 64B 对齐；可用 `__attribute__((aligned(N)))`，N ≥64 且为 2 的幂。
- 数组不自动初始化。
- `__memcpy` 第三个参数是字节数。
- 容量（KB）：mtp_220 512/512/2048；mtp_270 512/1024/2048；mtp_290 512/512/2048；mtp_372 768/1024/4096（NRAM/WRAM/SRAM）。
- mlu-ops 预留 128KB 栈（`REM_FOR_STACK`）。
- 性能对齐建议：NRAM 16B/128B、SRAM 16B/128B、WRAM 64B/128B、GDRAM 512B/512B、LDRAM 512B/512B（地址对齐/size 对齐）。
- GDRAM 单次读最小 64B；写 <64B 触发读-改-写。
- 向量指令每 cycle 处理 128B。

### 3.5 计算与同步

- `__bang_add` 等要求 dst/src 在 NRAM；2xx 上地址 64B 对齐、`elem_count*sizeof(type)` 128B 整除。
- float 在 2xx+ 支持；int/short/char 在 3xx+（tp_520 除外）；bfloat16 在 5xx+。
- `__bang_reduce_sum` 每 128B 求和到 dst 首元素；dst ≥128B；`elem_count*sizeof` 128B 整除；2xx 上其余置零，3xx+ 不修改。
- `__bang_sum`（返回标量）仅较新架构（BANG ≥520 / mtp_5xx）。
- `__bang_atomic_add(dst_nram, src1_gdram___mlu_device__, src2, size)`；322/520 不支持。
- 同步：`__sync`、`__sync_compute`、`__sync_io`、`__sync_move`、`__sync_io_move_compute`、`__sync_cluster`、`__sync_all_ipu`、`__sync_all_mpu`、`__sync_all`。
- 四条指令流：IO / Move / Compute / Scalar。
- 设备侧 C++ 限制：不支持函数指针、不支持设备侧全局变量动态初始化、不支持 `extern` 修饰设备侧全局变量和函数。

### 3.6 CNNL 已核实的接口

`cnnlCreate` / `cnnlDestroy`、`cnnlSetQueue` / `cnnlGetQueue`、
`cnnlCreateTensorDescriptor` / `cnnlSetTensorDescriptor` / `cnnlGetTensorDescriptor` / `cnnlDestroyTensorDescriptor`、
`cnnlConvolutionForward` / `BackwardData` / `BackwardFilter`、
`cnnlPoolingForward` / `Backward`、`cnnlActivationForward` / `Backward`、
`cnnlSoftmaxForward` / `Backward`、`cnnlBatchNormForwardInference` / `Training` / `Backward`、
`cnnlRNNForwardInference` / `Training`、`cnnlMatMul`、`cnnlBatchMatMul`、
`cnnlAxpy`、`cnnlScale`、`cnnlOpTensor`、`cnnlReduce`、`cnnlTranspose`、
`cnnlConcat`、`cnnlSplit`、`cnnlPad`、`cnnlNms`、`cnnlLrn`、`cnnlEmbeddingForward`、`cnnlFusedDropout`。

**已确认不存在**：`cnnlGemm`、`cnnlSgemm`、`cnnlDot`、`cnnlNrm2`、`cnnlAddTensor`。GEMM 用 `cnnlMatMul` / `cnnlBatchMatMul`；按元素运算用 `cnnlOpTensor` / `cnnlScale`。

---

## 4. 需要在本机核对的事项

以下内容本 skill **没有**完全核实，使用前必须查目标机头文件或对应版本文档：

| 事项 | 为什么不确定 | 怎么核对 |
|---|---|---|
| `cnrtMemset` 是否存在 | 本次核对的文档未列出 | `grep -r "cnrtMemset" $NEUWARE_HOME/include` |
| `cnrtMemcpyAsync` 精确签名 | 官方示例为 `(dst, src, size, queue, dir)`，仍需确认版本 | 查看 `cnrt.h` |
| `cnrtNotifierDuration` / `ElapsedTime` 的单位 | 文档与示例表述不一致 | 用已知耗时的 kernel 校准 |
| `cnrtQueueWaitNotifier` 第三个参数 | 版本差异 | 查看 `cnrt.h` |
| Union 是否支持 N=16 | 编程指南示例写 1/2/4/8，mlu-ops 定义到 16 | 查看 `cnrt.h` 枚举 |
| C++ 模板/lambda 的支持范围 | 版本文档可能更新 | 编译验证 |
| CNCL 具体 API 名称 | 未抓取 CNCL 文档 | CNCL Developer Guide |
| CNNL 各接口的精确签名/`_v2` 差异 | 未逐接口核对 | `cnnl.h` + 对应文档 |
| torch_mlu 的版本/API/自定义算子接入 | 未抓取 torch_mlu 文档 | torch_mlu 官方仓库 |
| `__bang_matmul` / `__bang_conv` 参数形式 | 只确认存在 | BANG C 文档对应页 |
| 统一内存/VMM 的语义与限制 | 只确认接口存在 | CNRT 文档 + 实测 |
| GPU 与 MLU 的浮点差异范围 | 取决于具体算子 | 用黄金数据实测 |
| CNPerf 精确命令行参数 | 版本变化 | `cnperf-cli --help` |

---

## 5. 术语表

| 术语 | 含义 |
|---|---|
| MLU | Machine Learning Unit，寒武纪 AI 加速卡/芯片 |
| BANG C | 寒武纪 C 语言扩展，用于编写设备侧 kernel |
| BANG C++ | BANG C 的 C++ 扩展子集 |
| CNCC | Cambricon Compiler Collection，编译 `.mlu` |
| CNRT | Cambricon Runtime，主机侧运行时 API |
| CNDrv | Cambricon Driver API，更底层的驱动接口 |
| CNNL | Cambricon Neural Network Library，算子库 |
| CNCL | Cambricon Communication Library，集合通信库 |
| CNBin | 设备侧 ELF 目标文件 |
| CNFatbin | 多架构设备代码包 |
| CNGDB | 调试器 |
| CNPerf | 性能分析工具 |
| cnmon | 设备监控工具（类 nvidia-smi） |
| MagicMind | 寒武纪推理引擎（类 TensorRT） |
| Task | MLU 的调度单位，一个 MLU Core 上的一次 kernel 实例 |
| Cluster | 硬件拓扑单位，通常 4 MLU Core + 1 Memory Core + 共享 SRAM |
| MLU Core | 计算核（IPU） |
| Memory Core | Cluster 内的内存/搬运核（MPU） |
| NRAM | 核内向量/张量存储 |
| WRAM | 核内权重存储 |
| SRAM | Cluster 内共享存储 |
| LDRAM | 核私有片外存储 |
| GDRAM | 全局显存 |
| GPR | 通用寄存器 |
| NFU | Neural Function Unit，张量计算单元 |
| Union | 多个 Cluster 协同执行的任务类型 |
| workspace | 算子运行时的临时全局内存 |

---

## 6. 资料使用建议

1. **优先看目标版本的文档**，不要用本 skill 的 API 名称直接写代码。
2. **官方示例优先**：`$NEUWARE_HOME/samples`、mlu-ops 的源码比任何二手资料可靠。
3. **先小后大**：先用最小样例确认工具链和 API，再迁移业务代码。
4. **保留证据**：每次“确认”都记录命令输出或文件路径，方便复盘。
5. **不确定就标注**：代码注释/文档里写“需核对”，比假装确定更安全。
