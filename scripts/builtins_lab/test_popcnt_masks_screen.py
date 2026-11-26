# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""popcnt-i64-masks T0 fixture: shipped kernels pass the oracle, broken ones are rejected before timing."""
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

EXAMPLES = Path(__file__).resolve().parent / 'screen_examples'
BASELINE = EXAMPLES / 'popcnt_i64_ispc.S'
CROARING_ISPC = EXAMPLES / 'popcnt_i64_croaring_ispc.S'
FIXTURE = 'popcnt-i64-masks'
CROARING = EXAMPLES / 'popcnt_i64_croaring.cpp'
CASES = ['all_on', 'even', 'odd', 'sparse_one_lane', 'random_mixed', 'all_off', 'even_static', 'chain_all_on',
         'chain_even']


class PopcntRegistrationTests(unittest.TestCase):
    def test_fixture_is_registered_with_its_own_lab_baseline(self):
        spec = bench_adapter.T0_FIXTURES['popcnt']
        self.assertEqual(spec['masks']['masks'], FIXTURE)
        self.assertEqual(spec['masks']['all'], 'popcnt-i64')
        baselines = spec['fixture_baselines'][FIXTURE]
        self.assertNotIn('.inc', baselines)
        self.assertTrue(all(path == BASELINE for path in baselines.values()))
        self.assertEqual(screen.FIXTURES[FIXTURE]['cases'], len(CASES))
        self.assertEqual(screen.FIXTURES[FIXTURE]['body_mode'], {False})

    def test_t1_packet_is_registered_and_loads(self):
        import fixture_packet
        packet = fixture_packet.load(bench_adapter.T1_PACKETS['popcnt'])
        manifest = packet['manifest']
        self.assertEqual(manifest['allowed_paths'], ['builtins/target-avx2-i32x8.ll', 'tests/lit-tests/3615.ispc'])
        self.assertEqual(manifest['functional_globs'], ['popcnt*.ispc'])
        self.assertIn('control_int32/min_time:0.100', manifest['cases'])

    def test_body_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                screen.screen(BASELINE, CROARING, 'clang++', Path(root) / 'out', min(os.sched_getaffinity(0)),
                              body_mode=True, fixture=FIXTURE)


@unittest.skipUnless(platform.machine() == 'x86_64' and Path('/proc/cpuinfo').exists(), 'Linux x86 fixture')
class PopcntScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cxx = shutil.which('clang++')
        flags = Path('/proc/cpuinfo').read_text()
        if not cls.cxx or not all(flag in flags for flag in ('avx2', 'rdtscp', 'popcnt')):
            raise unittest.SkipTest('clang++, AVX2, POPCNT and RDTSCP needed')
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        text = CROARING.read_text()
        mutations = {
            # Inactive lanes must be zero.
            'nomask': ('return _mm256_andnot_si256(_mm256_cmpeq_epi32(mask, _mm256_setzero_si256()), result);',
                       'return result;'),
            # Lane order of the int32 packing.
            'order': ('_MM_SHUFFLE(3, 1, 2, 0)', '_MM_SHUFFLE(3, 2, 1, 0)'),
            # Only the low 32 bits of every int64 counted.
            'low32': ('__m256i low = _mm256_and_si256(v, nibble);',
                      '__m256i low = _mm256_and_si256(_mm256_and_si256(v, _mm256_set1_epi64x(0xffffffff)), nibble);'),
            # Compile-time even entry point must still zero odd lanes.
            'evenmask': ('return _mm256_blend_epi32(popcnt8(v0, v1), _mm256_setzero_si256(), 0xaa);',
                         'return popcnt8(v0, v1);'),
            # Chain must feed the previous result back.
            'nochain': ('v0 = _mm256_xor_si256(v0, _mm256_cvtepu32_epi64(_mm256_castsi256_si128(previous)));', ''),
        }
        cls.broken = {}
        for name, (old, new) in mutations.items():
            assert text.count(old) == 1, name
            path = cls.root / f'{name}.cpp'
            path.write_text(text.replace(old, new))
            cls.broken[name] = path

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_screen(self, candidate, name, baseline=BASELINE, fixture=FIXTURE):
        return screen.screen(baseline, candidate, self.cxx, self.root / name, min(os.sched_getaffinity(0)),
                             groups=4, pairs=3, batch_ms=0.05, reps=3, fixture=fixture)

    def test_shipped_kernels_pass_both_popcnt_fixtures(self):
        # popcnt_i64_llvm_ctpop.cpp is left out: it needs clang 19+.
        for name, path in (('croaring', CROARING), ('croaring-ispc', CROARING_ISPC), ('ispc', BASELINE)):
            for fixture in ('popcnt-i64', FIXTURE):
                with self.subTest(name=name, fixture=fixture):
                    report = self.run_screen(path, f'{name}-{fixture}', EXAMPLES / 'popcnt_i64_scalar.S'
                                             if fixture == 'popcnt-i64' else BASELINE, fixture)
                    self.assertEqual(report['status'], 'screened_not_accepted')
                    self.assertTrue(report['result']['oracle'].startswith('passed'))

    def test_croaring_candidate_passes_oracle_and_reports_every_case(self):
        report = self.run_screen(CROARING, 'croaring')
        self.assertEqual(report['status'], 'screened_not_accepted')
        self.assertEqual(report['fixture'], 'popcnt_i64_masks_v1')
        self.assertEqual(report['result']['oracle'], 'passed_popcnt_i64_fixture')
        self.assertEqual([case['name'] for case in report['result']['cases']], CASES)
        for case in report['result']['cases']:
            self.assertEqual(len(case['pairs']), 3)
            self.assertLessEqual(case['ci95'][0], case['ci95'][1])

    def test_broken_candidates_fail_before_timing(self):
        for name, path in self.broken.items():
            with self.subTest(name), self.assertRaises(subprocess.CalledProcessError):
                self.run_screen(path, name)
            report = json.loads((self.root / name / 'report.json').read_text())
            self.assertEqual(report['status'], 'failed')
            self.assertNotIn('result', report)
            log = (self.root / name / 'measure.log').read_text()
            self.assertTrue('oracle mismatch' in log, log)


if __name__ == '__main__':
    unittest.main()
