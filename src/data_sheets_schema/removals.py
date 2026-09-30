"""Values deleted after phase 1, classified against the audit (#2923).

`reconcile_full` is told to "remove what a finding identifies as
unsupported", and nothing checked that each value it removed was named by a
finding. The checks beside it measure other things: the receipts block counts
receipt paths that stopped resolving (`receipts_to_removed_values`) and mixes
deletions with list-to-string flattenings; `report_claims` compares the
report with the record at the top level only (`removals_unrecorded`, #1054).
That top-level check is how #2923 was found: three of nine v8 reviews named
a receipted top-level slot removed with no record in the report — VOICE 04f
rep2 `data_governance`, AI_READI 04g rep3 `content_warnings`, CHORUS 04f
rep2 `regulatory_restrictions` — and the report regate's remedy for an
unrecorded removal is a `removed` row, which documents the deletion rather
than restoring the value. Read value by value, this module finds a receipted
value that no finding's path covers removed in eight v8 records, not three
(#3078): six of the twelve-record 04f/g fill — those three, VOICE 04f rep1,
CHORUS 04f rep3 and AI_READI 04g rep2 — the AI_READI 04f rep1 record its own
validation block declares invalid, and the 04b CM4AI canary. Those are values
whose text does not survive by the rule below, not values proven gone: of the
five such values in VOICE 04f rep1, CHORUS 04f rep3 and AI_READI 04g rep2,
four reappear reworded elsewhere in the final record (#3207, see below).

This module diffs the phase-1 snapshot (the API runner's
`intermediate/{P}_full.yaml`; on the native and direct arms, which write no
intermediate, the frozen `evidence/original_full.yaml`, #3037) against the
final full record, value by value, and puts every value the final record no
longer carries in one class:

``flattened``
    the value's text survives, normalised, under its nearest ancestor that
    survives (a list collapsed to a string, an object to prose). Not a
    deletion. Where that ancestor is a list that is still a list and the
    object entry below it is what the join lost, the list is a set of other
    entries and not the ancestor (#3076): the text must survive in the one
    sibling recognisably that entry's continuation, or in entries of the
    list beyond those its other phase-1 entries account for
    (`_folded_into`).
``founded``
    deleted, and the `slot`, `review_paths` or `remove_relationship` path of
    an audit finding not scoped to the core record alone covers the value's
    path or an ancestor of it (#3079). A finding index one past the end of
    its phase-1 list is read as the last entry and the row says so
    (`index_past_end`, #3077).
``unfounded``
    deleted, and no such path covers it.

A value is a populated scalar, or one member of a list of scalars. Its
identity across the diff is `receipts.remap_path`'s (#899): a list entry is
followed by its key, else by the overlap of its scalars, and an entry whose
minted key reconciliation stripped is located at its own index
(`same_key_stripped`, #1053) — so a reorder, an insertion ahead of an entry or
a stripped key is not a removal. A value emptied to null or "" is removed.
A member of a list of scalars is identified by its text, a resolver URL read
as its CURIE and — from v3 (#3038) — a British spelling as the American form
the #1002 normaliser writes (`american_spelling.americanise`), in every text
comparison here, so a member respelled at write time is the same member. A
member reworded in any other way still reads as removed unless its old text
survives in the list (flattened); v3 reports where its words went (below).

A reworded or moved value reads as deleted (#3207). The text test is
containment of the value's own normalised text under the nearest surviving
ancestor, so content that reconcile_full rephrased, moved to another key of
its entry or to another slot, or split across several members is counted
deleted — and unfounded when no finding covers it — although its content
survives. Among the v8 rows the review checked: AI_READI 04g rep2
`sampling_strategies[0].notes` restated in that entry's new `source_caveats`
(a move out of the claim slots into the run's commentary — a change of
standing, not of content); VOICE 04f rep1
`at_risk_populations.special_protections[0]` split and reworded into members
1 and 3 of a three-member list, and its `ethical_reviews[1].review_details`
reworded into `data_governance.notes`; CHORUS 04f rep3
`acquisition_methods[0].notes` reworded into
`labeling_strategies[0].data_annotation_protocol`. Those inflate the deleted,
unfounded and receipted-deleted counts.

Two routes deflated them under v1 (#3229), and v2 closes the one and measures
the other (#3243). A lost value was classed flattened by coincidental
containment — in 2026-08-22c v5 rep1 CM4AI, reconcile_full dropped
`file_collections[1]`, and its `file_count` 3 read as flattened into
`file_collections` because "3" is a token of "3.8 GB" in another entry. A
value whose every token is a number now needs `MIN_NUMERIC_DIGITS` digits
before containment counts; below that it is deleted, which can only inflate.
A word or a long number can still coincide with unrelated text, so the
deflating route is narrowed, not gone. And a scalar whose text is replaced in
place is carried, not removed, since the join asks only that its path still
resolve to a populated value: v2 lists it in its own class,

``rewritten``
    carried at its path, and the value there no longer carries its text by
    the containment test below — sorted founded or not by the same finding
    paths, and never counted in `removed`. A rewrite reconcile_full made on
    a finding is what it was told to do; a rewrite no finding covers is the
    in-place analogue of an unfounded removal. A rewording that keeps the
    content is counted here too.

A resolver URL and the CURIE it names are one text in every containment test
(#3129), as they already were for list membership and fold identity: v1
counted the AI_READI v4 rep1 creator's eight ROR URLs and its PI's ORCID
deleted where the final record carries them as CURIEs. Each containment test
only widens, but the move from v1 to v2 is not one-way: the list-level fold
(`_folded_into`) compares two counts that both widen, so a phase-1 sibling that
carried the other form now raises the count the survivors must exceed, and a
value v1 read as flattened into its list can read as deleted under v2 (#3383).
Class declarations, `source_caveats` and minted ids are outside the
classification (`exempt_value`).

v3 (#3130, #3223, #3038, #3037) narrows coincidental flattening for numbers,
reads a British spelling as its American form (above), reads the native and
direct arms, and adds annotations that move no class:

- **A number is carried whole or not at all** (#3130). A value of numbers
  only (a count, a date) is flattened only where a scalar under the
  surviving ancestor *is* that value, normalised — never by containment in
  prose, at any length. Every numeric-only value v2 flattened was measured
  (ten, over the 87 checked records): nine were a number quoted inside the
  prose that disowned it — the 2026-08-13 v4 VOICE rep1
  `instances[1].counts` 32522 as one per-feature count in the entry's
  `source_caveats`, and the CM4AI v4/v7 `collection_timeframes[0]` start and
  end dates as the award period in `timeframe_details` beside "the sources
  give no start or end date for data collection" — and one a release date
  carried as itself, which stays flattened. The other option #3130 named,
  never flattening a number, moves that tenth row too.
- **Where a deleted value's words went** (#3223). Each founded, unfounded
  or unsorted row whose value has `RELOCATED_MIN_WORDS` content words or
  more gets a reported-only `relocated_candidate` when at least
  `RELOCATED_THRESHOLD` of them occur in one final-record scalar (or one
  list of scalars taken whole): the best such path and the share. An
  identifier-shaped value (a URL, CURIE or `mailto:`) is assessed by its
  own text on token boundaries instead, its scheme `mailto:` aside. A
  candidate under `source_caveats` is marked `change_of_standing`: the
  value is no longer a claim, only the run's commentary on one. Validated
  on a hand-labelled sample of deleted rows (`RELOCATED_VALIDATION`). No
  class count moves: a candidate is where the words are, not proof the
  content survives, and a value it misses can still have been reworded.
- **A flattened value only the run's commentary carries** (#3223) keeps its
  class and is marked `into_source_caveats`: every scalar that carries its
  text is a `source_caveats` — a change of standing, not of text.
- **The native and direct arms** (#3037) are read from the snapshot they
  freeze, `evidence/original_full.yaml`, with `evidence/audit.json`. They
  write no phase output, so their removals are not attributed to a phase.
  Where the audit carries a `source_review` bound to the snapshot's bytes
  (evidence protocol v3+), each deleted or rewritten row carries its
  judgment (`supported`, `revise`, `metadata`, `unreviewed`), and — as
  #2923 proposed — a value reviewed `supported` is founded only by a
  finding linked to it by path (`review_paths` or `remove_relationship`),
  never by a finding's free-text `slot` alone.

The removing phase is the first stage after the last one that still carried
the value: `reconcile_full`, `repair_full_rN`, or `write` (the last phase
output carried it and the written record does not). A phase output that is
missing or cannot be read leaves every removal unattributed (#3152). A
repair round acts on validation errors, not on the audit, so a value it
removes has a finding only by coincidence: `unfounded_phase` splits the
unfounded count by the phase that removed each value (#3150).

Reported only. No provenance block is written here and nothing is gated:
`unfounded` says no finding's path covers the value, not that the removal was
wrong, and `founded` says a finding's path covers it, not that the finding
was right. With no phase-1 snapshot (the agentic path before the evidence
protocol writes none) every count is None, never 0 — the #899 convention: an
absent snapshot is not a clean diff.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from data_sheets_schema.receipts import (ENTRY_KEYS, _canonical_identifier, _populated, _resolve_value,
                                         dataset_identifier_forms, exempt, normalise, remap_path)

INSTRUMENT = ("removals v3 (#3037, #3038, #3130, #3223): phase-1 snapshot (or the native/direct "
              "evidence/original_full.yaml) against the final full record, joined by "
              "receipts.remap_path; flattened by normalised containment under the nearest "
              "surviving ancestor, a resolver URL and its CURIE one text, a British spelling and "
              "its American form one text, a value of numbers only below five digits never and "
              "otherwise only by a scalar equal to it, a dropped list entry's only in its "
              "recognised continuation or beyond what the list's other phase-1 entries account "
              "for; a carried scalar whose text its path no longer contains is rewritten, apart "
              "from the removals; founded by a finding's slot, review_paths or remove_relationship "
              "path covering the value or an ancestor (review_paths or remove_relationship only, "
              "for a value a bound source review judged supported), an index one past the end "
              "read as the last entry, in a finding whose record is not core only; a deleted "
              "value's relocation candidate reported at a content-word share of 0.7 or more")

#: Paths kept in the block per class; the counts are never capped.
PATH_LIMIT = 50

#: A value whose every normalised token is a number is flattened only with at
#: least this many digits (#3243). A count, an index or a year recurs in
#: sizes, versions and dates of unrelated text — the 22c CM4AI `file_count` 3
#: in "3.8 GB". From v3 (#3130) a longer one also needs a scalar equal to it,
#: so the guard now keeps a short number from being carried by an equal but
#: unrelated one (another entry's `file_count: 3`). Of the ten numeric-only
#: values v2 flattened, the one v3 still flattens is a date (the 2026-08-06
#: v3 AI_READI `distribution_dates[2].release_dates[0]`); the 5-digit count
#: of v4 VOICE rep1 — 32522 on the recording-features instance of the
#: snapshot the run pins, `VOICE_full_2.yaml`, not the 29278 of its
#: `VOICE_full.yaml` #3396 read — survived within that entry only as one
#: per-feature count in the entry's `source_caveats`.
MIN_NUMERIC_DIGITS = 5

#: A deleted value's relocation candidate (#3223): the share of its content
#: words (`_words`) that one final-record scalar, or one list of scalars
#: taken whole, must carry. Chosen on the hand-labelled sample in
#: `RELOCATED_VALIDATION`, where 0.6 trades precision for recall and 0.8
#: recall for precision.
RELOCATED_THRESHOLD = 0.7

#: Fewer content words than this and a share says nothing (a two-word name
#: recurs in any affiliation list): the row is not assessed. An
#: identifier-shaped value is assessed by its own text instead.
RELOCATED_MIN_WORDS = 3

#: The sample the threshold was chosen on, and what it measured there.
RELOCATED_VALIDATION = "notes/removals_relocated_sample_2026-09-29.yaml"

#: A path under the run's commentary: a move there is a change of standing.
_CAVEAT_PATH = re.compile(r"(?:^|\.)source_caveats(?:\[|\.|$)")

#: A value that is one identifier: a URL, a CURIE, a `mailto:`.
_IDENTIFIER_SHAPED = re.compile(r"(?:[a-z][a-z0-9+.-]*://\S+|[A-Za-z][\w.-]*:\S+)", re.I)

#: The grammar `receipts.remap_path` reads. A key outside it cannot be joined.
_ADDRESSABLE = re.compile(r"\w+(\[\d+\])*(\.\w+(\[\d+\])*)*")

NON_CHECKS = (
    "that an unfounded removal was wrong — a value can be unsupported with no finding naming "
    "it; unfounded says only that no finding's path covers it",
    "that a founded removal was right — a finding naming a slot is not evidence that its "
    "value was unsupported",
    "that a flattened value kept its meaning — normalised text containment under the nearest "
    "surviving ancestor, not a semantic comparison: a word can coincide with unrelated text "
    "(a number is flattened only by a scalar equal to it, and never below five digits, "
    "#3243, #3130), and a "
    "value a dropped list entry shared with its siblings is not traced "
    "to the entry — it is flattened where the sibling recognised as the entry's continuation "
    "carries it, though that copy may be the sibling's own, and otherwise only where more "
    "final entries carry it than the entry's other phase-1 siblings did (#3151)",
    "that a deleted value's content is gone — the text test is exact normalised containment of "
    "the value's own text, so a value reworded, moved to another key (source_caveats included) or "
    "slot, or split across several list members reads as deleted, and as unfounded when no "
    "finding covers it (#3207); and not that a flattened value's content survives — a word "
    "can still be flattened by coincidental containment, though a number no longer is (the "
    "file_count 3 that matched the '3' of '3.8 GB', #3243; a count or a date quoted in the "
    "prose that disowned it, #3130): rewording and moving inflate the deleted, unfounded and "
    "receipted-deleted counts, coincidental flattening still deflates them, so they bound "
    "nothing (#3229)",
    "that a relocation candidate restates the value — it is where the largest share of the "
    "value's content words recurs in one final scalar, not a semantic comparison: at the "
    "declared threshold the labelled sample measured it right about nine times in ten and "
    "found about four relocations in five (RELOCATED_VALIDATION), a value with fewer than "
    "three content words (a number, a date, a short name) is not assessed unless it is "
    "identifier-shaped (a CURIE or a URL, matched by its own text whatever its word count), "
    "and a candidate moves no count (#3223, #3553)",
    "that a source review's judgment was right — a removed value reviewed supported and founded "
    "by no linked finding is unfounded on the review's word, and one reviewed revise is still "
    "founded only by a finding's path (#3037)",
    "that a rewritten value lost its content, or that a carried one kept it — rewritten is a "
    "carried scalar whose normalised text the value now at its path does not contain, so a "
    "rewording that keeps the content is counted, and an edit that keeps the old text as a "
    "substring (an extension, or a change inside a longer text that leaves the value's words "
    "in order) is not; rewrites are reported beside the removals and never counted in them "
    "(#3243)",
    "a finding that narrows its slot in prose ('maintainers (the Emory contact)') is read at "
    "the path it names, so founded is an upper bound where findings narrow by prose",
    "that a finding's index means the entry it gives — one past the end of its list is read "
    "as the last entry (founded_past_end counts those values); an index in range is read as "
    "written, so an audit counting from 1 there founds the entry after the one it meant",
    "a finding scoped to the core record alone founds nothing here, though its path may cover "
    "the value (unfounded_named_by_core_finding counts those)",
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


@lru_cache(maxsize=1 << 16, typed=True)
def _member(value: Any) -> str:
    """A list member's identity: its text, a resolver URL read as the CURIE
    it names (#974's normaliser rewrites one to the other at write time)
    and a British spelling as the American form (#1002's normaliser, the
    form instrument's rules; #3038). Identifier-shaped tokens are left as
    written, as the normaliser leaves them; the text is folded to lower
    case first, so a Capitalised word its proper-noun rule would skip is
    folded too — this is an identity, not a rewrite."""
    if not isinstance(value, str):
        return _text(value)
    from data_sheets_schema.american_spelling import americanise
    return _text(americanise(_canonical_identifier(value.strip()).casefold())[0])


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

    def retains(self, path: str, value: Any) -> bool:
        """For a scalar under a key that `carried` finds: whether what its
        path holds now still contains its text (#3243). A member of a list
        of scalars is identified by its text, so it has no rewrite. A value
        with no text once normalised (a path of "/") is kept only as written."""
        rm = remap_path(path, self.original, self.target)
        ok, node = _resolve_value(self.target, rm["path"]) if rm["path"] is not None else (False, None)
        return ok and (node == value or _survives(value, node))

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


def _carries(hay: str, needle: str) -> bool:
    """Normalised containment on token boundaries."""
    return bool(needle) and f" {needle} " in f" {hay} "


def _hay(node: Any, form=_text) -> str:
    """A node's scalars as one normalised text."""
    return " ".join(form(s) for s in _scalars(node))


def _survives(value: Any, node: Any) -> bool:
    """Does `node` carry `value`'s text? Containment on token boundaries,
    with a resolver URL and the CURIE it names one text on either side
    (#3129): the needle and each scalar of the hay are read as written and
    as `_member` reads them, so a ROR URL the final record carries as
    `ROR:…` survives, and a URL quoted inside prose still matches as
    written."""
    needles = {_text(value), _member(value)} - {""}
    hays = (_hay(node), _hay(node, _member))
    return any(_carries(h, n) for n in needles for h in hays)


def _numeric(value: Any) -> bool:
    """A value of numbers only, once normalised: a count, a year, a date."""
    tokens = _text(value).split()
    return bool(tokens) and all(t.isdigit() for t in tokens)


def _flattenable(value: Any) -> bool:
    """Whether containment can count for this value at all: never a boolean
    (its text is not the fact it states), and never a value of numbers only
    with fewer than `MIN_NUMERIC_DIGITS` digits, which recurs in unrelated
    text by chance (#3243)."""
    if isinstance(value, bool) or not _text(value).split():
        return False
    return not (_numeric(value) and sum(map(len, _text(value).split())) < MIN_NUMERIC_DIGITS)


def _kept_in(value: Any, node: Any) -> bool:
    """The flattening test: `_survives`, except that a value of numbers only
    is carried only by a scalar equal to it, normalised (#3130) — a count or
    a date inside prose is a number quoted, not the value kept."""
    if not _numeric(value):
        return _survives(value, node)
    want = {_text(value), _member(value)}
    return any(_text(s) in want or _member(s) in want for s in _scalars(node))


def _into_source_caveats(value: Any, node: Any, path: str) -> bool:
    """Whether every scalar of `node` (at `path`) that carries the value's
    text is a `source_caveats` — the run's commentary, not a claim (#3223)."""
    wrapped = {"_": node}
    carriers = [p for p, s, _lp in values(wrapped) if _kept_in(value, s)]
    return bool(carriers) and all(_CAVEAT_PATH.search(path + p[1:]) for p in carriers)


def _identity(entry: dict[str, Any]) -> list[str]:
    """The identifying texts of a list entry: every `receipts.ENTRY_KEYS`
    string on the entry and on the objects nested in it by key — not on the
    entries of a list inside it, which are other things (an affiliation is
    not the creator). An identifier is read as the CURIE it names."""
    out: list[str] = []
    stack: list[Any] = [entry]
    while stack:
        node = stack.pop()
        out += [_member(node[k]) for k in ENTRY_KEYS if isinstance(node.get(k), str)]
        stack += [v for v in node.values() if isinstance(v, dict)]
    return [t for t in out if t]


def _join(base: str, rel: str) -> str:
    return f"{base}{rel}" if rel.startswith("[") else f"{base}.{rel}"


def _fold_target(entry_path: str, entry: dict[str, Any], survivors: list[Any],
                 record_id: str | None, carried: frozenset[str]) -> int | None:
    """The index of the one surviving entry recognisably the dropped
    entry's continuation, or None: the entry carrying the most of its
    identifying texts (`_identity`), no other as many — the CM4AI v4 rep3
    creator whose minted id was replaced by the PI's ORCID, the name moving
    to `principal_investigator` — or, for an entry with no identifying key,
    the one entry carrying every value it had that is inside the
    classification: the CHORUS 2026-08-11 leadership team folded into one
    entry's notes, name and affiliation each."""
    needles = _identity(entry)
    need_all = not needles
    if need_all:
        needles = [t for t in (_member(v) for p, v, lp in values(entry)
                               if not isinstance(v, bool)
                               and not exempt_value(_join(entry_path, lp if lp is not None else p), v,
                                                    record_id, carried)) if t]
    if not needles:
        return None
    scores = [sum(_carries(h, t) for t in needles) for h in (_hay(e, _member) for e in survivors)]
    best = max(scores, default=0)
    if best == 0 or (need_all and best < len(needles)) or scores.count(best) > 1:
        return None
    return scores.index(best)


def _folded_into(value: Any, entry_path: str, entry: dict[str, Any], snapshot_list: list[Any],
                 final_path: str, survivors: list[Any], record_id: str | None,
                 carried: frozenset[str]) -> str | None:
    """Where a value of a dropped list entry — an object `receipts.remap_path`
    no longer finds in a list that is still a list — survives, or None
    (#3076). The whole list is not the surviving ancestor: it is a set of
    distinct entries, and a word of the dropped entry that recurs in one of
    them is the root's coincidence at list level. The AI_READI v7 rep2
    `file_collections[9]` entry "Root metadata files" is in no sibling, yet
    its `collection_type` 'metadata' is a word of another entry's
    description and its conformance standard every sibling's. So the value
    survives only

    - in the sibling `_fold_target` recognises as the entry's continuation,
      or
    - in the list, where more of its final entries carry the value's text
      than the list's other phase-1 entries did: the surplus is the dropped
      entry's — an entry split in several (CM4AI 22c rep1's image archives,
      one entry per file), one whose key and name were both rewritten
      ('Ulrika Axelsson' as 'Axelsson U'), one folded into a sibling's
      prose. A text its siblings carried as often before (the conformance
      standard, a shared affiliation, an enum) is counted, not attributed.

    The path returned is the sibling's in the first case and the list's in
    the second. Texts are compared by `_survives`, a resolver URL and its
    CURIE as one (#3129). That widens both counts of the second route, so it
    can narrow: a sibling that carried the value's other form counts before,
    where v1 did not count it, and a v1 surplus can vanish (#3383). A value
    of numbers only counts only where a scalar equals it (`_kept_in`,
    #3130)."""
    j = _fold_target(entry_path, entry, survivors, record_id, carried)
    if j is not None and _kept_in(value, survivors[j]):
        return f"{final_path}[{j}]"
    k = int(entry_path[entry_path.rindex("[") + 1:-1])
    after = sum(_kept_in(value, e) for e in survivors)
    before = sum(_kept_in(value, e) for i, e in enumerate(snapshot_list) if i != k)
    return final_path if after > before else None


def _flattened_into(path: str, value: Any, original: dict[str, Any], final: dict[str, Any], *,
                    record_id: str | None = None, carried: frozenset[str] = frozenset()) -> str | None:
    """The final-record path of the nearest surviving ancestor whose text
    carries the value's, normalised and on token boundaries; None when the
    nearest surviving ancestor does not carry it, or none survives short of
    the root. The root never counts: a top-level slot whose words happen to
    occur elsewhere in the record was deleted, not flattened. Nor, for the
    same reason, does a list that is still a list when the object entry
    below it is what identity lost (`_folded_into`, #3076). A member of a
    list of scalars is one value of that slot, and its text surviving
    anywhere in the list is still read as flattened (a string split into
    members). A boolean is never flattened — its text is not the fact it
    states — nor a value of numbers only below `MIN_NUMERIC_DIGITS` digits
    (#3243), nor a longer one except by a scalar equal to it (#3130); a
    resolver URL and the CURIE it names are one text (#3129), and so are a
    British spelling and its American form (#3038)."""
    if not _flattenable(value):
        return None
    below = path
    for anc in _ancestors(path):
        rm = remap_path(anc, original, final)
        if rm["path"] is None:
            below = anc
            continue
        ok, node = _resolve_value(final, rm["path"])
        if not ok or not _populated(node):
            below = anc
            continue
        if isinstance(node, list) and below.startswith(anc + "["):
            _ok, entry = _resolve_value(original, below)
            _ok, snapshot_list = _resolve_value(original, anc)
            if isinstance(entry, dict) and isinstance(snapshot_list, list):
                return _folded_into(value, below, entry, snapshot_list, rm["path"], node, record_id, carried)
        return rm["path"] if _kept_in(value, node) else None
    return None


# -------------------------------------------------------------- relocation
@lru_cache(maxsize=1 << 16, typed=True)
def _words(value: Any) -> frozenset[str]:
    """A value's content words: `_member`'s tokens longer than two
    characters, less `redundancy.STOPWORDS` (#3223)."""
    from data_sheets_schema.redundancy import STOPWORDS
    return frozenset(w for w in _member(value).split() if len(w) > 2 and w not in STOPWORDS)


class _Relocation:
    """Where a deleted value's words recur in the final record (#3223):
    each populated scalar, and each list of scalars taken whole — a member
    split in three is in the list, not in any one member."""

    def __init__(self, final: dict[str, Any]):
        scalars = values(final)
        lists: dict[str, list[Any]] = {}
        for _p, v, lp in scalars:
            if lp is not None:
                lists.setdefault(lp, []).append(v)
        self.members = [(p, _member(v)) for p, v, _lp in scalars]
        self.words = ([(p, _words(v)) for p, v, _lp in scalars]
                      + [(lp, frozenset().union(*map(_words, vs))) for lp, vs in lists.items()])

    def candidate(self, value: Any) -> tuple[bool, dict[str, Any] | None]:
        """(assessed, candidate or None). An identifier-shaped value is
        assessed by its own text on token boundaries (a `mailto:` scheme
        aside); any other by the share of its content words one candidate
        carries, where it has `RELOCATED_MIN_WORDS` of them. The first
        path in record order wins a tie, a scalar before a list."""
        if isinstance(value, str) and _IDENTIFIER_SHAPED.fullmatch(value.strip()):
            needle = _member(re.sub(r"^mailto:", "", value.strip(), flags=re.I))
            hit = next((p for p, m in self.members if _carries(m, needle)), None)
            return True, (self._row(hit, 1.0) if hit is not None else None)
        want = _words(value)
        if isinstance(value, bool) or len(want) < RELOCATED_MIN_WORDS:
            return False, None
        best, at = 0.0, None
        for p, have in self.words:
            share = len(want & have) / len(want)
            if share > best:
                best, at = share, p
        return True, (self._row(at, best) if at is not None and best >= RELOCATED_THRESHOLD else None)

    @staticmethod
    def _row(path: str, share: float) -> dict[str, Any]:
        # A move into the run's commentary: no longer a claim (#3223).
        return {"to": path, "share": round(share, 3), "change_of_standing": bool(_CAVEAT_PATH.search(path))}


# ----------------------------------------------------------- source review
def _pointer_path(pointer: Any) -> str | None:
    """A JSON Pointer as this module's dotted path: `/a/0/b` -> `a[0].b`."""
    toks = pointer_tokens(pointer)
    if not toks:
        return None
    out = ""
    for t in toks:
        out += f"[{t}]" if isinstance(t, int) else (f".{t}" if out else str(t))
    return out


def source_review_judgments(audit: Any, snapshot_sha256: str | None = None
                            ) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    """(state, {path: judgment}) from an audit's original_full
    `source_review` (evidence protocol v3+; the native and direct arms, #3037).
    A value's judgment is `revise` where any claim on it is, `supported`
    where every claim is, `metadata` where it was exempted as record
    metadata. None, None where the audit carries no source review; the
    judgments None, with the reason, where it cannot be bound to the
    snapshot read — another artifact, or other bytes than `snapshot_sha256`."""
    review = audit.get("source_review") if isinstance(audit, dict) else None
    if review is None:
        return None, None
    if (not isinstance(review, dict) or review.get("artifact") != "original_full"
            or not isinstance(review.get("values"), list)):
        return {"state": "unusable", "reason": "the audit's source_review is not an original_full "
                                               "review with a values list"}, None
    if snapshot_sha256 is not None and review.get("sha256") != snapshot_sha256:
        return {"state": "unbound", "reason": "the source review is bound to other bytes than the snapshot "
                                              "read here (sha256 differs)"}, None
    judged: dict[str, str] = {}
    for row in review["values"]:
        path = _pointer_path(row.get("path")) if isinstance(row, dict) else None
        if path is None:
            continue
        if "claims" not in row and "metadata_reason" in row:
            judged[path] = "metadata"
            continue
        verdicts = {c.get("verdict") for c in row.get("claims") or [] if isinstance(c, dict)}
        judged[path] = ("revise" if "revise" in verdicts
                        else "supported" if verdicts == {"supported"} else "unreviewed")
    return {"state": "bound" if snapshot_sha256 is not None else "unhashed", "reason": None}, judged


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


def covers(finding_path: list[Any], path: str, original: dict[str, Any], *, past_end: bool = False) -> bool:
    """Does a finding's path name `path` or one of its ancestors? Keys must
    agree step for step; at a list index the finding may give the index, a
    wildcard, a set of indexes or an entry's name, or step over it with the
    next key (`creators.affiliations` for `creators[3].affiliations`). The
    empty path — the root — covers nothing.

    With `past_end`, an index exactly one past the end of the snapshot list
    it indexes is read as the list's last entry (#3077): as written it
    names no entry, and counting from 1 is the only reading under which it
    names one. The 04f v8 rep3 VOICE finding on `preprocessing_strategies[6]`
    of a six-entry list describes entry 5 (12 words shared, at most 3 with
    any other). Of the v7 rep2 AI_READI findings on a ten-entry
    `file_collections`, the one on `file_collections[10].id` quotes entry
    9's `#root-metadata` id, the only such id in the list, and the one on
    `.file_count` quotes `file_count: 9` and the nine metadata files that
    count covers — entry 9's count, and no other entry's (#3155). An index
    further past the end, or one in range, is read as written."""
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
                last = (past_end and isinstance(node, list) and len(node) > 0
                        and want == len(node) and step == len(node) - 1)
                if want != step and not last:
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


def past_end(finding_path: list[Any], original: dict[str, Any]) -> tuple[int, int] | None:
    """(index, length) where a finding's path gives a literal index at or
    past the end of the snapshot list it indexes, else None. Followed while
    each step is a key the snapshot has or an index; a wildcard, a set, a
    selector or a stepped-over index ends the walk, having no one entry to
    test."""
    node: Any = original
    for want in finding_path:
        if isinstance(node, list) and isinstance(want, int) and not isinstance(want, bool):
            if want >= len(node):
                return want, len(node)
            node = node[want]
        elif (isinstance(node, dict) and isinstance(want, str) and not isinstance(want, _Selector)
              and want in node):
            node = node[want]
        else:
            return None
    return None


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
            "founded": None, "unfounded": None, "founded_by": None, "founded_past_end": None,
            "unfounded_named_by_core_finding": None, "unfounded_mentioned_in_finding_text": None,
            "receipted": None, "phase": None, "unfounded_phase": None, "audit": None,
            "rewritten": None, "rewritten_unfounded": None, "rewritten_receipted": None,
            "rewritten_unfounded_phase": None, "flattened_into_source_caveats": None,
            "relocated_candidate": None, "relocated_candidate_unfounded": None,
            "relocated_candidate_standing": None, "relocated_not_assessed": None, "source_review": None,
            **{f"{cls}_paths{suffix}": ([] if not suffix else None)
               for cls in ("flattened", "founded", "unfounded", "unsorted", "rewritten")
               for suffix in ("", "_truncated")},
            "summary": f"not checked: {reason}", "non_checks": list(NON_CHECKS)}


def _cap(rows: list[dict[str, Any]], key: str, block: dict[str, Any]) -> None:
    block[key] = rows[:PATH_LIMIT]
    block[f"{key}_truncated"] = max(0, len(rows) - PATH_LIMIT) or None


def classify(original: dict[str, Any] | None, final: dict[str, Any],
             audit: dict[str, Any] | None = None, *,
             receipt: dict[str, Any] | None = None,
             intermediates: list[tuple[str, dict[str, Any] | None]] | None = None,
             audit_unread: str | None = None, snapshot_sha256: str | None = None) -> dict[str, Any]:
    """The block for one run. Pure: snapshot + final record + audit (+ the
    receipt, + the phase outputs in order) -> block.

    `original` None (no phase-1 snapshot) returns every count None. `audit`
    None, or one without a `findings` list, leaves `founded`/`unfounded`
    None while `flattened` and `deleted` are still counted, the deleted
    values listed under `unsorted_paths`: a missing audit is not an audit
    with no findings. `audit_unread` is why an audit that exists could not
    be read (`for_record` passes the reason), so the summary says that
    rather than that there is no audit (#3153). `receipt` None leaves
    `receipted` None. `intermediates` is `[(phase name, output or None),
    ...]` between the snapshot and the final record, in run order; without
    them, or with any output None (it is missing or could not be read),
    `phase` and `unfounded_phase` are None. `snapshot_sha256` is the hash
    of the snapshot bytes, which an audit's `source_review` must name to
    be read (#3037); without it the review is read as `unhashed`."""
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
    # A phase output that is missing or could not be read leaves every
    # removal unattributed: across the gap, "the stage after the last one
    # that carried it" would name a later phase for a value an earlier one
    # removed.
    attributed = intermediates is not None and all(isinstance(doc, dict) for _n, doc in intermediates)
    review_state, judged = source_review_judgments(audit, snapshot_sha256)
    relocation = _Relocation(final)
    at_final = _Presence(original, final)
    at_stage = [(name, _Presence(original, doc)) for name, doc in (intermediates or [])] if attributed else []

    def stage_after_last(keeps) -> str:
        # The stage after the last one that still kept the value; the
        # snapshot (index -1) kept it by construction.
        last = max((i for i, (_n, p) in enumerate(at_stage) if keeps(p)), default=-1)
        return at_stage[last + 1][0] if last + 1 < len(at_stage) else "write"

    def finding_for(path: str, linked_only: bool = False) -> tuple[int, str, bool] | None:
        pool = [t for t in named if not linked_only or t[1] != "slot"]
        hit = next(((n, via, False) for n, via, fp in pool if covers(fp, path, original)), None)
        if hit is None:
            # An index one past the end of its list names no entry as
            # written; read as the last entry, and said so on the row (#3077).
            hit = next(((n, via, True) for n, via, fp in pool
                        if covers(fp, path, original, past_end=True)), None)
        return hit

    def judge(row: dict[str, Any], path: str) -> tuple[int, str, bool] | None:
        # The source review's judgment on the value (#3037), and the finding
        # that founds it: for a value reviewed `supported`, only one linked
        # to it by path — a finding's free-text slot does not overrule the
        # review, as #2923 proposed.
        if judged is not None:
            row["source_review"] = judged.get(path, "unreviewed")
        if row.get("source_review") != "supported":
            return finding_for(path)
        hit = finding_for(path, linked_only=True)
        if hit is None and finding_for(path) is not None:
            row["supported_slot_only"] = True
        return hit

    total = exempted = unaddressable = not_assessed = 0
    rows: dict[str, list[dict[str, Any]]] = {"flattened": [], "founded": [], "unfounded": [], "unsorted": [],
                                             "rewritten": []}
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
            # Carried, but its path may hold other text now (#3243): reported
            # as its own class, never a removal.
            if list_path is None and not at_final.retains(path, value):
                rw: dict[str, Any] = {"path": path, "at": remap_path(path, original, final)["path"]}
                if attributed:
                    rw["phase"] = stage_after_last(lambda p: p.carried(path, None) and p.retains(path, value))
                if paths_receipted is not None:
                    rw["receipted"] = _receipted(path, None, paths_receipted)
                if named is not None:
                    hit = judge(rw, path)
                    rw["founded"] = hit is not None
                    if hit is not None:
                        rw.update({"by": hit[1], "finding": hit[0], **({"index_past_end": True} if hit[2] else {})})
                elif judged is not None:
                    rw["source_review"] = judged.get(path, "unreviewed")
                rows["rewritten"].append(rw)
            continue
        row: dict[str, Any] = {"path": path}
        if attributed:
            row["phase"] = stage_after_last(lambda p: p.carried(path, list_path))
            by_phase[row["phase"]] = by_phase.get(row["phase"], 0) + 1
        if paths_receipted is not None:
            row["receipted"] = _receipted(path, list_path, paths_receipted)
            receipted["removed"] += row["receipted"]
        into = _flattened_into(path, value, original, final, record_id=record_id, carried=carried)
        if into is not None:
            flat = {**row, "into": into}
            if _into_source_caveats(value, _resolve_value(final, into)[1], into):
                flat["into_source_caveats"] = True
            rows["flattened"].append(flat)
            receipted["flattened"] += bool(row.get("receipted"))
            continue
        receipted["deleted"] += bool(row.get("receipted"))
        # Where its words went (#3223): reported, never a class.
        assessed, where = relocation.candidate(value)
        if where is not None:
            row["relocated_candidate"] = where
        elif not assessed:
            not_assessed += 1
        if named is None:
            if judged is not None:
                row["source_review"] = judged.get(path, "unreviewed")
            rows["unsorted"].append(row)
            continue
        hit = judge(row, path)
        if hit is not None:
            founded_by[hit[1]] += 1
            rows["founded"].append({**row, "by": hit[1], "finding": hit[0],
                                    **({"index_past_end": True} if hit[2] else {})})
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
    deleted_rows = rows["founded"] + rows["unfounded"] + rows["unsorted"]

    def tally(rs: list[dict[str, Any]]) -> dict[str, int]:
        out = {k: 0 for k in ("supported", "revise", "metadata", "unreviewed")}
        for r in rs:
            out[r["source_review"]] += 1
        return out
    # Every finding path (not core only) whose literal index runs past the
    # end of the snapshot list: True where by exactly one of a non-empty
    # list, the reading `covers(past_end=True)` makes; False where further,
    # or into an empty list, which names nothing.
    ends = [e[0] == e[1] > 0 for _n, _via, fp in (named or []) if (e := past_end(fp, original))]
    deleted = len(rows["founded"]) + len(rows["unfounded"]) + len(rows["unsorted"])
    block: dict[str, Any] = {
        "instrument": INSTRUMENT, "checked": True, "reason": None,
        "snapshot_values": total, "exempt": exempted, "unaddressable": unaddressable,
        "removed": len(rows["flattened"]) + deleted, "flattened": len(rows["flattened"]),
        "deleted": deleted,
        "founded": len(rows["founded"]) if sorted_ else None,
        "unfounded": len(rows["unfounded"]) if sorted_ else None,
        "founded_by": founded_by if sorted_ else None,
        "founded_past_end": (sum(1 for r in rows["founded"] if r.get("index_past_end"))
                             if sorted_ else None),
        "unfounded_named_by_core_finding": (sum(1 for r in rows["unfounded"] if r.get("named_by_core_finding"))
                                            if sorted_ else None),
        "unfounded_mentioned_in_finding_text": (sum(1 for r in rows["unfounded"]
                                                    if r.get("mentioned_in_finding_text"))
                                                if sorted_ else None),
        "receipted": ({k: (v if sorted_ or k not in ("founded", "unfounded") else None)
                       for k, v in receipted.items()} if paths_receipted is not None else None),
        "phase": by_phase if attributed else None,
        # The unfounded count by removing phase (#3150): a repair round acts
        # on validation errors, not on the audit, so a value it removes has a
        # finding only by coincidence; reconcile_full is the phase told to
        # remove what a finding identifies.
        "unfounded_phase": (_by_phase(rows["unfounded"]) if attributed and sorted_ else None),
        "audit": ({"findings": len(findings), "core_only": sum(1 for f in findings if _core_only(f)),
                   "paths_past_end": ends.count(True) + ends.count(False),
                   "paths_one_past_end": ends.count(True)}
                  if findings is not None else None),
        # Carried scalars whose path now holds other text (#3243): beside
        # the removals, never in them. Unfounded and receipted as above.
        "rewritten": len(rows["rewritten"]),
        "rewritten_unfounded": (sum(1 for r in rows["rewritten"] if not r["founded"]) if sorted_ else None),
        "rewritten_receipted": (sum(1 for r in rows["rewritten"] if r["receipted"])
                                if paths_receipted is not None else None),
        "rewritten_unfounded_phase": (_by_phase([r for r in rows["rewritten"] if not r["founded"]])
                                      if attributed and sorted_ else None),
        # Reported only (#3223): a flattened value whose text only the run's
        # commentary carries, and where each deleted value's words went.
        "flattened_into_source_caveats": sum(1 for r in rows["flattened"] if r.get("into_source_caveats")),
        "relocated_candidate": sum(1 for r in deleted_rows if "relocated_candidate" in r),
        "relocated_candidate_unfounded": (sum(1 for r in rows["unfounded"] if "relocated_candidate" in r)
                                          if sorted_ else None),
        "relocated_candidate_standing": sum(1 for r in deleted_rows
                                            if (r.get("relocated_candidate") or {}).get("change_of_standing")),
        "relocated_not_assessed": not_assessed,
        # The source review's judgments on what was deleted or rewritten (#3037).
        "source_review": (None if review_state is None else {
            **review_state,
            "deleted": tally(deleted_rows) if judged is not None else None,
            "rewritten": tally(rows["rewritten"]) if judged is not None else None,
            "unfounded_supported": (sum(1 for r in rows["unfounded"] if r.get("source_review") == "supported")
                                    if judged is not None and sorted_ else None),
            "unfounded_supported_slot_only": (sum(1 for r in rows["unfounded"] if r.get("supported_slot_only"))
                                              if judged is not None and sorted_ else None)}),
    }
    for cls in ("flattened", "founded", "unfounded", "unsorted", "rewritten"):
        _cap(rows[cls], f"{cls}_paths", block)
    if findings is not None:
        unsorted_why = None
    elif audit_unread:
        unsorted_why = f"the audit could not be read ({audit_unread}), so the deletions are not sorted"
    elif isinstance(audit, dict):
        unsorted_why = "the audit carries no findings list to sort the deletions against"
    else:
        unsorted_why = "no audit to sort the deletions against"
    block["summary"] = _summary(block, unsorted_why)
    block["non_checks"] = list(NON_CHECKS)
    return block


def _by_phase(rows: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        out[r["phase"]] = out.get(r["phase"], 0) + 1
    return out


def _summary(block: dict[str, Any], unsorted_why: str | None = None) -> str:
    if not block["checked"]:
        return f"not checked: {block['reason']}"
    head = (f"{block['snapshot_values']} phase-1 values ({block['exempt']} exempt)"
            f" · {block['flattened']} flattened")
    if block["founded"] is None:
        return (head + f" · {block['deleted']} deleted · {unsorted_why or 'the deletions are not sorted'}"
                f" · {block['rewritten']} rewritten in place" + _v3_summary(block))
    s = head + f" · {block['founded']} founded · {block['unfounded']} unfounded"
    if block.get("founded_past_end"):
        s += f" ({block['founded_past_end']} founded by an index one past the end)"
    if block["receipted"] is not None:
        s += (f" · receipted: {block['receipted']['deleted']} deleted, "
              f"{block['receipted']['flattened']} flattened")
    s += f" · {block['rewritten']} rewritten in place ({block['rewritten_unfounded']} without a finding)"
    return s + _v3_summary(block)


def _v3_summary(block: dict[str, Any]) -> str:
    """The reported-only v3 annotations (#3223, #3037), where there are any."""
    s = ""
    if block["relocated_candidate"]:
        s += (f" · {block['relocated_candidate']} deleted with a relocation candidate"
              f" ({block['relocated_candidate_standing']} into source_caveats)")
    if block["flattened_into_source_caveats"]:
        s += f" · {block['flattened_into_source_caveats']} flattened into source_caveats only"
    review = block.get("source_review")
    if review is not None and review.get("deleted") is not None:
        s += (f" · source review: {review['deleted']['supported']} deleted reviewed supported"
              + (f", {review['unfounded_supported']} of them unfounded" if review["unfounded_supported"] is not None
                 else ""))
    elif review is not None:
        s += f" · source review not read: {review['reason']}"
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


def evidence_snapshot(core_dir: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """(snapshot, pin) from the native and direct arms' frozen original
    (#3037): `{method}_core/{label}/evidence/original_full.yaml`, written
    once, before the audit, by the evidence protocol's freeze command.
    None, None where there is none. The file is named for no project, so a
    label directory holding more than one project's record makes it no one
    record's: unusable, and said so."""
    path = core_dir / "evidence" / "original_full.yaml"
    if not path.exists():
        return None, None
    records = sorted(core_dir.glob("*_provenance.yaml"))
    if len(records) > 1:
        return None, {"path": str(path), "sha256": None, "state": "unusable", "source": "evidence",
                      "reason": f"{len(records)} records share this label directory, so its unprefixed "
                                "evidence/original_full.yaml belongs to none of them"}
    try:
        raw = path.read_bytes()
        doc = yaml.safe_load(raw.decode("utf-8"))
        if not isinstance(doc, dict) or not doc:
            raise ValueError("snapshot is not a nonempty mapping")
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
        return None, {"path": str(path), "sha256": None, "state": "unusable", "source": "evidence",
                      "reason": str(exc).splitlines()[0] if str(exc) else type(exc).__name__}
    return doc, {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "state": "usable",
                 "source": "evidence"}


def _evidence_audit(core_dir: Path) -> tuple[str, Path | None, Any, str | None]:
    """(state, path, parsed, why) for the evidence protocol's `evidence/audit.json`."""
    path = core_dir / "evidence" / "audit.json"
    if not path.exists():
        return "absent", None, None, None
    try:
        doc = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return "unusable", path, None, f"{type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else ''}"
    if not isinstance(doc, dict):
        return "unusable", path, None, f"the document is a {type(doc).__name__}, not a mapping"
    return "usable", path, doc, None


def for_record(provenance: Path, *, record: dict[str, Any] | None = None) -> dict[str, Any]:
    """The block for one run on disk. Read-only: nothing under the run's
    directories is written, and the provenance record is not changed.

    The phase-1 snapshot is the API runner's `intermediate/{P}_full.yaml`;
    where a run has none, the native/direct `evidence/original_full.yaml`,
    read with `evidence/audit.json` and no phase outputs (#3037)."""
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
    evidence = False
    if original is None and pin is None:
        original, pin = evidence_snapshot(core_dir)
        evidence = pin is not None
    if original is None:
        why = (pin or {}).get("reason")
        block = _unchecked(f"the phase-1 snapshot is present but not usable ({why})" if why else
                           "no phase-1 snapshot: the removals cannot be read against what phase 1 "
                           "wrote (#899)")
        block["artifacts"] = {"phase1_snapshot": pin}
        return block
    if evidence:
        # The native and direct arms reconcile in session and snapshot no
        # phase output: nothing to attribute a removal to (#3037).
        a_state, a_path, audit, a_why = _evidence_audit(core_dir)
    else:
        a_state, a_path, audit, a_why = _phase_output(core_dir, project, f"{project}_audit.json", record)
    stages: list[tuple[str, dict[str, Any] | None]] = []
    phases: list[dict[str, Any]] = []
    for name in ([] if evidence else
                 ["reconcile_full", *(f"repair_full_r{n}" for n in repair_rounds(core_dir, project, record))]):
        state, path, doc, why = _phase_output(core_dir, project, f"{project}_{name}.yaml", record)
        # A missing output is a gap like an unreadable one (#3152), not a
        # phase to skip: the runner snapshots every phase it runs, and runs
        # reconcile_full always, so the output was lost, and attributing
        # across the gap would name a later phase for a value an earlier
        # one removed. Its None leaves the removals unattributed.
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
                     receipt=receipt, intermediates=None if evidence else stages,
                     audit_unread=(a_why or "unreadable") if a_state == "unusable" else None,
                     snapshot_sha256=(pin or {}).get("sha256"))
    block["artifacts"] = {
        "phase1_snapshot": pin, "final": str(paths["full"]),
        "audit": {"state": a_state, "path": str(a_path) if a_path else None,
                  **({"reason": a_why} if a_why else {})},
        "receipt": {"state": r_state, "path": str(receipt_file) if r_state != "absent" else None},
        "phases": phases,
        **({"phases_reason": "the native/direct evidence protocol snapshots no phase output"} if evidence else {}),
    }
    return block
