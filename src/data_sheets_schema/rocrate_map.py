"""Map an RO-Crate to a D4D record using this repo's own static mapping table.

This is the *our-mapping* deterministic arm. It differs from
``rocrate_normalize`` in what it consumes and what it can therefore claim:

- ``rocrate_normalize`` repairs ``ro-crate-linkml.yaml``, a D4D-shaped rendering
  produced **upstream**. It works only where upstream ships one, and it is
  opaque about how good each mapping is.
- This module reads ``ro-crate-metadata.json``, which **every** crate has, and
  applies ``data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv``. Each
  emitted field therefore carries its own declared provenance: the source path,
  the SKOS mapping type, and the expected information loss.

No inference and no gap-filling: a field appears only when the declared path
resolves in the crate. Everything the table declares but the crate does not
supply is reported as unfilled, and every table row that cannot be placed in a
``Dataset`` record is reported with the reason.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from linkml_runtime import SchemaView

MAPPING_TSV = Path("data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv")
FULL_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
PACKAGES_DIR = Path("data/ro-crate_packages")
TARGET_CLASS = "Dataset"

# Path grammar actually present in the table (verified against all 133 rows):
#   @graph[?@type='T']['prop']
#   @graph[?@type='T']['prop'][?name='N']['prop2']
#   bare property name, e.g. rai:dataBiases  -> looked up on the crate root
# Anything else (N/A, prose such as "encodingFormat MIME parameter", or a
# d4d:* URI naming the D4D side rather than the crate side) is not a path.
GRAPH_RE = re.compile(
    r"^@graph\[\?@type='(?P<type>[^']+)'\]\['(?P<prop>[^']+)'\]"
    r"(?:\[\?name='(?P<name>[^']+)'\]\['(?P<prop2>[^']+)'\])?$"
)
NOT_A_PATH = re.compile(r"^(N/A|\s*|.*\s+MIME\s+parameter|d4d:.*)$", re.IGNORECASE)


@dataclass
class FieldResult:
    d4d_path: str
    source_path: str
    mapping_type: str
    information_loss: str
    status: str           # filled | empty | unresolvable | unplaceable
    detail: str = ""
    value_preview: str = ""


@dataclass
class MapResult:
    project: str
    record: dict = field(default_factory=dict)
    fields: list[FieldResult] = field(default_factory=list)
    outputs: dict[str, Path] = field(default_factory=dict)
    validation: str = ""

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.fields:
            out[f.status] = out.get(f.status, 0) + 1
        return out


def load_mapping(path: Path = MAPPING_TSV) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh, delimiter="\t") if r.get("D4D_Full_Path")]


# --------------------------------------------------------------------------
# crate access
# --------------------------------------------------------------------------

def _types_of(entity: dict) -> list[str]:
    t = entity.get("@type")
    return t if isinstance(t, list) else ([t] if t else [])


def _type_matches(entity: dict, wanted: str) -> bool:
    """Match 'Dataset' against 'Dataset' or 'https://w3id.org/EVI#Dataset'."""
    for t in _types_of(entity):
        if t == wanted or re.search(rf"[#/:]{re.escape(wanted)}$", str(t)):
            return True
    return False


def crate_root(graph: list[dict]) -> dict | None:
    """The crate's own top entity: the ROCrate-typed one, else first Dataset."""
    for e in graph:
        if any("ROCrate" in str(t) for t in _types_of(e)):
            return e
    for e in graph:
        if _type_matches(e, "Dataset"):
            return e
    return None


def resolve_path(expr: str, graph: list[dict], root: dict | None) -> tuple[Any, str]:
    """Return (value, note). value is None when the path does not resolve."""
    expr = (expr or "").strip()
    if NOT_A_PATH.match(expr):
        return None, "not a crate path"

    m = GRAPH_RE.match(expr)
    if m:
        wanted, prop = m.group("type"), m.group("prop")
        entities = [e for e in graph if _type_matches(e, wanted)]
        if not entities:
            return None, f"no @type={wanted} entity in crate"
        for entity in entities:
            value = entity.get(prop)
            if value in (None, "", [], {}):
                continue
            if m.group("name"):
                # nested selector: pick the list item whose name matches
                items = value if isinstance(value, list) else [value]
                for item in items:
                    if isinstance(item, dict) and item.get("name") == m.group("name"):
                        inner = item.get(m.group("prop2"))
                        if inner not in (None, "", [], {}):
                            return inner, ""
                continue
            return value, ""
        return None, f"@type={wanted} present but '{prop}' empty or absent"

    # bare property on the crate root (the rai:* rows)
    if root is not None and expr in root:
        value = root[expr]
        return (value, "") if value not in (None, "", [], {}) else (None, "root property empty")
    if root is None:
        return None, "no crate root entity"
    return None, f"'{expr}' not present on crate root"


