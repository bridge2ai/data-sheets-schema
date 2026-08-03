"""How much do replicates actually agree?

The figure this replaces — "replicates disagree on 77-98% of the slots they
share" (#229) — is exact byte equality over values that are mostly nested
objects full of free text. Two records describing the same collection method in
different words count as disagreeing, and measured on CHORUS **zero of ~40
object-valued slots ever match in any arm**. A measure that returns zero
regardless of input cannot detect a change in either direction, which is what
made the effort-tier experiment uninformative rather than negative.

So this module measures agreement three ways, cheapest first:

1. **exact** — byte equality. Kept for continuity with #229, and honest about
   being a floor rather than an estimate.
2. **similarity** — cosine between embeddings of the rendered values. Continuous,
   cheap, and survives rewording. A paraphrase pair scores ~0.87 against ~0.56
   for unrelated text on this endpoint, so it discriminates.
3. **equivalence** — an LLM judge asked whether the values state the same fact
   about the dataset. Categorical, costs a call per slot, and is the axis
   actually of interest.

Reporting all three together is the point. Similarity alone is a proxy nobody
has calibrated; the judge alone is too expensive to run over a corpus. Run
together on the same slots, the judge calibrates the proxy — and if similarity
predicts the verdict well, later sweeps can use the free measure and spend calls
only where it is uncertain.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CBORG_EMBEDDINGS = "https://api.cborg.lbl.gov/v1/embeddings"
EMBED_MODEL = "lbl/nomic-embed-text"

EQUIVALENCE_SYSTEM = """\
You judge whether two or more values placed in the SAME field of a dataset
datasheet state the same fact about that dataset.

You are NOT judging which is better written, more complete, or more accurate.
Two values agree if a reader would draw the same conclusion about the dataset
from either one. Differences of wording, ordering, length, formatting or level
of detail do NOT make them disagree, provided nothing asserted by one is
contradicted or absent-in-substance from another.

They DISAGREE when they assert different facts: a different count, a different
date, a different licence, a different method, or when one asserts something
substantive the other omits entirely.

