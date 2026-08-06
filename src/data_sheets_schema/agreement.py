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
together on the same slots, the judge calibrates the proxy.

**That calibration has now been done, and the proxy failed**: 0.923 mean cosine
on judged-equivalent slots against 0.914 on judged-different ones, a gap of
0.009 (`notes/replicate_agreement_2026-08-02.md`). Every value here is
schema-shaped prose about the same dataset, so the embedding measures topic,
and topic is held constant by construction. The embeddings themselves are fine
— 0.865 for a paraphrase against 0.564 for unrelated text — the failure is
specific to this population. `--embed` is therefore off by default: judged
equivalence has to be paid for, and the cheap route is closed rather than
untested.

Run it as a driver to rebuild the matrix::

    python -m data_sheets_schema.agreement --offline

`--offline` refuses to make a paid call, so it either reproduces the published
figures from the cache or fails loudly. Drop it to measure a new configuration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CBORG_EMBEDDINGS = "https://api.cborg.lbl.gov/v1/embeddings"
EMBED_MODEL = "lbl/nomic-embed-text"

# How much of a value each measure actually sees.
#
# A cut can only hide a disagreement that lives past it, so a truncated slot is
# biased towards "equivalent". The first version of this module capped the judge
# at 4000 characters, which bit 30 of the 540 published slots — asymmetrically
# between the two configurations being compared (issue #244).
#
# 100k is not "no limit": it is a limit no value in this corpus reaches (the
# longest is 29,024 characters), chosen so a pathological record cannot silently
# blow the context window of a paid call. `SlotAgreement.truncated` still
# records any slot the cap does bite, so the flag stays meaningful rather than
# becoming decorative.
JUDGE_VALUE_CHARS = 100_000
LEGACY_JUDGE_VALUE_CHARS = 4000

# The embedding endpoint truncates at 2048 tokens and does not say so. Measured,
# not read off a datasheet — nomic-embed-text is documented at 8192 tokens, and
# this endpoint is not that. A 30,000-character input returns HTTP 200 with
# `prompt_tokens: 2048`, and two values differing only past that point come back
# byte-identical, cosine 1.000000. The same contradiction scores 0.843 when it
# fits. So the endpoint will quietly report perfect agreement between two values
# that contradict each other, if the contradiction is late enough.
#
# A character cap cannot prevent this: characters per token vary with the text,
# so no fixed number is safe for all input. What is reliable is the response
# itself — `usage.prompt_tokens` hitting the ceiling means the tail was
# discarded, and that is recorded per vector and refuses to produce a
# similarity. See `notes/replicate_agreement_2026-08-02.md` and issue #251.
#
# 8000 characters remains as a client-side bound, now with an honest reason: it
# is roughly 2000 tokens of English prose, just under the ceiling, so ordinary
# values never reach the server's silent cut in the first place.
EMBED_VALUE_CHARS = 8000

# Hitting this exactly is inference, not observation: a complete 2048-token
# value and a cut one report the same `prompt_tokens`, so both are refused
# (#255). That is the right way round to be wrong — refusing a good vector
# costs a null, accepting a cut one costs a cosine of 1.0 between values that
# contradict each other. On this corpus it cannot arise; the 17 values over the
# ceiling all clear it comfortably.
EMBED_MAX_TOKENS = 2048

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
    scalar: bool = True
    max_chars: int = 0

    @property
    def truncated(self) -> bool:
        """Did the cap actually bite this slot?

        Derived from the longest value rather than stored, so the flag tracks
        the cap instead of recording what some earlier cap happened to do. The
        raw length is kept alongside it: it is what lets a future reader ask
        "would a cap of N have changed this?" without re-deriving the corpus.
        """
        return self.max_chars > JUDGE_VALUE_CHARS

    @property
    def truncated_at_legacy_cap(self) -> bool:
        """Would the original 4000-character cap have bitten it? (#244)"""
        return self.max_chars > LEGACY_JUDGE_VALUE_CHARS

    @property
    def shape(self) -> str:
        """Scalar or object.

        Worth carrying rather than deriving on demand: the scalar/object split
        is the whole reason byte equality failed. Zero of ~40 object-valued
        CHORUS slots ever matched, while the scalar ones sometimes did, so a
        rate reported without this breakdown hides which population it came
        from.
        """
        return "scalar" if self.scalar else "object"

    def as_dict(self) -> dict[str, Any]:
        return {"slot": self.slot, "n_holders": self.n_holders,
                "shape": self.shape, "exact": self.exact,
                "similarity": self.similarity, "equivalent": self.equivalent,
                "max_chars": self.max_chars, "truncated": self.truncated,
                "truncated_at_legacy_cap": self.truncated_at_legacy_cap,
                "reason": self.reason}


