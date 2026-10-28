#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Short real-caller T1 probe of trusted, hash-pinned existing binaries."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import sys
import time

import run as runner


SIDES = ("baseline", "candidate")
ORDER = (SIDES, tuple(reversed(SIDES)), SIDES)
LIMITATIONS = [
    "Exploratory T1 only; no patch acceptance or statistical confidence claim.",
    "Three short pairs do not establish a 2% regression bound.",
    "Coverage and independent oracle adequacy require coordinator review of the pinned job.",
    "Reuses prepared binaries; candidate preparation/build costs are outside this run.",
    "A selected panel is not independent confirmation of earlier results.",
]


def identity(item):
    if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
        raise ValueError("identity requires exactly path and sha256")
    if not isinstance(item["path"], str) or not Path(item["path"]).is_absolute():
        raise ValueError("identity path must be absolute")
    if not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
        raise ValueError("invalid sha256")
    path = Path(item["path"]).resolve(strict=True)
    if not path.is_file():
        raise ValueError("identity must name a regular file")
    return dict(path=str(path), sha256=item["sha256"])


def validate(job):
    keys = {"schema", "hypothesis", *SIDES, "checks", "cases", "provenance"}
    if not isinstance(job, dict) or set(job) != keys or type(job["schema"]) is not int or job["schema"] != 1:
        raise ValueError("unsupported trusted job schema")
    if not isinstance(job["hypothesis"], str) or not job["hypothesis"].strip():
        raise ValueError("hypothesis required")
    cases = job["cases"]
    if (not isinstance(cases, list) or not cases or
            any(not isinstance(c, str) or not c.strip() or "\n" in c or "\r" in c for c in cases) or
            len(set(cases)) != len(cases)):
        raise ValueError("cases must be nonempty unique benchmark names")
    result = dict(job)
    for side in SIDES:
        result[side] = identity(job[side])
    for key in ("checks", "provenance"):
        if not isinstance(job[key], list) or not job[key]:
            raise ValueError(f"nonempty {key} required")
        result[key] = [identity(i) for i in job[key]]
    for item in [result[s] for s in SIDES] + result["checks"]:
        if not os.access(item["path"], os.X_OK):
            raise ValueError("runtime input is not executable")
    return result


