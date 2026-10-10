"""Which source documents a coverage receipt cites, by tier (#2937).

A coverage receipt names, for each receipted field path, the chunks whose
snippets attest it (#708). The chunk manifest names each chunk's source
document (#707), and the source manifest ranks the documents by
`source_priority` tier (tier 1 is the release describing itself). Joined,
they say which tier each receipted path rests on, and how many distinct
documents cite it. Nothing here changes a receipt, a record, a floor or the
`receipts` block: this is a read-only report beside `receipts.check`, and
the tiers are read through `source_metadata.projection`, never redefined.

What the #2303 figure set found (fig19): 75-97% of a record's receipted
paths are cited by exactly one document, and on VOICE the tier-2 project
documentation is the sole citation for more paths than the tier-1 PhysioNet
release. The receipt protocol asks for *a* verbatim snippet, not the most
authoritative one, and chunks are read in manifest order, not tier order.
This report states that shape for one run, and screens for the case the
issue names: a path cited only to a lower tier while a higher-tier chunk
contains the value's tokens.

**The unit** (#2819): a path is a distinct receipt slot path as written that
resolves, by index, to a populated value in the final record — fig19's
`receipted_field_paths`. Several chunks citing one path count once. It is
not `receipts.check`'s `slots.with_receipt`, which counts populated leaf
paths a receipt covers (an entry receipt covers its leaves).

**No phase-1 snapshot join** (the #899 identity join is not applied, as
fig19 does not apply it): a path is read against the final record by index
alone, and it is counted only where that read reaches a populated value.
Where reconciliation moved or dropped the entry a path named, the path
reads whatever entry now holds its index. When that entry holds a populated
value at the path, the path is counted, credited and screened there
(#3123). Otherwise it is unresolved: its index is gone, or the entry now at
its index does not hold the path or holds it empty (#3190). A value that
survives elsewhere in the record does not rescue the path. On the 24 fig19
records, the paths on an entry that `receipts.remap_path`, against each
record's phase-1 snapshot, finds moved or dropped are:

- 19 counted at another entry: 11 on a dropped entry whose index another
  entry reuses, 7 on an entry that moved, 1 ambiguous;
- 31 unresolved because their index is gone: 28 on a dropped entry, 2 on
  an entry that moved, 1 ambiguous;
- 2 unresolved at an index another entry holds without the path, both in
  2026-09-01 v7 rep3 records: AI_READI `distribution_formats[0].media_type`
  (the entry moved to `[2]`, where the value still resolves) and CHORUS
  `creators[1].principal_investigator.name` (the entry was dropped).

The other 131 unresolved paths are not on a moved or dropped entry: a leaf
reconciliation removed or reshaped, such as a list of strings written as
one string (128), or a path phase 1 never had (3).
(Note: when receipts are reconciled against final records via
`reconcile_receipt`, dangling entries are pruned and moved entries remapped,
resolving all dropped entries).

**The bundle preamble** is not a source document: it has no tier, a path it
cites gains no citing document from it, and its citations are counted apart.

**Unranked** documents take `effective_priority` 99 from the projection, the
established `source_priority` fallback; a chunk source the manifest does not
declare for the project takes 99 too. Both are listed apart, with the basis.

The token screen is lexical: the value's normalised tokens
(`receipts._value_tokens`, each of at least four characters) all occur in a
higher-tier chunk. A common word matches everywhere, so a value is screened
only above a token-count and character floor, and every flagged path is an
item for a human spot-check, not a finding. Each flag also says whether the
value's folded text occurs there as one run (`verbatim`): on the 24 fig19
records, 30 of the 104 flags do.

**Supersession** (#3049) is a second screen beside the tier one, with the
same token rule and floors: a path cited only to documents the manifest
marks `superseded_by`, while a chunk of a replacement (any source down the
`superseded_by` chain that the path does not itself cite) holds every token
of the value. The tier screen cannot see it when the replacement shares the
superseded source's tier — CM4AI's `october_2025_dataverse_release` and its
replacement are both tier 1 — and `source_priority.decide` already ranks
supersession above tier for disagreements (#600). It is a separate count:
no tier outcome and no projection field changes, and a path can be flagged
by both screens (`also_higher_tier_match` says how many were). On the 24
fig19 records, 82 paths are cited only to superseded sources, every one with
a replacement chunk in its bundle. 9 of them are exempt (they owe no bundle
receipt) and keep the outcome `exempt` unscreened; of the other 73, 61 clear
the floors and are screened, and 12 of those are flagged (8 CM4AI against
`june_2026_dataverse_release`, 4 VOICE against `physionet_3_1_0`), 1
verbatim, and none of the 12 is also a tier-screen flag.

**Which manifest ranks**: the selected one by default, its sha256 stated
beside whether it is the run's recorded `inputs.source_manifest`. With
`--at-run-commit` (#3050) it is the bytes the run recorded, recovered by
hash (`run_source_manifest`). The 24 fig19 records recorded two versions
(md5 41408d… and 6c71e8…, 12 each, both recovered from git), and both rank
every document of those runs as today's manifest does: no count moves.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from data_sheets_schema import receipts as rc
from data_sheets_schema import source_metadata
from data_sheets_schema.chunking import PREAMBLE

#: v2 adds the supersession screen (#3049); every v1 key and count is unchanged.
INSTRUMENT = "receipt_sources v2 (#2937, #3049)"

UNIT = ("distinct receipt slot paths as written that resolve, by index, to a populated value in the "
        "final record (fig19's receipted_field_paths; several citing chunks count once; not "
        "`receipts check`'s slots with a receipt, which counts populated leaf paths covered, #2819)")

UNRANKED = source_metadata.UNRANKED

#: `receipts._value_tokens` keeps a token only at this length; stated in the
#: report so a reader knows what "a token" is (a test pins the two together).
TOKEN_MIN_CHARS = 4
#: A value is screened only when it carries at least this many distinct
#: tokens and this many characters across them — the snippet floors' shape
#: (`MIN_PART_CHARS` per part, `MIN_MULTIPART_CHARS` in all), one level up.
#: Below it the set is one or two words ("English", "Research",
#: "Bridge2AI-Voice") that most chunks of a bundle carry, and "a higher-tier
#: chunk contains it" says nothing about which document states the value.
#: The token floor is at least 1, and `source_dependence` refuses 0: a value
#: with no token ("Yes", a short number) has an empty token set, which is a
#: subset of every chunk, so with no floor at all it would flag against every
#: higher-tier chunk (#3121).
#: Measured on the 24 fig19 records (#2937, #3121, #3122):
#:   - 194 flags with no floor (before a zero floor was refused), 42 of
#:     them values with no token;
#:   - 151 at one token and no character floor (the loosest admitted);
#:   - 119 at two tokens and 12 characters;
#:   - 104 at three tokens.
#: At three tokens the character floor cannot bind: every token carries at
#: least `TOKEN_MIN_CHARS`, so three carry 12. The flag count is 104 with
#: the character floor or without it. The token floor does the work: the
#: character floor alone, at one token, gives 122. The three-token flags
#: read as the issue's case (a march-2025 release cited where the
#: october-2025 release holds the whole passage). What the floor drops is
#: common words, two-word names and bare grant numbers. The corpus test
#: pins every count here at one token and above.
MIN_MATCH_TOKENS = 3
MIN_MATCH_CHARS = rc.MIN_MULTIPART_CHARS
EXAMPLES = 10
VALUE_EXCERPT = 80

#: The token screen's outcome for each path; every path has exactly one.
SCREEN_OUTCOMES = ("higher_tier_match", "no_higher_tier_match", "below_floor",
                   "no_higher_tier_chunk", "exempt", "preamble_only")
#: The supersession screen's outcome for each path; every path has exactly
#: one. `cites_a_current_source`: some citing document is not superseded.
SUPERSESSION_OUTCOMES = ("replacement_match", "no_replacement_match", "below_floor",
                         "no_replacement_chunk", "cites_a_current_source", "exempt", "preamble_only")

NON_CHECKS = (
    "that a citation supports its value — this counts citation dependence in the run's own receipt; "
    "`d4d receipts check` verifies snippets, and neither judges support",
    "that a higher-tier chunk containing a value's tokens states that value — the screen is lexical; "
    "spot-check the listed paths",
    "which tiers the run itself saw — tiers are read from the selected source manifest's bytes, "
    "whose sha256 is stated, not from the bytes the run recorded in inputs.source_manifest "
    "(`--at-run-commit` reads those, recovered by hash rather than from the run's commit)",
)

#: With `--at-run-commit` (#3050) the last non-check above no longer holds;
#: this one takes its place.
NON_CHECK_AT_RUN_COMMIT = (
    "today's ranking — the tiers are the source manifest bytes the run recorded, recovered by hash "
    "(`--at-run-commit`), so a tier or source list changed since the run is not applied")


def non_checks(at_run_commit: bool = False) -> list[str]:
    """The report's non-checks for where its tiers were read from."""
    return list(NON_CHECKS[:-1]) + [NON_CHECK_AT_RUN_COMMIT] if at_run_commit else list(NON_CHECKS)


