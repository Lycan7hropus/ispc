#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Build fixed shuffle caller contexts against a chosen ISPC compiler."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

MODES = ('dynamic1', 'dynamic2', 'constant', 'masked')
CONTEXTS = ('latency', 'throughput', 'stream')


def source(kind):
    text = '// Copyright (c) 2026, Intel Corporation\n// SPDX-License-Identifier: BSD-3-Clause\n'
    for mode in MODES:
        for context in CONTEXTS:
            name = f'{mode}_{context}'
            expr = 'shuffle(x, y, index)' if mode == 'dynamic2' else (
                'shuffle(x, programCount - 1 - programIndex)' if mode == 'constant' else 'shuffle(x, index)')
            condition = 'if ((programIndex & 1) == 0)' if mode == 'masked' else ''
            text += f'\nexport void {name}(uniform int16 src[], uniform int32 indices[], uniform int16 out[], uniform int32 count) {{\n'
            text += '    int32 index = indices[programIndex];\n'
            if context == 'stream':
                text += f'''    foreach (i = 0 ... count) {{
        int16 x = src[i];
        int16 y = src[count + i];
        {condition} out[i] = {expr};
    }}
'''
            else:
                chains = 4 if context == 'throughput' else 1
                for c in range(chains):
                    text += f'    int16 x{c} = src[{c * 8} + programIndex];\n'
                    text += f'    int16 y{c} = src[{(c + 4) * 8} + programIndex];\n'
                text += '    for (uniform int32 iteration = 0; iteration < count; ++iteration) {\n'
                for c in range(chains):
                    expression = expr.replace('x,', f'x{c},').replace('y,', f'y{c},')
                    text += f'        {condition} x{c} = {expression};\n'
                text += '    }\n'
                for c in range(chains):
                    text += f'    out[{c * 8} + programIndex] = x{c};\n'
            text += '}\n'
    return text.replace('int16', kind)


