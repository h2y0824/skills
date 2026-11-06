# 迁移工作流：从 CUDA 工程到 MLU 工程

> 目标不是“让代码在 MLU 上编译通过”，而是“在 MLU 上得到可复现的正确结果，并且性能可解释”。
> 本文给出一套可以直接执行的分阶段流程、每阶段的准入/退出条件，以及构建系统改法。

## 目录

1. [总览与阶段门](#1-总览与阶段门)
2. [阶段 0：冻结 GPU 基线](#2-阶段-0冻结-gpu-基线)
3. [阶段 1：项目盘点](#3-阶段-1项目盘点)
4. [阶段 2：路线决策](#4-阶段-2路线决策)
5. [阶段 3：构建系统迁移](#5-阶段-3构建系统迁移)
6. [阶段 4：分层移植](#6-阶段-4分层移植)
7. [阶段 5：正确性验收](#7-阶段-5正确性验收)
8. [阶段 6：性能验收与调优](#8-阶段-6性能验收与调优)
9. [阶段 7：回归与交付](#9-阶段-7回归与交付)
10. [风险登记表](#10-风险登记表)
11. [迁移报告模板](#11-迁移报告模板)

---

## 1. 总览与阶段门

```
0 冻结基线 ──► 1 盘点 ──► 2 选路线 ──► 3 构建 ──► 4 分层移植 ──► 5 正确性 ──► 6 性能 ──► 7 回归交付
   (黄金数据)   (清单)     (决策记录)   (可链接)     (单Task→多Task)   (门槛)      (CNPerf)   (报告)
```

**阶段门规则**：上一阶段退出条件不满足，不进入下一阶段。

| 阶段 | 退出条件（硬性） |
|---|---|
| 0 基线 | GPU 上同一份输入可重复产出同一份输出；耗时可测；边界 shape 已列全 |
| 1 盘点 | 每个 `.cu`、每个 kernel、每个 `cuda*`/`cublas*`/`cudnn*`/`nccl*` 调用都有归属（迁/换/弃） |
| 2 路线 | 每个模块有且只有一条主路线；未覆盖算子有回退方案 |
| 3 构建 | 空 kernel 工程能在 MLU 上编译、链接、运行，且 `cnmon` 能看到负载 |
| 4 移植 | 单 Task 版本全部算对；多 Task 版本全部算对 |
| 5 正确性 | 全部 shape/dtype/边界用例通过；重复运行结果一致；无越界/无未初始化读 |
| 6 性能 | 有基线、有瓶颈结论、有关键优化项；性能不达标项有记录和原因 |
| 7 交付 | 报告、构建命令、已知限制、回退策略齐全 |

---

## 2. 阶段 0：冻结 GPU 基线

在任何 MLU 代码写出来之前，先把“什么叫做对”固定下来。

### 2.1 需要保存的东西

| 类别 | 内容 | 格式 |
|---|---|---|
| 输入 | 覆盖正常/边界/随机/真实数据的固定 seed 输入 | `.npy` / `.bin` / 固定 seed 生成脚本 |
| 输出 | GPU 上对应输入的输出张量 | 同上 |
| 指标 | 每个算子/全流程耗时、吞吐、内存峰值 | CSV / Markdown 表 |
| 环境 | GPU 型号、驱动、CUDA、cuDNN、框架版本 | 文本 |
| 容差 | 每类算子的 `atol` / `rtol` / 允许的最大相对误差 | 配置 |

### 2.2 边界 shape 清单（至少包含）

- `0`（空张量）
- `1`（单元素）
- 质数长度（如 1009、4093），用于暴露尾块错误
- 刚好是 tile 整数倍的长度
- 刚好是 tile 整数倍 + 1
- 非 128B 对齐的元素数（例如 `float` 的 31 个元素）
- 大 shape（跨多个 Task，且 `n % taskDim != 0`）
- 每个维度的 `1`（卷积/矩阵乘/归约的退化维度）
- 非连续 stride / 转置输入

### 2.3 容差怎么定

- 逐元素算子：`atol=0, rtol=0` 通常可以做到；做不到时按 dtype 定（fp32 常用 `1e-5` 量级，bf16/fp16 更宽）。
- 归约/矩阵乘：累加顺序不同必然产生差异，用相对误差 + 绝对误差双阈值。
- 分类/检测类后处理：先比“前 N 个结果的集合是否一致”，再比数值；排序并列情况要允许不同顺序。
- NaN/Inf：显式定义传播规则，不要用 `fabs(nan - nan) > eps` 这种永远为假的判断。

---

## 3. 阶段 1：项目盘点

### 3.1 自动扫描

```bash
python .claude/skills/gpu2mlu/scripts/scan_cuda_project.py <项目根目录> \
  --md migration-inventory.md \
  --json migration-inventory.json
```

脚本会统计：

- CUDA 源文件（`.cu` / `.cuh`）与含 CUDA 语法的 `.cpp/.h`
- kernel 定义（`__global__`）与设备函数（`__device__`）
- CUDA 运行时 API、cuBLAS/cuDNN/NCCL/cuSPARSE/NPP 调用
- Python 侧 CUDA 调用（`torch.cuda`、`cupy`、`cuda-python`、`pycuda`）
- 构建系统（CMake 的 `enable_language(CUDA)`/`find_package(CUDAToolkit)`、Makefile 的 `nvcc`、`setup.py` 的 `CUDAExtension`）

自动扫描只能给“候选”，必须人工确认。

### 3.2 人工盘点表

| 模块 | CUDA 资产 | 类型 | 调用频次 | 数值敏感度 | 目标 MLU 实现 | 风险 |
|---|---|---|---|---|---|---|
| preprocess | `resize_kernel` | 自定义 kernel | 每帧 | 低 | BANG C / CNNL | 中 |
| backbone | cuDNN conv/bn/relu | 库 | 每帧 | 中 | CNNL | 低 |
| head | `cublasSgemm` | 库 | 每帧 | 中 | `cnnlMatMul` | 低 |
| post | `nms_kernel` | 自定义 kernel | 每帧 | 高 | BANG C / `cnnlNms` | 高 |
| 训练 | NCCL AllReduce | 通信 | 每 step | 中 | CNCL | 高 |

### 3.3 盘点时必须回答的问题

1. 这段 CUDA 代码有没有用到 warp 级原语（shfl、vote、`__syncwarp`）？→ 需要重写成向量/查表。
2. 有没有依赖 `__constant__` 的小常量？→ 改成编译期常量、NRAM 或 `__mlu_const__`。
3. 有没有 `cudaMallocManaged`、CUDA Graph、dynamic parallelism、cooperative launch？→ 这些是高风险项，单独列。
4. kernel 里有没有 `printf` 调试？→ MLU 用 `__bang_printf`，但有性能影响。
5. 有没有依赖“线程块内任意同步”的算法（如 block-level scan）？→ 需要改算法。
6. 有没有为了 GPU 优化的奇怪切分（如 `blockDim.x=1024` 的棋盘格）？→ 不要照搬，按 MLU tile 重新设计。
7. Python 侧是否直接调用 CUDA 扩展？→ 需要 `.mlu` + pybind 或 torch_mlu 自定义算子。

---

## 4. 阶段 2：路线决策

### 4.1 决策矩阵

| 项目形态 | 首选路线 | 备选 | 不推荐 |
|---|---|---|---|
| 纯 PyTorch 训练/推理 | `torch_mlu` + CNNL | 导出 ONNX → MagicMind | 逐算子写 BANG C |
| PyTorch + 少量自定义 CUDA 扩展 | `torch_mlu` + 把扩展改写成 `.mlu`（pybind 封装） | 用 mlu-ops 现成算子替换 | 保留 CUDA 扩展 |
| C++ 推理引擎 + cuDNN/cuBLAS | CNRT + CNNL | mlu-ops | 自己重写卷积 |
| C++ 大量自定义 kernel | BANG C + mlu-ops 工程结构 | 逐个替换为 CNNL | 整个工程重写 |
| 训练框架（多卡） | CNCL + CNNL + CNRT | 只做单卡验证 | 先做多卡 |
| 边缘设备部署 | MagicMind / CNRT | 小模型直接 BANG C | 假设云端架构 |

### 4.2 路线记录（每个模块一条）

```
模块：postprocess/nms
CUDA 现状：自定义 nms_kernel，依赖每 block 1024 线程做候选排序
MLU 路线：先用 cnnlNms 验证语义；若语义不完全一致，写 BANG C 版本
理由：NMS 是精度敏感算子，优先用官方库降低风险
回退：若 cnnlNms 不支持该 IoU/坐标格式，回退到 CPU 实现（性能不达标但正确）
验收：与 GPU 基线做集合比对 + IoU 阈值比对
```

### 4.3 什么时候必须自己写 kernel

- 自定义数据布局或算子（如特殊的注意力 mask、稀疏模式）
- 融合能显著减少 IO（多个逐元素算子融合成一个）
- CNNL 不支持该 dtype/shape
- 对性能有硬要求且现成实现不达标（需要 profile 证明）

### 4.4 torch_mlu 路线的核对清单

如果项目是 PyTorch，优先考虑框架路线，但不要假设“改个设备名就能跑”：

1. **版本匹配**：确认 torch 与 torch_mlu 的配套版本、驱动、CNToolkit 满足官方要求。
2. **设备迁移**：`.cuda()` / `device="cuda"` → `.to("mlu")` / `device="mlu"`；`torch.cuda.*` → `torch.mlu.*`（`synchronize`、`device_count`、`is_available` 等）。
3. **算子覆盖**：完整跑一遍模型，记录不支持/回退的算子；不要假设所有 CUDA 算子都有对应实现。
4. **自定义算子**：优先找框架/CNNL 已有的融合算子；确实需要自己写时，按 torch_mlu 官方扩展机制接入 BANG C kernel。
5. **精度**：bf16/fp16 行为、dropout、随机数、归一化的 eps、loss 的 reduction 都要逐项比对。
6. **性能**：先跑通再优化；用框架自带 profiler 或 CNPerf 定位。

> 上述是通用迁移动作；具体 API 名称、支持范围和扩展机制随 torch_mlu 版本变化，**以目标版本的官方文档为准**。本 skill 未逐条核实 torch_mlu 接口。

---

## 5. 阶段 3：构建系统迁移

### 5.1 核心原则

- **`.mlu` 文件必须由 `cncc` 编译。** 包含 `<<<>>>` 启动语句的主机文件也必须由 `cncc` 编译（或由 cncc 链接设备目标文件）。
- **设备目标文件绑定架构。** 要么每台目标机单独编译，要么用 `--bang-arch=` 打成 CNFatbin。
- **默认 `-O0`。** Release 配置必须显式 `-O3`。
- **不要混用 CUDA 语言。** CMake 中移除 `enable_language(CUDA)` 和 `find_package(CUDAToolkit)`，否则配置阶段就会找 nvcc。

### 5.2 最小 CMake 改法

原工程（示意）：

```cmake
enable_language(CUDA)
find_package(CUDAToolkit REQUIRED)
add_library(foo foo.cpp foo_kernel.cu)
target_link_libraries(foo CUDA::cudart CUDA::cublas)
```

**方式 A：整个工程的 C++ 编译器换成 cncc（mlu-ops 风格）**

```cmake
set(NEUWARE_HOME "$ENV{NEUWARE_HOME}" CACHE PATH "Cambricon Neuware root")
set(MLU_ARCH "mtp_372" CACHE STRING "target architecture, confirm with cnmon")

set(CMAKE_CXX_COMPILER "${NEUWARE_HOME}/bin/cncc")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} --bang-mlu-arch=${MLU_ARCH} -O3")

# 让 CMake 把 .mlu 当 C++ 源文件处理
set_source_files_properties(kernels/foo_kernel.mlu PROPERTIES LANGUAGE CXX)

add_library(foo foo.cpp kernels/foo_kernel.mlu)
target_include_directories(foo PRIVATE ${NEUWARE_HOME}/include)
target_link_directories(foo PRIVATE ${NEUWARE_HOME}/lib64)
target_link_libraries(foo PRIVATE cnrt cndrv)
```

要求 CMake 能把 cncc 识别为 C++ 编译器。如果配置阶段报 “unknown compiler” 或编译器探测失败，用方式 B。

**方式 B：主机代码保持 g++，设备侧与启动封装隔离在一个 `.mlu` 里**

1. `kernels/foo_kernel.mlu` 同时包含设备 kernel 和 `extern "C"` 启动函数（见 5.4）。
2. 主机 `.cpp` 只包含 `include/kernels.h`，不含任何 `<<<>>>` / `__mlu_*`。
3. 设备侧用 cncc 编译，主机侧用 g++ 编译，最终用 cncc 链接：

```bash
cncc -c kernels/foo_kernel.mlu -o build/foo_kernel.o \
  -I"$NEUWARE_HOME/include" --bang-mlu-arch=$MLU_ARCH -O3 -std=c++11

g++ -c src/foo.cpp -o build/foo.o \
  -I"$NEUWARE_HOME/include" -Iinclude

cncc build/foo.o build/foo_kernel.o -o build/app \
  -L"$NEUWARE_HOME/lib64" -lcnrt -lcndrv
```

在 CMake 中把第 1 步写成 `add_custom_command`，并让最终 target 用 cncc 链接；或者直接把整个工程切到方式 A。

> 关键点：**不要**把 `.mlu` 当成普通 C++ 源文件交给 g++，也不要用 g++ 链接设备目标文件。
> 无论选哪种方式，都要在目标机上实测：能配置、能链接、能启动 kernel。

### 5.3 推荐的目录结构

```
project/
├── CMakeLists.txt
├── kernels/                 # 设备侧，全部 .mlu
│   ├── vec_add.mlu
│   └── nms.mlu
├── src/                     # 主机侧，纯 C++，不含 CUDA 语法
│   ├── launcher.cpp         # 调用 kernels 导出的 extern "C" 函数
│   └── ...
├── include/
│   └── kernels.h            # 设备侧启动函数的 C 接口声明
└── tests/
```

### 5.4 启动封装模式

`kernels/vec_add.mlu`：

```cpp
#include <bang.h>
#include "kernels.h"

__mlu_entry__ void vec_add_kernel(float *out, const float *a, const float *b, int n) {
  // ... 设备侧实现
}

extern "C" int launch_vec_add(float *out, const float *a, const float *b, int n,
                              cnrtQueue_t queue) {
  if (n <= 0) return 0;                       // 空张量：不要启动 0 任务
  int tasks = 4;                              // 按目标机 coreDim 计算；此处仅示例
  cnrtDim3_t dim = {(unsigned int)tasks, 1, 1};
  vec_add_kernel<<<dim, cnrtFuncTypeBlock, queue>>>(out, a, b, n);
  return 0;
}
```

`include/kernels.h`（纯 C，主机侧可包含）：

```c
#pragma once
#include <cnrt.h>
#ifdef __cplusplus
extern "C" {
#endif

int launch_vec_add(float *out, const float *a, const float *b, int n, cnrtQueue_t queue);

#ifdef __cplusplus
}
#endif
```

主机侧只需 `#include "kernels.h"` 并链接 `foo_kernels`，不需要 cncc 编译 `launcher.cpp`。

### 5.5 构建冒烟测试

在写任何业务代码前，先做一个“空 kernel + 一次拷贝 + 一次同步”的工程，确认：

```bash
cmake -B build -DMLU_ARCH=$(cnmon info | awk ...)   # 或手工填写
cmake --build build -j
./build/smoke_test
cnmon info        # 运行期间观察利用率
```

冒烟测试不通过，先解决工具链，不要继续移植。

---

## 6. 阶段 4：分层移植

顺序很重要：先做不改变数值的层，再动 kernel。

### 第 1 层：构建与运行时骨架

- 引入 `cnrt.h` / `cnnl.h`，建立 Queue、内存分配、错误检查。
- 把 `cudaMalloc/Free/Memcpy` 机械替换为 `cnrtMalloc/Free/Memcpy`。
- 保持所有 kernel 仍是空壳，先跑通“分配—拷贝—同步—回拷—比对”。

### 第 2 层：库替换

- cuBLAS → `cnnlMatMul` / `cnnlBatchMatMul` / `cnnlAxpy` / `cnnlScale`
- cuDNN → CNNL 卷积/池化/激活/归一化
- NCCL → CNCL（先单卡，再多卡）
- 每个库替换都要单独做数值比对，不要和 kernel 重写混在一起。

### 第 3 层：逐 kernel 重写

每个 kernel 按固定步骤：

1. **确定数学语义**：输入输出 shape、stride、dtype、边界、NaN 处理。
2. **确定 tile**：一个 Task 处理多少元素；tile 字节数必须是 128B 的整数倍；NRAM 要放得下输入+输出+临时。
3. **单 Task 版本**：`dim = {1,1,1}`，用 `taskId` 恒为 0 的假设写，先保证算法对。
4. **多 Task 版本**：按 `taskDim` 切分，处理 `n % taskDim != 0` 的尾块。
5. **同步检查**：每次 `__memcpy_async` 后是否有对应 `__sync`；跨核交换是否有 `__sync_cluster`。
6. **对齐检查**：GDRAM 偏移、NRAM 偏移、元素数。
7. **正确性回归**：单 Task 与多 Task 结果必须一致（浮点归约除外，按容差）。

### 第 4 层：融合与优化

详见 [`performance-tuning.md`](performance-tuning.md)。原则：**先正确，再做减少 IO 的融合，最后做流水**。

---

## 7. 阶段 5：正确性验收

### 7.1 测试矩阵

| 维度 | 取值 |
|---|---|
| shape | 0、1、质数、tile 整数倍、tile+1、非对齐、大 shape |
| dtype | 实际用到的所有类型（fp32/fp16/bf16/int8/int16/int32） |
| 布局 | 连续、转置、带 stride、非连续 |
| 值域 | 正常、全零、极大/极小、NaN/Inf（若语义允许）、随机 |
| 任务规模 | 单 Task、`taskDim == coreDim`、`taskDim > coreDim`、`taskDim` 不整除 `n` |
| 运行次数 | 至少 10 次重复，结果逐位一致（归约按容差） |
| 设备 | 单卡、多卡（若有） |
| 并发 | 多 Queue 并发调用同一 kernel |

### 7.2 常见“看起来对其实错”的情况

- 尾块没处理，最后一小段保留旧值/零值 → 用质数长度必现。
- `taskDim` 大于实际任务数，部分 Task 的 `start >= n` → 需要提前 return。
- 多 Task 写同一地址（切分重叠）→ 用输出全零初始化 + 非零输入暴露。
- 未初始化 NRAM 被读 → 用“每次运行前把 NRAM 写垃圾”难以做到，改为检查算法是否依赖初值。
- 异步拷贝未同步 → 小数据偶发正确、大数据稳定错误；用重复运行和压力测试暴露。
- 浮点归约顺序不同 → 与 GPU 基线有微小差异，需确认在容差内。
- 越界读不崩溃但结果错 → 检查所有 `taskId * tile + i` 的边界。

### 7.3 验收产物

- `pytest` / gtest 用例和运行日志
- 与 GPU 基线的逐用例对比表（最大绝对误差、最大相对误差、通过/失败）
- 已知差异说明（哪些是允许的浮点差异，哪些是限制）

---

## 8. 阶段 6：性能验收与调优

### 8.1 先建立基线

- 端到端耗时（CPU 计时 + `cnrtNotifier` 计时）
- 每个 kernel 的耗时（CNPerf `timechart` / `kernel_profiling`）
- 与 GPU 同 shape 的耗时对比（不一定要求更快，但要知道差多少、为什么）
- 硬件利用率、带宽、计算单元占用

### 8.2 判断瓶颈

| 现象 | 可能瓶颈 | 先查 |
|---|---|---|
| IO 时间长、Compute 时间短 | 搬运/带宽 | tile 是否太小、是否非对齐、是否跳到 stride |
| Compute 时间长、IO 时间短 | 计算/指令效率 | 是否用了向量指令、元素数是否 128B 对齐、是否有标量循环 |
| 多核利用率低 | 任务切分不均或 Task 太少 | `taskDim`、每 Task 工作量、尾块 |
| 单核利用率低 | 指令流串行 | 是否用了 `__memcpy` 同步版、是否可改软流水 |
| 反复启动开销大 | 小 kernel 太多 | 融合、批量、TaskTopo |

### 8.3 优化顺序（收益从大到小）

1. 增加每 Task 工作量，减少启动和调度开销。
2. 对齐 + 连续访问（GDRAM 512B、NRAM 128B）。
3. 用向量指令替标量循环。
4. 融合相邻逐元素算子，减少 GDRAM 往返。
5. 软流水/双缓冲，让 IO 与 Compute 重叠。
6. 多核/Union 并行。
7. 减少同步范围。

每次只改一个变量，改完回归正确性。

---

## 9. 阶段 7：回归与交付

### 9.1 回归清单

- [ ] 全部单元测试通过
- [ ] 端到端精度与 GPU 基线在容差内
- [ ] 重复运行稳定（无偶发错误）
- [ ] 多卡/多 Queue 场景通过
- [ ] 内存无泄漏（`cnrtMalloc`/`cnrtFree` 成对）
- [ ] 构建在干净环境中可复现
- [ ] 性能数据已记录
- [ ] 已知限制已文档化
- [ ] 回退路径可用（CPU/GPU 版本或开关）

### 9.2 交付物

- 迁移后的源码与构建脚本
- `migration-inventory.md`（资产清单）
- `migration-report.md`（见模板）
- 测试用例与基线数据
- 构建/运行说明（含目标架构、CNToolkit/CNNL 版本）

---

## 10. 风险登记表

| 风险 | 触发信号 | 缓解 |
|---|---|---|
| 目标架构不确定 | 不知道 `mtp_*` / `tp_*` | 先跑 `cnmon info` + `cncc --version`；编写架构无关代码 |
| CNNL 语义与 cuDNN 不完全一致 | 卷积/池化边界、padding 模式差异 | 逐算子数值比对；必要时自己写 kernel |
| 片上容量不足 | tile 放不进 NRAM，编译报栈溢出 | 减小 tile、分块循环、用 LDRAM/SRAM |
| 精度不达标 | bf16/fp16 累加误差大 | 用 fp32 累加、调整归约顺序、放宽容差并与用户确认 |
| 多卡通信不可用 | CNCL 初始化失败 | 先单卡交付，通信层单独评估 |
| 构建环境污染 | 同时装了 CUDA 和 CNToolkit，头文件冲突 | 显式 include 路径，避免全局 `-I/usr/local/cuda` |
| 性能远低于 GPU | 逐线程移植、tile 太小、未开 -O3 | 重写为 tile + 向量指令；CNPerf 定位 |
| 工具链版本不匹配 | 编译通过但运行报错 | 记录版本矩阵；用官方配套版本 |

---

## 11. 迁移报告模板

```markdown
# <项目名> CUDA → MLU 迁移报告

## 1. 环境
- 目标硬件：<板卡/芯片型号，来自 cnmon>
- 架构：<mtp_xxx / tp_xxx>
- CNToolkit / CNNL / 驱动：<版本>
- 操作系统 / 编译器：<版本>
- 是否有 torch_mlu：<是/否，版本>

## 2. 迁移范围
- 已迁移模块：...
- 未迁移模块及原因：...
- 路线：<torch_mlu / CNNL / BANG C / 混合>

## 3. 关键改动
| CUDA 资产 | MLU 实现 | 说明 |
|---|---|---|

## 4. 正确性
- 测试用例数 / 通过数
- 与 GPU 基线的最大误差
- 已知差异

## 5. 性能
| 阶段 | GPU | MLU | 说明 |
|---|---|---|---|
| 端到端 | | | |
| 热点 kernel | | | |

- 瓶颈结论：
- 已做优化：
- 未做优化及原因：

## 6. 已知限制与回退
- ...

## 7. 复现方式
- 构建命令：
- 运行命令：
- 测试命令：
```
