#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

"""Focused process cleanup tests; no build, measurement, or host locks."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import run


class ProcessCleanupTests(unittest.TestCase):
    def process_state(self, pid):
        try:
            return Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        except FileNotFoundError:
            return None

    def assert_stopped(self, pid):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            state = self.process_state(pid)
            if state is None or state[0] in ("Z", "X"):
                return
            time.sleep(.01)
        self.fail(f"timed-out command left process {pid} running")

    def exercise(self, separate_session, nested):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "child.json"
            child = root / "child.py"
            child.write_text(
                "import json, os, sys, time; from pathlib import Path; "
                "Path(sys.argv[1]).write_text(json.dumps(dict("
                "pid=os.getpid(), parent=os.getppid(), group=os.getpgrp(), "
                "started=Path('/proc/self/stat').read_text().rsplit(') ', 1)[1].split()[19]))); "
                "time.sleep(60)"
            )
            helper = root / "helper.py"
            creation = "start_new_session=True" if separate_session else "process_group=0"
            helper.write_text(
                "import subprocess, sys, time; "
                f"subprocess.Popen([sys.executable, {str(child)!r}, {str(marker)!r}], {creation}); "
                "time.sleep(60)"
            )
            argv = [sys.executable, str(helper)]
            if nested:
                wrapper = root / "wrapper.py"
                wrapper.write_text(
                    "import sys; from pathlib import Path; "
                    f"sys.path.insert(0, {str(Path(run.__file__).parent)!r}); "
                    "import run; "
                    f"run.execute({argv!r}, Path({str(root / 'nested.log')!r}), 60)"
                )
                argv = [sys.executable, str(wrapper)]
            try:
                # The outer invocation owns its group; nested helpers receive
                # the managed marker through the executor, as in evaluate.py.
                with mock.patch.dict(os.environ):
                    os.environ.pop("ISPC_BUILTINS_MANAGED_GROUP", None)
                    with self.assertRaises(subprocess.TimeoutExpired):
                        run.execute(argv, root / "outer.log", 2)
                metadata = json.loads(marker.read_text())
                self.assertNotEqual(metadata["group"], os.getpgrp())
                self.assert_stopped(metadata["pid"])
                self.assert_stopped(metadata["parent"])
            finally:
                # A failed regression test must not leave its sleeping child.
                if marker.exists():
                    metadata = json.loads(marker.read_text())
                    state = self.process_state(metadata["pid"])
                    if state is not None and state[19] == metadata["started"]:
                        try:
                            os.kill(metadata["pid"], signal.SIGKILL)
                        except ProcessLookupError:
                            pass

    def test_timeout_kills_child_in_separate_session(self):
        self.exercise(separate_session=True, nested=False)

    def test_timeout_kills_child_in_separate_process_group(self):
        self.exercise(separate_session=False, nested=False)

    def test_outer_timeout_kills_nested_helpers_separate_session(self):
        self.exercise(separate_session=True, nested=True)


if __name__ == "__main__":
    unittest.main()
