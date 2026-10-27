#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Compile and independently validate AVX2 x8 shuffle; retain sources and assembly.

Use the same script with baseline and candidate compilers in separate output
directories. This checks semantics, not speed. Only legal source indices are used.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys


TYPES = {
    "i8": ("int8", "int8_t"), "u8": ("unsigned int8", "uint8_t"),
    "i16": ("int16", "int16_t"), "u16": ("unsigned int16", "uint16_t"),
    "i32": ("int32", "int32_t"), "u32": ("unsigned int32", "uint32_t"),
    "i64": ("int64", "int64_t"), "u64": ("unsigned int64", "uint64_t"),
    "f32": ("float", "float"), "f64": ("double", "double"),
}


def ispc_source():
    source = "// Copyright (c) 2026, Intel Corporation\n// SPDX-License-Identifier: BSD-3-Clause\n"
    for name, (kind, _) in TYPES.items():
        source += f"""
export void validate_{name}(uniform {kind} a[], uniform {kind} b[],
                            uniform int32 indices[], uniform {kind} out[],
                            uniform int32 mask, uniform int32 mode) {{
    {kind} x = a[programIndex];
    {kind} y = b[programIndex];
    int32 index = indices[programIndex];
    if ((mask & (1 << programIndex)) != 0) {{
        if (mode == 0) out[programIndex] = shuffle(x, index);
        else if (mode == 1) out[programIndex] = shuffle(x, y, index);
        else if (mode == 2) out[programIndex] = shuffle(x, programCount - 1 - programIndex);
        else out[programIndex] = shuffle(x, y,
            ((programIndex * 3 + 1) % programCount) + (programIndex & 1) * programCount);
    }}
}}
"""
    return source


