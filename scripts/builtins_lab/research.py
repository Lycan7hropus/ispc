#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Generate the analysis agent task and validate its evidence handoff (Linux)."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def revision(repo, value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError('baseline must be a full commit SHA')
    subprocess.run(['git', '-C', str(repo), 'cat-file', '-e', value + '^{commit}'], check=True)
    return value


def validate(report, repo):
    baseline = revision(repo, report['baseline_revision'])
    candidates = report['candidates']
    if len(candidates) < 3 or len({c['family'] for c in candidates}) < 3:
        raise ValueError('inspect at least three distinct builtin families before selecting')
    identifiers = set()
    for candidate in candidates:
        identifier = candidate['id']
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            raise ValueError('candidate ids must be nonempty and unique')
        identifiers.add(identifier)
        for key in ('family', 'mechanism', 'expected_codegen_change', 'caller_relevance',
                    'risks', 'disproof', 'next_probe', 'ranking_reason'):
            if not isinstance(candidate.get(key), str) or not candidate[key].strip():
                raise ValueError(f'{identifier}: missing {key}')
        if candidate['evidence_level'] not in ('source_only', 'codegen_verified', 'profiled'):
            raise ValueError('invalid evidence level')
        if candidate['relevance_level'] not in ('unmeasured', 'representative', 'profiled'):
            raise ValueError('invalid relevance level')
        if not candidate['locations']:
            raise ValueError('source references required')
        for location in candidate['locations']:
            path, line = location['path'], location['line']
            if Path(path).is_absolute() or '..' in Path(path).parts:
                raise ValueError('source references must be repository-relative')
            content = subprocess.check_output(['git', '-C', str(repo), 'show', baseline + ':' + path]).decode()
            if type(line) is not int or not 1 <= line <= len(content.splitlines()):
                raise ValueError('source reference line outside pinned baseline')
        if not isinstance(candidate['evidence'], list):
            raise ValueError('evidence must be a list')
        for evidence in candidate['evidence']:
            path = Path(evidence['path'])
            command = evidence['command']
            if not path.is_absolute() or not path.is_file():
                raise ValueError('evidence artifact must exist at an absolute path')
            if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
                raise ValueError('evidence must record command arguments')
            if hashlib.sha256(path.read_bytes()).hexdigest() != evidence['sha256']:
                raise ValueError('evidence hash mismatch')
            if not isinstance(evidence.get('observation'), str) or not evidence['observation'].strip():
                raise ValueError('evidence observation required')
        if candidate['evidence_level'] != 'source_only' and not candidate['evidence']:
            raise ValueError('codegen/profile claims require retained evidence')
        if candidate['evidence_level'] == 'profiled':
            profile_path = Path(candidate.get('profile_report', ''))
            if not profile_path.is_absolute() or not profile_path.is_file():
                raise ValueError('profiled claims require a retained profile report')
            profile = json.loads(profile_path.read_text())
            if (profile.get('status') not in ('collected_for_review', 'partial') or
                    profile.get('workload_kind') not in ('application', 'representative_kernel', 'microbenchmark')):
                raise ValueError('profile report must identify successful collection and workload kind')
            if str(profile_path) not in {entry['path'] for entry in candidate['evidence']}:
                raise ValueError('profile report must be included in hashed evidence')
    if not isinstance(report.get('selection_reason'), str) or not report['selection_reason'].strip():
        raise ValueError('selection or abstention reason required')
    selected = report.get('selected')
    if selected is None:
        return dict(status='needs_more_evidence', selected=None)
    if selected not in identifiers:
        raise ValueError('selected candidate not present')
    candidate = next(c for c in candidates if c['id'] == selected)
    if candidate['evidence_level'] == 'source_only' or candidate['relevance_level'] == 'unmeasured':
        raise ValueError('selection requires observed codegen and an identified representative caller')
    return dict(status='ready_for_patch_design', selected=selected,
                runtime_evidence=('profiled_requires_workload_review' if candidate['evidence_level'] == 'profiled'
                                  else 'not_established'),
                limitation='Structural evidence check; human/code review must assess claims. '
                           'This does not prove a runtime hotspot or authorize evaluator expansion.')


