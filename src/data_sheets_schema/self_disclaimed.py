"""Typed-container entries whose own prose disclaims their role or presence (#2913).

A read-only lint that never gates. Design rule (#3625-#3628): v2 departs
from v1 only in the cases #3131, #3244, #3261 and #3273 name, each with a
named reason (the v2 lexicon's header lists them); for every other
sentence its verdict equals v1's, and a differential table in the tests
asserts that for every regression example. Each list member of a registered container
is read: `creators`, `maintainers` and `data_collectors` record a role, and
`variables`, `instances` and `splits` record that something is present in the
released data. The lint reads the member's own narrative leaves against a
versioned lexicon (`container_lexicons/self_disclaimed_v2.yaml`; v1 beside it
still loads, and this code reads it as v1 did, since every rule v2 adds is
declared in v2's file). It flags the member
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
recordings (#3159). A subject pronoun right before a cue that opens on its
auxiliary is such a self-reference: "This is not yet released", "After
review, it is not yet released" (#3265). A `presence` cue counts where a `self` cue would or
where its clause names the container's own presence term outside the
cue's own words and outside the member's self-references: "Unlike the
planned splits for the next release, this split is complete" names no
presence term but the one `presence.planned_element` spells (#3230). A
pattern that declares `self_reference_in: [item]` also counts on a
self-reference that heads the item it reports: "No source reports this
split as available" (#3261), not "the labels in this split" (#3607), and
not where the source-to-report span is negated (`self_reference_unless`:
"No source fails to report this split as available", #3625). A presence term with no other-marker ("The external
test set is described as planned") is taken as possibly the member's
unless its qualifier disagrees with the member's identity: in the prose of
a member named "Internal validation set" it is another item, on the
lexicon's external/internal and training/validation/test axes (#3244),
unless the item also names the member ("This split and the external test
set are not yet released", #3626). A
`subject` cue (`presence.prospective_predicate`, #3131) counts where a
self-reference that owns nothing precedes it, as a `self` cue would, and
heads the subject if the subject holds one, or where its subject is headed
by a source statement ("Both statements are prospective on that page") or
the container's presence term. A head has at most three words before it,
none a preposition or participle (#3560), nothing possessive after it and
nothing after it that it only modifies (#3592, #3606), so "The consent
process is prospective", "The consent process described in both
statements", "The labels in this split" and "The split labels" are out of
scope. A subject that opens on a negating determiner ("Neither statement",
"None of the statements", "No statements") says nothing it names is
prospective and is out of scope (`negated_subject`, #3614). The subject
these checks and the date/amount guard read is the cue's own conjunct: a
comma-less clause joined before it by a conjunction after an auxiliary or
copula ("Its release is pending and this split remains prospective") is
left out (`statement_subject.conjunction`, `clause_verb`, #3619), and a
conjunct with no subject of its own inherits the governing one ("The
holdout set was announced and remains prospective", #3627). "Not only
this split but also the holdout set" is affirmative coordination, not a
negated subject (`statement_subject.correlative`, #3628). A statement
topic ("statements about/of/for ...", #3615) must itself be headed by a
self-reference or presence term. A `none` cue has no further
condition: `role.not_necessarily` names the container's role in its cue.
A clause whose words
name other people or organisations ("those individuals") never counts. In
a presence container, nor does a cue whose reported item names other items
of the container's kind ("Two other variables are not part of the public
release", "The remaining partitions ...", "No source reports the other
splits as available"); that second check reads the item alone, the cue's
subject or, where the pattern declares its object as the cue's `item`
group, that group, so "Unlike the other splits, this split is not
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
passive one's subject together with an `as` complement, inside a cue
that ends on the role noun, or in the `item` group of a cue that cites its
source ("No source from 2024 reports <the holdout set> as available": the
year dates the source, not the split, #3265). A passive cue's subject leaves out an
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
- `identity_unresolved`: the entry cannot be followed to the final record:
  remap_path cannot place it, the entry it was followed to carries
  conflicting identity keys (`identity_conflict`: an overlap join on a
  caveat two people share is not the same person), or another original
  member was followed to the same final entry and it is not the one whose
  keys agree with it (`shared_final_entry`, #3265). Where no member's keys
  agree, the one whose scalar leaves overlap the entry strictly more than
  every other's keeps it (`shared_final_entry_by_overlap`, #3273).
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

INSTRUMENT = "self_disclaimed v2 (#2913, #3131)"
# Not under lexicons/: that directory is the pattern-lexicon registry (#2919),
# whose check refuses any file it does not register, and this file is a
# container registry with its own shape and its own pins.
LEXICON_DIR = Path(__file__).parent / "container_lexicons"
LEXICON_RESOURCE_DIR = "src/data_sheets_schema/container_lexicons"
#: The registered lexicon. Every earlier version stays in LEXICON_DIR and
#: loads (`lexicon_path(1)`): the rules a later version adds are declared in
#: its file, so an earlier file read by this code reproduces its output.
LEXICON_PATH = LEXICON_DIR / "self_disclaimed_v2.yaml"
LEXICON_RESOURCE = f"{LEXICON_RESOURCE_DIR}/{LEXICON_PATH.name}"
KINDS = ("person_role", "presence")
SCOPES = ("role", "presence", "self", "subject", "none")
# Where a pattern may also find a self-reference inside its cue (#3261).
SELF_IN_PARTS = ("item",)
# How the diff resolves members followed to one final entry (#3273).
RESOLVE_BY = ("identity_keys", "scalar_overlap")
# What a guard reads, and where a pattern's object lies (the lexicon's
# `reads` and `object` keys; see its guards comment).
GUARD_READS = ("clause", "before_cue", "cue", "after_phrase", "object")
OBJECT_PARTS = ("before_cue", "subject", "cue", "item", "after_phrase", "as_phrase")
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
    self_in: tuple = ()  # cue parts where a self-reference also licenses it (SELF_IN_PARTS)
    self_unless: re.Pattern | None = None  # negation before the item that voids that licence (#3625)


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
        # Optional blocks a later version declares; absent, the code reads
        # the lexicon as v1 did.
        self._statement = self._statement_topic = self._statement_head = None
        self._statement_tail = self._statement_negated = None
        self._clause_conjunction = self._clause_verb = self._correlative = None
        statement = data.get("statement_subject")
        if statement is not None:
            self._statement = _word(statement["nouns"])
            if statement.get("negated") is not None:
                self._statement_negated = re.compile(statement["negated"], re.I)
            if statement.get("head") is not None:
                self._statement_head = re.compile(statement["head"], re.I)
            if statement.get("tail") is not None:
                self._statement_tail = re.compile(statement["tail"], re.I)
            if (statement.get("conjunction") is None) != (statement.get("clause_verb") is None):
                raise ValueError("statement_subject.conjunction and clause_verb are declared together")
            if statement.get("conjunction") is not None:
                self._clause_conjunction = re.compile(statement["conjunction"], re.I)
                self._clause_verb = re.compile(statement["clause_verb"], re.I)
            if statement.get("correlative") is not None:
                self._correlative = re.compile(statement["correlative"], re.I)
                if set(self._correlative.groupindex) != {"open", "join"}:
                    raise ValueError("statement_subject.correlative must name its `open` and `join` groups")
            self._statement_topic = re.compile(statement["topic"], re.I)
            if "topic" not in self._statement_topic.groupindex:
                raise ValueError("statement_subject.topic must name its topic as a `topic` group")
        self._identity_fields: tuple = ()
        self._identity_id_fields: tuple = ()
        self._axes: tuple = ()
        self._qualifier_words = 0
        qualifiers = data.get("item_qualifiers")
        if qualifiers is not None:
            if type(qualifiers.get("words")) is not int or qualifiers["words"] < 0:
                raise ValueError("item_qualifiers.words must be a nonnegative integer")
            axes = qualifiers.get("axes")
            if not isinstance(axes, list) or not axes or any(
                    not isinstance(a, list) or len(a) < 2 for a in axes):
                raise ValueError("item_qualifiers.axes must be a nonempty list of axes of two or more alternatives")
            self._axes = tuple(tuple(_word([alt]) for alt in axis) for axis in axes)
            self._identity_fields = tuple(qualifiers.get("identity_fields") or ())
            self._identity_id_fields = tuple(qualifiers.get("identity_id_fields") or ())
            self._qualifier_words = qualifiers["words"]
        shared = data.get("shared_final_entry") or {"resolve_by": ["identity_keys"]}
        resolve_by = shared.get("resolve_by")
        if (not isinstance(resolve_by, list) or not resolve_by or resolve_by[0] != "identity_keys"
                or set(resolve_by) - set(RESOLVE_BY) or len(set(resolve_by)) != len(resolve_by)):
            raise ValueError(f"shared_final_entry.resolve_by must open on identity_keys and name only "
                             f"{', '.join(RESOLVE_BY)}")
        self.resolve_by = tuple(resolve_by)
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
            if "item" in parts and "(?P<item>" not in row["cue"]:
                raise ValueError(f"pattern {row['id']} declares its object in an `item` group its cue lacks")
            self_in = tuple(row.get("self_reference_in") or ())
            if set(self_in) - set(SELF_IN_PARTS):
                raise ValueError(f"pattern {row['id']} reads a self-reference outside {', '.join(SELF_IN_PARTS)}")
            if "item" in self_in and "(?P<item>" not in row["cue"]:
                raise ValueError(f"pattern {row['id']} reads a self-reference in an `item` group its cue lacks")
            if self_in and row["scope"] != "presence":
                raise ValueError(f"pattern {row['id']} reads a self-reference in its cue outside presence scope")
            unless = row.get("self_reference_unless")
            if unless is not None and "item" not in self_in:
                raise ValueError(f"pattern {row['id']} declares self_reference_unless without self_reference_in: [item]")
            if row["scope"] == "subject" and self._statement is None:
                raise ValueError(f"pattern {row['id']} has subject scope and the lexicon no statement_subject")
            if row["scope"] == "subject" and kinds != {"presence"}:
                raise ValueError(f"pattern {row['id']} has subject scope outside a presence container")
            patterns.append(Pattern(row["id"], row["class"], kinds, row["cue"],
                                    row["scope"], tuple(row["guards"]), parts, self_in,
                                    re.compile(unless, re.I) if unless is not None else None))
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


def lexicon_path(version: int) -> Path:
    """The file of a lexicon version in LEXICON_DIR, the current one or an
    earlier one kept for replay."""
    return LEXICON_DIR / f"self_disclaimed_v{version}.yaml"


def load_lexicon(path: Path = LEXICON_PATH) -> Lexicon:
    """The registered lexicon, an earlier version of it (`lexicon_path`), or
    another lexicon file a test names. A file in LEXICON_DIR is named by its
    repository-relative spelling wherever the package is installed."""
    shown = f"{LEXICON_RESOURCE_DIR}/{path.name}" if path.parent == LEXICON_DIR else str(path)
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


def _item_text(pattern, parts: dict[str, str]) -> str:
    """Where a presence cue names the item it says is unstated, for the
    other-item check: the cue's `item` group when the pattern declares it as
    its object ("No source reports <the other splits> as available", #3250,
    #3265), the whole cue when the pattern declares the cue, and otherwise
    the cue's subject."""
    if "item" in pattern.object:
        return parts["item"]
    if "cue" in pattern.object:
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


_PRONOUN = re.compile(r"\b(?:it|he|she|this)\b", re.I)


def _elided(text: str) -> bool:
    """Whether a conjunct's stretch before its cue has no subject of its
    own: empty, or only adverbs and auxiliaries (`_ELIDED`, a subject
    pronoun excluded: "and it remains" has one)."""
    return _ELIDED.fullmatch(text.strip()) is not None and _PRONOUN.search(text) is None


def _clause_cut(lexicon, subject: str) -> tuple[int, int]:
    """Where the cue's own subject lies in `subject` (a `_subject` stretch,
    unmasked), as (start, end). The cue's own conjunct starts after the
    last `statement_subject.conjunction` whose stretch before it (from the
    previous cut) holds a `statement_subject.clause_verb`, so the
    conjunction joins two clauses and the earlier one is not the cue's
    subject: "Its release is pending and this split" -> "this split"; "This
    split and its labels" is one noun phrase and is kept whole (#3619).
    A conjunct with no subject of its own (`_elided`) inherits the
    governing subject, the nearest earlier conjunct's text before its first
    clause verb: "The holdout set was announced and " -> "The holdout set",
    "It was announced in 2024 and " -> "It" (#3627). (0, len) when the
    lexicon declares no conjunction."""
    if lexicon is None or lexicon._clause_conjunction is None:
        return 0, len(subject)
    cuts = [(0, 0)]  # (conjunct start, previous conjunct end)
    for found in lexicon._clause_conjunction.finditer(subject):
        if lexicon._clause_verb.search(subject, cuts[-1][0], found.start()):
            cuts.append((found.end(), found.start()))
    start = cuts[-1][0]
    if len(cuts) == 1 or not _elided(subject[start:]):
        return start, len(subject)
    for k in range(len(cuts) - 2, -1, -1):
        c0, c1 = cuts[k][0], cuts[k + 1][1]
        verb = lexicon._clause_verb.search(subject, c0, c1)
        end = verb.start() if verb else c1
        if not _elided(subject[c0:end]):
            return c0, end
    return start, len(subject)


def _affirmed(lexicon, sentence: str, before: int) -> str:
    """`sentence` with each `statement_subject.correlative` before offset
    `before` read as affirmative coordination, offsets kept: its `open`
    words ("Not only", "Not just") blanked and its `join` ("but also")
    read as "and", so "Not only this split but also the holdout set" is not
    a negated subject and "this split" heads its conjunct (#3628). The
    sentence as it is when the lexicon declares no correlative."""
    if lexicon._correlative is None:
        return sentence
    chars = list(sentence)
    for found in lexicon._correlative.finditer(sentence, 0, before):
        o0, o1 = found.span("open")
        j0, j1 = found.span("join")
        chars[o0:o1] = " " * (o1 - o0)
        chars[j0:j1] = list("and".ljust(j1 - j0))
    return "".join(chars)


def _parts(masked: str, c0: int, c1: int, m, raw: str | None = None,
           lexicon=None) -> dict[str, str]:
    """The pieces of the cue's clause a guard or an object can name, read
    from the masked sentence: `clause`, `before_cue`, `subject` (a passive
    cue's subject, `_subject`, located on `raw`, the unmasked sentence, and,
    given a `lexicon` that declares clause conjunctions, cut to the cue's
    own conjunct or the subject that conjunct inherits, `_clause_cut`),
    `cue`, `item` (the cue's named `item` group: the item a cue that cites
    its source reports, empty when the cue has none), `after_phrase` (after
    the cue up to the phrase's end,
    `_PHRASE_END`) and `as_phrase` (`after_phrase` when it opens on `as`,
    else empty)."""
    after = masked[m.end():c1]
    end = _PHRASE_END.search(after)
    phrase = after[:end.start()] if end else after
    before = masked[c0:m.start()]
    text = (raw if raw is not None else masked)[c0:m.start()]
    s0, s1 = _subject(text)
    a, b = _clause_cut(lexicon, text[s0:s1])
    s0, s1 = s0 + a, s0 + b
    item = (masked[m.start("item"):m.end("item")]
            if "item" in m.re.groupindex and m.start("item") >= 0 else "")
    return {"clause": masked[c0:c1], "before_cue": before, "subject": before[s0:s1],
            "cue": masked[m.start():m.end()], "item": item, "after_phrase": phrase,
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
    [cue]` or `[item]`) keeps the cue, whose free span names the item it
    reports ("No source reports the holdout set as available")."""
    if "cue" in pattern.object or "item" in pattern.object:
        return masked[c0:c1]
    return masked[c0:m.start()] + " " * (m.end() - m.start()) + masked[m.end():c1]


def _identity_text(lexicon, member: dict) -> str:
    """The member's identifying words for `item_qualifiers` (#3244): its
    `identity_fields` and the fragment of its `identity_id_fields` (after
    the last `#`, `/` or `:`), punctuation and underscores read as spaces,
    so `internal_validation` and `#internal-validation` name `internal`."""
    words = [member.get(k) for k in lexicon._identity_fields]
    words += [re.split(r"[#/:]", member[k])[-1] for k in lexicon._identity_id_fields
              if isinstance(member.get(k), str)]
    return re.sub(r"[\W_]+", " ", " ".join(w for w in words if isinstance(w, str)))


def _qualifiers(lexicon, text: str) -> tuple[frozenset, ...]:
    """Per axis, the alternatives `text` names."""
    return tuple(frozenset(i for i, rx in enumerate(axis) if rx.search(text)) for axis in lexicon._axes)


def _presence_phrases(lexicon, container, member: dict, text: str) -> Iterator[tuple[str, str, bool, object]]:
    """Each presence noun phrase in `text` (the presence term with at most
    `item_qualifiers.words` words before it), its presence term, whether
    it names another item than the member's (on some axis both it and the
    member's identity name an alternative and none is shared, #3244), and
    the presence term's match in `text`. Never another's when the lexicon
    declares no `item_qualifiers` or the member's identity names no
    qualifier."""
    mine = _qualifiers(lexicon, _identity_text(lexicon, member)) if lexicon._axes else ()
    for found in container.presence_scope.finditer(text):
        lead = re.search(rf"(?:[\w-]+\s+){{0,{lexicon._qualifier_words}}}$", text[:found.start()])
        phrase = (lead.group(0) if lead else "") + found.group(0)
        other = any(p and q and not p & q for p, q in zip(_qualifiers(lexicon, phrase), mine))
        yield phrase, found.group(0), other, found


def _other_qualified_item(lexicon, container, member: dict, text: str) -> str | None:
    """The first presence noun phrase in `text` that names another item than
    the member's: "the external test set" in the prose of a member named
    "Internal validation set" (#3244)."""
    return next((" ".join(phrase.split()) for phrase, _t, other, _m
                 in _presence_phrases(lexicon, container, member, text) if other), None)


def _item_names_member(lexicon, container, member: dict, selves, item: str) -> bool:
    """Whether the reported `item` (possessor self-references blanked) also
    names the member: a self-reference to it, or a presence noun phrase that
    does not name another item. "This split and the external test set" and
    "The validation set and the external test set" (of an internal
    validation set) name it; "The external test set" does not (#3626). A
    lexicon with no `item_qualifiers` never gets here with another item."""
    if _search(selves, item):
        return True
    masked = _masked(item, selves)
    return any(not other for _p, _t, other, _f in _presence_phrases(lexicon, container, member, masked))


def _member_presence_term(lexicon, container, member: dict, text: str,
                          heads: bool = False) -> str | None:
    """The first presence term in `text` that does not name another item,
    for a `presence` or `subject` cue's licence. With `heads`, only one that
    heads `text` (`_heads`): a `subject` cue's subject or statement topic
    (#3592)."""
    return next((term for _p, term, other, found in _presence_phrases(lexicon, container, member, text)
                 if not other and (not heads or _heads(lexicon, text, found))), None)


def _ends_phrase(lexicon, text: str, end: int) -> bool:
    """Whether a head ending at `end` ends its noun phrase in `text`: what
    follows matches `statement_subject.tail` (the text's end, punctuation,
    or a word opening a postmodifier, a coordination or the predicate), so
    in "The split labels" and "The statement authors" the term only
    modifies the noun after it (#3606). With no `tail` declared, any
    ending counts."""
    return lexicon._statement_tail is None or lexicon._statement_tail.match(text, end) is not None


def _heads(lexicon, text: str, found) -> bool:
    """Whether the match `found` heads `text`: the text before it matches
    `statement_subject.head`, nothing possessive follows it and it ends its
    noun phrase (`_ends_phrase`), so "The holdout set" is headed by its
    presence term and "The consent process for the splits", "Enrollment of
    the pediatric arm of the split", "The split's schedule" (#3592) and "The
    split labels" (#3606) are not. With no `head` declared, any match
    counts, as before."""
    if lexicon._statement_head is None:
        return True
    return (lexicon._statement_head.fullmatch(text[:found.start()]) is not None
            and _POSSESSIVE_AFTER.match(text, found.end()) is None
            and _ends_phrase(lexicon, text, found.end()))


def _statement_head(lexicon, subject: str):
    """The first statement noun in `subject` that heads it: the text before
    it matches `statement_subject.head` (#3560) and it ends its noun phrase
    (`_ends_phrase`, #3606), so "Both statements" and "The references to
    ..." name one, and "The consent process described in both statements"
    and "The statement authors" do not. With no `head` declared, any
    statement noun in the subject counts."""
    for noun in lexicon._statement.finditer(subject):
        if lexicon._statement_head is None or (
                lexicon._statement_head.fullmatch(subject[:noun.start()])
                and _ends_phrase(lexicon, subject, noun.end())):
            return noun
    return None


def _self_heads_subject(lexicon, selves, subject: str) -> bool:
    """False when the subject holds self-references and none heads it
    (`_heads`): "The labels in this split are prospective" is about the
    labels, as "The consent process for the splits" is about the consent
    process (#3592). When the subject holds none, True only where it is
    elided ("It was announced in 2024 and remains prospective"), so a
    self-reference earlier in the sentence still counts, and not where it
    has words of its own: in "This split is balanced and the consent process
    remains prospective" the cue's subject, its own conjunct (#3619), is the
    consent process."""
    found = [f for rx in selves for f in rx.finditer(subject)]
    if not found:
        return _ELIDED.fullmatch(subject.strip()) is not None
    return any(_heads(lexicon, subject, f) for f in found)


def _item_self_reference(lexicon, selves, item: str) -> str | None:
    """The first self-reference that heads the item a cue reports
    (`_heads`, read on the item with possessor self-references blanked):
    "this split" in "No source reports this split as available" (#3261),
    not in "the labels in this split" or "the labels with this split", which
    are about the labels (#3607), as "The labels in this split" is for the
    subject scope (#3592)."""
    for rx in selves:
        for found in rx.finditer(item):
            if _heads(lexicon, item, found):
                return found.group(0)
    return None


def _topic_self_reference(lexicon, selves, topic: str) -> str | None:
    """The first self-reference that heads a statement's `topic` (`_heads`),
    so it owns nothing there: no preposition before it ("statements about
    the consent process for this split") and nothing possessive after it
    ("statements about this split's consent process") (#3593). Read on the
    topic alone, so the preposition that introduces the topic is not an
    owner: "descriptions of this split" names the split."""
    for rx in selves:
        for found in rx.finditer(topic):
            if _heads(lexicon, topic, found):
                return found.group(0)
    return None


def _subject_scope(lexicon, container, member, selves, sentence: str,
                   c0: int, c1: int, m) -> tuple[str, str | None]:
    """(`scope`, term) for a `subject` cue with no self-reference of its own
    (#3131): its subject is headed by a source statement ("Both statements
    are prospective on that page"; `_statement_head`), with any topic ("statements about ...",
    "descriptions of this split") headed by a self-reference that owns
    nothing or by a presence term, or it is headed by the container's
    presence term ("The holdout set is prospective", not "The consent
    process for the splits", #3592); else (`out_of_scope` reason, term).
    The presence terms are read with the member's self-references blanked,
    a topic's self-reference on the topic as written (`_topic_self_reference`,
    #3593)."""
    raw = _parts(sentence, c0, c1, m, sentence, lexicon)["subject"]
    subject = _parts(_masked(sentence, selves), c0, c1, m, sentence, lexicon)["subject"]
    noun = _statement_head(lexicon, subject)
    if noun is not None:
        # located on the unmasked subject (the same offsets): a blanked
        # self-reference would read as whitespace the topic pattern skips
        topic = lexicon._statement_topic.match(raw, noun.end())
        if topic is None:
            return "scope", noun.group(0)
        t0, t1 = topic.span("topic")
        term = (_topic_self_reference(lexicon, selves, raw[t0:t1])
                or _member_presence_term(lexicon, container, member, subject[t0:t1], heads=True))
        if term:
            return "scope", term
        return "statement_about_other", " ".join(raw[noun.start():].split())
    term = _member_presence_term(lexicon, container, member, subject, heads=True)
    return ("scope", term) if term else ("no_member_subject", None)


def _judge(lexicon, container, member, pattern, sentence, m) -> dict:
    """One cue match: a flag hit, a guarded hit, or out of scope, with why."""
    if pattern.scope == "subject":
        # "Not only this split but also ..." coordinates; it negates nothing
        # (#3628). Offsets are kept, so `m` still locates the cue.
        sentence = _affirmed(lexicon, sentence, m.start())
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
    # A `subject` cue's subject is its own conjunct: in "Its release is
    # pending and this split remains prospective" the earlier clause is
    # not what the cue says is prospective (#3619).
    cut = lexicon if pattern.scope == "subject" else None
    parts = _parts(masked, c0, c1, m, sentence, cut)
    if container.kind == "presence":
        other = _search(lexicon._other_item, _item_text(pattern, parts))
        if other:
            return {**out, "outcome": "out_of_scope", "reason": "other_subject", "term": other}
        # An item named with no other-marker whose qualifier disagrees with
        # the member's identity: "the external test set" in the prose of
        # the internal validation set (#3244).
    # The object read with only the member's possessor self-references
    # blanked ("this author's institution", "the email of this author"): a
    # self-reference that is itself the object ("does not name this
    # maintainer") names the role, one that owns the object does not (#3251).
    objects = _parts(_possessors_blanked(sentence, selves), c0, c1, m, sentence, cut)
    if container.kind == "presence":
        # A reported item that names the member as well is still the
        # member's, whatever else is coordinated with it: "This split and
        # the external test set are not yet released" disclaims both (#3626).
        other = _other_qualified_item(lexicon, container, member, _item_text(pattern, parts))
        if other and not _item_names_member(lexicon, container, member, selves, _item_text(pattern, objects)):
            return {**out, "outcome": "out_of_scope", "reason": "other_qualified_item", "term": other}
    if pattern.scope == "role":
        verdict, term = _role_scope(lexicon, container, sentence, masked, c0, c1, m,
                                    [objects[p] for p in pattern.object])
        if verdict != "scope":
            return {**out, "outcome": "out_of_scope", "reason": verdict,
                    **({"term": term} if term else {})}
        out["scope"] = term
    elif pattern.scope == "presence":
        term = _self_reference(selves, sentence, c0, m.start())
        if term is None and "item" in pattern.self_in and not (
                pattern.self_unless is not None
                and pattern.self_unless.search(sentence, m.start(), m.start("item"))):
            # A self-reference that owns nothing and heads the item the cue
            # reports: "No source reports this split as available" (#3261),
            # not "the labels in this split" (#3607), and not where the
            # source-to-report span is negated: "No source fails to report
            # this split as available" affirms it (#3625).
            term = _item_self_reference(lexicon, selves, objects["item"])
        if term is None:
            term = _member_presence_term(lexicon, container, member,
                                         _presence_text(pattern, masked, c0, c1, m))
        if term is None:
            return {**out, "outcome": "out_of_scope", "reason": "no_self_or_presence_term"}
        out["scope"] = term
    elif pattern.scope == "subject":
        # A self-reference that owns nothing, read as a `self` cue reads it:
        # "This split remains prospective", not "This split's schedule is
        # prospective" (#3131); where the subject holds one, it must head it:
        # not "The labels in this split are prospective" (#3592).
        owners = _possessors_blanked(sentence, selves)
        subject = _parts(owners, c0, c1, m, sentence, lexicon)["subject"]
        # A subject that opens on a negating determiner says nothing it
        # names is prospective: "Neither statement is prospective", "None
        # of the statements are prospective" (#3614).
        if lexicon._statement_negated is not None and lexicon._statement_negated.match(subject):
            return {**out, "outcome": "out_of_scope", "reason": "negated_subject"}
        term = _self_reference(selves, owners, c0, m.start())
        if term is not None and not _self_heads_subject(lexicon, selves, subject):
            term = None
        elif term is not None:
            # the self-reference that heads the cue's own conjunct, not one
            # in an earlier clause: "No data from this split has been
            # released so it remains prospective" is about "it" (#3619)
            term = _item_self_reference(lexicon, selves, subject) or term
        if term is None:
            verdict, term = _subject_scope(lexicon, container, member, selves, sentence, c0, c1, m)
            if verdict != "scope":
                return {**out, "outcome": "out_of_scope", "reason": verdict, **({"term": term} if term else {})}
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


def _identity(original_entry: Any, final_entry: Any) -> str:
    """How the identity keys (`receipts.ENTRY_KEYS`) of two list entries
    compare: `agrees` when a key both carry holds the same value on each
    (resolver URL and CURIE forms are one value), `conflicts` when they
    share keys and every one differs ("Alice Adams" and "Betty Baker" under
    `name`), `unknown` when they share none."""
    from data_sheets_schema.receipts import ENTRY_KEYS, _canonical_identifier
    if not isinstance(original_entry, dict) or not isinstance(final_entry, dict):
        return "unknown"
    shared = [k for k in ENTRY_KEYS
              if all(isinstance(e.get(k), str) and e[k].strip() for e in (original_entry, final_entry))]
    if not shared:
        return "unknown"
    same = any(_canonical_identifier(" ".join(original_entry[k].split()))
               == _canonical_identifier(" ".join(final_entry[k].split())) for k in shared)
    return "agrees" if same else "conflicts"


def _identity_steps(tokens: tuple, where: tuple, original: Any, final: Any) -> list[str]:
    """`_identity` at every list step of the member's path, original entry
    against the final entry it was followed to."""
    steps, o, f = [], original, final
    for a, b in zip(tokens, where):
        try:
            o, f = o[a], f[b]
        except (KeyError, IndexError, TypeError):
            return steps
        if isinstance(a, int):
            steps.append(_identity(o, f))
    return steps


def _follow(tokens: tuple, original: Any, final: Any) -> tuple[tuple | None, str]:
    """Where the member sits in the final record, joined by identity.

    The member is `removed` when it, or any ancestor of it, is gone from the
    final record or holds null or an empty list there: its own container,
    or a list further up (a nested member under `resources: null`, #3088).
    The nearest ancestor that resolves decides; when it is present and not
    empty, the member is `identity_unresolved` with remap_path's basis.

    remap_path joins an entry with no key match by the overlap of its
    scalar leaves, and a caveat two entries share is such a leaf. A join
    whose entries carry conflicting identity keys at any list step ("Alice
    Adams" followed to "Betty Baker" because both carry the same caveat) is
    rejected as `identity_conflict` (#3265): the final entry is someone
    else, and whether the member was deleted or renamed is not known."""
    from data_sheets_schema.receipts import remap_path
    moved = remap_path(_dotted(tokens), original, final)
    if moved["path"] is not None:
        where = _undotted(moved["path"])
        if "conflicts" in _identity_steps(tokens, where, original, final):
            return None, "identity_conflict"
        return where, moved["basis"]
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


def _entry_at(record: Any, tokens: tuple) -> Any:
    for t in tokens:
        record = record[t]
    return record


def _strongest_overlap(group: list[tuple], where: tuple, original: Any, final: Any) -> tuple | None:
    """The member of `group` whose scalar leaves (`receipts._scalar_pairs`)
    overlap the final entry at `where` strictly more than every other
    member's, or None on a tie or when none overlaps (#3273)."""
    from data_sheets_schema.receipts import _scalar_pairs
    entry = _scalar_pairs(_entry_at(final, where))
    scores = [len(_scalar_pairs(_entry_at(original, t)) & entry) for t in group]
    best = max(scores)
    if best == 0 or scores.count(best) > 1:
        return None
    return group[scores.index(best)]


def _resolve_all(original: Any, final: Any, lexicon: Lexicon) -> dict[tuple, tuple[tuple | None, str]]:
    """`_follow` for every member of the original, then one survivor per
    final entry. Where two original members are followed to the same final
    entry, the one whose identity keys agree with it at every list step
    keeps it. Where none agrees and the lexicon resolves by
    `scalar_overlap` (#3273), the one whose scalar leaves overlap the entry
    strictly more than every other's keeps it, with basis
    `shared_final_entry_by_overlap`. Every other, and all of them when
    neither rule picks one, is `identity_unresolved` with basis
    `shared_final_entry` (#3265): two distinct entries cannot both be
    retained as one."""
    out = {tokens: _follow(tokens, original, final) for tokens, _c, _m in members(original, lexicon)}
    landed: dict[tuple, list[tuple]] = {}
    for tokens, (where, _basis) in out.items():
        if where is not None:
            landed.setdefault(tuple(where), []).append(tokens)
    for where, group in landed.items():
        if len(group) < 2:
            continue
        agreed = [t for t in group
                  if set(_identity_steps(t, where, original, final)) == {"agrees"}]
        keep = agreed[0] if len(agreed) == 1 else None
        if not agreed and "scalar_overlap" in lexicon.resolve_by:
            keep = _strongest_overlap(group, where, original, final)
            if keep is not None:
                out[keep] = (where, "shared_final_entry_by_overlap")
        for tokens in group:
            if tokens != keep:
                out[tokens] = (None, "shared_final_entry")
    return out


def classify(flags: list, original: Any, final: Any, *, audit: Any = None,
             final_flags: list | None = None, retained: str = "self_disclaimed_retained",
             lexicon: Lexicon | None = None) -> dict:
    """Each flag on the original, followed to the final and classified."""
    lexicon = lexicon or load_lexicon()
    removals, naming, unreadable = _finding_pointers(audit) if audit is not None else ([], [], 0)
    still = {f["path"] for f in final_flags or []}
    rows, counts = [], {k: 0 for k in (*CLASSIFICATIONS, retained)}
    resolved = _resolve_all(original, final, lexicon) if flags else {}
    for flag in flags:
        tokens = parse_pointer(flag["path"])
        member = tuple(int(t) if re.fullmatch(r"0|[1-9][0-9]*", t) else t for t in tokens)
        container = lexicon.containers[flag["container"]]
        where, basis = resolved.get(member) or _follow(member, original, final)
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
