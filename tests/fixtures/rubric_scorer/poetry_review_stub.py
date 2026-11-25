# Real-validator mutation control for PR 6340 issues 6345 and 6347, 2026-11-25.
# Inputs: synthetic case and exact validator argv. Outputs: accepted byte snapshot,
# real validator result and optional post-validation candidate replacement.
# This executable never launches Codex or reads real credentials.
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    if sys.argv[1:3] != ["run", "python"]:
        raise ValueError("unexpected Poetry test argv")
    directory = Path(__file__).parent
    case = json.loads((directory / "case.json").read_bytes())
    candidate = Path(sys.argv[sys.argv.index("--file") + 1])
    before = candidate.read_bytes()
    (directory / "validated-snapshot.json").write_bytes(before)
    command = [sys.executable, *sys.argv[3:]]
    result = subprocess.run(command, capture_output=True, timeout=120)
    sys.stdout.buffer.write(result.stdout)
    sys.stderr.buffer.write(result.stderr)
    if result.returncode == 0 and case.get("post_validator_drift"):
        candidate.write_bytes(b"THIS IS SYNTHETIC POST-VALIDATION DRIFT, NOT JSON\n")
    (directory / "real-validator-result.json").write_text(json.dumps({
        "argv": command, "returncode": result.returncode,
        "accepted_snapshot_sha256": hashlib.sha256(before).hexdigest(),
        "candidate_after_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "post_validation_drift_applied": candidate.read_bytes() != before,
        "copied_auth_present_at_validation": (candidate.parent / "codex-home/auth.json").exists(),
    }, indent=2) + "\n")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