def prompt(repo, baseline, output):
    return f'''Analyze ISPC builtin optimization opportunities as the research agent.
Repository: {repo}
Pinned baseline: {baseline}
Output directory: {output}

Objective: a reusable builtin-optimization framework, not tuning one application.
An application profile is optional. Use a controlled family workload corpus and
scope conclusions to its cases and hardware; do not request an application as a gate.

Your task is analysis and evidence collection, not patch generation. Read applicable
repository instructions. Do not modify tracked files, tests, benchmarks, evaluators,
or measurement policies. Use an owned output directory for probes and results.

1. Survey at least three distinct builtin families. Do not assume shuffle is the
   best target because a shuffle evaluator exists. Inspect implementation, callers,
   tests, analogous target implementations, and relevant git history.
2. Rank opportunities by concrete mechanism, likely caller relevance, expected
   code-generation change, semantic risk and cost of validation. Source complexity
   alone is not evidence of runtime cost. Distinguish source suspicion, observed
   generated code, and measured runtime hotspots. Do not invent speedup estimates.
3. For the strongest two hypotheses, compile minimal representative baseline callers
   with the existing supported LLVM/ISPC toolchain. Record executable hashes, target,
   flags, commands, sources and final assembly. Check what survives inlining and LLVM
   optimization, including constant and masked controls. Read existing benchmark or
   application callers to explain relevance. Do not rebuild the compiler or run broad
   timing sweeps in this phase. If tools are unavailable, report the missing evidence.
   Evidence commands must be actual reproducible commands, not descriptive labels.
   For combined artifacts, retain the collector script and record its invocation.
4. Explain the dependency/memory/instruction cost mechanism and a result that would
   disprove each hypothesis. Downgrade ideas LLVM already optimizes. Consider all
   previously rejected shuffle attempts and their constant/masked regressions.
   Inventory runtime evidence separately: controlled workload, input distributions,
   sampled hotspots and counters, available profiler/PMU capabilities, and missing
   data. A representative benchmark is a valid primary workload for this library
   framework. Final assembly alone does not identify a runtime hotspot. Profile the
   optimized caller/workload rather than the compiler process or an isolated
   always-inlined symbol. Do not label a benchmark as an application profile.
5. Produce report.json using the contract below and a concise ranked explanation.
   Select at most one candidate, and only with codegen evidence and an identified
   representative caller. Abstain if none qualifies. Do not manufacture selection
   to satisfy the task. Identify the semantic oracle and representative measurement
   cases needed next; the evaluator supports shuffle and reviewed fixture packets.

Report contract:
{{"baseline_revision":"{baseline}", "selected":null,
 "selection_reason":"why this candidate, or why more evidence is needed",
 "candidates":[{{"id":"stable-id", "family":"family name",
   "locations":[{{"path":"builtins/file.ll", "line":1}}],
   "mechanism":"concrete avoidable cost",
   "expected_codegen_change":"specific instruction/dependency/memory change",
   "caller_relevance":"identified caller and workload assumptions",
   "relevance_level":"unmeasured|representative|profiled",
   "evidence_level":"source_only|codegen_verified|profiled",
   "profile_report":null,
   "evidence":[{{"path":"/absolute/artifact", "sha256":"hex digest",
     "command":["program","argument"], "observation":"what this artifact shows"}}],
   "risks":"semantic and constant/masked regression risks",
   "disproof":"specific observation that rejects the hypothesis",
   "next_probe":"next bounded experiment including required correctness coverage",
   "ranking_reason":"why ranked here relative to other candidates"}}]}}

Validation: python3 scripts/builtins_lab/research.py validate {output}/report.json --repo {repo}
The validator checks structure and artifact integrity, not the truth of conclusions.
For evidence_level=profiled, profile_report must name a retained collect_profile.py
report included in hashed evidence. Raw data, workload assumptions and limitations
still need technical review. Counter totals alone do not localize an instruction.
Stop after handing off analysis. Patch design follows a separate review of the
selected hypothesis and evaluator coverage; do not expand the existing evaluator
allowlist to make a proposal fit. Do not publish or commit.
'''


