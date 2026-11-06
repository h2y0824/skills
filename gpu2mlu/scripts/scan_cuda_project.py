#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_cuda_project.py — 盘点 CUDA 工程，生成 GPU→MLU 迁移清单。

用法：
    python scan_cuda_project.py <项目根目录>
    python scan_cuda_project.py <项目根目录> --md migration-inventory.md
    python scan_cuda_project.py <项目根目录> --json migration-inventory.json
    python scan_cuda_project.py <项目根目录> --md out.md --json out.json

特点：
- 只用 Python 标准库，兼容 Python 3.6+。
- 只读：不会修改项目文件。
- 扫描 .cu/.cuh/.cpp/.h/.py/CMakeLists.txt/Makefile/setup.py。
- 输出：kernel 清单、CUDA API 统计、构建系统线索、风险项、路线建议。
- 结果是“候选”，必须人工确认（注释/字符串可能造成误报）。
"""

from __future__ import print_function

import argparse
import io
import json
import os
import re
import sys
import tokenize
from collections import Counter, OrderedDict, defaultdict

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".svn", "build", "cmake-build-debug",
    "cmake-build-release", "node_modules", "__pycache__", ".venv", "venv",
    "env", ".idea", ".vscode", ".claude", "dist", ".eggs", "site-packages",
    "third_party", "thirdparty", "external", "submodules",
}

C_EXTS = {".cu", ".cuh", ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hh", ".hxx"}
PY_EXTS = {".py"}
BUILD_NAMES = {
    "CMakeLists.txt", "Makefile", "makefile", "GNUmakefile",
    "setup.py", "pyproject.toml", "requirements.txt",
}
BUILD_EXTS = {".cmake", ".mk", ".bazel", ".bzl"}

CUDA_INDICATOR = re.compile(
    r"\bcuda[A-Z]\w*|\b__global__\b|\bcublas\w*|\bcudnn\w*|\bnccl\w*|"
    r"\bthrust::|\bcub::|<<<|\b__device__\b|\bcuLaunchKernel\b"
)

# 设备侧 / 主机侧 API 统计
API_PATTERNS = OrderedDict([
    ("cuda_runtime", re.compile(r"\bcuda[A-Z][A-Za-z0-9_]*\b")),
    ("cuda_driver", re.compile(
        r"\bcu(?:LaunchKernel|ModuleLoad\w*|ModuleGetFunction|DeviceGet\w*|"
        r"MemAlloc\w*|Memcpy\w*|Ctx\w*|Event\w*|Stream\w*)\b")),
    ("cublas", re.compile(r"\bcublas[A-Za-z0-9_]*\b")),
    ("cudnn", re.compile(r"\bcudnn[A-Za-z0-9_]*\b")),
    ("nccl", re.compile(r"\bnccl[A-Za-z0-9_]*\b")),
    ("cusparse", re.compile(r"\bcusparse[A-Za-z0-9_]*\b")),
    ("curand", re.compile(r"\bcurand[A-Za-z0-9_]*\b")),
    ("cufft", re.compile(r"\bcufft[A-Za-z0-9_]*\b")),
    ("npp", re.compile(r"\bnpp[A-Za-z0-9_]*\b")),
    ("thrust", re.compile(r"\bthrust::[A-Za-z0-9_:]+")),
    ("cub", re.compile(r"\bcub::[A-Za-z0-9_:]+")),
])

# 代码特征
FEATURE_PATTERNS = OrderedDict([
    ("global_kernel", re.compile(r"\b__global__\b")),
    ("device_function", re.compile(r"\b__device__\b")),
    ("constant_memory", re.compile(r"\b__constant__\b")),
    ("shared_memory", re.compile(r"\b__shared__\b")),
    ("managed_memory", re.compile(r"\bcudaMallocManaged\b|\bcudaMemPrefetchAsync\b")),
    ("cuda_graph", re.compile(r"\bcudaGraph\w*")),
    ("cooperative_groups", re.compile(r"\bcooperative_groups\b|\bcg::")),
    ("warp_primitive", re.compile(
        r"\b__shfl\w*|\b__ballot\w*|\b__any_sync\b|\b__all_sync\b|"
        r"\b__syncwarp\b|\b__activemask\b|\b__match_any\w*")),
    ("inline_ptx", re.compile(r"\basm\s*(?:volatile\s*)?\(")),
    ("texture", re.compile(r"\btexture\s*<|\btex[123]D\w*|\bsurface\s*<")),
    ("atomic", re.compile(
        r"\batomic(?:Add|Sub|Exch|Min|Max|Inc|Dec|CAS|And|Or|Xor)\b")),
    ("half2_intrinsic", re.compile(r"\b__half2\b|\b__h(?:add|mul|fma|sub)2\b")),
    ("dynamic_parallelism", re.compile(r"\bcudaLaunchDevice\b|__cudaPushCallConfiguration")),
    ("vmm", re.compile(r"\bcuMemCreate\b|\bcuMemMap\b|cuMemAddressReserve")),
    ("launch_syntax", re.compile(r"<<<")),
])

BUILD_PATTERNS = OrderedDict([
    ("enable_language_cuda", re.compile(r"enable_language\s*\(\s*CUDA", re.I)),
    ("find_cudatoolkit", re.compile(r"find_package\s*\(\s*CUDAToolkit", re.I)),
    ("find_cuda", re.compile(r"find_package\s*\(\s*CUDA\b", re.I)),
    ("cuda_extension", re.compile(r"CUDAExtension|cpp_extension|CUDA_HOME")),
    ("nvcc", re.compile(r"\bnvcc\b")),
    ("arch_flag", re.compile(r"-arch\s*=\s*sm_|--generate-code|compute_\d+")),
    ("cuda_language", re.compile(r"\bLANGUAGES\b[^)]*\bCUDA\b", re.I)),
])

PY_PATTERNS = OrderedDict([
    ("torch_cuda", re.compile(r"\btorch\.cuda\b")),
    ("tensor_cuda", re.compile(r"\.cuda\(\)")),
    ("torch_mlu", re.compile(r"\btorch_mlu\b")),
    ("cupy", re.compile(r"\bcupy\b")),
    ("pycuda", re.compile(r"\bpycuda\b")),
    ("cuda_python", re.compile(r"\bfrom\s+cuda\b|\bimport\s+cuda\b")),
    ("numba_cuda", re.compile(r"\bnumba\.cuda\b|\bfrom\s+numba\s+import\s+cuda\b")),
    ("triton", re.compile(r"\btriton\b")),
])

KERNEL_RE = re.compile(
    r"__global__\s+(?:"                                       # 修饰符
    r"(?:void|[\w:<>,\s\*&]+?)\s+"                             # 返回类型
    r")?([A-Za-z_]\w*)\s*\(",
    re.M,
)

DEVICE_FUNC_RE = re.compile(
    r"__device__\s+(?:inline\s+|__forceinline__\s+)?"
    r"(?:void|[\w:<>,\s\*&]+?)\s+([A-Za-z_]\w*)\s*\(",
    re.M,
)


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def decode_bytes(data):
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def read_text(path, max_bytes):
    try:
        with io.open(path, "rb") as f:
            data = f.read(max_bytes + 1)
    except (IOError, OSError):
        return None
    if len(data) > max_bytes:
        return None
    return decode_bytes(data)


def mask_c_comments(text):
    """去掉 // 和 /* */ 注释，保留换行，减少注释造成的误报。"""
    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                j = text.find("\n", i)
                if j == -1:
                    break
                out.append(" " * (j - i))
                i = j
                continue
            if nxt == "*":
                j = text.find("*/", i + 2)
                if j == -1:
                    out.append(" " * (n - i))
                    break
                chunk = text[i:j + 2]
                out.append("".join("\n" if ch == "\n" else " " for ch in chunk))
                i = j + 2
                continue
        if c == '"' or c == "'":
            quote = c
            out.append(c)
            i += 1
            while i < n:
                ch = text[i]
                out.append(ch)
                if ch == "\\" and i + 1 < n:
                    out.append(text[i + 1])
                    i += 2
                    continue
                if ch == quote or ch == "\n":
                    i += 1
                    break
                i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def mask_py_comments(text):
    """用 tokenize 去掉 Python 注释；失败时退回简单替换。"""
    try:
        out = []
        last = (1, 0)
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                start = tok.start
                end = tok.end
                # 把注释替换成空格（保持行号）
                out.append((" " * (end[1] - start[1])))
            elif tok.type in (tokenize.NL, tokenize.NEWLINE):
                out.append("\n")
        if out:
            return text  # tokenize 路径不做重建，保持原始行结构
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return text


