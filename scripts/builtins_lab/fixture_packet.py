#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Compile a maintainer-reviewed, hash-pinned builtin oracle/corpus packet."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import run as runner

SOURCE_NAMES = {'oracle.ispc', 'oracle.cpp', 'contexts.ispc', 'contexts.cpp', 'config.h'}
FIELDS = {'schema', 'name', 'target', 'allowed_paths', 'sources', 'cases',
          'discovery_cases', 'functional_globs', 'benchmark_header', 'oracle_header'}


def names(value, label):
    if (not isinstance(value, list) or not value or
            not all(isinstance(v, str) and v for v in value) or len(set(value)) != len(value)):
        raise ValueError(label + ' must be a nonempty unique string list')
    return value


def load(path, expected_sha256=None):
    path = Path(path)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError('fixture packet manifest hash mismatch')
    manifest = json.loads(raw)
    if set(manifest) != FIELDS or manifest['schema'] != 1 or manifest['target'] != 'avx2-i32x8':
        raise ValueError('unsupported fixture packet schema/target')
    if not isinstance(manifest['name'], str) or not re.fullmatch('[a-zA-Z0-9_-]+', manifest['name']):
        raise ValueError('invalid fixture packet name')
    for name in names(manifest['allowed_paths'], 'allowed_paths'):
        if (not re.fullmatch(r'builtins/[a-zA-Z0-9_./-]+\.(ll|m4)', name) or
                '..' in Path(name).parts):
            raise ValueError('packet may allow only explicit builtin source paths')
    cases = names(manifest['cases'], 'cases')
    discovery = names(manifest['discovery_cases'], 'discovery_cases')
    if not set(discovery) <= set(cases):
        raise ValueError('discovery cases must be contained in the full inventory')
    for pattern in names(manifest['functional_globs'], 'functional_globs'):
        if '/' in pattern or '\\' in pattern or '..' in pattern or not pattern.endswith('.ispc'):
            raise ValueError('functional globs must be local ISPC filenames')
    for key in ('benchmark_header', 'oracle_header'):
        if not re.fullmatch(r'[a-zA-Z0-9_]+\.h', manifest[key]):
            raise ValueError('invalid generated header basename')
    if not isinstance(manifest['sources'], dict) or set(manifest['sources']) != SOURCE_NAMES:
        raise ValueError('fixture packet source inventory differs')
    content = {}
    for name, expected in manifest['sources'].items():
        source = path.parent / name
        if source.is_symlink() or not source.resolve().is_relative_to(path.parent.resolve()):
            raise ValueError('fixture source escapes packet directory')
        data = source.read_bytes()
        if not isinstance(expected, str) or hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('fixture source hash mismatch: ' + name)
        content[name] = data
    return dict(manifest=manifest, raw=raw, sha256=digest, content=content)


def freeze(packet, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'packet.json').write_bytes(packet['raw'])
    for name, data in packet['content'].items():
        (destination / name).write_bytes(data)


def compile_packet(packet_path, ispc, cxx, build, source_root, validation, contexts,
                   timeout=300, target='avx2-i32x8', compile_only=False):
    packet = load(packet_path)
    manifest = packet['manifest']
    if target not in ('avx2-i32x8', 'avx2vnni-i32x8'):
        raise ValueError('unsupported packet compilation target')
    if target != manifest['target'] and not compile_only:
        raise ValueError('inherited target is compile-only')
    validation, contexts = Path(validation), Path(contexts)
    for directory in (validation, contexts):
        directory.mkdir(parents=True, exist_ok=False)
    for name, data in packet['content'].items():
        directory = validation if name.startswith('oracle.') else contexts
        (directory / name).write_bytes(data)
    ispc, cxx = Path(ispc).absolute(), Path(cxx).absolute()  # preserve clang++ invocation name
    library = Path(build) / 'benchmarks/vendor/google/benchmark/src/libbenchmark.a'
    include = Path(source_root) / 'benchmarks/vendor/google/benchmark/include'
    report = dict(status='building', packet_sha256=packet['sha256'], target=target,
                  runtime_verified=False, commands=[],
                  toolchain_sha256=dict(ispc=runner.sha256(ispc), cxx=runner.sha256(cxx)),
                  library_sha256=runner.sha256(library))

    def save():
        (validation / 'fixture.json').write_text(json.dumps(report, indent=2) + '\n')

    def command(label, argv, directory):
        argv = [str(arg) for arg in argv]
        report['commands'].append(dict(label=label, argv=argv))
        save()
        runner.execute(argv, directory / (label + '.log'), timeout)

    save()
    try:
        for stem, directory, header in (
                ('oracle', validation, manifest['oracle_header']),
                ('contexts', contexts, manifest['benchmark_header'])):
            base = [ispc, directory / (stem + '.ispc'), '--target=' + target,
                    '--arch=x86-64', '-O2', '-g']
            command(stem + '-compile', [*base, '-o', directory / (stem + '.o'),
                    '-h', directory / header], directory)
            command(stem + '-assembly', [*base, '--emit-asm', '-o', directory / (stem + '.s')], directory)
            command(stem + '-ir', [*base, '--emit-llvm-text', '-o', directory / (stem + '.ll')], directory)
        command('oracle-link', [cxx, '-std=c++17', '-O2', '-g', '-mavx2',
            validation / 'oracle.cpp', validation / 'oracle.o', '-I' + str(validation),
            '-o', validation / 'validate-builtin'], validation)
        command('contexts-link', [cxx, '-std=c++17', '-O2', '-g', '-mavx2',
            '-fno-omit-frame-pointer', '-Wl,--build-id', contexts / 'contexts.cpp',
            contexts / 'contexts.o', '-I' + str(contexts), '-I' + str(include),
            library, '-lpthread', '-o', contexts / 'builtin-contexts'], contexts)
        if not compile_only:
            command('run', [validation / 'validate-builtin'], validation)
            command('preflight', [contexts / 'builtin-contexts', '--benchmark_list_tests=true'], contexts)
            if sorted((contexts / 'preflight.log').read_text().splitlines()) != sorted(manifest['cases']):
                raise ValueError('compiled benchmark differs from frozen packet inventory')
            report['runtime_verified'] = True
        report['status'] = 'compile_only_runtime_unverified' if compile_only else 'verified'
        report['artifacts_sha256'] = {
            str(path): runner.sha256(path) for directory in (validation, contexts)
            for path in sorted(directory.iterdir()) if path.is_file() and path.name != 'fixture.json'}
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('packet', 'ispc', 'cxx', 'build', 'source-root', 'validation', 'contexts'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--target', default='avx2-i32x8')
    parser.add_argument('--compile-only', action='store_true')
    args = parser.parse_args()
    try:
        report = compile_packet(args.packet, args.ispc, args.cxx, args.build, args.source_root,
                                args.validation, args.contexts, args.timeout, args.target, args.compile_only)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(report['status'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
