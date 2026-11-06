#!/usr/bin/env bash
# probe_mlu_env.sh — 只读探测寒武纪 MLU 环境
#
# 在目标 MLU 机器上运行：
#   bash probe_mlu_env.sh
#   bash probe_mlu_env.sh --json > env.json
#
# 不做任何修改：不安装、不加载驱动、不写设备。
# 所有命令都允许失败；失败项会显示为 "missing" 或 "unavailable"。

set -u
set -o pipefail

JSON=0
if [ "${1:-}" = "--json" ]; then
  JSON=1
fi

TMPDIR="${TMPDIR:-/tmp}"
WORK="$(mktemp -d "$TMPDIR/gpu2mlu-probe.XXXXXX" 2>/dev/null || echo "$TMPDIR")"
trap 'rm -rf "$WORK" 2>/dev/null' EXIT

have() { command -v "$1" >/dev/null 2>&1; }

# 运行命令并捕获 stdout+stderr，限制时间（若 timeout 可用）
run() {
  local secs="$1"; shift
  if have timeout; then
    timeout "$secs" "$@" 2>&1
  else
    "$@" 2>&1
  fi
}

first_line() {
  # 取输出的第一行非空内容
  sed -n '1{/^[[:space:]]*$/d;p;q}'
}

json_escape() {
  # 简化 JSON 转义（引号、反斜杠、换行、制表符）
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null \
    || sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | awk '{printf "%s\\n", $0}'
}

# ---------- 采集 ----------

OS_NAME="$(uname -s 2>/dev/null || echo unknown)"
OS_RELEASE="$(uname -r 2>/dev/null || echo unknown)"
OS_ARCH="$(uname -m 2>/dev/null || echo unknown)"
DISTRO="$( (grep -h '^PRETTY_NAME=' /etc/os-release 2>/dev/null || true) | head -1 | cut -d= -f2- | tr -d '"')"
[ -z "$DISTRO" ] && DISTRO="unknown"

NEUWARE="${NEUWARE_HOME:-}"
[ -z "$NEUWARE" ] && NEUWARE="/usr/local/neuware"

CNCC_PATH="$(command -v cncc 2>/dev/null || echo missing)"
CNCC_VERSION="$(if have cncc; then run 10 cncc --version | first_line; else echo missing; fi)"
CNCC_ARCH_FLAG="$(if have cncc; then run 10 cncc --help 2>&1 | grep -m1 -E -- '--bang-(mlu-)?arch' || true; else echo missing; fi)"

CNMON_PATH="$(command -v cnmon 2>/dev/null || echo missing)"
CNMON_INFO="$(if have cnmon; then run 15 cnmon info 2>&1 || echo unavailable; else echo missing; fi)"
CNMON_COUNT="$(if have cnmon; then (run 15 cnmon info 2>/dev/null | grep -ci '^Device' || true); else echo 0; fi)"

CNPERF_PATH="$(command -v cnperf-cli 2>/dev/null || echo missing)"
CNGDB_PATH="$(command -v cngdb 2>/dev/null || echo missing)"

DEV_NODES="$(ls -d /dev/cambricon* 2>/dev/null | tr '\n' ' ' || true)"
[ -z "$DEV_NODES" ] && DEV_NODES="none"

LIB_DIR="${NEUWARE}/lib64"
if [ ! -d "$LIB_DIR" ]; then
  if [ -d "${NEUWARE}/lib" ]; then LIB_DIR="${NEUWARE}/lib"; fi
fi
CORE_LIBS="$(ls "$LIB_DIR"/libcnrt.so* "$LIB_DIR"/libcndrv.so* "$LIB_DIR"/libcnnl.so* "$LIB_DIR"/libcncl.so* 2>/dev/null | sed 's#.*/##' | sort -u | tr '\n' ' ' || true)"
[ -z "$CORE_LIBS" ] && CORE_LIBS="none"

INCLUDE_DIR="${NEUWARE}/include"
HEADERS="$(ls "$INCLUDE_DIR"/bang.h "$INCLUDE_DIR"/cnrt.h "$INCLUDE_DIR"/cnnl.h "$INCLUDE_DIR"/cncl.h "$INCLUDE_DIR"/cndrv.h 2>/dev/null | sed 's#.*/##' | tr '\n' ' ' || true)"
[ -z "$HEADERS" ] && HEADERS="none"

PY=""
for c in python3 py python; do
  # Windows 上 python3/python 可能是应用商店的存根，必须实际执行判断
  if have "$c" && "$c" -c 'import sys; sys.exit(0)' >/dev/null 2>&1; then
    PY="$c"; break
  fi
done

TORCH_INFO="missing"
if [ -n "$PY" ]; then
  TORCH_INFO="$(run 20 "$PY" - <<'PYEOF' 2>&1 || echo unavailable
try:
    import torch
    info = {"torch": torch.__version__}
    try:
        import torch_mlu
        info["torch_mlu"] = getattr(torch_mlu, "__version__", "unknown")
        try:
            info["mlu_available"] = bool(torch.mlu.is_available())
        except Exception:
            pass
        try:
            info["mlu_device_count"] = int(torch.mlu.device_count())
        except Exception:
            pass
    except Exception as e:
        info["torch_mlu"] = "missing (%s: %s)" % (type(e).__name__, e)
    print(info)
