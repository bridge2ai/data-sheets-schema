#!/usr/bin/env python3
"""Purpose: write the provenance table of the triplicate root-scope v6 scoring of the
2026-11-25c series: one row per record x rubric x scoring number (90 cells), with the
attempt that was published, the points, the published file's sha256 and repository
path, or "not measured" with the refusal reason. Refused attempts are listed even when
a replacement was published. Reads the cell states from the JSON that
verify_root_scope_repeats_20261126.py wrote (which never opens a refused output), and
the points from the published files only.
Inputs: argv[1] repository root holding the 90 files (scoring 1 under
data/evaluation_llm/.../label_aware/<instrument>/, scorings 2 and 3 under
data/evaluation_repeats/<instrument>/); argv[2] verification JSON.
Outputs: TSV to argv[3]. No absolute path is written.
Serves: PR 6372. Date: 2026-11-26 (UTC). Lead: Claude lead."""
import hashlib, json, pathlib, sys
root, verification, out = pathlib.Path(sys.argv[1]), json.loads(pathlib.Path(sys.argv[2]).read_text()), pathlib.Path(sys.argv[3])
INST = verification["instrument"]; LABEL = "2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep"
PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC")
if verification["problems"]: raise SystemExit("verification reported problems; no table written")
cells = {(c["project"], c["generation_rep"], c["rubric"], c["scoring"]): c for c in verification["cells"]}
def published(rel):
    p = root / rel; raw = p.read_bytes(); d = json.loads(raw)
    if d["instrument_id"] != INST: raise SystemExit(f"instrument mismatch {rel}")
    return d["overall_score"]["total_points"], d["overall_score"]["max_points"], hashlib.sha256(raw).hexdigest()
rows = ["project\tgeneration_rep\trubric\tscoring\tstate\tpublished_attempt\tpoints\tmax_points\tsha256\tpath\trefused_attempts\trefusal_reason"]
for project in PROJECTS:
    for g in (1, 2, 3):
        for fam in ("rubric10", "rubric20"):
            for k in (1, 2, 3):
                name = f"{project}_{LABEL}{g}_evaluation.json"
                if k == 1:
                    rel = f"data/evaluation_llm/{fam}_semantic/label_aware/{INST}/{name}"
                    pts, mx, h = published(rel); rows.append(f"{project}\t{g}\t{fam}\t1\tmeasured\t1\t{pts}\t{mx}\t{h}\t{rel}\t0\t")
                    continue
                c = cells[(project, g, fam, k)]; rel = f"data/evaluation_repeats/{INST}/scoring_rep{k}/{fam}_semantic/{name}"
                attempt = c.get("attempt", 1)
                refusals = [c["attempt1_failure"]] if attempt == 2 else []
                if c["state"] == "REFUSED": refusals.append(c["failure"])
                reason = " | ".join(r.replace("\t", " ") for r in refusals)
                if c["state"] == "PUBLISHED":
                    pts, mx, h = published(rel)
                    if h != c["sha256"]: raise SystemExit(f"sha mismatch against verification {rel}")
                    rows.append(f"{project}\t{g}\t{fam}\t{k}\tmeasured\t{attempt}\t{pts}\t{mx}\t{h}\t{rel}\t{len(refusals)}\t{reason}")
                elif c["state"] == "REFUSED":
                    if (root / rel).exists(): raise SystemExit(f"refused cell has a file {rel}")
                    rows.append(f"{project}\t{g}\t{fam}\t{k}\tnot measured\t\t\t\t\t\t{len(refusals)}\t{reason}")
                else: raise SystemExit(f"cell not finished: {c['job']} {c['state']}")
out.write_text("\n".join(rows) + "\n")
print(f"rows {len(rows) - 1}; measured {sum(1 for r in rows[1:] if chr(9) + 'measured' + chr(9) in r)}; not measured {sum(1 for r in rows[1:] if 'not measured' in r)}; replaced {sum(1 for r in rows[1:] if r.split(chr(9))[5] == '2')}")
