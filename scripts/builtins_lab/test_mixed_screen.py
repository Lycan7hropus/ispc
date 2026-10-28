# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Functional mixed-frame regressions; never invoke a timing/calibration loop."""
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest

import run as runner
import screen

GOOD = """vpxor %ymm3, %ymm0, %ymm4
vpxor %ymm3, %ymm1, %ymm5
vpxor %ymm6, %ymm6, %ymm6
vpmovsxdq %xmm2, %ymm7
vextracti128 $1, %ymm2, %xmm8
vpmovsxdq %xmm8, %ymm8
vblendvpd %ymm7, %ymm4, %ymm6, %ymm4
vblendvpd %ymm8, %ymm5, %ymm6, %ymm5
vptest %ymm4, %ymm4
sete %al
vptest %ymm5, %ymm5
sete %r10b
andb %r10b, %al
movzbl %al, %eax
"""
IGNORE_MASK = """vpxor %ymm3, %ymm0, %ymm4
vpxor %ymm3, %ymm1, %ymm5
vptest %ymm4, %ymm4
sete %al
vptest %ymm5, %ymm5
sete %r10b
andb %r10b, %al
movzbl %al, %eax
"""
EXACT_MINUS_ONE = """vpcmpeqq %ymm15, %ymm15, %ymm15
vpcmpeqq %ymm15, %ymm2, %ymm2
""" + GOOD


class MixedDialectTests(unittest.TestCase):
    def test_register_only_body_preserves_frame_and_first_active(self):
        self.assertEqual(screen.validate_mixed_body(GOOD), GOOD)
        for body in ['vmovq %rax, %r9', 'vmovq %rax, %r8', 'vmovq %rax, %rbp',
                     'vmovq %rax, %rdi', 'vmovq (%rsi), %rax',
                     'vmovq %rax, (%rdx)', 'ret', 'call helper', '.byte 0',
                     'label: sete %al', 'vpxor %zmm0, %zmm0, %zmm0']:
            with self.subTest(body=body), self.assertRaises(ValueError):
                screen.validate_mixed_body(body)

    def test_comments_do_not_enable_control_flow_and_empty_body_fails(self):
        self.assertEqual(screen.validate_mixed_body('sete %al # call helper'), 'sete %al\n')
        for body in ['# empty', GOOD * 5]:
            with self.assertRaises(ValueError):
                screen.validate_mixed_body(body)


@unittest.skipUnless(platform.machine() == 'x86_64' and Path('/proc/cpuinfo').exists(),
                     'Linux x86-64 functional fixture')
class MixedFrameOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('clang++')
        if not compiler or 'avx2' not in Path('/proc/cpuinfo').read_text():
            raise unittest.SkipTest('clang++ and AVX2 required')
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        fixture_dir = Path(screen.__file__).resolve().parent
        frame = (fixture_dir / 'screen_mixed_frame.S').read_text()
        cls.libraries = {}
        # These kernels exist solely to validate the independent oracle. No speed claims.
        with runner.host_access(exclusive=False):
            for name, body in [('good', GOOD), ('ignore-mask', IGNORE_MASK),
                               ('exact-minus-one', EXACT_MINUS_ONE)]:
                source = cls.root / (name + '.S')
                source.write_text(frame.replace('/* BODY_INSERTION_POINT */',
                                                screen.validate_mixed_body(body)))
                library = cls.root / (name + '.so')
                subprocess.run([compiler, '-shared', '-fPIC', '-mavx2', str(source),
                                '-o', str(library)], check=True, capture_output=True, timeout=30)
                cls.libraries[name] = library
            driver = cls.root / 'oracle_driver.cpp'
            driver.write_text('#define main screen_timing_main\n#include "' +
                              str(fixture_dir / 'screen_mixed_kernel.cpp') +
                              '"\n#undef main\n' + r"""
Kernel delegate;
std::string mutation;
void corrupt(const uint64_t* input, const int32_t* masks, uint64_t* values,
             uint64_t* flags, size_t groups, size_t repeats) {
    delegate(input, masks, values, flags, groups, repeats);
    if (mutation == "input-guard" || (mutation == "zero-input" && repeats == 0))
        const_cast<uint64_t*>(input)[-1] ^= 1;
    if (mutation == "mask-guard" || (mutation == "zero-mask" && repeats == 0))
        const_cast<int32_t*>(masks)[-1] ^= 1;
}
int main(int argc, char** argv) {
    try {
        Library library(argv[1]);
        if (argc > 2) {
            delegate = library.kernel;
            mutation = argv[2];
            Fixture check(3, 0);
            check.verify(corrupt);
            throw std::runtime_error("corrupt kernel unexpectedly passed");
        }
        for (size_t groups : {size_t(0), size_t(1), size_t(2), size_t(3), size_t(7)})
            for (int pattern = 0; pattern != 3; ++pattern) {
                Fixture check(groups, pattern);
                check.verify(library.kernel);
            }
        constexpr int32_t negative[] = {-1, INT32_MIN, -2, -1234567};
        constexpr int32_t positive[] = {0, INT32_MAX, 1, 1234567};
        for (unsigned mask = 1; mask < 255; ++mask)
            for (unsigned repr = 0; repr < 4; ++repr) {
                Fixture check(1, 0);
                const uint64_t base = 0x8000000100000001ULL;
                for (size_t lane = 0; lane < 8; ++lane) {
                    const bool active = mask & (1U << lane);
                    check.masks[1 + lane] = active ? negative[repr] : positive[repr];
                    check.input[1 + lane] = active ? base : (~base ^ (uint64_t(lane) << 32));
                }
                check.verify(library.kernel);
                for (size_t lane = 0; lane < 8; ++lane)
                    for (size_t bit = 0; bit < 64; ++bit) {
                        check.input[1 + lane] ^= uint64_t(1) << bit;
                        check.verify(library.kernel);
                        check.input[1 + lane] ^= uint64_t(1) << bit;
                    }
            }
        std::cout << "functional oracle passed; no timing\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
""")
            cls.driver = cls.root / 'oracle-driver'
            subprocess.run([compiler, '-O2', '-std=c++17', str(driver), '-ldl',
                            '-o', str(cls.driver)], check=True, capture_output=True, timeout=30)

    def run_driver(self, name, mutation=None):
        argv = [str(self.driver), str(self.libraries[name])]
        if mutation:
            argv.append(mutation)
        with runner.host_access(exclusive=False):
            return subprocess.run(argv, capture_output=True, text=True, timeout=30)

    def test_good_frame_handles_all_masks_representations_bits_and_first_active(self):
        result = self.run_driver('good')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('no timing', result.stdout)

    def test_ignoring_inactive_lanes_is_rejected_by_scalar_oracle(self):
        result = self.run_driver('ignore-mask')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('independent mixed-mask oracle mismatch', result.stderr)

    def test_exact_minus_one_mask_assumption_is_rejected(self):
        result = self.run_driver('exact-minus-one')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('independent mixed-mask oracle mismatch', result.stderr)

    def test_input_mask_guards_and_zero_repeat_mutations_are_rejected(self):
        for mutation in ['input-guard', 'mask-guard', 'zero-input', 'zero-mask']:
            with self.subTest(mutation=mutation):
                result = self.run_driver('good', mutation)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('canary', result.stderr)
                self.assertNotIn('unexpectedly passed', result.stderr)


if __name__ == '__main__':
    unittest.main()
