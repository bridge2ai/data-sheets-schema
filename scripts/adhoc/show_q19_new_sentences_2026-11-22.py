# Purpose: print, with their source file and the rating's listed-absent context,
#   the five recommendation sentences and the one neighbouring-clause reason the
#   2026-11-22 general_context_v3 evaluations add to the Q19 corpus pins, so a
#   reviewer can check each hand-read class against its own rating.
# Inputs: data/evaluation_llm/rubric{10,20}_semantic/2026-11-22_general_context_v3/*.json
# Outputs: stdout only. Serves: PR 6309 review. Date: 2026-11-22.
import json, re, sys
from pathlib import Path
frags = ["Add structured derivation links (raw audio and REDCap sources",
         "Add top-level resources/parent_datasets links and a confidentiality_level",
         "Populate regulatory_restrictions.confidentiality_level and link",
         "Populate the dedicated fields where source information exists",
         "Record a confidentiality classification, IP restrictions",
         "was_derived_from or entity-activity-agent structure."]
def strings(v, path=""):
    if isinstance(v, str): yield path, v
    elif isinstance(v, dict):
        for k, x in v.items(): yield from strings(x, f"{path}/{k}")
    elif isinstance(v, list):
        for i, x in enumerate(v): yield from strings(x, f"{path}[{i}]")
for f in sorted(Path("data/evaluation_llm").glob("rubric*_semantic/2026-11-22_general_context_v3/*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    for path, s in strings(d):
        for fr in frags:
            if fr in s:
                print(f"== {f.relative_to('data/evaluation_llm')} :: {path}\n   FRAGMENT: {fr}\n   TEXT: {s[:900]}\n")
