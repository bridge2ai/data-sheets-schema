#!/usr/bin/env python3
"""Purpose: verify the one-pass root-scope v6 scoring of the 15 records of series
2026-11-22b (claudecode_agent, labels 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1..3)
cell by cell, and write its provenance table. For each of the 30 cells (record x rubric)
it finds attempt 1 (run directory <name>-01) and, if present, attempt 2 (<name>-02), and
classifies the cell as measured (with the attempt that was published) or not measured
(with every refusal reason). For a published run it checks: receipt
VALIDATED_AND_PUBLISHED, validator exit 0, auth copy absent; published bytes equal the
receipt and validator-input sha256; instrument id and version; evaluator model; one root
unit "#"; the rubric's fixed maximum; the record sha256 and scope-declaration sha256 in
the file equal the bytes in the checkout; no local path or account name in the file.
A cell with a second attempt must carry the reviewed replacement helper's claim and
terminal record (live-runs/first-scoring-remediations/<name>-01/). Both are parsed and
every named field is compared with what it must bind: cell identity, attempt and scoring
number, the reviewed helper's hash, the measured scorer head, the authorization, the
refused plan and receipt, the claim, the attempt-2 plan and receipt, the compared-plan digest (which must be the
canonical digest of the executed attempt-2 plan and the one its receipt binds), and, for
a publication only, the published bytes; a refusal must carry no accepted output. It never opens a refused
run's candidate output. It also re-verifies the 15 scope
declarations against scope-declarations.sha256.
Inputs: argv[1] evidence directory (holds checkout/, live-runs/, scope-declarations.sha256).
Outputs: lines on stdout; JSON to argv[2]; TSV provenance table to argv[3] (repository-
relative paths only). Exit 1 on any problem, and when any cell is running, not started
or carries a receipt that is neither REFUSED nor VALIDATED_AND_PUBLISHED; the table is
written only for a complete, problem-free pass.
Date: 2026-11-26 (UTC). Lead: Claude lead."""
import hashlib, json, pathlib, subprocess, sys
X, OUT, TSV = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
W = X / "checkout"
INST = "2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6"
LABEL = "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep"
PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC")
MAXP = {"rubric10": 50, "rubric20": 88}
LEAKS = ("/Users/", "/home/", "agent-work", pathlib.Path.home().name, "\\\\", ".codex/auth")
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
KIND = "ROOT_SCOPE_FIRST_SCORING_REPLACEMENT_V1"
MEASURED_HEAD = "9452a5c49a0533d86c5e08c1093021036ef98830"
APPROVED_HELPER_SHA256 = "a03186c85112d079e465f12beca995f63300e3cff95cef21a3462fc5c8f72afb"  # reviewed at 944d14d17
same_file = lambda recorded, expected: isinstance(recorded, str) and pathlib.Path(recorded).resolve() == pathlib.Path(expected).resolve()
def load_object(path, what, bad):
    try: value = json.loads(pathlib.Path(path).read_text())
    except (OSError, ValueError) as exc: bad(f"{what} is not readable JSON: {type(exc).__name__}"); return None
    if not isinstance(value, dict): bad(f"{what} is not a JSON object"); return None
    return value
