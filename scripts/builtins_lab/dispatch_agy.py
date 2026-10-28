#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Run an owned task through agy; process success is not task acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import run as runner


def workspace_identity(repo, owned_output=None):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args])
    untracked = {}
    for raw in git('ls-files', '--others', '--exclude-standard', '-z').split(b'\0'):
        if not raw:
            continue
        name = os.fsdecode(raw)
        path = Path(repo) / name
        if owned_output is not None and path.absolute().is_relative_to(Path(owned_output).absolute()):
            continue
        if path.is_symlink():
            untracked[name] = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
        elif path.is_file():
            untracked[name] = runner.sha256(path)
    return dict(head=git('rev-parse', 'HEAD').decode().strip(),
                status=git('status', '--porcelain=v1').decode(),
                untracked_sha256=untracked,
                tracked_diff_sha256=hashlib.sha256(git('diff', 'HEAD', '--binary')).hexdigest())


def backend_result(log):
    result = None
    for line in log.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # CLI diagnostic lines are retained verbatim alongside NDJSON.
        if isinstance(event, dict) and event.get('event') == 'result':
            result = event.get('result')
    return result if isinstance(result, dict) else None


def dispatch(task, repo, output, timeout=360, expected=()):
    if timeout < 30:
        raise ValueError('timeout must be at least 30 seconds')
    executable = shutil.which('agy')
    if executable is None:
        raise ValueError('agy not found in PATH')
    task_text = Path(task).read_text()
    if not task_text.strip():
        raise ValueError('task is empty')
    if any(Path(name).is_absolute() or '..' in Path(name).parts for name in expected):
        raise ValueError('expected artifacts must be relative to the owned output')
    repo = Path(repo).resolve()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    task_copy = output / 'task.txt'
    task_copy.write_text(task_text)
    command = [executable, '--sandbox', '--mode', 'accept-edits',
               '--add-dir', str(repo), '--print-timeout', str(timeout - 10) + 's',
               '--output-format', 'stream-json', '--print', task_text]
    before = workspace_identity(repo, output)
    report = dict(status='running', backend='agy', cwd=str(output),
                  executable=executable, executable_sha256=runner.sha256(Path(executable)),
                  task_sha256=runner.sha256(task_copy),
                  argv=command[:-1] + ['<contents of retained task.txt>'],
                  workspace_before=before,
                  expected_artifacts=list(expected),
                  remote_timeout_limitation='CLI timeout does not establish remote-turn cancellation; do not automatically resubmit partial tasks.',
                  limitation='Sandbox and task instructions do not prove completion or correctness; review retained artifacts.')

    def save():
        (output / 'dispatch.json').write_text(json.dumps(report, indent=2) + '\n')

    save()
    try:
        runner.execute(command, output / 'agy.log', timeout, cwd=output)
        report['status'] = 'process_exited_for_review'
        log = (output / 'agy.log').read_text(encoding='utf-8', errors='replace')
        result = backend_result(log)
        if result is not None:
            report['backend_reported'] = {key: result[key] for key in
                ('conversation_id', 'status', 'duration_seconds', 'num_turns', 'usage') if key in result}
            if result.get('status') != 'SUCCESS':
                report['status'] = 'backend_failed'
        else:
            report['status'] = 'missing_backend_result'
        if any(line.startswith('[agy] print timeout') for line in log.splitlines()):
            report['status'] = 'partial'
        missing = [name for name in expected if not (output / name).is_file()]
        report['missing_expected_artifacts'] = missing
        if missing and report['status'] == 'process_exited_for_review':
            report['status'] = 'missing_result'
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        after = workspace_identity(repo, output)
        report['workspace_after'] = after
        report['workspace_changed'] = after != before
        if after != before:
            report['status'] = 'workspace_changed_requires_review'
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', type=Path)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=360)
    parser.add_argument('--expect', action='append', default=[])
    args = parser.parse_args()
    try:
        report = dispatch(args.task, args.repo, args.output, args.timeout, args.expect)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(report['status'])
    return 0 if report['status'] == 'process_exited_for_review' else 2


if __name__ == '__main__':
    sys.exit(main())
