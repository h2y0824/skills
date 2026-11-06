# mlu-ops 工程指南

> 仓库：https://github.com/Cambricon/mlu-ops
> 本文依据 README、`docs/BANG-C-OPS-Develop-Guide.md`、`kernels/abs/*`、`kernels/kernel.h`、
> `kernels/unary_op/unary_op_3pipeline.h`（master 分支，2026-11 抓取）。
> 版本较新时目录/接口可能变化，先以仓库实际内容为准。

## 目录

1. [mlu-ops 是什么](#1-mlu-ops-是什么)
2. [目录结构](#2-目录结构)
3. [依赖与构建](#3-依赖与构建)
4. [一个算子的解剖](#4-一个算子的解剖)
5. [三段流水模板](#5-三段流水模板)
6. [host 侧写法](#6-host-侧写法)
7. [测试与性能工具](#7-测试与性能工具)
8. [新增一个算子的流程](#8-新增一个算子的流程)
9. [复用建议](#9-复用建议)
10. [常见问题](#10-常见问题)

---

## 1. mlu-ops 是什么

Cambricon 官方维护的 **MLU 算子示例库**（MIT 许可）：

- 用 BANG C 写的高质量算子实现（逐元素、归约、卷积、矩阵乘、NMS 等）。
- 配套：精度验收标准、性能验收标准、测试框架（GTest）、运行时测例生成（Gen-case）、性能分析工具。
- 目标是**参考实现**：可以直接拿来用，也可以作为自己写 kernel 的范本。

它不是一个“所有算子都覆盖”的生产库；Op List 之外的算子需要自己写或走 CNNL。

---

## 2. 目录结构

```
mlu-ops/
├── cmake/          # 编译相关 make 文件
├── core/           # 公共数据类型、运行时管理、日志
├── docker/         # CI 构建环境
├── docs/           # 算子开发指南、精度/性能标准、测试文档
├── kernels/        # 算子实现（一元/二元模板 + 各算子）
├── test/           # GTest 测试
├── mlu_op.h        # 公共类型 + 对外 C 接口
├── build.sh        # 构建入口
└── env.sh          # 环境变量
```

`kernels/` 内部通常按算子分目录，每个算子包含：

```
kernels/abs/
├── abs.cpp          # host 侧：接口、参数检查、选择 kernel、启动
├── abs.h            # 内部声明
├── abs_block.mlu    # Block 任务版 kernel
└── abs_union1.mlu   # Union1 版（可选）
```

公共模板在 `kernels/` 根下：`kernel.h`、`unary_op/unary_op_3pipeline.h`、`binary_op/...`。

---

## 3. 依赖与构建

### 3.1 依赖

来自 README：

| 类别 | 要求 |
|---|---|
| OS | x86_64：Ubuntu 22.04、CentOS 7.6/8.5、Kylin 10、Debian 10/12 |
| CNToolkit | ≥ v4.1.0 |
| CNNL | ≥ v1.28.0 |
| 驱动 | ≥ v6.0.3 |
| Python | ≥ 3.6（默认 3.8） |
| 外部库 | libxml2-dev、libprotobuf-dev、protobuf-compiler、llvm-6.0-dev、libfmt-dev ≥ 11.0.2、libeigen3-dev ≥ 3.4 |

### 3.2 构建

```bash
git clone https://github.com/Cambricon/mlu-ops.git
cd mlu-ops
git submodule update --init --recursive

source env.sh
./build.sh                      # 全量
./build.sh --filter="abs"       # 只编译匹配的算子/测试
```

产物：

| 产物 | 位置 |
|---|---|
| 动态库 | `build/lib/libmluops.so` |
| 测试 | `build/test/mluop_gtest` |

### 3.3 运行测试

```bash
./build/test/mluop_gtest                    # 全部
./build/test/mluop_gtest --gtest_filter='*abs*'
```

测试框架支持内存泄漏检测和代码覆盖率，见 `docs/GTest-User-Guide-zh.md`。

---

## 4. 一个算子的解剖

以 `abs` 为例。

### 4.1 `mlu_op.h`（对外接口）

定义公共 handle/类型和算子的 C 接口，例如：

```c
mluOpStatus_t MLUOP_WIN_API mluOpAbs(mluOpHandle_t handle,
                                     const mluOpTensorDescriptor_t x_desc,
                                     const void *x,
                                     const mluOpTensorDescriptor_t y_desc,
                                     void *y);
```

要点：

- 对外是 C 接口 + 描述符（shape/dtype/layout），不暴露 kernel 细节。
- `MLUOP_WIN_API` 控制符号可见性。

### 4.2 `abs.cpp`（host 侧）

职责：

1. 参数检查（nullptr、dtype、shape、stride、arch）。
2. 计算 task 规模与 kernel 类型。
3. 选择 Block / Union1 实现。
4. 启动 kernel。
5. 记录日志/错误。

典型结构：

```cpp
mluOpStatus_t MLUOP_WIN_API mluOpAbs(...) {
  // 1. 检查
  PARAM_CHECK("[mluOpAbs]", handle != nullptr);
  PARAM_CHECK("[mluOpAbs]", x != nullptr);
  // dtype 检查：只支持实际实现的类型

  // 2. 分派
  if (/* 满足 union1 条件 */) {
    return absUnion1(handle, x_desc, x, y_desc, y);
  }
  return absBlock(handle, x_desc, x, y_desc, y);
}
```

host 侧做完整检查很重要：kernel 内部越界/类型不符通常不会给你清晰的错误。

### 4.3 `abs_block.mlu`（设备侧）

结构（简化自真实源码）：

```cpp
#include "kernel.h"

__nram__ int8_t nram_buffer[UNARY_NRAM_SIZE];

__mlu_func__ void computeAbs(void *dst, void *src, int count, ...) {
  // 按 dtype 分派到 __bang_abs 等
}

__mlu_global__ void absBlockKernel(const void *x, void *y, int element_num) {
  if (__is_mpu()) {
    return;                       // Memory Core 不参与计算
  }

  const int num_per_core = element_num / taskDim;
  const int rem = element_num % taskDim;
  const int core_num = num_per_core + (taskId == taskDim - 1 ? rem : 0);
  if (core_num <= 0) {
    return;
  }
  const int core_offset = taskId * num_per_core;

  void *nram_in = nram_buffer;
  void *nram_out = (char *)nram_buffer + /* 偏移 */;

  // 三段流水
  // load → compute → store，每次按 tile 处理
}
```

要点：

- `nram_buffer` 是**整个 kernel 共享的一块 NRAM 字节数组**，内部再切分给输入/输出/临时；这样比声明多个大数组更容易控制总量。
- `__is_mpu()` 判断当前是否 Memory Core；计算 kernel 通常直接返回。
- 余数给最后一个 Task，是 mlu-ops 的常见约定。
- kernel 名可能是 `__mlu_global__`；新代码用 `__mlu_entry__` 也可以，不要纠结名字，行为一致。

### 4.4 `kernel.h` 里的常量（值得抄）

```cpp
#define NFU_ALIGN_SIZE 128          // Byte
#define WRAM_ALIGN_SIZE 64
#define COMPUTE_COUNT_ALIGN 64      // elem_count 需被 64 整除
#define CORE_DIM 4                   // 322 为 1，其余为 4
#define REM_FOR_STACK (128 * 1024)   // 给 cncc 预留的栈

#define MAX_NRAM_SIZE (__MLU_NRAM_SIZE__ * 1024 - REM_FOR_STACK)
#define MAX_SRAM_SIZE (__MLU_SRAM_SIZE__ * 1024 - REM_FOR_STACK)

#define PAD_UP(x, y)   (((x) / (y) + (int)((x) % (y) > 0)) * (y))
#define PAD_DOWN(x, y) (((x) / (y)) * (y))
#define CEIL_ALIGN(x, align)  (((x) + (align) - 1) / (align) * (align))
#define FLOOR_ALIGN(x, align) ((x) / (align) * (align))
```

注意：

- `__MLU_NRAM_SIZE__` 单位是 KB，所以 `* 1024`。
- `COMPUTE_COUNT_ALIGN = 64` 是**元素数**对齐；对 float 正好是 256B，比 128B 更保守。
- `CORE_DIM` 是编译期常量，322 上为 1，其他为 4。

自己的工程可以直接复用这些宏（MIT 许可），但要确认与目标架构一致。

---

## 5. 三段流水模板

`unary_op_3pipeline.h` 是 mlu-ops 一元算子的核心模板，结构：

```
   load(i)  ─────────────┐
                         ├──► compute(i) ──► store(i)
   load(i+1) ────────────┘
```

关键实现点（来自真实源码）：

1. **按 `taskDim` 切分**：`num_per_core = element_num / taskDim`，余数给最后一个 Task。
2. **NRAM 分块**：`UNARY_NRAM_SIZE` 再减去流水缓冲/对齐开销（源码里是 `+ REM_FOR_STACK - 148 * 1024`）。
3. **`__memcpy_async` + 显式同步**：在 async copy / compute / store 之间插入同步；源码使用内联 `asm volatile("sync;")` 精确控制指令流。
4. **tile 对齐**：`ALIGN_NUM 64`（元素数），保证向量指令的 128B/256B 要求。
5. **尾块**：最后一个 Task 处理余数；模板里对不足一个 tile 的情况有单独分支。

伪代码（**不是**可直接编译的源码，用于理解结构）：

```cpp
void unaryPipeline(void *nram, const void *x, void *y, int n) {
  const int per_core = n / taskDim;
  const int offset = taskId * per_core;
  const int count = (taskId == taskDim - 1) ? (n - offset) : per_core;
  if (count <= 0) return;

  void *buf0 = nram;
  void *buf1 = (char *)buf0 + TILE_BYTES;

  // prologue: 搬入第一块
  __memcpy_async(buf0, (const char *)x + offset * elem_size,
                 TILE_BYTES, GDRAM2NRAM);
  sync();

  for (int i = 0; i < count; i += TILE_ELEMS) {
    int cur = min(TILE_ELEMS, count - i);

    // 预取下一块
    if (i + TILE_ELEMS < count)
      __memcpy_async(buf1, (const char *)x + (offset + i + TILE_ELEMS) * elem_size,
                     TILE_BYTES, GDRAM2NRAM);

    // 计算当前块
    compute(buf0, buf0, cur);
    sync_compute();

    // 写回当前块
    __memcpy_async((char *)y + (offset + i) * elem_size,
                   buf0, cur * elem_size, NRAM2GDRAM);

    // 等预取完成，交换
    sync();
    swap(buf0, buf1);
  }
  sync();
}
```

实际使用时：

- 直接 include `unary_op_3pipeline.h` 的模板，实例化自己的 op 类型。
- 需要修改缓冲布局时，先确认 `UNARY_NRAM_SIZE` 计算是否仍成立。
- 不要照抄到 Non-unary 场景，模板对输入/输出数量有假设。

---

## 6. host 侧写法

### 6.1 描述符

```cpp
mluOpTensorDescriptor_t desc;
mluOpCreateTensorDescriptor(&desc);
mluOpSetTensorDescriptor(desc, MLUOP_LAYOUT_ARRAY, MLUOP_DTYPE_FLOAT, dims, 4);
```

### 6.2 启动

```cpp
cnrtQueue_t queue = handle->queue;
cnrtDim3_t dim = {task_dim, 1, 1};
cnrtFunctionType_t ktype = CNRT_FUNC_TYPE_BLOCK;
absBlockKernel<<<dim, ktype, queue>>>(x, y, element_num);
```

### 6.3 参数检查清单

- handle 非空，queue 有效
- 输入/输出指针非空
- dtype 在支持范围内
- shape 维度 ≤ 支持上限
- 连续（或 stride 在支持范围）
- `element_num` 不超过 `INT_MAX`
- 目标架构支持该 kernel（`__BANG_ARCH__` 条件编译）

### 6.4 错误码

`mluOpStatus_t` 常见值：`MLUOP_STATUS_SUCCESS`、`MLUOP_STATUS_BAD_PARAM`、`MLUOP_STATUS_NOT_SUPPORTED`、`MLUOP_STATUS_INTERNAL_ERROR`。具体枚举查 `mlu_op.h`。

---

## 7. 测试与性能工具

### 7.1 GTest

```bash
./build/test/mluop_gtest --gtest_filter='*abs*'
```

测试通常覆盖：

- 不同 dtype/shape
- 与 CPU 参考实现比对
- 边界 shape
- 内存泄漏（框架支持）

精度标准：`docs/MLU-OPS-Accuracy-Acceptance-Standard.md`。
性能标准：`docs/MLU-OPS-Performance-Acceptance-Standard.md`。

### 7.2 Gen-case

运行时生成测例，扩大 shape/dtype 覆盖，见 `docs/Gencase-User-Guide-zh.md`。

### 7.3 Perf-Analyse

`tools/perf_analyse`，用于批量性能分析和结果整理。

### 7.4 和 CNPerf 的分工

- GTest / Perf-Analyse：算子级正确性和吞吐回归。
- CNPerf：单次运行的时间线、PMU、瓶颈定位。

---

## 8. 新增一个算子的流程

1. **查 Op List**：确认没有现成实现。
2. **建目录**：`kernels/<op>/`。
3. **写 host 接口**：在 `mlu_op.h` 加 C 接口；实现 `op.cpp`。
4. **写 kernel**：从 `abs_block.mlu` 或 unary 模板复制结构，改成自己的计算。
5. **注册编译**：按仓库现有 CMake 规则加入源文件。
6. **写测试**：`test/` 下加 gtest 用例，覆盖边界 shape/dtype。
7. **本地构建**：`./build.sh --filter="<op>"`。
8. **跑测试**：`./build/test/mluop_gtest --gtest_filter='*<op>*'`。
9. **性能测试**：Perf-Analyse / CNPerf。
10. **更新 Op List**（如果贡献回仓库）。

编译过滤参数在不同版本可能不同；以 `./build.sh --help` 为准。

---

## 9. 复用建议

### 9.1 适合直接用的场景

- 该算子已在 Op List 中，且 dtype/shape 满足。
- 只需要推理，不要求修改内部实现。
- 想参考“官方推荐的写法”。

### 9.2 适合抄结构、不适合抄代码的场景

- 自己的算子语义相似但不同（例如自定义激活）。
- 需要不同的切分/tile 策略。
- 目标架构与示例不同。

抄什么：

- `kernel.h` 的宏和容量计算
- `nram_buffer` 的统一缓冲管理
- 三段流水的同步位置
- host 侧参数检查
- 测试结构

不要抄：

- 写死的架构常量（除非已确认）
- 只适用于特定 dtype 的分派逻辑
- 示例里为了简化而省略的边界处理

### 9.3 许可

mlu-ops 是 MIT 许可；可以商用、修改、再分发，但需保留版权声明。基于它写的算子建议在文件头注明来源。

---

## 10. 常见问题

| 问题 | 原因 | 处理 |
|---|---|---|
| 编译找不到 `kernel.h` | include 路径不对 | 按仓库 CMake 的 include 设置 |
| 运行报 unsupported arch | 编译架构与板卡不符 | `cnmon info` 确认，重编 |
| 结果只对一部分 | 尾块/切分 | 对照 `abs_block.mlu` 的余数处理 |
| 性能远低于预期 | 没用模板的流水，或 tile 太小 | 直接实例化 unary 模板对照 |
| 链接不到 `libmluops.so` | `LD_LIBRARY_PATH` 未包含 `build/lib` | 设置环境变量 |
| gtest 全挂 | CNNL/驱动版本不满足 | 对照 README 的版本要求 |
| 想改算子但不敢动 | 先复制一份到独立目录 | 保留原实现做对照 |
