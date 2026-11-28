#!/usr/bin/env python3
"""Purpose: verify the repeat (scoring 2 and 3) root-scope v6 scorings of the 15 records
of the 2026-11-25c series, cell by cell, from the evidence on disk. For each of the 60
expected cells it classifies the cell as PUBLISHED, REFUSED, RUNNING or NOT_STARTED and,
for a published cell, checks: receipt VALIDATED_AND_PUBLISHED with validator exit 0 and
the auth copy absent; export manifest EXPORTED_VALIDATED_REPEAT with no failure.json;
published bytes == manifest destination hash == runner output hash == validated bytes;
prompt equal to the first scoring's; instrument id and version; evaluator model; no
local path or account name in the published file. A refused cell with a replacement
(attempt 2, owner word relayed 2026-11-26T06:01Z) is judged on attempt 2: its manifest
must say attempt 2 and carry the sha256 of the refused attempt-1 receipt, and the cell
is listed as PUBLISHED with attempt 2, or as REFUSED twice. It never opens a refused run's
candidate output, so it reports no score of a refused cell (plan UPDATE
2026-11-26T05:29Z). It also re-verifies the 30 first-scoring files against
evaluations-before.sha256.
Inputs: argv[1] repeat evidence directory, argv[2] feature worktree root.
Outputs: one line per problem and a summary on stdout; JSON to argv[3].
Serves: PR 6366 / PR 6372 triplicate scoring. Date: 2026-11-26 (UTC). Lead: Claude lead."""
import hashlib, json, pathlib, subprocess, sys
E, W, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
INST = "2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6"
LABEL = "2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep"
PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC")
LEAKS = ("/Users/", "/home/", "agent-work", pathlib.Path.home().name, "\\\\", ".codex/auth")
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
cells, problems = [], []
for k in (2, 3):
    for g in (1, 2, 3):
        for project in PROJECTS:
            for fam in ("rubric10", "rubric20"):
                job = f"scoring_rep{k}__{LABEL}{g}__{project}__{fam}"
                run, exp = E / "live-runs" / job, E / "live-runs/export-manifests" / job
                dest = W / "data/evaluation_repeats" / INST / f"scoring_rep{k}" / f"{fam}_semantic" / f"{project}_{LABEL}{g}_evaluation.json"
                cell = {"job": job, "scoring": k, "generation_rep": g, "project": project, "rubric": fam}
                bad = lambda msg, cell=cell: (problems.append(f"{cell['job']}: {msg}"), cell.setdefault("problems", []).append(msg))
                run2, exp2 = run.with_name(job + "__attempt2"), exp.with_name(job + "__attempt2")
                if run2.exists():
                    r1 = json.loads((run / "receipt.json").read_text())
                    if r1.get("status") != "REFUSED": bad("attempt 2 exists but attempt 1 is not REFUSED")
                    if (exp / "manifest.json").exists(): bad("attempt 1 has an export manifest beside attempt 2")
                    cell["attempt"] = 2; cell["attempt1_failure"] = r1.get("failure"); cell["attempt1_receipt_sha256"] = sha(run / "receipt.json")
                    run, exp = run2, exp2
                if not run.exists():
                    cell["state"] = "NOT_STARTED"
                    if dest.exists() or exp.exists(): bad("no run directory but an export or destination exists")
                elif not (run / "receipt.json").exists():
                    cell["state"] = "RUNNING"
                    if dest.exists(): bad("no receipt but a destination exists")
                else:
                    r = json.loads((run / "receipt.json").read_text())
                    if r.get("status") != "VALIDATED_AND_PUBLISHED":
                        cell["state"] = "REFUSED"; cell["failure"] = r.get("failure"); cell["validator_exit"] = r.get("validator_exit")
                        if dest.exists(): bad("refused run has a published destination")
                        if (exp / "manifest.json").exists(): bad("refused run has an export manifest")
                    else:
                        cell["state"] = "PUBLISHED"
                        if r.get("validator_exit") != 0: bad("validator exit not 0")
                        if r.get("auth_copy_absent") is not True: bad("auth copy not shown absent")
                        if (run / "codex-home/auth.json").exists(): bad("auth copy present")
                        cell["model"] = r.get("evaluation_model", {}).get("name")
                        if cell["model"] != "gpt-6-astra": bad(f"model {cell['model']}")
                        if (exp / "failure.json").exists(): bad("failure.json present")
                        if not (exp / "manifest.json").exists(): bad("no export manifest")
                        elif not dest.exists(): bad("no published file")
                        else:
                            m = json.loads((exp / "manifest.json").read_text())
                            if m.get("status") != "EXPORTED_VALIDATED_REPEAT": bad(f"manifest status {m.get('status')}")
                            if m.get("copy_validator_exit") != 0: bad("copy validator exit not 0")
                            if m.get("prompt_equals_run1") is not True: bad("prompt not equal to first scoring")
                            if (m.get("scoring_replicate"), m.get("generation_replicate")) != (k, g): bad("manifest replicate indices differ")
                            if cell.get("attempt") == 2:
                                if m.get("attempt") != 2: bad("replacement manifest does not say attempt 2")
                                ref = m.get("refused_attempt_receipt") or {}
                                if cell["attempt1_receipt_sha256"] not in json.dumps(ref): bad("replacement manifest lacks the refused attempt-1 receipt hash")
                            elif "attempt" in m: bad("ordinary manifest carries an attempt field")
                            h = sha(dest); cell["sha256"] = h
                            if not (h == m.get("destination_sha256") == m.get("source_output_sha256") == r.get("output_sha256") == r.get("validator_input_sha256")):
                                bad("published, manifest, runner and validated hashes are not all equal")
                            if (exp / "staged-evaluation.json").exists() and sha(exp / "staged-evaluation.json") != h: bad("staged copy differs")
                            text = dest.read_text(); d = json.loads(text)
                            if d.get("instrument_id") != INST or d.get("version") != "6.0": bad("instrument mismatch")
                            hits = [t for t in LEAKS if t in text]
                            if hits: bad(f"leak tokens {hits}")
                cells.append(cell)