def _leaf_text(value: Any) -> str:
    """The text a value carries: scalar leaves joined, keys left out (a
    mapping's key names are schema words, not source text), booleans left
    out (the screen is text against text, as `receipts.check`'s is)."""
    if isinstance(value, dict):
        return " ".join(_leaf_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_leaf_text(v) for v in value)
    if value is None or isinstance(value, bool):
        return ""
    return str(value)


def _folded(text: str) -> str:
    # Underscores fold to spaces on both sides: `_value_tokens` folds them in
    # the value, and "voice_data" in a chunk must read as the same two words.
    return rc.normalise(text.replace("_", " "))


def _share(part: int, whole: int) -> float | None:
    return part / whole if whole else None


def source_dependence(receipt: dict[str, Any], chunk_manifest: dict[str, Any],
                      source_manifest_bytes: bytes | str, project: str,
                      full: dict[str, Any], chunk_texts: dict[str, str], *,
                      examples: int = EXAMPLES, min_tokens: int = MIN_MATCH_TOKENS,
                      min_chars: int = MIN_MATCH_CHARS) -> dict[str, Any]:
    """The receipt's citations by source document and tier. Pure.

    `chunk_manifest` must be the one the receipt was written against: the
    two `bundle_md5`s must agree, since chunk ids are positional and another
    manifest's ids name other text. `source_manifest_bytes` is the exact
    manifest; its projection supplies every tier and raises `ValueError` when
    the project is not declared. `chunk_texts` (id → text) feeds the token
    screen; a chunk without text is not screened and is counted.
    `min_tokens` must be at least 1 (`ValueError` otherwise): an empty token
    set is a subset of every chunk and would match each one (#3121).
    """
    if min_tokens < 1:
        raise ValueError(f"min_tokens must be at least 1, not {min_tokens!r}: a value with no token has an "
                         "empty token set, which every chunk contains")
    if receipt.get("bundle_md5") != chunk_manifest.get("bundle_md5"):
        raise ValueError(f"the receipt's bundle_md5 {receipt.get('bundle_md5')!r} is not the chunk "
                         f"manifest's {chunk_manifest.get('bundle_md5')!r}: its chunk ids would name other text")
    authority = source_metadata.projection(source_manifest_bytes, project)
    by_source = {row["source"]: row for row in authority["sources"]}

    documents: dict[str, dict[str, Any]] = {}
    for row in authority["sources"]:
        doc = {"document": row["source_id"], "source": row["source"], "source_type": row["source_type"],
               "tier": row["effective_priority"], "priority_basis": row["priority_basis"], "chunks": []}
        if "superseded_by" in row:
            doc["superseded_by"] = row["superseded_by"]
        documents[row["source_id"]] = doc
    chunk_doc: dict[str, str | None] = {}          # chunk id → document; None for the preamble
    preamble_chunks: list[str] = []
    for c in chunk_manifest.get("chunks") or []:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str):
            continue
        source = str(c.get("source"))
        if source == PREAMBLE:
            chunk_doc[c["id"]] = None
            preamble_chunks.append(c["id"])
            continue
        row = by_source.get(source)
        key = row["source_id"] if row is not None else f"undeclared:{source}"
        if row is None and key not in documents:
            documents[key] = {"document": key, "source": source, "source_type": None, "tier": UNRANKED,
                              "priority_basis": "undeclared", "chunks": []}
        documents[key]["chunks"].append(c["id"])
        chunk_doc[c["id"]] = key
    tier = {k: d["tier"] for k, d in documents.items()}

    def replacements(doc: str) -> list[str]:
        """Every source down `doc`'s `superseded_by` chain (acyclic: the
        projection refuses a cycle)."""
        out, current = [], documents[doc].get("superseded_by")
        while current is not None:
            out.append(current)
            current = documents[current].get("superseded_by")
        return out

    # --- citations: receipt path → citing documents
    citing: dict[str, dict[str, Any]] = {}
    entries = Counter()
    unresolved_paths: set[str] = set()
    redundant_targets: set[str] = set()
    redundant_entries = 0
    preamble_citations = 0
    for e in receipt.get("chunks") or []:
        if not isinstance(e, dict):
            continue
        cid = e.get("id")
        if e.get("status") == "redundant_with":
            redundant_entries += 1
            own = chunk_doc.get(cid)
            refs = e.get("chunks") if isinstance(e.get("chunks"), list) else []
            redundant_targets |= {chunk_doc[r] for r in refs
                                  if isinstance(r, str) and chunk_doc.get(r) and chunk_doc[r] != own}
            continue
        pairs = e.get("extracted")
        if e.get("status") != "extracted" or not isinstance(pairs, list):
            continue
        for pair in pairs:
            if not isinstance(pair, dict):
                continue
            entries["pairs"] += 1
            slot = str(pair.get("slot") or "")
            if not slot.strip():
                entries["empty_slot"] += 1
                continue
            if cid not in chunk_doc:
                entries["on_unknown_chunks"] += 1
                continue
            if not (rc.resolve(full, slot) and rc._populated(rc._resolve_value(full, slot)[1])):
                entries["unresolved_in_final"] += 1
                unresolved_paths.add(slot)
                continue
            entries["kept"] += 1
            item = citing.setdefault(slot, {"documents": set(), "chunks": set(), "preamble": False})
            item["chunks"].add(cid)
            if chunk_doc[cid] is None:
                item["preamble"] = True
                preamble_citations += 1
            else:
                item["documents"].add(chunk_doc[cid])
    n = len(citing)

    # --- shares
    sole_of = {p: next(iter(v["documents"])) for p, v in citing.items() if len(v["documents"]) == 1}
    best_of = {p: min(tier[d] for d in v["documents"]) for p, v in citing.items() if v["documents"]}
    doc_rows = []
    order = {k: i for i, k in enumerate(documents)}          # tier, then manifest order
    for key, d in sorted(documents.items(), key=lambda kv: (kv[1]["tier"], order[kv[0]])):
        cites = sum(1 for v in citing.values() if key in v["documents"])
        sole = sum(1 for s in sole_of.values() if s == key)
        doc_rows.append({**d, "paths_citing": cites, "paths_sole": sole, "sole_share": _share(sole, n)})
    tier_rows = []
    for t in sorted({d["tier"] for d in documents.values()}):
        members = [k for k, d in documents.items() if d["tier"] == t]
        sole = sum(1 for s in sole_of.values() if tier[s] == t)
        tier_rows.append({"tier": t, "documents": members,
                          "paths_citing": sum(1 for v in citing.values() if any(tier[d] == t for d in v["documents"])),
                          "paths_best_tier": sum(1 for b in best_of.values() if b == t),
                          "paths_sole_document": sole, "sole_share": _share(sole, n)})

    # --- token screen: cited to a lower tier while a higher-tier chunk holds the value's tokens
    folded = {cid: _folded(text) for cid, text in chunk_texts.items() if chunk_doc.get(cid)}
    hay = {cid: set(text.split()) for cid, text in folded.items()}
    no_text = sorted(cid for cid, doc in chunk_doc.items() if doc is not None and cid not in hay)
    record_id = full.get("id") if isinstance(full.get("id"), str) else None
    carried = rc.dataset_identifier_forms(full)
    outcomes = Counter()
    by_cited_tier = Counter()
    verbatim = 0
    flagged: list[dict[str, Any]] = []
    s_outcomes = Counter()
    s_verbatim = 0
    s_also_tier = 0
    s_flagged: list[dict[str, Any]] = []
    by_path = []
    for path in sorted(citing):
        v = citing[path]
        value = rc._resolve_value(full, path)[1]
        row = {"path": path, "documents": sorted(v["documents"]), "chunks": sorted(v["chunks"]),
               "tiers": sorted({tier[d] for d in v["documents"]}), "best_tier": best_of.get(path),
               "preamble": v["preamble"]}
        if not v["documents"]:
            outcome = "preamble_only"
        elif rc.exempt(path, value, record_id, carried):
            outcome = "exempt"                  # no bundle receipt is owed (#722, #1123); not screened
        else:
            # Every higher-tier chunk decides whether the path could be
            # flagged at all; only those with text can match, and a chunk
            # without text is listed rather than read as absent.
            higher = sorted(cid for cid, doc in chunk_doc.items()
                            if doc is not None and tier[doc] < best_of[path])
            tokens = rc._value_tokens(_leaf_text(value))
            if not higher:
                outcome = "no_higher_tier_chunk"
            elif len(tokens) < min_tokens or sum(len(t) for t in tokens) < min_chars:
                outcome = "below_floor"
            else:
                hits = [cid for cid in higher if cid in hay and tokens <= hay[cid]]
                outcome = "higher_tier_match" if hits else "no_higher_tier_match"
                if hits:
                    by_cited_tier[best_of[path]] += 1
                    # A narrower reading beside the bag of tokens: the value's
                    # folded text as one run in a matching chunk. An entry's
                    # leaves joined in record order seldom read so, so this
                    # orders the spot-check rather than replacing it.
                    phrase = _folded(_leaf_text(value))
                    in_order = any(phrase in folded[c] for c in hits)
                    verbatim += in_order
                    excerpt = " ".join(_leaf_text(value).split())
                    flagged.append({
                        "path": path,
                        "value": excerpt[:VALUE_EXCERPT] + ("…" if len(excerpt) > VALUE_EXCERPT else ""),
                        "tokens": len(tokens),
                        "verbatim": in_order,
                        "cited": [{"document": d, "tier": tier[d],
                                   "chunks": sorted(c for c in v["chunks"] if chunk_doc.get(c) == d)}
                                  for d in sorted(v["documents"], key=lambda d: (tier[d], d))],
                        "higher_tier_chunks": [{"chunk": c, "document": chunk_doc[c], "tier": tier[chunk_doc[c]]}
                                               for c in hits]})
                    row["higher_tier_chunks"] = hits
        outcomes[outcome] += 1
        row["token_screen"] = outcome

        # --- supersession screen (#3049): the same token rule, against the
        # chunks of the cited sources' replacements rather than of a higher tier
        if outcome in ("preamble_only", "exempt"):
            s_outcome = outcome
        elif not all(documents[d].get("superseded_by") for d in v["documents"]):
            s_outcome = "cites_a_current_source"
        else:
            successors = {r for d in v["documents"] for r in replacements(d)} - v["documents"]
            candidates = sorted(cid for cid, doc in chunk_doc.items() if doc in successors)
            tokens = rc._value_tokens(_leaf_text(value))
            if not candidates:
                s_outcome = "no_replacement_chunk"
            elif len(tokens) < min_tokens or sum(len(t) for t in tokens) < min_chars:
                s_outcome = "below_floor"
            else:
                hits = [cid for cid in candidates if cid in hay and tokens <= hay[cid]]
                s_outcome = "replacement_match" if hits else "no_replacement_match"
                if hits:
                    phrase = _folded(_leaf_text(value))
                    in_order = any(phrase in folded[c] for c in hits)
                    s_verbatim += in_order
                    s_also_tier += outcome == "higher_tier_match"
                    excerpt = " ".join(_leaf_text(value).split())
                    s_flagged.append({
                        "path": path,
                        "value": excerpt[:VALUE_EXCERPT] + ("…" if len(excerpt) > VALUE_EXCERPT else ""),
                        "tokens": len(tokens),
                        "verbatim": in_order,
                        "also_higher_tier_match": outcome == "higher_tier_match",
                        "cited": [{"document": d, "tier": tier[d], "superseded_by": documents[d]["superseded_by"],
                                   "chunks": sorted(c for c in v["chunks"] if chunk_doc.get(c) == d)}
                                  for d in sorted(v["documents"], key=lambda d: (tier[d], d))],
                        "replacement_chunks": [{"chunk": c, "document": chunk_doc[c], "tier": tier[chunk_doc[c]]}
                                               for c in hits]})
                    row["replacement_chunks"] = hits
        s_outcomes[s_outcome] += 1
        row["supersession_screen"] = s_outcome
        by_path.append(row)

    documents_cited = Counter(len(v["documents"]) for v in citing.values())
    single = len(sole_of)
    return {
        "instrument": INSTRUMENT,
        "unit": UNIT,
        "project": project,
        "bundle_md5": chunk_manifest.get("bundle_md5"),
        "source_manifest_sha256": authority["sha256"],
        "paths": n,
        "entries": {k: entries.get(k, 0) for k in
                    ("pairs", "kept", "unresolved_in_final", "on_unknown_chunks", "empty_slot")},
        "paths_unresolved_in_final": len(unresolved_paths - set(citing)),
        "single_document": {"paths": single, "share": _share(single, n)},
        "paths_by_citing_documents": {k: documents_cited[k] for k in sorted(documents_cited)},
        "by_tier": tier_rows,
        "documents": doc_rows,
        "unranked": [{"document": d["document"], "source": d["source"], "basis": d["priority_basis"]}
                     for d in doc_rows if d["tier"] == UNRANKED],
        "preamble": {"chunks": preamble_chunks, "citations": preamble_citations,
                     "paths_cited": sum(1 for v in citing.values() if v["preamble"]),
                     "paths_cited_only_by_preamble": outcomes["preamble_only"]},
        "redundant_with": {"entries": redundant_entries, "documents_pointed_to": sorted(redundant_targets)},
        "lower_tier_with_higher_tier_token_match": {
            "count": outcomes["higher_tier_match"],
            "screened": outcomes["higher_tier_match"] + outcomes["no_higher_tier_match"],
            "verbatim": verbatim,
            "outcomes": {k: outcomes[k] for k in SCREEN_OUTCOMES},
            "floors": {"min_tokens": min_tokens, "min_chars": min_chars, "token_min_chars": TOKEN_MIN_CHARS},
            "by_cited_tier": [{"tier": t, "paths": by_cited_tier[t]} for t in sorted(by_cited_tier)],
            "chunks_without_text": no_text,
            "examples": flagged[:examples],
            "examples_truncated": max(0, len(flagged) - examples) or None},
        "superseded_with_replacement_token_match": {
            "count": s_outcomes["replacement_match"],
            "screened": s_outcomes["replacement_match"] + s_outcomes["no_replacement_match"],
            "verbatim": s_verbatim,
            "also_higher_tier_match": s_also_tier,
            "outcomes": {k: s_outcomes[k] for k in SUPERSESSION_OUTCOMES},
            "superseded_documents": [{"document": k, "superseded_by": d["superseded_by"]}
                                     for k, d in documents.items() if d.get("superseded_by")],
            "examples": s_flagged[:examples],
            "examples_truncated": max(0, len(s_flagged) - examples) or None},
        "by_path": by_path,
        "non_checks": non_checks(),
    }


