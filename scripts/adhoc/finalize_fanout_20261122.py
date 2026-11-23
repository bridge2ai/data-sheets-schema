#!/usr/bin/env python3
"""Uniformity pass and summary table for the 2026-11-22b final agentic D4D series.

Purpose: after the three replicate drivers finish, make every run's provenance record
  uniform and summarise the series. For each of the 15 runs it (1) compares the request
  hash the record carries with the launch instruction file the driver sent, (2) re-records
  with rerecord_instruction_20261122.py when they differ, the instruction is missing or the
  strict run check fails, (3) re-runs the strict run check and the strict receipt check,
  and (4) writes one row per run.
Inputs:  none (paths below). Run with any Python that has PyYAML.
Outputs: <hold>/series_2026-11-22b_summary.tsv and the same table on stdout; exit 0 when all
  15 runs end with a passing strict run check, a passing receipt check and matching hashes.
Serves:  the final-D4D fast route (owner decision 2026-11-21/22). Date: 2026-11-22.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

E = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions")
HERE = Path(__file__).resolve().parent
WORKTREES = {1: E / "fast-d4d-20261121", 2: E / "fast-d4d-20261121-rep2", 3: E / "fast-d4d-20261121-rep3"}
PROJECTS = ["AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC"]
METHOD = "claudecode_agent"
OUT = E / "fast-d4d-hold-20261122" / "series_2026-11-22b_summary.tsv"


def run(py, cwd, *args):
    return subprocess.run([py, "-m", "data_sheets_schema.cli", *args], cwd=cwd, capture_output=True, text=True)


rows, bad = [], 0
for rep, W in WORKTREES.items():
    label = f"2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep{rep}"
    py = str(W / ".venv/bin/python")
    for P in PROJECTS:
        core_dir = W / f"data/d4d_concatenated/{METHOD}_core/{label}"
        prov = core_dir / f"{P}_provenance.yaml"
        full = W / f"data/d4d_concatenated/{METHOD}/{label}/{P}_d4d.yaml"
        instr = W / f".temp/launch/{P}_{label}.md"
        gate = W / f".temp/launch/gates/{P}_{label}.txt"
        if not (prov.is_file() and full.is_file() and instr.is_file()):
            rows.append([P, rep, "MISSING OUTPUTS", "", "", "", "", "", "", ""]); bad += 1
            continue
        sent = hashlib.sha256(instr.read_bytes()).hexdigest()

        def recorded():
            d = yaml.safe_load(prov.read_text())
            return ((d.get("prompts") or {}).get("request") or {}).get("sha256"), d

        sha, _ = recorded()
        check = run(py, W, "runs", "check", "--method", METHOD, "--label", label, "--project", P, "--strict")
        repaired = "no"
        if sha != sent or check.returncode != 0:
            fix = subprocess.run([py, str(HERE / "rerecord_instruction_20261122.py"), str(W), str(rep), P],
                                 capture_output=True, text=True)
            repaired = "yes" if fix.returncode == 0 else "REPAIR FAILED"
            sha, _ = recorded()
            check = run(py, W, "runs", "check", "--method", METHOD, "--label", label, "--project", P, "--strict")
        receipts = run(py, W, "--manifest", "data/preprocessed/source_manifest.yaml", "receipts", "check",
                       "--method", METHOD, "--label", label, "--project", P,
                       "--bundle", f"data/preprocessed/concatenated/{P}_preprocessed.txt",
                       "--chunk-manifest", f"data/preprocessed/chunks/{P}_chunks.yaml", "--strict")
        text = receipts.stdout
        chunks = (re.search(r"chunks (\d+/\d+)", text) or [None, "?"])[1]
        snippets = (re.search(r"snippets (\d+/\d+)", text) or [None, "?"])[1]
        slots = (re.search(r"slots (\d+/\d+)", text) or [None, "?"])[1]
        gtext = gate.read_text() if gate.is_file() else ""
        minutes = (re.search(r"minutes ([\d.]+)", gtext) or [None, "?"])[1]
        advisor = (re.search(r"advisor calls: (\d+)", gtext) or [None, "?"])[1]
        transcript_ok = "ok" if "TRANSCRIPT: ok" in gtext else "NOT OK"
        _, d = recorded()
        # Read the repair history from the gate file, so a run repaired before this pass is
        # still reported as repaired (the first table said "no" for six of seven).
        gtext = gate.read_text() if gate.is_file() else ""
        if "RERECORD: PASS" in gtext:
            repaired = "yes"
        phases_by = "orchestrator" if "attested here by the orchestrator" in gtext else "session"
        ok = (check.returncode == 0 and receipts.returncode == 0 and sha == sent and transcript_ok == "ok"
              and advisor == "0" and repaired != "REPAIR FAILED")
        bad += 0 if ok else 1
        rows.append([P, rep, "PASS" if ok else "FAIL", minutes, chunks, snippets, slots, advisor,
                     f"{repaired} (phases attested by {phases_by})", full.stat().st_size])

header = ["project", "rep", "result", "minutes", "chunks", "snippets_verified", "slots_with_receipt",
          "advisor_calls", "record_repaired", "full_yaml_bytes"]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join("\t".join(str(c) for c in r) for r in [header] + rows) + "\n")
for r in [header] + rows:
    print("\t".join(str(c) for c in r))
print(f"\n{len(rows) - bad} of {len(rows)} runs pass; table: {OUT}")
sys.exit(1 if bad else 0)
