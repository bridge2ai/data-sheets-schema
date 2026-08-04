"""Split the `form` fitness class into the two defects it conflates.

`notes/generic_v2_results.md` found that generic-v2's first rule did what it
said and the instrument could not show it. Form failures went 50 → 56, apparently
worse, while underneath:

    collapsed cardinality — several entities in one object   27 → 0
    hollow object — one object per entity, all content in
                    free-text `description`                   2 → 33

The rule eliminated the defect it named and produced a different one wearing the
same label. One `form` class covering two failures made a real improvement read
as a regression, and the note's conclusion was that any future comparison on
this axis has to split them. This module is that split.

**It does not re-judge fitness.** Editing `FITNESS_SYSTEM` would be the obvious
way to add sub-types and would invalidate all 1441 cached fitness judgements —
the cache is keyed on the rubric precisely so that a changed rubric cannot be
compared against an unchanged one. That is 13x the work and it would discard a
v1/v2 comparison that has already been paid for.

Instead this classifies the 106 form failures already in the cache. Each cached
entry carries the slot and the full value, which is everything the question
needs, so the existing fitness numbers stay exactly as published and the
sub-type breakdown is a second, narrower measurement layered on top.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from data_sheets_schema.agreement import (
    DEFAULT_CONFIGS,
    DEFAULT_ROOT,
    OfflineCacheMiss,
    _digest,
    _parse_verdict,
    load_replicates,
)

JUDGEMENT_CACHE = Path("data/evaluation_llm/judgement_cache")
SUBTYPE_CACHE = Path("data/evaluation_llm/form_subtype_cache")

#: Same reasoning as the judge cap in `agreement.py`: high enough that nothing
#: in this corpus reaches it, low enough that a pathological value cannot blow
#: the context of a paid call. Recorded per record so a later change is visible.
VALUE_CHARS = 100_000

SUBTYPES = ("collapsed_cardinality", "hollow_object", "both", "other")

FORM_SUBTYPE_SYSTEM = """\
A value has already been judged to fail on FORM — it does not match the range
or cardinality its field declares. You are not re-judging that. You are saying
WHICH form failure it is.

collapsed_cardinality
  The field declares a list, and several distinct real-world entities have been
  packed into ONE object. Three funders in a single Grant, four uses in a single
  IntendedUse, every subpopulation in one Subpopulation entry.

hollow_object
  Cardinality is RIGHT — one object per entity — but the object is hollow. The
  content sits in a free-text field such as `description` while the structured
  fields the range declares (`name`, `id`, `start_date`, `end_date`,
  `affiliations`, …) are unused. The shape is correct and empty.

both
  Entities are collapsed AND the objects are hollow.

other
  A form failure that is neither: a bare string where a list of objects is
  declared, a wrong range, a scalar where a structure belongs.

The distinction that matters is between the first two. Ask: how many objects are
there against how many entities the value describes, and are the declared
structured fields populated or is everything in prose?

