/* Copyright (c) 2026, Intel Corporation
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Generated from popcnt_i64_kernels.ispc by ISPC with the CRoaring __popcnt_int64_varying patch (branch viktor/popcnt-croaring-avx2)
 * (1.33.0dev, builtins/optimization-lab-wip e38083ae, LLVM 20.1.8):
 *   ispc --target=avx2-i32x8 --arch=x86-64 -O2 --pic --emit-asm popcnt_i64_kernels.ispc -o popcnt_i64_croaring_ispc.S
 * Do not edit; regenerate. */
	.file	"popcnt_i64_kernels.ispc"
	.section	.rodata.cst32,"aM",@progbits,32
	.p2align	5, 0x0                          # -- Begin function popcnt_runtime___vyI
.LCPI0_0:
	.zero	32,15
.LCPI0_1:
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
.LCPI0_2:
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.section	.rodata,"a",@progbits
.LCPI0_3:
	.byte	15                              # 0xf
	.section	.rodata.cst16,"aM",@progbits,16
	.p2align	4, 0x0
.LCPI0_4:
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
.LCPI0_5:
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.text
	.p2align	4
	.type	popcnt_runtime___vyI,@function
popcnt_runtime___vyI:                   # @popcnt_runtime___vyI
# %bb.0:
	vpbroadcastb	.LCPI0_3(%rip), %ymm3   # ymm3 = [15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15]
	vpand	%ymm3, %ymm0, %ymm4
	vpsrlw	$4, %ymm0, %ymm0
	vpand	%ymm3, %ymm0, %ymm0
	vbroadcasti128	.LCPI0_4(%rip), %ymm5   # ymm5 = [4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8,4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8]
                                        # ymm5 = mem[0,1,0,1]
	vpshufb	%ymm4, %ymm5, %ymm4
	vbroadcasti128	.LCPI0_5(%rip), %ymm6   # ymm6 = [4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0,4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0]
                                        # ymm6 = mem[0,1,0,1]
	vpshufb	%ymm0, %ymm6, %ymm0
	vpsadbw	%ymm0, %ymm4, %ymm0
	vpand	%ymm3, %ymm1, %ymm4
	vpsrlw	$4, %ymm1, %ymm1
	vpand	%ymm3, %ymm1, %ymm1
	vpshufb	%ymm4, %ymm5, %ymm3
	vpshufb	%ymm1, %ymm6, %ymm1
	vpsadbw	%ymm1, %ymm3, %ymm1
	vpackusdw	%ymm1, %ymm0, %ymm0
	vpermq	$216, %ymm0, %ymm0              # ymm0 = ymm0[0,2,1,3]
	vpxor	%xmm1, %xmm1, %xmm1
	vpcmpeqd	%ymm1, %ymm2, %ymm1
	vpandn	%ymm0, %ymm1, %ymm0
	retq
.Lfunc_end0:
	.size	popcnt_runtime___vyI, .Lfunc_end0-popcnt_runtime___vyI
                                        # -- End function
	.section	.rodata.cst32,"aM",@progbits,32
	.p2align	5, 0x0                          # -- Begin function lab_kernel___un_3C_unI_3E_un_3C_uni_3E_unIunI
.LCPI1_0:
	.zero	32,15
.LCPI1_1:
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
.LCPI1_2:
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.section	.rodata.cst4,"aM",@progbits,4
	.p2align	2, 0x0
.LCPI1_3:
	.zero	4,15
	.section	.rodata.cst16,"aM",@progbits,16
	.p2align	4, 0x0
.LCPI1_4:
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
.LCPI1_5:
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.section	.rodata,"a",@progbits
.LCPI1_6:
	.byte	15                              # 0xf
	.text
	.globl	lab_kernel___un_3C_unI_3E_un_3C_uni_3E_unIunI
	.p2align	4
	.type	lab_kernel___un_3C_unI_3E_un_3C_uni_3E_unIunI,@function
lab_kernel___un_3C_unI_3E_un_3C_uni_3E_unIunI: # @lab_kernel___un_3C_unI_3E_un_3C_uni_3E_unIunI
# %bb.0:
	pushq	%rbp
	pushq	%r14
	pushq	%rbx
	vpcmpeqd	%ymm1, %ymm1, %ymm1
	vtestps	%ymm1, %ymm0
	jb	.LBB1_11
