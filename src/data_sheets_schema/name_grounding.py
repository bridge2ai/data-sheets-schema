"""Is a person's name in the bundle the record was generated from? (#2918)

`grounding` (#547) catches "right answer, no evidence" for external
identifiers. Person names are as exposed and nothing checked them. The CM4AI
bundle names two authors only as `Axelsson U` and `Metallo C`; runs expanded
those initials into given names the bundle never states, and four published
CM4AI records (with their cores) still carry `Christian Metallo`. The ORCID
beside that name is in the bundle, so the person is right: the given name
came from memory, not from the evidence.

What is read
------------
A **name leaf** is the `name` of a mapping held by a slot whose induced
range is `Person` or `Creator`, or the string itself where the record
writes that slot as a string (`contact_person: Vardit Ravitsky (ORCID:…)`).
The slots are derived from the full and core schemas, never listed
(`person_name_slots`): `committee_contact`, `committee_members`,
`contact_person`, `creators`, `governance_committee_contact` and
`principal_investigator` today. `principal_investigator` is also named
explicitly, as the issue scopes it, so a later range change cannot drop it.
The walk recurses, so a creator's own `principal_investigator` is reached.

Not read: identifiers (a bare-name person id such as
`creators[4].id: Uma Axelsson` is an identifier-form defect, not a name
leaf), `maintainers` (a `Maintainer` is neither a `Person` nor a `Creator`),
affiliations, and prose outside these slots. A string leaf is read whole,
so a role written where a person belongs (`creators[3].name: Curator and
generator expertise profile`, a VOICE crate-arm record) is checked like a
name, and a word of it the bundle does not state is a finding. Paths are
indexed (`creators[20].name`) so a finding names the entry it is about.

Tokens and classes
------------------
A token is a run of letters (with any combining marks) of at least two
letters, so hyphens, apostrophes, digits and punctuation separate tokens:
`Jean-Christophe Bélisle-Pipon` is four tokens and the initials `U` and `C`
are none. Identifier-shaped spans in a string leaf — a URL, an email
address, a CURIE such as `ORCID:0000-…` — are removed first. Tokens compare
casefolded and NFKC-composed; the *folded* form used for
`diacritic_dropped` also decomposes (NFKD) and drops the combining marks.
The bundle is tokenised the same way, so a name the bundle wraps across a
line (`Charlotte\\nMarquez`) is still two tokens of it. Each token of a
name leaf is exactly one of:

``grounded``
    the token occurs in the bundle.
``diacritic_dropped``
    it occurs only after folding: the record and the bundle differ by a
    diacritic. The name follows the issue; the test is symmetric, so a mark
    the record *added* is counted here too. Letters NFKD does not decompose
    (`ø`, `ł`) are not folded.
``initial_expanded``
    it does not occur even folded, but it is capitalised and another token
    of the same name — the surname — sits in the bundle, capitalised, next
    to an initial that is this token's first letter: `Metallo C` or
    `C. Metallo` for `Christian Metallo`. The token is not itself a run of
    two or three capitals: initials the record kept (`JC Bélisle-Pipon`)
    or a degree (`Jorge Contreras, JD`) expand nothing and are `absent`.
    The surname is a token the record writes capitalised and not as
    initials, so `the` in an organisation's name stands in for none.
``absent``
    none of these.

Every rule below reads the bundle's layout, and decides only the class of
a token that is already a finding: whether a token is a finding depends on
the word sets alone.

- An **initial** is a single capital, or two or three capitals written
  together (`Levinson MA`), standing alone: one glued to a digit (the
  ORCID check digit of `…-420X`, the `G` of `G6`) is not an initial.
- **Before the surname**, an initial may be separated from it by
  whitespace, periods and hyphens. It is not the surname's when it is the
  trailing initial of the previous word (`Marquez C Metallo` gives Metallo
  no `C`). Where the surname has its initials before it on its line,
  whatever follows it opens the next entry (`C. Metallo, T. Clark` gives
  Metallo no `T`).
- **After the surname**, an initial may be separated from it by whitespace
  and at most one comma (`Metallo C`, `Metallo, C.`, `Metallo\\nC`). A run
  of two or three capitals followed on its line by a word is an acronym in
  prose, not initials (`The IRB will`, `RO-Crate`).
- **Initials written together** are single capitals with only joiners
  (`.`, `-`) and spaces between them, on one line (`J-C`, `J.-C.`,
  `M. A.`), in either direction. After the surname, one joined
  across a space must not be followed on its line by a word (`Clark T. A
  study` gives Clark no `A`). A line break, or a run of two or three
  capitals, ends them (`Axelsson U\\nKTH`, `Clark T. EVI`).

Layout is not meaning, so the rules can still be wrong in both
directions: `Levinson MA and` gives Levinson no initials there; a two- or
three-letter given name in capitals (`TIM CLARK`) reads as initials kept;
a suffix in mixed case (`Jr`) is judged like a given name; a run of
capitals ending the line before a surname (`La Jolla, CA\\nClark T`) is
read as that surname's initials; and a capitalised word that is not a
surname (`The` opening an organisation's name) can still stand in for
one.

Every token that is not `grounded` is a finding
(`{kind: name_token_not_in_bundle, path, name, token, class}`). Occurrences
and distinct tokens are both reported (#556): the first says how many name
tokens rest on no evidence, the second how many facts are at issue.

A lower bound
-------------
**A whole-bundle token match is a lower bound on the defect.** A given name
that occurs anywhere in the bundle grounds the token, including a different
person's entry: a record that expands `Clark T` into `Emma Clark` reads as
grounded, because Emma Lundberg is in the CM4AI bundle. Only a stronger
check would require the given name to sit near the surname, and that rule
must survive line wrapping — `Charlotte` is in the CM4AI bundle only as
`Charlotte\\nMarquez` — and the bundle's other author forms. A source's own
typo is grounded as written (`Ballllosero`), and a record that corrects it
is `absent`: the check measures agreement with the bytes, not correctness.
A script written without spaces between words (Chinese, Japanese, Thai) is
one run of letters per phrase, so a name inside such a phrase is not a
token of the bundle and reads `absent`: there the check over-reports.

The issue's criterion that `Belisle-Pipon` is `diacritic_dropped` does not
hold on its own bundle: the CM4AI bundle writes `Belisle-Pipon` without the
mark six times (lines 5436–7535) beside `Bélisle-Pipon`, so under the
whole-bundle rule both spellings are `grounded`. `diacritic_dropped` is
exercised on a synthetic bundle in the tests.

Which bytes
-----------
`check_record` compares one record with the text it is given. `check_run`
resolves the bytes a run's provenance record says it read
(`inputs.bundle_md5` / `inputs.bundle_sha256`): the bundle on disk when it
hashes to every hash the record recorded, otherwise the committed version
that does, through `provenance.bundle_bytes_for` (#1140). Today's bytes of
a drifted bundle are never used, and a record that pins no hash is not
checked. The result's `bundle.md5` is the md5 of the bytes checked.
Bytes that are not UTF-8 are refused rather than decoded with replacement
characters, which would split a name and report the pieces (the receipts
check refuses them the same way). The result states its
record scope: the phase-1 snapshot (`intermediate/{P}_full.yaml`, when the
run kept one), the final full record and the derived core, each reported
separately, never pooled.

Read-only and reported, never fatal (#520). Nothing here writes a record
or a provenance block.
"""