def check_deadline(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError("stage deadline reached")


def verify(items, deadline=None):
    for item in items:
        digest = hashlib.sha256()
        with Path(item["path"]).open("rb") as stream:
            while True:
                check_deadline(deadline)
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        check_deadline(deadline)
        if digest.hexdigest() != item["sha256"]:
            raise ValueError(f"identity changed: {item['path']}")


def read_iterations(path, expected):
    document = json.loads(Path(path).read_text())
    rows = document.get("benchmarks")
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise ValueError("wrong benchmark row count")
    result = {}
    for row in rows:
        if (not isinstance(row, dict) or row.get("error_occurred") or
                row.get("run_type", "iteration") != "iteration"):
            raise ValueError("failed or non-iteration benchmark row")
        name, value, unit = row.get("name"), row.get("cpu_time"), row.get("time_unit")
        if not isinstance(name, str) or name not in expected or name in result:
            raise ValueError("duplicate or unexpected benchmark")
        if (type(value) not in (int, float) or not math.isfinite(value) or value <= 0 or
                unit not in runner.UNITS):
            raise ValueError("invalid benchmark time")
        seconds = value * runner.UNITS[unit]
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("invalid normalized time")
        result[name] = seconds
    if set(result) != set(expected):
        raise ValueError("benchmark inventory mismatch")
    return result


def probe(job_path, expected_hash, output, cpu):
    started = time.monotonic()
    # Never overwrite an earlier trial, even one that failed before preflight.
    output.mkdir(parents=True, exist_ok=False)
    report = dict(schema=1, level="T1", status="invalid_input", accepted=False,
                  build_seconds=0, binaries_reused=True, limitations=LIMITATIONS, commands=[])
    stage = "input"
    try:
        if type(cpu) is not int or cpu not in os.sched_getaffinity(0):
            raise ValueError("CPU unavailable")
        original = identity(dict(path=str(job_path), sha256=expected_hash))
        job_bytes = job_path.read_bytes()
        if hashlib.sha256(job_bytes).hexdigest() != original["sha256"]:
            raise ValueError("job hash mismatch")
        job = validate(json.loads(job_bytes))
        taskset = Path(shutil.which("taskset") or "missing-taskset").resolve(strict=True)
        inputs = ([original, *[job[s] for s in SIDES], *job["checks"], *job["provenance"]] +
                  [dict(path=str(p), sha256=runner.sha256(p)) for p in
                   (Path(__file__).resolve(), Path(runner.__file__).resolve(), Path(sys.executable).resolve(), taskset)])
        # A typo must not redirect output into an input or overwrite retained evidence.
        for item in inputs:
            if Path(item["path"]).is_relative_to(output.resolve()):
                raise ValueError("output contains an input")
        (output / "job.json").write_bytes(job_bytes)
        pattern = "^(" + "|".join(re.escape(c) for c in job["cases"]) + ")$"
        protocol = dict(schema=1, level="T1", trusted_coordinator_job=job,
                        inputs=inputs, cpu=cpu, pairs=3, order=ORDER, filter=pattern,
                        min_time_seconds=0.01, repetitions=1, metric="cpu_time",
                        limits_seconds=dict(queue=30, active=60, preflight=30, measurement=15, process=10),
                        limitations=LIMITATIONS)
        (output / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
        protocol_identity = dict(path=str((output / "protocol.json").resolve()),
                                 sha256=runner.sha256(output / "protocol.json"))
        inputs.append(protocol_identity)
        report["protocol_sha256"] = protocol_identity["sha256"]
        report["setup_seconds"] = time.monotonic() - started
        stage = "queue"
        queued = time.monotonic()
        with runner.host_access(exclusive=True, deadline=queued + 30):
            report["queue_seconds"] = time.monotonic() - queued
            active_end = time.monotonic() + 60
            stage = "preflight"
            stage_start = time.monotonic()
            stage_end = min(active_end, stage_start + 30)
            verify(inputs, stage_end)

            def execute(label, argv):
                remaining = min(10, stage_end - time.monotonic())
                if remaining <= 0:
                    raise TimeoutError("stage deadline reached")
                entry = dict(label=label, argv=[str(taskset), "--cpu-list", str(cpu), *argv],
                             started_seconds=time.monotonic() - started, timeout_seconds=remaining)
                report["commands"].append(entry)
                try:
                    runner.execute(entry["argv"], output / (label + ".log"), remaining)
                finally:
                    entry["elapsed_seconds"] = time.monotonic() - started - entry["started_seconds"]

            for i, check in enumerate(job["checks"]):
                execute(f"oracle-{i}", [check["path"]])
            for side in SIDES:
                execute(f"inventory-{side}", [job[side]["path"], "--benchmark_list_tests=true",
                                             "--benchmark_filter=" + pattern])
                listed = [v.strip() for v in (output / f"inventory-{side}.log").read_text().splitlines() if v.strip()]
                if len(listed) != len(job["cases"]) or set(listed) != set(job["cases"]):
                    raise ValueError("preflight benchmark inventory mismatch")
                check_deadline(stage_end)
            report["preflight_seconds"] = time.monotonic() - stage_start
            report["inventories_verified_before_timing"] = True
            stage = "measurement"
            stage_start = time.monotonic()
            stage_end = min(active_end, stage_start + 15)
            parsed = []
            for pair, order in enumerate(ORDER):
                samples = {}
                for side in order:
                    label = f"pair-{pair}-{side}"
                    raw = output / (label + ".json")
                    execute(label, [job[side]["path"], "--benchmark_filter=" + pattern,
                                    "--benchmark_min_time=0.01s", "--benchmark_repetitions=1",
                                    "--benchmark_out_format=json", "--benchmark_out=" + str(raw)])
                    samples[side] = read_iterations(raw, job["cases"])
                    check_deadline(stage_end)
                parsed.append(samples)
            report["measurement_seconds"] = time.monotonic() - stage_start
            stage = "final_identity"
            verify(inputs, active_end)
            report["cases"] = []
            for name in job["cases"]:
                pairs = [dict(pair=i, order=ORDER[i], baseline_seconds=p["baseline"][name],
                              candidate_seconds=p["candidate"][name],
                              ratio=p["candidate"][name] / p["baseline"][name]) for i, p in enumerate(parsed)]
                ratios = [p["ratio"] for p in pairs]
                if not all(math.isfinite(v) and v > 0 for v in ratios):
                    raise ValueError("invalid paired ratio")
                report["cases"].append(dict(name=name, pairs=pairs, median_ratio=statistics.median(ratios),
                                            observed_ratio_range=[min(ratios), max(ratios)]))
            check_deadline(active_end)
            report["status"] = "focused_panel_complete_not_accepted"
    except Exception as error:
        report.update(status="failed", failure=dict(stage=stage, type=type(error).__name__, message=str(error)))
    finally:
        report["total_seconds"] = time.monotonic() - started
        (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("--job-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cpu", type=int, required=True)
    args = parser.parse_args()
    if not args.job.is_absolute() or not args.output.is_absolute():
        parser.error("job and output must be absolute paths")
    report = probe(args.job, args.job_sha256, args.output, args.cpu)
    print(json.dumps(dict(status=report["status"], accepted=False, report=str(args.output / "report.json"))))
    return 0 if report["status"] == "focused_panel_complete_not_accepted" else 1


if __name__ == "__main__":
    sys.exit(main())
