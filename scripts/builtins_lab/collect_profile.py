#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Retain aggregate counters, samples and provenance for a baseline workload."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import run as runner

EVENTS = 'cycles:u,instructions:u,branches:u,branch-misses:u,cache-references:u,cache-misses:u'


def counter_gaps(text):
    return [line for line in text.splitlines()
            if any(marker in line.lower() for marker in ('<not supported>', '<not counted>', 'not available'))]


def collect(perf, argv, output, workload_kind, description, timeout=180, repetitions=3, cpu=None):
    perf = Path(perf).absolute()
    if not perf.is_file() or not os.access(perf, os.X_OK):
        raise ValueError('perf must be an executable absolute path')
    if not argv or not Path(argv[0]).is_absolute() or not Path(argv[0]).is_file():
        raise ValueError('workload must begin with an absolute executable path')
    if workload_kind not in ('application', 'representative_kernel', 'microbenchmark'):
        raise ValueError('invalid workload kind')
    if not description.strip() or repetitions < 2 or timeout < 1:
        raise ValueError('describe workload/input assumptions and use >=2 stat repetitions')
    if cpu is None:
        cpu = min(os.sched_getaffinity(0))
    if cpu not in os.sched_getaffinity(0):
        raise ValueError('cpu is unavailable')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status='collecting', argv=argv, cwd=str(Path.cwd()),
                  workload_kind=workload_kind, description=description,
                  kernel=platform.release(), platform=platform.platform(),
                  affinity=sorted(os.sched_getaffinity(0)), cpu=cpu, commands=[],
                  executable_sha256=runner.sha256(Path(argv[0])),
                  perf_sha256=runner.sha256(perf), events=EVENTS,
                  limitations=['Counters cover the whole command; samples localize observed cost.',
                    'Sample attribution is statistical and may skid; an instruction sample is not proof of causality.',
                    'A microbenchmark profile does not establish application importance.',
                    'Profiler runs are diagnostic; use separate unprofiled runs for speedup decisions.'])

    def save():
        (output / 'profile.json').write_text(json.dumps(report, indent=2) + '\n')

    def stage(name, command):
        command = ['taskset', '--cpu-list', str(cpu), *[str(arg) for arg in command]]
        report['commands'].append(dict(name=name, argv=command))
        save()
        runner.execute(command, output / (name + '.log'), timeout)

    save()
    try:
        # Profiling perturbs execution and must not overlap cooperating measurements.
        with runner.host_access(exclusive=True):
            stage('perf-version', [perf, '--version'])
            stage('stat', [perf, 'stat', '-x', ';', '-r', str(repetitions),
                  '-e', EVENTS, '-o', output / 'stat.csv', '--', *argv])
            report['counter_gaps'] = counter_gaps((output / 'stat.csv').read_text())
            stage('record', [perf, 'record', '-e', 'cycles:u', '-F', '199',
                  '--call-graph', 'dwarf,8192', '-o', output / 'perf.data', '--', *argv])
            stage('hotspots', [perf, 'report', '--stdio', '--no-children',
                  '--sort', 'dso,symbol', '-i', output / 'perf.data'])
            stage('annotation', [perf, 'annotate', '--stdio', '--no-source',
                  '-i', output / 'perf.data'])
        if runner.sha256(Path(argv[0])) != report['executable_sha256']:
            raise ValueError('workload executable changed during collection')
        report['status'] = 'partial' if report['counter_gaps'] else 'collected_for_review'
        report['artifacts_sha256'] = {p.name: runner.sha256(p) for p in sorted(output.iterdir())
                                      if p.is_file() and p.name != 'profile.json'}
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--perf', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--kind', required=True, choices=('application', 'representative_kernel', 'microbenchmark'))
    parser.add_argument('--description', required=True)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--cpu', type=int, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    try:
        report = collect(args.perf, command, args.output, args.kind, args.description,
                         args.timeout, args.repetitions, args.cpu)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(report['status'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
