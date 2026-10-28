# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
import os
import platform
import shutil
import tempfile
import unittest

import screen


class BodyValidationTests(unittest.TestCase):
    def test_frame_mutation_control_flow_and_bad_memory_are_rejected(self):
        forbidden = ['ret', 'call lab_kernel', '.include "other.S"', 'loop: xorl %eax,%eax',
                     'xorl %ecx,%ecx', 'movq %rax,(%rdi)', 'cmpl 5,%eax',
                     'vmovdqu 40(%rdi),%ymm0', 'vmovdqu -8(%rdi),%ymm0',
                     'vmovdqu 0(%rsp),%ymm0', 'vpxor %zmm0,%zmm0,%zmm0']
        for body in forbidden:
            with self.subTest(body=body), self.assertRaises(ValueError):
                screen.validate_body(body)

    def test_comments_are_not_executed_and_empty_bodies_fail(self):
        self.assertEqual(screen.validate_body('xorl %eax,%eax # call fake'),'xorl %eax,%eax\n')
        with self.assertRaises(ValueError):
            screen.validate_body('# no instructions')


@unittest.skipUnless(platform.machine() == 'x86_64' and Path('/proc/cpuinfo').exists(), 'Linux x86 fixture')
class BodyIntegrationTests(unittest.TestCase):
    def test_common_frame_handles_result_width_without_weakening_oracle(self):
        cxx = shutil.which('clang++')
        flags = Path('/proc/cpuinfo').read_text()
        if not cxx or 'avx2' not in flags or 'rdtscp' not in flags:
            self.skipTest('clang++, AVX2 and RDTSCP needed')
        # Low32 bits return normalized0/1; high32 RAX intentionally unspecified.
        body = '''movq $0xffffffff00000000, %rax
vpbroadcastq (%rdi), %ymm0
vpxor (%rdi), %ymm0, %ymm1
vpxor 32(%rdi), %ymm0, %ymm2
vpor %ymm1, %ymm2, %ymm3
vptest %ymm3, %ymm3
sete %al
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'body.inc'
            source.write_text(body)
            report = screen.screen(source, source, cxx, root/'out',min(os.sched_getaffinity(0)),
                                   groups=3,pairs=3,batch_ms=1,body_mode=True)
            self.assertEqual(report['status'],'screened_not_accepted')
            self.assertEqual(report['framing'],'common_frame_v1')
            self.assertEqual(report['result']['oracle'],'passed_all_on_fixture_only')
            self.assertEqual(report['sources']['baseline']['expanded_sha256'],
                             report['sources']['candidate']['expanded_sha256'])
            self.assertEqual(report['sources']['baseline']['binary_sha256'],
                             report['sources']['candidate']['binary_sha256'])
            self.assertTrue((root/'out/screen_frame.S').exists())
