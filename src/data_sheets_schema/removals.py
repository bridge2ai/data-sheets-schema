"""Values deleted after phase 1, classified against the audit (#2923).

`reconcile_full` is told to "remove what a finding identifies as
unsupported", and nothing checked that each value it removed was named by a
finding. The checks beside it measure other things: the receipts block counts
receipt paths that stopped resolving (`receipts_to_removed_values`) and mixes
deletions with list-to-string flattenings; `report_claims` compares the
report with the record at the top level only (`removals_unrecorded`, #1054).
Three v8 API records lost a receipted value that no audit finding named —
VOICE 04f rep2 `data_governance`, AI_READI 04g rep3 `content_warnings`,
CHORUS 04f rep2 `regulatory_restrictions` — and the report regate's remedy
for an unrecorded removal is a `removed` row, which documents the deletion
rather than restoring the value.

This module diffs the phase-1 snapshot (the API runner's
`intermediate/{P}_full.yaml`) against the final full record, value by value,
and puts every value the final record no longer carries in one class:

``flattened``
    the value's text survives, normalised, under its nearest ancestor that
    survives (a list collapsed to a string, an object to prose, an entry
    folded into another). Not a deletion.
``founded``
    deleted, and an audit finding's `slot`, `review_paths` or
    `remove_relationship` path covers the value's path or an ancestor of it.
``unfounded``
    deleted, and no finding's path covers it.

A value is a populated scalar, or one member of a list of scalars. Its
identity across the diff is `receipts.remap_path`'s (#899): a list entry is
followed by its key, else by the overlap of its scalars, and an entry whose
minted key reconciliation stripped is located at its own index
(`same_key_stripped`, #1053) — so a reorder, an insertion ahead of an entry or
a stripped key is not a removal. A value emptied to null or "" is removed.
A member of a list of scalars is identified by its text, so a rewritten
member reads as removed unless its old text survives in the list (flattened).
Class declarations, `source_caveats` and minted ids are outside the
classification (`exempt_value`).

The removing phase is the first stage after the last one that still carried
the value: `reconcile_full`, `repair_full_rN`, or `write` (the last phase
output carried it and the written record does not).

Reported only. No provenance block is written here and nothing is gated:
`unfounded` says no finding's path covers the value, not that the removal was
wrong, and `founded` says a finding named it, not that the finding was right.
With no phase-1 snapshot (the agentic path writes none) every count is None,
never 0 — the #899 convention: an absent snapshot is not a clean diff.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from data_sheets_schema.receipts import (_canonical_identifier, _populated, _resolve_value,
                                         dataset_identifier_forms, exempt, normalise, remap_path)

INSTRUMENT = ("removals v1 (#2923): phase-1 snapshot against the final full record, joined by "
              "receipts.remap_path; flattened by normalised containment under the nearest "
              "surviving ancestor; founded by a finding's slot, review_paths or "
              "remove_relationship path covering the value or an ancestor, in a finding whose "
              "record is not core only")

#: Paths kept in the block per class; the counts are never capped.
PATH_LIMIT = 50

#: The grammar `receipts.remap_path` reads. A key outside it cannot be joined.
_ADDRESSABLE = re.compile(r"\w+(\[\d+\])*(\.\w+(\[\d+\])*)*")

NON_CHECKS = (
    "that an unfounded removal was wrong — a value can be unsupported with no finding naming "
    "it; unfounded says only that no finding's path covers it",
    "that a founded removal was right — a finding naming a slot is not evidence that its "
    "value was unsupported",
    "that a flattened value kept its meaning — normalised text containment under the nearest "
    "surviving ancestor, not a semantic comparison",
    "a finding that narrows its slot in prose ('maintainers (the Emory contact)') is read at "
    "the path it names, so founded is an upper bound where findings narrow by prose",
)


# ------------------------------------------------------------------ values
def exempt_value(path: str, value: Any, record_id: str | None, carried: frozenset[str]) -> bool:
    """Outside the classification: what the receipts denominator exempts
    (`receipts.exempt`) — the class declarations, the run's commentary in
    `source_caveats`, an id minted on the record's own identifiers, none of
    which has a source to delete — except `notes`. The receipts block
    exempts `notes` because a note needs no receipt; a deleted note is
    still deleted content, and an entry's notes can be the entry: the one
    receipted value AI_READI 04g rep3 lost with `content_warnings` was
    `content_warnings[0].notes`."""
    return exempt(path, value, record_id, carried) and path.rsplit(".", 1)[-1] != "notes"


def values(record: Any) -> list[tuple[str, Any, str | None]]:
    """(path, value, list path) for every populated scalar, depth first in
    record order. The list path is set for a member of a list of scalars —
    `keywords[2]` in `keywords` — and None for a scalar under a key. A key
    that is not a string (a YAML date or integer) is written `<key>`, which
    no join can read, so it is counted unaddressable rather than removed."""
    out: list[tuple[str, Any, str | None]] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                k = k if isinstance(k, str) else f"<{k}>"
                p = f"{path}.{k}" if path else k
                if isinstance(v, (dict, list)):
                    walk(v, p)
                elif _populated(v):
                    out.append((p, v, None))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                p = f"{path}[{i}]"
                if isinstance(v, (dict, list)):
                    walk(v, p)
                elif _populated(v):
                    out.append((p, v, path))

    walk(record, "")
    return out


def _text(value: Any) -> str:
    return normalise(value if isinstance(value, str) else str(value))


def _member(value: Any) -> str:
    """A list member's identity: its text, a resolver URL read as the CURIE
    it names (#974's normaliser rewrites one to the other at write time)."""
    return _text(_canonical_identifier(value.strip()) if isinstance(value, str) else value)


def _scalars(node: Any):
    if isinstance(node, dict):
        for v in node.values():
            yield from _scalars(v)
    elif isinstance(node, list):
        for v in node:
            yield from _scalars(v)
    elif _populated(node):
        yield node


def _ancestors(path: str) -> list[str]:
    """Proper ancestors of a path, nearest first, the root excluded:
    `a.b[2].c` -> `a.b[2]`, `a.b`, `a`."""
    cuts = [m.start() for m in re.finditer(r"\.|\[", path)]
    return [path[:c] for c in reversed(cuts)]


def _tokens(path: str) -> list[str | int]:
    return [int(t[1:-1]) if t.startswith("[") else t for t in re.findall(r"\w+|\[\d+\]", path)]


class _Presence:
    """Whether a snapshot value is still carried by `target` (a later phase
    output or the final record): through `remap_path` for a scalar under a
    key; for a member of a list of scalars, by its text in the list the
    join locates, counted so a duplicated member removed once is one
    removal. A list of one scalar and that scalar are the same value — the
    runner's multivalued coercion (`receipts._rewritten`)."""

    def __init__(self, original: dict[str, Any], target: dict[str, Any]):
        self.original, self.target = original, target
        self._members: dict[str, set[int]] = {}

    def carried(self, path: str, list_path: str | None) -> bool:
        if list_path is None:
            rm = remap_path(path, self.original, self.target)
            if rm["path"] is None:
                return False
            ok, value = _resolve_value(self.target, rm["path"])
            return ok and _populated(value)
        return int(path[path.rindex("[") + 1:-1]) in self._kept(list_path)

    def _kept(self, list_path: str) -> set[int]:
        if list_path not in self._members:
            kept: set[int] = set()
            ok_o, before = _resolve_value(self.original, list_path)
            rm = remap_path(list_path, self.original, self.target)
            after: Any = None
            if rm["path"] is not None:
                _ok, after = _resolve_value(self.target, rm["path"])
            if isinstance(after, (str, int, float, bool)):
                after = [after]
            if ok_o and isinstance(before, list) and isinstance(after, list):
                pool = [_member(x) for x in after if not isinstance(x, (dict, list)) and _populated(x)]
                for i, x in enumerate(before):
                    if isinstance(x, (dict, list)) or not _populated(x):
                        continue
                    t = _member(x)
                    if t in pool:
                        pool.remove(t)
                        kept.add(i)
            self._members[list_path] = kept
        return self._members[list_path]


def _flattened_into(path: str, value: Any, original: dict[str, Any], final: dict[str, Any]) -> str | None:
    """The final-record path of the nearest surviving ancestor whose text
    carries the value's, normalised and on token boundaries; None when the
    nearest surviving ancestor does not carry it, or none survives short of
    the root. The root never counts: a top-level slot whose words happen to
    occur elsewhere in the record was deleted, not flattened. A boolean is
    never flattened — its text is not the fact it states."""
    if isinstance(value, bool):
        return None
    needle = _text(value)
    if not needle:
        return None
    for anc in _ancestors(path):
        rm = remap_path(anc, original, final)
        if rm["path"] is None:
            continue
        ok, node = _resolve_value(final, rm["path"])
        if not ok or not _populated(node):
            continue
        hay = " ".join(_text(s) for s in _scalars(node))
        return rm["path"] if f" {needle} " in f" {hay} " else None
    return None


# ---------------------------------------------------------------- findings
#: A slot string's separators between paths, at bracket depth 0:
#: "a / b", "a, b", "a and b", "a vs b", "a; b".
_SEPARATOR = re.compile(r"\s+/\s+|\s*[,;]\s*|\s+and\s+|\s+vs\.?\s+")
_DOTTED = re.compile(r"[A-Za-z_]\w*(?:\[[^\]]*\]|\.[A-Za-z_]\w*)*")
_POINTER = re.compile(r"/[^\s]+")


class _Selector(str):
    """A bracket naming an entry rather than indexing it:
    `variables[particulate_matter]`."""


def _bracket(content: str) -> Any:
    c = content.strip()
    if c in ("", "*"):
        return "*"
    if c.isdigit():
        return int(c)
    if re.fullmatch(r"[\d\s.,\-–]+", c):
        picked: set[int] = set()
        for piece in re.split(r"\s*,\s*", c):
            m = re.fullmatch(r"(\d+)\s*(?:\.\.|-|–)\s*(\d+)", piece)
            if m:
                picked.update(range(int(m.group(1)), int(m.group(2)) + 1))
            elif piece.isdigit():
                picked.add(int(piece))
        return frozenset(picked)
    return _Selector(c)


def _dotted_tokens(text: str) -> list[Any]:
    out: list[Any] = []
    for m in re.finditer(r"\[([^\]]*)\]|[A-Za-z_]\w*", text):
        out.append(_bracket(m.group(1)) if m.group(0).startswith("[") else m.group(0))
    return out


def pointer_tokens(pointer: Any) -> list[Any] | None:
    """A JSON Pointer's steps, a digit step as a list index; None for
    anything that is not a non-root pointer (the root covers nothing)."""
    if not isinstance(pointer, str) or not pointer.startswith("/") or pointer == "/":
        return None
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer[1:].split("/")]
    return [int(p) if p.isdigit() else p for p in parts]


