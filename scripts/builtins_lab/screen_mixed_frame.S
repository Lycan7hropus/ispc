// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// Mixed 8i64 frame, proper partial masks only. Sign bits define activity.
// ABI: input, masks, values, flags, groups, repeats (SysV six arguments).
// Body: ymm0/1=input, ymm2=8xi32 mask, ymm3=splat(first active i64).
// Returns eax=0/1; clobbers vector registers, rax,r10,r11,flags only.
.text
.globl lab_kernel
.type lab_kernel,@function
.p2align 4
lab_kernel:
 testq %r8,%r8
 jz .Lexit
 testq %r9,%r9
 jz .Lexit
 pushq %rbx
 pushq %rbp
 pushq %r12
 pushq %r13
 pushq %r14
 pushq %r15
 movq %rdi,%r12
 movq %rsi,%r13
 movq %rdx,%r14
 movq %rcx,%r15
 movq %r8,%rbx
 movq %r9,%rbp
.p2align 4
.Lrepeat:
 movq %r12,%rdi
 movq %r13,%rsi
 movq %r14,%rdx
 movq %r15,%rcx
 movq %rbx,%r8
.p2align 4
.Lgroup:
 vmovdqu (%rdi),%ymm0
 vmovdqu 32(%rdi),%ymm1
 vmovdqu (%rsi),%ymm2
 vmovmskps %ymm2,%eax
 bsfl %eax,%eax
 movq (%rdi,%rax,8),%r9
 vmovq %r9,%xmm3
 vpbroadcastq %xmm3,%ymm3
/* BODY_INSERTION_POINT */
 movl %eax,%eax
 movq %rax,(%rcx)
 testl %eax,%eax
 jz .Lnext
 movq %r9,(%rdx)
.Lnext:
 addq $64,%rdi
 addq $32,%rsi
 addq $8,%rdx
 addq $8,%rcx
 decq %r8
 jnz .Lgroup
 decq %rbp
 jnz .Lrepeat
 vzeroupper
 popq %r15
 popq %r14
 popq %r13
 popq %r12
 popq %rbp
 popq %rbx
.Lexit:
 ret
.size lab_kernel,.-lab_kernel
.section .note.GNU-stack,"",@progbits