# ---------------------------------------------------------------- on disk
def run_chunks(provenance: Path) -> dict[str, Any]:
    """The chunk manifest and chunk texts a run's receipt was written
    against, from its provenance record. Read-only.

    The bytes are the bundle on disk when they hash to the record's
    `bundle_md5` (and `bundle_sha256`, where recorded), else the committed
    version of the declared path that does (`provenance.bundle_bytes_for`,
    #1140). The manifest is rebuilt from those bytes under the record's own
    `inputs.chunks.rule` and must reproduce `inputs.chunks.sha256` — so the
    chunk ids are the record's whichever file supplied the bytes. Raises
    `ValueError` naming why when it cannot, and `provenance.GitUnavailable`
    when git cannot answer.
    """
    import yaml

    from data_sheets_schema import backfill_checks as bc
    from data_sheets_schema import chunking
    from data_sheets_schema.provenance import bundle_bytes_for

    record = yaml.safe_load(bc._split_header(provenance.read_text(encoding="utf-8"))[1]) or {}
    if not isinstance(record, dict):
        raise ValueError(f"{provenance} is not a mapping")
    inputs = record.get("inputs") if isinstance(record.get("inputs"), dict) else {}
    chunks = inputs.get("chunks") if isinstance(inputs.get("chunks"), dict) else {}
    if not chunks.get("rule") or not chunks.get("sha256"):
        raise ValueError(f"{provenance} names no chunk rule and manifest digest (inputs.chunks), so its "
                         "receipt's chunk ids cannot be tied to bytes")
    recorded = {k: inputs[f"bundle_{k}"] for k in ("md5", "sha256") if inputs.get(f"bundle_{k}")}
    if not recorded:
        raise ValueError(f"{provenance} records no bundle hash, so the bytes its receipt read cannot be identified")
    digest = {"md5": lambda b: hashlib.md5(b).hexdigest(), "sha256": lambda b: hashlib.sha256(b).hexdigest()}
    bundle = bc.declared_bundle(record, provenance)
    raw: bytes | None = None
    if bundle is not None and bundle.exists():
        disk = bundle.read_bytes()
        if all(digest[k](disk) == v for k, v in recorded.items()):
            raw, basis = disk, {"source": "bundle on disk", "path": str(bundle)}
    if raw is None:
        rel = inputs.get("bundle_path")
        if not rel:
            raise ValueError("the bundle on disk is not the bytes the record hashed, and the record declares "
                             "no bundle path to look for the version it read")
        found = bundle_bytes_for(rel, md5=recorded.get("md5"), sha256=recorded.get("sha256"))
        if found is None:
            raise ValueError(f"no committed version of {rel} hashes to the record's {' and '.join(recorded)}")
        raw, entry = found
        basis = {"source": "git blob", "path": rel, "commit": entry["commit"]}
    name = chunks.get("bundle_name") or (chunking.canonical_name(bundle) if bundle is not None
                                         else Path(str(inputs.get("bundle_path") or "")).name)
    try:
        manifest = chunking.manifest_from_bytes(raw, name, chunks["rule"])
    except (KeyError, TypeError) as exc:
        raise ValueError(f"the recorded chunk rule cannot be applied ({exc!r})") from None
    if hashlib.sha256(chunking.dump_manifest(manifest).encode("utf-8")).hexdigest() != chunks["sha256"]:
        raise ValueError("the bytes the record hashed, chunked under its recorded rule, do not reproduce "
                         "inputs.chunks.sha256; the receipt's chunk identities cannot be established")
    texts = dict(zip([c["id"] for c in manifest["chunks"]],
                     chunking.chunk_texts(raw.decode("utf-8"), manifest["chunks"])))
    return {"record": record, "manifest": manifest, "texts": texts, "basis": basis}


