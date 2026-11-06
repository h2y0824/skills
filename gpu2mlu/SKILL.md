---
name: gpu2mlu
description: 将 CUDA/GPU 项目迁移到寒武纪 MLU（Cambricon MLU / BANG C / CNRT / CNNL / CNCL / mlu-ops / torch_mlu）时使用。只要用户提到寒武纪、MLU、BANG C、cncc、CNRT、CNNL、mlu-ops、CUDA 转 MLU、GPU 国产化替代、.cu 改 .mlu、MLU 算子开发、MLU 性能调优，或遇到 MLU 上的对齐、精度、链接、架构不匹配、结果错误等问题，就应使用本 skill——即使用户没有明确说“迁移”。本 skill 也适用于在已有 MLU 工程里新增/优化 BANG C kernel、把 CUDA 构建系统改为 cncc、以及评估某段 CUDA 代码能否直接映射到 MLU。
---

# GPU2MLU：从 CUDA 到寒武纪 MLU

## 这个 skill 怎么用

把迁移当成一条流水线，不要一上来改代码：

```
环境探测 → 项目盘点 → 选路线 → 构建系统 → 分层移植 → 正确性 → 性能 → 回归
```

- **先探测再写代码。** 目标架构、CNToolkit/CNNL 版本、片上容量、是否装了 torch_mlu，都会改变实现方式。不要凭记忆写 MLU API，也不要把本文档里的 `mtp_372` 当成用户的目标架构。
- **按需读 reference。** 用户往往只问一个点；先看下面的路由表，只加载相关文件。
- **区分“已核实”和“需在本机核对”。** 本 skill 的内容来自 CNToolkit 3.7.2 / BANG C 4.7.2 / 编程指南 1.7.0 / mlu-ops master；不同版本的接口、枚举名、支持架构可能不同。写代码前用目标机的 `$NEUWARE_HOME/include` 头文件或对应版本文档核对签名。
- **性能不是移植完再做。** MLU 的性能高度依赖 tile 大小、对齐、机上驻留和软流水；如果先写“能跑”的逐元素版本，后面往往要重写。

## 第 0 步：环境探测（不要跳过）

在目标 MLU 机器上运行（路径相对本 skill 目录）：

```bash
bash scripts/probe_mlu_env.sh
```

或手动确认并记录：

```bash
cncc --version                 # CNCC / BANG C 版本
cnmon info                     # 板卡型号、设备数、固件/驱动
echo "$NEUWARE_HOME"           # 通常为 /usr/local/neuware
ls "$NEUWARE_HOME/include"     # bang.h / cnrt.h / cnnl.h / cncl.h 是否存在
python3 -c "import torch, torch_mlu; print(torch.__version__, torch_mlu.__version__)"
```

必须落表的事实：

| 项 | 示例 | 为什么重要 |
|---|---|---|
| 目标架构 | `mtp_372`、`mtp_592`、`tp_322` | `cncc --bang-mlu-arch=` 必填，编错架构无法运行 |
| CNToolkit / CNNL | 4.x / 1.x | API 名称和 `_v2` 后缀随版本变化 |
| 设备数 / 单卡 Cluster 数 | 4 Cluster、每 Cluster 4 MLU Core | 决定 `taskDimX` 与 Union 任务类型 |
| NRAM/SRAM 容量 | 用 `__MLU_NRAM_SIZE__`、`__MLU_SRAM_SIZE__`（单位 KB） | 决定 tile 大小，不能照抄别的卡 |
| 是否 torch_mlu | 有/无 | 决定走框架路线还是 BANG C 路线 |

如果当前机器没有 MLU，先向用户索要以上输出；在拿到之前，只写与架构无关的迁移方案和占位代码，不要硬编码架构参数。

## 四个必须先建立的心智模型

### 1. Task 不是 thread

CUDA 里一个 kernel 启动成千上万个线程，每个线程处理一个元素；BANG C 里 kernel 的每个实例是一个 **Task**，Task 由 MLU Core 执行，Task 内部没有 CUDA 意义上的多线程。

