"""Support judge v2: typed source-support verdicts, one record's own values (#2929).

A new instrument beside `evidence_score.LLMSlotScorer`, which stays exactly as
it is: its prompt (`SCORER_SYSTEM`) is part of the identity of every cached
grounding judgement, so editing it would move that identity rather than
improve anything already measured.

## What v1 cannot see

`SCORER_SYSTEM` asks one question — do the documents substantiate this
claim — and scores 1.0 / 0.5 / 0.0. It is sent `{slot: value}` and the bundle,
nothing else. Five of the six completed CHORUS API canaries from v10b to v10j
were rejected by source review for defects of classes that question does not
ask about (#1782, #1799-#1801, #1815, #1816): a planned activity stated as
done, a person named in one capacity placed in another, a statement quoted
from the wrong document. Each such value has its words somewhere in the
bundle, so a judge that looks for matching words passes it (#2079).

## What v2 adds

Per value, the request carries:

- the field's schema specification — its description and declared range —
  rendered by the same `_render_slot_spec` the fitness judge reads, and keyed
  by the same complete-specification digest (#1261);
- for a relationship slot (one whose declared range is an inlined class:
  `creators`, `funders`, …) the entity the value is asserted *of*, so "this
  person is a creator" is judged as a claim about this dataset;
- the value's own attribution declarations — the document it names as its
  source and the claim status it asserts: keys in `DECLARATION_FIELDS` found
  inside the value, and any the caller passes from an audit claim —
  presented as claims under test, never as evidence.
  A judge told where a value came from is inclined to believe it; the prompt
  says the declaration is checked like the value, and a wrong declaration is
  itself a defect.

The reply is one of `VERDICTS`, parsed strictly: a malformed, keyed-wrong,
unknown-verdict or truncated reply raises. Nothing is salvaged, because a
typed verdict cannot be recovered from a prefix the way v1's leading number
could — and a guess would be the judge's failure scored as the record's.

## What v2 refuses

Propagation. v1 plans judge a stable slot once and copy the verdict to the
other replicates, whose values usually differ (#2372: 103 of 114 copied
support verdicts in figure 8 landed on a different value). v2 judges a value
it reads from the record it is given, so there is no value to copy a verdict
onto: `SupportJudgeV2` is not a `SlotScorer`, `as_slot_scorer` raises, and
every verdict carries `propagated=False`, which cannot be set.

The mapping from typed verdicts to report rates is not decided here (#2929,
owner decision 4), so a verdict carries no number.

Offline by construction in tests: the client is injected, and the model is
resolved through `evaluation_model` (#2928) when none is passed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

from data_sheets_schema import reasoning
from data_sheets_schema.evidence_score import JudgementContext, digest_of

INSTRUMENT = "support_judge v2 (#2929)"
AXIS = "grounding_v2"

#: The typed verdicts, in the precedence order the prompt states.
VERDICTS = ("contradicted", "status_shifted", "relationship_unsupported",
            "wrong_document", "unsupported", "partially_supported", "supported")

#: Keys that attribute a value to a source document or assert its claim
#: status: the audit grammar's declarations (`audit_grammar.CLAIM_KEYS`).
#: Read from inside the value (any depth) and shown to the judge as claims
#: to test.
#:
#: The schema's `status` and `was_derived_from` are deliberately absent
#: (#3347). They are not about the value's source document: `status` is a
#: resource's publication status (draft, published, deprecated) and
#: `was_derived_from` is prov:wasDerivedFrom, a resource this resource was
#: derived from (D4D_Base_import.yaml). The corpus uses the nested
#: `was_derived_from` for derivation-provenance identifiers — an ark naming
#: a processing computation, a repository DOI — that are not documents in
#: any bundle, so listing them as the value's declarations would frame a
#: derivation link as a citation and invite `wrong_document`. Where such a
#: key sits inside the value it is still judged, as part of the value.
DECLARATION_FIELDS = ("attributed_to", "claim_status", "source_status")

#: Scalar keys that identify the entity a relationship value is asserted of.
ENTITY_FIELDS = ("id", "name", "title", "doi", "version")

_REPLY_KEYS = frozenset({"verdict", "reason"})

SUPPORT_V2_SYSTEM = (
    "You judge whether one value in a dataset-documentation record is supported "
    "by the source documents supplied: in the role its field gives it, with the "
    "status it asserts, and from the document it is attributed to. You are not "
    "assessing whether the value is well written, complete or desirable.\n\n"
    "You are given the field's schema specification; for a field that relates "
    "an entity to the dataset, the entity the value is asserted of; any "
    "attribution declarations the record makes for the value (the document "
    "it names as the value's source, the claim status it asserts); and the "
    "value.\n\n"
    "The record's declarations are claims under test, not evidence. Check them "
    "against the documents exactly as you check the value. Never accept a value "
    "because the record says where it came from or what state it is in; a "
    "declaration the documents do not bear out is itself a defect.\n\n"
    "Matching words are not support. A value is supported only when the "
    "documents state the fact the field asserts: the same entity, the same role "
    "or relationship, and the same status.\n\n"
    "Choose exactly one verdict, the first that applies in this order:\n"
    "  contradicted — the documents state something incompatible with the "
    "value, other than its status.\n"
    "  status_shifted — the documents state the fact as planned, proposed, in "
    "progress, an instruction or a capability, and the value or its "
    "declaration states it as current, completed or applied.\n"
    "  relationship_unsupported — the documents state the fact, but not in the "
    "role or relationship this field asserts: for example a person the "
    "documents name only in another capacity, placed in a field that makes "
    "them a creator.\n"
    "  wrong_document — the fact is in the documents, but not in the document "
    "an explicit attribution for the value names as its source. Only an "
    "attribution counts: a resource the value says it was derived from, or "
    "an identifier inside the value, is not a citation of a source "
    "document.\n"
    "  unsupported — the documents do not state it. A value that is plausible, "
    "or whose words appear in the documents without stating this fact, is "
    "unsupported.\n"
    "  partially_supported — the documents state part of the value and not the "
    "rest.\n"
    "  supported — the documents state the value directly, in this role, with "
    "this status, and in the attributed document where one is attributed.\n\n"
    "Reply with a JSON object and nothing else, with exactly these keys:\n"
    '  {"verdict": "<one of the seven above>", "reason": "<one sentence>"}\n\n'
    "Keep `reason` under 25 words. A reply that is cut off is discarded, not "
    "scored."
)


class VerdictError(ValueError):
    """A reply that is not a complete, well-formed typed verdict."""


class PropagationRefused(TypeError):
    """v2 judges each record's own value; it never copies a verdict (#2372)."""


