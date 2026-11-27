#!/usr/bin/env python3
"""Purpose: write the root-scope declarations that the root-scope v6 instrument needs
for the 15 records of series 2026-11-22b (claudecode_agent, labels
2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1..3), one per record:
data/evaluation_scope/2026-11-22b/<label>/<PROJECT>.scope.json with exactly the keys
policy (root_dataset_v1), input_sha256 (sha256 of the record's bytes) and reason.
The reason mirrors the 2026-11-25c declarations word for word except for the series
name, so the two series' scope inputs differ only where they must. Refuses to
overwrite an existing declaration. Owner word: "yes" relayed by the watcher at
2026-11-26T06:33Z to rescoring this series on root-scope v6 with scope declarations.
Inputs: argv[1] repository root. Outputs: 15 files; a line per file on stdout.
Date: 2026-11-26 (UTC). Lead: Claude lead."""
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
LABEL = "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep"
REASON = ("The owner selected the complete submitted datasheet as the common comparison unit for every record of "
          "series 2026-11-22b. Component entries remain part of that unmodified record; this declaration does not "
          "assert identical underlying release coverage or infer applicability predicates.")
for g in (1, 2, 3):
    for project in ("AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC"):
        record = root / "data/d4d_concatenated/claudecode_agent" / f"{LABEL}{g}" / f"{project}_d4d.yaml"
        out = root / "data/evaluation_scope/2026-11-22b" / f"{LABEL}{g}" / f"{project}.scope.json"
        if out.exists(): raise SystemExit(f"refusing to overwrite {out.relative_to(root)}")
        digest = hashlib.sha256(record.read_bytes()).hexdigest()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"input_sha256": digest, "policy": "root_dataset_v1", "reason": REASON}, indent=2, sort_keys=True) + "\n")
        print(out.relative_to(root), digest[:16])