def run_source_manifest(record: dict[str, Any], provenance: Path) -> tuple[bytes, dict[str, Any]]:
    """The source manifest bytes a run recorded (`inputs.source_manifest`),
    for `--at-run-commit` (#3050). Read-only.

    The bytes are the manifest on disk at the recorded path when they hash to
    every hash the run kept, else the newest committed version of that path
    that does — recovered by hash, as `run_chunks` recovers a bundle
    (`provenance.committed_bytes_for`, #1140/#3412), not by the record's commit. Raises
    `ValueError` naming why when the run recorded no path or no hash or no
    version matches, and `provenance.GitUnavailable` when git cannot answer
    (a shallow clone among them).
    """
    from data_sheets_schema.provenance import committed_bytes_for, resolve_record_input

    inputs = record.get("inputs") if isinstance(record.get("inputs"), dict) else {}
    recorded = inputs.get("source_manifest") if isinstance(inputs.get("source_manifest"), dict) else {}
    rel = recorded.get("path")
    if not isinstance(rel, str) or not rel:
        why = f" ({recorded['basis']})" if isinstance(recorded.get("basis"), str) else ""
        raise ValueError(f"{provenance} records no source manifest path (inputs.source_manifest){why}, so the "
                         "bytes its run read cannot be looked for")
    hashes = {k: recorded[k] for k in ("md5", "sha256") if isinstance(recorded.get(k), str) and recorded[k]}
    if not hashes:
        raise ValueError(f"{provenance} records no source manifest hash, so the bytes its run read cannot be "
                         "identified")
    digest = {"md5": lambda b: hashlib.md5(b).hexdigest(), "sha256": lambda b: hashlib.sha256(b).hexdigest()}
    disk = resolve_record_input(Path(rel), provenance)
    if disk is not None and disk.is_file():
        raw = disk.read_bytes()
        if all(digest[k](raw) == v for k, v in hashes.items()):
            return raw, {"source": "manifest on disk", "path": str(disk)}
    found = committed_bytes_for(rel, md5=hashes.get("md5"), sha256=hashes.get("sha256"))
    if found is None:
        raise ValueError(f"no committed version of {rel} hashes to the run's recorded "
                         f"{' and '.join(hashes)}")
    raw, entry = found
    return raw, {"source": "git blob", "path": rel, "commit": entry["commit"]}