# %bb.1:
	testq	%rcx, %rcx
	jle	.LBB1_20
# %bb.2:
	testq	%rdx, %rdx
	jle	.LBB1_20
# %bb.3:
	vpermpd	$216, %ymm0, %ymm2              # ymm2 = ymm0[0,2,1,3]
	vshufps	$80, %ymm2, %ymm2, %ymm1        # ymm1 = ymm2[0,0,1,1,4,4,5,5]
	vshufps	$250, %ymm2, %ymm2, %ymm2       # ymm2 = ymm2[2,2,3,3,6,6,7,7]
	movabsq	$9223372036854775806, %rax      # imm = 0x7FFFFFFFFFFFFFFE
	andq	%rdx, %rax
	negq	%rax
	xorl	%r8d, %r8d
	vpxor	%xmm6, %xmm6, %xmm6
	vbroadcastss	.LCPI1_3(%rip), %ymm3   # ymm3 = [15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15]
	vbroadcasti128	.LCPI1_4(%rip), %ymm4   # ymm4 = [4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8,4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8]
                                        # ymm4 = mem[0,1,0,1]
	vbroadcasti128	.LCPI1_5(%rip), %ymm5   # ymm5 = [4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0,4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0]
                                        # ymm5 = mem[0,1,0,1]
	vpcmpeqd	%ymm6, %ymm0, %ymm6
	jmp	.LBB1_4
	.p2align	4
.LBB1_9:                                #   in Loop: Header=BB1_4 Depth=1
	movl	%r9d, %r10d
	shll	$6, %r9d
	movslq	%r9d, %r9
	vmaskmovpd	(%rdi,%r9), %ymm1, %ymm7
	shll	$5, %r10d
	vmaskmovpd	32(%rdi,%r9), %ymm2, %ymm8
	vandpd	%ymm3, %ymm7, %ymm9
	vpsrlw	$4, %ymm7, %ymm7
	vpand	%ymm3, %ymm7, %ymm7
	vpshufb	%ymm9, %ymm4, %ymm9
	vpshufb	%ymm7, %ymm5, %ymm7
	vpsadbw	%ymm7, %ymm9, %ymm7
	vandpd	%ymm3, %ymm8, %ymm9
	vpsrlw	$4, %ymm8, %ymm8
	vpand	%ymm3, %ymm8, %ymm8
	vpshufb	%ymm9, %ymm4, %ymm9
	vpshufb	%ymm8, %ymm5, %ymm8
	vpsadbw	%ymm8, %ymm9, %ymm8
	vpackusdw	%ymm8, %ymm7, %ymm7
	vpermq	$216, %ymm7, %ymm7              # ymm7 = ymm7[0,2,1,3]
	vpandn	%ymm7, %ymm6, %ymm7
	movslq	%r10d, %r9
	vmaskmovps	%ymm7, %ymm0, (%rsi,%r9)
.LBB1_10:                               #   in Loop: Header=BB1_4 Depth=1
	incq	%r8
	cmpq	%rcx, %r8
	je	.LBB1_20
.LBB1_4:                                # =>This Loop Header: Depth=1
                                        #     Child Loop BB1_6 Depth 2
	movl	$0, %r9d
	cmpq	$1, %rdx
	je	.LBB1_9
# %bb.5:                                #   in Loop: Header=BB1_4 Depth=1
	movl	$32, %r10d
	movl	$64, %r11d
	xorl	%r9d, %r9d
	.p2align	4
