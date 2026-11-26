// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// T0 fixture popcnt-i64-masks: isolated eight-lane varying popcnt(int64) -> int32 with ISPC mask
// semantics (avx2-i32x8: inactive lanes must be 0). Complements the all-on popcnt-i64 fixture
// (screen_popcnt_kernel.cpp). Not an ISPC ABI; no ISPC integration.
//
// A kernel library exports three symbols with one signature:
//   void f(const uint64_t *input, const int32_t *mask, int32_t *out, size_t groups, size_t repeats)
// Per group g (8 lanes): out[8g+l] = mask[8g+l] ? popcount(lane value) : 0. Mask lanes are 0 or -1.
//   lab_popcnt        lane value = input[8g+l]; runtime mask (independent groups -> throughput).
//   lab_popcnt_even   same, but the mask is the compile-time constant "even lanes on" (0,2,4,6);
//                     the mask argument is ignored. Models ISPC code after inlining with a known mask.
//   lab_popcnt_chain  lane value = input[8g+l] ^ uint64(out[8(g-1)+l]) (0 for g = 0, per repeat):
//                     each group depends on the previous result (latency, incl. widening).
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

using Kernel = void (*)(const uint64_t *, const int32_t *, int32_t *, size_t, size_t);
constexpr int32_t Sentinel = 0x2cd6b508;
volatile int64_t consumed;

struct Library {
    void *handle;
    Kernel popcnt, even, chain;
    explicit Library(const char *path) : handle(dlopen(path, RTLD_NOW | RTLD_LOCAL)) {
        if (!handle)
            throw std::runtime_error(dlerror());
        popcnt = lookup("lab_popcnt");
        even = lookup("lab_popcnt_even");
        chain = lookup("lab_popcnt_chain");
    }
    Kernel lookup(const char *name) {
        auto kernel = reinterpret_cast<Kernel>(dlsym(handle, name));
        if (!kernel)
            throw std::runtime_error(std::string("missing export ") + name);
        return kernel;
    }
    ~Library() { dlclose(handle); }
};

// Independent oracle: bit-clearing loop, no POPCNT instruction or builtin.
int32_t referenceCount(uint64_t value) {
    int32_t count = 0;
    while (value) {
        value &= value - 1;
        ++count;
    }
    return count;
}

enum class Mode { Popcnt, Even, Chain };

// Mask patterns: lane bit l of an 8-bit pattern -> lane l active.
enum Pattern { AllOn, EvenLanes, OddLanes, Sparse, Random, AllOff, Enumerate };

uint32_t patternBits(Pattern pattern, size_t g, uint64_t &state) {
    switch (pattern) {
    case AllOn:
        return 0xff;
    case EvenLanes:
        return 0x55;
    case OddLanes:
        return 0xaa;
    case Sparse:
        return 1u << (g % 8);
    case AllOff:
        return 0;
    case Enumerate:
        return uint32_t(g % 256);
    case Random:
    default:
        state = state * 6364136223846793005ULL + 1442695040888963407ULL;
        return uint32_t(state >> 56);
    }
}

struct Fixture {
    size_t groups;
    std::vector<uint64_t> input;
    std::vector<int32_t> mask, out;
    Fixture(size_t count, Pattern pattern, uint64_t seed = 0x5eed)
        : groups(count), input(count * 8), mask(count * 8), out(count * 8 + 16) {
        uint64_t state = seed, maskState = seed ^ 0xa5a5;
        for (size_t i = 0; i < input.size(); ++i) {
            state = state * 6364136223846793005ULL + 1442695040888963407ULL;
            uint64_t value = state ^ (state >> 29);
            switch (i % 7) { // vary density: zero, all ones, sparse, dense, random
            case 0:
                value = i % 14 ? value : 0;
                break;
            case 1:
                value = i % 21 ? value : UINT64_MAX;
                break;
            case 2:
                value &= value >> 17 & value >> 31;
                break;
            case 3:
                value |= value << 13 | value >> 7;
                break;
            }
            input[i] = value;
        }
        for (size_t g = 0; g < groups; ++g) {
            uint32_t bits = patternBits(pattern, g, maskState);
            for (size_t lane = 0; lane < 8; ++lane)
                mask[g * 8 + lane] = (bits >> lane & 1) ? -1 : 0;
        }
        reset();
    }
    void reset() { std::fill(out.begin(), out.end(), Sentinel); }
    void invoke(Kernel kernel, size_t repeats) { kernel(input.data(), mask.data(), out.data() + 8, groups, repeats); }
    void verify(Kernel kernel, Mode mode) {
        reset();
        const auto originalInput = input;
        const auto originalMask = mask;
        invoke(kernel, 3);
        std::vector<int32_t> previous(8, 0);
        for (size_t g = 0; g < groups; ++g)
            for (size_t lane = 0; lane < 8; ++lane) {
                size_t i = g * 8 + lane;
                bool active = mode == Mode::Even ? lane % 2 == 0 : mask[i] != 0;
                uint64_t value = input[i];
                if (mode == Mode::Chain)
                    value ^= uint64_t(uint32_t(previous[lane]));
                int32_t expected = active ? referenceCount(value) : 0;
                if (out[i + 8] != expected)
                    throw std::runtime_error("independent popcnt oracle mismatch (group " + std::to_string(g) +
                                             ", lane " + std::to_string(lane) + ")");
                previous[lane] = expected;
            }
        if (input != originalInput || mask != originalMask)
            throw std::runtime_error("input or mask modified");
        for (size_t i = 0; i < 8; ++i)
            if (out[i] != Sentinel || out[out.size() - 1 - i] != Sentinel)
                throw std::runtime_error("output canary modified");
        reset();
        invoke(kernel, 0);
        if (!std::all_of(out.begin(), out.end(), [](auto v) { return v == Sentinel; }))
            throw std::runtime_error("zero repetitions changed output");
    }
};

