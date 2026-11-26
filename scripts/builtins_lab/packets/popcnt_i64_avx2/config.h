// Copyright (c) 2026, Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
// popcnt(varying int64) T1 packet: shared sizes for contexts.cpp.
#pragma once
// Elements per call: stays in L1 like benchmarks/01_trivial/03_popcnt (8192 x int64 = 64 KiB there; 4096 here).
#define POPCNT_COUNT 4096
// Dependent popcnt steps per call in the chain (latency) contexts.
#define POPCNT_CHAIN_STEPS 4096