def source_manifest_basis(record: dict[str, Any], raw: bytes) -> dict[str, Any]:
    """Whether the source manifest the tiers come from is the one the run
    recorded (`inputs.source_manifest`), compared by whichever hash the run
    kept. `same_bytes` is None when the run recorded no hash to compare."""
    inputs = record.get("inputs") if isinstance(record.get("inputs"), dict) else {}
    recorded = inputs.get("source_manifest") if isinstance(inputs.get("source_manifest"), dict) else {}
    hashes = {k: recorded[k] for k in ("sha256", "md5") if isinstance(recorded.get(k), str)}
    here = {"sha256": hashlib.sha256(raw).hexdigest(), "md5": hashlib.md5(raw).hexdigest()}
    return {"recorded": recorded or None,
            "same_bytes": all(here[k] == v for k, v in hashes.items()) if hashes else None}


def basis_label(basis: dict[str, Any]) -> str:
    """Where bytes were read from, for a text line. A `git blob` basis
    carries the *commit* the blob was found at, not the blob's own hash, so
    the line says `git blob at commit <hash>` (#3476): `git cat-file blob`
    on a commit hash fails. The JSON keeps the basis as it is."""
    source = basis.get("source", "?")
    if not basis.get("commit"):
        return source
    return f"{source} at commit {basis['commit'][:12]}"


