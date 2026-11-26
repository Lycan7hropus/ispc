// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// T0 fixture: isolated all-on eight-lane integer64 reduce_equal, not an ISPC ABI.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <dlfcn.h>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <x86intrin.h>

using Kernel = void (*)(const uint64_t *, uint64_t *, uint64_t *, size_t, size_t);
constexpr uint64_t Sentinel = 0x93f487a12cd6b508ULL;
volatile uint64_t consumed;

struct Library {
    void *handle;
    Kernel kernel;
    explicit Library(const char *path) : handle(dlopen(path, RTLD_NOW | RTLD_LOCAL)) {
        if (!handle)
            throw std::runtime_error(dlerror());
        kernel = reinterpret_cast<Kernel>(dlsym(handle, "lab_kernel"));
        if (!kernel)
            throw std::runtime_error("missing lab_kernel export");
    }
    ~Library() { dlclose(handle); }
};

struct Fixture {
    size_t groups;
    std::vector<uint64_t> input, values, flags;
    Fixture(size_t count, int pattern) : groups(count), input(count * 8), values(count + 2), flags(count + 2) {
        for (size_t g = 0; g < groups; ++g) {
            uint64_t value = 0x9e3779b97f4a7c15ULL * (g + 1);
            if (g % 4 == 0)
                value = 0;
            if (g % 4 == 1)
                value = UINT64_MAX;
            std::fill_n(input.data() + g * 8, 8, value);
            if (pattern)
                input[g * 8 + (pattern == 1 ? 1 : 7)] ^= (1ULL << (g % 64));
        }
        reset();
    }
    void reset() {
        std::fill(values.begin(), values.end(), Sentinel);
        std::fill(flags.begin(), flags.end(), Sentinel);
    }
    void invoke(Kernel kernel, size_t repeats) {
        kernel(input.data(), values.data() + 1, flags.data() + 1, groups, repeats);
    }
    void verify(Kernel kernel) {
        reset();
        const auto originalInput = input;
        invoke(kernel, 3);
        for (size_t g = 0; g < groups; ++g) {
            bool equal = true;
            for (size_t lane = 1; lane < 8; ++lane)
                equal = equal && input[g * 8 + lane] == input[g * 8];
            if (flags[g + 1] != uint64_t(equal) || (equal && values[g + 1] != input[g * 8]))
                throw std::runtime_error("independent all-on oracle mismatch");
        }
        if (input != originalInput || values.front() != Sentinel || values.back() != Sentinel ||
            flags.front() != Sentinel || flags.back() != Sentinel)
            throw std::runtime_error("input or output canary modified");
        reset();
        invoke(kernel, 0);
        if (!std::all_of(values.begin(), values.end(), [](auto v) { return v == Sentinel; }) ||
            !std::all_of(flags.begin(), flags.end(), [](auto v) { return v == Sentinel; }))
            throw std::runtime_error("zero repetitions changed output");
    }
};

struct Sample {
    double ticks, ns;
};

Sample measure(Fixture &fixture, Kernel kernel, size_t repeats) {
    fixture.reset();
    unsigned beforeCpu = 0, afterCpu = 0;
    auto before = std::chrono::steady_clock::now();
    _mm_lfence();
    uint64_t start = __rdtscp(&beforeCpu);
    _mm_lfence();
    fixture.invoke(kernel, repeats);
    uint64_t end = __rdtscp(&afterCpu);
    _mm_lfence();
    auto after = std::chrono::steady_clock::now();
    if (beforeCpu != afterCpu || end < start)
        throw std::runtime_error("CPU migration or invalid TSC sample");
    uint64_t sum = 0;
    for (size_t i = 1; i <= fixture.groups; ++i)
        sum ^= fixture.values[i] + fixture.flags[i];
    consumed = sum;
    return {double(end - start), std::chrono::duration<double, std::nano>(after - before).count()};
}

