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
It never opens a refused run's candidate output. It also re-verifies the 15 scope
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
