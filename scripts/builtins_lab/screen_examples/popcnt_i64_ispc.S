/* Copyright (c) 2026, Intel Corporation
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Generated from popcnt_i64_kernels.ispc by stock ISPC
 * (1.33.0dev, builtins/optimization-lab-wip e38083ae, LLVM 20.1.8):
 *   ispc --target=avx2-i32x8 --arch=x86-64 -O2 --pic --emit-asm popcnt_i64_kernels.ispc -o popcnt_i64_ispc.S
 * Do not edit; regenerate. */
	.file	"popcnt_i64_kernels.ispc"
	.text
	.p2align	4                               # -- Begin function popcnt_runtime___vyI
	.type	popcnt_runtime___vyI,@function
popcnt_runtime___vyI:                   # @popcnt_runtime___vyI
# %bb.0:
	vmovq	%xmm0, %rax
	popcntq	%rax, %rax
	vpextrq	$1, %xmm0, %rcx
	popcntq	%rcx, %rcx
	vextracti128	$1, %ymm0, %xmm0
	vmovq	%xmm0, %rdx
	popcntq	%rdx, %rdx
	vpextrq	$1, %xmm0, %rsi
	vmovq	%xmm1, %rdi
	popcntq	%rdi, %rdi
	vpextrq	$1, %xmm1, %r8
	popcntq	%r8, %r8
	vextracti128	$1, %ymm1, %xmm0
	vmovq	%xmm0, %r9
	popcntq	%r9, %r9
	vpextrq	$1, %xmm0, %r10
	popcntq	%r10, %r10
	vmovd	%edi, %xmm0
	vpinsrd	$1, %r8d, %xmm0, %xmm0
	vpinsrd	$2, %r9d, %xmm0, %xmm0
	vpinsrd	$3, %r10d, %xmm0, %xmm0
	popcntq	%rsi, %rsi
	vmovd	%eax, %xmm1
	vpinsrd	$1, %ecx, %xmm1, %xmm1
	vpinsrd	$2, %edx, %xmm1, %xmm1
	vpinsrd	$3, %esi, %xmm1, %xmm1
	vinserti128	$1, %xmm0, %ymm1, %ymm0
	vpxor	%xmm1, %xmm1, %xmm1
	vpcmpeqd	%ymm1, %ymm2, %ymm1
	vpandn	%ymm0, %ymm1, %ymm0
	retq
.Lfunc_end0:
	.size	popcnt_runtime___vyI, .Lfunc_end0-popcnt_runtime___vyI
                                        # -- End function
	.globl	lab_kernel___un_3C_unI_3E_un_3C_uni_3E_unIunI # -- Begin function lab_kernel___un_3C_unI_3E_un_3C_uni_3E_unIunI
	.p2align	4
	.type	lab_kernel___un_3C_unI_3E_un_3C_uni_3E_unIunI,@function
lab_kernel___un_3C_unI_3E_un_3C_uni_3E_unIunI: # @lab_kernel___un_3C_unI_3E_un_3C_uni_3E_unIunI
# %bb.0:
	pushq	%rbp
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	vpcmpeqd	%ymm1, %ymm1, %ymm1
	vtestps	%ymm1, %ymm0
	movq	%rdx, -8(%rsp)                  # 8-byte Spill
	movq	%rcx, -16(%rsp)                 # 8-byte Spill
	jb	.LBB1_7
# %bb.1:
	testq	%rcx, %rcx
	jle	.LBB1_12
# %bb.2:
	testq	%rdx, %rdx
	jle	.LBB1_12
# %bb.3:
	vpermpd	$216, %ymm0, %ymm2              # ymm2 = ymm0[0,2,1,3]
	vshufps	$80, %ymm2, %ymm2, %ymm1        # ymm1 = ymm2[0,0,1,1,4,4,5,5]
	vshufps	$250, %ymm2, %ymm2, %ymm2       # ymm2 = ymm2[2,2,3,3,6,6,7,7]
	xorl	%ecx, %ecx
	vpxor	%xmm3, %xmm3, %xmm3
	vpcmpeqd	%ymm3, %ymm0, %ymm3
	.p2align	4
.LBB1_4:                                # =>This Loop Header: Depth=1
                                        #     Child Loop BB1_5 Depth 2
	xorl	%r8d, %r8d
	xorl	%r9d, %r9d
	movq	%rdx, %r10
	.p2align	4
.LBB1_5:                                #   Parent Loop BB1_4 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%r9d, %r9
	vmaskmovpd	(%rdi,%r9), %ymm1, %ymm4
	vmaskmovpd	32(%rdi,%r9), %ymm2, %ymm5
	vmovq	%xmm4, %r11
	popcntq	%r11, %r11
	vpextrq	$1, %xmm4, %rbx
	popcntq	%rbx, %rbx
	vextracti128	$1, %ymm4, %xmm4
	vmovq	%xmm4, %r14
	popcntq	%r14, %r14
	vpextrq	$1, %xmm4, %r15
	vmovq	%xmm5, %r12
	popcntq	%r12, %r12
	vpextrq	$1, %xmm5, %r13
	popcntq	%r13, %r13
	vextracti128	$1, %ymm5, %xmm4
	vmovq	%xmm4, %rbp
	popcntq	%rbp, %rbp
	vpextrq	$1, %xmm4, %rax
	popcntq	%rax, %rax
	vmovd	%r12d, %xmm4
	vpinsrd	$1, %r13d, %xmm4, %xmm4
	vpinsrd	$2, %ebp, %xmm4, %xmm4
	vpinsrd	$3, %eax, %xmm4, %xmm4
	xorl	%eax, %eax
	popcntq	%r15, %rax
	vmovd	%r11d, %xmm5
	vpinsrd	$1, %ebx, %xmm5, %xmm5
	vpinsrd	$2, %r14d, %xmm5, %xmm5
	vpinsrd	$3, %eax, %xmm5, %xmm5
	vinserti128	$1, %xmm4, %ymm5, %ymm4
	vpandn	%ymm4, %ymm3, %ymm4
	movslq	%r8d, %r8
	vmaskmovps	%ymm4, %ymm0, (%rsi,%r8)
	addl	$64, %r9d
	addl	$32, %r8d
	decq	%r10
	jne	.LBB1_5
