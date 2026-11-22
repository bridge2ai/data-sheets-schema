#!/usr/bin/env python3
"""Re-record a final agentic D4D run's provenance with the instruction as sent.

Purpose: in the 2026-11-22b series each headless session ends by running
  `d4d provenance record ...` itself. The rendered instruction's recorder line does
  not carry `--prompt-text`, so a session that does not add it leaves a record with
  no instruction (`d4d runs check --strict` then fails: "no instruction recorded").
  This script repeats the session's own last recorder command, unchanged except that
  `--prompt-text` names the launch instruction file the driver actually sent, then
  re-applies the transcript's observed measurements and re-runs the strict run check.
  It changes no datasheet; it rewrites only the provenance record.
Inputs:  <worktree> <replicate number> <project>
Outputs: the run's `<PROJECT>_provenance.yaml` (rewritten by the repository's recorder);
  a "--- re-record" section appended to the run's gate file; exit 0 when the strict run
  check passes afterwards and the recorded request hash equals the launch file's.
Serves:  the final-D4D fast route (owner decision 2026-11-21/22). Date: 2026-11-22.
"""
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

W = Path(sys.argv[1]).resolve()
REP, P = sys.argv[2], sys.argv[3]
LABEL = f"2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep{REP}"
METHOD = "claudecode_agent"
PY = str(W / ".venv/bin/python")
instr = W / f".temp/launch/{P}_{LABEL}.md"
stream = W / f".temp/launch/transcripts/{LABEL}/{P}.stream.jsonl"
observed = W / f".temp/launch/transcripts/{LABEL}/{P}.observed.json"
gate = W / f".temp/launch/gates/{P}_{LABEL}.txt"
prov = W / f"data/d4d_concatenated/{METHOD}_core/{LABEL}/{P}_provenance.yaml"
for f in (instr, stream, prov):
    if not f.is_file():
        sys.exit(f"missing: {f}")

# The session's last recorder command that actually names this label.
last = None
for line in stream.open(errors="replace"):
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if event.get("type") != "assistant":
        continue
    for block in (event.get("message") or {}).get("content") or []:
        if block.get("type") == "tool_use" and block.get("name") == "Bash":
            command = (block.get("input") or {}).get("command", "")
            if "provenance record" in command and "--label" in command and "--help" not in command:
                last = command
if last is None:
    sys.exit("no recorder command found in the transcript")

tokens = shlex.split(last)
# Keep from the interpreter that precedes "-m data_sheets_schema.cli provenance record"
# up to the first shell operator or redirection.
try:
    start = max(i for i, t in enumerate(tokens) if t == "-m" and tokens[i + 1:i + 4] ==
                ["data_sheets_schema.cli", "provenance", "record"])
except ValueError:
    sys.exit("recorder command has an unexpected shape:\n" + last[:400])
args = []
for token in tokens[start + 4:]:
    if token in (";", "|", "&&", "||", "&") or token.startswith((">", "2>", "1>", "<")):
        break
    args.append(token)
cleaned, skip = [], False
for token in args:
    if skip:
        skip = False
        continue
    if token in ("--prompt-text", "--prompt-text-env"):
        skip = True
        continue
    cleaned.append(token)
if f"--label" not in cleaned or LABEL not in cleaned or P not in cleaned:
    sys.exit("recorder command does not name this run:\n" + " ".join(cleaned)[:400])

# Some sessions ran only the bare recorder line the rendered instruction prints (no prompt
# file, no condition, no receipt flag, no phases). Complete it from the playbook's own
# template (d4d-full-core.md, "write a LIVE provenance record"), and say so in the gate file.
notes = []
PROMPT = "src/download/prompts/d4d_generic_arm_prompt_v9.md"
if "--prompt" not in cleaned:
    cleaned += ["--prompt", PROMPT]; notes.append("added --prompt (the condition's prompt file)")
if "--condition" not in cleaned:
    cleaned += ["--condition", "generic_v9"]; notes.append("added --condition generic_v9")
