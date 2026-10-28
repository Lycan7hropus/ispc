# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
# Input rdi:64 readable bytes. Output eax:0 or1. No stores.
    vmovdqu       0(%rdi), %ymm0
    vmovdqu      32(%rdi), %ymm1
    vpbroadcastq  0(%rdi), %ymm2
    vpcmpeqq     %ymm2, %ymm0, %ymm3
    vpcmpeqq     %ymm2, %ymm1, %ymm4
    vpand        %ymm3, %ymm4, %ymm5
    vmovmskpd    %ymm5, %eax
    cmpl         $15, %eax
    sete         %al
    movzbl       %al, %eax
