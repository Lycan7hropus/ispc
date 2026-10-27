#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

"""Run a correctness-gated comparison of two existing ISPC benchmark binaries.

Usage: python3 scripts/builtins_lab/run.py job.json --output /tmp/experiment-001
See benchmarks/README.md for the job format and interpretation of results.
"""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import statistics
import subprocess
import sys
import tempfile


UNITS = {"ns": 1e-9, "us": 1e-6, "ms": 1e-3, "s": 1.0}


def read_cases(path, metric):
    """Reject incomplete results instead of silently comparing their intersection."""
    doc = json.loads(Path(path).read_text())
    cases = {}
    for row in doc["benchmarks"]:
        if row.get("error_occurred"):
            raise ValueError(f"benchmark failed: {row.get('name')}: {row.get('error_message')}")
        if row.get("aggregate_name") != "median":
            continue
        name = row.get("run_name", row["name"])
        value = row[metric] * UNITS[row["time_unit"]]
        if name in cases or not math.isfinite(value) or value <= 0:
            raise ValueError(f"duplicate or invalid measurement: {name}")
        cases[name] = value
    if not cases:
        raise ValueError("no median measurements; an empty filter is not a successful experiment")
    return cases, doc.get("context", {})


def compare(samples, min_gain, max_regression):
    expected = set(samples["baseline"][0])
    if not expected:
        raise ValueError("empty case set")
    for runs in samples.values():
        for run in runs:
            if set(run) != expected:
                raise ValueError("benchmark case sets differ between builds or processes")
    rows = []
    for name in sorted(expected):
        base = [r[name] for r in samples["baseline"]]
        candidate = [r[name] for r in samples["candidate"]]
        # These are observed ranges, not statistical confidence intervals.
        low = min(candidate) / max(base)
        high = max(candidate) / min(base)
        ratio = statistics.median(candidate) / statistics.median(base)
        if low > 1 + max_regression:
            status = "regression"
        elif high < 1 - min_gain:
            status = "improvement"
        elif low >= 1 - min_gain and high <= 1 + max_regression:
            status = "within_budget"
        else:
            status = "inconclusive"
        rows.append(dict(name=name, baseline_seconds=base, candidate_seconds=candidate,
                         median_ratio=ratio, observed_ratio_range=[low, high], status=status))
    states = {r["status"] for r in rows}
    if "regression" in states:
        status = "regression"
    elif "inconclusive" in states:
        status = "inconclusive"
    elif "improvement" in states:
        status = "candidate_for_confirmation"
    else:
        status = "no_material_improvement"
    return dict(status=status, cases=rows)


def stop_process_tree(root_pid):
    """Stop descendants before their parents, including separate sessions.

    Freeze each parent before discovering its children so compiler drivers
    cannot launch new work while cleanup walks /proc. Identify processes by
    start time as well as PID to avoid signaling a reused PID.
    """
    owned = []
    seen = set()

    def identity(pid):
        try:
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
            return fields[19]  # /proc stat field 22: starttime.
        except (FileNotFoundError, ProcessLookupError):
            return None

    def signal_owned(pid, started, signum):
        if started is None or pid == os.getpid() or identity(pid) != started:
            return
        try:
            os.kill(pid, signum)
        except ProcessLookupError:
            pass

    def visit(pid):
        if pid in seen or pid == os.getpid():
            return
        seen.add(pid)
        started = identity(pid)
        if started is None:
            return
        owned.append((pid, started))
        signal_owned(pid, started, signal.SIGSTOP)
        # Children may belong to any thread of a compiler/build process.
        try:
            tasks = list(Path(f"/proc/{pid}/task").iterdir())
        except (FileNotFoundError, ProcessLookupError):
            return
        for task in tasks:
            try:
                children = (task / "children").read_text().split()
            except (FileNotFoundError, ProcessLookupError):
                continue
            for child in children:
                visit(int(child))

    try:
        visit(root_pid)
    finally:
        # Kill children first while the stopped root still owns the tree.
        # Never signal any process group: nested helpers may share ours.
        for pid, started in reversed(owned):
            signal_owned(pid, started, signal.SIGKILL)


def execute(argv, output, timeout, *, cwd=None, env=None):
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise ValueError("commands must be nonempty arrays of strings")
    managed = os.environ.get("ISPC_BUILTINS_MANAGED_GROUP") == "1"
    process_env = dict(os.environ if env is None else env)
    process_env["ISPC_BUILTINS_MANAGED_GROUP"] = "1"

    def stop(process):
        try:
            if managed:
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    with output.open("w") as log:
        with subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                              cwd=cwd, env=process_env, start_new_session=not managed) as process:
            try:
                code = process.wait(timeout=timeout)
            except BaseException:
                stop_process_tree(process.pid)
                stop(process)
                process.wait()
                raise
            finally:
                # Helpers join the outer executor's group. Its owner also cleans
                # up remaining descendants if a helper exits early or fails.
                if not managed:
                    stop(process)
            if code:
                raise subprocess.CalledProcessError(code, process.args)