class OfflineCacheMiss(RuntimeError):
    """A measurement was requested that is not cached, in offline mode.

    Raised rather than paid for, so that "reproduce the published matrix" and
    "measure something new" cannot be confused for one another.
    """


class PrefixOnlyEmbedding(RuntimeError):
    """The endpoint kept only the start of this value.

    Raised rather than returned because the failure mode is not a degraded
    number, it is a maximally wrong one: two values agreeing on their prefix and
    contradicting each other afterwards score exactly 1.0.
    """


class Embedder:
    """Cosine similarity between rendered values, memoised on the text sent."""

    def __init__(self, model: str = EMBED_MODEL, cache_path: Path | None = None,
                 offline: bool = False):
        self.model = model
        self.cache_path = Path(cache_path) if cache_path else None
        self.offline = offline
        self._vecs: dict[str, list[float]] = {}
        self._prefix_only: set[str] = set()
        self.calls = 0
        self.offline_misses = 0
        self.prefix_only_skips = 0
        self._load()

    def _load(self) -> None:
        if not self.cache_path or not self.cache_path.exists():
            return
        for line in self.cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("model") != self.model:
                continue
            self._vecs[e["key"]] = e["vector"]
            # Records written before the ceiling was known carry no token count.
            # Treating unknown as "not truncated" is safe here and only here:
            # every cached vector is a CHORUS v2 value, the longest of which is
            # 2,876 characters — roughly 719 tokens, a third of the ceiling.
            if e.get("prefix_only"):
                self._prefix_only.add(e["key"])

    def _save(self, key: str, vector: list[float], tokens: int | None,
              prefix_only: bool) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"model": self.model, "key": key,
                                 "chars": EMBED_VALUE_CHARS, "tokens": tokens,
                                 "prefix_only": prefix_only,
                                 "vector": vector}) + "\n")

    def vector(self, text: str) -> list[float]:
        """The vector for `text`, keyed on the text actually sent.

        Keyed on what is sent rather than on the value it came from, for the
        same reason as the judge (#244): otherwise changing the cap re-serves
        every vector computed under the old one. Nothing in the current cache
        moves, because no cached value is anywhere near the cap.
        """
        sent = text[:EMBED_VALUE_CHARS]
        key = _digest(sent)
        if key in self._vecs:
            if key in self._prefix_only:
                raise PrefixOnlyEmbedding(f"cached vector for {key} is a prefix")
            return self._vecs[key]
        if self.offline:
            raise OfflineCacheMiss(f"no cached embedding for {key}")
        body = json.dumps({"model": self.model, "input": [sent]}).encode()
        try:
            token = os.environ["CBORG_API_KEY"]
        except KeyError:
            raise RuntimeError(
                "CBORG_API_KEY is not set; embeddings need it. Use "
                "offline=True to read only what is already cached.") from None
        req = urllib.request.Request(
            CBORG_EMBEDDINGS, data=body,
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.load(resp)
        vec = payload["data"][0]["embedding"]
        tokens = (payload.get("usage") or {}).get("prompt_tokens")
        # The endpoint's own count is the only honest signal that the tail was
        # dropped: it answers 200 either way and says nothing about the cut.
        prefix_only = tokens is not None and tokens >= EMBED_MAX_TOKENS
        self.calls += 1
        self._vecs[key] = vec
        if prefix_only:
            self._prefix_only.add(key)
        self._save(key, vec, tokens, prefix_only)
        if prefix_only:
            raise PrefixOnlyEmbedding(
                f"{len(sent)}-character value came back at the "
                f"{EMBED_MAX_TOKENS}-token ceiling, so the tail was almost "
                "certainly discarded; refusing to build a cosine on it")
        return vec

    def similarity(self, texts: list[str]) -> float:
        """Mean pairwise cosine. 1.0 for a single distinct text.

        Raises `PrefixOnlyEmbedding` if any input was cut by the endpoint, since
        the resulting cosine would be a statement about prefixes wearing the
        costume of a statement about values.
        """
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


def _sent(distinct: list[str]) -> list[str]:
    """Exactly the text the judge is shown."""
    return [t[:JUDGE_VALUE_CHARS] for t in distinct]


def _judge_key(slot: str, sent: list[str]) -> str:
    """Keyed on the evidence the judge saw, not on the values it came from.

    This distinction is the whole of #244. Keyed on the full values, raising
    the character cap leaves the key unchanged, so every verdict reached under
    the old cap is served again as though it had been reached under the new
    one — the cache would quietly defeat the fix. Keyed on what was actually
    sent, widening the cap changes the key for precisely the slots the cap bit
    and for no others, so they re-judge and the remaining 510 stay cached.

    The encoding is JSON so that the slot and each value are delimited; scheme 1
    concatenated them bare, and ("titl", ["ex"]) collided with ("title", ["x"])
    (issue #242).
    """
    return _digest(json.dumps([slot, sorted(sent)], ensure_ascii=False))


def _legacy_judge_key(slot: str, distinct: list[str]) -> str:
    return _digest(slot + "".join(sorted(distinct)))


class EquivalenceJudge:
    """Does this set of values state the same fact?

    One call per slot, not per pair: asking about all holders at once is both
    cheaper and closer to the question — "do the replicates agree here" rather
    than "does rep1 agree with rep2".

    Cached verdicts are scoped to the rubric *and* the judge model. Reusing one
    model's verdict under another silently mixes two instruments, and this repo
    routinely varies model and effort tier. Records written before that scoping
    existed carry no model and are read from a separate legacy index: they are
    frozen, so keeping them costs nothing and re-running 434 paid calls to
    restate the same verdicts would buy nothing.
    """

    def __init__(self, client=None, model: str | None = None,
                 max_tokens: int = 16000, cache_path: Path | None = None,
                 offline: bool = False):
        self._client, self._model = client, model
        self.max_tokens = max_tokens
        self.cache_path = Path(cache_path) if cache_path else None
        self.offline = offline
        self._memo: dict[str, tuple[bool, str]] = {}
        self._legacy: dict[str, tuple[bool, str]] = {}
        self.calls = 0
        self.memo_hits = 0
        self.legacy_hits = 0
        self._load()

    @property
    def model(self) -> str:
        """The judge model, without building a client.

        Needed at load time to scope the cache, and offline mode must not need
        credentials just to read a file.
        """
        if self._model is None:
            from data_sheets_schema.api_runner import _model_settings
            self._model = _model_settings()["name"]
        return self._model

    def _resolve(self):
        if self._client is None:
            from data_sheets_schema.api_runner import _client
            self._client = _client()
        return self._client, self.model

    def _load(self) -> None:
        if not self.cache_path or not self.cache_path.exists():
            return
        for line in self.cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("rubric") != _digest(EQUIVALENCE_SYSTEM):
                continue
            verdict = (e["equivalent"], e.get("reason", ""))
            if "model" not in e:
                self._legacy[e["key"]] = verdict
            elif e["model"] == self.model:
                self._memo[e["key"]] = verdict

    def _save(self, key: str, slot: str, ok: bool, reason: str) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"rubric": _digest(EQUIVALENCE_SYSTEM),
                                 "model": self.model,
                                 "judge_chars": JUDGE_VALUE_CHARS,
                                 "key": key, "slot": slot,
                                 "equivalent": ok, "reason": reason}) + "\n")

    def __call__(self, slot: str, values: list[Any]) -> tuple[bool, str]:
        rendered = [render(v) for v in values]
        distinct = list(dict.fromkeys(rendered))
        if len(distinct) < 2:
            return True, "identical"
        sent = _sent(distinct)
        if len(set(sent)) < 2:
            # The cap destroyed the only difference between these values. The
            # judge would be shown two identical blocks and would answer
            # "equivalent" — correctly, on the evidence, and wrongly about the
            # dataset. That is #244 taken to its limit, and it is the one
            # outcome this measure must never report quietly.
            raise ValueError(
                f"slot {slot!r}: truncation at {JUDGE_VALUE_CHARS} chars "
                f"collapses {len(distinct)} distinct values into one; the "
                "measurement cannot be made at this cap")
        key = _judge_key(slot, sent)
        if key in self._memo:
            self.memo_hits += 1
            return self._memo[key]
        # Legacy records are keyed on the full values but were *judged* on the
        # first 4000 characters. Where nothing reached that cap the two are the
        # same text and the verdict still stands; where something did, the
        # cached answer was reached on evidence we would no longer accept, so
        # the slot has to be re-judged rather than quietly reused.
        if all(len(t) <= LEGACY_JUDGE_VALUE_CHARS for t in distinct):
            legacy = self._legacy.get(_legacy_judge_key(slot, distinct))
            if legacy is not None:
                self.legacy_hits += 1
                return legacy
        if self.offline:
            raise OfflineCacheMiss(f"no cached verdict for slot {slot!r}")

        client, model = self._resolve()
        from data_sheets_schema.api_runner import _call_with_retry
        blocks = "\n\n".join(f"--- value {i + 1} ---\n{t}"
                             for i, t in enumerate(sent))
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