def slot_paths(slot: Any, original: dict[str, Any] | None = None) -> list[list[Any]]:
    """The paths a finding's free-text `slot` names. Separators split it
    (`a / b`, `a, b`, `a and b`) outside brackets; each part is read up to
    its first character that is not path grammar, so a parenthetical or a
    trailing phrase is dropped; `[]` and `[*]` are wildcards, `[2..7,11]` a
    set of indexes, `[name]` an entry named so. A bare name that is not a
    top-level key of the snapshot, after a dotted part, is that part's
    sibling (`start_date / end_date`). A part with no leading path — `(whole
    record)`, `[3] (core)` — names nothing and covers nothing."""
    if not isinstance(slot, str):
        return []
    text = slot.replace("`", " ")
    guarded, depth = [], 0
    for ch in text:
        depth += ch == "["
        depth -= ch == "]" and depth > 0
        guarded.append("\x00" if depth and ch == "," else ch)
    top = set(original) if isinstance(original, dict) else set()
    out: list[list[Any]] = []
    previous: list[Any] | None = None
    for part in _SEPARATOR.split("".join(guarded)):
        part = part.replace("\x00", ",").strip()
        if part.startswith("/"):
            m = _POINTER.match(part)
            toks = pointer_tokens(m.group(0)) if m else None
        else:
            m = _DOTTED.match(part)
            toks = _dotted_tokens(m.group(0)) if m else None
        if not toks:
            continue
        if (len(toks) == 1 and isinstance(toks[0], str) and toks[0] not in top
                and previous is not None and len(previous) > 1):
            toks = previous[:-1] + toks
        out.append(toks)
        previous = toks
    return out


