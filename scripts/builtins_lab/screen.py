#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""T0: seconds-scale standalone kernel screen. Never accepts a builtin patch."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import time

import run as runner


def classify(ratios, margin=0.05):
    if not ratios or any(not 0 < value < float('inf') for value in ratios):
        raise ValueError('invalid paired ratios')
    if max(ratios) < 1 - margin:
        return 'promising_for_context_check'
    if min(ratios) > 1 + margin:
        return 'slower_in_this_screen'
    return 'unclear'


def screen(baseline, candidate, cxx, output, cpu, groups=32, pairs=5, batch_ms=5):
    started = time.monotonic()
    if cpu not in os.sched_getaffinity(0):
        raise ValueError('CPU unavailable')
    if platform.machine() != 'x86_64':
        raise ValueError('initial T0 fixture requires x86-64')
    flags = Path('/proc/cpuinfo').read_text().split('flags', 1)[-1].split('\n', 1)[0].split()
    if not {'avx2', 'rdtscp'} <= set(flags):
        raise ValueError('AVX2 and RDTSCP required by initial fixture')
    if not 1 <= groups <= 65536 or not 3 <= pairs <= 31 or not 1 <= batch_ms <= 50:
        raise ValueError('groups 1..65536, pairs 3..31, batch-ms 1..50 required')
    compiler = Path(shutil.which(str(cxx)) or str(cxx)).absolute()
    if not compiler.is_file():
        raise ValueError('C++ compiler not found')
    sources = {label: Path(path).absolute() for label, path in [('baseline', baseline), ('candidate', candidate)]}
    if any(p.suffix not in ('.S', '.s', '.cpp', '.so') or not p.is_file() for p in sources.values()):
        raise ValueError('provide trusted .S/.s/.cpp kernel source or prebuilt .so')
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status='running', level='T0', fixture='reduce_equal_i64_all_on_v1',
                  cpu=cpu, groups=groups, pairs=pairs, batch_ms=batch_ms,
                  correctness_scope='Independent all-on eight-lane i64 oracle; no mixed masks or ISPC integration.',
                  timing_unit='TSC reference ticks, not core cycles; wall nanoseconds also retained.',
                  limitation='Isolated out-of-line kernels/hypotheses are not proof of optimized ISPC caller behavior. No patch promotion.',
                  compiler_sha256=runner.sha256(compiler), screen_sha256=runner.sha256(Path(__file__)),
                  runner_sha256=runner.sha256(Path(runner.__file__)), sources={}, commands=[])

    def save():
        report['elapsed_seconds'] = time.monotonic() - started
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')

    def command(label, argv, timeout=30):
        argv = [str(v) for v in argv]
        report['commands'].append(argv)
        save()
        runner.execute(argv, output / (label + '.log'), timeout)

    try:
        # Compile tiny artifacts under the shared lock, never rebuild ISPC/CMake.
        with runner.host_access(exclusive=False):
            harness = output / 'screen_kernel.cpp'
            shutil.copyfile(Path(__file__).with_name('screen_kernel.cpp'), harness)
            report['harness_sha256'] = runner.sha256(harness)
            for label, source in sources.items():
                frozen = output / (label + source.suffix)
                shutil.copyfile(source, frozen)
                report['sources'][label] = dict(original=str(source), sha256=runner.sha256(frozen))
                library = output / (label + '.so')
                if source.suffix != '.so':
                    command(label + '-build', [compiler, '-shared', '-fPIC', '-O2', '-std=c++17',
                        '-mavx2', '-fno-vectorize', '-fno-slp-vectorize', '-Wl,-Bsymbolic', frozen, '-o', library])
                report['sources'][label]['binary_sha256'] = runner.sha256(library)
            command('harness-build', [compiler, '-O2', '-std=c++17', harness, '-ldl', '-o', output / 'screen-kernel'])
        report['build_seconds'] = time.monotonic() - started
        with runner.host_access(exclusive=True):
            measured = time.monotonic()
            command('measure', ['taskset', '--cpu-list', cpu, output / 'screen-kernel',
                output / 'baseline.so', output / 'candidate.so', groups, pairs, batch_ms, 1 << 28], 30)
            report['measurement_seconds'] = time.monotonic() - measured
        result = json.loads((output / 'measure.log').read_text())
        for case in result['cases']:
            ratios = [row['ratio'] for row in case['pairs']]
            case.update(median_ratio=statistics.median(ratios), observed_ratio_range=[min(ratios), max(ratios)],
                        screen_status=classify(ratios))
        report.update(status='screened_not_accepted', result=result)
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--cxx', default='clang++')
    parser.add_argument('--cpu', type=int, required=True)
    parser.add_argument('--groups', type=int, default=32)
    parser.add_argument('--pairs', type=int, default=5)
    parser.add_argument('--batch-ms', type=int, default=5)
    args = parser.parse_args()
    report = screen(args.baseline, args.candidate, args.cxx, args.output, args.cpu, args.groups, args.pairs, args.batch_ms)
    print(json.dumps({key: report[key] for key in ('status', 'elapsed_seconds', 'build_seconds', 'measurement_seconds')}, indent=2))
    for case in report['result']['cases']:
        print(case['name'], case['screen_status'], round(case['median_ratio'], 4))


if __name__ == '__main__':
    main()
