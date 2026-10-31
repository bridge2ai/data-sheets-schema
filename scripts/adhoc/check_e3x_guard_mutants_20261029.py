"""F10, 2026-10-29: verify causal guard tests by removing one guard at a time.

Inputs: current checkout, --only IDs, --output JSON, --basetemp outside checkout.
Outputs: per-mutant pytest logs and killed/survived JSON. Offline and serial;
restore exact source bytes in finally. Run only in the owned idle worktree.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

AUDIT = "scripts/audit_evaluation_comparability.py"
PACK = "src/data_sheets_schema/evaluation/blind_review_pack.py"
MUTANTS = {
    "I2": (AUDIT, 'require(accepted == doc, "registered_transcript_evaluation_mismatch")',
           'require(True, "registered_transcript_evaluation_mismatch")'),
    "I4": (AUDIT, 'require(rating.get("session_id") == session and session not in sessions,',
           'require(rating.get("session_id") == session,'),
    "I5": (AUDIT, 'require(prior.get("registration") == {"sha256": sha(generation_raw),\n                "raw_json": generation_raw.decode()}, "registered_provenance_registration_mismatch")',
           'require(True, "registered_provenance_registration_mismatch")'),
    "I12": (AUDIT, '                    and str(cost) == str(rating.get("estimated_cost_usd"))\n                    and str(cost) == str(attempt.get("estimated_cost_usd")), "registered_rating_receipt_mismatch")',
            ', "registered_rating_receipt_mismatch")'),
    "I17": (AUDIT, 'require(plan.get("format") == runner.FORMAT and runner.shared.canonical(plan) == manifest_raw,',
            'require(plan.get("format") == runner.FORMAT,'),
    "I20": (AUDIT, 'require(len(ratings) == plan["repeat_count"], "registered_validated_panel_incomplete")',
            'require(True, "registered_validated_panel_incomplete")'),
    "I21": (AUDIT, 'require(rating.get("status") == attempt.get("status") == "validated"\n                    and type(attempt.get("exit_code")) is int and attempt["exit_code"] == 0,',
            'require(rating.get("status") == attempt.get("status") == "validated",'),
    "I25": (AUDIT, 'require(plan.get("execution_mode") == "isolated_no_tools_controller_validation",\n                "registered_execution_mode_unsupported")',
            'require(True, "registered_execution_mode_unsupported")'),
    "I28": (AUDIT, 'elif context != contexts[run["project"]]:\n                reasons.append("applicability_context_differs_from_target")',
            'elif False:\n                pass'),
    "I29": (AUDIT, 'elif runtime.get("canonical_model") != evaluator_model:\n                reasons.append("evaluator_differs_from_target")',
            'elif False:\n                pass'),
    "B4": (PACK, '    identifiers.update((record.arm, record.label, str(record.source_path)))\n', ''),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", choices=list(MUTANTS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--basetemp", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.basetemp.resolve().is_relative_to(root):
        parser.error("pytest basetemp must be outside the checkout")
    env = {k: v for k, v in os.environ.items() if k not in
           ("ANTHROPIC_API_KEY", "CBORG_API_KEY", "OPENAI_API_KEY")}
    env.update(PYTHONPATH=str(root / "src"), PYTHONDONTWRITEBYTECODE="1")
    results = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.basetemp.mkdir(parents=True, exist_ok=True)
    for name in args.only:
        filename, old, new = MUTANTS[name]
        path = root / filename
        original = path.read_bytes()
        assert original.decode().count(old) == 1, name
        try:
            path.write_bytes(original.decode().replace(old, new).encode())
            env["PYTHONPYCACHEPREFIX"] = str(args.basetemp / "cache" / name)
            command = [sys.executable, "-m", "pytest", "tests/test_e3x_guard_kills.py",
                       "-k", f"test_kill_{name}_", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
                       "--basetemp=" + str(args.basetemp / name)]
            proc = subprocess.run(command, cwd=root, env=env, text=True, capture_output=True)
            log = args.output.with_name(args.output.stem + "-" + name + ".log")
            log.write_text(proc.stdout + proc.stderr)
            killed = proc.returncode == 1 and f"FAILED tests/test_e3x_guard_kills.py::test_kill_{name}_" in proc.stdout
            results.append({"guard": name, "killed": killed, "exit_code": proc.returncode, "log": str(log)})
        finally:
            path.write_bytes(original)
            assert path.read_bytes() == original
        args.output.write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps(results[-1]), flush=True)
    return 0 if all(r["killed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
