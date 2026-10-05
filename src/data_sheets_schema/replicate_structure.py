"""Structural agreement across generation replicates (#2932).

Three replicates of one bundle, prompt and arm do not produce records of the
same shape: a slot is filled in one replicate and missing from another, and a
list slot carries 1, 2 and 5 entries. Nothing measured either. `runs.compare`
counts record keys, so a key holding `null` or `[]` reads as present and
"absent in every replicate" cannot be told from "never applicable";
`agreement.compare_records` judges the values of slots two replicates share
and has no structural tier; `scripts/arm_comparison.py` reported populated
leaves per replicate and nothing across them.

`compare_structure` is that tier, for top-level slots (below them, see
the end of this docstring). It is pure: records
in, a report out, no file read. Per slot it gives

- **presence** per replicate. A value is empty when it is `None`, `""`, `[]`
  or `{}` — fig12's and fig02's `empty` (#2303), not key presence;
- **state**, on fig12's canonical form (key-sorted YAML, every whitespace run
  inside a string collapsed to one space, list order kept): `identical`,
  `two_agree` (three replicates, two forms equal; `some_agree` for more than
  three), `all_differ`, `intermittent` (present in some replicates, not all)
  or `absent`;
- **entry counts** where every present value is a list: per replicate, their
  spread (max − min) and max/min. A single object or a scalar has no item
  count and is kept out of every count denominator (`counted` is False), so
  a slot holding one `Distribution` object never reads as "one entry";
- **key sets** of the dict entries: each replicate's union of entry keys,
  the union and intersection of those across replicates, and whether they
  agree;
- **alignment** of list entries across each pair of replicates, one to one:
  on the identity `receipts._entry_key` reads (the first `id`, `name`,
  `title`, … string an entry carries, or a string entry's own value — a
  number or boolean entry is keyless), and a
  keyless entry against the keyless entry at its own index —
  `joined_by_position`, the same caveat as #908: position is no evidence of
  identity, so it is counted and never folded into the keyed count.

`dataset_slots` is the slot universe: class `Dataset`'s induced slots in the
merged schema, less `source_caveats` (commentary, not a claim about the
dataset) — fig12's rows. A record key outside it is reported by
`compare_structure` under `outside_universe` and not compared.

`omission_candidates` (#3335, #2932 1(c)) marks an intermittent slot a
receipt-backed omission candidate when a replicate that fills it carries a
verified receipt snippet for it (`verified_by_slot`, the verification
`receipts.check` applies). Both are pure; `record_chunk_texts` is the one
reader, recovering the chunk texts a record's receipt cites.

Below the top level (#3337), `compare_nested` walks the class-ranged slots
every replicate fills, pair by pair: dicts by field, lists by `align`'s
one-to-one join, recursively. Each comparison at a path is counted under its
join basis — `single` (one object each side), `key` or `position`, the
weakest on the way down — so position joins, which dominate (on v7
production, 135 top-level entries join by key against 1,048 by position),
are never read as identity. `entry_omission_candidates` (#3880) applies the
omission-candidate reading one level down, to list entries some replicates
carry and others do not, joined by key only, crediting a verified receipt
path that `resolve_verified` follows into the entry; `receipted_where_empty`
lists the slots a replicate leaves empty and yet receipts, and
`removal_status` reads what the removals block (#2923) says of them.
`nested_omission_candidates` (#3934) applies the same reading below that:
to the fields of objects and the entries of nested lists, wherever a chain
of single-object and keyed-list steps identifies them in every replicate.
"""
from __future__ import annotations

import re
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from data_sheets_schema import receipts as _receipts

FULL_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
EXCLUDED_SLOTS = ("source_caveats",)
PRESENT_STATES = ("identical", "two_agree", "some_agree", "all_differ")
STATES = PRESENT_STATES + ("intermittent", "absent")


def is_empty(value: Any) -> bool:
    """fig02's `empty`: None, "", [] and {} hold nothing. A list of empties
    (`[null]`) is not empty — the model wrote an entry."""
    return value is None or value == "" or value == [] or value == {}


