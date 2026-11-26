#!/usr/bin/env python3
"""Purpose: negative controls for the replacement check in
verify_root_scope_22b_20261126.py (independent review of PR 6396, 2026-11-26: the
verifier accepted an empty claim, an unrelated claim, and hashes placed in unrelated
fields). Builds a private mirror of the real 2026-11-22b evidence directory in which
everything is a symlink to the real, read-only evidence except the
first-scoring-remediations records, which are copied so they can be mutated. Runs the
verifier on the unmutated mirror (must exit 0 with no problems) and on each mutation
(must exit 1 and write no table). Nothing in the real evidence is written.
Inputs: argv[1] real evidence directory; argv[2] verifier script; argv[3] scratch
directory (created; must not exist). Outputs: one line per control; exit 1 if any
control gives the wrong result.
Date: 2026-11-26 (UTC). Lead: Claude lead."""
import copy, json, os, pathlib, shutil, subprocess, sys
REAL, VERIFIER, SCRATCH = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve(), pathlib.Path(sys.argv[3])
SCRATCH.mkdir(parents=True)
PUBLISHED, REFUSED = "chorus-22b-rep2-rubric20-01", "chorus-22b-rep1-rubric20-01"

def mirror(name):
    root = SCRATCH / name; (root / "live-runs").mkdir(parents=True)
    os.symlink(REAL / "checkout", root / "checkout")
    shutil.copy(REAL / "scope-declarations.sha256", root / "scope-declarations.sha256")
    for entry in (REAL / "live-runs").iterdir():
        if entry.name == "first-scoring-remediations":
            shutil.copytree(entry, root / "live-runs" / entry.name)
            # the copied terminal records name the claim by its real path; point that one path
            # field at the copy, as a run at this location would have written it
            for manifest in (root / "live-runs" / entry.name).glob("*/manifest.json"):
                record = json.loads(manifest.read_text()); record["claim_path"] = str(manifest.with_name("claim.json").resolve())
                manifest.write_text(json.dumps(record, indent=2, sort_keys=True))
        else: os.symlink(entry, root / "live-runs" / entry.name)
    return root

def run(root):
    out = subprocess.run([sys.executable, "-B", str(VERIFIER), str(root), str(root / "verification.json"), str(root / "scorings.tsv")],
                         capture_output=True, text=True)
    return out.returncode, (root / "scorings.tsv").exists(), [line for line in out.stdout.splitlines() if line.startswith("PROBLEM")]

def edit(root, cell, filename, change):
    path = root / "live-runs/first-scoring-remediations" / cell / filename
    record = json.loads(path.read_text()); change(record); path.write_text(json.dumps(record, indent=2, sort_keys=True))

def coherent(root, cell, change):
    """Apply one change to the claim and to the terminal record, then refresh the terminal
    record's claim hash and its verified copy, so that the two records agree with each other."""
    import hashlib
    base = root / "live-runs/first-scoring-remediations" / cell
    edit(root, cell, "claim.json", change)
    digest = hashlib.sha256((base / "claim.json").read_bytes()).hexdigest()
    def both(m):
        change(m); m["claim_sha256"] = digest
        if "claim_sha256" in (m.get("verified_bindings") or {}): m["verified_bindings"]["claim_sha256"] = digest
    edit(root, cell, "manifest.json", both)
def forged_receipt(root, cell):
    """Replace the linked attempt-2 run by a private copy of its plan and receipt, change the
    receipt's plan digest, and rebind every hash and path that names the receipt or the run, so
    that the only inconsistency left is the receipt naming a plan other than the executed one."""
    import hashlib
    base = cell[:-3]; link = root / "live-runs" / f"{base}-02"; real = link.resolve()
    link.unlink(); link.mkdir()
    for name in ("plan.json", "receipt.json"): shutil.copy(real / name, link / name)
    receipt = json.loads((link / "receipt.json").read_text()); receipt["plan_sha256"] = "9" * 64
    (link / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True))
    receipt_sha = hashlib.sha256((link / "receipt.json").read_bytes()).hexdigest()
    edit(root, cell, "claim.json", lambda claim: claim.update(run_directory=str(link.resolve())))
    claim_sha = hashlib.sha256((root / "live-runs/first-scoring-remediations" / cell / "claim.json").read_bytes()).hexdigest()
    def rebind(m):
        m.update(actual_plan=str((link / "plan.json").resolve()), actual_receipt=str((link / "receipt.json").resolve()),
                 actual_receipt_sha256=receipt_sha, claim_sha256=claim_sha)
        for key, value in (("actual_receipt_sha256", receipt_sha), ("claim_sha256", claim_sha)):
            if key in (m.get("verified_bindings") or {}): m["verified_bindings"][key] = value
    edit(root, cell, "manifest.json", rebind)

