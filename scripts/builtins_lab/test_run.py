#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

"""Runner tests; synthetic measurements test decisions, not ISPC performance."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import run


class ComparisonTests(unittest.TestCase):
    def samples(self, baseline, candidate):
        return {"baseline": [{"shuffle": v} for v in baseline],
                "candidate": [{"shuffle": v} for v in candidate]}

    def test_clear_gain_requires_confirmation(self):
        result = run.compare(self.samples([100, 101, 99], [80, 81, 79]), .03, .02)
        self.assertEqual(result["status"], "candidate_for_confirmation")

    def test_noisy_gain_is_inconclusive(self):
        result = run.compare(self.samples([90, 100, 110], [80, 90, 100]), .03, .02)
        self.assertEqual(result["status"], "inconclusive")

    def test_regression_cannot_hide_behind_average_gain(self):
        data = self.samples([100] * 3, [80] * 3)
        for label, value in (("baseline", 100), ("candidate", 110)):
            for sample in data[label]:
                sample["another_case"] = value
        self.assertEqual(run.compare(data, .03, .02)["status"], "regression")

    def test_equal_timings_are_not_a_gain(self):
        self.assertEqual(run.compare(self.samples([100] * 3, [100] * 3), .03, .02)["status"],
                         "no_material_improvement")

    def test_missing_case_fails(self):
        data = self.samples([100] * 3, [80] * 3)
        data["candidate"][1] = {}
        with self.assertRaisesRegex(ValueError, "case sets differ"):
            run.compare(data, .03, .02)


class ReaderTests(unittest.TestCase):
    def read(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.json"
            path.write_text(json.dumps({"benchmarks": rows}))
            return run.read_cases(path, "cpu_time")[0]

    def row(self, **kwargs):
        return dict(name="shuffle_median", run_name="shuffle", aggregate_name="median",
                    cpu_time=100, time_unit="ns", **kwargs)

    def test_units(self):
        self.assertAlmostEqual(self.read([self.row()])["shuffle"], 1e-7)

    def test_no_results_fails(self):
        with self.assertRaisesRegex(ValueError, "no median"):
            self.read([])

    def test_error_in_non_median_also_fails(self):
        with self.assertRaisesRegex(ValueError, "benchmark failed"):
            self.read([self.row(), dict(name="shuffle_mean", error_occurred=True)])

    def test_duplicate_fails(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.read([self.row(), self.row()])

    def test_nonfinite_or_zero_fails(self):
        for value in (0, -1, float("nan"), float("inf")):
            row = self.row()
            row["cpu_time"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.read([row])


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fake = self.root / "benchmark"
        self.fake.write_text(f"#!{sys.executable}\n" + '''import json, sys
from pathlib import Path
args = dict(arg[2:].split("=", 1) for arg in sys.argv[1:])
Path(args["benchmark_out"]).write_text(json.dumps({"benchmarks": [{
    "name": "shuffle_median", "run_name": "shuffle", "aggregate_name": "median",
    "cpu_time": 100, "time_unit": "ns"}]}))
''')
        self.fake.chmod(0o755)
        self.job = dict(hypothesis="runner integration test", baseline_revision="test-base",
                        candidate_revision="test-candidate", baseline=str(self.fake), candidate=str(self.fake),
                        checks=[[sys.executable, "-c", "pass"]], runs=3, repetitions=2,
                        cpu=min(os.sched_getaffinity(0)))

    def test_full_run_retains_raw_data_and_provenance(self):
        out = self.root / "out"
        out.mkdir()
        report = run.experiment(self.job, out)
        self.assertEqual(report["status"], "no_material_improvement")
        self.assertEqual(len(list(out.glob("baseline-*.json"))), 3)
        self.assertEqual(len(list(out.glob("candidate-*.json"))), 3)
        self.assertIn("baseline", report["binaries"])
        self.assertEqual(json.loads((out / "report.json").read_text())["status"], report["status"])

    def test_failed_check_prevents_measurement(self):
        self.job["checks"] = [[sys.executable, "-c", "raise SystemExit(1)"]]
        out = self.root / "out"
        out.mkdir()
        with self.assertRaises(subprocess.CalledProcessError):
            run.experiment(self.job, out)
        self.assertFalse(list(out.glob("baseline-*.json")))
        self.assertEqual(json.loads((out / "report.json").read_text())["status"], "failed")

    def test_timeout_is_failure(self):
        self.job["timeout"] = 1
        self.job["checks"] = [[sys.executable, "-c", "import time; time.sleep(10)"]]
        out = self.root / "out"
        out.mkdir()
        with self.assertRaises(subprocess.TimeoutExpired):
            run.experiment(self.job, out)
        self.assertEqual(json.loads((out / "report.json").read_text())["status"], "failed")

    def test_timeout_stops_descendant_process(self):
        marker = self.root / "child.pid"
        code = ("import subprocess, sys, time; from pathlib import Path; "
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
                "Path(sys.argv[1]).write_text(str(child.pid)); time.sleep(60)")
        with self.assertRaises(subprocess.TimeoutExpired):
            run.command([sys.executable, "-c", code, str(marker)],
                        self.root / "timeout.log", 1, self.job["cpu"])
        child_pid = int(marker.read_text())
        for attempt in range(200):
            try:
                state = Path(f"/proc/{child_pid}/stat").read_text().split(") ", 1)[1][0]
            except FileNotFoundError:
                break
            if state in ("Z", "X"):
                break
            time.sleep(.01)
        else:
            self.fail("timed-out command left a running descendant")

    def test_missing_checks_rejected(self):
        self.job["checks"] = []
        with self.assertRaisesRegex(ValueError, "correctness check"):
            run.validate(self.job)

    def test_invalid_budget_rejected(self):
        self.job["min_gain"] = float("nan")
        with self.assertRaisesRegex(ValueError, "min_gain"):
            run.validate(self.job)


if __name__ == "__main__":
    unittest.main()