int main(int argc, char **argv) {
    try {
        if (argc != 7 && argc != 8)
            throw std::runtime_error("baseline.so candidate.so groups pairs batch_ms max_repeats [reps] required");
        Library baseline(argv[1]), candidate(argv[2]);
        size_t groups = std::stoull(argv[3]), pairs = std::stoull(argv[4]);
        double targetNs = std::stod(argv[5]) * 1e6;
        size_t maxRepeats = std::stoull(argv[6]);
        size_t reps = argc == 8 ? std::stoull(argv[7]) : 1;
        if (!pairs || !reps || !(targetNs > 0))
            throw std::runtime_error("pairs, reps and batch_ms must be positive");
        for (size_t count : {size_t(0), size_t(1), size_t(3), groups})
            for (int pattern = 0; pattern < 3; ++pattern) {
                Fixture check(count, pattern);
                check.verify(baseline.kernel);
                check.verify(candidate.kernel);
            }
        // Correctness coverage is fixed, independent of the timed working set.
        for (size_t lane = 0; lane < 8; ++lane)
            for (size_t bit = 0; bit < 64; ++bit) {
                Fixture check(3, 0);
                for (size_t group = 0; group < check.groups; ++group)
                    check.input[group * 8 + lane] ^= uint64_t(1) << bit;
                check.verify(baseline.kernel);
                check.verify(candidate.kernel);
            }
        std::cout << "{\"oracle\":\"passed_all_on_fixture_only\",\"cases\":[";
        for (int pattern = 0; pattern < 3; ++pattern) {
            Fixture fixture(groups, pattern);
            // Calibrate by doubling, then rescale so the faster side takes about batch_ms.
            size_t repeats = 1;
            while (true) {
                auto b = measure(fixture, baseline.kernel, repeats);
                auto c = measure(fixture, candidate.kernel, repeats);
                double fastest = std::min(b.ns, c.ns);
                if (fastest >= targetNs / 4) {
                    double scaled = double(repeats) * targetNs / fastest;
                    repeats = std::max<size_t>(1, std::min<size_t>(maxRepeats, size_t(scaled + 0.5)));
                    break;
                }
                if (repeats > maxRepeats / 2)
                    throw std::runtime_error("batch calibration exceeded repetition cap");
                repeats *= 2;
            }
            // Discarded warm-up so the first timed pairs do not see cold caches or a ramping clock.
            for (int warm = 0; warm < 8; ++warm) {
                measure(fixture, baseline.kernel, repeats);
                measure(fixture, candidate.kernel, repeats);
            }
            if (pattern)
                std::cout << ',';
            std::cout << "{\"name\":\""
                      << (pattern == 0   ? "equal"
                          : pattern == 1 ? "early_diff"
                                         : "late_diff")
                      << "\",\"groups\":" << groups << ",\"repeats\":" << repeats << ",\"reps\":" << reps
                      << ",\"pairs\":[";
            for (size_t pair = 0; pair < pairs; ++pair) {
                // One pair = reps interleaved batches per side (order alternates between pairs);
                // each side keeps its least-disturbed (minimum) batch.
                Sample b{HUGE_VAL, HUGE_VAL}, c{HUGE_VAL, HUGE_VAL};
                for (size_t rep = 0; rep < reps; ++rep) {
                    Sample sb{}, sc{};
                    if (pair % 2 == 0) {
                        sb = measure(fixture, baseline.kernel, repeats);
                        sc = measure(fixture, candidate.kernel, repeats);
                    } else {
                        sc = measure(fixture, candidate.kernel, repeats);
                        sb = measure(fixture, baseline.kernel, repeats);
                    }
                    b = {std::min(b.ticks, sb.ticks), std::min(b.ns, sb.ns)};
                    c = {std::min(c.ticks, sc.ticks), std::min(c.ns, sc.ns)};
                }
                if (pair)
                    std::cout << ',';
                double work = double(groups) * double(repeats);
                std::cout << "{\"order\":\"" << (pair % 2 == 0 ? "AB" : "BA")
                          << "\",\"baseline_tsc_ticks_per_group\":" << b.ticks / work
                          << ",\"candidate_tsc_ticks_per_group\":" << c.ticks / work
                          << ",\"baseline_ns_per_group\":" << b.ns / work
                          << ",\"candidate_ns_per_group\":" << c.ns / work << ",\"ratio\":" << c.ticks / b.ticks << '}';
            }
            std::cout << "]}";
        }
        std::cout << "]}\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