if "--receipt-expected" not in cleaned:
    cleaned += ["--receipt-expected"]; notes.append("added --receipt-expected")
if "--phase" not in cleaned:
    core = W / f"data/d4d_concatenated/{METHOD}_core/{LABEL}/{P}_d4d_core.yaml"
    full = W / f"data/d4d_concatenated/{METHOD}/{LABEL}/{P}_d4d.yaml"
    receipt = core.with_name(f"{P}_coverage_receipt.yaml")
    report = core.with_name(f"{P}_reconciliation.md")
    missing = [f.name for f in (full, core, receipt, report) if not (f.is_file() and f.stat().st_size)]
    reconciled = core.is_file() and "Phase 4 reconciliation: completed" in core.read_text(errors="replace")[:4000]
    if missing or not reconciled:
        sys.exit(f"cannot attest phases: missing {missing}, core header says reconciled: {reconciled}")
    for phase in (
        {"name": "generate_full", "completed": True, "artifacts": [full.name, receipt.name]},
        {"name": "derive_core", "completed": True, "artifacts": [core.name]},
        {"name": "source_audit", "completed": True},
        {"name": "reconcile", "completed": True},
        {"name": "report", "completed": True, "artifacts": [report.name]},
    ):
        cleaned += ["--phase", json.dumps(phase)]
    notes.append("the session passed no --phase: five phases attested here by the orchestrator from the "
                 "artifacts on disk and the core header's 'Phase 4 reconciliation: completed' line; "
                 "no iteration counts or repair phases are claimed")
command = [PY, "-m", "data_sheets_schema.cli", "provenance", "record", *cleaned,
           "--prompt-text", str(instr.relative_to(W))]

out = [f"--- re-record with the instruction as sent ({instr.name})"] + ["note: " + n for n in notes]
done = subprocess.run(command, cwd=W, capture_output=True, text=True)
out.append(f"recorder exit {done.returncode}")
out += [x for x in (done.stdout + done.stderr).strip().splitlines()[-4:]]
if done.returncode == 0 and observed.is_file():
    ann = subprocess.run([PY, "-m", "data_sheets_schema.cli", "provenance", "annotate-observed",
                          "--project", P, "--method", METHOD, "--label", LABEL,
                          "--run", json.dumps(json.loads(observed.read_text()))],
                         cwd=W, capture_output=True, text=True)
    out.append(f"annotate-observed exit {ann.returncode}")
# A record a session wrote with the bare recorder line carries no validation block, and the
# strict run check refuses it ("nothing to verify"). `d4d runs validate` validates both
# records and writes the block; it skips a run that already records a result.
validate = subprocess.run([PY, "-m", "data_sheets_schema.cli", "runs", "validate", "--method", METHOD,
                           "--label", LABEL, "--project", P], cwd=W, capture_output=True, text=True)
out += [x.strip() for x in validate.stdout.splitlines() if "valid" in x][-1:]
out.append(f"runs validate exit {validate.returncode}")
check = subprocess.run([PY, "-m", "data_sheets_schema.cli", "runs", "check", "--method", METHOD,
                        "--label", LABEL, "--project", P, "--strict"],
                       cwd=W, capture_output=True, text=True)
out += [x for x in check.stdout.splitlines() if any(k in x for k in ("failing", "satisfy", "unverifiable", "missing", "mismatch"))]
out.append(f"runs_check_exit_after_rerecord {check.returncode}")

import yaml  # the worktree's interpreter is not needed for this read
record = yaml.safe_load(prov.read_text())
recorded = ((record.get("prompts") or {}).get("request") or {}).get("sha256")
sent = hashlib.sha256(instr.read_bytes()).hexdigest()
out.append(f"recorded request sha256 {recorded}")
out.append(f"launch file sha256      {sent}")
ok = done.returncode == 0 and check.returncode == 0 and recorded == sent
out.append("RERECORD: " + ("PASS" if ok else "FAIL"))
with gate.open("a") as handle:
    handle.write("\n".join(out) + "\n")
print("\n".join(out))
sys.exit(0 if ok else 1)