def _bump(obj: Any, name: str) -> None:
    """Increment a counter on an object we do not own.

    `embedder` is an injection point, so it may be any object with
    `.similarity()`. Requiring it to pre-declare bookkeeping attributes would
    mean the failure paths — the ones that only run when something has already
    gone wrong — demand more of the caller than the happy path does (#254).
    """
    setattr(obj, name, getattr(obj, name, 0) + 1)


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
            scalar=all(isinstance(v, (str, int, float, bool, type(None)))
                       for v in values),
            max_chars=max(len(t) for t in rendered))
        if embedder is not None:
            try:
                row.similarity = embedder.similarity(rendered)
            except OfflineCacheMiss:
                # Offline, similarity is simply unavailable for this slot —
                # leave it null and count it. Refusing to pay is the point of
                # offline mode; refusing to report the judgement too would not
                # be. Only the CHORUS v2 embeddings were ever computed.
                _bump(embedder, "offline_misses")
            except PrefixOnlyEmbedding:
                # The endpoint kept only the head of a value here, so any
                # cosine would describe prefixes rather than values. Null is
                # the honest entry; the judge's verdict for this slot stands
                # on its own and is unaffected.
                _bump(embedder, "prefix_only_skips")
        if judge is not None:
            row.equivalent, row.reason = judge(slot, values)
        out.append(row)
    return out


