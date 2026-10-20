"""Profile existing offline native acceptance tests for #4354/#4728 (2026-10-20).

Inputs: an explicitly allowlisted pytest node and this checkout's source.
Outputs: cProfile data, sorted statistics and CPU/wall/load metadata in a fresh
external evidence directory. Profiling timings are diagnostic, not acceptance.
No provider, native binary or test implementation is substituted by this helper.
"""
from __future__ import annotations

import argparse
import cProfile
import hashlib
import json
import os
from pathlib import Path
import pstats
import resource
import subprocess
import sys
import time


NODES = {
    "phase": "tests/test_native_shared_phase_replay.py::test_actual_phase_matches_original_with_fewer_real_reconstructions",
    "initial": "tests/test_native_shared_initial_receipts.py::test_initial_success_uses_only_captured_authority_and_has_no_final_claim",
    "neutral": "tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion",
    "omission": "tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses",
}


def source_state():
    """Bind both tracked edits and newly added source/tests in a shared lane."""
    diff = subprocess.check_output(["git", "diff", "--binary", "HEAD", "--", "src", "tests"])
    names = subprocess.check_output([
        "git", "ls-files", "--others", "--exclude-standard", "-z", "--", "src", "tests"
    ]).decode().split("\0")
    return {
        "tracked_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "has_tracked_changes": bool(diff),
        "untracked_sha256": {
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in names if name
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=NODES)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if Path.cwd().resolve() != root:
        parser.error("run from this helper's checkout root")
    output = args.output.resolve()
    if output == root or root in output.parents:
        parser.error("evidence output must be outside the checkout")
    output.mkdir(parents=True, exist_ok=False)
    import data_sheets_schema.native_shared_capture as capture
    if root / "src" not in Path(capture.__file__).resolve().parents:
        parser.error("native source imported from another checkout")
    import pytest
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    source_before = source_state()
    before = [resource.getrusage(kind) for kind in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
    load_before = os.getloadavg()
    started = time.perf_counter()
    profile = cProfile.Profile()
    profile.enable()
    try:
        code = pytest.main(["-q", "-p", "no:cacheprovider",
                            "--basetemp", str(output / "cases"), NODES[args.case]])
    finally:
        profile.disable()
        elapsed = time.perf_counter() - started
        after = [resource.getrusage(kind) for kind in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
        profile.dump_stats(output / "profile.pstats")
        with (output / "profile.txt").open("w") as stream:
            pstats.Stats(profile, stream=stream).sort_stats("cumulative").print_stats(100)
        cpu = [b.ru_utime + b.ru_stime - a.ru_utime - a.ru_stime
               for a, b in zip(before, after)]
        source_after = source_state()
        summary = {
            "case": args.case, "node": NODES[args.case], "head": head,
            "source_before": source_before, "source_after": source_after,
            "source_unchanged": source_before == source_after,
            "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "wall_seconds": elapsed,
            "cpu_self_seconds": cpu[0], "cpu_child_seconds": cpu[1],
            "load_before": load_before, "load_after": os.getloadavg(),
            "python": sys.version, "pytest_rc": int(code) if "code" in locals() else None,
            "timing_scope": "cProfile-instrumented parent pytest process; child CPU included separately",
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary), flush=True)
    return int(code) if source_before == source_after else 2


if __name__ == "__main__":
    raise SystemExit(main())
