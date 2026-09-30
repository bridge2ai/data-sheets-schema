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
  strings. The `tools` half is a regular expression over a free string
  (`TOOL_VERSION`), broader than the chunk-text version cue.

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

The zeros alone do not say whether a bundle states what a record lacks
(#3289). `notes/recall_target_bundle_adjudication.yaml` is a hand reading
that does: a verdict on every lexical candidate with a version or lineage
cue, keyed on the chunk text's sha256, and each versioned software
statement the bundles make, with a verbatim snippet. The script renders
the reading into the note and measures against it: which candidates have
no verdict, which verdicts match no candidate, whether each snippet is in
the bytes a record hashed, and whether the record carries the name with
the version (`fact_carriage`). The reading is not re-derived; the
measurement is.

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
ADJUDICATION = ROOT / "notes" / "recall_target_bundle_adjudication.yaml"
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

#: The chunk-text `version` cue: `v1.2`, `1.2.3`, `version 2`, `release 4.0`.
#: Deliberately narrow for prose: a bare two-part number (`1.9`, `3.11`) is
#: not a cue, because chunk text is full of decimals ("4.5 hours", "p < 0.05"),
#: and neither is a named version (`v.gpt-4-1106-preview`). The version-cue
#: counts are therefore a lower bound for chunks that state a version only in
#: those forms (#3301).
_VERSION_TOKEN = r"(?:\bv\d+(?:\.\d+)+\b|\b\d+\.\d+(?:\.\d+)+\b|\b(?:version|release)\s*:?\s*v?\d+(?:\.\d+)*\b)"
VERSION_TOKEN = re.compile(_VERSION_TOKEN, re.IGNORECASE)

#: A version in a `tools` string (`MachineAnnotationTools.tools`, "ToolName
#: version" by its description). Broader than the chunk cue, because the
#: string names one tool and a number in it is not prose: any dotted number
#: (`samtools 1.9`, `Python 3.11`, `spaCy 3.5.0`), a `v`-prefixed version
#: with or without a dot and with a named or numeric body (`v2`, `v3.0.1`,
#: `v.gpt-4-1106-preview`), or `version|release N`. A hyphenated model name
#: (`GPT-4`, `DenseNet-121`) and a stated `unknown` are not versions (#3301).
_TOOL_VERSION = (r"(?:\b\d+\.\d+(?:\.\d+)*\b|\bv\d+(?:\.\d+)*\b|\bv\.\s?[\w.-]*\d[\w.-]*"
                 r"|\b(?:version|release)\s*:?\s*v?\d+(?:\.\d+)*\b)")
TOOL_VERSION = re.compile(_TOOL_VERSION, re.IGNORECASE)

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


def tool_version_sha256() -> str:
    """The `tools` version pattern's identity, printed into the note."""
    return hashlib.sha256(_TOOL_VERSION.encode("utf-8")).hexdigest()


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
                out["tools_versioned"] += isinstance(tool, str) and bool(TOOL_VERSION.search(tool))
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


def hashed_bundle(inputs: dict[str, Any], root: Path) -> tuple[bytes | None, str]:
    """The bundle bytes the record hashed, and the basis they were read on;
    or None and why not: the bundle on disk where it still hashes to the
    record's md5/sha256, else the committed version that does."""
    bundle_rel = inputs.get("bundle_path")
    md5, sha = inputs.get("bundle_md5"), inputs.get("bundle_sha256")
    if not bundle_rel or not (md5 or sha):
        return None, "the record declares no bundle path and hash"
    disk = root / bundle_rel
    if disk.is_file():
        b = disk.read_bytes()
        if ((not md5 or hashlib.md5(b).hexdigest() == md5)
                and (not sha or hashlib.sha256(b).hexdigest() == sha)):
            return b, "bundle on disk"
    from data_sheets_schema.provenance import GitUnavailable, bundle_bytes_for
    try:
        recovered = bundle_bytes_for(bundle_rel, md5=md5, sha256=sha)
    except GitUnavailable as exc:
        return None, f"the bundle drifted and git could not supply the version hashed ({exc})"
    if recovered is None:
        return None, "the bundle drifted and no committed version hashes to the record's"
    return recovered[0], "committed version (git)"


def chunk_texts_for(inputs: dict[str, Any], root: Path,
                    bundle: tuple[bytes | None, str] | None = None) -> tuple[dict[str, str] | None, str]:
    """The record's chunk texts by id, and the basis they were read on; or
    None and why not. The bytes are the ones the record hashed
    (`hashed_bundle`, or `bundle` where the caller already read them) and
    the chunks are the record's own rule over them."""
    from data_sheets_schema.chunking import chunk_text, chunk_texts

    chunks = inputs.get("chunks") or {}
    rule = chunks.get("rule") if isinstance(chunks, dict) else None
    if not inputs.get("bundle_path") or not (inputs.get("bundle_md5") or inputs.get("bundle_sha256")):
        return None, "the record declares no bundle path and hash"
    if not isinstance(rule, dict):
        return None, "the record declares no chunk rule"
    raw, basis = bundle if bundle is not None else hashed_bundle(inputs, root)
    if raw is None:
        return None, basis
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
            cands.append({"chunk": str(c.get("id")), "status": c["status"], "cues": found,
                          "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    # A marked chunk whose text is unknown was not inspected, so the count is
    # unmeasured, not a floor: a stale id must not read as zero candidates.
    out["candidates"] = None if out["missing_chunks"] else cands
    return out


#: The cue classes the adjudication must cover (#3289): software versions
#: and lineage. Variables are not adjudicated here; whether a variables row
#: is a variable in a data file is #2079's question, not a bundle reading.
ADJUDICATED_CLASSES = ("version", "lineage")
SOFTWARE_VERDICTS = ("none", "referent", "companion", "cited")
PARENT_VERDICTS = ("none", "stated")
#: How a record carries a versioned software fact, strongest first.
CARRIAGE = ("structured", "elsewhere", "name_only", "absent")


def load_adjudication(path: Path) -> dict[str, Any]:
    """The hand adjudication, checked for shape: a malformed entry is an
    error, never a silently skipped verdict."""
    raw = path.read_bytes()
    data = _load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: not a mapping")
    chunks, facts, bundles = data.get("chunks") or [], data.get("facts") or [], data.get("bundles") or []
    for i, c in enumerate(chunks):
        where = f"{path}: chunks[{i}]"
        if not isinstance(c, dict) or not all(c.get(k) for k in ("project", "chunk", "sha256", "reading")):
            raise ValueError(f"{where}: needs project, chunk, sha256 and reading")
        if not isinstance(c["sha256"], list) or not all(re.fullmatch(r"[0-9a-f]{64}", str(s)) for s in c["sha256"]):
            raise ValueError(f"{where}: sha256 must be a list of full hex digests")
        if c.get("software_version") not in SOFTWARE_VERDICTS:
            raise ValueError(f"{where}: software_version must be one of {', '.join(SOFTWARE_VERDICTS)}")
        if c.get("parent_dataset") not in PARENT_VERDICTS:
            raise ValueError(f"{where}: parent_dataset must be one of {', '.join(PARENT_VERDICTS)}")
    seen: dict[str, str] = {}
    for c in chunks:
        for s in c["sha256"]:
            if s in seen:
                raise ValueError(f"{path}: chunk sha256 {s[:12]}… adjudicated twice")
            seen[s] = c["chunk"]
    ids = set()
    for i, f in enumerate(facts):
        where = f"{path}: facts[{i}]"
        if not isinstance(f, dict) or not all(f.get(k) for k in ("id", "project", "names", "version", "snippet")):
            raise ValueError(f"{where}: needs id, project, names, version and snippet")
        if f.get("scope") not in SOFTWARE_VERDICTS[1:]:
            raise ValueError(f"{where}: scope must be one of {', '.join(SOFTWARE_VERDICTS[1:])}")
        if not isinstance(f["names"], list):
            raise ValueError(f"{where}: names must be a list")
        if f["id"] in ids:
            raise ValueError(f"{where}: duplicate id {f['id']}")
        ids.add(f["id"])
    return {"chunks": chunks, "facts": facts, "bundles": bundles,
            "sha256": hashlib.sha256(raw).hexdigest(), "path": path}


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _fact_patterns(fact: dict[str, Any]) -> tuple[re.Pattern, re.Pattern]:
    """The fact's name (any of `names`) and its version, each as a whole
    token; the version may carry a `v`, `v.` or `version` prefix."""
    names = re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(str(n)) for n in fact["names"]) + r")(?![\w-])",
                       re.IGNORECASE)
    version = re.compile(r"(?<![\w.])(?:v\.?\s?|version\s)?" + re.escape(str(fact["version"])) + r"(?!\w|\.\d)",
                         re.IGNORECASE)
    return names, version


def _strings(node: Any):
    """Every scalar leaf, as text."""
    if isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)
    elif node not in (None, ""):
        yield _collapse(str(node))


