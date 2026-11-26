#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Adapt an ispc-lab-bench task folder to the builtins lab framework.

bench_adapter.py TASK_DIR OUT_DIR

  T0   -> screen.py (standalone kernel screen, plus an A/A control run)
  T1   -> evaluate.py with a short measurement policy
  full -> evaluate.py with the acceptance policy

Always writes OUT_DIR/result.json following the ispc-lab-bench README contract.
Raw framework output is kept under OUT_DIR/raw/.
"""
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import traceback

LAB = Path(__file__).resolve().parent
REPO = LAB.parent.parent
LLVM = Path(os.environ.get('BENCH_LLVM', '/usr/lib/llvm-20/bin'))
CPU = int(os.environ.get('BENCH_CPU', '2'))

T0_FIXTURES = {
    # builtin -> fixture knowledge. The only reviewed T0 fixture today.
    'reduce_equal': dict(types={'int64'}, targets={'avx2-i32x8'},
                         default_baseline={'.S': LAB / 'screen_examples/reduce_equal_scalar.S',
                                           '.s': LAB / 'screen_examples/reduce_equal_scalar.S',
                                           '.cpp': LAB / 'screen_examples/reduce_equal_scalar.S',
                                           '.so': LAB / 'screen_examples/reduce_equal_scalar.S',
                                           '.inc': LAB / 'screen_examples/reduce_equal_body.inc'}),
}
EVAL_TYPES = {'int16', 'int64', 'double'}
TIER_POLICY = {
    'T1': dict(runs=3, repetitions=2, min_gain=0.03, max_regression=0.03),
    'full': dict(runs=5, repetitions=5, min_gain=0.02, max_regression=0.02),
}


def cpu_description():
    model = 'unknown'
    for line in Path('/proc/cpuinfo').read_text().splitlines():
        if line.startswith('model name'):
            model = line.split(':', 1)[1].strip()
            break
    return f'{model} (pinned cpu {CPU})'


def llvm_version():
    try:
        out = subprocess.run([str(LLVM / 'clang++'), '--version'], capture_output=True, text=True, check=True)
        return out.stdout.splitlines()[0].strip()
    except (OSError, subprocess.CalledProcessError) as error:
        return f'unknown ({error})'


def load_task(task_dir):
    task = json.loads((task_dir / 'task.json').read_text())
    for key in ('builtin', 'tier'):
        if not isinstance(task.get(key), str) or not task[key]:
            raise ValueError(f'task.json: {key} is required')
    if task['tier'] not in ('T0', 'T1', 'full'):
        raise ValueError('task.json: tier must be T0, T1 or full')
    for key, default in (('targets', ['avx2-i32x8']), ('types', ['int64']), ('masks', ['all'])):
        value = task.setdefault(key, default)
        if not isinstance(value, list) or not value or not all(isinstance(v, str) and v for v in value):
            raise ValueError(f'task.json: {key} must be a nonempty list of strings')
    return task


def find_one(task_dir, stem, suffixes):
    found = [p for p in sorted(task_dir.iterdir()) if p.stem == stem and p.suffix in suffixes]
    if len(found) > 1:
        raise ValueError(f'ambiguous {stem}.*: ' + ', '.join(p.name for p in found))
    return found[0] if found else None


def run_logged(argv, log):
    print('+', ' '.join(map(str, argv)), flush=True)
    with log.open('w') as stream:
        result = subprocess.run([str(a) for a in argv], stdout=stream, stderr=subprocess.STDOUT, cwd=LAB)
    print(log.read_text()[-4000:], flush=True)
    return result.returncode


# ---------------------------------------------------------------- T0 ------
def screen_once(baseline, candidate, out, fixture, noise_threshold=None):
    argv = [sys.executable, LAB / 'screen.py', '--baseline', baseline, '--candidate', candidate,
            '--cxx', LLVM / 'clang++', '--cpu', CPU, '--output', out, '--fixture', fixture]
    if noise_threshold is not None:
        argv += ['--noise-threshold', f'{noise_threshold:.6f}']
    if candidate.suffix == '.inc':
        argv.append('--body-mode')
    out.parent.mkdir(parents=True, exist_ok=True)
    code = run_logged(argv, out.parent / (out.name + '.log'))
    report_path = out / 'report.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else dict(status='failed')
    if code and report.get('status') != 'failed':
        report['status'] = 'failed'
    return report


def aa_noise_threshold(aa, floor):
    """Largest distance from 1.0 that identical code reached in its A/A CI, never below the floor."""
    excursion = 0.0
    for case in aa.get('result', {}).get('cases', []):
        low, high = case.get('ci95') or case['observed_ratio_range']
        excursion = max(excursion, 1 - low, high - 1)
    return min(0.49, max(floor, excursion))  # screen.py accepts thresholds below 0.5


def t0_verdict(status):
    return {'promising_for_context_check': 'faster', 'slower_in_this_screen': 'slower'}.get(status, 'inconclusive')


def t0(task, task_dir, out_dir, result):
    spec = T0_FIXTURES.get(task['builtin'])
    if spec is None:
        raise ValueError(f"no reviewed T0 fixture for builtin '{task['builtin']}' (available: {', '.join(T0_FIXTURES)})")
    if set(task['types']) - spec['types'] or set(task['targets']) - spec['targets']:
        raise ValueError(f"T0 {task['builtin']} fixture covers only types {sorted(spec['types'])} "
                         f"and targets {sorted(spec['targets'])}")
    candidate = find_one(task_dir, 'candidate', ('.S', '.s', '.cpp', '.so', '.inc'))
    if candidate is None:
        raise ValueError('T0 needs candidate.{S,s,cpp,so,inc} in the task folder')
    baseline = find_one(task_dir, 'baseline', ('.S', '.s', '.cpp', '.so', '.inc'))
    if baseline is None:
        baseline = spec['default_baseline'][candidate.suffix]
        result['notes'].append(f'baseline: lab default {baseline.relative_to(REPO)}')
    else:
        result['notes'].append(f'baseline: task {baseline.name}')
    if (baseline.suffix == '.inc') != (candidate.suffix == '.inc'):
        raise ValueError('baseline and candidate must both be .inc bodies or both be kernels')

    correct, aa_ok = True, True
    result.update(aa_cases=[], t0_seconds=[])
    for mask in task['masks']:
        fixture = 'all-on' if mask == 'all' else 'mixed-mask'
        if fixture == 'mixed-mask' and candidate.suffix != '.inc':
            raise ValueError(f"mask '{mask}' uses the mixed-mask fixture, which needs .inc bodies")
        tag = 'all-on' if mask == 'all' else f'mixed-{mask}'
        if fixture == 'mixed-mask':
            result['notes'].append(f"mask '{mask}': T0 mixed-mask fixture covers all proper partial masks 1..254, "
                                   'not only this pattern')
        # A/A first: its CI tells how far identical code drifts in this run; the main verdict must clear it.
        aa = screen_once(baseline, baseline, out_dir / 'raw' / f'aa-{tag}', fixture)
        aa_ok_run = aa.get('status') == 'screened_not_accepted'
        floor = aa.get('estimator', {}).get('noise_floor', 0.005)
        threshold = aa_noise_threshold(aa, floor) if aa_ok_run else None
        main = screen_once(baseline, candidate, out_dir / 'raw' / f't0-{tag}', fixture, threshold)
        result['t0_seconds'].append(dict(tag=tag, aa=aa.get('elapsed_seconds'), main=main.get('elapsed_seconds')))
        ok = main.get('status') == 'screened_not_accepted' and str(main['result'].get('oracle', '')).startswith('passed')
        correct &= ok
        if not ok:
            result['notes'].append(f"{tag}: screen failed: {main.get('error', 'see raw log')}")
            continue
        result['t0_estimator'] = dict(pairs=main.get('pairs'), reps=main.get('reps'), batch_ms=main.get('batch_ms'),
                                      **main.get('estimator', {}))
        for case in main['result']['cases']:
            pairs = case['pairs']
            base = statistics.median(p['baseline_ns_per_group'] for p in pairs)
            cand = statistics.median(p['candidate_ns_per_group'] for p in pairs)
            point = case.get('trimmed_mean_ratio', case['median_ratio'])
            result['measurements'].append(dict(
                case=f"{task['builtin']}/{tag}/{case['name']}", baseline_ns=base, candidate_ns=cand,
                delta_pct=(point - 1) * 100, verdict=t0_verdict(case['screen_status']),
                tsc_ratio_median=case['median_ratio'], tsc_ratio_range=case['observed_ratio_range'],
                trimmed_mean_ratio=case.get('trimmed_mean_ratio'), ci95=case.get('ci95'),
                noise_threshold=case.get('noise_threshold'), pairs=len(pairs)))
        if not aa_ok_run:
            aa_ok = False
            result['notes'].append(f'{tag}: A/A control run failed')
            continue
        # A/A passes when the verdict rule (at the noise floor) does not call identical code faster/slower.
        for case in aa['result']['cases']:
            low, high = case['observed_ratio_range']
            verdict = t0_verdict(case['screen_status'])
            aa_ok &= verdict == 'inconclusive'
            ci = case.get('ci95')
            result['aa_cases'].append(dict(case=f"{task['builtin']}/{tag}/{case['name']}",
                                           trimmed_mean_ratio=case.get('trimmed_mean_ratio'), ci95=ci,
                                           median_ratio=case['median_ratio'], verdict=verdict))
            ci_text = f", CI95 {ci[0]:.4f}..{ci[1]:.4f}" if ci else ''
            result['notes'].append(f"{tag}: A/A {case['name']} median {case['median_ratio']:.3f}{ci_text}, "
                                   f"pair range {low:.3f}..{high:.3f} -> {verdict}")
        result['notes'].append(f'{tag}: noise threshold {threshold * 100:.2f}% (A/A CI excursion, floor {floor * 100:.1f}%)')
    result['correct'] = correct
    result['aa_control'] = 'pass' if aa_ok and correct else 'fail'
    result['notes'].append('T0 is a standalone kernel screen; it never accepts a builtin patch.')


# ---------------------------------------------------------- T1 / full -----
def evaluate_tier(task, task_dir, out_dir, result):
    patch = find_one(task_dir, 'candidate', ('.patch', '.diff'))
    if patch is None:
        raise ValueError(f"{task['tier']} needs candidate.patch (against ispc) in the task folder")
    types = set(task['types'])
    if len(types) != 1 or not types <= EVAL_TYPES:
        raise ValueError(f'evaluate.py measures exactly one type per run, one of {sorted(EVAL_TYPES)}')
    if task['targets'] != ['avx2-i32x8']:
        raise ValueError('evaluate.py measures target avx2-i32x8 only (avx2vnni-i32x8 is compile-checked)')
    if task['masks'] != ['all']:
        result['notes'].append('evaluate.py has its own fixed mask/context panel; task masks are not applied')
    revision = os.environ.get('BENCH_BASELINE_REV') or subprocess.check_output(
        ['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip()
    policy = dict(repo=str(REPO), baseline_revision=revision, llvm=str(LLVM),
                  cache=os.environ.get('BENCH_CACHE', str(Path.home() / '.cache/ispc-lab-bench/evaluator')),
                  type=next(iter(types)), cpu=CPU, jobs=int(os.environ.get('BENCH_JOBS', '12')),
                  timeout=int(os.environ.get('BENCH_TIMEOUT', '3600')), **TIER_POLICY[task['tier']])
    raw = out_dir / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    request = dict(hypothesis=task.get('notes') or f"{task['builtin']} candidate from {task_dir.name}",
                   patch=str(patch.resolve()))
    (raw / 'policy.json').write_text(json.dumps(policy, indent=2) + '\n')
    (raw / 'request.json').write_text(json.dumps(request, indent=2) + '\n')
    code = run_logged([sys.executable, LAB / 'evaluate.py', raw / 'request.json', '--policy', raw / 'policy.json',
                       '--worker', 'bench', '--output', raw / 'evaluation'], raw / 'evaluate.log')
    evaluation_path = raw / 'evaluation' / 'evaluation.json'
    report = json.loads(evaluation_path.read_text()) if evaluation_path.exists() else dict(status='failed')
    status = report.get('status', 'failed')
    result['evaluator_status'] = status
    result['correct'] = status != 'failed' and code in (0, 2)
    if report.get('error'):
        result['notes'].append('evaluator error: ' + report['error'])
    if status == 'no_material_improvement' and 'reason' in report:
        result['notes'].append(report['reason'])
    phase = report.get('confirmation') or report.get('discovery')
    verdicts = {'improvement': 'faster', 'regression': 'slower'}
    if phase:
        measured = json.loads(Path(phase['report']).read_text())
        for row in measured.get('cases', []):
            base = statistics.median(row['baseline_seconds']) * 1e9
            cand = statistics.median(row['candidate_seconds']) * 1e9
            result['measurements'].append(dict(
                case=row['name'], baseline_ns=base, candidate_ns=cand, delta_pct=(cand / base - 1) * 100,
                verdict=verdicts.get(row['status'], 'inconclusive'), framework_status=row['status'],
                ratio_range=row['observed_ratio_range']))
        result['aa_control'] = aa_control_eval(report, policy, raw)
    else:
        result['aa_control'] = 'fail'
        result['notes'].append('no timing phase ran; A/A control not executed')
    result['notes'].append(f"evaluate.py status: {status} (tier {task['tier']}: runs={policy['runs']}, "
                           f"repetitions={policy['repetitions']})")


def aa_control_eval(report, policy, raw):
    """Baseline-vs-baseline run on the same contexts binary and discovery cases."""
    sys.path.insert(0, str(LAB))
    import run as runner
    discovery_job = raw / 'evaluation' / 'discovery-job.json'
    job = json.loads(discovery_job.read_text())
    job.update(candidate=job['baseline'], candidate_revision=job['baseline_revision'] + '+aa-control',
               hypothesis='A/A control: baseline against itself')
    out = raw / 'aa-control'
    out.mkdir()
    try:
        aa = runner.experiment(job, out)
    except Exception as error:  # keep the main result even if the control fails
        print(f'A/A control failed: {error}', flush=True)
        return 'fail'
    # Identical binaries must not show a "significant" difference in either direction.
    return 'fail' if any(r['status'] in ('improvement', 'regression') for r in aa['cases']) else 'pass'


def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 64
    task_dir, out_dir = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    result = dict(task=task_dir.name, tier=None, cpu=cpu_description(), llvm=llvm_version(), correct=False,
                  measurements=[], aa_control='fail', notes=[],
                  framework_revision=subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'],
                                                    capture_output=True, text=True).stdout.strip(),
                  host=platform.node())
    code = 1
    try:
        task = load_task(task_dir)
        result.update(tier=task['tier'], builtin=task['builtin'], targets=task['targets'],
                      types=task['types'], masks=task['masks'])
        (t0 if task['tier'] == 'T0' else evaluate_tier)(task, task_dir, out_dir, result)
        code = 0 if result['correct'] else 1
    except Exception as error:
        traceback.print_exc()
        result['correct'] = False
        result['notes'].append(f'bench_entry failed: {error}')
    finally:
        result['notes'] = '\n'.join(result['notes'])
        (out_dir / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: result[k] for k in ('task', 'tier', 'correct', 'aa_control')}), flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