def _norm(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_norm(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    return value


def canonical(value: Any) -> str:
    """fig12's canonical form: key-sorted YAML with whitespace runs collapsed.
    List order counts."""
    return yaml.safe_dump(_norm(value), sort_keys=True, allow_unicode=True, width=10**9)


def dataset_slots(schema_path: Path | str = FULL_SCHEMA) -> dict[str, str]:
    """Slot -> kind for class `Dataset`'s induced slots, less
    `EXCLUDED_SLOTS`, in schema order. Kind: `nested` when the range is a
    schema class (one object or a list of them), `list` when multivalued with
    a type or enum range, else `scalar`. fig12 further splits scalar strings
    into long text by observed length; that is a property of the records,
    not of the slot, and is not needed here."""
    from data_sheets_schema.resources import resource_path
    from data_sheets_schema.schema_view import shared_view
    view = shared_view(resource_path(str(schema_path)))
    out: dict[str, str] = {}
    for slot in view.class_induced_slots("Dataset"):
        name = str(slot.name)
        if name in EXCLUDED_SLOTS:
            continue
        if slot.range and view.get_class(str(slot.range)) is not None:
            out[name] = "nested"
        elif slot.multivalued:
            out[name] = "list"
        else:
            out[name] = "scalar"
    return out


def _entry_keys(value: Any) -> set[str] | None:
    """The union of keys over a value's dict entries (a single dict is its
    own entry); None when it has no dict entry."""
    entries = value if isinstance(value, list) else [value]
    dicts = [e for e in entries if isinstance(e, dict)]
    if not dicts:
        return None
    return set().union(*(set(d) for d in dicts))


def _join(a: list[Any], b: list[Any]) -> list[tuple[int, int, str | None]]:
    """The one-to-one join `align` counts: `(i, j, key)` for entry `a[i]`
    joined with `b[j]`, `key` the identity key's name (`id`, `name`, …,
    `value` for a string entry) or None for a keyless entry joined by its
    index. Keyed joins first, in `a`'s order, each taking the first unjoined
    entry of `b` with the same key; then each keyless entry of `a` takes the
    keyless entry at its own index in `b`, if that is unjoined."""
    from data_sheets_schema.receipts import _entry_key
    keys_b = [_entry_key(e) for e in b]
    used: set[int] = set()
    out: list[tuple[int, int, str | None]] = []
    keyless_a = []
    for i, entry in enumerate(a):
        key = _entry_key(entry)
        if key is None:
            keyless_a.append(i)
            continue
        j = next((j for j, k in enumerate(keys_b) if k == key and j not in used), None)
        if j is not None:
            used.add(j)
            out.append((i, j, key[0]))
    for i in keyless_a:
        # Only a keyless entry of `b` can join by position (`keys_b[i] is None`),
        # and a keyed join only takes keyed entries, so the two passes never
        # compete for an entry of `b`; their order does not matter.
        if i < len(b) and i not in used and keys_b[i] is None:
            used.add(i)
            out.append((i, i, None))
    return out


def align(a: list[Any], b: list[Any]) -> dict[str, Any]:
    """One-to-one alignment of two lists' entries. An entry `receipts._entry_key`
    identifies joins the first unjoined entry of `b` with the same key; a
    keyless entry joins the keyless entry at its own index in `b`, if that is
    unjoined (`joined_by_position`). Everything else is unaligned, counted on
    both sides."""
    pairs = _join(a, b)
    by_key = Counter(k for _i, _j, k in pairs if k is not None)
    by_position = sum(1 for _i, _j, k in pairs if k is None)
    return {"joined_by_key": dict(sorted(by_key.items())), "joined_by_position": by_position,
            "unaligned": len(a) + len(b) - 2 * len(pairs)}


def compare_slot(values: Mapping[str, Any]) -> dict[str, Any]:
    """The structural comparison of one slot's values, replicate -> value."""
    reps = list(values)
    present = {r: not is_empty(values[r]) for r in reps}
    held = [r for r in reps if present[r]]
    n = len(held)
    out: dict[str, Any] = {"present": present, "n_present": n, "n_replicates": len(reps)}
    if n == 0:
        out["state"] = "absent"
    elif n < len(reps):
        out["state"] = "intermittent"
    else:
        k = len({canonical(values[r]) for r in held})
        out["n_distinct"] = k
        out["state"] = ("identical" if k == 1 else "all_differ" if k == n
                        else "two_agree" if n == 3 else "some_agree")

    counted = n > 0 and all(isinstance(values[r], list) for r in held)
    out["counted"] = counted
    out["counts"] = {r: len(values[r]) for r in held} if counted else None
    if counted:
        cs = list(out["counts"].values())
        out["spread"] = max(cs) - min(cs)
        out["max_over_min"] = max(cs) / min(cs)       # an empty list is absent, so min >= 1
        out["counts_differ"] = len(set(cs)) > 1
    else:
        out["spread"] = out["max_over_min"] = out["counts_differ"] = None

    per_rep = {r: _entry_keys(values[r]) for r in held}
    with_keys = [s for s in per_rep.values() if s is not None]
    out["keys"] = ({"per_replicate": {r: sorted(s) for r, s in per_rep.items() if s is not None},
                    "union": sorted(set().union(*with_keys)),
                    "intersection": sorted(set.intersection(*with_keys)),
                    "agree": all(s == with_keys[0] for s in with_keys)}
                   if with_keys else None)

    if counted and n >= 2:
        by_key: Counter[str] = Counter()
        by_position = unaligned = 0
        for ra, rb in combinations(held, 2):
            a = align(values[ra], values[rb])
            by_key.update(a["joined_by_key"])
            by_position += a["joined_by_position"]
            unaligned += a["unaligned"]
        out["alignment"] = {"pairs": n * (n - 1) // 2, "joined_by_key": dict(sorted(by_key.items())),
                            "joined_by_position": by_position, "unaligned": unaligned}
    else:
        out["alignment"] = None
    return out


def compare_structure(records: Mapping[str, Mapping[str, Any]],
                      slots: Mapping[str, str] | Iterable[str],
                      excluded: Iterable[str] = EXCLUDED_SLOTS) -> dict[str, Any]:
    """Compare replicate records (replicate -> top-level record) over `slots`
    (a `dataset_slots` mapping, or bare names). Returns `slots` (name ->
    `compare_slot` report, with `kind` where `slots` gave one),
    `state_counts`, and `outside_universe`: the record keys, holding a value,
    that neither `slots` nor `excluded` names — reported so that a record
    carrying a key the universe omits says so rather than being silently
    narrowed."""
    kinds = dict(slots) if isinstance(slots, Mapping) else {s: None for s in slots}
    report: dict[str, dict[str, Any]] = {}
    for name, kind in kinds.items():
        r = compare_slot({rep: (rec or {}).get(name) for rep, rec in records.items()})
        if kind is not None:
            r["kind"] = kind
        report[name] = r
    skip = set(excluded)
    outside = sorted({k for rec in records.values() for k, v in (rec or {}).items()
                      if k not in kinds and k not in skip and not is_empty(v)})
    counts = Counter(r["state"] for r in report.values())
    return {"replicates": list(records), "slots": report,
            "state_counts": {s: counts.get(s, 0) for s in STATES},
            "outside_universe": outside}


def summarize(result: Mapping[str, Any]) -> dict[str, Any]:
    """The per-group figures the arm comparison prints: slots held by all,
    some and no replicate; the intermittent slots; the nested slots held by
    all, how many of them are lists with an item count, how many of those
    differ in count and reach max/min >= 2; and the alignment totals over
    the counted nested slots."""
    rows = result["slots"]
    sc = result["state_counts"]
    all_nested = [s for s, r in rows.items() if r.get("kind") == "nested" and r["state"] in PRESENT_STATES]
    counted = [s for s in all_nested if rows[s]["counted"]]
    by_key: Counter[str] = Counter()
    by_position = unaligned = 0
    for s in counted:
        a = rows[s]["alignment"]
        if a:
            by_key.update(a["joined_by_key"])
            by_position += a["joined_by_position"]
            unaligned += a["unaligned"]
    return {
        "all": sum(sc[s] for s in PRESENT_STATES), "identical": sc["identical"],
        "some": sc["intermittent"], "none": sc["absent"],
        "intermittent": {s: r["n_present"] for s, r in rows.items() if r["state"] == "intermittent"},
        "nested_in_all": len(all_nested), "nested_counted": len(counted),
        "counts_differ": [s for s in counted if rows[s]["counts_differ"]],
        "ratio_ge_2": [s for s in counted if rows[s]["max_over_min"] >= 2],
        "joined_by_key": sum(by_key.values()), "joined_by_position": by_position,
        "unaligned": unaligned, "outside_universe": list(result["outside_universe"]),
    }


# ------------------------------------------- below the top level (#3337)
#: How a nested comparison's two values were paired, weakest last. `single`:
#: each replicate's slot (or the object above) holds one object, so the pair
#: is the only one there is; `key`: list entries joined by identity
#: (`receipts._entry_key`); `position`: keyless entries joined by index —
#: #908's caveat, no evidence of identity. A path's basis is the weakest of
#: every join on the way down, so a field of a position-joined entry is a
#: `position` comparison whatever joins lie below it.
BASES = ("single", "key", "position")
OUTCOMES = ("identical", "differ", "one_side")


def _weaker(a: str, b: str) -> str:
    return a if BASES.index(a) >= BASES.index(b) else b


def _walk(a: Any, b: Any, path: str, basis: str, acc: dict[str, dict[str, Any]], record: bool) -> None:
    """Compare `a` and `b` at `path` (recorded unless `record` is False, as
    for the top-level slot itself) and descend through dicts by field and
    through lists by `_join`."""
    ea, eb = is_empty(a), is_empty(b)
    if ea and eb:
        return
    if record:
        row = acc.setdefault(path, {"by_basis": {}, "unaligned": 0})
        outcome = ("one_side" if ea or eb else
                   "identical" if canonical(a) == canonical(b) else "differ")
        cell = row["by_basis"].setdefault(basis, {o: 0 for o in OUTCOMES})
        cell[outcome] += 1
    if ea or eb:
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k in EXCLUDED_SLOTS:
                continue                 # commentary, as at the top level
            _walk(a.get(k), b.get(k), f"{path}.{k}", basis, acc, True)
    elif isinstance(a, list) and isinstance(b, list):
        pairs = _join(a, b)
        entries = f"{path}[*]"
        for i, j, key in pairs:
            _walk(a[i], b[j], entries, _weaker(basis, "position" if key is None else "key"), acc, True)
        unaligned = len(a) + len(b) - 2 * len(pairs)
        if unaligned:
            acc.setdefault(entries, {"by_basis": {}, "unaligned": 0})["unaligned"] += unaligned


def compare_nested(records: Mapping[str, Mapping[str, Any]], result: Mapping[str, Any]) -> dict[str, Any]:
    """Structure below the top level (#3337). Pure.

    Over the class-ranged slots `result` (`compare_structure` of the same
    `records`) finds filled in every replicate — a slot without a `kind`
    (bare names) is taken as class-ranged — the values of each pair of
    replicates are walked together: a dict by field (`license.name`), a
    list by the one-to-one join `align` counts (`creators[*]`), and so on
    down. At each path below the top level, every pair of joined values
    where at least one side holds something is one comparison: `identical`
    (fig12's canonical form), `differ`, or `one_side` (held in one
    replicate's entry, empty in the other's — the key-set disagreement the
    top-level table sees only as `keys.agree`). Each comparison is counted
    under its join basis (`BASES`), never pooled across them. At an entries
    path (`…[*]`), `unaligned` counts the entries the join left unpaired,
    on both sides; nothing below an unpaired entry is compared. A field in
    `EXCLUDED_SLOTS` (`source_caveats`) is not compared at any depth, as
    at the top level. A list
    against an object, or either against a scalar, is compared and not
    descended.

    Returns `paths` (path -> `by_basis` {basis -> outcome counts},
    `unaligned`), `slots` (the top-level slots walked) and `pairs` (the
    replicate pairs)."""
    reps = list(records)
    slots = [name for name, r in result["slots"].items()
             if r["state"] in PRESENT_STATES and r.get("kind", "nested") == "nested"]
    acc: dict[str, dict[str, Any]] = {}
    for name in slots:
        for ra, rb in combinations(reps, 2):
            _walk((records[ra] or {}).get(name), (records[rb] or {}).get(name), name, "single", acc, False)
    return {"slots": slots, "pairs": len(reps) * (len(reps) - 1) // 2,
            "paths": {p: acc[p] for p in sorted(acc)}}


def summarize_nested(nested: Mapping[str, Any]) -> dict[str, Any]:
    """Per-basis totals over every path of a `compare_nested` report:
    comparisons, and of those `one_side` and `differ`; entries left
    unaligned; the number of paths. A comparison is one path x one joined
    pair, so an entry and each of its fields are counted at their own
    paths."""
    tot = {b: {o: 0 for o in OUTCOMES} for b in BASES}
    unaligned = 0
    for row in nested["paths"].values():
        unaligned += row["unaligned"]
        for b, cell in row["by_basis"].items():
            for o, n in cell.items():
                tot[b][o] += n
    return {"paths": len(nested["paths"]),
            "compared": {b: sum(tot[b].values()) for b in BASES},
            "one_side": {b: tot[b]["one_side"] for b in BASES},
            "differ": {b: tot[b]["differ"] for b in BASES},
            "unaligned": unaligned}


# ------------------------------------------------ omission candidates (#3335)
#: The keys the receipts instrument reads as the run's own commentary or as
#: set by the runner — `receipts.EXEMPT_LEAVES` (`conforms_to_class`,
#: `conforms_to_schema`, `notes`, `source_caveats`, at any depth; not
#: `conforms_to` or `conforms_to_standard`, which carry facts from the bundle,
#: #4434) and `receipts.EXEMPT_SLOTS` — imported, not
#: copied, so the two instruments cannot disagree about what is a claim
#: (#3893). A receipt path through one of them receipts commentary about the
#: slot, not a claim of it: `human_subject_research.source_caveats` quoting
#: "the bundle names no IRB" is evidence the slot is unsupported. An
#: intermittent slot that is itself one of them is set aside as commentary
#: rather than classified: a snippet for `notes` is not the bundle supporting
#: a claim another replicate omitted.
COMMENTARY_KEYS = tuple(sorted(_receipts.EXEMPT_LEAVES | _receipts.EXEMPT_SLOTS))

CANDIDATE = "candidate"
NOT_CANDIDATE = "not_candidate"
UNMEASURED = "unmeasured"
COMMENTARY = "commentary"


def top_slot(path: Any) -> str | None:
    """The top-level slot a receipt path names (`variables[3].name` ->
    `variables`), or None for an empty path or one through a
    `COMMENTARY_KEYS` key at any depth (`notes`, `source_caveats`, …)."""
    parts = re.findall(r"[A-Za-z_]\w*", str(path or ""))
    if not parts or any(p in COMMENTARY_KEYS for p in parts):
        return None
    return parts[0]


def verified_by_path(receipt: Mapping[str, Any], chunk_texts: Mapping[str, str]) -> dict[str, int]:
    """Receipt path, as the receipt wrote it -> the number of its snippets
    that verify in the chunk they cite, for every path `top_slot` does not
    drop as commentary. Pure. `verified_by_slot` is this summed by top-level
    slot; the verification is the one described there."""
    from data_sheets_schema.receipts import (
        _receipt_entries, claim_receipts, elide_artifact_lines, normalise, normalise_joined, snippet_in,
    )
    entries, _findings = _receipt_entries(dict(receipt))
    claims = claim_receipts({"chunks": entries})
    hays: dict[str, tuple[str, str, str, str]] = {}
    out: Counter[str] = Counter()
    for path, item in claims["slots"].items():
        if top_slot(path) is None:
            continue
        for r in item["receipts"]:
            text, snippet = chunk_texts.get(r["chunk"]), r["snippet"]
            if text is None or not isinstance(snippet, str) or not snippet.strip():
                continue
            if r["chunk"] not in hays:
                hays[r["chunk"]] = (normalise(text), normalise_joined(text),
                                    normalise(elide_artifact_lines(text)),
                                    normalise_joined(elide_artifact_lines(text)))
            if snippet_in(snippet, text, *hays[r["chunk"]])[0]:
                out[path] += 1
    return dict(sorted(out.items()))


def verified_by_slot(receipt: Mapping[str, Any], chunk_texts: Mapping[str, str]) -> dict[str, int]:
    """Top-level slot -> the number of the receipt's snippets for it that
    verify in the chunk they cite. Pure.

    The receipt is inverted by slot with `receipts.claim_receipts` (after
    `receipts._receipt_entries` sets aside the malformed entries `check`
    sets aside), and a snippet counts exactly where `receipts.check` counts
    it as `verified`: a non-empty string that `snippet_in` finds in its own
    chunk, under the #720 floors. A snippet verbatim only in another chunk
    (`adjacent`/`elsewhere`) or across a boundary is not counted: `check`
    does not count it verified either. Summed over every path, commentary
    included, these are `check`'s `snippets.verified`; `top_slot` then
    drops the commentary paths."""
    out: Counter[str] = Counter()
    for path, n in verified_by_path(receipt, chunk_texts).items():
        out[top_slot(path)] += n
    return dict(sorted(out.items()))


def omission_candidates(result: Mapping[str, Any],
                        verified: Mapping[str, Mapping[str, int] | None]) -> dict[str, Any]:
    """Receipt-backed omission candidates among a comparison's intermittent
    slots (#2932 1(c)). Pure.

    `result` is `compare_structure`'s report and `verified` maps each of its
    replicates to `verified_by_slot` of that replicate's receipt, or None
    where the replicate has no receipt that could be read (the procedure
    wrote none, or its bytes could not be recovered) — never an empty
    mapping for that, which would read as "receipted nothing".

    An intermittent slot is a **candidate** when at least one replicate that
    fills it carries a verified snippet for it: the bundle supports the slot
    and the replicates that leave it empty omitted it. It is **not a
    candidate** when every filling replicate has a receipt and none verifies
    a snippet for it, and **unmeasured** when none verifies one and some
    filling replicate has no readable receipt. An intermittent slot in
    `COMMENTARY_KEYS` (`notes`) is **commentary**: counted, never
    classified, and never a candidate a replicate omits (#3893). A candidate
    is evidence that the bundle supports the slot in one replicate's
    reading; it is not a judgement that the omitting replicate was wrong to
    leave it out.

    The group is `measured` when at least one of its replicates has a
    readable receipt, whatever its slots' statuses (#3892): a measured group
    can hold unmeasured slots, and an unmeasured group is exactly one where
    no replicate's receipt could be read, so every slot it has is
    unmeasured or commentary.

    Returns `slots` (name -> status, `filled_by`, `receipted_in`: the
    filling replicates with a verified snippet, `unreceipted`: those with no
    readable receipt), `per_replicate` (replicate -> the candidate slots
    it leaves empty, or None when the group is not measured) and `counts`
    by status, which sum to the group's intermittent slots."""
    rows = result["slots"]
    slots: dict[str, dict[str, Any]] = {}
    for name, r in rows.items():
        if r["state"] != "intermittent":
            continue
        filled = [rep for rep, held in r["present"].items() if held]
        receipted = [rep for rep in filled if verified.get(rep) is not None and verified[rep].get(name, 0) > 0]
        unreceipted = [rep for rep in filled if verified.get(rep) is None]
        if name in COMMENTARY_KEYS:
            status, receipted = COMMENTARY, []
        else:
            status = CANDIDATE if receipted else UNMEASURED if unreceipted else NOT_CANDIDATE
        slots[name] = {"status": status, "filled_by": filled,
                       "receipted_in": receipted, "unreceipted": unreceipted}
    measured = any(verified.get(rep) is not None for rep in result["replicates"])
    per_replicate = {rep: ([n for n, s in slots.items() if s["status"] == CANDIDATE and rep not in s["filled_by"]]
                           if measured else None)
                     for rep in result["replicates"]}
    counts = Counter(s["status"] for s in slots.values())
    return {"slots": slots, "per_replicate": per_replicate, "measured": measured,
            "counts": {k: counts.get(k, 0) for k in (CANDIDATE, NOT_CANDIDATE, UNMEASURED, COMMENTARY)}}


# ------------------------- below the top level, and where empty (#3880)
def resolve_verified(paths: Mapping[str, int], snapshot: Mapping[str, Any] | None,
                     final: Mapping[str, Any], *, unusable: str | None = None) -> dict[str, Any]:
    """Where each verified receipt path (`verified_by_path`, as the receipt
    wrote it) sits in the final record, and on what basis. Pure.

    A receipt is written against the phase-1 record and reconciliation
    reorders, inserts and drops entries after it (#742), so an index in a
    receipt path is followed by identity with `receipts.remap_path` where
    the run left a phase-1 snapshot (#899) — `same`, `by_<key>`,
    `by_overlap`, `same_key_stripped` — and read as written where it left
    none (`no_snapshot`: an index join, the agentic path's). A path the
    snapshot never had (`not_in_snapshot`) or whose entry or leaf is gone
    (`entry_dropped`, `leaf_dropped`, `ambiguous`) resolves nowhere, as in
    `receipts.claim_receipts`. So does a path that does not parse as a slot
    path, or one where an index step finds a list in the snapshot and no list
    in the final record: `remap_path` returns `unresolved` for those, and the
    parse test comes before the snapshot test, so an unparseable path is
    `unresolved` with or without a snapshot, never `no_snapshot`. The rule is
    one-way: where the snapshot holds an object and the final record a list,
    a key step is `leaf_dropped` and an index step `not_in_snapshot`, not
    `unresolved` (#3997). Every one of these resolves nowhere.

    `unusable` is why a snapshot that is present cannot be read
    (`receipts.phase1_snapshot_state`'s `unusable` state: a parse error,
    bytes that are not UTF-8, an empty document, a list or a scalar). Such a
    snapshot is not an absent one: the receipt join refuses it rather than
    falling back to an index join (#1124, #3954), so `paths` is None — no
    readable receipt for an entry — and every snippet is counted under
    `snapshot_unusable`.

    Returns `paths` (resolved path -> snippets, or None as above) and
    `basis` (basis -> snippets, resolved or not)."""
    if unusable is not None:
        total = sum(paths.values())
        return {"paths": None, "basis": {"snapshot_unusable": total} if total else {}}
    from data_sheets_schema.receipts import remap_path
    out: Counter[str] = Counter()
    basis: Counter[str] = Counter()
    for path, n in paths.items():
        rm = remap_path(path, dict(snapshot) if snapshot is not None else None, dict(final))
        basis[rm["basis"]] += n
        if rm["path"] and rm["basis"] != "not_in_snapshot":
            out[rm["path"]] += n
    return {"paths": dict(sorted(out.items())), "basis": dict(sorted(basis.items()))}


def _into(paths: Mapping[str, int], entry: str) -> bool:
    """A verified path on the entry or below it. A receipt on the list
    itself covers only the list (#721), never an entry of it."""
    return any(n > 0 and (p == entry or p.startswith(entry + ".") or p.startswith(entry + "["))
               for p, n in paths.items())


def _keyed(lists: Mapping[str, list[Any]], *,
           objects_only: bool = False) -> tuple[dict[tuple[str, str, int], dict[str, int]], int, int]:
    """The n-way keyed join of one list per replicate: (key name, key value,
    occurrence among that replicate's entries with the key) -> {replicate:
    index}, in first-seen order, then the numbers of keyless entries and of
    values over every replicate. The occurrence makes it the one-to-one
    join `align` counts, so an entry is missing from a replicate exactly
    where that join leaves it unpaired. With `objects_only`, an entry that
    is not a mapping is a value, neither joined nor keyless; otherwise a
    string entry is its own key and the value count is 0."""
    from data_sheets_schema.receipts import _entry_key
    where: dict[tuple[str, str, int], dict[str, int]] = {}
    keyless = values = 0
    for rep, entries in lists.items():
        seen: Counter[tuple[str, str]] = Counter()
        for i, entry in enumerate(entries):
            if objects_only and not isinstance(entry, dict):
                values += 1
                continue
            key = _entry_key(entry)
            if key is None:
                keyless += 1
                continue
            seen[key] += 1
            where.setdefault((key[0], key[1], seen[key]), {})[rep] = i
    return where, keyless, values


def _status(held: Mapping[str, str],
            resolved: Mapping[str, Mapping[str, int] | None]) -> tuple[list[str], list[str], str]:
    """(receipted in, unreceipted, status) of a node the replicates in
    `held` carry, each at its own path in its final record: a candidate
    where a holder has a verified path on that node or below it (`_into`),
    unmeasured where none does and some holder has no readable receipt,
    else not a candidate."""
    receipted = [rep for rep, path in held.items() if resolved.get(rep) is not None and _into(resolved[rep], path)]
    unreceipted = [rep for rep in held if resolved.get(rep) is None]
    return receipted, unreceipted, CANDIDATE if receipted else UNMEASURED if unreceipted else NOT_CANDIDATE


def _key_label(kname: str, kval: str, nth: int) -> str:
    """An identified entry as a row names it: `name=B`, or `name=B (#2)`
    for the second of a replicate's entries carrying that key."""
    return f"{kname}={kval}" + (f" (#{nth})" if nth > 1 else "")


def _held_in_all(result: Mapping[str, Any]) -> list[str]:
    """The slots the entry readings start from: class-ranged (a slot
    without a `kind` is taken as class-ranged), filled in every replicate,
    and not in `COMMENTARY_KEYS`, in `result`'s order."""
    return [name for name, r in result["slots"].items()
            if r["state"] in PRESENT_STATES and r.get("kind", "nested") == "nested" and name not in COMMENTARY_KEYS]


def entry_omission_candidates(records: Mapping[str, Mapping[str, Any]], result: Mapping[str, Any],
                              resolved: Mapping[str, Mapping[str, int] | None]) -> dict[str, Any]:
    """Receipt-backed omission candidates one level down (#3880 (1)): list
    entries some replicates carry and others do not. Pure.

    Over the class-ranged slots `result` finds filled in every replicate
    and a list in each (`counted`; a slot without a `kind` is taken as
    class-ranged), less `COMMENTARY_KEYS`. An entry is identified by
    `receipts._entry_key` and its occurrence among the entries with that key
    — the one-to-one keyed join `align` makes — so an entry is **missing**
    from a replicate exactly where the keyed join leaves it unpaired. A
    keyless entry has no identity to be missing by: a position join is no
    evidence (#908), so keyless entries are counted (`keyless`) and never
    classified. `resolved` maps each replicate to `resolve_verified(...)
    ["paths"]` or None where it has no readable receipt.

    An entry held by some replicates and not all is a **candidate** when a
    replicate holding it has a verified receipt path on that entry or below
    it (`slot[i]`, `slot[i].name`); **not_candidate** when every holder has
    a receipt and none does; **unmeasured** otherwise. Returns `entries`
    (one row per such entry: `slot`, `key`, `held_by`, `receipted_in`,
    `unreceipted`, `status`), `counts` by status, `keyless`, `measured` and
    `per_replicate` (replicate -> the number of candidate entries it lacks,
    or None when no replicate has a readable receipt). Below these entries,
    and in the fields of a slot holding one object, see
    `nested_omission_candidates` (#3934)."""
    reps = list(result["replicates"])
    rows: list[dict[str, Any]] = []
    keyless = 0
    for name in _held_in_all(result):
        if not result["slots"][name]["counted"]:
            continue
        where, n, _values = _keyed({rep: records[rep][name] for rep in reps})
        keyless += n
        for (kname, kval, nth), at in where.items():
            if len(at) == len(reps):
                continue
            receipted, unreceipted, status = _status({rep: f"{name}[{i}]" for rep, i in at.items()}, resolved)
            rows.append({"slot": name, "key": _key_label(kname, kval, nth), "held_by": list(at),
                         "receipted_in": receipted, "unreceipted": unreceipted, "status": status})
    measured = any(resolved.get(rep) is not None for rep in reps)
    per_replicate = {rep: (sum(1 for e in rows if e["status"] == CANDIDATE and rep not in e["held_by"])
                           if measured else None) for rep in reps}
    counts = Counter(e["status"] for e in rows)
    return {"entries": rows, "keyless": keyless, "measured": measured, "per_replicate": per_replicate,
            "counts": {k: counts.get(k, 0) for k in (CANDIDATE, NOT_CANDIDATE, UNMEASURED)}}


#: The rows `nested_omission_candidates` classifies: a field of an object,
#: and an entry of a list below the first level.
NESTED_KINDS = ("field", "entry")


def _below(node: Mapping[str, Any], at: Mapping[str, str], path: str, chain: str, basis: str,
           resolved: Mapping[str, Mapping[str, int] | None], rows: list[dict[str, Any]], *,
           first: bool = False) -> Counter[str]:
    """`nested_omission_candidates`' walk below a node every replicate
    holds, appending its rows to `rows` and returning the `keyless` and
    `values` entries it met: `node` is replicate -> its value at the node,
    `at` replicate -> the node's path in that replicate's final record.
    The `first` level, a top-level list, is joined as
    `entry_omission_candidates` joins it, and its entries that some
    replicates lack and its keyless entries are that function's."""
    n, met = len(node), Counter()
    if all(isinstance(v, dict) for v in node.values()):
        for k in sorted(set().union(*node.values()), key=str):
            if k in EXCLUDED_SLOTS:
                continue
            held = {rep: f"{at[rep]}.{k}" for rep, v in node.items() if not is_empty(v.get(k))}
            if len(held) == n:
                if k not in COMMENTARY_KEYS:
                    met += _below({rep: v[k] for rep, v in node.items()}, held, f"{path}.{k}",
                                  f"{chain}.{k}", basis, resolved, rows)
            elif held:
                rows.append(_nested_row("field", f"{path}.{k}", f"{chain}.{k}", basis, held, resolved,
                                        commentary=k in COMMENTARY_KEYS))
    elif all(isinstance(v, list) for v in node.values()):
        where, keyless, values = _keyed(node, objects_only=not first)
        if not first:
            met.update(keyless=keyless, values=values)
        for (kname, kval, nth), idx in where.items():
            held = {rep: f"{at[rep]}[{i}]" for rep, i in idx.items()}
            step = f"{chain}[{_key_label(kname, kval, nth)}]"
            if len(held) == n:
                met += _below({rep: node[rep][i] for rep, i in idx.items()}, held, f"{path}[*]", step,
                              "key", resolved, rows)
            elif not first:
                rows.append(_nested_row("entry", f"{path}[*]", step, "key", held, resolved))
    return met


def _nested_row(kind: str, path: str, chain: str, basis: str, held: Mapping[str, str],
                resolved: Mapping[str, Mapping[str, int] | None], *, commentary: bool = False) -> dict[str, Any]:
    """One `nested_omission_candidates` row; `held` is holder -> its path."""
    if commentary:
        receipted, unreceipted, status = [], [rep for rep in held if resolved.get(rep) is None], COMMENTARY
    else:
        receipted, unreceipted, status = _status(held, resolved)
    return {"kind": kind, "path": path, "chain": chain, "basis": basis, "held_by": list(held),
            "receipted_in": receipted, "unreceipted": unreceipted, "status": status}


def nested_omission_candidates(records: Mapping[str, Mapping[str, Any]], result: Mapping[str, Any],
                               resolved: Mapping[str, Mapping[str, int] | None]) -> dict[str, Any]:
    """Receipt-backed omission candidates below the entries
    `entry_omission_candidates` reads (#3934): the fields of objects and the
    entries of nested lists that some replicates carry and others do not.
    Pure.

    The walk starts from the class-ranged slots every replicate fills, less
    `COMMENTARY_KEYS` — a slot holding a list in every replicate, whose
    entries `entry_omission_candidates` reads, and one holding one object in
    every replicate, which it does not — and goes down only by steps that
    identify one node in every replicate: a **single-object** step, to a
    field of an object every replicate holds there, and a **keyed-list**
    step, to an entry every replicate holds, identified as
    `entry_omission_candidates` identifies one (`receipts._entry_key` and
    its occurrence): by its key's value as `_entry_key` reads it — stripped,
    and a resolver URL of a declared prefix read as its CURIE — and nothing
    else normalised, so a name in other words, or another key, is another
    entry (#4439). Below the first level only an entry that is an object
    is identified. A keyless object has only its index to be joined by, no
    evidence of identity (#908); a string (or other scalar) entry is a
    **value**, whose only identity is its exact text — most are the prose
    items of a list of values (`ip_restrictions.restrictions`), where one
    replicate's rewording of another's item would read as two items, each
    missing from the other — so both are counted (`keyless`, `values`) and
    never classified, as the items of a top-level list of values are not. A
    top-level list's keyless entries are `entry_omission_candidates`' to
    count. Nothing is read below a keyless entry, below a value that is a
    list in one replicate and not in another (as `compare_nested` does not
    descend there), below a field in `COMMENTARY_KEYS`, or below a node some
    replicate lacks: that node is a row, and below it there is no identity
    across every replicate.

    A row is one step below a node every replicate holds: a **field** some
    replicates fill (`is_empty`) and others do not — `EXCLUDED_SLOTS`
    excepted, at any depth, as in `compare_nested` — or, below the first
    level, an **entry** some replicates' lists carry and others' do not. A
    field in `COMMENTARY_KEYS` (`conforms_to_class`, `conforms_to_schema`,
    `notes`; `source_caveats` is excepted above) is **commentary**:
    counted, never classified, never a candidate a replicate omits (#3893);
    `conforms_to` and `conforms_to_standard`, which the receipts instrument
    does not exempt, are classified like any other field (#4434). Any other
    row is a **candidate** when a replicate holding it has a verified
    receipt path on the node or below it, at the node's own path in that
    replicate — `resolve_verified`'s path, followed into the final record by
    identity where the run left a phase-1 snapshot and read as written (an
    index join, the agentic path's) where it left none (#4438) — so a
    receipt credits a node only through the same chain of entries in its
    own replicate: a receipt at the path where another holder has the node
    and its own replicate has something else credits nothing (#4435). One on
    the object or entry holding the node attests that object or entry, not
    the field or entry another replicate lacks; one on a list covers only
    the list (#721). It is **not_candidate** when every holder has a
    readable receipt and none does, **unmeasured** otherwise.

    Returns `rows` (`kind`: `field` or `entry`; `path`, as `compare_nested`
    names it, `[*]` for each list step; `chain`, the same path naming each
    entry by its key (`creators[name=Ada].affiliations[name=MIT]`);
    `basis`, as in `compare_nested`: `single` when every step to the row is
    a single-object step, else `key`; `held_by`, `receipted_in`,
    `unreceipted`, `status`), `counts` (kind -> status -> rows), `keyless`
    and `values` (entries of the nested lists read, over every replicate),
    `measured` and `per_replicate` (replicate -> kind -> the candidate rows
    it lacks, or None when no replicate has a readable receipt). Every
    row's parent is held by every replicate, so a replicate missing from
    `held_by` holds the parent and lacks that field or entry."""
    reps = list(result["replicates"])
    rows: list[dict[str, Any]] = []
    met: Counter[str] = Counter()
    for name in _held_in_all(result):
        met += _below({rep: records[rep][name] for rep in reps}, {rep: name for rep in reps}, name, name,
                      "single", resolved, rows, first=True)
    measured = any(resolved.get(rep) is not None for rep in reps)
    per_replicate = {rep: ({kind: sum(1 for e in rows if e["kind"] == kind and e["status"] == CANDIDATE
                                      and rep not in e["held_by"]) for kind in NESTED_KINDS}
                           if measured else None) for rep in reps}
    statuses = (CANDIDATE, NOT_CANDIDATE, UNMEASURED, COMMENTARY)
    counts = Counter((e["kind"], e["status"]) for e in rows)
    return {"rows": rows, "keyless": met["keyless"], "values": met["values"], "measured": measured,
            "per_replicate": per_replicate,
            "counts": {kind: {s: counts.get((kind, s), 0) for s in statuses} for kind in NESTED_KINDS}}


def receipted_where_empty(result: Mapping[str, Any],
                          verified: Mapping[str, Mapping[str, int] | None]) -> dict[str, list[str]]:
    """Slot -> the replicates that leave it empty and yet carry a verified
    receipt snippet for it (#3880 (2)), over the slots `result` compares
    that some replicate leaves empty (intermittent or absent), less
    `COMMENTARY_KEYS`. Pure. `verified` is `verified_by_slot` per replicate,
    None where there is no readable receipt. Such a value was receipted
    against the phase-1 record and is not in the final one — removed by
    reconcile or repair, or receipted at a path phase 1 never wrote;
    `removal_status` reads which from the removals block (#2923)."""
    out: dict[str, list[str]] = {}
    for name, r in result["slots"].items():
        if r["state"] in PRESENT_STATES or name in COMMENTARY_KEYS:
            continue
        reps = [rep for rep, held in r["present"].items()
                if not held and verified.get(rep) is not None and verified[rep].get(name, 0) > 0]
        if reps:
            out[name] = reps
    return out


#: The removals block's capped row lists (`removals._cap`), by what they say.
REMOVAL_ROWS = (("flattened_paths", "flattened"), ("founded_paths", "deleted"),
                ("unfounded_paths", "deleted"), ("unsorted_paths", "deleted"))


def removal_status(block: Mapping[str, Any] | None, slot: str) -> str:
    """What a record's removals block (`removals.for_record`, #2923) says of
    `slot`: `deleted` or `flattened` where it lists a removed phase-1 value
    at the slot or below it (`deleted` wins), `no removal row` where the
    block was checked and lists none, `rows truncated` where it lists none
    but a row list was capped, and `removals unchecked` where the block
    could not be computed (no phase-1 snapshot, #899). Pure."""
    if not block or not block.get("checked"):
        return "removals unchecked"
    found = {what for key, what in REMOVAL_ROWS for row in (block.get(key) or [])
             if isinstance(row, dict) and _under(str(row.get("path") or ""), slot)}
    if found:
        return "deleted" if "deleted" in found else "flattened"
    if any(block.get(f"{key}_truncated") for key, _w in REMOVAL_ROWS):
        return "rows truncated"
    return "no removal row"


def _under(path: str, slot: str) -> bool:
    return path == slot or path.startswith(slot + ".") or path.startswith(slot + "[")


_TEXTS_CACHE: dict[tuple, tuple[dict[str, str] | None, str]] = {}


def record_chunk_texts(inputs: Mapping[str, Any], root: Path | str = ".") -> tuple[dict[str, str] | None, str]:
    """(chunk id -> text, basis) for the bundle a provenance record's
    `inputs` says it read, or (None, why not). Reads files and asks git.

    The bytes are the bundle on disk where they hash to the record's
    `bundle_md5`/`bundle_sha256`, else the committed version of
    `bundle_path` whose every recorded hash matches
    (`provenance.committed_bytes_for`, #1140). They are chunked in memory
    under the record's own `inputs.chunks.rule`, and refused where that
    does not reproduce the recorded `chunk_count` or manifest sha256, since
    chunk ids are positional. This is `receipts.block_for`'s recovery with
    the on-disk manifest left out: a manifest that is the record's is the
    one the recorded rule reproduces byte for byte. Memoised per inputs."""
    import hashlib

    from data_sheets_schema.chunking import chunk_texts, dump_manifest, manifest_from_bytes
    from data_sheets_schema.provenance import GitUnavailable, committed_bytes_for
    chunks = inputs.get("chunks") or {}
    md5, sha = inputs.get("bundle_md5"), inputs.get("bundle_sha256")
    path, rule = inputs.get("bundle_path"), chunks.get("rule")
    key = (str(Path(root).resolve()), path, md5, sha, repr(chunks))
    if key in _TEXTS_CACHE:
        return _TEXTS_CACHE[key]
    if not path or not (md5 or sha):
        out: tuple[dict[str, str] | None, str] = (None, "the record names no bundle path and hash")
    elif not isinstance(rule, dict):
        out = (None, "the record carries no chunking rule")
    else:
        raw, basis = None, ""
        disk = Path(root) / path
        if disk.is_file():
            b = disk.read_bytes()
            if (not md5 or hashlib.md5(b).hexdigest() == md5) and (not sha or hashlib.sha256(b).hexdigest() == sha):
                raw, basis = b, "bundle on disk"
        if raw is None:
            try:
                got = committed_bytes_for(path, md5=md5, sha256=sha)
            except GitUnavailable as exc:
                got, basis = None, f"git could not supply the version the record hashed: {exc}"
            if got is not None:
                raw, basis = got[0], f"git blob {got[1]['commit'][:12]}"
            elif not basis:
                basis = "no committed version of the bundle hashes to the record's"
        if raw is None:
            out = (None, basis)
        else:
            try:
                built = manifest_from_bytes(raw, chunks.get("bundle_name") or Path(path).name, rule)
            except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
                built, basis = None, f"the recorded rule cannot chunk the bytes ({exc})"
            if built is not None and chunks.get("chunk_count") is not None \
                    and built.get("chunk_count") != chunks["chunk_count"]:
                built, basis = None, "the recorded rule does not reproduce the recorded chunk count"
            if built is not None and chunks.get("sha256") and \
                    hashlib.sha256(dump_manifest(built).encode("utf-8")).hexdigest() != chunks["sha256"]:
                built, basis = None, "the recorded rule does not reproduce the recorded manifest sha256"
            out = ((dict(zip([c["id"] for c in built["chunks"]],
                             chunk_texts(raw.decode("utf-8"), built["chunks"]))), basis)
                   if built is not None else (None, basis))
    _TEXTS_CACHE[key] = out
    return out
