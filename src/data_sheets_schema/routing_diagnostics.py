"""Slot-meaning diagnostics: a value whose meaning belongs to another slot (#2931).

A source can label a passage with its own section heading — a Dataverse page's
`Completeness`, which the publisher's crate also carries as
`rai:dataCollectionMissingData` — and generation can still route it to a slot
whose meaning is wrong. The case that found this: CM4AI's "Some datasets are
under temporary pre-publication embargo" sits under
`confidential_elements[].confidentiality_details`, with
`confidential_elements_present: true`, in 5 of the 9 CM4AI full records the
issue parsed — v6 agentic 2026-08-28, v7 API 2026-09-01 and v8 API
2026-09-04g, reps 1-3 of each — namely v6 rep2 and rep3, v7 rep2, and v8 rep1
and rep2. An embargo is a statement about *when* data are released, not that
the data are confidential, so the record asserts confidential elements on the
strength of a release date. The fact itself is supported and kept elsewhere
(`known_limitations` in 8 of those 9); the defect is the claim the slot makes.

Those nine are a selection, not the corpus. On 2026-09-28 the `*d4d*.yaml`
files committed under `data/d4d_concatenated` include 73 CM4AI full records
and 63 cores (every core named `CM4AI_d4d_core.yaml`). Of the full records,
71 are named `CM4AI_d4d.yaml`; the other two are `gpt5/CM4AI_d4d_alldocs.yaml`
and `gpt5/CM4AI_d4d_fixed.yaml`, which the loader cannot read, so the scan
checks 72 full records and all 63 cores (#3204). It flags 37 of those full
records and 35 of those cores, 13 of each with an entry asserting
`confidential_elements_present: true`, and no record of another project
there. Those counts are of that directory only: archived
copies under `data/ATTIC`, and CM4AI records elsewhere in the repository, are
not in them, and the scan flags some of the archived ones too.

`slot_meaning_mismatch` reports such values. It is a **slot-meaning** finding,
not an unsupported claim: the text may be quoted exactly from the source.

## Scope: two slots, on purpose

Only `confidential_elements` and `sensitive_elements`, at any depth (a nested
`resources[*].confidential_elements` answers the same question). The same
embargo or release text is correct in `known_limitations`,
`distribution_dates`, access and distribution slots, so a lexicon run over the
whole record would flag correct routing. Widening the scope is a new instrument
version, not an edit.

## What the lexicon catches, and what it deliberately does not

Three kinds, each a narrow phrase family about release *timing*:

- `embargo` — embargo, embargoed.
- `release_timing` — pre-publication, until/upon/after publication, not yet
  released or published, will be released, scheduled for release, release date.
- `availability_timing` — not yet available, will be made available, available
  upon publication, coming soon.

Access-control language is **not** matched: "withheld from the public
release", "controlled access", "available only under a data use agreement",
"cannot be released". Withholding sensitive variables is exactly what these
slots describe — the full schema's own `confidential_elements` description says
"what is confidential and why it cannot be released" — and the committed
AI-READI, CHORUS and VOICE records use those phrases there correctly. A bare
"release" is not matched either: "the release records Human Subjects: No" is
a correct sensitivity answer.

## What is read

Every string leaf under each slot entry, except `id` (an identifier, not prose;
a minted `#confidential-embargoed-…` fragment restates the entry it names) and
`source_caveats` (the schema defines it as commentary on the evidence, "not
dataset content"). `notes` is read: the schema defines it as residual content
of the object. Each finding carries the entry's own `<slot>_present` value, so
a reader sees whether the misrouted text is also asserting the elements exist.

A record is read as `yaml.safe_load` reads it, which keeps the last of a
duplicated mapping key (#1029). The values before the last are never scanned.
`unread_duplicate_keys` names a duplicate whenever one of those dropped values
held something the scan reads: the duplicate is a scoped slot, or a key inside
one that is neither a skipped key nor under one, or it is an ancestor — a
second `resources` block, say — whose dropped copy holds a scoped slot at any
depth. A mapping is judged at every place the scan reaches it, through an
alias or a merge key as well as where it is written, so a duplicate inside a
mapping anchored elsewhere and aliased under a scoped slot is named there
(#3063). `check_text` then reports the record as not checked rather than
clean. A duplicated ancestor whose dropped copies hold no scoped slot hides
nothing from this scan and is not named. Neither the findings the dropped
values would have produced nor the kept values' own are reported: the record
is not checked, not partly checked.

A key that a merge key brings in and an explicit key of the same mapping
overrides is YAML's override rule, not a key written twice. The #1029 gate
does not count it, and it is not named here. The overridden value is dropped
whole and never scanned, so a key repeated *inside* it hides nothing and is
not named either; the same holds for a key an earlier mapping in a
`<<: [...]` list shadows, since the loader keeps the first there (#3203). A
merged mapping is judged only for the keys the loader takes from it.

A record the loader cannot read at all — a YAML syntax error, an impossible
unquoted date such as `2026-02-30`, which PyYAML raises as a bare
`ValueError`, or nesting past the interpreter's recursion limit — is likewise
not checked. `check_text` catches whatever the loader raises, so one such
record never stops the others in a run from being reported. The command
`d4d evaluate slot-meaning` reads each named file itself and reports one it
cannot read as text in the same way: a missing path, a directory, a file
without read permission or one that is not UTF-8 is not checked, and the
other files named in the call are still reported (#3144).

## What this is not

Non-gating and read-only. Nothing here writes a record, a provenance block or
a canary row; the published records are evidence and are never rewritten, and
any remediation goes through `d4d review disposition` on the owner's call.
Routing guidance for generation (the mapping-derived RAI → slot table, the
label crosswalk) and a Phase 3 audit clause are later, pinned changes.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterator

import yaml

# The #1029 gate's key identity (the constructed key, as the loader compares
# it), so this module and the gate agree on what a duplicate is.
from data_sheets_schema.duplicate_keys import _key_identity

INSTRUMENT_NAME = "routing_diagnostics"
#: Bump on any change to SCOPED_SLOTS, SKIPPED_KEYS or LEXICON, or to how the
#: lexicon is compiled. LEXICON_SHA256 covers all four; it does not cover the
#: traversal code, whose changes are a bump by convention only. The test keeps
#: one LEXICON_SHA256 per released version and fails until the current
#: version's digest is pinned. It cannot tell a new version's pin from an old
#: version's pin rewritten in place: that edit passes the test and shows only
#: in the diff of the pin table.
INSTRUMENT_VERSION = 1
INSTRUMENT = f"{INSTRUMENT_NAME} v{INSTRUMENT_VERSION} (#2931)"

#: The slots whose meaning an embargo or release date contradicts. Findings
#: come in record order, not grouped by slot; this order is what a report
#: names as its scope.
SCOPED_SLOTS = ("confidential_elements", "sensitive_elements")

#: Leaf keys never read, at any depth under a scoped slot (see module docstring).
SKIPPED_KEYS = frozenset({"id", "source_caveats"})

EMBARGO = "embargo"
RELEASE_TIMING = "release_timing"
AVAILABILITY_TIMING = "availability_timing"

#: kind -> alternatives, matched case-insensitively on word boundaries.
LEXICON: dict[str, tuple[str, ...]] = {
    EMBARGO: (
        r"embargo(?:ed|es|s)?",
    ),
    RELEASE_TIMING: (
        r"pre[-\s]?publication",
        r"(?:until|upon|after|following|pending)\s+(?:the\s+|its\s+)?publication",
        r"not\s+yet\s+(?:been\s+)?(?:publicly\s+)?(?:released|published)",
        r"will\s+be\s+(?:publicly\s+)?released",
        r"(?:scheduled|planned)\s+for\s+(?:public\s+)?release",
        r"release\s+date",
    ),
    AVAILABILITY_TIMING: (
        r"not\s+yet\s+(?:publicly\s+|openly\s+)?available",
        r"will\s+(?:later\s+|eventually\s+)?be\s+made\s+(?:publicly\s+|openly\s+)?available",
        r"(?:available|accessible)\s+(?:upon|after|following)\s+publication",
        r"coming\s+soon",
    ),
}

_PATTERNS = {kind: re.compile(r"\b(?:" + "|".join(alternatives) + r")\b", re.IGNORECASE)
             for kind, alternatives in LEXICON.items()}


def _digest(scoped_slots: tuple[str, ...], skipped_keys: frozenset[str],
            patterns: dict[str, re.Pattern[str]]) -> str:
    """What the instrument reads, as bytes: scope, skipped keys and each kind's
    compiled pattern with its flags, so the word-boundary wrapper and the case
    rule are covered as well as the alternatives."""
    compiled = sorted((kind, pattern.pattern, pattern.flags) for kind, pattern in patterns.items())
    return hashlib.sha256(repr((tuple(scoped_slots), sorted(skipped_keys), compiled))
                          .encode("utf-8")).hexdigest()


LEXICON_SHA256 = _digest(SCOPED_SLOTS, SKIPPED_KEYS, _PATTERNS)


@dataclass(frozen=True)
class Mismatch:
    """One string leaf under a scoped slot whose text is about release timing."""
    slot: str
    path: str
    kinds: tuple[str, ...]
    terms: tuple[str, ...]
    #: The entry's own `<slot>_present`; None where the entry carries none or
    #: the slot holds bare strings.
    present: bool | None


def _leaves(node: Any, path: str) -> Iterator[tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in SKIPPED_KEYS:
                continue
            yield from _leaves(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _leaves(value, f"{path}[{index}]")
    elif isinstance(node, str):
        yield path, node


def _entries(slot: str, value: Any, path: str) -> Iterator[tuple[str, Any, bool | None]]:
    """Each entry under a slot with its path and its `<slot>_present` flag. A
    single mapping or a bare string is read as one entry: a record that breaks
    the declared list shape still says what it says."""
    items = list(enumerate(value)) if isinstance(value, list) else [(None, value)]
    for index, entry in items:
        entry_path = path if index is None else f"{path}[{index}]"
        present = entry.get(f"{slot}_present") if isinstance(entry, dict) else None
        yield entry_path, entry, present if isinstance(present, bool) else None


def _match(text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The kinds a text matches, and each distinct term as first written."""
    kinds, terms = [], {}
    for kind, pattern in _PATTERNS.items():
        found = [m.group(0) for m in pattern.finditer(text)]
        if found:
            kinds.append(kind)
            for term in found:
                terms.setdefault(" ".join(term.lower().split()), term)
    return tuple(kinds), tuple(terms.values())


