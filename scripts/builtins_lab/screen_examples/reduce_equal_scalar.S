// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
/*
 * baseline.S - Scalar reduce_equal int64 (all-on mask T0 fixture)
 *
 * Linux x86-64 SysV ABI:
 * extern "C" void lab_kernel(const uint64_t *input,
 *                            uint64_t *values,
 *                            uint64_t *flags,
 *                            size_t groups,
 *                            size_t repeats);
 *
 * Register convention:
 *   rdi: input (groups * 8 uint64_t)
 *   rsi: values (groups uint64_t)
 *   rdx: flags (groups uint64_t)
 *   rcx: groups
 *   r8 : repeats
 *
 * Hypothesis: Scalar extract/xor/or equality representation.
 * Note: Hand-coded hypothesis fixture; not production ISPC compiler emitted code.
 */

    .text
    .globl lab_kernel
    .type lab_kernel, @function
    .p2align 4
lab_kernel:
    # Early exit if groups == 0 or repeats == 0
    testq   %rcx, %rcx
    jz      .Lbase_early_exit
    testq   %r8, %r8
    jz      .Lbase_early_exit

    # Preserve callee-saved registers (5 * 8 = 40 bytes -> RSP 16-byte aligned)
    pushq   %rbx
    pushq   %r12
    pushq   %r13
    pushq   %r14
    pushq   %r15

    movq    %rdi, %r12          # base input pointer
    movq    %rsi, %r13          # base values pointer
    movq    %rdx, %r14          # base flags pointer
    movq    %rcx, %r15          # groups count
    movq    %r8,  %rbx          # repeat counter

    .p2align 4
.Lbase_repeat_loop:
    movq    %r12, %rdi          # cur input ptr
    movq    %r13, %rsi          # cur values ptr
    movq    %r14, %rdx          # cur flags ptr
    movq    %r15, %rcx          # remaining groups

    .p2align 4
.Lbase_group_loop:
    # Scalar extract/xor/or equality cost across 8 lanes
    movq     0(%rdi), %rax      # lane 0
    movq     8(%rdi), %r8       # lane 1
    xorq    %rax, %r8           # diff = lane 0 ^ lane 1

    movq    16(%rdi), %r9       # lane 2
    xorq    %rax, %r9
    orq     %r9, %r8

    movq    24(%rdi), %r10      # lane 3
    xorq    %rax, %r10
    orq     %r10, %r8

    movq    32(%rdi), %r11      # lane 4
    xorq    %rax, %r11
    orq     %r11, %r8

    movq    40(%rdi), %r9       # lane 5
    xorq    %rax, %r9
    orq     %r9, %r8

    movq    48(%rdi), %r10      # lane 6
    xorq    %rax, %r10
    orq     %r10, %r8

    movq    56(%rdi), %r11      # lane 7
    xorq    %rax, %r11
    orq     %r11, %r8

    testq   %r8, %r8
    jnz     .Lbase_not_equal

    # All 8 equal
    movq    $1, (%rdx)          # flags[g] = 1
    movq    %rax, (%rsi)        # values[g] = input[g*8]
    jmp     .Lbase_next_group

    .p2align 4
.Lbase_not_equal:
    movq    $0, (%rdx)          # flags[g] = 0
    # values[g] is preserved unchanged

.Lbase_next_group:
    addq    $64, %rdi           # advance input (8 * 8 bytes)
    addq    $8,  %rsi           # advance values (1 * 8 bytes)
    addq    $8,  %rdx           # advance flags (1 * 8 bytes)
    decq    %rcx
    jnz     .Lbase_group_loop

    decq    %rbx
    jnz     .Lbase_repeat_loop

    # Restore callee-saved registers
    popq    %r15
    popq    %r14
    popq    %r13
    popq    %r12
    popq    %rbx

.Lbase_early_exit:
    ret

    .size lab_kernel, .-lab_kernel
    .section .note.GNU-stack,"",@progbits
