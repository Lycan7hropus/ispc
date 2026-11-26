#!/usr/bin/env bash
# PROBE branch only: runs the T0 noise probe instead of the adapter.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$2"
export PATH="${BENCH_LLVM:-/usr/lib/llvm-20/bin}:$PATH"
exec python3 "$HERE/scripts/builtins_lab/probe.py" "$(realpath "$1")" "$(realpath "$2")"
