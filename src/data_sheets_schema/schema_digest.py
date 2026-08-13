"""Compact slot inventory for prompt injection.

The merged schemas are ~254 KB (`data_sheets_schema_all.yaml`, class `Dataset`)
and ~216 KB (`..._core_all.yaml`, class `CoreDataset`) — larger than any input
bundle in the corpus. Sending either verbatim to a model costs more than the
evidence it is meant to structure, and most of the bytes are imports, mappings,
and provenance annotations that say nothing about how to fill a record.

What a generation run actually needs is the target class's slots: name, range,
cardinality, whether it is required, and the description that says what belongs
there. This module emits exactly that.

The digest is a *structural* artifact. It carries no dataset facts, so it is
safe under the provenance guard: it tells a run what shape the answer takes,
never what the answer is. Enum permissible values are included because a slot
whose range is an enum is unanswerable without them; free-text descriptions are
truncated because their tail is usually curation notes rather than instruction.
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from linkml_runtime import SchemaView

FULL_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
CORE_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml")

# Where each target class is actually defined. They are separate merged
# artifacts; CoreDataset does not exist in the full schema.
CLASS_SCHEMA = {"Dataset": FULL_SCHEMA, "CoreDataset": CORE_SCHEMA}

DESCRIPTION_CHARS = 300
# Above the largest enum in either schema (EncodingEnum, 43). A truncated enum
# is not like a truncated description: the tail of a description is usually
# curation notes, but the tail of a vocabulary is values the model is then
# unable to choose and will approximate instead. At this size the whole
# vocabulary costs 38 bytes more than the clipped one, in a cached prefix.
MAX_ENUM_VALUES = 60

# Attribute names every class inherits. Listing them on all 66 nested classes
# would be 264 tokens saying nothing — the model already reaches for
# `description`, which is the problem this listing exists to solve.
UNIVERSAL_ATTRIBUTES = frozenset({"id", "name", "description", "used_software"})

# Optional attributes listed per nested class before truncating.
MAX_OPTIONAL_SHOWN = 24

# Above this overlap with the top-level slot listing, a nested class is
# described by reference instead of enumerated. Exactly three classes qualify —
# `Dataset` (100%), `DataSubset` (98%) and `FileCollection` (85%) — and they are
# the three large enough to be truncated, so listing the alphabetically-first 24
# would spend the tokens on a redundant and arbitrary slice.
MIRRORS_TOP_LEVEL = 0.8


@dataclass
class SlotDigest:
    name: str
    range: str | None
    description: str | None
    required: bool = False
    multivalued: bool = False
    enum_values: list[str] = field(default_factory=list)
    enum_truncated: int = 0
    #: `values_from` targets, so the permitted vocabulary can be rendered
    #: (#538). Collected and rendered together — collecting without rendering
    #: is the state this issue was filed about.
    values_from: list[str] = field(default_factory=list)


@dataclass
class NestedClass:
    """A class used as a slot range, and what it requires.

    Without this the digest names a range (`subsets — Subset [many]`) but never
    says that `Subset` requires an `id`. The first live API run emitted five
    subsets, none with an id, and the record failed validation — the model was
    never told. Ranges are only useful alongside their obligations.
    """

    name: str
    required: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)
    # Enum-ranged slots on the nested class, and the values they accept.
    # Naming the key was not enough. `DatasetRelationship` was rendered as
    # "required: relationship_type, target_dataset" with no hint that
    # relationship_type takes a controlled vocabulary, so runs filled it with
    # DataCite spellings (`IsNewVersionOf`, `Continues`, `References`) and
    # inventions (`related_to`, `is a later release in the same series as`).
    # Those are plausible and wrong, which is the hardest kind to catch. A
    # model cannot choose from a list it has never been shown.
    enums: dict[str, list[str]] = field(default_factory=dict)
    enums_truncated: dict[str, int] = field(default_factory=dict)
    # Declared range of each nested attribute (#486). Names alone let a judge
    # assess *hollowness* — content in prose while structured keys sit empty —
    # and not *range conformance*, because "a wrong range" cannot be seen
    # without the range. `unit: mg/dL` under a `uriorcurie` declaration was
    # invisible to the fitness axis for exactly this reason; `d4d runs
    # identifiers` found those values only because it reads the schema itself
    # rather than asking a judge.
    ranges: dict[str, str] = field(default_factory=dict)
    #: `values_from` targets per nested attribute (#538). `data_topic` and
    #: `data_substrate` are attributes of `Instance`, not slots of `Dataset`,
    #: so a top-level-only rendering reaches neither — the same reason #486
    #: had to render nested ranges here rather than on the slot listing.
    values_from: dict[str, list[str]] = field(default_factory=dict)


#: Registry vocabularies for slots declaring `values_from` (#538), pinned in
#: `b2ai_registry_vocabularies.yaml`.
VOCABULARY_PIN = Path(__file__).with_name("b2ai_registry_vocabularies.yaml")

_VOCABULARIES: dict[str, dict[str, str]] | None = None


def vocabularies() -> dict[str, dict[str, str]]:
    """The pinned registry vocabularies, keyed by `values_from` name."""
    global _VOCABULARIES
    if _VOCABULARIES is None:
        import yaml as _yaml
        doc = _yaml.safe_load(VOCABULARY_PIN.read_text(encoding="utf-8")) or {}
        _VOCABULARIES = doc.get("vocabularies") or {}
    return _VOCABULARIES


def render_values_from(names: list[str]) -> str | None:
    """The permitted terms for a slot that declares `values_from` (#538).

    Rendered because nothing rendered it before. `data_topic` and
    `data_substrate` have declared `values_from` all along and no run has ever
    seen it, so runs improvised: every one of the 23 well-formed
    `data_substrate` IRIs names a cell line or an assay technique, neither of
    which is a type of data, while the 11 prose values are right in substance
    and had no term to be written as.

    The prefix is stated once and terms listed as `id=name`, which halves the
    cost against repeating `B2AI_SUBSTRATE:` 81 times — the digest is
    prompt-injected and defends a size budget.

    A `values_from` naming no pinned vocabulary renders nothing rather than
    guessing. Silence is the honest output when the terms are unknown.
    """
    known = vocabularies()
    parts = []
    for name in names:
        terms = known.get(name)
        if not terms:
            continue
        prefix = f"{name}:"
        items = ", ".join(
            f"{k[len(prefix):] if k.startswith(prefix) else k}={v}"
            for k, v in terms.items())
        parts.append(f"{name} (use `{name}:<id>`) — {items}")
    if not parts:
        return None
    # The fallback, carried here because a nested attribute's *description* is
    # not rendered: a run sees this list and never the slot's own "prefer
    # omission over a prose topic". The vocabulary is not exhaustive — CHORUS's
    # subject is acute and critical care, and none of the 56 B2AI_TOPIC terms
    # names it — so without this a run meeting an uncovered subject has 56
    # near-neighbours in front of it and no instruction to decline. Picking the
    # closest is the invention #403 added `OTHER` to prevent.
    return ("; ".join(parts)
            + ". If no term fits, omit the slot rather than approximate, and "
              "never restate the subject as prose here.")


#: Ranges that hold on essentially every object range, stated once rather than
#: repeated 67 times (#486). `id` is `uriorcurie` on all 67 nested classes and
#: `used_software` is `Software[]` on 64 — so a per-class line would be bloat
#: that an existing guard already forbids, while the information itself is the
#: most valuable here: `id → uriorcurie` is the whole #402/#457 family, and a
#: bare token validates exactly as cleanly as a ROR IRI.
UNIVERSAL_RANGES = "`id` is `uriorcurie`; `used_software` is `Software[]`"


def shown_ranges(nested: "NestedClass") -> dict[str, str]:
    """The nested attribute ranges rendered to a reader — digest and judge alike.

    **One function so the two cannot diverge (#486).** The digest render and
    `slot_spec` originally applied different filters: `slot_spec` showed
    `id`, `data_type` and `used_software` while the digest omitted them as
    universal attributes. The fitness cache keys on the digest fingerprint, so
    a change to any of those three would have moved the judge's question while
    leaving the key unchanged — cached labels answering a worse-informed
    question, silently, which is the #465 failure this was meant to prevent.

    `string` is excluded because it is the schema's `default_range`: naming it
    costs size and carries no information. Enum-ranged attributes are excluded
    because their permitted values are rendered separately and in more detail.

    Universal attributes are excluded and stated once as `UNIVERSAL_RANGES`
    instead. Repeating them per class is what `test_universal_attributes_are_
    not_repeated_on_every_class` already forbids, and the first version of this
    change reintroduced them 67 times and pushed the digest past its size
    budget. Saying `id → uriorcurie` once is strictly better than saying it 67
    times: same information, no bloat, and one place to keep the judge's view
    and the cache key in step.
    """
    return {k: v for k, v in sorted(nested.ranges.items())
            if v not in ("string", "string[]") and k not in nested.enums
            and k not in UNIVERSAL_ATTRIBUTES}


@dataclass
class ClassDigest:
    class_name: str
    schema_path: str
    slots: list[SlotDigest] = field(default_factory=list)
    nested: list[NestedClass] = field(default_factory=list)

    @property
    def required_names(self) -> list[str]:
        return [s.name for s in self.slots if s.required]


def _truncate(text: str | None, limit: int = DESCRIPTION_CHARS) -> str | None:
    if not text:
        return None
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


_BUILD_CACHE: dict[tuple[str, str], "ClassDigest"] = {}


def build(class_name: str, schema_path: Path | None = None) -> ClassDigest:
    """Memoised on (class_name, schema_path); see _build_uncached.

    Returns a **copy**. The cache used to hand out the stored object itself, so
    any caller that mutated the result — or its `nested` entries, or their
    `ranges`/`enums` dicts — silently changed what every later `build()` for
    that class returned, for the life of the process (#528).

    Found when a test stripped `ranges` to check the fingerprint responded, and
    two later tests in the same file then measured an empty digest and failed.
    Those failures read as real defects in the code under test, which is the
    dangerous shape: the first instinct is to "fix" code that was correct.

    The exposure is not confined to tests. `build` feeds the generation prompt,
    `slot_spec` (what the fitness judge reads) and the digest fingerprint that
    keys the fitness and sub-type caches. A mutation anywhere in a long-lived
    process would change the prompt or the cache key for everything after it,
    silently and with nothing recording that it happened.

    A copy per call is cheap against what memoisation saves here: `SchemaView`
    construction and `class_induced_slots` over the whole class, which is the
    expensive part this cache exists to avoid repeating.
    """
    key = (class_name, str(schema_path or ""))
    if key not in _BUILD_CACHE:
        _BUILD_CACHE[key] = _build_uncached(class_name, schema_path)
    return copy.deepcopy(_BUILD_CACHE[key])


def _build_uncached(class_name: str, schema_path: Path | None = None) -> ClassDigest:
    """Slot inventory for one target class."""
    path = Path(schema_path) if schema_path else CLASS_SCHEMA.get(class_name)
    if path is None:
        raise ValueError(
            f"No schema known for class {class_name!r}; pass schema_path "
            f"explicitly. Known: {sorted(CLASS_SCHEMA)}")
    sv = SchemaView(str(path))
    digest = ClassDigest(class_name=class_name, schema_path=str(path))

    for slot in sv.class_induced_slots(class_name):
        enum_values: list[str] = []
        truncated = 0
        rng = slot.range
        if rng:
            enum = sv.get_enum(rng)
            if enum is not None:
                values = list((enum.permissible_values or {}).keys())
                enum_values = values[:MAX_ENUM_VALUES]
                truncated = max(0, len(values) - MAX_ENUM_VALUES)
        digest.slots.append(SlotDigest(
            name=str(slot.name),
            range=str(rng) if rng else None,
            description=_truncate(slot.description),
            required=bool(slot.required),
            multivalued=bool(slot.multivalued),
            enum_values=enum_values,
            enum_truncated=truncated,
            values_from=[str(v) for v in (slot.values_from or [])],
        ))
    digest.slots.sort(key=lambda s: s.name)

    # One level of nesting only. Deeper recursion reproduces most of the schema
    # and defeats the point of a digest; one level is what a generation run
    # needs to populate a slot's object without guessing its required keys.
    seen: set[str] = set()
    for slot in digest.slots:
        rng = slot.range
        if not rng or rng in seen:
            continue
        cls = sv.get_class(rng)
        if cls is None:
            continue
        seen.add(rng)
        req, opt = [], []
        enums: dict[str, list[str]] = {}
        enums_truncated: dict[str, int] = {}
        ranges: dict[str, str] = {}
        values_from: dict[str, list[str]] = {}
        for sub in sv.class_induced_slots(rng):
            (req if sub.required else opt).append(str(sub.name))
            if sub.range:
                ranges[str(sub.name)] = (
                    f"{sub.range}[]" if sub.multivalued else str(sub.range))
            if sub.values_from:
                values_from[str(sub.name)] = [str(v) for v in sub.values_from]
            sub_enum = sv.get_enum(sub.range) if sub.range else None
            if sub_enum is not None:
                values = list((sub_enum.permissible_values or {}).keys())
                enums[str(sub.name)] = values[:MAX_ENUM_VALUES]
                extra = len(values) - MAX_ENUM_VALUES
                if extra > 0:
                    enums_truncated[str(sub.name)] = extra
        if req or opt:
            digest.nested.append(NestedClass(
                name=rng, required=sorted(req), optional=sorted(opt),
                enums=enums, enums_truncated=enums_truncated,
                ranges=ranges, values_from=values_from))
    digest.nested.sort(key=lambda n: n.name)
    return digest


def render(digest: ClassDigest) -> str:
    """Markdown rendering, sized for prompt injection."""
    lines = [
        f"# Target class `{digest.class_name}` — slot inventory",
        "",
        f"Derived from `{digest.schema_path}`. Structure only: this states what "
        "shape a record takes, never what any dataset contains.",
        "",
        f"{len(digest.slots)} slots. `[req]` must be populated; `[many]` takes a "
        "list. A slot with an enum range accepts only the listed values.",
        "",
    ]
    for s in digest.slots:
        flags = "".join(f" [{f}]" for f, on in
                        (("req", s.required), ("many", s.multivalued)) if on)
        rng = f" — *{s.range}*" if s.range else ""
        lines.append(f"## `{s.name}`{rng}{flags}")
        if s.description:
            lines.append(s.description)
        if s.enum_values:
            shown = ", ".join(f"`{v}`" for v in s.enum_values)
            tail = f" (+{s.enum_truncated} more)" if s.enum_truncated else ""
            lines.append(f"Permitted: {shown}{tail}")
        vocabulary = render_values_from(s.values_from)
        if vocabulary:
            lines.append(f"Draw from: {vocabulary}")
        lines.append("")

    if digest.nested:
        lines += [
            "# Object ranges — required keys",
            "",
            "A slot whose range is one of these takes an object (or list of "
            "objects). Any listed **required** key must be present on every such "
            "object, or the record fails validation.",
            "",
            f"On every object below: {UNIVERSAL_RANGES}. A value of the wrong "
            "kind for its declared range is a defect even when it reads well.",
            "",
        ]
        top_level = {s.name for s in digest.slots}
        for n in digest.nested:
            req = ", ".join(f"`{k}`" for k in n.required) if n.required else "none"
            lines.append(f"- **{n.name}** — required: {req}")
            # `optional` was collected from the first version and never
            # rendered, so the digest said which nested keys were *mandatory*
            # and never which were *available*. 54 of 66 classes rendered as a
            # bare "required: none", and 367 attributes were named nowhere.
            #
            # Measured on the 25 current records: not one populates
            # `regulatory_restrictions.confidentiality_level`,
            # `.hipaa_compliant`, `.other_compliance` or
            # `.governance_committee_contact`. Every record instead writes prose
            # into that object's `description`, and the prose *contains the
            # answers* — "FDA Regulated: No", "De-identified Samples: Yes". The
            # model had the facts and no structured place it had been told
            # about. Q9 of rubric20 is capped at 3/5 on every record as a direct
            # result.
            optional = [k for k in n.optional if k not in UNIVERSAL_ATTRIBUTES]
            if optional:
                own = [k for k in optional if k not in top_level]
                mirrors = 1 - len(own) / len(optional) >= MIRRORS_TOP_LEVEL
                if mirrors:
                    extra = (" plus " + ", ".join(f"`{k}`" for k in own)) if own else ""
                    lines.append("    - also accepts the same slots as the "
                                 f"top-level listing above{extra}")
                else:
                    shown = ", ".join(f"`{k}`" for k in optional[:MAX_OPTIONAL_SHOWN])
                    over = len(optional) - MAX_OPTIONAL_SHOWN
                    tail = f" (+{over} more)" if over > 0 else ""
                    lines.append(f"    - also accepts: {shown}{tail}")
            # Ranges of nested attributes, for the same reason the enums are
            # here: the top-level listing never reaches them (#486).
            #
            # Only non-string ranges are shown. `string` is the schema's
            # default_range, so naming it costs digest size and tells a reader
            # nothing — while `uriorcurie`, `integer` and a class range are
            # exactly where a plausible-looking value can be the wrong kind.
            # `unit: mg/dL` is a correct-looking string under a `uriorcurie`
            # declaration, and it was invisible to the fitness judge because the
            # judge was shown the name and not the range.
            typed = shown_ranges(n)
            if typed:
                shown = ", ".join(f"`{k}`: {v}" for k, v in
                                  sorted(typed.items())[:MAX_OPTIONAL_SHOWN])
                over = len(typed) - MAX_OPTIONAL_SHOWN
                tail = f" (+{over} more)" if over > 0 else ""
                lines.append(f"    - ranges: {shown}{tail}")

            # A controlled vocabulary on a nested slot has to be shown here or
            # nowhere: the top-level listing never reaches it.
            for slot_name, values in sorted(n.enums.items()):
                shown = ", ".join(f"`{v}`" for v in values)
                extra = n.enums_truncated.get(slot_name, 0)
                tail = f" (+{extra} more)" if extra else ""
                lines.append(f"    - `{slot_name}` accepts only: {shown}{tail}")
            # The registry vocabulary a nested attribute draws from (#538).
            # Here or nowhere, exactly as for the enums above.
            for slot_name, names in sorted(n.values_from.items()):
                vocabulary = render_values_from(names)
                if vocabulary:
                    lines.append(f"    - `{slot_name}` draws from {vocabulary}")
        lines.append("")
    return "\n".join(lines)


_TEXT_CACHE: dict[tuple[str, str], str] = {}


def digest_text(class_name: str, schema_path: Path | None = None) -> str:
    """The rendered digest, memoised separately from `build`.

    `build` returns a deep copy so a caller cannot corrupt the cache (#528),
    which costs ~1.7 ms. `digest_text` renders and discards, so it needs no
    copy at all — and it is on a hot path: `LLMSlotFitnessScorer._context`
    calls it once per judgement to compute the cache key, so the copy would
    have been paid 1,441 times in a sweep for a value that never changes.

    Caching the *string* is safe where caching the object was not: strings are
    immutable, so there is nothing for a caller to mutate.
    """
    key = (class_name, str(schema_path or ""))
    if key not in _TEXT_CACHE:
        _TEXT_CACHE[key] = render(build(class_name, schema_path))
    return _TEXT_CACHE[key]


def fingerprint(text: str) -> str:
    """md5 of the rendered digest, for the provenance record.

    The digest is a generation input, so a run must be able to name exactly
    which one it consumed — the same reason the input bundle is hashed.
    """
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def stats(class_name: str, schema_path: Path | None = None) -> dict[str, Any]:
    """Size of the digest against the schema it replaces."""
    path = Path(schema_path) if schema_path else CLASS_SCHEMA.get(class_name)
    text = digest_text(class_name, path)
    raw = path.stat().st_size if path and path.exists() else 0
    return {
        "class": class_name,
        "schema_path": str(path),
        "schema_chars": raw,
        "digest_chars": len(text),
        "reduction": (1 - len(text) / raw) if raw else 0.0,
        "slots": len(build(class_name, path).slots),
        "md5": fingerprint(text),
    }