# --- driver -----------------------------------------------------------------
#
# The published matrix (notes/replicate_agreement_2026-08-02.md) came from these
# defaults. They are here rather than in the note because a note cannot be run.

DEFAULT_METHOD = "claudecode_agent"
DEFAULT_CONFIGS = {"v1  (2026-07-28 generic)": "2026-07-28_claude-opus-5-generic",
                   "v2  (2026-07-31 generic-v2)": "2026-07-31_claude-opus-5-generic-v2"}
DEFAULT_PROJECTS = ("AI_READI", "CHORUS", "CM4AI", "VOICE")
DEFAULT_ROOT = Path("data/d4d_concatenated")
DEFAULT_CACHE = Path("data/evaluation_llm/agreement_cache")


def load_replicates(root: Path, method: str, label: str, project: str,
                    reps: int = 3) -> dict[str, dict[str, Any]]:
    """The full record per replicate — `{PROJECT}_d4d.yaml`, not `_d4d_core`.

    Which of the two the matrix used is not cosmetic: on CHORUS the full
    records share 48 slots against the core records' 43, and the published
    counts are the full ones.
    """
    records: dict[str, dict[str, Any]] = {}
    for rep in range(1, reps + 1):
        path = root / method / f"{label}_rep{rep}" / f"{project}_d4d.yaml"
        if path.exists():
            records[f"rep{rep}"] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return records


