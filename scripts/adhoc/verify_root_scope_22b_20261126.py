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
a publication only, the published bytes; a refusal must carry no accepted output. A third attempt is accepted only for a cell
whose attempts 1 and 2 were both refused, only in the revised-reader checkout, and only if
its evaluation records the revised runner hash with attempt 1's prompt and inputs; every
other cell must record the measured runner hash. The table's last column gives the runner
hash that accepted each measured cell. It never opens a refused run's candidate output. It also re-verifies the 15 scope
declarations against scope-declarations.sha256.
Inputs: argv[1] evidence directory (holds checkout/, live-runs/, scope-declarations.sha256).
Outputs: lines on stdout; JSON to argv[2]; TSV provenance table to argv[3] (repository-
relative paths only). Exit 1 on any problem, and when any cell is running, not started
or carries a receipt that is neither REFUSED nor VALIDATED_AND_PUBLISHED; the table is
written only for a complete, problem-free pass.
Date: 2026-11-26 (UTC). Lead: Claude lead."""
import hashlib, json, pathlib, shlex, subprocess, sys
X, OUT, TSV = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
W = X / "checkout"
INST = "2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6"
LABEL = "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep"
PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC")
MAXP = {"rubric10": 50, "rubric20": 88}
LEAKS = ("/Users/", "/home/", "agent-work", pathlib.Path.home().name, "\\\\", ".codex/auth")
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
MEASURED_RUNNER_SHA256 = "b2a5c0995d891d4c5179509834b460390b1d921d78b0191965fc4ea3f91c21b9"  # scorer at 9452a5c49
REVISED_RUNNER_SHA256 = "45324f05ef4360f95620c5e9a37d7896661321177242f700f25bd22fe72cf51b"   # session reader fixed, 60dc19972 (issue 6384)
W2 = X / "checkout-revised-reader"  # a third attempt, on the owner's word, runs here under the revised reader
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
def relocated(value, pairs):
    """Explicit path relocation used to build an expected plan from a trusted one: a string (or a
    mapping key) is changed only when it IS one of the given roots or lies under it; shell command
    strings are handled token by token under the same rule."""
    def one(text):
        for old, new in pairs:
            if text == old or text.startswith(old + "/"): return new + text[len(old):]
        return text
    if isinstance(value, dict): return {one(k) if isinstance(k, str) else k: relocated(v, pairs) for k, v in value.items()}
    if isinstance(value, list): return [relocated(v, pairs) for v in value]
    return one(value) if isinstance(value, str) else value
def shell_tokens(command, pairs):
    out = []
    for token in shlex.split(command):
        head, sep, tail = token.partition("=")
        out.append(head + sep + relocated(tail, pairs) if sep and tail.startswith("/") else relocated(token, pairs))
    return out
def check_third(cell, bad, base, project, label, fam, rel, third):
    """A third attempt under the revised session reader, allowed only for a cell whose attempts 1
    and 2 were both refused (owner's word of 2026-11-27 for two cells). It is a separately
    labelled measurement: the evaluation must record the revised runner hash, and the whole
    executed plan must be attempt 1's plan moved forward to the revised checkout and the third
    run directory, with the revised runner hash, compared as JSON text; the scorer file at
    the plan's runner path must be the revised checkout's and hash to the revised hash. Authorization, completion and plan binding are checked
    before the outcome is read, so a refusal is held to the same record as a publication."""
    if cell["state"] == "measured": bad("a third attempt exists for a cell already measured"); return
    if [r["attempt"] for r in cell["refusals"]] != [1, 2]: bad("a third attempt without two refused attempts"); return
    if not (third / "receipt.json").exists(): cell["state"] = "running"; return
    r = load_object(third / "receipt.json", "attempt 3 receipt", bad)
    if r is None: cell["state"] = "unknown"; return
    first, second = X / "live-runs" / f"{base}-01", X / "live-runs" / f"{base}-02"
    # common checks, whatever the outcome
    auth = r.get("authorization_reference")
    earlier = {json.loads((d / "receipt.json").read_text()).get("authorization_reference") for d in (first, second)}
    if not isinstance(auth, str) or not auth.strip(): bad("attempt 3: authorization is not a nonblank string")
    elif auth.strip() in {e.strip() for e in earlier if isinstance(e, str)}: bad("attempt 3: no authorization of its own")
    if not isinstance(r.get("finished_utc"), str) or not r["finished_utc"].strip(): bad("attempt 3: receipt has no completion time")
    plan3 = load_object(third / "plan.json", "attempt 3 plan", bad) if (third / "plan.json").exists() else None
    if plan3 is None: bad("attempt 3: no executed plan")
    else:
        plan1 = json.loads((first / "plan.json").read_text())
        # Build the plan a third attempt MUST have: attempt 1's plan with its run directory and
        # checkout moved forward to the third run and the revised checkout, and the revised runner
        # hash. A path that still names the measured checkout is then simply a difference.
        forward = [(str(first.resolve()), str(third.resolve())), (str(W.resolve()), str(W2.resolve()))]
        if plan1.get("runner_sha256") != MEASURED_RUNNER_SHA256: bad("attempt 1: plan does not name the measured runner")
        expect = relocated({k: v for k, v in plan1.items() if k != "commands_shell"}, forward)
        expect["runner_sha256"] = REVISED_RUNNER_SHA256
        got = {k: v for k, v in plan3.items() if k != "commands_shell"}
        canon = lambda value: json.dumps(value, sort_keys=True)   # JSON text, so that false and 0 differ
        if canon(got) != canon(expect): bad("attempt 3: executed plan is not attempt 1's plan moved to the revised checkout and third run directory with the revised runner hash: " + ", ".join(sorted(k for k in set(expect) | set(got) if canon(expect.get(k)) != canon(got.get(k)))))
        try:
            if [shell_tokens(c, forward) for c in plan1["commands_shell"]] != [shlex.split(c) for c in plan3["commands_shell"]]: bad("attempt 3: shell commands are not attempt 1's moved to the revised checkout and third run directory")
        except (TypeError, ValueError, KeyError): bad("attempt 3: shell commands are not comparable")
        runner = W2 / "scripts/adhoc/score_semantic_rubric_codex_20261125.py"
        if not same_file(plan3.get("runner"), runner): bad("attempt 3: runner path is not the revised checkout's scorer")
        elif sha(runner) != REVISED_RUNNER_SHA256: bad("attempt 3: the scorer file at the runner path does not hash to the revised runner hash")
        for plan, name in ((plan1, "attempt 1"), (plan3, "attempt 3")):
            if not isinstance(plan.get("prompt"), str) or hashlib.sha256(plan["prompt"].encode()).hexdigest() != plan.get("prompt_sha256"): bad(f"{name}: prompt bytes do not hash to the recorded prompt digest")
        for path, digest in (plan3.get("validation_sha256") or {}).items():
            if not pathlib.Path(path).is_file() or sha(path) != digest: bad(f"attempt 3: validator dependency {pathlib.Path(path).name} does not match its bound hash")
        if not plan3.get("validation_sha256"): bad("attempt 3: no validator bindings")
        if r.get("plan_sha256") != hashlib.sha256(json.dumps(plan3, sort_keys=True).encode()).hexdigest(): bad("attempt 3: receipt does not bind the executed plan")
        saved = X / "revised-reader-plans" / f"{base}-03.plan.json"
        if not saved.exists() or json.loads(saved.read_text()) != plan3: bad("attempt 3: executed plan differs from the plan saved before the run")
    dest = W2 / rel
    if r.get("status") == "REFUSED":
        if not isinstance(r.get("failure"), str) or not r["failure"].strip(): bad("attempt 3: refusal without a reason")
        cell["refusals"].append({"attempt": 3, "reason": r.get("failure"), "validator_exit": r.get("validator_exit")})
        if dest.exists() or "output_sha256" in r: bad("refused third attempt has a file or claims one")
        return
    if r.get("status") != "VALIDATED_AND_PUBLISHED": bad(f"attempt 3: receipt status {r.get('status')!r}"); cell["state"] = "unknown"; return
    cell["state"], cell["attempt"] = "measured", 3
    if r.get("validator_exit") != 0 or r.get("codex_exit") != 0: bad("attempt 3: exit codes not 0")
    if r.get("auth_copy_absent") is not True or (third / "codex-home/auth.json").exists(): bad("attempt 3: auth copy not shown absent")
    if r.get("evaluation_model", {}).get("name") != "gpt-6-astra": bad("attempt 3: unexpected evaluator model")
    if not same_file(r.get("output"), dest) or not dest.exists(): bad("attempt 3: published file missing or not the cell's file"); return
    h = sha(dest); cell["sha256"] = h
    if not (h == r.get("output_sha256") == r.get("validator_input_sha256")): bad("attempt 3: published, receipt and validated hashes differ")
    text = dest.read_text(); d = json.loads(text)
    if d.get("instrument_id") != INST or d.get("version") != "6.0": bad("attempt 3: instrument mismatch")
    if (d.get("project"), d.get("label"), d.get("method")) != (project, label, "claudecode_agent"): bad("attempt 3: identity mismatch")
    if [u.get("path") for u in d.get("evaluation_scope", {}).get("units", [])] != ["#"]: bad("attempt 3: not exactly one root unit")
    score = d["overall_score"]
    if score.get("max_points") != MAXP[fam] or score.get("adjusted_max_points") != MAXP[fam]: bad("attempt 3: unexpected maximum")
    cell["points"], cell["max_points"] = score["total_points"], score["max_points"]
    record = "data/d4d_concatenated/claudecode_agent/" + label + f"/{project}_d4d.yaml"
    scope = "data/evaluation_scope/2026-11-22b/" + label + f"/{project}.scope.json"
    if sha(W2 / record) != sha(W / record) or d["metadata"].get("input_sha256") != sha(W / record): bad("attempt 3: record bytes differ from the measured checkout's")
    if sha(W2 / scope) != sha(W / scope) or d["metadata"].get("scope_context_sha256") != sha(W / scope): bad("attempt 3: scope declaration differs from the reviewed one")
    hits = [t for t in LEAKS if t in text]
    if hits: bad(f"attempt 3: leak tokens {hits}")
    instrument = d.get("scorer_instrument") or {}
    cell["accepting_runner_sha256"] = instrument.get("runner_sha256")
    if cell["accepting_runner_sha256"] != REVISED_RUNNER_SHA256: bad("attempt 3: not accepted by the revised runner")
    if plan3 is not None and instrument.get("prompt_sha256") != plan3.get("prompt_sha256"): bad("attempt 3: the evaluation's prompt digest is not the executed plan's")
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
                if not isinstance(r.get("finished_utc"), str) or not r["finished_utc"].strip(): bad("published receipt has no completion time")
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
                    cell["accepting_runner_sha256"] = (d.get("scorer_instrument") or {}).get("runner_sha256")
                    if cell["accepting_runner_sha256"] != MEASURED_RUNNER_SHA256: bad("not accepted by the measured runner")
            if cell["state"] != "measured" and (W / rel).exists(): bad("a file exists for a cell that is not measured")
            # a second attempt must be declared by the reviewed replacement helper: parse the
            # claim and the terminal record and compare every named binding field with the files
            second = X / "live-runs" / f"{base}-02"
            remedy = X / "live-runs" / "first-scoring-remediations" / f"{base}-01"
            if second.exists() or remedy.exists():
                check_remedy(cell, bad, base, project, label, fam, rel, second, remedy)
            elif cell.get("attempt") == 2: bad("attempt 2 published without a remedy record")
            third = X / "live-runs-revised-reader" / f"{base}-03"
            if third.exists(): check_third(cell, bad, base, project, label, fam, rel, third)
            elif (W2 / rel).exists(): bad("a revised-reader file exists without its run")
            cells.append(cell)
on_disk = sorted(str(p.relative_to(W)) for p in (W / "data/evaluation_llm").glob(f"*_semantic/label_aware/{INST}/*_evaluation.json"))
on_disk_revised = sorted(str(p.relative_to(W2)) for p in (W2 / "data/evaluation_llm").glob(f"*_semantic/label_aware/{INST}/*_evaluation.json")) if W2.exists() else []
if set(on_disk) & set(on_disk_revised): problems.append("a cell has a file in both checkouts")
if sorted(on_disk_revised) != sorted(c["path"] for c in cells if c.get("attempt") == 3 and c["state"] == "measured"): problems.append("revised-reader files on disk differ from the third-attempt cells")
on_disk = sorted(on_disk + on_disk_revised)
expected = sorted(c["path"] for c in cells if c["state"] == "measured")
if on_disk != expected: problems.append(f"files on disk ({len(on_disk)}) differ from measured cells ({len(expected)})")
chk = subprocess.run(["shasum", "-a", "256", "-c", str(X / "scope-declarations.sha256")], cwd=W, capture_output=True, text=True)
decl_ok = sum(line.endswith(": OK") for line in chk.stdout.splitlines())
if chk.returncode != 0 or decl_ok != 15: problems.append(f"scope declarations: {decl_ok} of 15 verify")
rows = ["project\tgeneration_rep\trubric\tstate\tpublished_attempt\tpoints\tmax_points\tsha256\tpath\trefused_attempts\trefusal_reason\taccepting_runner_sha256"]
for c in cells:
    reason = " | ".join(str(r["reason"]).replace("\t", " ") for r in c["refusals"])
    if c["state"] == "measured":
        rows.append(f"{c['project']}\t{c['generation_rep']}\t{c['rubric']}\tmeasured\t{c['attempt']}\t{c['points']}\t{c['max_points']}\t{c['sha256']}\t{c['path']}\t{len(c['refusals'])}\t{reason}\t{c['accepting_runner_sha256']}")
    else:
        rows.append(f"{c['project']}\t{c['generation_rep']}\t{c['rubric']}\t{c['state']}\t\t\t\t\t\t{len(c['refusals'])}\t{reason}\t")
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