CPP = r"""// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
#include "shuffle_ispc.h"
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <random>
#include <type_traits>

constexpr int width = 8;
uint64_t comparisons = 0;

template <typename T, typename F> bool check(const char *name, F kernel) {
    std::mt19937_64 random(0x53485546464c45ULL);
    for (int dataset = 0; dataset < 4; ++dataset) {
        std::array<T, width> a, b, out, expected;
        for (int lane = 0; lane < width; ++lane) {
            uint64_t bits_a = random(), bits_b = random();
            if (dataset == 0) { // Distinguishable source and lane values.
                a[lane] = static_cast<T>(lane + 1);
                b[lane] = static_cast<T>(lane + 33);
            } else {
                if constexpr (std::is_integral_v<T>) {
                    if (dataset == 1) {
                        const T edges[] = {std::numeric_limits<T>::min(),
                            std::numeric_limits<T>::max(), T(0), T(1),
                            T(-1), T(0x55), T(0x2a), T(2)};
                        std::memcpy(&bits_a, &edges[lane], sizeof(T));
                        std::memcpy(&bits_b, &edges[width - 1 - lane], sizeof(T));
                    }
                }
                if constexpr (std::is_floating_point_v<T>) {
                    // Both signs, zero, infinity, NaN payloads, and subnormals.
                    const uint64_t f64[] = {0, 0x8000000000000000ULL,
                        0x7ff0000000000000ULL, 0xfff0000000000000ULL,
                        0x7ff8000000001234ULL, 1, 0x0010000000000000ULL,
                        0x7ff0000000000001ULL};
                    const uint32_t f32[] = {0, 0x80000000U, 0x7f800000U,
                        0xff800000U, 0x7fc01234U, 1, 0x00800000U, 0x7f800001U};
                    if (dataset == 1) {
                        if constexpr (sizeof(T) == 4) {
                            bits_a = f32[lane]; bits_b = f32[width - 1 - lane];
                        } else {
                            bits_a = f64[lane]; bits_b = f64[width - 1 - lane];
                        }
                    }
                }
                std::memcpy(&a[lane], &bits_a, sizeof(T));
                std::memcpy(&b[lane], &bits_b, sizeof(T));
            }
        }
        for (int mode = 0; mode < 4; ++mode) {
            const int choices = mode == 1 ? 2 * width : width;
            for (int pattern = 0; pattern < choices + 36; ++pattern) {
                std::array<int32_t, width> index;
                for (int lane = 0; lane < width; ++lane) {
                    if (pattern < choices) index[lane] = pattern; // Every source at every output.
                    else if (pattern == choices) index[lane] = lane;
                    else if (pattern == choices + 1) index[lane] = width - 1 - lane;
                    else if (pattern == choices + 2) index[lane] = (lane + 1) % choices;
                    else if (pattern == choices + 3) index[lane] = (lane * 3 + width - 1) % choices;
                    else index[lane] = static_cast<int32_t>(random() % choices);
                }
                for (int mask = 0; mask < (1 << width); ++mask) {
                    std::memset(out.data(), 0xa5, sizeof(out));
                    std::memcpy(expected.data(), out.data(), sizeof(out));
                    for (int lane = 0; lane < width; ++lane) {
                        if (!(mask & (1 << lane))) continue;
                        int source = index[lane];
                        if (mode == 2) source = width - 1 - lane;
                        if (mode == 3) source = ((lane * 3 + 1) % width) + (lane & 1) * width;
                        const T *value = source < width ? &a[source] : &b[source - width];
                        std::memcpy(&expected[lane], value, sizeof(T));
                    }
                    kernel(a.data(), b.data(), index.data(), out.data(), mask, mode);
                    for (int lane = 0; lane < width; ++lane) {
                        ++comparisons;
                        if (std::memcmp(&out[lane], &expected[lane], sizeof(T)) != 0) {
                            std::cerr << name << " dataset=" << dataset << " mode=" << mode
                                      << " pattern=" << pattern << " mask=" << mask
                                      << " lane=" << lane << '\n';
                            return false;
                        }
                    }
                }
            }
        }
    }
    return true;
}

int main() {
__CALLS__
    std::cout << "PASS: " << comparisons << " bitwise lane comparisons\n";
}
"""


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ispc", required=True, type=Path)
    parser.add_argument("--cxx", default="clang++-20")
    parser.add_argument("--target", default="avx2-i32x8",
                        choices=("avx2-i32x8", "avx2vnni-i32x8"))
    parser.add_argument("--compile-only", action="store_true",
                        help="retain code without running it on an unsupported CPU")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    compiler = args.ispc.resolve(strict=True)
    cxx = shutil.which(args.cxx)
    if cxx is None:
        parser.error("C++ compiler not found")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture = out / "shuffle.ispc"
    host = out / "shuffle.cpp"
    fixture.write_text(ispc_source())
    calls = "\n".join(f'    if (!check<{kind}>("{name}", ispc::validate_{name})) return 1;'
                      for name, (_, kind) in TYPES.items())
    host.write_text(CPP.replace("__CALLS__", calls))
    report = {"status": "failed", "target": args.target, "commands": [],
              "ispc": str(compiler), "ispc_sha256": digest(compiler),
              "cxx": cxx, "cxx_sha256": digest(cxx),
              "source_sha256": {p.name: digest(p) for p in (fixture, host)}}

    def execute(argv, label):
        report["commands"].append(argv)
        log_path = out / f"{label}.log"
        with log_path.open("w") as log:
            with subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                  start_new_session=True) as process:
                try:
                    code = process.wait(timeout=180)
                except BaseException:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                    raise
                if code:
                    raise subprocess.CalledProcessError(code, argv)
        return log_path.read_text().strip()

    try:
        report["ispc_version"] = execute([str(compiler), "--version"], "ispc-version")
        report["cxx_version"] = execute([cxx, "--version"], "cxx-version")
        flags = [str(compiler), str(fixture), f"--target={args.target}", "--arch=x86-64", "-O2"]
        execute([*flags, "-o", str(out / "shuffle.o"), "-h", str(out / "shuffle_ispc.h")], "compile-ispc")
        execute([*flags, "--emit-asm", "-o", str(out / "shuffle.s")], "assembly")
        execute([cxx, "-std=c++17", "-O2", str(host), str(out / "shuffle.o"),
                 "-o", str(out / "validate-shuffle")], "compile-host")
        if args.compile_only:
            report["result"] = "Compiled only; runtime semantics remain unverified"
        else:
            report["result"] = execute([str(out / "validate-shuffle")], "validation")
        if digest(compiler) != report["ispc_sha256"]:
            raise ValueError("ISPC binary changed during validation")
        report["status"] = "compiled_unverified" if args.compile_only else "passed"
        print(report["result"])
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report["error"] = str(error)
        print(f"Shuffle validation failed: {error}; logs: {out}", file=sys.stderr)
        return 1
    finally:
        (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    sys.exit(main())
