# BANG C Kernel 开发指南

> 面向“已经会写 CUDA kernel、第一次写 BANG C”的读者。
> 所有 API 名称来自 BANG C Developer Guide 4.7.2 / 编程指南 1.7.0；不同架构支持范围不同，写字前先确认目标架构。

## 目录

1. [文件与编译](#1-文件与编译)
2. [Task 模型](#2-task-模型)
3. [Block 与 Union](#3-block-与-union)
4. [内存与搬运](#4-内存与搬运)
5. [计算原语](#5-计算原语)
6. [同步](#6-同步)
7. [分块与尾块模板](#7-分块与尾块模板)
8. [多 Task 切分模板](#8-多-task-切分模板)
9. [归约模板](#9-归约模板)
10. [矩阵乘与卷积](#10-矩阵乘与卷积)
11. [原子操作](#11-原子操作)
12. [调试](#12-调试)
13. [C++ 语言限制](#13-c-语言限制)
14. [移植检查清单](#14-移植检查清单)

---

## 1. 文件与编译

### 1.1 文件类型

| 文件 | 内容 | 编译器 |
|---|---|---|
| `.mlu` | 主机侧 + 设备侧 BANG C（含 `main` 或启动封装） | `cncc` |
| `.h` / `.hpp` | 声明、常量、模板 | 任意 |
| `.cpp` | 纯主机侧代码（不含 `<<<>>>`、不含 `__mlu_*`） | g++ / clang++ |

`#include <bang.h>` 是必须的；主机侧还需要 `cnrt.h`（`bang.h` 通常已包含）。

### 1.2 必需与常用编译选项

```bash
cncc kernel.mlu -o kernel \
  -I"$NEUWARE_HOME/include" \
  -L"$NEUWARE_HOME/lib64" -lcndrv -lcnrt \
  --bang-mlu-arch=mtp_372 \
  -O3 -std=c++11
```

| 选项 | 作用 | 注意 |
|---|---|---|
| `--bang-mlu-arch=<arch>` | 目标架构 | **必填**；写错会“编译通过但运行找不到 kernel” |
| `--bang-arch=<arch>` | 生成多架构 fatbin | 用于分发；语法查版本文档 |
| `-O3` | 优化 | **cncc 默认 -O0**，性能代码必须显式加 |
| `-g` | 调试信息 | 只能与 `-O0` 配合 |
| `-S` | 输出汇编 | 排查是否生成向量指令 |
| `--bang-device-only` | 只编译设备代码 | 产物为 CNBin |
| `--bang-host-only` | 只编译主机代码 | |
| `--bang-fatbin-only` | 只生成 fatbin | |

架构宏：`__BANG_ARCH__` 是数值（如 372），`__MLU_NRAM_SIZE__` / `__MLU_SRAM_SIZE__` / `__MLU_WRAM_SIZE__` 是 **KB** 数值。

### 1.3 最小可运行程序

```cpp
#include <bang.h>

#define LEN 1024

__mlu_entry__ void vec_add(float *out, const float *a, const float *b) {
  __nram__ float na[LEN];
  __nram__ float nb[LEN];
  __nram__ float no[LEN];

  __memcpy(na, a + taskId * LEN, LEN * sizeof(float), GDRAM2NRAM);
  __memcpy(nb, b + taskId * LEN, LEN * sizeof(float), GDRAM2NRAM);
  __bang_add(no, na, nb, LEN);
  __memcpy(out + taskId * LEN, no, LEN * sizeof(float), NRAM2GDRAM);
}

int main() {
  cnrtQueue_t queue;
  CNRT_CHECK(cnrtSetDevice(0));
  CNRT_CHECK(cnrtQueueCreate(&queue));

  float *h_a = (float *)malloc(LEN * sizeof(float));
  float *h_b = (float *)malloc(LEN * sizeof(float));
  float *h_o = (float *)malloc(LEN * sizeof(float));
  for (int i = 0; i < LEN; ++i) { h_a[i] = 1.0f; h_b[i] = 2.0f; }

  float *d_a, *d_b, *d_o;
  CNRT_CHECK(cnrtMalloc((void **)&d_a, LEN * sizeof(float)));
  CNRT_CHECK(cnrtMalloc((void **)&d_b, LEN * sizeof(float)));
  CNRT_CHECK(cnrtMalloc((void **)&d_o, LEN * sizeof(float)));
  CNRT_CHECK(cnrtMemcpy(d_a, h_a, LEN * sizeof(float), cnrtMemcpyHostToDev));
  CNRT_CHECK(cnrtMemcpy(d_b, h_b, LEN * sizeof(float), cnrtMemcpyHostToDev));

  cnrtDim3_t dim = {1, 1, 1};
  vec_add<<<dim, cnrtFuncTypeBlock, queue>>>(d_o, d_a, d_b);
  CNRT_CHECK(cnrtQueueSync(queue));               // kernel 异步，必须同步

  CNRT_CHECK(cnrtMemcpy(h_o, d_o, LEN * sizeof(float), cnrtMemcpyDevToHost));
  for (int i = 0; i < LEN; ++i)
    if (h_o[i] != 3.0f) { printf("mismatch at %d: %f\n", i, h_o[i]); return 1; }

  CNRT_CHECK(cnrtQueueDestroy(queue));
  CNRT_CHECK(cnrtFree(d_a)); CNRT_CHECK(cnrtFree(d_b)); CNRT_CHECK(cnrtFree(d_o));
  free(h_a); free(h_b); free(h_o);
  return 0;
}
```

---

## 2. Task 模型

### 2.1 内建变量

| 变量 | 含义 |
|---|---|
| `taskId` | 当前 Task 在 task grid 中的线性编号，`0 .. taskDim-1` |
| `taskDim` | Task 总数 |
| `taskIdX/Y/Z` | 三维编号 |
| `taskDimX/Y/Z` | 三维规模 |
| `coreDim` | 每 Cluster 的 MLU Core 数（372 为 4；322 为 1） |
| `coreId` | 当前 Core 在 Cluster 内的编号 |
| `clusterDim` | 当前任务可用的 Cluster 规模（具体语义以版本文档为准） |
| `clusterId` | 当前 Cluster 编号 |

线性关系：

```
taskDim  = taskDimX * taskDimY * taskDimZ
taskId   = taskIdZ * taskDimY * taskDimX + taskIdY * taskDimX + taskIdX
```

### 2.2 启动

```cpp
Kernel<<<dim, ktype, queue>>>(args...);
```

- `dim`：`cnrtDim3_t`，Task 的三维规模。
- `ktype`：`cnrtFunctionType_t`，`cnrtFuncTypeBlock` 或 `cnrtFuncTypeUnionN`。
- `queue`：`cnrtQueue_t`；默认 Queue 可传 `0`。
- 启动是**异步**的；返回值不表示完成。

> `cnrtFunctionType_t` 的枚举在不同版本的示例中可能写作 `cnrtFuncTypeBlock` 或 `CNRT_FUNC_TYPE_BLOCK`；以目标机 `cnrt.h` 为准。

### 2.3 一个 Task 到底在做什么

一个 Task 是**一个 MLU Core 上的一次 kernel 实例执行**。Task 内部：

- 没有 CUDA 意义上的线程；并行靠向量指令（一次处理 128B）。
- 可以用 `taskId` 选出自己要处理的数据块。
- 多个 Task 可能被调度到同一个物理 Core 上顺序执行（Block 模式下 driver 可以多轮展开）。
- 不要假设 `taskDim == 物理核数`，也不要假设 `taskId == coreId`。

### 2.4 编写思路

CUDA：

```
每个线程处理一个元素 → 启动 N 个线程
```

BANG C：

```
每个 Task 处理一个 tile（≥128B，尽量几 KB 到几十 KB）
→ 启动 taskDim 个 Task
→ Task 内部用 __bang_* 向量指令处理整块
```

tile 越大，启动/调度/同步开销摊得越薄，但受 NRAM 容量限制；tile 太小会退化为“搬运比计算还贵”。

---

## 3. Block 与 Union

### 3.1 Block

```cpp
cnrtDim3_t dim = {16, 1, 1};
Kernel<<<dim, cnrtFuncTypeBlock, queue>>>(...);
```

- 每个 Task 独立占用一个 MLU Core，Task 之间不保证同步。
- 没有跨 Task 通信需求时用 Block。
- Task 会被调度到当前空闲的 Core；多个 Task 可能落在同一个 Core 上。

### 3.2 Union

```cpp
cnrtDim3_t dim = {16, 1, 1};
Kernel<<<dim, cnrtFuncTypeUnion1, queue>>>(...);   // 每 4 个 Task 组成一个 Union
```

Union N：**N 个 Cluster 作为一个整体**被调度，Cluster 内的 Core 可以协同（共享 SRAM、`__sync_cluster` / `__sync_all_ipu`）。

官方约束（务必在启动前检查，否则可能启动失败或结果错）：

1. 起始物理 Cluster ID 必须能被 N 整除。
2. 至少要有 N 个 Cluster 空闲。
3. `taskDimX % (N * coreDim) == 0`（未展开时）。
4. 最小并行度是 `clusterDim * coreDim`。
5. 迭代次数为 `taskDimZ * taskDimY * taskDimX / (N * coreDim)`（未展开时）。

`N` 的取值：编程指南示例写 Union1/2/4/8，mlu-ops 中定义了到 Union16 的类型宏；以目标版本 `cnrt.h` 为准。

### 3.3 怎么选

| 场景 | 选择 |
|---|---|
| 逐元素、归一化、简单池化 | Block |
| 需要 Cluster 内共享 SRAM 做数据交换 | Union1 起 |
| 需要更大并行度/跨 Cluster 归约 | UnionN，先用最小 N 验证 |
| 不确定 | 先 Block，正确且性能不够再考虑 Union |

---

## 4. 内存与搬运

### 4.1 地址空间

| 修饰符 | 位置 | 生存期 | 访问者 |
|---|---|---|---|
| `__nram__` | NRAM | 一个 Task | 本 Core |
| `__wram__` | WRAM | 一个 Task | 本 Core |
| `__ldram__` | LDRAM（片外，Core 私有） | 一个 Task | 本 Core |
| `__mlu_shared__` | SRAM | 整个 Kernel | 本 Cluster 所有 Core |
| `__mlu_const__` | GDRAM | 上下文 | 所有 Task（只读） |
| `__mlu_device__` | GDRAM | 上下文 | 所有 Task |

- 以上数组**默认 64B 对齐**，可用 `__attribute__((aligned(128)))` 提升；对齐值必须是 ≥64 的 2 的幂。
- 以上数组**不会自动初始化**；必须显式写入。
- 普通栈数组不能用 IO/MOVE/COMPUTE 流指令访问；要参与计算必须加修饰符。

### 4.2 `__memcpy`

```cpp
__memcpy(dst, src, bytes, direction);
```

第三个参数是**字节数**。常用方向（完整枚举与支持情况以 `bang.h` / 版本文档为准）：

| 方向 | 含义 |
|---|---|
| `GDRAM2NRAM` | 全局 → 片上向量存储 |
| `NRAM2GDRAM` | 片上 → 全局 |
| `GDRAM2GDRAM` | 全局 → 全局（设备内拷贝） |
| `GDRAM2SRAM` / `SRAM2GDRAM` | 全局 ↔ Cluster 共享 |
| `NRAM2SRAM` / `SRAM2NRAM` | 核内 ↔ Cluster 共享 |
| `LDRAM2NRAM` / `NRAM2LDRAM` | 核私有片外 ↔ 片上 |
| `GDRAM2WRAM` / `WRAM2GDRAM` | 全局 ↔ 权重存储 |

约束：地址对齐和 size 对齐随架构不同。**保守写法**：所有地址按 64B 对齐，size 按 128B 对齐。

异步版本：

```cpp
__memcpy_async(dst, src, bytes, direction);
// 之后必须 __sync() 或 __sync_io_move_compute() 才能安全消费数据
```

### 4.3 容量

```cpp
#if defined(__BANG_ARCH__)
  constexpr int NRAM_BYTES = __MLU_NRAM_SIZE__ * 1024;   // 单位 KB
  constexpr int SRAM_BYTES = __MLU_SRAM_SIZE__ * 1024;
  constexpr int WRAM_BYTES = __MLU_WRAM_SIZE__ * 1024;
#endif
```

> 这些是“编译时可见的容量上限”，**不是全部可用**：编译器要保留栈空间。mlu-ops 的 `kernel.h` 在 NRAM/SRAM 上统一减去 `REM_FOR_STACK = 128 * 1024` 字节，并在 unary 模板里进一步保守。写自己的工程时至少预留 128KB，并以运行时/编译日志为准。

不要写死具体容量。用宏，并在编译期加 `static_assert`。

---

## 5. 计算原语

### 5.1 逐元素

```cpp
__bang_add(dst, src1, src2, count);
__bang_sub(dst, src1, src2, count);
__bang_mul(dst, src1, src2, count);
__bang_div(dst, src1, src2, count);
__bang_max(dst, src1, src2, count);
__bang_min(dst, src1, src2, count);
__bang_pow(dst, src, count);          // 幂/指数类请查具体函数名
__bang_abs(dst, src, count);
__bang_neg(dst, src, count);
__bang_reciprocal(dst, src, count);
__bang_sqrt(dst, src, count);
__bang_exp(dst, src, count);
__bang_log(dst, src, count);
```

通用约束（以 2xx 系列最严格，3xx/5xx 部分放宽）：

- `dst` / `src` 必须在 NRAM。
- 地址按 64B 对齐。
- `count * sizeof(type)` 按 128B 整除（2xx 强制；其他架构为了性能也照做）。
- 支持的数据类型随架构变化：float 在 2xx+；int/short/char 在 3xx+（tp_520 除外）；bfloat16 在 5xx+。**写之前查目标架构的表**。

当 `count * sizeof(type)` 不是 128B 整数倍时，用掩码/填充补齐，或对尾部改用标量循环。

### 5.2 标量扩展

`__bang_add_scalar(dst, src, scalar, count)` 之类的标量版本、`__bang_mul_scalar` 等，参数顺序以头文件为准；不确定时用“把标量广播成 NRAM 向量再做二元运算”的稳妥写法。

### 5.3 类型转换

`__bang_float2int16`、`__bang_int82half` 等命名有规律但数量多，按目标版本文档查表。`__bang_cast` 不是通用接口。

### 5.4 归约

```cpp
__bang_reduce_sum(dst, src, count);
```

- 每 128B 源数据求和，结果写到 `dst` 对应 128B 块的**首元素**。
- `dst` 至少 128B。
- `count * sizeof(type)` 必须是 128B 的整数倍。
- 2xx 上 `dst` 其余元素会被置零；3xx+ 不修改。
- 返回标量的 `__bang_sum` 仅在较新架构（BANG ≥ 520 / mtp_5xx）可用，**不要假设所有卡都有**。

### 5.5 其他常用

| 接口 | 用途 | 备注 |
|---|---|---|
| `__bang_write_zero(dst, count)` | 初始化 NRAM 为零 | 数组不会自动初始化 |
| `__bang_fusion` | 融合运算 | 参数形式查文档 |
| `__bang_fcmpfilter` | 比较过滤 | |
| `__bang_lut_s32` / `_s16` | 查表 | |
| `__bang_printf` | 设备侧打印 | 有性能影响，调试用 |
| `__bang_atomic_add` 等 | 原子 | 见第 11 节 |
| `__bang_matmul` | 矩阵乘 | 见第 10 节 |
| `__bang_conv` | 卷积 | 见第 10 节 |

---

## 6. 同步

### 6.1 四条指令流

IO（GDRAM↔片上）、Move（片上↔片上）、Compute（向量/张量计算）、Scalar（标量）可以并行。硬件只保证寄存器依赖，**内存依赖要显式同步**。

### 6.2 核内

| 接口 | 等待 |
|---|---|
| `__sync()` | 本 Core 所有指令流（最稳妥） |
| `__sync_compute()` | Compute 流 |
| `__sync_io()` | IO 流 |
| `__sync_move()` | Move 流 |
| `__sync_io_move_compute()` | IO + Move + Compute |

### 6.3 核间

| 接口 | 范围 |
|---|---|
| `__sync_cluster()` | 本 Cluster 的 1 个 MPU + `coreDim` 个 MLU Core |
| `__sync_all_ipu()` | 所有参与 Kernel 的 MLU Core（Union1=4、Union2=8、Union4=16，依此类推） |
| `__sync_all_mpu()` | 所有 MPU |
| `__sync_all()` | 所有 IPU + MPU（最贵） |

### 6.4 使用原则

1. 同步版 `__memcpy` 不需要额外同步；异步版需要。
2. 跨核读写共享 SRAM：写方 `__sync_cluster()`，读方也在 `__sync_cluster()` 之后读。
3. 只在必要处用最大范围同步；`__sync_all()` 会显著降低并行度。
4. 不要在循环里无条件塞 `__sync()`，先判断是否真的存在跨流依赖。

### 6.5 常见错误

| 错误 | 后果 |
|---|---|
| `__memcpy_async` 后直接读 NRAM | 读到旧数据/半成品 |
| 两个 Core 写同一 SRAM 区域后再读，没有 `__sync_cluster` | 读到未写完的数据 |
| 用 `__sync()` 代替 `__sync_cluster()` 做跨核同步 | 同步范围不够，结果随机错 |
| 在非 Union 任务里用 `__sync_cluster()` | 语义不成立或行为未定义 |

---

## 7. 分块与尾块模板

### 7.1 逐元素：固定 tile + 尾块

```cpp
#define TILE 4096          // 元素数；TILE * sizeof(float) 必须是 128B 的倍数

__mlu_entry__ void add_kernel(float *out, const float *a, const float *b, int n) {
  int start = taskId * TILE;
  if (start >= n) return;                     // 空 Task，必须提前返回
  int remain = n - start;
  int count = remain < TILE ? remain : TILE;

  __nram__ float na[TILE];
  __nram__ float nb[TILE];
  __nram__ float no[TILE];

  if (count == TILE) {
    __memcpy(na, a + start, TILE * sizeof(float), GDRAM2NRAM);
    __memcpy(nb, b + start, TILE * sizeof(float), GDRAM2NRAM);
    __bang_add(no, na, nb, TILE);
    __memcpy(out + start, no, TILE * sizeof(float), NRAM2GDRAM);
  } else {
    // 尾块：按字节拷贝，保证不越界；向量指令不可用时用标量循环
    __memcpy(na, a + start, count * sizeof(float), GDRAM2NRAM);
    __memcpy(nb, b + start, count * sizeof(float), GDRAM2NRAM);
    for (int i = 0; i < count; ++i) na[i] = na[i] + nb[i];
    __memcpy(out + start, na, count * sizeof(float), NRAM2GDRAM);
  }
}
```

要点：

- `count * sizeof(float)` 为 0 时不要调用拷贝（空指针/零长度行为不保证）。
- 尾块的标量循环慢，但只在最后一个 Task 出现；也可以把尾块合并进主循环的“最后一次不足 tile”处理。
- 如果要求所有 Task 用同一条向量路径，可以把尾块 padding 到 128B，但**不要把 padding 写回 GDRAM 越界区域**。

### 7.2 1D → 大 tile 循环

```cpp
__mlu_entry__ void add_loop(float *out, const float *a, const float *b, int n) {
  const int TILE = 4096;
  __nram__ float na[TILE];
  __nram__ float nb[TILE];
  __nram__ float no[TILE];

  for (int base = taskId * TILE; base < n; base += taskDim * TILE) {
    int count = (n - base) < TILE ? (n - base) : TILE;
    if (count <= 0) continue;
    __memcpy(na, a + base, count * sizeof(float), GDRAM2NRAM);
    __memcpy(nb, b + base, count * sizeof(float), GDRAM2NRAM);
    if (count % 32 == 0) {                    // count*4 是 128B 的整数倍
      __bang_add(no, na, nb, count);
      __memcpy(out + base, no, count * sizeof(float), NRAM2GDRAM);
    } else {
      for (int i = 0; i < count; ++i) na[i] += nb[i];
      __memcpy(out + base, na, count * sizeof(float), NRAM2GDRAM);
    }
  }
}
```

这种“grid-stride”写法让每个 Task 处理多个 tile，适合 `n` 远大于 `taskDim * TILE` 的情况，能显著摊薄启动开销。

### 7.3 软流水（IO / Compute / Store 重叠）

```cpp
// TILE 个 float；TILE * sizeof(float) 必须是 128B 的倍数
void pipeline_stage(float *out, const float *in, int base, int count) {
  __nram__ float buf_a[2][TILE];     // 输入双缓冲
  __nram__ float buf_b[2][TILE];     // 输出双缓冲

  // prologue：搬入第一块
  __memcpy_async(buf_a[0], in + base, TILE * sizeof(float), GDRAM2NRAM);
  __sync();

  int cur = 0;
  for (int i = 0; i < count; i += TILE) {
    int next = i + TILE;
    if (next < count) {
      __memcpy_async(buf_a[cur ^ 1], in + base + next,
                     TILE * sizeof(float), GDRAM2NRAM);
    }

    // 计算当前块（用向量指令，不要写标量循环）
    __bang_add(buf_b[cur], buf_a[cur], buf_a[cur], TILE);   // 2 * x
    __sync_compute();

    // 写回当前块
    __memcpy_async(out + base + i, buf_b[cur],
                   TILE * sizeof(float), NRAM2GDRAM);

    if (next < count) {
      __sync();                     // 等预取完成，再切换到下一组缓冲
      cur ^= 1;
    }
  }
  __sync();                         // 等最后一块写回完成
}
```

要点：

- 用索引 `cur` 乒乓切换，不要逐元素复制缓冲。
- 这里用 `__sync()` 保证正确性；性能敏感时替换为 `__sync_io_move_compute()` 等更细的同步。
- `count` 不是 `TILE` 整数倍时，上面的写法会在最后一块越界。调用方必须先处理尾块，或把循环条件改成 `i + TILE <= count`，尾块单独走标量路径。
- mlu-ops 的三段流水（`unary_op_3pipeline.h`）使用更细粒度的同步和内联 `asm volatile("sync;")`；那是经过验证的实现，工程里优先复用它的结构。

---

## 8. 多 Task 切分模板

### 8.1 均分（余数给最后一个 Task）

```cpp
int per = n / taskDim;
int start = taskId * per;
int count = (taskId == taskDim - 1) ? (n - start) : per;
if (count <= 0) return;
```

优点：简单；缺点：最后一个 Task 可能明显更重。

### 8.2 余数逐个分给前 `rem` 个 Task

```cpp
int per = n / taskDim;
int rem = n % taskDim;
int start = taskId * per + (taskId < rem ? taskId : rem);
int count = per + (taskId < rem ? 1 : 0);
if (count <= 0) return;
```

负载更均衡；适合逐元素算子。

### 8.3 按行/按 tile 分配（二维数据）

```cpp
int rows_per_task = (rows + taskDim - 1) / taskDim;
int r0 = taskId * rows_per_task;
int r1 = (r0 + rows_per_task) < rows ? (r0 + rows_per_task) : rows;
if (r0 >= rows) return;

for (int r = r0; r < r1; ++r) {
  // 处理第 r 行：按列 tile 循环
}
```

### 8.4 按块（2D tile）分配

```cpp
int tiles_x = (cols + TILE_X - 1) / TILE_X;
int tiles_y = (rows + TILE_Y - 1) / TILE_Y;
int total_tiles = tiles_x * tiles_y;

for (int t = taskId; t < total_tiles; t += taskDim) {
  int ty = t / tiles_x;
  int tx = t % tiles_x;
  int x0 = tx * TILE_X, y0 = ty * TILE_Y;
  int w = min(TILE_X, cols - x0);
  int h = min(TILE_Y, rows - y0);
  // 处理 [y0, y0+h) x [x0, x0+w)
}
```

### 8.5 切分检查清单

- [ ] `taskDim == 0` 不会发生（主机侧保证）
- [ ] `n == 0` 时主机侧不启动，或 kernel 内 `if (n <= 0) return;`
- [ ] `start >= n` 的 Task 提前返回
- [ ] 每个字节只被一个 Task 写（不重叠）
- [ ] 尾块不会读到/写到分配区之外
- [ ] Block 模式下 Task 可能被多轮调度，循环条件用 `base < n` 而不是固定轮数

---

## 9. 归约模板

### 9.1 单 Task 内归约（NRAM）

```cpp
#define TILE 4096

float reduce_sum_local(const float *src, int n) {
  __nram__ float buf[TILE];
  float total = 0.0f;
  for (int base = 0; base < n; base += TILE) {
    int count = (n - base) < TILE ? (n - base) : TILE;
    __memcpy(buf, src + base, count * sizeof(float), GDRAM2NRAM);
    for (int i = 0; i < count; ++i) total += buf[i];
  }
  return total;
}
```

标量循环会慢；优化版用 `__bang_reduce_sum` 两级归约（下一节）。

### 9.2 多级归约（推荐）

```
每个 Task:
  1. 用 __bang_reduce_sum 把 TILE 内每 128B 求和到 buf
  2. 对 buf 再做一次 reduce，得到本 Task 的局部和
  3. 把局部和写到 workspace[taskId]
主机或一个 Task:
  4. 对 workspace 求和
```

```cpp
#define TILE 4096
#define REDUCE_TILE 32                  // TILE / REDUCE_TILE 个中间结果

__mlu_entry__ void row_sum(float *workspace, const float *src, int n) {
  __nram__ float buf[TILE];
  __nram__ float part[TILE / REDUCE_TILE];   // 每个 128B 块一个结果

  int per = n / taskDim;
  int start = taskId * per;
  int count = (taskId == taskDim - 1) ? (n - start) : per;
  if (count <= 0) { workspace[taskId] = 0.0f; return; }

  // 简化：假设 count 按 128B 对齐且是 TILE 的整数倍
  float total = 0.0f;
  for (int base = 0; base < count; base += TILE) {
    int c = (count - base) < TILE ? (count - base) : TILE;
    __memcpy(buf, src + start + base, c * sizeof(float), GDRAM2NRAM);
    if (c == TILE) {
      __bang_reduce_sum(part, buf, TILE);
      for (int i = 0; i < TILE / REDUCE_TILE; ++i) total += part[i];
    } else {
      for (int i = 0; i < c; ++i) total += buf[i];
    }
  }
  workspace[taskId] = total;              // 一个 Task 写一个槽位，无竞争
}
```

主机侧再对 `taskDim` 个值求和（数据量很小）。

### 9.3 为什么不用全局原子做归约

`__bang_atomic_add` 每次都要访问 GDRAM，`taskDim` 大时争用严重；workspace + 一次主机/单 Task 归约通常更快，而且结果确定。

### 9.4 浮点顺序

多级归约的累加顺序与 GPU 不同，fp32 也可能出现末位差异。验收时用相对误差，或在关键路径用更高精度累加。

---

## 10. 矩阵乘与卷积

### 10.1 `__bang_matmul`

- 典型布局：A 在 NRAM、B 在 WRAM、C 在 NRAM。
- 维度/转置/批量参数形式因架构和版本而异。
- 大矩阵需要自己分块（tiling），一次只算一个 `Mtile x Ntile`。
- 不要按 CUDA 的“一个线程算一个输出元素”移植；按“一个 Task 算一个输出 tile”设计。

伪结构：

```cpp
// 仅示意数据流，不是可直接编译的完整调用
__nram__ half a_tile[MT * KT];
__wram__ half b_tile[KT * NT];
__nram__ float c_tile[MT * NT];

for (k0 = 0; k0 < K; k0 += KT) {
  __memcpy(a_tile, A + ..., ..., GDRAM2NRAM);
  __memcpy(b_tile, B + ..., ..., GDRAM2WRAM);
  __bang_matmul(c_tile, a_tile, b_tile, ...);   // 参数查头文件
  __sync();
}
```

### 10.2 卷积

- `__bang_conv` 的输入/权重/输出布局和参数顺序以文档为准。
- 优先用 CNNL 的 `cnnlConvolutionForward`，只有特殊布局/融合需求才自己写。
- 自己写时通常：权重放 WRAM，输入 tile 放 NRAM，按输出 tile 循环，注意 padding/stride/dilation 的索引计算。

### 10.3 不要在矩阵乘里做的事

- 不要用标量三重循环代替 `__bang_matmul`（会慢一到两个数量级）。
- 不要把整个矩阵搬进 NRAM（容量不够）；必须分块。
- 不要忽略 WRAM 的对齐要求（默认 64B，按 128B 准备更稳）。

---

## 11. 原子操作

```cpp
__bang_atomic_add(dst_nram, src1_gdram, src2_nram_or_scalar, count);
```

语义：把 `src2` 原子地加到 GDRAM 上的 `src1`，并把**旧值**写到 `dst_nram`。

| 项目 | 约束 |
|---|---|
| `dst_nram` | NRAM |
| `src1_gdram` | 必须声明为 `__mlu_device__` 的 GDRAM 变量 |
| `src2` | NRAM 或标量 |
| 支持架构 | 322 / 520 不支持（以目标架构表为准） |
| 对齐 | `src1` 按元素类型对齐（通常 4B/8B） |

其他：`__bang_atomic_max/_min`（含 `_number_` / `_nan_` 变体）、`_and/_or/_xor`。`atomicCAS` 是否存在需查版本。

使用建议：

- 原子走 IO 流，延迟高；优先 workspace 方案。
- 需要“原子 + 返回旧值”时，注意 `dst_nram` 不能被其他指令流并发写。
- 多 Task 对同一地址原子累加时，结果与顺序无关（加法），但浮点加法不满足结合律，仍可能有末位差异。

---

## 12. 调试

### 12.1 `__bang_printf`

```cpp
__bang_printf("task %d count %d val %f\n", taskId, count, buf[0]);
```

- 设备侧打印，有性能开销，只在调试时用。
- 输出顺序不保证；多 Task 时加 `taskId` 前缀。

### 12.2 CNGDB

```bash
cncc kernel.mlu -o kernel --bang-mlu-arch=mtp_372 -O0 -g
cngdb ./kernel
```

- `-g` 只能配合 `-O0`。
- 断点、单步、查看 NRAM 变量；具体命令查 CNGDB 手册。

### 12.3 常见错误的定位方法

| 现象 | 定位 |
|---|---|
| 结果全零 | 检查主机拷贝方向、kernel 是否启动、`taskDim` 是否为 0 |
| 只有第一块对 | 检查 `taskId` 偏移、`taskDim` 设置 |
| 最后一块错 | 尾块边界 |
| 随机错 | 缺同步、重叠写、未初始化 |
| 精度差 | 归约顺序、类型转换、累加精度 |
| 编译通过但运行报错 | 架构不匹配、链接了错误库 |

### 12.4 编译期自检

```cpp
static_assert(__MLU_NRAM_SIZE__ >= 512, "NRAM too small");
static_assert((TILE * sizeof(float)) % 128 == 0, "TILE must be 128B aligned");
```

---

## 13. C++ 语言限制

设备侧（`__mlu_entry__` / `__mlu_func__` 函数体内）：

- **不支持函数指针**。
- **不支持设备侧全局变量的动态初始化**（构造器不会运行）。
- **不支持 `extern` 修饰设备侧全局变量和函数**。
- 模板、lambda、虚函数等支持范围以版本文档为准；保守写法是用模板做 dtype 泛化，不用虚函数。
- 不要依赖异常处理、RTTI、`std::function`。
- 设备侧全局变量必须带地址空间修饰符（`__mlu_device__` / `__mlu_const__` / `__mlu_shared__`）。
- 栈变量不能参与 IO/MOVE/COMPUTE 流指令。

主机侧没有这些限制，但包含 `<<<>>>` 的文件必须交给 cncc。

---

## 14. 移植检查清单

每个 kernel 完成时逐项确认：

**语义**

- [ ] 输入/输出 shape、stride、dtype、布局与 CUDA 版本一致
- [ ] padding/边界/NaN/Inf 行为一致
- [ ] 浮点累加顺序差异已评估

**任务**

- [ ] tile 大小使 `tile * sizeof(type)` 是 128B 的倍数
- [ ] tile 放得进 NRAM（含中间/临时缓冲），预留 ≥128KB 栈
- [ ] `taskDim` 与实际工作量匹配；空 Task 提前返回
- [ ] 多 Task 切分不重叠、不越界
- [ ] Union 任务的 N/coreDim/taskDim 约束满足

**内存**

- [ ] 所有计算数据在 NRAM/WRAM/SRAM
- [ ] 数组未依赖自动初始化
- [ ] GDRAM 偏移按 64B/512B 对齐（性能）
- [ ] 所有 `__memcpy` 的字节数正确（不是元素数）

**同步**

- [ ] `__memcpy_async` 后有 `__sync`
- [ ] 跨核共享 SRAM 有 `__sync_cluster`
- [ ] 主机侧有 `cnrtQueueSync`
- [ ] 没有在不需要的地方滥用 `__sync_all`

**性能**

- [ ] 编译加 `-O3`
- [ ] 没有把标量循环留在大数据路径上
- [ ] 必要时做了软流水/双缓冲
- [ ] CNPerf 已确认瓶颈

**构建**

- [ ] `--bang-mlu-arch` 与目标板卡一致
- [ ] 链接了 `cnrt`（用 CNNL 还要 `cnnl`）
- [ ] 主机启动代码由 cncc 编译，或通过 `extern "C"` 封装隔离
