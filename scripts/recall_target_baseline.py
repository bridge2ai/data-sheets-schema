#!/usr/bin/env python
"""Offline baseline of the recall-target slots, per record and per arm (#2930).

Reviewers explained the rubric20 fall from v6 to v7/v8 by "empty derivation
slots where lineage is documented in prose instead, absent variable
metadata, and unpinned tool versions" (`notes/generic_v8_analysis_plan.md`).
Before any recall rule or omission inventory is registered, this counts what
the existing arms carry on exactly those targets, and writes the table to
`notes/recall_target_baseline.md`. The records, receipts and bundles are
only read.

Per full record, at any depth of the record:

- **lineage**: populated `was_derived_from` values and `parent_datasets`
  entries (a list counts its populated members, a populated scalar one);
- **variables**: populated `variables` entries;
- **versioned software**: `used_software` entries (the schema's `Software`
  range) whose `version` is populated, beside all `used_software` entries;
  and `tools` strings (`MachineAnnotationTools.tools`, "ToolName version" by
  its description) that carry a version-like token, beside all `tools`
  strings. The `tools` half is a regular expression over a free string.

Per coverage receipt, the chunks marked `nothing_relevant` or
`redundant_with` whose text carries a lineage, variable or version cue
(`CUES`). That list is **lexical**: a cue is a regular-expression match over
the chunk's whitespace-collapsed text, not a finding that the chunk holds a
fact the record lacks. The chunk text is the bytes the record hashed
(`inputs.bundle_md5`/`bundle_sha256`): the bundle on disk where it still
hashes to them, else the committed version that does
(`provenance.bundle_bytes_for`, #1140), chunked under the record's own
`inputs.chunks.rule`. A record with no receipt reads None on every receipt
column, never 0, and so does one whose chunk text cannot be recovered; the
note says which and why.

The arms are fixed here (`ARMS`), copied from `scripts/arm_comparison.py`
plus the single v9 canary, so a later edit to that table does not silently
move this baseline. A record its own validation block declares invalid is
listed and not counted, as `arm_comparison.py` does (#1029). The note names
each counted record's sha256 and its receipt's, so a record amended later
makes the note stale rather than quietly describing other bytes; a
corpus-lane test regenerates it and compares the committed bytes.

Usage:
    poetry run python scripts/recall_target_baseline.py            # rewrite the note
    poetry run python scripts/recall_target_baseline.py --check    # read-only: exit 1 when stale
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

CORPUS = ROOT / "data" / "d4d_concatenated"
OUT_MD = ROOT / "notes" / "recall_target_baseline.md"
PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE")
#: The two directories a generic-arm label can live in (#690): agentic and
#: API runs through v7 under the first, the API baseline from v8 the second.
METHODS = ("claudecode_agent", "claudecode_api")

#: (key, display, labels). The first seven are `scripts/arm_comparison.py`'s
#: ARMS as of #2930; a test holds them equal where both name an arm. The v9
#: canary is a single API CHORUS record (the only v9 run on main), shown so
#: the comparator the analysis plan will name is on the table, not chosen.
ARMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("v4", "v4 API (2026-08-13)",
     tuple(f"2026-08-13_claude-opus-5-api-generic-v4_rep{r}" for r in (1, 2, 3))),
    ("v5api", "v5 API (2026-08-22c)",
     tuple(f"2026-08-22c_claude-opus-5-api-generic-v5_rep{r}" for r in (1, 2, 3))),
    ("v5agentic", "v5 agentic (2026-08-24)",
     tuple(f"2026-08-24_claude-opus-5-claudecode-generic-v5_rep{r}" for r in (1, 2, 3))),
    ("v6agentic", "v6 agentic (2026-08-28)",
     tuple(f"2026-08-28_claude-opus-5-claudecode-generic-v6_rep{r}" for r in (1, 2, 3))),
    ("v7api", "v7 API canaries (2026-08-28…d, exploratory)",
     ("2026-08-28_claude-opus-5-api-generic-v7_rep1", "2026-08-28b_claude-opus-5-api-generic-v7_rep1",
      "2026-08-28c_claude-opus-5-api-generic-v7_rep1", "2026-08-28d_claude-opus-5-api-generic-v7_rep1")),
    ("v7prod", "v7 API production (2026-09-01)",
     tuple(f"2026-09-01_claude-opus-5-api-generic-v7_rep{r}" for r in (1, 2, 3))),
    ("v8prod", "v8 API production (2026-09-04f/g)",
     tuple(f"2026-09-04f_claude-opus-5-api-generic-v8_rep{r}" for r in (1, 2, 3))
     + tuple(f"2026-09-04g_claude-opus-5-api-generic-v8_rep{r}" for r in (1, 2, 3))),
    ("v9canary", "v9 API canary (2026-09-12, CHORUS only)",
     ("2026-09-12_claude-opus-5-api-generic-v9_rep1",)),
)

LINEAGE_KEYS = ("was_derived_from", "parent_datasets")
VARIABLE_KEYS = ("variables",)
REVIEWED_ELSEWHERE = ("nothing_relevant", "redundant_with")

#: A version-like token: `v1.2`, `1.2.3`, `version 2`, `release 4.0`. Applied
#: to a `tools` string to say whether it names a version, and (as the
#: `version` cue class) to chunk text.
_VERSION_TOKEN = r"(?:\bv\d+(?:\.\d+)+\b|\b\d+\.\d+(?:\.\d+)+\b|\b(?:version|release)\s*:?\s*v?\d+(?:\.\d+)*\b)"
VERSION_TOKEN = re.compile(_VERSION_TOKEN, re.IGNORECASE)

#: The lexical cues, by class. Case-insensitive, over whitespace-collapsed
#: chunk text. Recorded in the note by id; changing one changes the note.
CUES: dict[str, tuple[tuple[str, str], ...]] = {
    "lineage": (
        ("lin.derived-from", r"\bderived\s+from\b"),
        ("lin.derivation", r"\bderivations?\b"),
        ("lin.lineage", r"\blineage\b"),
        ("lin.provenance", r"\bprovenance\b"),
        ("lin.parent", r"\bparent\s+(?:dataset|data\s+set|study|cohort|project)s?\b"),
        ("lin.subset-of", r"\bsub-?sets?\s+of\b"),
        ("lin.source-dataset", r"\bsource\s+(?:dataset|data\s+set)s?\b"),
    ),
    "variables": (
        ("var.variable", r"\bvariables?\b"),
        ("var.data-dictionary", r"\bdata\s+dictionar(?:y|ies)\b"),
        ("var.codebook", r"\bcode\s?books?\b"),
        ("var.column", r"\bcolumns?\b"),
        ("var.data-element", r"\bdata\s+elements?\b"),
        ("var.field-name", r"\bfield\s+names?\b"),
    ),
    "version": (
        ("ver.version-token", _VERSION_TOKEN),
    ),
}
_COMPILED = {cls: tuple((pid, re.compile(rx, re.IGNORECASE)) for pid, rx in pats) for cls, pats in CUES.items()}


def cues_sha256() -> str:
    """The cue patterns' identity, printed into the note."""
    body = "".join(f"{cls}\t{pid}\t{rx}\n" for cls, pats in CUES.items() for pid, rx in pats)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _populated(value: Any) -> bool:
    """`receipts._populated`'s reading, applied through nesting: a value is
    populated when some leaf under it is neither None nor empty."""
    if isinstance(value, dict):
        return any(_populated(v) for v in value.values())
    if isinstance(value, list):
        return any(_populated(v) for v in value)
    return value not in (None, "")