def _mappings(node: Any):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _mappings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _mappings(v)


def fact_carriage(record: Any, fact: dict[str, Any]) -> str:
    """How the record carries a versioned software fact (`CARRIAGE`):
    `structured` is a `used_software` entry naming it with that `version`,
    or a `tools` string holding both; `elsewhere` is any other string, or
    one mapping's own values, holding both (prose, a resource entry);
    `name_only` the name without the version; `absent` neither. Lexical,
    like the cues: a match does not check that the value is right."""
    names, version = _fact_patterns(fact)
    for key, value in _walk(record):
        if key == "used_software":
            for sw in entries(value):
                if (isinstance(sw, dict) and _populated(sw.get("version"))
                        and version.search(_collapse(str(sw["version"])))
                        and any(names.search(s) for s in _strings(sw))):
                    return "structured"
        elif key == "tools":
            for tool in entries(value):
                if isinstance(tool, str) and names.search(tool) and version.search(tool):
                    return "structured"
    strings = list(_strings(record))
    if any(names.search(s) and version.search(s) for s in strings):
        return "elsewhere"
    for m in _mappings(record):
        own = [_collapse(str(v)) for v in m.values() if v not in (None, "") and not isinstance(v, (dict, list))]
        if any(names.search(s) for s in own) and any(version.search(s) for s in own):
            return "elsewhere"
    return "name_only" if any(names.search(s) for s in strings) else "absent"


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
            projects: tuple[str, ...] | None = None,
            adjudication: dict[str, Any] | None = None) -> dict[str, Any]:
    """One row per record of every arm: its counts, its receipt's, and the
    basis of each. `root` is what a record's repository-relative bundle path
    resolves against (the checkout by default). `adjudication` is a
    `load_adjudication` result (the committed file when it exists, for the
    default corpus); each row then carries, per fact of its project,
    whether its hashed bytes state the snippet and how it carries it."""
    corpus, arms, root = corpus or CORPUS, ARMS if arms is None else arms, root or ROOT
    projects = PROJECTS if projects is None else projects
    if adjudication is None and corpus == CORPUS and ADJUDICATION.is_file():
        adjudication = load_adjudication(ADJUDICATION)
    facts = (adjudication or {}).get("facts") or []
    bundles: dict[tuple, tuple[bytes | None, str]] = {}
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
                inputs = prov_rec.get("inputs") or {}
                mine = [f for f in facts if f["project"] == project]
                rpath = corpus / f"{method}_core" / label / f"{project}_coverage_receipt.yaml"
                bundle = None
                if rpath.is_file() or mine:
                    bkey = (inputs.get("bundle_path"), inputs.get("bundle_md5"), inputs.get("bundle_sha256"))
                    if bkey not in bundles:
                        bundles[bkey] = hashed_bundle(inputs, root)
                    bundle = bundles[bkey]
                texts = None
                if rpath.is_file():
                    rraw = rpath.read_bytes()
                    receipt = _load(rraw)
                    row["receipt_sha256"] = hashlib.sha256(rraw).hexdigest()
                    texts, basis = chunk_texts_for(inputs, root, bundle)
                    row["text_basis"] = basis
                    row["receipt"] = receipt_candidates(receipt if isinstance(receipt, dict) else {}, texts)
                if mine:
                    row["facts"] = fact_rows(mine, record, bundle, texts)
                rows.append(row)
    return {"rows": rows, "excluded": excluded, "corpus": corpus, "adjudication": adjudication}