.LBB1_6:                                #   Parent Loop BB1_4 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	leal	-64(%r11), %ebx
	movslq	%ebx, %rbx
	vmaskmovpd	(%rdi,%rbx), %ymm1, %ymm7
	leal	-32(%r10), %ebp
	vmaskmovpd	32(%rdi,%rbx), %ymm2, %ymm8
	vandpd	%ymm3, %ymm7, %ymm9
	vpsrlw	$4, %ymm7, %ymm7
	vpand	%ymm3, %ymm7, %ymm7
	vpshufb	%ymm9, %ymm4, %ymm9
	vpshufb	%ymm7, %ymm5, %ymm7
	vpsadbw	%ymm7, %ymm9, %ymm7
	vandpd	%ymm3, %ymm8, %ymm9
	vpsrlw	$4, %ymm8, %ymm8
	vpand	%ymm3, %ymm8, %ymm8
	vpshufb	%ymm9, %ymm4, %ymm9
	vpshufb	%ymm8, %ymm5, %ymm8
	vpsadbw	%ymm8, %ymm9, %ymm8
	vpackusdw	%ymm8, %ymm7, %ymm7
	vpermq	$216, %ymm7, %ymm7              # ymm7 = ymm7[0,2,1,3]
	vpandn	%ymm7, %ymm6, %ymm7
	movslq	%ebp, %rbx
	vmaskmovps	%ymm7, %ymm0, (%rsi,%rbx)
	movslq	%r11d, %r11
	vmaskmovpd	(%rdi,%r11), %ymm1, %ymm7
	vmaskmovpd	32(%rdi,%r11), %ymm2, %ymm8
	vandpd	%ymm3, %ymm7, %ymm9
	vpsrlw	$4, %ymm7, %ymm7
	vpand	%ymm3, %ymm7, %ymm7
	vpshufb	%ymm9, %ymm4, %ymm9
	vpshufb	%ymm7, %ymm5, %ymm7
	vpsadbw	%ymm7, %ymm9, %ymm7
	vandpd	%ymm3, %ymm8, %ymm9
	vpsrlw	$4, %ymm8, %ymm8
	vpand	%ymm3, %ymm8, %ymm8
	vpshufb	%ymm9, %ymm4, %ymm9
	vpshufb	%ymm8, %ymm5, %ymm8
	vpsadbw	%ymm8, %ymm9, %ymm8
	vpackusdw	%ymm8, %ymm7, %ymm7
	vpermq	$216, %ymm7, %ymm7              # ymm7 = ymm7[0,2,1,3]
	vpandn	%ymm7, %ymm6, %ymm7
	movslq	%r10d, %r10
	vmaskmovps	%ymm7, %ymm0, (%rsi,%r10)
	addl	$64, %r10d
	subl	$-128, %r11d
	addq	$-2, %r9
	cmpq	%r9, %rax
	jne	.LBB1_6
# %bb.7:                                #   in Loop: Header=BB1_4 Depth=1
	testb	$1, %dl
	je	.LBB1_10
# %bb.8:                                #   in Loop: Header=BB1_4 Depth=1
	negq	%r9
	jmp	.LBB1_9
.LBB1_11:
	testq	%rcx, %rcx
	setle	%al
	testq	%rdx, %rdx
	setle	%r8b
	orb	%al, %r8b
	jne	.LBB1_20
# %bb.12:
	movabsq	$9223372036854775806, %rax      # imm = 0x7FFFFFFFFFFFFFFE
	andq	%rdx, %rax
	negq	%rax
	xorl	%r8d, %r8d
	vpbroadcastb	.LCPI1_6(%rip), %ymm0   # ymm0 = [15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15]
	vbroadcasti128	.LCPI1_4(%rip), %ymm1   # ymm1 = [4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8,4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8]
                                        # ymm1 = mem[0,1,0,1]
	vbroadcasti128	.LCPI1_5(%rip), %ymm2   # ymm2 = [4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0,4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0]
                                        # ymm2 = mem[0,1,0,1]
	jmp	.LBB1_13
	.p2align	4
