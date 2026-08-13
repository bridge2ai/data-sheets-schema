"""Score a D4D record against its input bundle, not against a reference.

There is no gold standard in this repository. The `curated` records were
produced through a ChatGPT chat interface and document superseded releases, so
scoring against them penalises correct current facts as errors (issue #177).
That leaves one defensible question: **is each populated slot supported by the
declared evidence?** It needs no reference, covers all four projects, and is
what the audit phase already asks of a single run.

The presence half cannot carry this alone. Measured across all four projects and
three replicates, rubric20 returns 71/88 for every record — every question
resolves as present and takes the stub's value of 4, so it cannot rank anything.
Rubric10 does separate replicates where they differ (CM4AI 39/42/43 against slot
counts 60/63/69) but is flat for AI-READI. So evidence support is the
discriminating component, and presence is the cheap prior.

## Why scoring is partitioned

Scoring every slot of every replicate is 897 field-judgements for four projects
at three replicates. Most of that is redundant: 249 of 299 slots are present in
*all* replicates. Scoring those once per project and propagating drops it to 399
— 56% fewer.

**The propagation is an approximation, and it is the weak point of this module.**
Slots present in all replicates still hold materially different values: across
CHORUS's 59 slots only 3 are byte-identical between replicates, and normalising
whitespace and ordering recovers none. The replicates assert similar facts in
different structure and prose. Propagating one score to all three therefore
assumes those variants are equally well supported, which is exactly the kind of
difference selection is supposed to detect.

So propagation is recorded, never silent: every `SlotScore` carries
``propagated``, and :func:`measure_propagation_error` re-scores a sample of
stable slots per replicate to quantify the cost. Run it before trusting a
ranking that propagation produced.

**Read that measurement by magnitude, not incidence.** Scores are continuous, so
two judgements of the same claim differ slightly nearly every time; on CM4AI 85%
of sampled stable slots had a nonzero spread, at a mean of 0.046 on a 0-1 scale.
What a ranking actually pays is ``record_level_spread`` — the gap between the
best and worst replicate's *mean* over those slots. Scattered error cancels
across 57 slots; error that consistently favours one replicate does not.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

import yaml

from data_sheets_schema import reasoning

@dataclass(frozen=True)
class JudgementContext:
    """Everything that can change a judgement's answer, in one declared place.

    The cache key is derived from this, not hand-assembled at each call site.
    That distinction is the whole point. Keyed by hand, the cache omitted the
    *bundle* — so judging `is_tabular: true` for AI-READI and then VOICE made one
    API call and gave VOICE the wrong verdict (#180). Patching that in place left
    two more inputs unkeyed, both of which were already live:

    - **the rubric.** `SCORER_SYSTEM` was edited mid-session; every judgement
      cached before the edit kept answering the old rubric.
    - **the schema.** Fitness is judged against `slot_spec()` output, so changing
      a slot's description or range invalidates every fitness judgement about it.
      In a schema project that is not hypothetical.

    Adding a field here changes every fingerprint automatically, so the next
    input cannot be forgotten the way these three were. Fields that do not apply
    to an axis stay empty rather than being omitted, so the two axes remain
    comparable and a grounding entry can never be mistaken for a fitness one.
    """

    axis: str                 # grounding | fitness
    model: str
    rubric: str               # digest of the system prompt actually sent
    corpus: str = ""          # bundle digest — grounding only
    schema: str = ""          # schema digest — fitness only

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"axis": self.axis, "model": self.model, "rubric": self.rubric,
             "corpus": self.corpus, "schema": self.schema}, sort_keys=True)
        return hashlib.md5(payload.encode("utf-8")).hexdigest()[:16]

    def as_entry(self) -> dict[str, str]:
        """The context fields as stored on every cache entry.

        Written in full rather than as the fingerprint alone so an entry is
        self-describing: a cache can be audited, and a mismatch can say *which*
        dimension moved instead of only that something did.
        """
        return {"axis": self.axis, "model": self.model, "rubric": self.rubric,
                "corpus": self.corpus, "schema": self.schema}

    @staticmethod
    def mismatch(entry: dict[str, Any], current: "JudgementContext") -> str | None:
        """Which dimension makes a stored entry unusable, if any."""
        for fieldname in ("axis", "model", "rubric", "corpus", "schema"):
            if entry.get(fieldname, "") != getattr(current, fieldname):
                return fieldname
        return None


def digest_of(text: str) -> str:
    """Short digest of any text that participates in a judgement's identity."""
    return hashlib.md5((text or "").encode("utf-8")).hexdigest()[:12]


def bundle_fingerprint(bundle: str) -> str:
    """Short digest identifying which corpus a grounding judgement was made against.

    Stored rather than the bundle itself: the bundles run to 80k+ tokens, and a
    cache entry only needs to answer "was this the same corpus?".
    """
    return hashlib.md5((bundle or "").encode("utf-8")).hexdigest()[:12]


# A scorer judges one slot's value against the bundle, returning 0.0-1.0.
# Injected rather than imported so this module is testable without an API key.
class SlotScorer(Protocol):
    def __call__(self, *, project: str, slot: str, value: Any,
                 bundle: str) -> "SlotJudgement": ...


@dataclass
class SlotJudgement:
    supported: float          # 0.0 unsupported .. 1.0 fully supported
    reason: str = ""


@dataclass
class SlotScore:
    slot: str
    label: str
    supported: float
    reason: str = ""
    # True when this score was computed for a different replicate and copied.
    # Load-bearing: a ranking built mostly from propagated scores is mostly
    # measuring the slots that diverged, which may be too few to rank on.
    propagated: bool = False


@dataclass
class Partition:
    """Slots split by whether every replicate populated them."""

    stable: set[str] = field(default_factory=set)
    divergent: set[str] = field(default_factory=set)

    @property
    def total(self) -> int:
        return len(self.stable) + len(self.divergent)

    def scoring_count(self, records: dict[str, dict[str, Any]]) -> int:
        """Judgements a plan performs: stable once, divergent per occurrence.

        Counted from the records rather than as ``divergent * n_replicates``.
        A divergent slot is by definition absent from at least one replicate,
        so multiplying overcounts — AI-READI's 5 divergent slots occupy 8
        replicate-slots, not 15.
        """
        return len(self.stable) + sum(
            1 for slot in self.divergent for r in records.values() if slot in r)

    def naive_count(self, records: dict[str, dict[str, Any]]) -> int:
        """Judgements without partitioning: every populated slot, every record."""
        return sum(len(r) for r in records.values())


def load_record(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8-sig")) or {}
    # Curated records wrap the dataset in a DatasetCollection; unwrap so the
    # slot sets are comparable with generated records.
    if isinstance(data, dict) and "DatasetCollection" in data:
        resources = (data["DatasetCollection"] or {}).get("resources") or []
        return dict(resources[0]) if resources else {}
    return data


def partition_slots(records: dict[str, dict[str, Any]]) -> Partition:
    """Split slots into those every replicate populated and those that vary.

    Presence, not value: values differ between replicates almost always, so a
    value-identity partition saves ~4% instead of ~56%. The cost of the looser
    definition is the propagation approximation documented above.
    """
    if not records:
        return Partition()
    sets = [set(r) for r in records.values()]
    union = set().union(*sets)
    stable = set.intersection(*sets) if sets else set()
    return Partition(stable=stable, divergent=union - stable)


@dataclass
class ScoringPlan:
    project: str
    partition: Partition
    # (slot, label) pairs actually to be judged. Stable slots appear once, with
    # the label of the replicate whose value represents them.
    to_score: list[tuple[str, str]] = field(default_factory=list)
    representative: dict[str, str] = field(default_factory=dict)


def build_plan(project: str, records: dict[str, dict[str, Any]],
               representative_label: str | None = None) -> ScoringPlan:
    """Decide what to judge, and which replicate speaks for each stable slot."""
    part = partition_slots(records)
    labels = sorted(records)
    rep = representative_label or (labels[0] if labels else "")

    plan = ScoringPlan(project=project, partition=part)
    for slot in sorted(part.stable):
        plan.to_score.append((slot, rep))
        plan.representative[slot] = rep
    for slot in sorted(part.divergent):
        for label in labels:
            if slot in records[label]:
                plan.to_score.append((slot, label))
    return plan


def run_plan(plan: ScoringPlan, records: dict[str, dict[str, Any]],
             bundle: str, scorer: SlotScorer) -> list[SlotScore]:
    """Execute a plan, propagating stable-slot judgements to every replicate."""
    scores: list[SlotScore] = []
    judged: dict[tuple[str, str], SlotJudgement] = {}

    for slot, label in plan.to_score:
        j = scorer(project=plan.project, slot=slot,
                   value=records[label].get(slot), bundle=bundle)
        judged[(slot, label)] = j

    for slot, rep_label in plan.representative.items():
        j = judged[(slot, rep_label)]
        for label in records:
            scores.append(SlotScore(slot=slot, label=label,
                                    supported=j.supported, reason=j.reason,
                                    propagated=(label != rep_label)))

    for slot in plan.partition.divergent:
        for label in records:
            if slot in records[label]:
                j = judged[(slot, label)]
                scores.append(SlotScore(slot=slot, label=label,
                                        supported=j.supported, reason=j.reason))
    return scores


@dataclass
class RecordScore:
    label: str
    evidence: float           # mean support over populated slots, 0.0-1.0
    presence: float           # rubric10 percentage / 100, or 0.0
    combined: float
    slots_scored: int
    slots_propagated: int
    # Sum of support — "how much grounded content does this record carry".
    # This is the ranking key; `evidence` is diagnostic. See combine().
    supported_slots: float = 0.0

    @property
    def propagated_fraction(self) -> float:
        return self.slots_propagated / self.slots_scored if self.slots_scored else 0.0


def combine(scores: Iterable[SlotScore], presence: dict[str, float],
            evidence_weight: float = 0.7) -> list[RecordScore]:
    """Per-replicate score from slot judgements plus a presence prior.

    Evidence is weighted above presence by default because presence rewards
    density — the failure mode where a record that fabricates plausible content
    outranks an honest sparse one. Presence is retained as a prior because a
    record can be scrupulously supported and still uselessly thin.

    ## Rank on `supported_slots`, not on `evidence`

    ``evidence`` is a *mean*, and a mean cannot rank these records. Measured on
    CM4AI: rep3 carried 12 of 16 divergent slots at 0.965 support against rep1's
    3 at 0.943 — a decisive difference — yet their evidence means came out
    0.9575 and 0.9553, a gap of 0.0022 against a measured propagation bias of
    0.016. The 57 stable slots are shared and mostly propagated, so they are
    near-identical by construction; averaging over them divides the signal by
    the very thing the records agree about.

    ``supported_slots`` — the *sum* of support — is the aggregation that matches
    the question. Summing rewards a record for covering more ground, but only
    insofar as the extra content is grounded: an unsupported slot scores 0.0 and
    adds nothing. On the same CM4AI data it separates cleanly — 66.07 / 59.91 /
    57.32 — where the mean could not.

    ## What that separation is *not* evidence of

    It reproduces the presence ranking exactly. Support ran 0.951-0.958 of slot
    count across all three replicates, so ``supported_slots`` here is little
    more than slot count rescaled by a near-constant, and counting slots — free —
    orders the records identically to 78 API judgements.

    So the case for evidence scoring is **not** that it ranks better. On this
    corpus it does not rank differently at all. The case is that it is a guard:
    a record that invents plausible content scores 0.0 on those slots and
    forfeits the credit presence would hand it. That guard is currently
    untested, because across 78 judgements nothing scored below 0.60 — there is
    no fabrication in this corpus for it to catch.

    Treat the two accordingly. Rank with presence; use evidence to detect when a
    record's coverage is not backed by the documents, which is the only case
    where the two diverge and the only case worth the tokens.
    """
    by_label: dict[str, list[SlotScore]] = {}
    for s in scores:
        by_label.setdefault(s.label, []).append(s)

    out = []
    for label, items in sorted(by_label.items()):
        ev = sum(i.supported for i in items) / len(items) if items else 0.0
        total = sum(i.supported for i in items)
        pr = presence.get(label, 0.0)
        out.append(RecordScore(
            label=label, evidence=ev, presence=pr,
            supported_slots=total,
            combined=evidence_weight * ev + (1 - evidence_weight) * pr,
            slots_scored=len(items),
            slots_propagated=sum(1 for i in items if i.propagated)))
    # Ranked by supported_slots for the reason above. `combined` is retained on
    # each record for comparison, but ordering by it reproduces the mean's
    # inability to separate.
    return sorted(out, key=lambda r: r.supported_slots, reverse=True)


def measure_propagation_error(project: str, records: dict[str, dict[str, Any]],
                              bundle: str, scorer: SlotScorer, *,
                              sample: int = 20, seed: int = 0) -> dict[str, Any]:
    """Re-score a sample of stable slots per replicate, to test propagation.

    Propagation assumes replicates' differing values for a shared slot are
    equally supported. This measures how wrong that is.

    ## Why incidence is the wrong question

    An earlier version of this function counted a "disagreement" whenever a
    slot's spread exceeded zero, and declared propagation unsafe above a 10%
    rate. Measured on CM4AI that returned 85%, which sounds decisive and is
    almost meaningless: scores are continuous, so two judgements of the same
    claim differ *slightly* nearly every time. The threshold was unreachable by
    construction, and the mean spread behind that 85% was 0.046 on a 0-1 scale.

    What propagation actually costs a *ranking* is the record-level term. Errors
    that scatter cancel when averaged over 57 slots; errors that all favour one
    replicate do not. So this reports both:

    - ``mean_spread`` / ``max_spread`` — per-slot disagreement magnitude.
    - ``record_level_spread`` — the gap between the best and worst replicate's
      mean over the sampled stable slots. This is the bias propagation injects
      into a record's score, and the number to compare against the difference
      selection must resolve.

    A high per-slot spread with a near-zero record-level spread means the scorer
    is noisy but unbiased, and propagation is affordable. Both high means
    propagation is picking a winner on its own.
    """
    part = partition_slots(records)
    rng = random.Random(seed)
    slots = sorted(part.stable)
    if not slots:
        return {"sampled": 0, "note": "no stable slots"}
    chosen = rng.sample(slots, min(sample, len(slots)))
    labels = sorted(records)

    detail: list[dict[str, Any]] = []
    deltas: list[float] = []
    per_label: dict[str, list[float]] = {lab: [] for lab in labels}

    for slot in chosen:
        judged = {lab: scorer(project=project, slot=slot,
                              value=records[lab].get(slot),
                              bundle=bundle).supported for lab in labels}
        spread = max(judged.values()) - min(judged.values())
        deltas.append(spread)
        for lab, v in judged.items():
            per_label[lab].append(v)
        detail.append({"slot": slot, "scores": judged, "spread": spread})

    means = {lab: sum(v) / len(v) for lab, v in per_label.items() if v}
    record_spread = max(means.values()) - min(means.values()) if means else 0.0
    material = sum(1 for d in deltas if d >= 0.25)

    return {
        "sampled": len(chosen),
        "stable_slots": len(slots),
        # Retained for continuity, but read `material_disagreements` instead:
        # any-difference incidence is ~1.0 for a continuous scorer by nature.
        "disagreements": sum(1 for d in deltas if d > 0),
        "disagreement_rate": sum(1 for d in deltas if d > 0) / len(deltas),
        # A gap of one grade band on the 0.0 / 0.5 / 1.0 scale the scorer is
        # given, so it marks a change of judgement rather than a wobble.
        "material_disagreements": material,
        "material_rate": material / len(deltas),
        "mean_spread": sum(deltas) / len(deltas),
        "max_spread": max(deltas),
        "label_means": means,
        "record_level_spread": record_spread,
        "verdict": _propagation_verdict(record_spread, material / len(deltas)),
        "detail": detail,
    }


# Below this, propagation moves a record's mean by less than the scorer's own
# per-slot noise, so it cannot invent a ranking. Not derived from theory — set
# against the observed CM4AI figures and should be revisited if a project shows
# a materially different noise profile.
RECORD_SPREAD_TOLERANCE = 0.05


def _propagation_verdict(record_spread: float, material_rate: float) -> str:
    if record_spread < RECORD_SPREAD_TOLERANCE and material_rate < 0.2:
        return ("propagation is affordable: per-slot noise cancels at record "
                "level")
    if record_spread < RECORD_SPREAD_TOLERANCE:
        return ("propagation shifts individual slots but not record totals; "
                "affordable for ranking, not for per-slot claims")
    return "propagation biases record scores; score every replicate fully"


SCORER_SYSTEM = (
    "You judge whether a claim in a dataset documentation record is supported "
    "by the source documents supplied. You are not assessing whether the claim "
    "is well written, complete, or desirable — only whether the documents "
    "substantiate it.\n\n"
    "Reply with a JSON object and nothing else:\n"
    '  {"supported": <0.0-1.0>, "reason": "<one sentence>"}\n\n'
    "1.0 = the documents state this directly.\n"
    "0.5 = the documents imply it, or support part of it.\n"
    "0.0 = the documents do not support it, or contradict it.\n\n"
    "A value that is plausible for this kind of dataset but absent from the "
    "documents scores 0.0. Plausibility is not evidence.\n\n"
    "Keep `reason` under 25 words. A long reason risks being cut off before the "
    "JSON closes, which discards the judgement entirely."
)


class LLMSlotScorer:
    """Judge slot values against the bundle via the API.

    Two things make this affordable. The bundle is a cached block, so a 81k-token
    corpus is written once and read thereafter — without that, judging 60 slots
    would mean 60 full reads of it. And identical values are memoised: replicates
    often repeat a value verbatim, and re-judging it would spend tokens to obtain
    an answer already held.

    Deliberately one slot per call rather than batched. Batching invites the
    model to score relative to the other slots in the batch, and the judgements
    then depend on which slots happened to travel together — a comparison
    artifact of exactly the sort this scoring exists to avoid.
    """

    # Sized for the reasoning, not the answer. The judgement itself is ~60
    # tokens, but `google/claude-opus-5-high` emits a thinking block first and
    # it is charged against max_tokens. At 1000 that block consumed the whole
    # budget: some replies were cut mid-JSON, and one arrived with *no* text at
    # all. Output is billed as produced, so a high ceiling costs nothing on the
    # calls that do not need it.
    def __init__(self, client=None, model: str | None = None,
                 max_tokens: int = 8000, log_path: Path | None = None,
                 cache_path: Path | None = None):
        self._client = client
        self._model = model
        self.max_tokens = max_tokens
        self.log_path = Path(log_path) if log_path else None
        # Judging one slot reads the whole bundle from cache — 7.5M cached-read
        # tokens for a 58-judgement propagation probe. Since a judgement is a
        # pure function of (model, slot, value, bundle), re-running the same
        # measurement should cost nothing, and without this every re-analysis
        # pays that again.
        self.cache_path = Path(cache_path) if cache_path else None
        self._loaded: set[str] = set()
        self.cache_loaded = 0
        self.cache_skipped: dict[str, int] = {}
        self._memo: dict[tuple[str, str, str], SlotJudgement] = {}
        self.calls = 0
        self.memo_hits = 0
        self.truncated = 0
        self.usage: list[dict[str, Any]] = []
        # Only calls, not memo hits: a memoised judgement did no new reasoning,
        # and logging it again would inflate the totals with duplicates.
        self.reasoning: list[dict[str, Any]] = []

    def _resolve(self):
        from data_sheets_schema import api_runner
        if self._client is None:
            self._client = api_runner._client()
        if self._model is None:
            self._model = api_runner._model_settings()["name"]
        return self._client, self._model

    def _load_cache(self, ctx: "JudgementContext") -> None:
        """Warm the memo from disk, keeping only entries made in this context.

        Deferred past __init__ because the model resolves lazily. Every entry
        carries the context it was produced under, so a mismatch is skipped and
        *named* — a cache that silently returns judgements from another model,
        rubric or corpus would make a comparison return itself.
        """
        fp = ctx.fingerprint()
        if fp in self._loaded or not self.cache_path:
            return
        self._loaded.add(fp)
        if not self.cache_path.exists():
            return
        skipped: dict[str, int] = {}
        for line in self.cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            why = JudgementContext.mismatch(e, ctx)
            if why is not None:
                skipped[why] = skipped.get(why, 0) + 1
                continue
            self._memo[(fp, e["slot"], e["value"])] = SlotJudgement(
                supported=e["supported"], reason=e.get("reason", ""))
        self.cache_loaded = len(self._memo)
        self.cache_skipped = skipped

    def __call__(self, *, project: str, slot: str, value: Any,
                 bundle: str) -> SlotJudgement:
        # Resolve before the memo check: the disk cache is keyed on the model,
        # so it cannot be consulted until the model is known.
        client, model = self._resolve()

        ctx = JudgementContext(axis="grounding", model=model,
                               rubric=digest_of(SCORER_SYSTEM),
                               corpus=digest_of(bundle))
        self._load_cache(ctx)

        key = (ctx.fingerprint(), slot,
               json.dumps(value, sort_keys=True, default=str))
        if key in self._memo:
            self.memo_hits += 1
            return self._memo[key]

        from data_sheets_schema.api_runner import _call_with_retry

        rendered = yaml.safe_dump({slot: value}, sort_keys=False,
                                  allow_unicode=True)
        parts = [
            {"type": "text", "text": f"# Source documents\n\n{bundle}",
             "cache_control": {"type": "ephemeral"}},
            {"type": "text",
             "text": (f"Record field `{slot}` asserts:\n\n```yaml\n{rendered}"
                      "```\n\nIs this supported by the source documents above?")},
        ]
        resp = _call_with_retry(client, model=model, max_tokens=self.max_tokens,
                                temperature=None, system=SCORER_SYSTEM,
                                messages=[{"role": "user", "content": parts}])
        self.calls += 1
        u = getattr(resp, "usage", None)
        self.usage.append({
            "slot": slot,
            "input": getattr(u, "input_tokens", None),
            "cache_read": getattr(u, "cache_read_input_tokens", None),
            "cache_write": getattr(u, "cache_creation_input_tokens", None),
            "output": getattr(u, "output_tokens", None),
        })

        # A judgement's reasoning is the case for its score. `supported: 0.5`
        # with a 25-word reason is not reviewable; the deliberation behind it
        # is. Captured per judgement, and written out if a log path was given.
        cap = reasoning.capture(resp)
        entry = {"project": project, "slot": slot, "model": model,
                 **cap.to_dict()}
        self.reasoning.append(entry)
        if self.log_path is not None:
            reasoning.append(self.log_path, entry)

        text = "".join(b.text for b in resp.content
                       if getattr(b, "type", "") == "text")
        truncated = getattr(resp, "stop_reason", None) == "max_tokens"
        try:
            judgement = _parse_judgement(text)
        except (ValueError, json.JSONDecodeError) as exc:
            # Distinguish "cut off" from "malformed". Reporting a truncation as
            # a parse failure sends the reader after a parser bug that does not
            # exist — which is exactly what happened on the first probe.
            if truncated:
                raise RuntimeError(
                    f"judgement for slot {slot!r} hit max_tokens "
                    f"({self.max_tokens}) and no score could be recovered. "
                    "Raise max_tokens.") from exc
            raise
        if truncated:
            self.truncated += 1
        self._memo[key] = judgement
        if self.cache_path is not None:
            # Appended as earned, so a probe interrupted at judgement 40 keeps
            # those 40 rather than restarting a full pass.
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    **ctx.as_entry(), "slot": slot, "value": key[2],
                    "supported": judgement.supported,
                    "reason": judgement.reason}, ensure_ascii=False) + "\n")
        return judgement