from __future__ import annotations

import functools
import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterator, NamedTuple

import yaml

#: Named so a result says which instrument produced it (#907).
INSTRUMENT = "name_grounding v1 (#2918)"

#: The classes, in the order they are decided.
CLASSES = ("grounded", "diacritic_dropped", "initial_expanded", "absent")

#: The records of one run this checks, in pipeline order.
RECORDS = ("phase1", "full", "core")

#: Scoped by the issue whatever the schema ranges it.
_ALWAYS = frozenset({"principal_investigator"})

#: Ranges whose values are people, or creators that may be people.
_PERSON_RANGES = frozenset({"Person", "Creator"})


class Token(NamedTuple):
    text: str
    start: int
    end: int


def _runs(text: str) -> list[Token]:
    """Every run of letters in `text`, with the combining marks inside it.

    A scan by Unicode category rather than `[^\\W\\d_]+`, which would split
    a decomposed `e\\u0301` from its mark and cut `Bélisle` in two.
    """
    out: list[Token] = []
    start = None
    for i, ch in enumerate(text):
        cat = unicodedata.category(ch)
        if cat[0] == "L" or (cat[0] == "M" and start is not None):
            if start is None:
                start = i
        elif start is not None:
            out.append(Token(text[start:i], start, i))
            start = None
    if start is not None:
        out.append(Token(text[start:], start, len(text)))
    return out