- `taskId` 是 Task 在 task grid 中的线性编号，`taskDim` 是 Task 总数；`taskIdX/Y/Z`、`taskDimX/Y/Z` 是三维形式。
- 数据并行不靠“多线程”，而靠 `__bang_*` **向量指令**在 NRAM 上一次处理 128B（或更多）数据。
- 移植时不要逐线程翻译。正确的问法是：**一个线程原本处理多少元素？把它合并成一个 tile（至少 128B），让一个 Task 用向量指令处理这个 tile。**
- `dim.x` 通常设为你希望同时占用的 MLU Core 数（如 4、8、16、32），而不是 CUDA 的 block 数。Block 任务会被驱动展开/多轮迭代，不能假设 `taskDim` 与物理核数一一对应。

### 2. 计算数据必须先在 NRAM

所有向量/张量指令的输入、输出都必须在 `__nram__` 地址空间。GDRAM 上的数据不能直接参与 `__bang_add` 等计算，必须先 `__memcpy(..., GDRAM2NRAM)`。

- CUDA 的 `__shared__` 最接近 `__mlu_shared__`，但后者位于 **SRAM、属于整个 Cluster**、生存期为整个 Kernel，不是“每个 block 私有一份”。
- CUDA 的 `__constant__` 最接近 `__mlu_const__`；它存放在 GDRAM，通过 L2 Cache 加速，不是片上小常量区。
- 普通局部数组在栈上，**不能用 IO/MOVE/COMPUTE 流指令读写**；要参与向量计算，显式声明成 `__nram__`。

### 3. 搬运和同步是显式的，四条流水线并行

MLU Core 有 IO / Move / Compute / Scalar 四条可并行的指令流。硬件只保证不同流之间的**寄存器依赖**，NRAM/SRAM/GDRAM 上的数据依赖需要软件同步：

- 简单代码用同步版 `__memcpy`，它是最稳妥的默认选择。
- 用 `__memcpy_async` 做软流水时，必须在“拷贝完成”和“消费数据”之间插入 `__sync()`（或 `__sync_io_move_compute()` 等等价同步）；mlu-ops 的三段流水正是这样写的。
- 核内同步用 `__sync()` / `__sync_compute()` / `__sync_io()` / `__sync_move()`；核间用 `__sync_cluster()`、`__sync_all_ipu()`、`__sync_all()`。**能用小范围就不用大范围**，`__sync_all()` 代价最高。
- Kernel 启动本身是异步的：主机侧 `<<<>>>` 返回后 kernel 可能还没跑完；取结果前要 `cnrtQueueSync(queue)` 或使用 notifier 等待。

### 4. 设备代码在编译时绑定架构

设备端目标文件面向特定架构，`--bang-mlu-arch=` 缺失或写错会导致“编译通过但运行找不到 kernel / invalid device function”。多架构分发用 `--bang-arch=` 生成 CNFatbin。`cncc` 默认优化级别是 **-O0**，性能代码必须显式加 `-O3`。

## 先选路线：不要所有项目都写 BANG C

```
项目里有没有自定义 CUDA kernel（__global__ / .cu / cpp_extension）？
├─ 没有，纯 Python/PyTorch
│   └─ 优先 torch_mlu + CNNL/mlu-ops；逐算子核对覆盖，再做数值回归
├─ 只有 cuBLAS / cuDNN / NCCL 调用
│   └─ 换成 CNNL / CNCL，通常不需要自己写 kernel
└─ 有自定义 kernel
    ├─ 能对应到 mlu-ops 已有算子 → 直接调用或参考其实现
    └─ 不能 → 写 BANG C kernel（先单核正确，再多核，再流水）
```

路线选择的详细矩阵、构建方式和验收标准见 [`references/migration-workflow.md`](references/migration-workflow.md)。

## 最小可运行样例（先建立手感）

设备侧 `vec_add.mlu`：

