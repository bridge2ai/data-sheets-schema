#!/usr/bin/env python3
"""Purpose: negative controls for the replacement check in
verify_root_scope_22b_20261126.py (independent review of PR 6396, 2026-11-26: the
verifier accepted an empty claim, an unrelated claim, and hashes placed in unrelated
fields). Builds a private mirror of the real 2026-11-22b evidence directory in which
everything is a symlink to the real, read-only evidence except the
first-scoring-remediations records, which are copied so they can be mutated. Runs the
verifier on the unmutated mirror and on each positive control (must exit 0 with no
problems and a table) and on each mutation (must exit 1 and write no table). Nothing in the real evidence is written.
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
    # the cells scored under the revised session reader: their checkout and saved plans are linked,
    # their run directories are linked one by one so that a control can replace one with a copy
    for name in ("checkout-revised-reader", "revised-reader-plans"):
        if (REAL / name).exists(): os.symlink(REAL / name, root / name)
    if (REAL / "live-runs-revised-reader").exists():
        (root / "live-runs-revised-reader").mkdir()
        for entry in (REAL / "live-runs-revised-reader").iterdir(): os.symlink(entry, root / "live-runs-revised-reader" / entry.name)
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

THIRD = "chorus-22b-rep1-rubric20-03"
OTHER_THIRD = "chorus-22b-rep3-rubric20-03"
INSTRUMENT_DIR = "2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6"
def private_third(root, name=None):
    """Replace the linked third-attempt run by a private, self-consistent copy: its plan names the
    private run directory (as a run at this location would have), the plan saved before the run is
    the same plan, and the receipt binds it. Unchanged, such a copy must still be accepted."""
    import hashlib
    name = name or THIRD
    link = root / "live-runs-revised-reader" / name; real = link.resolve()
    link.unlink(); link.mkdir()
    plan = json.loads((real / "plan.json").read_text().replace(str(real), str(link.resolve())))
    receipt = json.loads((real / "receipt.json").read_text().replace(str(real), str(link.resolve())))
    plans = root / "revised-reader-plans"
    if plans.is_symlink():
        source = plans.resolve(); plans.unlink(); plans.mkdir()
        for entry in source.iterdir():
            if entry.is_file() and not entry.name.startswith("."): shutil.copy(entry, plans / entry.name)
    def store(executed=True, saved=True, bind=True):
        if executed: (link / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True))
        if saved: (plans / f"{name}.plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True))
        if bind: receipt["plan_sha256"] = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
        (link / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True))
    store()
    return plan, receipt, store

def third_receipt(root, change):
    """Change only the receipt of the private third attempt."""
    plan, receipt, store = private_third(root); change(receipt); store(executed=False, saved=False, bind=False)

def third_plan(root, change):
    """Change only the executed plan of the private third attempt; nothing is rebound."""
    plan, receipt, store = private_third(root); change(plan); store(saved=False, bind=False)

def third_saved_only(root, change):
    """Change only the plan saved before the run; the executed plan and the receipt are untouched."""
    plan, receipt, store = private_third(root)
    saved = root / "revised-reader-plans" / f"{THIRD}.plan.json"
    other = json.loads(saved.read_text()); change(other); saved.write_text(json.dumps(other, indent=2, sort_keys=True))

def third_coherent(root, change):
    """Change the executed plan and make every copy agree with it: the plan saved before the run
    and the receipt's canonical plan digest. Only a comparison with attempt 1 or with the real
    files can then notice the change."""
    plan, receipt, store = private_third(root); change(plan, root); store()

def zero_validator(plan, root):
    key = next(k for k in plan["validation_sha256"] if k.endswith("scripts/validate_evaluation_schema.py"))
    plan["validation_sha256"][key] = "0" * 64

def refuse_third(root, change=lambda receipt: None):
    """Turn the private third attempt into a finished refusal with a reason and its own
    authorization, and remove its publication from a private view of the revised checkout."""
    plan, receipt, store = private_third(root)
    receipt.update(status="REFUSED", failure="ScorerError: synthetic refusal for a control")
    for key in ("output", "output_sha256", "validator_input_sha256", "validator_exit"): receipt.pop(key, None)
    change(receipt); store(executed=False, saved=False, bind=False)
    view = root / "checkout-revised-reader"; real = view.resolve(); view.unlink()
    target = next((real / "data/evaluation_llm/rubric20_semantic/label_aware" / INSTRUMENT_DIR).glob("CHORUS_*_rep1_evaluation.json")).relative_to(real)
    here, there = view, real
    for part in target.parts[:-1] + (None,):
        here.mkdir()
        for entry in there.iterdir():
            if part is None and entry.name == target.name: continue       # the publication is gone
            if entry.name == part: continue                                # descend into this one
            os.symlink(entry, here / entry.name)
        if part is None: break
        here, there = here / part, there / part
    # the plan names the revised checkout by its real path; point it at the private view, as a
    # run in this view would have recorded it, and keep the saved plan and the receipt in step
    moved = json.loads(json.dumps(plan).replace(str(real), str(view.resolve())))
    plan.clear(); plan.update(moved); store()
    # the other cell scored in that checkout names it by its real path too: give it the same view
    other_plan, other_receipt, other_store = private_third(root, OTHER_THIRD)
    moved = json.loads(json.dumps(other_plan).replace(str(real), str(view.resolve())))
    other_plan.clear(); other_plan.update(moved)
    other_receipt["output"] = other_receipt["output"].replace(str(real), str(view.resolve()))
    other_store()

positives = {
    "private self-consistent copy of the third attempt, unchanged": lambda r: private_third(r),
    "third attempt as a finished refusal with a reason and its own authorization": lambda r: refuse_third(r),
}
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
    # the two cells scored under the revised session reader (third attempt)
    "third attempt reusing attempt 2's authorization": lambda r: third_receipt(r, lambda rc: rc.update(
        authorization_reference=json.loads((REAL / "live-runs" / (THIRD[:-3] + "-02") / "receipt.json").read_text())["authorization_reference"])),
    "third attempt whose receipt names another plan digest": lambda r: third_receipt(r, lambda rc: rc.update(plan_sha256="8" * 64)),
    "third attempt whose plan names the measured runner": lambda r: third_plan(r, lambda pl: pl.update(runner_sha256="b2a5c0995d891d4c5179509834b460390b1d921d78b0191965fc4ea3f91c21b9")),
    "third attempt with a prompt other than attempt 1's": lambda r: third_plan(r, lambda pl: pl.update(prompt_sha256="a" * 64)),
    "third attempt for a cell whose second attempt was published": lambda r: os.symlink(
        REAL / "live-runs-revised-reader" / THIRD, r / "live-runs-revised-reader" / "chorus-22b-rep2-rubric20-03"),
    # final review round: the third attempt's authorization type, its whole plan, and a refusal's record
    "third attempt authorization is JSON null": lambda r: third_receipt(r, lambda rc: rc.update(authorization_reference=None)),
    "third attempt authorization is a JSON object": lambda r: third_receipt(r, lambda rc: rc.update(authorization_reference={"owner": "yes"})),
    "third attempt prompt extended, digest label kept, saved plan and receipt rebound": lambda r: third_coherent(r, lambda pl, root: pl.update(prompt=pl["prompt"] + "\nAdditional instruction.")),
    "third attempt validator binding zeroed, saved plan and receipt rebound": lambda r: third_coherent(r, zero_validator),
    "refused third attempt without a completion time": lambda r: refuse_third(r, lambda rc: rc.pop("finished_utc")),
    "refused third attempt without a reason": lambda r: refuse_third(r, lambda rc: rc.pop("failure")),
    "refused third attempt without an authorization": lambda r: refuse_third(r, lambda rc: rc.pop("authorization_reference")),
    # recheck round: source paths that still name the measured checkout, and JSON types
    "third attempt runner path is the measured checkout's scorer, revised hash label kept, rebound": lambda r: third_coherent(r, lambda pl, root: pl.update(
        runner=json.loads((REAL / "live-runs" / (THIRD[:-3] + "-01") / "plan.json").read_text())["runner"])),
    "third attempt repo_root is the measured checkout, rebound": lambda r: third_coherent(r, lambda pl, root: pl.update(
        repo_root=json.loads((REAL / "live-runs" / (THIRD[:-3] + "-01") / "plan.json").read_text())["repo_root"])),
    "third attempt names the measured checkout everywhere, revised hash label kept, rebound": lambda r: third_coherent(r, lambda pl, root: (
        lambda moved: (pl.clear(), pl.update(moved)))(json.loads(json.dumps(pl).replace(str((REAL / "checkout-revised-reader").resolve()), str((REAL / "checkout").resolve()))))),
    "third attempt plan with a JSON false replaced by 0, rebound": lambda r: third_coherent(r, lambda pl, root: pl["deterministic_fields"]["evaluation_scope"].update(collection_metadata_inherited=0)),
    "saved third-attempt plan with a JSON false replaced by 0, executed plan untouched": lambda r: third_saved_only(r, lambda pl: pl["deterministic_fields"]["evaluation_scope"].update(collection_metadata_inherited=0)),
    "published record carrying binding failures": lambda r: edit(r, PUBLISHED, "manifest.json", lambda m: m.update(binding_failures=["claim_sha256"])),
}
ok = True
code, table, found = run(mirror("baseline"))
good = code == 0 and table and not found; ok &= good
print(f"{'PASS' if good else 'FAIL'} baseline: exit {code}, table written {table}, problems {len(found)}")
for index, (name, mutate) in enumerate(positives.items(), 1):
    root = mirror(f"positive-{index:02d}"); mutate(root)
    code, table, found = run(root)
    good = code == 0 and table and not found; ok &= good
    print(f"{'PASS' if good else 'FAIL'} positive, {name}: exit {code}, table written {table}, problems {len(found)}" + (f" ({found[0][8:110]})" if found else ""))
for index, (name, mutate) in enumerate(controls.items(), 1):
    root = mirror(f"control-{index:02d}"); mutate(root)
    code, table, found = run(root)
    good = code == 1 and not table and bool(found); ok &= good
    print(f"{'PASS' if good else 'FAIL'} {name}: exit {code}, table written {table}, problems {len(found)}" + (f" ({found[0][8:110]})" if found else ""))
sys.exit(0 if ok else 1)