Reply with JSON only:
{"equivalent": true|false, "reason": "<one sentence>"}
"""


def render(value: Any) -> str:
    """Values as the reader meets them, not as Python repr.

    YAML rather than JSON because the records are YAML and the judge reads
    better prose out of it; sorted keys so key order alone never registers as a
    difference.
    """
    if isinstance(value, str):
        return value.strip()
    return yaml.safe_dump(value, sort_keys=True, allow_unicode=True,
                          default_flow_style=False).strip()


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class SlotAgreement:
    slot: str
    n_holders: int
    exact: bool
    similarity: float | None = None
    equivalent: bool | None = None
    reason: str = ""

    @property
    def shape(self) -> str:
        return "scalar" if self.n_holders and self._scalar else "object"

    _scalar: bool = True


class Embedder:
    """Cosine similarity between rendered values, memoised on the text."""

    def __init__(self, model: str = EMBED_MODEL, cache_path: Path | None = None):
        self.model = model
        self.cache_path = Path(cache_path) if cache_path else None
        self._vecs: dict[str, list[float]] = {}
        self.calls = 0
        self._load()

    def _load(self) -> None:
        if not self.cache_path or not self.cache_path.exists():
            return
        for line in self.cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("model") == self.model:
                self._vecs[e["key"]] = e["vector"]

    def _save(self, key: str, vector: list[float]) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"model": self.model, "key": key,
                                 "vector": vector}) + "\n")

    def vector(self, text: str) -> list[float]:
        key = _digest(text)
        if key in self._vecs:
            return self._vecs[key]
        body = json.dumps({"model": self.model, "input": [text[:8000]]}).encode()
        req = urllib.request.Request(
            CBORG_EMBEDDINGS, data=body,
            headers={"Authorization": f"Bearer {os.environ['CBORG_API_KEY']}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            vec = json.load(resp)["data"][0]["embedding"]
        self.calls += 1
        self._vecs[key] = vec
        self._save(key, vec)
        return vec

    def similarity(self, texts: list[str]) -> float:
        """Mean pairwise cosine. 1.0 for a single distinct text."""
        distinct = list(dict.fromkeys(texts))
        if len(distinct) < 2:
            return 1.0
        vecs = [self.vector(t) for t in distinct]
        sims = []
        for i in range(len(vecs)):
            for j in range(i + 1, len(vecs)):
                a, b = vecs[i], vecs[j]
                num = sum(x * y for x, y in zip(a, b))
                den = (math.sqrt(sum(x * x for x in a))
                       * math.sqrt(sum(y * y for y in b)))
                sims.append(num / den if den else 0.0)
        return sum(sims) / len(sims)


class EquivalenceJudge:
    """Does this set of values state the same fact?

    One call per slot, not per pair: asking about all holders at once is both
    cheaper and closer to the question — "do the replicates agree here" rather
    than "does rep1 agree with rep2".
    """

    def __init__(self, client=None, model: str | None = None,
                 max_tokens: int = 16000, cache_path: Path | None = None):
        self._client, self._model = client, model
        self.max_tokens = max_tokens
        self.cache_path = Path(cache_path) if cache_path else None
        self._memo: dict[str, tuple[bool, str]] = {}
        self.calls = 0
        self.memo_hits = 0
        self._load()

    def _resolve(self):
        if self._client is None:
            from data_sheets_schema.api_runner import _client, _model_settings
            self._client = _client()
            self._model = self._model or _model_settings()["name"]
        return self._client, self._model

    def _load(self) -> None:
        if not self.cache_path or not self.cache_path.exists():
            return
        for line in self.cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("rubric") == _digest(EQUIVALENCE_SYSTEM):
                self._memo[e["key"]] = (e["equivalent"], e.get("reason", ""))

    def _save(self, key: str, slot: str, ok: bool, reason: str) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"rubric": _digest(EQUIVALENCE_SYSTEM),
                                 "key": key, "slot": slot,
                                 "equivalent": ok, "reason": reason}) + "\n")

    def __call__(self, slot: str, values: list[Any]) -> tuple[bool, str]:
        rendered = [render(v) for v in values]
        distinct = list(dict.fromkeys(rendered))
        if len(distinct) < 2:
            return True, "identical"
        key = _digest(slot + "" + "".join(sorted(distinct)))
        if key in self._memo:
            self.memo_hits += 1
            return self._memo[key]

        client, model = self._resolve()
        from data_sheets_schema.api_runner import _call_with_retry
        blocks = "\n\n".join(f"--- value {i + 1} ---\n{t[:4000]}"
                             for i, t in enumerate(distinct))
        prompt = (f"Field: `{slot}`\n\n{blocks}\n\n"
                  "Do these state the same fact about the dataset?")
        resp = _call_with_retry(client, model=model, max_tokens=self.max_tokens,
                                temperature=None, system=EQUIVALENCE_SYSTEM,
                                messages=[{"role": "user", "content": prompt}])
        self.calls += 1
        text = "".join(b.text for b in resp.content
                       if getattr(b, "type", "") == "text")
        ok, reason = _parse_verdict(text)
        self._memo[key] = (ok, reason)
        self._save(key, slot, ok, reason)
        return ok, reason


def _parse_verdict(text: str) -> tuple[bool, str]:
    """Tolerant of fences and prose around the JSON, strict about the field.

    A missing or unparseable verdict is *not* silently treated as agreement —
    that would inflate the figure this module exists to measure honestly.
    """
    import re
    for candidate in re.findall(r"\{.*?\}", text, re.S):
        try:
            d = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if "equivalent" in d:
            return bool(d["equivalent"]), str(d.get("reason", ""))[:300]
    # Truncated JSON still carries the verdict. Thinking blocks bill against the
    # same budget as the answer, so a long deliberation can cut the closing
    # brace off a decision that was already made — salvage it rather than
    # throwing away a paid call. The reason may be clipped; the verdict is not.
    m = re.search(r'"equivalent"\s*:\s*(true|false)', text, re.I)
    if m:
        reason = re.search(r'"reason"\s*:\s*"([^"]*)', text)
        return m.group(1).lower() == "true", (
            (reason.group(1)[:300] + " [truncated]") if reason else "[truncated]")
    raise ValueError(f"no verdict in response: {text.strip()[:160]!r}")


def compare_records(records: dict[str, dict[str, Any]], *,
                    embedder: Embedder | None = None,
                    judge: EquivalenceJudge | None = None,
                    ) -> list[SlotAgreement]:
    """One row per slot held by two or more replicates."""
    out: list[SlotAgreement] = []
    all_slots = {s for r in records.values() for s in r}
    for slot in sorted(all_slots):
        holders = [lab for lab, r in records.items() if slot in r]
        if len(holders) < 2:
            continue
        values = [records[lab][slot] for lab in holders]
        rendered = [render(v) for v in values]
        row = SlotAgreement(
            slot=slot, n_holders=len(holders),
            exact=len(set(rendered)) == 1,
            _scalar=all(isinstance(v, (str, int, float, bool, type(None)))
                        for v in values))
        if embedder is not None:
            row.similarity = embedder.similarity(rendered)
        if judge is not None:
            row.equivalent, row.reason = judge(slot, values)
        out.append(row)
    return out
