// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// Independent oracle for popcnt(varying int64) on avx2-i32x8: bit-clearing reference, no POPCNT.
#include <cstdint>
#include <cstdio>
#include <vector>

#include "popcnt_oracle_ispc.h"

namespace {

int failures = 0;

int32_t reference(uint64_t value) {
    int32_t count = 0;
    for (; value; value &= value - 1)
        ++count;
    return count;
}

void expect(bool ok, const char *what, int index) {
    if (!ok && failures++ < 20)
        std::printf("FAIL %s at %d\n", what, index);
}

std::vector<int64_t> corpus() {
    std::vector<int64_t> values = {0,
                                   -1,
                                   1,
                                   INT64_MIN,
                                   INT64_MAX,
                                   0x5555555555555555LL,
                                   int64_t(0xaaaaaaaaaaaaaaaaULL),
                                   0x00000000ffffffffLL,
                                   int64_t(0xffffffff00000000ULL),
                                   0x0f0f0f0f0f0f0f0fLL,
                                   int64_t(0xf0f0f0f0f0f0f0f0ULL),
                                   0x0101010101010101LL};
    for (int bit = 0; bit < 64; ++bit) {
        values.push_back(int64_t(uint64_t(1) << bit));
        values.push_back(int64_t(~(uint64_t(1) << bit)));
    }
    uint64_t state = 0x9e3779b97f4a7c15ULL;
    while (values.size() % 8 || values.size() < 2048) {
        state = state * 6364136223846793005ULL + 1442695040888963407ULL;
        uint64_t v = state ^ (state >> 31);
        switch (values.size() % 4) {
        case 0:
            v &= v >> 7 & v >> 19; // sparse
            break;
        case 1:
            v |= v << 5 | v >> 11; // dense
            break;
        }
        values.push_back(int64_t(v));
    }
    return values;
}

} // namespace

int main() {
    const std::vector<int64_t> src = corpus();
    const int n = int(src.size());
    std::vector<int32_t> dst(n + 8), mask(n);
    std::vector<int64_t> dst64(n + 8);

    // Full and partial foreach tails.
    for (int count : {1, 3, 7, 8, 9, 15, 17, 64, n}) {
        std::fill(dst.begin(), dst.end(), 0x5a5a5a5a);
        ispc::oracle_all(const_cast<int64_t *>(src.data()), dst.data(), count);
        for (int i = 0; i < count; ++i)
            expect(dst[i] == reference(uint64_t(src[i])), "all", i);
        expect(dst[count] == 0x5a5a5a5a, "all: wrote past count", count);

        ispc::oracle_even(const_cast<int64_t *>(src.data()), dst.data(), count);
        for (int i = 0; i < count; ++i)
            expect(dst[i] == ((i & 1) == 0 ? reference(uint64_t(src[i])) : -1), "even", i);

        ispc::oracle_nested(const_cast<int64_t *>(src.data()), dst64.data(), count);
        for (int i = 0; i < count; ++i)
            expect(dst64[i] == reference(uint64_t(reference(uint64_t(src[i])))), "nested", i);

        int64_t sum = 0;
        for (int i = 0; i < count; ++i)
            sum += reference(uint64_t(src[i]));
        expect(ispc::oracle_reduce(const_cast<int64_t *>(src.data()), count) == sum, "reduce", count);
    }

    // Every 8-lane runtime mask (group g uses mask pattern g % 256).
    for (int i = 0; i < n; ++i)
        mask[i] = ((i / 8) % 256 >> (i % 8) & 1) ? -1 : 0;
    for (int shift = 0; shift < 2; ++shift) {
        std::vector<int64_t> shifted(src.begin() + shift * 8, src.end());
        shifted.resize(n, 0x123456789abcdefLL);
        // 256 patterns need 2048 elements; use one 2048-element pass per data shift.
        ispc::oracle_mask(shifted.data(), mask.data(), dst.data(), n);
        for (int i = 0; i < n; ++i)
            expect(dst[i] == (mask[i] ? reference(uint64_t(shifted[i])) : -1), "mask", i);
    }

    // Dependent chain under every mask pattern of one group.
    for (int pattern = 0; pattern < 256; ++pattern) {
        int32_t lanes[8];
        for (int lane = 0; lane < 8; ++lane)
            lanes[lane] = (pattern >> lane & 1) ? -1 : 0;
        int32_t out[8];
        const int64_t *x = src.data() + (pattern % (n / 8)) * 8;
        ispc::oracle_chain(const_cast<int64_t *>(x), lanes, out, 5);
        for (int lane = 0; lane < 8; ++lane) {
            int32_t r = 0;
            if (lanes[lane])
                for (int s = 0; s < 5; ++s)
                    r = reference(uint64_t(x[lane]) ^ uint64_t(int64_t(r)));
            expect(out[lane] == r, "chain", pattern * 8 + lane);
        }
    }

    if (failures) {
        std::printf("popcnt oracle: %d failures\n", failures);
        return 1;
    }
    std::printf("popcnt oracle passed (%d values, 256 masks, tails, nested, reduce, chain)\n", n);
    return 0;
}
