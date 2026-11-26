#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Paired T1 protocol tests; synthetic Google Benchmark stand-ins test decisions, not ISPC."""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

import evaluate
import paired

CASES = ['work_a/min_time:0.100', 'work_b/min_time:0.100', 'control_x/min_time:0.100']
FAKE = '''#!{python} -I
import json, random, sys
from pathlib import Path
config = json.loads(Path({config!r}).read_text())
counter = Path({config!r} + '.count')
calls = int(counter.read_text()) if counter.exists() else 0
counter.write_text(str(calls + 1))
rng = random.Random(config['seed'] * 100003 + calls)
out = [a.split('=', 1)[1] for a in sys.argv if a.startswith('--benchmark_out=')][0]
rows = []
for name in {cases!r}:
    if name in config.get('omit', []):
        continue
    base = 1000.0 * config.get('scale', {{}}).get(name.split('/')[0], 1.0)
    rows.append(dict(name=name, run_name=name, run_type='iteration', time_unit='ns',
                     cpu_time=base * (1 + rng.gauss(0, config.get('noise', 0.002)))))
Path(out).write_text(json.dumps(dict(context={{}}, benchmarks=rows)))
'''


class PairedTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.check = self.root / 'check'  # a correctness check only has to exit 0
        self.check.write_text('#!/bin/sh\nexit 0\n')
        self.check.chmod(0o755)

    def tearDown(self):
        self.temporary.cleanup()

    def fake(self, name, config):
        config = dict(dict(seed=len(name)), **config)
        path = self.root / (name + '.json')
        path.write_text(json.dumps(config))
        binary = self.root / name
        binary.write_text(FAKE.format(python=sys.executable, config=str(path), cases=CASES))
        binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
        return binary

    def job(self, baseline, candidate, layout=None, **extra):
        job = dict(hypothesis='synthetic', baseline_revision='a' * 40, candidate_revision='b' * 40,
                   filter='.*', pairs=20, min_gain=0.03, max_regression=0.03,
                   cpu=min(os.sched_getaffinity(0)), timeout=30, metric='cpu_time', expected_cases=CASES,
                   control_cases=['control_x/min_time:0.100'], checks=[[str(self.check)]],
                   baseline=str(baseline), candidate=str(candidate))
        if layout is not None:
            job['layout_baseline'] = str(layout)
        job.update(extra)
        return job

    def run_job(self, name, job, thresholds=None):
        out = self.root / 'runs' / name
        out.mkdir(parents=True)
        return paired.experiment(job, out, thresholds), out

    def test_identity_is_no_material_improvement_and_gate_passes(self):
        base = self.fake('base', {})
        report, out = self.run_job('identity', self.job(base, self.fake('same', {}), self.fake('layout', {})))
        self.assertEqual(report['status'], 'no_material_improvement')
        self.assertTrue(report['aa_gate']['passed'])
        self.assertEqual({row['status'] for row in report['cases']}, {'inconclusive'})
        self.assertEqual(len(list(out.glob('ab-*-first.json'))), 20)
        self.assertEqual(report['cases'][0]['pairs'], 20)

    def test_clear_gain_outside_bound_needs_confirmation_and_controls_stay(self):
        base = self.fake('base', {})
        faster = self.fake('faster', dict(scale=dict(work_a=0.8, work_b=0.9)))
        report, _ = self.run_job('gain', self.job(base, faster, self.fake('layout', {})))
        status = {row['name'].split('/')[0]: row['status'] for row in report['cases']}
        self.assertEqual(report['status'], 'candidate_for_confirmation')
        self.assertEqual(status, dict(work_a='improvement', work_b='improvement', control_x='inconclusive'))
        row = next(r for r in report['cases'] if r['name'].startswith('work_a'))
        self.assertAlmostEqual(row['trimmed_mean_ratio'], 0.8, delta=0.01)
        self.assertLess(row['ci95'][1], 0.97)

    def test_gain_inside_bound_is_not_claimed(self):
        base = self.fake('base', {})
        report, _ = self.run_job('small', self.job(base, self.fake('small', dict(scale=dict(work_a=0.985))),
                                                   self.fake('layout', {})))
        self.assertEqual(report['status'], 'no_material_improvement')

    def test_one_slower_case_is_a_regression_despite_other_gains(self):
        base = self.fake('base', {})
        mixed = self.fake('mixed', dict(scale=dict(work_a=0.7, work_b=1.1)))
        report, _ = self.run_job('regress', self.job(base, mixed, self.fake('layout', {})))
        self.assertEqual(report['status'], 'regression')

    def test_moved_control_blocks_promotion(self):
        base = self.fake('base', {})
        moved = self.fake('moved', dict(scale=dict(work_a=0.7, control_x=0.9)))
        report, _ = self.run_job('control', self.job(base, moved, self.fake('layout', {})))
        self.assertEqual(report['status'], 'control_moved')

    def test_noisy_identity_fails_the_gate_before_any_ab_timing(self):
        noisy = self.fake('noisy', dict(noise=0.15))
        report, out = self.run_job('gate', self.job(noisy, self.fake('cand', dict(scale=dict(work_a=0.5))),
                                                    self.fake('layout', {})))
        self.assertEqual(report['status'], 'aa_gate_failed')
        self.assertFalse(report['aa_gate']['passed'])
        self.assertNotIn('cases', report)
        self.assertEqual(list(out.glob('ab-*')), [])

    def test_layout_shift_raises_threshold_above_bound(self):
        base = self.fake('base', {})
        layout = self.fake('layout', dict(scale=dict(work_a=1.06)))  # layout alone moves work_a by 6%
        cand = self.fake('cand', dict(scale=dict(work_a=0.955)))     # 4.5% gain: beyond 0.97, inside layout
        report, _ = self.run_job('layout', self.job(base, cand, layout))
        row = next(r for r in report['cases'] if r['name'].startswith('work_a'))
        self.assertGreater(row['threshold']['gain'], 0.055)
        self.assertEqual(row['status'], 'inconclusive')
        self.assertEqual(report['thresholds']['work_b/min_time:0.100']['gain'], 0.03)

    def test_confirmation_uses_frozen_thresholds_without_gate(self):
        base = self.fake('base', {})
        cand = self.fake('cand', dict(scale=dict(work_a=0.8)))
        frozen = {case: dict(gain=0.03, regression=0.03) for case in CASES}
        report, out = self.run_job('confirm', self.job(base, cand), frozen)
        self.assertEqual(report['phase'], 'confirmation')
        self.assertEqual(report['status'], 'candidate_for_confirmation')
        self.assertEqual(list(out.glob('aa-*')), [])
        with self.assertRaisesRegex(ValueError, 'cover exactly'):
            self.run_job('confirm-bad', self.job(base, cand), {CASES[0]: dict(gain=0.03, regression=0.03)})

    def test_missing_case_or_short_protocol_is_rejected(self):
        base = self.fake('base', {})
        broken = self.fake('broken', dict(omit=[CASES[1]]))
        with self.assertRaisesRegex(ValueError, 'frozen inventory'):
            self.run_job('missing', self.job(base, broken, self.fake('layout', {})))
        with self.assertRaisesRegex(ValueError, 'pairs'):
            paired.validate(self.job(base, base, base, pairs=5), None)
        with self.assertRaisesRegex(ValueError, 'layout_baseline'):
            paired.validate(self.job(base, base), None)