def _selects(selector: str, entry: Any) -> bool:
    """Does a bracketed name pick this entry? `[bias_type=selection_bias]`
    compares that key's value; `[particulate_matter]` any scalar value."""
    keyed = re.fullmatch(r"\s*(\w+)\s*[=:]\s*(.+?)\s*", selector)
    if keyed and isinstance(entry, dict) and keyed.group(1) in entry:
        v = entry[keyed.group(1)]
        return isinstance(v, (str, int, float)) and _text(v) == _text(keyed.group(2).strip("'\""))
    want = _text(selector)
    if isinstance(entry, dict):
        return any(_text(v) == want for v in entry.values()
                   if isinstance(v, (str, int, float)) and not isinstance(v, bool))
    return isinstance(entry, str) and _text(entry) == want


def covers(finding_path: list[Any], path: str, original: dict[str, Any]) -> bool:
    """Does a finding's path name `path` or one of its ancestors? Keys must
    agree step for step; at a list index the finding may give the index, a
    wildcard, a set of indexes or an entry's name, or step over it with the
    next key (`creators.affiliations` for `creators[3].affiliations`). The
    empty path — the root — covers nothing."""
    if not finding_path:
        return False
    steps = _tokens(path)
    node: Any = original
    i = j = 0
    while i < len(finding_path):
        if j >= len(steps):
            return False
        want, step = finding_path[i], steps[j]
        if isinstance(step, int):
            if isinstance(want, _Selector):
                if not (isinstance(node, list) and step < len(node) and _selects(want, node[step])):
                    return False
            elif isinstance(want, frozenset):
                if step not in want:
                    return False
            elif isinstance(want, int) and not isinstance(want, bool):
                if want != step:
                    return False
            elif want != "*":
                # a key where the path has an index: the finding stepped over it
                node = node[step] if isinstance(node, list) and step < len(node) else None
                j += 1
                continue
        elif want != step:
            return False
        if isinstance(node, dict):
            node = node.get(step)
        elif isinstance(node, list) and isinstance(step, int) and step < len(node):
            node = node[step]
        else:
            node = None
        i += 1
        j += 1
    return True


