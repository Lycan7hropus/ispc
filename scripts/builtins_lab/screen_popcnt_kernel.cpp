// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// T0 fixture: isolated all-on eight-lane integer64 popcnt (varying int64 -> varying int32), not an ISPC ABI.
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

using Kernel = void (*)(const uint64_t *, int32_t *, size_t, size_t);
constexpr int32_t Sentinel = int32_t(0x9b1d4e37);
constexpr size_t Guard = 8; // one full group of int32 canaries on each side
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

uint64_t splitmix(uint64_t &state) {
    uint64_t z = (state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

// Independent oracle: one bit at a time, no popcnt instruction or builtin.
int32_t reference(uint64_t value) {
    int32_t count = 0;
    for (int bit = 0; bit < 64; ++bit)
        count += int32_t((value >> bit) & 1);
    return count;
}

struct Fixture {
    size_t groups;
    std::vector<uint64_t> input;
    std::vector<int32_t> counts;
    // pattern 0: random, 1: sparse (0..3 bits per lane), 2: dense (61..64 bits per lane)
    Fixture(size_t count, int pattern) : groups(count), input(count * 8), counts(count * 8 + 2 * Guard) {
        uint64_t state = 0x5eed0000ULL + uint64_t(pattern) * 7919 + count;
        for (auto &value : input) {
            value = splitmix(state);
            if (pattern) {
                uint64_t sparse = 0;
                for (uint64_t bits = splitmix(state) % 4, i = 0; i < bits; ++i)
                    sparse |= uint64_t(1) << (splitmix(state) % 64);
                value = pattern == 1 ? sparse : ~sparse;
            }
        }
        reset();
    }
    void reset() { std::fill(counts.begin(), counts.end(), Sentinel); }
    void invoke(Kernel kernel, size_t repeats) { kernel(input.data(), counts.data() + Guard, groups, repeats); }
    void verify(Kernel kernel) {
        reset();
        const auto originalInput = input;
        invoke(kernel, 3);
        for (size_t i = 0; i < groups * 8; ++i)
            if (counts[Guard + i] != reference(input[i]))
                throw std::runtime_error("independent popcnt oracle mismatch");
        if (input != originalInput || !std::all_of(counts.begin(), counts.begin() + Guard, [](auto v) { return v == Sentinel; }) ||
            !std::all_of(counts.end() - Guard, counts.end(), [](auto v) { return v == Sentinel; }))
            throw std::runtime_error("input or output canary modified");
        reset();
        invoke(kernel, 0);
        if (!std::all_of(counts.begin(), counts.end(), [](auto v) { return v == Sentinel; }))
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
    for (size_t i = 0; i < fixture.groups * 8; ++i)
        sum = sum * 31 + uint32_t(fixture.counts[Guard + i]);
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
        auto check = [&](Fixture &fixture) {
            fixture.verify(baseline.kernel);
            fixture.verify(candidate.kernel);
        };
        for (size_t count : {size_t(0), size_t(1), size_t(3), groups})
            for (int pattern = 0; pattern < 3; ++pattern) {
                Fixture fixture(count, pattern);
                check(fixture);
            }
        // Fixed coverage, independent of the timed working set:
        // every lane x every bit position (single set bit, and single clear bit),
        Fixture single(2, 0);
        for (size_t lane = 0; lane < 8; ++lane)
            for (int bit = 0; bit < 64; ++bit)
                for (uint64_t base : {uint64_t(0), ~uint64_t(0)}) {
                    for (size_t group = 0; group < single.groups; ++group) {
                        for (size_t other = 0; other < 8; ++other)
                            single.input[group * 8 + other] = 0x0123456789abcdefULL * (other + 1);
                        single.input[group * 8 + lane] = base ^ (uint64_t(1) << bit);
                    }
                    check(single);
                }
        // every count 0..64 in every lane (catches byte/nibble sums that saturate or wrap),
        Fixture runs(2, 0);
        for (int bits = 0; bits <= 64; ++bits) {
            uint64_t ones = bits == 64 ? ~uint64_t(0) : (uint64_t(1) << bits) - 1;
            for (size_t i = 0; i < runs.input.size(); ++i) {
                int rotate = int((i * 7) % 64);
                runs.input[i] = rotate ? (ones << rotate) | (ones >> (64 - rotate)) : ones;
            }
            check(runs);
        }
        // and nibble/byte boundary patterns used by lookup-table methods.
        Fixture boundary(2, 0);
        const uint64_t patterns[] = {0x0f0f0f0f0f0f0f0fULL, 0xf0f0f0f0f0f0f0f0ULL, 0x8000000000000001ULL,
                                     0x00000000ffffffffULL, 0xffffffff00000000ULL, 0x5555555555555555ULL,
                                     0xaaaaaaaaaaaaaaaaULL, 0x8080808080808080ULL};
        for (size_t shift = 0; shift < 8; ++shift) {
            for (size_t i = 0; i < boundary.input.size(); ++i)
                boundary.input[i] = patterns[(i + shift) % 8];
            check(boundary);
        }
        std::cout << "{\"oracle\":\"passed_popcnt_i64_all_on_fixture_only\",\"cases\":[";
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
                      << (pattern == 0   ? "random"
                          : pattern == 1 ? "sparse"
                                         : "dense")
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
