"""Purpose: causal guard-removal checks for E3x re-review R3, 2026-10-29.

Inputs: this real checkout, --only guard IDs, external --basetemp and --output.
Outputs: per-guard pytest logs and JSON; restores each source byte-for-byte.
Offline, serial, synthetic evaluators only. Run one canary before the other five.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

AUDIT = "scripts/audit_evaluation_comparability.py"
PACK = "src/data_sheets_schema/evaluation/blind_review_pack.py"
TESTS = "tests/test_e3x_rereview_kills.py"
MUTANTS = {
    "N6": (AUDIT, 'require(rating.get("files") == attempt.get("files") ==',
           'require(True or rating.get("files") == attempt.get("files") =='),
    "N6b": (AUDIT, 'require(attempt.get("files") == names and set(names)',
            'require(True or attempt.get("files") == names and set(names)'),
    "N10": (AUDIT, 'require(mapping(blinding).get("dumper_class") == emitter["dumper_class"],',
            'require(True,'),
    "N18": (PACK, 'forbidden.update((declaration["comparison_arm"], declaration["condition"],',
            '(lambda *a: None)((declaration["comparison_arm"], declaration["condition"],'),
    "N19": (PACK, 'metadata_ids.discard(record.input_arm)', 'pass'),
    "N24": (AUDIT, 'require(receipt.get("format") == runner.RECEIPT_FORMAT,', 'require(True,'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", choices=MUTANTS, required=True)
    parser.add_argument("--basetemp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.basetemp.resolve().is_relative_to(root):
        parser.error("pytest basetemp must be outside the checkout")
    env = {k: v for k, v in os.environ.items() if k not in
           ("ANTHROPIC_API_KEY", "CBORG_API_KEY", "OPENAI_API_KEY")}
    env.update(PYTHONPATH=str(root / "src"), PYTHONDONTWRITEBYTECODE="1")
    args.basetemp.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for name in args.only:
        filename, old, new = MUTANTS[name]
        path = root / filename
        original = path.read_bytes()
        assert original.decode().count(old) == 1, name
        try:
            path.write_bytes(original.decode().replace(old, new).encode())
            env["PYTHONPYCACHEPREFIX"] = str(args.basetemp / "cache" / name)
            proc = subprocess.run([sys.executable, "-m", "pytest", TESTS,
                "-k", f"test_kill_{name}_", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
                "--basetemp=" + str(args.basetemp / name)], cwd=root, env=env,
                capture_output=True, text=True)
            log = args.output.with_name(args.output.stem + "-" + name + ".log")
            log.write_text(proc.stdout + proc.stderr)
            killed = proc.returncode == 1 and f"FAILED {TESTS}::test_kill_{name}_" in proc.stdout
            results.append({"guard": name, "killed": killed, "exit_code": proc.returncode, "log": str(log)})
        finally:
            path.write_bytes(original)
            assert path.read_bytes() == original
        args.output.write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps(results[-1]), flush=True)
    return 0 if all(row["killed"] for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