.LBB1_18:                               #   in Loop: Header=BB1_13 Depth=1
	movl	%r9d, %r10d
	shll	$5, %r10d
	shll	$6, %r9d
	movslq	%r9d, %r9
	vmovdqu	(%rdi,%r9), %ymm3
	vmovdqu	32(%rdi,%r9), %ymm4
	vpand	%ymm0, %ymm3, %ymm5
	vpsrlw	$4, %ymm3, %ymm3
	vpand	%ymm0, %ymm3, %ymm3
	vpshufb	%ymm5, %ymm1, %ymm5
	vpshufb	%ymm3, %ymm2, %ymm3
	vpsadbw	%ymm3, %ymm5, %ymm3
	vpand	%ymm0, %ymm4, %ymm5
	vpsrlw	$4, %ymm4, %ymm4
	vpand	%ymm0, %ymm4, %ymm4
	vpshufb	%ymm5, %ymm1, %ymm5
	vpshufb	%ymm4, %ymm2, %ymm4
	vpsadbw	%ymm4, %ymm5, %ymm4
	vpackusdw	%ymm4, %ymm3, %ymm3
	vpermq	$216, %ymm3, %ymm3              # ymm3 = ymm3[0,2,1,3]
	movslq	%r10d, %r9
	vmovdqu	%ymm3, (%rsi,%r9)
.LBB1_19:                               #   in Loop: Header=BB1_13 Depth=1
	incq	%r8
	cmpq	%rcx, %r8
	je	.LBB1_20
.LBB1_13:                               # =>This Loop Header: Depth=1
                                        #     Child Loop BB1_15 Depth 2
	movl	$0, %r9d
	cmpq	$1, %rdx
	je	.LBB1_18
# %bb.14:                               #   in Loop: Header=BB1_13 Depth=1
	movl	$32, %r10d
	movl	$64, %r11d
	xorl	%r9d, %r9d
	.p2align	4
.LBB1_15:                               #   Parent Loop BB1_13 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	leal	-32(%r10), %ebx
	leal	-64(%r11), %ebp
	movslq	%ebp, %r14
	vmovdqu	(%rdi,%r14), %ymm3
	vmovdqu	32(%rdi,%r14), %ymm4
	vpand	%ymm0, %ymm3, %ymm5
	vpsrlw	$4, %ymm3, %ymm3
	vpand	%ymm0, %ymm3, %ymm3
	vpshufb	%ymm5, %ymm1, %ymm5
	vpshufb	%ymm3, %ymm2, %ymm3
	vpsadbw	%ymm3, %ymm5, %ymm3
	vpand	%ymm0, %ymm4, %ymm5
	vpsrlw	$4, %ymm4, %ymm4
	vpand	%ymm0, %ymm4, %ymm4
	vpshufb	%ymm5, %ymm1, %ymm5
	vpshufb	%ymm4, %ymm2, %ymm4
	vpsadbw	%ymm4, %ymm5, %ymm4
	vpackusdw	%ymm4, %ymm3, %ymm3
	vpermq	$216, %ymm3, %ymm3              # ymm3 = ymm3[0,2,1,3]
	movslq	%ebx, %rbx
	vmovdqu	%ymm3, (%rsi,%rbx)
	movslq	%r11d, %r11
	vmovdqu	(%rdi,%r11), %ymm3
	vmovdqu	32(%rdi,%r11), %ymm4
	vpand	%ymm0, %ymm3, %ymm5
	vpsrlw	$4, %ymm3, %ymm3
	vpand	%ymm0, %ymm3, %ymm3
	vpshufb	%ymm5, %ymm1, %ymm5
	vpshufb	%ymm3, %ymm2, %ymm3
	vpsadbw	%ymm3, %ymm5, %ymm3
	vpand	%ymm0, %ymm4, %ymm5
	vpsrlw	$4, %ymm4, %ymm4
	vpand	%ymm0, %ymm4, %ymm4
	vpshufb	%ymm5, %ymm1, %ymm5
	vpshufb	%ymm4, %ymm2, %ymm4
	vpsadbw	%ymm4, %ymm5, %ymm4
	vpackusdw	%ymm4, %ymm3, %ymm3
	vpermq	$216, %ymm3, %ymm3              # ymm3 = ymm3[0,2,1,3]
	movslq	%r10d, %r10
	vmovdqu	%ymm3, (%rsi,%r10)
	addl	$64, %r10d
	subl	$-128, %r11d
	addq	$-2, %r9
	cmpq	%r9, %rax
	jne	.LBB1_15
# %bb.16:                               #   in Loop: Header=BB1_13 Depth=1
	testb	$1, %dl
	je	.LBB1_19
