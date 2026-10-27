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

Start with the shuffle family on `avx2-i32x8`. Build baseline and candidate with
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

The next implementation steps are automated build capture and an agent adapter that
submits candidates to this fixed evaluator. Larger target families should reuse
the runner while supplying their own reviewed semantic cases.
