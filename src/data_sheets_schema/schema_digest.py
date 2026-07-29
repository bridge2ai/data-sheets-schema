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
MAX_ENUM_VALUES = 40


@dataclass
class SlotDigest:
    name: str
    range: str | None
    description: str | None
    required: bool = False
    multivalued: bool = False
    enum_values: list[str] = field(default_factory=list)
    enum_truncated: int = 0


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


def build(class_name: str, schema_path: Path | None = None) -> ClassDigest:
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
        for sub in sv.class_induced_slots(rng):
            (req if sub.required else opt).append(str(sub.name))
        if req or opt:
            digest.nested.append(NestedClass(name=rng, required=sorted(req),
                                             optional=sorted(opt)))
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
        lines.append("")

    if digest.nested:
        lines += [
            "# Object ranges — required keys",
            "",
            "A slot whose range is one of these takes an object (or list of "
            "objects). Any listed **required** key must be present on every such "
            "object, or the record fails validation.",
            "",
        ]
        for n in digest.nested:
            req = ", ".join(f"`{k}`" for k in n.required) if n.required else "none"
            lines.append(f"- **{n.name}** — required: {req}")
        lines.append("")
    return "\n".join(lines)


def digest_text(class_name: str, schema_path: Path | None = None) -> str:
    return render(build(class_name, schema_path))


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