# %bb.17:                               #   in Loop: Header=BB1_13 Depth=1
	negq	%r9
	jmp	.LBB1_18
.LBB1_20:
	popq	%rbx
	popq	%r14
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
	.section	.rodata.cst32,"aM",@progbits,32
	.p2align	5, 0x0                          # -- Begin function lab_popcnt_even___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
.LCPI3_0:
	.zero	32,15
.LCPI3_1:
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
.LCPI3_2:
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.section	.rodata.cst16,"aM",@progbits,16
	.p2align	4, 0x0
.LCPI3_3:
	.quad	-1                              # 0xffffffffffffffff
	.quad	0                               # 0x0
.LCPI3_5:
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
.LCPI3_6:
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.section	.rodata.cst4,"aM",@progbits,4
	.p2align	2, 0x0
.LCPI3_4:
	.zero	4,15
	.text
	.globl	lab_popcnt_even___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
	.p2align	4
	.type	lab_popcnt_even___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI,@function
lab_popcnt_even___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI: # @lab_popcnt_even___un_3C_unI_3E_un_3C_uni_3E_un_3C_uni_3E_unIunI
# %bb.0:
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
	vblendps	$170, %ymm1, %ymm0, %ymm7       # ymm7 = ymm0[0],ymm1[1],ymm0[2],ymm1[3],ymm0[4],ymm1[5],ymm0[6],ymm1[7]
	vtestps	%ymm7, %ymm7
	je	.LBB3_8
# %bb.4:
	vpermpd	$216, %ymm7, %ymm2              # ymm2 = ymm7[0,2,1,3]
	vshufps	$80, %ymm2, %ymm2, %ymm1        # ymm1 = ymm2[0,0,1,1,4,4,5,5]
	vshufps	$250, %ymm2, %ymm2, %ymm2       # ymm2 = ymm2[2,2,3,3,6,6,7,7]
	xorl	%eax, %eax
	vpxor	%xmm3, %xmm3, %xmm3
	vbroadcastss	.LCPI3_4(%rip), %ymm4   # ymm4 = [15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15]
	vbroadcasti128	.LCPI3_5(%rip), %ymm5   # ymm5 = [4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8,4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8]
                                        # ymm5 = mem[0,1,0,1]
	vbroadcasti128	.LCPI3_6(%rip), %ymm6   # ymm6 = [4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0,4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0]
                                        # ymm6 = mem[0,1,0,1]
	vpcmpeqd	%ymm3, %ymm7, %ymm7
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
	vmaskmovpd	(%rdi,%rsi), %ymm1, %ymm8
	vmaskmovpd	32(%rdi,%rsi), %ymm2, %ymm9
	vandpd	%ymm4, %ymm8, %ymm10
	vpshufb	%ymm10, %ymm5, %ymm10
	vpsrlw	$4, %ymm8, %ymm8
	vpand	%ymm4, %ymm8, %ymm8
	vpshufb	%ymm8, %ymm6, %ymm8
	vpsadbw	%ymm8, %ymm10, %ymm8
	vandpd	%ymm4, %ymm9, %ymm10
	vpshufb	%ymm10, %ymm5, %ymm10
	vpsrlw	$4, %ymm9, %ymm9
	vpand	%ymm4, %ymm9, %ymm9
	vpshufb	%ymm9, %ymm6, %ymm9
	vpsadbw	%ymm9, %ymm10, %ymm9
	vpackusdw	%ymm9, %ymm8, %ymm8
	vpermq	$216, %ymm8, %ymm8              # ymm8 = ymm8[0,2,1,3]
	vpandn	%ymm8, %ymm7, %ymm8
	vpblendd	$170, %ymm3, %ymm8, %ymm8       # ymm8 = ymm8[0],ymm3[1],ymm8[2],ymm3[3],ymm8[4],ymm3[5],ymm8[6],ymm3[7]
	movslq	%r9d, %r9
	vmaskmovps	%ymm8, %ymm0, (%rdx,%r9)
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
	vbroadcastf128	.LCPI3_3(%rip), %ymm0   # ymm0 = [18446744073709551615,0,18446744073709551615,0]
                                        # ymm0 = mem[0,1,0,1]
	vbroadcastss	.LCPI3_4(%rip), %ymm1   # ymm1 = [15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15]
	vbroadcasti128	.LCPI3_5(%rip), %ymm2   # ymm2 = [4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8,4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8]
                                        # ymm2 = mem[0,1,0,1]
	vbroadcasti128	.LCPI3_6(%rip), %ymm3   # ymm3 = [4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0,4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0]
                                        # ymm3 = mem[0,1,0,1]
	vpxor	%xmm4, %xmm4, %xmm4
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
	vmaskmovpd	(%rdi,%rsi), %ymm0, %ymm5
	vmaskmovpd	32(%rdi,%rsi), %ymm0, %ymm6
	vandpd	%ymm1, %ymm5, %ymm7
	vpsrlw	$4, %ymm5, %ymm5
	vpand	%ymm1, %ymm5, %ymm5
	vpshufb	%ymm7, %ymm2, %ymm7
	vpshufb	%ymm5, %ymm3, %ymm5
	vpsadbw	%ymm5, %ymm7, %ymm5
	vandpd	%ymm1, %ymm6, %ymm7
	vpsrlw	$4, %ymm6, %ymm6
	vpand	%ymm1, %ymm6, %ymm6
	vpshufb	%ymm7, %ymm2, %ymm7
	vpshufb	%ymm6, %ymm3, %ymm6
	vpsadbw	%ymm6, %ymm7, %ymm6
	vpackusdw	%ymm6, %ymm5, %ymm5
	vpermq	$216, %ymm5, %ymm5              # ymm5 = ymm5[0,2,1,3]
	vpblendd	$170, %ymm4, %ymm5, %ymm5       # ymm5 = ymm5[0],ymm4[1],ymm5[2],ymm4[3],ymm5[4],ymm4[5],ymm5[6],ymm4[7]
	movslq	%r9d, %r9
	vmovdqu	%ymm5, (%rdx,%r9)
	addl	$32, %r9d
	addl	$64, %esi
	decq	%r10
	jne	.LBB3_20
