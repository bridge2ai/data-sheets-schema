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
from budgeted_cborg import cborg_client, provider_context_evidence
from prepare_registration import spec_for

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(manifest, path, expected_sha):
    if "audit_batches" in manifest:
        raise BudgetStop("audit_batches is audit-only; generation cannot select it")
    if "scientific_contract_transition" in manifest:
        raise BudgetStop("scientific_contract_transition is continuation-only; generation cannot select it")
    if "audit_drafting" in manifest:
        raise BudgetStop("audit_drafting is audit-only; generation cannot select it")
    if "audit_contract_context" in manifest:
        raise BudgetStop("audit_contract_context is audit-only; generation cannot select it")
    if "native_upstream_read_timeout_seconds" in manifest:
        raise BudgetStop("native_upstream_read_timeout_seconds is audit-only; generation cannot select it")
    if "native_stall_policy" in manifest:
        raise BudgetStop("native_stall_policy is audit-only; generation cannot select it")
    generation = manifest.get("generation")
    jobs = generation.get("jobs") if isinstance(generation, dict) else None
    if isinstance(jobs, list):
        for job in jobs:
            spec = job.get("render_spec") if isinstance(job, dict) else None
            if isinstance(spec, dict) and spec.get("render_version") in (19, "19", 20, "20", 21, "21"):
                raise BudgetStop(f"renderer {spec['render_version']} is audit-continuation-only; generation cannot select it")
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


def require_registered_receipt_inputs(spec, record, registered):
    """A current canary cannot use provenance to select historical source bytes."""
    import yaml
    inputs = record.get("inputs")
    if not isinstance(inputs, dict) or not isinstance(inputs.get("chunks"), dict):
        raise ValueError("receipt source identities are missing")
    declared = {"bundle": {"path": inputs.get("bundle_path"),
                           "sha256": inputs.get("bundle_sha256"),
                           "md5": inputs.get("bundle_md5")},
                "chunks": inputs["chunks"]}
    selected = {"bundle": spec.bundle, "chunks": spec.chunk_manifest}
    for name in ("bundle", "chunks"):
        expected = registered[name]
        path = Path(expected["path"])
        item = declared[name]
        if (selected[name] is None or path.resolve() != Path(selected[name]).resolve()
                or not isinstance(item.get("path"), str)
                or Path(item["path"]).resolve() != path.resolve()):
            raise ValueError("receipt source path differs from registration")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != expected["sha256"]:
            raise ValueError("registered receipt source bytes changed")
        if name == "bundle":
            if not (item.get("md5") or item.get("sha256")):
                raise ValueError("receipt bundle has no recorded hash")
            for algorithm in ("md5", "sha256"):
                if item.get(algorithm) is not None and item[algorithm] != hashlib.new(algorithm, raw).hexdigest():
                    raise ValueError("receipt bundle hash differs from registration")
        else:
            manifest = yaml.safe_load(raw)
            if (item.get("sha256") != digest or not isinstance(manifest, dict)
                    or item.get("rule") != manifest.get("rule")
                    or item.get("bundle_name") != manifest.get("bundle")
                    or type(item.get("chunk_count")) is not int
                    or item["chunk_count"] != manifest.get("chunk_count")):
                raise ValueError("receipt chunk identity differs from registration")


def check_canary_receipts(spec, registered_inputs):
    """Recompute the existing strict receipt floors; never repair measured bytes."""
    import yaml
    from data_sheets_schema import api_runner
    from data_sheets_schema.canary import receipt_floors
    try:
        record = yaml.safe_load(spec.provenance_path.read_bytes())
        if not isinstance(record, dict):
            raise ValueError("provenance is not a mapping")
        require_registered_receipt_inputs(spec, record, registered_inputs)
        block = api_runner._receipts_block(spec, record)
        if block.get("checked") is not True:
            return {"passed": False, "floors": None, "receipts": block}
        floors = receipt_floors(block)
        return {"passed": not any(floors.values()), "floors": floors, "receipts": block}
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
        return {"passed": False, "floors": None, "receipts": None,
                "reason": f"receipt acceptance could not be recomputed: {type(exc).__name__}"}


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
    api_runner.MAX_ATTEMPTS = manifest["generation"]["api_max_attempts"]
    if api_runner.PHASE_WALL_CLOCK_SECONDS != manifest["generation"]["api_phase_deadline_seconds"]:
        raise BudgetStop("phase deadline differs from registration")
    spec = spec_for(job)
    if spec.render_spec() != job["render_spec"] or spec.input_identity() != job["input_identity"]:
        raise BudgetStop("generation render or input identity changed")
    if api_runner.provider_identity()["base_url"] != manifest["provider_base_url"]:
        raise BudgetStop("provider identity does not match the configured CBORG endpoint")
    ledger = open_ledger(manifest, manifest_sha)
    client = CappedClient(cborg_client(manifest, key,
                                      max_retries=manifest["generation"]["sdk_max_retries"]),
        ledger=ledger, attempt=attempt_identity(manifest_sha, job["id"]), evidence=attempt / "requests",
        model=manifest["model"]["model"], prices=manifest["budget"]["prices_per_token"],
        verify=lambda: verify(manifest, args.registration, manifest_sha),
        initial_request=json.loads(Path(job["initial_request"]).read_bytes()))
    receipt = {"job": job["id"], "registration_sha256": manifest_sha,
               "provider_context": provider_context_evidence(manifest),
               "review_sha256": sha(args.review), "started_at": datetime.now(timezone.utc).isoformat(),
               "launch_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
               "status": "incomplete", "generation_requests_admitted": 0}
    write_new(attempt / "started.json", receipt)
    try:
        record = api_runner.execute(spec, client=client, resume=False)
        client.messages.require_active()
        verify(manifest, args.registration, manifest_sha)
        verify_history(manifest)
        receipt_check = check_canary_receipts(spec, job["input_identity"])
        problems = list(record["validation_problems"])
        if not receipt_check["passed"]:
            problems.append("coverage receipt acceptance failed")
        receipt.update(status="validation_failed" if problems else "completed_pending_independent_review",
                       validation_problems=problems,
                       checks={**record["checks"], "receipt_acceptance": receipt_check})
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
