# ISPC micro-benchmarks.

Micro-benchmarks are designed to test efficiency of different aspects of ISPC code generation. This suite assumes three type of tests:

1. [**Individual language features and library functions**](01_trivial). Testing them in isolation focuses on implementation quality of language constructs, like ``foreach`` loops and library function like ``aos_to_soa()``. This category of tests allow covering ISPC functionality quite thoroughly, but doesn't address interplay between different features and compiler optimizations.
2. [**Feature combinations and non-obvious optimization effects**](02_medium). It's impractical to cover all combinations, so this kind of tests requires understanding of the specific effects triggered by features combination. An example might be memory operations nesting in non-trivial loops.
3. [**More complex cases inspired by real algorithms**](03_complex). Any example reduced from real-life applications and representing either a known performance problem, or a code snippet known to be critical for performance of the real code. When contributing this kind of examples, please mind the license of the original code.

The benchmarks might be used for comparison of different platforms and regression tracking. In this case ISPC implementation is sufficient.

For some features it also makes sense to compare with alternative implementations in other languages. In such case C++ (or other) implementation needs to be provided.

## Building and running

Use ``-DISPC_INCLUDE_BENCHMARKS=ON`` in your CMake configuration flags to enable building benchmarks. If ``--recurse-submodules`` was not used during repo cloning, CMake will fetch [Google Benchmark](https://github.com/google/benchmark) submodule. By default ISPC built from sources will used for building benchmarks. If you need to use pre-build ISPC binary, you can turn off building ISPC by setting ``-DISPC_BUILD=OFF`` and provide ISPC in your `PATH` environment variable.

You can use CMake options ``BENCHMARKS_ISPC_TARGETS`` and ``BENCHMARKS_ISPC_FLAGS`` to set specific targets or ISPC compilation switches. For example, ``-DBENCHMARKS_ISPC_TARGETS=sse4-i32x4,avx2-i32x8,avx512skx-x16 -DBENCHMARKS_ISPC_FLAGS="-O3 --woff"``. Every benchmark is built separately for each target in the list, e.g. ``01_aossoa.sse4-i32x4``, ``01_aossoa.avx2-i32x8`` and ``01_aossoa.avx512skx-x16``. The C++ part of each executable is compiled for the same ISA as its ISPC target. If the list has at least two ISAs, ``16_dispatcher_overhead`` is additionally built as ``16_dispatcher_overhead.dispatch``, an auto-dispatch binary with the first target of every ISA from the list. Executables for an ISA that the host doesn't support can't be run, and their tests fail.

To run benchmarks, you need to execute them individually. They will be located in `benchmarks` folder of your install location. You can also run `make test` to verify that benchmarks are built correctly and executed successfully.

To do a performance measurements, it is recommended to do a frequency stabilization on your system. This is OS and hardware specific and there is no universal recipe, but here are the things that might work:
1. Disable CPU frequency scaling on Linux, as suggested in Google Benchmark [documentation](https://github.com/google/benchmark/blob/main/docs/user_guide.md#disabling-cpu-frequency-scaling)
2. Control the CPU core where the benchmark is running. This is especially important for heterogeneous CPUs. On Linux you can use `taskset` to pin the process to specific core. For example:
```
taskset --cpu-list 0 bin/01_aossoa.avx2-i32x8
```

## Performance dashboard

The [weekly workflow](../.github/workflows/benchmarks-weekly.yml) runs the benchmarks of ``01_trivial`` and ``02_medium`` on a dedicated machine every Saturday to Sunday night, and can also be started manually. It stores them with [github-action-benchmark](https://github.com/benchmark-action/github-action-benchmark) in the ``gh-pages`` branch and deploys it to GitHub Pages, one page per target: ``https://ispc.github.io/ispc/benchmarks/<target>/``. ``16_dispatcher_overhead.dispatch`` is shown on the ``dispatch`` page, under the name of its target list. Every case is run in 3 separate processes, and the minimum of the per-process medians is shown. Only the cases shown on the dashboard are run: one size of every benchmark function, the closest one to 4096 elements, and the largest size of benchmarks that measure memory traffic (see ``scripts/benchmark_dashboard_data.py``). If a case gets more than 10% slower than the last result of an earlier commit, the job fails (when the ``BENCHMARKS_FAIL_ON_REGRESSION`` repository variable is ``true``). Cases known to be noisy are shown in a separate "not gated" section and don't fail it. The results of every run are kept as workflow artifacts.

## TODO

### Individual language features and library functions.

- Loops: ``foreach`` loops vs ISPC ``for`` loops vs C++ ``for`` loops. Iteration limits divisible and not divisible by programIndex need to be tested.
- Nested loops: multi-dimensional ``foreach`` loops vs separate ``foreach`` loops vs ``for`` loops. Different axis for vectorization need to be tested.
- ``foreach_unique`` performance.
- ``foreach_active`` performance.
- memory operations: gather/scatter, vector load/store.
- ``aos_to_soa()``, ``soa_to_aos()`` functions.
- other ``stdlib`` function.
- ``select()`` vs ``cond ? t : f``.

### Feature combinations and non-obvious optimization effects.

- strided loads/stores, which combine to continuous loads/stores.
- dot-product and cross-product of short vectors.
- other code gen artifacts, triggered by seemingly similar code, but yielding different results.


## Builtin optimization experiments (prototype)

`scripts/builtins_lab/run.py` is the first measurement component of a builtin
optimization loop. It compares existing Google Benchmark executables from two
builds. It does not generate patches, build ISPC, prove builtin equivalence, or
promote a patch automatically. Linux and Python 3.11+ are required.

The existing measurement pilot covers shuffle on `avx2-i32x8`; this is not
evidence that shuffle is the highest-value optimization target. Build baseline and candidate with
the same LLVM, build configuration, target list, and benchmark sources. Use the
CMake settings above and keep both build directories. Supply a job JSON file:

```json
{
  "hypothesis": "Describe the expected code generation improvement",
  "baseline_revision": "full baseline commit SHA",
  "candidate_revision": "full candidate commit SHA",
  "baseline": "/absolute/base/bin/09_shuffle.avx2-i32x8",
  "candidate": "/absolute/candidate/bin/09_shuffle.avx2-i32x8",
  "checks": [
    ["/absolute/base/bin/09_shuffle.avx2-i32x8", "--benchmark_min_time=0.01s"],
    ["/absolute/candidate/bin/09_shuffle.avx2-i32x8", "--benchmark_min_time=0.01s"]
  ],
  "cpu": 1,
  "runs": 5,
  "repetitions": 5,
  "timeout": 600,
  "metric": "cpu_time",
  "min_gain": 0.03,
  "max_regression": 0.02
}
```

Replace paths, revisions, and CPU before running. Revision strings are supplied
by the caller; executable hashes are recorded independently. Add family-specific
correctness commands to `checks`: the benchmark checks in this example alone
are insufficient to establish shuffle correctness. Commands are argument arrays,
run without a shell, relative to the invoking working directory. The runner
trusts their exit codes; it cannot determine whether the selected tests are adequate.

```bash
python3 scripts/builtins_lab/run.py job.json --output /tmp/shuffle-experiment-001
python3 -m unittest discover -s scripts/builtins_lab -p 'test_*.py'
```

The output directory must be new. Every correctness command must succeed before
measurements start. A per-user host lock serializes cooperating runners across
worktrees, and all commands use the selected CPU. This does not isolate the CPU
from unrelated processes, other users, or VM host activity. Stabilize and reserve
the measurement machine separately as described above.

Measurements alternate build order each round. The output retains check logs,
all benchmark JSON and logs, executable hashes, CPU information, benchmark
contexts, and a machine-readable `report.json`. Timeouts, benchmark errors,
missing cases, duplicate cases, empty filters, and nonpositive/nonfinite timings
fail the experiment. Successful subprocess execution alone is insufficient.

For each case, the runner compares the observed ranges of process medians.
`min_gain` is a required reduction in measured time, and `max_regression` is the
allowed increase. Defaults are starting budgets, not universal thresholds.
Ranges are conservative observations, not statistical confidence intervals.

- `candidate_for_confirmation`: at least one case improves across the observed
  ranges; every other case stays within budget. Rerun the frozen candidate in a
  fresh output directory and validate it on the required target/CPU/LLVM matrix.
- `no_material_improvement`: every observed range stays within budget, with no
  qualifying gain. Leaving the implementation unchanged is a valid outcome.
- `regression`: at least one case exceeds the regression budget across its range.
- `inconclusive`: variation or a tradeoff prevents a clear decision.
- `failed`: a check, command, or result validation failed; inspect the retained logs.

Exit codes are 0 for the first two statuses, 2 for regression/inconclusive, and 1
for execution/input failure. Exit code 0 never authorizes merging a patch.

### Procedure for optimization workers

1. Assign a family, types, target widths, CPU models, LLVM versions, and a fixed
   experiment budget. Use a separate worktree for each worker. Map actual builtin
   resolution through `targetParentMap` before changing a parent implementation.
2. Establish a semantic contract and a fixed correctness suite independently of
   candidate generation. Differential testing against baseline complements an
   independent reference; baseline itself may contain bugs. Track correctness
   fixes separately from behavior-preserving optimization.
3. Reproduce baseline results. Inspect final caller assembly after inlining and
   record the hypothesis before making one small change. Check history before
   reviving an old implementation. Do not change the frozen tests, budgets,
   compiler flags, or benchmark inputs to make a candidate pass.
4. Run correctness checks, then measure. Include both dependent chains and
   independent operations when measuring latency and throughput. Include caller
   contexts, masks, and constant versus dynamic inputs. An identical assembly
   result provides no evidence of an instruction-level improvement.
5. Keep every attempt and its reason for acceptance or rejection. Stop when the
   budget is exhausted or there is no supported hypothesis. A noisy measurement,
   unsupported verifier operation, or unavailable target is unverified.
6. Recheck finalists with fresh measurements and previously unused validation
   cases. Repeated search can select lucky measurements. Review effects on child
   targets and the supported LLVM matrix; do not generalize one CPU's result.
7. Submit only a small patch with its correctness evidence, before/after assembly,
   raw timings, environment, limitations, and confirmation results.

For shuffle specifically, test different runtime permutations (identity, reverse,
rotation, broadcast, and mixed selection from two vectors), using distinguishable
source vectors and lane values. Exercise only indices permitted by the contract.
Cover active masks and constant-index callers separately. The existing shuffle
benchmark's runtime permutation is identity and its two input vectors contain the
same values; it is a useful timing case, not a complete correctness oracle.

The independent AVX2 x8 shuffle validator can be run against either compiler:

```bash
python3 scripts/builtins_lab/validate_shuffle.py --ispc build/bin/ispc \
  --cxx clang++-20 --output build/shuffle-validation-baseline
```

The output directory must be new. It retains generated ISPC and scalar C++
reference sources, compiler versions and hashes, commands and logs, object code,
final caller assembly, and `validation.json`. Validation covers signed/unsigned
8/16/32/64-bit integers, float and double, all 256 output masks, every legal
source index at every output lane, seeded random permutations, and constant-index
callers. The reference compares bits, including NaNs and signed zero. Inputs are
loaded before divergence; indices outside the valid domain are never exercised.
This is not exhaustive over input values, does not cover float16, and does not
validate other targets or widths. A passed run establishes no performance gain.
Its retained `validate-shuffle` executable can be included in a job's `checks`.
Recompile it with each compiler before comparing baseline and candidate.

Fixed caller contexts can be built against either compiler with:

```bash
python3 scripts/builtins_lab/build_shuffle_bench.py --ispc build/bin/ispc \
  --build build --cxx /absolute/llvm/bin/clang++ --type int64 \
  --output build/shuffle-contexts-baseline
```

`--type` supports `int16`, `int64`, and `double`. The build must contain Google
Benchmark (`ISPC_INCLUDE_BENCHMARKS=ON`). Sources, compiler hashes, commands,
assembly, and logs are retained. Each binary independently checks all caller
contexts against a scalar simulation before listing or timing any cases.
The output directory must be new. Generate baseline and candidate from the same
script and verify identical generated-source hashes before comparing them.

The contexts include dependent chains, four independent chains, and L1-sized
load/shuffle/store loops. Runtime inputs cover identity, reverse, rotation,
broadcast, and mixed selection. Two-input and partial-mask callers provide
regression coverage. Constant-index callers are code-generation controls:
repeated reversals may cancel, so their timings do not establish shuffle latency.
Google Benchmark appends `/min_time:0.100` to names; account for that suffix in
anchored filters. Inspect `--benchmark_list_tests=true` before freezing a job.
Do not alter sources, thresholds, or case coverage after seeing a candidate's
timings. A failed empty filter must be retained and corrected before measuring.

Use the supported LLVM build with the patches in `llvm_patches/` when establishing
baseline. Compiler version alone does not describe the toolchain: for example,
different LLVM builds can lower the same generic shuffle to scalar stack loads
or native vector instructions. Inspect final caller assembly on the actual
toolchain before proposing an optimization. Keep failed attempts and restore
the original implementation when none stays within the frozen regression budget.

### Agent workflow: research before patch design

The coordinator maintains the process, prompts and evaluation policy. A research
agent performs code analysis and baseline probes; the coordinator reviews the
evidence rather than substituting its own hotspot search. Generate its task with:

```bash
python3 scripts/builtins_lab/research.py prompt --repo /absolute/ispc \
  --baseline FULL_40_CHARACTER_COMMIT_SHA --output /absolute/new/research
```

Dispatch the generated `agent-task.txt` to the research agent. The task requires a
comparison of at least three builtin families and baseline caller probes for the
two strongest hypotheses. It asks for source/history references, retained assembly,
commands and hashes, caller relevance, concrete cost mechanisms, regression risks,
disproof criteria, and the next bounded experiment. It prohibits compiler patches
in this phase. Source complexity is a suspicion; final assembly verifies codegen;
only workload measurements establish a runtime hotspot. A representative caller
alone does not establish frequency or application impact.

```bash
python3 scripts/builtins_lab/research.py validate /absolute/research/report.json \
  --repo /absolute/ispc
```

The validator requires three distinct families, references to the pinned source,
and matching hashes of retained evidence. Selecting a candidate requires observed
codegen and an identified representative caller. `selected: null` is a valid
abstention with status `needs_more_evidence`. `ready_for_patch_design` only passes
the structural handoff; it does not prove the claims, approve an optimization, or
launch the patch evaluator. Review the ranked evidence and reject unsupported
claims before assigning a patch agent. Do not demand a successful selection.

After technical review accepts the selected research hypothesis, generate the
next agent task:

```bash
python3 scripts/builtins_lab/research.py design /absolute/research/report.json \
  --repo /absolute/ispc --output /absolute/new/design
```

This refuses an abstention and freezes the selected report in the new output.
The agent resolves the public contract, implements and runs an independent oracle
against the baseline, freezes representative cases, and proposes one candidate
algorithm without implementing it. Review its `design.json`, oracle and retained
commands before adapting the evaluator or assigning a patch experiment. Task
generation is not technical approval; the coordinator owns that review.

After review, freeze the selected hypothesis, target, representative workload,
semantic oracle, constant/masked controls and regression budget. If the selected
family lacks evaluator coverage, build and review that coverage before patch
experiments; do not change an allowlist to force it into the shuffle pilot.
Then assign one bounded patch experiment to an agent and submit it to the fixed
evaluator below. A failed experiment returns to the hypothesis and its disproof
criterion, rather than prompting repeated blind rewrites. An inconclusive result
retains its status until new evidence justifies a predefined follow-up.

The scripts generate tasks and validate artifacts; agent dispatch and technical
review belong to the coordinator. The low-level `evaluate.py` remains available
for reproducing existing experiments and does not enforce this research workflow.

### Tiered validation: cheap ideas first

Do not rebuild ISPC or run the complete evaluator for every low-level variant.
Use these levels; only a promising idea earns the cost of the next level.

| Level | Purpose | Work |
|---|---|---|
| T0: kernel screen | Quickly reject weak standalone hypotheses | Tiny driver + two kernels, small independent oracle, short paired batches; no ISPC rebuild, full suites or profiler |
| T1: focused caller check | Check whether the gain survives real ISPC codegen and masks/constants | Family oracle and a small representative caller subset; reuse binaries; prepare one candidate compiler only after T0 |
| T2: acceptance | Decide whether a production patch qualifies | Complete fixed evaluator, frozen corpus/budgets, full lit/family checks and independent confirmation |

T0 is implemented by `screen.py` plus `screen_kernel.cpp`; it needs only clang++,
not Google Benchmark, CMake or a candidate compiler. The initial reviewed fixture
is all-on `reduce_equal` for eight integer64 lanes on AVX2 Linux. Other builtin
families require their own fixture; do not relabel these semantics as generic.
For example, this command builds two standalone assembly hypotheses and measures
them (on the development host, about two seconds including compilation):

```bash
python3 scripts/builtins_lab/screen.py \
  --baseline scripts/builtins_lab/screen_examples/reduce_equal_scalar.S \
  --candidate scripts/builtins_lab/screen_examples/reduce_equal_avx2.S \
  --cxx /absolute/llvm/bin/clang++ --cpu 2 --output /absolute/new/screen
```

Trusted `.S`, `.s`, `.cpp` sources or prebuilt `.so` files export this Linux SysV
adapter ABI (not ISPC's public ABI):

```cpp
extern "C" void lab_kernel(const uint64_t *input, uint64_t *values,
                         uint64_t *flags, size_t groups, size_t repeats);
```

Each group contains eight input words. Every repetition computes equality and
writes a 0/1 flag; `values[g]` is meaningful only on true. Zero groups/repetitions
perform no writes. Kernels must execute the repeated work; avoid compiler hoisting
in C++ adapters. The included assembly kernels do so explicitly. They are synthetic
hypotheses, not exact extracted production ISPC loops.

The fixed oracle checks all lanes and all 64 differing bits independently of the
timed working set, equality/extreme values, zero work, input integrity and output
canaries. It does not establish mixed-mask or public-overload correctness. A bad
kernel stops before timing results. Timing uses calibrated batches, a pinned CPU,
alternating A/B order, retained output consumption, and five paired samples for
equal/early/late inputs. The default screen takes a fraction of a second after
building; `report.json` separates build, measurement and end-to-end elapsed time.
TSC reference ticks and wall nanoseconds are retained; TSC ticks are not core cycles.

Only consistently greater-than-5% differences get a direction label; all other
results are `unclear`. This rough filter is not a significance test or the T2
regression policy. Its status is always `screened_not_accepted`. Source/binary
hashes, commands and raw pairs remain reviewable. The common per-user host lock prevents
overlap with other lab timings. Passing T0 does not prove the compiler emits this
code or that the gain survives inlining, masks, constants or a different workload.

For primitive instruction comparisons, prefer `--body-mode`. Both `.inc` inputs
are inserted into the same retained `screen_frame.S`; agents cannot change loop
updates, repetition, conditional output handling or exits through that interface.
For an identity control, use the same body on both sides:

```bash
python3 scripts/builtins_lab/screen.py --body-mode \
  --baseline scripts/builtins_lab/screen_examples/reduce_equal_body.inc \
  --candidate scripts/builtins_lab/screen_examples/reduce_equal_body.inc \
  --cxx /absolute/llvm/bin/clang++ --cpu 2 --output /absolute/new/body-identity
```

A body reads one unaligned 64-byte group through `rdi`, returns a normalized 0/1
in `eax`, and may clobber only vector registers, `rax`, `r9`–`r11` and flags.
The shared frame normalizes the return width before storing a 64-bit flag. It
provides disjoint input/output buffers; overlapping-buffer equivalence is not
established. The narrow trusted-input dialect rejects directives, labels, calls,
branches, stores, protected-register operands and reads outside that group.
This is not a hostile assembler sandbox; semantic correctness still needs the
independent oracle and source review. Raw bodies, expanded assembly and frame
hashes are retained. Different body lengths can still shift later addresses and
branch encodings, so a common frame does not eliminate all layout effects.

Keep whole-kernel mode for explicit scheduling/loop studies and label those
conclusions accordingly. A gain from deleted loop instructions is not evidence of
a better builtin primitive. Likewise, retain actual LLVM/ISPC-emitted bodies when
checking compiler correspondence: a plausible hand-written instruction sequence
may differ from optimized lowering. T1 can reuse retained compiler/benchmark
binaries for a small frozen caller panel; report preparation/build cost separately
and never relabel a short panel as complete acceptance.

During agent tasks, save artifacts first, stop after one bounded variant, and send
only the selected idea to T1/T2. Use profiling for a specific unresolved mechanism;
do not make a broad profile a prerequisite for every cheap kernel screen. Candidate
compiler build cost still exists at T1 and must be reported separately from timing.

### All-on popcnt int64 T0 fixture

`screen.py --fixture popcnt-i64` (kernel mode only) screens `popcnt(varying int64)
-> varying int32` for eight lanes. Kernels export a different adapter ABI:

```cpp
extern "C" void lab_kernel(const uint64_t *input, int32_t *counts,
                           size_t groups, size_t repeats);
```

Every repetition writes `counts[g * 8 + lane]` for all groups; no other bytes.
`screen_popcnt_kernel.cpp` checks both kernels before any timing against a
bitwise oracle (no popcnt instruction): random/sparse/dense data at 0, 1, 3 and
the timed group counts, every lane x bit with all other bits clear and set,
every count 0..64 in every lane, and nibble/byte boundary patterns. It also
checks one-group canaries on both sides of the output, unchanged input, and
that zero repetitions write nothing. Timed cases are `random`, `sparse` and
`dense` with the same paired estimator as `reduce_equal`. Kernels are built
with `-mavx2 -mpopcnt`.

`screen_examples/popcnt_i64_scalar.S` is the default baseline: its loop body is
what ISPC emits today for `dst[i] = popcnt(src[i])` on avx2-i32x8 (eight
memory-operand `popcntq`, `vpinsrd` assembly, two stores). Callers whose value
is already in registers pay extra extracts that this baseline does not model.
`popcnt_i64_avx2_lut.S` (vpshufb nibble lookup + vpsadbw) is a positive control;
on the i9-11900K bench host it screens at about 0.588x, and a baseline A/A at
1.0000 +/- 0.003%. Masked/partial popcnt and ISPC integration remain T1 work.

### Masked popcnt int64 T0 fixture and T1 packet

`screen.py --fixture popcnt-i64-masks` (bench task `"builtin": "popcnt", "masks": ["masks"]`;
`["all", "masks"]` runs both popcnt fixtures) times nine cases in one screen. Kernels export
three symbols with one signature:

```cpp
extern "C" void f(const uint64_t *input, const int32_t *mask, int32_t *out,
                  size_t groups, size_t repeats);  // lab_popcnt, lab_popcnt_even, lab_popcnt_chain
```

`out[8g + l] = mask[8g + l] ? popcount(lane) : 0` with 0/-1 mask lanes. `lab_popcnt` takes a
runtime mask (cases `all_on`, `even`, `odd`, `sparse_one_lane`, `random_mixed`, `all_off`),
`lab_popcnt_even` models a compile-time even mask after inlining (`even_static`: the generic
builtin then needs only four scalar POPCNTs) and `lab_popcnt_chain` feeds each group's result
into the next group's input (`chain_all_on`, `chain_even`, latency). The oracle
(`screen_popcnt_masks_kernel.cpp`, bit-clearing loop) checks all 256 lane masks, every single-bit
position, density patterns, zero inactive lanes, canaries, unchanged input/mask and zero repeats.
Default baseline `screen_examples/popcnt_i64_ispc.S` is generated by stock ISPC from
`popcnt_i64_kernels.ispc` (command in its header): runtime-mask cases call a noinline
`popcnt(int64)` whose body is exactly what ISPC emits for a register-resident value (8 x
vmovq/vpextrq + popcntq, vmovd/vpinsrd packing, vpcmpeqd/vpandn select). Candidates for a
builtin patch should be generated from the same source by the patched ISPC
(`popcnt_i64_croaring_ispc.S`), so both sides share every instruction outside the builtin.
`popcnt_i64_croaring.cpp` (hand-written two-table vpshufb + vpsadbw) and
`popcnt_i64_llvm_ctpop.cpp` are references. Every shipped kernel exports both ABIs, so one
candidate file serves `popcnt-i64` and `popcnt-i64-masks`.

T1/full for `"builtin": "popcnt"` uses the fixture packet `packets/popcnt_i64_avx2/` (pinned by
sha256 in the policy) instead of the shuffle contexts: caller contexts from
`benchmarks/01_trivial/03_popcnt` (`official_all`, `official_even`), streams with all-on, static
even and runtime masks, an array reduction, dependent chains and two unchanged controls
(`control_int32`, `control_uniform_int64`). The packet allows patches to
`builtins/target-avx2-i32x8.ll` and `tests/lit-tests/3615.ispc` (which pins the scalar
`llvm.ctpop.i64` codegen) and runs `tests/func-tests/popcnt*.ispc`. `fixture_packet.py` now
accepts explicitly listed `tests/lit-tests/*.ispc` paths in a packet next to builtin sources.

### Proper partial masks in a common T0 frame

`screen.py --fixture mixed-mask --body-mode` uses a separately versioned fixture,
`reduce_equal_i64_proper_partial_v1`. It never changes the frozen full-evaluator
corpus. The six-argument SysV kernel ABI is input i64s, mask i32s, output values,
output flags, group count, repeat count. Input, masks and outputs must be disjoint
and fully accessible. Masks use the sign bit, including noncanonical negative
words; every group must have at least one active and one inactive lane.

The shared frame loads both input halves and the existing eight-word mask,
selects the first active scalar with movemask/bit scan and broadcasts it. Bodies
receive input halves in ymm0/ymm1, mask in ymm2 and broadcast base in ymm3, and
return normalized EAX. Bodies can change vector registers, RAX, R10/R11 and flags;
they cannot touch memory, pointers, stack, loop state or R9 (the saved scalar).
The frame owns all pointer steps, repeats, output flags and conditional samevalue
stores. It preserves output values on false as a fixture property, without making
that claim about the public builtin contract. Zero groups/repeats write nothing.

```bash
python3 scripts/builtins_lab/screen.py --fixture mixed-mask --body-mode \
  --baseline /absolute/reviewed-baseline-body.inc \
  --candidate /absolute/reviewed-candidate-body.inc \
  --cxx /absolute/clang++ --cpu 2 --output /absolute/new/mixed-t0
```

The independent scalar oracle covers all 254 proper partial masks, four
sign-equivalent representations, an equal input and every bit in every lane as
a single mismatch, plus zero/odd/multiple groups and repeated calls. It checks
true samevalue, false preservation and input/mask/output boundary canaries. The
timed corpus uses masks 0x55/0xaa/0x7f/0xfe with equal, first-active-different and
last-active-different data. These three cases combine densities; they are not
separate estimates for each mask. Presets, threshold and paired order match the
existing T0 screen; a promising result earns only real-caller investigation.

This frame has no guard for empty/full masks; its fixed fixture never generates
them. It cannot test all-off behavior, inaccessible inactive addresses, arbitrary
aliasing or LLVM poison at runtime. Poison suppression needs an IR/source argument
using `select(active, eq, true)` before reduction. A modeled LLVM comparison graph
must be labeled as modeled, even when its emitted body is retained exactly. Record
any register renaming, removed wrappers and normalization adapters. Common framing
does not eliminate code-layout effects or prove production ISPC lowering.

### Disposition of uncertain T2 measurements

Keep the original evaluator rule and all earlier inconclusive results unchanged.
The reviewed paired-median proposal is not an installed acceptance policy.
Observed min/max envelopes and descriptive order-statistic ranges are not
confidence guarantees. Record pairing, order, drift and serial correlation to
explain uncertainty; these diagnostics cannot prove independent stationary
samples or turn an inconclusive result into a pass.

A completed 32-pair baseline-only diagnostic of the frozen 22-case corpus took
about 30 seconds with retained binaries. It establishes practical cost for that
session, not statistical calibration. A mandatory twelve-session campaign is not
justified as an iid certification step: finitely many quiet sessions cannot prove
the needed assumptions. Do not fit invalidation thresholds to candidate data or
silently install null thresholds. A future selected candidate may justify a new
reviewed, frozen, bounded paired diagnostic, with no acceptance claim, replacement
pairs, post-result budget changes or repeated trials until it passes. Full T2 and
fresh confirmation remain distinct from exploratory diagnosis.

### Short real-caller T1 probes

`focus.py` runs a frozen small caller panel using existing benchmark and oracle
binaries. It does not build ISPC or require a completed T2 evaluation. The
coordinator prepares a trusted job after reviewing the family oracle, actual
generated assembly and panel coverage. A worker must not choose its own checks
or remove cases after seeing a result. The schema is deliberately separate from
the full evaluator's acceptance policy:

```json
{
  "schema": 1,
  "hypothesis": "A reviewed code generation change survives these caller contexts",
  "baseline": {"path": "/absolute/baseline-contexts", "sha256": "64_lowercase_hex_digits"},
  "candidate": {"path": "/absolute/candidate-contexts", "sha256": "64_lowercase_hex_digits"},
  "checks": [{"path": "/absolute/independent-oracle", "sha256": "64_lowercase_hex_digits"}],
  "cases": ["exact/registered/case/name"],
  "provenance": [{"path": "/absolute/reviewed-fixture-manifest.json", "sha256": "64_lowercase_hex_digits"}]
}
```

Every field is required; executable checks take no arguments. Pin both builds'
oracles, fixture sources, submitted patch and generated assembly in provenance.
Additional files such as runtime libraries can also be pinned. Hashes establish
artifact identity, not oracle adequacy or semantic equivalence. The coordinator
remains responsible for that review. Identical baseline/candidate binaries are
allowed for identity controls.

```bash
python3 scripts/builtins_lab/focus.py /absolute/job.json \
  --job-sha256 SHA256_OF_JOB --output /absolute/new/t1 --cpu 2
```

The runner freezes the job, protocol and current tools, acquires the same exclusive
host lock as other lab timings, verifies inputs, runs every oracle, then verifies
both exact filtered inventories before timing. Three pairs use AB, BA, AB order;
each process uses one repetition and 0.01 seconds minimum time per case. Missing,
duplicate, failed or nonpositive/nonfinite measurement rows invalidate the trial.
Time units are normalized before ratios. All identities are checked again after
measurement. Outputs retain raw JSON, logs, commands, paired ratios and descriptive
observed ranges; these ranges are not confidence intervals.

Lock acquisition is limited to 30 seconds. Active work has a 60-second deadline,
with 30 seconds for preflight, 15 seconds for measurement, and at most 10 seconds
per subprocess. Local hash loops and stage boundaries check remaining time;
filesystem stalls and cleanup can delay the return, but an expired deadline cannot
produce a successful result. Initial input setup has no hard deadline and is
reported separately. A panel too large for the fixed budget fails without retry.
Output directories must be new, and failures preserve partial evidence.

The only completed status is `focused_panel_complete_not_accepted`, always with
`accepted=false`. Three short pairs cannot establish a 2% regression bound. A panel
informed by earlier measurements is not independent confirmation. Build time is
zero because binaries are reused; preparing a candidate compiler/caller still
costs time outside this run. Record that cost separately. T2 and fresh confirmation
remain necessary for a production decision; this runner never rewrites old T2
results or automatically promotes a candidate.

### Paired T1 timing protocol (`"protocol": "paired"`)

With a fixture packet, an `evaluate.py` policy may add `"protocol": "paired"`,
`"pairs"` (20..400) and `"layout_pad"` (bytes, not a multiple of 64). Timing then
uses `paired.py` instead of `run.py`; builds, oracles, lit and functional gates are
unchanged. `bench_adapter.py` uses it for T1 with 80 pairs, 48 bytes, 0.97/1.03.
All of this is frozen before timing:

- One pair is one first-binary and one second-binary process, back to back, in
  AB/BA order alternating between pairs; each process runs every frozen case once.
  Per case: 20% trimmed mean of per-pair cpu_time ratios, seeded bootstrap CI95.
- A/A gate: baseline vs baseline. Every case's CI must lie inside
  [1 - min_gain, 1 + max_regression], otherwise `aa_gate_failed` and no A/B.
- Layout control (not a gate, not tuning): baseline vs the same objects relinked
  with `layout_pad` bytes before the ISPC object. The evaluator verifies that all
  ISPC symbols moved by one offset off their 64-byte phase and the inventory holds.
- Per-case threshold = max(bound, A/A excursion, layout excursion), where an
  excursion is the largest distance of a CI bound from 1.
- A/B: `improvement` if CI_high < 1 - threshold, `regression` if CI_low > 1 +
  threshold, else inconclusive. Any non-control regression wins, then any moved
  `control_*` case (`control_moved`), then improvement (`candidate_for_confirmation`).
- Confirmation is a fresh A/B with discovery's frozen thresholds.

Lit gates accept failures that the cached baseline already had (recorded in
`baseline.json` and `evaluation.json`); the candidate may add none, and a lit run
without its summary is an error.

### Preparing a candidate for T1 without full T2

`prepare_t1.py` accepts the same trusted policy, two-field worker request and
worker name as `evaluate.py`, but requires a reviewed fixture packet and an
existing valid baseline compiler cache. A cache miss stops; this command never
initializes a worktree, configures a cold build or builds a baseline compiler.
Prepare that cache separately through the full evaluator first.

```bash
python3 scripts/builtins_lab/prepare_t1.py /absolute/request.json \
  --policy /absolute/reviewed-policy.json --worker existing-worker \
  --output /absolute/new/preparation
```

Under the existing worker lock and shared host lock it checks the pinned cache,
compiles both sides' frozen oracle/callers with the retained baseline and one
incrementally built candidate compiler, runs both oracles and verifies exact
inventory and source parity. It restores original source bytes and checks a clean
pinned checkout before emitting `focus-job.json`. Changed input identities or
failed restoration invalidate preparation and prevent a ready job. Candidate
binaries, patch, assembly, IR and logs remain available after restoration.

The checked preparation deadline is 900 seconds including initialization/queues,
with at most 30 seconds per lock acquisition and 300 seconds per subprocess,
clamped to the remaining budget. Local filesystem stalls/cleanup can delay return;
expired preparation cannot report readiness. Cleanup still runs after timeout.
Each command duration and total preparation time are retained. Source restoration
does not rebuild the mutable candidate compiler: only the separate pinned
`baseline-ispc` may supply baseline fixtures on a later run.

If the built compiler is byte-identical to the pinned baseline, preparation
restores the source and ends as `no_compiler_change_not_accepted`, without a
candidate fixture or focus job. This identity gate cannot prove that a changed
compiler contains the intended optimization. Before paying for a compiler build,
inspect full target emission and inherited modules: testing an isolated m4 macro
or merely assembling an entire target is insufficient. Assert the exact expected
function definition and new path are present in the module actually selected by
ISPC. After preparation, review real caller code before allowing any timing.
Assembly text hashes can differ solely because debug/source paths differ.

The prepared status is `prepared_for_T1_not_accepted`, with `accepted=false`.
Full lit, family functional tests, inherited VNNI validation, discovery and fresh
confirmation remain T2 gates and are explicitly recorded as skipped. Preparation
never launches timings. Review generated caller code and the hash-pinned focus
job, then invoke `focus.py` separately; it obtains exclusive host access itself.
The original full evaluator retains its existing validation order and decisions.

### Executing agent tasks through agy

Prefer the configured agy CLI for research/design execution in this lab.
The coordinator maintains the process and reviews evidence. Send a retained task
through this adapter instead of starting another coordinator subagent session:

```bash
python3 scripts/builtins_lab/dispatch_agy.py /absolute/agent-task.txt \
  --repo /absolute/ispc --output /absolute/new/dispatch --timeout 360
```

The adapter uses the existing agy configuration and default model. It does not
manage credentials or infer backend token accounting. It enables the CLI sandbox,
uses an owned working directory, and does not enable permission-bypass flags.
The task must explicitly name its allowed output paths and prohibited repository
edits. Generated task output paths remain authoritative; dispatch logs live in
the separate new dispatch directory.

`dispatch.json`, `task.txt` and `agy.log` retain the executable/task hashes,
arguments, timeout/failure and before/after Git HEAD, status and tracked-diff
identity. These are cooperative audit checks, not a complete filesystem sandbox.
The log uses stream JSON for backend progress and any reported session/usage
metadata. Pass `--expect result.json` (repeatable) for task-specific output files.
An agy print timeout can return exit code zero while the turn is incomplete;
the adapter labels it `partial`. CLI timeout does not prove remote cancellation,
so do not automatically resubmit a partial task or accept an initial draft.
`process_exited_for_review` only records a successful process exit. Review the
task's actual result and evidence, then apply the existing research/design and
fixed-evaluator gates. Neither an agy response nor process success accepts a
patch, publishes code or weakens the frozen experiment policy.

Use separate bounded research, fixture-design and patch-delivery tasks. Every task
must name absolute shared output paths, write its initial status first, and save
reviewable artifacts before optional explanation. An agent terminal's temporary
directory may disappear between turns or be invisible to the coordinator. Never
accept a prototype that exists only in a log or private temporary directory.
On partial output, inspect the existing conversation and artifacts before steering
that conversation; preserve every rejected patch rather than overwriting evidence.

Before building a shared m4 candidate, review every selected and nonselected
ISA/type/width expansion. Require complete fallback branches, valid predecessor
lists and no duplicate definitions. Preprocess and assemble the selected target,
its inherited child, neighboring widths and an unrelated ISA; compare nonselected
function bodies to baseline. `git apply --check` establishes patch applicability
only. An agent's `patch_ready` declaration does not establish valid IR or scope.
Repair concrete delivery/syntax/scope failures before any timing; algorithmic
rewrites still require returning to the hypothesis and its disproof criterion.

### Runtime evidence and profiler inputs

The objective is a reusable framework for builtin families. A particular
application is not required. Before a patch experiment, review a baseline execution
profile for the controlled family workload corpus. Representative microbenchmarks
are valid primary inputs here. Keep their conclusions scoped to the cases and CPU;
application profiles can later add external validation, without becoming a gate.
Oracle execution is a correctness workload and must not be substituted for the
optimization workload.

Freeze relevant corpus dimensions before candidates exist: active masks/density,
constant and dynamic arguments, data distributions, working-set/locality regimes,
dependency chains and independent calls, inlining/hoisting, and result consumption.
Use a justified set of cases rather than an arbitrary Cartesian product. Compare
per-case effects and worst regressions under the frozen policy; do not invent
application-frequency weights or collapse them into a universal score. Profiling
explains the mechanism in those contexts, while separate timing determines benefit.

The research packet should include workload/input provenance, binary/toolchain
hashes, optimized build flags and symbol availability, exact replay commands,
sampled hot regions mapped to caller source/assembly, and raw hardware counters.
Start with time distribution, then investigate the observed bottleneck: memory
access, instruction/dependency cost, speculation, or front-end pressure. Generic
counter totals do not establish a top-down breakdown or pinpoint an instruction.
Inlined builtins are analyzed inside the optimized caller. Sampling can skid;
source attribution depends on debug information and compiler transformations.

`collect_profile.py` retains basic user-mode counters, cycle samples and annotated
assembly using an explicitly selected Linux perf binary. It shares the host lock
with timing experiments, pins a CPU and records failures and unavailable counters.
For example, adjust paths, inputs and filter to a meaningful several-second run:

```bash
python3 scripts/builtins_lab/collect_profile.py --perf /absolute/perf --cpu 2 \
  --kind microbenchmark --description "input distribution and working set" \
  --output /absolute/new/profile -- /absolute/benchmark --benchmark_filter=CASE
```

Read `profile.json`, `stat.csv`, `perf.data`, `hotspots.log` and `annotation.log`
together. Check counter availability, running percentages/multiplexing, sample
count, unresolved symbols and workload coverage before interpreting ratios.
`collected_for_review` means artifacts were collected, not that a bottleneck was
proven. Keep profiler runs separate from unprofiled performance acceptance runs.
The collector does not gather model-specific memory-latency or top-down events;
those need a reviewed CPU-specific collection (for example VTune) if the observed
problem calls for it. Do not infer them from IPC or cache-miss totals alone.

For adaptive benchmarks, `perf stat -r N` runs N complete processes. Keep and
decode all N benchmark output documents separately. A mean whole-process counter
divided by the mean reported iteration count is only a descriptive proxy: startup,
calibration and preflight work remain in the counter numerator. Never divide stat
aggregates by the separate `perf record` process's iterations, or treat repetitions
as new acceptance observations. Missing repetition metadata means this normalized
metric is unavailable. Retain counter running fractions and raw denominators;
reported counter variation is not a confidence interval. Short cycle profiles may
contain only dozens of samples, insufficient for precise instruction costs.

Check caller specialization before generalizing a dynamic-mask win. The old
constant-mask path may already lower to a cheaper graph. Freeze both static and
runtime masks in T1, and verify any compile-time helper actually resolves in the
optimized caller; O0 or disabled mask optimizations may behave differently. A
folded constant control can mostly measure the host adapter and dispatch.
Verify that it is still folded in each candidate: inspect the executed CFG and
trip count for the frozen input, not just whole-function instruction counts or
the absence of helper calls. A late-resolved specialization helper can leave an
actual loop where the baseline computes a closed-form count. A shorter function
can therefore execute more work. Earlier profiling of a folded control does not
transfer to a new binary whose executed path changed. Retain
its negative timing and inspect executed bytes, addresses and sample distribution;
do not subtract overhead, tune alignment, discard the control or declare layout
causality from matching source instructions alone.

Profiling bundles should freeze their cases, order, identities and total deadline
before execution, and stop on the first failure without replacement. The collector
owns exclusive host access; a parent supervisor must not hold a shared/exclusive
host lock while waiting on that child. Its outer process timeout must also bound
the collector's lock wait and preserve partial evidence. Source/LLVM preparation
can resume once the serialized profiling phase is finished.

The research validator requires a hashed collector report for `profiled` claims.
It still permits codegen-only hypotheses to reach oracle/design review, while
explicitly returning `runtime_evidence: not_established`. No such status is proof
of application relevance, which is not a prerequisite here. Review missing corpus evidence
before assigning a patch experiment.

The workflow follows Intel's [Hotspots then Microarchitecture Exploration
guidance](https://www.intel.com/content/www/us/en/docs/vtune-profiler/user-guide/2026-1/general-exploration-analysis.html).
Profiler capability must be checked on the actual host/VM; installing a tool alone
does not establish PMU event availability.

### Reviewed fixture packets for another builtin family

The maintainer can freeze a reviewed oracle/corpus as a packet before candidate
generation. Add `packet` (absolute `packet.json` path) and `packet_sha256` to the
maintainer policy, then use the same `evaluate.py` command. Worker submissions
still contain only `hypothesis` and `patch`; they cannot select or replace a packet.
Omitting these policy fields retains the shuffle pilot.

The initial packet schema supports integer64 policies on `avx2-i32x8`. Its JSON
has `schema: 1`, `name`, `target`, exact `allowed_paths` under `builtins/`, a
`sources` map of SHA256 hashes for `oracle.ispc`, `oracle.cpp`, `contexts.ispc`,
`contexts.cpp`, `config.h`, exact `cases`, `discovery_cases` (a subset), local
`functional_globs`, and generated `oracle_header`/`benchmark_header` basenames.
Review source scope and semantics before pinning this manifest. These are trusted
maintainer inputs, not a sandbox for hostile C++ or IR.

The evaluator copies the verified source bytes into each run, freezes all hashes,
compiles both sides with the same fixed flags/library, runs the oracle and rejects
inventory drift before timing. It retains full lit tests and the packet's existing
functional tests, and compiles the VNNI child with runtime explicitly unverified.
Compiler caches remain keyed by compiler inputs; fresh packet fixtures/checks are
never reused from another evaluation. Original worker sources are restored after
the experiment, including failure paths.

Establish baseline repeatability against the intended regression budget before
spending a broad optimization sweep on timing. If identity controls cannot resolve
that budget, keep performance promotion unresolved while designing a revised
measurement study. Freeze any revised policy before its experiments; never loosen
the active experiment's budget in response to a candidate's results.

If discovery is inconclusive, preserve that result and the complete corpus. A
reviewed diagnostic follow-up may run one baseline-versus-itself arm and one fresh
whole-corpus baseline/candidate arm using the frozen binaries, cases, flags and
budgets. Record the exact arm count and stop rule before timing; never rerun until
a candidate passes. Diagnostic arms do not automatically supersede the original
acceptance result. Retain all failed or inconclusive evidence.

The same-binary control estimates repeat variability, not the effect of differing
binary layouts. Observed ranges from a few processes are not confidence intervals;
overlapping ranges do not prove that a candidate difference is noise. Identical
function instructions do not prove identical placement or whole-program behavior.
Code-size changes and branch counts suggest mechanisms, not causal attribution.
Measure object/symbol sizes when discussing code size: assembly-text file length
also contains labels, debug directives and formatting. Constant-folding checks and
assembly comparisons supplement the frozen timing controls; they do not remove
inconclusive controls from the acceptance inventory.

Discovery and confirmation can use the same frozen corpus with independent fresh
timing processes. Do not claim unseen-data validation unless the manifest actually
contains reserved cases. The integer64 reduce_equal pilot uses 22 cases: signed
and unsigned, full/fixed/runtime masks, equal/early/late differences, constants,
and L1/small working-set versus 256 KiB input cases. The latter is not a DRAM
streaming claim. Accumulation versus store is a context comparison, not a clean
causal decomposition of store cost; accumulation adds its own dependency.

### Submitting a patch to the fixed evaluator

`evaluate.py` runs the shuffle pilot or a reviewed fixture packet without manual
build or measurement steps. A maintainer provides a policy JSON; a worker provides only a hypothesis
and an absolute patch path. For example, copy and adjust this policy:

```json
{
  "repo": "/absolute/ispc",
  "baseline_revision": "818b8e23a35c852d9cc19b14d5510c4e7fadbcc0",
  "llvm": "/absolute/llvm/bin",
  "cache": "/absolute/ispc-lab-workers",
  "type": "int64",
  "cpu": 2,
  "runs": 3,
  "repetitions": 3,
  "min_gain": 0.03,
  "max_regression": 0.02,
  "jobs": 2,
  "timeout": 1800
}
```

Use a supported LLVM with the ISPC patches and a full baseline commit SHA.
Replace all paths and select an available CPU. `timeout` is seconds per stage.
The first invocation requires network access to initialize pinned submodules.
The policy, toolchain and evaluator are trusted inputs; keep them separate from
worker-editable proposals. The request has exactly these two fields:

```json
{
  "hypothesis": "Describe a testable code generation improvement",
  "patch": "/absolute/candidate.patch"
}
```

```bash
python3 scripts/builtins_lab/evaluate.py request.json --policy policy.json \
  --worker worker-1 --output /absolute/new/experiment
```

The current adapter accepts content changes only to the existing
`builtins/target-avx2-i32x8.ll`. It rejects edits to tests, benchmarks, evaluator,
file modes, new files and other targets. The submission cannot override tests,
case inventory, flags or budgets. These are cooperative workflow checks, not an
OS sandbox for hostile code. Expanding the allowed family requires review.

Each worker owns a separate detached worktree and incremental build directory.
Baseline cache identity includes the commit, LLVM executable and resolved shared
library hashes, CMake flags, and build schema. Evaluator hashes are frozen in
each evaluation; fixtures and correctness checks are regenerated rather than
cached. This permits driver fixes without rebuilding an identical compiler.
The reusable baseline marker
is published only after successful build and lit tests. Later submissions reuse
the frozen baseline executable and incrementally rebuild the candidate. A worker
lock protects the checkout through restoration; do not edit owned worker trees.
Build/test stages share host access, while measurements request exclusive host
access. This prevents cooperating adapters from compiling during another's
measurements. Unrelated processes, other users and VM host activity remain outside
this coordination. Commands run by nested lab helpers share their owner's process
group. Timeout cleanup also walks owned Linux descendants, covering compiler
processes that create separate sessions or groups.

Every candidate passes the independent bitwise oracle, all caller-context checks,
lit tests and existing shuffle functional tests before timing starts. The VNNI
child is compiled separately; its runtime status remains explicitly unverified.
The discovery phase uses an exact inventory of 12 cases. Only a qualifying result
triggers fresh confirmation across all 48 cases, including unused permutations.
The raw runner rejects a missing frozen case even if both builds omit it.

`evaluation.json` records stages, commands, hashes, build environment, decisions
and errors. Outputs retain the submitted patch, policy/request, frozen evaluator,
CMake cache, generated sources, assembly, check logs and raw measurements. Failed
submissions retain an audit record. The original builtin is restored in the owned
worker even after a failed build; candidate binaries and evidence remain available.
A hard process/host crash can require manual inspection of that worker before reuse.

Statuses are `confirmed_for_review`, `no_material_improvement`, `regression`,
`inconclusive`, or `failed`. Exit codes are 0 for the first two, 2 for regression or
inconclusive, and 1 for failure. No status commits or merges a patch automatically.
The adapter is a reusable submission boundary, independent of an agent provider.
Larger target families need their own reviewed semantic cases and build policies.
