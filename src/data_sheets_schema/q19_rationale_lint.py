"""Flag rubric20 Q19 scores held below 5 for how provenance is represented (#2911).

Rubric20 Q19 contradicts itself. Its scoring distinction and its 3/5 anchors
name a "full provenance graph", and the sentence between them says provenance
"may be represented as text OR as W3C PROV-O graphs". Evaluators resolve the
contradiction by withholding 5 for the form of the lineage rather than for its
content: an empty `was_derived_from`, no PROV serialization, lineage a machine
cannot traverse, lineage spread across fields. Two inspections of the 48
version-1.0 ratings of the two recorded reference rescores flagged 24 such
rationales (#1337, #1349). The definition those ratings used (sha256
9d08b5f3…, pinned by the errata) has been edited since, and Q19's scale
moved from 0-5 to 0/3/5 (fb4110101), so a later rating is 0, 3 or 5 and is
never "held at 4"; but Q19's description still says text OR graph between
anchors that name a graph, so later ratings inherit the contradiction. This
lint reads a rating's own rationale and says whether it withholds 5 on those
grounds, so the check does not depend on someone rereading every Q19 by
hand.

**What is read.** The Q19 item's `score_label`, `quality_note` and
`semantic_analysis` (whichever are present: a version-2.0 item carries no
per-item `semantic_analysis`). Nothing else. The input record is not read,
so the lint cannot tell whether the lineage content an evaluator missed is
really in the record. That is an adjudicator's question; this is a screen.

**Gated on the score and on withholding language.** Vocabulary alone does
not separate the two groups: every one of the 18 recorded Q19=5 rationales
names representation vocabulary, usually to say the content is carried
elsewhere. Seventeen name `was_derived_from`, a graph or PROV; the other
(CBORG AI_READI v8 rep2) names `parent_datasets`, typed links,
machine-readable form and lineage across fields. So:

- a score at its maximum withholds nothing and is never flagged
  (`FULL_SCORE`); its vocabulary is still reported as `mentions`;
- below the maximum, only the sentences that say why the score is below it
  are read (`withholding_sentences`): a sentence with a score-directed cue
  ("held at 4 because", "falls short of the 5-band", "what keeps it from
  5"), its neighbours when it names no reason itself ("Short of 5."), and
  the reason clauses of the score label (`_label_reasons`). A label's
  clauses end at punctuation, a spaced dash, a parenthesis and before
  "but", "without", "rather than" and "short of", so its reason is the
  same with or without a comma: from its first contrast or withholding cue
  onward ("…, short of a full provenance graph", "… - no typed derivation
  links", "… but no version history", "Held at 4 because …"), and any
  earlier clause saying something is absent ("…, structural derivation
  slots empty"). The label's other clauses are credit and are not read,
  with one exception: a contrast that names nothing of its own ("graph
  claimed but not evidenced", "full provenance graph asserted rather than
  exhibited") is about the words before it in its clause, and those are
  read with it;
- the basis is `STATED` when a quality-note or semantic-analysis sentence
  carries a cue, or the label carries a withholding cue and names a reason
  ("Held at 4 because was_derived_from is empty"). A label's contrast or
  absence clause ("…, no formal provenance graph") names a gap the record
  has without saying that gap is what held the score, so it does not
  state the basis on its own;
- otherwise nothing says why the score is below the maximum
  (`basis == UNSTATED`), and every gap the quality note and semantic
  analysis name is a candidate reason beside the label's reason clauses: a
  sentence is read only where it says something is absent, negated or
  incomplete (`_gap_part`), less any text before its first "but",
  "whereas" or "however" that names no gap itself (as in a label, a
  contrast naming nothing of its own keeps the words before it in its
  clause: "changelog mentioned but not detailed"). A sentence that names
  no gap ("RO-Crate packages include provenance graphs", "per-archive MD5
  checksums give real integrity evidence") is credit and is not read, as
  the label's credit is not. A sentence pairing credit with a gap and no
  contrast word between them is read whole;
- inside those sentences a clause that accepts or disclaims ("which the
  rubric accepts in place of a PROV-O serialization", "despite the
  dedicated field being empty", "not a reason to withhold 5") names no
  reason. Clauses end at punctuation and before "but", "whereas",
  "although", "(even) though", "despite" and "in spite of", so a concession
  that shares a clause with a reason ("was_derived_from is empty even
  though the lineage is complete in prose", "text is permitted but no PROV
  graph is provided") removes only itself.

**Representation reasons flag; substantive reasons are reported beside
them, never as a clean pass.** `REPRESENTATION_CONCERNS` is the vocabulary
#2911 proposed from the figure-set adjudication rules: empty derivation
slots, graph/PROV/serialization/typed form, machine readability or
traversal, and lineage scattered across fields for a reader to assemble.
`SUBSTANTIVE_CONCERNS` is the content the frozen rule says can still
matter: version history and errata, missing-data and split documentation,
which specific artifact came from which specific input, identifiers, fixity
and quality evidence. A rating citing both is
`REPRESENTATION_AND_SUBSTANTIVE`: flagged, because a representation reason
was given, with the substantive reasons listed so an adjudicator can decide
which one limited the score. Only `REPRESENTATION_ONLY` rests on
representation alone.

**Calibration, and its limit.** Against the two inspections' 48 recorded
ratings (`inspection_statuses`): all 24 flagged ratings are flagged (9
`REPRESENTATION_ONLY`, 15 with a substantive co-reason), and all 18 Q19=5
ratings are `FULL_SCORE` with no withholding sentence. The six ratings
below 5 that the inspections left unflagged are flagged too: five with a
substantive co-reason, and 09-11 CM4AI v8 rep1 as `REPRESENTATION_ONLY`,
its one other limit (a derivation "inferred from filenames") being in no
vocabulary. Each names an empty `was_derived_from` or a graph in the
sentence that holds it below 5; the inspections judged, with the input
record in hand, that the limiting concern was something else, mostly which
specific artifact came from which input. That judgement is not lexical.
Near-identical wording carries both labels: "the 5 band needs a complete
graph: there is no was_derived_from linking a specific released artefact to
a specific source" is unflagged by the CBORG inspection (CHORUS v7 rep3),
and "the 5-point anchor asks for a full provenance graph: no field links a
specific derived artifact to the specific raw input" is flagged by the
09-11 one (AI_READI v8 rep2). The CM4AI v8 rep1 rationales of the two
conditions both hold 5 back for empty `was_derived_from` and
`parent_datasets` and a filename-inferred derivation, and one is flagged,
the other not. Read as concern profiles the labels do not separate either:
09-11 CM4AI v8 rep1 (unflagged) gives an empty slot and graph form and no
substantive reason, as four flagged ratings do (CBORG CM4AI v8 rep1 among
them); missing-data documentation, the one reason CBORG CHORUS v7 rep2
(unflagged) gives beyond those of 09-11 CHORUS v8 rep3 (flagged), is given
by four flagged ratings and four unflagged ones; and flagging a rating with
a substantive co-reason only when it also cites machine form or scattering
would miss four flagged ratings while still flagging 09-11 CM4AI v8 rep1.
A rule reproducing every label would be fitted to the phrasing of 48
rationales, so the lint flags these six and reports the disagreement
(`d4d evaluate q19-lint --inspection …`). The vocabulary was
written against these 48 rationales and read against the 85 other committed
rubric20 semantic outputs, which no inspection labels (plural "graphs", a
label's ", no …", a bare "Short of 5.", a passive "one point withheld" came
from those). Its precision and recall on unseen ratings are unmeasured.
An empty-slot match is the slot's name, not a check that the slot is
empty (#2982). Where nothing says why, a sentence that names no gap is not
read, so credit naming a populated slot is not read there: before that rule
the committed CHORUS 2026-09-04f API rep1 rating (UNSTATED) gave an
empty-slot reason, and a missing-data one, from "was_derived_from is
explicit rather than implied, and missing data is documented with reasons
at instance level", which says the slot is populated. A sentence that says
why the score is below 5 is still read whole, less its concessions, so one
naming a populated slot as credit beside its reason would be read as giving
that reason. Of the 88 empty-slot reasons read from the 133 committed
ratings, 78 name the slot in a clause saying something is empty, absent or
negated; the other 10 name it in a list or parenthesis whose emptiness a
neighbouring clause of the same sentence states ("the dedicated derivation
fields (was_derived_from, parent_datasets) are empty", "No version history,
errata or structured derivation"). None is credit.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

RUBRIC = "rubric20-semantic"
Q19_ID = 19
#: The rationale fields read, in reading order. The item's `evidence` lists
#: what the record contains and is not a reason, so it is not read.
FIELDS = ("score_label", "quality_note", "semantic_analysis")

REPRESENTATION = "representation"
SUBSTANTIVE = "substantive"

FULL_SCORE = "full_score"
NOT_SCORED = "not_scored"
REPRESENTATION_ONLY = "representation_only"
REPRESENTATION_AND_SUBSTANTIVE = "representation_and_substantive"
SUBSTANTIVE_ONLY = "substantive_only"
NO_STATED_REASON = "no_stated_reason"
FLAGGED = frozenset({REPRESENTATION_ONLY, REPRESENTATION_AND_SUBSTANTIVE})

#: Where the withholding reasons were read from.
STATED = "stated"          # sentences that say why the score is below maximum
UNSTATED = "unstated"      # none do: label reason clauses and body gaps were read
NOT_LINTED = "not_linted"  # at the maximum, or no numeric score

_I = re.IGNORECASE

#: Grounds the frozen text-or-graph rule does not allow on their own (#2911).
REPRESENTATION_CONCERNS = {
    "empty_slot": re.compile(
        r"was_derived_from|parent_datasets|was_generated_by"
        r"|\bderivation (?:fields?|slots?)"
        r"|\b(?:dedicated|designated|structured) (?:provenance |derivation |graph )?(?:fields?|slots?)"
        r"|\bprovenance fields?|\bschema slots?|\bstructured derivation"
        r"|\bthe fields? the (?:question|rubric) names", _I),
    "graph_form": re.compile(
        r"(?<!or-)\bgraphs?\b|\bPROV-O\b|\bPROV\b|serializ|serialis|\bRDF\b"
        r"|\baddressable|\buntyped\b|\btyped\b|\bformal (?:expression|derivation)"
        r"|\b(?:not|never) (?:itself |yet )?(?:represent|express|encod|instantiat)\w*"
        r"|\b(?:rather than|instead of) (?:being )?(?:represented|expressed|encoded|instantiated)"
        r"|\bto be represented\b", _I),
    "machine_form": re.compile(
        r"machine[- ]?(?:readab|actionab|travers|consum)|\bby a machine"
        r"|\ba machine (?:cannot|could not)|\bmechanical|\bprogrammatic"
        r"|\bhuman[- ]readable|\btravers(?:ed|able|al)\b", _I),
    "scattered": re.compile(
        r"\bscattered|\bspans sections"
        r"|\bacross (?:\w+ )?(?:separate |unrelated |several |different )?(?:fields|sections)"
        r"|\bdistributed across|\bmatching prose"
        r"|\b(?:assembled|reassembled|reconstructed) by (?:a|the) reader"
        r"|\breader must (?:assemble|reassemble)|\bread off\b", _I),
}

#: Q19 content whose absence can still justify a score below 5.
SUBSTANTIVE_CONCERNS = {
    "version_history": re.compile(
        r"version[_ ]access|\berrat(?:a|um)\b|\bunversioned|\bversioning"
        r"|\bversion (?:history|identifiers?|control)|non-monotonic"
        r"|\bchange ?logs?\b|\brelease notes\b", _I),
    "lineage_content": re.compile(
        r"\b(?:no|partial|incomplete|absent|missing|thin) (?:processing |textual |source )?lineage\b"
        r"|\blineage (?:is |remains )?(?:absent|missing|partial|incomplete|thin|undocumented"
        r"|not (?:captured|documented|described|stated))", _I),
    "missing_data": re.compile(
        r"\bmissingness|\bmissing[- _]data|\bsplit indicators?|is_data_split", _I),
    "artifact_granularity": re.compile(
        r"\bgranularit|artifact-level|\bper[- ]artifact"
        r"|\b(?:specific|particular|individual|given) (?:released |derived |raw )?"
        r"(?:archive|artefact|artifact|file|collection|table|input|source|activity"
        r"|extract|deposit|release)"
        r"|\bwhich (?:\w+ ){0,3}(?:produced|derives)", _I),
    "identifiers": re.compile(
        r"\bidentifiers?\b|\bunidentified\b|\baccessions?\b", _I),
    "integrity": re.compile(
        r"\bchecksums?\b|\bfixity\b|\bmd5\b|\b(?:quality|QC) metrics?", _I),
}

#: A sentence saying why the score is below its maximum. Score-directed on
#: purpose: "raw data are withheld" and "recorded as an issue rather than a
#: deduction" are about the data or disclaim a deduction, and matched in
#: four of the Q19=5 rationales when the cues were bare words. So a passive
#: "withheld" counts only after the thing a score withholds ("one point
#: withheld", "the fifth mark is withheld", "the top band is withheld").
_WITHHOLDING = re.compile(
    r"\b(?:held|holds?|kept|stays?|remains?) (?:it |this )?(?:at|to|below) (?:[0-4]|5|a [0-4])\b"
    r"|\bfalls? short\b|\bshort of (?:5|the|an?|full)\b|\bnot (?:a )?5\b|\bnot reach"
    r"|\bkeeps? (?:it|this|the score) from (?:5|five|the top|a 5|full)"
    r"|\bblocks? (?:a )?5\b|\bprevents? (?:a )?(?:higher|5|full)"
    r"|\bbelow the (?:top|5)|\bdeducted\b"
    r"|\bwithh(?:eld|olds?|olding) (?:the |a |full )?(?:5|five|top|point|band|mark)"
    r"|\b(?:5|five|point|mark|band) (?:is |was )?withheld\b"
    r"|\bwhat is missing\b|\btop band requires|\bfull marks require"
    r"|\b(?:asks|calls) for a full|\bneeds a (?:complete|full)"
    r"|\bseparates this from the top|\brather than (?:a )?(?:5|five)\b|\bnot quite complete\b", _I)

#: A clause that accepts a form or disclaims a deduction names no reason.
#: "rather than a deduction" and "rather than from being a 5" disclaim;
#: "a 4 rather than a 5" withholds, so the alternative names both exactly.
_ACCEPTANCE = re.compile(
    r"\baccepts?\b|\baccepted\b|\bpermits?\b|\bpermitted\b|\ballows?\b"
    r"|\bin place of\b|\bon equal footing\b|\bdespite\b|\bin spite of\b|\balthough\b|\bthough\b"
    r"|\bregardless of\b|\birrespective of\b"
    r"|\bnot (?:itself )?(?:a|the) (?:reason|ground|deduction)"
    r"|\brather than (?:a deduction|from being a 5)\b"
    r"|\bwithout (?:moving|reducing|lowering|penali[sz]ing)"
    r"|\b(?:is|are) not required\b|\b(?:does|do|need) not (?:require|need|count|matter)", _I)

#: Where a clause ends inside a sentence or a score label: , ; : ( ) an em
#: dash, or a spaced hyphen, en dash or double hyphen ("Very Good - no
#: formal provenance graph"). Sentence ends are split before this is used.
_CLAUSE_BREAK = r"[,;:()]|\s[—–-]{1,2}\s|—"
_BREAK = re.compile(_CLAUSE_BREAK)

#: A score label is a one-line summary; it gives a reason where it contrasts.
#: A contrasting conjunction opens a label clause of its own even with no
#: punctuation before it, so "Good versioning but no PROV graph" gives its
#: reason after "but", as "Good versioning, but no PROV graph" does.
_LABEL_CONJUNCTION = re.compile(r"\s+(?=(?:but|without|rather than|short of)\b)", _I)
#: A label clause gives a reason when it opens with a contrasting
#: conjunction or with "no", or says "not".
_LABEL_CONTRAST = re.compile(r"^(?:but|without|rather than|short of|no)\b|\bnot\b", _I)
#: A label clause that says something is absent gives a reason with no
#: contrast word ("…, structural derivation slots empty", "…; version history
#: and missingness absent"). "missing-data documentation" names content.
_ABSENCE = re.compile(
    r"\b(?:empty|absent|unpopulated|unfilled|blank|lacking|lacks)\b|\bmissing\b(?![-_ ]data)", _I)

#: A quality-note or semantic-analysis sentence names a gap when it says
#: something is absent, negated or incomplete. Where nothing says why a score
#: is below its maximum, only such sentences are read: "RO-Crate packages
#: include provenance graphs", "was_derived_from is explicit rather than
#: implied, and missing data is documented" and "per-archive MD5 checksums
#: give real integrity evidence" are credit. A hyphenated "-only" is a name
#: ("the version-history-only anchor"), and a bare "rather than" contrasts
#: as often as it withholds ("explicit rather than implied").
_GAP = re.compile(
    r"\b(?:no|not|none|nor|neither|never|nothing|without|cannot|lacks?|lacking|lacked"
    r"|absent|empty|unpopulated|unfilled|blank|partial(?:ly)?|incomplete|insufficient|limited)\b"
    r"|(?<!-)\bonly\b|\bmissing\b(?![-_ ]data)|n't\b"
    r"|\bun(?:typed|versioned|identified|documented|structured|linked)\b"
    r"|\b(?:rather than|instead of) (?:being )?(?:represented|expressed|encoded|instantiated)"
    r"|\bscattered\b|\breader must (?:re)?assemble|\b(?:re)?assembled by (?:a|the) reader"
    r"|\b(?:could|would) benefit\b", _I)
#: What divides a sentence's credit from its gap: "… is recoverable from
#: prose, which exceeds the version-history-only anchor, but no PROV-O graph".
_BODY_CONTRAST = re.compile(r"\b(?:but|whereas|however)\b", _I)

#: Sentences end at . ! ? — not at a semicolon, which in these rationales
#: joins a withholding cue to the reason it gives ("…lack accessions; that
#: combination … is what separates this from the top band"). The next
#: sentence may open with a lower-case slot name ("missing_information on …").
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[\w\"'(])|\n+")
#: Clauses end at punctuation and before a contrasting or conceding
#: conjunction, so a concession ("…is empty even though the lineage is
#: complete", "text is permitted but no PROV graph is provided") is judged
#: apart from the reason it shares a sentence with. The conjunction opens the
#: clause it heads, where `_ACCEPTANCE` sees a concessive one; "but" and
#: "whereas" head either side of a contrast and accept nothing.
_CLAUSE = re.compile(
    rf"\s*(?:{_CLAUSE_BREAK})\s*"
    r"|\s+(?=(?:but|whereas|although|even though|despite|in spite of)\b)"
    r"|(?<!\beven)\s+(?=though\b)", _I)


@dataclass(frozen=True)
class Reason:
    concern: str   # a key of REPRESENTATION_CONCERNS or SUBSTANTIVE_CONCERNS
    kind: str      # REPRESENTATION or SUBSTANTIVE
    field: str     # the rationale field the sentence came from
    match: str     # the matched text
    #: The text read: a sentence, a label's reason clauses, or, where
    #: nothing says why, the part of a sentence that names a gap.
    sentence: str
    clause: str    # the clause of `sentence` the match is in


@dataclass(frozen=True)
class Q19Lint:
    score: float | None
    max_score: float | None
    basis: str
    #: Reasons found where the rationale explains why the score is below
    #: its maximum. Empty at the maximum.
    reasons: tuple[Reason, ...]
    #: Every concern named anywhere in the rationale, with no score gate, no
    #: withholding scope and no acceptance clause: vocabulary alone.
    mentions: tuple[Reason, ...]

    def concerns(self, kind: str) -> list[str]:
        return sorted({r.concern for r in self.reasons if r.kind == kind})

    @property
    def verdict(self) -> str:
        if self.basis == NOT_LINTED:
            # A score with no maximum to compare it with was not linted
            # either; calling it full would claim a comparison never made.
            return NOT_SCORED if self.score is None or self.max_score is None else FULL_SCORE
        rep, sub = self.concerns(REPRESENTATION), self.concerns(SUBSTANTIVE)
        if rep:
            return REPRESENTATION_AND_SUBSTANTIVE if sub else REPRESENTATION_ONLY
        return SUBSTANTIVE_ONLY if sub else NO_STATED_REASON

    @property
    def flagged(self) -> bool:
        return self.verdict in FLAGGED


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def q19_item(evaluation: dict) -> dict:
    """The Q19 question of a rubric20 semantic evaluation, found by id."""
    found = [q for category in evaluation.get("categories") or [] if isinstance(category, dict)
             for q in category.get("questions") or []
             if isinstance(q, dict) and q.get("id") == Q19_ID]
    if len(found) != 1:
        raise ValueError(f"expected one Q19 question, found {len(found)}")
    return found[0]


def _sentences(item: dict) -> list[tuple[str, str]]:
    out = []
    for name in FIELDS:
        text = item.get(name)
        if isinstance(text, str):
            out.extend((name, s.strip()) for s in _SENTENCE.split(text) if s.strip())
    return out


def _spans(text: str) -> list[tuple[int, int]]:
    """(start, end) of each clause of `text`, split at `_CLAUSE_BREAK`."""
    out, pos = [], 0
    for m in _BREAK.finditer(text):
        out.append((pos, m.start()))
        pos = m.end()
    return out + [(pos, len(text))]


def _label_reasons(label: str) -> list[str]:
    """The parts of one score-label sentence that give a reason; the rest is
    credit.

    Clauses end at `_CLAUSE_BREAK` and before a contrasting conjunction
    (`_LABEL_CONJUNCTION`). The reason runs from the first clause carrying a
    contrast or withholding cue to the end of the sentence: "Well beyond
    version history, with a declared provenance graph, short of an explicit
    graph in the record" gives its reason in the last clause, the first two
    are credit; "Typed derivation links in was_derived_from but no version
    history" gives it after "but", whatever punctuation precedes it; "Held
    at 4 because was_derived_from is empty" is a reason whole. A contrast
    that names nothing of its own is about the words before it in its
    clause, which are read with it: "graph claimed but not evidenced",
    "full provenance graph asserted rather than exhibited". Before the
    reason, each clause saying something is absent is a reason of its own:
    "Prose lineage; was_derived_from empty".
    """
    out = []
    for a, b in _spans(label):
        cuts = [a] + [m.end() for m in _LABEL_CONJUNCTION.finditer(label, a, b)]
        for i, start in enumerate(cuts):
            part = label[start:cuts[i + 1] if i + 1 < len(cuts) else b].strip()
            if _LABEL_CONTRAST.search(part) or _WITHHOLDING.search(part):
                if i and not _reasons([("score_label", label[start:b])]):
                    start = cuts[i - 1]
                return [text for text in out + [label[start:].strip()] if text]
        if _ABSENCE.search(label[a:b]):
            out.append(label[a:b].strip())
    return out


def _gap_part(sentence: str) -> str:
    """The part of a quality-note or semantic-analysis sentence that names a
    gap (`_GAP`), or "" where it names none: the whole sentence, less any
    credit before its first contrast ("…recoverable from prose, which
    exceeds the version-history-only anchor, but no PROV-O graph") when
    that credit names no gap itself. As in a label, a contrast that names
    nothing of its own ("changelog mentioned but not detailed") is about the
    words before it in its clause, which are kept."""
    if not _GAP.search(sentence):
        return ""
    contrast = _BODY_CONTRAST.search(sentence)
    if contrast is None or _GAP.search(sentence[:contrast.start()]):
        return sentence
    start = contrast.start()
    a, b = next((a, b) for a, b in _spans(sentence) if a <= start <= b)
    if not _reasons([("", sentence[start:b])]):
        start = a
    return sentence[start:].strip()


def withholding_sentences(item: dict) -> list[tuple[str, str]]:
    """(field, sentence) pairs that say why the score is below its maximum:
    body sentences carrying a withholding cue, and a label's reason clauses
    (`_label_reasons`). A cue sentence that names no concern of its own
    ("Short of 5.", "One point is deducted for that gap.") gives its reason
    in a neighbour, so the sentences either side of it in the same field are
    read with it."""
    sentences = _sentences(item)
    keep = []
    for i, (name, sentence) in enumerate(sentences):
        if name == "score_label":
            keep.extend((i, reason) for reason in _label_reasons(sentence))
        elif _WITHHOLDING.search(sentence):
            keep.append((i, sentence))
            if not _reasons([(name, sentence)]):
                keep.extend((j, sentences[j][1]) for j in (i - 1, i + 1)
                            if 0 <= j < len(sentences) and sentences[j][0] == name)
    seen, out = set(), []
    for i, text in sorted(keep, key=lambda k: k[0]):
        if (i, text) not in seen:
            seen.add((i, text)); out.append((sentences[i][0], text))
    return out


def _reasons(pairs, *, accepting: bool = True) -> tuple[Reason, ...]:
    found = {}
    for name, sentence in pairs:
        for clause in _CLAUSE.split(sentence):
            if accepting and _ACCEPTANCE.search(clause):
                continue
            for kind, table in ((REPRESENTATION, REPRESENTATION_CONCERNS),
                                (SUBSTANTIVE, SUBSTANTIVE_CONCERNS)):
                for concern, pattern in table.items():
                    m = pattern.search(clause)
                    if m:
                        found.setdefault((concern, name, sentence),
                                         Reason(concern, kind, name, m.group(0), sentence, clause))
    return tuple(found.values())


def lint_q19(item: dict) -> Q19Lint:
    """Lint one Q19 item. The item is read, never changed."""
    score, maximum = _number(item.get("score")), _number(item.get("max_score"))
    sentences = _sentences(item)
    mentions = _reasons(sentences, accepting=False)
    if score is None or maximum is None or score >= maximum:
        return Q19Lint(score, maximum, NOT_LINTED, (), mentions)
    stated = withholding_sentences(item)
    label = [(name, s) for name, s in stated if name == "score_label"]
    # A label says why the score is held when it carries a withholding cue
    # and names a reason ("Held at 4 because was_derived_from is empty").
    # A contrast or absence clause ("…, no formal provenance graph") names a
    # gap the record has without saying that is what held the score, and a
    # bare "Short of 5" names none, so both leave the body to say it.
    label_says_why = any(_WITHHOLDING.search(s) for _, s in label) and bool(_reasons(label))
    if label_says_why or any(name != "score_label" for name, _ in stated):
        return Q19Lint(score, maximum, STATED, _reasons(stated), mentions)
    # Nothing says why: every gap the body names is a candidate reason beside
    # the label's reason clauses; the body's credit, like the label's, is not.
    body = [(name, part) for name, s in sentences if name != "score_label"
            for part in (_gap_part(s),) if part]
    return Q19Lint(score, maximum, UNSTATED, _reasons(label + body), mentions)


def lint_file(path: Path | str) -> Q19Lint:
    """Lint the Q19 item of one rubric20 semantic evaluation file."""
    evaluation = json.loads(Path(path).read_text(encoding="utf-8"))
    rubric = evaluation.get("rubric") if isinstance(evaluation, dict) else None
    if rubric != RUBRIC:
        raise ValueError(f"not a {RUBRIC} evaluation (rubric {rubric!r})")
    return lint_q19(q19_item(evaluation))


# -- the recorded inspections (#1337, #1349) ---------------------------------

@dataclass(frozen=True)
class InspectionStatus:
    job_id: str
    path: Path            # the evaluation the inspection read, resolved
    q19_score: int
    flagged: bool         # "requires adjudication"
    #: The bytes the inspection read: from its JSON companion where it has
    #: one, else from the record's Markdown section; None where neither says.
    sha256: str | None


_STATUS = {"requires adjudication": True, "requires_adjudication": True,
           "not flagged by this inspection": False,
           "not_flagged_by_this_inspection": False}
#: The 09-11 errata's table: | record | Q19 | total | status | [link](path#Ln) |
_TABLE_ROW = re.compile(
    r"^\s*\|\s*(?P<job>\w+)\s*\|\s*(?P<score>\d+)\s*\|\s*[\d.]+\s*\|\s*(?P<status>[^|]+?)\s*\|"
    r"\s*\[[^\]]*\]\((?P<path>[^)#]+)(?:#L\d+)?\)\s*\|\s*$")
_TABLE_SEPARATOR = re.compile(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$")
#: The CBORG review's per-record sections.
_SECTION_STATUS = re.compile(r"^Recorded Q19: (?P<score>\d+)/5\. Status: `(?P<status>\w+)`\.", re.M)
_SECTION_OUTPUT = re.compile(r"^Original output: \[evaluation\]\((?P<path>[^)#]+)\)", re.M)
_SECTION_SHA = re.compile(r"^(?:Original output: .*?; |Evaluation )SHA256:? `(?P<sha>[0-9a-f]{64})`", re.M)
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _table_rows(md: Path, text: str) -> list[tuple[str, int, str, str]]:
    """Every row of every pipe table, each of which must be a record row.

    A table's header is the line above its separator; any other row that
    does not read as `| record | Q19 | total | status | [link](path) |` (a
    total of "n/a", a score of 4.5, text after the link, a hyphenated
    record) is refused rather than skipped, so a partly unreadable
    inspection cannot shrink the set it is compared on.
    """
    lines, rows = text.splitlines(), []
    for n, line in enumerate(lines):
        if not line.lstrip().startswith("|") or _TABLE_SEPARATOR.match(line):
            continue
        if n + 1 < len(lines) and _TABLE_SEPARATOR.match(lines[n + 1]):
            continue
        m = _TABLE_ROW.match(line)
        if m is None:
            raise ValueError(f"{md}:{n + 1}: table row is not an inspection record: {line.strip()!r}")
        rows.append((m["job"], int(m["score"]), m["status"], m["path"]))
    return rows


def _companion(md: Path) -> tuple[Path, dict[str, dict]] | None:
    """The inspection's structured companion (`<stem>.json` beside it), by
    job id, or None where it has none. Each case must name the sha256 of the
    evaluation it read."""
    companion = md.with_suffix(".json")
    if not companion.is_file():
        return None
    try:
        data = json.loads(companion.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{companion}: not JSON: {exc}") from exc
    cases = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{companion}: no cases")
    out = {}
    for case in cases:
        job = case.get("job_id") if isinstance(case, dict) else None
        if not isinstance(job, str):
            raise ValueError(f"{companion}: a case with no job_id")
        if job in out:
            raise ValueError(f"{companion}: {job} is listed twice")
        sha = case.get("evaluation_sha256")
        if not (isinstance(sha, str) and _SHA256.fullmatch(sha)):
            raise ValueError(f"{companion}: {job}: no evaluation_sha256")
        out[job] = case
    return companion, out


def _companion_score(case: dict):
    """The Q19 score a companion case records: the 09-11 errata's
    `q19_score` or the CBORG review's `q19.score`; None where neither."""
    if "q19_score" in case:
        return case["q19_score"]
    q19 = case.get("q19")
    return q19.get("score") if isinstance(q19, dict) else None


def _names(path: Path, output) -> bool:
    """Whether a companion's `output` (relative to the repository it was
    written in) names the evaluation the Markdown links to."""
    if not isinstance(output, str):
        return False
    parts = [part for part in PurePosixPath(output).parts if part != "."]
    return bool(parts) and ".." not in parts and list(path.parts[-len(parts):]) == parts


def inspection_statuses(path: Path | str) -> dict[str, InspectionStatus]:
    """The Q19 statuses a recorded inspection assigned, by job id.

    Reads either shape the two inspections were written in: the 09-11
    errata's table (`notes/reference_rescore_2026-09-11/semantic_errata.md`)
    or the CBORG review's per-record sections
    (`notes/reference_rescore_2026-09-12_cborg_runtime/semantic_review.md`).
    Evaluation links resolve against the document's directory. A status the
    inspections never used, a record listed twice, a table row that is not a
    record, or a document with no records is an error, not a skipped line.

    Where the inspection has a JSON companion (`semantic_errata.json`,
    `semantic_review.json`), it must name the same records with the same
    statuses, outputs, Q19 scores and, where the Markdown records one, the
    same hash; the hash each status carries is the companion's. The 09-11
    errata's Markdown hashes only the 15 records it flagged, its companion
    all 24, so without the companion 9 of the evaluations it read could not
    be tied to their bytes.
    """
    md = Path(path)
    text = md.read_text(encoding="utf-8")
    # One `## <record>` heading per record section; prose headings have spaces.
    heads = list(re.finditer(r"^## (\w+)\s*$", text, re.M))
    sections = {}
    for i, m in enumerate(heads):
        if m.group(1) in sections:
            raise ValueError(f"{md}: {m.group(1)} has two sections")
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        sections[m.group(1)] = text[m.end():end]

    rows = _table_rows(md, text)
    if not rows:
        for job, body in sections.items():
            status, output = _SECTION_STATUS.search(body), _SECTION_OUTPUT.search(body)
            if not (status and output):
                raise ValueError(f"{md}: {job}: section has no Q19 status or no evaluation link")
            rows.append((job, int(status["score"]), status["status"], output["path"]))
    if not rows:
        raise ValueError(f"{md}: no inspection records found")
    out = {}
    for job, score, status, link in rows:
        if status.strip().lower() not in _STATUS:
            raise ValueError(f"{md}: {job}: unknown inspection status {status!r}")
        if job in out:
            raise ValueError(f"{md}: {job} is listed twice")
        body = sections.get(job)
        sha = _SECTION_SHA.search(body) if body is not None else None
        out[job] = InspectionStatus(job, (md.parent / link).resolve(), score,
                                    _STATUS[status.strip().lower()],
                                    sha["sha"] if sha else None)
    found = _companion(md)
    if found is None:
        return out
    companion, cases = found
    if set(cases) != set(out):
        raise ValueError(
            f"{companion}: names other records than {md.name}: only in the companion "
            f"{sorted(set(cases) - set(out))}, only in the Markdown {sorted(set(out) - set(cases))}")
    for job, status in out.items():
        case = cases[job]
        recorded = _STATUS.get(str(case.get("status", "")).strip().lower())
        score = _companion_score(case)
        disagree = [what for what, differs in (
            ("status", recorded != status.flagged),
            ("output", not _names(status.path, case.get("output"))),
            ("Q19 score", score is not None and (isinstance(score, bool) or score != status.q19_score)),
            ("sha256", status.sha256 not in (None, case["evaluation_sha256"])),
        ) if differs]
        if disagree:
            raise ValueError(f"{companion}: {job}: {', '.join(disagree)} disagree with {md.name}")
        out[job] = InspectionStatus(job, status.path, status.q19_score, status.flagged,
                                    case["evaluation_sha256"])
    return out


def sha256_of(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# -- the report `d4d evaluate q19-lint` prints --------------------------------

def _shown(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def lint_report(paths=(), inspections=(), *, show: bool = False) -> tuple[list[str], int]:
    """Lint rubric20 semantic evaluations and say how the result compares
    with the recorded inspections. Returns the report's lines and the number
    of flagged ratings; evaluation files are read, never written.

    `paths` are evaluation files, or directories searched for
    `*_evaluation.json`. Each of `inspections` (a `semantic_errata.md` or
    `semantic_review.md`) adds the evaluations it names, and is refused where
    one is missing, where the inspection records no hash for it (in its JSON
    companion or its Markdown), where it no longer hashes to the bytes the
    inspection read, or where its Q19 score is not the one the inspection
    recorded: agreement would then compare other text. Raises ValueError for
    anything that cannot be read whole.
    """
    files = []
    for path in map(Path, paths):
        files.extend(sorted(path.rglob("*_evaluation.json")) if path.is_dir() else [path])
    recorded = {}
    for doc in map(Path, inspections):
        for status in inspection_statuses(doc).values():
            if not status.path.is_file():
                raise ValueError(f"{doc}: {status.job_id}: {status.path} is missing")
            if status.sha256 is None:
                raise ValueError(
                    f"{doc}: {status.job_id}: the inspection records no sha256 for {status.path} "
                    f"(no JSON companion, and no hash in its section); agreement could not be "
                    f"tied to the bytes it read")
            if sha256_of(status.path) != status.sha256:
                raise ValueError(
                    f"{doc}: {status.job_id}: {status.path} is not the bytes the inspection "
                    f"read (sha256 {status.sha256[:12]}…); agreement would compare other text")
            recorded[status.path] = (doc, status)
            files.append(status.path)
    seen, unique = set(), []
    for f in files:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            unique.append(f)
    if not unique:
        raise ValueError("nothing to lint: name evaluation files, directories or --inspection")

    results = []
    for f in unique:
        try:
            result = lint_file(f)
        except ValueError as exc:
            raise ValueError(f"{f}: {exc}") from exc
        doc, status = recorded.get(f.resolve(), (None, None))
        if status is not None and result.score != status.q19_score:
            raise ValueError(
                f"{doc}: {status.job_id}: the inspection records Q19 {status.q19_score}, "
                f"{f} scores {result.score}; agreement would compare other text")
        results.append((f, result))
    lines = []
    agree = {"both": [], "lint_only": [], "inspection_only": [], "neither": []}
    for f, r in results:
        score = "n/a" if r.score is None else (
            f"{r.score:g}/" + ("?" if r.max_score is None else f"{r.max_score:g}"))
        if r.basis == NOT_LINTED:
            # Nothing is withheld, so nothing is read as a reason; the
            # vocabulary is reported so a reader sees what the gate held back.
            named = ",".join(sorted({m.concern for m in r.mentions if m.kind == REPRESENTATION})) or "-"
            line = f"{r.verdict:32}{score:>6}  mentions={named}"
        else:
            rep = ",".join(r.concerns(REPRESENTATION)) or "-"
            sub = ",".join(r.concerns(SUBSTANTIVE)) or "-"
            line = f"{r.verdict:32}{score:>6}  rep={rep}  sub={sub}"
        if r.basis == UNSTATED:
            # The label's credit and the body's credit were not read (#3070).
            line += "  (nothing says why: label reason clauses and body gaps read)"
        doc, status = recorded.get(f.resolve(), (None, None))
        if status is not None:
            key = ("both" if status.flagged and r.flagged else "lint_only" if r.flagged
                   else "inspection_only" if status.flagged else "neither")
            # Job ids repeat across inspections; the directory says which.
            agree[key].append(f"{doc.parent.name}/{status.job_id}")
            line += f"  inspection={'flagged' if status.flagged else 'unflagged'}"
        lines.append(f"{line}  {_shown(f)}")
        if show:
            lines.extend(f"    [{reason.kind}:{reason.concern}] {reason.field}: "
                         f"{reason.match!r} in: {reason.sentence}" for reason in r.reasons)
    flagged = sum(1 for _, r in results if r.flagged)
    below = sum(1 for _, r in results if r.basis != NOT_LINTED)
    verdicts = Counter(r.verdict for _, r in results)
    lines.append(f"\n{flagged} flagged of {below} Q19 score(s) below maximum; {len(results)} rating(s): "
                 + ", ".join(f"{v} {n}" for v, n in sorted(verdicts.items())))
    if recorded:
        compared = sum(len(v) for v in agree.values())
        lines.append(f"inspection agreement: {len(agree['both']) + len(agree['neither'])}/{compared}"
                     f" (flagged by both {len(agree['both'])}, by neither {len(agree['neither'])})")
        for key, what in (("inspection_only", "flagged by the inspection, not the lint"),
                          ("lint_only", "flagged by the lint, not the inspection")):
            if agree[key]:
                lines.append(f"  {what}: {', '.join(sorted(agree[key]))}")
    return lines, flagged