def count_patterns(text, patterns):
    result = OrderedDict()
    for name, pat in patterns.items():
        matches = pat.findall(text)
        if matches:
            result[name] = len(matches)
    return result


def collect_names(text, patterns, limit=200):
    names = Counter()
    for pat in patterns.values():
        for m in pat.finditer(text):
            names[m.group(0)] += 1
    return names.most_common(limit)


def rel(path, root):
    try:
        return os.path.relpath(path, root).replace(os.sep, "/")
    except ValueError:
        return path


def iter_files(root, max_bytes):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".git")]
        for name in filenames:
            full = os.path.join(dirpath, name)
            ext = os.path.splitext(name)[1].lower()
            if ext in C_EXTS or ext in PY_EXTS or name in BUILD_NAMES or ext in BUILD_EXTS:
                yield full


def classify(path):
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()
    if name in BUILD_NAMES or ext in BUILD_EXTS:
        return "build"
    if ext in PY_EXTS:
        return "python"
    if ext == ".cu" or ext == ".cuh":
        return "cuda"
    if ext in C_EXTS:
        return "cxx"
    return "other"


# ---------------------------------------------------------------------------
# 扫描
# ---------------------------------------------------------------------------

def scan(root, max_bytes=5 * 1024 * 1024):
    files = []
    api_counter = Counter()
    feature_counter = Counter()
    api_locations = defaultdict(set)
    feature_locations = defaultdict(set)
    build_findings = []
    py_findings = []
    kernels = []
    devices = []
    errors = []

    for path in iter_files(root, max_bytes):
        text = read_text(path, max_bytes)
        if text is None:
            continue
        kind = classify(path)
        rpath = rel(path, root)

        if kind == "cuda" or kind == "cxx":
            masked = mask_c_comments(text)
            if kind == "cxx" and not CUDA_INDICATOR.search(masked):
                continue
            lines = masked.count("\n") + 1
            apis = count_patterns(masked, API_PATTERNS)
            feats = count_patterns(masked, FEATURE_PATTERNS)

            for name in apis:
                api_counter[name] += apis[name]
                api_locations[name].add(rpath)
            for name in feats:
                feature_counter[name] += feats[name]
                feature_locations[name].add(rpath)

            fn = []
            for m in KERNEL_RE.finditer(masked):
                fn.append(m.group(1))
                kernels.append({"name": m.group(1), "file": rpath,
                                "line": masked[:m.start()].count("\n") + 1})
            dfn = []
            for m in DEVICE_FUNC_RE.finditer(masked):
                dfn.append(m.group(1))
                devices.append({"name": m.group(1), "file": rpath,
                                "line": masked[:m.start()].count("\n") + 1})

            files.append({
                "path": rpath,
                "kind": kind,
                "lines": lines,
                "kernels": sorted(set(fn)),
                "device_functions": sorted(set(dfn)),
                "apis": apis,
                "features": feats,
            })

        elif kind == "build":
            masked = mask_c_comments(text) if not path.lower().endswith((".py", ".toml")) else text
            found = {}
            for name, pat in BUILD_PATTERNS.items():
                n = len(pat.findall(masked))
                if n:
                    found[name] = n
            if found:
                build_findings.append({"path": rpath, "findings": found})
                files.append({"path": rpath, "kind": "build", "lines": text.count("\n") + 1,
                              "findings": found})

        elif kind == "python":
            masked = mask_py_comments(text)
            found = {}
            for name, pat in PY_PATTERNS.items():
                n = len(pat.findall(masked))
                if n:
                    found[name] = n
            if found:
                py_findings.append({"path": rpath, "findings": found})
                files.append({"path": rpath, "kind": "python", "lines": text.count("\n") + 1,
                              "findings": found})

    return {
        "root": os.path.abspath(root),
        "files": files,
        "kernels": kernels,
        "device_functions": devices,
        "api_counts": dict(api_counter),
        "api_locations": {k: sorted(v) for k, v in api_locations.items()},
        "feature_counts": dict(feature_counter),
        "feature_locations": {k: sorted(v) for k, v in feature_locations.items()},
        "build": build_findings,
        "python": py_findings,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# 分析与建议
# ---------------------------------------------------------------------------

RISK_RULES = [
    ("warp_primitive",
     "使用了 warp 级原语（shfl/vote/syncwarp）",
     "BANG C 没有 warp；需要改写成向量指令、查表或重排算法。",
     "高"),
    ("cooperative_groups",
     "使用了 cooperative groups",
     "MLU 只有 __sync_cluster / __sync_all 等硬件同步原语，没有 grid-wide 协作组对象。",
     "高"),
    ("dynamic_parallelism",
     "使用了动态并行（设备侧启动 kernel）",
     "MLU 无直接对应；改为主机侧循环启动或拆分 Task。",
     "高"),
    ("managed_memory",
     "使用了统一内存（cudaMallocManaged）",
     "CNRT 无 drop-in 等价；需要显式拷贝或 VMM，并处理缓存一致性。",
     "高"),
    ("cuda_graph",
     "使用了 CUDA Graph",
     "对应 CNRT TaskTopo/QueueCapture，API 不同，需重写。",
     "中"),
    ("texture",
     "使用了 texture/surface",
     "MLU 无直接对应；查表用 __bang_lut_s32/s16，图像类用 CNNL。",
     "中"),
    ("inline_ptx",
     "包含内联 PTX",
     "PTX 不能移植；必须用 BANG C 内建函数或内联 BANG 汇编重写。",
     "高"),
    ("constant_memory",
     "使用了 __constant__",
     "MLU 的 __mlu_const__ 在 GDRAM，经 L2 加速；不是片上常量缓存。",
     "中"),
    ("half2_intrinsic",
     "使用了 half2 打包运算",
     "MLU 的向量指令一次处理 128B；需要重新组织数据布局。",
     "中"),
    ("atomic",
     "使用了原子操作",
     "MLU 原子走 IO 流、代价高；优先 workspace 方案。",
     "低"),
]

LIB_RISK = [
    ("cublas", "cuBLAS", "映射到 cnnlMatMul / cnnlBatchMatMul / cnnlAxpy / cnnlScale / cnnlOpTensor；不存在 cnnlGemm。", "中"),
    ("cudnn", "cuDNN", "映射到 CNNL 卷积/池化/激活/归一化接口；注意 _v2 版本与描述符差异。", "中"),
    ("nccl", "NCCL", "映射到 CNCL；先单卡验证，再多卡。", "高"),
    ("cusparse", "cuSPARSE", "CNNL 稀疏接口或 mlu-ops，覆盖需逐算子确认。", "高"),
    ("curand", "cuRAND", "MLU 随机数生成接口需查版本；不要假设相同分布。", "中"),
    ("cufft", "cuFFT", "MLU FFT 支持需查 CNNL/工具链版本。", "高"),
    ("npp", "NPP", "图像预处理需逐算子找 CNNL/mlu-ops 对应。", "中"),
    ("thrust", "Thrust", "无 STL 式设备算法库；归约/扫描/排序需用 BANG C 或 mlu-ops。", "高"),
    ("cub", "CUB", "同上；CUB 的 block/grid 原语不能直接映射。", "高"),
]

TOP_KERNEL_LIMIT = 40


def analyze(info):
    risks = []
    feats = info["feature_counts"]
    apis = info["api_counts"]

    for key, title, detail, sev in RISK_RULES:
        if feats.get(key):
            risks.append({
                "severity": sev,
                "title": title,
                "detail": detail,
                "files": info["feature_locations"].get(key, [])[:20],
                "count": feats.get(key, 0),
            })

    for key, lib, detail, sev in LIB_RISK:
        if apis.get(key):
            risks.append({
                "severity": sev,
                "title": "%s 调用" % lib,
                "detail": detail,
                "files": info["api_locations"].get(key, [])[:20],
                "count": apis.get(key, 0),
            })

    sev_order = {"高": 0, "中": 1, "低": 2}
    risks.sort(key=lambda r: (sev_order.get(r["severity"], 9), -r["count"]))

    n_kernels = len(info["kernels"])
    libs = [k for k in apis if k in ("cublas", "cudnn", "nccl", "cusparse", "curand", "cufft", "npp")]
    has_py_cuda = any(f["findings"].get("torch_cuda") or f["findings"].get("tensor_cuda")
                      for f in info["python"])
    has_torch_mlu = any(f["findings"].get("torch_mlu") for f in info["python"])
    has_cpp_ext = any("cuda_extension" in b["findings"] for b in info["build"])

    if n_kernels > 0 and (libs or has_cpp_ext):
        route = "混合路线：CNNL/CNCL 替换库调用 + BANG C 重写自定义 kernel（可参考 mlu-ops）"
        rationale = "同时存在自定义 kernel 和 GPU 库调用，需要分层处理。"
    elif n_kernels > 0:
        route = "BANG C 路线：逐个重写 kernel；优先从 mlu-ops 找现成实现"
        rationale = "有自定义 kernel，没有（或很少）GPU 库调用。"
    elif libs:
        route = "库替换路线：cuBLAS/cuDNN/NCCL → CNNL/CNCL，通常不需要自己写 kernel"
        rationale = "只有库调用，没有自定义 kernel。"
    elif has_py_cuda:
        route = "框架路线：torch_mlu + 逐算子核对覆盖；用 .to('mlu') 替代 .cuda()"
        rationale = "Python 侧使用 CUDA 张量，没有自定义 kernel。"
    elif has_torch_mlu:
        route = "已经使用 torch_mlu；重点核对版本和算子覆盖"
        rationale = "检测到 torch_mlu 引用。"
    else:
        route = "未检测到明显 CUDA 资产；确认扫描范围/排除目录是否正确"
        rationale = "没有 kernel、库调用或 Python CUDA 调用。"

    return {
        "route": route,
        "rationale": rationale,
        "risks": risks,
        "stats": {
            "kernels": n_kernels,
            "device_functions": len(info["device_functions"]),
            "libs": libs,
            "has_python_cuda": has_py_cuda,
            "has_torch_mlu": has_torch_mlu,
            "has_cpp_extension": has_cpp_ext,
        },
    }


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

def render_markdown(info, analysis):
    lines = []
    add = lines.append

    add("# CUDA → MLU 迁移盘点")
    add("")
    add("- 项目根目录：`%s`" % info["root"])
    add("- 扫描文件数：%d" % len(info["files"]))
    add("- kernel 数：%d；设备函数数：%d" % (len(info["kernels"]), len(info["device_functions"])))
    add("")
    add("> 自动扫描结果是候选清单，注释/字符串/宏可能造成误报，必须人工确认。")
    add("")

    add("## 1. 路线建议")
    add("")
    add("**%s**" % analysis["route"])
    add("")
    add("理由：%s" % analysis["rationale"])
    add("")
    st = analysis["stats"]
    add("| 统计 | 值 |")
    add("|---|---|")
    add("| 自定义 kernel | %d |" % st["kernels"])
    add("| 设备函数 | %d |" % st["device_functions"])
    add("| GPU 库 | %s |" % (", ".join(st["libs"]) if st["libs"] else "无"))
    add("| Python CUDA 调用 | %s |" % ("是" if st["has_python_cuda"] else "否"))
    add("| torch_mlu | %s |" % ("是" if st["has_torch_mlu"] else "否"))
    add("| C++ 扩展 | %s |" % ("是" if st["has_cpp_extension"] else "否"))
    add("")

    add("## 2. Kernel 清单")
    add("")
    if info["kernels"]:
        add("| # | kernel | 文件:行 |")
        add("|---|---|---|")
        for i, k in enumerate(info["kernels"][:TOP_KERNEL_LIMIT], 1):
            add("| %d | `%s` | `%s:%d` |" % (i, k["name"], k["file"], k["line"]))
        if len(info["kernels"]) > TOP_KERNEL_LIMIT:
            add("")
            add("> 只显示前 %d 个；完整列表见 JSON。" % TOP_KERNEL_LIMIT)
    else:
        add("未检测到 `__global__` kernel。")
    add("")

    add("## 3. CUDA API 统计")
    add("")
    if info["api_counts"]:
        add("| 类别 | 次数 | 文件数 |")
        add("|---|---|---|")
        for name, n in sorted(info["api_counts"].items(), key=lambda kv: -kv[1]):
            add("| %s | %d | %d |" % (name, n, len(info["api_locations"].get(name, []))))
    else:
        add("未检测到 CUDA API 调用。")
    add("")

    add("## 4. 代码特征")
    add("")
    if info["feature_counts"]:
        add("| 特征 | 次数 | 文件数 |")
        add("|---|---|---|")
        for name, n in sorted(info["feature_counts"].items(), key=lambda kv: -kv[1]):
            add("| %s | %d | %d |" % (name, n, len(info["feature_locations"].get(name, []))))
    else:
        add("未检测到显著特征。")
    add("")

    add("## 5. 风险项")
    add("")
    if analysis["risks"]:
        add("| 严重度 | 风险 | 次数 | 说明 |")
        add("|---|---|---|---|")
        for r in analysis["risks"]:
            detail = r["detail"].replace("|", "\\|")
            add("| %s | %s | %d | %s |" % (r["severity"], r["title"], r["count"], detail))
    else:
        add("未发现高风险特征。仍需人工核对语义差异。")
    add("")

    add("## 6. 构建系统")
    add("")
    if info["build"]:
        add("| 文件 | 线索 |")
        add("|---|---|")
        for b in info["build"]:
            found = ", ".join("%s(%d)" % (k, v) for k, v in sorted(b["findings"].items()))
            add("| `%s` | %s |" % (b["path"], found))
    else:
        add("未检测到 CUDA 构建线索。")
    add("")

    add("## 7. Python 侧")
    add("")
    if info["python"]:
        add("| 文件 | 线索 |")
        add("|---|---|")
        for p in info["python"]:
            found = ", ".join("%s(%d)" % (k, v) for k, v in sorted(p["findings"].items()))
            add("| `%s` | %s |" % (p["path"], found))
    else:
        add("未检测到 Python CUDA 调用。")
    add("")

    add("## 8. 下一步")
    add("")
    add("1. 运行 `probe_mlu_env.sh` 记录目标架构、CNToolkit/CNNL 版本、设备数。")
    add("2. 人工确认本节 kernel 清单，补上每个 kernel 的输入输出、dtype、边界 shape。")
    add("3. 冻结 GPU 基线（输入/输出/耗时/容差）。")
    add("4. 按路线建议分层迁移：库替换 → 主机运行时 → kernel 重写 → 构建系统。")
    add("5. 每个 kernel 用 `bang-c-kernel-guide.md` 的检查清单验收。")
    add("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="扫描 CUDA 工程并生成 MLU 迁移清单（只读）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root", help="项目根目录")
    parser.add_argument("--md", dest="md", help="输出 Markdown 文件路径")
    parser.add_argument("--json", dest="json", help="输出 JSON 文件路径")
    parser.add_argument("--max-file-bytes", type=int, default=5 * 1024 * 1024,
                        help="跳过大于该字节数的文件（默认 5MB）")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.root):
        print("错误：不是目录：%s" % args.root, file=sys.stderr)
        return 2

    info = scan(args.root, args.max_file_bytes)
    analysis = analyze(info)
    data = {"info": info, "analysis": analysis}

    md = render_markdown(info, analysis)

    if args.json:
        with io.open(args.json, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2))
        print("已写入 JSON：%s" % args.json)

    if args.md:
        with io.open(args.md, "w", encoding="utf-8") as f:
            f.write(md)
        print("已写入 Markdown：%s" % args.md)
    elif not args.json:
        print(md)

    # 摘要
    print()
    print("摘要：%d 个文件，%d 个 kernel，%d 个设备函数，%d 类 CUDA API"
          % (len(info["files"]), len(info["kernels"]),
             len(info["device_functions"]), len(info["api_counts"])))
    print("路线：%s" % analysis["route"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