def fact_rows(facts: list[dict[str, Any]], record: Any, bundle: tuple[bytes | None, str] | None,
              texts: dict[str, str] | None) -> dict[str, dict[str, Any]]:
    """Per fact: `stated` (the snippet is in the bytes the record hashed;
    None where they are not recovered), the chunks that carry it where the
    chunk text is known, and the record's `fact_carriage`."""
    flat = None
    if bundle is not None and bundle[0] is not None:
        try:
            flat = _collapse(bundle[0].decode("utf-8"))
        except UnicodeDecodeError:
            flat = None
    out = {}
    for f in facts:
        snippet = _collapse(str(f["snippet"]))
        out[f["id"]] = {
            "stated": None if flat is None else snippet in flat,
            "chunks": ([cid for cid, t in texts.items() if snippet in _collapse(t)] if texts is not None else None),
            "carried": fact_carriage(record, f),
        }
    return out


def adjudication_coverage(collected: dict[str, Any], arms=None) -> dict[str, Any]:
    """Which lexical candidates with an adjudicated cue class have a
    verdict, which do not, and which verdicts match no candidate. A
    candidate is identified by its project and chunk text sha256."""
    arms = ARMS if arms is None else arms
    order = {key: i for i, (key, _, _) in enumerate(arms)}
    adj = collected.get("adjudication") or {"chunks": []}
    by_sha = {(c["project"], s): c for c in adj["chunks"] for s in c["sha256"]}
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for r in collected["rows"]:
        rc = r["receipt"]
        for c in (rc or {}).get("candidates") or []:
            if not any(cls in c["cues"] for cls in ADJUDICATED_CLASSES):
                continue
            k = (r["project"], c["sha256"])
            e = seen.setdefault(k, {"project": r["project"], "chunk": c["chunk"], "sha256": c["sha256"], "arms": []})
            if r["arm"] not in e["arms"]:
                e["arms"].append(r["arm"])
    for e in seen.values():
        e["arms"].sort(key=lambda a: order.get(a, len(order)))
    matched = [dict(e, verdict=by_sha[k]) for k, e in sorted(seen.items(), key=lambda kv: (kv[0][0], kv[1]["chunk"]))
               if k in by_sha]
    missing = [e for k, e in sorted(seen.items(), key=lambda kv: (kv[0][0], kv[1]["chunk"])) if k not in by_sha]
    unmatched = [c for c in adj["chunks"] if not any((c["project"], s) in seen for s in c["sha256"])]
    return {"matched": matched, "missing": missing, "unmatched": unmatched}


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
        "expression over a free string, `TOOL_VERSION`: any dotted number, `v` with a numeric or",
        "named body such as `v3.0.1` or `v.gpt-4-1106-preview`, or `version`/`release N`; a",
        "hyphenated model name such as `GPT-4` and a stated `unknown` are not versions). A",
        "count is of what the record carries, not of whether",
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
        f"- **Tools version pattern:** sha256 `{tool_version_sha256()}` over `_TOOL_VERSION` in the script.",
        "- **Version cue is narrower than the tools pattern:** in chunk text a bare two-part number",
        "  (`1.9`) or a named version (`v.gpt-4-1106-preview`) is not a cue, since prose is full",
        "  of decimals; the version-cue counts are a lower bound for chunks stating a version only",
        "  in those forms.",
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
    if collected.get("adjudication"):
        lines += render_adjudication(collected, arms)
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
            if rc["missing_chunks"]:
                lines += [f"Chunk text: {r['text_basis']}. Receipt chunk ids absent from the record's chunks: "
                          + ", ".join(f"`{c}`" for c in rc["missing_chunks"]) + ". Candidates –.", ""]
            else:
                lines += [f"Chunk text not recovered: {r['text_basis']}. Candidates –.", ""]
            continue
        lines.append(f"Chunk text: {r['text_basis']}. {rc['marked']} chunk(s) marked "
                     f"nothing_relevant/redundant_with; {len(rc['candidates'])} with a cue.")
        lines.append("")
        if rc["candidates"]:
            lines += ["| chunk | status | cues |", "|---|---|---|"]
            for c in rc["candidates"]:
                cues = "; ".join(f"{cls}: " + ", ".join(f"`{pid}` {n}" for pid, n in hits.items())
                                 for cls, hits in c["cues"].items())
                lines.append(f"| {c['chunk']} | {c['status']} | {cues} |")
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def _one_line(text: Any) -> str:
    return _collapse(str(text)).replace("|", "\\|")


