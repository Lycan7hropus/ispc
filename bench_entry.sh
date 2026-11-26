#!/usr/bin/env bash
# Entry point for the ispc-lab-bench self-hosted runner (label ispc-bench).
#   bench_entry.sh TASK_DIR OUT_DIR
# Reads TASK_DIR/task.json, runs T0 (screen.py) or T1/full (evaluate.py) and
# writes OUT_DIR/result.json. Tunables (env): BENCH_CPU (2), BENCH_LLVM
# (/usr/lib/llvm-20/bin), BENCH_JOBS (12), BENCH_TIMEOUT (3600),
# BENCH_CACHE (~/.cache/ispc-lab-bench/evaluator), BENCH_BASELINE_REV (lab HEAD).
set -euo pipefail
if [ "$#" -ne 2 ]; then
  echo "usage: $0 TASK_DIR OUT_DIR" >&2
  exit 64
fi
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(realpath "$1")"
mkdir -p "$2"
OUT_DIR="$(realpath "$2")"
test -f "$TASK_DIR/task.json" || { echo "missing $TASK_DIR/task.json" >&2; exit 66; }
export PATH="${BENCH_LLVM:-/usr/lib/llvm-20/bin}:$PATH"
exec python3 "$HERE/scripts/builtins_lab/bench_adapter.py" "$TASK_DIR" "$OUT_DIR"