# %bb.21:                               #   in Loop: Header=BB3_19 Depth=1
	incq	%rax
	cmpq	%r8, %rax
	jne	.LBB3_19
.LBB3_22:
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
	.section	.rodata.cst32,"aM",@progbits,32
	.p2align	5, 0x0                          # -- Begin function lab_kernel
.LCPI5_0:
	.zero	32,15
.LCPI5_1:
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
.LCPI5_2:
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.section	.rodata,"a",@progbits
.LCPI5_3:
	.byte	15                              # 0xf
	.section	.rodata.cst16,"aM",@progbits,16
	.p2align	4, 0x0
.LCPI5_4:
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
.LCPI5_5:
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.text
	.globl	lab_kernel
	.p2align	4
	.type	lab_kernel,@function
lab_kernel:                             # @lab_kernel
# %bb.0:
	testq	%rcx, %rcx
	setg	%al
	testq	%rdx, %rdx
	setg	%r8b
	andb	%al, %r8b
	cmpb	$1, %r8b
	jne	.LBB5_10
# %bb.1:
	pushq	%rbp
	pushq	%r14
	pushq	%rbx
	movabsq	$9223372036854775806, %rax      # imm = 0x7FFFFFFFFFFFFFFE
	andq	%rdx, %rax
	negq	%rax
	xorl	%r8d, %r8d
	vpbroadcastb	.LCPI5_3(%rip), %ymm0   # ymm0 = [15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15]
	vbroadcasti128	.LCPI5_4(%rip), %ymm1   # ymm1 = [4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8,4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8]
                                        # ymm1 = mem[0,1,0,1]
	vbroadcasti128	.LCPI5_5(%rip), %ymm2   # ymm2 = [4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0,4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0]
                                        # ymm2 = mem[0,1,0,1]
	jmp	.LBB5_2
	.p2align	4
