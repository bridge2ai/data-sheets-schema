"""Combine replicates into one record, without splicing two different subjects.

Replicates differ in coverage, not quality (#176): across all four projects,
ranking by fitness reproduces ranking by slot count, because per-field quality is
drawn from one distribution while the *set* of populated fields varies. So the
gain available is coverage — take every slot any replicate produced.

The hazard is that `Dataset` admits one referent and replicates do not always
choose the same one. A union merge can then produce a record that validates
cleanly and describes nothing that exists.

## Measured on CM4AI, 2026-07-29

An unguarded union of the three generic replicates produced:

    title    Cell Maps for Artificial Intelligence (CM4AI) Data Release Programme
    version  June 2026 Data Release (Beta); Dataverse dataset version 2.0
    issued   2026-06-17T00:00:00Z
    doi      doi:10.18130/V3/HIGT4C

The title came from rep3 (the programme); the version, issue date and DOI came
from rep2 (one release inside it). The record claims to document a release
programme while carrying a single release's identity. **It passed
`linkml-validate`** — schema validation cannot see this, which is why a separate
referent check is needed rather than more validation.

## Why the first check missed it

The obvious check — compare referent-bearing fields across replicates and flag
disagreement — got this exactly backwards. It reported four problems, of which
`license` (`https://creativecommons.org/licenses/by-nc-sa/4.0/` vs
`CC BY-NC-SA 4.0`) and `status` (three prose elaborations of "Beta") are the same
fact written differently. And it *skipped* `version`, `issued` and `doi` entirely,
because it required two holders to compare and those appear in only one replicate.

That guard inverted the signal. **A referent-bearing field present in only some
replicates is the strongest evidence of divergence available**, because it means
one replicate committed to a narrower subject than the others. No string
comparison is needed to see it, and it is the one case a comparison-based check
cannot reach.

So this module distinguishes three findings, and treats asymmetry as decisive:

- ``representational`` — same referent, different form. Harmless to merge.
- ``referential`` — different referent asserted in the same field.
- ``asymmetric`` — the field exists in a subset of replicates, so those
  replicates identify a subject the others do not. Blocks an unguarded merge.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml

# Slots that answer "which thing is this record about?". Distinguished from slots
# that merely *describe* the thing: a disagreement here means two subjects, while
# a disagreement in `known_biases` means two descriptions of one subject.
#
# Split by strength. An `identity` field pins the subject to one artifact and its
# presence in only some replicates is decisive. A `naming` field labels the
# subject and varies freely in form, so it is judged rather than trusted.
IDENTITY_SLOTS = ("version", "issued", "doi", "identifier")
NAMING_SLOTS = ("id", "title", "landing_page", "publisher", "license", "status")
REFERENT_SLOTS = IDENTITY_SLOTS + NAMING_SLOTS

AGREE = "agree"
REPRESENTATIONAL = "representational"
REFERENTIAL = "referential"
ASYMMETRIC = "asymmetric"


@dataclass
class ReferentJudgement:
    """Do two renderings name the same subject, or different subjects?"""

    same_referent: bool
    reason: str = ""


class ReferentJudge(Protocol):
    def __call__(self, *, slot: str, values: dict[str, str]
                 ) -> ReferentJudgement: ...


@dataclass
class SlotFinding:
    slot: str
    kind: str                     # agree | representational | referential | asymmetric
    holders: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    values: dict[str, str] = field(default_factory=dict)
    reason: str = ""

    @property
    def blocks_merge(self) -> bool:
        return self.kind in (REFERENTIAL, ASYMMETRIC)


@dataclass
class ReferentReport:
    findings: list[SlotFinding] = field(default_factory=list)

    @property
    def blocking(self) -> list[SlotFinding]:
        return [f for f in self.findings if f.blocks_merge]

    @property
    def coherent(self) -> bool:
        return not self.blocking

    @property
    def verdict(self) -> str:
        if self.coherent:
            reps = [f.slot for f in self.findings
                    if f.kind == REPRESENTATIONAL]
            if reps:
                return ("coherent — replicates name one referent; "
                        f"{len(reps)} field(s) differ only in form")
            return "coherent — replicates agree on every referent-bearing field"
        asym = [f.slot for f in self.blocking if f.kind == ASYMMETRIC]
        refr = [f.slot for f in self.blocking if f.kind == REFERENTIAL]
        parts = []
        if asym:
            parts.append(f"{', '.join(asym)} present in only some replicates")
        if refr:
            parts.append(f"{', '.join(refr)} assert different referents")
        return "INCOHERENT — " + "; ".join(parts)


def _render(v: Any) -> str:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return str(v)
    return json.dumps(v, default=str, sort_keys=True)


def _normalise(s: str) -> str:
    """Collapse differences that never indicate a different subject.

    Case, whitespace, a trailing slash and a URL scheme. Deliberately narrow:
    anything beyond this is a semantic question and goes to the judge, because a
    normaliser aggressive enough to equate `CC BY-NC-SA 4.0` with its URL is also
    aggressive enough to equate two things that differ.
    """
    s = re.sub(r"\s+", " ", s).strip().lower().rstrip("/")
    return re.sub(r"^https?://", "", s)


def referent_report(records: dict[str, dict[str, Any]],
                    judge: ReferentJudge | None = None,
                    slots: tuple[str, ...] = REFERENT_SLOTS) -> ReferentReport:
    """Classify every referent-bearing field across replicates.

    ``judge`` decides whether two differing renderings name the same subject. It
    is injected so this is testable without an API key, and so the semantic call
    is visible rather than buried in a normaliser.
    """
    report = ReferentReport()
    labels = sorted(records)

    for slot in slots:
        holders = [l for l in labels if slot in records[l]]
        if not holders:
            continue

        # Asymmetry first, and without consulting the judge. A field that pins
        # the subject and appears in only some replicates means those replicates
        # chose a narrower subject — there is nothing to compare, and that is the
        # point. Naming fields are exempt: a missing `title` is an omission, not
        # a different subject.
        if len(holders) < len(labels) and slot in IDENTITY_SLOTS:
            report.findings.append(SlotFinding(
                slot=slot, kind=ASYMMETRIC, holders=holders,
                missing=[l for l in labels if l not in holders],
                values={l: _render(records[l][slot])[:200] for l in holders},
                reason=(f"{', '.join(holders)} pin an identity the others omit, "
                        "so they describe a narrower subject")))
            continue

        if len(holders) < 2:
            continue

        vals = {l: _render(records[l][slot]) for l in holders}
        if len({_normalise(v) for v in vals.values()}) == 1:
            report.findings.append(SlotFinding(
                slot=slot, kind=AGREE, holders=holders, values=vals))
            continue

        if judge is None:
            # No judge: report the difference without claiming to know its kind.
            # Guessing `referential` would block a merge over a trailing comma;
            # guessing `representational` would wave through a real fork.
            report.findings.append(SlotFinding(
                slot=slot, kind=REFERENTIAL, holders=holders, values=vals,
                reason="values differ and no semantic judge was supplied; "
                       "treated as referential because the safe default is to "
                       "refuse the merge"))
            continue

        j = judge(slot=slot, values=vals)
        report.findings.append(SlotFinding(
            slot=slot,
            kind=REPRESENTATIONAL if j.same_referent else REFERENTIAL,
            holders=holders, values=vals, reason=j.reason))

    return report


@dataclass
class MergeResult:
    record: dict[str, Any] = field(default_factory=dict)
    source_of: dict[str, str] = field(default_factory=dict)
    base: str = ""
    guarded: bool = False
    report: ReferentReport | None = None
    contested: int = 0

    @property
    def contributions(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for lab in self.source_of.values():
            out[lab] = out.get(lab, 0) + 1
        return out


def union_merge(records: dict[str, dict[str, Any]], *,
                scorer: Callable[..., Any] | None = None,
                project: str = "",
                base: str | None = None,
                guarded: bool = True,
                judge: ReferentJudge | None = None) -> MergeResult:
    """Union every replicate's slots, choosing the best-fitting contested value.

    ``guarded`` takes *all* referent-bearing fields from one base record rather
    than picking each independently. That is what keeps the subject single: the
    unguarded merge on CM4AI took its title from the programme-level replicate
    and its DOI from the release-level one, and the result described neither.
    Non-referent fields still come from whichever replicate supplied the
    best-fitting value, so the coverage gain survives the guard.

    A merge is refused when the report blocks and ``guarded`` is False, rather
    than written and left for a reader to notice.
    """
    labels = sorted(records)
    report = referent_report(records, judge=judge)
    if not guarded and report.blocking:
        raise ValueError(
            "refusing an unguarded merge: " + report.verdict +
            ". Pass guarded=True to pin referent-bearing fields to one base "
            "record, or resolve the divergence upstream.")

    base = base or max(labels, key=lambda l: len(records[l]))
    merged: dict[str, Any] = {}
    source_of: dict[str, str] = {}
    contested = 0

    union = sorted(set().union(*(set(r) for r in records.values())))
    for slot in union:
        holders = [l for l in labels if slot in records[l]]

        if guarded and slot in REFERENT_SLOTS:
            # Referent fields follow the base, or are dropped if the base lacks
            # them. Dropping is correct: importing an identity the base never
            # asserted is how the incoherent record got made.
            if slot in records[base]:
                merged[slot] = records[base][slot]
                source_of[slot] = base
            continue

        if len(holders) == 1:
            merged[slot] = records[holders[0]][slot]
            source_of[slot] = holders[0]
            continue

        contested += 1
        if scorer is None:
            merged[slot] = records[base][slot] if slot in records[base] \
                else records[holders[0]][slot]
            source_of[slot] = base if slot in records[base] else holders[0]
            continue

        scored = [(scorer(project=project, slot=slot,
                          value=records[l][slot]), l) for l in holders]
        # Ties break toward the base, so a merge stays as close to one coherent
        # record as the evidence allows.
        best = max(scored, key=lambda t: (_fitness(t[0]), t[1] == base))
        merged[slot] = records[best[1]][slot]
        source_of[slot] = best[1]

    return MergeResult(record=merged, source_of=source_of, base=base,
                       guarded=guarded, report=report, contested=contested)


def _fitness(j: Any) -> float:
    """Read a score off either judgement type, so both axes work here."""
    for attr in ("fitness", "supported"):
        v = getattr(j, attr, None)
        if v is not None:
            return float(v)
    return float(j)


REFERENT_JUDGE_SYSTEM = (
    "You decide whether two or more renderings of one metadata field identify "
    "the SAME subject, or DIFFERENT subjects.\n\n"
    "Same subject, different rendering — answer true:\n"
    "  - a licence URL versus its short label\n"
    "  - a CURIE versus the URL it resolves to\n"
    "  - the same status or title with different wording or added prose\n\n"
    "Different subjects — answer false:\n"
    "  - one names a release programme, another a single release within it\n"
    "  - different version numbers, DOIs, or dated editions\n"
    "  - different datasets, cohorts, or collections\n\n"
    "The question is what the values point AT, not how well they are written.\n\n"
    "Reply with a JSON object and nothing else:\n"
    '  {"same_referent": <true|false>, "reason": "<one sentence under 25 words>"}'
)


class LLMReferentJudge:
    """Ask the model whether differing values name the same subject."""

    def __init__(self, client=None, model: str | None = None,
                 max_tokens: int = 8000):
        self._client = client
        self._model = model
        # Sized for reasoning, not the answer — see evidence_score.LLMSlotScorer.
        self.max_tokens = max_tokens
        self.calls = 0

    def __call__(self, *, slot: str, values: dict[str, str]
                 ) -> ReferentJudgement:
        from data_sheets_schema import api_runner
        client = self._client or api_runner._client()
        model = self._model or api_runner._model_settings()["name"]

        rendered = "\n".join(f"  {lab}: {v[:600]}"
                             for lab, v in sorted(values.items()))
        prompt = (f"Field: `{slot}`\n\nValues from different generation runs of "
                  f"the same dataset:\n\n{rendered}\n\n"
                  "Do these identify the same subject?")
        resp = api_runner._call_with_retry(
            client, model=model, max_tokens=self.max_tokens, temperature=None,
            system=REFERENT_JUDGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}])
        self.calls += 1
        text = "".join(b.text for b in resp.content
                       if getattr(b, "type", "") == "text")
        return _parse_referent(text)


def _parse_referent(text: str) -> ReferentJudgement:
    """Parse a verdict, refusing to guess when the reply is unreadable.

    A truncated reply salvages `same_referent`, which is emitted first. An
    unreadable one raises rather than defaulting: defaulting to True would wave
    through the exact fork this check exists to catch, and defaulting to False
    would block every merge on a parse error.
    """
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        data = json.loads(m.group(0))
        if "same_referent" not in data:
            raise ValueError(f"judgement lacks `same_referent`: {data}")
        return ReferentJudgement(same_referent=bool(data["same_referent"]),
                                 reason=str(data.get("reason", "")))
    partial = re.search(r'"same_referent"\s*:\s*(true|false)', text, re.I)
    if partial:
        return ReferentJudgement(
            same_referent=partial.group(1).lower() == "true",
            reason="(reason truncated; verdict recovered from partial reply)")
    raise ValueError(f"no JSON object in referent judgement: {text[:200]!r}")


def write_merge(result: MergeResult, path: Path, *,
                sources: dict[str, Path] | None = None,
                project: str = "", method: str = "", label: str = "",
                provenance_path: Path | None = None) -> Path:
    """Write the merged record, and its provenance alongside when sources are given.

    ``sources`` maps each contributing replicate label to the record it supplied.
    Given it, a `record_mode: derived` provenance record is written naming every
    contributor by md5 and stating the rule that combined them — which is what
    makes a merged record shippable rather than an unattributed artifact.

    Omitting ``sources`` still writes the record, for probes and experiments, but
    the result carries no provenance and must not be treated as a datasheet.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(result.record, sort_keys=False, allow_unicode=True),
        encoding="utf-8")
    if not sources:
        return path

    from data_sheets_schema.provenance import (
        build_derived_record, contribution)

    def _source_label(path: Path) -> str:
        """The run label a contributing record sits under."""
        return Path(path).parent.name

    def _source_root(path: Path) -> Path:
        """The `d4d_concatenated` a source lives under, not the default one.

        Sources may sit outside the working corpus — a probe, a fixture, another
        checkout. Looking their attestation up in the default directory would
        report `none` for a record that is perfectly well attested where it
        actually is.
        """
        parts = Path(path).parts
        if "d4d_concatenated" in parts:
            i = parts.index("d4d_concatenated")
            return Path(*parts[:i + 1])
        return Path(path).parent.parent.parent

    def _source_method(path: Path) -> str:
        """The method a contributing record came from, read off its own path.

        Not the derived record's method: a source generated by
        `claudecode_agent` does not become a `claudecode_agent_merged` record by
        being consumed, and labelling it so would misattribute the generation.
        """
        parts = Path(path).parts
        if "d4d_concatenated" in parts:
            i = parts.index("d4d_concatenated")
            if len(parts) > i + 1:
                return parts[i + 1]
        return "unknown"

    from data_sheets_schema.runs import ATTESTED, LIVE, attestation

    # The playbook's cross-label carve-out is conditional, so the conditions are
    # checked here rather than trusted. Prose in a playbook binds an agent that
    # reads it; this binds the code path regardless.
    for lab, src in sorted(sources.items()):
        src_method = _source_method(src)
        if src_method.endswith("_merged") or "merged" in Path(src).parts:
            raise ValueError(
                f"{lab} is itself a derived record. Chaining merges makes the "
                "source md5s an incomplete account of where the content came "
                "from, and the provenance stops being checkable in one step.")
        level = attestation(src_method, _source_label(src), project,
                            _source_root(src))
        if level not in (LIVE, ATTESTED):
            raise ValueError(
                f"{lab} is {level}: its conditions cannot be established, so a "
                "record combining it would have inputs that cannot be placed. "
                "Only complete, attested runs may contribute.")

    contributions = [
        contribution(src, label=lab, project=project,
                     method=_source_method(src),
                     contributed_slots=sum(
                         1 for v in result.source_of.values() if v == lab))
        for lab, src in sorted(sources.items())]

    guard = ("referent-bearing fields pinned to base "
             f"`{result.base}`" if result.guarded else "unguarded union")
    rule = (
        f"Union of slots across {len(contributions)} replicates; where several "
        f"supplied one slot, the best-fitting value was taken ({guard}). "
        f"{result.contested} slots were contested.")
    rec = build_derived_record(
        project, method, label, sources=contributions, derivation=rule,
        outputs={"full": path},
        extra_notes=[result.report.verdict] if result.report else None)
    rec.write(provenance_path or path.with_name(f"{project}_provenance.yaml"))
    return path