def _letters(token: str) -> int:
    return sum(1 for ch in token if unicodedata.category(ch)[0] == "L")


def exact_key(token: str) -> str:
    """Casefolded and compatibility-composed: `É` and `é` are one key."""
    return unicodedata.normalize("NFKC", token.casefold())


def folded_key(token: str) -> str:
    """`exact_key` with the combining marks removed: `Bélisle` → `belisle`."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", token.casefold())
                   if not unicodedata.combining(ch))


#: Identifier-shaped spans a string leaf may carry beside the name: a URL, an
#: email address, a CURIE (`ORCID:0000-0002-7080-8801`). Their letters are
#: not a name, and whether they are in the bundle is #547's question.
_NOT_A_NAME = re.compile(r"\S*://\S*|\S+@\S+|\b[A-Za-z][\w.\-]*:[^\s)\],;]+")


def name_tokens(name: str) -> list[str]:
    """The tokens of a name leaf that are checked: two or more letters,
    outside any identifier-shaped span."""
    return [t.text for t in _runs(_NOT_A_NAME.sub(" ", name)) if _letters(t.text) >= 2]


def _is_initial(token: str) -> bool:
    """A capital initial or a run of two or three written together."""
    return 1 <= _letters(token) <= 3 and token.isupper()


#: What may join the initials of one person: `J-C`, `M.A.`, `J.-C.`.
_JOINERS = ".-\u2010\u2011"


def _gap_ok(gap: str, allowed: str, commas: int = 0) -> bool:
    return (all(ch.isspace() or ch in allowed or ch == "," for ch in gap)
            and gap.count(",") <= commas)


#: A word of two or more letters after an initial on the same line, across
#: spaces or a hyphen: `The IRB will`, `RO-Crate`, `T. A study`. Not across
#: a line break, which ends an author entry (`Axelsson U\nKTH`).
_WORD_AFTER = re.compile(r"[ \t\-\u2010\u2011]+[^\W\d_]{2}")

#: Spaces on one line: what may sit between two initials besides joiners.
_SPACES = " \t"


class BundleIndex:
    """One bundle tokenised once: the word sets and the token stream."""

    def __init__(self, text: str):
        self.text = text
        self.tokens = _runs(text)
        self.exact = {exact_key(t.text) for t in self.tokens}
        self.folded: set[str] = set()
        self.positions: dict[str, list[int]] = {}
        for i, t in enumerate(self.tokens):
            key = folded_key(t.text)
            self.folded.add(key)
            self.positions.setdefault(key, []).append(i)

    def _gap(self, i: int, j: int) -> str:
        return self.text[self.tokens[i].end:self.tokens[j].start]

    def _initial_at(self, j: int) -> bool:
        """Token `j` is an initial standing alone: not glued to a digit, as
        the ORCID check digit of `…-420X` and the `G` of `G6` are."""
        if not (0 <= j < len(self.tokens) and _is_initial(self.tokens[j].text)):
            return False
        t = self.tokens[j]
        return not (self.text[t.start - 1:t.start].isdigit()
                    or self.text[t.end:t.end + 1].isdigit())

    def _word_after(self, j: int) -> bool:
        return bool(_WORD_AFTER.match(self.text, self.tokens[j].end))

    def _joined(self, i: int, j: int) -> bool:
        """Initials `i` < `j` written together as one person's: single
        capitals with only joiners and spaces between them, on one line
        (`J-C`, `J.-C.`, `M.A.`, `M. A.`). A run of two or three capitals
        (`MA`, `JC`) is already all of that person's initials."""
        return (_letters(self.tokens[i].text) == 1 and _letters(self.tokens[j].text) == 1
                and all(ch in _JOINERS or ch in _SPACES for ch in self._gap(i, j)))

    def initials_beside(self, surname: str) -> set[str]:
        """Folded initial letters written next to `surname` in the bundle,
        where the bundle writes it capitalised: `access R` is not a name.
        The rule is the one the module docstring gives under
        `initial_expanded`."""
        out: set[str] = set()
        for k in self.positions.get(folded_key(surname), ()):
            if not self.tokens[k].text[:1].isupper():
                continue
            # Before it: `C. Metallo`, `J.-C. Bélisle-Pipon`.
            run: list[int] = []
            j = k - 1
            if self._initial_at(j) and _gap_ok(self._gap(j, k), _JOINERS):
                run.append(j)
                while self._initial_at(j - 1) and self._joined(j - 1, j):
                    j -= 1
                    run.append(j)
            if run:
                first = run[-1]
                prev = first - 1
                # Not the trailing initial of the word before: in
                # `Marquez C\nMetallo C` the first C is Marquez's.
                belongs_to_previous = (prev >= 0 and self.tokens[prev].text[:1].isupper()
                                       and not _is_initial(self.tokens[prev].text)
                                       and _gap_ok(self._gap(prev, first), ""))
                if not belongs_to_previous:
                    for i in run:
                        out.update(folded_key(self.tokens[i].text))
                    # Written `C. Metallo` on one line, so what follows it
                    # opens the next entry: in `C. Metallo, T. Clark` the T
                    # is Clark's. Not across a line break, where the "initials"
                    # may end the line before (`La Jolla, CA\nClark T`).
                    if not any(ch in "\r\n" for ch in self._gap(run[0], k)):
                        continue
            # After it: `Metallo C`, `Metallo, C.`, `Levinson MA`, `Pipon J-C`.
            j = k + 1
            if not (self._initial_at(j) and _gap_ok(self._gap(k, j), "", commas=1)):
                continue
            if _letters(self.tokens[j].text) > 1 and self._word_after(j):
                continue                     # an acronym in prose: `The IRB will`, `RO-Crate`
            out.update(folded_key(self.tokens[j].text))
            while (self._initial_at(j + 1) and self._joined(j, j + 1)
                   and not (any(ch in _SPACES for ch in self._gap(j, j + 1))
                            and self._word_after(j + 1))):     # not `Clark T. A study`
                j += 1
                out.update(folded_key(self.tokens[j].text))
        return out