def _parse_judgement(text: str) -> SlotJudgement:
    """Read the model's verdict, refusing to guess when it is unreadable.

    An unparseable reply must not silently become 0.0 — that would score the
    record for the scorer's failure and quietly drag its evidence average down.

    A truncated reply is a special case worth salvaging rather than discarding.
    `supported` is emitted first, so a reply cut off inside the `reason` string
    still carries the score in full. Recovering it is not guessing: the number
    is present and complete, and only the explanation is lost. Slots holding
    long lists (CM4AI's `creators`) provoke reasons that enumerate every entry
    and overrun any sane ceiling, so this is the common case, not an edge one.
    """
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        data = json.loads(m.group(0))
        if "supported" not in data:
            raise ValueError(f"judgement lacks `supported`: {data}")
        return SlotJudgement(supported=float(data["supported"]),
                             reason=str(data.get("reason", "")))

    partial = re.search(r'"supported"\s*:\s*([0-9]*\.?[0-9]+)', text)
    if partial:
        return SlotJudgement(
            supported=float(partial.group(1)),
            reason="(reason truncated; score recovered from partial reply)")

    raise ValueError(f"no JSON object in judgement: {text[:200]!r}")


def savings(records: dict[str, dict[str, Any]]) -> dict[str, int | float]:
    part = partition_slots(records)
    naive, smart = part.naive_count(records), part.scoring_count(records)
    return {"stable": len(part.stable), "divergent": len(part.divergent),
            "naive_scorings": naive, "planned_scorings": smart,
            "reduction": (1 - smart / naive) if naive else 0.0}