except Exception as e:
    print("torch missing (%s: %s)" % (type(e).__name__, e))
PYEOF
)"
fi

ENV_VARS="$(env | grep -E '^(NEUWARE_HOME|LD_LIBRARY_PATH|PATH|CN|MLU|CNDRV|CNRT)' 2>/dev/null | sort || true)"
[ -z "$ENV_VARS" ] && ENV_VARS="none"

KERNEL_DRIVER="$(lsmod 2>/dev/null | grep -iE 'cambricon|cn_|cndrv|mlu' || true)"
[ -z "$KERNEL_DRIVER" ] && KERNEL_DRIVER="not found (or lsmod unavailable)"

# ---------- 输出 ----------

if [ "$JSON" -eq 1 ]; then
  if [ -n "$PY" ]; then
    "$PY" - "$OS_NAME" "$OS_RELEASE" "$OS_ARCH" "$DISTRO" \
      "$NEUWARE" "$CNCC_PATH" "$CNCC_VERSION" "$CNCC_ARCH_FLAG" \
      "$CNMON_PATH" "$CNMON_INFO" "$CNMON_COUNT" \
      "$CNPERF_PATH" "$CNGDB_PATH" "$DEV_NODES" \
      "$LIB_DIR" "$CORE_LIBS" "$INCLUDE_DIR" "$HEADERS" \
      "$TORCH_INFO" "$ENV_VARS" "$KERNEL_DRIVER" <<'PYEOF'
import json, sys
keys = [
    "os_name", "os_release", "os_arch", "distro",
    "neuware_home", "cncc_path", "cncc_version", "cncc_arch_flag",
    "cnmon_path", "cnmon_info", "cnmon_device_lines",
    "cnperf_path", "cngdb_path", "dev_nodes",
    "lib_dir", "core_libs", "include_dir", "headers",
    "python_runtime", "env_vars", "kernel_driver",
]
vals = sys.argv[1:]
data = dict(zip(keys, vals))
print(json.dumps(data, ensure_ascii=False, indent=2))
PYEOF
  else
    echo '{"error": "python3 not found; run without --json"}'
  fi
  exit 0
fi

echo "# MLU 环境探测报告"
echo
echo "- 采集时间: $(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || echo unknown)"
echo "- 主机: $(hostname 2>/dev/null || echo unknown)"
echo

echo "## 1. 系统"
echo
echo "| 项 | 值 |"
echo "|---|---|"
echo "| OS | ${OS_NAME} ${OS_RELEASE} |"
echo "| 发行版 | ${DISTRO} |"
echo "| 架构 | ${OS_ARCH} |"
echo "| 设备节点 | ${DEV_NODES} |"
echo "| 内核驱动 | $(printf '%s' "$KERNEL_DRIVER" | head -3 | tr '\n' ';' ) |"
echo

echo "## 2. 工具链"
echo
echo "| 项 | 值 |"
echo "|---|---|"
echo "| NEUWARE_HOME | ${NEUWARE} |"
echo "| cncc | ${CNCC_PATH} |"
echo "| cncc 版本 | ${CNCC_VERSION} |"
echo "| cncc 架构选项 | ${CNCC_ARCH_FLAG} |"
echo "| cnmon | ${CNMON_PATH} |"
echo "| cnperf-cli | ${CNPERF_PATH} |"
echo "| cngdb | ${CNGDB_PATH} |"
echo

echo "## 3. 设备"
echo
if [ "$CNMON_INFO" = "missing" ] || [ "$CNMON_INFO" = "unavailable" ]; then
  echo "\`cnmon info\` 不可用：${CNMON_INFO}"
else
  echo '```'
  printf '%s\n' "$CNMON_INFO" | head -80
  echo '```'
  echo
  echo "检测到设备行数（粗略）：${CNMON_COUNT}"
fi
echo

echo "## 4. 库与头文件"
echo
echo "| 项 | 值 |"
echo "|---|---|"
echo "| 库目录 | ${LIB_DIR} |"
echo "| 核心库 | ${CORE_LIBS} |"
echo "| 头文件目录 | ${INCLUDE_DIR} |"
echo "| 头文件 | ${HEADERS} |"
echo

echo "## 5. Python / torch_mlu"
echo
echo '```'
printf '%s\n' "$TORCH_INFO"
echo '```'
echo

echo "## 6. 环境变量"
echo
echo '```'
printf '%s\n' "$ENV_VARS"
echo '```'
echo

echo "## 7. 需要人工确认的项"
echo
echo "- [ ] 目标架构标识（用于 \`--bang-mlu-arch=\`），来源：厂商/文档/\`cnmon\`"
echo "- [ ] \`__MLU_NRAM_SIZE__\` / \`__MLU_SRAM_SIZE__\` / \`__MLU_WRAM_SIZE__\` 的实际值（编译期宏，单位 KB）"
echo "- [ ] CNNL / CNCL 版本与 \`$NEUWARE/include\` 中的接口是否匹配"
echo "- [ ] 驱动版本是否满足 mlu-ops 要求（≥ v6.0.3）"
echo "- [ ] 是否安装 torch_mlu，版本是否与 torch 匹配"
echo "- [ ] 多卡拓扑（若使用 CNCL）"