def classify(token: str, name: list[str], index: BundleIndex) -> str:
    """The class of one token of a name, given the name's other tokens."""
    if exact_key(token) in index.exact:
        return "grounded"
    if folded_key(token) in index.folded:
        return "diacritic_dropped"
    if not token[:1].isupper():
        return "absent"                  # an initial expands into a capitalised name
    if _is_initial(token):
        return "absent"                  # initials kept (`JC`) or a degree (`JD`): nothing expanded
    initial = folded_key(token)[:1]
    for other in name:
        if folded_key(other) == folded_key(token) or folded_key(other) not in index.folded:
            continue
        if not other[:1].isupper() or _is_initial(other):
            continue                     # not written as a surname here (`the`, `MA`)
        if initial in index.initials_beside(other):
            return "initial_expanded"
    return "absent"


@functools.lru_cache(maxsize=None)
def _schema_person_slots(schema_path: str) -> frozenset[str]:
    from data_sheets_schema.schema_view import shared_view
    sv = shared_view(Path(schema_path))
    return frozenset(str(sl.name) for c in sv.all_classes()
                     for sl in sv.class_induced_slots(c)
                     if str(sl.range) in _PERSON_RANGES)


def person_name_slots() -> frozenset[str]:
    """Slots ranged `Person` or `Creator` in the full or core schema, plus
    `principal_investigator`. Each has one range wherever it is declared,
    so matching a key by name is matching it by range."""
    from data_sheets_schema.provenance import CORE_SCHEMA, FULL_SCHEMA
    return (_schema_person_slots(str(FULL_SCHEMA)) | _schema_person_slots(str(CORE_SCHEMA))
            | _ALWAYS)


def iter_name_leaves(node: Any, slots: frozenset[str] | set[str],
                     path: str = "") -> Iterator[tuple[str, str]]:
    """(path, name) for every person-name leaf, with indexed paths
    (`creators[12].name`) so a finding names the entry it is about."""
    def at(key: str) -> str:
        return f"{path}.{key}" if path else key

    if isinstance(node, dict):
        for key, child in node.items():
            here = at(str(key))
            if key in slots:
                items = child if isinstance(child, list) else [child]
                for i, value in enumerate(items):
                    where = f"{here}[{i}]" if isinstance(child, list) else here
                    if isinstance(value, str) and value.strip():
                        yield where, value
                    elif isinstance(value, dict) and isinstance(value.get("name"), str) \
                            and value["name"].strip():
                        yield f"{where}.name", value["name"]
            yield from iter_name_leaves(child, slots, here)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from iter_name_leaves(item, slots, f"{path}[{i}]")