def _scan(node: Any, path: str) -> Iterator[Mismatch]:
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            if key in SCOPED_SLOTS:
                for entry_path, entry, present in _entries(key, value, child):
                    for leaf_path, text in _leaves(entry, entry_path):
                        kinds, terms = _match(text)
                        if kinds:
                            yield Mismatch(key, leaf_path, kinds, terms, present)
            else:
                yield from _scan(value, child)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _scan(value, f"{path}[{index}]")


def slot_meaning_mismatch(record: dict[str, Any]) -> list[Mismatch]:
    """Every string leaf under `confidential_elements` or `sensitive_elements`,
    at any depth, whose text is about an embargo, release timing or
    availability timing — in record order, one finding per leaf.

    Raises TypeError for a record that is not a mapping: an empty list would
    read as a clean record the diagnostic never looked at.
    """
    if not isinstance(record, dict):
        raise TypeError(f"a record is a mapping, not {type(record).__name__}")
    return list(_scan(record, ""))


#: Where the scan stands at a node: outside every scoped slot, walking through
#: to find one, or inside one, reading every leaf but a skipped key's. A node
#: under a skipped key inside a scoped slot is never read and is not walked.
_OUTSIDE, _INSIDE = "outside", "inside"


def _constructed(identity: tuple[str, Any]) -> Any:
    """The key the loader builds from a `_key_identity`, or None where it
    builds none this module could compare with a slot name."""
    return identity[1] if identity[0] == "value" else None


