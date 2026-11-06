# MLU 性能调优

> 目标：把“能跑”变成“知道为什么快/慢，并且每次改动都有数据支撑”。
> 工具以 CNPerf 为主；命令参数随版本变化，先用 `cnperf-cli --help` 确认。

## 目录

1. [方法论](#1-方法论)
2. [CNPerf 使用](#2-cnperf-使用)
3. [多级并行](#3-多级并行)
4. [四条指令流与软流水](#4-四条指令流与软流水)
5. [向量化与融合](#5-向量化与融合)
6. [IO 优化](#6-io-优化)
7. [同步优化](#7-同步优化)
8. [归约优化](#8-归约优化)
9. [编译器与构建](#9-编译器与构建)
10. [测量陷阱](#10-测量陷阱)
11. [调优检查清单](#11-调优检查清单)

---

## 1. 方法论

```
1. 建立基线（端到端 + 每 kernel）
2. 找热点（时间占比最大的 kernel）
3. 判断瓶颈类型（IO / Compute / 调度 / 同步）
4. 只改一个变量
5. 回归正确性 + 重新测量
6. 记录结论
```

不要做的：

- 不看 profile 就“加 -O3、加核、加流水”。
- 一次改三个地方，然后无法归因。
- 只测一个大 shape；小 shape 可能完全是启动开销主导。
- 用主机侧 wall clock 推断 kernel 时间（提交是异步的）。

---

## 2. CNPerf 使用

### 2.1 常用子命令

| 命令 | 用途 |
|---|---|
| `cnperf-cli record --args <可执行程序及参数>` | 录制一次运行 |
| `cnperf-cli timechart <日志>` | 查看时间线（各 Queue/任务/拷贝的重叠情况） |
| `cnperf-cli monitor` | 运行时监控（利用率、带宽、温度等） |
| `cnperf-cli record --pmu --args ...` | 采集 PMU 硬件计数器 |
| `cnperf-cli record --kernel_profiling --args ...` | 单 kernel 级别的耗时/资源统计 |

先跑：

```bash
cnperf-cli record --args ./your_app
cnperf-cli timechart ./your_app.cnperf-replay   # 实际输出目录名以命令提示为准
```

### 2.2 看什么

**时间线**

- 主机提交时间 vs 设备执行时间：如果设备空转等待主机，是提交/同步问题。
- 拷贝与计算是否重叠：如果串行，检查是否用了同步 `__memcpy` 或同一 Queue。
- 多 Queue 是否真的并行。
- 是否有大量小任务（碎片化）。

**PMU**

- IO 带宽是否接近峰值。
- 计算单元利用率。
- 停顿原因（内存等待、同步等待、依赖）。

**kernel profiler**

- 每个 kernel 的耗时、调用次数、平均时间。
- 单次调用的 tile 数/任务数。

### 2.3 用前后对照

保留每次优化前后的：

- 端到端耗时
- 热点 kernel 耗时
- 带宽/利用率
- 正确性结果

没有对照，调优就是玄学。

---

## 3. 多级并行

### 3.1 三个层次

| 层次 | 手段 | 适用 |
|---|---|---|
| 设备级 | 多 Queue、多流并行 | 多个独立计算/拷贝 |
| Cluster/Core 级 | `taskDim`、Union | kernel 内多核并行 |
| Core 内 | 向量指令、四条指令流 | 单任务内部效率 |

### 3.2 任务切分

```cpp
// 负载均衡：余数逐个分给前 rem 个 Task
int per = n / taskDim;
int rem = n % taskDim;
int start = taskId * per + (taskId < rem ? taskId : rem);
int count = per + (taskId < rem ? 1 : 0);
```

**常见问题**

| 问题 | 现象 | 处理 |
|---|---|---|
| `taskDim` 太小 | 只用了一部分 Core | 增大 `taskDim`，或每 Task 处理更多 tile |
| `taskDim` 太大 | 每 Task 数据太少，启动开销占比高 | 减小 `taskDim`，或改 grid-stride |
| 切分不均 | 最后一个 Task 拖尾 | 余数分摊，或按 tile 数分配 |
| 空 Task | `start >= n` 仍进入循环 | 提前 return |
| Task 数远大于物理核 | 多轮调度，统计失真 | 以实际吞吐为准，不要假设一轮完成 |

### 3.3 Union 的并行度

- UnionN 让 N 个 Cluster 协同；N 越大，单次并行度越高，但约束越多、同步越贵。
- 先小 N 验证正确性，再扩大。
- 不要用 Union 解决“单核算得太慢”；先优化单核内的向量化和流水。

### 3.4 设备级并行

```cpp
// 两个独立分支：不同 Queue
branch_a<<<dim, cnrtFuncTypeBlock, qa>>>(...);
branch_b<<<dim, cnrtFuncTypeBlock, qb>>>(...);
CNRT_CHECK(cnrtQueueSync(qa));
CNRT_CHECK(cnrtQueueSync(qb));
```

只有分支之间没有数据依赖时才并行；有依赖就用 notifier 建立顺序。

---

## 4. 四条指令流与软流水

### 4.1 并行前提

IO / Move / Compute / Scalar 四条流可以同时执行。但要满足：

1. 数据依赖已同步。
2. 片上缓冲足够（双缓冲）。
3. 指令之间没有隐式串行（例如标量循环会阻塞）。

### 4.2 最简单的软流水

```
iteration i:
  [IO]   async load tile i+1
  [Comp] compute tile i
  [IO]   async store tile i-1
```

代码结构见 [`bang-c-kernel-guide.md`](bang-c-kernel-guide.md) 第 7.3 节。

### 4.3 同步粒度

| 同步 | 效果 |
|---|---|
| `__sync()` | 全部流等待，最稳但最慢 |
| `__sync_io()` | 只等 IO，允许 Compute 继续 |
| `__sync_compute()` | 只等 Compute |
| `__sync_io_move_compute()` | 等三条流 |

软流水里尽量用细粒度同步；不确定时用 `__sync()` 保证正确，再逐步收紧。

### 4.4 双缓冲开销

- 缓冲翻倍会减少可用的 tile 大小，可能抵消收益。
- 数据量大、计算重时收益明显；小 kernel 可能负收益。
- 用 CNPerf 看 IO 与 Compute 是否真的重叠；没重叠就是同步写错了。

---

## 5. 向量化与融合

### 5.1 向量化

一条向量指令每 cycle 处理 128B。判断是否向量化：

- 源码里有没有逐元素 for 循环做大块数据？
- `cncc -S` 看生成的是向量指令还是标量指令？
- 元素数是否 ≥128B？小类型是否成组处理？

**反例**：

```cpp
for (int i = 0; i < n; ++i) out[i] = a[i] + b[i];   // 标量
```

**正例**：

```cpp
__bang_add(out, a, b, n);                            // 向量
```

### 5.2 融合

把多个逐元素算子合成一个 kernel，减少 GDRAM 往返：

```
未融合：GDRAM → NRAM → add → GDRAM → NRAM → mul → GDRAM ...
融合后：GDRAM → NRAM → add → mul → GDRAM
```

融合的收益来自减少 IO，不是减少计算。如果 kernel 是计算瓶颈，融合收益有限。

融合的代价：

- NRAM 需要更多缓冲。
- kernel 变大，编译时间/寄存器压力上升。
- 调试困难；建议先保留未融合版本做对照。

### 5.3 选择正确的原语

| 计算 | 原语 |
|---|---|
| 逐元素 add/mul | `__bang_add` / `__bang_mul` |
| 激活函数 | `__bang_*` 或 `__bang_fusion` |
| 矩阵乘 | `__bang_matmul` |
| 卷积 | `__bang_conv` 或 CNNL |
| 查表 | `__bang_lut_s32/s16` |
| 比较过滤 | `__bang_fcmpfilter` |

不要用多条逐元素指令去模拟一个融合原语。

---

## 6. IO 优化

### 6.1 对齐

| 存储 | 地址 | size |
|---|---|---|
| GDRAM | 512B | 512B |
| NRAM | 16B | 128B |
| SRAM | 16B | 128B |
| WRAM | 64B | 128B |

这是峰值带宽建议；不满足会掉带宽。详见 [`memory-and-alignment.md`](memory-and-alignment.md)。

### 6.2 访问模式

```
连续读 > 连续写 > 跳 stride 读 > 跳 stride 写
```

- 转置尽量在片上做。
- 卷积的 im2col 如果必须落 GDRAM，考虑融合进卷积 kernel。
- 多 batch 数据如果地址跳跃，按行/按块搬运。

### 6.3 搬运粒度

- 单次 <64B 的 GDRAM 写会触发读-改-写。
- 每次搬运尽量 ≥512B。
- 不要把“一次搬运”拆成逐元素拷贝。

### 6.4 重叠

- 同一 Queue 内是顺序的；叠加拷/算重叠需要多 Queue 或异步拷贝。
- `__memcpy_async` 的正确性依赖同步；重叠收益依赖缓冲。

---

## 7. 同步优化

### 7.1 同步代价排序

```
__sync_compute / __sync_io / __sync_move  <  __sync  <  __sync_cluster  <  __sync_all_ipu  <  __sync_all
```

### 7.2 常见浪费

- 循环里每次都 `__sync()`，其实只需要最后一次。
- 用 `__sync_all()` 同步整个设备，其实只需要 Cluster 内。
- 用 `__sync_cluster()` 在 Block 任务里（语义不对）。
- 主机侧 `cnrtSyncDevice()` 代替 `cnrtQueueSync(queue)`，把其他 Queue 也等了。

### 7.3 正确性优先

同步优化必须在正确性回归之后做。少一个 `__sync` 可能只在大数据/多核/特定调度下出错。

---

## 8. 归约优化

### 8.1 层次

```
Task 内：__bang_reduce_sum（每 128B 一个结果）→ 局部归约
Task 间：workspace[taskId] → 单 Task 或主机归约
Cluster 间：__sync_cluster + SRAM（Union）
```

### 8.2 避免全局原子

`__bang_atomic_add` 走 GDRAM，争用高。workspace 方案通常更快且结果确定。

### 8.3 树形归约

如果 `taskDim` 很大，主机侧串行求和会成为瓶颈；可以在 kernel 内做树形归约（需要多轮启动或 Union 同步）。

---

## 9. 编译器与构建

### 9.1 必做

```bash
cncc ... -O3 --bang-mlu-arch=<correct_arch>
```

- cncc 默认 `-O0`；不加 `-O3` 性能可能差数倍。
- 架构必须匹配；错误架构可能直接无法运行。
- Release 构建不要带 `-g`（`-g` 只能配 `-O0`）。

### 9.2 查看生成代码

```bash
cncc kernel.mlu -S --bang-mlu-arch=mtp_372 -O3 -o kernel.s
```

检查：

- 是否生成了向量指令。
- 是否有大量标量循环。
- 栈/NRAM 使用量。

### 9.3 算法选择

- 同样的语义，不同实现差异可能远大于编译选项。
- 矩阵乘优先 `__bang_matmul`，卷积优先 `__bang_conv`/CNNL。
- 逐元素优先单条向量指令，不要用多条指令拼接。

---

## 10. 测量陷阱

| 陷阱 | 说明 | 正确做法 |
|---|---|---|
| 异步启动未同步 | 主机计时只测到提交时间 | `cnrtQueueSync` 后再停表 |
| 首次运行包含初始化 | 首次调用有加载/编译开销 | 预热后再测 |
| 缓存效应 | 第二次运行数据在 L2 | 每次清缓存或测冷/热两组 |
| 单位混淆 | `cnrtNotifierElapsedTime` 与 `cnrtNotifierDuration` 单位说明不一致 | 目标机校准 |
| 单 shape 采样 | 小 shape 全是启动开销 | 多 shape 测 |
| 只测 kernel | 忽略前后拷贝 | 端到端 + 分 kernel 都测 |
| 多 Queue 未同步就停表 | 少算了尾部时间 | 所有 Queue 都同步 |
| 主机侧打印 | `printf`/`__bang_printf` 改变时序 | 测量时关闭 |

### 10.1 计时模板

```cpp
// 预热
for (int i = 0; i < 5; ++i) kernel<<<dim, cnrtFuncTypeBlock, queue>>>(...);
CNRT_CHECK(cnrtQueueSync(queue));

// 计时
cnrtNotifier_t t0, t1;
CNRT_CHECK(cnrtNotifierCreate(&t0));
CNRT_CHECK(cnrtNotifierCreate(&t1));
const int iters = 50;
CNRT_CHECK(cnrtPlaceNotifier(t0, queue));
for (int i = 0; i < iters; ++i)
  kernel<<<dim, cnrtFuncTypeBlock, queue>>>(...);
CNRT_CHECK(cnrtPlaceNotifier(t1, queue));
CNRT_CHECK(cnrtQueueSync(queue));

float total = 0.0f;
CNRT_CHECK(cnrtNotifierElapsedTime(t0, t1, &total));
printf("avg: %.3f ms\n", total / iters);   // 单位以目标机校准为准
```

---

## 11. 调优检查清单

**先确认**

- [ ] 有 GPU 基线（同 shape、同 dtype）
- [ ] 有 MLU 端到端与分 kernel 基线
- [ ] 已确定热点 kernel
- [ ] 已判断瓶颈类型（IO/Compute/调度/同步）

**任务与并行**

- [ ] `taskDim` 与工作量匹配
- [ ] 切分均衡，尾块不拖尾
- [ ] 空 Task 提前返回
- [ ] 需要跨核协作时才用 Union

**IO**

- [ ] GDRAM 偏移 512B 对齐
- [ ] 每次搬运 ≥512B
- [ ] 连续访问
- [ ] 异步拷贝与计算重叠

**计算**

- [ ] 使用向量指令而非标量循环
- [ ] 元素数 ≥128B
- [ ] 使用合适的融合原语
- [ ] 必要时融合相邻算子

**同步**

- [ ] 同步范围最小化
- [ ] 没有冗余同步
- [ ] 正确性回归通过

**构建**

- [ ] `-O3`
- [ ] 正确的 `--bang-mlu-arch`
- [ ] 没有调试打印
- [ ] 已用 `-S` 检查生成代码
