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

`omission_candidates` (#3335, #2932 1(c)) marks an intermittent slot a
receipt-backed omission candidate when a replicate that fills it carries a
verified receipt snippet for it (`verified_by_slot`, the verification
`receipts.check` applies). Both are pure; `record_chunk_texts` is the one
reader, recovering the chunk texts a record's receipt cites.
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


# ------------------------------------------------ omission candidates (#3335)
#: The keys the receipts instrument reads as the run's own commentary or as
#: set by the runner — `receipts.EXEMPT_LEAVES` (`notes`, `source_caveats`,
#: `conforms_to_*`, at any depth) and `receipts.EXEMPT_SLOTS` — imported, not
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
    from data_sheets_schema.receipts import (
        _receipt_entries, claim_receipts, elide_artifact_lines, normalise, normalise_joined, snippet_in,
    )
    entries, _findings = _receipt_entries(dict(receipt))
    claims = claim_receipts({"chunks": entries})
    hays: dict[str, tuple[str, str, str, str]] = {}
    out: Counter[str] = Counter()
    for path, item in claims["slots"].items():
        slot = top_slot(path)
        if slot is None:
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
                out[slot] += 1
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