def check_record(record: Any, bundle: str | BundleIndex,
                 slots: frozenset[str] | set[str] | None = None) -> dict[str, Any]:
    """Classify every name token of one record against a bundle's text."""
    if not isinstance(record, dict):
        return {"checked": False, "instrument": INSTRUMENT,
                "reason": ("the record is an empty document" if record is None
                           else f"the record is a {type(record).__name__}, not a mapping")}
    index = bundle if isinstance(bundle, BundleIndex) else BundleIndex(bundle)
    slots = person_name_slots() if slots is None else slots
    counts = {c: 0 for c in CLASSES}
    distinct: dict[str, set[str]] = {c: set() for c in CLASSES}
    findings: list[dict[str, str]] = []
    leaves = 0
    for path, name in iter_name_leaves(record, slots):
        leaves += 1
        tokens = name_tokens(name)
        seen: set[str] = set()
        for token in tokens:
            cls = classify(token, tokens, index)
            counts[cls] += 1
            distinct[cls].add(exact_key(token))
            if cls != "grounded" and exact_key(token) not in seen:
                seen.add(exact_key(token))
                findings.append({"kind": "name_token_not_in_bundle", "path": path,
                                 "name": name, "token": token, "class": cls})
    return {"checked": True, "instrument": INSTRUMENT, "name_leaves": leaves,
            "counts": counts, "distinct": {c: len(v) for c, v in distinct.items()},
            "findings": findings}


def parse_record(raw: bytes) -> tuple[Any, str | None]:
    """(the parsed document, None), or (None, why it does not parse).

    `ValueError` too: PyYAML's scalar constructors raise it for a value such
    as `release_date: 2026-02-30`, and one such record must not end a walk
    over a run's records."""
    try:
        return yaml.safe_load(raw.decode("utf-8")), None
    except (yaml.YAMLError, UnicodeDecodeError, ValueError) as exc:
        return None, f"does not parse: {type(exc).__name__}"


def bundle_text(raw: bytes) -> tuple[str | None, str | None]:
    """(the bundle's text, None), or (None, why): bytes that are not UTF-8
    are refused, not decoded with replacement characters that would split a
    name into pieces the bundle then lacks."""
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError as exc:
        return None, f"the bundle bytes are not UTF-8 ({exc.reason} at byte {exc.start})"


def _hashes_match(raw: bytes, md5: str | None, sha256: str | None) -> bool:
    """Every hash the record gave matches, and it gave at least one."""
    checks = [(md5, hashlib.md5(raw).hexdigest()), (sha256, hashlib.sha256(raw).hexdigest())]
    given = [(want, got) for want, got in checks if want]
    return bool(given) and all(want == got for want, got in given)


def record_bundle_bytes(record: dict[str, Any], provenance: Path
                        ) -> tuple[bytes | None, dict[str, Any]]:
    """(the bytes the record hashed, their basis), or (None, a reason).

    The bundle on disk only where it hashes to every hash the record
    recorded — then it *is* those bytes and git is not asked (#1140) —
    otherwise the committed version through `provenance.bundle_bytes_for`.
    """
    from data_sheets_schema.backfill_checks import declared_bundle
    from data_sheets_schema.provenance import GitUnavailable, bundle_bytes_for
    inputs = record.get("inputs") if isinstance(record.get("inputs"), dict) else {}
    declared = inputs.get("bundle_path")
    md5, sha256 = inputs.get("bundle_md5"), inputs.get("bundle_sha256")
    if not declared:
        return None, {"reason": "the record names no input bundle"}
    if not md5 and not sha256:
        return None, {"reason": ("the record pins no md5 or sha256 of the bundle it read, so the "
                                 "bytes it read cannot be established")}
    hashes = {k: v for k, v in (("md5", md5), ("sha256", sha256)) if v}
    on_disk = declared_bundle(record, provenance)
    disk = "is absent"
    if on_disk is not None and on_disk.is_file():
        raw = on_disk.read_bytes()
        if _hashes_match(raw, md5, sha256):
            return raw, {"source": "bundle on disk", "path": str(declared),
                         "matched_on": sorted(hashes)}
        disk = "is not those bytes"
    try:
        found = bundle_bytes_for(str(declared), md5=md5, sha256=sha256)
    except GitUnavailable as exc:
        return None, {"reason": (f"the bundle on disk {disk}, and git could not supply the "
                                 f"version the record hashed: {exc}")}
    if found is None:
        return None, {"reason": (f"the bundle on disk {disk}, and no committed version of "
                                 f"{declared} hashes to the record's {' and '.join(sorted(hashes))}")}
    raw, entry = found
    return raw, {"source": "git blob", "path": str(declared), "commit": entry["commit"],
                 "committed_on": entry.get("date"), "matched_on": entry.get("matched_on")}


