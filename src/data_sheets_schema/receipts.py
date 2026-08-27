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
EXEMPT_SLOTS = frozenset({
    "conforms_to", "conforms_to_standard", "conforms_to_schema", "conforms_to_class",
    "notes", "source_caveats",
})
#: Leaf keys exempt wherever they appear (nested entries carry their own).
EXEMPT_LEAVES = frozenset({"conforms_to_class", "conforms_to_schema", "notes"})

NON_CHECKS = (
    "that a chunk marked nothing_relevant truly held nothing for the record — a "
    "judgement; sample by chunk id in review",
    "that a verified snippet supports the value it is attached to — a snippet "
    "can be real and irrelevant; sample by slot path in review",
)


# ---------------------------------------------------------------- normalise
_EDITORIAL = re.compile(r"\[[^\]]*\]")
_NONWORD = re.compile(r"[^\w\s]+", re.UNICODE)
_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    """DisMech's folding, minus the Greek-letter table: editorial `[...]`
    stripped, Unicode compatibility-normalised, case folded, punctuation to
    space, whitespace collapsed."""
    t = unicodedata.normalize("NFKC", _EDITORIAL.sub(" ", text))
    t = _NONWORD.sub(" ", t.casefold())
    return _WS.sub(" ", t).strip()


def snippet_in(snippet: str, chunk_text: str) -> tuple[bool, str]:
    """(verified, reason). `...` splits the snippet into parts matched
    independently, in order."""
    hay = normalise(chunk_text)
    parts = [normalise(p) for p in re.split(r"\.{3}|…", snippet)]
    parts = [p for p in parts if p]
    if not parts:
        return False, "empty after normalisation"
    pos = 0
    for p in parts:
        i = hay.find(p, pos)
        if i < 0:
            return False, (f"part not found in chunk: {p[:60]!r}" if len(parts) > 1
                           else "not found in chunk")
        pos = i + len(p)
    return True, ""


# ---------------------------------------------------------------- record walk
def _is_leaf(value: Any) -> bool:
    return not isinstance(value, (dict, list)) or (
        isinstance(value, list) and all(not isinstance(v, (dict, list)) for v in value))


def _populated(value: Any) -> bool:
    return value not in (None, [], {}, "")


def _minted(value: Any) -> bool:
    return isinstance(value, str) and (value.startswith("urn:") or "#" in value)


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


def exempt(path: str, value: Any) -> bool:
    top = re.split(r"[.\[]", path, maxsplit=1)[0]
    leaf = path.rsplit(".", 1)[-1]
    if top in EXEMPT_SLOTS or leaf in EXEMPT_LEAVES:
        return True
    if leaf == "id" and _minted(value):
        return True                      # a minted fragment or urn has no source
    return False


def resolve(record: Any, path: str) -> bool:
    parts = re.findall(r"[\w]+|\[\d+\]", path)
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
    """A receipt on a container path covers every leaf beneath it — one
    snippet may attest a whole entry (a funder, a file)."""
    return leaf_path == receipt_path or leaf_path.startswith(receipt_path + ".") \
        or leaf_path.startswith(receipt_path + "[")


# ---------------------------------------------------------------- derived core
def core_path_map(full: dict[str, Any]) -> dict[str, str]:
    """Full-record path prefix → derived-core path prefix (#694, #711 review
    F1). The derivation builds `distributions` as one entry per
    `file_collections[i]` followed by one per file under it, in order, and
    recursively under `resources[r]`; every other shared slot keeps its path.
    A receipt on `file_collections[0].resources[1].md5` therefore resolves in
    the core as `distributions[2].md5`."""
    out: dict[str, str] = {}

    def walk(node: dict[str, Any], prefix: str) -> None:
        j = 0
        for i, coll in enumerate(node.get("file_collections") or []):
            out[f"{prefix}file_collections[{i}]"] = f"{prefix}distributions[{j}]"
            j += 1
            for k, _f in enumerate((coll or {}).get("resources") or []):
                out[f"{prefix}file_collections[{i}].resources[{k}]"] = f"{prefix}distributions[{j}]"
                j += 1
        for r, res in enumerate(node.get("resources") or []):
            if isinstance(res, dict):
                walk(res, f"{prefix}resources[{r}].")

    walk(full, "")
    return out


def core_path(full_path: str, pmap: dict[str, str]) -> str | None:
    """The derived-core path for a full-record receipt path, or None when the
    slot is full-only (no core counterpart)."""
    for pre in sorted(pmap, key=len, reverse=True):
        if _covers(pre, full_path):
            return pmap[pre] + full_path[len(pre):]
    if full_path.split(".", 1)[0].split("[", 1)[0] == "file_collections":
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