class EvaluatorProtocolTests(unittest.TestCase):
    def test_lit_failures_require_a_completed_summary(self):
        with tempfile.TemporaryDirectory() as root:
            log = Path(root) / 'lit.log'
            # Shape of the bundled utils/lit check-all output (bench run 45878927542, baseline-lit.log).
            body = ('XFAIL: ispc :: a.ispc (1 of 4)\nFAIL: ispc :: 2334_unroll.ispc (2 of 4)\n'
                    'PASS: ispc :: b.ispc (3 of 4)\nTIMEOUT: ispc :: slow.ispc (4 of 4)\n'
                    '********************\nFailed Tests (1):\n  ispc :: 2334_unroll.ispc\n\n\n')
            log.write_text(body + 'Testing Time: 69.90s\n  Passed           :   1\n  Expectedly Failed:   1\n'
                           '  Timed Out        :   1\n  Failed           :   1\n'
                           'ninja: build stopped: subcommand failed.\n')
            self.assertEqual(evaluate.lit_failures(log), ['2334_unroll.ispc', 'slow.ispc'])
            log.write_text(body + 'Testing Time: 1.00s\n  Failed           :   3\n')
            with self.assertRaisesRegex(ValueError, 'counts 3 failing tests but 2'):
                evaluate.lit_failures(log)
            log.write_text(body)
            with self.assertRaisesRegex(ValueError, 'did not complete'):
                evaluate.lit_failures(log)

    def test_paired_policy_fields_are_validated(self):
        policy = dict(repo='/r', baseline_revision='a' * 40, llvm='/l', cache='/c', type='int64',
                      cpu=min(os.sched_getaffinity(0)), runs=3, repetitions=2, min_gain=0.03, max_regression=0.03,
                      jobs=1, timeout=10, packet='/p/packet.json', packet_sha256='0' * 64,
                      protocol='paired', pairs=80, layout_pad=48)
        evaluate.validate_policy(policy)
        for change, message in ((dict(layout_pad=64), 'multiple of 64'), (dict(pairs=10), 'pairs'),
                                (dict(protocol='other'), 'protocol')):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, message):
                evaluate.validate_policy(dict(policy, **change))
        without_packet = {k: v for k, v in policy.items() if k not in ('packet', 'packet_sha256')}
        with self.assertRaisesRegex(ValueError, 'requires a fixture packet'):
            evaluate.validate_policy(without_packet)


if __name__ == '__main__':
    unittest.main()