def finding_paths(finding: dict[str, Any], original: dict[str, Any]) -> list[tuple[str, list[Any]]]:
    """(via, path) for every path a finding names: its `slot`, each of its
    `review_paths` and its `remove_relationship.path` (JSON Pointers into
    original_full, evidence protocol v1+)."""
    out: list[tuple[str, list[Any]]] = [("slot", p) for p in slot_paths(finding.get("slot"), original)]
    for pointer in finding.get("review_paths") or []:
        toks = pointer_tokens(pointer)
        if toks:
            out.append(("review_paths", toks))
    rule = finding.get("remove_relationship")
    if isinstance(rule, dict):
        toks = pointer_tokens(rule.get("path"))
        if toks:
            out.append(("remove_relationship", toks))
    return out


def _core_only(finding: dict[str, Any]) -> bool:
    return str(finding.get("record") or "").strip().lower() == "core"


def _mentioned(top: str, findings: list[dict[str, Any]]) -> bool:
    pattern = re.compile(rf"(?<![\w.]){re.escape(top)}(?!\w)")
    return any(isinstance(f.get(k), str) and pattern.search(f[k])
               for f in findings for k in ("issue", "slot"))


# --------------------------------------------------------------- receipts
def receipt_paths(receipt: dict[str, Any] | None) -> set[str] | None:
    """Every slot path an `extracted` receipt entry names, or None where
    there is no receipt to read."""
    if not isinstance(receipt, dict) or not isinstance(receipt.get("chunks"), list):
        return None
    return {str(pair.get("slot") or "") for e in receipt["chunks"]
            if isinstance(e, dict) and e.get("status") == "extracted"
            for pair in (e.get("extracted") or []) if isinstance(pair, dict)} - {""}


def _receipted(path: str, list_path: str | None, paths: set[str]) -> bool:
    """A receipt on the value, on an entry above it (#721), or — for a
    member of a list of scalars — on the list, which is the receipts leaf."""
    if path in paths or (list_path is not None and list_path in paths):
        return True
    # An ancestor the path continues from with a key is an entry or an
    # object; one it continues from with an index is a list, which covers
    # only itself (#721).
    return any(anc in paths for anc in _ancestors(path) if path.startswith(anc + "."))