def _holds_a_scoped_slot(node: Any) -> bool:
    """Whether `node`, walked as `_scan` walks a record, reaches a scoped slot:
    a mapping key naming one at any depth, through any key and through
    aliases and merge keys. Iterative, so depth is no limit."""
    stack, seen = [node], set()
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, yaml.MappingNode):
            for key_node, value_node in current.value:
                if isinstance(key_node, yaml.ScalarNode) and key_node.value in SCOPED_SLOTS:
                    return True
                stack.append(value_node)
        elif isinstance(current, yaml.SequenceNode):
            stack.extend(current.value)
    return False


def _hides_something(where: str, key: Any, dropped: list[Any]) -> bool:
    """Whether a key written more than once, in a mapping the scan reaches
    `where`, dropped a value the scan would have read. Inside a scoped slot
    every key but a skipped one is read. Outside, a scoped slot is read, and
    so is any value that holds one at any depth: an ancestor such as a
    second `resources` block (#2980, #3005)."""
    if where == _INSIDE:
        return key not in SKIPPED_KEYS
    return key in SCOPED_SLOTS or any(_holds_a_scoped_slot(value) for value in dropped)


def _is_merge(key_node: Any) -> bool:
    return (getattr(key_node, "value", None) == "<<"
            and getattr(key_node, "tag", "") == "tag:yaml.org,2002:merge")


