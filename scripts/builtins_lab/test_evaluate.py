#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Policy boundaries, restoration, and build/measurement coordination tests."""
import json
import multiprocessing
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import sys
import time
import unittest
from unittest import mock

import evaluate
import run


def lock_holder(exclusive, started, acquired, release):
    started.set()
    with run.host_access(exclusive):
        acquired.put(True)
        release.wait(10)


class PolicyTests(unittest.TestCase):
    def policy(self):
        return dict(repo='/repo', llvm='/llvm/bin', cache='/cache', baseline_revision='a' * 40,
                    type='int64', cpu=min(os.sched_getaffinity(0)), runs=3, repetitions=2,
                    jobs=2, timeout=300, min_gain=.03, max_regression=.02)

    def test_agent_cannot_override_evaluator_fields(self):
        for field in ('checks', 'filter', 'min_gain', 'llvm', 'expected_cases'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                evaluate.validate_request(dict(hypothesis='test', patch='/patch', **{field: 'override'}))

    def test_moving_baseline_and_invalid_budgets_rejected(self):
        for field, value in (('baseline_revision', 'main'), ('runs', 1),
                             ('min_gain', float('nan')), ('jobs', True), ('type', 'int8')):
            policy = self.policy()
            policy[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                evaluate.validate_policy(policy)

    def test_full_inventory_includes_discovery_and_unused_cases(self):
        discovery, confirmation = map(set, (evaluate.expected_cases(), evaluate.expected_cases(True)))
        self.assertEqual(len(discovery), 12)
        self.assertEqual(len(confirmation), 48)
        self.assertTrue(discovery < confirmation)
        self.assertIn('masked/throughput/p4/min_time:0.100', confirmation - discovery)


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.target = self.root / evaluate.ALLOWED[0]
        self.target.parent.mkdir()
        self.target.write_text('original\n')
        protected = self.root / 'scripts/check.py'
        protected.parent.mkdir()
        protected.write_text('protected\n')
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)

    def patch(self):
        path = self.root / 'submission.patch'
        path.write_bytes(subprocess.check_output(['git', '-C', str(self.root), 'diff', '--binary']))
        return path

    def test_content_change_allowed(self):
        self.target.write_text('candidate\n')
        self.assertEqual(evaluate.changed_paths(self.root, self.patch()), list(evaluate.ALLOWED))

    def test_frozen_harness_edit_rejected(self):
        (self.root / 'scripts/check.py').write_text('weakened\n')
        with self.assertRaisesRegex(ValueError, 'protected'):
            evaluate.changed_paths(self.root, self.patch())

    def test_mode_change_rejected_before_application(self):
        self.target.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'mode changes'):
            evaluate.changed_paths(self.root, self.patch())

    def test_binary_change_rejected(self):
        self.target.write_bytes(b'\0binary')
        with self.assertRaises(ValueError):
            evaluate.changed_paths(self.root, self.patch())