def check_remedy(cell, bad, base, project, label, fam, rel, second, remedy):
    """Structured check of a first-scoring replacement: the claim and the terminal record are
    parsed, and each named field is compared with the file or value it must bind. A hash that
    merely occurs somewhere in a record satisfies nothing."""
    first = X / "live-runs" / f"{base}-01"
    if not (remedy / "claim.json").exists() or not (remedy / "manifest.json").exists(): bad("attempt 2 without the helper's claim and terminal record"); return
    claim, term = load_object(remedy / "claim.json", "claim", bad), load_object(remedy / "manifest.json", "terminal record", bad)
    if claim is None or term is None: return
    identity = {"project": project, "label": label, "method": "claudecode_agent", "rubric": fam + "-semantic", "instrument_id": INST, "version": "6.0",
                "d4d_file": f"data/d4d_concatenated/claudecode_agent/{label}/{project}_d4d.yaml"}
    refused = {"plan_sha256": sha(first / "plan.json"), "receipt_sha256": sha(first / "receipt.json")}
    first_receipt = json.loads((first / "receipt.json").read_text())
    if first_receipt.get("status") != "REFUSED": bad("attempt 1 is not REFUSED but a remedy exists")
    for name, record in (("claim", claim), ("terminal record", term)):
        if record.get("kind") != KIND or record.get("action") != "replacement": bad(f"{name}: not a first-scoring replacement")
        if type(record.get("attempt")) is not int or type(record.get("scoring_replicate")) is not int or (record["attempt"], record["scoring_replicate"]) != (2, 1): bad(f"{name}: attempt or scoring number is wrong")
        if record.get("identity") != identity: bad(f"{name}: cell identity differs")
        if record.get("source_head") != MEASURED_HEAD: bad(f"{name}: measured scorer head differs")
        if (record.get("orchestration") or {}).get("sha256") != APPROVED_HELPER_SHA256: bad(f"{name}: not the reviewed helper")
        ra = record.get("refused_attempt") or {}
        if ra.get("plan_sha256") != refused["plan_sha256"] or ra.get("receipt_sha256") != refused["receipt_sha256"]: bad(f"{name}: refused plan or receipt hash field is wrong")
        if not (same_file(ra.get("plan_path"), first / "plan.json") and same_file(ra.get("receipt_path"), first / "receipt.json") and same_file(ra.get("run_directory"), first)): bad(f"{name}: refused attempt paths are wrong")
        if not same_file(record.get("destination"), W / rel): bad(f"{name}: destination is not the cell's file")
    auth = claim.get("authorization_reference")
    if not isinstance(auth, str) or not auth.strip(): bad("claim: no authorization reference")
    elif auth.strip() == str(first_receipt.get("authorization_reference", "")).strip(): bad("claim: authorization is attempt 1's")
    if claim.get("status") != "ATTEMPT2_CLAIMED": bad("claim: unexpected status")
    if not same_file(claim.get("run_directory"), second): bad("claim: run directory is not attempt 2")
    if term.get("authorization_reference") != auth: bad("terminal record: authorization differs from the claim")
    digest = claim.get("replacement_plan_sha256")
    if not (isinstance(digest, str) and len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest)): bad("claim: compared-plan digest is not a sha256"); digest = None
    if term.get("replacement_plan_sha256") != claim.get("replacement_plan_sha256"): bad("terminal record: compared-plan digest differs from the claim")
    if term.get("claim_sha256") != sha(remedy / "claim.json") or not same_file(term.get("claim_path"), remedy / "claim.json"): bad("terminal record: claim binding is wrong")
    if term.get("observed_original_plan_sha256") != refused["plan_sha256"] or term.get("observed_original_receipt_sha256") != refused["receipt_sha256"]: bad("terminal record: observed original hashes are wrong")
    status = term.get("status"); cell["remedy_status"] = status
    have_run = (second / "plan.json").exists() and (second / "receipt.json").exists()
    if not have_run: bad("attempt 2 has no plan and receipt")
    else:
        if term.get("actual_plan_sha256") != sha(second / "plan.json") or term.get("actual_receipt_sha256") != sha(second / "receipt.json"): bad("terminal record: actual plan or receipt hash field is wrong")
        if not (same_file(term.get("actual_plan"), second / "plan.json") and same_file(term.get("actual_receipt"), second / "receipt.json")): bad("terminal record: actual plan or receipt path is wrong")
        second_receipt = json.loads((second / "receipt.json").read_text())
        if second_receipt.get("authorization_reference") != auth: bad("attempt-2 receipt: authorization differs from the claim")
        # the plan that was compared with attempt 1 must be the plan that ran: the producer's
        # canonical digest of the saved attempt-2 plan, which the scorer also puts in its receipt
        canonical = hashlib.sha256(json.dumps(json.loads((second / "plan.json").read_text()), sort_keys=True).encode()).hexdigest()
        if digest != canonical: bad("compared-plan digest is not the digest of the executed attempt-2 plan")
        if second_receipt.get("plan_sha256") != canonical: bad("attempt-2 receipt does not bind the executed plan")
    vb = term.get("verified_bindings") or {}
    for key, value in vb.items():
        if term.get(key) != value: bad(f"terminal record: verified binding {key} differs from its field")
    for key in ("claim_sha256", "observed_original_plan_sha256", "observed_original_receipt_sha256"):
        if key not in vb: bad(f"terminal record: binding {key} was not verified")
    if cell["state"] == "measured":
        if cell.get("attempt") != 2: bad("a remedy exists but attempt 1 is the published one")
        if status != "FIRST_SCORING_REPLACEMENT_PUBLISHED": bad(f"published attempt 2 but terminal status {status}")
        published = cell.get("sha256")
        for key in ("accepted_output_sha256", "output_sha256", "destination_sha256", "observed_destination_sha256", "validator_input_sha256"):
            if term.get(key) != published or not published: bad(f"terminal record: {key} does not equal the published bytes")
        if term.get("destination_exists") is not True or term.get("failure") or term.get("binding_failures"): bad("terminal record: publication fields are inconsistent")
        for key in ("actual_plan_sha256", "actual_receipt_sha256", "observed_destination_sha256"):
            if key not in vb: bad(f"terminal record: binding {key} was not verified")
    else:
        if status != "FIRST_SCORING_REPLACEMENT_REFUSED": bad(f"cell not measured but terminal status {status}")
        if term.get("accepted_output_sha256") is not None or term.get("destination_exists") is not False: bad("terminal record: a refusal carries an accepted output")
        if not term.get("failure"): bad("terminal record: refusal without a reason")
        elif have_run and term.get("failure") != second_receipt.get("failure"): bad("terminal record: refusal reason differs from the attempt-2 receipt")
