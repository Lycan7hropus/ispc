// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// popcnt(varying int64) T0 kernel (avx2-i32x8, 8 lanes) for both popcnt fixtures: lab_kernel
// (popcnt-i64, all-on) and lab_popcnt* (popcnt-i64-masks, screen_popcnt_masks_kernel.cpp).
// Needs clang 19+ (__builtin_elementwise_popcount).
// Reference: llvm.ctpop on 8 x i64 + trunc to 8 x i32 (what a plain vector ctpop builtin gives on
// AVX2: LLVM's vpshufb lookup, vpaddb, vpsadbw against zero, then packing).
#include <cstddef>
#include <cstdint>
#include <immintrin.h>

typedef uint64_t u64x8 __attribute__((ext_vector_type(8)));
typedef uint32_t u32x8 __attribute__((ext_vector_type(8)));
typedef uint64_t u64x4 __attribute__((ext_vector_type(4)));

static inline __m256i popcnt8(__m256i v0, __m256i v1) {
    u64x8 value = __builtin_shufflevector((u64x4)v0, (u64x4)v1, 0, 1, 2, 3, 4, 5, 6, 7);
    u32x8 counts = __builtin_convertvector(__builtin_elementwise_popcount(value), u32x8);
    return (__m256i)counts;
}

static inline __m256i popcnt8_even(__m256i v0, __m256i v1) {
    return _mm256_blend_epi32(popcnt8(v0, v1), _mm256_setzero_si256(), 0xaa);
}

// Common frame (identical in every popcnt T0 kernel): runtime mask, compile-time even mask, chain.
static inline __m256i activeOnly(__m256i result, __m256i mask) {
    // ISPC generic select "mask ? r : 0" -> vpcmpeqd + vpandn.
    return _mm256_andnot_si256(_mm256_cmpeq_epi32(mask, _mm256_setzero_si256()), result);
}

extern "C" void lab_popcnt(const uint64_t *input, const int32_t *mask, int32_t *out, size_t groups, size_t repeats) {
    for (size_t r = 0; r < repeats; ++r) {
        asm volatile("" ::: "memory");
        for (size_t g = 0; g < groups; ++g) {
            __m256i v0 = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(input + g * 8));
            __m256i v1 = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(input + g * 8 + 4));
            __m256i m = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(mask + g * 8));
            _mm256_storeu_si256(reinterpret_cast<__m256i *>(out + g * 8), activeOnly(popcnt8(v0, v1), m));
        }
    }
}

extern "C" void lab_popcnt_even(const uint64_t *input, const int32_t *, int32_t *out, size_t groups, size_t repeats) {
    for (size_t r = 0; r < repeats; ++r) {
        asm volatile("" ::: "memory");
        for (size_t g = 0; g < groups; ++g) {
            __m256i v0 = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(input + g * 8));
            __m256i v1 = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(input + g * 8 + 4));
            _mm256_storeu_si256(reinterpret_cast<__m256i *>(out + g * 8), popcnt8_even(v0, v1));
        }
    }
}

extern "C" void lab_popcnt_chain(const uint64_t *input, const int32_t *mask, int32_t *out, size_t groups,
                                 size_t repeats) {
    for (size_t r = 0; r < repeats; ++r) {
        asm volatile("" ::: "memory");
        __m256i previous = _mm256_setzero_si256();
        for (size_t g = 0; g < groups; ++g) {
            __m256i v0 = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(input + g * 8));
            __m256i v1 = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(input + g * 8 + 4));
            __m256i m = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(mask + g * 8));
            // ISPC: (int64)r zero-extends the non-negative int32 count.
            v0 = _mm256_xor_si256(v0, _mm256_cvtepu32_epi64(_mm256_castsi256_si128(previous)));
            v1 = _mm256_xor_si256(v1, _mm256_cvtepu32_epi64(_mm256_extracti128_si256(previous, 1)));
            previous = activeOnly(popcnt8(v0, v1), m);
            _mm256_storeu_si256(reinterpret_cast<__m256i *>(out + g * 8), previous);
        }
    }
}

// All-on popcnt-i64 fixture ABI (screen_popcnt_kernel.cpp), so one candidate file serves both fixtures.
extern "C" void lab_kernel(const uint64_t *input, int32_t *counts, size_t groups, size_t repeats) {
    for (size_t r = 0; r < repeats; ++r) {
        asm volatile("" ::: "memory");
        for (size_t g = 0; g < groups; ++g) {
            __m256i v0 = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(input + g * 8));
            __m256i v1 = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(input + g * 8 + 4));
            _mm256_storeu_si256(reinterpret_cast<__m256i *>(counts + g * 8), popcnt8(v0, v1));
        }
    }
}