# %bb.6:                                #   in Loop: Header=BB1_4 Depth=1
	incq	%rcx
	cmpq	-16(%rsp), %rcx                 # 8-byte Folded Reload
	movq	-8(%rsp), %rdx                  # 8-byte Reload
	jne	.LBB1_4
	jmp	.LBB1_12
.LBB1_7:
	testq	%rcx, %rcx
	setg	%al
	testq	%rdx, %rdx
	setg	%cl
	andb	%al, %cl
	cmpb	$1, %cl
	jne	.LBB1_12
# %bb.8:
	xorl	%eax, %eax
	.p2align	4
.LBB1_9:                                # =>This Loop Header: Depth=1
                                        #     Child Loop BB1_10 Depth 2
	xorl	%r8d, %r8d
	xorl	%r9d, %r9d
	movq	%rdx, %r10
	.p2align	4
.LBB1_10:                               #   Parent Loop BB1_9 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%r9d, %r9
	xorl	%edx, %edx
	popcntq	(%rdi,%r9), %rdx
	xorl	%r11d, %r11d
	popcntq	8(%rdi,%r9), %r11
	xorl	%ebx, %ebx
	popcntq	16(%rdi,%r9), %rbx
	xorl	%r14d, %r14d
	popcntq	24(%rdi,%r9), %r14
	xorl	%r15d, %r15d
	popcntq	32(%rdi,%r9), %r15
	xorl	%r12d, %r12d
	popcntq	40(%rdi,%r9), %r12
	xorl	%r13d, %r13d
	popcntq	48(%rdi,%r9), %r13
	xorl	%ebp, %ebp
	popcntq	56(%rdi,%r9), %rbp
	vmovd	%edx, %xmm0
	vpinsrd	$1, %r11d, %xmm0, %xmm0
	vpinsrd	$2, %ebx, %xmm0, %xmm0
	vpinsrd	$3, %r14d, %xmm0, %xmm0
	vmovd	%r15d, %xmm1
	vpinsrd	$1, %r12d, %xmm1, %xmm1
	vpinsrd	$2, %r13d, %xmm1, %xmm1
	vpinsrd	$3, %ebp, %xmm1, %xmm1
	movslq	%r8d, %r8
	vmovdqu	%xmm1, 16(%rsi,%r8)
	vmovdqu	%xmm0, (%rsi,%r8)
	addl	$64, %r9d
	addl	$32, %r8d
	decq	%r10
	jne	.LBB1_10
# %bb.11:                               #   in Loop: Header=BB1_9 Depth=1
	incq	%rax
	cmpq	-16(%rsp), %rax                 # 8-byte Folded Reload
	movq	-8(%rsp), %rdx                  # 8-byte Reload
	jne	.LBB1_9
.LBB1_12:
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	vzeroupper
	retq
.Lfunc_end1:
	.size	lab_kernel___un_3C_unI_3E_un_3C_uni_3E_unIunI, .Lfunc_end1-lab_kernel___un_3C_unI_3E_un_3C_uni_3E_unIunI
                                        # -- End function
	.section	.rodata.cst32,"aM",@progbits,32
	.p2align	5, 0x0                          # -- Begin function lab_popcnt___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
.LCPI2_0:
	.zero	32
.LCPI2_1:
	.zero	32,255
	.text
	.globl	lab_popcnt___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
	.p2align	4
	.type	lab_popcnt___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI,@function
lab_popcnt___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI: # @lab_popcnt___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
# %bb.0:
	pushq	%rbp
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	subq	$168, %rsp
	vmovdqa	%ymm0, %ymm3
	movq	%rcx, %rbp
	movq	%rdx, %r15
	movq	%rsi, %r12
	movq	%rdi, %r13
	vpcmpeqd	%ymm0, %ymm0, %ymm0
	vtestps	%ymm0, %ymm3
	movq	%r8, 16(%rsp)                   # 8-byte Spill
	movq	%rcx, 8(%rsp)                   # 8-byte Spill
	jb	.LBB2_10
# %bb.1:
	testq	%r8, %r8
	jle	.LBB2_18
# %bb.2:
	testq	%rbp, %rbp
	jle	.LBB2_18
# %bb.3:
	vpermq	$216, %ymm3, %ymm0              # ymm0 = ymm3[0,2,1,3]
	vpshufd	$250, %ymm0, %ymm1              # ymm1 = ymm0[2,2,3,3,6,6,7,7]
	vmovdqu	%ymm1, 128(%rsp)                # 32-byte Spill
	vpshufd	$80, %ymm0, %ymm0               # ymm0 = ymm0[0,0,1,1,4,4,5,5]
	vmovdqu	%ymm0, 96(%rsp)                 # 32-byte Spill
	xorl	%eax, %eax
	vmovups	%ymm3, 32(%rsp)                 # 32-byte Spill
	jmp	.LBB2_4
	.p2align	4
.LBB2_9:                                #   in Loop: Header=BB2_4 Depth=1
	movq	24(%rsp), %rax                  # 8-byte Reload
	incq	%rax
	cmpq	16(%rsp), %rax                  # 8-byte Folded Reload
	movq	8(%rsp), %rbp                   # 8-byte Reload
	je	.LBB2_18