cells, problems = [], []
for project in PROJECTS:
    for g in (1, 2, 3):
        for fam in ("rubric10", "rubric20"):
            label = f"{LABEL}{g}"
            base = project.lower().replace("_", "-") + f"-22b-rep{g}-{fam}"
            rel = f"data/evaluation_llm/{fam}_semantic/label_aware/{INST}/{project}_{label}_evaluation.json"
            cell = {"project": project, "generation_rep": g, "rubric": fam, "path": rel, "refusals": [], "state": "not started"}
            bad = lambda msg, cell=cell, base=base: (problems.append(f"{base}: {msg}"), cell.setdefault("problems", []).append(msg))
            published = None
            for attempt in (1, 2):
                run = X / "live-runs" / f"{base}-0{attempt}"
                if not run.exists(): continue
                if not (run / "receipt.json").exists(): cell["state"] = "running"; continue
                r = json.loads((run / "receipt.json").read_text())
                if r.get("status") == "REFUSED":
                    if not r.get("failure") or not r.get("finished_utc"): bad(f"attempt {attempt}: REFUSED receipt without a reason or a finish time")
                    cell["refusals"].append({"attempt": attempt, "reason": r.get("failure"), "validator_exit": r.get("validator_exit")})
                    cell["state"] = "not measured"; continue
                if r.get("status") != "VALIDATED_AND_PUBLISHED":
                    # neither a terminal refusal nor a publication: not a state this table may describe
                    bad(f"attempt {attempt}: receipt status {r.get('status')!r} is neither REFUSED nor VALIDATED_AND_PUBLISHED")
                    cell["state"] = "unknown"; continue
                if published is not None: bad("two published attempts")
                published = attempt; cell["state"] = "measured"; cell["attempt"] = attempt
                if r.get("validator_exit") != 0 or r.get("codex_exit") != 0: bad("exit codes not 0")
                if r.get("auth_copy_absent") is not True or (run / "codex-home/auth.json").exists(): bad("auth copy not shown absent")
                if r.get("evaluation_model", {}).get("name") != "gpt-6-astra": bad("unexpected evaluator model")
                dest = W / rel
                if pathlib.Path(r["output"]).resolve() != dest.resolve(): bad("receipt output path is not the expected file")
                elif not dest.exists(): bad("published file missing")
                else:
                    h = sha(dest); cell["sha256"] = h
                    if not (h == r.get("output_sha256") == r.get("validator_input_sha256")): bad("published, receipt and validated hashes differ")
                    text = dest.read_text(); d = json.loads(text)
                    if d.get("instrument_id") != INST or d.get("version") != "6.0": bad("instrument mismatch")
                    if (d.get("project"), d.get("label"), d.get("method")) != (project, label, "claudecode_agent"): bad("identity mismatch")
                    units = d.get("evaluation_scope", {}).get("units", [])
                    if [u.get("path") for u in units] != ["#"]: bad("not exactly one root unit")
                    s = d["overall_score"]
                    if s.get("max_points") != MAXP[fam] or s.get("adjusted_max_points") != MAXP[fam]: bad("unexpected maximum")
                    cell["points"], cell["max_points"] = s["total_points"], s["max_points"]
                    record = W / "data/d4d_concatenated/claudecode_agent" / label / f"{project}_d4d.yaml"
                    scope = W / "data/evaluation_scope/2026-11-22b" / label / f"{project}.scope.json"
                    if d["metadata"].get("input_sha256") != sha(record): bad("record hash in file differs from the record")
                    if d["metadata"].get("scope_context_sha256") != sha(scope): bad("scope hash in file differs from the declaration")
                    hits = [t for t in LEAKS if t in text]
                    if hits: bad(f"leak tokens {hits}")
            if cell["state"] != "measured" and (W / rel).exists(): bad("a file exists for a cell that is not measured")
            # a second attempt must be declared by the reviewed replacement helper: parse the
            # claim and the terminal record and compare every named binding field with the files
            second = X / "live-runs" / f"{base}-02"
            remedy = X / "live-runs" / "first-scoring-remediations" / f"{base}-01"
            if second.exists() or remedy.exists():
                check_remedy(cell, bad, base, project, label, fam, rel, second, remedy)
            elif cell.get("attempt") == 2: bad("attempt 2 published without a remedy record")
            cells.append(cell)