void verifyAll(Library &library) {
    const std::pair<Kernel, Mode> kernels[] = {
        {library.popcnt, Mode::Popcnt}, {library.even, Mode::Even}, {library.chain, Mode::Chain}};
    for (auto [kernel, mode] : kernels) {
        for (size_t count : {size_t(0), size_t(1), size_t(3), size_t(32)})
            for (Pattern pattern : {AllOn, EvenLanes, OddLanes, Sparse, Random, AllOff}) {
                Fixture check(count, pattern, 0x1234 + count);
                check.verify(kernel, mode);
            }
        // Every one of the 256 lane masks, twice with different data.
        for (uint64_t seed : {1ULL, 2ULL}) {
            Fixture check(512, Enumerate, seed);
            check.verify(kernel, mode);
        }
        // Each single bit in each lane, alone and on top of all-ones (counts 1 and 63, every position).
        for (size_t bit = 0; bit < 64; ++bit) {
            Fixture single(8, AllOn), cleared(8, AllOn);
            for (size_t i = 0; i < single.input.size(); ++i) {
                single.input[i] = uint64_t(1) << ((bit + i) % 64);
                cleared.input[i] = ~single.input[i];
            }
            single.verify(kernel, mode);
            cleared.verify(kernel, mode);
        }
    }
}

struct Sample {
    double ticks, ns;
};

Sample measure(Fixture &fixture, Kernel kernel, size_t repeats) {
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
    int64_t sum = 0;
    for (size_t i = 0; i < fixture.groups * 8; i += 7)
        sum += fixture.out[i + 8];
    consumed = sum;
    return {double(end - start), std::chrono::duration<double, std::nano>(after - before).count()};
}

struct Case {
    const char *name;
    Mode mode;
    Pattern pattern;
};

int main(int argc, char **argv) {
    try {
        if (argc != 7 && argc != 8)
            throw std::runtime_error("baseline.so candidate.so groups pairs batch_ms max_repeats [reps] required");
        Library baseline(argv[1]), candidate(argv[2]);
        size_t groups = std::stoull(argv[3]), pairs = std::stoull(argv[4]);
        double targetNs = std::stod(argv[5]) * 1e6;
        size_t maxRepeats = std::stoull(argv[6]);
        size_t reps = argc == 8 ? std::stoull(argv[7]) : 1;
        if (!pairs || !reps || !(targetNs > 0) || !groups)
            throw std::runtime_error("groups, pairs, reps and batch_ms must be positive");
        verifyAll(baseline);
        verifyAll(candidate);
        const Case cases[] = {
            {"all_on", Mode::Popcnt, AllOn},        {"even", Mode::Popcnt, EvenLanes},
            {"odd", Mode::Popcnt, OddLanes},        {"sparse_one_lane", Mode::Popcnt, Sparse},
            {"random_mixed", Mode::Popcnt, Random}, {"all_off", Mode::Popcnt, AllOff},
            {"even_static", Mode::Even, EvenLanes}, {"chain_all_on", Mode::Chain, AllOn},
            {"chain_even", Mode::Chain, EvenLanes},
        };
        std::cout << "{\"oracle\":\"passed_popcnt_i64_fixture\",\"cases\":[";
        bool firstCase = true;
        for (const Case &spec : cases) {
            auto pick = [&](Library &library) {
                return spec.mode == Mode::Even    ? library.even
                       : spec.mode == Mode::Chain ? library.chain
                                                  : library.popcnt;
            };
            Kernel base = pick(baseline), cand = pick(candidate);
            Fixture fixture(groups, spec.pattern);
            // Calibrate by doubling, then rescale so the faster side takes about batch_ms.
            size_t repeats = 1;
            while (true) {
                auto b = measure(fixture, base, repeats);
                auto c = measure(fixture, cand, repeats);
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
            for (int warm = 0; warm < 8; ++warm) {
                measure(fixture, base, repeats);
                measure(fixture, cand, repeats);
            }
            if (!firstCase)
                std::cout << ',';
            firstCase = false;
            std::cout << "{\"name\":\"" << spec.name << "\",\"groups\":" << groups << ",\"repeats\":" << repeats
                      << ",\"reps\":" << reps << ",\"pairs\":[";
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
                // Same estimator as screen_kernel.cpp: reps adjacent ABBA couples of short batches.
                for (size_t rep = 0; rep < reps; ++rep) {
                    Sample b{}, c{};
                    if ((pair + rep) % 2 == 0) {
                        b = measure(fixture, base, repeats);
                        c = measure(fixture, cand, repeats);
                    } else {
                        c = measure(fixture, cand, repeats);
                        b = measure(fixture, base, repeats);
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
