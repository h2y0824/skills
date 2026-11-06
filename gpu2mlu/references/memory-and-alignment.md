# 内存模型、对齐与容量

> MLU 上最常见的“结果错”和“性能差”都来自这一层：数据放错地址空间、对齐不满足、tile 超出片上容量、stride 访问。
> 本文给出可执行的规则和计算公式。

## 目录

1. [存储层级](#1-存储层级)
2. [容量表](#2-容量表)
3. [地址空间语义](#3-地址空间语义)
4. [对齐规则](#4-对齐规则)
5. [tile 大小怎么算](#5-tile-大小怎么算)
6. [GDRAM 访问模式](#6-gdram-访问模式)
7. [stride 与布局](#7-stride-与布局)
8. [workspace](#8-workspace)
9. [片上驻留](#9-片上驻留)
10. [检查清单](#10-检查清单)

---

## 1. 存储层级

```
GDRAM（全局显存，所有 Core 共享）
  │
  ├── L2 Cache（硬件管理）
  │
  ├── LDRAM（每个 Core 私有的片外缓冲）
  │
  └── Cluster
        ├── SRAM（Cluster 内共享，4 个 MLU Core + 1 个 Memory Core）
        ├── MLU Core
        │     ├── NRAM（向量/张量存储）
        │     ├── WRAM（权重存储）
        │     └── GPR（通用寄存器，≤48 bit）
        └── ...
```

| 存储 | 位置 | 私有性 | 访问方式 | 典型用途 |
|---|---|---|---|---|
| GPR | 片上 | Core 私有 | 标量指令 | 地址、循环变量、标量运算 |
| NRAM | 片上 | Core 私有 | `__memcpy` + `__bang_*` | 逐元素/归约的输入输出 |
| WRAM | 片上 | Core 私有 | `__memcpy` + 矩阵/卷积指令 | 权重、B 矩阵 |
| SRAM | 片上 | Cluster 共享 | `__memcpy` + 同步 | 多核交换、共享中间结果 |
| LDRAM | 片外 | Core 私有 | `__memcpy` | 放不下的私有数据 |
| L2 | 片上 | 设备共享 | 硬件 | 缓存 |
| GDRAM | 片外 | 设备全局 | `__memcpy` / 直接寻址 | 输入输出、全局变量 |

**关键点**

- 向量/张量指令的输入输出**必须在 NRAM/WRAM/SRAM**；不能直接对 GDRAM 指针做 `__bang_add`。
- `__mlu_shared__` 在 SRAM，属于**整个 Kernel 的 Cluster**，不是每个 Task 私有。
- GDRAM 上的指针可以参与地址计算（`a + offset`），但数据必须先搬进片上才能算。

---

## 2. 容量表

官方 BANG C 4.1 文档给出的片上容量（单位 KB）：

| 架构 | NRAM | WRAM | SRAM |
|---|---|---|---|
| mtp_220 | 512 | 512 | 2048 |
| mtp_270 | 512 | 1024 | 2048 |
| mtp_290 | 512 | 512 | 2048 |
| mtp_372 | 768 | 1024 | 4096 |

**不要把这些数字写死在代码里。** 用编译宏：

```cpp
constexpr int NRAM_KB = __MLU_NRAM_SIZE__;
constexpr int SRAM_KB = __MLU_SRAM_SIZE__;
constexpr int WRAM_KB = __MLU_WRAM_SIZE__;
```

宏的单位是 **KB**。实际可用量要减去编译器栈保留：mlu-ops 的 `kernel.h` 定义为

```cpp
#define REM_FOR_STACK (128 * 1024)                       // Byte
#define MAX_NRAM_SIZE (__MLU_NRAM_SIZE__ * 1024 - REM_FOR_STACK)
#define MAX_SRAM_SIZE (__MLU_SRAM_SIZE__ * 1024 - REM_FOR_STACK)
```

unary 模板更进一步：

```cpp
#define UNARY_NRAM_SIZE (MAX_NRAM_SIZE + REM_FOR_STACK - 148 * 1024)
```

也就是说，在 372 上 unary 模板实际只用约 `768 - 148 = 620KB` 的 NRAM。自己写工程时，至少预留 128KB，复杂 kernel 预留更多。

**验证方式**：编译后看 cncc 是否报栈溢出；用 `-S` 看栈分配；必要时用 CNGDB 查看。不要等到运行时才发现。

---

## 3. 地址空间语义

| 修饰符 | 默认对齐 | 生存期 | 初始化 | 共享范围 |
|---|---|---|---|---|
| `__nram__` | 64B | 一个 Task | 否 | 单 Core |
| `__wram__` | 64B | 一个 Task | 否 | 单 Core |
| `__ldram__` | 64B | 一个 Task | 否 | 单 Core |
| `__mlu_shared__` | 64B | 整个 Kernel | 否 | Cluster 内所有 Core |
| `__mlu_const__` | — | 上下文 | 否 | 所有 Task（只读） |
| `__mlu_device__` | — | 上下文 | 否 | 所有 Task |

要点：

1. **不会自动初始化。** `__nram__ float buf[1024];` 的内容是不确定的；用之前必须 `__memcpy` 或 `__bang_write_zero`。
2. **默认 64B 对齐。** 可以用 `__attribute__((aligned(128)))` 提升到 128B/256B；对齐值必须是 ≥64 的 2 的幂。
3. **栈变量不能用于 IO/MOVE/COMPUTE 流。** 普通局部数组在栈上，`__memcpy(buf, ...)` 或 `__bang_add(buf, ...)` 可能编译失败或行为未定义。
4. **设备侧全局变量必须带修饰符。** `__mlu_device__` / `__mlu_const__` / `__mlu_shared__`；`extern` 修饰设备侧全局变量不被支持。
5. **`__mlu_const__` 在 GDRAM。** 不是 CUDA 那种片上常量缓存；小常量优先编译期展开或放 NRAM。

---

## 4. 对齐规则

### 4.1 三个层次

| 层次 | 要求 | 不满足的后果 |
|---|---|---|
| 功能正确性 | `__memcpy` 的地址按类型对齐；size 按架构要求 | 编译错误、运行错误、结果错 |
| 向量指令 | 地址 64B 对齐；`count * sizeof(type)` 是 128B 的整数倍（2xx 强制） | 结果错或编译报错 |
| 峰值带宽 | 见下表 | 能跑但带宽下降 |

### 4.2 官方性能对齐表

| 存储 | 地址对齐 | size 对齐 |
|---|---|---|
| NRAM | 16B | 128B |
| SRAM | 16B | 128B |
| WRAM | 64B | 128B |
| GDRAM | 512B | 512B |
| LDRAM | 512B | 512B |

这是“达到峰值带宽”的建议对齐，不是正确性下限。实际写法：

- 所有设备内存分配用 `cnrtMalloc`，起始地址默认满足较大对齐；但**偏移**是你自己算的，`ptr + offset` 可能破坏对齐。
- 每个 tile 的起始偏移按 512B（GDRAM）/128B（NRAM）对齐。
- `count * sizeof(type)` 按 128B 向上取整。

### 4.3 对齐计算

```cpp
#define ALIGN_UP(x, a)   (((x) + (a) - 1) / (a) * (a))
#define ALIGN_DOWN(x, a) ((x) / (a) * (a))

// 元素数对齐到 128B
int align_elems(int n, int elem_size) {
  int bytes = n * elem_size;
  bytes = ALIGN_UP(bytes, 128);
  return bytes / elem_size;
}
```

浮点数组按 32 个元素（128B）对齐；`half` 按 64 个；`int8` 按 128 个。

### 4.4 尾块怎么处理

三条路，按优先级：

1. **主机侧 padding**：把输入补齐到 128B 整数倍（最干净，但要保证输出不越界写回）。
2. **kernel 内尾块单独处理**：主循环走向量指令，最后不足 128B 的部分用标量循环。
3. **掩码/边界检查**：`__bang_fcmpfilter` 等，仅当架构支持。

不要做的：把越界数据写回 GDRAM“反正多写了几个字节”。这会破坏相邻内存，且在某些分配下不崩溃、更难查。

### 4.5 典型错误

```cpp
__nram__ float buf[TILE];
float *p = src + taskId * TILE + 1;       // 偏移 4 字节，破坏 64B 对齐
__memcpy(buf, p, TILE * sizeof(float), GDRAM2NRAM);
__bang_add(buf, buf, buf, TILE);           // 可能报错或结果错
```

修正：让每个 Task 的起始偏移按 tile 对齐；如果业务上必须从 `+1` 开始，先按对齐地址搬入，再在 NRAM 内做偏移。

---

## 5. tile 大小怎么算

### 5.1 公式

设一次计算需要 `k` 个 NRAM 缓冲区，每个 tile 有 `T` 个元素，元素大小 `s` 字节：

```
k * T * s <= NRAM_AVAILABLE
T * s % 128 == 0
T >= 32 (float) / 64 (half) / 128 (int8)   // 至少 128B
```

`NRAM_AVAILABLE = __MLU_NRAM_SIZE__ * 1024 - 栈预留`。

### 5.2 例：fp32 逐元素加法

- 372：`768KB - 128KB = 640KB` 可用。
- 三个缓冲（a、b、out）：`3 * T * 4 <= 640 * 1024` → `T <= 54613`。
- 向下取到 128B 的整数倍：`T = 49152`（对应每个缓冲 192KB）。
- 也可以用两个缓冲原地计算：`2 * T * 4 <= 640KB` → `T <= 81920`，取 81920 → 每缓冲 320KB。

### 5.3 例：带中间结果的归约

- 输入 `T` + 输出 `T/32` + 临时 → 按 `1.1 * T * 4` 估算，留余量。
- 如果还要双缓冲（软流水），乘 2。

### 5.4 tile 不是越大越好

| tile 太小 | tile 太大 |
|---|---|
| 启动/同步开销占比高 | NRAM 放不下 |
| 向量指令利用率低 | 尾块粒度粗，负载不均 |
| 多核并行度可能不足 | 单 Task 延迟高，流水难重叠 |

经验起点：每 Task 处理 32KB–256KB 的数据，按实际 profile 调整。

### 5.5 编译期检查

```cpp
constexpr int TILE = 49152;
static_assert((TILE * sizeof(float)) % 128 == 0, "tile must be 128B multiple");
static_assert(3 * TILE * sizeof(float) <= 640 * 1024, "tile exceeds NRAM budget");
```

宏 `__MLU_NRAM_SIZE__` 在设备编译时可用；主机编译时不可用，所以这类断言放在 `.mlu` 文件里。

---

## 6. GDRAM 访问模式

### 6.1 粒度

- GDRAM 单次读的最小粒度是 **64B**。
- 写小于 64B 会触发**读-改-写**，带宽利用率下降。
- 因此：每次 `__memcpy` 的 size 尽量是 64B/512B 的整数倍。

### 6.2 访问模式排序（从好到差）

```
连续读  >  连续写  >  跳 stride 读  >  跳 stride 写
```

- 连续访问能打满带宽。
- stride 访问（转置、卷积 im2col 前）会产生大量小事务。
- 转置优先在片上（NRAM/SRAM）做，而不是直接读 GDRAM 的列。

### 6.3 向量指令的 128B 粒度

向量指令每个 cycle 处理 128B；处理 1B 和处理 128B 都占一个 cycle。所以：

- 元素数远小于 128B 时，计算效率按 128B 计，实际利用率极低。
- 逐元素处理 `char`/`int8` 时，务必按 128 个元素成组处理。

### 6.4 读改写陷阱

```cpp
// 错误示范：每次只写 4 字节
for (int i = 0; i < n; ++i) __memcpy(out + i, tmp + i, 4, NRAM2GDRAM);
```

应改为一次拷贝整块：

```cpp
__memcpy(out + base, tmp, count * sizeof(float), NRAM2GDRAM);
```

---

## 7. stride 与布局

### 7.1 什么时候 stride 会出问题

- 输入是非连续视图（NHWC ↔ NCHW、转置、切片）。
- 卷积的 im2col / 滑窗。
- 多 batch 的地址不连续。

### 7.2 处理策略

| 策略 | 说明 | 代价 |
|---|---|---|
| 主机侧先做连续化 | 预处理成连续张量 | 额外内存/带宽，但 kernel 简单 |
| kernel 内按行拷贝 | 每行一次 `__memcpy`，行内连续 | 行数多时启动开销大 |
| 2D 拷贝 | `cnrtMemcpy2D`（主机）或分块搬运 | 参数复杂 |
| 片上转置 | 搬入 NRAM 后用 `__bang_*` 重排 | 需要额外缓冲 |
| 直接在 stride 上算 | 只在 stride 很大、无法连续化时 | 性能差，容易错 |

### 7.3 stride 计算模板

```cpp
// 按行搬入，行内连续
int rows = ...;
int cols = ...;
int row_stride = ...;      // 元素数

for (int r = r0; r < r1; ++r) {
  const float *src_row = src + r * row_stride + c0;
  __memcpy(buf, src_row, cols * sizeof(float), GDRAM2NRAM);
  // 处理 buf[0..cols)
  __memcpy(dst + r * row_stride + c0, buf, cols * sizeof(float), NRAM2GDRAM);
}
```

如果 `cols * sizeof(float)` 不是 128B 整数倍，行内计算要处理尾块，或者按列 tile 分块。

---

## 8. workspace

多 Task 归约、排序、扫描等需要临时全局空间。

### 8.1 分配方式

- **主机侧分配**：`cnrtMalloc(workspace, bytes)`，kernel 参数传入。最常用。
- **`__mlu_shared__`**：Cluster 内共享，生存期整个 Kernel，适合 Cluster 级中间结果。
- **slab / 静态 workspace**：mlu-ops 在算子内部管理 workspace；自研工程建议显式分配。

### 8.2 大小计算

```
workspace_bytes = taskDim * partial_size + padding
```

例如 32 个 Task、每个 float 局部和：`32 * 4 = 128B`；按 512B 对齐分配即可。

### 8.3 使用规则

- 每个 Task 只写自己的槽位（`workspace[taskId]`），避免竞争。
- 写完局部结果后，需要一个 Task（或主机）做最终归约。
- Kernel 结束时 workspace 不需要清零；下次运行会覆盖。
- 不要用 `__mlu_device__` 大数组代替 workspace（全局变量容量有限且不易管理）。

---

## 9. 片上驻留

性能优化的核心：让数据在片上多停留，减少 GDRAM 往返。

### 9.1 什么时候值得驻留

- 同一份数据被多个算子反复使用（如常量权重、mask）。
- 多阶段计算可以在一个 kernel 内完成，避免中间结果落盘。
- 卷积/矩阵乘的分块复用。

### 9.2 手段

| 手段 | 位置 | 说明 |
|---|---|---|
| 融合 | NRAM | 多个逐元素算子合成一个 kernel |
| 权重常驻 | WRAM | 矩阵乘/卷积核，循环内复用 |
| Cluster 共享 | SRAM | 多个 Core 需要同一份中间结果 |
| 双缓冲 | NRAM | IO 与 Compute 重叠 |
| 分块循环 | NRAM | 一个 Task 内处理多个 tile，减少调度 |

### 9.3 代价

- 驻留占用片上容量，降低 tile 大小或并行度。
- SRAM 共享需要同步，跨核同步有开销。
- 融合后的 kernel 更难调试、更难复用。

原则：**先用 CNPerf 证明 GDRAM 往返是瓶颈，再做融合和驻留。**

---

## 10. 检查清单

**正确性**

- [ ] 所有计算数据在 NRAM/WRAM/SRAM，不在栈上
- [ ] 所有片上数组显式初始化（若算法依赖初值）
- [ ] `__memcpy` 第三个参数是字节数
- [ ] 所有偏移按元素类型对齐；向量路径按 64B/128B 对齐
- [ ] `count * sizeof(type)` 是 128B 的整数倍（或走标量尾块）
- [ ] 尾块不越界读写
- [ ] 多 Task 不重叠写
- [ ] 跨核共享 SRAM 有 `__sync_cluster`

**容量**

- [ ] tile 总字节数 ≤ 可用 NRAM（已减去栈预留）
- [ ] `static_assert` 做了编译期检查
- [ ] 双缓冲/临时缓冲都算进去了
- [ ] 大 shape 不会导致 tile 溢出

**性能**

- [ ] GDRAM 偏移按 512B 对齐
- [ ] 每次搬运 ≥64B，尽量 ≥512B
- [ ] 连续访问优先，stride 访问有意识
- [ ] 向量指令处理的元素数 ≥128B
- [ ] 没有逐元素的小 `__memcpy`