# ---------------------------------------------------------------------------
# Fitness: does the value satisfy the field, as the schema specifies it?
# ---------------------------------------------------------------------------
#
# Grounding and fitness are different questions, and only the second
# discriminates. `LLMSlotScorer` asks whether a value traces to the source
# documents — but the generator was *given* those documents, so tracing back to
# them is close to tautological. Measured on CM4AI, 78 grounding judgements
# spanned 0.951-0.958 of slot count for every replicate, reproducing the
# free presence ranking and adding nothing.
#
# Fitness asks the question that is actually open: the slot declares a range, a
# cardinality and a description saying what belongs in it. Does this value
# satisfy that? A value can be impeccably documented and still be the wrong kind
# of thing — prose where a structured list is declared, an adjacent fact that
# does not answer the field, or a restatement of the field name carrying no
# content. None of that is visible to a grounding check.
#
# The two axes are deliberately judged in separate calls with separate prompts.
# Asking one judge for both invites it to average them, and a value that is
# well-documented but misplaced would come back mid-scale for the wrong reason.

FITNESS_SYSTEM = (
    "You judge whether a value placed in a dataset-documentation field actually "
    "satisfies that field, as the schema specifies it.\n\n"
    "You are NOT judging whether the value is true, or whether any document "
    "supports it. Assume it is accurate. Judge only fit: does this value answer "
    "what this field asks for, in the form the field declares?\n\n"
    "Weigh three things:\n"
    "  1. Form — does it match the declared range and cardinality? A single "
    "string where a list of structured objects is declared does not.\n"
    "  2. Target — does it answer *this* field, or an adjacent one? Naming the "
    "principal investigator does not answer who funded the work.\n"
    "  3. Substance — does it carry information? A value that restates the "
    "field name, or says documentation exists without giving it, is empty.\n\n"
    "Reply with a JSON object and nothing else:\n"
    '  {"fitness": <0.0-1.0>, "failure": "<none|form|target|substance>", '
    '"reason": "<one sentence>"}\n\n'
    "1.00 satisfies the field as specified.\n"
    "0.75 right kind of content, but partial or partly off-target.\n"
    "0.50 adjacent — related information that does not answer the field.\n"
    "0.25 wrong kind of content, or a contentless placeholder.\n"
    "0.00 does not belong in this field at all.\n\n"
    "Use the full range. Most fields in a competent record fit well; say so. "
    "But do not award 1.00 to a value that merely mentions the right topic.\n\n"
    "Keep `reason` under 25 words."
)