@dataclass(frozen=True)
class SupportVerdict:
    slot: str
    verdict: str
    reason: str
    from_cache: bool = False
    # Not an init argument: no caller can mark a v2 verdict as copied.
    propagated: bool = field(default=False, init=False)


@dataclass(frozen=True)
class ValueContext:
    """What the judge is told about one value besides the value itself."""

    entity: dict[str, Any] | None
    declarations: dict[str, Any]

    def digest(self) -> str:
        """Part of the cache key: two identical values asserted of different
        entities, or under different declarations, are different questions."""
        payload = json.dumps({"entity": self.entity,
                              "declarations": self.declarations},
                             sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class SupportSpecification:
    """The slot specification the judge reads, and the digest that keys it.

    `from_schema` is the fitness judge's own rendering and digest, so the two
    axes judge against one specification. Injectable so tests can use a
    neutral synthetic schema.
    """

    digest: str
    render: Callable[[str], str]
    relationship: Callable[[str], bool]

    @classmethod
    def from_schema(cls, class_name: str = "Dataset",
                    schema_path: Path | None = None, *,
                    profile=None) -> "SupportSpecification":
        from data_sheets_schema.evidence_score import (
            _render_slot_spec, slot_specification_snapshot)
        _, inventory, vocabulary, specification = slot_specification_snapshot(
            class_name, schema_path, profile=profile)
        nested = {n.name for n in inventory.nested}
        slots = {s.name: s for s in inventory.slots}

        def relationship(slot: str) -> bool:
            sd = slots.get(slot)
            return bool(sd and (sd.inlined or sd.range in nested))

        return cls(digest=specification,
                   render=lambda slot: _render_slot_spec(slot, inventory, vocabulary),
                   relationship=relationship)


def _declarations_in(value: Any, pointer: str = "") -> dict[str, Any]:
    """Declaration keys found anywhere inside `value`, by JSON Pointer."""
    found: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            here = f"{pointer}/{str(key).replace('~', '~0').replace('/', '~1')}"
            if key in DECLARATION_FIELDS:
                found[here] = item
            found.update(_declarations_in(item, here))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            found.update(_declarations_in(item, f"{pointer}/{i}"))
    return found


def build_value_context(record: dict[str, Any], slot: str, *,
                        relationship: bool,
                        declarations: dict[str, Any] | None = None) -> ValueContext:
    """The containing entity (relationship slots only) and the declarations.

    Declarations inside the value are keyed by their pointer from the record
    root (`/creators/0/claim_status`); ones the caller supplies — an audit
    claim's `attributed_to`, say — are keyed by name under `declared:`.
    """
    entity = None
    if relationship:
        entity = {k: record[k] for k in ENTITY_FIELDS
                  if isinstance(record.get(k), (str, int, float))
                  and not isinstance(record.get(k), bool)} or None
    slot_pointer = "/" + slot.replace("~", "~0").replace("/", "~1")
    found = _declarations_in(record.get(slot), slot_pointer)
    for key, item in (declarations or {}).items():
        found[f"declared: {key}"] = item
    return ValueContext(entity=entity, declarations=found)


def _dump(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def render_request(slot: str, value: Any, spec: str, context: ValueContext) -> str:
    """The per-value text sent after the cached documents block."""
    parts = [f"# Field specification\n\n{spec}"]
    if context.entity is not None:
        parts.append(
            "# Containing entity\n\nThe value is asserted of this entity, in "
            f"the role the field names:\n\n```yaml\n{_dump(context.entity)}```")
    if context.declarations:
        parts.append(
            "# The record's attribution declarations for this value\n\nClaims to "
            "test against the documents, not evidence:\n\n"
            f"```yaml\n{_dump(context.declarations)}```")
    else:
        parts.append("# The record's attribution declarations for this value\n\n"
                     "None declared.")
    parts.append(f"# Value\n\nRecord field `{slot}` asserts:\n\n"
                 f"```yaml\n{_dump({slot: value})}```\n\n"
                 "Which verdict applies?")
    return "\n\n".join(parts)


def request_arguments(*, model: str, max_tokens: int, bundle: str,
                      value_text: str) -> dict[str, Any]:
    """Pure arguments at the shared judge/transport boundary (#3341).

    This does not initialize a client or apply provider-specific transport
    policy. Offline plans pin these exact arguments, not alleged wire bytes.
    """
    return {"model": model, "max_tokens": max_tokens, "temperature": None,
            "system": SUPPORT_V2_SYSTEM,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": f"# Source documents\n\n{bundle}",
                 "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": value_text}]}]}