def render(report: dict[str, Any]) -> list[str]:
    """The report as terminal lines (`d4d receipts sources`)."""
    n = report["paths"]

    def share(x: float | None) -> str:
        return "n/a" if x is None else f"{x:.3f}"

    run = report.get("run") or {}
    basis = run.get("bundle_basis") or {}
    where = basis_label(basis)
    tiers_from = run.get("source_manifest", "the source manifest")
    if run.get("source_manifest_bytes"):              # --at-run-commit: say where the recorded bytes came from
        tiers_from = f"{tiers_from} ({basis_label(run['source_manifest_bytes'])})"
    same = (run.get("source_manifest_basis") or {}).get("same_bytes")
    note = {True: "the bytes the run recorded", False: "not the bytes the run recorded",
            None: "the run recorded no hash to compare"}[same]
    e = report["entries"]
    lines = [f"   {report['project']} · {run.get('label', '?')} ({run.get('method', '?')}) · chunks from the {where}",
             f"   tiers: {tiers_from} sha256 {report['source_manifest_sha256'][:12]} ({note})",
             f"   unit: {report['unit']}",
             f"   paths {n}, from {e['kept']} of {e['pairs']} extracted pairs ({e['unresolved_in_final']} unresolved "
             f"in the final record, {e['on_unknown_chunks']} on chunks not in the manifest, "
             f"{e['empty_slot']} with no slot)",
             f"   cited by exactly one document: {report['single_document']['paths']}/{n} "
             f"({share(report['single_document']['share'])}) · paths by citing documents: "
             + (", ".join(f"{k}: {v}" for k, v in report["paths_by_citing_documents"].items()) or "none"),
             "   by tier (sole: the path's only citing document is of this tier; best: its highest-tier citation)"]
    for t in report["by_tier"]:
        name = f"unranked ({UNRANKED})" if t["tier"] == UNRANKED else f"tier {t['tier']}"
        lines.append(f"     {name:<14} sole {t['paths_sole_document']}/{n} ({share(t['sole_share'])}) · "
                     f"best {t['paths_best_tier']} · citing {t['paths_citing']}")
    lines.append("   documents (sole: paths this document alone cites)")
    width = max((len(d["document"]) for d in report["documents"]), default=0)
    for d in report["documents"]:
        extra = f" · superseded by {d['superseded_by']}" if d.get("superseded_by") else ""
        lines.append(f"     {d['document']:<{width}}  tier {d['tier']:<2}  sole {d['paths_sole']}/{n} "
                     f"({share(d['sole_share'])})  citing {d['paths_citing']}{extra}")
    unranked = report["unranked"]
    lines.append(f"   unranked (tier {UNRANKED}, listed apart): "
                 + (", ".join(f"{u['document']} ({u['basis']})" for u in unranked) if unranked else "none"))
    p = report["preamble"]
    lines.append(f"   preamble ({', '.join(p['chunks']) or 'no chunk'}; not a source document, no tier): "
                 f"{p['citations']} citation(s) on {p['paths_cited']} path(s), "
                 f"{p['paths_cited_only_by_preamble']} cited by it alone")
    r = report["redundant_with"]
    if r["entries"]:
        lines.append(f"   redundant_with: {r['entries']} entr{'y' if r['entries'] == 1 else 'ies'} itemize no paths"
                     + (f"; the sole shares of {', '.join(r['documents_pointed_to'])} may overstate dependence"
                        if r["documents_pointed_to"] else ""))
    m = report["lower_tier_with_higher_tier_token_match"]
    o, f = m["outcomes"], m["floors"]
    lines.append(f"   lower tier, higher-tier token match: {m['count']} of {m['screened']} screened paths "
                 f"({m['verbatim']} verbatim) are cited only by documents ranked below a chunk that holds every "
                 "token of the value "
                 f"(floors: {f['min_tokens']} tokens of {f['token_min_chars']}+ characters, {f['min_chars']} "
                 f"in all) · {o['below_floor']} below the floors · {o['no_higher_tier_chunk']} at the highest "
                 f"tier in the bundle · {o['exempt']} exempt · {o['preamble_only']} preamble only")
    if m["chunks_without_text"]:
        lines.append(f"     not screened against (no text): {', '.join(m['chunks_without_text'])}")
    for ex in m["examples"]:
        cited = "; ".join(f"{c['document']} (tier {c['tier']}, {', '.join(c['chunks'])})" for c in ex["cited"])
        found = "; ".join(f"{h['chunk']} {h['document']} (tier {h['tier']})" for h in ex["higher_tier_chunks"])
        lines.append(f"     {ex['path']} = {ex['value']!r}: cited {cited}; "
                     f"{'verbatim' if ex['verbatim'] else 'tokens'} in {found}")
    if m["examples_truncated"]:
        lines.append(f"     … {m['examples_truncated']} more (--examples, or --json for every path)")
    s = report["superseded_with_replacement_token_match"]
    so = s["outcomes"]
    lines.append(f"   superseded, replacement token match: {s['count']} of {s['screened']} screened paths "
                 f"({s['verbatim']} verbatim, {s['also_higher_tier_match']} also in the tier screen) are cited "
                 "only by superseded documents while a replacement's chunk holds every token of the value "
                 f"(same floors) · {so['cites_a_current_source']} cite a current source · "
                 f"{so['no_replacement_chunk']} with no replacement chunk in the bundle · "
                 f"{so['below_floor']} below the floors · {so['exempt']} exempt · "
                 f"{so['preamble_only']} preamble only")
    for ex in s["examples"]:
        cited = "; ".join(f"{c['document']} (tier {c['tier']}, superseded by {c['superseded_by']}, "
                          f"{', '.join(c['chunks'])})" for c in ex["cited"])
        found = "; ".join(f"{h['chunk']} {h['document']} (tier {h['tier']})" for h in ex["replacement_chunks"])
        lines.append(f"     {ex['path']} = {ex['value']!r}: cited {cited}; "
                     f"{'verbatim' if ex['verbatim'] else 'tokens'} in {found}")
    if s["examples_truncated"]:
        lines.append(f"     … {s['examples_truncated']} more (--examples, or --json for every path)")
    lines += [f"   · not checked here: {nc}" for nc in report["non_checks"]]
    return lines
