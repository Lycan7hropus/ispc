// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
/*
 * popcnt_i64_avx2_lut.S - AVX2 nibble-lookup popcnt int64 (all-on T0 fixture)
 *
 * Linux x86-64 SysV ABI:
 * extern "C" void lab_kernel(const uint64_t *input,   // groups * 8 int64 lanes
 *                            int32_t *counts,         // groups * 8 int32 results
 *                            size_t groups,
 *                            size_t repeats);
 *
 * Hypothesis (positive control for the fixture, not a tuned candidate):
 * per-byte counts via two vpshufb nibble lookups, vpsadbw against zero to sum
 * the eight bytes of each qword, then pack the two ymm of qword counts into
 * eight dwords with vpsllq/vpor/vpermd. This is the well-known Mula
 * vpshufb method that CRoaring's AVX2 popcount builds on.
 * Hand-coded hypothesis fixture; not production ISPC compiler emitted code.
 * AVX2 only; uses vzeroupper at exit.
 */

    .section .rodata
    .p2align 5
.Lnibble_counts:
    .byte 0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4
    .byte 0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4
.Llow_nibble:
    .fill 32,1,0x0f
.Lpack_order:
    .long 0,2,4,6,1,3,5,7

    .text
    .globl lab_kernel
    .type lab_kernel, @function
    .p2align 4
lab_kernel:
    testq   %rdx, %rdx
    je      .Ldone
    testq   %rcx, %rcx
    je      .Ldone
    vmovdqa .Lnibble_counts(%rip), %ymm15
    vmovdqa .Llow_nibble(%rip), %ymm14
    vmovdqa .Lpack_order(%rip), %ymm12
    vpxor   %xmm13, %xmm13, %xmm13
.Lrepeat:
    movq    %rdi, %rax              # input cursor
    movq    %rsi, %r8               # output cursor
    movq    %rdx, %r9               # groups left
    .p2align 4
.Lgroup:
    vmovdqu (%rax), %ymm0           # lanes 0..3
    vmovdqu 32(%rax), %ymm1         # lanes 4..7
    vpand   %ymm14, %ymm0, %ymm2
    vpsrlw  $4, %ymm0, %ymm3
    vpand   %ymm14, %ymm3, %ymm3
    vpshufb %ymm2, %ymm15, %ymm2
    vpshufb %ymm3, %ymm15, %ymm3
    vpaddb  %ymm3, %ymm2, %ymm0
    vpsadbw %ymm13, %ymm0, %ymm0    # qword i = popcnt(lane i), i = 0..3
    vpand   %ymm14, %ymm1, %ymm4
    vpsrlw  $4, %ymm1, %ymm5
    vpand   %ymm14, %ymm5, %ymm5
    vpshufb %ymm4, %ymm15, %ymm4
    vpshufb %ymm5, %ymm15, %ymm5
    vpaddb  %ymm5, %ymm4, %ymm1
    vpsadbw %ymm13, %ymm1, %ymm1    # qword i = popcnt(lane 4 + i)
    vpsllq  $32, %ymm1, %ymm1
    vpor    %ymm1, %ymm0, %ymm0     # dwords: c0,c4,c1,c5,c2,c6,c3,c7
    vpermd  %ymm0, %ymm12, %ymm0    # dwords: c0..c7
    vmovdqu %ymm0, (%r8)
    addq    $64, %rax
    addq    $32, %r8
    decq    %r9
    jne     .Lgroup
    decq    %rcx
    jne     .Lrepeat
    vzeroupper
.Ldone:
    ret
    .size lab_kernel, .-lab_kernel
    .section .note.GNU-stack,"",@progbits
