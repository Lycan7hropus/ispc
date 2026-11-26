// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// Source of the ISPC-generated popcnt T0 kernels (popcnt_i64_ispc.S with stock ISPC, candidates with a
// patched ISPC). Regenerate with:
//   ispc --target=avx2-i32x8 --arch=x86-64 -O2 --pic --emit-asm popcnt_i64_kernels.ispc -o <name>.S
// Exports both popcnt fixture ABIs:
//   lab_kernel                      popcnt-i64 (all-on), inlined popcnt in a load/store loop
//   lab_popcnt / lab_popcnt_chain   popcnt-i64-masks, runtime mask: popcnt in a noinline function, so
//                                   the value arrives in ymm0/ymm1 and the mask in ymm2 (register form)
//   lab_popcnt_even                 popcnt-i64-masks, compile-time even mask, inlined

static noinline int32 popcnt_runtime(int64 value) { return popcnt(value); }

export void lab_kernel(uniform int64 input[], uniform int32 counts[], uniform int64 groups, uniform int64 repeats) {
    for (uniform int64 r = 0; r < repeats; ++r)
        for (uniform int64 g = 0; g < groups; ++g)
            counts[g * 8 + programIndex] = popcnt(input[g * 8 + programIndex]);
}

export void lab_popcnt(uniform int64 input[], uniform int32 mask[], uniform int32 out[], uniform int64 groups,
                       uniform int64 repeats) {
    for (uniform int64 r = 0; r < repeats; ++r)
        for (uniform int64 g = 0; g < groups; ++g) {
            int64 value = input[g * 8 + programIndex];
            int32 result = 0;
            if (mask[g * 8 + programIndex] != 0)
                result = popcnt_runtime(value);
            out[g * 8 + programIndex] = result;
        }
}

export void lab_popcnt_even(uniform int64 input[], uniform int32 mask[], uniform int32 out[], uniform int64 groups,
                            uniform int64 repeats) {
    for (uniform int64 r = 0; r < repeats; ++r)
        for (uniform int64 g = 0; g < groups; ++g) {
            int32 result = 0;
            if ((programIndex & 1) == 0)
                result = popcnt(input[g * 8 + programIndex]);
            out[g * 8 + programIndex] = result;
        }
}

export void lab_popcnt_chain(uniform int64 input[], uniform int32 mask[], uniform int32 out[], uniform int64 groups,
                             uniform int64 repeats) {
    for (uniform int64 r = 0; r < repeats; ++r) {
        int32 previous = 0;
        for (uniform int64 g = 0; g < groups; ++g) {
            int64 value = input[g * 8 + programIndex] ^ (int64)previous;
            int32 result = 0;
            if (mask[g * 8 + programIndex] != 0)
                result = popcnt_runtime(value);
            out[g * 8 + programIndex] = result;
            previous = result;
        }
    }
}
