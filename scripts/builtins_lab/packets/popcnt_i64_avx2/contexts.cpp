// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// Google Benchmark driver for the popcnt(varying int64) T1 contexts (contexts.ispc).
#include <benchmark/benchmark.h>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <string>
#include <vector>

#include "config.h"
#include "popcnt_contexts_ispc.h"

namespace {

struct Data {
    std::vector<int64_t> src = std::vector<int64_t>(POPCNT_COUNT);
    std::vector<int32_t> src32 = std::vector<int32_t>(POPCNT_COUNT);
    std::vector<int64_t> dst64 = std::vector<int64_t>(POPCNT_COUNT);
    std::vector<int32_t> dst = std::vector<int32_t>(POPCNT_COUNT);
    std::vector<int32_t> even = std::vector<int32_t>(POPCNT_COUNT), random = std::vector<int32_t>(POPCNT_COUNT),
                         sparse = std::vector<int32_t>(POPCNT_COUNT);
    Data() {
        uint64_t state = 0x2545f4914f6cdd1dULL;
        for (int i = 0; i < POPCNT_COUNT; ++i) {
            state = state * 6364136223846793005ULL + 1442695040888963407ULL;
            src[i] = int64_t(state ^ (state >> 29));
            src32[i] = int32_t(src[i] >> 16);
            even[i] = i % 2 == 0 ? -1 : 0;
            random[i] = (state >> 61) & 1 ? -1 : 0;
            sparse[i] = i % 8 == (i / 8) % 8 ? -1 : 0; // one active lane per group of 8, rotating
        }
    }
};

Data &data() {
    static Data value;
    return value;
}

void add(const char *name, std::function<void()> body) {
    benchmark::RegisterBenchmark(name, [body](benchmark::State &state) {
        for (auto _ : state) {
            body();
            benchmark::ClobberMemory();
        }
    })->MinTime(0.1);
}

} // namespace

int main(int argc, char **argv) {
    Data &d = data();
    add("official_all", [&] { ispc::official_all(d.src.data(), d.dst64.data(), POPCNT_COUNT); });
    add("official_even", [&] { ispc::official_even(d.src.data(), d.dst64.data(), POPCNT_COUNT); });
    add("stream_all", [&] { ispc::stream_all(d.src.data(), d.dst.data(), POPCNT_COUNT); });
    add("stream_even", [&] { ispc::stream_even(d.src.data(), d.dst.data(), POPCNT_COUNT); });
    add("stream_mask_even", [&] { ispc::stream_mask(d.src.data(), d.even.data(), d.dst.data(), POPCNT_COUNT); });
    add("stream_mask_random", [&] { ispc::stream_mask(d.src.data(), d.random.data(), d.dst.data(), POPCNT_COUNT); });
    add("stream_mask_sparse", [&] { ispc::stream_mask(d.src.data(), d.sparse.data(), d.dst.data(), POPCNT_COUNT); });
    add("reduce_all", [&] { benchmark::DoNotOptimize(ispc::reduce_all(d.src.data(), POPCNT_COUNT)); });
    add("chain_all", [&] { ispc::chain_all(d.src.data(), d.dst.data(), POPCNT_CHAIN_STEPS); });
    add("chain_even", [&] { ispc::chain_even(d.src.data(), d.dst.data(), POPCNT_CHAIN_STEPS); });
    add("control_int32", [&] { ispc::control_int32(d.src32.data(), d.dst.data(), POPCNT_COUNT); });
    add("control_uniform_int64", [&] { ispc::control_uniform_int64(d.src.data(), d.dst.data(), POPCNT_COUNT); });
    benchmark::Initialize(&argc, argv);
    if (benchmark::ReportUnrecognizedArguments(argc, argv))
        return 1;
    benchmark::RunSpecifiedBenchmarks();
    benchmark::Shutdown();
    return 0;
}
