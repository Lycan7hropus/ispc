#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""T0 noise probe (scratch, not for merge): raw ABBA batch time series on the bench host."""
import json, os, random, subprocess, sys, time
from pathlib import Path
LAB = Path(__file__).resolve().parent
CXX = str(Path(os.environ.get('BENCH_LLVM', '/usr/lib/llvm-20/bin')) / 'clang++')
CPU = os.environ.get('BENCH_CPU', '2')
task_dir, out = Path(sys.argv[1]), Path(sys.argv[2])
raw = out / 'raw'; raw.mkdir(parents=True, exist_ok=True)
def sh(*a):
    subprocess.run([str(x) for x in a], check=True)
base = LAB / 'screen_examples/reduce_equal_scalar.S'
slow = task_dir / 'candidate.S'
sh(CXX, '-O2', '-std=c++17', LAB / 'probe_kernel.cpp', '-ldl', '-o', raw / 'probe')
libs = {}
for name, src in (('a1', base), ('a2', base), ('slow', slow)):
    libs[name] = raw / f'{name}.so'
    sh(CXX, '-shared', '-fPIC', '-O2', '-mavx2', '-Wl,-Bsymbolic', src, '-o', libs[name])
plan = []
for batch_us in tuple(int(v) for v in os.environ.get("PROBE_BATCHES", "100,500,2000").split(",")):
    for proc in range(4):
        plan.append((batch_us, proc, 'a1', 'a2'))
    for proc in range(2):
        plan.append((batch_us, proc, 'a1', 'slow'))
random.Random(1).shuffle(plan)
summary = []
started = time.time()
for batch_us, proc, x, y in plan:
    tag = f'{x}-{y}-b{batch_us}-p{proc}'
    t = time.time()
    with open(raw / f'{tag}.json', 'w') as f:
        subprocess.run(['taskset', '--cpu-list', CPU, raw / 'probe', libs[x], libs[y], '32', '0', str(batch_us / 1000),
                        str(1 << 28), os.environ.get("PROBE_SECONDS", "2")], stdout=f, check=True)
    summary.append(dict(tag=tag, seconds=time.time() - t))
    print(tag, round(time.time() - t, 1), flush=True)
(out / 'result.json').write_text(json.dumps(dict(task=task_dir.name, tier='probe', correct=True, measurements=[],
    aa_control='n/a', notes='T0 noise probe raw data in raw/', probe=summary, total_seconds=time.time() - started), indent=1))
