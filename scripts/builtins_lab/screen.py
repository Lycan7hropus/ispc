#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""T0: seconds-scale standalone kernel screen. Never accepts a builtin patch."""
import argparse
import json
import os
from pathlib import Path
import platform
import random
import re
import shutil
import statistics
import subprocess
import time

import run as runner


# Estimator defaults: ~4.8 s of timing per case, ~20 s per screen with build and bootstrap.
# Short batches matter: on the WSL2 bench host the clock drifts within milliseconds, so only
# adjacent ~0.1 ms batches see the same frequency (2 ms batches gave +/-2% run-level bias).
DEFAULT_PAIRS = 1200
DEFAULT_REPS = 20
DEFAULT_BATCH_MS = 0.1
TRIM = 0.2
BOOTSTRAP_RESAMPLES = 2000
NOISE_FLOOR = 0.005  # never call a difference below 0.5%, whatever the A/A control says


def trimmed_mean(values, trim=TRIM):
    ordered = sorted(values)
    cut = int(len(ordered) * trim)
    kept = ordered[cut:len(ordered) - cut] or ordered
    return sum(kept) / len(kept)


def bootstrap_ci(values, trim=TRIM, resamples=BOOTSTRAP_RESAMPLES, seed=0x15bc):
    """Percentile bootstrap 95% CI of the trimmed mean (pairs resampled with replacement)."""
    rng = random.Random(seed)
    estimates = sorted(trimmed_mean(rng.choices(values, k=len(values)), trim) for _ in range(resamples))
    return [estimates[int(0.025 * resamples)], estimates[int(0.975 * resamples) - 1]]


def check_ratios(ratios):
    if not ratios or any(not 0 < value < float('inf') for value in ratios):
        raise ValueError('invalid paired ratios')


def classify(ci, threshold=NOISE_FLOOR):
    """Call a direction only when the whole CI lies beyond the noise threshold."""
    check_ratios(ci)
    if not 0 <= threshold < 1:
        raise ValueError('noise threshold must be in [0, 1)')
    low, high = ci
    if high < 1 - threshold:
        return 'promising_for_context_check'
    if low > 1 + threshold:
        return 'slower_in_this_screen'
    return 'unclear'


def summarize(ratios, threshold=NOISE_FLOOR):
    """Per-pair candidate/baseline ratios -> robust point estimate, CI and verdict."""
    check_ratios(ratios)
    ci = bootstrap_ci(ratios)
    return dict(median_ratio=statistics.median(ratios), trimmed_mean_ratio=trimmed_mean(ratios), ci95=ci,
                observed_ratio_range=[min(ratios), max(ratios)], noise_threshold=threshold,
                screen_status=classify(ci, threshold))


BODY_OPS = {'vmovdqu', 'vmovdqa', 'vpbroadcastq', 'vpcmpeqq', 'vpand', 'vpxor',
            'vpor', 'vptest', 'vmovmskpd', 'vpmovmskb', 'vpermq', 'cmpl', 'cmpq',
            'testl', 'testq', 'movq', 'sete', 'setz', 'movzbl', 'xorl', 'andl', 'orl'}
BODY_REGISTER = re.compile(r'%(?:(?:xmm|ymm)(?:[0-9]|1[0-5])|rax|eax|al|r(?:9|10|11)d?)$')
BODY_MEMORY = re.compile(r'(0|8|16|24|32|40|48|56)?\(%rdi\)$')


