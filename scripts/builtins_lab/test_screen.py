# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest

import screen


class DecisionTests(unittest.TestCase):
    def test_screen_is_conservative_and_not_a_confidence_interval(self):
        self.assertEqual(screen.classify([0.7, 0.8, 0.9]), 'promising_for_context_check')
        self.assertEqual(screen.classify([1.2, 1.3, 1.1]), 'slower_in_this_screen')
        self.assertEqual(screen.classify([0.7, 1.02, 0.9]), 'unclear')
        self.assertEqual(screen.classify([0.99, 1, 1.01]), 'unclear')

    def test_nonfinite_or_nonpositive_measurements_are_rejected(self):
        for value in (0, -1, float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                screen.classify([value])


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
                             groups=3,pairs=3,batch_ms=1)

    def test_identity_screen_retains_inputs_and_never_accepts_patch(self):
        out = self.root/'identity'
        report = self.run_screen(self.good,out)
        self.assertEqual(report['status'],'screened_not_accepted')
        self.assertEqual(report['sources']['baseline']['binary_sha256'],report['sources']['candidate']['binary_sha256'])
        self.assertEqual(len(report['result']['cases']),3)
        self.assertEqual(report['result']['oracle'],'passed_all_on_fixture_only')
        self.assertEqual((out/'baseline.so').read_bytes(),self.good.read_bytes())
        self.assertEqual(len(report['result']['cases'][0]['pairs']),3)

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