# ---------------------------------------------------------------- classify
def _unchecked(reason: str) -> dict[str, Any]:
    return {"instrument": INSTRUMENT, "checked": False, "reason": reason,
            "snapshot_values": None, "exempt": None, "unaddressable": None,
            "removed": None, "flattened": None, "deleted": None,
            "founded": None, "unfounded": None, "founded_by": None,
            "unfounded_named_by_core_finding": None, "unfounded_mentioned_in_finding_text": None,
            "receipted": None, "phase": None, "audit": None,
            **{f"{cls}_paths{suffix}": ([] if not suffix else None)
               for cls in ("flattened", "founded", "unfounded", "unsorted")
               for suffix in ("", "_truncated")},
            "summary": f"not checked: {reason}", "non_checks": list(NON_CHECKS)}


def _cap(rows: list[dict[str, Any]], key: str, block: dict[str, Any]) -> None:
    block[key] = rows[:PATH_LIMIT]
    block[f"{key}_truncated"] = max(0, len(rows) - PATH_LIMIT) or None


def classify(original: dict[str, Any] | None, final: dict[str, Any],
             audit: dict[str, Any] | None = None, *,
             receipt: dict[str, Any] | None = None,
             intermediates: list[tuple[str, dict[str, Any] | None]] | None = None) -> dict[str, Any]:
    """The block for one run. Pure: snapshot + final record + audit (+ the
    receipt, + the phase outputs in order) -> block.

    `original` None (no phase-1 snapshot) returns every count None. `audit`
    None, or one without a `findings` list, leaves `founded`/`unfounded`
    None while `flattened` and `deleted` are still counted, the deleted
    values listed under `unsorted_paths`: a missing audit is not an audit
    with no findings. `receipt` None leaves `receipted` None.
    `intermediates` is `[(phase name, output or None), ...]` between the
    snapshot and the final record, in run order; without them, or with any
    output None (it could not be read), `phase` is None."""
    if not isinstance(original, dict):
        return _unchecked("no phase-1 snapshot: the removals cannot be read against what phase 1 wrote (#899)")
    final = final if isinstance(final, dict) else {}
    findings = audit.get("findings") if isinstance(audit, dict) else None
    findings = [f for f in findings if isinstance(f, dict)] if isinstance(findings, list) else None
    record_id = original.get("id") if isinstance(original.get("id"), str) else None
    carried = dataset_identifier_forms(original)
    paths_receipted = receipt_paths(receipt)
    named = ([(n, via, fp) for n, f in enumerate(findings) if not _core_only(f)
              for via, fp in finding_paths(f, original)] if findings is not None else None)
    core_named = ([fp for f in findings if _core_only(f) for _via, fp in finding_paths(f, original)]
                  if findings is not None else None)
    # A phase output that could not be read leaves every removal
    # unattributed: across the gap, "the stage after the last one that
    # carried it" would name a later phase for a value an earlier one
    # removed.
    attributed = intermediates is not None and all(isinstance(doc, dict) for _n, doc in intermediates)
    at_final = _Presence(original, final)
    at_stage = [(name, _Presence(original, doc)) for name, doc in (intermediates or [])] if attributed else []

    total = exempted = unaddressable = 0
    rows: dict[str, list[dict[str, Any]]] = {"flattened": [], "founded": [], "unfounded": [], "unsorted": []}
    founded_by = {"slot": 0, "review_paths": 0, "remove_relationship": 0}
    receipted = {"removed": 0, "flattened": 0, "deleted": 0, "founded": 0, "unfounded": 0}
    by_phase: dict[str, int] = {}
    for path, value, list_path in values(original):
        total += 1
        if exempt_value(list_path or path, value, record_id, carried):
            exempted += 1
            continue
        if not _ADDRESSABLE.fullmatch(path):
            unaddressable += 1
            continue
        if at_final.carried(path, list_path):
            continue
        row: dict[str, Any] = {"path": path}
        if attributed:
            # The stage after the last one that still carried the value; the
            # snapshot (index -1) carried it by construction.
            last = max((i for i, (_n, p) in enumerate(at_stage) if p.carried(path, list_path)), default=-1)
            row["phase"] = at_stage[last + 1][0] if last + 1 < len(at_stage) else "write"
            by_phase[row["phase"]] = by_phase.get(row["phase"], 0) + 1
        if paths_receipted is not None:
            row["receipted"] = _receipted(path, list_path, paths_receipted)
            receipted["removed"] += row["receipted"]
        into = _flattened_into(path, value, original, final)
        if into is not None:
            rows["flattened"].append({**row, "into": into})
            receipted["flattened"] += bool(row.get("receipted"))
            continue
        receipted["deleted"] += bool(row.get("receipted"))
        if named is None:
            rows["unsorted"].append(row)
            continue
        hit = next(((n, via) for n, via, fp in named if covers(fp, path, original)), None)
        if hit is not None:
            founded_by[hit[1]] += 1
            rows["founded"].append({**row, "by": hit[1], "finding": hit[0]})
            receipted["founded"] += bool(row.get("receipted"))
            continue
        # Not founded. Two reported annotations, never a class: a finding
        # scoped to the core record alone names the path, or a finding's
        # text names its top-level slot — founded-by-text is not founded.
        if any(covers(fp, path, original) for fp in core_named or []):
            row["named_by_core_finding"] = True
        if _mentioned(str(_tokens(path)[0]), findings or []):
            row["mentioned_in_finding_text"] = True
        rows["unfounded"].append(row)
        receipted["unfounded"] += bool(row.get("receipted"))

    sorted_ = named is not None
    deleted = len(rows["founded"]) + len(rows["unfounded"]) + len(rows["unsorted"])
    block: dict[str, Any] = {
        "instrument": INSTRUMENT, "checked": True, "reason": None,
        "snapshot_values": total, "exempt": exempted, "unaddressable": unaddressable,
        "removed": len(rows["flattened"]) + deleted, "flattened": len(rows["flattened"]),
        "deleted": deleted,
        "founded": len(rows["founded"]) if sorted_ else None,
        "unfounded": len(rows["unfounded"]) if sorted_ else None,
        "founded_by": founded_by if sorted_ else None,
        "unfounded_named_by_core_finding": (sum(1 for r in rows["unfounded"] if r.get("named_by_core_finding"))
                                            if sorted_ else None),
        "unfounded_mentioned_in_finding_text": (sum(1 for r in rows["unfounded"]
                                                    if r.get("mentioned_in_finding_text"))
                                                if sorted_ else None),
        "receipted": ({k: (v if sorted_ or k not in ("founded", "unfounded") else None)
                       for k, v in receipted.items()} if paths_receipted is not None else None),
        "phase": by_phase if attributed else None,
        "audit": ({"findings": len(findings), "core_only": sum(1 for f in findings if _core_only(f))}
                  if findings is not None else None),
    }
    for cls in ("flattened", "founded", "unfounded", "unsorted"):
        _cap(rows[cls], f"{cls}_paths", block)
    block["summary"] = _summary(block)
    block["non_checks"] = list(NON_CHECKS)
    return block


