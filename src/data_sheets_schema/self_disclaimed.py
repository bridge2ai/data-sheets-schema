"""Typed-container entries whose own prose disclaims their role or presence (#2913).

A read-only lint that never gates. Each list member of a registered container
is read: `creators`, `maintainers` and `data_collectors` record a role, and
`variables`, `instances` and `splits` record that something is present in the
released data. The lint reads the member's own narrative leaves against a
versioned lexicon (`lexicons/self_disclaimed_v1.yaml`). It flags the member
when one of those leaves says the source does not establish that role or
presence: check (a). The lexicon is scoped, per pattern. A `role` cue counts
only where its clause names the container's own role, a role verb or a
role-assignment noun that no other thing owns: "the title of the award" and
"the position of the server" name the award's title and the server's
position, so they put nothing in scope, and a cue whose own assignment noun
is another thing's ("does not state the title of the award") is out of
scope whatever else its clause names (#3209). A `self` cue counts only where a self-reference to the
member precedes it in its own clause or, when that clause has no subject of
its own ("It is derived, but is not yet released"), earlier in the sentence.
A self-reference that a comma separates from the cue counts only when the
stretch after the last such comma has no subject of its own either: "Given
the consent terms, the raw recordings are not released" is about the
recordings (#3159). A `presence` cue counts where a `self` cue would or
where its clause names the container's own presence term outside the
cue's own words and outside the member's self-references: "Unlike the
planned splits for the next release, this split is complete" names no
presence term but the one `presence.planned_element` spells (#3230). A
presence term with no other-marker ("The external test set is described
as planned") is taken as possibly the member's, since the lint does not
know which item the member is. A `none` cue has
no further condition: `role.not_necessarily` names the container's role in
its cue, but `presence.prospective_predicate` counts whatever its clause's
subject is, so "the consent process is prospective" in an instance's prose
is flagged like "both statements are prospective". A clause whose words
name other people or organisations ("those individuals") never counts. In
a presence container, nor does a cue whose reported item names other items
of the container's kind ("Two other variables are not part of the public
release", "The remaining partitions ...", "No source reports the other
splits as available"); that second check reads the item alone, the cue's
subject or, where the pattern declares its object inside the cue, the
cue's `item` group, so "Unlike the other splits, this split is not
released" still counts (#3231, #3250). It is not applied to a person-role
container, where an active cue's subject is the source it cites: "These
data sets do not name her as a creator" is the member's disclaimer (#3249).
The member's own self-reference ("this member among the creators") is
blanked before both checks, so it is never read as someone else (#3156).
Nor does the role noun inside a self-reference put a clause in `role`
scope by itself: it counts only where the self-reference is the cue's own
object ("does not name this maintainer") and does not own it, so "this
author's institution is not stated" is out of scope as "her institution"
is (#3251).

A cue does not count where a guard shows that what it says is unstated is a
date, an amount, an attribute, a narrower sub-role or a study's design. The
date, amount and attribute guards read the cue's object. Each pattern
declares where that lies: after an active cue up to the phrase's end, in a
passive one's subject together with an `as` complement, or inside a cue
that ends on the role noun. A passive cue's subject leaves out an
appositive and anything before a comma: in "This split, planned for 2025,
is not yet released" what is unstated is the split, not the year (#3210),
while in "This split's 2025 release date is not yet available" it is the
date. So the source a sentence cites ("The website does not name her as a
creator", "The 2024 slide ...") and the cue's own verb ("do not credit her
as an author") are not read as the thing unstated (#3157, #3158). A role cue is read that narrowly only where its object
names the role itself; where the role that licenses it lies elsewhere in
the clause, the object is not located and the guards read the whole
clause, the cue's verb included. A sub-role
counts only as a complement ("as the corresponding author", "is the PI")
or as the modifier of a role noun or of a principal investigator ("a
principal investigator role", "the contact PI"), so "identify the contact
as the maintainer" disclaims the maintainer role of the member it calls
the contact (#3162). A guard never reads the member's own self-reference
("this contact") as one of those.

With a coverage receipt, the lint also reports check (b) in a bucket of its
own: each person-role member that no receipt snippet addressed to it names
in one of its container's role predicates.

Given the final record as well, the lint diffs the two. It follows each flag
on the original to the final by identity (`receipts.remap_path`, #899) and
classifies it:

- `removal_declared`: an audit finding's `remove_relationship` selects the
  member or an ancestor of it.
- `removed`: the final record no longer carries the entry.
- `named_by_finding`: a finding's `review_paths`, `remove_relationship` or
  `original_full` evidence paths name the member itself or one of its
  placement leaves (`id`, `name`, a maintainer's `role`, ...; the lexicon
  lists them per container).
- `identity_unresolved`: the entry cannot be followed to the final record.
- `self_disclaimed_retained`: none of the above.

A finding that names only the member's prose, a count or an affiliation is
about that value, not the placement. A flag counts as retained whether or
not its disclaimer text survived, because deleting a caveat does not dispose
of the entry. Check (b)'s flags are classified the same way, with
`role_predicate_retained` in place of `self_disclaimed_retained`.

A flag is not a semantic judgement. It says that the entry's own words
disclaim its placement. Whether the source supports the placement is review
work. Nothing reads this output as a gate. evidence_assertions,
anonymous_removals, audit_grammar, source_review and receipts do not import
this module, so their import closures are unchanged.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import yaml

INSTRUMENT = "self_disclaimed v1 (#2913)"
LEXICON_PATH = Path(__file__).parent / "lexicons" / "self_disclaimed_v1.yaml"
LEXICON_RESOURCE = "src/data_sheets_schema/lexicons/self_disclaimed_v1.yaml"
KINDS = ("person_role", "presence")
SCOPES = ("role", "presence", "self", "none")
# What a guard reads, and where a pattern's object lies (the lexicon's
# `reads` and `object` keys; see its guards comment).
GUARD_READS = ("clause", "before_cue", "cue", "after_phrase", "object")
OBJECT_PARTS = ("before_cue", "subject", "cue", "after_phrase", "as_phrase")
CLASSIFICATIONS = ("removal_declared", "removed", "named_by_finding", "identity_unresolved")
NON_CHECKS = (
    "whether the source supports the placement: a flag reads the member's own words, never the bundle",
    "prose outside the member's own narrative leaves: nested objects and other members are not read",
    "check (b) reads only receipt snippets addressed to the member, so a listed author whose snippet "
    "quotes only a name is flagged; receipt coverage is partial",
    "whether a finding that names a member justifies keeping it: the audit grammar has no "
    "keep-justification form",
)

_SENTENCE = re.compile(r"(?<=[.!?;:])\s+")
_CLAUSE = re.compile(r",\s+(?=(?:and|but|so|while|whereas|because|although|though|since)\b)", re.I)
# The text a clause opens with before its cue when its subject is elided:
# the conjunction, at most a subject pronoun, adverbs and auxiliaries ("but
# is not yet released", "and it has not been released", "but so far is not
# released", "but is not named as a creator"). A clause with a subject of its
# own ("but the raw images are not released") is about that subject.
_ELIDED = re.compile(
    r"(?:(?:and|but|so|while|whereas|because|although|though|since)\s+)?(?:(?:it|he|she)\s+)?"
    r"(?:(?:still|also|yet|currently|however|therefore|thus|so far|as yet)\s+)*"
    r"(?:(?:is|are|was|were|has|have|had|been|be)\s+)*", re.I)
# Where the phrase after a cue ends: punctuation, a coordinating
# conjunction, a contrast or a subordinator. "does not name her as an author
# and gives no ORCID": the ORCID is not what the cue says is unstated.
_PHRASE_END = re.compile(r"[,;:.]|\b(?:and|or|but|nor|rather|because|since|while|whereas|although|though)\b",
                         re.I)
_EXCERPT = 240


@dataclass(frozen=True)
class Pattern:
    id: str
    cls: str
    kinds: frozenset
    cue: str
    scope: str
    guards: tuple
    object: tuple = ()  # where the thing the cue says is unstated lies (OBJECT_PARTS)


@dataclass(frozen=True)
class Container:
    name: str
    kind: str
    narrative_fields: frozenset
    placement_fields: frozenset    # leaves through which a finding names the placement
    cues: tuple                    # (Pattern, compiled cue) for this container
    role_scope: re.Pattern | None  # role terms, role verbs or assignment nouns
    role_words: re.Pattern | None  # role terms or role verbs: an owner that is the member's
    presence_scope: re.Pattern | None
    role_predicates: re.Pattern | None


def _alternation(terms) -> str:
    if not isinstance(terms, list) or not terms or not all(isinstance(t, str) and t for t in terms):
        raise ValueError("a lexicon term list must be a nonempty list of patterns")
    return "|".join(f"(?:{t})" for t in terms)


def _word(terms) -> re.Pattern:
    return re.compile(rf"\b(?:{_alternation(terms)})\b", re.I)


class Lexicon:
    """The lexicon file, parsed and compiled. `sha256` is of its exact bytes,
    so a run's output names the instrument that produced it."""

    def __init__(self, raw: bytes, *, path: str | None = None):
        data = yaml.safe_load(raw.decode("utf-8"))
        if not isinstance(data, dict) or data.get("instrument") != "self_disclaimed":
            raise ValueError("not a self_disclaimed lexicon")
        if type(data.get("version")) is not int:
            raise ValueError("the lexicon needs an integer version")
        self.version = data["version"]
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.path = path
        narrative = data["narrative"]
        self._fields = frozenset(narrative["fields"])
        self._suffixes = tuple(narrative["suffixes"])
        placement = frozenset(data["placement"]["fields"])
        self._self = [re.compile(p, re.I) for p in data["self_reference"]]
        self._other = [re.compile(p, re.I) for p in data["other_subject"]]
        self._other_item = [re.compile(p, re.I) for p in data["other_item_subject"]]
        self._guards = {}
        for name, guard in data["guards"].items():
            if guard.get("reads") not in GUARD_READS:
                raise ValueError(f"guard {name} must read one of {', '.join(GUARD_READS)}")
            self._guards[name] = (guard["reads"], re.compile(guard["regex"], re.I))
        assignment = data["assignment_nouns"]
        self._assignment = _word(assignment)
        owner = data["assignment_owner"]
        if type(owner.get("words")) is not int or owner["words"] < 1:
            raise ValueError("assignment_owner.words must be a positive integer")
        self._owner_after = re.compile(owner["after"], re.I)
        self._owner_words = owner["words"]
        self._owner_member = _word(owner["member_words"])
        self._owner_held_in = _word(owner["held_in_words"])
        if self._owner_after.groups != 1:
            raise ValueError("assignment_owner.after must capture its preposition as its one group")
        patterns = []
        for row in data["patterns"]:
            kinds = frozenset(row["kinds"])
            if not kinds <= set(KINDS) or row["scope"] not in SCOPES:
                raise ValueError(f"pattern {row.get('id')} names an unknown kind or scope")
            if set(row["guards"]) - set(self._guards):
                raise ValueError(f"pattern {row['id']} names an unknown guard")
            parts = tuple(row.get("object") or ())
            if set(parts) - set(OBJECT_PARTS):
                raise ValueError(f"pattern {row['id']} declares an object outside {', '.join(OBJECT_PARTS)}")
            if not parts and any(self._guards[g][0] == "object" for g in row["guards"]):
                raise ValueError(f"pattern {row['id']} has a guard that reads its object but declares none")
            patterns.append(Pattern(row["id"], row["class"], kinds, row["cue"],
                                    row["scope"], tuple(row["guards"]), parts))
        if len({p.id for p in patterns}) != len(patterns):
            raise ValueError("pattern ids must be unique")
        self.patterns = tuple(patterns)
        self.containers = {}
        for name, spec in data["containers"].items():
            kind = spec["kind"]
            if kind not in KINDS:
                raise ValueError(f"container {name} has unknown kind {kind!r}")
            role = words = presence = predicates = None
            fill = {}
            if kind == "person_role":
                fill["role"] = _alternation(spec["role_terms"])
                role = _word(spec["role_terms"] + spec["role_verbs"] + assignment)
                words = _word(spec["role_terms"] + spec["role_verbs"])
                predicates = _word(spec["role_predicates"])
            else:
                fill["presence"] = _alternation(spec["presence_terms"])
                presence = _word(spec["presence_terms"])
            cues = []
            for p in patterns:
                if kind in p.kinds:
                    cue = re.sub(r"\{(role|presence)\}", lambda m: fill[m.group(1)], p.cue)
                    cues.append((p, re.compile(cue, re.I)))
            self.containers[name] = Container(
                name, kind, self._fields | frozenset(spec.get("narrative_fields") or ()),
                placement | frozenset(spec.get("placement_fields") or ()),
                tuple(cues), role, words, presence, predicates)

    def is_narrative(self, container: Container, key: Any) -> bool:
        return isinstance(key, str) and (key in container.narrative_fields
                                         or key.endswith(self._suffixes))

    def describe(self) -> dict:
        return {"path": self.path, "version": self.version, "sha256": self.sha256}