def entries(value: Any) -> list[Any]:
    """A slot's populated entries: a list's populated members, else the
    value itself when populated."""
    if isinstance(value, list):
        return [v for v in value if _populated(v)]
    return [value] if _populated(value) else []


def _walk(node: Any):
    """Every (key, value) pair of every mapping at any depth."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def target_counts(record: dict[str, Any]) -> dict[str, int]:
    """The recall-target counts of one full record (see the module doc)."""
    out = {"was_derived_from": 0, "parent_datasets": 0, "variables": 0,
           "software": 0, "software_versioned": 0, "tools": 0, "tools_versioned": 0}
    for key, value in _walk(record):
        if key in LINEAGE_KEYS or key in VARIABLE_KEYS:
            out[key] += len(entries(value))
        elif key == "used_software":
            for sw in entries(value):
                out["software"] += 1
                out["software_versioned"] += isinstance(sw, dict) and _populated(sw.get("version"))
        elif key == "tools":
            for tool in entries(value):
                out["tools"] += 1
                out["tools_versioned"] += isinstance(tool, str) and bool(VERSION_TOKEN.search(tool))
    out["lineage"] = out["was_derived_from"] + out["parent_datasets"]
    return out


def chunk_cues(text: str) -> dict[str, dict[str, int]]:
    """Per cue class, the matches of each pattern that matched at all."""
    flat = " ".join(text.split())
    found: dict[str, dict[str, int]] = {}
    for cls, pats in _COMPILED.items():
        hits = {pid: len(rx.findall(flat)) for pid, rx in pats}
        hits = {pid: n for pid, n in hits.items() if n}
        if hits:
            found[cls] = hits
    return found


def chunk_texts_for(inputs: dict[str, Any], root: Path) -> tuple[dict[str, str] | None, str]:
    """The record's chunk texts by id, and the basis they were read on; or
    None and why not. The bytes are the ones the record hashed — the bundle
    on disk where it still hashes to them, else the committed version that
    does — and the chunks are the record's own rule over them."""
    from data_sheets_schema.chunking import chunk_text, chunk_texts

    bundle_rel = inputs.get("bundle_path")
    md5, sha = inputs.get("bundle_md5"), inputs.get("bundle_sha256")
    chunks = inputs.get("chunks") or {}
    rule = chunks.get("rule") if isinstance(chunks, dict) else None
    if not bundle_rel or not (md5 or sha):
        return None, "the record declares no bundle path and hash"
    if not isinstance(rule, dict):
        return None, "the record declares no chunk rule"
    raw: bytes | None = None
    basis = ""
    disk = root / bundle_rel
    if disk.is_file():
        b = disk.read_bytes()
        if ((not md5 or hashlib.md5(b).hexdigest() == md5)
                and (not sha or hashlib.sha256(b).hexdigest() == sha)):
            raw, basis = b, "bundle on disk"
    if raw is None:
        from data_sheets_schema.provenance import GitUnavailable, bundle_bytes_for
        try:
            recovered = bundle_bytes_for(bundle_rel, md5=md5, sha256=sha)
        except GitUnavailable as exc:
            return None, f"the bundle drifted and git could not supply the version hashed ({exc})"
        if recovered is None:
            return None, "the bundle drifted and no committed version hashes to the record's"
        raw, basis = recovered[0], "committed version (git)"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, "the bytes hashed are not UTF-8"
    built = chunk_text(text, rule)
    if chunks.get("chunk_count") is not None and len(built) != chunks["chunk_count"]:
        return None, f"the record's rule gives {len(built)} chunks, not the {chunks['chunk_count']} it cites"
    digest = hashlib.sha256(raw).hexdigest()[:12]
    return ({c["id"]: t for c, t in zip(built, chunk_texts(text, built))},
            f"{basis}, bundle sha256 {digest}…")


