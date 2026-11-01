#!/usr/bin/env python3
"""Isolate E3x x #5096 validation-harness failures, 2026-10-30.

Inputs: retained complete CI logs; outputs: individual pytest evidence and JSON
rerun index. Only reviewed local-process cases omit the optional network sandbox;
the common launcher still unsets provider keys. No providers or rating runs.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


GROUPS = (
    ("checkout", "ci-ordinary-6", "tests/test_preflight_resource_authority.py::", 3, True, False),
    ("process", "ci-ordinary-2", "tests/test_run_lock.py::TestAgainstARealProcess::", 2, False, False),
    ("native", "ci-native", "notes/matched_cborg_2026-09-13/native_controls/test_native_launch.py::", 27, False, True),
    ("audit", "ci-audit", "notes/matched_cborg_2026-09-13/audit_controls/test_history_control_lifecycle.py::", 1, True, True),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--canary", action="store_true")
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    root = Path(__file__).resolve().parents[2]
    plan = []
    for group, lane, prefix, count, sandbox, notes in GROUPS:
        nodes = re.findall(r"^(?:FAILED|ERROR) (.+)$", (evidence / (lane + ".log")).read_text(), re.M)
        assert len(nodes) == len(set(nodes)) == count, (lane, nodes)
        assert all(node.startswith(prefix) for node in nodes), (lane, nodes)
        for index, node in enumerate(nodes, 1):
            plan.append({"label": f"rerun-{group}-{index}", "original_lane": lane,
                         "node": node, "network_sandbox": sandbox, "notes_controls": notes})
    if args.canary:
        plan = plan[:1]
    else:
        # Independent reproduction of the macOS sandbox's ps restriction.
        results = []
        for sandbox in (True, False):
            command = ["/bin/ps", "-p", str(os.getpid()), "-o", "state="]
            if sandbox:
                command = ["/usr/bin/sandbox-exec", "-f", str(root / "scripts/adhoc/e3x_offline_20261029.sb"), *command]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            results.append({"network_sandbox": sandbox, "exit": result.returncode,
                            "stdout": result.stdout, "stderr": result.stderr})
        (evidence / "ps-sandbox-diagnostic.json").write_text(json.dumps(results, indent=2) + "\n")
    index_path = evidence / ("environment-canary.json" if args.canary else "environment-reruns.json")
    index_path.write_text(json.dumps(plan, indent=2) + "\n")
    failed = False
    for row in plan:
        status_path = evidence / (row["label"] + ".exit")
        if status_path.exists():
            row["exit"] = int(status_path.read_text())
            assert (evidence / (row["label"] + ".xml")).stat().st_size
        else:
            env = dict(os.environ, E3X_LOOPBACK_SANDBOX=str(int(row["network_sandbox"])),
                       E3X_NOTES_CONTROLS=str(int(row["notes_controls"])))
            result = subprocess.run(["bash", "scripts/adhoc/run_e3x_relocation_checks_20261029.sh",
                                     row["label"], str(evidence), "-q", row["node"]],
                                    cwd=root, env=env, check=False)
            row["exit"] = result.returncode
            assert status_path.exists() and int(status_path.read_text()) == result.returncode
        print(row["label"], row["exit"], row["node"], flush=True)
        failed |= row["exit"] != 0
        index_path.write_text(json.dumps(plan, indent=2) + "\n")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
