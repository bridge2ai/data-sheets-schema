"""Structural agreement across generation replicates (#2932).

Three replicates of one bundle, prompt and arm do not produce records of the
same shape: a slot is filled in one replicate and missing from another, and a
list slot carries 1, 2 and 5 entries. Nothing measured either. `runs.compare`
counts record keys, so a key holding `null` or `[]` reads as present and
"absent in every replicate" cannot be told from "never applicable";
`agreement.compare_records` judges the values of slots two replicates share
and has no structural tier; `scripts/arm_comparison.py` reported populated
leaves per replicate and nothing across them.

`compare_structure` is that tier, for top-level slots. It is pure: records
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
"""
from __future__ import annotations

import re
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

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


def align(a: list[Any], b: list[Any]) -> dict[str, Any]:
    """One-to-one alignment of two lists' entries. An entry `receipts._entry_key`
    identifies joins the first unjoined entry of `b` with the same key; a
    keyless entry joins the keyless entry at its own index in `b`, if that is
    unjoined (`joined_by_position`). Everything else is unaligned, counted on
    both sides."""
    from data_sheets_schema.receipts import _entry_key
    keys_b = [_entry_key(e) for e in b]
    used: set[int] = set()
    by_key: Counter[str] = Counter()
    by_position = 0
    keyless_a = []
    for i, entry in enumerate(a):
        key = _entry_key(entry)
        if key is None:
            keyless_a.append(i)
            continue
        j = next((j for j, k in enumerate(keys_b) if k == key and j not in used), None)
        if j is not None:
            used.add(j)
            by_key[key[0]] += 1
    for i in keyless_a:
        # Only a keyless entry of `b` can join by position (`keys_b[i] is None`),
        # and a keyed join only takes keyed entries, so the two passes never
        # compete for an entry of `b`; their order does not matter.
        if i < len(b) and i not in used and keys_b[i] is None:
            used.add(i)
            by_position += 1
    joined = sum(by_key.values()) + by_position
    return {"joined_by_key": dict(sorted(by_key.items())), "joined_by_position": by_position,
            "unaligned": len(a) + len(b) - 2 * joined}


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