def build_matrix(*, root: Path = DEFAULT_ROOT, method: str = DEFAULT_METHOD,
                 configs: dict[str, str] | None = None,
                 projects: tuple[str, ...] = DEFAULT_PROJECTS,
                 reps: int = 3, cache_dir: Path = DEFAULT_CACHE,
                 embed: bool = False, offline: bool = False,
                 embed_online: bool = False,
                 judge_model: str | None = None,
                 ) -> tuple[dict[str, dict[str, Any]], dict[str, list[SlotAgreement]]]:
    """The whole matrix, plus the per-slot rows behind every cell.

    `embed_online` is separate from `offline` so that re-judging a handful of
    slots cannot quietly buy ~1400 embeddings on the way past. The embedder
    reads its cache and stops there unless asked otherwise.

    `judge_model` pins the instrument. Left as None the judge inherits the
    live config pin — right for a fresh measurement, wrong for reproducing a
    published one: when #345 switched the pin, every model-scoped cached
    verdict silently fell out of scope and the offline rebuild of an already
    frozen artifact failed (#351). A reproduction passes the judge_model the
    publication records.
    """
    configs = configs or DEFAULT_CONFIGS
    embedder = (Embedder(cache_path=cache_dir / "embeddings.jsonl",
                         offline=offline or not embed_online)
                if embed else None)
    matrix: dict[str, dict[str, Any]] = {}
    rows: dict[str, list[SlotAgreement]] = {}
    for cfg, label in configs.items():
        for project in projects:
            records = load_replicates(root, method, label, project, reps)
            if len(records) < 2:
                print(f"skip {cfg}|{project}: {len(records)} replicate(s) found",
                      file=sys.stderr)
                continue
            judge = EquivalenceJudge(
                model=judge_model,
                cache_path=cache_dir / f"{project}_equivalence.jsonl",
                offline=offline)
            result = compare_records(records, embedder=embedder, judge=judge)
            key = f"{cfg}|{project}"
            rows[key] = result
            # `is True`, not `bool(...)`: an unjudged slot is None, and
            # bool(None) would file it under "judged, and they disagreed".
            # "Nothing was measured" and "nothing agreed" are the two most
            # different readings this instrument has, and they must not
            # serialize identically (#250).
            judged = [r for r in result if r.equivalent is not None]
            n_equiv = sum(r.equivalent is True for r in result)
            matrix[key] = {
                "shared": len(result),
                "equivalent": n_equiv,
                "unjudged": len(result) - len(judged),
                "exact": sum(r.exact for r in result),
                "truncated": sum(r.truncated for r in result),
                "truncated_at_legacy_cap": sum(r.truncated_at_legacy_cap
                                               for r in result),
                "rate": (n_equiv / len(result)
                         if result and len(judged) == len(result) else None),
                # A null similarity has three quite different causes — never
                # asked, not cached offline, or refused as prefix-only — and
                # an artifact that shows none of them reads as full coverage
                # when it is not (#253).
                "similarity_absent": sum(r.similarity is None for r in result),
                "judge_model": judge.model,
                "judge_chars": JUDGE_VALUE_CHARS,
                "replicates": sorted(records),
            }
    return matrix, rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    p.add_argument("--method", default=DEFAULT_METHOD)
    p.add_argument("--project", dest="projects", action="append")
    p.add_argument("--config", dest="configs", action="append", metavar="NAME=LABEL",
                   help="repeatable; defaults to the two published configs")
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    p.add_argument("--embed", action="store_true",
                   help="also compute embedding similarity (shown not to "
                        "discriminate here; off by default)")
    p.add_argument("--embed-online", action="store_true",
                   help="allow paid embedding calls (off by default, so a "
                        "re-judge cannot buy ~1400 embeddings in passing)")
    p.add_argument("--offline", action="store_true",
                   help="fail instead of making a paid call")
    p.add_argument("--write", action="store_true",
                   help="write matrix.json and {PROJECT}_{CONFIG}_rows.json")
    a = p.parse_args(argv)

    configs = ({c.split("=", 1)[0]: c.split("=", 1)[1] for c in a.configs}
               if a.configs else None)
    matrix, rows = build_matrix(
        root=a.root, method=a.method, configs=configs,
        projects=tuple(a.projects) if a.projects else DEFAULT_PROJECTS,
        reps=a.reps, cache_dir=a.cache_dir, embed=a.embed, offline=a.offline,
        embed_online=a.embed_online)

    for key, cell in sorted(matrix.items()):
        rate = f"{cell['rate']:6.1%}" if cell["rate"] is not None else "     —"
        print(f"{key:38s} {cell['equivalent']:3d}/{cell['shared']:3d} "
              f"= {rate}  (exact {cell['exact']}, "
              f"truncated {cell['truncated']}, "
              f"would-have-been {cell['truncated_at_legacy_cap']})")
    absent = sum(c["similarity_absent"] for c in matrix.values())
    if a.embed and absent:
        print(f"similarity absent for {absent} slots "
              f"(offline or refused as prefix-only); see rows files",
              file=sys.stderr)
    if a.write:
        a.cache_dir.mkdir(parents=True, exist_ok=True)
        (a.cache_dir / "matrix.json").write_text(
            json.dumps(matrix, indent=1) + "\n", encoding="utf-8")
        for key, result in rows.items():
            cfg, project = key.split("|")
            tag = cfg.split()[0]
            (a.cache_dir / f"{project}_{tag}_rows.json").write_text(
                json.dumps([r.as_dict() for r in result], indent=1) + "\n",
                encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
