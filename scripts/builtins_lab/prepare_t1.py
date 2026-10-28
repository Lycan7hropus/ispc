#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Prepare a reviewed packet for T1 using an existing compiler cache. No timing."""

import argparse
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import evaluate
import run as runner


SKIPPED = ['full lit suite', 'family functional suite', 'VNNI inherited-target compile/runtime',
           'full evaluator discovery', 'independent confirmation', 'performance acceptance']


def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise TimeoutError('T1 preparation deadline reached')
    return value


@contextmanager
def bounded_worker(path, deadline):
    # Existing marker/cache validation precedes this; never create a new worker.
    with path.open('a') as lock:
        while True:
            delay = remaining(deadline)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                time.sleep(min(.05, delay))
        yield


class Preparation(evaluate.Evaluation):
    def __init__(self, policy, request, worker, out):
        self.started = time.monotonic()
        self.deadline = self.started + 900
        self.out = out.resolve()
        self.out.mkdir(parents=True, exist_ok=False)
        self.report = dict(status='failed', accepted=False, level='T1_preparation', commands=[], steps=[])
        self.originals = {}
        self.save()
        try:
            with runner.host_access(False, deadline=min(self.deadline, time.monotonic() + 30)):
                self.initialize(policy, request, worker)
                self.report.update(accepted=False, level='T1_preparation', skipped_T2_gates=SKIPPED,
                                   limits_seconds=dict(total=900, lock_queue=30, process=300))
                if not self.packet:
                    raise ValueError('T1 preparation requires a reviewed packet')
                for name in ('prepare_t1.py', 'focus.py'):
                    target = self.tools / name
                    shutil.copyfile(Path(__file__).with_name(name), target)
                    self.report['evaluator_sha256'][name] = runner.sha256(target)
                self.require_cache()
                self.input_hashes = self.input_identities()
                self.report['preparation_inputs_sha256'] = self.input_hashes
                remaining(self.deadline)
        except Exception as error:
            self.report.update(status='failed', error=str(error))
            self.save()
            raise
        self.save()

    def require_cache(self):
        for path in (self.home/'worker.json', self.home/'baseline.json', self.home/'baseline-ispc',
                     self.build/'CMakeCache.txt', self.build/'build.ninja'):
            if not path.is_file():
                raise ValueError('cache miss; separate baseline preparation required: ' + str(path))

    def input_identities(self):
        paths = [self.home/'worker.json', self.home/'baseline.json', self.home/'baseline-ispc',
                 self.build/'CMakeCache.txt', self.patch,
                 self.build/'benchmarks/vendor/google/benchmark/src/libbenchmark.a']
        include = self.source/'benchmarks/vendor/google/benchmark/include'
        paths += sorted(p for p in include.rglob('*') if p.is_file())
        if not include.is_dir() or len(paths) == 6:
            raise ValueError('cached benchmark headers missing')
        paths += [self.llvm/name for name in self.report['toolchain']]
        paths += [Path(p) for p in self.report['shared_libraries']]
        paths += [self.tools/name for name in self.report['evaluator_sha256']]
        for name in ('cmake', 'ninja'):
            path = shutil.which(name)
            if not path:
                raise ValueError(name + ' unavailable')
            paths.append(Path(path).resolve())
        paths.append(Path(sys.executable).resolve())
        return {str(p): runner.sha256(p) for p in paths}

    def verify_inputs(self):
        if self.input_identities() != self.input_hashes:
            raise ValueError('preparation inputs changed')
        remaining(self.deadline)

    def stage(self, label, argv, cwd=None, timeout=None, environment=None):
        if label in {'worktree', 'submodules', 'configure', 'baseline-build', 'baseline-lit'}:
            raise ValueError('cold preparation is forbidden in T1: ' + label)
        budget = min(300, timeout or self.policy['timeout'], remaining(self.deadline))
        began = time.monotonic()
        try:
            super().stage(label, argv, cwd=cwd, timeout=budget, environment=environment)
        finally:
            if self.report.get('commands'):
                self.report['commands'][-1]['elapsed_seconds'] = time.monotonic() - began
        remaining(self.deadline)

    def source_parity(self):
        for label in ('baseline', 'candidate'):
            manifest = json.loads((self.out/f'{label}-validation/fixture.json').read_text())
            if manifest['status'] != 'verified' or not manifest['runtime_verified']:
                raise ValueError('fixture oracle not verified')
            if manifest['packet_sha256'] != self.packet['sha256']:
                raise ValueError('fixture packet changed')
            for name, expected in self.packet['manifest']['sources'].items():
                directory = self.out/f'{label}-validation' if name.startswith('oracle.') else self.out/f'{label}-contexts'
                if runner.sha256(directory/name) != expected:
                    raise ValueError('fixture source differs from packet: ' + label + '/' + name)
            for path, digest in manifest['artifacts_sha256'].items():
                if runner.sha256(Path(path)) != digest:
                    raise ValueError('fixture artifact changed: ' + path)

    def restore(self):
        for name, data in self.originals.items():
            (self.source/name).write_bytes(data)
        restored = bool(self.originals) and all((self.source/name).read_bytes() == data
                                               for name, data in self.originals.items())
        self.report['source_restored'] = restored
        clean = not self.git('status', '--porcelain', '--untracked-files=normal')
        pinned = self.git('rev-parse', 'HEAD') == self.policy['baseline_revision']
        self.report['postconditions'] = dict(worker_source_restored=restored, clean=clean, pinned=pinned)
        if not clean or not pinned or (self.originals and not restored):
            raise ValueError('worker restoration failed; inspect worker before reuse')

    def emit_job(self):
        def pin(path):
            return dict(path=str(path.resolve()), sha256=runner.sha256(path))
        provenance = [self.patch, self.out/'CMakeCache.txt', self.home/'baseline-ispc', self.out/'candidate-ispc']
        provenance += [self.tools/name for name in self.report['evaluator_sha256']]
        for label in ('baseline', 'candidate'):
            provenance.append(self.out/f'{label}-validation/fixture.json')
            for directory in (self.out/f'{label}-contexts', self.out/f'{label}-validation'):
                provenance += [p for p in directory.iterdir() if p.suffix in ('.s', '.ll', '.ispc', '.cpp', '.h')]
        executables = [self.benchmark_binary(s) for s in ('baseline', 'candidate')]
        executables += [self.oracle_binary(s) for s in ('baseline', 'candidate')]
        libraries = evaluate.shared_libraries(executables)
        provenance += [Path(p) for p in libraries]
        self.report['runtime_libraries_sha256'] = libraries
        snapshot = self.out/'preparation-provenance.json'
        snapshot.write_text(json.dumps(self.report, indent=2)+'\n')
        provenance.append(snapshot)
        job = dict(schema=1, hypothesis=self.request['hypothesis'],
                   baseline=pin(self.benchmark_binary('baseline')), candidate=pin(self.benchmark_binary('candidate')),
                   checks=[pin(self.oracle_binary(s)) for s in ('baseline', 'candidate')],
                   cases=self.cases(), provenance=[pin(p) for p in sorted(set(provenance))])
        path = self.out/'focus-job.json'
        path.write_text(json.dumps(job, indent=2)+'\n')
        self.report['focus_job'] = pin(path)

    def prepare_t1(self):
        try:
            with bounded_worker(self.home/'worker.lock', min(self.deadline, time.monotonic()+30)):
                try:
                    with runner.host_access(False, deadline=min(self.deadline, time.monotonic()+30)):
                        self.require_cache()
                        self.verify_inputs()
                        self.prepare()  # Cache exists: this path cannot initialize/build a baseline.
                        self.fixtures('baseline', self.home/'baseline-ispc')
                        self.compile_candidate()
                        self.fixtures('candidate', self.out/'candidate-ispc')
                        self.source_parity()
                        shutil.copy2(self.build/'CMakeCache.txt', self.out/'CMakeCache.txt')
                        self.report['candidate_ispc_sha256'] = runner.sha256(self.out/'candidate-ispc')
                        self.report['caller_assembly_sha256'] = {
                            s: runner.sha256(self.out/f'{s}-contexts/contexts.s') for s in ('baseline','candidate')}
                        self.verify_inputs()
                finally:
                    self.restore()
                self.verify_inputs()
                self.source_parity()
                self.report.update(status='prepared_for_T1_not_accepted', elapsed_seconds=time.monotonic()-self.started)
                self.emit_job()  # Only after successful restoration, never launches timing.
                remaining(self.deadline)
        except Exception as error:
            self.report.update(status='failed', error=str(error))
            (self.out/'focus-job.json').unlink(missing_ok=True)
            self.report.pop('focus_job', None)
            raise
        finally:
            self.report['elapsed_seconds'] = time.monotonic()-self.started
            self.save()
        return self.report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('--policy', required=True, type=Path)
    parser.add_argument('--worker', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        trial = Preparation(json.loads(args.policy.read_text()), json.loads(args.request.read_text()), args.worker, args.output)
        report = trial.prepare_t1()
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1
    print(report['status'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