```cpp
#include <bang.h>

#define LEN 4096                       // 每个 Task 处理的元素数
                                       // LEN * sizeof(float) 必须是 128B 的倍数

__mlu_entry__ void vec_add(float *out, const float *a, const float *b) {
  __nram__ float na[LEN];
  __nram__ float nb[LEN];
  __nram__ float no[LEN];

  __memcpy(na, a + taskId * LEN, LEN * sizeof(float), GDRAM2NRAM);
  __memcpy(nb, b + taskId * LEN, LEN * sizeof(float), GDRAM2NRAM);
  __bang_add(no, na, nb, LEN);
  __memcpy(out + taskId * LEN, no, LEN * sizeof(float), NRAM2GDRAM);
}
```

主机侧启动（可以放在同一个 `.mlu` 的 `main` 里，也可以封装成 `extern "C"` 启动函数供 C++ 调用）：

```cpp
cnrtQueue_t queue;
CNRT_CHECK(cnrtQueueCreate(&queue));

cnrtDim3_t dim = {blocks, 1, 1};              // blocks 个 Task
cnrtFunctionType_t ktype = cnrtFuncTypeBlock; // 或 Union1/2/4...

vec_add<<<dim, ktype, queue>>>(out, a, b);
CNRT_CHECK(cnrtQueueSync(queue));             // kernel 异步，取结果前必须同步
CNRT_CHECK(cnrtQueueDestroy(queue));
```

编译：

```bash
cncc vec_add.mlu -o vec_add \
  -I"$NEUWARE_HOME/include" \
  -L"$NEUWARE_HOME/lib64" -lcndrv -lcnrt \
  --bang-mlu-arch=mtp_372 -O3 -std=c++11
```

这只是“固定大小、无尾块”的演示。真实项目要把长度、尾块、多核切分、双缓冲做对；直接套用会越界或算错。完整模板见 [`references/bang-c-kernel-guide.md`](references/bang-c-kernel-guide.md)。

## 迁移时最容易踩的坑（速查）

| 现象 | 先查什么 | 处理 |
|---|---|---|
| 编译报 `__global__`/`threadIdx` 未定义 | 还在用 CUDA 语法 | 换 `__mlu_entry__`、`taskId`/`taskDim` |
| 编译通过，运行说找不到 kernel / invalid device function | `--bang-mlu-arch` 与板卡不匹配 | 用 `cnmon` 确认真实架构；多架构用 `--bang-arch` |
| 结果部分正确、部分为零/旧值 | 缺同步，或 task 偏移算错 | 核对 `taskId` 切分；异步拷贝后加 `__sync()`；取结果前 `cnrtQueueSync` |
| `__bang_add` 结果乱码/精度异常 | 输入不在 NRAM、地址未 64B 对齐、元素数不是 128B 整数倍 | 全部放 `__nram__`；tile 按 32 个 float 对齐；尾块单独处理 |
| 运行时崩溃在越界 | 最后一个 Task 的 `end` 超长 | 用 `min` 截断；不要假设 `n % taskDim == 0` |
| Union 任务启动失败 | `dim.x` 不满足对齐约束 | Union1 要求 `dim.x % (1 * coreDim) == 0`（372 上 coreDim=4）；UnionN 同理 |
| 性能远低于预期 | 没加 `-O3`；每个 Task 数据太少；GDRAM 非对齐/跳 stride | 先 `-O3`，再按 512B/128B 对齐，增大 tile，做软流水 |
| CNNL 调用返回 bad param | 描述符 shape/layout/dtype 与版本不匹配 | 对照对应版本 CNNL 文档；注意 `_v2` 接口差异 |
| 主机侧拷贝参数顺序写错 | `cnrtMemcpyAsync` 参数顺序与 `cnrtMemcpy` 不同 | `cnrtMemcpy(dst, src, size, dir)`；`cnrtMemcpyAsync(dst, src, size, queue, dir)` |

