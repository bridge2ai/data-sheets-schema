"""Archive P4/#4354 idle-only evidence, 2026-10-27 UTC.

Inputs: the two completed idle-check directories from the 2026-10-27 queue.
Outputs: exclusive lossless tar.gz archives, per-file hashes and a small summary.
No imports of production code, measurement, tests, network or input mutation.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import stat
import tarfile


ROOT = Path(__file__).resolve().parents[2]
SOURCE_HEAD = "01969cbed8eed93f420c640c1f1c306e5f58b033"
INPUT_PARENT = Path("/private/tmp/d4d-recorder-measurements-20261026")
NAMES = ("idle-check-20261027-queue", "idle-check-20261027-queue-ps")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def snapshot(directory: Path) -> dict[str, bytes]:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"input is not a physical directory: {directory}")
    result = {}
    for path in sorted(directory.rglob("*")):
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(f"unsupported input entry: {path}")
        result[path.relative_to(directory).as_posix()] = path.read_bytes()
    return result


def write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def archive(directory: Path, output: Path, *, completed: bool) -> dict:
    files = snapshot(directory)
    expected = {"host.jsonl", "outcome.json", "plan.json", "source-before.json", "source-after.json"}
    if completed:
        expected.add("idle-decision.json")
    if set(files) != expected:
        raise ValueError(f"unexpected completed evidence roster: {directory}: {sorted(files)}")
    plan = json.loads(files["plan.json"])
    outcome = json.loads(files["outcome.json"])
    before = json.loads(files["source-before.json"])
    if (plan["idle_only"] is not True or plan["idle_window_seconds"] != 60
            or outcome["source_unchanged"] is not True
            or files["source-before.json"] != files["source-after.json"]
            or before["head"] != SOURCE_HEAD or outcome["returncode"] is not None
            or "child_pid" in outcome):
        raise ValueError(f"idle-only/source preservation authority mismatch: {directory}")
    driver = ROOT / "scripts/adhoc/native_recorder_measure_20261026.py"
    if plan["helper"]["sha256"] != sha(driver.read_bytes()):
        raise ValueError("recorded measurement driver differs from this tooling checkout")
    samples = [json.loads(line) for line in files["host.jsonl"].splitlines()]
    summary = {"original_directory": str(directory), "outcome": outcome,
               "started_at": plan["started_at"], "idle_only": True,
               "source_head": before["head"], "source_tree": before["tree"],
               "measurement_driver": plan["helper"], "host_samples": len(samples),
               "source_before_after_byte_identical": True,
               "recorder_pytest_launched": False}
    if completed:
        decision = json.loads(files["idle-decision.json"])
        measured = {"mean_cpu_percent": sum(row["cpu_percent"] for row in samples) / len(samples),
                    "peak_cpu_percent": max(row["cpu_percent"] for row in samples),
                    "max_one_minute_load_per_cpu": max(row["load"][0] / row["logical_cpus"] for row in samples)}
        if (len(samples) != 60 or decision["samples"] != 60 or decision["idle"] is not False
                or outcome["status"] != "blocked_host_busy"
                or any(row["stage"] != "before" for row in samples)
                or any(not math.isclose(value, decision[key], abs_tol=1e-10, rel_tol=0)
                       for key, value in measured.items())):
            raise ValueError("completed idle decision does not match its retained host samples")
        summary["decision"] = {key: decision[key] for key in (
            "idle", "samples", "mean_cpu_percent", "peak_cpu_percent",
            "max_one_minute_load_per_cpu", "thresholds", "scope")}
        summary["decision"]["competing_process_observation_count"] = len(
            decision["competing_process_observations"])
        summary["decision"]["process_inventory_scope"] = (
            "Full recorded observations remain in the archive; process identities are not causal attribution.")
    elif (samples or outcome["status"] != "measurement_error"
          or outcome["error"] != "PermissionError: [Errno 1] Operation not permitted: 'ps'"):
        raise ValueError("first attempt is not the recorded pre-sampling ps permission refusal")

    destination = output / (directory.name + ".tar.gz")
    with destination.open("xb") as target:
        with gzip.GzipFile(fileobj=target, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as bundle:
                for name, raw in files.items():
                    info = bundle.gettarinfo(str(directory / name), arcname=name)
                    bundle.addfile(info, io.BytesIO(raw))
    with tarfile.open(destination, "r:gz") as bundle:
        members = bundle.getmembers()
        if len(members) != len(files) or {member.name for member in members} != set(files):
            raise ValueError("archive member roster changed")
        for member in members:
            if not member.isfile() or bundle.extractfile(member).read() != files[member.name]:
                raise ValueError("archive member bytes changed: " + member.name)
    if snapshot(directory) != files:
        raise ValueError("input evidence changed while archiving")
    summary["archive"] = {"path": destination.name, "bytes": destination.stat().st_size,
                          "sha256": sha(destination.read_bytes()), "all_member_bytes_verified": True}
    summary["files"] = {name: {"bytes": len(raw), "sha256": sha(raw)} for name, raw in files.items()}
    summary["original_inputs_rechecked_unchanged"] = True
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.relative_to(ROOT / "notes")
    output.mkdir(parents=True, exist_ok=False)
    rows = [archive(INPUT_PARENT / name, output, completed=number == 1)
            for number, name in enumerate(NAMES)]
    document = {
        "format": "native_recorder_idle_archive_v1", "date_utc": "2026-10-27",
        "purpose": "P4/#4354 preservation of two idle-only gate attempts, not timeout diagnosis",
        "archive_helper": {"path": str(Path(__file__).resolve()),
                           "sha256": sha(Path(__file__).read_bytes())},
        "attempts": rows, "recorder_trials_launched": 0,
        "decision": "defer three uninstrumented trials and paired diagnosis until the declared quiet-host gate passes",
        "limits": ["No recorder runtime was measured.", "No timeout causality is inferred.",
                   "The source comparison concerns the saved before/after inventories, not a new runtime attestation.",
                   "Process exclusion decisions are retained from the driver, not independently recomputed by this archiver.",
                   "Scientific acceptance was not assessed."],
    }
    write_json(output / "summary.json", document)
    print(json.dumps({"output": str(output), "archives": [row["archive"] for row in rows],
                      "recorder_trials_launched": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