def design_prompt(repo, report, output):
    selected = next(c for c in report['candidates'] if c['id'] == report['selected'])
    return f'''Prepare the semantic oracle and bounded experiment design as the optimization agent.
Repository: {repo}
Baseline: {report['baseline_revision']}
Selected hypothesis: {selected['id']}
Output: {output}
Read the frozen research-report.json in this directory and applicable repository instructions.

The objective is a builtin framework. A target application is not required.
Freeze a controlled family corpus: masks/density, constant/dynamic arguments,
data distributions, locality, dependency chains versus independent operations,
inlining/hoisting and result consumption. Cover relevant dimensions rather than
an arbitrary full Cartesian product. Keep per-case effects and regression budgets;
do not invent application-frequency weights or claim universal CPU wins.

Use staged validation; do not run the complete evaluator for every idea.
T0: first save a tiny standalone kernel comparison and minimal independent oracle.
Use screen.py --body-mode for the supported eight-lane all-on i64 primitive;
keep loop/output framing identical and use an identity control first. Whole-kernel
scheduling studies must be labeled separately. Verify actual LLVM/ISPC lowering
before claiming a hand-written body corresponds to production code. Another family needs
its own reviewed small fixture. Proper partial eight-lane i64 masks can use
screen.py --fixture mixed-mask --body-mode: frame owns first-active selection,
broadcast, loop and output; bodies receive existing sign-mask vectors. This tests
fully accessible disjoint buffers, never empty/full masks or runtime LLVM poison.
Clearly label modeled LLVM graphs versus exact production body extraction.
Compile only the tiny kernels/driver, not ISPC.
Keep the default seconds-scale screen; do not expand to broad sweeps or profiling.
Label hand-written hypothesis assembly separately from exact compiler-emitted code.
An unclear result needs a specific new probe, not repeated runs until it passes.
T1: only a promising T0 earns a focused real ISPC caller/mask/constant check and
family oracle. Reuse built artifacts. Record candidate compiler preparation cost
separately; the standalone screen does not remove that integration cost.
Use focus.py with a coordinator-reviewed hash-pinned job for a short real-caller
panel, retaining both independent oracles, fixture/assembly provenance and exact
cases. Its three paired runs are descriptive T1 evidence, never acceptance or a
2% regression guarantee. Do not change cases or repeat a failed trial to obtain a
favorable result; retain failures and the preparation cost. It needs existing
binaries but does not require completing T2 first. When real candidate binaries
are missing, the coordinator can use prepare_t1.py with a reviewed packet and
existing validated compiler cache. It incrementally builds only the candidate,
runs packet oracles/contexts, restores source and emits a focus job without full
T2 gates or timings. Cache miss or failed provenance requires separate preparation
review; do not silently start a cold compiler build. Report preparation cost.
T2: only the selected integrated candidate reaches full fixed-evaluator validation,
all frozen cases, independent confirmation and any mechanism-specific profiling.
Do not repeat the family survey or demand a full profile for each T0 variant.
Keep stage, tested domain, time budget and next promotion criterion in design.json.
Leave inconclusive T2 results unchanged. Paired order/drift/correlation diagnostics
are descriptive, not acceptance or iid proof. The paired-median proposal is not an
installed rule; do not demand twelve calibration sessions as a prerequisite or fit
thresholds to a candidate. A new diagnostic needs a reviewed frozen bounded plan;
never replace pairs or rerun until favorable.

The coordinator reviewed this hypothesis for experiment design, not as a proven
runtime hotspot or speedup. Keep the evidence level and uncertainties explicit.
Do not change tracked files, the compiler, existing tests, evaluator policy or
allowlists. Use the existing baseline toolchain. Do not publish or commit.

1. For T0, resolve only the exact input domain and minimal semantic contract
   being screened from the relevant source/tests. Use an existing reviewed fixture
   when applicable. Defer the complete inactive-mask/overload/history audit to T1.
   At T1 resolve the full public contract from stdlib, builtins, tests and history. Cite paths and lines. Include inactive/all-off masks, output arguments,
   constant callers, and representation-specific edge cases. List any unresolved
   behavior. Restrict the initial experiment to the selected types and target.
2. At T0 use the existing tiny independent oracle, or implement a reviewed small
   oracle for the explicitly limited domain; do not build the exhaustive suite yet.
   At T1 implement the family oracle and real caller harness in this output
   directory. Exercise every mask for the selected gang width, equal and
   differing values, early/late and high/low-half differences, extremes, randomized
   patterns, and all relevant public overloads. The oracle must not copy the builtin
   algorithm or derive expectations from the compiler under test. Do not assert
   values for contractually unspecified results. Run it against the baseline and
   retain the exact source, commands, executable/toolchain hashes and results.
3. Freeze minimal T0 input cases before screening, without a broad corpus sweep.
   At T1 freeze representative acceptance case names before a production patch
   exists; do not select favorable cases based on T0 timings.
   Include working-set/distribution controls, runtime/fixed masks and constants.
   Explain which cases measure a useful operation and which are only regression
   controls. Use the existing benchmark's workload assumptions where justified.
   Do not infer speedup from instruction count. Do not run broad timing sweeps.
4. Design at most one concrete candidate algorithm. At T0 an owned standalone
   kernel implementation is allowed; do not patch or rebuild ISPC. Retain its
   source, screen report and scope limitations before moving to T1. Specify the smallest source
   change and inheritance scope, anticipated instruction/dependency change,
   semantic proof obligations, disproof criterion, and regression risks.
   Do not implement a production builtin patch yet. If the oracle, contract or relevance fails,
   abstain and state the next evidence needed rather than forcing a patch.
   Full acceptance needs reviewed runtime evidence for its intended workload;
   an isolated T0 screen is a cheap filter, not final integration evidence.
   List missing corpus evidence explicitly. Microbenchmarks are valid intended
   workloads here; scope conclusions to their cases and CPU. An application
   profile is optional and its absence must not block library-level investigation.
5. Produce design.json containing baseline_revision, selected, stage (T0/T1/T2),
   next_gate, elapsed_seconds, status (ready_for_focused_check for a promising T0,
   ready_for_evaluator_review only after T1, or needs_more_evidence), contract, scope,
   oracle_commands, oracle_results, artifacts (paths and SHA256), measurement_cases,
   candidate_design, risks, disproof and unresolved. Use actual replayable commands;
   retain collector scripts for combined artifacts. Add a short reviewer explanation.

Stop at this handoff. The coordinator reviews and freezes oracle and measurement
coverage before a separate patch experiment. Existing shuffle validation cannot
establish correctness or performance for another family. Request no user approval
for ordinary read-only analysis or owned baseline probes.
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    generate = commands.add_parser('prompt')
    generate.add_argument('--baseline', required=True)
    generate.add_argument('--output', required=True, type=Path)
    generate.add_argument('--repo', required=True, type=Path)
    check = commands.add_parser('validate')
    check.add_argument('report', type=Path)
    check.add_argument('--repo', required=True, type=Path)
    design = commands.add_parser('design')
    design.add_argument('report', type=Path)
    design.add_argument('--repo', required=True, type=Path)
    design.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.action == 'prompt':
        revision(args.repo, args.baseline)
        args.output.mkdir(parents=True, exist_ok=False)
        task = args.output / 'agent-task.txt'
        task.write_text(prompt(args.repo.resolve(), args.baseline, args.output.resolve()))
        print(task)
    elif args.action == 'validate':
        print(json.dumps(validate(json.loads(args.report.read_text()), args.repo), indent=2))
    else:
        report = json.loads(args.report.read_text())
        if validate(report, args.repo)['status'] != 'ready_for_patch_design':
            parser.error('research has no evidence-backed selection')
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / 'research-report.json').write_text(json.dumps(report, indent=2) + '\n')
        task = args.output / 'agent-task.txt'
        task.write_text(design_prompt(args.repo.resolve(), report, args.output.resolve()))
        print(task)


if __name__ == '__main__':
    main()
