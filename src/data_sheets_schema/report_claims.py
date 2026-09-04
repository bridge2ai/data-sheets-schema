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
_OBLIQUE = re.compile(r"\b(?:from|into|to|in|on|within|onto|under|beside|"
                      r"alongside)\s+(?:the\s+|core\s+|full\s+)*`")
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


def disposition_rows(text: str) -> list[dict[str, str]]:
    """Rows of every table whose header names a `disposition` column."""
    rows: list[dict[str, str]] = []
    header: dict[str, int] | None = None
    for line in text.splitlines():
        cells = _cells(line)
        if cells is None:
            if line.lstrip().startswith("|"):
                continue                      # the separator row keeps the header
            header = None
            continue
        low = [c.lower() for c in cells]
        if "disposition" in low and header is None:
            header = {name: i for i, name in enumerate(low)}
            continue
        if header is None:
            continue
        d = cells[header["disposition"]] if header["disposition"] < len(cells) else ""
        m = _DISPOSITION.match(d)
        if not m:
            continue
        slot_cell = cells[header.get("slot", 0)] if header.get("slot", 0) < len(cells) else cells[0]
        names = _TICKED.findall(slot_cell) or ([slot_cell.strip()] if re.fullmatch(r"[\w.\[\]]+", slot_cell.strip()) else [])
        record = ""
        if "record" in header and header["record"] < len(cells):
            record = cells[header["record"]].strip().lower()
        for name in names:
            rows.append({"slot": name, "disposition": m.group(1).lower(),
                         "record": record if record in ("full", "core", "both") else "either",
                         "line": line.strip()})
    return rows


def check_report(report: Path, full: dict, core: dict,
                 declared: dict[str, set[str]]) -> dict[str, Any]:
    """Findings, plus what was skipped.

    `declared` maps a class name to its induced slot names — passed in so a
    caller checking twelve reports builds the SchemaView once.
    """
    if not report.exists():
        return {"checked": False, "reason": f"no report at {report}",
                "findings": []}
    text = report.read_text(encoding="utf-8", errors="replace")
    findings: list[dict[str, str]] = []
    claims = unnamed = 0

    def removal(names: list[str], context: str, claim: str) -> None:
        nonlocal claims, unnamed
        if not names:
            unnamed += 1
            return
        if _ELEMENT_REMOVAL.search(claim):
            unnamed += 1                     # a nested field of the entries (#782)
            return
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
            live = {"core": in_core and _populated(v_core),
                    "full": in_full and _populated(v_full),
                    "both": (in_core and _populated(v_core))
                            or (in_full and _populated(v_full)),
                    "either": in_core and _populated(v_core)}[where]
            if live:
                v = v_full if where == "full" else v_core
                findings.append({
                    "kind": "removal_not_performed", "slot": name,
                    "record": where,
                    "detail": f"report says removed; record has {_describe(v)}",
                    "claim": claim[:240]})

    for line in text.splitlines():
        cells = _cells(line)
        if not cells:
            continue
        # The change cell is found rather than assumed at a fixed index: one
        # report writes `| core | \`distributions\` | removed; … |`, putting the
        # record in column 0 and the slot in column 1.
        for i, cell in enumerate(cells):
            if i and _CELL_REMOVED.match(cell):
                named = [n for c in cells[:i] for n in _named(c)]
                removal(named, line, line)
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
                holders = sorted(c for c, sl in declared.items() if root in sl)
                if holders:
                    findings.append({
                        "kind": "false_schema_claim", "slot": root,
                        "detail": ("report says this is not a declared slot; "
                                   "it is declared on " + ", ".join(holders)),
                        "claim": claim.strip()[:240]})

    # One claim can be stated twice — a summary table row and the prose that
    # elaborates it. Reporting it twice inflates the count a reader uses to
    # judge how bad a report is.
    # Presence claims from the dispositions table (#929). A `removed` row
    # is already a removal claim above (its cell matches _CELL_REMOVED); a
    # retained/changed/added row claims the slot is there, in the record the
    # row names, or in the core when it names none (the `_target` reading).
    rows = disposition_rows(text)
    for row in rows:
        if row["disposition"] not in _PRESENCE_DISPOSITIONS:
            continue
        if re.search(r"\[\d+\]$", row["slot"]):
            unnamed += 1
            continue
        claims += 1
        in_full, v_full = resolve(full, row["slot"])
        in_core, v_core = resolve(core, row["slot"])
        present = {"core": in_core and _populated(v_core),
                   "full": in_full and _populated(v_full),
                   "both": (in_core and _populated(v_core)) and (in_full and _populated(v_full)),
                   "either": in_core and _populated(v_core)}[row["record"]]
        if not present:
            findings.append({
                "kind": ("retention_not_shown" if row["disposition"] in
                         ("retained", "kept", "unchanged", "left as-is", "left as is")
                         else "change_not_shown"),
                "slot": row["slot"], "record": row["record"],
                "detail": f"report says {row['disposition']}; the {row['record']} record does not carry it",
                "claim": row["line"][:240]})
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
            "claims_unnamed": unnamed, "disposition_rows": len(rows)}


def declared_slots() -> dict[str, set[str]]:
    """Induced slots for the classes a report makes claims about."""
    from linkml_runtime import SchemaView

    from data_sheets_schema.provenance import CORE_SCHEMA, FULL_SCHEMA
    out: dict[str, set[str]] = {}
    for schema, classes in ((FULL_SCHEMA, ("Dataset",)),
                            (CORE_SCHEMA, ("CoreDataset", "CoreDistribution"))):
        view = shared_view(schema)
        for cls in classes:
            if cls in view.all_classes():
                out[cls] = {s.name for s in view.class_induced_slots(cls)}
    return out
