#!/usr/bin/env python3
"""Evidence-boundary audit of the final agentic D4D transcripts (series 2026-11-22b + canary).

Purpose: the driver's gate checked only Read-tool paths. Each worktree also holds the whole
  historical corpus, each label directory holds that replicate's other projects, and sessions
  left scratch files. This audit reads every tool call in every transcript (Bash, Read, Edit,
  Write, Grep, Glob) and reports any that touches:
    - data/d4d_concatenated outside the run's own project files in its own label directories;
    - data/ro-crate_packages, data/evaluation*, data/d4d_html, data/ATTIC;
    - a recursive grep/find/ls over data/ or data/d4d_concatenated;
    - another project's files under .temp/.
  It also reports, per run, whether the transcript shows the core being derived by command and
  the pair/receipt checkers being run (needed where the orchestrator attested the phases).
Inputs:  none (paths below).
Outputs: stdout table; <notes>/boundary_audit.tsv; exit 0 when no run has a boundary hit.
Serves:  the final-D4D fast route (owner decision 2026-11-21/22). Date: 2026-11-22.
"""
import json
import re
import sys
from pathlib import Path

E = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions")
A = E / "fast-d4d-20261121"
HOLD = E / "fast-d4d-hold-20261122"
PROJECTS = ["AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC"]
runs = []
for rep, W in ((1, A), (2, E / "fast-d4d-20261121-rep2"), (3, E / "fast-d4d-20261121-rep3")):
    label = f"2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep{rep}"
    for P in PROJECTS:
        runs.append((P, f"rep{rep}", label, W / f".temp/launch/transcripts/{label}/{P}.stream.jsonl"))
canary_label = "2026-11-22_claude-opus-5-5-claudecode-generic-v9_rep1"
canary = sorted((HOLD / "canary_advisor_on/temp/launch/transcripts" / canary_label).glob("*.jsonl"))
if canary:
    runs.append(("AI_READI", "canary", canary_label, canary[0]))

OTHER_DATA = re.compile(r"data/(ro-crate_packages|evaluation[a-z_]*|d4d_html|ATTIC|d4d_individual)\b")
RECURSIVE = re.compile(r"\b(grep\s+(-[A-Za-z]*[rR][A-Za-z]*|--recursive)|rg\b|find|ls\s+-[A-Za-z]*R)\b[^|;&]*\bdata(/d4d_concatenated)?/?(\s|$|['\"])")
D4D_PATH = re.compile(r"data/d4d_concatenated/[^\s'\"`;|&)>]*")


def hits_for(text, project, label):
    found = []
    # A command that sets L=<own label> and uses $L or f-strings still names only its own label.
    expanded = text.replace("${L}", label).replace("$L", label).replace("{L}", label).replace("$LABEL", label) \
                   .replace("${LABEL}", label).replace("{LABEL}", label).replace("$VERSION", label) \
                   .replace("${VERSION}", label).replace("{VERSION}", label)
    # Resolve the command's own simple assignments (D=<label>, lab = '<label>', ...) so a path
    # written through a variable is judged by the value the command gave it.
    for name, value in re.findall(r"\b([A-Za-z_]\w*)\s*=\s*f?['\"]?(2026-11-22b?_[\w.\-]+)", text):
        for form in ("${%s}" % name, "$%s" % name, "{%s}" % name):
            expanded = expanded.replace(form, value)
    # A listing of the method directory piped through grep for the run's own series shows the
    # session only names in that series; reported separately, not as a read of other outputs.
    if re.search(r"ls\s+data/d4d_concatenated/claudecode_agent(_core)?/?\s*\|\s*grep\s+['\"]?2026-11-22b", expanded):
        found.append(("listing filtered to its own series", "ls <method dir> | grep 2026-11-22b"))
        expanded = re.sub(r"ls\s+data/d4d_concatenated/claudecode_agent(_core)?/?\s*\|", "ls <method dir> |", expanded)
    for match in D4D_PATH.finditer(expanded):
        path = match.group(0).rstrip("/.,:")
        own_dir = re.fullmatch(rf"data/d4d_concatenated/claudecode_agent(_core)?/{re.escape(label)}/?", path)
        own_file = re.match(rf"data/d4d_concatenated/claudecode_agent(_core)?/{re.escape(label)}/{project}_", path)
        variable = "$" in path or "{" in path
        if own_dir or own_file:
            continue
        found.append(("other d4d path" if not variable else "d4d path with an unexpanded variable", path[:110]))
    if OTHER_DATA.search(expanded):
        found.append(("other data tree", OTHER_DATA.search(expanded).group(0)))
    if RECURSIVE.search(expanded):
        found.append(("recursive search over data/", RECURSIVE.search(expanded).group(0)[:90]))
    for other in PROJECTS:
        if other != project and re.search(rf"\.temp/[^\s'\"]*\b{other}_", expanded):
            found.append(("another project's .temp file", other))
    return found


rows, total_hits = [], 0
for project, rep, label, path in runs:
    if not path.is_file():
        rows.append([project, rep, "TRANSCRIPT MISSING", "", "", "", "", ""]); total_hits += 1
        continue
    calls = hits = filtered_listings = 0
    derive = pair = receipts = False
    examples = []
    for line in path.open(errors="replace"):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") != "assistant":
            continue
        for block in (event.get("message") or {}).get("content") or []:
            if block.get("type") != "tool_use":
                continue
            calls += 1
            data = block.get("input") or {}
            text = " ".join(str(data.get(k, "")) for k in ("command", "file_path", "path", "pattern", "glob"))
            if block.get("name") == "Bash":
                command = data.get("command", "")
                derive = derive or bool(re.search(r"\bderive\b.*(core|--full)|d4d_core\.yaml.*--out|core derive|schema derive|derive-core", command))
                pair = pair or bool(re.search(r"pair|consisten", command))
                receipts = receipts or "receipts check" in command
            for kind, what in hits_for(text, project, label):
                if kind == "listing filtered to its own series":
                    filtered_listings += 1
                    continue
                hits += 1
                if len(examples) < 3:
                    examples.append(f"{block.get('name')}: {kind}: {what}")
    total_hits += hits
    rows.append([project, rep, calls, hits, filtered_listings, "yes" if derive else "NO",
                 "yes" if receipts else "NO", " || ".join(examples)])

header = ["project", "run", "tool_calls", "boundary_hits", "own_series_filtered_listings", "core_derived_by_command", "receipts_check_run", "examples"]
out = A / "notes/final_agentic_2026-11-22/boundary_audit.tsv"
out.write_text("\n".join("\t".join(str(c) for c in r) for r in [header] + rows) + "\n")
for r in [header] + rows:
    print("\t".join(str(c) for c in r)[:230])
print(f"\ntotal boundary hits: {total_hits}; table: {out}")
sys.exit(1 if total_hits else 0)