def receipt_candidates(receipt: dict[str, Any], texts: dict[str, str] | None) -> dict[str, Any]:
    """The receipt's `nothing_relevant`/`redundant_with` chunks and, where the
    chunk text is known, those carrying a cue. `candidates` is None, not [],
    when the text is not known."""
    marked = [c for c in receipt.get("chunks") or []
              if isinstance(c, dict) and c.get("status") in REVIEWED_ELSEWHERE]
    out: dict[str, Any] = {"marked": len(marked),
                           "by_status": {s: sum(c.get("status") == s for c in marked) for s in REVIEWED_ELSEWHERE},
                           "candidates": None, "missing_chunks": []}
    if texts is None:
        return out
    cands = []
    for c in marked:
        text = texts.get(str(c.get("id")))
        if text is None:
            out["missing_chunks"].append(str(c.get("id")))
            continue
        found = chunk_cues(text)
        if found:
            cands.append({"chunk": str(c.get("id")), "status": c["status"], "cues": found})
    out["candidates"] = cands
    return out


def locate(label: str, project: str, corpus: Path) -> tuple[str, Path, Path] | None:
    """(method, full record, provenance record), or None where the label has
    no full record for the project. Two copies is an error, not a choice."""
    found = [(m, corpus / m / label / f"{project}_d4d.yaml",
              corpus / f"{m}_core" / label / f"{project}_provenance.yaml")
             for m in METHODS if (corpus / m / label / f"{project}_d4d.yaml").is_file()]
    if len(found) > 1:
        raise LookupError(f"{label} {project} has a full record under {', '.join(m for m, _, _ in found)}")
    return found[0] if found else None


