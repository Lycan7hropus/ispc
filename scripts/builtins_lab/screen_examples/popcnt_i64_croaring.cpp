// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// popcnt(varying int64) T0 kernel (avx2-i32x8, 8 lanes) for both popcnt fixtures: lab_kernel
// (popcnt-i64, all-on) and lab_popcnt* (popcnt-i64-masks, screen_popcnt_masks_kernel.cpp).
// Candidate: CRoaring two-table nibble lookup (vpshufb) + vpsadbw per 4 x int64, then the two
// 4 x i64 count vectors are packed to 8 x int32 with vshufps + vpermq.
#include <cstddef>
#include <cstdint>
#include <immintrin.h>

// CRoaring (Lemire et al.): lookup tables hold 4 + popcount(nibble) and 4 - popcount(nibble), so
// vpsadbw(pos[low nibble], neg[high nibble]) = sum(pc(lo) + pc(hi)) per 64-bit lane: no vpaddb.
static inline __m256i croaring4(__m256i v) {
    const __m256i positive = _mm256_setr_epi8(4, 5, 5, 6, 5, 6, 6, 7, 5, 6, 6, 7, 6, 7, 7, 8, 4, 5, 5, 6, 5, 6, 6, 7, 5,
                                              6, 6, 7, 6, 7, 7, 8);
    const __m256i negative = _mm256_setr_epi8(4, 3, 3, 2, 3, 2, 2, 1, 3, 2, 2, 1, 2, 1, 1, 0, 4, 3, 3, 2, 3, 2, 2, 1, 3,
                                              2, 2, 1, 2, 1, 1, 0);
    const __m256i nibble = _mm256_set1_epi8(0x0f);
    __m256i low = _mm256_and_si256(v, nibble);
    __m256i high = _mm256_and_si256(_mm256_srli_epi16(v, 4), nibble);
    return _mm256_sad_epu8(_mm256_shuffle_epi8(positive, low), _mm256_shuffle_epi8(negative, high));
}

static inline __m256i pack(__m256i low, __m256i high) {
    // Counts sit in the low dword of every qword: [l0 l1 h0 h1 | l2 l3 h2 h3] -> [l0..l3 h0..h3].
    __m256 packed = _mm256_shuffle_ps(_mm256_castsi256_ps(low), _mm256_castsi256_ps(high), _MM_SHUFFLE(2, 0, 2, 0));
    return _mm256_permute4x64_epi64(_mm256_castps_si256(packed), _MM_SHUFFLE(3, 1, 2, 0));
}

static inline __m256i popcnt8(__m256i v0, __m256i v1) { return pack(croaring4(v0), croaring4(v1)); }

static inline __m256i popcnt8_even(__m256i v0, __m256i v1) {
    // A vector builtin cannot skip lanes: full count, then ISPC's constant select keeps lanes 0,2,4,6.
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