# --------------------------------------------------------------------------
# placing values into a Dataset record
# --------------------------------------------------------------------------

def build_placement(sv: SchemaView) -> dict[str, str]:
    """Map a nested class name -> the Dataset slot that ranges over it."""
    placement: dict[str, str] = {}
    for slot in sv.class_induced_slots(TARGET_CLASS):
        if slot.range and sv.get_class(slot.range):
            placement.setdefault(slot.range, slot.name)
    return placement


NAME_MAX = 120


def _to_object(value: Any, cls_name: str, sv: SchemaView, project: str,
               slot_name: str, counter: dict[str, int]) -> tuple[Any, str]:
    """Shape a crate scalar or reference into an instance of a D4D class.

    Crates supply plain strings (``"Yael Bensoussan"``) or bare references
    (``{"@id": "..."}``) where D4D expects an object. The only value this
    invents is an identifier, and only where the class *requires* one —
    matching the ``urn:d4d:`` convention used elsewhere for structurally
    required but unsupplied ids.
    """
    slots = {s.name: s for s in sv.class_induced_slots(cls_name)}
    required_id = any(s.name == "id" and s.required for s in slots.values())
    obj: dict[str, Any] = {}
    note = ""

    if isinstance(value, dict):
        if "@id" in value and "id" in slots:
            obj["id"] = value["@id"]
        if value.get("name") and "name" in slots:
            obj["name"] = value["name"]
        if value.get("description") and "description" in slots:
            obj["description"] = value["description"]
        if not obj:
            return value, ""  # leave it; validation will judge
        note = f"crate reference -> {cls_name}"
    else:
        text = str(value)
        single_line = "\n" not in text.strip()
        # A required text slot takes precedence: filling `name` while leaving a
        # required `source_description` empty would produce an invalid object.
        required_text = next(
            (s.name for s in slots.values()
             if s.required and s.range == "string" and s.name not in ("id",)),
            None,
        )
        if required_text:
            obj[required_text] = text
            note = f"string -> {cls_name}.{required_text} (required slot)"
        elif "name" in slots and single_line and len(text) <= NAME_MAX:
            obj["name"] = text
            note = f"string -> {cls_name}.name"
        elif "description" in slots:
            obj["description"] = text
            note = f"string -> {cls_name}.description"
        else:
            return value, ""

    if required_id and "id" not in obj:
        counter[slot_name] = counter.get(slot_name, 0) + 1
        obj["id"] = f"urn:d4d:{project.lower()}:{slot_name}:{counter[slot_name]}"
        note += "; minted required id"
    return obj, note


ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLASH_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def _normalize_datetime(value: Any) -> tuple[Any, str]:
    """Bring crate dates to date-time, refusing to guess ambiguous ones.

    ``12/16/2025`` is unambiguous (16 cannot be a month) so it resolves.
    ``03/04/2026`` is not — the crates are known to mix DD/MM and MM/DD — so it
    is dropped rather than silently resolved to one reading.
    """
    if not isinstance(value, str):
        return value, ""
    text = value.strip()
    if ISO_DATE.match(text):
        return f"{text}T00:00:00Z", "date -> date-time"
    m = SLASH_DATE.match(text)
    if m:
        a, b, year = int(m.group(1)), int(m.group(2)), m.group(3)
        if a > 12 and b <= 12:      # DD/MM
            return f"{year}-{b:02d}-{a:02d}T00:00:00Z", "DD/MM/YYYY -> date-time"
        if b > 12 and a <= 12:      # MM/DD
            return f"{year}-{a:02d}-{b:02d}T00:00:00Z", "MM/DD/YYYY -> date-time"
        return None, (f"ambiguous date {text!r}: both components are <= 12, so "
                      "DD/MM and MM/DD cannot be distinguished; dropped rather "
                      "than guessed")
    return value, ""


