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
    evaluation_model: dict[str, Any] | None = None


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
    evaluation_model: dict[str, Any] | None = None

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
            holders=holders, values=vals, reason=j.reason,
            evaluation_model=getattr(j, "evaluation_model", None)))

    return report


@dataclass
class MergeResult:
    record: dict[str, Any] = field(default_factory=dict)
    source_of: dict[str, str] = field(default_factory=dict)
    base: str = ""
    guarded: bool = False
    report: ReferentReport | None = None
    contested: int = 0
    selection_mode: str | None = None
    scorer_identity: str | None = None
    scorer_instrument: dict[str, Any] | None = None

    @property
    def contributions(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for lab in self.source_of.values():
            out[lab] = out.get(lab, 0) + 1
        return out


def check_sources(sources: dict[str, Path], project: str) -> None:
    """Enforce the playbook's carve-out conditions on a set of contributing records.

    Called wherever the contributing *paths* are known, not only where provenance
    is being written. Gating on that was the wrong shape: the conditions are
    about whether a merge is legitimate, which does not depend on whether the
    caller asked for a provenance record — and the shorter call, which skipped
    them, is the one a hurried caller writes.
    """
    from data_sheets_schema.runs import ATTESTED, LIVE, attestation, record_mode

    # Without a project there is no provenance path to look up, so every source
    # would report `none` and the check would refuse everything — failing loudly
    # for the wrong reason, which is barely better than passing silently.
    if not project:
        raise ValueError(
            "check_sources needs the project: provenance is recorded per "
            "project, and without one every source resolves to no record.")

    for lab, src in sorted(sources.items()):
        method = _source_method(src)
        label = _source_label(src)
        root = _source_root(src)

        # `record_mode` is authoritative; the method name is a convention. A
        # derived record under a method not named *_merged would otherwise be
        # refused by the attestation check for the wrong reason, reporting
        # missing provenance rather than a chained merge.
        if record_mode(method, label, project, root) == "derived":
            raise ValueError(
                f"{lab} is itself a derived record. Chaining merges makes the "
                "source md5s an incomplete account of where the content came "
                "from, and the provenance stops being checkable in one step.")

        level = attestation(method, label, project, root)
        if level not in (LIVE, ATTESTED):
            hint = (" It looks like a derived record by its path, which would "
                    "explain the missing generation fields."
                    if "merged" in Path(src).parts or method.endswith("_merged")
                    else "")
            raise ValueError(
                f"{lab} is {level}: its conditions cannot be established, so a "
                "record combining it would have inputs that cannot be placed. "
                "Only complete, attested runs may contribute." + hint)


def _source_label(path: Path) -> str:
    """The run label a contributing record sits under."""
    return Path(path).parent.name


def _source_method(path: Path) -> str:
    """The method a contributing record came from, read off its own path.

    Not the derived record's method: a source generated by `claudecode_agent`
    does not become a `claudecode_agent_merged` record by being consumed, and
    labelling it so would misattribute the generation.
    """
    parts = Path(path).parts
    if "d4d_concatenated" in parts:
        i = parts.index("d4d_concatenated")
        if len(parts) > i + 1:
            return parts[i + 1]
    return "unknown"


def _source_root(path: Path) -> Path:
    """The `d4d_concatenated` a source lives under, not the default one.

    Sources may sit outside the working corpus — a probe, a fixture, another
    checkout. Looking their attestation up in the default directory would report
    `none` for a record that is perfectly well attested where it actually is.
    """
    parts = Path(path).parts
    if "d4d_concatenated" in parts:
        i = parts.index("d4d_concatenated")
        return Path(*parts[:i + 1])
    # No recognisable corpus root: treat the record's own directory as one, so
    # provenance lands beside it rather than in whatever the default happens to
    # be. A probe writing to /tmp keeps its provenance in /tmp.
    return Path(path).parent


def union_merge(records: dict[str, dict[str, Any]], *,
                scorer: Callable[..., Any] | None = None,
                project: str = "",
                base: str | None = None,
                guarded: bool = True,
                judge: ReferentJudge | None = None,
                source_paths: dict[str, Path] | None = None,
                scorer_identity: str | None = None) -> MergeResult:
    """Union slots using the base/first holder or a caller-supplied score.

    ``guarded`` takes *all* referent-bearing fields from one base record rather
    than picking each independently. That is what keeps the subject single: the
    unguarded merge on CM4AI took its title from the programme-level replicate
    and its DOI from the release-level one, and the result described neither.
    Without a scorer, contested fields use the base when present, otherwise the
    first holder in sorted label order. With a scorer, the maximum supplied
    numeric score wins, with ties preferring the base then the first holder.
    ``scorer_identity`` is an optional caller-declared label, not an authenticated
    instrument or evidence of scientific validity. A scorer is not invoked when
    there are no contested fields outside the guard.

    A merge is refused when the report blocks and ``guarded`` is False, rather
    than written and left for a reader to notice.
    """
    _validate_scorer_identity(scorer_identity)
    if scorer_identity is not None and not callable(scorer):
        raise ValueError("scorer_identity requires a supplied callable scorer")
    # Only the real fitness scorer can supply this context; generic callables
    # keep the existing caller-declared label/unknown behavior.
    instrument = None
    if scorer is not None:
        from data_sheets_schema.evidence_score import LLMSlotFitnessScorer
        if type(scorer) is LLMSlotFitnessScorer:
            instrument = scorer.pinned_instrument()
    labels = sorted(records)
    if source_paths:
        check_sources(source_paths, project)
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

    if instrument is not None and scorer.pinned_instrument() != instrument:
        raise ValueError("fitness instrument changed during merge")
    return MergeResult(record=merged, source_of=source_of, base=base,
                       guarded=guarded, report=report, contested=contested,
                       selection_mode=("base_or_first_holder" if scorer is None
                                       else "maximum_supplied_score"),
                       scorer_identity=scorer_identity,
                       scorer_instrument=instrument)


def _validate_scorer_identity(identity: str | None) -> None:
    if identity is not None and (type(identity) is not str or not identity.strip()):
        raise ValueError("scorer_identity must be a nonempty exact string or None")


def _selection_description(result: MergeResult) -> str:
    """Validate new metadata before publication; legacy mode remains unknown."""
    mode = result.selection_mode
    _validate_scorer_identity(result.scorer_identity)
    if mode is not None and (type(mode) is not str or mode not in {
            "base_or_first_holder", "maximum_supplied_score"}):
        raise ValueError("unrecognized merge selection_mode")
    if result.scorer_identity is not None and mode != "maximum_supplied_score":
        raise ValueError("scorer_identity requires maximum_supplied_score selection_mode")
    instrument = _instrument_description(result.scorer_instrument)
    if instrument is not None and mode != "maximum_supplied_score":
        raise ValueError("scorer_instrument requires maximum_supplied_score selection_mode")
    if mode is None:
        return "Selection mode was not recorded; whether a scorer ran is unknown."
    if mode == "base_or_first_holder":
        return (f"Contested slots use base `{result.base}` when it holds the slot, "
                "otherwise the first holder in sorted label order. No scorer was supplied.")
    identity = ("unrecorded" if result.scorer_identity is None else
                "caller-declared " + json.dumps(result.scorer_identity))
    selection = (f"Contested slots use the maximum supplied numeric score; ties prefer base "
                 f"`{result.base}`, otherwise the first holder in sorted label order.")
    invocation = ("No contested slots; the supplied scorer was not invoked."
                  if result.contested == 0 else "The supplied scorer was invoked for contested slots.")
    if instrument is not None:
        return (f"{selection} {invocation} Pinned fitness context: {instrument}. "
                "This records the checked context and scoring mode, not provider authenticity, "
                "calibration or scientific validity.")
    return (f"{selection} {invocation} Scorer identity: {identity}; "
            "this does not authenticate an instrument, model, calibration or scientific validity.")


def _instrument_description(instrument: dict[str, Any] | None) -> str | None:
    if instrument is None:
        return None
    from data_sheets_schema.evidence_score import JudgementContext, validate_fitness_context
    fields = {"context", "class_name", "profile", "schema_guidance", "mode",
              "cache_sha256", "cache_bytes"}
    if type(instrument) is not dict or set(instrument) != fields:
        raise ValueError("invalid scorer_instrument fields")
    context = instrument["context"]
    if type(context) is not dict or set(context) != {
            "axis", "model", "rubric", "corpus", "schema", "specification"}:
        raise ValueError("invalid scorer_instrument context")
    validate_fitness_context(JudgementContext(**context))
    if (type(instrument["class_name"]) is not str or not instrument["class_name"]
            or any(value is not None and (type(value) is not str or not value)
                   for value in (instrument["profile"], instrument["schema_guidance"]))):
        raise ValueError("invalid scorer_instrument selection")
    mode = instrument["mode"]
    if mode == "cache_only":
        if (type(instrument["cache_sha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", instrument["cache_sha256"]) is None
                or type(instrument["cache_bytes"]) is not int or instrument["cache_bytes"] < 0):
            raise ValueError("invalid scorer_instrument cache pin")
    elif mode != "live_or_cache" or instrument["cache_sha256"] is not None or instrument["cache_bytes"] is not None:
        raise ValueError("invalid scorer_instrument mode")
    return json.dumps(instrument, sort_keys=True)


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
        self.evaluation_model = None
        # Sized for reasoning, not the answer — see evidence_score.LLMSlotScorer.
        self.max_tokens = max_tokens
        self.calls = 0

    def __call__(self, *, slot: str, values: dict[str, str]
                 ) -> ReferentJudgement:
        from data_sheets_schema import api_runner
        client = self._client or api_runner._client()
        # One judge instance has one instrument, even if the configuration is
        # edited between fields of a report (#4231).
        if self.evaluation_model is None:
            from data_sheets_schema.evaluation_model import model_selection
            self.evaluation_model = model_selection(self._model)
            self._model = self.evaluation_model["name"]
        model = self._model

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
        result = _parse_referent(text)
        from copy import deepcopy
        result.evaluation_model = deepcopy(self.evaluation_model)
        return result


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


def check_merge_destination(path: Path, *, sources: dict[str, Path],
                            project: str, method: str, label: str,
                            provenance_path: Path | None = None) -> Path:
    """Validate sourced publication before writes; return its provenance path.

    A distinct label is insufficient: the destination method must differ from
    every source family, including the provenance ``_core`` alias. Conventional
    corpus paths must agree with the declared method/label. Explicit disjoint
    destinations outside a corpus remain supported for library callers.

    Existing symlinks and hard links to contributor artifacts are checked. This
    preflight does not promise atomic publication against concurrent path edits.
    """
    from data_sheets_schema.provenance import record_path_for

    for name, value in (("method", method), ("label", label), ("project", project)):
        if (not isinstance(value, str) or not value.strip() or value in (".", "..")
                or any(char in value for char in "/\\\0")):
            raise ValueError(f"merge destination {name} must be one nonempty path component")
    if method.endswith("_core"):
        raise ValueError("merge destination method must be a base method, not a _core alias")

    path = Path(path)
    provenance = (Path(provenance_path) if provenance_path is not None else
                  record_path_for(project, method, label, _source_root(path)))

    def resolved(candidate):
        try:
            return candidate.resolve()
        except RuntimeError as exc:  # pathlib on Python 3.9: symlink loop
            raise ValueError(f"cannot resolve merge destination/source: {candidate}") from exc

    def conventional(candidate, expected_method):
        if "d4d_concatenated" in candidate.parts:
            root = _source_root(candidate)
            expected = root / expected_method / label
            if (candidate.parent != expected or
                    resolved(candidate.parent) != resolved(root) / expected_method / label or
                    resolved(candidate).parent != resolved(root) / expected_method / label):
                raise ValueError("merge destination path does not match its declared method/label")

    conventional(path, method)
    conventional(provenance, f"{method}_core")
    conventional(resolved(path), method)
    conventional(resolved(provenance), f"{method}_core")
    targets = (path, provenance)
    real_targets = tuple(resolved(target) for target in targets)

    def same_file(first, second):
        return (resolved(first) == resolved(second) or
                (first.exists() and second.exists() and first.samefile(second)))

    if same_file(path, provenance):
        raise ValueError("merge full record and provenance must be distinct files")

    for src in sources.values():
        src = Path(src)
        source_method = _source_method(src)
        source_base = source_method[:-5] if source_method.endswith("_core") else source_method
        source_provenance = record_path_for(
            project, source_method, _source_label(src), _source_root(src))
        protected = {src.parent, source_provenance.parent}
        for source_path in (src, resolved(src)):
            if "d4d_concatenated" in source_path.parts:
                source_root = _source_root(source_path)
                family = _source_method(source_path)
                family = family[:-5] if family.endswith("_core") else family
                if method == family:
                    raise ValueError("merge output method must be distinct from every source method")
                protected.update((source_root / family, source_root / f"{family}_core"))
        if method == source_base:
            raise ValueError("merge output method must be distinct from every source method")
        for directory in protected:
            directory = resolved(directory)
            if any(target == directory or directory in target.parents or
                   (directory.exists() and any(parent.exists() and parent.samefile(directory)
                                               for parent in target.parents))
                   for target in real_targets):
                raise ValueError("merge destination aliases a contributing method/run directory")
        artifacts = (src, source_provenance,
                     source_provenance.parent / f"{project}_d4d_core.yaml",
                     source_provenance.parent / f"{project}_reconciliation.md")
        if any(same_file(target, artifact) for target in targets for artifact in artifacts):
            raise ValueError("merge destination aliases a contributing artifact")
    return provenance


def write_merge(result: MergeResult, path: Path, *,
                sources: dict[str, Path] | None = None,
                project: str = "", method: str = "", label: str = "",
                provenance_path: Path | None = None) -> Path:
    """Write the merged record, and its provenance alongside when sources are given.

    ``sources`` maps each contributing replicate label to the record it supplied.
    Given it, a `record_mode: derived` provenance record is written naming every
    contributor by md5 and stating the recorded selection rule. That disclosure
    does not certify scientific correctness or shipping eligibility.

    Omitting ``sources`` still writes the record, for probes and experiments, but
    the result carries no provenance and must not be treated as a datasheet.
    """
    selection = _selection_description(result)
    if sources:
        destination = check_merge_destination(
            path, sources=sources, project=project, method=method, label=label,
            provenance_path=provenance_path)
        check_sources(sources, project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(result.record, sort_keys=False, allow_unicode=True),
        encoding="utf-8")
    if not sources:
        return path

    from data_sheets_schema.provenance import (
        build_derived_record, contribution)

    contributions = [
        contribution(src, label=lab, project=project,
                     method=_source_method(src),
                     contributed_slots=sum(
                         1 for v in result.source_of.values() if v == lab))
        for lab, src in sorted(sources.items())]

    guard = ("referent-bearing fields pinned to base "
             f"`{result.base}`" if result.guarded else "unguarded union")
    rule = (
        f"Union of slots across {len(contributions)} replicates. {selection} "
        f"Referent guard: {guard}. "
        f"{result.contested} slots were contested.")
    rec = build_derived_record(
        project, method, label, sources=contributions, derivation=rule,
        outputs={"full": path},
        extra_notes=[result.report.verdict] if result.report else None)
    # The canonical path, not beside the record. `record_path_for` resolves to
    # `{method}_core/{label}/`, and every consumer — attestation, record_mode,
    # check_provenance — looks there. Writing it next to the record left four
    # correctly-formed derived records reporting `none`, provenance present and
    # invisible.
    # Resolved against the corpus the record is being written into, not the
    # default one. `record_path_for` defaults to the working corpus, so a merge
    # written to a temp directory would have deposited its provenance in the
    # real repository — right convention, wrong tree.
    rec.write(destination)
    return path
