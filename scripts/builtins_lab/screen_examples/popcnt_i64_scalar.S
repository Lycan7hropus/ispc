// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
/*
 * popcnt_i64_scalar.S - baseline popcnt int64 (all-on T0 fixture)
 *
 * Linux x86-64 SysV ABI:
 * extern "C" void lab_kernel(const uint64_t *input,   // groups * 8 int64 lanes
 *                            int32_t *counts,         // groups * 8 int32 results
 *                            size_t groups,
 *                            size_t repeats);
 *
 * The .Lgroup body is, instruction for instruction, the loop ISPC 1.33.0dev
 * (LLVM 20.1.2) emits for
 *   foreach (i = 0 ... n) dst[i] = popcnt(src[i]);
 * with --target=avx2-i32x8 -O2: eight scalar popcntq with memory operands
 * (each after a dependency-breaking xorl), vmovd/vpinsrd assembly of two xmm
 * halves and two 16-byte stores, indexed by a lane counter.
 * Only the limit register differs (r13 here, rcx in ISPC: rcx holds repeats).
 * Register-resident callers extract with vmovq/vpextrq before popcntq
 * instead; that lowering is not modeled by this baseline.
 */

    .text
    .globl lab_kernel
    .type lab_kernel, @function
    .p2align 4
lab_kernel:
    testq   %rdx, %rdx
    je      .Ldone
    testq   %rcx, %rcx
    je      .Ldone
    pushq   %r15
    pushq   %r14
    pushq   %r13
    pushq   %r12
    pushq   %rbx
    leaq    (,%rdx,8), %r13         # lane limit = groups * 8
.Lrepeat:
    xorl    %eax, %eax
    .p2align 4
.Lgroup:
    xorl    %r8d, %r8d
    popcntq (%rdi,%rax,8), %r8
    xorl    %r9d, %r9d
    popcntq 8(%rdi,%rax,8), %r9
    xorl    %r10d, %r10d
    popcntq 16(%rdi,%rax,8), %r10
    xorl    %r11d, %r11d
    popcntq 24(%rdi,%rax,8), %r11
    xorl    %ebx, %ebx
    popcntq 32(%rdi,%rax,8), %rbx
    xorl    %r14d, %r14d
    popcntq 40(%rdi,%rax,8), %r14
    xorl    %r15d, %r15d
    popcntq 48(%rdi,%rax,8), %r15
    xorl    %r12d, %r12d
    popcntq 56(%rdi,%rax,8), %r12
    vmovd   %r8d, %xmm0
    vpinsrd $1, %r9d, %xmm0, %xmm0
    vpinsrd $2, %r10d, %xmm0, %xmm0
    vpinsrd $3, %r11d, %xmm0, %xmm0
    vmovd   %ebx, %xmm1
    vpinsrd $1, %r14d, %xmm1, %xmm1
    vpinsrd $2, %r15d, %xmm1, %xmm1
    vpinsrd $3, %r12d, %xmm1, %xmm1
    vmovdqu %xmm1, 16(%rsi,%rax,4)
    vmovdqu %xmm0, (%rsi,%rax,4)
    addq    $8, %rax
    cmpq    %r13, %rax
    jb      .Lgroup
    decq    %rcx
    jne     .Lrepeat
    popq    %rbx
    popq    %r12
    popq    %r13
    popq    %r14
    popq    %r15
.Ldone:
    ret
    .size lab_kernel, .-lab_kernel
    .section .note.GNU-stack,"",@progbits
