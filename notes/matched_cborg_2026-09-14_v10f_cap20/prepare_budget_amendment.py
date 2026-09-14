"""Preserve the unexecuted v10f instrument and amend only its approved budget."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / "matched_cborg_2026-09-14_v10f"
BASE_SHA = "93da075cb69c1850ba2451829323fe86086a0739864e66f68faf0300fd6f8232"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    original = PRIOR / "registration.json"
    assert sha(original) == BASE_SHA
    base = json.loads(original.read_bytes())
    assert not (PRIOR / "attempts").exists()
    assert not (PRIOR / "acceptances").exists()
    assert all(not Path(path).exists() for job in base["generation"]["jobs"]
               for path in job["output_directories"])
    prior_ledger = json.loads((PRIOR / "billing.json").read_bytes())
    checkpoint = json.loads(Path(base["budget"]["continuation"]["checkpoint"]).read_bytes())
    assert prior_ledger["requests"] == checkpoint["requests"]
    assert len(checkpoint["requests"]) == 17
    assert all(row["status"] == "settled" for row in checkpoint["requests"])
    assert sum(Decimal(row["cost_usd"]) for row in checkpoint["requests"]) == Decimal("12.67597200")
    caps_path = HERE / "approved_caps.json"
    caps = json.loads(caps_path.read_bytes())
    assert caps == {"CHORUS_api_rep1": 20, "CHORUS_agentic_rep1": 10,
                    "KIDS_FIRST_api_rep1": 15, "KIDS_FIRST_agentic_rep1": 15}
    authorization_path = HERE / "budget_authorization_2026-09-14.json"
    authorization = json.loads(authorization_path.read_bytes())
    assert authorization["base_registration_sha256"] == BASE_SHA
    assert authorization["approved_whole_attempt_caps_usd"] == caps
    assert base["budget"]["additional_usd"] == 200
    assert base["budget"]["per_attempt_usd"] == 5
    amended = deepcopy(base)
    amended["registered_at"] = authorization["recorded_at"]
    amended["budget"]["per_job_attempt_usd"] = caps
    amended["budget"]["ledger_path"] = str(HERE / "billing.json")
    amended["budget_amendment"] = {
        "base_registration": str(original), "base_registration_sha256": BASE_SHA,
        "authorization": str(authorization_path),
        "authorized_caps": str(caps_path),
        "scope": "One replacement CHORUS API attempt capped at $20; other canary caps remain $10/$15/$15. No automatic whole-attempt retry.",
        "instrument_unchanged": True,
        "prior_candidate": "Unexecuted $10 registration superseded for launch; all its original files remain unchanged.",
    }
    for path in (original, caps_path, authorization_path, Path(__file__)):
        amended["pinned_files"][str(path)] = sha(path)
    assert amended["generation"] == base["generation"]
    assert amended["evaluations"] == base["evaluations"]
    assert all(amended["pinned_files"][path] == pin for path, pin in base["pinned_files"].items())
    return amended


if __name__ == "__main__":
    result = build()
    with (HERE / "registration.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"registration_sha256": sha(HERE / "registration.json"),
                      "pinned_files": len(result["pinned_files"]),
                      "generation_instrument_changed": False,
                      "approved_canary_caps_usd": result["budget"]["per_job_attempt_usd"]}))
