# 主机侧运行时：CNRT / CNDrv

> 对应 CUDA Runtime API 的那一层。以下接口名称已在 CNRT 6.5.x 文档中核对；参数细节以
> `$NEUWARE_HOME/include/cnrt.h` 为准，尤其注意带 `_v2` / `_Ex` 后缀的版本差异。

## 目录

1. [初始化与上下文](#1-初始化与上下文)
2. [设备管理](#2-设备管理)
3. [内存管理](#3-内存管理)
4. [同步与异步拷贝](#4-同步与异步拷贝)
5. [Queue](#5-queue)
6. [Notifier](#6-notifier)
7. [错误处理](#7-错误处理)
8. [多设备与多线程](#8-多设备与多线程)
9. [TaskTopo：CUDA Graph 的对应物](#9-tasktopocuda-graph-的对应物)
10. [CNDrv 驱动 API](#10-cndrv-驱动-api)
11. [环境变量与调试](#11-环境变量与调试)
12. [CUDA 对照代码](#12-cuda-对照代码)

---

## 1. 初始化与上下文

### 1.1 CNRT 是隐式初始化

CNRT 不需要 `cnrtInit()`。第一次调用任意 CNRT 接口时，运行时会：

1. 初始化 `cndrv`；
2. 创建（或复用）一个 **Shared Context**；
3. 把当前线程绑定到这个 Context。

因此最小主机程序可以直接：

```cpp
#include <cnrt.h>

int main() {
  unsigned int dev_count = 0;
  CNRT_CHECK(cnrtGetDeviceCount(&dev_count));
  CNRT_CHECK(cnrtSetDevice(0));
  // ...
}
```

### 1.2 Shared Context 的含义

- 同一进程内，同一设备上的 CNRT 调用默认共享一个 Context。
- `cnrtDeviceReset()` 会销毁当前线程 Shared Context 下的资源（Queue、内存、Module 等）。
- 如果混用 CNDrv，显式创建的 Context 与 CNRT Shared Context 不是同一个；不要交叉使用对方创建的资源。
- 多线程下，每个线程第一次调用 CNRT 时会绑定到该设备上的 Shared Context（具体行为以版本文档为准）；需要隔离时用 CNDrv 显式 Context。

### 1.3 初始化检查顺序

```cpp
cnrtGetDeviceCount(&n);       // 1. 有没有设备
cnrtSetDevice(0);             // 2. 选中设备
cnrtDeviceGetAttribute(...);  // 3. 查属性
cnrtQueueCreate(&queue);      // 4. 建队列
```

如果 `cnrtGetDeviceCount` 返回 0，先查驱动和 `cnmon`，不要继续。

---

## 2. 设备管理

| 接口 | 作用 | 备注 |
|---|---|---|
| `cnrtGetDeviceCount(unsigned int *)` | 设备数 | |
| `cnrtSetDevice(int)` | 设置当前线程使用的设备 | 不返回错误上下文时可继续用 `cnrtGetDevice` 确认 |
| `cnrtGetDevice(int *)` | 获取当前设备 | |
| `cnrtDeviceReset()` | 重置当前设备 | 会销毁该 Context 下资源 |
| `cnrtSyncDevice()` | 等待设备上所有 Queue | 粗粒度同步，性能调试时避免 |
| `cnrtDeviceGetAttribute(...)` | 查询属性 | 枚举和参数查头文件 |
| `cnrtDeviceGetPCISlot` / `cnrtDeviceGetNUMANodeId` 等 | 拓扑信息 | 多卡绑核时用 |

**不要**用设备属性推断片上容量；容量用编译宏 `__MLU_NRAM_SIZE__` 等（单位 KB）。

```cpp
int dev = 0;
CNRT_CHECK(cnrtGetDevice(&dev));
```

### 2.1 设备属性中值得记录的值

- 设备型号 / 芯片型号
- Cluster 数
- 每 Cluster 的 Core 数（与 `coreDim` 对应）
- 显存大小
- 驱动/固件版本

这些信息优先从 `cnmon info` 获取，CNRT 属性作为程序内自检。

---

## 3. 内存管理

### 3.1 设备内存

```cpp
void *d_ptr = nullptr;
CNRT_CHECK(cnrtMalloc(&d_ptr, bytes));      // 第一个参数是 void**
// ...
CNRT_CHECK(cnrtFree(d_ptr));
```

规则：

- `cnrtMalloc` 的返回值必须检查；申请失败不会抛异常。
- 分配大小建议按 512B 对齐（性能），至少按元素类型对齐。
- 同一块内存不要重复 `cnrtFree`。
- 设备内存不会自动清零；需要零值就显式写。

### 3.2 页锁定主机内存

```cpp
void *h_ptr = nullptr;
CNRT_CHECK(cnrtHostMalloc(&h_ptr, bytes));
CNRT_CHECK(cnrtFreeHost(h_ptr));
```

用于高频主机↔设备拷贝（异步拷贝要求主机内存页锁定，否则可能退化为同步或失败）。

### 3.3 符号内存

```cpp
CNRT_CHECK(cnrtMemcpyToSymbol(symbol, src, bytes, offset, dir));
CNRT_CHECK(cnrtMemcpyFromSymbol(dst, symbol, bytes, offset, dir));
```

用于 `__mlu_device__` 全局变量。symbol 的取法查头文件/文档（通常是变量名或 `cnrtSymbol_t`）。

### 3.4 没有确认的接口

- `cnrtMemset`：本次核对的文档中没有列出。设备侧用 `__bang_write_zero`，或主机侧先准备缓冲区再拷贝；如果目标版本确实有，再使用。
- `cudaMallocManaged` 的 drop-in 等价物：没有。CNRT 的 VMM（`cnrtMmap` / `cnMemCreate` / `cnMemAddressReserve` 等）是另一套模型，统一内存语义不等价；CE 平台还需要考虑缓存一致性。

---

## 4. 同步与异步拷贝

### 4.1 两个函数的签名不同

```cpp
// 同步
cnrtRet_t cnrtMemcpy(void *dst, const void *src, size_t size, cnrtMemcpyKind_t kind);

// 异步：queue 在 kind 之前
cnrtRet_t cnrtMemcpyAsync(void *dst, const void *src, size_t size,
                          cnrtQueue_t queue, cnrtMemcpyKind_t kind);
```

**最常见的移植 bug**：把 `cudaMemcpyAsync(dst, src, size, kind, stream)` 的参数顺序直接照搬，结果把 Queue 句柄当成 kind 传进去。编译可能通过（类型转换），运行时行为错误。

### 4.2 拷贝方向

| 枚举 | 方向 |
|---|---|
| `cnrtMemcpyHostToDev` | 主机 → 设备 |
| `cnrtMemcpyDevToHost` | 设备 → 主机 |
| `cnrtMemcpyDevToDev` | 设备 → 设备（同设备） |
| `cnrtMemcpyPeerToPeer` / 相关变体 | 跨设备 |

名称以 `cnrt.h` 为准；有的版本用 `cnrtMemcpyHostToDevice` 风格。

### 4.3 同步 vs 异步

| 场景 | 用法 |
|---|---|
| 一次性初始化数据 | `cnrtMemcpy` |
| 流水线中重叠拷贝与计算 | `cnrtMemcpyAsync` + Queue |
| 取结果前 | `cnrtQueueSync(queue)` |

异步拷贝之后：

- 同一 Queue 中的后续任务天然有序，不需要额外同步。
- 换到另一个 Queue 使用数据时，需要 `cnrtQueueWaitNotifier`。
- 主机侧直接读设备内存（不通过 CNRT）是非法的。

### 4.4 2D / 3D 拷贝

```cpp
cnrtMemcpy2D(...);
cnrtMemcpy3D(...);
```

用于带 pitch 的图像/张量。参数结构（pitch、height、depth）与 `cudaMemcpy2D/3D` 不同，必须查头文件；不要按 CUDA 的参数顺序猜。

---

## 5. Queue

### 5.1 基本用法

```cpp
cnrtQueue_t queue = nullptr;
CNRT_CHECK(cnrtQueueCreate(&queue));
// ... 启动 kernel、拷贝
CNRT_CHECK(cnrtQueueSync(queue));
CNRT_CHECK(cnrtQueueDestroy(queue));
```

### 5.2 语义

- Queue 内任务**顺序执行**。
- 不同 Queue 之间**没有隐式顺序**；需要显式依赖（notifier）。
- 默认 Queue：句柄传 `0` 或 `NULL`；每个设备、每个主机线程一个；由运行时管理，**不能** `cnrtQueueDestroy`。
- `cnrtQueueQuery` 完成返回 `cnrtSuccess`，未完成返回 `cnrtErrorNotReady`。

### 5.3 多 Queue 的正确姿势

```cpp
cnrtQueue_t q1, q2;
cnrtNotifier_t ev;
CNRT_CHECK(cnrtQueueCreate(&q1));
CNRT_CHECK(cnrtQueueCreate(&q2));
CNRT_CHECK(cnrtNotifierCreate(&ev));

// q1 上生产数据
produce<<<dim, cnrtFuncTypeBlock, q1>>>(d_data);
CNRT_CHECK(cnrtPlaceNotifier(ev, q1));

// q2 等待 q1 的事件
CNRT_CHECK(cnrtQueueWaitNotifier(ev, q2, 0));
consume<<<dim, cnrtFuncTypeBlock, q2>>>(d_data);

CNRT_CHECK(cnrtQueueSync(q2));
```

> `cnrtQueueWaitNotifier` 的第三个参数（flags/超时）签名以版本为准；有的版本是 `(notifier, queue, flags)`。

### 5.4 性能提示

- 不要每个算子建一个 Queue；Queue 有创建/销毁开销。
- 计算与拷贝重叠时，至少两个 Queue + notifier。
- 大量小任务可以合并，或用 TaskTopo 降低提交开销。

---

## 6. Notifier

### 6.1 接口

| 接口 | 作用 |
|---|---|
| `cnrtNotifierCreate(cnrtNotifier_t *)` | 创建 |
| `cnrtNotifierCreateWithFlags(...)` | 带 flags 创建 |
| `cnrtNotifierDestroy(cnrtNotifier_t)` | 销毁 |
| `cnrtPlaceNotifier(cnrtNotifier_t, cnrtQueue_t)` | 在 Queue 中记录事件 |
| `cnrtWaitNotifier(cnrtNotifier_t)` | 主机线程阻塞等待 |
| `cnrtQueryNotifier(cnrtNotifier_t)` | 查询是否完成 |
| `cnrtQueueWaitNotifier(cnrtNotifier_t, cnrtQueue_t, ...)` | Queue 等待事件 |
| `cnrtNotifierElapsedTime(start, end, float *)` | 计时（文档：毫秒） |
| `cnrtNotifierDuration(start, end, float *)` | 计时（官方样例按微秒使用） |

### 6.2 计时单位要注意

同一份官方材料里，`cnrtNotifierElapsedTime` 的说明是毫秒，而 `cnrtNotifierDuration` 的示例把结果除以 1000 当作毫秒打印（即按微秒理解）。**不要混用**。选一个接口，在目标机上用 `sleep` 或已知耗时的 kernel 校准单位后再写进代码。

### 6.3 计时模板

```cpp
cnrtNotifier_t start, end;
CNRT_CHECK(cnrtNotifierCreate(&start));
CNRT_CHECK(cnrtNotifierCreate(&end));

CNRT_CHECK(cnrtPlaceNotifier(start, queue));
kernel<<<dim, cnrtFuncTypeBlock, queue>>>(...);
CNRT_CHECK(cnrtPlaceNotifier(end, queue));
CNRT_CHECK(cnrtQueueSync(queue));

float ms = 0.0f;
CNRT_CHECK(cnrtNotifierElapsedTime(start, end, &ms));
printf("kernel: %.3f ms\n", ms);

CNRT_CHECK(cnrtNotifierDestroy(start));
CNRT_CHECK(cnrtNotifierDestroy(end));
```

注意：notifier 测量的是 Queue 中两端之间任务的 GPU 时间，不包含主机侧提交开销。

### 6.4 跨进程

`cnrtIpcGetNotifierHandle` / `cnrtIpcOpenNotifierHandle` 用于跨进程同步；使用前确认版本支持和权限。

---

## 7. 错误处理

### 7.1 返回值

```cpp
cnrtRet_t ret = cnrtMalloc(&p, bytes);
if (ret != cnrtSuccess) {
  fprintf(stderr, "cnrtMalloc failed: %d\n", (int)ret);
  // 清理并返回错误
}
```

### 7.2 官方样式的宏

```cpp
#define CNRT_CHECK(expr)                                                     \
  do {                                                                       \
    cnrtRet_t _ret = (expr);                                                 \
    if (_ret != cnrtSuccess) {                                               \
      fprintf(stderr, "[CNRT] %s:%d %s -> %d\n", __FILE__, __LINE__, #expr,   \
              (int)_ret);                                                    \
      exit(EXIT_FAILURE);                                                    \
    }                                                                        \
  } while (0)
```

生产代码不要 `exit`；把错误码向上传，或转成项目自己的错误类型。

### 7.3 异步错误的坑

- `<<<>>>` 启动错误可能延迟到同步时才报告。
- 每次 `cnrtQueueSync` / `cnrtSyncDevice` 后检查 `cnrtGetLastError()`。
- Kernel 内部越界/非法访问可能表现为结果错误、进程崩溃或设备异常，不一定有清晰错误码；配合 CNGDB 和边界检查。

### 7.4 错误码

| 值 | 含义 |
|---|---|
| `cnrtSuccess` | 成功 |
| `cnrtErrorNotReady` | 未就绪（`cnrtQueueQuery` 常用） |
| 其他 | 查 `cnrt.h` 的 `cnrtRet_t` 枚举 |

不要打印“未知错误”就结束；把数值和调用点一起记录下来。

---

## 8. 多设备与多线程

### 8.1 多设备

- 每个线程调用 `cnrtSetDevice(dev)` 后，后续 CNRT 调用作用于该设备。
- 设备内存不跨设备直接访问；需要 P2P 拷贝或经过主机。
- 多设备并发时，每设备独立 Queue。

### 8.2 多线程

- 每个线程独立 `cnrtSetDevice`、独立 Queue。
- 不要跨线程共享同一个 Queue（除非明确加锁且有性能理由）。
- 不要依赖“全局最后一个错误”跨线程；错误状态是线程相关的。

### 8.3 进程级资源

- `cnrtDeviceReset()` 是重量级操作，只在进程退出或彻底重置时用。
- 正常情况下 `cnrtFree` / `cnrtQueueDestroy` / `cnrtNotifierDestroy` 成对。

---

## 9. TaskTopo：CUDA Graph 的对应物

CUDA Graph 把一串 kernel/拷贝录制下来，一次提交，降低 CPU 提交开销。CNRT 的对应机制是 **TaskTopo / QueueCapture**（文档第 6.5.14 节附近）。

概念对应：

| CUDA | CNRT |
|---|---|
| `cudaGraphCreate` | 创建 TaskTopo |
| `cudaGraphAddKernelNode` | 添加 Task 节点 |
| `cudaGraphInstantiate` | 实例化 |
| `cudaGraphLaunch` | 启动 |
| Stream capture | QueueCapture |

**不要照搬 CUDA Graph 的 API 名**。具体函数名、节点类型、依赖表达方式以目标版本 CNRT 文档为准；在没确认之前，用普通 Queue 提交保证正确性。

适用场景：固定 shape、反复执行的推理图；小 kernel 很多、CPU 提交成为瓶颈时收益明显。

---

## 10. CNDrv 驱动 API

CNRT 是运行时层；CNDrv 是更底层的驱动层。需要显式 Context、Module、底层内存/事件管理时使用。

差异：

| 项目 | CNRT | CNDrv |
|---|---|---|
| 初始化 | 隐式 | 显式 `cnInit()` |
| 上下文 | Shared Context 自动管理 | 显式创建/绑定 Context |
| 函数加载 | 不需要 | `cnModuleLoadData` 等 |
| 适用 | 大多数应用 | 框架、需要精细控制的场景 |

不要在同一份资源上混用两层：CNRT 分配的指针不要传给 CNDrv 的释放接口，反之亦然。

CNDrv 的错误码用 `cnGetErrorString` 转字符串。

---

## 11. 环境变量与调试

常见（以版本为准，不要假设全部存在）：

| 变量 | 作用 |
|---|---|
| `NEUWARE_HOME` | CNToolkit 安装根目录，通常 `/usr/local/neuware` |
| `LD_LIBRARY_PATH` | 需要包含 `$NEUWARE_HOME/lib64` |
| `CN_CORE_DUMP_ENABLE` / `CN_CORE_DUMP_PATH` 等 | 设备侧 core dump（名称查 CNGDB 手册） |
| CNRT/CNNL 日志变量 | 查对应版本文档 |

调试顺序：

```bash
cnmon info                                   # 设备是否正常
cncc --version                               # 工具链版本
ldd ./your_binary | grep -E 'cnrt|cnnl'     # 链接的是哪套库
cnperf-cli timechart ...                     # 运行时间线
cngdb ./your_binary                          # 源码级调试
```

---

## 12. CUDA 对照代码

### 12.1 初始化 + 分配 + 拷贝 + 启动 + 回收

CUDA：

```cpp
cudaSetDevice(0);
float *d_in, *d_out;
cudaMalloc(&d_in, bytes);
cudaMalloc(&d_out, bytes);
cudaMemcpy(d_in, h_in, bytes, cudaMemcpyHostToDevice);
kernel<<<grid, block, 0, stream>>>(d_in, d_out, n);
cudaStreamSynchronize(stream);
cudaMemcpy(h_out, d_out, bytes, cudaMemcpyDeviceToHost);
cudaFree(d_in);
cudaFree(d_out);
```

MLU：

```cpp
CNRT_CHECK(cnrtSetDevice(0));
float *d_in = nullptr, *d_out = nullptr;
CNRT_CHECK(cnrtMalloc((void **)&d_in, bytes));
CNRT_CHECK(cnrtMalloc((void **)&d_out, bytes));
CNRT_CHECK(cnrtMemcpy(d_in, h_in, bytes, cnrtMemcpyHostToDev));

cnrtQueue_t queue = nullptr;
CNRT_CHECK(cnrtQueueCreate(&queue));
cnrtDim3_t dim = {task_num, 1, 1};
kernel<<<dim, cnrtFuncTypeBlock, queue>>>(d_in, d_out, n);
CNRT_CHECK(cnrtQueueSync(queue));

CNRT_CHECK(cnrtMemcpy(h_out, d_out, bytes, cnrtMemcpyDevToHost));
CNRT_CHECK(cnrtFree(d_in));
CNRT_CHECK(cnrtFree(d_out));
CNRT_CHECK(cnrtQueueDestroy(queue));
```

### 12.2 异步拷贝 + 事件

CUDA：

```cpp
cudaMemcpyAsync(d_in, h_in, bytes, cudaMemcpyHostToDevice, stream);
cudaEventRecord(ev, stream);
kernel<<<grid, block, 0, stream>>>(d_in, d_out, n);
cudaEventSynchronize(ev);
```

MLU：

```cpp
CNRT_CHECK(cnrtMemcpyAsync(d_in, h_in, bytes, queue, cnrtMemcpyHostToDev));
CNRT_CHECK(cnrtPlaceNotifier(ev, queue));
kernel<<<dim, cnrtFuncTypeBlock, queue>>>(d_in, d_out, n);
CNRT_CHECK(cnrtWaitNotifier(ev));
```

### 12.3 转换速查

| CUDA | CNRT | 陷阱 |
|---|---|---|
| `cudaMalloc(&p, n)` | `cnrtMalloc(&p, n)` | 参数都是 `void**` |
| `cudaMemcpy(d,s,n,k)` | `cnrtMemcpy(d,s,n,kind)` | 一致 |
| `cudaMemcpyAsync(d,s,n,k,st)` | `cnrtMemcpyAsync(d,s,n,queue,kind)` | **kind 与 queue 顺序相反** |
| `cudaStreamSynchronize(st)` | `cnrtQueueSync(queue)` | |
| `cudaStreamDestroy(st)` | `cnrtQueueDestroy(queue)` | 默认 Queue 不能销毁 |
| `cudaEventRecord(ev, st)` | `cnrtPlaceNotifier(ev, queue)` | |
| `cudaEventSynchronize(ev)` | `cnrtWaitNotifier(ev)` | |
| `cudaEventElapsedTime(&ms,a,b)` | `cnrtNotifierElapsedTime(a,b,&t)` | 单位需校准 |
| `cudaDeviceSynchronize()` | `cnrtSyncDevice()` | 粗粒度 |
| `cudaGetLastError()` | `cnrtGetLastError()` | |