def check(receipt: dict[str, Any], manifest: dict[str, Any], chunk_texts: dict[str, str],
          full: dict[str, Any], record_bundle_md5: str | None) -> dict[str, Any]:
    """The validator. Pure: receipt + manifest + chunk texts + record → block."""
    findings: list[dict[str, Any]] = []
    manifest_ids = [c["id"] for c in manifest.get("chunks") or []]
    entries = receipt.get("chunks") or []

    # --- chunks: exactly once each, no strangers, a status with its predicate
    seen: dict[str, int] = {}
    by_status: dict[str, int] = {s: 0 for s in STATUSES}
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

    # --- snippets, each against its own chunk
    snippets = {"total": 0, "verified": 0, "mismatched": 0, "unchecked": 0}
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
            if text is None:
                snippets["unchecked"] += 1
                continue
            ok, why = snippet_in(snippet, text)
            if ok:
                snippets["verified"] += 1
            else:
                snippets["mismatched"] += 1
                findings.append({"kind": "snippet_mismatch", "chunk": e.get("id"),
                                 "slot": pair.get("slot"), "snippet": snippet[:60], "reason": why})

    # --- slots: paths resolve; every receiptable populated leaf has one
    receipt_paths = sorted({str(p.get("slot", "")) for e in entries if e.get("status") == "extracted"
                            for p in (e.get("extracted") or [])})
    unresolved = [p for p in receipt_paths if not resolve(full, p)]
    for p in unresolved:
        findings.append({"kind": "slot_not_in_record", "slot": p})
    leaves = populated_leaves(full)
    receiptable = [(p, v) for p, v in leaves if not exempt(p, v)]
    without = [p for p, _v in receiptable if not any(_covers(r, p) for r in receipt_paths)]
    slots = {"populated": len(leaves), "exempt": len(leaves) - len(receiptable),
             "receiptable": len(receiptable), "with_receipt": len(receiptable) - len(without),
             "without_receipt": without[:50],
             "without_receipt_truncated": max(0, len(without) - 50) or None,
             "receipt_paths": len(receipt_paths), "unresolved": unresolved}

    chunks = {"total": len(manifest_ids), "reviewed": reviewed, "unreviewed": missing[:50],
              "by_status": by_status}
    measured = snippets["total"] > 0 or len(manifest_ids) > 0
    return {"checked": True, "measured": measured,
            "chunks": chunks, "snippets": snippets, "slots": slots,
            "findings": findings[:100], "findings_truncated": max(0, len(findings) - 100) or None,
            "summary": (f"chunks {reviewed}/{len(manifest_ids)} reviewed · snippets "
                        f"{snippets['verified']}/{snippets['total']} verified"
                        + (f" ({snippets['unchecked']} unchecked)" if snippets["unchecked"] else "")
                        + f" · slots {slots['with_receipt']}/{slots['receiptable']} with a receipt"
                        + (f" ({slots['exempt']} exempt)" if slots["exempt"] else "")),
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
    from data_sheets_schema.chunking import load_manifest, manifest_path

    base = {"expected": expected, "non_checks": list(NON_CHECKS)}
    if not receipt.exists():
        return {**base, "checked": False, "reason": f"no coverage receipt at {receipt}"}
    try:
        rec = load_receipt(receipt)
    except (ValueError, yaml.YAMLError) as exc:
        return {**base, "checked": False, "reason": f"receipt unreadable: {exc}"}
    if bundle is None or not bundle.exists():
        return {**base, "checked": False, "reason": "the record's bundle is absent; chunk texts cannot be loaded"}
    if manifest is not None:
        mpath = manifest
    elif bundle.name.endswith("_preprocessed.txt"):
        mpath = manifest_path(bundle.name[: -len("_preprocessed.txt")])
    else:
        mpath = None
    if mpath is None or not mpath.exists():
        return {**base, "checked": False, "reason": f"no chunk manifest for {bundle.name}"}
    m = load_manifest(mpath)
    raw = bundle.read_bytes()
    if hashlib.md5(raw).hexdigest() != m.get("bundle_md5"):
        return {**base, "checked": False,
                "reason": "the bundle on disk is not the bytes the manifest chunked; rebuild with d4d bundle chunk"}
    if record_bundle_md5 and record_bundle_md5 != m.get("bundle_md5"):
        return {**base, "checked": False,
                "reason": "bundle drifted since the run; the receipt's chunks are not today's bytes"}
    texts = dict(zip([c["id"] for c in m["chunks"]], _texts(raw.decode("utf-8"), m["chunks"])))
    full = (yaml.safe_load(full_path.read_text(encoding="utf-8")) or {}) if full_path.exists() else {}
    block = check(rec, m, texts, full, record_bundle_md5)
    block["artifacts"] = {
        "receipt": {"path": str(receipt), "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest()},
        "manifest": {"path": str(mpath), "sha256": hashlib.sha256(mpath.read_bytes()).hexdigest()},
    }
    return {**base, **block}