.LBB2_4:                                # =>This Loop Header: Depth=1
                                        #     Child Loop BB2_5 Depth 2
	movq	%rax, 24(%rsp)                  # 8-byte Spill
	xorl	%r14d, %r14d
	xorl	%ebx, %ebx
	jmp	.LBB2_5
	.p2align	4
.LBB2_7:                                #   in Loop: Header=BB2_5 Depth=2
	vpxor	.LCPI2_1(%rip), %ymm0, %ymm1
	vextracti128	$1, %ymm1, %xmm2
	vpackssdw	%xmm2, %xmm1, %xmm1
	vmovdqa	%xmm1, 64(%rsp)                 # 16-byte Spill
	movslq	%ebx, %rax
	vmovupd	128(%rsp), %ymm1                # 32-byte Reload
	vmaskmovpd	32(%r13,%rax), %ymm1, %ymm1
	vpandn	%ymm3, %ymm0, %ymm2
	vmovupd	96(%rsp), %ymm0                 # 32-byte Reload
	vmaskmovpd	(%r13,%rax), %ymm0, %ymm0
	callq	popcnt_runtime___vyI
	vmovups	32(%rsp), %ymm3                 # 32-byte Reload
	vpmovsxwd	64(%rsp), %ymm1         # 16-byte Folded Reload
	vpand	%ymm0, %ymm1, %ymm0
.LBB2_8:                                #   in Loop: Header=BB2_5 Depth=2
	vmaskmovps	%ymm0, %ymm3, (%r15,%r14)
	addl	$64, %ebx
	addl	$32, %r14d
	decq	%rbp
	je	.LBB2_9
.LBB2_5:                                #   Parent Loop BB2_4 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%r14d, %r14
	vmaskmovps	(%r12,%r14), %ymm3, %ymm0
	vpcmpeqd	.LCPI2_0(%rip), %ymm0, %ymm0
	vtestps	%ymm3, %ymm0
	jae	.LBB2_7
# %bb.6:                                #   in Loop: Header=BB2_5 Depth=2
	vpxor	%xmm0, %xmm0, %xmm0
	jmp	.LBB2_8
.LBB2_10:
	testq	%r8, %r8
	setg	%al
	testq	%rbp, %rbp
	setg	%dl
	andb	%al, %dl
	cmpb	$1, %dl
	jne	.LBB2_18
# %bb.11:
	xorl	%eax, %eax
	jmp	.LBB2_12
	.p2align	4
.LBB2_17:                               #   in Loop: Header=BB2_12 Depth=1
	movq	32(%rsp), %rax                  # 8-byte Reload
	incq	%rax
	cmpq	16(%rsp), %rax                  # 8-byte Folded Reload
	movq	8(%rsp), %rbp                   # 8-byte Reload
	je	.LBB2_18
.LBB2_12:                               # =>This Loop Header: Depth=1
                                        #     Child Loop BB2_13 Depth 2
	movq	%rax, 32(%rsp)                  # 8-byte Spill
	xorl	%ebx, %ebx
	xorl	%r14d, %r14d
	jmp	.LBB2_13
	.p2align	4
.LBB2_15:                               #   in Loop: Header=BB2_13 Depth=2
	movslq	%r14d, %rax
	vpcmpeqd	.LCPI2_0(%rip), %ymm0, %ymm0
	vmovdqu	%ymm0, 64(%rsp)                 # 32-byte Spill
	vpxor	.LCPI2_1(%rip), %ymm0, %ymm2
	vmovdqu	(%r13,%rax), %ymm0
	vmovups	32(%r13,%rax), %ymm1
	callq	popcnt_runtime___vyI
	vmovdqu	64(%rsp), %ymm1                 # 32-byte Reload
	vpandn	%ymm0, %ymm1, %ymm0
.LBB2_16:                               #   in Loop: Header=BB2_13 Depth=2
	vmovdqu	%ymm0, (%r15,%rbx)
	addl	$64, %r14d
	addl	$32, %ebx
	decq	%rbp
	je	.LBB2_17
.LBB2_13:                               #   Parent Loop BB2_12 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%ebx, %rbx
	vmovdqu	(%r12,%rbx), %ymm0
	vptest	%ymm0, %ymm0
	jne	.LBB2_15
# %bb.14:                               #   in Loop: Header=BB2_13 Depth=2
	vpxor	%xmm0, %xmm0, %xmm0
	jmp	.LBB2_16
.LBB2_18:
	addq	$168, %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	vzeroupper
	retq
.Lfunc_end2:
	.size	lab_popcnt___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI, .Lfunc_end2-lab_popcnt___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
                                        # -- End function
	.section	.rodata.cst16,"aM",@progbits,16
	.p2align	4, 0x0                          # -- Begin function lab_popcnt_even___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
.LCPI3_0:
	.quad	-1                              # 0xffffffffffffffff
	.quad	0                               # 0x0
	.text
	.globl	lab_popcnt_even___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
	.p2align	4
	.type	lab_popcnt_even___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI,@function
lab_popcnt_even___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI: # @lab_popcnt_even___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
# %bb.0:
	pushq	%r15
	pushq	%r14
	pushq	%rbx
	vpcmpeqd	%ymm1, %ymm1, %ymm1
	vtestps	%ymm1, %ymm0
	jb	.LBB3_17
# %bb.1:
	testq	%r8, %r8
	jle	.LBB3_22
# %bb.2:
	testq	%rcx, %rcx
	jle	.LBB3_22
