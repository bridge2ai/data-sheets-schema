"""Coverage and claim receipts, and the validator that counts them (#708).

An instruction ("read the whole bundle") asks for a behaviour and cannot
tell laziness from compliance. A receipt makes the behaviour leave a mark a
validator can check (notes/receipts_pattern_2026-08-27.md, after DisMech's
evidence pattern). The unit here is one entry per chunk of the bundle's
chunk manifest (#707), written by the agent as it reads:

    bundle_md5: 9b2ef4…                 # must equal the manifest's
    chunks:
    - id: c001
      status: extracted                 # closed vocabulary, see STATUSES
      extracted:
      - slot: funders[0].grant_id
        snippet: "OT2OD032701"          # verbatim from *this* chunk
    - id: c002
      status: nothing_relevant
      reason: acknowledgements and references only
    - id: c003
      status: redundant_with            # relevant, every fact already receipted
      chunks: [c001]
    - id: c004
      status: duplicate_of              # the same content as another chunk
      of: c001

Inverted by slot, the same (slot, chunk, snippet) triples are the record's
*claim receipts*: which chunk supports each populated slot, with what text.

What the validator checks is deterministic and offline: every manifest chunk
appears exactly once; the md5s agree; every snippet is a substring of its own
chunk under a fixed normalisation; every slot path resolves in the record;
every populated slot that can have a bundle receipt has one. It reports
**affirmative counts** — chunks reviewed N/N, snippets verified M/M, slots
with a receipt S/T — because a validator that counts only failures prints the
same thing for a clean run and a no-op (DisMech's #7252; our #684).

What it cannot check is named in the block, not hidden: that a
`nothing_relevant` chunk truly had nothing, and that a verified snippet
actually supports the value it is attached to (a real quote can be irrelevant
— laundering). Both are review work the receipt makes *specific*: a chunk id
and a slot path instead of "did the agent read the bundle".

Outcomes per snippet are `verified`, `mismatched` (with the reason) or
`unchecked` (the chunk's text could not be loaded). There is no "relaxed"
verdict: DisMech's exists to excuse defects in *its* cache extraction, and
here the chunk *is* the source bytes.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml

STATUSES = ("extracted", "redundant_with", "nothing_relevant", "duplicate_of")

#: Populated slots that have no bundle receipt *by design*: set by the runner,
#: minted by the rule that allows minting, or the run's own commentary. Data,
#: not a review-time judgement — without this list the "slots without a
#: receipt" count is never zero and means nothing (#711 review F2).
EXEMPT_SLOTS = frozenset({"conforms_to_schema", "conforms_to_class"})
#: Leaf keys exempt wherever they appear: the run's own commentary on an
#: entry ("No IRB approval is stated in the bundle") has no snippet by
#: construction — CHORUS v5 carries 28 nested `source_caveats` (#722).
#: `conforms_to`/`conforms_to_standard` are *not* exempt: on CHORUS they are
#: bundle facts (OMOP, DICOM). Dates are not exempt either — a normalised
#: date is receipted by the text it was normalised from.
EXEMPT_LEAVES = frozenset({"conforms_to_class", "conforms_to_schema", "notes", "source_caveats"})
#: A snippet must carry at least this much after normalisation (#720): "a"
#: verifies against any chunk, and an agent could receipt every slot with it.
#: Summed over the `...`-parts, each of which must carry MIN_PART_CHARS: the
#: second v7 canary receipted "50,000...Patient admissions from ICU" and a
#: per-part minimum of 8 rejected the number that anchored it (#763).
MIN_SNIPPET_CHARS = 8          # at least one part carries this much
MIN_PART_CHARS = 3             # every part carries this much
MIN_MULTIPART_CHARS = 12       # a multi-part snippet carries this much in all
MIN_NUMERIC_PART_CHARS = 6     # a part with two digits pins a passage at this length (#780, #784)
_VERSION_LIKE = re.compile(r"^v?\d+( \d+){2,}$")   # "3 0 0": a version string, in a third of a bundle's chunks
# "the ... and ... for" verified in 25 of 28 AI_READI chunks under a
# parts>=3/total>=8 rule (#765); one part of 8 is what pins a snippet to
# a passage, and the numeric anchor rides beside it.

NON_CHECKS = (
    "that a chunk marked nothing_relevant truly held nothing for the record — a "
    "judgement; sample by chunk id in review",
    "that a verified snippet supports the value it is attached to — a snippet "
    "can be real and irrelevant; sample by slot path in review",
)


# ---------------------------------------------------------------- normalise
_NONWORD = re.compile(r"[^\w\s]+", re.UNICODE)
_WS = re.compile(r"\s+")
_ELLIPSIS = re.compile(r"\[\s*\.{3}\s*\]|\.{3}|…")


def normalise(text: str) -> str:
    """DisMech's folding without its editorial `[...]` stripping: Unicode
    compatibility-normalised, case folded, punctuation to space, whitespace
    collapsed. No stripping because the chunk *is* the source bytes — there
    are no editorial insertions to excuse, and stripping ate 23% of
    AI_READI's characters (its JSON arrays) so verbatim values could not
    verify while bracket-padded fabrications could (#720)."""
    # JSON-escaped whitespace inside a bundle's embedded JSON strings is
    # whitespace: the AI_READI citation sits in one with a literal \n where
    # the model quoted a newline (#786).
    text = re.sub(r"\\[ntr]", " ", text).replace('\\"', '"')
    t = _NONWORD.sub(" ", unicodedata.normalize("NFKC", text).casefold())
    return _WS.sub(" ", t).strip()


#: A lone one-or-two-digit section number WITH its dot ("6.", "7.") — the
#: observed PDF artifact class (#887). Deliberately narrow (#889): bare
#: numbers (journal volumes, table cells) and 3+ digits are NOT elided, so
#: a quote omitting a meaningful number still fails. The accepted residual:
#: numbered-LIST markers match, so items quoted as one phrase verify — a
#: test pins that as known behavior.
_ARTIFACT_LINE = re.compile(r"\s*\d{1,2}\.\s*")


def elide_artifact_lines(text: str) -> str:
    """The haystack with lone section-number lines removed (#887): PDF
    extraction drops stray "6." / "7." lines mid-sentence, so an honest
    single-line quotation of the surrounding sentence cannot match any
    contiguous form. Haystack-side, like the linewrap join — the snippet is
    never edited (#720)."""
    return "\n".join(l for l in text.split("\n") if not _ARTIFACT_LINE.fullmatch(l))


def normalise_joined(text: str) -> str:
    """The chunk with hyphenated line breaks joined: a PDF extraction that
    wrapped mid-word ("Partic-\nipants") reads as the word a quoting model
    wrote (#789). Tried second, after the plain form."""
    # Only a hyphenated break joins ("Partic-\nipants"): the hyphen is the
    # extractor's, not the word's. Every other line break stays whitespace,
    # or "bias\nknown" would read "biasknown".
    return normalise(re.sub(r"(\w)-[ \t]*\n[ \t]*(\w)", r"\1\2", text.replace("\r", "")))


def snippet_in(snippet: str, chunk_text: str, hay: str | None = None,
               hay_joined: str | None = None, hay_elided: str | None = None,
               hay_joined_elided: str | None = None) -> tuple[bool, str]:
    """(verified, reason). `...` (or `[...]`) splits the snippet into parts
    matched independently, in order. `hay` is the chunk already normalised,
    for a caller checking many snippets against one chunk (#766);
    `hay_joined` its line-break-joined form (#789). A match found only in
    the joined form returns the reason "linewrap-joined" so the caller can
    count it."""
    hay = normalise(chunk_text) if hay is None else hay
    parts = [normalise(p) for p in _ELLIPSIS.split(snippet)]
    parts = [p for p in parts if p]
    if not parts:
        return False, "empty after normalisation"
    short = [p for p in parts if len(p) < MIN_PART_CHARS]
    # A part that carries a digit pins a passage at five characters —
    # "165,051", "3.82 TB" are exact slot values, not common words (#780).
    def pins(p: str) -> bool:
        if len(p) >= MIN_SNIPPET_CHARS:
            return True
        return (len(p) >= MIN_NUMERIC_PART_CHARS and sum(ch.isdigit() for ch in p) >= 2
                and not _VERSION_LIKE.match(p))
    if (short or not any(pins(p) for p in parts)
            or (len(parts) > 1 and sum(len(p) for p in parts) < MIN_MULTIPART_CHARS)):
        return False, (f"too short to attest anything: {(short or parts)[0]!r} "
                       f"(every part >= {MIN_PART_CHARS}, one part >= {MIN_SNIPPET_CHARS}, "
                       f"a multi-part snippet >= {MIN_MULTIPART_CHARS} in all)")
    def find_all(h: str) -> bool:
        pos = 0
        for p in parts:
            i = h.find(p, pos)
            if i < 0:
                return False
            pos = i + len(p)
        return True
    if find_all(hay):
        return True, ""
    hj = normalise_joined(chunk_text) if hay_joined is None else hay_joined
    if hj and find_all(hj):
        return True, "linewrap-joined"
    # #887: the single-line variant of the artifact interruption — try the
    # haystack with lone section-number lines elided (both plain and
    # linewrap-joined forms).
    if hay_elided is None:
        hay_elided = normalise(elide_artifact_lines(chunk_text)) if chunk_text else ""
    if hay_joined_elided is None:
        hay_joined_elided = normalise_joined(elide_artifact_lines(chunk_text)) if chunk_text else ""
    he, hje = hay_elided, hay_joined_elided
    if he and he != hay and find_all(he):
        return True, "artifact-line-elided"
    if hje and hje != hj and find_all(hje):
        return True, "artifact-line-elided"
    # A stray extraction artifact can interrupt a sentence mid-quote — the
    # AI_READI license text reads "…of any term / 7. / of this Agreement"
    # (#882) — so an honest multi-line quotation fails contiguity while every
    # line of it is verbatim. Retry with the snippet's own line breaks as
    # implicit ellipsis separators: the same parts logic, same #720 floors,
    # same in-order requirement the explicit "..." form already gets. Parity,
    # not relaxation — and counted apart as "split-at-linebreaks".
    if "\n" in snippet:
        nl_parts = [normalise(x) for x in snippet.split("\n")]
        nl_parts = [x for x in nl_parts if x]
        if (len(nl_parts) > 1 and not [x for x in nl_parts if len(x) < MIN_PART_CHARS]
                and any(pins(x) for x in nl_parts)
                and sum(len(x) for x in nl_parts) >= MIN_MULTIPART_CHARS):
            def find_all_parts(h: str, ps: list) -> bool:
                pos = 0
                for x in ps:
                    i = h.find(x, pos)
                    if i < 0:
                        return False
                    pos = i + len(x)
                return True
            if (find_all_parts(hay, nl_parts) or (hj and find_all_parts(hj, nl_parts))
                    or (he and find_all_parts(he, nl_parts)) or (hje and find_all_parts(hje, nl_parts))):
                return True, "split-at-linebreaks"
    return False, (f"part not found in chunk: {parts[0][:60]!r}" if len(parts) > 1
                   else "not found in chunk")


# ---------------------------------------------------------------- record walk
def _is_leaf(value: Any) -> bool:
    return not isinstance(value, (dict, list)) or (
        isinstance(value, list) and all(not isinstance(v, (dict, list)) for v in value))


def _populated(value: Any) -> bool:
    return value not in (None, [], {}, "")


def _minted(value: Any, record_id: str | None = None) -> bool:
    """A urn, or a fragment on the record's own id — the form the rules allow
    minting in. A `#` on some other base is a real anchor, not a minting."""
    if not isinstance(value, str):
        return False
    if value.startswith("urn:"):
        return True
    return bool(record_id) and "#" in value and value.split("#", 1)[0] == str(record_id)


def populated_leaves(record: dict[str, Any]) -> list[tuple[str, Any]]:
    """(path, value) for every populated leaf slot, depth first, in record order."""
    out: list[tuple[str, Any]] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                p = f"{path}.{k}" if path else k
                if _is_leaf(v):
                    if _populated(v):
                        out.append((p, v))
                else:
                    walk(v, p)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(record, "")
    return out


def exempt(path: str, value: Any, record_id: str | None = None) -> bool:
    top = re.split(r"[.\[]", path, maxsplit=1)[0]
    leaf = path.rsplit(".", 1)[-1]
    if top in EXEMPT_SLOTS or leaf in EXEMPT_LEAVES:
        return True
    if leaf == "id" and _minted(value, record_id):
        return True                      # a minted fragment or urn has no source
    return False


def resolve(record: Any, path: str) -> bool:
    parts = re.findall(r"[\w]+|\[\d+\]", path)
    if not parts or not re.fullmatch(r"\w+(\[\d+\])*(\.\w+(\[\d+\])*)*", path):
        return False                     # "" and malformed paths resolve to nothing (#721)
    cur = record
    for part in parts:
        if part.startswith("["):
            i = int(part[1:-1])
            if not isinstance(cur, list) or i >= len(cur):
                return False
            cur = cur[i]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return False
            cur = cur[part]
    return True


def _covers(receipt_path: str, leaf_path: str) -> bool:
    """A receipt on an *entry* (a dict: `funders[0]`) covers the leaves
    beneath it — one snippet may attest a funder or a file, which is also how
    a boolean or enum leaf gets its receipt. A receipt on a *list*
    (`funders`) covers only itself: it must not attest every entry at once
    (#721)."""
    return leaf_path == receipt_path or leaf_path.startswith(receipt_path + ".")


# ---------------------------------------------------------------- derived core
def core_path_map(full: dict[str, Any]) -> dict[str, str]:
    """Full-record path prefix → derived-core path prefix (#694, #711 review
    F1). The derivation builds `distributions` as one entry per
    `file_collections[i]` followed by one per file under it, in order, and
    recursively under `resources[r]`; every other shared slot keeps its path.
    A receipt on `file_collections[0].resources[1].md5` therefore resolves in
    the core as `distributions[2].md5`."""
    from data_sheets_schema.derive_core import derive_core
    out: dict[str, str] = {}

    def index_by_id(items: Any) -> dict[str, int]:
        return {e["id"]: j for j, e in enumerate(items or [])
                if isinstance(e, dict) and isinstance(e.get("id"), str)}

    def walk(node: dict[str, Any], core_node: dict[str, Any], prefix: str) -> None:
        # By id against the core the derivation actually produces, not by
        # counting: the derivation skips an entry that projects to nothing
        # and recurses only into resources with a string id (#723).
        dists = index_by_id(core_node.get("distributions"))
        out[f"{prefix}file_collections"] = f"{prefix}distributions"
        for i, coll in enumerate(node.get("file_collections") or []):
            if not isinstance(coll, dict):
                continue
            j = dists.get(coll.get("id"))
            if j is not None:
                out[f"{prefix}file_collections[{i}]"] = f"{prefix}distributions[{j}]"
            for k, f in enumerate(coll.get("resources") or []):
                jf = dists.get(f.get("id")) if isinstance(f, dict) else None
                if jf is not None:
                    out[f"{prefix}file_collections[{i}].resources[{k}]"] = f"{prefix}distributions[{jf}]"
        core_res = index_by_id(core_node.get("resources"))
        for r, res in enumerate(node.get("resources") or []):
            if isinstance(res, dict) and res.get("id") in core_res:
                cr = core_res[res["id"]]
                if cr != r:
                    out[f"{prefix}resources[{r}]"] = f"{prefix}resources[{cr}]"
                walk(res, core_node["resources"][cr], f"{prefix}resources[{r}].")

    walk(full, derive_core(full), "")
    return out


def core_path(full_path: str, pmap: dict[str, str]) -> str | None:
    """The derived-core path for a full-record receipt path, or None when the
    slot is full-only (no core counterpart)."""
    for pre in sorted(pmap, key=len, reverse=True):
        if full_path == pre or full_path.startswith(pre + ".") or full_path.startswith(pre + "["):
            rest = full_path[len(pre):]
            if rest.startswith("["):
                return None              # an entry the derivation did not carry
            return pmap[pre] + rest
    if "file_collections" in full_path:
        return None
    return full_path


# ---------------------------------------------------------------- receipt
def load_receipt(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("chunks"), list):
        raise ValueError(f"{path}: a receipt is a mapping with a `chunks` list")
    return data


def claim_receipts(receipt: dict[str, Any], full: dict[str, Any] | None = None) -> dict[str, Any]:
    """The coverage receipt inverted by slot. With the full record, each
    claim also names its derived-core path (or `null` for a full-only slot)."""
    pmap = core_path_map(full) if full is not None else None
    slots: dict[str, list[dict[str, Any]]] = {}
    for entry in receipt.get("chunks") or []:
        if entry.get("status") != "extracted":
            continue
        for pair in entry.get("extracted") or []:
            slot = str(pair.get("slot", ""))
            slots.setdefault(slot, []).append({"chunk": entry.get("id"),
                                               "snippet": pair.get("snippet")})
    out: dict[str, Any] = {"bundle_md5": receipt.get("bundle_md5"), "slots": {}}
    for slot in sorted(slots):
        item: dict[str, Any] = {"receipts": slots[slot]}
        if pmap is not None:
            item["core_path"] = core_path(slot, pmap)
        out["slots"][slot] = item
    return out


def _value_tokens(node: Any) -> set[str]:
    """Normalised tokens (>= 4 chars) of a value or subtree, for the
    reported overlap flags (#806, #804). Token overlap is a screen, not a
    support judgement — NON_CHECKS still stands."""
    if isinstance(node, (dict, list)):
        text = yaml.safe_dump(node, allow_unicode=True)
    else:
        text = str(node)
    return {t for t in normalise(text.replace("_", " ")).split() if len(t) >= 4}


def _resolve_value(record: Any, path: str) -> tuple[bool, Any]:
    parts = re.findall(r"[\w]+|\[\d+\]", path)
    if not parts:
        return False, None
    cur = record
    for part in parts:
        if part.startswith("["):
            i = int(part[1:-1])
            if not isinstance(cur, list) or i >= len(cur):
                return False, None
            cur = cur[i]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return False, None
            cur = cur[part]
    return True, cur


def check(receipt: dict[str, Any], manifest: dict[str, Any], chunk_texts: dict[str, str],
          full: dict[str, Any], record_bundle_md5: str | None,
          original: dict[str, Any] | None = None) -> dict[str, Any]:
    """The validator. Pure: receipt + manifest + chunk texts + record → block.

    `original` is the record as it stood when the receipt was written (the
    API path's phase-1 snapshot). A receipt path that resolved there but not
    in the final record was reshaped by a later phase — reconcile flattened
    `principal_investigator: {name: …}` to a string on the v7 canary — and is
    reported as `reshaped_by_reconcile`, not as a path that never existed
    (#758). The API path has no re-receipt route after reconcile (#742), so
    this is a measured limitation, kept out of the findings and the gate.
    """
    findings: list[dict[str, Any]] = []
    manifest_ids = [c["id"] for c in manifest.get("chunks") or [] if isinstance(c, dict) and "id" in c]

    # A malformed entry is a finding, never a traceback (#724): the receipt is
    # model output, and the validator's job is to say what is wrong with it.
    entries: list[dict[str, Any]] = []
    for n, e in enumerate(receipt.get("chunks") or []):
        if not isinstance(e, dict) or not isinstance(e.get("id"), str):
            findings.append({"kind": "malformed_entry", "index": n,
                             "reason": "not a mapping with a string id"})
            continue
        pairs = e.get("extracted")
        if e.get("status") == "extracted" and pairs is not None and not (
                isinstance(pairs, list) and all(isinstance(p, dict) for p in pairs)):
            findings.append({"kind": "malformed_entry", "chunk": e["id"],
                             "reason": "extracted is not a list of {slot, snippet} mappings"})
            e = {**e, "extracted": []}
        entries.append(e)

    # --- chunks: exactly once each, no strangers, a status with its predicate
    seen: dict[str, int] = {}
    by_status: dict[str, int] = {s: 0 for s in STATUSES}
    status_of = {e["id"]: e.get("status") for e in entries}
    for e in entries:
        cid = e.get("id")
        seen[cid] = seen.get(cid, 0) + 1
        st = e.get("status")
        if st not in STATUSES:
            findings.append({"kind": "unknown_status", "chunk": cid, "status": st})
            continue
        by_status[st] += 1
        if st == "extracted" and not (e.get("extracted") or []):
            findings.append({"kind": "extracted_without_pairs", "chunk": cid})
        elif st == "nothing_relevant" and not str(e.get("reason") or "").strip():
            findings.append({"kind": "nothing_relevant_without_reason", "chunk": cid})
        elif st == "redundant_with":
            refs = e.get("chunks") or []
            if not refs or any(r not in manifest_ids for r in refs):
                findings.append({"kind": "redundant_with_unknown_chunks", "chunk": cid, "chunks": refs})
            elif any(status_of.get(r) != "extracted" for r in refs):
                # "already receipted from c001" where c001 extracted nothing
                # is a contradiction, not a redundancy (#724).
                findings.append({"kind": "redundant_with_a_chunk_that_extracted_nothing",
                                 "chunk": cid, "chunks": [r for r in refs if status_of.get(r) != "extracted"]})
        elif st == "duplicate_of":
            of = e.get("of")
            if of not in manifest_ids or of == cid:
                findings.append({"kind": "duplicate_of_unknown_chunk", "chunk": cid, "of": of})
    for cid, n in seen.items():
        if cid not in manifest_ids:
            findings.append({"kind": "chunk_not_in_manifest", "chunk": cid})
        elif n > 1:
            findings.append({"kind": "chunk_reviewed_more_than_once", "chunk": cid, "times": n})
    dup_targets = {e.get("of") for e in entries if e.get("status") == "duplicate_of"}
    for e in entries:
        if e.get("status") == "duplicate_of" and e.get("id") in dup_targets:
            findings.append({"kind": "duplicate_of_a_duplicate", "chunk": e.get("id")})
    missing = [cid for cid in manifest_ids if cid not in seen]
    reviewed = sum(1 for cid in manifest_ids if cid in seen)

    # --- md5 agreement
    md5s = {"receipt": receipt.get("bundle_md5"), "manifest": manifest.get("bundle_md5"),
            "record": record_bundle_md5}
    if len({v for v in md5s.values() if v}) > 1 or not md5s["receipt"]:
        findings.append({"kind": "bundle_md5_disagreement", **md5s})

    # --- snippets, each against its own chunk. A snippet that is verbatim
    # in the bundle but in a chunk other than the one cited is a wrong
    # attribution, not a fabrication: both v7 API canaries showed ~2% of
    # these, every one a neighbouring chunk (#763). They are counted apart —
    # `adjacent` (the chunk before or after), `elsewhere` (any other) — and
    # reported, never gated; the floor of 0 is for text found nowhere.
    record_id_flag = full.get("id") if isinstance(full.get("id"), str) else None
    snippets = {"total": 0, "verified": 0, "linewrap_joined": 0, "adjacent": 0, "elsewhere": 0,
                "spans_boundary": 0, "split_at_linebreaks": 0, "artifact_elided": 0,
                # #891: a snippet below the #720 floors attests nothing - it is
                # not evidence and not a misquote. Counted apart, no coverage
                # credit for a slot whose only snippets are unattesting.
                "unattesting": 0, "unattesting_sample": [],
                "mismatched": 0, "unchecked": 0,
                # Reported, never gated (#806, #804): a verified snippet whose
                # normalised tokens overlap nothing in the value it receipts
                # is verbatim laundering the deterministic floor cannot see
                # alone; an entry receipt whose snippet overlaps at most one
                # of several child leaves covers the rest by construction.
                # Token overlap is a screen — NON_CHECKS still stands.
                # Counters with samples, never findings: `--strict` fails on
                # findings and a screen must not gate (#839, #840).
                "no_value_overlap": 0, "no_value_overlap_sample": [],
                "entry_single_leaf": 0, "entry_single_leaf_sample": []}
    order = {cid: i for i, cid in enumerate(manifest_ids)}
    unattesting_pairs: set = set()
    hays = {cid: normalise(t) for cid, t in chunk_texts.items()}      # once per chunk (#766)
    hays_j = {cid: normalise_joined(t) for cid, t in chunk_texts.items()}   # line breaks joined (#789)
    hays_e = {cid: normalise(elide_artifact_lines(t)) for cid, t in chunk_texts.items()}       # #887/#890
    hays_je = {cid: normalise_joined(elide_artifact_lines(t)) for cid, t in chunk_texts.items()}
    for e in entries:
        if e.get("status") != "extracted":
            continue
        text = chunk_texts.get(e.get("id"))
        for pair in e.get("extracted") or []:
            snippets["total"] += 1
            snippet = pair.get("snippet")
            if not isinstance(snippet, str) or not snippet.strip():
                snippets["mismatched"] += 1
                findings.append({"kind": "snippet_empty", "chunk": e.get("id"), "slot": pair.get("slot")})
                continue
            if e.get("id") not in manifest_ids:
                snippets["mismatched"] += 1      # nothing it could be verified against
                continue
            if text is None:
                snippets["unchecked"] += 1
                continue
            ok, why = snippet_in(snippet, text, hays.get(e.get("id")), hays_j.get(e.get("id")),
                                 hays_e.get(e.get("id")), hays_je.get(e.get("id")))
            if ok:
                snippets["verified"] += 1
                if why == "linewrap-joined":
                    snippets["linewrap_joined"] += 1
                elif why == "split-at-linebreaks":
                    snippets["split_at_linebreaks"] += 1
                elif why == "artifact-line-elided":
                    snippets["artifact_elided"] += 1
                spath = str(pair.get("slot") or "")
                # Prefer the value the receipt was written against: on the
                # API path reconcile/repair rewrite after the receipt (#844).
                resolved, value = (_resolve_value(original, spath) if original is not None
                                   else (False, None))
                if not resolved:
                    resolved, value = _resolve_value(full, spath)
                # The record's own id names the record (it is in the
                # denominator, not exempt — #843), and an exempt path is
                # outside the denominator — neither is screened. A boolean
                # or numeric leaf is attested by a sentence whose tokens
                # never equal the value (#841): the screen is text vs text.
                if (resolved and spath != "id" and not exempt(spath, value, record_id_flag)
                        and not isinstance(value, (bool, int, float))):
                    stoks = {t for t in normalise(snippet).split() if len(t) >= 4}
                    if isinstance(value, dict):
                        # An entry receipt covers its leaves by construction
                        # (#721); when the snippet's tokens touch at most one
                        # of several *attestable* leaves — text, not booleans,
                        # numbers or minted ids (#842) — the rest ride along.
                        kids = [(k, v) for k, v in value.items()
                                if _is_leaf(v) and _populated(v)
                                and not isinstance(v, (bool, int, float))
                                and not (k == "id" and _minted(v, record_id_flag))]
                        if len(kids) >= 3 and stoks:
                            hit = sum(1 for _k, v in kids if stoks & _value_tokens(v))
                            if hit <= 1:
                                snippets["entry_single_leaf"] += 1
                                snippets["entry_single_leaf_sample"].append(
                                    {"chunk": e.get("id"), "slot": spath,
                                     "leaves": len(kids), "overlapping": hit})
                    else:
                        vtoks = _value_tokens(value)
                        if stoks and vtoks and not (stoks & vtoks):
                            snippets["no_value_overlap"] += 1
                            snippets["no_value_overlap_sample"].append(
                                {"chunk": e.get("id"), "slot": spath, "snippet": snippet[:60]})
                continue
            if why.startswith("too short"):
                snippets["unattesting"] += 1
                snippets["unattesting_sample"].append({"chunk": e.get("id"),
                                                       "slot": pair.get("slot"),
                                                       "snippet": snippet[:40]})
                unattesting_pairs.add((e.get("id"), str(pair.get("slot") or ""), snippet))
                continue
            where = [
                cid for cid, h in hays.items() if cid != e.get("id")
                and snippet_in(snippet, "", h, hays_j.get(cid), hays_e.get(cid), hays_je.get(cid))[0]]
            # A passage the chunk boundary cuts is in no single chunk (#781):
            # test the cited chunk joined with its neighbours, and report it
            # as spanning rather than as found nowhere.
            if not where and not why.startswith("too short"):
                i = order.get(e.get("id"), -1)
                # Only neighbours whose text is present are joined: a missing
                # neighbour must not splice two non-adjacent chunks (#786).
                window = [manifest_ids[j] for j in (i - 1, i, i + 1) if 0 <= j < len(manifest_ids)]
                joined = "".join(chunk_texts[c] for c in window if c in chunk_texts) if i >= 0 else ""
                if joined and all(c in chunk_texts for c in window) and snippet_in(snippet, joined)[0]:
                    snippets["spans_boundary"] += 1
                    findings.append({"kind": "snippet_spans_boundary", "chunk": e.get("id"),
                                     "slot": pair.get("slot"), "snippet": snippet[:60]})
                    continue
            if where:
                near = any(abs(order.get(cid, -9) - order.get(e.get("id"), 9)) == 1 for cid in where)
                kind = "adjacent" if near else "elsewhere"
                snippets[kind] += 1
                findings.append({"kind": f"snippet_{kind}_chunk", "chunk": e.get("id"), "found_in": where,
                                 "slot": pair.get("slot"), "snippet": snippet[:60]})
            else:
                snippets["mismatched"] += 1
                findings.append({"kind": "snippet_mismatch", "chunk": e.get("id"),
                                 "slot": pair.get("slot"), "snippet": snippet[:60], "reason": why})

    # --- slots: paths resolve; every receiptable populated leaf has one
    all_paths = sorted({str(p.get("slot") or "") for e in entries if e.get("status") == "extracted"
                        for p in (e.get("extracted") or [])})
    attesting = {str(p.get("slot") or "") for e in entries if e.get("status") == "extracted"
                 for p in (e.get("extracted") or [])
                 if (e.get("id"), str(p.get("slot") or ""), p.get("snippet")) not in unattesting_pairs}
    # #893: an unattesting snippet forfeits coverage, but its PATH is still a
    # claim about the record's structure - it runs the same resolution,
    # off-by-one and addressing checks, so a fabricated path cannot hide
    # behind a tiny snippet.
    receipt_paths = all_paths
    unresolved = [p for p in receipt_paths if not resolve(full, p)]
    reshaped = [p for p in unresolved if p and original is not None and resolve(original, p)]
    unresolved = [p for p in unresolved if p not in reshaped]
    # A path that resolves nowhere as written may be an addressing slip
    # rather than a fabricated slot — the 2026-09-01 CM4AI canary wrote
    # creators[43].source_caveats for the value at creators[44] (#876). The
    # first version reclassified any unique ±1 resolution and transferred
    # coverage credit; on a live record 163/170 phantom citations resolved
    # "uniquely", so that rule was hollow (#878). The class is now narrow:
    # the path must parse (#879: the lax prober laundered malformed paths),
    # only the LAST index segment may move, by exactly one, and the target
    # must be either an end-overrun by one (the written index is len(list))
    # or the UNIQUE carrier of that leaf across the whole array (no other
    # entry has the leaf, so the address carries no information the leaf
    # name does not). Reported with the resolved path; the written path
    # keeps NO coverage credit (#878) — escape from the gate is all the
    # reclassification grants, and NON_CHECKS still names snippet-supports-
    # value as unchecked.
    off_by_one = []
    still = []
    for pth in unresolved:
        m = None
        if pth and re.fullmatch(r"\w+(\[\d+\])*(\.\w+(\[\d+\])*)*", pth):
            for m2 in re.finditer(r"\[(\d+)\]", pth):
                m = m2                                       # last index segment
        if m is None:
            still.append(pth); continue
        n = int(m.group(1)); head, tail = pth[:m.start()], pth[m.end():]
        ok_parent, arr = _resolve_value(full, head) if head else (True, full)
        if not (ok_parent and isinstance(arr, list)):
            still.append(pth); continue
        leaf = tail.lstrip(".")
        carriers = [k for k, e in enumerate(arr)
                    if isinstance(e, dict) and leaf and resolve(e, leaf)
                    and _populated(_resolve_value(e, leaf)[1])] if leaf else []
        target = None
        if n == len(arr) and n - 1 >= 0:                     # end-overrun by one
            cand = f"{head}[{n - 1}]{tail}"
            if resolve(full, cand):
                target = cand
        elif leaf and len(carriers) == 1 and abs(carriers[0] - n) == 1:
            target = f"{head}[{carriers[0]}]{tail}"          # unique carrier, one away
        if target:
            off_by_one.append({"path": pth, "resolved_path": target})
        else:
            still.append(pth)
    unresolved = still
    # #891: an unresolved path is ADDRESSING-SHAPED when it parses, its
    # parent array resolves, and the leaf name exists on at least one
    # sibling entry - the variables[24].notes shape: a real passage filed
    # at a wrong interior index that the narrow #878 rule rightly refuses
    # to relocate. Counted apart; the canary floor tolerates
    # ceil(snippets_total/200) of them (exposure-adjusted, registered in
    # the v7 plan). A path that names no real structure stays a finding.
    addressing = []
    kept = []
    for pth in unresolved:
        shaped = False
        if pth and re.fullmatch(r"\w+(\[\d+\])*(\.\w+(\[\d+\])*)*", pth):
            m = None
            for m2 in re.finditer(r"\[(\d+)\]", pth):
                m = m2
            if m is not None:
                head, tail = pth[:m.start()], pth[m.end():]
                okp, arr = _resolve_value(full, head) if head else (True, full)
                leaf = tail.lstrip(".")
                if okp and isinstance(arr, list) and leaf and any(
                        isinstance(x, dict) and resolve(x, leaf) for x in arr):
                    shaped = True
        (addressing if shaped else kept).append(pth)
    unresolved = kept
    for p in unresolved:
        findings.append({"kind": "slot_not_in_record" if p else "slot_empty", "slot": p})
    leaves = populated_leaves(full)
    record_id = full.get("id") if isinstance(full.get("id"), str) else None
    receiptable = [(p, v) for p, v in leaves if not exempt(p, v, record_id)]
    without = [p for p, _v in receiptable if not any(_covers(r, p) for r in attesting)]
    # #807: `without_receipt` is a mixture on the API path. Split against the
    # phase-1 snapshot: a path populated when the receipt was written and not
    # covered then was *never* receipted; one the snapshot lacks was added by
    # a later phase, which has no re-receipt route (#742). None (not 0) when
    # there is no snapshot to split against — the agentic path re-receipts.
    # The split is by *path resolution* in the snapshot, not value identity
    # (#843): a reordered list entry counts as never_receipted, and a repair
    # that rewrote an existing index does too — `added_after_receipt` is a
    # floor on later-phase additions, not the whole of them.
    never_receipted = added_after_receipt = None
    if original is not None:
        never_receipted = sum(1 for p in without if resolve(original, p))
        added_after_receipt = len(without) - never_receipted
    slots = {"populated": len(leaves), "exempt": len(leaves) - len(receiptable),
             "receiptable": len(receiptable), "with_receipt": len(receiptable) - len(without),
             "without_receipt": without[:50],
             "without_receipt_truncated": max(0, len(without) - 50) or None,
             "never_receipted": never_receipted, "added_after_receipt": added_after_receipt,
             "receipt_paths": len(receipt_paths), "unresolved": unresolved,
             "path_off_by_one": off_by_one[:20],
             "path_off_by_one_count": len(off_by_one),
             "addressing_slips": addressing[:20],
             "addressing_slips_count": len(addressing),
             "reshaped_by_reconcile": reshaped,
             "receipts_to_removed_values": len(reshaped)}

    snippets["no_value_overlap_sample"] = snippets["no_value_overlap_sample"][:10]
    snippets["unattesting_sample"] = snippets["unattesting_sample"][:10]
    snippets["entry_single_leaf_sample"] = snippets["entry_single_leaf_sample"][:10]
    chunks = {"total": len(manifest_ids), "reviewed": reviewed, "unreviewed": missing[:50],
              "by_status": by_status}
    # The gated-findings count, computed before the [:100] cap: a block whose
    # reported-only findings crowd the list must not read as gate-clean (#840;
    # latent on main via the adjacent/elsewhere kinds).
    reported_kinds = {"snippet_mismatch", "snippet_empty", "snippet_adjacent_chunk",
                      "snippet_elsewhere_chunk", "snippet_spans_boundary"}
    findings_gated = sum(1 for f in findings if f.get("kind") not in reported_kinds)
    return {"checked": True,
            "chunks": chunks, "snippets": snippets, "slots": slots,
            "findings": findings[:100], "findings_truncated": max(0, len(findings) - 100) or None,
            "findings_gated": findings_gated,
            "summary": (f"chunks {reviewed}/{len(manifest_ids)} reviewed · snippets "
                        f"{snippets['verified']}/{snippets['total']} verified"
                        + (f" ({snippets['unchecked']} unchecked)" if snippets["unchecked"] else "")
                        + (f" ({snippets['linewrap_joined']} across a wrapped line)" if snippets["linewrap_joined"] else "")
                        + (f" ({snippets['split_at_linebreaks']} split at line breaks)" if snippets["split_at_linebreaks"] else "")
                        + (f" ({snippets['artifact_elided']} across an artifact line)" if snippets["artifact_elided"] else "")
                        + (f" ({snippets['unattesting']} unattesting, below the floors)" if snippets["unattesting"] else "")
                        + (f" ({snippets['adjacent']} in an adjacent chunk)" if snippets["adjacent"] else "")
                        + (f" ({snippets['elsewhere']} in another chunk)" if snippets["elsewhere"] else "")
                        + (f" ({snippets['spans_boundary']} spanning a chunk boundary)" if snippets["spans_boundary"] else "")
                        + (f" ({snippets['no_value_overlap']} bearing on no token of their value)"
                           if snippets["no_value_overlap"] else "")
                        + (f" ({snippets['entry_single_leaf']} entry receipt(s) overlapping one leaf)"
                           if snippets["entry_single_leaf"] else "")
                        + f" · slots {slots['with_receipt']}/{slots['receiptable']} with a receipt"
                        + (f" ({slots['never_receipted']} never receipted, "
                           f"{slots['added_after_receipt']} added after the receipt)"
                           if never_receipted is not None and without else "")
                        + (f" ({slots['exempt']} exempt)" if slots["exempt"] else "")
                        + (f" · {len(reshaped)} receipt path(s) reshaped by reconcile" if reshaped else "")
                        + (f" · {len(off_by_one)} receipt path(s) off by one index" if off_by_one else "")
                        + (f" · {len(addressing)} addressing slip(s)" if addressing else "")),
            "non_checks": list(NON_CHECKS)}


# ---------------------------------------------------------------- on disk
def receipt_path(core_dir: Path, project: str) -> Path:
    return core_dir / f"{project}_coverage_receipt.yaml"


def claims_path(core_dir: Path, project: str) -> Path:
    return core_dir / f"{project}_receipts.yaml"


def block_for(full_path: Path, receipt: Path, bundle: Path | None, record_bundle_md5: str | None,
              expected: bool, manifest: Path | None = None) -> dict[str, Any]:
    """The provenance block for one run, or why it could not be computed.

    `expected` is whether this run's procedure was to write a receipt. It is
    carried into the block so the canary gate can tell "no receipt from a
    procedure that writes none" (not gated) from "no receipt from one that
    does" (UNMEASURABLE, #613). A receipt that exists is checked either way.
    """
    import hashlib

    from data_sheets_schema.chunking import chunk_texts as _texts
    from data_sheets_schema.chunking import load_manifest, manifest_for

    base = {"expected": expected, "non_checks": list(NON_CHECKS)}
    if not receipt.exists():
        return {**base, "checked": False, "reason": f"no coverage receipt at {receipt}"}
    try:
        rec = load_receipt(receipt)
    except (ValueError, yaml.YAMLError) as exc:
        return {**base, "checked": False, "reason": f"receipt unreadable: {exc}"}
    if bundle is None or not bundle.exists():
        return {**base, "checked": False, "reason": "the record's bundle is absent; chunk texts cannot be loaded"}
    mpath = manifest if manifest is not None else manifest_for(bundle)
    if not mpath.exists():
        return {**base, "checked": False,
                "reason": f"no chunk manifest for {bundle.name} at {mpath}; run "
                          "`d4d bundle chunk` (every bundle kind is chunked, #725)"}
    try:
        m = load_manifest(mpath)
        if not isinstance(m, dict) or not isinstance(m.get("chunks"), list):
            raise ValueError("manifest is not a mapping with a chunks list")
    except (ValueError, yaml.YAMLError) as exc:
        return {**base, "checked": False, "reason": f"manifest unreadable: {exc}"}
    raw = bundle.read_bytes()
    if hashlib.md5(raw).hexdigest() != m.get("bundle_md5"):
        return {**base, "checked": False,
                "reason": "the bundle on disk is not the bytes the manifest chunked; rebuild with d4d bundle chunk"}
    if record_bundle_md5 and record_bundle_md5 != m.get("bundle_md5"):
        return {**base, "checked": False,
                "reason": "bundle drifted since the run; the receipt's chunks are not today's bytes"}
    texts = dict(zip([c["id"] for c in m["chunks"]], _texts(raw.decode("utf-8"), m["chunks"])))
    full = (yaml.safe_load(full_path.read_text(encoding="utf-8")) or {}) if full_path.exists() else {}
    # The record as the `full` phase wrote it: the API runner's phase-1
    # snapshot beside the receipt under intermediate/ (#758) — written after
    # the runner's value normalisation, so shapes match the record at the
    # path level while the receipt itself came from the raw text. A same-
    # label re-run appends _2, _3 to the snapshot names while the top-level
    # receipt is overwritten, so the contemporary snapshot is the highest-
    # numbered one (#761). Absent on the agentic path, whose Phase 3
    # re-receipts what it changes. A reshaped path is kept out of the
    # findings and is *not* credited for coverage: its leaves show under
    # `without_receipt` until something re-receipts them.
    original = None
    stem = receipt.name.replace("_coverage_receipt.yaml", "_full")
    snaps = sorted((receipt.parent / "intermediate").glob(f"{stem}.yaml")) + sorted(
        (receipt.parent / "intermediate").glob(f"{stem}_[0-9]*.yaml"),
        key=lambda p: int(p.stem.rsplit("_", 1)[1]))
    if snaps:
        try:
            original = yaml.safe_load(snaps[-1].read_text(encoding="utf-8")) or None
        except yaml.YAMLError:
            original = None
    block = check(rec, m, texts, full, record_bundle_md5, original)
    block["artifacts"] = {
        "receipt": {"path": str(receipt), "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest()},
        "manifest": {"path": str(mpath), "sha256": hashlib.sha256(mpath.read_bytes()).hexdigest()},
    }
    return {**base, **block}