controls = {
    "empty claim file": lambda r: (r / "live-runs/first-scoring-remediations" / PUBLISHED / "claim.json").write_text(""),
    "claim is not JSON": lambda r: (r / "live-runs/first-scoring-remediations" / PUBLISHED / "claim.json").write_text("{not json"),
    "claim names another project and has no authorization": lambda r: edit(r, PUBLISHED, "claim.json", lambda c: (c["identity"].update(project="VOICE"), c.pop("authorization_reference"))),
    "refused plan and receipt fields wrong, right hashes in a note": lambda r: edit(r, PUBLISHED, "manifest.json", lambda m: (
        m.update(note=[m["refused_attempt"]["plan_sha256"], m["refused_attempt"]["receipt_sha256"]]),
        m["refused_attempt"].update(plan_sha256="0" * 64, receipt_sha256="1" * 64),
        m.update(observed_original_plan_sha256="0" * 64, observed_original_receipt_sha256="1" * 64))),
    "accepted output field wrong, right hash in a note": lambda r: edit(r, PUBLISHED, "manifest.json", lambda m: (
        m.update(note=m["accepted_output_sha256"]), m.update(accepted_output_sha256="2" * 64))),
    "actual plan, actual receipt and claim hash fields wrong": lambda r: edit(r, PUBLISHED, "manifest.json", lambda m: m.update(
        actual_plan_sha256="3" * 64, actual_receipt_sha256="4" * 64, claim_sha256="5" * 64)),
    "not the reviewed helper": lambda r: edit(r, PUBLISHED, "claim.json", lambda c: c["orchestration"].update(sha256="6" * 64)),
    "refusal carrying an accepted output": lambda r: edit(r, REFUSED, "manifest.json", lambda m: m.update(accepted_output_sha256="7" * 64)),
    "refusal relabelled as published": lambda r: edit(r, REFUSED, "manifest.json", lambda m: m.update(status="FIRST_SCORING_REPLACEMENT_PUBLISHED")),
    "terminal record missing": lambda r: (r / "live-runs/first-scoring-remediations" / PUBLISHED / "manifest.json").unlink(),
    # second review round: forgeries that keep the claim and the terminal record consistent with each other
    "compared-plan digest replaced by zeroes in both records": lambda r: coherent(r, PUBLISHED, lambda rec: rec.update(replacement_plan_sha256="0" * 64)),
    "compared-plan digest replaced by a non-digest in both records": lambda r: coherent(r, PUBLISHED, lambda rec: rec.update(replacement_plan_sha256={"not": "a digest"})),
    "same forged digest on a refused replacement": lambda r: coherent(r, REFUSED, lambda rec: rec.update(replacement_plan_sha256="0" * 64)),
    "scoring number given as JSON true in both records": lambda r: coherent(r, PUBLISHED, lambda rec: rec.update(scoring_replicate=True)),
    "attempt-2 receipt names another plan digest, everything else rebound": lambda r: forged_receipt(r, REFUSED),
    "published record carrying binding failures": lambda r: edit(r, PUBLISHED, "manifest.json", lambda m: m.update(binding_failures=["claim_sha256"])),
}
ok = True
code, table, found = run(mirror("baseline"))
good = code == 0 and table and not found; ok &= good
print(f"{'PASS' if good else 'FAIL'} baseline: exit {code}, table written {table}, problems {len(found)}")
for index, (name, mutate) in enumerate(controls.items(), 1):
    root = mirror(f"control-{index:02d}"); mutate(root)
    code, table, found = run(root)
    good = code == 1 and not table and bool(found); ok &= good
    print(f"{'PASS' if good else 'FAIL'} {name}: exit {code}, table written {table}, problems {len(found)}" + (f" ({found[0][8:110]})" if found else ""))
sys.exit(0 if ok else 1)