# %bb.3:
	vxorps	%xmm1, %xmm1, %xmm1
	vblendps	$170, %ymm1, %ymm0, %ymm4       # ymm4 = ymm0[0],ymm1[1],ymm0[2],ymm1[3],ymm0[4],ymm1[5],ymm0[6],ymm1[7]
	vtestps	%ymm4, %ymm4
	je	.LBB3_8
# %bb.4:
	vpermpd	$216, %ymm4, %ymm2              # ymm2 = ymm4[0,2,1,3]
	vshufps	$80, %ymm2, %ymm2, %ymm1        # ymm1 = ymm2[0,0,1,1,4,4,5,5]
	vshufps	$250, %ymm2, %ymm2, %ymm2       # ymm2 = ymm2[2,2,3,3,6,6,7,7]
	xorl	%eax, %eax
	vpxor	%xmm3, %xmm3, %xmm3
	vpcmpeqd	%ymm3, %ymm4, %ymm4
	.p2align	4
.LBB3_5:                                # =>This Loop Header: Depth=1
                                        #     Child Loop BB3_6 Depth 2
	xorl	%esi, %esi
	xorl	%r9d, %r9d
	movq	%rcx, %r10
	.p2align	4
.LBB3_6:                                #   Parent Loop BB3_5 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%esi, %rsi
	vmaskmovpd	(%rdi,%rsi), %ymm1, %ymm5
	vmaskmovpd	32(%rdi,%rsi), %ymm2, %ymm6
	vmovq	%xmm5, %r11
	popcntq	%r11, %r11
	vextracti128	$1, %ymm5, %xmm5
	vmovq	%xmm5, %rbx
	vmovq	%xmm6, %r14
	popcntq	%r14, %r14
	vextracti128	$1, %ymm6, %xmm5
	vmovq	%xmm5, %r15
	popcntq	%r15, %r15
	vmovd	%r14d, %xmm5
	vpinsrd	$2, %r15d, %xmm5, %xmm5
	popcntq	%rbx, %rbx
	vmovd	%r11d, %xmm6
	vpinsrd	$2, %ebx, %xmm6, %xmm6
	vinserti128	$1, %xmm5, %ymm6, %ymm5
	vpandn	%ymm5, %ymm4, %ymm5
	vpblendd	$170, %ymm3, %ymm5, %ymm5       # ymm5 = ymm5[0],ymm3[1],ymm5[2],ymm3[3],ymm5[4],ymm3[5],ymm5[6],ymm3[7]
	movslq	%r9d, %r9
	vmaskmovps	%ymm5, %ymm0, (%rdx,%r9)
	addl	$32, %r9d
	addl	$64, %esi
	decq	%r10
	jne	.LBB3_6
# %bb.7:                                #   in Loop: Header=BB3_5 Depth=1
	incq	%rax
	cmpq	%r8, %rax
	jne	.LBB3_5
	jmp	.LBB3_22
.LBB3_17:
	testq	%r8, %r8
	setle	%al
	testq	%rcx, %rcx
	setle	%sil
	orb	%al, %sil
	jne	.LBB3_22
# %bb.18:
	xorl	%eax, %eax
	vbroadcastf128	.LCPI3_0(%rip), %ymm0   # ymm0 = [18446744073709551615,0,18446744073709551615,0]
                                        # ymm0 = mem[0,1,0,1]
	.p2align	4
.LBB3_19:                               # =>This Loop Header: Depth=1
                                        #     Child Loop BB3_20 Depth 2
	xorl	%esi, %esi
	xorl	%r9d, %r9d
	movq	%rcx, %r10
	.p2align	4
.LBB3_20:                               #   Parent Loop BB3_19 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%esi, %rsi
	vmaskmovpd	(%rdi,%rsi), %ymm0, %ymm1
	vmaskmovpd	32(%rdi,%rsi), %ymm0, %ymm2
	vmovq	%xmm1, %r11
	popcntq	%r11, %r11
	vextracti128	$1, %ymm1, %xmm1
	vmovq	%xmm1, %rbx
	popcntq	%rbx, %rbx
	vmovq	%xmm2, %r14
	popcntq	%r14, %r14
	vextracti128	$1, %ymm2, %xmm1
	vmovq	%xmm1, %r15
	popcntq	%r15, %r15
	vmovd	%ebx, %xmm1
	vmovd	%r15d, %xmm2
	vinserti128	$1, %xmm2, %ymm1, %ymm1
	vmovd	%r11d, %xmm2
	vmovd	%r14d, %xmm3
	vinserti128	$1, %xmm3, %ymm2, %ymm2
	vpunpcklqdq	%ymm1, %ymm2, %ymm1     # ymm1 = ymm2[0],ymm1[0],ymm2[2],ymm1[2]
	movslq	%r9d, %r9
	vmovdqu	%ymm1, (%rdx,%r9)
	addl	$32, %r9d
	addl	$64, %esi
	decq	%r10
	jne	.LBB3_20
# %bb.21:                               #   in Loop: Header=BB3_19 Depth=1
	incq	%rax
	cmpq	%r8, %rax
	jne	.LBB3_19
.LBB3_22:
	popq	%rbx
	popq	%r14
	popq	%r15
	vzeroupper
	retq
.LBB3_8:
	movabsq	$9223372036854775800, %rax      # imm = 0x7FFFFFFFFFFFFFF8
	andq	%rcx, %rax
	movl	%ecx, %esi
	andl	$7, %esi
	xorl	%edi, %edi
	jmp	.LBB3_9
	.p2align	4
.LBB3_16:                               #   in Loop: Header=BB3_9 Depth=1
	incq	%rdi
	cmpq	%r8, %rdi
	je	.LBB3_22
.LBB3_9:                                # =>This Loop Header: Depth=1
                                        #     Child Loop BB3_12 Depth 2
                                        #     Child Loop BB3_15 Depth 2
	cmpq	$8, %rcx
	jae	.LBB3_11