def _coerce(value: Any, slot, sv: SchemaView, project: str,
            counter: dict[str, int]) -> tuple[Any, str]:
    """Shape a crate value to the slot's cardinality and range."""
    notes: list[str] = []

    # Enum ranges: keep only permitted values, never coerce into one.
    enum = sv.get_enum(slot.range) if slot.range else None
    if enum:
        permitted = set(enum.permissible_values)
        candidates = value if isinstance(value, list) else [value]
        kept = [v for v in candidates if v in permitted]
        if not kept:
            return None, (f"no value permitted by {slot.range} "
                          f"({'|'.join(sorted(permitted))}); dropped")
        value = kept if slot.multivalued else kept[0]
        if len(kept) != len(candidates):
            notes.append(f"kept {len(kept)}/{len(candidates)} enum-permitted values")

    if slot.range in ("datetime", "date"):
        value, note = _normalize_datetime(value)
        if value is None:
            return None, note
        if note:
            notes.append(note)

    is_class = bool(slot.range) and sv.get_class(slot.range) is not None

    if is_class:
        items = value if isinstance(value, list) else [value]
        shaped = []
        for item in items:
            obj, note = _to_object(item, slot.range, sv, project, slot.name, counter)
            shaped.append(obj)
            if note and note not in notes:
                notes.append(note)
        value = shaped if isinstance(value, list) else shaped[0]

    multivalued = bool(slot.multivalued)
    if multivalued and not isinstance(value, list):
        value = [value]
        notes.append("wrapped scalar into a list")
    elif not multivalued and isinstance(value, list):
        if len(value) == 1:
            value = value[0]
            notes.append("unwrapped single-item list")
        else:
            value = "; ".join(str(v) for v in value)
            notes.append(f"joined {len(value)} list items")
    return value, "; ".join(notes)


def map_crate(graph: list[dict], rows: list[dict], sv: SchemaView,
              project: str = "") -> MapResult:
    res = MapResult(project=project)
    counter: dict[str, int] = {}
    root = crate_root(graph)
    dataset_slots = {s.name: s for s in sv.class_induced_slots(TARGET_CLASS)}
    placement = build_placement(sv)
    nested: dict[str, dict] = {}

    for row in rows:
        d4d_path = row["D4D_Full_Path"].strip()
        source = (row.get("RO_Crate_JSON_Path") or "").strip()
        mtype = (row.get("Mapping_Type") or "").strip()
        loss = (row.get("Information_Loss") or "").strip()
        cls, _, slot_name = d4d_path.partition(".")

        def record(status, detail="", preview=""):
            res.fields.append(FieldResult(d4d_path, source, mtype, loss,
                                          status, detail, preview))

        # Can this row be placed in a Dataset record at all?
        if cls == TARGET_CLASS:
            slot = dataset_slots.get(slot_name)
            if slot is None:
                record("unplaceable", f"'{slot_name}' is not a slot on {TARGET_CLASS}")
                continue
            target = ("root", slot)
        else:
            host_slot_name = placement.get(cls)
            if host_slot_name is None:
                record("unplaceable",
                       f"no {TARGET_CLASS} slot ranges over {cls}")
                continue
            nested_slots = {s.name: s for s in sv.class_induced_slots(cls)}
            slot = nested_slots.get(slot_name)
            if slot is None:
                record("unplaceable", f"'{slot_name}' is not a slot on {cls}")
                continue
            target = (host_slot_name, slot)

        value, note = resolve_path(source, graph, root)
        if value is None:
            record("unresolvable" if note == "not a crate path" else "empty", note)
            continue

        value, coercion = _coerce(value, slot, sv, project or 'd4d', counter)
        if value is None:
            record("empty", coercion)
            continue
        where, slot = target
        if where == "root":
            res.record[slot_name] = value
        else:
            nested.setdefault(where, {})[slot_name] = value
        record("filled", coercion, _preview(value))

    # The record's own required id: use the crate's identifier rather than
    # minting one, so the D4D record points back at the crate it came from.
    if "id" not in res.record and root is not None:
        crate_id = root.get("identifier") or root.get("@id")
        if isinstance(crate_id, list):
            crate_id = crate_id[0] if crate_id else None
        if crate_id:
            res.record["id"] = str(crate_id)
            res.fields.append(FieldResult(
                "Dataset.id", "crate root identifier/@id", "exactMatch", "none",
                "filled", "required by the schema; taken from the crate itself",
                _preview(crate_id)))

    # attach nested objects, respecting each host slot's cardinality
    for host_slot_name, obj in nested.items():
        host = dataset_slots[host_slot_name]
        res.record[host_slot_name] = [obj] if host.multivalued else obj

    return res


def _preview(value: Any, limit: int = 90) -> str:
    s = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return s if len(s) <= limit else s[: limit - 1] + "…"


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def validate(path: Path) -> str:
    proc = subprocess.run(
        ["poetry", "run", "linkml-validate", "-s", str(FULL_SCHEMA),
         "-C", TARGET_CLASS, str(path)],
        capture_output=True, text=True,
    )
    out = (proc.stdout + proc.stderr).strip()
    return "PASS" if proc.returncode == 0 and "No issues found" in out else f"FAIL\n{out}"