def parse_verdict(text: str, *, truncated: bool = False) -> tuple[str, str]:
    """`(verdict, reason)` from a complete reply, or `VerdictError`.

    Strict where `evidence_score._parse_judgement` is lenient: the reply is a
    JSON object — optionally in one ```json fence — with exactly `verdict`
    and `reason`, the verdict one of `VERDICTS` as spelled, the reason a
    non-empty string. A reply that stopped at `max_tokens` is rejected even
    if it happens to parse.
    """
    if truncated:
        raise VerdictError("reply stopped at max_tokens; a truncated verdict is "
                           "discarded, not recovered")
    body = (text or "").strip()
    if body.startswith("```"):
        lines = body.splitlines()
        if len(lines) < 2 or lines[-1].strip() != "```" or \
                lines[0].strip() not in ("```", "```json"):
            raise VerdictError(f"unterminated or unrecognised fence: {body[:120]!r}")
        body = "\n".join(lines[1:-1]).strip()

    def unique(pairs):
        seen: dict[str, Any] = {}
        for key, item in pairs:
            if key in seen:
                raise VerdictError(f"duplicate key in verdict: {key!r}")
            seen[key] = item
        return seen

    try:
        data = json.loads(body, object_pairs_hook=unique)
    except json.JSONDecodeError as exc:
        raise VerdictError(f"reply is not one JSON object: {body[:120]!r}") from exc
    if not isinstance(data, dict):
        raise VerdictError(f"reply is not a JSON object: {body[:120]!r}")
    if set(data) != _REPLY_KEYS:
        raise VerdictError(f"reply keys {sorted(data)} are not exactly "
                           f"{sorted(_REPLY_KEYS)}")
    verdict, reason = data["verdict"], data["reason"]
    if not isinstance(verdict, str) or verdict not in VERDICTS:
        raise VerdictError(f"unknown verdict {verdict!r}")
    if not isinstance(reason, str) or not reason.strip():
        raise VerdictError("reason is missing or empty")
    return verdict, reason