def command(argv, output, timeout, cpu):
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise ValueError("commands must be nonempty arrays of strings")
    execute(["taskset", "--cpu-list", str(cpu), *argv], output, timeout)


@contextmanager
def host_access(exclusive):
    path = Path(tempfile.gettempdir()) / f"ispc-builtins-host-{os.getuid()}.lock"
    with path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate(job):
    for key in ("hypothesis", "baseline_revision", "candidate_revision"):
        if not isinstance(job.get(key), str) or not job[key].strip():
            raise ValueError(f"{key} is required")
    if not isinstance(job.get("checks"), list) or not job["checks"]:
        raise ValueError("at least one correctness check command is required")
    for argv in job["checks"]:
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise ValueError("checks must contain nonempty command argument arrays")
    for key, default, minimum in (("runs", 5, 3), ("repetitions", 5, 2), ("timeout", 600, 1)):
        value = job.get(key, default)
        if type(value) is not int or value < minimum:
            raise ValueError(f"{key} must be an integer >= {minimum}")
    for key, default in (("min_gain", 0.03), ("max_regression", 0.02)):
        value = job.get(key, default)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value < 1:
            raise ValueError(f"{key} must be between 0 and 1")
    if type(job.get("cpu")) is not int or job["cpu"] not in os.sched_getaffinity(0):
        raise ValueError("cpu must name one CPU available to this process")
    if job.get("metric", "cpu_time") not in ("cpu_time", "real_time"):
        raise ValueError("metric must be cpu_time or real_time")
    if "expected_cases" in job:
        cases = job["expected_cases"]
        if (not isinstance(cases, list) or not cases or
                not all(isinstance(name, str) and name for name in cases) or
                len(set(cases)) != len(cases)):
            raise ValueError("expected_cases must be a nonempty list of unique names")
    for label in ("baseline", "candidate"):
        path = Path(job[label])
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(f"{label} must be an absolute executable path")


def experiment(job, out):
    validate(job)
    # A single host-wide queue for cooperating workers, including workers in other worktrees.
    lock_path = Path(tempfile.gettempdir()) / f"ispc-builtins-lab-{os.getuid()}.lock"
    with host_access(exclusive=True), lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        report = dict(status="failed", job=job, platform=platform.platform(),
                      affinity=sorted(os.sched_getaffinity(0)),
                      cpuinfo=Path("/proc/cpuinfo").read_text(),
                      binaries={label: sha256(Path(job[label])) for label in ("baseline", "candidate")})
        try:
            timeout, cpu = job.get("timeout", 600), job["cpu"]
            for i, argv in enumerate(job["checks"]):
                command(argv, out / f"check-{i}.log", timeout, cpu)
            samples = {"baseline": [], "candidate": []}
            contexts = {"baseline": [], "candidate": []}
            for i in range(job.get("runs", 5)):
                # Reverse order each round to balance systematic drift.
                order = ("baseline", "candidate") if i % 2 == 0 else ("candidate", "baseline")
                for label in order:
                    raw = out / f"{label}-{i}.json"
                    argv = [job[label], f"--benchmark_repetitions={job.get('repetitions', 5)}",
                            "--benchmark_report_aggregates_only=true", "--benchmark_out_format=json",
                            f"--benchmark_out={raw}"]
                    if job.get("filter"):
                        argv.append(f"--benchmark_filter={job['filter']}")
                    command(argv, out / f"{label}-{i}.log", timeout, cpu)
                    cases, context = read_cases(raw, job.get("metric", "cpu_time"))
                    if "expected_cases" in job and set(cases) != set(job["expected_cases"]):
                        raise ValueError("benchmark cases differ from the frozen inventory")
                    samples[label].append(cases)
                    contexts[label].append(context)
            for label in ("baseline", "candidate"):
                if sha256(Path(job[label])) != report["binaries"][label]:
                    raise ValueError(f"{label} binary changed during experiment")
            report.update(compare(samples, job.get("min_gain", 0.03), job.get("max_regression", 0.02)))
            report["benchmark_contexts"] = contexts
        except Exception as error:
            report["error"] = str(error)
            raise
        finally:
            (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="new directory; existing paths are rejected")
    args = parser.parse_args()
    try:
        job = json.loads(args.job.read_text())
        out = args.output.resolve()
        out.mkdir(parents=True, exist_ok=False)
        report = experiment(job, out)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"experiment failed: {error}", file=sys.stderr)
        return 1
    print(f"{report['status']}: {out / 'report.json'}")
    return 0 if report["status"] in ("candidate_for_confirmation", "no_material_improvement") else 2


if __name__ == "__main__":
    sys.exit(main())