.LBB5_7:                                #   in Loop: Header=BB5_2 Depth=1
	movl	%r9d, %r10d
	shll	$5, %r10d
	shll	$6, %r9d
	movslq	%r9d, %r9
	vmovdqu	(%rdi,%r9), %ymm3
	vmovdqu	32(%rdi,%r9), %ymm4
	vpand	%ymm0, %ymm3, %ymm5
	vpsrlw	$4, %ymm3, %ymm3
	vpand	%ymm0, %ymm3, %ymm3
	vpshufb	%ymm5, %ymm1, %ymm5
	vpshufb	%ymm3, %ymm2, %ymm3
	vpsadbw	%ymm3, %ymm5, %ymm3
	vpand	%ymm0, %ymm4, %ymm5
	vpsrlw	$4, %ymm4, %ymm4
	vpand	%ymm0, %ymm4, %ymm4
	vpshufb	%ymm5, %ymm1, %ymm5
	vpshufb	%ymm4, %ymm2, %ymm4
	vpsadbw	%ymm4, %ymm5, %ymm4
	vpackusdw	%ymm4, %ymm3, %ymm3
	vpermq	$216, %ymm3, %ymm3              # ymm3 = ymm3[0,2,1,3]
	movslq	%r10d, %r9
	vmovdqu	%ymm3, (%rsi,%r9)
.LBB5_8:                                #   in Loop: Header=BB5_2 Depth=1
	incq	%r8
	cmpq	%rcx, %r8
	je	.LBB5_9
.LBB5_2:                                # =>This Loop Header: Depth=1
                                        #     Child Loop BB5_4 Depth 2
	movl	$0, %r9d
	cmpq	$1, %rdx
	je	.LBB5_7
# %bb.3:                                #   in Loop: Header=BB5_2 Depth=1
	movl	$32, %r10d
	movl	$64, %r11d
	xorl	%r9d, %r9d
	.p2align	4
.LBB5_4:                                #   Parent Loop BB5_2 Depth=1
                                        # =>  This Inner Loop Header: Depth=2
	leal	-32(%r10), %ebx
	leal	-64(%r11), %ebp
	movslq	%ebp, %r14
	vmovdqu	(%rdi,%r14), %ymm3
	vmovdqu	32(%rdi,%r14), %ymm4
	vpand	%ymm0, %ymm3, %ymm5
	vpsrlw	$4, %ymm3, %ymm3
	vpand	%ymm0, %ymm3, %ymm3
	vpshufb	%ymm5, %ymm1, %ymm5
	vpshufb	%ymm3, %ymm2, %ymm3
	vpsadbw	%ymm3, %ymm5, %ymm3
	vpand	%ymm0, %ymm4, %ymm5
	vpsrlw	$4, %ymm4, %ymm4
	vpand	%ymm0, %ymm4, %ymm4
	vpshufb	%ymm5, %ymm1, %ymm5
	vpshufb	%ymm4, %ymm2, %ymm4
	vpsadbw	%ymm4, %ymm5, %ymm4
	vpackusdw	%ymm4, %ymm3, %ymm3
	vpermq	$216, %ymm3, %ymm3              # ymm3 = ymm3[0,2,1,3]
	movslq	%ebx, %rbx
	vmovdqu	%ymm3, (%rsi,%rbx)
	movslq	%r11d, %r11
	vmovdqu	(%rdi,%r11), %ymm3
	vmovdqu	32(%rdi,%r11), %ymm4
	vpand	%ymm0, %ymm3, %ymm5
	vpsrlw	$4, %ymm3, %ymm3
	vpand	%ymm0, %ymm3, %ymm3
	vpshufb	%ymm5, %ymm1, %ymm5
	vpshufb	%ymm3, %ymm2, %ymm3
	vpsadbw	%ymm3, %ymm5, %ymm3
	vpand	%ymm0, %ymm4, %ymm5
	vpsrlw	$4, %ymm4, %ymm4
	vpand	%ymm0, %ymm4, %ymm4
	vpshufb	%ymm5, %ymm1, %ymm5
	vpshufb	%ymm4, %ymm2, %ymm4
	vpsadbw	%ymm4, %ymm5, %ymm4
	vpackusdw	%ymm4, %ymm3, %ymm3
	vpermq	$216, %ymm3, %ymm3              # ymm3 = ymm3[0,2,1,3]
	movslq	%r10d, %r10
	vmovdqu	%ymm3, (%rsi,%r10)
	addl	$64, %r10d
	subl	$-128, %r11d
	addq	$-2, %r9
	cmpq	%r9, %rax
	jne	.LBB5_4