Reply with JSON only:
{"subtype": "collapsed_cardinality|hollow_object|both|other", "reason": "<one sentence>"}
"""


@dataclass
class FormFailure:
    project: str
    slot: str
    value: str
    reason: str
    fitness: float
    config: str = ""          # v1 | v2, filled by attribution

    @property
    def key(self) -> str:
        return _digest(json.dumps([self.slot, self.value[:VALUE_CHARS]],
                                  ensure_ascii=False))


def load_form_failures(cache_dir: Path = JUDGEMENT_CACHE) -> list[FormFailure]:
    """Every cached fitness judgement whose failure class is `form`.

    Refuses a set spanning more than one fitness rubric or model. Those fields
    exist on every entry precisely so a judgement is self-describing, and this
    module's premise is that `FITNESS_SYSTEM` will not be edited *because*
    editing it invalidates the cache. If it ever is — or the fitness judge runs
    under a second model — pooling both here would mix two instruments while
    the sub-type table looked exactly the same (#277).

    Loudly rather than by filtering: a silent skip could halve the corpus and
    still produce a plausible table.
    """
    out: list[FormFailure] = []
    rubrics: set[str] = set()
    models: set[str] = set()
    for path in sorted(cache_dir.glob("*_fitness.jsonl")):
        project = path.name.replace("_fitness.jsonl", "")
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("failure") != "form":
                continue
            rubrics.add(entry.get("rubric", ""))
            models.add(entry.get("model", ""))
            out.append(FormFailure(
                project=project, slot=entry["slot"], value=entry["value"],
                reason=entry.get("reason", ""),
                fitness=float(entry.get("fitness", 0.0))))
    for name, seen in (("rubric", rubrics), ("model", models)):
        if len(seen) > 1:
            raise ValueError(
                f"form failures span {len(seen)} fitness {name}s: "
                f"{sorted(seen)}. These are different instruments and their "
                "failures cannot be pooled into one sub-type table.")
    return out


def _value_index(root: Path, method: str,
                 configs: dict[str, str]) -> dict[tuple[str, str], set[str]]:
    """(slot, canonical value) -> the configs that produced it."""
    index: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for cfg, label in configs.items():
        tag = cfg.split()[0]
        for project in ("AI_READI", "CHORUS", "CM4AI", "VOICE"):
            for record in load_replicates(root, method, label, project).values():
                for slot, value in record.items():
                    index[(slot, json.dumps(value, sort_keys=True))].add(tag)
    return index


def attribute(failures: list[FormFailure], *, root: Path = DEFAULT_ROOT,
              method: str = "claudecode_agent",
              configs: dict[str, str] | None = None) -> list[FormFailure]:
    """Tag each failure with the configuration that produced its value.

    The fitness cache records no run label — it is keyed on the judgement, not
    on provenance — so the arm is recovered by matching the stored value back
    against the records. Exact match on the canonical JSON, not similarity:
    an approximate attribution would silently mix the two arms being compared,
    which is the one error this whole exercise exists to undo.
    """
    index = _value_index(root, method, configs or DEFAULT_CONFIGS)
    for failure in failures:
        try:
            canonical = json.dumps(json.loads(failure.value), sort_keys=True)
        except (json.JSONDecodeError, TypeError):
            canonical = failure.value
        tags = index.get((failure.slot, canonical), set())
        failure.config = "+".join(sorted(tags))
    return failures


class FormSubtypeClassifier:
    """Which form failure is this? Cached, model-scoped, offline-capable."""

    def __init__(self, client=None, model: str | None = None,
                 max_tokens: int = 8000, cache_path: Path | None = None,
                 offline: bool = False):
        self._client, self._model = client, model
        self.max_tokens = max_tokens
        self.cache_path = Path(cache_path) if cache_path else None
        self.offline = offline
        self._memo: dict[str, tuple[str, str]] = {}
        self.calls = 0
        self.memo_hits = 0
        self._load()

    @property
    def model(self) -> str:
        if self._model is None:
            from data_sheets_schema.api_runner import _model_settings
            self._model = _model_settings()["name"]
        return self._model

    def _load(self) -> None:
        if not self.cache_path or not self.cache_path.exists():
            return
        for line in self.cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if (entry.get("rubric") == _digest(FORM_SUBTYPE_SYSTEM)
                    and entry.get("model") == self.model):
                self._memo[entry["key"]] = (entry["subtype"],
                                            entry.get("reason", ""))

    def _save(self, key: str, slot: str, subtype: str, reason: str) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"rubric": _digest(FORM_SUBTYPE_SYSTEM),
                                 "model": self.model, "chars": VALUE_CHARS,
                                 "key": key, "slot": slot,
                                 "subtype": subtype, "reason": reason}) + "\n")

    def __call__(self, failure: FormFailure) -> tuple[str, str]:
        key = failure.key
        if key in self._memo:
            self.memo_hits += 1
            return self._memo[key]
        if self.offline:
            raise OfflineCacheMiss(f"no cached subtype for {failure.slot!r}")

        from data_sheets_schema.api_runner import _call_with_retry, _client
        from data_sheets_schema.evidence_score import slot_spec
        if self._client is None:
            self._client = _client()

        prompt = (f"{slot_spec(failure.slot)}\n\n"
                  f"Value as written:\n{failure.value[:VALUE_CHARS]}\n\n"
                  f"The fitness judge said: {failure.reason}\n\n"
                  "Which form failure is this?")
        resp = _call_with_retry(self._client, model=self.model,
                                max_tokens=self.max_tokens, temperature=None,
                                system=FORM_SUBTYPE_SYSTEM,
                                messages=[{"role": "user", "content": prompt}])
        self.calls += 1
        text = "".join(b.text for b in resp.content
                       if getattr(b, "type", "") == "text")
        subtype, reason = _parse_subtype(text)
        self._memo[key] = (subtype, reason)
        self._save(key, failure.slot, subtype, reason)
        return subtype, reason


def _parse_subtype(text: str) -> tuple[str, str]:
    """Strict about the label, tolerant of fences and prose around it.

    An unreadable answer raises rather than defaulting to `other`. `other` is a
    real finding — "a form failure that is neither" — and quietly filling it
    with parse failures would make the residual category absorb the classifier's
    own errors, which is exactly how the `form` class came to hide two defects
    in the first place.
    """
    import re
    for candidate in re.findall(r"\{.*?\}", text, re.S):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if "subtype" in data:
            subtype = str(data["subtype"]).strip()
            if subtype not in SUBTYPES:
                raise ValueError(f"unknown subtype {subtype!r}")
            return subtype, str(data.get("reason", ""))[:300]
    match = re.search(r'"subtype"\s*:\s*"([a-z_]+)"', text)
    if match and match.group(1) in SUBTYPES:
        return match.group(1), "[truncated]"
    raise ValueError(f"no subtype in response: {text.strip()[:160]!r}")


def classify(failures: list[FormFailure],
             classifier: FormSubtypeClassifier) -> list[tuple[FormFailure, str, str]]:
    out = []
    for failure in failures:
        subtype, reason = classifier(failure)
        out.append((failure, subtype, reason))
    return out


def table(classified: list[tuple[FormFailure, str, str]]) -> dict[str, dict[str, int]]:
    """subtype -> {config -> count}, in the shape the note's table uses."""
    counts: dict[str, dict[str, int]] = {s: collections.Counter() for s in SUBTYPES}
    for failure, subtype, _ in classified:
        counts[subtype][failure.config or "unattributed"] += 1
    return {s: dict(c) for s, c in counts.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--judgement-cache", type=Path, default=JUDGEMENT_CACHE)
    parser.add_argument("--cache", type=Path,
                        default=SUBTYPE_CACHE / "form_subtypes.jsonl")
    parser.add_argument("--offline", action="store_true",
                        help="fail instead of making a paid call")
    parser.add_argument("--limit", type=int, default=None,
                        help="classify only the first N (for a canary)")
    args = parser.parse_args(argv)

    failures = attribute(load_form_failures(args.judgement_cache))
    if args.limit:
        failures = failures[:args.limit]
    print(f"{len(failures)} form failure(s) loaded", file=sys.stderr)

    classifier = FormSubtypeClassifier(cache_path=args.cache,
                                       offline=args.offline)
    classified = classify(failures, classifier)
    counts = table(classified)

    configs = sorted({f.config or "unattributed" for f, _, _ in classified})
    width = max(len(s) for s in SUBTYPES)
    print(f"{'subtype':<{width}} " + " ".join(f"{c:>6}" for c in configs))
    for subtype in SUBTYPES:
        row = counts[subtype]
        print(f"{subtype:<{width}} "
              + " ".join(f"{row.get(c, 0):>6}" for c in configs))
    print(f"{'total':<{width}} "
          + " ".join(f"{sum(counts[s].get(c, 0) for s in SUBTYPES):>6}"
                     for c in configs))
    print(f"\n{classifier.calls} call(s), {classifier.memo_hits} cached",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