# %bb.10:                               #   in Loop: Header=BB3_9 Depth=1
	xorl	%r9d, %r9d
	jmp	.LBB3_13
	.p2align	4
.LBB3_11:                               #   in Loop: Header=BB3_9 Depth=1
	movl	$224, %r10d
	xorl	%r9d, %r9d
	.p2align	4
.LBB3_12:                               #   Parent Loop BB3_9 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	leal	-224(%r10), %r11d
	movslq	%r11d, %r11
	vmaskmovps	%ymm1, %ymm0, (%rdx,%r11)
	leal	-192(%r10), %r11d
	movslq	%r11d, %r11
	vmaskmovps	%ymm1, %ymm0, (%rdx,%r11)
	leal	-160(%r10), %r11d
	movslq	%r11d, %r11
	vmaskmovps	%ymm1, %ymm0, (%rdx,%r11)
	leal	-128(%r10), %r11d
	movslq	%r11d, %r11
	vmaskmovps	%ymm1, %ymm0, (%rdx,%r11)
	leal	-96(%r10), %r11d
	movslq	%r11d, %r11
	vmaskmovps	%ymm1, %ymm0, (%rdx,%r11)
	leal	-64(%r10), %r11d
	movslq	%r11d, %r11
	vmaskmovps	%ymm1, %ymm0, (%rdx,%r11)
	leal	-32(%r10), %r11d
	movslq	%r11d, %r11
	vmaskmovps	%ymm1, %ymm0, (%rdx,%r11)
	movslq	%r10d, %r10
	vmaskmovps	%ymm1, %ymm0, (%rdx,%r10)
	addq	$8, %r9
	addl	$256, %r10d                     # imm = 0x100
	cmpq	%r9, %rax
	jne	.LBB3_12
.LBB3_13:                               #   in Loop: Header=BB3_9 Depth=1
	testb	$7, %cl
	je	.LBB3_16
# %bb.14:                               #   in Loop: Header=BB3_9 Depth=1
	shll	$5, %r9d
	movq	%rsi, %r10
	.p2align	4
.LBB3_15:                               #   Parent Loop BB3_9 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%r9d, %r9
	vmaskmovps	%ymm1, %ymm0, (%rdx,%r9)
	addl	$32, %r9d
	decq	%r10
	jne	.LBB3_15
	jmp	.LBB3_16
.Lfunc_end3:
	.size	lab_popcnt_even___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI, .Lfunc_end3-lab_popcnt_even___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
                                        # -- End function
	.section	.rodata.cst32,"aM",@progbits,32
	.p2align	5, 0x0                          # -- Begin function lab_popcnt_chain___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
.LCPI4_0:
	.zero	32,255
.LCPI4_1:
	.zero	32
	.text
	.globl	lab_popcnt_chain___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
	.p2align	4
	.type	lab_popcnt_chain___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI,@function
lab_popcnt_chain___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI: # @lab_popcnt_chain___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
# %bb.0:
	pushq	%rbp
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	subq	$168, %rsp
	vmovdqa	%ymm0, %ymm4
	movq	%rcx, %rbp
	movq	%rdx, %r15
	movq	%rsi, %r12
	movq	%rdi, %r13
	vpcmpeqd	%ymm0, %ymm0, %ymm0
	vtestps	%ymm0, %ymm4
	movq	%r8, 16(%rsp)                   # 8-byte Spill
	movq	%rcx, 8(%rsp)                   # 8-byte Spill
	jb	.LBB4_9
# %bb.1:
	testq	%r8, %r8
	jle	.LBB4_17
# %bb.2:
	testq	%rbp, %rbp
	jle	.LBB4_17
# %bb.3:
	vpermq	$216, %ymm4, %ymm0              # ymm0 = ymm4[0,2,1,3]
	vpshufd	$250, %ymm0, %ymm1              # ymm1 = ymm0[2,2,3,3,6,6,7,7]
	vmovdqu	%ymm1, 128(%rsp)                # 32-byte Spill
	vpshufd	$80, %ymm0, %ymm0               # ymm0 = ymm0[0,0,1,1,4,4,5,5]
	vmovdqu	%ymm0, 96(%rsp)                 # 32-byte Spill
	xorl	%eax, %eax
	vmovups	%ymm4, 32(%rsp)                 # 32-byte Spill
	jmp	.LBB4_4
	.p2align	4
.LBB4_8:                                #   in Loop: Header=BB4_4 Depth=1
	movq	24(%rsp), %rax                  # 8-byte Reload
	incq	%rax
	cmpq	16(%rsp), %rax                  # 8-byte Folded Reload
	movq	8(%rsp), %rbp                   # 8-byte Reload
	je	.LBB4_17
.LBB4_4:                                # =>This Loop Header: Depth=1
                                        #     Child Loop BB4_5 Depth 2
	movq	%rax, 24(%rsp)                  # 8-byte Spill
	xorl	%r14d, %r14d
	xorl	%ebx, %ebx
	vpxor	%xmm0, %xmm0, %xmm0
	jmp	.LBB4_5
	.p2align	4
.LBB4_7:                                #   in Loop: Header=BB4_5 Depth=2
	vmaskmovps	%ymm1, %ymm4, (%r15,%r14)
	addl	$64, %ebx
	addl	$32, %r14d
	vmovdqa	%ymm1, %ymm0
	decq	%rbp
	je	.LBB4_8
.LBB4_5:                                #   Parent Loop BB4_4 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%r14d, %r14
	vmaskmovps	(%r12,%r14), %ymm4, %ymm1
	vpcmpeqd	.LCPI4_1(%rip), %ymm1, %ymm2
	vtestps	%ymm4, %ymm2
	vpxor	%xmm1, %xmm1, %xmm1
	jb	.LBB4_7
