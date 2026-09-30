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
    A longer run is a name written in capitals and is judged like any
    other (`CHRISTIAN METALLO`); in a name written wholly in capitals with
    a word of four or more letters, a run of two or three before the first
    comma is a word too (`TIM CLARK`, #3026). A generational suffix (`Jr`,
    `Sr`, `III`) expands nothing and stands in for no surname. The surname
    is a token the record writes capitalised and not as initials, and not
    a function word (`the`, `and`, `of`, `for`, `from`, `with`), so `The`
    opening an organisation's name stands in for none (#3026). A token the
    record writes in lower case (`christian Metallo`, `Access requests`)
    is `absent`: an initial expands into a capitalised name.
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
  no `C`), unless that word has its own initials before it on its line,
  written as single capitals, and so takes no trailing one: `C.
  Metallo\\nT. Clark` gives Clark the `T` (#3126). "Its own" is read one
  level back, without this exception. A run of two or three capitals
  ending the line before is not the surname's (`La Jolla, CA\\nClark T`,
  #3026). Where the surname has its initials before it on its line,
  written as single capitals, whatever follows it opens the next entry
  (`C. Metallo, T. Clark` gives Metallo no `T`). A run of two or three
  capitals there is credited as its initials but does not show where its
  entry starts: it may be an acronym, and the capitalised words after it
  no surname, so `La Jolla, CA Clark T` and `the NIH Common Fund Metallo
  C` keep the initial after the surname (#3143).
- A **compound surname** is capitalised words, none of them initials,
  joined by hyphens or spaces on one line (`Bélisle-Pipon`, `Ballllosero
  Navarro`). Its initials sit before its first word, and are credited to
  that word only; the rule above then holds for every word of it
  (`J.-C. Bélisle-Pipon, T. Clark` gives Pipon no `T`, and `F. Ballllosero
  Navarro, T. Clark` gives Navarro none).
- **After the surname**, an initial may be separated from it by whitespace
  and at most one comma (`Metallo C`, `Metallo, C.`, `Metallo\\nC`). A run
  of two or three capitals followed on its line by a word is an acronym in
  prose, not initials (`The IRB will`, `RO-Crate`), except `and` or `&`
  and then a capitalised word, the next entry of an author list
  (`Levinson MA and Marquez C`, #3026). A word on the next
  line does not count, so a bundle that lists one author per line keeps
  their initials (`Levinson MA\\nMarquez C`, `Levinson M A\\nMarquez C`).
- **Initials written together** are single capitals with only joiners
  (`.`, `-`) and spaces between them, on one line (`J-C`, `J.-C.`,
  `M. A.`), in either direction. After the surname, one joined
  across a space must not be followed on its line by a word (`Clark T. A
  study` gives Clark no `A`). A line break, or a run of two or three
  capitals, ends them (`Axelsson U\\nKTH`, `Clark T. EVI`).

Layout is not meaning, so the rules can still be wrong in both
directions: a run of two or three capitals followed by any other word
(`Levinson MA with`) gives no initials there; a name in capitals with no
word longer than three letters (`TIM LEE`) reads as initials kept, as
does `TIM Clark`; a run of capitals before a surname on its line (`La
Jolla, CA Clark T`), or single capitals ending the line before
(`U.S.A.\\nClark T`), is read as that surname's initials, and so is a
run after it that no word follows on its line (the CM4AI bundle's
`Zhandos Sembay, UAB` gives Sembay `UAB`, and `UW Medicine PHI.` gives
Medicine `PHI`); a surname after a given name
spelled out takes the next entry's initial (`Christian Metallo, T.
Clark` gives Metallo `T`: only single capitals before it show where its
entry starts, and `Ballllosero Navarro, F.` is laid out the same way), and
so does one after initials written as a run of capitals (`MA Levinson, T.
Clark`, `JC Bélisle-Pipon, T. Clark`, and on the next line too, `MA
Levinson\\nT. Clark`); a single capital before
capitalised words on one line reads as a compound surname's initials
whatever the words are (`A Common Fund Metallo C` gives Metallo no `C`); a
surname with a lower-case particle (`J. van der Berg, T. Clark`) is not
read as one compound, so `Berg` takes the `T`; initials before a surname
joined to the previous entry's trailing one (`Axelsson U C. Metallo\\nT.
Clark`) are read as all that entry's, so Metallo leads nothing and takes
the `T`; and a capitalised word outside the short function-word list
(`In` opening an organisation's name) can still stand in for a surname.

Every token that is not `grounded` is a finding
(`{kind: name_token_not_in_bundle, path, name, token, class}`). Occurrences
and distinct tokens are both reported (#556): the first says how many name
tokens rest on no evidence, the second how many facts are at issue.

A lower bound, and the v2 proximity reading
-------------------------------------------
**A whole-bundle token match is a lower bound on the defect.** A given name
that occurs anywhere in the bundle grounds the token, including a different
person's entry: a record that expands `Clark T` into `Emma Clark` reads as
grounded, because Emma Lundberg is in the CM4AI bundle.

The **v2 proximity reading** (#2978, `PROXIMITY_INSTRUMENT`) re-reads each
v1-`grounded` token and reports, beside v1 and never as a finding, the
ones it would demote. A leaf is split into parts at `;`, `,`, `:`,
brackets and identifier spans (`person_parts`), and within a part the
capitalised tokens that are not initials are read together; a part of
fewer than two distinct such words is not judged (`Doctor Y`, `PhD`, a
leaf written `Clark, Tim`). A judged token stays grounded when the
bundle writes it near another word of its part — at most
`PROXIMITY_WINDOW` capitalised tokens (or words the leaf itself writes,
`de`, `of`) between them, only whitespace (line breaks included:
`Charlotte\\nMarquez`), periods after an initial (not after a word,
where a sentence ends: `Emma Lundberg. Clark J`, unless the leaf writes
that word with a period too, `St. Louis`; so `Tim St John` against `Tim
St. John` demotes `John`, a cost), hyphens, apostrophes
or digits inside a word (`Bridge2AI`) between tokens, and one comma only where the bundle
inverts the record's order (`Clark, Tim`) — or beside that word's
initial (`Metallo C`, `C. Metallo`, `Metallo, C.`, `Pipon J-C` keep
`Metallo` for `Christian Metallo`; a suffix or `The` has no initial
there). A digit before a comma is an
affiliation mark and ends the entry (`Levinson1, Charlotte`). A demoted
token carries the class it would have were it absent (`initial_expanded`
where the other word has its initial beside it: `Jing Gao` against
`Jing Chen; Gao J`), and whether v1 found its leaf clean. On the
committed corpus at this change (283 provenance records, 4 not
checkable) v2 demotes 10 token occurrences in 6 records: 7 in leaves v1
finds clean, among them `Jing` in a CM4AI `Jing Gao` (full and core),
the rest prose in person slots (`Contact Principal Investigator`). A
source's own
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

#: Named so a result says which instrument produced it (#907). v1.1 moved
#: classes only, never whether a token is a finding (#3026, #3126).
INSTRUMENT = "name_grounding v1.1 (#2918, #3026, #3126)"

#: The proximity reading beside it (#2978): report-only, never a finding.
PROXIMITY_INSTRUMENT = "name_grounding v2 proximity (#2978), report-only"

#: At most this many tokens (middle names, initials) between two tokens of
#: one name for them to be read as one entry: `Mark D. Wilkinson`,
#: `Jean-Christophe Bélisle-Pipon`.
PROXIMITY_WINDOW = 2

#: The classes, in the order they are decided.
CLASSES = ("grounded", "diacritic_dropped", "initial_expanded", "absent")

#: The records of one run this checks, in pipeline order.
RECORDS = ("phase1", "full", "core")

#: Scoped by the issue whatever the schema ranges it.
_ALWAYS = frozenset({"principal_investigator"})

#: Ranges whose values are people, or creators that may be people.
_PERSON_RANGES = frozenset({"Person", "Creator"})

#: Generational suffixes, folded: written beside a name they expand no
#: initial (`John Smith Jr`, #3026).
_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv"})

#: Words that stand in for no surname, folded: `The` opening an
#: organisation's name is not a person's (#3026). Kept short on purpose:
#: `An` and `To` are surnames.
_NOT_SURNAMES = frozenset({"the", "and", "of", "for", "from", "with"})

#: Neither stands in for a surname.
_NO_STAND_IN = _NOT_SURNAMES | _SUFFIXES


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
#: a line break, which ends an author entry where the bundle lists one per
#: line: `Levinson MA\nMarquez C` gives Levinson `MA`. The cost is capitals
#: ending a line after a surname (`Zhandos Sembay, UAB` in the CM4AI
#: bundle gives Sembay `UAB`).
_WORD_AFTER = re.compile(r"[ \t\-\u2010\u2011]+[^\W\d_]{2}")

#: `and` or `&` and then a capitalised word, on one line, after a run of
#: capitals: an author list (`Levinson MA and Marquez C`, #3026), where
#: `The IRB and the` stays prose. The group is the next word's first
#: character, whose case decides.
_AUTHOR_AND = re.compile(r"[ \t]+(?:and|&)[ \t]+(\w)")

#: Spaces on one line: what may sit between two initials besides joiners.
_SPACES = " \t"

#: What may sit between two tokens of one name in one entry (#2978):
#: spaces and line breaks, joiners and periods (`J.-C.`, `M. D.`) and
#: apostrophes (`O'Brien`). A period only after an initial: after a word
#: it ends a sentence, and so the entry (`Emma Lundberg. Clark J`, #3427).
#: A comma only under the rule in `_one_entry`, and digits only inside one
#: word (`Bridge2AI`): a digit beside anything else (an affiliation mark,
#: `Levinson1, Charlotte`), a semicolon or a bracket ends the entry.
_IN_ENTRY = _JOINERS + "'\u2019"

#: What may sit between the words of one compound surname, on one line:
#: `Bélisle-Pipon`, `Ballllosero Navarro`.
_COMPOUND = "-\u2010\u2011" + _SPACES


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
        self._exact_positions: dict[str, list[int]] | None = None
        self._beside: dict[str, set[str]] = {}

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

    def _author_and(self, j: int) -> bool:
        """`and`/`&` then a capitalised word after token `j`, on its line:
        the next entry of an author list, not prose (#3026)."""
        m = _AUTHOR_AND.match(self.text, self.tokens[j].end)
        return bool(m) and m.group(1).isupper()

    def _trailing_of_previous(self, prev: int, first: int) -> bool:
        """Initial `first` may be the trailing initial of word `prev`:
        capitalised, not an initial, with only whitespace between."""
        return (prev >= 0 and self.tokens[prev].text[:1].isupper()
                and not _is_initial(self.tokens[prev].text)
                and _gap_ok(self._gap(prev, first), ""))

    def _leads_its_entry(self, k: int) -> bool:
        """Word `k` (or the compound surname it ends) has its own initials
        before it on its line, written as single capitals (`C. Metallo`), so
        it takes no trailing initial: the capital after it opens the next
        entry, on the next line too (`C. Metallo\\nT. Clark`, #3126). "Its
        own" is read one level back: the initials are not the trailing
        initial of the word before them (`Marquez C Metallo`)."""
        start = self._surname_start(k)
        j = start - 1
        if not (self._initial_at(j) and _letters(self.tokens[j].text) == 1
                and _gap_ok(self._gap(j, start), _JOINERS)
                and not any(ch in "\r\n" for ch in self._gap(j, start))):
            return False
        while self._initial_at(j - 1) and self._joined(j - 1, j):
            j -= 1
        return not self._trailing_of_previous(j - 1, j)

    def _joined(self, i: int, j: int) -> bool:
        """Initials `i` < `j` written together as one person's: single
        capitals with only joiners and spaces between them, on one line
        (`J-C`, `J.-C.`, `M.A.`, `M. A.`). A run of two or three capitals
        (`MA`, `JC`) is already all of that person's initials."""
        return (_letters(self.tokens[i].text) == 1 and _letters(self.tokens[j].text) == 1
                and all(ch in _JOINERS or ch in _SPACES for ch in self._gap(i, j)))

    def _surname_start(self, k: int) -> int:
        """The first word of the compound surname that token `k` ends or
        sits in: capitalised words, none of them initials, with only
        hyphens and spaces between them on one line (`Bélisle-Pipon`,
        `Ballllosero Navarro`). `k` itself when the word before it is not
        one. A lower-case particle (`van der Berg`) or a period ends it."""
        while (k - 1 >= 0 and self.tokens[k - 1].text[:1].isupper()
               and not _is_initial(self.tokens[k - 1].text)
               and all(ch in _COMPOUND for ch in self._gap(k - 1, k))):
            k -= 1
        return k

    def initials_beside(self, surname: str) -> set[str]:
        """Folded initial letters written next to `surname` in the bundle,
        where the bundle writes it capitalised: `access R` is not a name.
        The rule is the one the module docstring gives under
        `initial_expanded`. Computed once per surname."""
        key = folded_key(surname)
        if key not in self._beside:
            self._beside[key] = self._initials_beside(key)
        return set(self._beside[key])

    def _initials_beside(self, key: str) -> set[str]:
        out: set[str] = set()
        for k in self.positions.get(key, ()):
            if not self.tokens[k].text[:1].isupper():
                continue
            # Before it: `C. Metallo`, `J.-C. Bélisle-Pipon`. A compound
            # surname's initials sit before its first word only
            # (`F. Ballllosero Navarro`), so they are sought there.
            start = self._surname_start(k)
            run: list[int] = []
            j = start - 1
            if self._initial_at(j) and _gap_ok(self._gap(j, start), _JOINERS):
                run.append(j)
                while self._initial_at(j - 1) and self._joined(j - 1, j):
                    j -= 1
                    run.append(j)
            if run:
                first = run[-1]
                prev = first - 1
                # Not the trailing initial of the word before: in
                # `Marquez C\nMetallo C` the first C is Marquez's. Unless
                # that word leads its own entry with initials, and so takes
                # no trailing one: in `C. Metallo\nT. Clark` the T is
                # Clark's (#3126).
                belongs_to_previous = (self._trailing_of_previous(prev, first)
                                       and not self._leads_its_entry(prev))
                # A run of two or three capitals ending the line before is
                # not this surname's: `La Jolla, CA\nClark T` (#3026).
                across = any(ch in "\r\n" for ch in self._gap(run[0], start))
                run_of_capitals = _letters(self.tokens[run[0]].text) > 1
                if not belongs_to_previous and not (run_of_capitals and across):
                    if start == k:           # credited to the word they sit beside
                        for i in run:
                            out.update(folded_key(self.tokens[i].text))
                    # Written `C. Metallo` on one line, so what follows it
                    # opens the next entry: in `C. Metallo, T. Clark` the T
                    # is Clark's, and in `J.-C. Bélisle-Pipon, T. Clark` it
                    # is not Pipon's either. Only single capitals show
                    # that. A run of two or three before a word may be an
                    # acronym, with no surname after it (`La Jolla, CA Clark
                    # T`, `the NIH Common Fund Metallo C`). Nor across a
                    # line break, where the "initials" may end the line
                    # before (`La Jolla, CA\nClark T`).
                    if not run_of_capitals and not across:
                        continue
            # After it: `Metallo C`, `Metallo, C.`, `Levinson MA`, `Pipon J-C`.
            j = k + 1
            if not (self._initial_at(j) and _gap_ok(self._gap(k, j), "", commas=1)):
                continue
            if (_letters(self.tokens[j].text) > 1 and self._word_after(j)
                    and not self._author_and(j)):
                continue                     # an acronym in prose: `The IRB will`, `RO-Crate`
            out.update(folded_key(self.tokens[j].text))
            while (self._initial_at(j + 1) and self._joined(j, j + 1)
                   and not (any(ch in _SPACES for ch in self._gap(j, j + 1))
                            and self._word_after(j + 1)
                            and not self._author_and(j + 1))):     # not `Clark T. A study`
                j += 1
                out.update(folded_key(self.tokens[j].text))
        return out

    def _one_entry(self, i: int, j: int, comma_ok: bool, between: frozenset[str],
                   abbreviated: frozenset[str] = frozenset()) -> bool:
        """Tokens `i` < `j` read as one entry (#2978): every token between
        them capitalised (a middle name, an initial) or one the record's
        own leaf writes (`de` in `Michael de Riesthal`, `of` in `University
        of Alabama`), and between tokens only whitespace, line breaks
        included (`Charlotte\\nMarquez`), `_IN_ENTRY` characters, or digits
        inside one word (`Bridge2AI`). A period only after an initial
        (`Mark D. Wilkinson`) or after a word in `abbreviated`, one the
        leaf itself writes with a period after it (`St.` in `Washington
        University in St. Louis`): after any other word it ends a sentence
        (`Emma Lundberg. Clark J`, #3427). One comma where `comma_ok`, the
        `Surname, Given` form."""
        if any(not self.tokens[m].text[:1].isupper() and exact_key(self.tokens[m].text) not in between
               for m in range(i + 1, j)):
            return False
        commas = 0
        for m in range(i, j):
            gap = self._gap(m, m + 1)
            if gap.isdigit():
                continue
            if not all(ch.isspace() or ch in _IN_ENTRY or ch == "," for ch in gap):
                return False
            if ("." in gap and not _is_initial(self.tokens[m].text)
                    and exact_key(self.tokens[m].text) not in abbreviated):
                return False                 # a sentence ends here (#3427)
            commas += gap.count(",")
        return commas == 0 or (comma_ok and commas == 1)

    def near(self, token: str, partner: str, token_first: bool | None = None,
             between: frozenset[str] = frozenset(),
             abbreviated: frozenset[str] = frozenset()) -> bool:
        """`token` occurs in the bundle within `PROXIMITY_WINDOW` tokens of
        `partner`, in one entry. `token` is matched exactly (it is a v1
        `grounded` token), `partner` folded. `token_first` is whether the
        record writes `token` before `partner`; one comma is allowed only
        where the bundle inverts that order, the `Surname, Given` form
        (`Clark, Tim` for `Tim Clark`, not `Tim, Clark`), and never when
        `token_first` is None. `between` are the exact keys of the record
        leaf's tokens, which may sit between the two in any case;
        `abbreviated` those it writes with a period after them, which may
        be followed by one in the bundle too (`abbreviations`)."""
        if self._exact_positions is None:
            self._exact_positions = {}
            for i, t in enumerate(self.tokens):
                self._exact_positions.setdefault(exact_key(t.text), []).append(i)
        others = set(self.positions.get(folded_key(partner), ()))
        reach = PROXIMITY_WINDOW + 1
        for a in self._exact_positions.get(exact_key(token), ()):
            for b in range(a - reach, a + reach + 1):
                inverted = token_first is not None and (a < b) != token_first
                if b != a and b in others and self._one_entry(min(a, b), max(a, b), inverted,
                                                                   between, abbreviated):
                    return True
        return False


def words_in_capitals(name: str) -> frozenset[str]:
    """Exact keys of the tokens of `name` that look like initials (two or
    three capitals) but are words, because the whole name is written in
    capitals (`TIM CLARK`, #3026): every token is in capitals and one has
    four or more letters. Only before the first comma, since a degree
    follows one (`JORGE CONTRERAS, JD`), and never a suffix."""
    text = _NOT_A_NAME.sub(" ", name)
    tokens = [t for t in _runs(text) if _letters(t.text) >= 2]
    if not (tokens and all(t.text.isupper() for t in tokens)
            and any(_letters(t.text) > 3 for t in tokens)):
        return frozenset()
    comma = text.find(",")
    return frozenset(exact_key(t.text) for t in tokens
                     if _is_initial(t.text) and (comma < 0 or t.start < comma)
                     and folded_key(t.text) not in _SUFFIXES)


def _initials_like(token: str, words: frozenset[str]) -> bool:
    return _is_initial(token) and exact_key(token) not in words


def expansion_class(token: str, name: list[str], index: BundleIndex,
                    words: frozenset[str] = frozenset()) -> str:
    """`initial_expanded` or `absent`: the class of a token read as not in
    the bundle, whether or not it is. `words` are the tokens of the name
    that are words though written like initials (`words_in_capitals`)."""
    if not token[:1].isupper():
        return "absent"                  # an initial expands into a capitalised name
    if folded_key(token) in _SUFFIXES:
        return "absent"                  # `Jr`: a suffix expands nothing (#3026)
    if _initials_like(token, words):
        return "absent"                  # initials kept (`JC`) or a degree (`JD`): nothing expanded
    initial = folded_key(token)[:1]
    for other in name:
        if folded_key(other) == folded_key(token) or folded_key(other) not in index.folded:
            continue
        if not other[:1].isupper() or _initials_like(other, words):
            continue                     # not written as a surname here (`the`, `MA`)
        if folded_key(other) in _NO_STAND_IN:
            continue                     # `The` opening an organisation's name (#3026)
        if initial in index.initials_beside(other):
            return "initial_expanded"
    return "absent"


def classify(token: str, name: list[str], index: BundleIndex,
             words: frozenset[str] = frozenset()) -> str:
    """The class of one token of a name, given the name's other tokens
    (and, from `words_in_capitals`, which of them are words)."""
    if exact_key(token) in index.exact:
        return "grounded"
    if folded_key(token) in index.folded:
        return "diacritic_dropped"
    return expansion_class(token, name, index, words)


def classify_name(name: str, index: BundleIndex) -> list[tuple[str, str]]:
    """(token, class) for every checked token of one name leaf."""
    tokens = name_tokens(name)
    words = words_in_capitals(name)
    return [(t, classify(t, tokens, index, words)) for t in tokens]


#: What separates the people, roles and degrees of one name leaf for v2:
#: `Forget A, Obernier K`, `Olivier Elemento, PhD`, `Access requests: …`.
_PART_BREAK = re.compile(r"[;,:()\[\]/|]")


def abbreviations(name: str) -> frozenset[str]:
    """Exact keys of the tokens `name` writes with a period right after
    them (`St` in `St. Louis`): where the leaf abbreviates a word, a period
    after it in the bundle is the abbreviation's, not a sentence end
    (#3427)."""
    text = _NOT_A_NAME.sub(" ", name)
    return frozenset(exact_key(t.text) for t in _runs(text) if text[t.end:t.end + 1] == ".")


def person_parts(name: str, words: frozenset[str] = frozenset()) -> list[list[str]]:
    """The name words of each part of a leaf, split at `_PART_BREAK`, that
    v2 judges together: capitalised tokens that are not initials. A part of
    fewer than two distinct words has no partner and is not judged, so
    `Doctor Y; Dailamy A`, a degree after a comma and lower-case prose
    are not; nor is a leaf written `Clark, Tim`. An identifier span
    (`_NOT_A_NAME`) breaks a part too."""
    parts = []
    for part in _PART_BREAK.split(_NOT_A_NAME.sub(";", name)):
        parts.append([t for t in name_tokens(part)
                      if t[:1].isupper() and not _initials_like(t, words)])
    return parts


def proximity(token: str, name: list[str], index: BundleIndex,
              words: frozenset[str] = frozenset(),
              between: frozenset[str] = frozenset(),
              abbreviated: frozenset[str] = frozenset()) -> str | None:
    """The v2 reading of a v1-`grounded` token (#2978): None where it sits
    near another token of its name — `near` it, or written beside that
    token's initial (`Metallo C`, `C. Metallo`, `Metallo, C.`, `Pipon J-C`
    for `Christian Metallo` grounds `Metallo`) — else the class it would
    have were it not in the bundle (`expansion_class`). A name of one
    distinct token is not judged: the caller skips it. A suffix or a
    function word (`_NO_STAND_IN`: `Jr`, `The`) has no initial to be
    written beside `token`, as in `expansion_class` (#3428). `between` and
    `abbreviated` are as `BundleIndex.near` takes them."""
    here = name.index(token)
    for at, other in enumerate(name):
        if exact_key(other) == exact_key(token):
            continue
        if index.near(token, other, token_first=here < at, between=between,
                      abbreviated=abbreviated):
            return None
        if (other[:1].isupper() and not _initials_like(other, words)
                and folded_key(other) not in _NO_STAND_IN      # not `Jr`, `The` (#3428)
                and folded_key(other)[:1] in index.initials_beside(token)):
            return None
    return expansion_class(token, name, index, words)


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
    prox = {"judged": 0, "near": 0, "not_judged": 0, "demoted": 0,
            "demoted_in_clean_leaves": 0}
    prox_counts = {"initial_expanded": 0, "absent": 0}
    prox_distinct: set[str] = set()
    demoted: list[dict[str, str]] = []
    leaves = 0
    for path, name in iter_name_leaves(record, slots):
        leaves += 1
        tokens = name_tokens(name)
        words = words_in_capitals(name)
        classes = [(t, classify(t, tokens, index, words)) for t in tokens]
        seen: set[str] = set()
        for token, cls in classes:
            counts[cls] += 1
            distinct[cls].add(exact_key(token))
            if cls != "grounded" and exact_key(token) not in seen:
                seen.add(exact_key(token))
                findings.append({"kind": "name_token_not_in_bundle", "path": path,
                                 "name": name, "token": token, "class": cls})
        # v2 (#2978), beside v1 and never pooled into it.
        clean = all(cls == "grounded" for _, cls in classes)
        grounded = {exact_key(t) for t, cls in classes if cls == "grounded"}
        counts_grounded = sum(1 for _, cls in classes if cls == "grounded")
        leaf_keys = frozenset(exact_key(t) for t in tokens)
        dotted = abbreviations(name)
        listed: set[str] = set()
        judged = 0
        for part in person_parts(name, words):
            if len({exact_key(t) for t in part}) < 2:
                continue
            for token in part:
                if exact_key(token) not in grounded:
                    continue
                judged += 1
                prox["judged"] += 1
                v2 = proximity(token, part, index, words, leaf_keys, dotted)
                if v2 is None:
                    prox["near"] += 1
                    continue
                prox["demoted"] += 1
                prox["demoted_in_clean_leaves"] += clean
                prox_counts[v2] += 1
                prox_distinct.add(exact_key(token))
                if exact_key(token) not in listed:
                    listed.add(exact_key(token))
                    demoted.append({"kind": "name_token_not_near_its_name", "path": path,
                                    "name": name, "token": token, "class": v2,
                                    "v1_class": "grounded", "leaf_clean_under_v1": clean})
        prox["not_judged"] += counts_grounded - judged
    return {"checked": True, "instrument": INSTRUMENT, "name_leaves": leaves,
            "counts": counts, "distinct": {c: len(v) for c, v in distinct.items()},
            "findings": findings,
            "proximity": {"instrument": PROXIMITY_INSTRUMENT, "window": PROXIMITY_WINDOW,
                          **prox, "counts": prox_counts,
                          "demoted_distinct": len(prox_distinct), "demoted_tokens": demoted}}


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
