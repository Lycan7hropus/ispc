# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import dispatch_agy


class DispatchTests(unittest.TestCase):
    def test_untracked_content_is_audited_and_owned_output_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            source = root / 'source'
            source.write_text('baseline')
            subprocess.run(['git', '-C', str(root), 'add', 'source'], check=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=Test', '-c',
                            'user.email=test@example.com', 'commit', '-qm', 'baseline'], check=True)
            pending = root / 'pending.py'
            pending.write_text('original')
            out = root / 'owned'
            out.mkdir()
            artifact = out / 'result.json'
            artifact.write_text('initial')
            before = dispatch_agy.workspace_identity(root, out)
            artifact.write_text('finished')
            self.assertEqual(before, dispatch_agy.workspace_identity(root, out))
            pending.write_text('changed by worker')
            after = dispatch_agy.workspace_identity(root, out)
            self.assertEqual(before['status'], after['status'])
            self.assertNotEqual(before['untracked_sha256'], after['untracked_sha256'])

    def test_zero_exit_with_failed_backend_result_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = root / 'task.txt'
            task.write_text('owned task')
            executable = root / 'agy'
            executable.write_text('test executable')

            def failed_backend(command, log, *args, **kwargs):
                log.write_text(json.dumps(dict(event='result', result=dict(
                    status='ERROR', conversation_id='session', usage=dict(total_tokens=5)))))

            with mock.patch.object(dispatch_agy.shutil, 'which', return_value=str(executable)), \
                 mock.patch.object(dispatch_agy, 'workspace_identity', return_value={'head': 'fixed'}), \
                 mock.patch.object(dispatch_agy.runner, 'execute', side_effect=failed_backend):
                report = dispatch_agy.dispatch(task, root, root / 'output')
            self.assertEqual(report['status'], 'backend_failed')
            self.assertEqual(report['backend_reported']['usage']['total_tokens'], 5)

    def test_zero_exit_with_print_timeout_is_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = root / 'task.txt'
            task.write_text('owned task')
            executable = root / 'agy'
            executable.write_text('test executable')

            def partial(command, log, *args, **kwargs):
                log.write_text('[agy] print timeout after 20s with turn in progress; returning partial output')

            with mock.patch.object(dispatch_agy.shutil, 'which', return_value=str(executable)), \
                 mock.patch.object(dispatch_agy, 'workspace_identity', return_value={'head': 'fixed'}), \
                 mock.patch.object(dispatch_agy.runner, 'execute', side_effect=partial):
                report = dispatch_agy.dispatch(task, root, root / 'output', expected=['result.json'])
            self.assertEqual(report['status'], 'partial')
            self.assertEqual(report['missing_expected_artifacts'], ['result.json'])

    def test_dirty_file_content_change_is_detected_even_if_status_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            source = root / 'source'
            source.write_text('initial')
            subprocess.run(['git', '-C', str(root), 'add', 'source'], check=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=Test', '-c',
                            'user.email=test@example.com', 'commit', '-qm', 'baseline'], check=True)
            source.write_text('already dirty')
            before = dispatch_agy.workspace_identity(root)
            source.write_text('modified by worker')
            after = dispatch_agy.workspace_identity(root)
            self.assertEqual(before['status'], after['status'])
            self.assertNotEqual(before['tracked_diff_sha256'], after['tracked_diff_sha256'])

    def test_worker_failure_retains_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = root / 'task.txt'
            task.write_text('owned task')
            executable = root / 'agy'
            executable.write_text('test executable')
            output = root / 'output'
            with mock.patch.object(dispatch_agy.shutil, 'which', return_value=str(executable)), \
                 mock.patch.object(dispatch_agy, 'workspace_identity', return_value={'head': 'fixed'}), \
                 mock.patch.object(dispatch_agy.runner, 'execute',
                                   side_effect=subprocess.CalledProcessError(1, ['agy'])):
                with self.assertRaises(subprocess.CalledProcessError):
                    dispatch_agy.dispatch(task, root, output)
            audit = json.loads((output / 'dispatch.json').read_text())
            self.assertEqual(audit['status'], 'failed')
            self.assertFalse(audit['workspace_changed'])
            self.assertEqual((output / 'task.txt').read_text(), 'owned task')


if __name__ == '__main__':
    unittest.main()