def _load(raw: bytes) -> Any:
    return yaml.safe_load(raw.decode("utf-8"))


def collect(corpus: Path | None = None, arms=None, root: Path | None = None,
            projects: tuple[str, ...] | None = None) -> dict[str, Any]:
    """One row per record of every arm: its counts, its receipt's, and the
    basis of each. `root` is what a record's repository-relative bundle path
    resolves against (the checkout by default)."""
    corpus, arms, root = corpus or CORPUS, ARMS if arms is None else arms, root or ROOT
    projects = PROJECTS if projects is None else projects
    rows: list[dict[str, Any]] = []
    excluded: list[str] = []
    for key, _, labels in arms:
        for label in labels:
            for project in projects:
                hit = locate(label, project, corpus)
                if hit is None:
                    continue
                method, full, prov = hit
                rel = full.relative_to(corpus).as_posix()
                prov_rec = _load(prov.read_bytes()) if prov.is_file() else {}
                prov_rec = prov_rec if isinstance(prov_rec, dict) else {}
                if (prov_rec.get("validation") or {}).get("passed") is False:
                    excluded.append(rel)
                    continue
                raw = full.read_bytes()
                record = _load(raw)
                row: dict[str, Any] = {
                    "arm": key, "label": label, "project": project, "method": method, "path": rel,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "counts": target_counts(record if isinstance(record, dict) else {}),
                    "receipt": None, "receipt_sha256": None, "text_basis": None,
                }
                rpath = corpus / f"{method}_core" / label / f"{project}_coverage_receipt.yaml"
                if rpath.is_file():
                    rraw = rpath.read_bytes()
                    receipt = _load(rraw)
                    row["receipt_sha256"] = hashlib.sha256(rraw).hexdigest()
                    texts, basis = chunk_texts_for(prov_rec.get("inputs") or {}, root)
                    row["text_basis"] = basis
                    row["receipt"] = receipt_candidates(receipt if isinstance(receipt, dict) else {}, texts)
                rows.append(row)
    return {"rows": rows, "excluded": excluded, "corpus": corpus}


COUNT_COLUMNS = (("lineage", "lineage entries"), ("was_derived_from", "was_derived_from"),
                 ("parent_datasets", "parent_datasets"), ("variables", "variables entries"),
                 ("software_versioned", "used_software with version"), ("software", "used_software"),
                 ("tools_versioned", "tools with version token"), ("tools", "tools"))


def _cell(v: Any) -> str:
    return "–" if v is None else str(v)


