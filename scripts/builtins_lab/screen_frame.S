// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// Shared all-on 8i64 frame. Body reads rdi[0..63], returns eax=0/1.
// Bodies may clobber vector registers, rax, r9-r11 and flags only.
.text
.globl lab_kernel
.type lab_kernel,@function
.p2align 4
lab_kernel:
 testq %rcx,%rcx
 jz .Lexit
 testq %r8,%r8
 jz .Lexit
 pushq %rbx
 pushq %r12
 pushq %r13
 pushq %r14
 pushq %r15
 movq %rdi,%r12
 movq %rsi,%r13
 movq %rdx,%r14
 movq %rcx,%r15
 movq %r8,%rbx
.p2align 4
.Lrepeat:
 movq %r12,%rdi
 movq %r13,%rsi
 movq %r14,%rdx
 movq %r15,%rcx
.p2align 4
.Lgroup:
/* BODY_INSERTION_POINT */
 movl %eax,%eax
 movq %rax,(%rdx)
 testl %eax,%eax
 jz .Lnext
 movq (%rdi),%r9
 movq %r9,(%rsi)
.Lnext:
 addq $64,%rdi
 addq $8,%rsi
 addq $8,%rdx
 decq %rcx
 jnz .Lgroup
 decq %rbx
 jnz .Lrepeat
 vzeroupper
 popq %r15
 popq %r14
 popq %r13
 popq %r12
 popq %rbx
.Lexit:
 ret
.size lab_kernel,.-lab_kernel
.section .note.GNU-stack,"",@progbits