def slot_spec(slot: str, class_name: str = "Dataset",
              schema_path: Path | None = None) -> str:
    """Render one slot's schema specification, for a fitness judge to read.

    Includes the range class's own obligations when the range is a class: a
    judge told only `known_biases — DatasetBias [many]` cannot tell whether the
    value populated DatasetBias correctly, which is most of what fitness means
    for a structured range.
    """
    from data_sheets_schema import schema_digest

    digest = schema_digest.build(class_name, schema_path)
    sd = next((s for s in digest.slots if s.name == slot), None)
    if sd is None:
        return f"`{slot}` — not a slot of {class_name}."

    lines = [f"Field: `{sd.name}`",
             f"Declared range: {sd.range}"
             + (" (list — many values expected)" if sd.multivalued else "")
             + (" [required]" if sd.required else "")]
    if sd.description:
        lines.append(f"Specification: {sd.description}")
    if sd.enum_values:
        shown = ", ".join(sd.enum_values)
        more = (f" (+{sd.enum_truncated} more)" if sd.enum_truncated else "")
        lines.append(f"Permitted values: {shown}{more}")

    nested = next((n for n in digest.nested if n.name == sd.range), None)
    if nested:
        lines.append(f"`{sd.range}` requires: "
                     f"{', '.join(nested.required) or '(nothing)'}")
        if nested.optional:
            lines.append(f"`{sd.range}` also accepts: "
                         f"{', '.join(nested.optional)}")
        # The ranges of those attributes, without which "a wrong range" — one
        # of the two defects FORM_SUBTYPE_SYSTEM asks the judge to separate —
        # cannot be assessed below the top level (#486).
        #
        # Only non-string ranges: `string` is the default, so naming it adds
        # prompt length and no information, while `uriorcurie` is where a
        # plausible-looking value is the wrong kind. `unit: mg/dL` reads as a
        # perfectly good value until you know `unit` is declared `uriorcurie`.
        # Universal ranges once, then the ones specific to this class — the
        # same split the digest render uses, from the same constants, so the
        # judge's question and the cache key cannot drift apart.
        lines.append(f"On every `{sd.range}` object: "
                     f"{schema_digest.UNIVERSAL_RANGES}")
        typed = schema_digest.shown_ranges(nested)
        if typed:
            lines.append(
                f"`{sd.range}` attribute ranges: "
                + ", ".join(f"{k} → {v}" for k, v in typed.items()))
        lines.append(
            "A value of the wrong kind for its declared range is a form "
            "failure even when it reads well.")
        # The registry vocabulary those attributes draw from (#538). Without
        # it a judge cannot tell that a Cellosaurus cell line in
        # `data_substrate` is the wrong *kind* of thing — it is a resolvable
        # IRI, so every syntactic check passes it.
        for attribute, names in sorted(nested.values_from.items()):
            vocabulary = schema_digest.render_values_from(names)
            if vocabulary:
                lines.append(f"`{attribute}` must be drawn from {vocabulary}")
    return "\n".join(lines)


