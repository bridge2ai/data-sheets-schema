#!/usr/bin/env python3
"""Check the Zenodo citation metadata added before the first Zenodo-archived release (2026-11-10).

Purpose: CITATION.cff is what Zenodo reads for authors, ORCIDs and affiliations when no .zenodo.json exists, and
GitHub shows "Cite this repository" only for a valid file. No CFF validator is installed offline, so this checks
the CFF 1.2.0 required fields and shapes, the ORCID checksum (ISO 7064 mod 11-2), that `version` equals the
schema's declared version, and that the files whose cookiecutter "My Name" placeholder was replaced still parse
and hold no placeholder.
Inputs: the repository root (argv[1], default "."). Outputs: one line per check; exit 1 on any failure.
Serves: the Zenodo-GitHub integration PR (cookiecutter placeholders + CITATION.cff). Written by claude, 2026-11-10.
"""
import json
import re
import sys
from pathlib import Path

import yaml

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
failures = []


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        failures.append(what)


def orcid_checksum_ok(orcid):
    digits = orcid.replace("-", "")
    total = 0
    for ch in digits[:-1]:
        total = (total + int(ch)) * 2
    result = (12 - total % 11) % 11
    expected = "X" if result == 10 else str(result)
    return digits[-1] == expected


cff = yaml.safe_load((root / "CITATION.cff").read_text(encoding="utf-8"))
check(isinstance(cff, dict), "CITATION.cff parses to a mapping")
for key in ("cff-version", "message", "title", "authors"):
    check(key in cff, f"CITATION.cff has required key {key!r}")
check(cff.get("cff-version") == "1.2.0", "cff-version is 1.2.0")
check(cff.get("type") in ("software", "dataset"), "type is software or dataset")
authors = cff.get("authors") or []
check(isinstance(authors, list) and len(authors) >= 1, "authors is a non-empty list")
for i, a in enumerate(authors):
    check(isinstance(a, dict) and ("family-names" in a or "name" in a), f"author {i} has family-names or name")
    orcid = (a or {}).get("orcid")
    if orcid is not None:
        m = re.fullmatch(r"https://orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", orcid)
        check(bool(m), f"author {i} ORCID is an https://orcid.org/ URL")
        check(bool(m) and orcid_checksum_ok(m.group(1)), f"author {i} ORCID checksum is valid")
check(cff.get("license") == "MIT", "license is the SPDX id MIT")
for key in ("repository-code", "url"):
    check(str(cff.get(key, "")).startswith("https://"), f"{key} is an https URL")
check(all(isinstance(k, str) for k in cff.get("keywords", [])), "keywords are strings")

schema = yaml.safe_load((root / "src/data_sheets_schema/schema/data_sheets_schema.yaml").read_text(encoding="utf-8"))
check(str(cff.get("version")) == str(schema.get("version")),
      f"CITATION.cff version {cff.get('version')!r} equals the schema's declared version {schema.get('version')!r}")

pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
authors_pp = (pyproject.get("tool", {}).get("poetry", {}) or pyproject.get("project", {})).get("authors", [])
check(bool(authors_pp), "pyproject.toml parses and declares authors")
check(json.loads((root / ".cruft.json").read_text(encoding="utf-8")) is not None, ".cruft.json parses")
check(isinstance(yaml.safe_load((root / "about.yaml").read_text(encoding="utf-8")), dict), "about.yaml parses")
for name in ("pyproject.toml", "LICENSE", "about.yaml", ".cruft.json", "CITATION.cff"):
    check("My Name" not in (root / name).read_text(encoding="utf-8"), f"{name} holds no 'My Name' placeholder")

print(f"{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