# %bb.5:                                #   in Loop: Header=BB5_2 Depth=1
	testb	$1, %dl
	je	.LBB5_8
# %bb.6:                                #   in Loop: Header=BB5_2 Depth=1
	negq	%r9
	jmp	.LBB5_7
.LBB5_9:
	popq	%rbx
	popq	%r14
	popq	%rbp
.LBB5_10:
	vzeroupper
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
.LCPI7_5:
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
.LCPI7_6:
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.section	.rodata.cst32,"aM",@progbits,32
	.p2align	5, 0x0
.LCPI7_1:
	.zero	32,15
.LCPI7_2:
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
	.byte	4                               # 0x4
	.byte	5                               # 0x5
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	5                               # 0x5
	.byte	6                               # 0x6
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	6                               # 0x6
	.byte	7                               # 0x7
	.byte	7                               # 0x7
	.byte	8                               # 0x8
.LCPI7_3:
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.byte	4                               # 0x4
	.byte	3                               # 0x3
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	3                               # 0x3
	.byte	2                               # 0x2
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	2                               # 0x2
	.byte	1                               # 0x1
	.byte	1                               # 0x1
	.byte	0                               # 0x0
	.section	.rodata.cst4,"aM",@progbits,4
	.p2align	2, 0x0
.LCPI7_4:
	.zero	4,15
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
	jne	.LBB7_5
# %bb.1:
	xorl	%eax, %eax
	vbroadcastf128	.LCPI7_0(%rip), %ymm0   # ymm0 = [18446744073709551615,0,18446744073709551615,0]
                                        # ymm0 = mem[0,1,0,1]
	vbroadcastss	.LCPI7_4(%rip), %ymm1   # ymm1 = [15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15]
	vbroadcasti128	.LCPI7_5(%rip), %ymm2   # ymm2 = [4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8,4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8]
                                        # ymm2 = mem[0,1,0,1]
	vbroadcasti128	.LCPI7_6(%rip), %ymm3   # ymm3 = [4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0,4,3,3,2,3,2,2,1,3,2,2,1,2,1,1,0]
                                        # ymm3 = mem[0,1,0,1]
	vpxor	%xmm4, %xmm4, %xmm4
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
	vmaskmovpd	(%rdi,%rsi), %ymm0, %ymm5
	vmaskmovpd	32(%rdi,%rsi), %ymm0, %ymm6
	vandpd	%ymm1, %ymm5, %ymm7
	vpsrlw	$4, %ymm5, %ymm5
	vpand	%ymm1, %ymm5, %ymm5
	vpshufb	%ymm7, %ymm2, %ymm7
	vpshufb	%ymm5, %ymm3, %ymm5
	vpsadbw	%ymm5, %ymm7, %ymm5
	vandpd	%ymm1, %ymm6, %ymm7
	vpsrlw	$4, %ymm6, %ymm6
	vpand	%ymm1, %ymm6, %ymm6
	vpshufb	%ymm7, %ymm2, %ymm7
	vpshufb	%ymm6, %ymm3, %ymm6
	vpsadbw	%ymm6, %ymm7, %ymm6
	vpackusdw	%ymm6, %ymm5, %ymm5
	vpermq	$216, %ymm5, %ymm5              # ymm5 = ymm5[0,2,1,3]
	vpblendd	$170, %ymm4, %ymm5, %ymm5       # ymm5 = ymm5[0],ymm4[1],ymm5[2],ymm4[3],ymm5[4],ymm4[5],ymm5[6],ymm4[7]
	movslq	%r9d, %r9
	vmovdqu	%ymm5, (%rdx,%r9)
	addl	$32, %r9d
	addl	$64, %esi
	decq	%r10
	jne	.LBB7_3
# %bb.4:                                #   in Loop: Header=BB7_2 Depth=1
	incq	%rax
	cmpq	%r8, %rax
	jne	.LBB7_2
.LBB7_5:
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
