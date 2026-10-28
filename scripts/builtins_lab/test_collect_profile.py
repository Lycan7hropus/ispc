# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import collect_profile


class ProfileAuditTests(unittest.TestCase):
    def test_missing_counter_is_explicit(self):
        self.assertEqual(collect_profile.counter_gaps('1;cycles\n<not counted>;cache-misses\n'),
                         ['<not counted>;cache-misses'])

    def test_failure_retains_command_and_executable_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / 'workload'
            executable.write_text('test executable')
            executable.chmod(0o755)
            out = root / 'profile'
            with mock.patch.object(collect_profile.runner, 'execute',
                                   side_effect=subprocess.TimeoutExpired(['perf'], 1)):
                with self.assertRaises(subprocess.TimeoutExpired):
                    collect_profile.collect(executable, [str(executable)], out,
                                            'microbenchmark', 'test audit retention')
            report = json.loads((out / 'profile.json').read_text())
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(report['executable_sha256'], collect_profile.runner.sha256(executable))
            self.assertTrue(report['commands'])


if __name__ == '__main__':
    unittest.main()