def write_provenance(res: MapResult, path: Path, source_file: Path) -> None:
    c = res.counts()
    lines = [
        f"# Crate → D4D Static Mapping — {res.project}",
        "",
        "Produced by `d4d rocrate map`. Every field below was placed by this",
        f"repo's own mapping table (`{MAPPING_TSV}`), not by an upstream",
        "D4D-shaped rendering. No value is inferred: a field is filled only when",
        "its declared path resolves in the crate.",
        "",
        f"- Crate metadata: `{source_file}`",
        f"- Mapping table: `{MAPPING_TSV}` ({len(res.fields)} rows applied)",
        f"- Validation: **{res.validation.splitlines()[0]}**",
        "",
        "## Outcome",
        "",
        "| Status | Rows | Meaning |",
        "|--------|------|---------|",
        f"| filled | {c.get('filled',0)} | path resolved; value placed |",
        f"| empty | {c.get('empty',0)} | path valid but the crate has no value there |",
        f"| unresolvable | {c.get('unresolvable',0)} | the table declares no crate path |",
        f"| unplaceable | {c.get('unplaceable',0)} | no route into a `Dataset` record |",
        "",
        "## Fidelity of what was filled",
        "",
    ]
    filled = [f for f in res.fields if f.status == "filled"]
    by_type: dict[str, int] = {}
    by_loss: dict[str, int] = {}
    for f in filled:
        by_type[f.mapping_type] = by_type.get(f.mapping_type, 0) + 1
        by_loss[f.information_loss] = by_loss.get(f.information_loss, 0) + 1
    lines += ["| Mapping type | Filled fields |", "|---|---|"]
    lines += [f"| {k or '(unstated)'} | {v} |" for k, v in sorted(by_type.items())]
    lines += ["", "| Information loss | Filled fields |", "|---|---|"]
    lines += [f"| {k or '(unstated)'} | {v} |" for k, v in sorted(by_loss.items())]
    lines += [
        "",
        "Fields marked `moderate` or `high` loss carry a value that the mapping",
        "table itself flags as an imperfect representation of the crate's",
        "content. Treat them as weaker evidence than `none`/`minimal` fields.",
        "",
        "## Per-field detail",
        "",
        "| D4D path | Status | Mapping | Loss | Source path | Value / note |",
        "|---|---|---|---|---|---|",
    ]
    for f in sorted(res.fields, key=lambda x: (x.status != "filled", x.d4d_path)):
        cell = f.value_preview or f.detail
        row = [f.d4d_path, f.status, f.mapping_type or "—",
               f.information_loss or "—", f.source_path or "—", cell or ""]
        lines.append("| " + " | ".join(
            str(x).replace("|", "\\|").replace("\n", " ") for x in row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def map_project(project: str, packages_dir: Path = PACKAGES_DIR,
                sv: SchemaView | None = None,
                rows: list[dict] | None = None) -> MapResult:
    project_dir = packages_dir / project
    source = None
    for base in (project_dir / "raw", project_dir / "crate"):
        candidate = base / "ro-crate-metadata.json"
        if candidate.exists():
            source = candidate
            break
    if source is None:
        raise FileNotFoundError(
            f"No ro-crate-metadata.json under {project_dir}/raw or {project_dir}/crate"
        )

    sv = sv or SchemaView(str(FULL_SCHEMA))
    rows = rows if rows is not None else load_mapping()
    graph = json.loads(source.read_text(encoding="utf-8")).get("@graph", [])

    res = map_crate(graph, rows, sv, project)

    out_dir = project_dir / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{project}_crate_mapped_d4d.yaml"
    header = (
        f"# D4D record for {project}, mapped from its RO-Crate\n"
        "# Method: static mapping using this repo's own mapping table\n"
        f"# Mapping table: {MAPPING_TSV}\n"
        f"# Source: {source}\n"
        "# Upstream ro-crate-linkml.yaml deliberately NOT used\n"
        "# No inferred values; see the provenance report alongside\n"
    )
    target.write_text(
        header + yaml.safe_dump(res.record, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    res.outputs["d4d"] = target
    res.validation = validate(target)

    report = out_dir / f"{project}_crate_mapping_provenance.md"
    write_provenance(res, report, source)
    res.outputs["provenance"] = report
    return res
