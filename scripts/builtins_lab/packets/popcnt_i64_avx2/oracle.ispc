// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// popcnt(varying int64) oracle kernels: every caller shape of contexts.ispc, plus partial foreach tails.

export void oracle_all(uniform int64 src[], uniform int32 dst[], uniform int count) {
    foreach (i = 0 ... count) {
        dst[i] = popcnt(src[i]);
    }
}

export void oracle_even(uniform int64 src[], uniform int32 dst[], uniform int count) {
    foreach (i = 0 ... count) {
        int32 r = -1;
        if ((programIndex & 1) == 0)
            r = popcnt(src[i]);
        dst[i] = r;
    }
}

export void oracle_mask(uniform int64 src[], uniform int32 mask[], uniform int32 dst[], uniform int count) {
    foreach (i = 0 ... count) {
        int32 r = -1;
        if (mask[i] != 0)
            r = popcnt(src[i]);
        dst[i] = r;
    }
}

export void oracle_nested(uniform int64 src[], uniform int64 dst[], uniform int count) {
    foreach (i = 0 ... count) {
        dst[i] = popcnt(popcnt(src[i]));
    }
}

export uniform int64 oracle_reduce(uniform int64 src[], uniform int count) {
    int64 sum = 0;
    foreach (i = 0 ... count) {
        sum += popcnt(src[i]);
    }
    return reduce_add(sum);
}

export void oracle_chain(uniform int64 src[], uniform int32 mask[], uniform int32 dst[], uniform int steps) {
    int64 x = src[programIndex];
    int32 r = 0;
    if (mask[programIndex] != 0) {
        for (uniform int s = 0; s < steps; ++s)
            r = popcnt(x ^ (int64)r);
    }
    dst[programIndex] = r;
}
