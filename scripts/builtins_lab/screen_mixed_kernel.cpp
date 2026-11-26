// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// T0 fixture: modeled mixed-mask eight-lane i64, not an ISPC ABI.
// Only masks1..254; all8 input values must be accessible; buffers disjoint.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <dlfcn.h>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <x86intrin.h>

using Kernel = void (*)(const uint64_t *, const int32_t *, uint64_t *, uint64_t *, size_t, size_t);
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
    std::vector<int32_t> masks;
    Fixture(size_t count, int pattern)
        : groups(count), input(count * 8 + 2), values(count + 2), flags(count + 2), masks(count * 8 + 2) {
        for (size_t g = 0; g < groups; ++g) {
            uint64_t value = 0x9e3779b97f4a7c15ULL * (g + 1);
            if (g % 4 == 0)
                value = 0;
            if (g % 4 == 1)
                value = UINT64_MAX;
            std::fill_n(input.data() + 1 + g * 8, 8, value);
            // Timed masks alternate density and first-active position; every mask is proper partial.
            constexpr unsigned panel[] = {0x55, 0xaa, 0x7f, 0xfe};
            unsigned mask = panel[g % 4];
            size_t first = 0, last = 7;
            while (!(mask & (1U << first)))
                ++first;
            while (!(mask & (1U << last)))
                --last;
            for (size_t lane = 0; lane < 8; ++lane) {
                masks[1 + (g * 8 + lane)] = mask & (1U << lane) ? -1 : 0;
                if (!(mask & (1U << lane)))
                    input[1 + (g * 8 + lane)] = ~value;
            }
            if (pattern) {
                size_t changed = pattern == 1 ? first : last;
                input[1 + (g * 8 + changed)] ^= (uint64_t(1) << (g % 64));
            }
        }
        input.front() = input.back() = Sentinel;
        masks.front() = masks.back() = 0x139a4f72;
        reset();
    }
    void reset() {
        std::fill(values.begin(), values.end(), Sentinel);
        std::fill(flags.begin(), flags.end(), Sentinel);
    }
    void invoke(Kernel kernel, size_t repeats) {
        kernel(input.data() + 1, masks.data() + 1, values.data() + 1, flags.data() + 1, groups, repeats);
    }
    void verify(Kernel kernel) {
        reset();
        const auto originalInput = input;
        const auto originalMasks = masks;
        invoke(kernel, 3);
        for (size_t g = 0; g < groups; ++g) {
            bool equal = true, found = false;
            uint64_t base = 0;
            unsigned active = 0;
            for (size_t lane = 0; lane < 8; ++lane) {
                if (masks[1 + (g * 8 + lane)] < 0) {
                    active |= 1U << lane;
                    if (!found) {
                        base = input[1 + (g * 8 + lane)];
                        found = true;
                    }
                    equal = equal && input[1 + (g * 8 + lane)] == base;
                }
            }
            if (active == 0 || active == 255)
                throw std::runtime_error("outside proper partial mask fixture");
            if (flags[g + 1] != uint64_t(equal) || (equal && values[g + 1] != base) ||
                (!equal && values[g + 1] != Sentinel))
                throw std::runtime_error("independent mixed-mask oracle mismatch");
        }
        if (input != originalInput || masks != originalMasks || values.front() != Sentinel ||
            values.back() != Sentinel || flags.front() != Sentinel || flags.back() != Sentinel)
            throw std::runtime_error("input or output canary modified");
        reset();
        invoke(kernel, 0);
        if (input != originalInput || masks != originalMasks)
            throw std::runtime_error("zero repetitions changed input or mask canary");
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
        // Fixed oracle domain, independent of timed groups/cases. All254 proper partial masks,
        // all64bit mismatches in every lane and four sign-equivalent representations.
        size_t oracleChecks = 0;
        for (unsigned mask = 1; mask < 255; ++mask)
            for (unsigned repr = 0; repr < 4; ++repr)
                for (unsigned variant = 0; variant <= 512; ++variant) {
                    Fixture check(1, 0);
                    uint64_t base = mask % 3 == 0 ? 0 : mask % 3 == 1 ? UINT64_MAX : 0x8000000100000001ULL;
                    for (size_t lane = 0; lane < 8; ++lane) {
                        bool active = mask & (1U << lane);
                        constexpr int32_t negative[] = {-1, INT32_MIN, -2, -1234567};
                        constexpr int32_t positive[] = {0, INT32_MAX, 1, 1234567};
                        check.masks[1 + (lane)] = active ? negative[repr] : positive[repr];
                        check.input[1 + (lane)] = active ? base : (~base ^ (uint64_t(lane) << 32));
                    }
                    if (variant)
                        check.input[1 + ((variant - 1) / 64)] ^= uint64_t(1) << ((variant - 1) % 64);
                    check.verify(baseline.kernel);
                    check.verify(candidate.kernel);
                    ++oracleChecks;
                }
        std::cout << "{\"oracle\":\"passed_proper_partial_masks_only\",\"oracle_vectors_per_kernel\":" << oracleChecks
                  << ",\"cases\":[";
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
            std::vector<double> ratios(reps), baseTicks(reps), candTicks(reps), baseNs(reps), candNs(reps);
            auto median = [](std::vector<double> values) {
                auto middle = values.begin() + values.size() / 2;
                std::nth_element(values.begin(), middle, values.end());
                double upper = *middle;
                if (values.size() % 2)
                    return upper;
                return (upper + *std::max_element(values.begin(), middle)) / 2;
            };
            for (size_t pair = 0; pair < pairs; ++pair) {
                // One pair = reps adjacent baseline/candidate couples of short batches in ABBA order
                // (the first order alternates between pairs). Adjacent batches see the same clock
                // state, so each couple's ratio cancels frequency drift; the pair keeps their median.
                for (size_t rep = 0; rep < reps; ++rep) {
                    Sample b{}, c{};
                    if ((pair + rep) % 2 == 0) {
                        b = measure(fixture, baseline.kernel, repeats);
                        c = measure(fixture, candidate.kernel, repeats);
                    } else {
                        c = measure(fixture, candidate.kernel, repeats);
                        b = measure(fixture, baseline.kernel, repeats);
                    }
                    ratios[rep] = c.ticks / b.ticks;
                    baseTicks[rep] = b.ticks;
                    candTicks[rep] = c.ticks;
                    baseNs[rep] = b.ns;
                    candNs[rep] = c.ns;
                }
                if (pair)
                    std::cout << ',';
                double work = double(groups) * double(repeats);
                std::cout << "{\"order\":\"" << (pair % 2 == 0 ? "AB" : "BA")
                          << "\",\"baseline_tsc_ticks_per_group\":" << median(baseTicks) / work
                          << ",\"candidate_tsc_ticks_per_group\":" << median(candTicks) / work
                          << ",\"baseline_ns_per_group\":" << median(baseNs) / work
                          << ",\"candidate_ns_per_group\":" << median(candNs) / work << ",\"ratio\":" << median(ratios)
                          << '}';
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
