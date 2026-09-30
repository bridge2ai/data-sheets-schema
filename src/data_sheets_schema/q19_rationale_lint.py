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
  5") that is not itself disclaimed, accepted or conceded (the last point
  below), its neighbours when it names no reason itself ("Short of 5."),
  and the reason clauses of the score label (`_label_reasons`). A label's
  clauses end at punctuation, a spaced dash, a parenthesis and before
  "but", "without", "rather than" and "short of", so a reason given after
  one of those four words is the same with or without a comma. The reason
  runs from the label's first contrast or withholding cue onward ("…,
  short of a full provenance graph", "… - no typed derivation links", "…
  but no version history", "Held at 4 because …"). Before it, a clause
  saying something is absent ("…, structural derivation slots empty") is a
  reason too. A clause whose "not" or absence word stands inside it rather
  than opening it is read only where every concern it names is of one
  kind. Where it names both kinds ("Typed was_derived_from links and
  errata missing", "Machine-readable PROV graph lacking errata", "Typed
  PROV graph with errata not recorded"), its words do not say which is
  absent and which is credit, so it is not read; a comma ("…links, errata
  missing") makes the absent one a clause of its own, which is. The
  label's other clauses are credit and are not read. Two cases are read
  with the reason: credit in the clause that carries the first contrast or
  cue, or after it (#3128); and the words before a contrast that names
  nothing of its own ("graph claimed but not evidenced", "full provenance
  graph asserted rather than exhibited"), which is about them;
- the basis is `STATED` when a quality-note or semantic-analysis sentence
  carries a cue, or the label carries a withholding cue and names a reason
  ("Held at 4 because was_derived_from is empty"). A label's contrast or
  absence clause ("…, no formal provenance graph") names a gap the record
  has without saying that gap is what held the score, so it does not
  state the basis on its own;
- otherwise nothing says why the score is below the maximum
  (`basis == UNSTATED`), and every gap the quality note and semantic
  analysis name is a candidate reason beside the label's reason clauses.
  Each sentence is divided before every "but", "whereas" and "however",
  and a part is read only where it says something is absent, negated or
  incomplete (`_gap_parts`). A part that names no gap is credit and is not
  read, whether it comes before a contrast or after it ("RO-Crate packages
  include provenance graphs"; "No errata are recorded, but
  was_derived_from links every release to its parent dataset"). A part is
  read whole, so credit that shares a part with a gap is read (#3128). As
  in a label, a part that names a gap and nothing of its own is about the
  words before it in its clause, which are read with it ("changelog
  mentioned but not detailed");
- inside what is read, a clause that accepts, concedes or disclaims names
  no reason (`_clauses`). A withholding cue in a clause that accepts or
  concedes does not say why, nor does one after a disclaiming phrase or a
  negation within three words (`_says_why`); a disclaimer after the cue
  removes its clause from what is read, not the cue ("It falls short of 5
  not because of form but because no errata are recorded" says why):
  - it accepts where it says "accept", "permit" or "allow" in one of the
    forms `_PERMISSION` lists (accept, accepts, accepted, accepting,
    acceptable; permit, permits, permitted, permitting, permissible; allow,
    allows, allowed, allowing, allowable; #3227): "which the rubric accepts
    in place of a PROV-O serialization", "text is allowed in place of a
    PROV-O graph". Other derived words ("acceptance", "allowance") accept
    nothing, and "unacceptable" or "impermissible" is not a permission. A
    permission negated or restricted where it stands states a limit and is read ("does
    not allow a machine to traverse the lineage", "is not permitted",
    "allows only a human-readable reconstruction"; #3147). "In place of",
    like "instead of" and "rather than", says what a form is given as, not
    that it is accepted, so on its own it accepts nothing: "the lineage is
    given as prose in place of a PROV-O graph" is a reason (#3205). The
    lint does not check who accepts: whatever the subject of the
    permission, its clause is not read;
  - it concedes with "despite", "in spite of", "although", "(even) though",
    "regardless of" or "irrespective of" ("despite the dedicated field
    being empty");
  - it disclaims a deduction in so many words ("not a reason to withhold
    5", "not because …"), or where "not", "no", "nothing", "never", "none",
    "cannot" or "n't" comes within three words before a withholding cue or a
    word for deducting ("deduct…", "penalis…", "withh…"): "nothing is
    deducted for the empty was_derived_from", "no point is withheld",
    "does not keep it from 5", "not penalised" (#3145). A negation further
    back is about something else ("No errata are recorded and this keeps
    it from 5"). One within three words is always read as disclaiming, so
    a terse "No PROV graph so held at 4" gives no reason: the lint cannot
    tell it from a disclaimer.
  Clauses end at punctuation and before "but", "whereas", "however",
  "although", "(even) though", "despite", "in spite of", "regardless of"
  and "irrespective of", so a clause that concedes, or accepts after one of
  those words or punctuation, removes only itself even when it shares a
  sentence with a reason ("was_derived_from is empty even though the
  lineage is complete in prose", "… is empty regardless of the prose
  lineage", "text is permitted but no PROV graph is provided"; #3206).
  Clauses do not end at "and", so an acceptance joined to a reason by
  "and" alone shares its clause, and the whole clause, reason and any
  withholding cue included, is not read: "Held at 4 because
  was_derived_from is empty and the rubric accepts prose for lineage"
  gives `REASON_NOT_DETERMINED`, where the same sentence with a comma
  before "and" gives the empty-slot reason. Such a rating is marked
  `cue_unread`, and the report says a withholding cue was not read rather
  than that nothing says why (#3205). A label clause left unread because
  it names both kinds (above) is marked `label_ambiguous`, and the report
  says so rather than that nothing says why (#3404). A clause that opens
  with "but", "whereas" or "however", and disclaims without naming a concern of its own, is about the clause
  before it, which is not read either ("the empty was_derived_from is
  noted but not penalised"). A clause that is not read keeps its scope
  across the commas and parentheses that split what it is about (#3248):
  after it, an aside in parentheses is not read, verb or not, nor is a
  fragment with no finite verb (a list item: "nothing is deducted for the
  empty derivation slots (was_derived_from, parent_datasets)", "not
  because of the empty was_derived_from, parent_datasets or PROV graph"),
  and a disclaimer that has not yet reached its verb ("not because
  was_derived_from, parent_datasets and the PROV graph are empty") takes
  the fragment that supplies it. A disclaimer closing a list takes the
  list ("the empty was_derived_from, parent_datasets and PROV graph are
  noted, but that is not a reason to withhold 5"). The scope ends at a
  semicolon, colon or dash, at a conjunction, and at a fragment with a
  finite verb of its own after a complete clause. A verbless fragment
  may be an item of an outer list instead, and the lint does not guess
  but by parallel structure (`_outer_item`, #3260): after a clause that
  concedes or accepts, a fragment that opens with the word the clause
  before the concession opens with, where that word says something is
  absent ("no", "without", `_EMPTINESS`) and the concession carries it
  nowhere, is that outer list's item and is read ("no errata channel, no
  missing_data_documentation despite known_limitations confirming …, and
  no structured was_derived_from or parent_datasets linkage", the
  committed 09-11 CHORUS v7 rep1 rating). Otherwise it is not read, and
  a disclaimer's list is never an outer list. A shared article is no
  evidence (#3575): in "the errata are missing, although we accept the
  empty was_derived_from, the empty parent_datasets and the absent PROV
  graph" the last two objects are the acceptance's. `_FINITE` is a closed list
  of auxiliaries: widening it with lexical verbs ("links", "names",
  "records") would make plural nouns in a list ("no typed links") read as
  clauses of their own, and moved nothing on the committed ratings. A
  withholding cue in such a scope
  does not say why either (#3264): in the scope of an acceptance or
  concession it is reported as `cue_unread`, and in a disclaimer's it is
  disclaimed, so it neither states the basis nor sends the lint to its
  sentence's neighbours ("The rubric accepts prose (even if it falls
  short of a full graph)" reads as the same words with no parentheses).
  A label's reason clauses are ranges of the label, judged in the whole
  label, so they keep this scope too: "Good despite empty provenance
  fields (no was_derived_from)" names no reason, as the same label with
  no punctuation names none. A cue is judged by its whole clause, not
  the part of it after a label cut, and a contrast or cue in a clause
  that is not read starts no label reason, so the credit after it is not
  read as the rest of one ("Prose lineage accepted (short of a full
  graph); typed PROV graph otherwise complete").

Where nothing the lint reads names a concern, the verdict is
`REASON_NOT_DETERMINED`. The rationale may give no reason, give one outside
the vocabulary, or give it only in text the lint does not read. The verdict
is reported and is never a pass.

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
empty. So it is a reason only where a clause read with it, in the same
sentence or label range, carries one of the words `_EMPTINESS` lists
(#2982): "empty", "absent", "absence", "unpopulated", "unfilled",
"unused", "unset", "blank", "null", "missing" (not "missing-data"),
"omits"/"omitted", "lacks"/"lacking", "without", and the negations "no",
"not", "none", "nor", "neither", "never", "nothing" and "n't"; and an
absence named as a noun or a state (`_ABSENCE_NAMED`: "absences",
"absentee(s)", "gap(s)", "silent"). "Held at 4 because errata are thin;
was_derived_from links every release to its parent" gives no empty-slot
reason. An absence stated in other words ("was_derived_from is left out")
is not recognised, and the slot is then not read as a reason: the list is
closed, as `_FINITE` is. Its recall was measured on 2026-09-30 at
badb4eedd (#3544). In-sample it misses nothing: of the 121 sentences in
the Q19 fields of the 133 committed ratings that name a slot, 119 carry
an `_EMPTINESS` word, and the other two say the slot is populated
(CHORUS 2026-09-04f API rep1's "was_derived_from is explicit rather than
implied", superseded VOICE 2026-09-01 API rep2's "with was_derived_from
populated"). The gate drops none of the 88 empty-slot reasons read. The
vocabulary was written against those fields, so the measure is the text
it was not written against: the 1,046 distinct sentences outside them
that name a slot, anywhere in the committed evaluation outputs (other
rubric20 questions, rubric10 semantic). Of those, 769 carry an
`_EMPTINESS` word; 13 state an absence as a noun or a state, each naming
a slot that is absent, and those words are the `_ABSENCE_NAMED` list;
121 open with an imperative, recommendations ("Populate was_derived_from
…", "Mirror … into parent_datasets") that state no absence; and of the
other 143, read by hand, 16 say a slot is unused by saying where its
content is instead ("derivation in related_datasets rather than
was_derived_from", "four is_new_version_of related_datasets stand in for
parent_datasets", "recorded outside the derivation slots", "covered by
semantic equivalents: parent_datasets by …"). Those 16 are not
recognised, and no word marks them: "rather than" and "instead" as often
say a slot is used ("was_derived_from is explicit rather than implied",
the credit the gate was written to drop). Two more say how many of the
designated fields are populated ("Four of the five …") and name no absent
slot; the rest are credit. So on text it was not written against the
list misses 16 sentences, all of them placements; before the
`_ABSENCE_NAMED` words, which were taken from the 13, it missed 29. That
is no held-out figure for those four words. It bounds the
misses, not a recall ratio: which of the 769 carry their word about the
slot, rather than a negation about something else, was not read.
Recognising a placement needs the gate to tell a slot named as
unused from one named as credit, which a word list cannot. The
requirement is sentence-level, not clause-level, because 10 of the 88
empty-slot reasons read from the 133 committed ratings name the slot in a
list or parenthesis whose emptiness a neighbouring clause of the same
sentence states ("the dedicated derivation fields (was_derived_from,
parent_datasets) are empty", "No version history, errata or structured
derivation"); the other 78 name it in a clause carrying one of those
words. The requirement moved none of them. It does not tell which slot a
negation is about, so credit naming a populated slot beside a gap in the
same sentence is still read. Where nothing says why, a part of a sentence
that names no gap is not read, so credit naming a populated slot is not
read there unless it shares a part with a gap. Before that rule the
committed CHORUS 2026-09-04f API rep1 rating (UNSTATED) gave an
empty-slot reason, and a missing-data one, from "was_derived_from is
explicit rather than implied, and missing data is documented with reasons
at instance level", which says the slot is populated. A sentence that
says why the score is below 5 is still read whole, less the clauses that
accept, concede or disclaim. So a sentence that names a populated slot as
credit beside its reason, and says something is absent, would be read as
giving that reason (#3128). The requirement filters reasons and never
chooses what is read: where a label's reason starts, and whether a
sentence's neighbours or a part's preceding words are read, are decided
with every empty-slot match counted (`_names_reason`, #3576), so a
filtered match does not send the lint to credit around it.
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
#: Below the maximum, and nothing the lint reads names a concern: the
#: rationale gives no reason, gives one outside the vocabulary, or gives it
#: only where the lint does not read (a clause that accepts, concedes or
#: disclaims; a label clause whose words do not say which concern is
#: absent). Named `no_stated_reason` before review round 3 of #2967 (#3146).
REASON_NOT_DETERMINED = "reason_not_determined"
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
#: A cue counts only in a clause that is read (`_says_why`), so a negated
#: one ("nothing is deducted", "does not keep it from 5") disclaims.
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

#: A clause that concedes names no reason ...
_CONCESSION = re.compile(
    r"\bdespite\b|\bin spite of\b|\balthough\b|\bthough\b|\bregardless of\b|\birrespective of\b", _I)
#: ... nor does one that disclaims a deduction in so many words (see also
#: `_disclaims`). "rather than a deduction" and "rather than from being a 5"
#: disclaim; "a 4 rather than a 5" withholds, so the alternative names both
#: exactly.
_DISCLAIMER = re.compile(
    r"\bnot (?:itself )?(?:a|the) (?:reason|ground|deduction)|\bnot because\b"
    r"|\brather than (?:a deduction|from being a 5)\b"
    r"|\bwithout (?:moving|reducing|lowering|penali[sz]ing)"
    r"|\b(?:is|are) not required\b|\b(?:does|do|need) not (?:require|need|count|matter)", _I)
#: A clause that accepts a form says "accept", "permit" or "allow", in any
#: of the inflections and "-able"/"-ible" adjectives listed here (#3227;
#: "allowed" was missing beside "accepted" and "permitted") ...
#: "In place of" and "on equal footing" name no acceptance on their own:
#: "the lineage is given as prose in place of a PROV-O graph" is a reason,
#: as it is with "instead of" (#3205). Every committed rationale that says
#: either also says "accepts".
_PERMISSION = re.compile(
    r"\baccept(?:s|ed|ing|able)?\b|\bpermit(?:s|ted|ting)?\b|\bpermissible\b"
    r"|\ballow(?:s|ed|ing|able)?\b", _I)
#: ... unless the permission is negated or restricted where it stands, which
#: states a limit rather than accepting one (#3147): "does not allow a
#: machine to traverse", "is not permitted", "cannot be accepted", "allows
#: no machine traversal", "allows only a human-readable reconstruction",
#: "does not accept prose in place of a PROV-O graph", "is not permissible".
_PERMISSION_DENIED = re.compile(
    r"(?:\b(?:not|never|cannot)|n't)\s+(?:(?:be|been|being|itself)\s+)?(?:accept|permi[ts]|allow)\w*"
    r"|\b(?:accept|permi[ts]|allow)\w*\s+(?:no|only|nothing)\b", _I)
#: A negation, and the words for deducting that it can negate besides the
#: withholding cues. A negation within `_DISCLAIM_WINDOW` words before a
#: cue or one of those words disclaims a deduction (#3145): "nothing is deducted for …", "no
#: point is withheld", "does not keep it from 5", "not a ground for
#: withholding 5", "noted but not penalised".
_NEGATION = re.compile(r"\b(?:not|no|nothing|never|none|cannot)\b|n't\b", _I)
_DEDUCTION = re.compile(r"\b(?:deduct|penali[sz]|withh(?:eld|old))\w*", _I)
_DISCLAIM_WINDOW = 3
_WORD = re.compile(r"\w+")

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
#: conjunction, "no" or "not" (`_LABEL_OPENS`), or says "not" further in
#: (`_LABEL_NOT`), which, like an absence word, may follow credit in the
#: same clause ("Typed PROV graph with errata not recorded").
_LABEL_OPENS = re.compile(r"^(?:but|without|rather than|short of|no|not)\b", _I)
_LABEL_NOT = re.compile(r"\bnot\b", _I)
#: A label clause that says something is absent gives a reason with no
#: contrast word ("…, structural derivation slots empty", "…; version history
#: and missingness absent"). "missing-data documentation" names content.
_ABSENCE = re.compile(
    r"\b(?:empty|absent|unpopulated|unfilled|blank|lacking|lacks)\b|\bmissing\b(?![-_ ]data)", _I)

#: A quality-note or semantic-analysis sentence names a gap when it says
#: something is absent, negated or incomplete. Where nothing says why a score
#: is below its maximum, only the parts of sentences that name one are read
#: (`_gap_parts`): "RO-Crate packages include provenance graphs",
#: "was_derived_from is explicit rather than implied, and missing data is
#: documented" and "per-archive MD5 checksums give real integrity evidence"
#: are credit. A hyphenated "-only" is a name
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
#: The words that say a slot is empty or absent. An empty-slot match
#: (`REPRESENTATION_CONCERNS['empty_slot']`) names a slot; it is read as a
#: reason only where the words read with it, in the same sentence or label
#: range, carry one of these (#2982). Sentence-level on purpose: a clause-level
#: requirement loses the ten committed reasons that name the slot in a list
#: or parenthesis and say it is empty in a neighbouring clause ("the
#: dedicated derivation fields (was_derived_from, parent_datasets) are
#: empty"). "missing-data documentation" names content, not an absence.
#: "absence", "omits" and "unset" state an absence too (#3539). The list is
#: closed: an absence phrased otherwise is not recognised.
_EMPTINESS = re.compile(
    r"\b(?:empty|absent|absence|unpopulated|unfilled|unused|unset|blank|null|no|not|none|nor"
    r"|neither|never|nothing|without|lacks?|lacking|lacked|omits?|omitted|omitting)\b"
    r"|\bmissing\b(?![-_ ]data)|n't\b", _I)
#: Absence named as a noun or a state rather than by an `_EMPTINESS` word,
#: each found saying a slot is absent in committed evaluation text the
#: vocabulary was not written against (other rubric20 questions and the
#: rubric10 semantic outputs; #3544): "two absences: resources, and
#: parent_datasets", "parent_datasets is the sole absentee", "doi,
#: variables, resources and parent_datasets remain the gaps", "The one
#: gap, parent_datasets, …", "The dedicated provenance field is therefore
#: silent". The gate reads them with `_EMPTINESS` (`_says_empty`); what text
#: is read (`_outer_item`) does not, so they choose nothing read.
_ABSENCE_NAMED = re.compile(r"\b(?:absences|absentees?|gaps?|silent)\b", _I)


def _says_empty(text: str) -> bool:
    """Whether `text` says something is empty or absent, for the #2982
    empty-slot gate: an `_EMPTINESS` word or an `_ABSENCE_NAMED` one."""
    return bool(_EMPTINESS.search(text) or _ABSENCE_NAMED.search(text))


#: What divides a sentence's credit from its gap: "… is recoverable from
#: prose, which exceeds the version-history-only anchor, but no PROV-O graph".
_BODY_CONTRAST = re.compile(r"\b(?:but|whereas|however)\b", _I)

#: Sentences end at . ! ? — not at a semicolon, which in these rationales
#: joins a withholding cue to the reason it gives ("…lack accessions; that
#: combination … is what separates this from the top band"). The next
#: sentence may open with a lower-case slot name ("missing_information on …").
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[\w\"'(])|\n+")
#: Clauses end at punctuation and before a contrasting or conceding
#: conjunction (every `_CONCESSION` phrase, #3206), so a concession ("…is empty even though the lineage is
#: complete", "text is permitted but no PROV graph is provided") is judged
#: apart from the reason it shares a sentence with. The conjunction opens the
#: clause it heads, where `_CONCESSION` sees a concessive one; "but",
#: "whereas" and "however" head either side of a contrast and accept nothing.
_CLAUSE = re.compile(
    rf"\s*(?:{_CLAUSE_BREAK})\s*"
    r"|\s+(?=(?:but|whereas|however|although|even though|despite|in spite of"
    r"|regardless of|irrespective of)\b)"
    r"|(?<!\beven)\s+(?=though\b)", _I)
_CONTRAST_OPENS = re.compile(r"(?:but|whereas|however)\b", _I)


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
    #: Where the basis is UNSTATED: a withholding cue, neither negated nor
    #: disclaimed, stands in a clause that accepts or concedes, or in that
    #: clause's aside or list (#3264), so what it gives as the reason was
    #: not read (#3205). The rationale may say why;
    #: the lint could not tell which words were the reason.
    cue_unread: bool = False
    #: Where the basis is UNSTATED: a score-label clause says something is
    #: absent or "not" but names both kinds of concern, so it was not read
    #: (#3146): its words do not say which is absent and which is credit.
    #: The label may name a gap; the lint could not tell which (#3404).
    label_ambiguous: bool = False

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
        return SUBSTANTIVE_ONLY if sub else REASON_NOT_DETERMINED

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


def _kinds(text: str) -> set[str]:
    """The kinds of concern `text` names, read or not: vocabulary alone."""
    return {kind for kind, table in ((REPRESENTATION, REPRESENTATION_CONCERNS),
                                     (SUBSTANTIVE, SUBSTANTIVE_CONCERNS))
            if any(pattern.search(text) for pattern in table.values())}


def _names_concern(text: str) -> bool:
    """Whether `text` names any concern, read or not: vocabulary alone."""
    return bool(_kinds(text))


def _negated(clause: str, at: int) -> bool:
    """Whether a negation (`_NEGATION`) stands within `_DISCLAIM_WINDOW`
    words before position `at` of `clause`. A negation further back is
    about something else ("No errata are recorded and this keeps it from
    5")."""
    before = clause[:at]
    return any(len(_WORD.findall(before[n.end():])) <= _DISCLAIM_WINDOW
               for n in _NEGATION.finditer(before))


def _disclaims(clause: str) -> bool:
    """Whether a clause disclaims a deduction: in so many words
    (`_DISCLAIMER`), or by a negation within `_DISCLAIM_WINDOW` words before
    a withholding cue or a word for deducting (#3145). "Nothing is deducted
    for the empty was_derived_from", "no point is withheld for …", "does
    not keep it from 5", "is not a ground for withholding 5", "was not
    deducted here because …"."""
    return bool(_DISCLAIMER.search(clause)) or any(
        _negated(clause, target.start())
        for target in (*_WITHHOLDING.finditer(clause), *_DEDUCTION.finditer(clause)))


def _accepts(clause: str) -> bool:
    """Whether a clause concedes, or accepts a form by a permission that is
    not denied where it stands."""
    return bool(_CONCESSION.search(clause)
                or (_PERMISSION.search(clause) and not _PERMISSION_DENIED.search(clause)))


def _unread(clause: str) -> bool:
    """Whether a clause names no reason: it concedes, accepts or disclaims."""
    return _accepts(clause) or _disclaims(clause)


def _clauses(text: str) -> list[tuple[int, int, bool]]:
    """(start, end, read) of each clause of `text`, split at `_CLAUSE`.

    A clause is not read where it concedes, disclaims or accepts
    (`_unread`). A clause opening with "but", "whereas" or "however" that
    disclaims a deduction and names no concern of its own is about the
    clause before it, which is not read either: "the empty was_derived_from
    is noted but not penalised", "was_derived_from is empty, but that is
    not a reason to withhold 5". An acceptance names its own object ("no
    PROV graph is provided, but prose is accepted"), so it removes only
    itself.

    A clause that is not read keeps its scope across the commas and
    parentheses that split what it is about (`_in_scope`, #3248), so a slot
    named in a list or an aside of a disclaimer is not read as a reason:
    "nothing is deducted for the empty derivation slots (was_derived_from,
    parent_datasets)", "not because of the empty was_derived_from,
    parent_datasets or PROV graph", "not because was_derived_from,
    parent_datasets and the PROV graph are empty", "despite the dedicated
    fields (was_derived_from, parent_datasets) being empty". Where the
    words do not say whether a fragment continues the clause or starts one
    of its own, it is not read."""
    return [(a, b, read) for a, b, read, _ in _scoped_clauses(text)]


def _scoped_clauses(text: str) -> list[tuple[int, int, bool, int]]:
    """(start, end, read, origin) of each clause of `text`, as `_clauses`
    reads them. `origin` is the index of the clause whose words decide that
    a clause is not read: the clause itself where it concedes, accepts or
    disclaims (`_unread`), else the clause whose scope it is in, a
    disclaimer opening with "but", "whereas" or "however" after it, or the
    clause a comma or parenthesis continues (`_in_scope`). It is the
    clause's own index where the clause is read (#3264)."""
    clauses, seps, pos, sep = [], [], 0, ""
    for m in _CLAUSE.finditer(text):
        clauses.append([pos, m.start(), True, len(clauses)])
        seps.append(sep)
        pos, sep = m.end(), m.group(0).strip()
    clauses.append([pos, len(text), True, len(clauses)])
    seps.append(sep)
    for k, clause in enumerate(clauses):
        a, b = clause[0], clause[1]
        clause[2] = not _unread(text[a:b])
        if (k and _CONTRAST_OPENS.match(text, a) and _disclaims(text[a:b])
                and not _names_concern(text[a:b])):
            # The disclaimed clause, and the list or aside it closes.
            j = k - 1
            clauses[j][2:] = [False, k]
            while j and seps[j] in _SCOPE_SEPARATORS and not _FINITE.search(
                    text[clauses[j - 1][0]:clauses[j - 1][1]]):
                j -= 1
                clauses[j][2:] = [False, k]
    _in_scope(text, clauses, seps)
    return [tuple(clause) for clause in clauses]


#: What splits a clause's own list or aside from it: a comma or a
#: parenthesis. A semicolon, colon, dash or conjunction starts a clause of
#: its own.
_SCOPE_SEPARATORS = frozenset({",", "(", ")"})
#: A finite or auxiliary verb: a fragment carrying one says something of its
#: own; a fragment carrying none is a list item or an aside of the clause
#: before it ("was_derived_from", "parent_datasets or PROV graph", "being
#: empty"). A lexical verb outside this list is not seen, so such a fragment
#: after a clause that is not read is not read either: the rule reads less
#: rather than guess.
_FINITE = re.compile(
    r"\b(?:is|are|was|were|be|been|has|have|had|does|do|did|can|cannot|could|would"
    r"|should|will|may|might|must)\b|n't\b", _I)


def _in_scope(text: str, clauses: list[list], seps: list[str]) -> None:
    """Carry the scope of each clause that is not read forward, in place
    (#3248).

    A fragment continues the clause before it when that clause is not read,
    only a comma or a parenthesis (`_SCOPE_SEPARATORS`) divides them, and
    the fragment does not open with a conjunction of its own
    (`_OWN_CLAUSE`). A continuing fragment is not read where:

    - it opens or stands inside a parenthesis opened in that scope, or ends
      one: an aside is about what it follows, verb or not;
    - it has no finite verb (`_FINITE`): a list item or an aside of the
      clause ("was_derived_from", "parent_datasets or PROV graph"), unless
      parallel structure makes it an item of an outer list
      (`_outer_item`, #3260);
    - the clause is a disclaimer with no finite verb of its own, so it has
      not yet said what it disclaims ("not because was_derived_from"): the
      fragment that supplies the verb ("parent_datasets and the PROV graph
      are empty") completes the disclaimer and is not read either.

    A continuing fragment with a finite verb after a complete clause says
    something of its own and keeps its reading ("Although the lineage is
    complete in prose, was_derived_from is empty")."""
    depth, pending = 0, False
    for k, clause in enumerate(clauses):
        a, b, read = clause[:3]
        fragment = text[a:b]
        if not (k and not clauses[k - 1][2] and seps[k] in _SCOPE_SEPARATORS
                and not _OWN_CLAUSE.match(fragment)):
            depth, pending = 0, False
        elif seps[k] == "(" or (seps[k] == ")" and depth) or depth:
            depth += {"(": 1, ")": -1}.get(seps[k], 0)
            clause[2] = False
        elif not _FINITE.search(fragment):
            clause[2] = read and _outer_item(text, clauses, k)
        elif pending:
            clause[2], pending = False, False
        if not clause[2] and _disclaims(fragment) and not _FINITE.search(fragment):
            pending = True
        if read and not clause[2]:
            # Not read for its predecessor's words, not its own.
            clause[3] = clauses[k - 1][3]


#: The word a list item opens with, after any "and", "or" or "nor".
_LIST_LEAD = re.compile(r"\s*(?:(?:and|or|nor)\s+)?(?P<word>\w+)", _I)


def _outer_item(text: str, clauses: list[list], k: int) -> bool:
    """Whether the verbless fragment `clauses[k]`, in the scope of a clause
    that is not read, is an item of an outer list instead (#3260).

    It is where all of these hold:

    - the clause whose words put it out of scope concedes or accepts (a
      disclaimer's list stays disclaimed), and the clause before that one
      is read;
    - the fragment opens, after any "and", "or" or "nor", with the word
      that clause opens with, and that word says something is absent
      (`_EMPTINESS`: "no", "without", "missing" …). A shared article or
      any other shared word is not evidence of a list (#3575): in "the
      errata are missing, although we accept the empty was_derived_from,
      the empty parent_datasets and the absent PROV graph" every object
      opens with "the", and the last two are the acceptance's;
    - the conceding or accepting clause does not carry that word anywhere,
      so the fragment cannot be coordinated with an object of its own
      ("although we accept no was_derived_from, no parent_datasets").

    "no version_access, no errata channel, no missing_data_documentation
    despite known_limitations confirming modality availability is uneven,
    and no structured was_derived_from or parent_datasets linkage" reads
    its last item. "no errata despite no version history, no changelog"
    does not: the concession's own list opens with "no" too, so the words
    do not say whose item it is."""
    origin = clauses[k - 1][3]
    if origin < 1 or not clauses[origin - 1][2]:
        return False
    governing = text[clauses[origin][0]:clauses[origin][1]]
    if not _accepts(governing) or _disclaims(governing):
        return False
    lead = _LIST_LEAD.match(text, clauses[origin - 1][0], clauses[origin - 1][1])
    item = _LIST_LEAD.match(text, clauses[k][0], clauses[k][1])
    if not (lead and item and item["word"].lower() == lead["word"].lower()):
        return False
    word = lead["word"]
    return bool(_EMPTINESS.fullmatch(word)) and not re.search(
        rf"\b{re.escape(word)}\b", governing, _I)


#: A fragment opening with one of these was split at a conjunction and
#: carries its own reading.
_OWN_CLAUSE = re.compile(
    r"(?:but|whereas|however|although|even though|though|despite|in spite of"
    r"|regardless of|irrespective of)\b", _I)


def _says_why(text: str) -> bool:
    """Whether `text` carries a withholding cue that says why the score is
    below 5: one in a clause that neither concedes nor accepts, with no
    negation within `_DISCLAIM_WINDOW` words before it and no disclaiming
    phrase (`_DISCLAIMER`) before it in its clause. A disclaimer after the
    cue removes its own clause from what is read, not the cue: "It falls
    short of 5 not because of form but because no errata are recorded"
    says why.

    A cue in a clause that is not read for another clause's words (the
    aside or list of an acceptance, a concession or a disclaimer, #3248)
    does not say why either, so it neither states the basis nor sends the
    lint to the neighbouring sentences (#3264): "The rubric accepts prose
    (even if it falls short of a full graph)" gives no reason, as the same
    words without the parentheses give none."""
    return any(not accepts for accepts in _cue_clauses(text))


def _cue_clauses(text: str, lo: int = 0, hi: int | None = None):
    """For each withholding cue in `text` that starts within `lo`..`hi`
    (its clause judged whole, in the whole of `text`) that is neither negated within
    `_DISCLAIM_WINDOW` words nor preceded by a disclaiming phrase in its
    clause: whether its clause accepts or concedes (`_accepts`). A cue in a
    clause that is not read for another clause's words is yielded as
    accepting where that clause accepts or concedes, and not at all where
    it disclaims: a disclaimer's scope is disclaimed (#3264)."""
    hi = len(text) if hi is None else hi
    scoped = _scoped_clauses(text)
    for k, (a, b, read, origin) in enumerate(scoped):
        # The whole clause is judged, not the part of it inside the range:
        # "short of a graph" in "Prose accepted short of a graph" accepts.
        clause = text[a:b]
        governing = text[scoped[origin][0]:scoped[origin][1]]
        for cue in _WITHHOLDING.finditer(clause):
            if not lo <= a + cue.start() < hi:
                continue
            if _negated(clause, cue.start()) or _DISCLAIMER.search(clause[:cue.start()]):
                continue
            if origin == k:
                yield _accepts(clause)
            elif _accepts(governing):
                yield True


def _read_in(text: str, lo: int, hi: int) -> bool:
    """Whether any words of `text[lo:hi]` stand in a clause that is read,
    its clauses judged in the whole of `text` (`_clauses`)."""
    return any(read and text[max(a, lo):min(b, hi)].strip()
               for a, b, read in _clauses(text))


def _label_reasons(label: str) -> list[tuple[int, int]]:
    """The (start, end) of each part of one score-label sentence that gives
    a reason; the rest is credit. Each part is a range of the label, read
    with its clauses judged in the whole label (`_reasons`), so a part keeps
    the scope of the clause before it: in "Good despite empty provenance
    fields (no was_derived_from)" the parenthesis is the concession's
    aside and names no reason, as it does with no parenthesis (#3264).
    For the same reason a contrast or cue that is not read in the whole
    label (`_read_in`) does not start the reason: in "Prose lineage
    accepted (short of a full graph); typed PROV graph otherwise complete"
    the "short of" is the acceptance's aside, so the credit after the
    semicolon is not read as the rest of a reason.

    Clauses end at `_CLAUSE_BREAK` and before a contrasting conjunction
    (`_LABEL_CONJUNCTION`). The reason runs from the first clause carrying a
    contrast or a withholding cue (`_says_why`) to the end of the sentence:
    "Well beyond version history, with a declared provenance graph, short of
    an explicit graph in the record" gives its reason in the last clause,
    the first two are credit; "Typed derivation links in was_derived_from
    but no version history" gives it after "but", whatever punctuation
    precedes it; "Held at 4 because was_derived_from is empty" is a reason
    whole. A contrast that names nothing of its own is about the words
    before it in its clause, which are read with it: "graph claimed but not
    evidenced", "full provenance graph asserted rather than exhibited".

    Before the reason, a clause saying something is absent is a reason of
    its own ("Prose lineage; was_derived_from empty"). A clause whose "not"
    or absence word stands inside it rather than opening it is read only
    where every concern it names is of one kind. Where it names both kinds
    ("Typed was_derived_from links and errata missing", "Machine-readable
    PROV graph lacking errata", "Typed PROV graph with errata not
    recorded"), its words do not say which is absent and which is credit,
    and the answer would decide the flag, so it is not read (#3146).
    """
    return _label_reading(label)[0]


def _label_reading(label: str) -> tuple[list[tuple[int, int]], bool]:
    """`_label_reasons`, and whether a clause before the reason was left
    unread because it names both kinds of concern (#3146): a clause whose
    "not" or absence word stands inside it, in a clause that is read (not
    in a concession's or an acceptance's), and whose words do not say which
    concern is absent. The lint report says so rather than that nothing
    says why (#3404)."""
    def said_absent(pattern, lo, hi):
        return any(_read_in(label, m.start(), m.end()) for m in pattern.finditer(label, lo, hi))

    out, ambiguous = [], False
    for a, b in _spans(label):
        cuts = [a] + [m.end() for m in _LABEL_CONJUNCTION.finditer(label, a, b)]
        for i, start in enumerate(cuts):
            part = label[start:cuts[i + 1] if i + 1 < len(cuts) else b].strip()
            end = cuts[i + 1] if i + 1 < len(cuts) else b
            read = _read_in(label, start, end)
            if read and (
                    _LABEL_OPENS.search(part)
                    or any(not accepts for accepts in _cue_clauses(label, start, end))
                    or (_LABEL_NOT.search(part) and len(_kinds(part)) < 2)):
                if i and not _names_reason([("score_label", label, (start, b))]):
                    start = cuts[i - 1]
                return [(lo, hi) for lo, hi in out + [(start, len(label))]
                        if label[lo:hi].strip()], ambiguous
            ambiguous |= read and said_absent(_LABEL_NOT, start, end)
        clause = label[a:b].strip()
        absent = _ABSENCE.search(clause)
        if absent and (absent.start() == 0 or len(_kinds(clause)) < 2):
            out.append((a, b))
        elif absent and said_absent(_ABSENCE, a, b):
            ambiguous = True
    return out, ambiguous


def _gap_parts(sentence: str) -> list[tuple[int, int]]:
    """Where nothing says why: the (start, end) of each part of a
    quality-note or semantic-analysis sentence that is read.

    The sentence is divided before each "but", "whereas" and "however"
    (`_BODY_CONTRAST`), and a part is read only where it names a gap
    (`_GAP`). A part that names none is credit and is not read, whether it
    comes before a contrast ("…recoverable from prose, which exceeds the
    version-history-only anchor, but no PROV-O graph") or after one ("No
    errata are recorded, but was_derived_from links every release to its
    parent dataset", #3146). A part is read whole, so credit that shares a
    part with a gap is read (#3128). As in a label, a part that names a gap
    and nothing of its own ("changelog mentioned but not detailed") is about
    the words before it in its punctuation clause, which are read with it.
    Adjacent parts that are read are one range."""
    bounds = [0] + [m.start() for m in _BODY_CONTRAST.finditer(sentence)] + [len(sentence)]
    out = []
    for lo, hi in zip(bounds, bounds[1:]):
        if lo == hi or not _GAP.search(sentence[lo:hi]):
            continue
        if lo:
            a, b = next((a, b) for a, b in _spans(sentence) if a <= lo <= b)
            if not _names_reason([("", sentence, (lo, min(b, hi)))]):
                lo = a
        if out and lo <= out[-1][1]:
            lo = out.pop()[0]
        out.append((lo, hi))
    return out


def withholding_sentences(item: dict) -> list[tuple[str, str]]:
    """(field, sentence) pairs that say why the score is below its maximum:
    body sentences carrying a withholding cue in a clause that is read
    (`_says_why`), and a label's reason clauses (`_label_reasons`). A cue
    sentence that names no concern of its own ("Short of 5.", "One point is
    deducted for that gap.") gives its reason in a neighbour, so the
    sentences either side of it in the same field are read with it."""
    return [(name, text[lo:hi].strip()) for name, text, (lo, hi) in _withholding(item)]


def _withholding(item: dict) -> list[tuple[str, str, tuple[int, int]]]:
    """`withholding_sentences` as (field, sentence, (start, end)) triples,
    which `_reasons` reads with the sentence's clauses judged whole: a
    label's reason is a range of the label, not a string cut from it
    (#3264)."""
    sentences = _sentences(item)
    keep = []
    for i, (name, sentence) in enumerate(sentences):
        if name == "score_label":
            keep.extend((i, span) for span in _label_reasons(sentence))
        elif _says_why(sentence):
            keep.append((i, (0, len(sentence))))
            if not _names_reason([(name, sentence)]):
                keep.extend((j, (0, len(sentences[j][1]))) for j in (i - 1, i + 1)
                            if 0 <= j < len(sentences) and sentences[j][0] == name)
    seen, out = set(), []
    for i, span in sorted(keep, key=lambda k: k[0]):
        if (i, span) not in seen:
            seen.add((i, span)); out.append((sentences[i][0], sentences[i][1], span))
    return out


def _names_reason(pairs) -> bool:
    """Whether the clauses read in `pairs` name any concern, an empty-slot
    match counted whether or not anything says the slot is empty: concern
    detection, as `_reasons` read before #2982.

    The decisions that choose what text is read use this, not `_reasons`
    (#3576): where a label's reason starts, whether a body part is about
    the words before it, whether a cue sentence's neighbours are read, and
    whether a label says why. The #2982 emptiness gate only filters what
    that text gives as a reason. Were it to steer those decisions, a
    filtered empty-slot match would read as a text naming nothing and send
    the lint to the words around it, which may be credit: "Excellent
    version history but held at 4 for incomplete was_derived_from" would
    give "Excellent version history" as its reason."""
    return bool(_reasons(pairs, emptiness=False))


def _reasons(pairs, *, accepting: bool = True, emptiness: bool = True) -> tuple[Reason, ...]:
    """The concerns named in the clauses of each (field, text) pair that are
    read (`_clauses`; every clause when not `accepting`). A (field, text,
    (start, end)) triple reads only that range of `text`, its clauses judged
    in the whole of it, so a range that stops before "but not penalised"
    still does not read what that clause disclaims. Where `emptiness`, an
    empty-slot match counts only where a clause read in the range says
    something is empty (`_EMPTINESS`, #2982); `_names_reason` reads with
    it off to decide what text is read (#3576)."""
    found = {}
    for name, text, *within in pairs:
        lo, hi = within[0] if within else (0, len(text))
        shown = text[lo:hi].strip()
        clauses = [(max(a, lo), min(b, hi), read)
                   for a, b, read in _clauses(text) if max(a, lo) < min(b, hi)]
        # An empty-slot match is a slot's name; it is a reason only where the
        # words read say something is empty or absent (#2982).
        emptied = not (accepting and emptiness) or any(
            read and _says_empty(text[a:b]) for a, b, read in clauses)
        for a, b, read in clauses:
            if accepting and not read:
                continue
            clause = text[a:b].strip()
            for kind, table in ((REPRESENTATION, REPRESENTATION_CONCERNS),
                                (SUBSTANTIVE, SUBSTANTIVE_CONCERNS)):
                for concern, pattern in table.items():
                    if concern == "empty_slot" and not emptied:
                        continue
                    m = pattern.search(clause)
                    if m:
                        found.setdefault((concern, name, shown),
                                         Reason(concern, kind, name, m.group(0), shown, clause))
    return tuple(found.values())


def lint_q19(item: dict) -> Q19Lint:
    """Lint one Q19 item. The item is read, never changed."""
    score, maximum = _number(item.get("score")), _number(item.get("max_score"))
    sentences = _sentences(item)
    mentions = _reasons(sentences, accepting=False)
    if score is None or maximum is None or score >= maximum:
        return Q19Lint(score, maximum, NOT_LINTED, (), mentions)
    stated = _withholding(item)
    label = [(name, s, span) for name, s, span in stated if name == "score_label"]
    # A label says why the score is held when it carries a withholding cue
    # and names a reason ("Held at 4 because was_derived_from is empty").
    # A contrast or absence clause ("…, no formal provenance graph") names a
    # gap the record has without saying that is what held the score, and a
    # bare "Short of 5" names none, so both leave the body to say it.
    label_says_why = any(not accepts for _, s, span in label
                         for accepts in _cue_clauses(s, *span)) and _names_reason(label)
    if label_says_why or any(name != "score_label" for name, *_ in stated):
        return Q19Lint(score, maximum, STATED, _reasons(stated), mentions)
    # Nothing says why: the label's reason clauses and the body's parts that
    # name a gap are read (`_gap_parts`); a part naming no gap is not.
    body = [(name, s, part) for name, s in sentences if name != "score_label"
            for part in _gap_parts(s)]
    unread = any(accepts for _, s in sentences for accepts in _cue_clauses(s))
    ambiguous = any(_label_reading(s)[1] for name, s in sentences if name == "score_label")
    return Q19Lint(score, maximum, UNSTATED, _reasons(label + body), mentions, unread, ambiguous)


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
    same hash; a companion case that records no Q19 score disagrees, as one
    with no status or output does (#3228); the hash each status carries is the companion's. The 09-11
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
            ("Q19 score", score is None or isinstance(score, bool) or score != status.q19_score),
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
            # Only the label's reason clauses and the body's parts naming a
            # gap were read; a part naming no gap was not (#3070, #3146). A
            # cue in a clause that accepts or concedes, or in its aside or
            # list, was not read either, so "nothing says why" would be
            # false there (#3205, #3264). Nor where a label clause naming
            # both kinds of concern was left unread as ambiguous (#3404).
            said = "; ".join(text for flag, text in (
                (r.cue_unread, "a withholding cue stands in the scope of an acceptance or "
                               "concession and was not read"),
                (r.label_ambiguous, "a label clause names both kinds of concern and was left "
                                    "unread as ambiguous")) if flag) or "nothing says why"
            line += f"  ({said}: label reason clauses and body gaps read)"
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