on_disk = sorted(str(p.relative_to(W)) for p in (W / "data/evaluation_llm").glob(f"*_semantic/label_aware/{INST}/*_evaluation.json"))
expected = sorted(c["path"] for c in cells if c["state"] == "measured")
if on_disk != expected: problems.append(f"files on disk ({len(on_disk)}) differ from measured cells ({len(expected)})")
chk = subprocess.run(["shasum", "-a", "256", "-c", str(X / "scope-declarations.sha256")], cwd=W, capture_output=True, text=True)
decl_ok = sum(line.endswith(": OK") for line in chk.stdout.splitlines())
if chk.returncode != 0 or decl_ok != 15: problems.append(f"scope declarations: {decl_ok} of 15 verify")
rows = ["project\tgeneration_rep\trubric\tstate\tpublished_attempt\tpoints\tmax_points\tsha256\tpath\trefused_attempts\trefusal_reason"]
for c in cells:
    reason = " | ".join(str(r["reason"]).replace("\t", " ") for r in c["refusals"])
    if c["state"] == "measured":
        rows.append(f"{c['project']}\t{c['generation_rep']}\t{c['rubric']}\tmeasured\t{c['attempt']}\t{c['points']}\t{c['max_points']}\t{c['sha256']}\t{c['path']}\t{len(c['refusals'])}\t{reason}")
    else:
        rows.append(f"{c['project']}\t{c['generation_rep']}\t{c['rubric']}\t{c['state']}\t\t\t\t\t\t{len(c['refusals'])}\t{reason}")
counts = {}
for c in cells: counts[c["state"]] = counts.get(c["state"], 0) + 1
for p in problems: print("PROBLEM", p)
for c in cells:
    if c["state"] != "measured" or c["refusals"]:
        print(f"{c['state']}: {c['project']} rep{c['generation_rep']} {c['rubric']}" + (f" attempt {c.get('attempt')}" if c.get("attempt") else "") + " | refused: " + "; ".join(f"attempt {r['attempt']}: {r['reason']}" for r in c["refusals"]))
print(f"cells {len(cells)}; " + "; ".join(f"{k} {v}" for k, v in sorted(counts.items())) + f"; files on disk {len(on_disk)}; declarations verified {decl_ok}/15; problems {len(problems)}")
OUT.write_text(json.dumps({"instrument": INST, "counts": counts, "declarations_verified": decl_ok, "problems": problems, "cells": cells}, indent=1))
incomplete = sum(counts.get(k, 0) for k in ("running", "not started", "unknown"))
if incomplete: print(f"INCOMPLETE: {incomplete} cells are running, not started or in an unknown state; no table written")
if not problems and not incomplete: TSV.write_text("\n".join(rows) + "\n")
sys.exit(1 if problems or incomplete else 0)