def render_adjudication(collected: dict[str, Any], arms=None) -> list[str]:
    """The #3289 section: the hand reading as written, and what the script
    measures against it."""
    arms = ARMS if arms is None else arms
    adj = collected["adjudication"]
    path = adj["path"]
    shown = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
    cov = adjudication_coverage(collected, arms)
    rows = collected["rows"]
    lines = [
        "", "## Bundle adjudication (#3289)", "",
        f"A hand reading, `{shown}` (sha256 `{adj['sha256']}`), rendered here: edit that file, not",
        "this note. It asks whether the zeros above are bundle facts or omissions. Keep #1349 in",
        "view: lineage stated in text form is valid, so a biological or clinical source written as",
        "prose is not a missing parent dataset. Variables are not adjudicated (#2079: whether a row",
        "is a variable in a data file is not a lexical question). The verdicts are a reading; the",
        "coverage, the snippet checks and the carriage counts below are measured.",
        "", "### The answer by project", "",
        "| project | software versions | parent datasets |", "|---|---|---|",
    ]
    for b in adj["bundles"]:
        lines.append(f"| {b.get('project')} | {_one_line(b.get('software_version'))} "
                     f"| {_one_line(b.get('parent_dataset'))} |")
    lines += [
        "", "### Lexical candidates with a version or lineage cue", "",
        "Each distinct candidate text, keyed on its sha256 (the chunk manifests' `sha256`), with the",
        "arms whose receipts mark it `nothing_relevant`/`redundant_with`. **software version**: `none`",
        "(the cue is not a software version), `referent` (stated as used for the dataset the record",
        "describes), `companion` (stated for an analysis the bundle documents, not said to be applied",
        "to the released data) or `cited` (a versioned citation with no stated use). **parent",
        "dataset**: `none` or `stated`.", "",
        "| project | chunk | chunk sha256 | candidate in | software version | parent dataset | reading |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in cov["matched"]:
        v = e["verdict"]
        lines.append(f"| {e['project']} | {e['chunk']} | `{e['sha256'][:12]}` | {', '.join(e['arms'])} "
                     f"| {v['software_version']} | {v['parent_dataset']} | {_one_line(v['reading'])} |")
    lines.append("")
    lines.append("Not adjudicated: " + ("; ".join(f"{e['project']} {e['chunk']} `{e['sha256'][:12]}` "
                                                   f"({', '.join(e['arms'])})" for e in cov["missing"])
                                         if cov["missing"] else "none") + ".")
    lines.append("Adjudicated but matching no candidate: "
                 + ("; ".join(f"{c['project']} {c['chunk']}" for c in cov["unmatched"]) if cov["unmatched"]
                    else "none") + ".")
    lines += [
        "", "### Versioned software the bundles state, and where the records carry it", "",
        "Every versioned software statement found in the four bundles, searched in full, citations",
        "included; what is not one (releases, standards, database versions, paper titles, the",
        "Dataverse host's footer) is listed in the adjudication file's header. Per arm,",
        "over the records of the fact's project: **stated** is the records whose hashed bundle bytes",
        "contain the snippet (`–` where the bytes are not recovered); **used_software/tools** is a",
        "`used_software` entry naming the software with that `version`, or a `tools` string with",
        "both; **elsewhere** is any other string, or one mapping's own values, holding the name and",
        "the version (prose, a resource entry); **name only** is the name without the version;",
        "**absent** is neither. Lexical, like the cues: a match does not check that the value is",
        "right, and a `companion` or `cited` fact carried is not thereby in scope.", "",
        "| fact | scope | stated in chunks | arm | records | stated | used_software/tools | elsewhere "
        "| name only | absent |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for f in adj["facts"]:
        mine = [r for r in rows if f["id"] in (r.get("facts") or {})]
        chunk_ids = sorted({c for r in mine for c in (r["facts"][f["id"]]["chunks"] or [])})
        for key, display, _ in arms:
            arm_rows = [r["facts"][f["id"]] for r in mine if r["arm"] == key]
            if not arm_rows:
                continue
            known = [x["stated"] for x in arm_rows if x["stated"] is not None]
            stated = f"{sum(known)}" + (f" of {len(known)}" if len(known) != len(arm_rows) else "") if known else "–"
            n = {c: sum(x["carried"] == c for x in arm_rows) for c in CARRIAGE}
            lines.append(f"| `{f['id']}` | {f['scope']} | {', '.join(chunk_ids) or '–'} | {display} "
                         f"| {len(arm_rows)} | {stated} | " + " | ".join(str(n[c]) for c in CARRIAGE) + " |")
    lines += ["", "Where each fact is stated, as read:", ""]
    lines += [f"- `{f['id']}`: {_one_line(f.get('reading', ''))}" for f in adj["facts"]]
    return lines


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