# %bb.6:                                #   in Loop: Header=BB4_5 Depth=2
	vpxor	.LCPI4_0(%rip), %ymm2, %ymm1
	vextracti128	$1, %ymm1, %xmm3
	vpackssdw	%xmm3, %xmm1, %xmm1
	vmovdqa	%xmm1, 64(%rsp)                 # 16-byte Spill
	vandnps	%ymm4, %ymm2, %ymm2
	movslq	%ebx, %rax
	vmovupd	128(%rsp), %ymm1                # 32-byte Reload
	vmaskmovpd	32(%r13,%rax), %ymm1, %ymm1
	vmovupd	96(%rsp), %ymm3                 # 32-byte Reload
	vmaskmovpd	(%r13,%rax), %ymm3, %ymm3
	vextracti128	$1, %ymm0, %xmm4
	vpmovsxdq	%xmm4, %ymm4
	vxorpd	%ymm4, %ymm1, %ymm1
	vpmovsxdq	%xmm0, %ymm0
	vxorpd	%ymm0, %ymm3, %ymm0
	callq	popcnt_runtime___vyI
	vmovups	32(%rsp), %ymm4                 # 32-byte Reload
	vpmovsxwd	64(%rsp), %ymm1         # 16-byte Folded Reload
	vpand	%ymm0, %ymm1, %ymm1
	jmp	.LBB4_7
.LBB4_9:
	testq	%r8, %r8
	setg	%al
	testq	%rbp, %rbp
	setg	%dl
	andb	%al, %dl
	cmpb	$1, %dl
	jne	.LBB4_17
# %bb.10:
	xorl	%eax, %eax
	jmp	.LBB4_11
	.p2align	4
.LBB4_16:                               #   in Loop: Header=BB4_11 Depth=1
	movq	32(%rsp), %rax                  # 8-byte Reload
	incq	%rax
	cmpq	16(%rsp), %rax                  # 8-byte Folded Reload
	movq	8(%rsp), %rbp                   # 8-byte Reload
	je	.LBB4_17
.LBB4_11:                               # =>This Loop Header: Depth=1
                                        #     Child Loop BB4_12 Depth 2
	movq	%rax, 32(%rsp)                  # 8-byte Spill
	xorl	%ebx, %ebx
	xorl	%r14d, %r14d
	vpxor	%xmm0, %xmm0, %xmm0
	jmp	.LBB4_12
	.p2align	4
.LBB4_14:                               #   in Loop: Header=BB4_12 Depth=2
	movslq	%r14d, %rax
	vpcmpeqd	.LCPI4_1(%rip), %ymm1, %ymm1
	vmovdqu	%ymm1, 64(%rsp)                 # 32-byte Spill
	vpxor	.LCPI4_0(%rip), %ymm1, %ymm2
	vpmovsxdq	%xmm0, %ymm3
	vextracti128	$1, %ymm0, %xmm0
	vpmovsxdq	%xmm0, %ymm0
	vpxor	32(%r13,%rax), %ymm0, %ymm1
	vpxor	(%r13,%rax), %ymm3, %ymm0
	callq	popcnt_runtime___vyI
	vmovdqu	64(%rsp), %ymm1                 # 32-byte Reload
	vpandn	%ymm0, %ymm1, %ymm0
.LBB4_15:                               #   in Loop: Header=BB4_12 Depth=2
	vmovdqu	%ymm0, (%r15,%rbx)
	addl	$64, %r14d
	addl	$32, %ebx
	decq	%rbp
	je	.LBB4_16
.LBB4_12:                               #   Parent Loop BB4_11 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%ebx, %rbx
	vmovdqu	(%r12,%rbx), %ymm1
	vptest	%ymm1, %ymm1
	jne	.LBB4_14
# %bb.13:                               #   in Loop: Header=BB4_12 Depth=2
	vpxor	%xmm0, %xmm0, %xmm0
	jmp	.LBB4_15
.LBB4_17:
	addq	$168, %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	vzeroupper
	retq
.Lfunc_end4:
	.size	lab_popcnt_chain___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI, .Lfunc_end4-lab_popcnt_chain___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
                                        # -- End function
	.globl	lab_kernel                      # -- Begin function lab_kernel
	.p2align	4
	.type	lab_kernel,@function
lab_kernel:                             # @lab_kernel
# %bb.0:
	pushq	%rbp
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	movq	%rcx, -8(%rsp)                  # 8-byte Spill
	testq	%rcx, %rcx
	setg	%al
	testq	%rdx, %rdx
	setg	%r8b
	andb	%al, %r8b
	cmpb	$1, %r8b
	jne	.LBB5_5
# %bb.1:
	xorl	%ecx, %ecx
	.p2align	4
.LBB5_2:                                # =>This Loop Header: Depth=1
                                        #     Child Loop BB5_3 Depth 2
	xorl	%r8d, %r8d
	xorl	%r9d, %r9d
	movq	%rdx, %r10
	.p2align	4