def load_lexicon(path: Path = LEXICON_PATH) -> Lexicon:
    """The registered lexicon, or another lexicon file a test names. The
    registered one is named by its repository-relative spelling wherever
    the package is installed."""
    shown = LEXICON_RESOURCE if path == LEXICON_PATH else str(path)
    return Lexicon(path.read_bytes(), path=shown)


# ------------------------------------------------------------------ paths
def pointer(tokens) -> str:
    return "".join("/" + str(t).replace("~", "~0").replace("/", "~1") for t in tokens)


def parse_pointer(value: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value.startswith("/") or re.search(r"~(?![01])", value):
        raise ValueError(f"not a JSON Pointer: {value!r}")
    return tuple(part.replace("~1", "/").replace("~0", "~") for part in value[1:].split("/"))


def _dotted(tokens) -> str:
    out = ""
    for t in tokens:
        out += f"[{t}]" if isinstance(t, int) else (f".{t}" if out else str(t))
    return out


def _undotted(path: str) -> tuple:
    return tuple(int(p[1:-1]) if p.startswith("[") else p for p in re.findall(r"\w+|\[\d+\]", path))


def members(record: Any, lexicon: Lexicon) -> Iterator[tuple[tuple, Container, dict]]:
    """Every object member of a registered container, at any depth (a nested
    `resources[*]` or `subsets[*]` dataset carries the same slots)."""
    def walk(value, tokens, ancestors):
        if isinstance(value, (dict, list)):
            if id(value) in ancestors:
                raise ValueError("cyclic record")
            ancestors = ancestors | {id(value)}
        if isinstance(value, dict):
            for key, child in value.items():
                spec = lexicon.containers.get(key) if isinstance(key, str) else None
                if spec is not None and isinstance(child, list):
                    for i, member in enumerate(child):
                        if isinstance(member, dict):
                            yield tokens + (key, i), spec, member
                yield from walk(child, tokens + (key,), ancestors)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                yield from walk(child, tokens + (i,), ancestors)
    yield from walk(record, (), frozenset())


# ---------------------------------------------------------------- check (a)
def _clause(sentence: str, at: int) -> tuple[int, int]:
    start, end = 0, len(sentence)
    for m in _CLAUSE.finditer(sentence):
        if m.end() <= at:
            start = m.end()
        elif m.start() >= at:
            end = m.start()
            break
    return start, end


def _search(patterns, *texts) -> str | None:
    for text in texts:
        for rx in patterns:
            m = rx.search(text)
            if m:
                return m.group(0)
    return None


def _own_names(member: dict) -> list[re.Pattern]:
    """The member's own name as a self-reference: in full, and by its last
    word when the name reads as a personal name (two to four capitalized
    words) and that word has at least four letters ("Jane Dough" ->
    "Dough"). A shorter last word is too often an ordinary word or an
    initialism, so "Jane Doe" or "Wei Li" is a self-reference only in full:
    "Doe is not a creator" is out of scope for lack of one."""
    out = []
    for key in ("name", "variable_name"):
        name = member.get(key)
        if not isinstance(name, str) or len(name.strip()) < 3:
            continue
        name = " ".join(name.split())
        out.append(re.compile(rf"\b{re.escape(name)}\b", re.I))
        words = name.split()
        if 2 <= len(words) <= 4 and all(w[:1].isupper() for w in words) and len(words[-1]) >= 4:
            out.append(re.compile(rf"\b{re.escape(words[-1])}\b"))
    return out


def _masked(sentence: str, selves) -> str:
    """The sentence with the member's own self-references blanked, offsets
    kept, for the guards: in "which category of maintainer this contact
    represents is not stated", "this contact" is the member, not a narrower
    sub-role (#3080)."""
    chars = list(sentence)
    for rx in selves:
        for found in rx.finditer(sentence):
            chars[found.start():found.end()] = " " * (found.end() - found.start())
    return "".join(chars)


_POSSESSIVE_AFTER = re.compile(r"['\u2019]s?\b|['\u2019](?=\s)")
_POSSESSIVE_BEFORE = re.compile(r"\b(?:of|for)\s+$", re.I)


def _possessors_blanked(sentence: str, selves) -> str:
    """The sentence with those of the member's self-references blanked that
    own something rather than name the member: a possessive ("this author's
    institution") or the object of `of`/`for` ("the email of this author").
    Offsets are kept. What is unstated there is the possessed thing, so the
    role noun inside the self-reference does not name the role (#3251);
    "does not name this maintainer" keeps its self-reference."""
    chars = list(sentence)
    for rx in selves:
        for found in rx.finditer(sentence):
            if (_POSSESSIVE_AFTER.match(sentence, found.end())
                    or _POSSESSIVE_BEFORE.search(sentence[:found.start()])):
                chars[found.start():found.end()] = " " * (found.end() - found.start())
    return "".join(chars)


def _item_text(pattern, parts: dict[str, str], masked: str, m) -> str:
    """Where a presence cue names the item it says is unstated, for the
    other-item check: the cue's `item` group when the pattern declares its
    object inside the cue ("No source reports <the other splits> as
    available", #3250), the whole cue when that pattern has no such group,
    and otherwise the cue's subject."""
    if "cue" in pattern.object:
        if "item" in m.re.groupindex and m.start("item") >= 0:
            return masked[m.start("item"):m.end("item")]
        return parts["cue"]
    return parts["subject"]


def _own_self_reference(selves, text: str) -> str | None:
    """The first self-reference in `text` (the cue's clause up to the cue)
    that the cue is about. One a comma separates from the cue counts only
    when the stretch after the last such comma has no subject of its own:
    "Given the consent terms, the raw recordings are not released" and
    "Listed in the manifest, the waveforms are not released" are about the
    recordings and the waveforms, while "This variable, per the codebook, is
    not released" is about the variable (#3159)."""
    for rx in selves:
        for found in rx.finditer(text):
            tail = text[found.end():]
            if "," in tail and _ELIDED.fullmatch(tail.rsplit(",", 1)[1].lstrip()) is None:
                continue
            return found.group(0)
    return None


def _self_reference(selves, sentence: str, c0: int, at: int) -> str | None:
    """A self-reference that makes the cue at `at` about the member: one in
    the cue's own clause before it or, when that clause has no subject of
    its own, one earlier in the sentence. "This split is balanced, but the
    raw images are not released" is about the images (#3082)."""
    own = _own_self_reference(selves, sentence[c0:at])
    if own is not None or c0 == 0:
        return own
    if _ELIDED.fullmatch(sentence[c0:at]) is None:
        return None
    return _search(selves, sentence[:at])


def _subject(before: str) -> tuple[int, int]:
    """Where a passive cue's subject lies in `before` (its clause up to the
    cue, unmasked): an appositive that closes on a comma right before the
    cue is left out, and so is anything before the last comma that remains.
    "This split, planned for 2025, " -> "This split"; "Per the 2024 slide,
    this split " -> "this split"; "This split's 2025 release date " is
    itself (#3210). Read on the unmasked text, since a blanked
    self-reference would look like an empty stretch."""
    cuts = [0] + [i + 1 for i, ch in enumerate(before) if ch == ","] + [len(before) + 1]
    spans = [(cuts[k], cuts[k + 1] - 1) for k in range(len(cuts) - 1)]
    if len(spans) >= 2 and not before[spans[-1][0]:spans[-1][1]].strip():
        return spans[-3] if len(spans) > 2 else spans[0]
    return spans[-1]


def _parts(masked: str, c0: int, c1: int, m, raw: str | None = None) -> dict[str, str]:
    """The pieces of the cue's clause a guard or an object can name, read
    from the masked sentence: `clause`, `before_cue`, `subject` (a passive
    cue's subject, `_subject`, located on `raw`, the unmasked sentence),
    `cue`, `after_phrase` (after the cue up to the phrase's end,
    `_PHRASE_END`) and `as_phrase` (`after_phrase` when it opens on `as`,
    else empty)."""
    after = masked[m.end():c1]
    end = _PHRASE_END.search(after)
    phrase = after[:end.start()] if end else after
    before = masked[c0:m.start()]
    s0, s1 = _subject((raw if raw is not None else masked)[c0:m.start()])
    return {"clause": masked[c0:c1], "before_cue": before, "subject": before[s0:s1],
            "cue": masked[m.start():m.end()], "after_phrase": phrase,
            "as_phrase": phrase if re.match(r"\s*as\b", phrase, re.I) else ""}


def _owned_by_other(lexicon, container, sentence: str, masked: str, noun) -> str | None:
    """The preposition and owner phrase when another thing owns the
    assignment noun `noun` (a match in `sentence`): "title of the award" ->
    "of the award". None when the noun has no `of`/`for` owner, or its
    owner is the member: one of its own self-references (blanked in
    `masked`), a role term or verb, or a member word ("a role for her", "the
    category of maintainer", "a role for this person"), or, after `for`,
    what a role is held in ("credit roles for the dataset") (#3209)."""
    after = lexicon._owner_after.match(sentence, noun.end())
    if after is None:
        return None
    rest = sentence[after.end():]
    end = _PHRASE_END.search(rest)
    owner = " ".join((rest[:end.start()] if end else rest).split()[:lexicon._owner_words])
    if not owner:
        return None
    if masked[after.end():after.end() + len(owner)] != sentence[after.end():after.end() + len(owner)]:
        return None
    if lexicon._owner_member.search(owner) or container.role_words.search(owner):
        return None
    preposition = after.group(1).lower()
    if preposition == "for" and lexicon._owner_held_in.search(owner):
        return None
    return f"{preposition} {owner}"


def _role_scope(lexicon, container, sentence: str, masked: str, c0: int, c1: int, m,
                objects=()) -> tuple[str, str]:
    """(`scope`, term) for a `role` cue: the first role term, role verb or
    member-owned assignment noun in its clause, or (`out_of_scope` reason,
    term) when there is none or the cue's own assignment noun is another
    thing's (#3209). The clause is read with the member's self-references
    blanked, so the role noun in "this author" puts nothing in scope by
    itself: "For this creator, the dataset license is not stated" names no
    role. A self-reference counts only inside the cue's own object
    (`objects`, possessor self-references already blanked), where it is what
    the cue says is unstated: "does not name this maintainer" (#3251)."""
    for noun in lexicon._assignment.finditer(sentence, m.start(), m.end()):
        owner = _owned_by_other(lexicon, container, sentence, masked, noun)
        if owner is not None:
            return "assignment_noun_of_other", f"{noun.group(0)} {owner}"
    foreign = None
    for found in container.role_scope.finditer(masked, c0, c1):
        if lexicon._assignment.fullmatch(found.group(0)):
            owner = _owned_by_other(lexicon, container, sentence, masked, found)
            if owner is not None:
                foreign = foreign or f"{found.group(0)} {owner}"
                continue
        return "scope", found.group(0)
    found = _search([container.role_words], *objects)
    if found:
        return "scope", found
    return ("assignment_noun_of_other", foreign) if foreign else ("no_role_term", None)


def _object_texts(pattern, container, raw: dict[str, str], masked: dict[str, str]) -> list[str]:
    """The texts naming what the cue says is unstated, as the pattern
    declares them, read masked: `subject` (a passive cue's subject;
    `before_cue`, the whole clause before a cue, is also accepted), `cue` (a cue that ends on the role noun: "does not state a credit
    role"), `after_phrase` (an active cue's object) and `as_phrase` (the
    `as` complement after a passive cue: "are not recorded as creator
    affiliations"). The source a sentence cites is an active cue's subject
    and is not read. A role cue is read this narrowly only where its object
    names the role itself (read with only possessor self-references blanked,
    so "this maintainer" names one and "this author's institution" does
    not, #3251).
    Where the role that licenses it lies elsewhere in the clause ("the
    author affiliations ... do not name the Hastings Center", "No source
    names a further creating team, assigns CRediT roles, ...") what the cue
    says is unstated is not located, and the guard reads the whole clause."""
    if pattern.scope == "role" and not any(container.role_scope.search(raw[p]) for p in pattern.object):
        return [masked["clause"]]
    return [masked[p] for p in pattern.object]


def _presence_text(pattern, masked: str, c0: int, c1: int, m) -> str:
    """Where a `presence` cue's clause is searched for the container's
    presence term: the masked clause, so a term inside one of the member's
    own self-references ("this split") is not a second licence for a cue the
    self-reference rule rejected, with the cue's own span blanked. A term the
    cue itself spells cannot fail to be there: `presence.planned_element`
    ends on the planned noun, so "Unlike the planned splits for the next
    release, this split is complete" names no presence term of its own
    (#3230). A pattern that declares its object inside the cue (`object:
    [cue]`) keeps the cue, whose free span names the item it reports ("No
    source reports the holdout set as available")."""
    if "cue" in pattern.object:
        return masked[c0:c1]
    return masked[c0:m.start()] + " " * (m.end() - m.start()) + masked[m.end():c1]


def _judge(lexicon, container, member, pattern, sentence, m) -> dict:
    """One cue match: a flag hit, a guarded hit, or out of scope, with why."""
    c0, c1 = _clause(sentence, m.start())
    out = {"rule": pattern.id, "class": pattern.cls, "cue": m.group(0)}
    selves = lexicon._self + _own_names(member)
    masked = _masked(sentence, selves)
    # The clause is about someone or something else ("those individuals ...
    # rather than as creators"): its wording disclaims nothing of the member.
    # Read with the member's own self-references blanked: "this member among
    # the creators" is the member, not a group of other people (#3156).
    other = _search(lexicon._other, masked[c0:m.start()], masked[c0:c1])
    if other:
        return {**out, "outcome": "out_of_scope", "reason": "other_subject", "term": other}
    # The item a presence cue says is unstated names other items of the
    # container's kind ("Two other variables are not part of the public
    # release", "No source reports the other splits as available"), read in
    # that item alone: "Unlike the other splits, this split is not released"
    # is about the member (#3231). Only a presence container's: a role cue's
    # subject is the source it cites, not another item (#3249, #3250).
    parts = _parts(masked, c0, c1, m, sentence)
    if container.kind == "presence":
        other = _search(lexicon._other_item, _item_text(pattern, parts, masked, m))
        if other:
            return {**out, "outcome": "out_of_scope", "reason": "other_subject", "term": other}
    # The object read with only the member's possessor self-references
    # blanked ("this author's institution", "the email of this author"): a
    # self-reference that is itself the object ("does not name this
    # maintainer") names the role, one that owns the object does not (#3251).
    objects = _parts(_possessors_blanked(sentence, selves), c0, c1, m, sentence)
    if pattern.scope == "role":
        verdict, term = _role_scope(lexicon, container, sentence, masked, c0, c1, m,
                                    [objects[p] for p in pattern.object])
        if verdict != "scope":
            return {**out, "outcome": "out_of_scope", "reason": verdict,
                    **({"term": term} if term else {})}
        out["scope"] = term
    elif pattern.scope == "presence":
        term = _self_reference(selves, sentence, c0, m.start())
        if term is None:
            found = container.presence_scope.search(_presence_text(pattern, masked, c0, c1, m))
            term = found.group(0) if found else None
        if term is None:
            return {**out, "outcome": "out_of_scope", "reason": "no_self_or_presence_term"}
        out["scope"] = term
    elif pattern.scope == "self":
        term = _self_reference(selves, sentence, c0, m.start())
        if term is None:
            return {**out, "outcome": "out_of_scope", "reason": "no_self_reference"}
        out["scope"] = term
    read = {k: [parts[k]] for k in ("clause", "before_cue", "cue", "after_phrase")}
    read["object"] = _object_texts(pattern, container, objects, parts)
    for name in pattern.guards:
        reads, rx = lexicon._guards[name]
        for text in read[reads]:
            found = rx.search(text)
            if found:
                return {**out, "outcome": "guarded", "guard": name, "term": found.group(0)}
    return {**out, "outcome": "flag"}


def _texts(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def scan(record: Any, lexicon: Lexicon | None = None) -> dict:
    """Check (a) over one record: `flags` (one entry per flagged member, with
    its hits), `guarded` and `out_of_scope` (cue matches that did not count,
    with why), and the number of members read."""
    lexicon = lexicon or load_lexicon()
    flags, guarded, out_of_scope, count = [], [], [], 0
    for tokens, container, member in members(record, lexicon):
        count += 1
        hits = []
        for key, value in member.items():
            if not lexicon.is_narrative(container, key):
                continue
            for text in _texts(value):
                for sentence in _SENTENCE.split(" ".join(text.split())):
                    for pattern, cue in container.cues:
                        for m in cue.finditer(sentence):
                            row = _judge(lexicon, container, member, pattern, sentence, m)
                            row.update(leaf=pointer(tokens + (key,)), sentence=sentence[:_EXCERPT])
                            outcome = row.pop("outcome")
                            if outcome == "flag":
                                hits.append(row)
                            else:
                                (guarded if outcome == "guarded" else out_of_scope).append(
                                    {"path": pointer(tokens), **row})
        if hits:
            flags.append({"path": pointer(tokens), "container": container.name,
                          "kind": container.kind, "hits": hits})
    return {"members_read": count, "flags": flags, "guarded": guarded, "out_of_scope": out_of_scope}


# ---------------------------------------------------------------- check (b)
def role_predicates(record: Any, receipt: dict, lexicon: Lexicon | None = None) -> dict:
    """Check (b): each person-role member is flagged when no `extracted`
    receipt snippet addressed to it (its own path or a path beneath it)
    carries a role predicate of its container — `no_receipt` when no
    snippet is addressed to it at all, `no_role_predicate` otherwise. Run
    it on the record the receipt was written against."""
    lexicon = lexicon or load_lexicon()
    snippets: list[tuple[str, str]] = []
    for entry in receipt.get("chunks") or []:
        if isinstance(entry, dict) and entry.get("status") == "extracted":
            for pair in entry.get("extracted") or []:
                if isinstance(pair, dict) and isinstance(pair.get("snippet"), str):
                    snippets.append((str(pair.get("slot", "")), " ".join(pair["snippet"].split())))
    flags, supported, count = [], 0, 0
    for tokens, container, _member in members(record, lexicon):
        if container.kind != "person_role":
            continue
        count += 1
        path = _dotted(tokens)
        mine = [s for slot, s in snippets
                if slot == path or slot.startswith(path + ".") or slot.startswith(path + "[")]
        if mine and any(container.role_predicates.search(s) for s in mine):
            supported += 1
            continue
        flags.append({"path": pointer(tokens), "container": container.name,
                      "reason": "no_role_predicate" if mine else "no_receipt",
                      "snippets_addressed": len(mine)})
    return {"members_read": count, "supported": supported, "flags": flags}


# ----------------------------------------------------------------- the diff
def _finding_pointers(audit: Any) -> tuple[list, list, int]:
    """(removals, naming, unreadable): each a list of (finding index, tokens).
    A finding names a path through `review_paths`, `remove_relationship` and
    its `original_full` evidence; other artifacts index other records."""
    if not isinstance(audit, dict) or not isinstance(audit.get("findings"), list):
        raise ValueError("audit.findings must be an array")
    removals, naming, unreadable = [], [], 0

    def take(index, value, into):
        nonlocal unreadable
        try:
            tokens = parse_pointer(value)
        except ValueError:
            unreadable += 1
            return
        for target in into:
            target.append((index, tokens))

    for index, finding in enumerate(audit["findings"]):
        if not isinstance(finding, dict):
            continue
        rule = finding.get("remove_relationship")
        if isinstance(rule, dict) and "path" in rule:
            take(index, rule["path"], (removals, naming))
        paths = finding.get("review_paths")
        for value in paths if isinstance(paths, list) else []:
            take(index, value, (naming,))
        evidence = finding.get("evidence")
        for entry in evidence if isinstance(evidence, list) else []:
            if isinstance(entry, dict) and entry.get("artifact") == "original_full" and "path" in entry:
                if entry["path"] != "@header":
                    take(index, entry["path"], (naming,))
    return removals, naming, unreadable


def _names_member(member: tuple, named: tuple, container: Container) -> bool:
    """The finding path is the member, or runs through one of its placement
    leaves (`/creators/1/name`, `/maintainers/0/role`). A path to its prose
    (`/maintainers/0/source_caveats`) names what the prose says, not the
    placement: v3's bundle-wide-absence finding named that caveat, and
    reconciliation deleted the caveat and kept the entry (#2913)."""
    if named == member:
        return True
    return (len(named) > len(member) and named[:len(member)] == member
            and named[len(member)] in container.placement_fields)


def _follow(tokens: tuple, original: Any, final: Any) -> tuple[tuple | None, str]:
    """Where the member sits in the final record, joined by identity.

    The member is `removed` when it, or any ancestor of it, is gone from the
    final record or holds null or an empty list there: its own container,
    or a list further up (a nested member under `resources: null`, #3088).
    The nearest ancestor that resolves decides; when it is present and not
    empty, the member is `identity_unresolved` with remap_path's basis."""
    from data_sheets_schema.receipts import remap_path
    moved = remap_path(_dotted(tokens), original, final)
    if moved["path"] is not None:
        return _undotted(moved["path"]), moved["basis"]
    if moved["basis"] in ("entry_dropped", "leaf_dropped"):
        return None, "removed"
    for depth in range(len(tokens) - 1, 0, -1):
        holder = remap_path(_dotted(tokens[:depth]), original, final)
        if holder["path"] is None:
            if holder["basis"] in ("entry_dropped", "leaf_dropped"):
                return None, "removed"
            continue
        value: Any = final
        for t in _undotted(holder["path"]):
            value = value[t]
        if value is None or value == []:
            return None, "removed"
        break
    return None, moved["basis"]


def classify(flags: list, original: Any, final: Any, *, audit: Any = None,
             final_flags: list | None = None, retained: str = "self_disclaimed_retained",
             lexicon: Lexicon | None = None) -> dict:
    """Each flag on the original, followed to the final and classified."""
    lexicon = lexicon or load_lexicon()
    removals, naming, unreadable = _finding_pointers(audit) if audit is not None else ([], [], 0)
    still = {f["path"] for f in final_flags or []}
    rows, counts = [], {k: 0 for k in (*CLASSIFICATIONS, retained)}
    for flag in flags:
        tokens = parse_pointer(flag["path"])
        member = tuple(int(t) if re.fullmatch(r"0|[1-9][0-9]*", t) else t for t in tokens)
        container = lexicon.containers[flag["container"]]
        where, basis = _follow(member, original, final)
        declared = sorted({i for i, p in removals if len(p) <= len(tokens) and tokens[:len(p)] == p})
        named = sorted({i for i, p in naming if _names_member(tokens, p, container)})
        if declared:
            outcome = "removal_declared"
        elif where is None and basis == "removed":
            outcome = "removed"
        elif where is None:
            outcome = "identity_unresolved"
        elif named:
            outcome = "named_by_finding"
        else:
            outcome = retained
        counts[outcome] += 1
        final_path = pointer(where) if where is not None else None
        row = {"path": flag["path"], "container": flag["container"], "classification": outcome,
               "final_path": final_path, "identity_basis": basis,
               "findings_declaring_removal": declared, "findings_naming_member": named}
        if final_flags is not None:
            row["still_flagged_in_final"] = final_path in still if final_path else False
        rows.append(row)
    return {"rows": rows, "counts": counts, "audit_pointers_unreadable": unreadable}


def diff(original: Any, final: Any, *, audit: Any = None, receipt: dict | None = None,
         lexicon: Lexicon | None = None) -> dict:
    """The original-to-final diff of check (a) and, with a receipt, of check
    (b). `final_only` lists final flags no original flag maps to."""
    lexicon = lexicon or load_lexicon()
    before, after = scan(original, lexicon), scan(final, lexicon)
    lexical = classify(before["flags"], original, final, audit=audit,
                       final_flags=after["flags"], lexicon=lexicon)
    mapped = {row["final_path"] for row in lexical["rows"] if row["final_path"]}
    out = {"original": before, "final": after, "lexicon_diff": lexical,
           "final_only": [f["path"] for f in after["flags"] if f["path"] not in mapped]}
    if receipt is not None:
        checked = role_predicates(original, receipt, lexicon)
        out["role_predicate"] = checked
        out["role_predicate_diff"] = classify(checked["flags"], original, final, audit=audit,
                                              retained="role_predicate_retained", lexicon=lexicon)
    return out


# ------------------------------------------------------------------ files
def check_files(original: Path, final: Path | None = None, audit: Path | None = None,
                receipt: Path | None = None, *, lexicon: Lexicon | None = None) -> dict:
    """The report `d4d review self-disclaimed` prints. Reads exactly the
    files named, records each one's sha256, and writes nothing. `gating` is
    always false. A record with duplicate mapping keys is refused: which
    value a path names would be ambiguous."""
    from data_sheets_schema.evidence_assertions import load_json, load_record
    from data_sheets_schema.receipts import load_receipt
    if audit is not None and final is None:
        raise ValueError("an audit is read against an original/final pair; pass the final record too")
    lexicon = lexicon or load_lexicon()
    inputs: dict[str, dict] = {}

    def read(name, path, parse):
        if path is None:
            return None
        raw = path.read_bytes()
        inputs[name] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
        try:
            return parse(raw)
        except (ValueError, yaml.YAMLError) as exc:
            raise ValueError(f"{name} {path}: {exc}") from exc

    before = read("original", original, lambda raw: load_record(raw.decode("utf-8")))
    after = read("final", final, lambda raw: load_record(raw.decode("utf-8")))
    parsed_audit = read("audit", audit, load_json)
    parsed_receipt = read("receipt", receipt, lambda raw: load_receipt(receipt, raw=raw))
    out = {"instrument": INSTRUMENT, "lexicon": lexicon.describe(), "gating": False,
           "inputs": inputs, "non_checks": list(NON_CHECKS)}
    if after is None:
        out["original"] = scan(before, lexicon)
        if parsed_receipt is not None:
            out["role_predicate"] = role_predicates(before, parsed_receipt, lexicon)
    else:
        out.update(diff(before, after, audit=parsed_audit, receipt=parsed_receipt, lexicon=lexicon))
    out["counts"] = _counts(out)
    return out


def _counts(out: dict) -> dict:
    counts = {"original_flags": len(out["original"]["flags"]),
              "original_guarded": len(out["original"]["guarded"]),
              "original_out_of_scope": len(out["original"]["out_of_scope"])}
    if "final" in out:
        counts["final_flags"] = len(out["final"]["flags"])
        counts["final_only"] = len(out["final_only"])
        counts["lexicon_diff"] = out["lexicon_diff"]["counts"]
    if "role_predicate" in out:
        counts["role_predicate_flags"] = len(out["role_predicate"]["flags"])
    if "role_predicate_diff" in out:
        counts["role_predicate_diff"] = out["role_predicate_diff"]["counts"]
    return counts