def _merge_sources(node: yaml.MappingNode, path: str,
                   active: frozenset[int]) -> list[tuple[yaml.MappingNode, str]]:
    """The mappings whose pairs the loader reads as `node`'s, each with the
    path it is named at, in the order PyYAML's `flatten_mapping` lays their
    pairs out: every `<<` in turn — a merged mapping's own merges before its
    pairs, and a list of merges last to first, so the first wins — then
    `node` itself. A merge cycle, which the loader cannot construct, is cut.
    A mapping reached more than once — merged twice, or through two merges
    of a diamond — is listed once, at its last place: the loader lays its
    pairs out at each place, but they are the same key nodes with the same
    values, so the repeat drops nothing, and its last place is the one whose
    pairs win against the mappings between (#3226)."""
    if id(node) in active:
        return []
    active = active | {id(node)}
    sources: list[tuple[yaml.MappingNode, str]] = []
    base = f"{path}.<<" if path else "<<"
    for key_node, value_node in node.value:
        if not _is_merge(key_node):
            continue
        if isinstance(value_node, yaml.MappingNode):
            sources.extend(_merge_sources(value_node, base, active))
        elif isinstance(value_node, yaml.SequenceNode):
            for index, item in reversed(list(enumerate(value_node.value))):
                if isinstance(item, yaml.MappingNode):
                    sources.extend(_merge_sources(item, f"{base}[{index}]", active))
    sources.append((node, path))
    last = {id(source): index for index, (source, _) in enumerate(sources)}
    return [entry for index, entry in enumerate(sources) if last[id(entry[0])] == index]


def unread_duplicate_keys(text: str) -> list[dict[str, Any]]:
    """Duplicated mapping keys in a record's text one of whose dropped values
    held something the scan reads: a scoped slot written twice, a key
    repeated inside one that is neither a skipped key nor under one, or an
    ancestor — two `resources` blocks, say — whose earlier copy holds a
    scoped slot at any depth. `safe_load` keeps the last value (#1029), so a
    record carrying one of these is not a clean record whatever its last
    values say.

    The composed node tree is walked as `_scan` walks the loaded record, so a
    mapping is judged at every place the scan reaches it, through an alias
    or a merge key as well as where it is written: a duplicate inside a
    mapping anchored outside the scoped slots and aliased under one is named
    under the slot (#3063). A merged mapping is judged only for the keys
    the loader takes from it: a key an explicit key of the mapping
    overrides, or an earlier mapping in a merge list shadows, is dropped
    whole, so a duplicate inside that dropped value hides nothing and is
    neither named nor walked (#3203). Each duplicate is named once, at the first such
    place in document order, with the lines its key is written on; the list
    is in line order. Keys are compared by the #1029 gate's identity, and
    merge keys are not duplicates, as there. A text the composer rejects
    yields nothing: `safe_load` rejects it too, and the record is not
    checked on that."""
    try:
        loader = yaml.SafeLoader(text)
    except (yaml.YAMLError, RecursionError):
        return []
    named: dict[tuple[int, Any], dict[str, Any]] = {}
    try:
        root = loader.get_single_node()
        stack = [(root, "", _OUTSIDE)] if root is not None else []
        # A node is walked at most once outside the scoped slots and once
        # inside one, so a cyclic or widely shared graph neither recurses
        # forever nor is walked once per alias, as in the #1029 gate (#1032).
        walked: set[tuple[int, str]] = set()
        while stack:
            node, path, where = stack.pop()
            if (id(node), where) in walked:
                continue
            walked.add((id(node), where))
            if isinstance(node, yaml.SequenceNode):
                stack.extend((item, f"{path}[{i}]", where) for i, item in reversed(list(enumerate(node.value))))
                continue
            if not isinstance(node, yaml.MappingNode):
                continue
            # The pairs the loader reads here, in the order it reads them: each
            # merged mapping's (its own merges first), then this mapping's own.
            # A key is kept from the last pair that writes it, so a merged key
            # an explicit key overrides, or an earlier mapping in a merge list
            # shadows, is dropped whole and never scanned (#3203).
            pairs = []
            for source, label_path in _merge_sources(node, path, frozenset()):
                for key_node, value_node in source.value:
                    if _is_merge(key_node):
                        continue
                    pairs.append((source, label_path, _key_identity(loader, key_node), key_node, value_node))
            kept = {identity: id(source) for source, _, identity, _, _ in pairs}
            groups: dict[tuple[int, Any], tuple[str, str, list[tuple[int, Any]]]] = {}
            children = []
            for source, label_path, identity, key_node, value_node in pairs:
                if kept[identity] != id(source):
                    continue
                text_key = getattr(key_node, "value", None)
                label = text_key if isinstance(text_key, str) else str(text_key)
                groups.setdefault((id(source), identity), (label_path, label, []))[2].append(
                    (key_node.start_mark.line + 1, value_node))
                key = _constructed(identity)
                child = f"{label_path}.{label}" if label_path else label
                if where == _OUTSIDE:
                    children.append((value_node, child, _INSIDE if key in SCOPED_SLOTS else _OUTSIDE))
                elif key not in SKIPPED_KEYS:
                    children.append((value_node, child, _INSIDE))
            for (source_id, identity), (label_path, label, occurrences) in groups.items():
                if (len(occurrences) > 1 and (source_id, identity) not in named
                        and _hides_something(where, _constructed(identity),
                                             [value for _, value in occurrences[:-1]])):
                    named[(source_id, identity)] = {
                        "path": label_path or "$", "key": label,
                        "lines": [line for line, _ in occurrences], "count": len(occurrences)}
            stack.extend(reversed(children))
    except (yaml.YAMLError, RecursionError):
        return []
    finally:
        loader.dispose()
    return sorted(named.values(), key=lambda d: d["lines"][0])