.LBB5_3:                                #   Parent Loop BB5_2 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%r9d, %r9
	xorl	%r11d, %r11d
	popcntq	(%rdi,%r9), %r11
	xorl	%ebx, %ebx
	popcntq	8(%rdi,%r9), %rbx
	xorl	%r14d, %r14d
	popcntq	16(%rdi,%r9), %r14
	xorl	%r15d, %r15d
	popcntq	24(%rdi,%r9), %r15
	xorl	%r12d, %r12d
	popcntq	32(%rdi,%r9), %r12
	xorl	%r13d, %r13d
	popcntq	40(%rdi,%r9), %r13
	xorl	%ebp, %ebp
	popcntq	48(%rdi,%r9), %rbp
	xorl	%eax, %eax
	popcntq	56(%rdi,%r9), %rax
	vmovd	%r11d, %xmm0
	vpinsrd	$1, %ebx, %xmm0, %xmm0
	vpinsrd	$2, %r14d, %xmm0, %xmm0
	vpinsrd	$3, %r15d, %xmm0, %xmm0
	vmovd	%r12d, %xmm1
	vpinsrd	$1, %r13d, %xmm1, %xmm1
	vpinsrd	$2, %ebp, %xmm1, %xmm1
	vpinsrd	$3, %eax, %xmm1, %xmm1
	movslq	%r8d, %r8
	vmovdqu	%xmm1, 16(%rsi,%r8)
	vmovdqu	%xmm0, (%rsi,%r8)
	addl	$64, %r9d
	addl	$32, %r8d
	decq	%r10
	jne	.LBB5_3
# %bb.4:                                #   in Loop: Header=BB5_2 Depth=1
	incq	%rcx
	cmpq	-8(%rsp), %rcx                  # 8-byte Folded Reload
	jne	.LBB5_2
.LBB5_5:
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	retq
.Lfunc_end5:
	.size	lab_kernel, .Lfunc_end5-lab_kernel
                                        # -- End function
	.section	.rodata.cst32,"aM",@progbits,32
	.p2align	5, 0x0                          # -- Begin function lab_popcnt
.LCPI6_0:
	.zero	32
.LCPI6_1:
	.zero	32,255
	.text
	.globl	lab_popcnt
	.p2align	4
	.type	lab_popcnt,@function
lab_popcnt:                             # @lab_popcnt
# %bb.0:
	pushq	%rbp
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	subq	$72, %rsp
	movq	%r8, 16(%rsp)                   # 8-byte Spill
	testq	%r8, %r8
	setg	%al
	movq	%rcx, 8(%rsp)                   # 8-byte Spill
	testq	%rcx, %rcx
	setg	%cl
	andb	%al, %cl
	cmpb	$1, %cl
	jne	.LBB6_8
# %bb.1:
	movq	%rdx, %r15
	movq	%rsi, %r12
	movq	%rdi, %r13
	xorl	%eax, %eax
	jmp	.LBB6_2
	.p2align	4
.LBB6_7:                                #   in Loop: Header=BB6_2 Depth=1
	movq	24(%rsp), %rax                  # 8-byte Reload
	incq	%rax
	cmpq	16(%rsp), %rax                  # 8-byte Folded Reload
	je	.LBB6_8
.LBB6_2:                                # =>This Loop Header: Depth=1
                                        #     Child Loop BB6_3 Depth 2
	movq	%rax, 24(%rsp)                  # 8-byte Spill
	xorl	%ebx, %ebx
	xorl	%r14d, %r14d
	movq	8(%rsp), %rbp                   # 8-byte Reload
	jmp	.LBB6_3
	.p2align	4
.LBB6_5:                                #   in Loop: Header=BB6_3 Depth=2
	movslq	%r14d, %rax
	vpcmpeqd	.LCPI6_0(%rip), %ymm0, %ymm0
	vmovdqu	%ymm0, 32(%rsp)                 # 32-byte Spill
	vpxor	.LCPI6_1(%rip), %ymm0, %ymm2
	vmovdqu	(%r13,%rax), %ymm0
	vmovups	32(%r13,%rax), %ymm1
	callq	popcnt_runtime___vyI
	vmovdqu	32(%rsp), %ymm1                 # 32-byte Reload
	vpandn	%ymm0, %ymm1, %ymm0
.LBB6_6:                                #   in Loop: Header=BB6_3 Depth=2
	vmovdqu	%ymm0, (%r15,%rbx)
	addl	$64, %r14d
	addl	$32, %ebx
	decq	%rbp
	je	.LBB6_7
.LBB6_3:                                #   Parent Loop BB6_2 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%ebx, %rbx
	vmovdqu	(%r12,%rbx), %ymm0
	vptest	%ymm0, %ymm0
	jne	.LBB6_5
# %bb.4:                                #   in Loop: Header=BB6_3 Depth=2
	vpxor	%xmm0, %xmm0, %xmm0
	jmp	.LBB6_6
.LBB6_8:
	addq	$72, %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	vzeroupper
	retq
.Lfunc_end6:
	.size	lab_popcnt, .Lfunc_end6-lab_popcnt
                                        # -- End function
	.section	.rodata.cst16,"aM",@progbits,16
	.p2align	4, 0x0                          # -- Begin function lab_popcnt_even
.LCPI7_0:
	.quad	-1                              # 0xffffffffffffffff
	.quad	0                               # 0x0
	.text
	.globl	lab_popcnt_even
	.p2align	4
	.type	lab_popcnt_even,@function
lab_popcnt_even:                        # @lab_popcnt_even
# %bb.0:
	testq	%r8, %r8
	setg	%al
	testq	%rcx, %rcx
	setg	%sil
	andb	%al, %sil
	cmpb	$1, %sil
	jne	.LBB7_6
# %bb.1:
	pushq	%r15
	pushq	%r14
	pushq	%rbx
	xorl	%eax, %eax
	vbroadcastf128	.LCPI7_0(%rip), %ymm0   # ymm0 = [18446744073709551615,0,18446744073709551615,0]
                                        # ymm0 = mem[0,1,0,1]
	.p2align	4
.LBB7_2:                                # =>This Loop Header: Depth=1
                                        #     Child Loop BB7_3 Depth 2
	xorl	%esi, %esi
	xorl	%r9d, %r9d
	movq	%rcx, %r10
	.p2align	4
