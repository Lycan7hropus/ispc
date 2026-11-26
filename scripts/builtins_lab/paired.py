#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Paired-process timing protocol for T1 (evaluate.py policy "protocol": "paired").

One pair = one first-binary process and one second-binary process run back to back,
order alternating AB/BA between pairs. Each process runs every frozen case once
(--benchmark_repetitions=1, the case's own min_time). Per case, the statistic is the
20% trimmed mean of the per-pair second/first cpu_time ratios with a seeded
percentile-bootstrap 95% CI (screen.trimmed_mean / screen.bootstrap_ci).

Discovery (thresholds=None), all fixed before any timing:
  1. A/A gate: `pairs` pairs of baseline vs baseline. Every case's CI must lie inside
     [1 - min_gain, 1 + max_regression]; otherwise status aa_gate_failed, no A/B.
  2. Layout control: `pairs` pairs of baseline vs layout_baseline (the same baseline
     objects relinked with padding in front of the ISPC object). Not a gate.
  3. Per-case thresholds: gain = max(min_gain, A/A excursion, layout excursion),
     regression = max(max_regression, the same excursions); excursion = largest
     distance of a CI bound from 1.
  4. A/B: `pairs` pairs of baseline vs candidate.
Confirmation (thresholds given): a fresh A/B with discovery's frozen thresholds.

Case verdict: improvement if CI_high < 1 - gain, regression if CI_low > 1 + regression,
otherwise inconclusive. Overall: regression (any non-control case) > control_moved
(any control_cases case not inconclusive) > candidate_for_confirmation (any
improvement) > no_material_improvement.
"""
import json
import math
from pathlib import Path
import platform
import os
import fcntl
import statistics
import tempfile

import run as runner
import screen

PROTOCOL = 'paired_v1'
MIN_PAIRS = 20


def validate(job, thresholds):
    for key in ('hypothesis', 'baseline_revision', 'candidate_revision', 'filter'):
        if not isinstance(job.get(key), str) or not job[key].strip():
            raise ValueError(f'{key} is required')
    if type(job.get('pairs')) is not int or job['pairs'] < MIN_PAIRS:
        raise ValueError(f'pairs must be an integer >= {MIN_PAIRS}')
    for key in ('min_gain', 'max_regression'):
        value = job.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value < 0.5:
            raise ValueError(f'{key} must be between 0 and 0.5')
    if type(job.get('cpu')) is not int or job['cpu'] not in os.sched_getaffinity(0):
        raise ValueError('cpu must name one CPU available to this process')
    if type(job.get('timeout')) is not int or job['timeout'] < 1:
        raise ValueError('timeout must be a positive integer')
    if job.get('metric', 'cpu_time') not in ('cpu_time', 'real_time'):
        raise ValueError('metric must be cpu_time or real_time')
    cases = job.get('expected_cases')
    if not isinstance(cases, list) or not cases or len(set(cases)) != len(cases):
        raise ValueError('expected_cases must be a nonempty list of unique names')
    controls = job.get('control_cases', [])
    if not isinstance(controls, list) or not set(controls) <= set(cases):
        raise ValueError('control_cases must be a subset of expected_cases')
    if not isinstance(job.get('checks'), list) or not job['checks']:
        raise ValueError('at least one correctness check command is required')
    labels = ('baseline', 'candidate') + (() if thresholds else ('layout_baseline',))
    for label in labels:
        path = Path(job.get(label, ''))
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(f'{label} must be an absolute executable path')
    if thresholds is not None and set(thresholds) != set(cases):
        raise ValueError('frozen thresholds must cover exactly the expected cases')


def read_single(path, metric, expected):
    """One process, one repetition: every expected case exactly once, positive and finite."""
    doc = json.loads(Path(path).read_text())
    cases = {}
    for row in doc['benchmarks']:
        if row.get('error_occurred'):
            raise ValueError(f"benchmark failed: {row.get('name')}: {row.get('error_message')}")
        if row.get('run_type', 'iteration') != 'iteration':
            continue
        name = row.get('run_name', row['name'])
        value = row[metric] * runner.UNITS[row['time_unit']]
        if name in cases or not math.isfinite(value) or value <= 0:
            raise ValueError(f'duplicate or invalid measurement: {name}')
        cases[name] = value
    if set(cases) != set(expected):
        raise ValueError('benchmark cases differ from the frozen inventory')
    return cases


def run_arm(label, first, second, job, out):
    """Return {case: {'first': [s...], 'second': [s...]}} over job['pairs'] AB/BA pairs."""
    seconds = {case: dict(first=[], second=[]) for case in job['expected_cases']}
    for index in range(job['pairs']):
        order = [('first', first), ('second', second)]
        if index % 2:
            order.reverse()
        for role, binary in order:
            stem = out / f'{label}-{index:03d}-{role}'
            raw = stem.with_suffix('.json')
            runner.command([str(binary), '--benchmark_repetitions=1', '--benchmark_out_format=json',
                            f'--benchmark_out={raw}', f"--benchmark_filter={job['filter']}"],
                           stem.with_suffix('.log'), job['timeout'], job['cpu'])
            for case, value in read_single(raw, job.get('metric', 'cpu_time'), job['expected_cases']).items():
                seconds[case][role].append(value)
    return seconds


def summarize(seconds):
    ratios = [s / f for f, s in zip(seconds['first'], seconds['second'])]
    ci = screen.bootstrap_ci(ratios)
    return dict(trimmed_mean_ratio=screen.trimmed_mean(ratios), ci95=ci,
                median_ratio=statistics.median(ratios), observed_ratio_range=[min(ratios), max(ratios)],
                excursion=max(0.0, 1 - ci[0], ci[1] - 1), pairs=len(ratios))


def verdict(summary, threshold):
    low, high = summary['ci95']
    if high < 1 - threshold['gain']:
        return 'improvement'
    if low > 1 + threshold['regression']:
        return 'regression'
    return 'inconclusive'


def overall(rows, controls):
    states = {row['name']: row['status'] for row in rows}
    if any(state == 'regression' for name, state in states.items() if name not in controls):
        return 'regression'
    if any(states[name] != 'inconclusive' for name in controls):
        return 'control_moved'
    if 'improvement' in states.values():
        return 'candidate_for_confirmation'
    return 'no_material_improvement'


def experiment(job, out, thresholds=None):
    validate(job, thresholds)
    out = Path(out)
    lock_path = Path(tempfile.gettempdir()) / f'ispc-builtins-lab-{os.getuid()}.lock'
    with runner.host_access(exclusive=True), lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        labels = ('baseline', 'candidate') + (() if thresholds else ('layout_baseline',))
        report = dict(status='failed', protocol=PROTOCOL, phase='confirmation' if thresholds else 'discovery',
                      job=job, platform=platform.platform(), affinity=sorted(os.sched_getaffinity(0)),
                      binaries={label: runner.sha256(Path(job[label])) for label in labels})

        def save():
            (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')

        try:
            for i, argv in enumerate(job['checks']):
                runner.command(argv, out / f'check-{i}.log', job['timeout'], job['cpu'])
            if thresholds is None:
                gate = {}
                for arm, second in (('aa', job['baseline']), ('layout', job['layout_baseline'])):
                    data = run_arm(arm, job['baseline'], second, job, out)
                    gate[arm] = {case: summarize(data[case]) for case in job['expected_cases']}
                    report[f'{arm}_arm'] = gate[arm]
                    save()
                failed = [case for case, s in gate['aa'].items()
                          if not (1 - job['min_gain'] <= s['ci95'][0] and s['ci95'][1] <= 1 + job['max_regression'])]
                report['aa_gate'] = dict(passed=not failed, failed_cases=failed,
                                         bounds=[1 - job['min_gain'], 1 + job['max_regression']])
                if failed:
                    report['status'] = 'aa_gate_failed'
                    return report
                thresholds = {case: dict(
                    gain=max(job['min_gain'], gate['aa'][case]['excursion'], gate['layout'][case]['excursion']),
                    regression=max(job['max_regression'], gate['aa'][case]['excursion'],
                                   gate['layout'][case]['excursion']))
                    for case in job['expected_cases']}
            report['thresholds'] = thresholds
            data = run_arm('ab', job['baseline'], job['candidate'], job, out)
            rows = []
            for case in sorted(job['expected_cases']):
                summary = summarize(data[case])
                rows.append(dict(name=case, baseline_seconds=data[case]['first'],
                                 candidate_seconds=data[case]['second'], threshold=thresholds[case],
                                 status=verdict(summary, thresholds[case]),
                                 control=case in job.get('control_cases', []), **summary))
            for label in labels:
                if runner.sha256(Path(job[label])) != report['binaries'][label]:
                    raise ValueError(f'{label} binary changed during experiment')
            report.update(cases=rows, status=overall(rows, job.get('control_cases', [])))
        except Exception as error:
            report['error'] = str(error)
            raise
        finally:
            save()
    return report
