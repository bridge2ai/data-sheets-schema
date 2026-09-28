"""Flag rubric20 Q19 scores held below 5 for how provenance is represented (#2911).

Rubric20 Q19 contradicts itself. Its scoring distinction and its 3/5 anchors
name a "full provenance graph", and the sentence between them says provenance
"may be represented as text OR as W3C PROV-O graphs". Evaluators resolve the
contradiction by withholding 5 for the form of the lineage rather than for its
content: an empty `was_derived_from`, no PROV serialization, lineage a machine
cannot traverse, lineage spread across fields. Two inspections of the recorded
1.0 ratings flagged 24 such rationales (#1337, #1349). The instrument has not
changed, so every later rating inherits the wording. This lint reads a
rating's own rationale and says whether it withholds 5 on those grounds, so
the check does not depend on someone rereading every Q19 by hand.

**What is read.** The Q19 item's `score_label`, `quality_note` and
`semantic_analysis` (whichever are present: a version-2.0 item carries no
per-item `semantic_analysis`). Nothing else. The input record is not read,
so the lint cannot tell whether the lineage content an evaluator missed is
really in the record. That is an adjudicator's question; this is a screen.

**Gated on the score and on withholding language.** Vocabulary alone does
not separate the two groups: every one of the 18 recorded Q19=5 rationales
names `was_derived_from`, a graph or PROV, usually to say the content is
carried elsewhere. So:

- a score at its maximum withholds nothing and is never flagged
  (`FULL_SCORE`); its vocabulary is still reported as `mentions`;
- below the maximum, only the sentences that say why the score is below it
  are read (`withholding_sentences`): a sentence with a score-directed cue
  ("held at 4 because", "falls short of the 5-band", "what keeps it from
  5"), its neighbours when it names no reason itself ("Short of 5."), and
  the reason clause of a score label that contrasts ("…, short of a full
  provenance graph", "…; no typed derivation links");
- a rationale below the maximum that never says why is read whole
  (`basis == UNSTATED`): every gap it names is a candidate reason;
- inside those sentences a clause that accepts or disclaims ("which the
  rubric accepts in place of a PROV-O serialization", "despite the
  dedicated field being empty", "not a reason to withhold 5") names no
  reason.

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
09-11 CHORUS v8 rep3 (flagged) and CBORG CHORUS v7 rep2 (unflagged) both
give an empty slot as their one representation reason beside artifact
granularity, identifiers and version history; and flagging a rating with a
substantive co-reason only when it also cites machine form or scattering
would miss four flagged ratings while still flagging 09-11 CM4AI v8 rep1.
A rule reproducing every label would be fitted to the phrasing of 48
rationales, so the lint flags these six and reports the disagreement
(`d4d evaluate q19-lint --inspection …`). The vocabulary was
written against these 48 rationales and read against the 85 other committed
rubric20 semantic outputs, which no inspection labels (plural "graphs", a
label's ", no …", a bare "Short of 5.", a passive "one point withheld" came
from those). Its precision and recall on unseen ratings are unmeasured.
An empty-slot match is the slot's name, not a check that the slot is
empty. On the committed ratings the two coincide (each of the 87 empty-slot
reasons read from the 133 comes from a sentence carrying an emptiness or
negation word), but a rationale that never says why its score is below 5
and names a populated `was_derived_from` as credit is read as giving that
reason.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

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
UNSTATED = "unstated"      # none do, so the whole rationale was read
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
    r"|\bfalls? short\b|\bshort of (?:5|the|a|full)\b|\bnot (?:a )?5\b|\bnot reach"
    r"|\bkeeps? (?:it|this|the score) from (?:5|five|the top|a 5|full)"
    r"|\bblocks? (?:a )?5\b|\bprevents? (?:a )?(?:higher|5|full)"
    r"|\bbelow the (?:top|5)|\bdeducted\b"
    r"|\bwithh(?:eld|olds?|olding) (?:the |a |full )?(?:5|five|top|point|band|mark)"
    r"|\b(?:5|five|point|mark|band) (?:is |was )?withheld\b"
    r"|\bwhat is missing\b|\btop band requires|\bfull marks require"
    r"|\b(?:asks|calls) for a full|\bneeds a (?:complete|full)"
    r"|\bseparates this from the top|\brather than (?:5|five)\b|\bnot quite complete\b", _I)

#: A clause that accepts a form or disclaims a deduction names no reason.
_ACCEPTANCE = re.compile(
    r"\baccepts?\b|\baccepted\b|\bpermits?\b|\bpermitted\b|\ballows?\b"
    r"|\bin place of\b|\bon equal footing\b|\bdespite\b|\beven though\b|\balthough\b"
    r"|\bregardless of\b|\birrespective of\b"
    r"|\bnot (?:itself )?(?:a|the) (?:reason|ground|deduction)"
    r"|\brather than (?:a|from being a) (?:deduction|5)"
    r"|\bwithout (?:moving|reducing|lowering|penali[sz]ing)"
    r"|\b(?:is|are) not required\b|\b(?:does|do|need) not (?:require|need|count|matter)", _I)

#: A score label is a one-line summary; it gives a reason when it contrasts.
_LABEL_CONTRAST = re.compile(
    r"\bbut\b|\bshort of\b|[,;:—]\s*no\b|\bnot\b|\bwithout\b|\brather than\b", _I)

#: Sentences end at . ! ? — not at a semicolon, which in these rationales
#: joins a withholding cue to the reason it gives ("…lack accessions; that
#: combination … is what separates this from the top band"). The next
#: sentence may open with a lower-case slot name ("missing_information on …").
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[\w\"'(])|\n+")
_CLAUSE = re.compile(r"\s*(?:[,;:()]|\s[—–-]{1,2}\s|—)\s*")


@dataclass(frozen=True)
class Reason:
    concern: str   # a key of REPRESENTATION_CONCERNS or SUBSTANTIVE_CONCERNS
    kind: str      # REPRESENTATION or SUBSTANTIVE
    field: str     # the rationale field the sentence came from
    match: str     # the matched text
    sentence: str


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


def _label_reason(label: str) -> str | None:
    """The part of a score label that gives a reason: from the clause holding
    its first contrast onward. "Well beyond version history, with a declared
    provenance graph, short of an explicit graph in the record" gives its
    reason in the last clause; the first two are credit."""
    m = _LABEL_CONTRAST.search(label)
    if m is None:
        return None
    start = max(label.rfind(sep, 0, m.start() + 1) for sep in ",;:—")
    return label[start + 1:].strip()


def withholding_sentences(item: dict) -> list[tuple[str, str]]:
    """(field, sentence) pairs that say why the score is below its maximum:
    body sentences carrying a withholding cue, and a contrasting label's
    reason clause. A cue sentence that names no concern of its own ("Short
    of 5.", "One point is deducted for that gap.") gives its reason in a
    neighbour, so the sentences either side of it in the same field are
    read with it."""
    sentences = _sentences(item)
    keep = []
    for i, (name, sentence) in enumerate(sentences):
        if name == "score_label":
            reason = _label_reason(sentence)
            if reason:
                keep.append((i, reason))
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
                                         Reason(concern, kind, name, m.group(0), sentence))
    return tuple(found.values())


def lint_q19(item: dict) -> Q19Lint:
    """Lint one Q19 item. The item is read, never changed."""
    score, maximum = _number(item.get("score")), _number(item.get("max_score"))
    sentences = _sentences(item)
    mentions = _reasons(sentences, accepting=False)
    if score is None or maximum is None or score >= maximum:
        return Q19Lint(score, maximum, NOT_LINTED, (), mentions)
    stated = withholding_sentences(item)
    if any(name != "score_label" for name, _ in stated):
        return Q19Lint(score, maximum, STATED, _reasons(stated), mentions)
    # Nothing says why: every gap the body names is a candidate reason, and
    # the label contributes its reason clause only, as above, not its credit.
    label = [(name, s) for name, s in stated if name == "score_label"]
    body = [(name, s) for name, s in sentences if name != "score_label"]
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
    sha256: str | None    # the bytes the inspection read, where it says


_STATUS = {"requires adjudication": True, "requires_adjudication": True,
           "not flagged by this inspection": False,
           "not_flagged_by_this_inspection": False}
#: The 09-11 errata's table: | record | Q19 | total | status | [link](path#Ln) |
_TABLE_ROW = re.compile(
    r"^\|\s*(?P<job>\w+)\s*\|\s*(?P<score>\d+)\s*\|\s*[\d.]+\s*\|\s*(?P<status>[^|]+?)\s*\|"
    r"\s*\[[^\]]*\]\((?P<path>[^)#]+)(?:#L\d+)?\)\s*\|\s*$", re.M)
#: The CBORG review's per-record sections.
_SECTION_STATUS = re.compile(r"^Recorded Q19: (?P<score>\d+)/5\. Status: `(?P<status>\w+)`\.", re.M)
_SECTION_OUTPUT = re.compile(r"^Original output: \[evaluation\]\((?P<path>[^)#]+)\)", re.M)
_SECTION_SHA = re.compile(r"^(?:Original output: .*?; |Evaluation )SHA256:? `(?P<sha>[0-9a-f]{64})`", re.M)


def inspection_statuses(path: Path | str) -> dict[str, InspectionStatus]:
    """The Q19 statuses a recorded inspection assigned, by job id.

    Reads either shape the two inspections were written in: the 09-11
    errata's table (`notes/reference_rescore_2026-09-11/semantic_errata.md`)
    or the CBORG review's per-record sections
    (`notes/reference_rescore_2026-09-12_cborg_runtime/semantic_review.md`).
    Evaluation links resolve against the document's directory. A status the
    inspections never used, a record listed twice, or a document with no
    records is an error, not a skipped line.
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

    rows = [(m["job"], int(m["score"]), m["status"], m["path"]) for m in _TABLE_ROW.finditer(text)]
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
    one is missing or no longer hashes to the bytes the inspection read:
    agreement would then compare other text. Raises ValueError for anything
    that cannot be read whole.
    """
    files = []
    for path in map(Path, paths):
        files.extend(sorted(path.rglob("*_evaluation.json")) if path.is_dir() else [path])
    recorded = {}
    for doc in map(Path, inspections):
        for status in inspection_statuses(doc).values():
            if not status.path.is_file():
                raise ValueError(f"{doc}: {status.job_id}: {status.path} is missing")
            if status.sha256 and sha256_of(status.path) != status.sha256:
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
            results.append((f, lint_file(f)))
        except ValueError as exc:
            raise ValueError(f"{f}: {exc}") from exc
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
            line += "  (no withholding sentence: whole rationale read)"
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
