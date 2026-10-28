// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
/*
 * candidate.S - AVX2 native vector broadcast/compare/reduction for 8i64
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
 * Hypothesis: AVX2 vector broadcast/compare/reduction.
 * Note: Hand-coded hypothesis fixture; not production ISPC compiler emitted code.
 * AVX2 only; no AVX512. Uses vzeroupper at exit.
 */

    .text
    .globl lab_kernel
    .type lab_kernel, @function
    .p2align 4
lab_kernel:
    # Early exit if groups == 0 or repeats == 0
    testq   %rcx, %rcx
    jz      .Lcand_early_exit
    testq   %r8, %r8
    jz      .Lcand_early_exit

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
.Lcand_repeat_loop:
    movq    %r12, %rdi          # cur input ptr
    movq    %r13, %rsi          # cur values ptr
    movq    %r14, %rdx          # cur flags ptr
    movq    %r15, %rcx          # remaining groups

    .p2align 4
.Lcand_group_loop:
    # AVX2 broadcast/compare/reduction across 8 lanes (64 bytes)
    vmovdqu      0(%rdi), %ymm0     # lanes 0..3
    vmovdqu     32(%rdi), %ymm1     # lanes 4..7
    vpbroadcastq 0(%rdi), %ymm2     # broadcast lane 0 to 4 qwords

    vpcmpeqq    %ymm2, %ymm0, %ymm3 # compare lanes 0..3 with lane 0
    vpcmpeqq    %ymm2, %ymm1, %ymm4 # compare lanes 4..7 with lane 0
    vpand       %ymm3, %ymm4, %ymm5 # combine match masks

    # Check if all 4 qwords in ymm5 are all-ones (-1)
    vmovmskpd   %ymm5, %eax         # extract 4-bit sign mask
    cmpl        $15, %eax
    jne         .Lcand_not_equal

    # All 8 equal
    movq    $1, (%rdx)              # flags[g] = 1
    movq    0(%rdi), %rax           # lane 0 value
    movq    %rax, (%rsi)            # values[g] = input[g*8]
    jmp     .Lcand_next_group

    .p2align 4
.Lcand_not_equal:
    movq    $0, (%rdx)              # flags[g] = 0
    # values[g] is preserved unchanged

.Lcand_next_group:
    addq    $64, %rdi               # advance input (8 * 8 bytes)
    addq    $8,  %rsi               # advance values (1 * 8 bytes)
    addq    $8,  %rdx               # advance flags (1 * 8 bytes)
    decq    %rcx
    jnz     .Lcand_group_loop

    decq    %rbx
    jnz     .Lcand_repeat_loop

    vzeroupper

    # Restore callee-saved registers
    popq    %r15
    popq    %r14
    popq    %r13
    popq    %r12
    popq    %rbx

.Lcand_early_exit:
    ret

    .size lab_kernel, .-lab_kernel
    .section .note.GNU-stack,"",@progbits
