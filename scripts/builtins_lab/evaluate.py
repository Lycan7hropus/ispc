#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Evaluate a worker's builtin patch against a maintainer-pinned shuffle policy.

python3 scripts/builtins_lab/evaluate.py request.json --policy policy.json \
    --worker worker-1 --output /absolute/new/attempt
"""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import run as runner
import fixture_packet

ALLOWED = ('builtins/target-avx2-i32x8.ll',)
TOOLS = ('run.py', 'validate_shuffle.py', 'build_shuffle_bench.py', 'evaluate.py', 'fixture_packet.py')
POLICY_KEYS = {'repo', 'baseline_revision', 'llvm', 'cache', 'type', 'cpu',
               'runs', 'repetitions', 'min_gain', 'max_regression', 'jobs', 'timeout',
               'packet', 'packet_sha256'}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def shared_libraries(executables):
    paths = set()
    for executable in executables:
        result = subprocess.run(['ldd', str(executable)], capture_output=True, text=True)
        if 'not found' in result.stdout:
            raise ValueError(f'missing shared library for {executable}')
        if result.returncode and 'not a dynamic executable' not in result.stderr + result.stdout:
            raise ValueError(f'cannot inspect dynamic dependencies: {executable}')
        for line in result.stdout.splitlines():
            match = re.search(r'(/[^\s]+)', line)
            if match:
                paths.add(Path(match.group(1)).resolve())
    return {str(path): runner.sha256(path) for path in sorted(paths)}


def validate_policy(policy):
    if not isinstance(policy, dict) or set(policy) - POLICY_KEYS:
        raise ValueError('unknown policy fields')
    for key in ('repo', 'llvm', 'cache'):
        if not isinstance(policy.get(key), str) or not Path(policy[key]).is_absolute():
            raise ValueError(f'{key} must be an absolute path')
    if ('packet' in policy) != ('packet_sha256' in policy):
        raise ValueError('packet and packet_sha256 must be supplied together')
    if 'packet' in policy:
        if not isinstance(policy['packet'], str) or not Path(policy['packet']).is_absolute():
            raise ValueError('packet must be an absolute manifest path')
        if not isinstance(policy['packet_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', policy['packet_sha256']):
            raise ValueError('packet_sha256 must pin the manifest')
        if policy.get('type') != 'int64':
            raise ValueError('initial fixture packet policy requires integer64')
    if not re.fullmatch('[0-9a-f]{40}', policy.get('baseline_revision', '')):
        raise ValueError('baseline_revision must be a full commit SHA')
    if policy.get('type') not in ('int16', 'int64', 'double'):
        raise ValueError('type must be int16, int64, or double')
    if type(policy.get('cpu')) is not int or policy['cpu'] not in os.sched_getaffinity(0):
        raise ValueError('cpu must be available to this process')
    for key, minimum in (('runs', 3), ('repetitions', 2), ('jobs', 1), ('timeout', 1)):
        if type(policy.get(key)) is not int or policy[key] < minimum:
            raise ValueError(f'{key} must be an integer >= {minimum}')
    for key in ('min_gain', 'max_regression'):
        value = policy.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value < 1:
            raise ValueError(f'{key} must be between zero and one')


def validate_request(request):
    if not isinstance(request, dict) or set(request) != {'hypothesis', 'patch'}:
        raise ValueError('request must contain only hypothesis and patch')
    if not isinstance(request['hypothesis'], str) or not request['hypothesis'].strip():
        raise ValueError('hypothesis must be nonempty')
    if not isinstance(request['patch'], str) or not Path(request['patch']).is_absolute():
        raise ValueError('patch must be an absolute path')


def changed_paths(repo, patch, allowed=ALLOWED):
    summary = subprocess.run(['git', '-C', str(repo), 'apply', '--summary', str(patch)],
                             capture_output=True, check=True)
    if summary.stdout.strip():
        raise ValueError('patch must modify existing file content without mode changes or renames')
    result = subprocess.run(['git', '-C', str(repo), 'apply', '--numstat', '-z', str(patch)],
                            capture_output=True, check=True)
    paths = []
    for record in result.stdout.split(b'\0'):
        if not record:
            continue
        parts = record.decode('utf-8').split('\t')
        if len(parts) != 3 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError('binary or renamed patch entries are not supported')
        if parts[2] not in allowed or parts[2] in paths:
            raise ValueError(f'patch changes a protected or duplicate path: {parts[2]}')
        paths.append(parts[2])
    if not paths:
        raise ValueError('patch contains no builtin change')
    return paths


def expected_cases(confirmation=False):
    MODES = ('dynamic1', 'dynamic2', 'constant', 'masked')
    CONTEXTS = ('latency', 'throughput', 'stream')
    return sorted(f'{mode}/{context}/p{pattern}/min_time:0.100'
                  for mode in MODES for context in CONTEXTS
                  for pattern in (range(1 if mode == 'constant' else 5)
                                  if confirmation else (0,) if mode == 'constant' else (2,)))


def case_filter(cases):
    # Google Benchmark may use POSIX ERE, which has no non-capturing groups.
    return '^(' + '|'.join(re.escape(case) for case in cases) + ')$'


@contextmanager
def worker_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


class Evaluation:
    def __init__(self, policy, request, worker, out):
        self.out = out.resolve()
        self.out.mkdir(parents=True, exist_ok=False)
        self.report = dict(status='failed', policy=policy, request=request, commands=[], steps=[])
        self.save()
        for name, value in (('policy.json', policy), ('request.json', request)):
            (self.out / name).write_text(json.dumps(value, indent=2) + '\n')
        try:
            with runner.host_access(exclusive=False):
                self.initialize(policy, request, worker)
        except Exception as error:
            self.report['error'] = str(error)
            self.save()
            raise

    def initialize(self, policy, request, worker):
        validate_policy(policy)
        validate_request(request)
        if not re.fullmatch('[a-zA-Z0-9_-]{1,40}', worker):
            raise ValueError('invalid worker name')
        self.policy, self.request = policy, request
        self.repo, self.llvm = Path(policy['repo']), Path(policy['llvm'])
        self.packet = (fixture_packet.load(policy['packet'], policy['packet_sha256'])
                       if 'packet' in policy else None)
        self.patch = self.out / 'candidate.patch'
        shutil.copyfile(request['patch'], self.patch)
        allowed = self.packet['manifest']['allowed_paths'] if self.packet else ALLOWED
        self.paths = changed_paths(self.repo, self.patch, allowed)
        self.tools = self.out / 'evaluator'
        self.tools.mkdir()
        for name in TOOLS:
            shutil.copyfile(Path(__file__).parent / name, self.tools / name)
        frozen_names = list(TOOLS)
        if self.packet:
            fixture_packet.freeze(self.packet, self.tools / 'packet')
            frozen_names += ['packet/packet.json', *['packet/' + name for name in self.packet['content']]]
        toolchain = {name: runner.sha256(self.llvm / name)
                     for name in ('llvm-config', 'clang', 'clang++', 'llvm-as')}
        libraries = shared_libraries(self.llvm / name for name in toolchain)
        evaluator_hashes = {name: runner.sha256(self.tools / name) for name in frozen_names}
        self.configure_flags = ['-DCMAKE_BUILD_TYPE=Release',
            f'-DCMAKE_C_COMPILER={self.llvm / "clang"}', f'-DCMAKE_CXX_COMPILER={self.llvm / "clang++"}',
            f'-DLLVM_CONFIG_EXECUTABLE={self.llvm / "llvm-config"}', '-DARM_ENABLED=OFF',
            '-DISPC_INCLUDE_EXAMPLES=OFF', '-DISPC_INCLUDE_RT=OFF', '-DISPC_LIBRARY=OFF',
            '-DISPC_LIBRARY_JIT=OFF', '-DISPC_INCLUDE_BENCHMARKS=ON']
        identity = dict(repo=str(self.repo.resolve()), revision=policy['baseline_revision'],
                        llvm=str(self.llvm.absolute()), toolchain=toolchain,
                        shared_libraries=libraries,
                        cmake_flags=self.configure_flags,
                        build_schema=1, jobs=policy['jobs'])
        self.key = fingerprint(identity)
        self.home = Path(policy['cache']) / self.key / worker
        if not (self.home / 'worker.json').exists():
            # Earlier development versions keyed compiler caches by evaluator
            # hashes too. Reuse one only when every compiler input is identical;
            # fixtures and candidate correctness are always regenerated below.
            for marker in Path(policy['cache']).glob(f'*/{worker}/worker.json'):
                existing = json.loads(marker.read_text())
                existing.pop('evaluator', None)
                if existing == identity:
                    self.home = marker.parent
                    break
        self.source, self.build = self.home / 'source', self.home / 'build'
        self.identity = identity
        self.report = dict(status='failed', policy=policy, request=request,
                           patch_sha256=runner.sha256(self.patch), toolchain=toolchain,
                           shared_libraries=libraries,
                           evaluator_sha256=evaluator_hashes,
                           worker=str(self.home), commands=[], steps=[])
        self.originals = {}
        if self.packet:
            self.report['fixture_packet'] = dict(sha256=self.packet['sha256'], manifest=self.packet['manifest'])
        for name, value in (('policy.json', policy), ('request.json', request)):
            (self.out / name).write_text(json.dumps(value, indent=2) + '\n')

    def git(self, *args, cwd=None):
        return subprocess.check_output(['git', '-C', str(cwd or self.source), *args], text=True).strip()

    def stage(self, label, argv, cwd=None, timeout=None, environment=None):
        print(label, flush=True)
        record = dict(label=label, argv=[str(a) for a in argv], cwd=str(cwd or self.source))
        self.report['commands'].append(record)
        self.report['steps'].append(label)
        self.save()
        env = dict(os.environ)
        # Ubuntu's multiarch libc headers are needed by the unknown-unknown
        # triples used when generating ISPC bitcode; this is part of provenance.
        env['CPATH'] = '/usr/include/x86_64-linux-gnu'
        env.update(environment or {})
        record['environment'] = {'CPATH': env['CPATH'], **(environment or {})}
        runner.execute(record['argv'], self.out / f'{label}.log',
                       timeout or self.policy['timeout'], cwd=cwd or self.source, env=env)

    def save(self):
        self.report['build_environment'] = {'CPATH': '/usr/include/x86_64-linux-gnu'}
        (self.out / 'evaluation.json').write_text(json.dumps(self.report, indent=2) + '\n')

    def prepare(self):
        marker = self.home / 'worker.json'
        if marker.exists():
            existing = json.loads(marker.read_text())
            existing.pop('evaluator', None)
            if existing != self.identity:
                raise ValueError('worker identity differs')
        else:
            if self.source.exists():
                raise ValueError('refusing to reuse an unowned checkout')
            self.stage('worktree', ['git', '-C', self.repo, 'worktree', 'add', '--detach',
                                   self.source, self.policy['baseline_revision']], cwd=self.repo)
            marker.write_text(json.dumps(self.identity, indent=2) + '\n')
        if self.git('rev-parse', 'HEAD') != self.policy['baseline_revision']:
            raise ValueError('worker checkout moved from pinned baseline')
        if self.git('status', '--porcelain', '--untracked-files=normal'):
            raise ValueError('worker checkout has changes; inspect before reusing it')
        self.originals = {name: (self.source / name).read_bytes() for name in self.paths}
        self.stage('patch-check', ['git', '-C', self.source, 'apply', '--check', self.patch])
        ready = self.home / 'baseline.json'
        if ready.exists():
            metadata = json.loads(ready.read_text())
            if runner.sha256(self.home / 'baseline-ispc') != metadata['ispc_sha256']:
                raise ValueError('cached baseline binary changed')
            if runner.sha256(self.build / 'CMakeCache.txt') != metadata['cmake_cache_sha256']:
                raise ValueError('cached build configuration changed')
            self.report['baseline_cache_hit'] = True
            self.report['baseline'] = metadata
            return
        self.stage('submodules', ['git', '-C', self.source, 'submodule', 'update', '--init', '--recursive'])
        self.stage('configure', ['cmake', '-S', self.source, '-B', self.build, '-G', 'Ninja',
                                 *self.configure_flags])
        self.stage('baseline-build', ['cmake', '--build', self.build, '--target', 'ispc', 'benchmark',
                                      '-j', str(self.policy['jobs'])])
        self.stage('baseline-lit', ['cmake', '--build', self.build, '--target', 'check-all',
                                    '-j', str(self.policy['jobs'])])
        shutil.copy2(self.build / 'bin/ispc', self.home / 'baseline-ispc')
        metadata = dict(ispc_sha256=runner.sha256(self.home / 'baseline-ispc'),
                        cmake_cache_sha256=runner.sha256(self.build / 'CMakeCache.txt'),
                        submodules=self.git('submodule', 'status'), prepared_in=str(self.out),
                        lit_log_sha256=runner.sha256(self.out / 'baseline-lit.log'))
        temporary = self.home / 'baseline.json.tmp'
        temporary.write_text(json.dumps(metadata, indent=2) + '\n')
        temporary.replace(ready)
        self.report['baseline_cache_hit'] = False
        self.report['baseline'] = metadata

    def cases(self, confirmation=False):
        if getattr(self, 'packet', None):
            return sorted(self.packet['manifest']['cases' if confirmation else 'discovery_cases'])
        return expected_cases(confirmation)

    def benchmark_binary(self, label):
        name = 'builtin-contexts' if getattr(self, 'packet', None) else 'shuffle-contexts'
        return self.out / f'{label}-contexts' / name

    def oracle_binary(self, label):
        name = 'validate-builtin' if getattr(self, 'packet', None) else 'validate-shuffle'
        return self.out / f'{label}-validation' / name

    def packet_command(self, compiler, validation, contexts, target='avx2-i32x8', compile_only=False):
        command = ['python3', self.tools / 'fixture_packet.py', '--packet', self.tools / 'packet/packet.json',
                   '--ispc', compiler, '--cxx', self.llvm / 'clang++', '--build', self.build,
                   '--source-root', self.source, '--validation', validation, '--contexts', contexts,
                   '--target', target, '--timeout', str(self.policy['timeout'])]
        return command + (['--compile-only'] if compile_only else [])

    def fixtures(self, label, compiler):
        if self.packet:
            self.stage(f'{label}-fixture', self.packet_command(compiler,
                self.out / f'{label}-validation', self.out / f'{label}-contexts'))
        else:
            self.stage(f'{label}-oracle', ['python3', self.tools / 'validate_shuffle.py',
                '--ispc', compiler, '--cxx', self.llvm / 'clang++',
                '--output', self.out / f'{label}-validation'])
            self.stage(f'{label}-contexts', ['python3', self.tools / 'build_shuffle_bench.py',
                '--ispc', compiler, '--cxx', self.llvm / 'clang++', '--build', self.build,
                '--source-root', self.source, '--type', self.policy['type'],
                '--output', self.out / f'{label}-contexts'])
        rows = (self.out / f'{label}-contexts/preflight.log').read_text().splitlines()
        if sorted(rows) != self.cases(True):
            raise ValueError(f'{label}: benchmark inventory differs from fixed evaluator')
        for confirmation in (False, True):
            phase = 'confirmation' if confirmation else 'discovery'
            cases = self.cases(confirmation)
            inventory_label = f'{label}-{phase}-inventory'
            self.stage(inventory_label, [self.benchmark_binary(label),
                '--benchmark_list_tests=true', '--benchmark_filter=' + case_filter(cases)])
            if sorted((self.out / f'{inventory_label}.log').read_text().splitlines()) != cases:
                raise ValueError(f'{label}: {phase} filter changes fixed inventory')

    def build_candidate(self):
        if runner.sha256(self.patch) != self.report['patch_sha256']:
            raise ValueError('submitted patch changed after validation')
        self.stage('patch-apply', ['git', '-C', self.source, 'apply', self.patch])
        if sorted(self.git('diff', '--name-only').splitlines()) != sorted(self.paths):
            raise ValueError('applied patch changes unexpected paths or no content')
        if self.git('diff', '--summary'):
            raise ValueError('applied patch changes file metadata')
        self.stage('candidate-build', ['cmake', '--build', self.build, '--target', 'ispc',
                                      '-j', str(self.policy['jobs'])])
        shutil.copy2(self.build / 'bin/ispc', self.out / 'candidate-ispc')
        self.fixtures('candidate', self.out / 'candidate-ispc')
        if self.packet:
            self.stage('candidate-vnni-compile', self.packet_command(self.out / 'candidate-ispc',
                self.out / 'candidate-vnni-unverified', self.out / 'candidate-vnni-contexts',
                'avx2vnni-i32x8', True))
        else:
            self.stage('candidate-vnni-compile', ['python3', self.tools / 'validate_shuffle.py',
                '--ispc', self.out / 'candidate-ispc', '--cxx', self.llvm / 'clang++',
                '--target', 'avx2vnni-i32x8', '--compile-only',
                '--output', self.out / 'candidate-vnni-unverified'])
        for name in ('contexts.ispc', 'contexts.cpp'):
            if runner.sha256(self.out / 'baseline-contexts' / name) != runner.sha256(self.out / 'candidate-contexts' / name):
                raise ValueError('baseline and candidate harness sources differ')
        self.stage('candidate-lit', ['cmake', '--build', self.build, '--target', 'check-all',
                                    '-j', str(self.policy['jobs'])])
        patterns = self.packet['manifest']['functional_globs'] if self.packet else ['shuffle*.ispc']
        tests = sorted({path for pattern in patterns for path in self.source.glob('tests/func-tests/' + pattern)})
        if not tests:
            raise ValueError('no functional tests for the selected builtin family')
        self.report['functional_test_sha256'] = {str(p.relative_to(self.source)): runner.sha256(p) for p in tests}
        self.stage('candidate-functional', ['python3', self.source / 'scripts/run_tests.py',
            '--target=avx2-i32x8', '--compiler=clang++',
            '--jobs=' + str(self.policy['jobs']), '--non-interactive', *tests],
            timeout=self.policy['timeout'], environment={'ISPC_HOME': str(self.build / 'bin'),
                'PATH': str(self.llvm) + os.pathsep + os.environ.get('PATH', '')})

    def measure(self, confirmation=False):
        label = 'confirmation' if confirmation else 'discovery'
        print(label, flush=True)
        job = {key: self.policy[key] for key in ('cpu', 'runs', 'repetitions', 'min_gain', 'max_regression')}
        cases = self.cases(confirmation)
        job.update(hypothesis=self.request['hypothesis'], baseline_revision=self.policy['baseline_revision'],
                   candidate_revision=self.policy['baseline_revision'] + '+patch-' + self.report['patch_sha256'],
                   baseline=str(self.benchmark_binary('baseline')),
                   candidate=str(self.benchmark_binary('candidate')), metric='cpu_time',
                   timeout=self.policy['timeout'], expected_cases=cases,
                   filter=case_filter(cases),
                   checks=[[str(self.oracle_binary(name))] for name in ('baseline', 'candidate')])
        (self.out / f'{label}-job.json').write_text(json.dumps(job, indent=2) + '\n')
        directory = self.out / label
        directory.mkdir()
        result = runner.experiment(job, directory)
        self.report[label] = dict(status=result['status'], report=str(directory / 'report.json'))
        self.save()
        return result['status']

    def evaluate(self):
        try:
            with worker_lock(self.home / 'worker.lock'):
                try:
                    with runner.host_access(exclusive=False):
                        self.prepare()
                        self.fixtures('baseline', self.home / 'baseline-ispc')
                        self.build_candidate()
                        shutil.copy2(self.build / 'CMakeCache.txt', self.out / 'CMakeCache.txt')
                        self.report['caller_assembly_sha256'] = {
                            label: runner.sha256(self.out / f'{label}-contexts/contexts.s')
                            for label in ('baseline', 'candidate')}
                    if len(set(self.report['caller_assembly_sha256'].values())) == 1:
                        self.report['status'] = 'no_material_improvement'
                        self.report['reason'] = 'No change in final caller assembly; no speedup claimed'
                    else:
                        status = self.measure()
                        if status == 'candidate_for_confirmation':
                            status = self.measure(confirmation=True)
                            self.report['status'] = ('confirmed_for_review' if status == 'candidate_for_confirmation' else status)
                        else:
                            self.report['status'] = status
                finally:
                    # Only restore exact files owned by this dedicated worker.
                    # Retained candidate binaries and patches remain reviewable.
                    for name, content in self.originals.items():
                        (self.source / name).write_bytes(content)
                    self.report['source_restored'] = bool(self.originals)
        except Exception as error:
            self.report['status'] = 'failed'
            self.report['error'] = str(error)
            raise
        finally:
            self.save()
        return self.report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('--policy', required=True, type=Path)
    parser.add_argument('--worker', default='worker-1')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        evaluation = Evaluation(json.loads(args.policy.read_text()), json.loads(args.request.read_text()),
                                args.worker, args.output)
        result = evaluation.evaluate()
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'evaluation failed: {error}', file=sys.stderr)
        return 1
    print(result['status'])
    return 0 if result['status'] in ('confirmed_for_review', 'no_material_improvement') else 2


if __name__ == '__main__':
    sys.exit(main())
