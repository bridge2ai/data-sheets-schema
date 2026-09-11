"""Check a reconciliation report against the record and the schema (#546).

A reconciliation report is the human-readable audit trail — the artifact a
reviewer reads *instead of* diffing YAML. Nothing checked it against anything,
and in the 2026-08-13 v4 arm three of twelve reports asserted:

    **Action:** the `distributions` block was removed from the core record in
    its entirety.

on records that retained ten, ten and three entries. All three justified it the
same way:

    No such slot appears in the schema digest's inventory for
    `Dataset`/`CoreDataset`.

`distributions` is a declared `CoreDataset` slot with range `CoreDistribution`,
and every key those reports listed is a declared `CoreDistribution` slot. The
audit reasoned from a false statement about the schema toward a removal, and
then did not perform it. The records are correct by accident.

Both claims are decidable: one against the record, one against a schema that is
machine-readable and right there.

## Precision over recall, deliberately

Only two claim forms are read, because they are the two whose subject is
unambiguous:

- a table row whose change cell says the slot was removed —
  ``| `distributions` | **Removed** | Not declared anywhere in the schema. |``
- an ``**Action:**`` line naming its subject in backticks.

A first version read every sentence containing a removal verb and produced 122
findings across the 12 v4 reports, most of them wrong: ``citation prose removed
from core `notes` `` was read as removing `notes`, ``neither was deleted`` as a
removal, and markdown table cells bled into their neighbours. A checker whose
output a reader learns to ignore is how the reports got into this state; it
would be a poor way to fix it.

So there are real claims here this will not check — "The four MuSIC-pipeline
objects were removed" names no slot in backticks and is skipped. The count of
what was skipped is reported rather than left silent.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from data_sheets_schema.schema_view import shared_view

#: A change cell asserting the slot is gone. Anchored to the cell, so a reason
#: cell mentioning removal cannot trigger it.
_CELL_REMOVED = re.compile(
    r"^\W*(?:\*\*)?(?:removed|deleted|dropped)\b", re.I)

#: An `**Action:**` line that asserts a removal. Negations are excluded here
#: rather than filtered later: "neither was deleted" is a claim that nothing
#: happened, and reading it as a removal is how the first version got CHORUS
#: rep1 wrong.
#: Reports label their outcome paragraph inconsistently — `**Action:**`,
#: `**Disposition — changed.**`, `**Resolution:**` all appear across the 12 v4
#: reports. Matching only the first missed two of the three false removals
#: #546 names.
_ACTION = re.compile(r"^\s*(?:[-*]\s*)?\*\*(?:action|disposition|resolution)"
                     r"\b[^*]*\*\*:?\s*(?P<body>.*)$", re.I | re.S)
_REMOVAL_VERB = re.compile(r"\b(?:was|were|have been|has been)\s+"
                           r"(?:removed|deleted|dropped)\b", re.I)
_NEGATED = re.compile(r"\b(?:neither|nor|not|never|no)\b[^.]{0,40}"
                      r"\b(?:removed|deleted|dropped)\b", re.I)

#: A claim that something is not in the schema. Decidable, and in every v4
#: instance false.
# "does not exist/appear" counts only with a schema-shaped object: "does not
# appear in the reconciled description" is a sentence about a value, and read
# without that guard it made the v7 API canary's only report finding (#757).
_ABSENT_FROM_SCHEMA = re.compile(
    r"\bnot declared\b|\bno such slot\b|"
    # up to a short adjective run before the noun: "in the supplied schema
    # digest", "in the declared `Dataset` slot inventory" (#760)
    r"\bdoes not (?:exist|appear) (?:in|on) (?:[\w`\-]+ ){0,6}?"
    r"(?:schema|class|inventory|digest)\b|"
    r"\bnot a (?:declared|valid|recognised|recognized) slot\b|"
    r"\bnot in the (?:inventory|schema)\b|\bnot attested (?:keys?|slots?)\b|"
    r"\bappears? to have been invented\b", re.I)

_TICKED = re.compile(r"`([A-Za-z_][\w]*(?:\[(?:\d+|\*)\])?"
                     r"(?:\.[\w]+(?:\[(?:\d+|\*)\])?)*)`")
#: A backticked name in this position is a container or a destination, not the
#: thing removed: "citation prose removed from core `notes`".
#: A name after a preposition is a place, not a casualty — with up to two
#: words of the noun phrase between ("in the existing `funders` block",
#: #1175 Codex review, M1), which stop at a clause boundary or a verb this
#: reader knows, so the preposition of an earlier clause does not reach.
_OBLIQUE = re.compile(r"\b(?:from|into|to|in|on|within|onto|under|beside|"
                      r"alongside)\s+(?:the\s+|core\s+|full\s+)*"
                      r"(?:(?!(?:was|were|is|are|has|have|had|will|removed|deleted|dropped|remains?)\b)"
                      r"[A-Za-z][\w-]*\s+){0,2}`")
#: The head noun after a backticked name decides what was removed. "the
#: `distributions` block was removed" removes the slot; "the unfounded
#: `source_caveats` claim was removed" removes a sentence of prose from inside
#: a slot that stays. Only the second kind is excluded — `block`, `slot`,
#: `entry` and a bare name all mean the slot itself.
_CONTENT_NOUN = re.compile(
    r"^\s*(?:claim|prose|note|notes|sentence|statement|assertion|text|"
    r"wording|caveat|disclaimer|phrase|language|description|dates?|values?|"
    r"keys?|fields?|reference|prefix)\b", re.I)


def _cells(line: str) -> list[str] | None:
    """The cells of a markdown table row, or None if this is not one."""
    if not line.lstrip().startswith("|"):
        return None
    parts = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(parts) < 2 or all(set(c) <= set("-: ") for c in parts):
        return None                                   # separator row
    return parts


def resolve(data: Any, path: str) -> tuple[bool, Any]:
    """(present, value) for a dotted/indexed path like `instances[0].counts`.

    Reports name nested slots as often as top-level ones. `[*]` means "any
    element", so `creators[*].affiliations` is present when any creator has it
    — a report claiming that was removed is contradicted by one survivor.
    """
    parts = re.findall(r"[\w]+|\[\d+\]|\[\*\]", path)

    def walk(cur: Any, i: int) -> tuple[bool, Any]:
        if i == len(parts):
            return True, cur
        part = parts[i]
        if part == "[*]":
            if not isinstance(cur, list):
                return False, None
            for item in cur:
                ok, val = walk(item, i + 1)
                if ok and _populated(val):
                    return True, val
            return False, None
        if part.startswith("["):
            idx = int(part[1:-1])
            if not isinstance(cur, list) or idx >= len(cur):
                return False, None
            return walk(cur[idx], i + 1)
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        return walk(cur[part], i + 1)

    return walk(data, 0)


def _populated(value: Any) -> bool:
    """A slot present but empty is removed for the purpose a report describes.

    `distributions: []` is not a ten-entry block, and calling that a false
    claim would be pedantry that buries the real finding.
    """
    return value not in (None, [], {}, "")


def _target(text: str) -> str:
    """Which record a claim is about: 'core', 'full' or 'either'.

    'either' means the claim named no record. Those are read against the core
    record: reconciliation exists to produce core from full, and a slot the
    full record legitimately keeps while core drops it is the normal outcome,
    not a false claim. Reading them against both instead was too weak to see
    AI_READI rep1, whose `distributions` block only ever existed in core — the
    full record's absence of it made the claim look satisfied.
    """
    low = text.lower()
    core = "core record" in low or "core file" in low or "from core" in low
    full = "full record" in low or "full file" in low or "from full" in low
    if core and not full:
        return "core"
    if full and not core:
        return "full"
    if core and full:
        # Named both, so both must have performed it. This fell into `either`
        # and was read against core alone, so "removed from the full and core
        # records" passed while the full record still held it (#578) — which is
        # the very direction #566 is about.
        return "both"
    return "either"


def _named(text: str) -> list[str]:
    """Backticked names in `text` that denote a slot, not a place or a phrase.

    Shared by prose and table cells. A cell reading "Dataverse Subject in
    `keywords`" names where something was removed *from*, and one reading
    "`collection_timeframes` dates" names what inside the slot went — neither
    is a claim that the slot is gone.
    """
    out = []
    for m in _TICKED.finditer(text):
        if _OBLIQUE.search(text[max(0, m.start() - 30):m.start()] + "`"):
            continue
        if _CONTENT_NOUN.match(text[m.end():m.end() + 24]):
            continue
        out.append(m.group(1))
    return out


def _subjects(body: str) -> list[str]:
    """Backticked names that are the thing removed.

    Two rules, both learned from false positives on the v4 reports:

    - The name must come *before* the removal verb. "the block was removed. Its
      content was already represented by the declared `distribution_formats`
      slot, which was retained" names the slot that survived, not the one that
      went.
    - It must not sit in an oblique phrase: "citation prose removed from core
      `notes`" removes prose, not `notes`.

    A removal whose subject is only "the slot" or "the block" yields nothing,
    and is counted as unnamed rather than guessed at.
    """
    verb = _REMOVAL_VERB.search(body)
    if not verb:
        return []
    # The sentence containing the verb, not the whole paragraph. Reading the
    # paragraph let "`id` is now `https://ror.org/…`" three sentences earlier
    # become the subject of a removal further down.
    start = max((body.rfind(p, 0, verb.start()) for p in (". ", "! ", "? ")),
                default=-1)
    return _named(body[start + 1:verb.start()])


#: A removal whose subject is a bare noun — "the block was removed". Its slot
#: is named in the section heading and nowhere else, which is how AI_READI
#: rep1's false removal escaped a first version that only read the sentence.
# `object`/`objects`/`entries` are not here (#782): "the second object was
# removed" removes an element of the heading's slot, not the slot, and the
# slot's presence afterwards proves nothing about the claim.
_BARE_SUBJECT = re.compile(r"\b(?:the|this|these|those|that)\s+(?:\w+\s+){0,2}"
                           r"(?:block|slot|slots|array|"
                           r"list)\s+(?:was|were|have been|has been)\s+"
                           r"(?:removed|deleted|dropped)\b", re.I)
#: A removal *from inside* a slot's entries — "`description` was removed
#: from all eleven objects" — removes a nested field the checker cannot
#: resolve without knowing the parent; counted as unnamed, never tested at
#: the root (#782).
_ELEMENT_REMOVAL = re.compile(
    r"\b(?:removed|deleted|dropped)\s+from\s+(?:all|each|every|both|the|its|their|\w+\s+of\s+the|\d+|"
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b)?[^.;]{0,40}?"
    r"\b(?:objects?|entries|entry|items?|elements?)\b", re.I)


def _heading_fallback(body: str, heading_slots: list[str]) -> list[str]:
    """The heading's slot, but only when the sentence names none of its own.

    Guarded twice. If the sentence contains any backticked name, that name was
    considered and rejected — "the unfounded `source_caveats` claim was
    removed" removes prose, and reaching past it to the heading would
    resurrect exactly the false positive the content-noun rule just removed.
    And the subject must actually be a bare noun, so a sentence about
    something else entirely cannot borrow the heading's subject.
    """
    verb = _REMOVAL_VERB.search(body)
    if not verb or _TICKED.search(body[:verb.end()]):
        return []
    return heading_slots if _BARE_SUBJECT.search(body) else []


def _describe(value: Any) -> str:
    if isinstance(value, list):
        return f"{len(value)} entr{'y' if len(value) == 1 else 'ies'}"
    return "a value"


#: The dispositions table the v8 report phase ends with (#929): a header row
#: with a `disposition` column, one row per slot, the disposition one of
#: these. `removed` rows are read by the removal check above (a table cell
#: matching `_CELL_REMOVED`); the rest are claims of presence, which no
#: earlier report form let the checker test (#914: AI_READI v7 rep3 claimed
#: `extension_mechanism` was retained when neither record carried it).
_PRESENCE_DISPOSITIONS = {"retained", "kept", "unchanged", "left as-is", "left as is",
                          "changed", "amended", "corrected", "added"}
_DISPOSITION = re.compile(r"^\W*(?:\*\*)?(removed|deleted|dropped|retained|kept|unchanged|"
                          r"left as-is|left as is|changed|amended|corrected|added)\b", re.I)

#: A retention claim in prose (#1054): "the legal analysis remains in
#: `regulatory_restrictions.regulatory_restrictions`" is the table's
#: `retained` row said in a sentence, and the first four instrument versions
#: read only the table and the removal verbs. The path is the backticked one
#: right after the verb phrase; a negated clause ("no longer remains in") is
#: not a retention.
_PROSE_RETAINED = re.compile(
    r"\b(?:remains?|stays?|is (?:kept|retained|left|preserved)|"
    r"are (?:kept|retained|left|preserved)|(?:was|were) (?:kept|retained|left|preserved))\s+"
    r"(?:in|under|at|on)\s+`([A-Za-z_][\w]*(?:\[(?:\d+|\*)\])?(?:\.[A-Za-z_][\w]*(?:\[(?:\d+|\*)\])?)*)`",
    re.I)
#: A negation in the clause before the verb turns the sentence into the
#: opposite of a retention ("nothing remains in `errata`", "it never
#: remains in `notes`", "no longer kept in `x`"; #1175 review S2).
_NEGATED_BEFORE = re.compile(r"\b(?:no longer|not|never|nothing|neither|none)\b[^.;:,()—-]{0,12}$", re.I)
#: A negation anywhere in the verb's own clause: "No value remains in
#: `errata`" (#1175 Codex review, M7). The clause is the last one
#: `_CLAUSE_SPLIT` yields, so "names no committee, so … retained under
#: `notes`" is a claim (#1175 round 2, S1).
_NEGATION = re.compile(r"\b(?:no|not|never|neither|nor|none|nothing)\b", re.I)


def _negated_clause(before: str) -> bool:
    """Is the retention verb's own clause negated? The window stops at the
    previous sentence (#1175 round 7, M3): without that it inherited the
    negation of the sentence before and dropped 19 genuine claims, every
    one of the form "… no DPIA …. The substantive content is retained
    under `x`"."""
    sentence = re.split(r"[.!?]\s", before)[-1]
    return bool(_NEGATION.search(_CLAUSE_SPLIT.split(sentence)[-1]))
#: Literals a `remains at`/`remains in` phrase can name that are not slots
#: ("the flag remains at `false`", #1175 Codex review, M7).
_NOT_A_SLOT = frozenset({"true", "false", "null", "none", "nan", "n_a", "na", "yes", "no", "unknown"})
#: A slot path is snake_case segments; `HIPAA` and `CoreDataset` are not.
_SLOT_PATH = re.compile(r"[a-z][a-z0-9_]*(?:\[(?:\d+|\*)\])?(?:\.[a-z][a-z0-9_]*(?:\[(?:\d+|\*)\])?)*")
#: The weak signal that a report *records* a removal, for suppressing the
#: snapshot finding only (#1175 review S1) — never for a removal claim,
#: where precision matters: a bare backticked slot name in a sentence that
#: carries a removal word. "### 4.7 Removed `errata`", "- `errata`
#: **removed**", "`conforms_to_standard` is absent from both records". The
#: names are read by `_named`, so a destination ("recorded in `errata`")
#: is not a casualty, a sentence about the core alone records nothing
#: about the full record, and no table line is read (#1175 round 2, M1).
#: The present-tense forms are here for the weak signal's sake (#1175
#: round 8, M1): "Both records now omit `citation`" records a removal as
#: plainly as "`citation` was removed", and reading only past participles
#: listed it as unrecorded.
_REMOVAL_WORD = re.compile(r"\b(?:remove[sd]?|delete[sd]?|drops?|dropped|omits?|omitted|"
                           r"strips?|stripped|absent|withdraws?|withdrawn)\b", re.I)
#: A removal word that is negated, hypothetical or contrasted records no
#: removal (#1175 Codex review, M1): "was retained rather than removed",
#: "was never removed", "if `x` is removed, explain why". Order decides
#: (#1175 round 7, M2): the token must sit *before* the removal word, or
#: "was removed, not renamed" and "removed rather than guessed" — 21
#: corpus names — are voided by their own contrast.
#: `nothing` and `none` are here and bare `no` is not (#1175 round 9, S2):
#: "None of these is a slot removed from a record: `counts` and …" denies a
#: removal and recorded one, while 19 of the 20 corpus clauses where `no`
#: precedes the removal word are removals — "`collection_type` has no
#: `CoreDistribution` counterpart and is dropped" — which bare `no` would
#: void. `rewritten` and `alternative` are the present tense's cost (round
#: 9, S1): "`special_protections` was rewritten to drop the superseded
#: clause" leaves the slot in place, and "the alternative is to drop five
#: well-evidenced relations" is a road not taken.
_REMOVAL_VOID = re.compile(r"\b(?:rather than|instead of|not|never|nor|neither|no longer|nothing|none|"
                           r"without|rewritten|alternative|"
                           r"if|whether|unless|would|should|could|may|might|must|please|explain)\b", re.I)
#: A present-tense removal word used as a noun: "The intentional projection
#: drops are unchanged" (#1175 round 9, S1). Only the -s forms, and only
#: before a verb: "the slots removed are `a` and `b`" is a real removal, so
#: a past participle before `are` must not be voided.
_REMOVAL_AS_NOUN = re.compile(r"\b(?:removes|deletes|drops|omits|strips|withdraws)\s+"
                              r"(?:are|is|were|was)\b", re.I)


def _removal_voided(clause: str) -> bool:
    m = _REMOVAL_WORD.search(clause)
    if not m:
        return False
    return bool(_REMOVAL_VOID.search(clause[:m.start()]) or _REMOVAL_AS_NOUN.search(clause))
#: A clause boundary: the weak signal reads only the clause the removal
#: word sits in, so "`errata` was removed because `funders` remains valid"
#: records `errata` and not `funders` (#1175 Codex review, M1).
#: A clause boundary. Not an em dash or a colon: in these reports both
#: join a slot to its disposition — "### 2.1 `publisher` — removed",
#: "`errata`: removed", "- **Removed:** `publisher`" — and splitting on
#: them severed the subject from the removal word in 197 of the 301
#: reports (#1175 round 7, M1).
_CLAUSE_SPLIT = re.compile(r"\s*(?:;|,\s*(?:but|while|whereas|although|though|because|since|so|and then)\b|"
                           r"\s(?:but|while|whereas|although|though|because|since)\s|"
                           # a relative clause is about its antecedent, not about a
                           # name earlier in the sentence: "`funders` contains
                           # identifiers that were removed" (Codex review, M1)
                           r"\s(?:that|which|whose|who)\s)\s*", re.I)
#: After a list the removal word must follow closely, in the same clause,
#: for the list to be its casualties: at most a few words, none of them a
#: retention verb, a negation or "rather than" (#1175 round 5, M1).
_CASUALTY_TAIL = re.compile(r"(?:\s+(?!(?:remains?|stays?|retained|kept|carried|rather|not|never|neither|nor)\b)[\w'\-]+){0,4}\s+"
                            r"(?:were|was|are|is|have been|has been|be|being|get|got)?\s*"
                            r"(?:removed|deleted|dropped|omitted|stripped|withdrawn)\b", re.I)
#: "recorded in `a`, `b` and `c`": every backticked name in the list after
#: the preposition is a destination.
_DESTINATION_LIST = re.compile(r"\b(?:from|into|to|in|on|within|onto|under|beside|alongside)\s+(?:the\s+|core\s+|full\s+)*"
                               r"`[^`]+`(?:\s*,\s*`[^`]+`)*(?:\s*,?\s*(?:and|or)\s+`[^`]+`)?", re.I)

#: Top-level keys a snapshot diff does not report (#1054): the class
#: declarations and the commentary slots the receipt denominator also
#: excludes (#722), which reconciliation rewrites freely.
_SNAPSHOT_EXEMPT = frozenset({"conforms_to_schema", "conforms_to_class", "notes", "source_caveats"})


#: The checker's own version (#996). The block pins the report, both records
#: and the schema by hash, but the checker moved under #914, #929, #962 and
#: #990 with nothing recording which reading produced a block; everything
#: before this constant is v1.
REPORT_CLAIMS_INSTRUMENT = ("v5 (#1054): with the phase-1 snapshot on disk, a top-level slot the "
                            "snapshot carried that the final full record does not, with no `removed` "
                            "row or removal sentence naming it, is `removal_not_recorded`; a prose "
                            "retention claim (`remains in`, `stays in`, `is kept in`, `is retained "
                            "in` a backticked path) is read like a retained row; "
                            "v4 (#1122): `rows_by_record` tallies the dispositions rows by "
                            "their record column — `full`, `core`, `both`, `either` for an empty "
                            "cell, `no_record_column` for a table with no such column, `invalid` "
                            "for anything else — so a `both` row wrongly flipped to `full`, "
                            "which the gate cannot see (a `full` row resolves against the full "
                            "record only), is countable from the block; v3 (#1022, #1046): a "
                            "schema claim that names its own scope — the core schema, the full "
                            "schema, a class — is resolved against that scope only, not against "
                            "every class; v2 (#990): a finding on a `both` row names when the "
                            "core class declares no such slot; `claims_core_cannot_hold` counts "
                            "them")

#: The values `disposition_rows` can read off a row's `record` cell, in the
#: order the block lists them. Fixed keys, zero-filled, so two blocks compare
#: without a missing key standing for a zero (#1122).
RECORD_COLUMN_VALUES = ("full", "core", "both", "either", "no_record_column", "invalid")


def rows_by_record(rows: list[dict[str, str]]) -> dict[str, int]:
    """How many dispositions rows name each record (#1122).

    `either` is an empty (or missing) cell in a table that has a record
    column, `no_record_column` a row of a table with no such column — a
    report format that names no record (two v2 reports name one; the two
    non-v8 reports whose rows fall here are a v4 and a bare-condition one),
    which is "not measurable" rather than "no `both` rows" (#1139 review, S2) —
    and `invalid` anything but `full`, `core` or `both`; exactly as
    `disposition_rows` reads them, and the values sum to `disposition_rows`.
    """
    counts = {value: 0 for value in RECORD_COLUMN_VALUES}
    for row in rows:
        counts[row["record"]] += 1
    return counts

#: A schema claim can name the inventory it is about, and the instruction the
#: v8 report phase follows asks for exactly that sentence: "`splits` and
#: `participant_privacy` are not declared by the core schema and appear only
#: in the full record." Resolving the slot against every class turned true
#: sentences of that shape into `false_schema_claim` findings, and two
#: regates were fed them — VOICE `2026-09-04f_rep1`, whose two findings were
#: both false, and CM4AI `2026-09-04g_rep3`, where two of four were (#1022,
#: #1046). The scope is read from the claim's own words.
_CORE_SCOPE = re.compile(
    r"\bcore\s+(?:schema|record|class|inventory|digest|dataset|"
    r"projection|view|subset)\b|"
    r"\bCoreDataset\b|\bCoreDistribution\b", re.I)
_FULL_SCOPE = re.compile(
    r"\bfull\s+(?:schema|record|class|inventory|digest|dataset|"
    r"projection|view)\b", re.I)
#: A claim that ranges over the classes itself is not scoped to one of them,
#: whichever class it happens to name in passing: "no such slot appears in the
#: inventory for `Dataset`, and `md5` and `path` are not attested keys on **any
#: listed range class**" is two claims, and the second is about all of them.
_ANY_CLASS = re.compile(r"\bany (?:listed |declared |named )?"
                        r"(?:range )?class(?:es)?\b|\bany of the classes\b|"
                        r"\bno class\b|\bany schema\b", re.I)

#: A bare class name is not a scope signal. "in the inventory for `Dataset`"
#: reads as one, and the sentence it appears in is generally about several
#: classes at once; only the words "core" and "full" qualifying a schema, a
#: record or an inventory are taken as the claim naming its own scope.


#: Clause boundaries. The scope word has to sit in the same clause as the
#: "not declared" phrase, because a reconciliation report says "the full
#: record" in passing constantly (#1087). Read over the whole sentence, one
#: v5 VOICE report's trailing clause — "…and stated content in five slots
#: that the full record did not state" — scoped a `distributions` claim in
#: the *first* clause to `Dataset`, where `distributions` is not declared,
#: and silenced the one finding #546 exists to make. `full` resolves to
#: `Dataset` alone, so every subject of #546 — `distributions`, `path`,
#: `md5`, `format`, `media_type`, all `CoreDataset` or `CoreDistribution` —
#: was one stray boilerplate clause away from being unreportable.
_CLAUSE = re.compile(r"[;,]\s+")


def _claim_scope(claim: str, classes: set[str]) -> tuple[set[str], str]:
    """The classes a schema claim is about, and how that was decided.

    The scope is read from the clause carrying the "not declared" phrase, not
    from the sentence: a clause elsewhere in the sentence is about something
    else, and taking it as the scope silences true findings.

    A clause naming both scopes — "not declared by the core schema and appears
    only in the full record" — is about the core one: the full mention is
    where the slot *is*, the clause's own contrast, not a second inventory to
    check it against.
    """
    core = {c for c in classes if c.startswith("Core")}
    full = classes - core
    where = claim
    for clause in _CLAUSE.split(claim):
        if _ABSENT_FROM_SCHEMA.search(clause):
            where = clause
            break
    if _ANY_CLASS.search(where):
        return classes, "unscoped"
    if core and _CORE_SCOPE.search(where):
        return core, "core"
    if full and _FULL_SCOPE.search(where):
        return full, "full"
    return classes, "unscoped"


def _path_steps(path: str) -> list[str]:
    """`resources[0].file_collections[1].id` → the slot names, in order.
    Indices are dropped: a list index says nothing about what a class
    declares."""
    return [s for s in re.split(r"[.\[]", path) if s and not s.rstrip("]").isdigit()]


def _core_declares(path: str, declared: dict[str, set[str]],
                   ranges: dict[str, dict[str, str | None]] | None = None) -> bool:
    """Whether the core class can carry `path`, step by step.

    Root-only until #994, on the reasoning that every class-ranged slot
    CoreDataset shares with Dataset has the same range. Two do not.
    `resources` is ranged `Dataset` on the full and `CoreDataset` on the
    core, so it recurses into a smaller class — `resources[0].subsets` is a
    path the full can hold and the core cannot — and a derived core carries
    `distributions`, ranged `CoreDistribution`, where the full carries
    `distribution_formats`. A finding on a `both` row under either was
    still correct, because the row is checked against the core record
    literally; what it could not say was that the core *could not* carry
    the value, which is the difference between "name `full`" and "the two
    records disagree".

    With `ranges` — class name to slot name to the range class it induces,
    from `declared_ranges` — each step is resolved against the class the
    step before it lands in. Without it the root test stands, so a caller
    that has not been updated keeps the old answer rather than a wrong one.
    A step whose range is not a class in the core schema ends the walk: a
    scalar cannot carry a slot, so a deeper path is one the core cannot
    hold.

    `declared` without a `CoreDataset` entry is a broken core schema:
    `check_report` refuses it up front, since a checker that carried on
    would drop the cause from every such finding with no signal (#993).
    """
    if "CoreDataset" not in declared:
        raise ValueError("declared slots carry no `CoreDataset` class; "
                         "the core schema could not be read")
    steps = _path_steps(path)
    if not steps:
        return False
    if not ranges:
        return steps[0] in declared["CoreDataset"]
    cls = "CoreDataset"
    for i, step in enumerate(steps):
        here = ranges.get(cls)
        if here is None:                       # a class the core schema does not define
            return False
        if step not in here:
            return False
        if i + 1 == len(steps):
            return True
        cls = here[step] or ""                 # a scalar range ends the walk
    return True


def _core_cannot_hold_cause(path: str, declared: dict[str, set[str]],
                            ranges: dict[str, dict[str, str | None]] | None) -> str:
    """The clause naming which step of `path` the core cannot carry (#994).

    Root-only phrasing where there are no ranges, so the sentence never
    claims a precision the walk did not have."""
    steps = _path_steps(path)
    if not ranges or len(steps) < 2:
        root = steps[0] if steps else path
        return (f"; the core class declares no `{root}` slot, so the row "
                f"must name `full`")
    cls = "CoreDataset"
    for i, step in enumerate(steps):
        here = ranges.get(cls)
        if here is None:
            return (f"; the core schema defines no `{cls}` class, so the row "
                    f"must name `full`")
        if step not in here:
            where = "the core class" if i == 0 else f"`{cls}`"
            return (f"; {where} declares no `{step}` slot, so the row must "
                    f"name `full`")
        cls = here[step] or ""
    return (f"; the core class cannot carry `{path}`, so the row must name `full`")


def _header_cells(cells: list[str]) -> list[str]:
    """Header cells as the strict reader compares them: lower-cased, with
    markdown decoration (`**Slot**`, `_Slot_`, `Slot:`) stripped (#1175
    round 5, S1) — one rule for both readers (round 5, M2)."""
    return [c.strip().strip("*_").strip().rstrip(":").strip().lower() for c in cells]


def _is_dispositions_header(cells: list[str] | None) -> bool:
    if cells is None:
        return False
    low = _header_cells(cells)
    return "disposition" in low and "slot" in low


def _dispositions_table_lines(text: str) -> set[str]:
    """The stripped lines of every table whose header `disposition_rows`
    recognises — header, rule and every row to the next header or the
    first non-`|` line, parseable or not (#1175 round 3, M1/S2; round 4,
    M1/S4). Keyed on the header, not on the rows that parsed: a
    recognised table none of whose rows the strict reader can read is
    still the strict reader's (round 4, M1 — "| `errata` | Reviewed |
    both | … slot kept |" is nobody's removal claim), and a second header
    written directly under a table starts another table, which is excluded
    only if it is recognised too (S4). A table the strict reader does not
    recognise ("| core | `distributions` | removed |") stays with the
    generic scan, and a dispositions-shaped table with no heading is still
    the strict reader's. A header is any row the strict reader's own test
    recognises — a separator row is not required (round 5, M2: the strict
    reader parses a separator-less table, so the exclusion must cover it)."""
    out: set[str] = set()
    recognised = False
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            recognised = False
            continue
        cells = _cells(line)
        if _is_dispositions_header(cells):
            recognised = True
        elif cells is not None and recognised and _cells_look_like_a_header(cells):
            recognised = False                      # another table's header, not a dispositions one
        if recognised:
            out.add(line.strip())
    return out


def _cells_look_like_a_header(cells: list[str]) -> bool:
    """A row whose every cell is a bare capitalised or lower-case word with
    no backtick, digit or disposition word — the shape a header takes and a
    dispositions row never does."""
    return all(re.fullmatch(r"[A-Za-z][A-Za-z ]{0,30}", c.strip("*_ ").rstrip(":")) for c in cells) and not any(
        _DISPOSITION.match(c) for c in cells)


def disposition_rows(text: str) -> list[dict[str, str]]:
    """Rows of every table whose header names `slot` and `disposition` columns.

    A slot is a backticked name read through `_named` (so "moved into
    `notes`" names no slot), or a bare path that starts with a letter (a
    numbered finding table whose column happens to be called Disposition
    yields nothing, #962). For `changed`/`added` rows written as
    "`old` -> `new`" the claim is about the destination. The `record` cell
    must be exactly `full`, `core` or `both`; empty reads as `either`, a
    table with no record column reads `no_record_column` (#1122), and
    anything else is `invalid`, which the checker counts as unnamed rather
    than guess at.
    """
    rows: list[dict[str, str]] = []
    header: dict[str, int] | None = None
    for line in text.splitlines():
        cells = _cells(line)
        if cells is None:
            if line.lstrip().startswith("|"):
                continue                      # the separator row keeps the header
            header = None
            continue
        if _is_dispositions_header(cells):
            # Both columns, or it is some other table with a Disposition
            # column — a numbered finding table, say (#962) — whose rows are
            # not claims about slots. A second recognised header starts its
            # own table: keeping the first's column map decoded the second's
            # rows by the wrong columns (#1175 Codex review, M5).
            header = {name: i for i, name in enumerate(_header_cells(cells))}
            continue
        if header is None:
            continue
        d = cells[header["disposition"]] if header["disposition"] < len(cells) else ""
        m = _DISPOSITION.match(d)
        if not m:
            continue
        slot_col = header.get("slot", 0)
        slot_cell = cells[slot_col] if slot_col < len(cells) else cells[0]
        names = _named(slot_cell)
        if not names and re.fullmatch(r"[A-Za-z_][\w.\[\]]*", slot_cell.strip()):
            names = [slot_cell.strip()]
        disposition = m.group(1).lower()
        if len(names) > 1 and disposition in ("changed", "amended", "corrected", "added"):
            names = names[-1:]
        # The column's presence is kept out of the value (#1139 review, R1):
        # a cell that literally reads `no_record_column` is a value the
        # checker will not guess at, like any other, and stays `invalid`.
        has_col = "record" in header
        record = cells[header["record"]].strip().lower() if has_col and header["record"] < len(cells) else ""
        if record not in ("full", "core", "both"):
            record = "no_record_column" if not has_col else ("either" if not record else "invalid")
        for name in names:
            rows.append({"slot": name, "disposition": disposition, "record": record,
                         "line": line.strip()})
    return rows


def check_report(report: Path, full: dict, core: dict,
                 declared: dict[str, set[str]],
                 snapshot: dict | None = None,
                 dispositions_expected: bool | None = None,
                 ranges: dict[str, dict[str, str | None]] | None = None) -> dict[str, Any]:
    """Findings, plus what was skipped.

    `declared` maps a class name to its induced slot names — passed in so a
    caller checking twelve reports builds the SchemaView once. `ranges`
    (`declared_ranges`) is the same for the range class each core slot
    induces, and is what lets a `both` row on a nested path say which step
    the core cannot carry rather than only which root (#994). It is not
    defaulted from the schema: `declared` and `ranges` must describe one
    core schema, and filling one from disk while the caller supplied the
    other would judge a synthetic slot map against the real classes.
    Without it the root test stands, which is what every caller had before
    #994. `snapshot` is
    the phase-1 record (`intermediate/{P}_full.yaml`, #758) where the runner
    kept one: with it, a top-level slot the snapshot carried and the final
    record does not, with no row or sentence recording the removal, is a
    deterministic finding that needs no claim parsing (#1054, instrument
    v5). Without it — the agentic path, a run before #758 — that check is
    reported as not made (`snapshot_checked: false`), never as clean.
    `dispositions_expected` is the run's own statement that its report
    phase was asked for the table (`inputs.dispositions_expected`, #961):
    only then is an unrecorded removal a finding — on a report never asked
    for a row the removals are listed, not counted (the #684 precedent) —
    and a parsed table is not the test, because a pre-#929 audit summary
    can parse as one (#1175 review, M2).
    """
    if not report.exists():
        return {"checked": False, "reason": f"no report at {report}",
                "findings": []}
    text = report.read_text(encoding="utf-8", errors="replace")
    findings: list[dict[str, str]] = []
    claims = unnamed = core_cannot_hold = 0
    # Refused up front, not only on the row that would consult it (#993): a
    # report with no failing `both` row would otherwise check clean against
    # a core schema that could not be read.
    if "CoreDataset" not in declared:
        raise ValueError("declared slots carry no `CoreDataset` class; "
                         "the core schema could not be read")

    # (name as written, record the removal is claimed from), for the
    # snapshot diff's suppression: only an exact top-level name, claimed
    # from the full record or from no named record, records a whole-slot
    # removal — a row removing `x.leaf` or `x[0]`, or removing `x` from the
    # core alone, says nothing about `x` leaving the full record (#1175
    # review, M1).
    removal_named: set[tuple[str, str]] = set()

    def removal(names: list[str], context: str, claim: str) -> None:
        nonlocal claims, unnamed
        if not names:
            unnamed += 1
            return
        if _ELEMENT_REMOVAL.search(claim):
            # A field removed from every entry is not the slot leaving, so
            # the claim is unusable — and a claim the reader cannot use
            # records nothing either (#1175 Codex review, M3: it was
            # counted unnamed and still suppressed the snapshot finding).
            unnamed += 1
            return
        removal_named.update((n, _target(context)) for n in names)
        claims += 1
        where = _target(context)
        for name in names:
            # `errata[0] removed` cannot be checked by presence at index 0.
            # Removing an element renumbers the rest, so index 0 afterwards is
            # the object that survived — VOICE rep1 folded one Erratum into
            # another and the surviving one sits exactly where the dropped one
            # was. Skipped and counted, not guessed at.
            if re.search(r"\[\d+\]$", name):
                unnamed += 1
                continue
            in_full, v_full = resolve(full, name)
            in_core, v_core = resolve(core, name)
            # A dotted step over a list reads as `[*]` here too (#1175
            # round 3, S4): one claim, one reading, for removals as well.
            full_live = (in_full and _populated(v_full)) or _resolve_loose(full, name)
            core_live = (in_core and _populated(v_core)) or _resolve_loose(core, name)
            live = {"core": core_live, "full": full_live,
                    "both": core_live or full_live,
                    "either": core_live}[where]
            if live:
                # Describe the value that is live. Under `both` the full
                # record may be the only one carrying it, and describing the
                # core's `None` as "record has a value" named the wrong
                # record (#995); a value live only through the loose reading
                # is described from that reading (round 4, S6).
                if where == "full":
                    v = v_full if in_full and _populated(v_full) else _loose_value(full, name)
                elif core_live:
                    v = v_core if in_core and _populated(v_core) else _loose_value(core, name)
                else:
                    v = v_full if in_full and _populated(v_full) else _loose_value(full, name)
                findings.append({
                    "kind": "removal_not_performed", "slot": name,
                    "record": where,
                    "detail": f"report says removed; record has {_describe(v)}",
                    "claim": claim[:240]})

    # Rows of a dispositions table (#929) are read below, column by column;
    # the generic scan would read their free-text `reason` cell as a removal
    # claim ("Dropped the duplicate entry; slot kept", #962).
    rows = disposition_rows(text)
    # Every line of the dispositions table, not only the rows that parsed:
    # a row whose disposition cell the reader does not know ("Reviewed")
    # carries a free-text reason ("Dropped the duplicate entry; slot kept")
    # that is not a removal claim, and the generic scan below read it as
    # one (#962; #1175 round 2, M1). The table is the strict reader's.
    disposition_lines = {row["line"] for row in rows} | _dispositions_table_lines(text)
    for line in text.splitlines():
        cells = _cells(line)
        if not cells or line.strip() in disposition_lines:
            continue
        # The change cell is found rather than assumed at a fixed index: one
        # report writes `| core | \`distributions\` | removed; … |`, putting the
        # record in column 0 and the slot in column 1.
        for i, cell in enumerate(cells):
            if i and _CELL_REMOVED.match(cell):
                named = [n for c in cells[:i] for n in _named(c)]
                # `| core | `distributions` | removed |`: the record is a
                # bare cell, which `_target`'s prose test cannot see, so the
                # row read as `either` (#1175 Codex review, M6).
                bare = [c.strip().strip("`*_ ").lower() for c in cells]
                where = next((c for c in bare if c in ("full", "core", "both")), None)
                removal(named, f"the {where} record" if where else line, line)
                break

    # Paragraphs, not lines: an outcome sentence wraps, and "The three
    # `distributions` objects were removed from" is the whole of its first line.
    paras = re.split(r"\n\s*\n", text)
    headings: dict[int, tuple[list[str], str]] = {}
    para_index: dict[int, int] = {}
    current: tuple[list[str], str] = ([], "")
    for n, para in enumerate(paras):
        para_index[id(para)] = n
        for ln in para.splitlines():
            h = re.match(r"^#{1,6}\s+(.*)$", ln)
            if h:
                current = (_TICKED.findall(h.group(1)), h.group(1))
        headings[n] = current
    for para in paras:
        if para.lstrip().startswith("|"):
            continue
        m = _ACTION.match(" ".join(para.split()))
        if not m:
            continue
        body = m.group("body")
        if _REMOVAL_VERB.search(body) and not _NEGATED.search(body):
            head, head_text = headings.get(para_index.get(id(para), -1),
                                           ([], ""))
            # The heading is part of the context, not only a source of names:
            # "### 2.1 Core `distributions` slot not in the schema" is where
            # that section says which record it is about, and without it the
            # claim falls back to the conservative both-records rule and a real
            # false removal goes unreported.
            removal(_subjects(body) or _heading_fallback(body, head),
                    body + " " + head_text, body)

    # Schema claims, per sentence. "This slot is not declared on `CoreDataset`"
    # names its subject in the sentence before it, and the surrounding key
    # lists — `path`, `format`, `media_type` — are examples, not subjects. The
    # first version flagged every backticked name on the line.
    classes = set(declared)
    for line in text.splitlines():
        cells = _cells(line)
        if cells and len(cells) >= 3 and _ABSENT_FROM_SCHEMA.search(cells[-1]):
            sentence_subjects = [(_TICKED.findall(cells[0]), cells[-1])]
        elif cells:
            continue
        else:
            sentence_subjects = []
            prev: list[str] = []
            for sent in re.split(r"(?<=[.!?])\s+", line):
                here = [n for n in _TICKED.findall(sent) if n not in classes]
                for phrase in _ABSENT_FROM_SCHEMA.finditer(sent):
                    # Only names *before* the phrase. After it they are
                    # attributions, and the report is generally right about
                    # them: "the key set is a hybrid of `FileCollection`
                    # (`path`) and `DistributionFormat` (`format`)" correctly
                    # places two keys it is not claiming are undeclared.
                    before = [n for n in _TICKED.findall(sent[:phrase.start()])
                              if n not in classes]
                    # Nothing before it means the subject is a demonstrative —
                    # "This slot is not declared" — naming the slot introduced
                    # in the sentence above. Only then: a sentence with no
                    # backticked subject and no demonstrative is about
                    # something else, and borrowing the previous sentence's
                    # slot made a prose remark a schema claim (#757).
                    demonstrative = re.match(r"\s*(?:this|that|these|those|the|it|no such|such)\b", sent, re.I)
                    sentence_subjects.append((before or (prev[:1] if demonstrative else []), sent))
                if here:
                    prev = here

        for names, claim in sentence_subjects:
            for name in names:
                # A dotted path names a slot on a nested class, not the root.
                # Resolving `distributions.bogus` to `distributions` reported a
                # true claim as false, because the root does exist (#578).
                # Only unqualified names are checkable against a class
                # inventory; a nested one needs the range class, which this
                # does not resolve, so it is skipped rather than guessed.
                if re.search(r"[.\[]", name):
                    continue
                root = name
                scope, basis = _claim_scope(claim, classes)
                holders = sorted(c for c, sl in declared.items()
                                 if root in sl and c in scope)
                if holders:
                    where = ("; the claim is scoped to the "
                             + basis + " schema" if basis != "unscoped" else "")
                    findings.append({
                        "kind": "false_schema_claim", "slot": root,
                        "scope": basis,
                        "detail": ("report says this is not a declared slot; "
                                   "it is declared on " + ", ".join(holders)
                                   + where),
                        "claim": claim.strip()[:240]})

    # One claim can be stated twice — a summary table row and the prose that
    # elaborates it. Reporting it twice inflates the count a reader uses to
    # judge how bad a report is.
    # The dispositions table (#929), column by column. A `removed` row is a
    # removal claim against the record the row names — the column the
    # instruction promises is honoured (#964), so `both` must be absent from
    # both (#578's direction) and `full` is read against the full record. A
    # retained/changed/added row claims the slot is present in the record
    # named, or in *either* record when it names none (#963): reconciliation
    # legitimately keeps a full-only slot out of the derived core.
    _CONTEXT = {"full": "from the full record", "core": "from the core record",
                "both": "from the full record and core record", "either": "",
                "no_record_column": "", "invalid": ""}
    for row in rows:
        if row["disposition"] in ("removed", "deleted", "dropped"):
            if row["record"] == "invalid":
                unnamed += 1
                continue
            removal([row["slot"]], _CONTEXT[row["record"]], row["line"])
            continue
        if row["disposition"] not in _PRESENCE_DISPOSITIONS:
            continue
        if row["record"] == "invalid":
            unnamed += 1
            continue
        claims += 1
        in_full, v_full = resolve(full, row["slot"])
        in_core, v_core = resolve(core, row["slot"])
        # A dotted step over a list reads as `[*]` here as in prose (#1175
        # round 2, S3): the two readings of one claim must not disagree.
        full_has = (in_full and _populated(v_full)) or _resolve_loose(full, row["slot"])
        core_has = (in_core and _populated(v_core)) or _resolve_loose(core, row["slot"])
        # A table with no record column reads like an empty cell here —
        # against either record — and is only counted apart (#1122).
        where = "either" if row["record"] == "no_record_column" else row["record"]
        present = {"core": core_has, "full": full_has,
                   "both": core_has and full_has,
                   "either": core_has or full_has}[where]
        if not present:
            # `both` on a slot the core class does not declare is a claim the
            # core cannot satisfy by construction (#990): the VOICE v8
            # canary's five remaining contradictions were all `retained |
            # both` on `citation`, `consent_revocations` and kin. The row is
            # read as written — the instruction defines `both` as present in
            # both, and a report stating the core carries what it cannot is
            # a false claim about the core (#992) — but the finding names the
            # cause, so the regate can fix the row rather than guess, and the
            # block counts these apart from substantive contradictions.
            cause = ""
            # Only where the full record does carry it: a `both` row on a
            # slot neither record holds is a substantive contradiction, and
            # "name `full`" would be wrong advice.
            if (where == "both" and in_full and _populated(v_full)
                    and not _core_declares(row["slot"], declared, ranges)):
                core_cannot_hold += 1
                cause = _core_cannot_hold_cause(row["slot"], declared, ranges)
            findings.append({
                "kind": ("retention_not_shown" if row["disposition"] in
                         ("retained", "kept", "unchanged", "left as-is", "left as is")
                         else "change_not_shown"),
                "slot": row["slot"], "record": where,
                "detail": f"report says {row['disposition']}; the {where} record does not carry it" + cause,
                "claim": row["line"][:240]})
    # Prose retention claims (#1054): read like a `retained` row that names no
    # record — present in either record satisfies it — so a sentence saying a
    # value "remains in `X`" when nothing is at `X` is a finding, not silence.
    # Paragraphs, not lines, as the removal scan reads them (#1175 review,
    # S3); table lines are skipped, their cells are read above.
    prose_retained = 0
    for para in re.split(r"\n\s*\n", text):
        prose = " ".join(ln for ln in para.splitlines()
                         if not ln.lstrip().startswith("|") and not _cells(ln)
                         and ln.strip() not in disposition_lines)
        for m in _PROSE_RETAINED.finditer(prose):
            path = m.group(1)
            if path.lower() in _NOT_A_SLOT or path.isdigit():
                continue                       # "remains at `false`" names a value, not a slot (Codex M7)
            before = prose[max(0, m.start() - 80):m.start()]
            if _NEGATED_BEFORE.search(before) or _negated_clause(before):
                continue                       # "nothing remains in `x`", "no value remains in `x`"
            targets = {"full": full, "core": core}
            written = path
            head, _, rest = path.partition(".")
            if head in targets and rest:
                # "remains in `core.notes`" names the record, not a slot.
                targets, path = {head: targets[head]}, rest
            if not _SLOT_PATH.fullmatch(path):
                continue                       # `CoreDataset`, `HIPAA`: not a slot path (snake_case only)
            claims += 1
            prose_retained += 1
            if any(_resolve_loose(rec, path) for rec in targets.values()):
                continue
            # Prose names a leaf, not a path: "the four named reviewers stay
            # in `review_details`" means `ethical_reviews[0].review_details`.
            # A populated key of that name under the claim's own root (or
            # anywhere, when the root is not a slot) satisfies it; only a
            # name found nowhere is a finding.
            if any(_leaf_under_root(rec, path) for rec in targets.values()):
                continue
            findings.append({
                "kind": "retention_not_shown", "slot": written, "record": "either",
                "detail": "report says the value remains there; neither record carries it, "
                          "at that path or under that name anywhere",
                "claim": prose.strip()[:240]})
    # The snapshot diff (#1054): deterministic, no claim parsing. A top-level
    # slot the phase-1 record populated and the final full record does not,
    # with no `removed` row and no removal statement naming it, is a
    # removal the report did not record — the CHORUS 04f rep2
    # `regulatory_restrictions` case, the AI_READI 04g rep3 `content_warnings`
    # case, the VOICE 04f rep2 `data_governance` object (five receipted
    # leaves). Objects and leaves alike: the test is the root key.
    # A finding only where the run was asked for the table the row belongs
    # to (`dispositions_expected`, #961): a report never asked for a row
    # has none for anything, and every removal in it would read as
    # unrecorded. Those are listed under `removals_unrecorded` and not
    # counted as findings, the #684 precedent — a check the instruction
    # never asked for is not a floor of 0. A parsed table is not the test:
    # a pre-#929 audit summary parses as one (#1175 review, M2).
    # What records a removal, for suppression only: an exact top-level name
    # in a `removed` row or a removal claim against the full record or no
    # named record (M1), or the weak prose signal — the bare name in a
    # sentence with a removal word (S1). The strict reading stays for
    # `removal_not_performed`, where precision matters.
    recorded = {n for n, where in removal_named if where in ("full", "both", "either")}
    # The weak signal reads prose only: every table line is left to the
    # strict readers above (a row whose disposition cell does not parse
    # carries a free-text reason that is not a statement about the record,
    # #962), a sentence about the core alone records nothing about the full
    # record, and `_named` keeps a destination out of the casualties.
    prose_only = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("|"))
    for whole in re.split(r"(?<=[.!?])\s+|\n", prose_only):
        # Only the clause the removal word sits in, and only where nothing
        # voids it (#1175 Codex review, M1): a name in another clause is
        # not what was removed, and a negated or hypothetical removal
        # records nothing at all.
        for sent in _CLAUSE_SPLIT.split(whole):
            if not _REMOVAL_WORD.search(sent) or _removal_voided(sent):
                continue
            if _target(sent) == "core" or _target(whole) == "core":
                continue
            # A coordinated destination list ("recorded in `a` and `b`")
            # names no casualty past its first item, which `_named`'s
            # lookback reaches; the rest are excluded here (#1175 round 3).
            # ... and only where a removal word precedes the preposition
            # (round 4, S1): in "the values in `a`, `b` and `c` were
            # removed" the removal comes after the list, so every item is
            # a casualty — the first one too, which `_named`'s lookback
            # would otherwise read as a place.
            destinations: set[str] = set(); casualties: set[str] = set()
            for m in _DESTINATION_LIST.finditer(sent):
                names = _TICKED.findall(m.group(0))
                if _REMOVAL_WORD.search(sent[:m.start()]):
                    destinations.update(names)
                elif _CASUALTY_TAIL.match(sent, m.end()):
                    # "the values in `a`, `b` and `c` were removed": the
                    # removal follows the list in the same clause, with no
                    # retention verb or "rather than" between (round 5, M1 —
                    # the first cut read every un-preceded list as
                    # casualties and silenced 51 corpus destinations)
                    casualties.update(n for n in names if n in _named(m.group(0).replace("in ", "", 1)))
            recorded.update(n for n in [*_named(sent), *casualties]
                            if _SLOT_PATH.fullmatch(n) and n not in destinations)
    unrecorded: list[dict[str, str]] = []
    expected = bool(dispositions_expected)
    if isinstance(snapshot, dict):
        for key, before in snapshot.items():
            if key in _SNAPSHOT_EXEMPT or not _populated(before):
                continue
            if key in full and _populated(full.get(key)):
                continue
            if key in recorded:
                continue
            unrecorded.append({"slot": key})
            if not expected:
                continue
            findings.append({
                "kind": "removal_not_recorded", "slot": key, "record": "full",
                "detail": (f"the phase-1 record carried `{key}` ({_describe(before)}); the final "
                           f"record does not, and no Dispositions row and no removal statement "
                           f"names it — add a `removed` row for `{key}`"),
                "claim": ""})
    seen, unique = set(), []
    for f in findings:
        key = (f["kind"], f.get("slot"), f.get("record"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)
    return {"checked": True, "findings": unique, "claims_checked": claims,
            # Named rather than dropped: a claim naming no slot in backticks
            # cannot be checked, and a reader should know how many there were.
            "claims_unnamed": unnamed, "disposition_rows": len(rows),
            # By record column (#1122): the v9 canary reader compares the
            # `both` count with the v8 fill's, because a `both` row flipped to
            # `full` resolves against the full record only and raises nothing.
            "rows_by_record": rows_by_record(rows),
            # Findings on `both` rows whose slot the core class does not
            # declare (#990/#992): a mis-named record rather than a
            # substantive contradiction, and a reader should see the two apart.
            "claims_core_cannot_hold": core_cannot_hold,
            # The snapshot diff (#1054): made or not, and what it found. A
            # record with no snapshot reads `false` here, not zero findings.
            "snapshot_checked": isinstance(snapshot, dict),
            "snapshot_basis": (None if not isinstance(snapshot, dict)
                               else ("dispositions table expected: unrecorded removals are findings"
                                     + ("" if rows else " (no table parsed)"))
                               if expected
                               else "no dispositions table expected: unrecorded removals listed, not findings"),
            "prose_retention_claims": prose_retained,
            "removals_unrecorded": [u["slot"] for u in unrecorded],
            "removals_unrecorded_count": len(unrecorded) if isinstance(snapshot, dict) else None,
            "instrument": REPORT_CLAIMS_INSTRUMENT}


def _leaf_under_root(rec: Any, path: str) -> bool:
    """The prose fallback (#1054): a populated key of the path's leaf name
    under the path's root. A dotted path whose root the record lacks cannot
    be satisfied by a leaf found elsewhere (#1175 round 2, S2); a bare name
    is searched anywhere."""
    segs = re.split(r"[.\[]", path.rstrip("]"))
    segs = [s for s in segs if s and not s.isdigit() and s != "*"]
    leaf, root = segs[-1], segs[0]
    if not isinstance(rec, dict):
        return False
    if len(segs) == 1:
        return _has_populated_key(rec, leaf)
    if root not in rec:
        return False
    return _has_populated_key(rec.get(root), leaf)


def _loose_value(data: Any, path: str) -> Any:
    """The populated values a dotted-over-list path reads to, as one list,
    so a loose-only match can be described by its count (round 4, S6)."""
    parts = re.findall(r"[\w]+|\[\d+\]|\[\*\]", path)
    out: list[Any] = []

    def walk(cur: Any, i: int) -> None:
        if i == len(parts):
            if _populated(cur):
                out.append(cur)
            return
        part = parts[i]
        if isinstance(cur, list) and not part.startswith("["):
            for item in cur:
                walk(item, i)
            return
        if part == "[*]":
            if isinstance(cur, list):
                for item in cur:
                    walk(item, i + 1)
            return
        if part.startswith("["):
            idx = int(part[1:-1])
            if isinstance(cur, list) and idx < len(cur):
                walk(cur[idx], i + 1)
            return
        if isinstance(cur, dict) and part in cur:
            walk(cur[part], i + 1)

    walk(data, 0)
    if len(out) == 1:
        return out[0]
    if out and all(isinstance(o, list) for o in out):
        return [x for o in out for x in o]              # entries across the matches, not matches (round 5, S2)
    return out


def _resolve_loose(data: Any, path: str) -> bool:
    """`resolve`, but a dotted step over a list reads as `[*]`: prose writes
    `splits.split_details` for `splits[*].split_details` (#1175 review, S4).
    True when a populated value sits at the path."""
    parts = re.findall(r"[\w]+|\[\d+\]|\[\*\]", path)

    def walk(cur: Any, i: int) -> bool:
        if i == len(parts):
            return _populated(cur)
        part = parts[i]
        if isinstance(cur, list) and not part.startswith("["):
            return any(walk(item, i) for item in cur)
        if part == "[*]":
            return isinstance(cur, list) and any(walk(item, i + 1) for item in cur)
        if part.startswith("["):
            idx = int(part[1:-1])
            return isinstance(cur, list) and idx < len(cur) and walk(cur[idx], i + 1)
        return isinstance(cur, dict) and part in cur and walk(cur[part], i + 1)

    return walk(data, 0)


def _has_populated_key(node: Any, name: str) -> bool:
    """A populated mapping key of this name anywhere in the structure."""
    if isinstance(node, dict):
        if name in node and _populated(node[name]):
            return True
        return any(_has_populated_key(v, name) for v in node.values())
    if isinstance(node, list):
        return any(_has_populated_key(v, name) for v in node)
    return False


def phase1_snapshot_for(core_path: Path) -> dict | None:
    """The phase-1 snapshot beside a core record, by the same rule the
    receipts join uses (`receipts.phase1_snapshot`, #758/#761): the
    highest-numbered `intermediate/{P}_full*.yaml`. None where the runner
    kept none."""
    from data_sheets_schema.receipts import phase1_snapshot
    receipt = core_path.parent / core_path.name.replace("_d4d_core.yaml", "_coverage_receipt.yaml")
    return phase1_snapshot(receipt)


def declared_slots() -> dict[str, set[str]]:
    """Induced slots for the classes a report makes claims about."""
    from data_sheets_schema.provenance import CORE_SCHEMA, FULL_SCHEMA
    out: dict[str, set[str]] = {}
    for schema, classes in ((FULL_SCHEMA, ("Dataset",)),
                            (CORE_SCHEMA, ("CoreDataset", "CoreDistribution"))):
        view = shared_view(schema)
        for cls in classes:
            if cls in view.all_classes():
                out[cls] = {s.name for s in view.class_induced_slots(cls)}
    return out


def declared_ranges() -> dict[str, dict[str, str | None]]:
    """Every core class, its induced slots, and the class each slot ranges
    to — the map `_core_declares` walks a nested path against (#994).

    Every class the core schema defines, not only `CoreDataset`, because
    `resources` ranges back to `CoreDataset` and `distributions` to
    `CoreDistribution`, and a path can descend through either. A slot whose
    range is not a class in this schema is recorded as `None`: a scalar,
    and the end of any walk that reaches it."""
    from data_sheets_schema.provenance import CORE_SCHEMA
    view = shared_view(CORE_SCHEMA)
    classes = set(view.all_classes())
    out: dict[str, dict[str, str | None]] = {}
    for cls in classes:
        out[cls] = {s.name: (s.range if s.range in classes else None)
                    for s in view.class_induced_slots(cls)}
    return out
