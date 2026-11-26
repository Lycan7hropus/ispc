# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import tempfile
import unittest

import bench_adapter
import screen


class DecisionTests(unittest.TestCase):
    def test_verdict_needs_whole_ci_beyond_threshold(self):
        self.assertEqual(screen.classify([0.95, 0.97]), 'promising_for_context_check')
        self.assertEqual(screen.classify([1.02, 1.04]), 'slower_in_this_screen')
        self.assertEqual(screen.classify([0.97, 1.001]), 'unclear')
        self.assertEqual(screen.classify([0.996, 1.004]), 'unclear')
        self.assertEqual(screen.classify([0.994, 0.999]), 'unclear')
        # The CI clears 1% but not an A/A-derived 3% threshold.
        self.assertEqual(screen.classify([1.015, 1.025], 0.01), 'slower_in_this_screen')
        self.assertEqual(screen.classify([1.015, 1.025], 0.03), 'unclear')

    def test_nonfinite_or_nonpositive_measurements_are_rejected(self):
        for value in (0, -1, float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                screen.classify([value, 1.0])
            with self.assertRaises(ValueError):
                screen.summarize([1.0, value, 1.0])

    def test_trimmed_mean_ignores_disturbed_pairs(self):
        clean = [1.0 + 0.001 * (i % 5 - 2) for i in range(100)]
        disturbed = clean[:90] + [1.5] * 5 + [0.6] * 5
        self.assertAlmostEqual(screen.trimmed_mean(clean), 1.0, places=6)
        self.assertAlmostEqual(screen.trimmed_mean(disturbed), 1.0, delta=0.002)
        self.assertEqual(screen.trimmed_mean([2.0]), 2.0)

    def test_summary_detects_small_shift_and_stays_unclear_for_identity(self):
        rng = random.Random(7)
        same = [rng.gauss(1.0, 0.01) for _ in range(300)]
        slower = [value * 1.02 for value in same]
        identity = screen.summarize(same)
        self.assertEqual(identity['screen_status'], 'unclear')
        low, high = identity['ci95']
        self.assertTrue(low < identity['trimmed_mean_ratio'] < high)
        self.assertLess(high - low, 0.005)
        self.assertEqual(screen.summarize(slower)['screen_status'], 'slower_in_this_screen')
        self.assertEqual(screen.summarize([1 / v for v in slower])['screen_status'], 'promising_for_context_check')
        for key in ('median_ratio', 'observed_ratio_range', 'trimmed_mean_ratio', 'ci95', 'noise_threshold'):
            self.assertIn(key, identity)
        self.assertEqual(screen.summarize(same), identity)  # seeded bootstrap is reproducible

    def test_bench_threshold_follows_aa_noise_with_floor(self):
        quiet = dict(result=dict(cases=[dict(ci95=[0.998, 1.003]), dict(ci95=[0.999, 1.001])]))
        noisy = dict(result=dict(cases=[dict(ci95=[0.97, 1.004]), dict(ci95=[0.99, 1.012])]))
        self.assertEqual(bench_adapter.aa_noise_threshold(quiet, 0.005), 0.005)
        self.assertAlmostEqual(bench_adapter.aa_noise_threshold(noisy, 0.005), 0.03)


@unittest.skipUnless(platform.machine() == 'x86_64' and Path('/proc/cpuinfo').exists(), 'Linux x86 fixture')
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cxx = shutil.which('clang++')
        flags = Path('/proc/cpuinfo').read_text()
        if not cls.cxx or 'avx2' not in flags or 'rdtscp' not in flags:
            raise unittest.SkipTest('clang++, AVX2 and RDTSCP needed')
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.good = cls.root/'good.so'
        cls.bad = cls.root/'bad.so'
        good = '''#include <cstdint>
#include <cstddef>
extern "C" void lab_kernel(const uint64_t *in, uint64_t *v, uint64_t *f, size_t n, size_t r) {
    for (size_t k=0;k<r;++k) {
        asm volatile("" ::: "memory");
        for(size_t g=0;g<n;++g) {
            bool same=true;
            for(size_t j=1;j<8;++j) same &= in[g*8+j]==in[g*8];
            f[g]=same;
            if(same) v[g]=in[g*8];
        }
    }
}'''
        variants = [('good', good), ('bad', good.replace('f[g]=same;', 'f[g]=0;')),
                    ('low32', good.replace('in[g*8+j]==in[g*8]', 'uint32_t(in[g*8+j])==uint32_t(in[g*8])')),
                    ('ignored', good.replace('same &= in[g*8+j]==in[g*8];', 'if(j!=5) same &= in[g*8+j]==in[g*8];')),
                    ('falsewrite', good.replace('if(same) v[g]=in[g*8];', 'v[g]=same ? in[g*8] : 123;'))]
        for name, text in variants:
            source = cls.root/(name+'.cpp')
            source.write_text(text)
            subprocess.run([cls.cxx,'-O2','-shared','-fPIC',str(source),'-o',str(cls.root/(name+'.so'))], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_screen(self, candidate, destination):
        return screen.screen(self.good,candidate,self.cxx,destination,min(os.sched_getaffinity(0)),
                             groups=3,pairs=3,batch_ms=0.1,reps=3)

    def test_identity_screen_retains_inputs_and_never_accepts_patch(self):
        out = self.root/'identity'
        report = self.run_screen(self.good,out)
        self.assertEqual(report['status'],'screened_not_accepted')
        self.assertEqual(report['sources']['baseline']['binary_sha256'],report['sources']['candidate']['binary_sha256'])
        self.assertEqual(len(report['result']['cases']),3)
        self.assertEqual(report['result']['oracle'],'passed_all_on_fixture_only')
        self.assertEqual((out/'baseline.so').read_bytes(),self.good.read_bytes())
        self.assertEqual(len(report['result']['cases'][0]['pairs']),3)
        case = report['result']['cases'][0]
        self.assertEqual(case['reps'], 3)
        self.assertEqual(case['noise_threshold'], screen.NOISE_FLOOR)
        self.assertLessEqual(case['ci95'][0], case['ci95'][1])
        self.assertIn(case['screen_status'], ('unclear', 'promising_for_context_check', 'slower_in_this_screen'))

    def test_bad_kernel_stops_before_timing_results_and_retains_failure(self):
        out = self.root/'bad-output'
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_screen(self.bad,out)
        report = json.loads((out/'report.json').read_text())
        self.assertEqual(report['status'],'failed')
        self.assertNotIn('result',report)
        self.assertIn('oracle mismatch',(out/'measure.log').read_text())

    def test_oracle_catches_high_half_and_every_lane_independent_of_timing_groups(self):
        for variant in ('low32','ignored'):
            with self.assertRaises(subprocess.CalledProcessError):
                self.run_screen(self.root/(variant+'.so'),self.root/(variant+'-output'))

    def test_false_result_does_not_require_preserved_samevalue(self):
        report = self.run_screen(self.root/'falsewrite.so',self.root/'falsewrite-output')
        self.assertEqual(report['status'],'screened_not_accepted')