HOST = r'''// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
#include "contexts_ispc.h"
#include <benchmark/benchmark.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

using Kernel = void (*)(int16_t *, int32_t *, int16_t *, int32_t);
struct Case { const char *name; Kernel function; int mode; int context; };
Case cases[] = {
__CASES__
};

std::array<int32_t, 8> permutation(int pattern, bool dual) {
    std::array<int32_t, 8> p;
    for (int lane = 0; lane < 8; ++lane) {
        switch (pattern) {
        case 0: p[lane] = lane; break;
        case 1: p[lane] = 7 - lane; break;
        case 2: p[lane] = (lane + 1) % 8; break;
        case 3: p[lane] = 3; break;
        default: p[lane] = (lane * 3 + 1) % 8; break;
        }
        if (dual && (lane & 1)) p[lane] += 8;
    }
    return p;
}

std::vector<int16_t> inputs(int count) {
    std::vector<int16_t> src(2 * count);
    for (int i = 0; i < 2 * count; ++i) src[i] = static_cast<int16_t>(i * 37 + 11);
    return src;
}

bool validate(const Case &c, int pattern) {
    auto p = permutation(pattern, c.mode == 1);
    const int count = c.context == 2 ? 512 : 257;
    auto src = inputs(c.context == 2 ? count : 32);
    std::vector<int16_t> out(c.context == 2 ? count : 32, -1234), expected(out);
    if (c.context == 2) {
        for (int i = 0; i < count; ++i) {
            if (c.mode == 3 && (i & 1)) continue;
            const int index = c.mode == 2 ? 7 - i % 8 : p[i % 8];
            expected[i] = src[(i / 8) * 8 + index % 8 + (index >= 8 ? count : 0)];
        }
    } else {
        const int chains = c.context == 1 ? 4 : 1;
        for (int chain = 0; chain < chains; ++chain) {
            std::array<int16_t, 8> x;
            std::copy_n(src.data() + chain * 8, 8, x.begin());
            for (int iteration = 0; iteration < count; ++iteration) {
                auto next = x;
                for (int lane = 0; lane < 8; ++lane) {
                    if (c.mode == 3 && (lane & 1)) continue;
                    const int index = c.mode == 2 ? 7 - lane : p[lane];
                    next[lane] = index < 8 ? x[index] : src[(chain + 4) * 8 + index - 8];
                }
                x = next;
            }
            std::copy(x.begin(), x.end(), expected.begin() + chain * 8);
        }
    }
    c.function(src.data(), p.data(), out.data(), count);
    if (out != expected) {
        std::cerr << "Incorrect caller context: " << c.name << " pattern=" << pattern << '\n';
        return false;
    }
    return true;
}

int main(int argc, char **argv) {
    for (const auto &c : cases) {
        for (int pattern = 0; pattern < (c.mode == 2 ? 1 : 5); ++pattern) {
            if (!validate(c, pattern)) return 1;
            auto p = permutation(pattern, c.mode == 1);
            const std::string name = std::string(c.name) + "/p" + std::to_string(pattern);
            benchmark::RegisterBenchmark(name.c_str(), [c, p](benchmark::State &state) mutable {
                const int count = c.context == 2 ? 512 : 256;
                auto src = inputs(c.context == 2 ? count : 32);
                std::vector<int16_t> out(c.context == 2 ? count : 32, -1234);
                for (auto _ : state) {
                    c.function(src.data(), p.data(), out.data(), count);
                    benchmark::DoNotOptimize(out.data());
                    benchmark::ClobberMemory();
                }
            })->MinTime(0.1);
        }
    }
    benchmark::Initialize(&argc, argv);
    if (benchmark::ReportUnrecognizedArguments(argc, argv)) return 1;
    benchmark::RunSpecifiedBenchmarks();
    benchmark::Shutdown();
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ispc', required=True, type=Path)
    parser.add_argument('--build', required=True, type=Path, help='ISPC build containing Google Benchmark')
    parser.add_argument('--cxx', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--type', default='int16', choices=('int16', 'int64', 'double'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture, host = out / 'contexts.ispc', out / 'contexts.cpp'
    fixture.write_text(source(args.type))
    rows = [f'    {{"{mode}/{context}", ispc::{mode}_{context}, {m}, {c}}},'
            for m, mode in enumerate(MODES) for c, context in enumerate(CONTEXTS)]
    host_kind = {'int16': 'int16_t', 'int64': 'int64_t', 'double': 'double'}[args.type]
    host.write_text(HOST.replace('__CASES__', '\n'.join(rows)).replace('int16_t', host_kind))
    # clang++ may be a symlink to clang: its invoked name selects C++ linking.
    compiler, cxx, build = args.ispc.resolve(), args.cxx.absolute(), args.build.resolve()
    def digest(path):
        with Path(path).open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    report = dict(status='failed', data_type=args.type, ispc=str(compiler), ispc_sha256=digest(compiler),
                  cxx=str(cxx), cxx_sha256=digest(cxx),
                  sources={p.name: digest(p) for p in (fixture, host)}, commands=[])
    # Reuse the evaluator's process-group cleanup and log preservation.
    import os
    from run import command
    def execute(argv, label):
        report['commands'].append(argv)
        command(argv, out / f'{label}.log', 180, min(os.sched_getaffinity(0)))
    try:
        flags = [str(compiler), str(fixture), '--target=avx2-i32x8', '--arch=x86-64', '-O2']
        execute([*flags, '-o', str(out / 'contexts.o'), '-h', str(out / 'contexts_ispc.h')], 'ispc')
        execute([*flags, '--emit-asm', '-o', str(out / 'contexts.s')], 'assembly')
        execute([str(cxx), '-std=c++17', '-O2', str(host), str(out / 'contexts.o'),
                 '-I' + str(root / 'benchmarks/vendor/google/benchmark/include'),
                 str(build / 'benchmarks/vendor/google/benchmark/src/libbenchmark.a'),
                 '-lpthread', '-o', str(out / 'shuffle-contexts')], 'host')
        execute([str(out / 'shuffle-contexts'), '--benchmark_list_tests=true'], 'preflight')
        if digest(compiler) != report['ispc_sha256']:
            raise ValueError('ISPC binary changed during compilation')
        report['status'] = 'passed'
        print(out / 'shuffle-contexts')
    finally:
        (out / 'build.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
