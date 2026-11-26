#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""T0 popcnt int64 fixture: oracle rejects wrong kernels, examples pass, adapter routing."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest

import bench_adapter
import screen

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE / 'screen_examples'

GOOD = '''#include <cstdint>
#include <cstddef>
static int32_t count(uint64_t v) { int32_t c = 0; while (v) { v &= v - 1; ++c; } return c; }
extern "C" void lab_kernel(const uint64_t *in, int32_t *out, size_t n, size_t r) {
    for (size_t k = 0; k < r; ++k) {
        asm volatile("" ::: "memory");
        for (size_t i = 0; i < n * 8; ++i) out[i] = count(in[i]);
    }
}'''
BROKEN = {
    'low32': ('count(in[i])', 'count(uint32_t(in[i]))'),
    'lane-swap': ('out[i] = count(in[i]);', 'out[i ^ 1] = count(in[i]);'),
    'saturate': ('return c;', 'return c > 63 ? 63 : c;'),
    'byte-wrap': ('return c;', 'return c & 31;'),
    'overrun': ('out[i] = count(in[i]);', '{ out[i] = count(in[i]); out[n * 8] = 0; }'),
    'underrun': ('out[i] = count(in[i]);', '{ out[i] = count(in[i]); out[-1] = 0; }'),
    'zero-repeat': ('for (size_t k = 0; k < r; ++k) {', 'out[0] = 0; for (size_t k = 0; k < r; ++k) {'),
    'input-write': ('out[i] = count(in[i]);', '{ out[i] = count(in[i]); const_cast<uint64_t *>(in)[i] ^= 1; }'),
}


def available():
    flags = Path('/proc/cpuinfo').read_text() if Path('/proc/cpuinfo').exists() else ''
    return platform.machine() == 'x86_64' and all(f in flags for f in ('avx2', 'rdtscp', 'popcnt'))


class RoutingTests(unittest.TestCase):
    def test_fixture_registered_without_body_mode(self):
        spec = screen.FIXTURES['popcnt-i64']
        self.assertEqual(spec['body_mode'], {False})
        self.assertIn('-mpopcnt', spec['build_flags'])
        with tempfile.TemporaryDirectory() as root, self.assertRaisesRegex(ValueError, 'does not support body mode'):
            screen.screen(EXAMPLES / 'popcnt_i64_scalar.S', EXAMPLES / 'popcnt_i64_scalar.S', 'clang++',
                          Path(root) / 'out', min(os.sched_getaffinity(0)), body_mode=True, fixture='popcnt-i64')

    def test_adapter_rejects_masks_and_types_outside_fixture(self):
        with tempfile.TemporaryDirectory() as root:
            task = Path(root) / 'task'
            task.mkdir()
            shutil.copyfile(EXAMPLES / 'popcnt_i64_scalar.S', task / 'candidate.S')
            for change, message in (({'masks': ['even']}, "not 'even'"), ({'types': ['int32']}, 'covers only types')):
                spec = dict(builtin='popcnt', tier='T0', targets=['avx2-i32x8'], types=['int64'], masks=['all'])
                spec.update(change)
                (task / 'task.json').write_text(json.dumps(spec))
                result = dict(notes=[], measurements=[])
                with self.subTest(change=change), self.assertRaisesRegex(ValueError, message):
                    bench_adapter.t0(bench_adapter.load_task(task), task, Path(root) / 'out', result)


@unittest.skipUnless(available(), 'x86-64 Linux with AVX2, RDTSCP and POPCNT needed')
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cxx = shutil.which('clang++')
        if not cls.cxx:
            raise unittest.SkipTest('clang++ needed')
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        for name, text in [('good', GOOD)] + [(n, GOOD.replace(a, b)) for n, (a, b) in BROKEN.items()]:
            if name != 'good' and text == GOOD:
                raise AssertionError(f'mutation {name} did not apply')
            source = cls.root / (name + '.cpp')
            source.write_text(text)
            subprocess.run([cls.cxx, '-O1', '-shared', '-fPIC', str(source), '-o', str(cls.root / (name + '.so'))],
                           check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_screen(self, baseline, candidate, name):
        return screen.screen(baseline, candidate, self.cxx, self.root / name, min(os.sched_getaffinity(0)),
                             groups=3, pairs=3, batch_ms=0.1, reps=3, fixture='popcnt-i64')

    def test_reference_kernel_and_both_examples_pass_oracle(self):
        for name, candidate in (('identity', self.root / 'good.so'),
                                ('scalar', EXAMPLES / 'popcnt_i64_scalar.S'),
                                ('lut', EXAMPLES / 'popcnt_i64_avx2_lut.S')):
            with self.subTest(candidate=name):
                report = self.run_screen(self.root / 'good.so', candidate, name)
                self.assertEqual(report['status'], 'screened_not_accepted')
                self.assertEqual(report['fixture'], 'popcnt_i64_all_on_v1')
                self.assertEqual(report['result']['oracle'], 'passed_popcnt_i64_all_on_fixture_only')
                self.assertEqual([c['name'] for c in report['result']['cases']], ['random', 'sparse', 'dense'])
                self.assertTrue(all('ci95' in c for c in report['result']['cases']))

    def test_oracle_rejects_every_broken_kernel_before_timing(self):
        for name in BROKEN:
            with self.subTest(mutation=name):
                with self.assertRaises(subprocess.CalledProcessError):
                    self.run_screen(self.root / 'good.so', self.root / (name + '.so'), 'broken-' + name)
                report = json.loads((self.root / ('broken-' + name) / 'report.json').read_text())
                self.assertEqual(report['status'], 'failed')
                self.assertNotIn('result', report)
                log = (self.root / ('broken-' + name) / 'measure.log').read_text()
                self.assertRegex(log, 'oracle mismatch|canary modified|zero repetitions changed output')


if __name__ == '__main__':
    unittest.main()