.LBB7_3:                                #   Parent Loop BB7_2 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%esi, %rsi
	vmaskmovpd	(%rdi,%rsi), %ymm0, %ymm1
	vmaskmovpd	32(%rdi,%rsi), %ymm0, %ymm2
	vmovq	%xmm1, %r11
	popcntq	%r11, %r11
	vextracti128	$1, %ymm1, %xmm1
	vmovq	%xmm1, %rbx
	popcntq	%rbx, %rbx
	vmovq	%xmm2, %r14
	popcntq	%r14, %r14
	vextracti128	$1, %ymm2, %xmm1
	vmovq	%xmm1, %r15
	popcntq	%r15, %r15
	vmovd	%ebx, %xmm1
	vmovd	%r15d, %xmm2
	vinserti128	$1, %xmm2, %ymm1, %ymm1
	vmovd	%r11d, %xmm2
	vmovd	%r14d, %xmm3
	vinserti128	$1, %xmm3, %ymm2, %ymm2
	vpunpcklqdq	%ymm1, %ymm2, %ymm1     # ymm1 = ymm2[0],ymm1[0],ymm2[2],ymm1[2]
	movslq	%r9d, %r9
	vmovdqu	%ymm1, (%rdx,%r9)
	addl	$32, %r9d
	addl	$64, %esi
	decq	%r10
	jne	.LBB7_3
# %bb.4:                                #   in Loop: Header=BB7_2 Depth=1
	incq	%rax
	cmpq	%r8, %rax
	jne	.LBB7_2
# %bb.5:
	popq	%rbx
	popq	%r14
	popq	%r15
.LBB7_6:
	vzeroupper
	retq
.Lfunc_end7:
	.size	lab_popcnt_even, .Lfunc_end7-lab_popcnt_even
                                        # -- End function
	.section	.rodata.cst32,"aM",@progbits,32
	.p2align	5, 0x0                          # -- Begin function lab_popcnt_chain
.LCPI8_0:
	.zero	32
.LCPI8_1:
	.zero	32,255
	.text
	.globl	lab_popcnt_chain
	.p2align	4
	.type	lab_popcnt_chain,@function
lab_popcnt_chain:                       # @lab_popcnt_chain
# %bb.0:
	pushq	%rbp
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%rbx
	subq	$72, %rsp
	movq	%r8, 16(%rsp)                   # 8-byte Spill
	testq	%r8, %r8
	setg	%al
	movq	%rcx, 8(%rsp)                   # 8-byte Spill
	testq	%rcx, %rcx
	setg	%cl
	andb	%al, %cl
	cmpb	$1, %cl
	jne	.LBB8_8
# %bb.1:
	movq	%rdx, %r15
	movq	%rsi, %r12
	movq	%rdi, %r13
	xorl	%eax, %eax
	jmp	.LBB8_2
	.p2align	4
.LBB8_7:                                #   in Loop: Header=BB8_2 Depth=1
	movq	24(%rsp), %rax                  # 8-byte Reload
	incq	%rax
	cmpq	16(%rsp), %rax                  # 8-byte Folded Reload
	je	.LBB8_8
.LBB8_2:                                # =>This Loop Header: Depth=1
                                        #     Child Loop BB8_3 Depth 2
	movq	%rax, 24(%rsp)                  # 8-byte Spill
	xorl	%ebx, %ebx
	xorl	%r14d, %r14d
	movq	8(%rsp), %rbp                   # 8-byte Reload
	vpxor	%xmm0, %xmm0, %xmm0
	jmp	.LBB8_3
	.p2align	4
.LBB8_5:                                #   in Loop: Header=BB8_3 Depth=2
	movslq	%r14d, %rax
	vpcmpeqd	.LCPI8_0(%rip), %ymm1, %ymm1
	vmovdqu	%ymm1, 32(%rsp)                 # 32-byte Spill
	vpxor	.LCPI8_1(%rip), %ymm1, %ymm2
	vpmovsxdq	%xmm0, %ymm3
	vextracti128	$1, %ymm0, %xmm0
	vpmovsxdq	%xmm0, %ymm0
	vpxor	32(%r13,%rax), %ymm0, %ymm1
	vpxor	(%r13,%rax), %ymm3, %ymm0
	callq	popcnt_runtime___vyI
	vmovdqu	32(%rsp), %ymm1                 # 32-byte Reload
	vpandn	%ymm0, %ymm1, %ymm0
.LBB8_6:                                #   in Loop: Header=BB8_3 Depth=2
	vmovdqu	%ymm0, (%r15,%rbx)
	addl	$64, %r14d
	addl	$32, %ebx
	decq	%rbp
	je	.LBB8_7
.LBB8_3:                                #   Parent Loop BB8_2 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	movslq	%ebx, %rbx
	vmovdqu	(%r12,%rbx), %ymm1
	vptest	%ymm1, %ymm1
	jne	.LBB8_5
# %bb.4:                                #   in Loop: Header=BB8_3 Depth=2
	vpxor	%xmm0, %xmm0, %xmm0
	jmp	.LBB8_6
.LBB8_8:
	addq	$72, %rsp
	popq	%rbx
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	vzeroupper
	retq
.Lfunc_end8:
	.size	lab_popcnt_chain, .Lfunc_end8-lab_popcnt_chain
                                        # -- End function
	.ident	"Intel(r) Implicit SPMD Program Compiler (Intel(r) ISPC), 1.33.0dev (build commit e38083ae17471b43 @ 20220101, LLVM 20.1.8)"
	.ident	"Debian LLVM version 20.1.8 (++20250708063551+0c9f909b7976-1~exp1~20250708183702.136)"
	.section	".note.GNU-stack","",@progbits