def _phase1(provenance: Path, record: dict[str, Any]) -> tuple[Path, bytes] | None:
    """The phase-1 snapshot's path and bytes, read the way the receipts
    check reads it (under the run's attested identity where it has one),
    or None when the run kept none."""
    from data_sheets_schema.receipts import phase1_snapshot_read, receipt_path
    project = provenance.name[: -len("_provenance.yaml")]
    return phase1_snapshot_read(receipt_path(provenance.parent, project), record=record)


def _load(which: str, provenance: Path, record: dict[str, Any]
          ) -> tuple[str | None, Any, str | None]:
    """(path, parsed record, why not) for one of a run's records."""
    from data_sheets_schema.backfill_checks import record_paths
    if which == "phase1":
        try:
            found = _phase1(provenance, record)
        except OSError as exc:
            # `UsageLedgerError` is an OSError: an attested snapshot whose
            # bytes changed, or an index that names another run.
            return None, None, f"the phase-1 snapshot cannot be read: {type(exc).__name__}: {exc}"
        if found is None:
            return None, None, "the run kept no phase-1 snapshot"
        path, raw = found
    else:
        path = record_paths(provenance)[which]
        if not path.is_file():
            return str(path), None, "not on disk"
        raw = path.read_bytes()
    doc, why = parse_record(raw)
    return str(path), doc, why


def check_run(provenance: Path, records: tuple[str, ...] = RECORDS) -> dict[str, Any]:
    """Every name leaf of a run's records against the bytes the run read.

    `records` is the record scope, named in the result: any of `phase1`
    (the `full` phase's snapshot under `intermediate/`), `full` (the final
    full record) and `core` (the derived core). Each is reported on its
    own; nothing is pooled across them. Where bytes were resolved,
    `bundle.md5` is the md5 of the bytes the records were checked against.
    """
    from data_sheets_schema.schema_cache import load_yaml
    out: dict[str, Any] = {"instrument": INSTRUMENT,
                           "project": provenance.name[: -len("_provenance.yaml")],
                           "label": provenance.parent.name, "provenance": str(provenance),
                           "record_scope": list(records)}
    try:
        record = load_yaml(provenance)
    except (OSError, yaml.YAMLError, UnicodeDecodeError, ValueError) as exc:
        return {**out, "checked": False,
                "reason": f"the provenance record cannot be read: {type(exc).__name__}"}
    if not isinstance(record, dict):
        return {**out, "checked": False, "reason": "the provenance record is not a mapping"}
    raw, basis = record_bundle_bytes(record, provenance)
    out["bundle"] = basis
    if raw is None:
        return {**out, "checked": False, "reason": basis["reason"]}
    # The md5 of the bytes actually indexed, so a reader (and the corpus
    # test) can compare it with the bundle it expects, not only trust the
    # basis's `matched_on`.
    out["bundle"] = {**basis, "md5": hashlib.md5(raw).hexdigest()}
    text, why = bundle_text(raw)
    if text is None:
        return {**out, "checked": False, "reason": why}
    index = BundleIndex(text)
    slots = person_name_slots()
    out["checked"] = True
    out["records"] = {}
    for which in records:
        path, doc, why = _load(which, provenance, record)
        out["records"][which] = ({"checked": False, "path": path, "reason": why} if why
                                 else {"path": path, **check_record(doc, index, slots)})
    return out
