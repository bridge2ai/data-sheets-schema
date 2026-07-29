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
stable slots per replicate to quantify how often the assumption was wrong. Run
it before trusting a ranking that propagation produced.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

import yaml

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
    """
    by_label: dict[str, list[SlotScore]] = {}
    for s in scores:
        by_label.setdefault(s.label, []).append(s)

    out = []
    for label, items in sorted(by_label.items()):
        ev = sum(i.supported for i in items) / len(items) if items else 0.0
        pr = presence.get(label, 0.0)
        out.append(RecordScore(
            label=label, evidence=ev, presence=pr,
            combined=evidence_weight * ev + (1 - evidence_weight) * pr,
            slots_scored=len(items),
            slots_propagated=sum(1 for i in items if i.propagated)))
    return sorted(out, key=lambda r: r.combined, reverse=True)


def measure_propagation_error(project: str, records: dict[str, dict[str, Any]],
                              bundle: str, scorer: SlotScorer, *,
                              sample: int = 20, seed: int = 0) -> dict[str, Any]:
    """Re-score a sample of stable slots per replicate, to test propagation.

    Propagation assumes replicates' differing values for a shared slot are
    equally supported. This measures how often that is false. A high
    disagreement rate means the ranking is being flattened precisely where it
    should discriminate, and the partition should be abandoned for full scoring.
    """
    part = partition_slots(records)
    rng = random.Random(seed)
    slots = sorted(part.stable)
    if not slots:
        return {"sampled": 0, "note": "no stable slots"}
    chosen = rng.sample(slots, min(sample, len(slots)))

    disagreements, deltas = 0, []
    for slot in chosen:
        judged = [scorer(project=project, slot=slot,
                         value=records[label].get(slot), bundle=bundle).supported
                  for label in sorted(records)]
        spread = max(judged) - min(judged)
        deltas.append(spread)
        if spread > 0:
            disagreements += 1

    return {
        "sampled": len(chosen),
        "stable_slots": len(slots),
        "disagreements": disagreements,
        "disagreement_rate": disagreements / len(chosen),
        "mean_spread": sum(deltas) / len(deltas),
        "max_spread": max(deltas),
        "verdict": ("propagation is safe" if disagreements / len(chosen) < 0.1
                    else "propagation flattens real differences; score fully"),
    }


def savings(records: dict[str, dict[str, Any]]) -> dict[str, int | float]:
    part = partition_slots(records)
    naive, smart = part.naive_count(records), part.scoring_count(records)
    return {"stable": len(part.stable), "divergent": len(part.divergent),
            "naive_scorings": naive, "planned_scorings": smart,
            "reduction": (1 - smart / naive) if naive else 0.0}