def validate_body(body):
    # Narrow trusted-input dialect, not a sandbox against hostile assembler.
    lines = []
    for original in body.splitlines():
        line = original.split('#', 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or parts[0] not in BODY_OPS:
            raise ValueError('body opcode/directive/control flow not allowed: ' + line)
        operands = [value.strip() for value in parts[1].split(',')]
        if not 1 <= len(operands) <= 4:
            raise ValueError('invalid body operands')
        for index, operand in enumerate(operands):
            if BODY_REGISTER.fullmatch(operand) or re.fullmatch(r'\$(?:0x[0-9a-fA-F]+|[0-9]+)', operand):
                continue
            memory = BODY_MEMORY.fullmatch(operand)
            if memory and index == 0:
                size = 8 if parts[0] in {'vpbroadcastq', 'cmpq', 'testq', 'movq'} else 4 if parts[0] in {'cmpl', 'testl'} else 32
                if int(memory.group(1) or 0) + size <= 64:
                    continue
            raise ValueError('body touches frame state, writes memory, or has invalid operand: ' + operand)
        if not BODY_REGISTER.fullmatch(operands[-1]):
            raise ValueError('body destination must be a scratch register')
        lines.append(line)
    if not lines or len(lines) > 64:
        raise ValueError('body must contain 1..64 instructions')
    return '\n'.join(lines) + '\n'



MIXED_OPS = {'andb', 'cmpq', 'movzbl', 'sete', 'vblendpd', 'vblendvpd',
             'vextracti128', 'vmovq', 'vpbroadcastq', 'vpermpd', 'vpermq',
             'vpextrq', 'vpmovsxdq', 'vptest', 'vpxor', 'vxorpd', 'setb',
             'vpackssdw', 'vpcmpeqq', 'vtestps'}
MIXED_REGISTER = re.compile(r'%(?:(?:xmm|ymm)(?:[0-9]|1[0-5])|rax|eax|al|r(?:10|11)(?:d|b)?)$')


def validate_mixed_body(body):
    """Register-only dialect: body cannot change first-active value or framing."""
    lines = []
    for original in body.splitlines():
        line = original.split('#', 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or parts[0] not in MIXED_OPS:
            raise ValueError('mixed body opcode/directive/control flow not allowed: ' + line)
        operands = [v.strip() for v in parts[1].split(',')]
        if not 1 <= len(operands) <= 4:
            raise ValueError('invalid mixed body operands')
        for operand in operands:
            if not (MIXED_REGISTER.fullmatch(operand) or re.fullmatch(r'\$(?:0x[0-9a-fA-F]+|[0-9]+)', operand)):
                raise ValueError('mixed body touches memory or frame state: ' + operand)
        if not MIXED_REGISTER.fullmatch(operands[-1]):
            raise ValueError('mixed body destination must be scratch register')
        lines.append(line)
    if not lines or len(lines) > 64:
        raise ValueError('mixed body must contain 1..64 instructions')
    return '\n'.join(lines) + '\n'


# Reviewed T0 fixtures. Each harness owns its oracle, ABI and case names.
FIXTURES = {
    'all-on': dict(name='reduce_equal_i64_all_on_v1', harness='screen_kernel.cpp', frame='screen_frame.S',
                   body=validate_body, body_mode={False, True}, cpu_flags={'avx2', 'rdtscp'}, build_flags=(),
                   scope='Independent all-on eight-lane i64 oracle with disjoint buffers; no mixed masks or ISPC integration.'),
    'mixed-mask': dict(name='reduce_equal_i64_proper_partial_v1', harness='screen_mixed_kernel.cpp',
                       frame='screen_mixed_frame.S', body=validate_mixed_body, body_mode={True},
                       cpu_flags={'avx2', 'rdtscp'}, build_flags=(),
                       scope='Independent proper partial sign-mask eight-lane i64 oracle, fully accessible disjoint buffers; excludes masks0/255, inactive poison and ISPC integration.'),
    'popcnt-i64': dict(name='popcnt_i64_all_on_v1', harness='screen_popcnt_kernel.cpp', frame=None, body=None,
                       body_mode={False}, cpu_flags={'avx2', 'rdtscp', 'popcnt'}, build_flags=('-mpopcnt',),
                       scope='Independent bitwise all-on eight-lane i64 -> i32 popcnt oracle (every lane x bit, every count 0..64, '
                             'nibble/byte boundary patterns) with guarded disjoint buffers; no masks or ISPC integration.'),
    'popcnt-i64-masks': dict(name='popcnt_i64_masks_v1', harness='screen_popcnt_masks_kernel.cpp', frame=None,
                             body=None, body_mode={False}, cpu_flags={'avx2', 'rdtscp', 'popcnt'},
                             build_flags=('-mpopcnt',), cases=9,
                             scope='Independent bit-loop oracle for eight-lane popcnt(int64) -> int32 under ISPC masks: '
                                   'runtime masks (all 256 lane masks; all-on/even/odd/sparse/random/off timed), '
                                   'compile-time even mask, dependent chain; inactive lanes must be 0; mask lanes are '
                                   '0/-1 (ISPC avx2 representation). No ISPC integration.'),
}


def screen(baseline, candidate, cxx, output, cpu, groups=32, pairs=DEFAULT_PAIRS, batch_ms=DEFAULT_BATCH_MS,
           body_mode=False, fixture='all-on', reps=DEFAULT_REPS, noise_threshold=NOISE_FLOOR):

    started = time.monotonic()
    if fixture not in FIXTURES:
        raise ValueError('unknown fixture: ' + str(fixture))
    spec = FIXTURES[fixture]
    if body_mode not in spec['body_mode']:
        raise ValueError(f"{fixture} fixture {'does not support' if body_mode else 'requires'} body mode")
    if cpu not in os.sched_getaffinity(0):
        raise ValueError('CPU unavailable')
    if platform.machine() != 'x86_64':
        raise ValueError('initial T0 fixture requires x86-64')
    flags = Path('/proc/cpuinfo').read_text().split('flags', 1)[-1].split('\n', 1)[0].split()
    if not spec['cpu_flags'] <= set(flags):
        raise ValueError(f"{' and '.join(sorted(spec['cpu_flags'])).upper()} required by {fixture} fixture")
    if not 1 <= groups <= 65536 or not 3 <= pairs <= 4000 or not 0.02 <= batch_ms <= 50 or not 1 <= reps <= 101:
        raise ValueError('groups 1..65536, pairs 3..4000, batch-ms 0.02..50, reps 1..101 required')
    if not NOISE_FLOOR <= noise_threshold < 0.5:
        raise ValueError(f'noise threshold must be in [{NOISE_FLOOR}, 0.5)')
    # Timing budget: cases x pairs x reps x 2 sides x batch; slower candidates take longer.
    planned_seconds = spec.get('cases', 3) * pairs * reps * 2 * batch_ms / 1000
    compiler = Path(shutil.which(str(cxx)) or str(cxx)).absolute()
    if not compiler.is_file():
        raise ValueError('C++ compiler not found')
    sources = {label: Path(path).absolute() for label, path in [('baseline', baseline), ('candidate', candidate)]}
    suffixes = ('.inc',) if body_mode else ('.S', '.s', '.cpp', '.so')
    if any(p.suffix not in suffixes or not p.is_file() for p in sources.values()):
        raise ValueError('body mode requires .inc; kernel mode requires .S/.s/.cpp/.so')
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status='running', level='T0', fixture=spec['name'],
                  cpu=cpu, groups=groups, pairs=pairs, batch_ms=batch_ms, reps=reps,
                  estimator=dict(pair_statistic='median over reps adjacent ABBA batch couples of candidate/baseline TSC ratio',
                                 summary=f'{int(TRIM * 100)}% trimmed mean of pair ratios',
                                 ci=f'percentile bootstrap 95% ({BOOTSTRAP_RESAMPLES} resamples)',
                                 verdict='direction only when the whole CI is beyond 1 +/- noise_threshold',
                                 noise_floor=NOISE_FLOOR, planned_timing_seconds=planned_seconds),
                  noise_threshold=noise_threshold,
                  framing='mixed_common_frame_v1' if fixture == 'mixed-mask' else 'common_frame_v1' if body_mode else 'kernel_owned',
                  correctness_scope=spec['scope'],
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
            harness_name = spec['harness']
            harness = output / harness_name
            shutil.copyfile(Path(__file__).with_name(harness_name), harness)
            report['harness_sha256'] = runner.sha256(harness)
            frame = None
            if body_mode:
                frame_name = spec['frame']
                frame_path = output / frame_name
                shutil.copyfile(Path(__file__).with_name(frame_name), frame_path)
                frame = frame_path.read_text()
                if frame.count('/* BODY_INSERTION_POINT */') != 1:
                    raise ValueError('invalid common frame')
                report['frame_sha256'] = runner.sha256(frame_path)
                report['layout_limitation'] = 'Common instructions do not remove layout effects: body length can shift later addresses and branch encodings.'
            for label, source in sources.items():
                frozen = output / (label + source.suffix)
                shutil.copyfile(source, frozen)
                report['sources'][label] = dict(original=str(source), sha256=runner.sha256(frozen))
                if body_mode:
                    body = spec['body'](frozen.read_text())
                    frozen = output / (label + '.S')
                    frozen.write_text(frame.replace('/* BODY_INSERTION_POINT */', body))
                    report['sources'][label]['expanded_sha256'] = runner.sha256(frozen)
                library = output / (label + '.so')
                if source.suffix != '.so':
                    command(label + '-build', [compiler, '-shared', '-fPIC', '-O2', '-std=c++17',
                        '-mavx2', *spec['build_flags'], '-fno-vectorize', '-fno-slp-vectorize', '-Wl,-Bsymbolic',
                        frozen, '-o', library])
                report['sources'][label]['binary_sha256'] = runner.sha256(library)
            command('harness-build', [compiler, '-O2', '-std=c++17', harness, '-ldl', '-o', output / 'screen-kernel'])
        report['build_seconds'] = time.monotonic() - started
        with runner.host_access(exclusive=True):
            measured = time.monotonic()
            command('measure', ['taskset', '--cpu-list', cpu, output / 'screen-kernel',
                output / 'baseline.so', output / 'candidate.so', groups, pairs, batch_ms, 1 << 28, reps],
                30 + 8 * planned_seconds)
            report['measurement_seconds'] = time.monotonic() - measured
        result = json.loads((output / 'measure.log').read_text())
        for case in result['cases']:
            case.update(summarize([row['ratio'] for row in case['pairs']], noise_threshold))
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
    parser.add_argument('--pairs', type=int, default=DEFAULT_PAIRS, help='interleaved A/B pairs per case')
    parser.add_argument('--batch-ms', type=float, default=DEFAULT_BATCH_MS, help='target length of one timed batch')
    parser.add_argument('--reps', type=int, default=DEFAULT_REPS, help='adjacent A/B batch couples per pair; median kept')
    parser.add_argument('--noise-threshold', type=float, default=NOISE_FLOOR,
                        help='relative effect the CI must clear (bench_adapter derives it from its A/A run)')
    parser.add_argument('--body-mode', action='store_true', help='wrap .inc primitives in one immutable loop/output frame')
    parser.add_argument('--fixture', choices=tuple(FIXTURES), default='all-on')
    args = parser.parse_args()
    report = screen(args.baseline, args.candidate, args.cxx, args.output, args.cpu, args.groups, args.pairs,
                    args.batch_ms, args.body_mode, args.fixture, args.reps, args.noise_threshold)
    print(json.dumps({key: report[key] for key in ('status', 'elapsed_seconds', 'build_seconds', 'measurement_seconds')}, indent=2))
    for case in report['result']['cases']:
        low, high = case['ci95']
        print(case['name'], case['screen_status'], f"trimmed mean {case['trimmed_mean_ratio']:.4f}",
              f"CI95 {low:.4f}..{high:.4f}", f"median {case['median_ratio']:.4f}")


if __name__ == '__main__':
    main()
