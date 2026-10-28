# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
import contextlib
import copy
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

import focus
import run as runner


class FocusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.job = dict(schema=1, hypothesis='Pinned caller probe', cases=['alpha', 'beta'],
                        checks=[], provenance=[])
        for name in ('baseline', 'candidate', 'oracle', 'source'):
            path = self.root / name
            path.write_text(name)
            path.chmod(0o755 if name != 'source' else 0o644)
            item = dict(path=str(path), sha256=runner.sha256(path))
            if name in focus.SIDES:
                self.job[name] = item
            else:
                self.job['checks' if name == 'oracle' else 'provenance'].append(item)
        self.job_path = self.root / 'trusted.json'
        self.job_path.write_text(json.dumps(self.job))
        self.job_hash = runner.sha256(self.job_path)
        self.output = self.root / 'output'
        self.cpu = next(iter(os.sched_getaffinity(0)))

    def rows(self, **overrides):
        row = dict(name='alpha', cpu_time=4, time_unit='ns', run_type='iteration')
        row.update(overrides)
        return [row, dict(name='beta', cpu_time=5, time_unit='us')]

    def parse(self, rows, expected=('alpha', 'beta')):
        path = self.root / 'raw.json'
        path.write_text(json.dumps(dict(benchmarks=rows)))
        return focus.read_iterations(path, expected)

    def test_units_are_normalized_and_inventory_order_is_not_required(self):
        for unit, scale in runner.UNITS.items():
            with self.subTest(unit=unit):
                got = self.parse(list(reversed(self.rows(time_unit=unit))))
                self.assertAlmostEqual(got['alpha'], 4 * scale)
                self.assertAlmostEqual(got['beta'], 5e-6)

    def test_duplicate_unexpected_missing_and_extra_rows_are_rejected(self):
        bad = [self.rows(name='beta'), self.rows(name='unexpected'),
               self.rows()[:1], self.rows() + self.rows()[:1], None]
        for rows in bad:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.parse(rows)

    def test_invalid_times_units_and_noniterations_are_rejected(self):
        invalid = [dict(cpu_time=value) for value in
                   (0, -1, True, '4', None, float('nan'), float('inf'), -float('inf'))]
        invalid += [dict(time_unit='ticks'), dict(time_unit=None),
                    dict(error_occurred=True), dict(run_type='aggregate')]
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.parse(self.rows(**changes))

    def test_strict_job_schema_and_case_inventory(self):
        self.assertEqual(focus.validate(self.job)['cases'], ['alpha', 'beta'])
        variants = []
        for changes in (dict(schema=True), dict(schema=2), dict(extra=1),
                        dict(hypothesis=' '), dict(cases=[]), dict(cases=['x', 'x']),
                        dict(cases=['bad\nname']), dict(cases=[2]),
                        dict(checks=[]), dict(provenance=[])):
            variant = copy.deepcopy(self.job)
            variant.update(changes)
            variants.append(variant)
        missing = copy.deepcopy(self.job)
        del missing['schema']
        variants.append(missing)
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                focus.validate(variant)

    def test_identity_schema_paths_hashes_and_executable_requirement(self):
        for changes in (dict(path='relative'), dict(sha256='a'), dict(extra=True)):
            item = dict(self.job['baseline'])
            item.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                focus.identity(item)
        Path(self.job['baseline']['path']).chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'not executable'):
            focus.validate(self.job)

    def test_verify_detects_runtime_or_provenance_mutation(self):
        for item in (self.job['baseline'], self.job['provenance'][0]):
            with self.subTest(path=item['path']):
                focus.verify([item])
                Path(item['path']).write_text('mutated')
                with self.assertRaisesRegex(ValueError, 'identity changed'):
                    focus.verify([item])

    def test_expired_identity_deadline_prevents_read(self):
        stream = mock.MagicMock()
        with mock.patch.object(focus.time, 'monotonic', return_value=2), \
             mock.patch.object(Path, 'open', return_value=stream):
            with self.assertRaisesRegex(TimeoutError, 'stage deadline'):
                focus.verify([self.job['baseline']], deadline=1)
        stream.__enter__.return_value.read.assert_not_called()

    def test_identity_read_crossing_deadline_is_rejected(self):
        clock = [0]
        stream = mock.MagicMock()
        def read(size):
            clock[0] = 2
            return b'baseline'
        stream.__enter__.return_value.read.side_effect = read
        with mock.patch.object(focus.time, 'monotonic', side_effect=lambda: clock[0]), \
             mock.patch.object(Path, 'open', return_value=stream):
            with self.assertRaisesRegex(TimeoutError, 'stage deadline'):
                focus.verify([self.job['baseline']], deadline=1)
        self.assertEqual(stream.__enter__.return_value.read.call_count, 1)

    def probe(self, execute):
        with mock.patch.object(runner, 'host_access', return_value=contextlib.nullcontext()), \
             mock.patch.object(runner, 'execute', side_effect=execute):
            return focus.probe(self.job_path, self.job_hash, self.output, self.cpu)

    def fake_execute(self, argv, output, timeout):
        self.assertGreater(timeout, 0)
        self.assertEqual(argv[:3], [str(Path('/usr/bin/taskset').resolve()), '--cpu-list', str(self.cpu)])
        if output.stem.startswith('inventory-'):
            output.write_text('beta\nalpha\n')
        elif output.stem.startswith('pair-'):
            self.assertIn('--benchmark_min_time=0.01s', argv)
            self.assertIn('--benchmark_repetitions=1', argv)
            raw = Path(next(a.split('=', 1)[1] for a in argv if a.startswith('--benchmark_out=')))
            value = 2 if argv[3] == self.job['candidate']['path'] else 4
            raw.write_text(json.dumps(dict(benchmarks=[dict(name=name, cpu_time=value, time_unit='ns')
                                                      for name in reversed(self.job['cases'])])))
            output.write_text('mock benchmark output')
        else:
            output.write_text('oracle passed')

    def test_success_preserves_fixed_pair_order_and_not_accepted_status(self):
        report = self.probe(self.fake_execute)
        self.assertEqual(report['status'], 'focused_panel_complete_not_accepted')
        self.assertFalse(report['accepted'])
        self.assertEqual(report['build_seconds'], 0)
        self.assertTrue(report['inventories_verified_before_timing'])
        self.assertEqual([entry['label'] for entry in report['commands']], [
            'oracle-0', 'inventory-baseline', 'inventory-candidate',
            'pair-0-baseline', 'pair-0-candidate', 'pair-1-candidate',
            'pair-1-baseline', 'pair-2-baseline', 'pair-2-candidate'])
        self.assertEqual([row['median_ratio'] for row in report['cases']], [.5, .5])
        self.assertTrue((self.output / 'protocol.json').exists())

    def test_preflight_inventory_failure_prevents_any_timing(self):
        def execute(argv, output, timeout):
            self.fake_execute(argv, output, timeout)
            if output.stem == 'inventory-candidate':
                output.write_text('alpha\n')
        report = self.probe(execute)
        self.assertEqual(report['failure']['stage'], 'preflight')
        self.assertEqual(report['status'], 'failed')
        self.assertFalse(any(c['label'].startswith('pair-') for c in report['commands']))
        self.assertFalse(list(self.output.glob('pair-*.json')))

    def test_final_identity_rejects_mutation_during_mock_measurement(self):
        def execute(argv, output, timeout):
            self.fake_execute(argv, output, timeout)
            if output.stem == 'pair-2-candidate':
                Path(self.job['candidate']['path']).write_text('changed during measurement')
        report = self.probe(execute)
        self.assertEqual(report['failure']['stage'], 'final_identity')
        self.assertEqual(report['status'], 'failed')
        self.assertFalse(report['accepted'])
        self.assertEqual(len(list(self.output.glob('pair-*.json'))), 6)
        self.assertNotIn('cases', report)

    def test_late_json_read_cannot_report_success_or_launch_next_measurement(self):
        clock = [0]
        original = focus.read_iterations
        def late_read(path, expected):
            parsed = original(path, expected)
            clock[0] = 20
            return parsed
        with mock.patch.object(focus.time, 'monotonic', side_effect=lambda: clock[0]), \
             mock.patch.object(focus, 'read_iterations', side_effect=late_read):
            report = self.probe(self.fake_execute)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['failure']['stage'], 'measurement')
        self.assertEqual(report['failure']['type'], 'TimeoutError')
        self.assertFalse(report['accepted'])
        self.assertEqual(len([c for c in report['commands'] if c['label'].startswith('pair-')]), 1)
        self.assertEqual(json.loads((self.output / 'report.json').read_text()), report)

    def test_late_final_verification_cannot_report_success(self):
        clock = [0]
        original = focus.verify
        calls = [0]
        def late_verify(items, deadline=None):
            calls[0] += 1
            original(items, deadline)
            if calls[0] == 2:
                clock[0] = 61
        with mock.patch.object(focus.time, 'monotonic', side_effect=lambda: clock[0]), \
             mock.patch.object(focus, 'verify', side_effect=late_verify):
            report = self.probe(self.fake_execute)
        self.assertEqual(calls[0], 2)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['failure']['stage'], 'final_identity')
        self.assertEqual(report['failure']['type'], 'TimeoutError')
        self.assertFalse(report['accepted'])
        self.assertEqual(len(list(self.output.glob('pair-*.json'))), 6)
        self.assertEqual(json.loads((self.output / 'report.json').read_text()), json.loads(json.dumps(report)))

    def test_command_timeout_preserves_partial_evidence_without_retry(self):
        def timeout(argv, output, seconds):
            if output.stem == 'pair-0-baseline':
                output.write_text('partial process log before timeout')
                raw = Path(next(a.split('=', 1)[1] for a in argv if a.startswith('--benchmark_out=')))
                raw.write_text('{"benchmarks":')
                raise subprocess.TimeoutExpired(argv, seconds)
            self.fake_execute(argv, output, seconds)
        report = self.probe(timeout)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['failure']['stage'], 'measurement')
        self.assertEqual(report['failure']['type'], 'TimeoutExpired')
        measurements = [c for c in report['commands'] if c['label'].startswith('pair-')]
        self.assertEqual(len(measurements), 1)
        self.assertIn('elapsed_seconds', measurements[0])
        self.assertGreater(measurements[0]['timeout_seconds'], 0)
        self.assertEqual((self.output / 'pair-0-baseline.log').read_text(), 'partial process log before timeout')
        self.assertEqual((self.output / 'pair-0-baseline.json').read_text(), '{"benchmarks":')
        self.assertEqual(json.loads((self.output / 'report.json').read_text()), report)

    def test_job_hash_failure_preserves_failure_report_without_commands(self):
        self.job_path.write_text(self.job_path.read_text() + '\n')
        report = self.probe(mock.Mock(side_effect=AssertionError('Must not execute')))
        self.assertEqual(report['failure']['stage'], 'input')
        self.assertIn('job hash mismatch', report['failure']['message'])
        self.assertEqual(report['commands'], [])
        self.assertEqual(json.loads((self.output / 'report.json').read_text()), report)

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / 'report.json'
        marker.write_text('retained evidence')
        with self.assertRaises(FileExistsError):
            focus.probe(self.job_path, self.job_hash, self.output, self.cpu)
        self.assertEqual(marker.read_text(), 'retained evidence')


class HostDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.patch = mock.patch.object(runner.tempfile, 'gettempdir', return_value=str(self.root))
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.held = (self.root / ('ispc-builtins-host-%s.lock' % os.getuid())).open('a')
        self.addCleanup(self.held.close)
        fcntl.flock(self.held, fcntl.LOCK_EX)

    def test_contended_lock_times_out_with_bounded_wait(self):
        started = time.monotonic()
        with self.assertRaisesRegex(TimeoutError, 'host lock deadline'):
            with runner.host_access(exclusive=True, deadline=started + .06):
                self.fail('Contended exclusive lock must not be acquired')
        self.assertLess(time.monotonic() - started, .5)

    def test_waiting_lock_succeeds_after_release_and_is_released_on_exit(self):
        release = threading.Timer(.04, lambda: fcntl.flock(self.held, fcntl.LOCK_UN))
        release.start()
        self.addCleanup(release.join)
        with runner.host_access(exclusive=True, deadline=time.monotonic() + 1):
            with self.assertRaises(BlockingIOError):
                fcntl.flock(self.held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(self.held, fcntl.LOCK_EX | fcntl.LOCK_NB)


if __name__ == '__main__':
    unittest.main()