class RestorationTests(unittest.TestCase):
    def test_discovery_gain_is_not_promoted_when_confirmation_regresses(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            source = out / 'source'
            target = source / evaluate.ALLOWED[0]
            target.parent.mkdir(parents=True)
            target.write_bytes(b'baseline\n')
            instance = evaluate.Evaluation.__new__(evaluate.Evaluation)
            instance.out, instance.source, instance.home = out, source, out / 'worker'
            instance.build = out / 'build'
            instance.build.mkdir()
            (instance.build / 'CMakeCache.txt').write_text('fixed config')
            instance.originals = {evaluate.ALLOWED[0]: b'baseline\n'}
            instance.report = dict(status='failed')
            for label, text in (('baseline', 'old assembly'), ('candidate', 'new assembly')):
                context = out / f'{label}-contexts'
                context.mkdir()
                (context / 'contexts.s').write_text(text)
            with mock.patch.object(instance, 'prepare'), mock.patch.object(instance, 'fixtures'), \
                 mock.patch.object(instance, 'build_candidate'), \
                 mock.patch.object(instance, 'measure', side_effect=['candidate_for_confirmation', 'regression']) as measure:
                report = instance.evaluate()
            self.assertEqual(report['status'], 'regression')
            self.assertEqual(measure.call_args_list, [mock.call(), mock.call(confirmation=True)])

    def test_identical_assembly_is_not_promoted_by_timing_noise(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            source = out / 'source'
            target = source / evaluate.ALLOWED[0]
            target.parent.mkdir(parents=True)
            target.write_bytes(b'baseline\n')
            instance = evaluate.Evaluation.__new__(evaluate.Evaluation)
            instance.out, instance.source, instance.home = out, source, out / 'worker'
            instance.build = out / 'build'
            instance.build.mkdir()
            (instance.build / 'CMakeCache.txt').write_text('fixed config')
            instance.originals = {evaluate.ALLOWED[0]: b'baseline\n'}
            instance.report = dict(status='failed')
            for label in ('baseline', 'candidate'):
                context = out / f'{label}-contexts'
                context.mkdir()
                (context / 'contexts.s').write_text('same final code')
            with mock.patch.object(instance, 'prepare'), mock.patch.object(instance, 'fixtures'), \
                 mock.patch.object(instance, 'build_candidate'), mock.patch.object(instance, 'measure') as measure:
                report = instance.evaluate()
            self.assertEqual(report['status'], 'no_material_improvement')
            measure.assert_not_called()

    def test_constructor_rejection_has_audit_record(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'rejected'
            with self.assertRaises(ValueError):
                evaluate.Evaluation({}, {'hypothesis': 'invalid policy', 'patch': '/missing'}, 'worker', out)
            report = json.loads((out / 'evaluation.json').read_text())
            self.assertEqual(report['status'], 'failed')
            self.assertIn('error', report)
            self.assertEqual(json.loads((out / 'request.json').read_text())['hypothesis'], 'invalid policy')

    def test_failed_build_restores_original_and_retains_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            source = out / 'source'
            target = source / evaluate.ALLOWED[0]
            target.parent.mkdir(parents=True)
            target.write_bytes(b'baseline\n')
            instance = evaluate.Evaluation.__new__(evaluate.Evaluation)
            instance.out, instance.source, instance.home = out, source, out / 'worker'
            instance.originals = {evaluate.ALLOWED[0]: b'baseline\n'}
            instance.report = dict(status='failed')
            instance.patch = out / 'candidate.patch'
            instance.patch.write_text('retained evidence')
            def fail():
                target.write_bytes(b'broken candidate\n')
                raise RuntimeError('compiler failed')
            with mock.patch.object(instance, 'prepare'), mock.patch.object(instance, 'fixtures'), \
                 mock.patch.object(instance, 'build_candidate', side_effect=fail), \
                 mock.patch.object(instance, 'measure') as measure:
                with self.assertRaisesRegex(RuntimeError, 'compiler failed'):
                    instance.evaluate()
            self.assertEqual(target.read_bytes(), b'baseline\n')
            self.assertEqual(instance.patch.read_text(), 'retained evidence')
            self.assertEqual(json.loads((out / 'evaluation.json').read_text())['status'], 'failed')
            measure.assert_not_called()


class CoordinationTests(unittest.TestCase):
    def test_outer_timeout_stops_nested_executor_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / 'nested.pid'
            child = ('import os,time; from pathlib import Path; '
                     f'Path({str(marker)!r}).write_text(str(os.getpid())); time.sleep(60)')
            helper = root / 'helper.py'
            helper.write_text('import sys; from pathlib import Path\n' +
                f'sys.path.insert(0, {str(Path(run.__file__).parent)!r})\n' +
                'import run\n' +
                f'run.execute([{sys.executable!r}, "-c", {child!r}], Path({str(root / "inner.log")!r}), 60)\n')
            with self.assertRaises(subprocess.TimeoutExpired):
                run.execute([sys.executable, str(helper)], root / 'outer.log', 1)
            child_pid = int(marker.read_text())
            for attempt in range(200):
                try:
                    state = Path(f'/proc/{child_pid}/stat').read_text().split(') ', 1)[1][0]
                except FileNotFoundError:
                    break
                if state in ('Z', 'X'):
                    break
                time.sleep(.01)
            else:
                self.fail('outer executor left a nested process running')

    def test_measurement_waits_until_all_builders_release_host(self):
        context = multiprocessing.get_context('fork')
        release_builders, release_measurement = context.Event(), context.Event()
        started = [context.Event() for _ in range(3)]
        acquired = [context.Queue() for _ in range(3)]
        processes = [context.Process(target=lock_holder, args=(False, started[i], acquired[i], release_builders))
                     for i in range(2)]
        processes.append(context.Process(target=lock_holder,
            args=(True, started[2], acquired[2], release_measurement)))
        try:
            for process in processes[:2]:
                process.start()
            for i in range(2):
                self.assertTrue(acquired[i].get(timeout=5))
            processes[2].start()
            self.assertTrue(started[2].wait(5))
            with self.assertRaises(queue.Empty):
                acquired[2].get(timeout=.2)
            release_builders.set()
            self.assertTrue(acquired[2].get(timeout=5))
        finally:
            release_builders.set()
            release_measurement.set()
            for process in processes:
                if process.pid:
                    process.join(5)
                    if process.is_alive():
                        process.kill()
                        process.join()


if __name__ == '__main__':
    unittest.main()
