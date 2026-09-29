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

Those nine are a selection, not the corpus. On 2026-09-28 the repository
commits 71 CM4AI full records and 63 cores; this scan flags 37 of the full
records and 35 of the cores, 13 of each with an entry asserting
`confidential_elements_present: true`, and no record of another project.

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
held something the scan reads: the duplicate is a scoped slot or sits under
one, or it is an ancestor — a second `resources` block, say — whose dropped
copy holds a scoped slot at any depth. `check_text` then reports the record as
not checked rather than clean. A duplicated ancestor whose dropped copies hold
no scoped slot hides nothing from this scan and is not named. The findings the
dropped values would have produced are not reported: the record is not
checked, not partly checked.

A record the loader cannot read at all — a YAML syntax error, an impossible
unquoted date such as `2026-02-30`, which PyYAML raises as a bare
`ValueError`, or nesting past the interpreter's recursion limit — is likewise
not checked. `check_text` catches whatever the loader raises, so one such
record never stops the others in a run from being reported.

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
from data_sheets_schema.duplicate_keys import _key_identity, find_duplicate_keys

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


def _read_by_the_scan(path: str, key: str) -> bool:
    """Whether the scan reads `key` in the mapping at `path` (a
    `duplicate_keys` path, `$` for the top level): the key is a scoped slot,
    or it sits under one and not under a skipped key."""
    names = [segment.split("[", 1)[0] for segment in path.split(".")] + [key]
    for index, name in enumerate(names):
        if name in SCOPED_SLOTS:
            return not SKIPPED_KEYS.intersection(names[index + 1:])
    return False


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


def _ancestors_hiding_a_slot(text: str) -> list[dict[str, Any]]:
    """Duplicated keys outside every scoped slot one of whose dropped values
    holds a scoped slot (#2980), in `find_duplicate_keys`'s shape and path
    spelling. Keys are compared by the #1029 gate's identity and merge keys
    are not duplicates, as there. A text the composer rejects yields nothing:
    `safe_load` rejects it too, and the record is not checked on that."""
    out: list[dict[str, Any]] = []
    try:
        loader = yaml.SafeLoader(text)
    except yaml.YAMLError:
        return out
    try:
        root = loader.get_single_node()
        stack = [(root, "")] if root is not None else []
        seen: set[int] = set()
        while stack:
            node, path = stack.pop()
            if id(node) in seen:
                continue
            seen.add(id(node))
            if isinstance(node, yaml.SequenceNode):
                stack.extend((item, f"{path}[{i}]") for i, item in reversed(list(enumerate(node.value))))
                continue
            if not isinstance(node, yaml.MappingNode):
                continue
            groups: dict[Any, tuple[str, list[tuple[int, Any]]]] = {}
            children = []
            for key_node, value_node in node.value:
                text_key = getattr(key_node, "value", None)
                label = text_key if isinstance(text_key, str) else str(text_key)
                child = f"{path}.{label}" if path else label
                if text_key == "<<" and getattr(key_node, "tag", "") == "tag:yaml.org,2002:merge":
                    children.append((value_node, f"{path}.<<" if path else "<<"))
                    continue
                groups.setdefault(_key_identity(loader, key_node), (label, []))[1].append(
                    (key_node.start_mark.line + 1, value_node))
                # A scoped slot's own contents are `_read_by_the_scan`'s to judge.
                if text_key not in SCOPED_SLOTS:
                    children.append((value_node, child))
            for label, occurrences in groups.values():
                dropped = [value for _, value in occurrences[:-1]]
                if len(occurrences) > 1 and any(_holds_a_scoped_slot(value) for value in dropped):
                    out.append({"path": path or "$", "key": label,
                                "lines": [line for line, _ in occurrences], "count": len(occurrences)})
            stack.extend(reversed(children))
    except yaml.YAMLError:
        return []
    finally:
        loader.dispose()
    return out


def unread_duplicate_keys(text: str) -> list[dict[str, Any]]:
    """Duplicated mapping keys in a record's text one of whose dropped values
    held something the scan reads: a scoped slot written twice, a key
    repeated inside one, or an ancestor — two `resources` blocks, say — whose
    earlier copy holds a scoped slot at any depth. `safe_load` keeps the last
    value (#1029), so a record carrying one of these is not a clean record
    whatever its last values say. Each is named once, in line order."""
    named = [d for d in find_duplicate_keys(text) if _read_by_the_scan(d["path"], d["key"])]
    known = {(d["path"], d["key"], tuple(d["lines"])) for d in named}
    named += [d for d in _ancestors_hiding_a_slot(text) if (d["path"], d["key"], tuple(d["lines"])) not in known]
    return sorted(named, key=lambda d: d["lines"][0])


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
