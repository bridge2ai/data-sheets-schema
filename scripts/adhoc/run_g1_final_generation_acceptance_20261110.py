"""Helper script to execute G1 final-generation acceptance checks with an external deadline.

Purpose: Run either the positive-only canary (--mode positive-canary) or the full
         G1 acceptance suite (--mode all) under an external process-group deadline,
         persisting generated full/Core/HTML/CSS artifacts and a JSON receipt under
         a durable scratch directory outside /tmp and outside repo notes/.
Inputs:  --mode {positive-canary,all}
         --work-dir <path>
         --evidence-json <path>
         --timeout-seconds <int>
Outputs: Persisted artifacts in --work-dir and JSON receipt at --evidence-json.
Issue:   #5798
Work unit: G1 (agy/final-generation-shapes-20261110)
Date:    2026-11-10
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
DEFAULT_SCRATCH_BASE = (
    REPO_ROOT.parent / "scratch-g1-final-generation-20261110" / "canary-2"
)
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _run_inner(mode: str, work_dir: Path, evidence_json: Path) -> int:
    from tests.test_final_generation_acceptance import (
        test_negative_shape_mutations_fail_for_exact_field,
        test_positive_full_to_core_pair_and_html_acceptance,
    )

    work_dir.mkdir(parents=True, exist_ok=True)
    checks_passed = ["test_positive_full_to_core_pair_and_html_acceptance"]
    test_positive_full_to_core_pair_and_html_acceptance(work_dir)
    if mode == "all":
        test_negative_shape_mutations_fail_for_exact_field()
        checks_passed.append("test_negative_shape_mutations_fail_for_exact_field")

    base_evidence = json.loads(
        (work_dir / "g1_acceptance_evidence.json").read_text(encoding="utf-8")
    )
    base_evidence["work_unit"] = "G1"
    base_evidence["mode"] = mode
    base_evidence["checks_passed"] = checks_passed
    evidence_json.parent.mkdir(parents=True, exist_ok=True)
    evidence_json.write_text(
        json.dumps(base_evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(base_evidence, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("positive-canary", "all"),
        default="positive-canary",
        help="Select positive-only canary or full G1 suite (positive + 4 negatives).",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=DEFAULT_SCRATCH_BASE / "work",
        help="Durable directory where full YAML, Core YAML, and rendered HTML/CSS are written.",
    )
    parser.add_argument(
        "--evidence-json",
        type=Path,
        default=DEFAULT_SCRATCH_BASE / "g1_canary_evidence.json",
        help="Durable output JSON file path for persisted G1 evidence receipt.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="External process-group deadline in seconds (default: 30).",
    )
    parser.add_argument(
        "--_inner",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    work_dir = args.work_dir.resolve()
    evidence_json = args.evidence_json.resolve()
    if args._inner:
        return _run_inner(args.mode, work_dir, evidence_json)

    if evidence_json.exists() or (work_dir.exists() and any(work_dir.iterdir())):
        raise SystemExit(
            f"Refusing to overwrite retained G1 evidence in {work_dir} or {evidence_json}"
        )

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join([str(SRC_ROOT), str(REPO_ROOT)])
    cmd = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--_inner",
        "--mode",
        args.mode,
        "--work-dir",
        str(work_dir),
        "--evidence-json",
        str(evidence_json),
    ]
    start = time.monotonic()
    child = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = child.communicate(timeout=args.timeout_seconds)
        code = child.returncode
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate()
        code = 124
    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    if code != 0:
        fail_meta = evidence_json.with_suffix(".failed.json")
        fail_meta.parent.mkdir(parents=True, exist_ok=True)
        fail_meta.write_text(
            json.dumps(
                {
                    "work_unit": "G1",
                    "mode": args.mode,
                    "exit_code": code,
                    "elapsed_seconds": round(time.monotonic() - start, 3),
                    "timeout_seconds": args.timeout_seconds,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