def describe_unread(duplicates: list[dict[str, Any]]) -> str:
    """One line naming each duplicate and why the record is not checked."""
    where = "; ".join(f"`{d['key']}` at {d['path']} on lines {', '.join(map(str, d['lines']))}"
                      for d in duplicates)
    return f"duplicate key {where}: a loader keeps only the last, so the earlier values were never scanned"


def _first_line(exc: BaseException) -> str:
    return (str(exc).splitlines() or [type(exc).__name__])[0]


def check_text(text: str) -> tuple[list[Mismatch] | None, str | None]:
    """A record's findings from its YAML text, or None and why it was not
    checked: the loader could not read it, it is not a mapping, or a
    duplicated key dropped values the scan would have read. Never raises for
    a record the loader rejects, so one bad record in a run cannot stop the
    others being reported (a record never looked at is not a clean one)."""
    try:
        record = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return None, _first_line(exc)
    except Exception as exc:                                   # noqa: BLE001
        # PyYAML's constructors raise bare ValueError (an impossible unquoted
        # date), AttributeError (`!!timestamp` on a non-date) and
        # RecursionError (deep nesting): every one means the record was not read.
        return None, f"the YAML loader raised {type(exc).__name__}: {_first_line(exc)}"
    try:
        found = slot_meaning_mismatch(record)
        unread = unread_duplicate_keys(text)
    except (TypeError, RecursionError) as exc:
        return None, _first_line(exc)
    return (None, describe_unread(unread)) if unread else (found, None)


def as_dict(mismatch: Mismatch) -> dict[str, Any]:
    """A finding as plain data (lists, not tuples), for JSON or YAML."""
    return {**asdict(mismatch), "kinds": list(mismatch.kinds), "terms": list(mismatch.terms)}


def report(record: dict[str, Any]) -> dict[str, Any]:
    """The findings as a plain block, naming the instrument that produced them.
    `gating: false` is part of the block so no consumer mistakes a count here
    for a floor."""
    found = slot_meaning_mismatch(record)
    return {
        "instrument": INSTRUMENT,
        "lexicon_sha256": LEXICON_SHA256,
        "gating": False,
        "slots": list(SCOPED_SLOTS),
        "mismatches": [as_dict(m) for m in found],
        "count": len(found),
    }


def describe(mismatch: Mismatch) -> str:
    """One line: where, what kind, the matched terms, and what the entry claims."""
    flag = f"{mismatch.slot}_present"
    claim = ("; the entry asserts " + f"{flag}: {str(mismatch.present).lower()}"
             if mismatch.present is not None else f"; the entry carries no {flag}")
    terms = ", ".join(repr(t) for t in mismatch.terms)
    return f"{mismatch.path}: {', '.join(mismatch.kinds)} ({terms}){claim}"