@dataclass
class FitnessJudgement:
    fitness: float
    failure: str = "none"     # none | form | target | substance
    reason: str = ""


class LLMSlotFitnessScorer:
    """Judge slot values against the schema specification, not the bundle.

    Cheaper per call than grounding: the prompt carries one slot's spec and one
    value rather than the whole document corpus, so there is no cached prefix to
    read and nothing to amortise. That also means no 7.5M-token cache read per
    sweep.
    """

    def __init__(self, client=None, model: str | None = None,
                 class_name: str = "Dataset", max_tokens: int = 8000,
                 log_path: Path | None = None, cache_path: Path | None = None,
                 schema_path: Path | None = None):
        self._client = client
        self._model = model
        self.class_name = class_name
        self.schema_path = schema_path
        # Sized for the reasoning, not the answer — see LLMSlotScorer.
        self.max_tokens = max_tokens
        self.log_path = Path(log_path) if log_path else None
        self.cache_path = Path(cache_path) if cache_path else None
        self._loaded: set[str] = set()
        self.cache_loaded = 0
        self._memo: dict[tuple[str, str, str], FitnessJudgement] = {}
        self.cache_skipped: dict[str, int] = {}
        self._specs: dict[str, str] = {}
        self.calls = 0
        self.memo_hits = 0
        self.truncated = 0
        self.usage: list[dict[str, Any]] = []
        self.reasoning: list[dict[str, Any]] = []

    def _resolve(self):
        from data_sheets_schema import api_runner
        if self._client is None:
            self._client = api_runner._client()
        if self._model is None:
            self._model = api_runner._model_settings()["name"]
        return self._client, self._model

    def _context(self, model: str) -> "JudgementContext":
        from data_sheets_schema import schema_digest
        return JudgementContext(
            axis="fitness", model=model, rubric=digest_of(FITNESS_SYSTEM),
            schema=schema_digest.fingerprint(
                schema_digest.digest_text(self.class_name, self.schema_path)))

    def _load_cache(self, ctx: "JudgementContext") -> None:
        """Keep only entries produced under this exact context.

        Fitness has no corpus, but it does have a *schema*: judgements are made
        against `slot_spec()` output, so editing a slot's description or range
        invalidates every judgement about it. That input was unkeyed until the
        context was introduced, which in a schema project is a live hazard
        rather than a theoretical one.
        """
        fp = ctx.fingerprint()
        if fp in self._loaded or not self.cache_path:
            return
        self._loaded.add(fp)
        if not self.cache_path.exists():
            return
        skipped: dict[str, int] = {}
        for line in self.cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            why = JudgementContext.mismatch(e, ctx)
            if why is not None:
                skipped[why] = skipped.get(why, 0) + 1
                continue
            self._memo[(fp, e["slot"], e["value"])] = FitnessJudgement(
                fitness=e["fitness"], failure=e.get("failure", "none"),
                reason=e.get("reason", ""))
        self.cache_loaded = len(self._memo)
        self.cache_skipped = skipped

    def as_slot_scorer(self) -> "SlotScorer":
        """Adapt to the SlotScorer protocol, so `run_plan` and
        `measure_propagation_error` work unchanged on the fitness axis.

        Worth having rather than duplicating that machinery: the partition,
        propagation and record-ranking logic is axis-agnostic, and the question
        "does propagation flatten differences" needs asking of whichever axis is
        actually used to rank — not only of the first one that was written.
        """
        def _score(*, project, slot, value, bundle=""):
            j = self(project=project, slot=slot, value=value)
            return SlotJudgement(supported=j.fitness,
                                 reason=f"[{j.failure}] {j.reason}")
        return _score

    def spec(self, slot: str) -> str:
        if slot not in self._specs:
            self._specs[slot] = slot_spec(slot, self.class_name,
                                          self.schema_path)
        return self._specs[slot]

    def __call__(self, *, project: str, slot: str, value: Any,
                 bundle: str = "") -> FitnessJudgement:
        """`bundle` is accepted and ignored, so this is drop-in for SlotScorer.

        Ignored on purpose: fitness must not consult the documents, or it
        collapses back into the grounding question this axis exists to separate
        from.
        """
        client, model = self._resolve()
        ctx = self._context(model)
        self._load_cache(ctx)

        key = (ctx.fingerprint(), slot,
               json.dumps(value, sort_keys=True, default=str))
        if key in self._memo:
            self.memo_hits += 1
            return self._memo[key]

        from data_sheets_schema.api_runner import _call_with_retry

        rendered = yaml.safe_dump({slot: value}, sort_keys=False,
                                  allow_unicode=True)
        prompt = (f"{self.spec(slot)}\n\n"
                  f"Value supplied:\n\n```yaml\n{rendered}```\n\n"
                  "Does this value satisfy the field as specified?")
        resp = _call_with_retry(client, model=model, max_tokens=self.max_tokens,
                                temperature=None, system=FITNESS_SYSTEM,
                                messages=[{"role": "user", "content": prompt}])
        self.calls += 1
        u = getattr(resp, "usage", None)
        self.usage.append({"slot": slot,
                           "input": getattr(u, "input_tokens", None),
                           "output": getattr(u, "output_tokens", None)})

        text = "".join(b.text for b in resp.content
                       if getattr(b, "type", "") == "text")
        truncated = getattr(resp, "stop_reason", None) == "max_tokens"
        try:
            judgement = _parse_fitness(text)
        except (ValueError, json.JSONDecodeError) as exc:
            if truncated:
                raise RuntimeError(
                    f"fitness judgement for slot {slot!r} hit max_tokens "
                    f"({self.max_tokens}) and no score could be recovered."
                ) from exc
            raise
        if truncated:
            self.truncated += 1

        cap = reasoning.capture(resp)
        entry = {"project": project, "slot": slot, "model": model,
                 "axis": "fitness", **cap.to_dict()}
        self.reasoning.append(entry)
        if self.log_path is not None:
            reasoning.append(self.log_path, entry)

        self._memo[key] = judgement
        if self.cache_path is not None:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    **ctx.as_entry(), "slot": slot, "value": key[2],
                    "fitness": judgement.fitness, "failure": judgement.failure,
                    "reason": judgement.reason}, ensure_ascii=False) + "\n")
        return judgement


def _parse_fitness(text: str) -> FitnessJudgement:
    """Read a fitness verdict, salvaging a score from a truncated reply.

    Same rule as `_parse_judgement`: `fitness` is emitted first, so a reply cut
    off inside `reason` still carries a complete score. Recovering it is not
    guessing; defaulting an unreadable reply to 0.0 would be.
    """
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        data = json.loads(m.group(0))
        if "fitness" not in data:
            raise ValueError(f"judgement lacks `fitness`: {data}")
        return FitnessJudgement(fitness=float(data["fitness"]),
                                failure=str(data.get("failure", "none")),
                                reason=str(data.get("reason", "")))

    partial = re.search(r'"fitness"\s*:\s*([0-9]*\.?[0-9]+)', text)
    if partial:
        return FitnessJudgement(
            fitness=float(partial.group(1)),
            reason="(reason truncated; score recovered from partial reply)")

    raise ValueError(f"no JSON object in fitness judgement: {text[:200]!r}")