def _summary(block: dict[str, Any]) -> str:
    if not block["checked"]:
        return f"not checked: {block['reason']}"
    head = (f"{block['snapshot_values']} phase-1 values ({block['exempt']} exempt)"
            f" · {block['flattened']} flattened")
    if block["founded"] is None:
        return head + " · no audit to sort the deletions against"
    s = head + f" · {block['founded']} founded · {block['unfounded']} unfounded"
    if block["receipted"] is not None:
        s += (f" · receipted: {block['receipted']['deleted']} deleted, "
              f"{block['receipted']['flattened']} flattened")
    return s


# ----------------------------------------------------------------- on disk
def _phase_output(core_dir: Path, project: str, name: str,
                  record: dict[str, Any] | None) -> tuple[str, Path | None, Any, str | None]:
    """(state, path, parsed, why) for one phase output under intermediate/:
    read under the run's attested identity (`snapshot_store.read_latest`,
    #1409/#1415), else — for a historical run that predates that — the
    newest of its numbered files, the rule `receipts.phase1_snapshot_read`
    applies to the phase-1 snapshot."""
    from data_sheets_schema.snapshot_store import read_latest
    try:
        indexed, found = read_latest(core_dir, project, name, record=record)
        if not indexed:
            stem, suffix = name.rsplit(".", 1)
            inter = core_dir / "intermediate"
            files = sorted(inter.glob(f"{stem}.{suffix}")) + sorted(
                inter.glob(f"{stem}_[0-9]*.{suffix}"), key=lambda p: int(p.stem.rsplit("_", 1)[1]))
            found = (files[-1], files[-1].read_bytes()) if files else None
    except (OSError, ValueError) as exc:
        return "unusable", None, None, str(exc).splitlines()[0] if str(exc) else type(exc).__name__
    if found is None:
        return "absent", None, None, None
    path, raw = found
    try:
        text = raw.decode("utf-8")
        doc = json.loads(text) if name.endswith(".json") else yaml.safe_load(text)
    except (UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
        return "unusable", path, None, f"{type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else ''}"
    if not isinstance(doc, dict):
        return "unusable", path, None, f"the document is a {type(doc).__name__}, not a mapping"
    return "usable", path, doc, None


def repair_rounds(core_dir: Path, project: str, record: dict[str, Any] | None) -> list[int]:
    """The full-record repair rounds a run wrote, from its attested phase
    inventory and the files beside it."""
    names = [str(e.get("phase") or Path(str(e.get("path") or "")).name)
             for e in ((record or {}).get("intermediates") or []) if isinstance(e, dict)]
    names += [p.name for p in (core_dir / "intermediate").glob(f"{project}_repair_full_r*.yaml")]
    pattern = re.compile(rf"{re.escape(project)}_repair_full_r(\d+)(?:_\d+)?\.yaml")
    return sorted({int(m.group(1)) for n in names if (m := pattern.fullmatch(n))})


def for_record(provenance: Path, *, record: dict[str, Any] | None = None) -> dict[str, Any]:
    """The block for one run on disk. Read-only: nothing under the run's
    directories is written, and the provenance record is not changed."""
    from data_sheets_schema.backfill_checks import record_paths
    from data_sheets_schema.report_claims import phase1_snapshot_with_pin_for
    paths = record_paths(provenance)
    project, core_dir = paths["project"], provenance.parent
    if record is None:
        record = yaml.safe_load(provenance.read_text(encoding="utf-8")) or {}
    if not paths["full"].exists():
        return _unchecked(f"no final full record at {paths['full']}")
    final = yaml.safe_load(paths["full"].read_text(encoding="utf-8")) or {}
    original, pin = phase1_snapshot_with_pin_for(paths["core"], record=record)
    if original is None:
        why = (pin or {}).get("reason")
        block = _unchecked(f"the phase-1 snapshot is present but not usable ({why})" if why else
                           "no phase-1 snapshot: the removals cannot be read against what phase 1 "
                           "wrote (#899)")
        block["artifacts"] = {"phase1_snapshot": pin}
        return block
    a_state, a_path, audit, a_why = _phase_output(core_dir, project, f"{project}_audit.json", record)
    stages: list[tuple[str, dict[str, Any] | None]] = []
    phases: list[dict[str, Any]] = []
    for name in ["reconcile_full", *(f"repair_full_r{n}" for n in repair_rounds(core_dir, project, record))]:
        state, path, doc, why = _phase_output(core_dir, project, f"{project}_{name}.yaml", record)
        if state == "absent":
            continue
        stages.append((name, doc))
        phases.append({"phase": name, "state": state, "path": str(path) if path else None,
                       **({"reason": why} if why else {})})
    # The receipt beside the core record: its paths address the phase-1
    # record, which is the snapshot read here (#899).
    receipt_file = core_dir / f"{project}_coverage_receipt.yaml"
    receipt, r_state = None, "absent"
    if receipt_file.exists():
        try:
            receipt = yaml.safe_load(receipt_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            receipt = None
        r_state = "usable" if receipt_paths(receipt) is not None else "unusable"
    block = classify(original, final, audit if a_state == "usable" else None,
                     receipt=receipt, intermediates=stages if stages else None)
    block["artifacts"] = {
        "phase1_snapshot": pin, "final": str(paths["full"]),
        "audit": {"state": a_state, "path": str(a_path) if a_path else None,
                  **({"reason": a_why} if a_why else {})},
        "receipt": {"state": r_state, "path": str(receipt_file) if r_state != "absent" else None},
        "phases": phases,
    }
    return block