published = sorted(str(p.relative_to(W)) for p in (W / "data/evaluation_repeats").rglob("*_evaluation.json"))
expected = sorted(str((W / "data/evaluation_repeats" / INST / f"scoring_rep{c['scoring']}" / f"{c['rubric']}_semantic" /
                       f"{c['project']}_{LABEL}{c['generation_rep']}_evaluation.json").relative_to(W)) for c in cells if c["state"] == "PUBLISHED")
if published != expected: problems.append(f"published files on disk ({len(published)}) differ from published cells ({len(expected)})")
chk = subprocess.run(["shasum", "-a", "256", "-c", str(E / "evaluations-before.sha256")], cwd=W, capture_output=True, text=True)
first_ok = sum(line.endswith(": OK") for line in chk.stdout.splitlines())
if chk.returncode != 0 or first_ok != 30: problems.append(f"first scorings: {first_ok} of 30 verify, exit {chk.returncode}")
counts = {}
for c in cells: counts[c["state"]] = counts.get(c["state"], 0) + 1
for p in problems: print("PROBLEM", p)
for c in cells:
    if c.get("attempt") == 2: print(f"REPLACEMENT attempt 2 {c['state']}: generation rep{c['generation_rep']} {c['project']} {c['rubric']} scoring {c['scoring']} (attempt 1 refused: {c['attempt1_failure']})")
    if c["state"] != "PUBLISHED": print(f"{c['state']}: generation rep{c['generation_rep']} {c['project']} {c['rubric']} scoring {c['scoring']}" + (f" ({c['failure']})" if c.get("failure") else ""))
print(f"cells {len(cells)}; " + "; ".join(f"{k} {v}" for k, v in sorted(counts.items())) + f"; published files on disk {len(published)}; first scorings verified {first_ok}/30; problems {len(problems)}")
OUT.write_text(json.dumps({"instrument": INST, "counts": counts, "first_scorings_verified": first_ok, "problems": problems, "cells": cells}, indent=1))
sys.exit(1 if problems else 0)