def _mean(values: list[int]) -> str:
    return f"{sum(values) / len(values):.1f}" if values else "–"


def arm_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """An arm's sums and per-record means, and its receipt columns over the
    records that carry one; None where no record does."""
    n = len(rows)
    sums = {k: sum(r["counts"][k] for r in rows) for k, _ in COUNT_COLUMNS}
    receipted = [r for r in rows if r["receipt"] is not None]
    readable = [r for r in receipted if r["receipt"]["candidates"] is not None]
    return {
        "records": n, "sums": sums,
        "means": {k: _mean([r["counts"][k] for r in rows]) for k, _ in COUNT_COLUMNS},
        "receipts": len(receipted),
        "marked": sum(r["receipt"]["marked"] for r in receipted) if receipted else None,
        "readable": len(readable),
        "candidates": sum(len(r["receipt"]["candidates"]) for r in readable) if readable else None,
        "by_class": ({cls: sum(cls in c["cues"] for r in readable for c in r["receipt"]["candidates"])
                      for cls in CUES} if readable else None),
    }


def render_markdown(collected: dict[str, Any], arms=None) -> str:
    arms = ARMS if arms is None else arms
    rows = collected["rows"]
    lines = [
        "# Recall-target baseline: lineage, variables and software versions",
        "",
        "Generated by `scripts/recall_target_baseline.py` (#2930). Do not edit by hand: run the",
        "script to regenerate it, or `--check` to ask whether it still matches the records.",
        "",
        "Read-only. Nothing here writes a record, a receipt or a provenance block, and no",
        "prediction is registered here: the comparator baseline for the recall rule is the",
        "analysis plan's to name (#2930).",
        "",
        "## What is counted",
        "",
        "Per full record, at any depth: **lineage** is populated `was_derived_from` values plus",
        "`parent_datasets` entries; **variables** is populated `variables` entries;",
        "**used_software with version** is `used_software` entries whose `version` is populated;",
        "**tools with version token** is `tools` strings carrying a version-like token (a regular",
        "expression over a free string). A count is of what the record carries, not of whether",
        "it is supported. A variables count says nothing about whether the entries are variables",
        "in data files or promoted data-type rows (#2079).",
        "",
        "Per coverage receipt: the chunks marked `nothing_relevant` or `redundant_with`, and among",
        "them the **lexical candidates**, chunks whose text carries a lineage, variable or version",
        "cue. **Lexical** means a regular-expression match over the chunk's whitespace-collapsed",
        "text: a candidate is a chunk to look at, not a finding that the chunk states a fact the",
        "record lacks, and a `redundant_with` chunk's facts may be receipted from the chunks it",
        "names. The chunk text is the bytes the record hashed, chunked under the record's own",
        "rule. `–` is not measured: no receipt, or chunk text that could not be recovered; it is",
        "never 0.",
        "",
        f"- **Cue patterns:** sha256 `{cues_sha256()}` over `CUES` in the script.",
        "- **Arms:** fixed in the script (`ARMS`): `scripts/arm_comparison.py`'s arms plus the v9",
        "  canary. A record whose own validation block says `passed: false` is not counted (#1029).",
        "",
        "| cue class | patterns |",
        "|---|---|",
    ]
    for cls, pats in CUES.items():
        lines.append(f"| {cls} | " + ", ".join(f"`{pid}`" for pid, _ in pats) + " |")
    lines += ["", "## By arm", "",
              "Sums over the arm's records, with the per-record mean in parentheses.", "",
              "| arm | records | " + " | ".join(h for _, h in COUNT_COLUMNS)
              + " | receipts | chunks nothing_relevant/redundant_with | lexical candidates | "
              + " | ".join(f"with {c} cue" for c in CUES) + " |",
              "|---|---:|" + "---:|" * len(COUNT_COLUMNS) + "---:|---:|---:|" + "---:|" * len(CUES)]
    for key, display, _ in arms:
        mine = [r for r in rows if r["arm"] == key]
        s = arm_summary(mine)
        cand = (_cell(s["candidates"]) + (f" ({s['readable']} of {s['receipts']} read)"
                                          if s["receipts"] and s["readable"] != s["receipts"] else ""))
        lines.append(
            f"| {display} | {s['records']} | "
            + " | ".join(f"{s['sums'][k]} ({s['means'][k]})" for k, _ in COUNT_COLUMNS)
            + f" | {s['receipts']} | {_cell(s['marked'])} | {cand} | "
            + " | ".join(_cell(s["by_class"][c] if s["by_class"] else None) for c in CUES) + " |")
    lines += ["", "## By record", "",
              "| arm | record | " + " | ".join(h for _, h in COUNT_COLUMNS)
              + " | nothing_relevant | redundant_with | lexical candidates | record sha256 | receipt sha256 |",
              "|---|---|" + "---:|" * len(COUNT_COLUMNS) + "---:|---:|---:|---|---|"]
    for r in rows:
        rc = r["receipt"]
        cands = None if rc is None or rc["candidates"] is None else len(rc["candidates"])
        lines.append(
            f"| {r['arm']} | `{r['path']}` | "
            + " | ".join(str(r["counts"][k]) for k, _ in COUNT_COLUMNS)
            + f" | {_cell(rc and rc['by_status']['nothing_relevant'])}"
            + f" | {_cell(rc and rc['by_status']['redundant_with'])}"
            + f" | {_cell(cands)} | `{r['sha256'][:16]}` | "
            + (f"`{r['receipt_sha256'][:16]}`" if r["receipt_sha256"] else "–") + " |")
    if collected["excluded"]:
        lines += ["", "Not counted, declared invalid by their own validation block: "
                  + "; ".join(f"`{p}`" for p in collected["excluded"]) + "."]
    lines += ["", "## Lexical candidates by record", "",
              "Each receipted record: the basis its chunk text was read on, then each",
              "`nothing_relevant`/`redundant_with` chunk with a cue, its cue classes and the",
              "matches per pattern. No chunk text is reproduced here.", ""]
    for r in rows:
        rc = r["receipt"]
        if rc is None:
            continue
        lines.append(f"### `{r['path']}`")
        lines.append("")
        if rc["candidates"] is None:
            lines += [f"Chunk text not recovered: {r['text_basis']}. Candidates –.", ""]
            continue
        lines.append(f"Chunk text: {r['text_basis']}. {rc['marked']} chunk(s) marked "
                     f"nothing_relevant/redundant_with; {len(rc['candidates'])} with a cue.")
        if rc["missing_chunks"]:
            lines.append("Receipt chunk ids absent from the record's chunks: "
                         + ", ".join(f"`{c}`" for c in rc["missing_chunks"]) + ".")
        lines.append("")
        if rc["candidates"]:
            lines += ["| chunk | status | cues |", "|---|---|---|"]
            for c in rc["candidates"]:
                cues = "; ".join(f"{cls}: " + ", ".join(f"`{pid}` {n}" for pid, n in hits.items())
                                 for cls, hits in c["cues"].items())
                lines.append(f"| {c['chunk']} | {c['status']} | {cues} |")
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="read-only: exit 1 when the committed note does not match the records")
    args = ap.parse_args(argv)
    text = render_markdown(collect())
    shown = OUT_MD.relative_to(ROOT).as_posix() if OUT_MD.is_relative_to(ROOT) else str(OUT_MD)
    if args.check:
        if not OUT_MD.exists() or OUT_MD.read_text(encoding="utf-8") != text:
            print(f"stale: {shown} does not match the records; run scripts/recall_target_baseline.py",
                  file=sys.stderr)
            return 1
        print(f"{shown} matches the records")
        return 0
    OUT_MD.write_text(text, encoding="utf-8")
    print(f"wrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
