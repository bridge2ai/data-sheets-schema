"""Launch one explicitly reviewed API generation canary, never a batch."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess

from budgeted_cborg import BudgetStop, CappedClient, open_ledger, attempt_identity, write_new
from prepare_registration import spec_for

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(manifest, path, expected_sha):
    if Path.cwd().resolve() != Path(manifest["repository"]).resolve():
        raise BudgetStop("working directory differs from the registered repository")
    if sha(path) != expected_sha:
        raise BudgetStop("registration changed")
    changed = [p for p, h in manifest["pinned_files"].items() if not Path(p).is_file() or sha(p) != h]
    if changed:
        raise BudgetStop(f"registered input or instrument changed: {changed[:5]}")
    if sys.executable != manifest["python"] or sys.version != manifest["python_version"]:
        raise BudgetStop("Python runtime changed")
    from data_sheets_schema import api_runner
    expected_module = Path(manifest["repository"]) / "src/data_sheets_schema/api_runner.py"
    if Path(api_runner.__file__).resolve() != expected_module.resolve():
        raise BudgetStop("generation implementation was imported from another checkout or install")


def verify_history(manifest):
    path = Path(manifest["preservation_inventory"])
    if sha(path) != manifest["preservation_inventory_sha256"]:
        raise BudgetStop("historical inventory changed")
    inventory = json.loads(path.read_bytes())
    root = Path(inventory["source_root"])
    changed = [rel for rel, pin in inventory["preservation_files"].items()
               if not (root / rel).is_file() or sha(root / rel) != pin["sha256"]]
    if changed:
        raise BudgetStop(f"historical source artifacts changed: {changed[:5]}")
    for item in manifest.get("prior_attempt_artifacts", []):
        if not Path(item["path"]).is_file() or sha(item["path"]) != item["sha256"]:
            raise BudgetStop("a preserved prior-canary artifact changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", type=Path, default=HERE / "registration.json")
    parser.add_argument("--job", required=True)
    parser.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()
    here = args.registration.resolve().parent
    manifest = json.loads(args.registration.read_bytes())
    if manifest.get("generation", {}).get("external_canary", {}).get("status") != "registered":
        raise BudgetStop("external source registration is incomplete; no canary launch")
    manifest_sha = sha(args.registration)
    review = json.loads(args.review.read_bytes())
    if (review.get("registration_sha256") != manifest_sha or review.get("verdict") != "approve"
            or review.get("ci_conclusion") != "success" or args.job not in review.get("allowed_jobs", [])):
        raise BudgetStop("this exact registration and canary job require passed preflight review and CI")
    job = next(j for j in manifest["generation"]["jobs"] if j["id"] == args.job)
    if not job["canary"] or job["execution_arm"] != "api":
        raise BudgetStop("this entry point only launches API generation canaries")
    order = manifest["generation"]["canary_order"]
    for previous in order[:order.index(args.job)]:
        acceptance = here / "acceptances" / f"{previous}.json"
        if not acceptance.exists():
            raise BudgetStop(f"earlier canary needs independent acceptance: {previous}")
        value = json.loads(acceptance.read_bytes())
        if value.get("registration_sha256") != manifest_sha or value.get("verdict") != "accept":
            raise BudgetStop("prior canary acceptance does not match this condition")
        if not value.get("artifacts") or any(not Path(p).is_file() or sha(p) != h for p, h in value["artifacts"].items()):
            raise BudgetStop("prior canary acceptance lacks unchanged original artifacts")
    verify(manifest, args.registration, manifest_sha)
    verify_history(manifest)
    if any(Path(p).exists() for p in job["output_directories"]):
        raise BudgetStop("attempt output directory already exists; never overwrite or automatically resume")
    attempt = here / "attempts" / job["id"]
    attempt.mkdir(parents=True, exist_ok=False)
    # Metadata and the actual client must agree: api_runner otherwise gives
    # inherited direct Anthropic credentials precedence over CBORG.
    key = os.environ.get("CBORG_API_KEY")
    if not key:
        raise BudgetStop("CBORG_API_KEY is required; provider fallback is prohibited")
    for name in list(os.environ):
        if name.startswith("ANTHROPIC_") or name in {"D4D_PROFILE", "D4D_MANIFEST"}:
            os.environ.pop(name)
    from data_sheets_schema import api_runner
    import anthropic
    api_runner.MAX_ATTEMPTS = manifest["generation"]["api_max_attempts"]
    if api_runner.PHASE_WALL_CLOCK_SECONDS != manifest["generation"]["api_phase_deadline_seconds"]:
        raise BudgetStop("phase deadline differs from registration")
    spec = spec_for(job)
    if spec.render_spec() != job["render_spec"] or spec.input_identity() != job["input_identity"]:
        raise BudgetStop("generation render or input identity changed")
    if api_runner.provider_identity()["base_url"] != manifest["provider_base_url"]:
        raise BudgetStop("provider identity does not match the configured CBORG endpoint")
    ledger = open_ledger(manifest, manifest_sha, here)
    client = CappedClient(anthropic.Anthropic(api_key=key, base_url=manifest["provider_base_url"],
                                             max_retries=manifest["generation"]["sdk_max_retries"]),
        ledger=ledger, attempt=attempt_identity(manifest_sha, job["id"]), evidence=attempt / "requests",
        model=manifest["model"]["model"], prices=manifest["budget"]["prices_per_token"],
        verify=lambda: verify(manifest, args.registration, manifest_sha),
        initial_request=json.loads(Path(job["initial_request"]).read_bytes()))
    receipt = {"job": job["id"], "registration_sha256": manifest_sha,
               "review_sha256": sha(args.review), "started_at": datetime.now(timezone.utc).isoformat(),
               "launch_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
               "status": "incomplete", "generation_requests_admitted": 0}
    write_new(attempt / "started.json", receipt)
    try:
        record = api_runner.execute(spec, client=client, resume=False)
        client.messages.require_active()
        verify(manifest, args.registration, manifest_sha)
        verify_history(manifest)
        receipt.update(status="validation_failed" if record["validation_problems"] else "completed_pending_independent_review",
                       validation_problems=record["validation_problems"], checks=record["checks"])
    except Exception as exc:
        # Do not stringify provider exceptions: HTTP errors can contain headers.
        receipt.update(status="stopped", error_type=type(exc).__name__)
        if isinstance(exc, BudgetStop):
            receipt["reason"] = str(exc)
    finally:
        receipt.update(finished_at=datetime.now(timezone.utc).isoformat(),
                       generation_requests_admitted=client.messages.requests_started,
                       artifacts={str(p): sha(p) for folder in job["output_directories"]
                                  for p in sorted(Path(folder).rglob("*")) if p.is_file()})
        write_new(attempt / "result.json", receipt)
        print(json.dumps({k: v for k, v in receipt.items() if k not in {"artifacts", "checks", "validation_problems"}}, indent=2))
    return 0 if receipt["status"] == "completed_pending_independent_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