更多症状和根因见 [`references/runtime-cnrt.md`](references/runtime-cnrt.md) 与 [`references/memory-and-alignment.md`](references/memory-and-alignment.md)。

## Reference 路由表

| 你现在要做什么 | 读这个 |
|---|---|
| 判断项目该怎么迁、分几步、构建系统怎么改、如何验收 | [`references/migration-workflow.md`](references/migration-workflow.md) |
| 查 CUDA 概念/API 在 MLU 上的对应物 | [`references/cuda-to-mlu-mapping.md`](references/cuda-to-mlu-mapping.md) |
| 写/改 BANG C kernel，做分块、尾块、多核、同步、归约 | [`references/bang-c-kernel-guide.md`](references/bang-c-kernel-guide.md) |
| 移植主机侧代码：设备、内存、Queue、Notifier、异步、错误处理 | [`references/runtime-cnrt.md`](references/runtime-cnrt.md) |
| 解决对齐、越界、tile 大小、stride、workspace、片上容量问题 | [`references/memory-and-alignment.md`](references/memory-and-alignment.md) |
| 用 CNPerf 找瓶颈，做多核/流水/向量化/融合优化 | [`references/performance-tuning.md`](references/performance-tuning.md) |
| 想复用 mlu-ops 的工程结构、模板、测试和构建方式 | [`references/mlu-ops.md`](references/mlu-ops.md) |
| 核对官方链接、版本、哪些 API 是已核实的 | [`references/sources.md`](references/sources.md) |

## 迁移工作方式（建议直接照做）

1. **冻结基线。** 在 GPU 上记录一组可重复的输入/输出（含边界 shape）和耗时，作为 MLU 版本的黄金数据。没有基线就无法判断“能跑”还是“跑对”。
2. **盘点。** 运行 `python <skill-dir>/scripts/scan_cuda_project.py <项目根目录> --md migration-inventory.md`，得到 kernel、CUDA API、构建依赖、Python CUDA 调用的清单。
3. **分层。** 把工作分成：库替换（CNNL/CNCL）、主机运行时（CNRT）、kernel 重写、构建系统。先做不会改变数值的层，缩小问题面。
4. **先单 Task 正确，再多 Task 正确，最后才优化。** 单 Task 版本便于打印和比对；多 Task 版本重点查切分、尾块和同步。
5. **正确性门槛：** 多 shape（含 0/1/质数/非对齐长度）、多 dtype、多设备/多核、与黄金数据比对（明确 atol/rtol）、重复运行一致。
6. **性能门槛：** 用 CNPerf 建立基线，按“IO 瓶颈 / 计算瓶颈”分别优化；每次只改一个变量并回归正确性。
7. **交付：** 迁移清单、每个 kernel 的映射说明、构建命令、已知限制、性能对比、未覆盖算子列表。

## 事实纪律（很重要）

- **不要发明 API。** 不确定的函数名、枚举名、参数顺序，先查 `$NEUWARE_HOME/include` 或对应版本文档；本 skill 未列出的接口，明确标注“需核对”。
- **不要假设架构。** 默认值、容量、coreDim、支持的数据类型都可能随 `mtp_*` 变化。
- **不要假设语义等价。** 尤其是 `__syncthreads`、原子、浮点归约顺序、`__constant__`、统一内存、CUDA Graph。
- **不要静默截断。** 覆盖不了的 shape/dtype/算子要显式报错或走回退路径，不能算出一个“看起来对”的结果。

## 完成标准

一次迁移至少应留下：

- [ ] 环境探测记录（架构、版本、设备数、片上容量）
- [ ] CUDA 资产清单和路线决策
- [ ] 可复现的构建命令/CMake 配置
- [ ] 每个 kernel 的 CUDA→BANG C 对照说明（切分、内存、同步、尾块）
- [ ] 正确性测试与黄金数据比对结果
- [ ] CNPerf 性能对比与瓶颈说明
- [ ] 已知限制、未迁移项、回退策略