def populated(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


class SupportJudgeV2:
    """Judge a record's own values against its bundle, with typed verdicts.

    One value per call, as v1: a batch invites judging values relative to
    each other. The bundle is a cached block, so a record's values share one
    corpus write.
    """

    def __init__(self, client=None, model: str | None = None, *,
                 specification: SupportSpecification | None = None,
                 class_name: str = "Dataset", schema_path: Path | None = None,
                 profile=None, max_tokens: int = 8000,
                 log_path: Path | None = None, cache_path: Path | None = None):
        self._client = client
        self._model = model
        # `explicit` when the caller named the model; otherwise the basis
        # `evaluation_model` reports, for a run manifest to disclose.
        self.model_basis = "explicit" if model is not None else None
        self._specification = specification
        self.class_name = class_name
        self.schema_path = schema_path
        self.profile = profile
        # Sized for the reasoning, not the answer — see LLMSlotScorer.
        self.max_tokens = max_tokens
        self.log_path = Path(log_path) if log_path else None
        self.cache_path = Path(cache_path) if cache_path else None
        self._loaded: set[str] = set()
        self._memo: dict[tuple[str, str, str, str], SupportVerdict] = {}
        self._specs: dict[str, str] = {}
        self.cache_loaded = 0
        self.cache_skipped: dict[str, int] = {}
        self.calls = 0
        self.memo_hits = 0
        self.usage: list[dict[str, Any]] = []
        self.reasoning: list[dict[str, Any]] = []

    # -- identity ---------------------------------------------------------

    @property
    def specification(self) -> SupportSpecification:
        if self._specification is None:
            self._specification = SupportSpecification.from_schema(
                self.class_name, self.schema_path, profile=self.profile)
        return self._specification

    def _resolve(self):
        from data_sheets_schema import api_runner
        if self._client is None:
            self._client = api_runner._client()
        if self._model is None:
            from data_sheets_schema.evaluation_model import evaluation_model_settings
            settings = evaluation_model_settings()
            self._model, self.model_basis = settings["name"], settings.get("basis")
        return self._client, self._model

    def context(self, model: str, bundle: str) -> JudgementContext:
        return JudgementContext(axis=AXIS, model=model,
                                rubric=digest_of(SUPPORT_V2_SYSTEM),
                                corpus=digest_of(bundle),
                                specification=self.specification.digest)

    def spec(self, slot: str) -> str:
        if slot not in self._specs:
            self._specs[slot] = self.specification.render(slot)
        return self._specs[slot]

    # -- cache ------------------------------------------------------------

    def _load_cache(self, ctx: JudgementContext) -> None:
        """Keep only v2 entries made under this exact context.

        Beyond the context, an entry must carry a known verdict and must not
        claim to be propagated. v1 entries are skipped on `axis`, including
        the July CM4AI entries that carry no axis at all.
        """
        fp = ctx.fingerprint()
        if fp in self._loaded or not self.cache_path:
            return
        self._loaded.add(fp)
        if not self.cache_path.exists():
            return
        skipped: dict[str, int] = {}
        loaded = 0
        for line in self.cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                why = "unreadable"
            else:
                why = JudgementContext.mismatch(e, ctx) if isinstance(e, dict) else "unreadable"
                if why is None and e.get("verdict") not in VERDICTS:
                    why = "verdict"
                if why is None and e.get("propagated", False) is not False:
                    why = "propagated"
                if why is None and not all(isinstance(e.get(k), str)
                                           for k in ("slot", "value", "value_context")):
                    why = "key"
            if why is not None:
                skipped[why] = skipped.get(why, 0) + 1
                continue
            self._memo[(fp, e["slot"], e["value"], e["value_context"])] = SupportVerdict(
                slot=e["slot"], verdict=e["verdict"], reason=e.get("reason", ""),
                from_cache=True)
            loaded += 1
        self.cache_loaded += loaded
        for why, n in skipped.items():
            self.cache_skipped[why] = self.cache_skipped.get(why, 0) + n

    # -- judging ----------------------------------------------------------

    def as_slot_scorer(self):
        raise PropagationRefused(
            "SupportJudgeV2 is not a SlotScorer: run_plan and "
            "measure_propagation_error copy one replicate's verdict to others "
            "(#2372). Judge each record with judge_record().")

    def judge(self, *, project: str, record: dict[str, Any], slot: str,
              bundle: str, declarations: dict[str, Any] | None = None
              ) -> SupportVerdict:
        """Judge `record[slot]` — the value is read from the record, never
        supplied, so a verdict always belongs to the value it names."""
        if not isinstance(record, dict):
            raise TypeError("record must be a mapping")
        if not bundle:
            raise ValueError("a support judgement needs the source documents")
        value = record.get(slot)
        if not populated(value):
            raise ValueError(f"slot {slot!r} is not populated in this record")

        spec = self.spec(slot)
        vctx = build_value_context(
            record, slot, relationship=self.specification.relationship(slot),
            declarations=declarations)
        client, model = self._resolve()
        ctx = self.context(model, bundle)
        self._load_cache(ctx)

        value_key = json.dumps(value, sort_keys=True, default=str)
        key = (ctx.fingerprint(), slot, value_key, vctx.digest())
        if key in self._memo:
            self.memo_hits += 1
            return self._memo[key]

        from data_sheets_schema.api_runner import _call_with_retry

        resp = _call_with_retry(client, **request_arguments(
            model=model, max_tokens=self.max_tokens, bundle=bundle,
            value_text=render_request(slot, value, spec, vctx)))
        self.calls += 1
        u = getattr(resp, "usage", None)
        self.usage.append({
            "slot": slot,
            "input": getattr(u, "input_tokens", None),
            "cache_read": getattr(u, "cache_read_input_tokens", None),
            "cache_write": getattr(u, "cache_creation_input_tokens", None),
            "output": getattr(u, "output_tokens", None),
        })
        cap = reasoning.capture(resp)
        entry = {"project": project, "slot": slot, "model": model, "axis": AXIS,
                 **cap.to_dict()}
        self.reasoning.append(entry)
        if self.log_path is not None:
            reasoning.append(self.log_path, entry)

        text = "".join(b.text for b in resp.content
                       if getattr(b, "type", "") == "text")
        verdict, reason = parse_verdict(
            text, truncated=getattr(resp, "stop_reason", None) == "max_tokens")
        result = SupportVerdict(slot=slot, verdict=verdict, reason=reason)
        self._memo[key] = result
        if self.cache_path is not None:
            # Appended as earned, as v1: an interrupted pass keeps what it paid for.
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    **ctx.as_entry(), "instrument": INSTRUMENT,
                    "project": project, "slot": slot, "value": value_key,
                    "value_context": vctx.digest(), "verdict": verdict,
                    "reason": reason, "propagated": False},
                    ensure_ascii=False) + "\n")
        return result

    def judge_record(self, *, project: str, record: dict[str, Any], bundle: str,
                     slots: list[str] | None = None,
                     declarations: dict[str, dict[str, Any]] | None = None
                     ) -> list[SupportVerdict]:
        """Every populated slot of one record (or the named ones), each judged
        on its own value. `declarations` maps a slot to what the caller knows
        was declared for it."""
        names = slots if slots is not None else [s for s in record if populated(record[s])]
        return [self.judge(project=project, record=record, slot=s, bundle=bundle,
                           declarations=(declarations or {}).get(s))
                for s in names]
