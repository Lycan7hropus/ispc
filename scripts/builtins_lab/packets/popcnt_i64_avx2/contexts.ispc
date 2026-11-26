// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// popcnt(varying int64) caller contexts for T1 on avx2-i32x8. Each export is one caller shape:
//   official_*  benchmarks/01_trivial/03_popcnt.ispc varying int64 (8 nested popcnt; only the first is int64)
//   stream_*    one popcnt(int64) per element, store int32 (throughput), all-on / static even / runtime mask
//   reduce_all  Hamming weight of an array (popcnt accumulated in a varying int64, reduce_add at the end)
//   chain_*     r = popcnt(x ^ r) dependent chain in registers (latency incl. int32 -> int64 widening)
//   control_*   varying int32 and uniform int64 popcnt: not changed by an int64 varying builtin patch
#define POPCNT8(arg) popcnt(popcnt(popcnt(popcnt(popcnt(popcnt(popcnt(popcnt(arg))))))))

export void official_all(uniform int64 src[], uniform int64 dst[], uniform int count) {
    foreach (i = 0 ... count) {
        dst[i] = POPCNT8(src[i]);
    }
}

export void official_even(uniform int64 src[], uniform int64 dst[], uniform int count) {
    foreach (i = 0 ... count) {
        if ((programIndex & 1) == 0)
            dst[i] = POPCNT8(src[i]);
    }
}

export void stream_all(uniform int64 src[], uniform int32 dst[], uniform int count) {
    foreach (i = 0 ... count) {
        dst[i] = popcnt(src[i]);
    }
}

export void stream_even(uniform int64 src[], uniform int32 dst[], uniform int count) {
    foreach (i = 0 ... count) {
        if ((programIndex & 1) == 0)
            dst[i] = popcnt(src[i]);
    }
}

export void stream_mask(uniform int64 src[], uniform int32 mask[], uniform int32 dst[], uniform int count) {
    foreach (i = 0 ... count) {
        int32 r = 0;
        if (mask[i] != 0)
            r = popcnt(src[i]);
        dst[i] = r;
    }
}

export uniform int64 reduce_all(uniform int64 src[], uniform int count) {
    int64 sum = 0;
    foreach (i = 0 ... count) {
        sum += popcnt(src[i]);
    }
    return reduce_add(sum);
}

export void chain_all(uniform int64 src[], uniform int32 dst[], uniform int steps) {
    int64 x = src[programIndex];
    int32 r = 0;
    for (uniform int s = 0; s < steps; ++s)
        r = popcnt(x ^ (int64)r);
    dst[programIndex] = r;
}

export void chain_even(uniform int64 src[], uniform int32 dst[], uniform int steps) {
    int64 x = src[programIndex];
    int32 r = 0;
    if ((programIndex & 1) == 0) {
        for (uniform int s = 0; s < steps; ++s)
            r = popcnt(x ^ (int64)r);
    }
    dst[programIndex] = r;
}

export void control_int32(uniform int32 src[], uniform int32 dst[], uniform int count) {
    foreach (i = 0 ... count) {
        dst[i] = popcnt(src[i]);
    }
}

export void control_uniform_int64(uniform int64 src[], uniform int32 dst[], uniform int count) {
    for (uniform int i = 0; i < count; ++i)
        dst[i] = popcnt(src[i]);
}
