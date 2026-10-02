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
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import MAXYEAR, MINYEAR, date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from linkml_runtime import SchemaView
from data_sheets_schema.schema_view import shared_view
from data_sheets_schema.scope import _norm, bare_doi

MAPPING_TSV = Path("data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv")
FULL_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
PACKAGES_DIR = Path("data/ro-crate_packages")
TARGET_CLASS = "Dataset"

#: The slot whose pattern is anchored to the bare DOI (#646). Crates carry the
#: resolver URL, and copying it through failed the schema while the report
#: still said PASS (#2916).
DOI_SLOT = "doi"

# Path grammar actually present in the table (verified against all 136 rows):
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
    status: str           # filled | subsumed | empty | unresolvable | unplaceable
    detail: str = ""
    value_preview: str = ""
    #: The crate's value, previewed, on the two identifier rows where the
    #: value written is not the crate's: a `doi` slot the DOI rule repaired
    #: (#2916), and the record `id` written as a `doi:` CURIE or taken from
    #: one item of a list. `write_provenance` shows it and `detail` beside
    #: the value, so the report never presents a rewritten value as the one
    #: the crate holds at the source path (#3139). Empty when the value is
    #: the crate's own. The other coercions (dates, joins, object shaping) do
    #: not set it; their note stays in `detail`, which the report shows
    #: beside the value on a filled table row (#3191).
    rewritten_from: str = ""
    #: False only on the record's `id` row, which `map_crate` takes from the
    #: crate root and no table row supplies; the report counts table rows
    #: apart from it (#2915).
    from_table: bool = True
    #: True on an `unplaceable` nested row that does resolve into the record
    #: but whose host slot a `Dataset` row already filled from another crate
    #: property; merging the two is not decided (#2915). The report's
    #: Outcome legend counts these apart, since "no route into a `Dataset`
    #: record" is not true of them (#3258).
    merge_undecided: bool = False


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


def crate_property(expr: str) -> str | None:
    """The crate property a source path reads, whichever form spells it.

    The table writes one property two ways: a Dataset row as
    ``@graph[?@type='Dataset']['rai:dataPreprocessingProtocol']`` and the
    nested row beside it as the bare ``rai:dataPreprocessingProtocol``. A
    name-selected path names its selector too, so two different
    ``additionalProperty`` entries are two properties. None for anything
    `resolve_path` does not read as a path.
    """
    expr = (expr or "").strip()
    if NOT_A_PATH.match(expr):
        return None
    m = GRAPH_RE.match(expr)
    if not m:
        return expr
    if m.group("name"):
        return f"{m.group('prop')}[?name='{m.group('name')}']['{m.group('prop2')}']"
    return m.group("prop")


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


ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
SLASH_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def _not_a_calendar_date(year: int, month: int, day: int) -> str:
    """Why `year`, `month` and `day` name no calendar date, or "" when they
    name one (#4168). `datetime.date` decides. The reason names the first
    part out of range, read in the order month, year, day, since the days a
    month has depend on the other two."""
    try:
        date(year, month, day)
    except ValueError:
        if not 1 <= month <= 12:
            return f"month {month} is not in 1-12"
        if not MINYEAR <= year <= MAXYEAR:
            return f"year {year:04d} is not in {MINYEAR:04d}-{MAXYEAR}"
        return (f"day {day} is not in 1-{monthrange(year, month)[1]} "
                f"for {year:04d}-{month:02d}")
    return ""


def _normalize_datetime(value: Any) -> tuple[Any, str]:
    """Bring crate dates to date-time, refusing to guess ambiguous ones.

    ``12/16/2025`` is unambiguous (16 cannot be a month) so it resolves.
    ``03/04/2026`` is not — the crates are known to mix DD/MM and MM/DD — so it
    is dropped rather than silently resolved to one reading. A slash date is
    ambiguous only where both orders read a calendar date (#4183).

    A value in either form that is not a calendar date is dropped too, with
    a reason that says so; it is never widened (#4168). `datetime.date`
    checks the year, month and day before a date-time is written. That
    covers an ISO date such as ``2026-13-45``, and a slash date that
    neither order reads as a date: ``13/13/2026``, ``31/02/2026``,
    ``0/0/2026``, ``01/02/0000``. Such a slash date had been called
    ambiguous, as though both orders read a date, or widened to a date-time
    the schema rejects. Year ``0000`` is no year to `datetime.date`, and the
    schema's date-time check rejects it too.

    It reads one text value. Anything else, a list included, comes back
    unchanged with no note, as does text in neither form; `_coerce`
    therefore unwraps a single-valued slot's one-item list whose item is
    text before calling it (#4109, #4154).
    """
    if not isinstance(value, str):
        return value, ""
    text = value.strip()
    m = ISO_DATE.match(text)
    if m:
        why = _not_a_calendar_date(*(int(part) for part in m.groups()))
        if why:
            return None, f"not a calendar date {text!r}: {why}; dropped"
        return f"{text}T00:00:00Z", "date -> date-time"
    m = SLASH_DATE.match(text)
    if m:
        a, b, year = (int(part) for part in m.groups())
        # Each order's (month, day), and why it reads no calendar date, or ""
        # where it reads one. The value is ambiguous only where both orders
        # read a date: both components are then months, but two months are
        # not enough, since `01/02/0000` reads no date in either order
        # (#4183). Where one order reads a date, the value is that date: a
        # component above 12 is no month, and 0 is neither a day nor a month.
        orders = {"DD/MM/YYYY": (b, a), "MM/DD/YYYY": (a, b)}
        why = {form: _not_a_calendar_date(year, month, day)
               for form, (month, day) in orders.items()}
        dates = [form for form in orders if not why[form]]
        if len(dates) == 2:
            return None, (f"ambiguous date {text!r}: both components are <= 12, so "
                          "DD/MM and MM/DD cannot be distinguished; dropped rather "
                          "than guessed")
        if dates:
            month, day = orders[dates[0]]
            return (f"{year:04d}-{month:02d}-{day:02d}T00:00:00Z",
                    f"{dates[0]} -> date-time")
        return None, (f"not a calendar date {text!r}: as DD/MM/YYYY, "
                      f"{why['DD/MM/YYYY']}, and as MM/DD/YYYY, "
                      f"{why['MM/DD/YYYY']}; dropped")
    return value, ""


def doi_for_slot(value: Any, pattern: str | None) -> tuple[str | None, str]:
    """The value a `doi` slot takes for a crate value, and what was done (#2916).

    `pattern` is the slot's own declared pattern, which the caller reads from
    the schema (the anchored bare-DOI pattern on every `doi` slot since #646).
    A value it already accepts is kept exactly as written: there is nothing
    to repair (#2989). Any other value is repaired only by `scope.bare_doi`:
    its resolver or `doi:` prefix, a trailing `/` and surrounding whitespace
    come off, and its case stays. `bare_doi` recognises a narrower shape than
    the pattern accepts (a registrant of four to nine digits, as in
    Crossref's recommended DOI pattern, and no whitespace in the suffix), so
    a prefixed value outside that shape is not repaired but dropped with the
    reason: what the rule does not recognise it does not guess at. A slot
    that declares no pattern accepts nothing as written here, and takes only
    what `bare_doi` finds.

    A list gives up its one DOI. Two spellings name one DOI when
    `scope._norm`, the comparison the scope checks use, makes them equal —
    DOIs are case-insensitive, so `10.5555/Test` and `10.5555/TEST` are one
    (#2987) — and the first spelling is kept. No DOI, or two different ones,
    gives None and the reason: an invalid value is never kept, and neither
    DOI is chosen over the other.

    Where each arm applies it (#2988): `rocrate_map._coerce` to every `doi`
    slot a mapping row fills — the table's only such row today is
    `Dataset.doi` — and `rocrate_normalize.normalize_linkml` to the Dataset's
    own `doi` only, so a `doi` nested inside another object passes through
    normalize as upstream wrote it, for validation to judge. `Dataset.doi` is
    the slot both arms write, and a crate value reaches it in one form
    whichever arm writes it.
    """
    candidates = value if isinstance(value, list) else [value]
    found: dict[str, list[tuple[str, str]]] = {}   # identity -> [(written, slot form)]
    for written in candidates:
        if isinstance(written, str) and pattern and re.search(pattern, written):
            form = written
        else:
            form = bare_doi(written)
        if form is not None:
            found.setdefault(_norm(form), []).append((written, form))
    if len(found) != 1:
        why = (f"{len(found)} distinct DOIs; the slot holds one and none is chosen"
               if found else "not a DOI the slot accepts as written or the "
               f"repair recognises: {_preview(value)}")
        return None, f"{why}; the doi slot takes the bare DOI only (#646)"
    spellings = next(iter(found.values()))
    written, doi = spellings[0]
    notes = []
    if isinstance(value, list):
        notes.append(f"the one DOI among {len(candidates)} list item(s)")
    forms = list(dict.fromkeys(form for _, form in spellings))
    if len(forms) > 1:
        notes.append(f"{len(forms)} spellings that differ only in case, a "
                     "trailing `/` or surrounding whitespace, so one DOI "
                     "(#2987); the first is kept")
    if doi != written:
        notes.append(_repair_note(written, doi))
    return doi, "; ".join(notes)


def _repair_note(written: str, doi: str) -> str:
    """What `bare_doi` took off `written` to leave `doi`, named part by part so
    a log never says a prefix came off when only a `/` or whitespace did."""
    stripped = written.strip()
    trimmed = stripped.rstrip("/")
    removed = []
    if trimmed != doi:
        removed.append("resolver or `doi:` prefix")
    if trimmed != stripped:
        removed.append("trailing `/`")
    if stripped != written:
        removed.append("surrounding whitespace")
    said = removed[0] if len(removed) == 1 else (
        ", ".join(removed[:-1]) + " and " + removed[-1])
    return f"{said} removed, case kept"


def _coerce(value: Any, slot, sv: SchemaView, project: str,
            counter: dict[str, int]) -> tuple[Any, str]:
    """Shape a crate value to the slot's cardinality and range."""
    notes: list[str] = []

    # Two list shapes are settled before any rule reads the value, so a row
    # reports them alike whatever its slot (#4164). A list whose every item
    # is null holds no value: the row is empty, and its reason names the
    # null, as `resolve_path` names an empty root property. That is decided
    # here, not in `resolve_path`, which passes an empty value by and reads
    # the next entity of the type: there the null would change which entity
    # a row reads. Here the entity is the same, and what changes is the row:
    # its reason everywhere, and its status and record wherever the rules
    # below had made the null a value. A null beside a value is not read
    # here (#4172). A list inside the list fits no slot, which holds one
    # value or a list of single values, so it is dropped, never flattened
    # one level. The rest of the list is shaped as though the crate held it
    # alone, and the row's detail names each list dropped before what the
    # rest's rules say, as the enum rule's `kept k/n` reports what it left
    # out (#4183). A list holding nothing but lists and nulls leaves nothing
    # to shape, so it is refused. The rules below had read both shapes as
    # values: the enum rule raised TypeError on a list item, the class step
    # made `{name: 'None'}` of a null and `{name: "['x']"}` of a list, the
    # cardinality step unwrapped `[[x]]` into a list in a single-valued slot
    # and joined `["x", ["y"]]` into `x; ['y']` and `[null, null]` into
    # `None; None`, and a multivalued text slot kept both shapes as written.
    #
    # Where this arm and the FAIRSCAPE converter of PR #4042 (`_shape`)
    # agree, checked by running both on each shape, with text, dates,
    # numbers, a boolean, URLs, references and objects, for every crate
    # property they map to the same `Dataset` slot: neither writes anything
    # for a list of only nulls, of only lists, or of nulls and lists. On a
    # list that mixes values with lists, this arm writes what it writes for
    # those values alone. So does the converter, except in two places, the
    # only ones where the arms agree on the values alone and not on the
    # list (#4194):
    # - A single-valued slot whose range is a class (`updates`,
    #   `human_subject_research`). The converter, which joins only text into
    #   one object, refuses the whole list, and this arm keeps the value.
    # - `collection_timeframes`, from a `rai:dataCollectionTimeframe` list
    #   holding an item written as a date (`2022`, `2022-09-01`,
    #   `9/1/2022`). The converter's `_timeframe` reads that list before
    #   `_shape` does: two items are a start and an end, a list inside the
    #   list counting as one of them, and three or more are dropped whole.
    #   So for `["2022-09-01", ["2026-01-31"]]` the converter writes one
    #   timeframe from 2022-09-01 to 2026-01-31, with nothing in `dropped`,
    #   and for `["2022-09-01", ["y"], ["z"]]` nothing. This arm writes
    #   `[{name: '2022-09-01'}]` for each, as for `["2022-09-01"]` alone,
    #   and names each list it dropped.
    # They do not agree on a null beside a value, which the converter drops
    # (#4172).
    if isinstance(value, list) and value:
        if all(item is None for item in value):
            return None, f"no value: the list holds only null ({_preview(value)})"
        nested = [item for item in value if isinstance(item, list)]
        if nested:
            holds = "a list of single values" if slot.multivalued else "one value"
            rest = [item for item in value if not isinstance(item, list)]
            if all(item is None for item in rest):
                return None, (f"a list inside a list, for a slot that holds {holds}: "
                              f"{_preview(value)}; dropped rather than flattened")
            left_out = (
                f"{len(nested)} of {len(value)} list items "
                f"{'is a list' if len(nested) == 1 else 'are lists'} inside the "
                f"list, for a slot that holds {holds}: "
                f"{_preview(', '.join(_preview(item) for item in nested))}; "
                "dropped rather than flattened")
            # `rest` holds no list, so this goes one call deep.
            value, note = _coerce(rest, slot, sv, project, counter)
            return value, "; ".join(part for part in (left_out, note) if part)

    # Every class's `doi` slot carries the same anchored pattern, so a row
    # that fills a nested class's `doi` is shaped the same way as the
    # Dataset's own, against that slot's pattern.
    if slot.name == DOI_SLOT:
        value, note = doi_for_slot(value, slot.pattern)
        if value is None:
            return None, note
        if note:
            notes.append(note)

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
        # The date rule reads one text value and passes anything else
        # through, a list included, so a single-valued slot's one-item list
        # whose item is text is unwrapped here, before it, not by the
        # cardinality step below: `["2026-06-30"]` stayed a date in a
        # date-time slot, and `["9/1/2022"]` got past the ambiguity refusal
        # (#4109). The rule makes text into text or nothing, never a list,
        # so that step then finds no list: a value the rule keeps carries
        # the note once, and one it refuses carries the refusal alone, as
        # its scalar form does. A one-item list whose item is not text (a
        # number, a reference) is not the rule's to read; it is left to that
        # step, which unwraps it once (#4154). `[null]` and a list inside a
        # list never reach here (#4164).
        if (not slot.multivalued and isinstance(value, list) and len(value) == 1
                and isinstance(value[0], str)):
            value = value[0]
            notes.append("unwrapped single-item list")
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
            # Counted before the join: after it, `len` is the joined string's
            # character count, which the report printed as the item count
            # (#3191).
            items = len(value)
            value = "; ".join(str(v) for v in value)
            notes.append(f"joined {items} list items")
    return value, "; ".join(notes)


def map_crate(graph: list[dict], rows: list[dict], sv: SchemaView,
              project: str = "") -> MapResult:
    """Apply `rows` to the crate `graph`, reporting every row's outcome.

    A ``Dataset.<slot>`` row is placed as it is read. A row for a nested
    class is held until every row has been read, so what it may do does not
    depend on where it sits in the table (#2915): a host slot that a
    ``Dataset.<host>`` row filled is never replaced. Where that row read the
    same crate value, the nested row is ``subsumed`` and its detail names the
    row that carries the value; replacing it had turned a multi-item list of
    objects into one object with the items '; '-joined. Where it read
    something else, the nested row is unplaceable and says so: merging two
    crate properties into one object is a curation decision this arm does not
    make. Nested rows with no such Dataset row fill one object, as before.
    """
    res = MapResult(project=project)
    counter: dict[str, int] = {}
    root = crate_root(graph)
    dataset_slots = {s.name: s for s in sv.class_induced_slots(TARGET_CLASS)}
    placement = build_placement(sv)
    nested: dict[str, dict] = {}
    #: host slot -> (the Dataset row that filled it, crate property, crate value)
    filled_by: dict[str, tuple[FieldResult, str | None, Any]] = {}
    #: nested rows that resolved, in table order, awaiting the second pass:
    #: (their report row, host slot, nested slot name, value, property, crate value)
    held: list[tuple[FieldResult, str, str, Any, str | None, Any]] = []

    for row in rows:
        d4d_path = row["D4D_Full_Path"].strip()
        source = (row.get("RO_Crate_JSON_Path") or "").strip()
        mtype = (row.get("Mapping_Type") or "").strip()
        loss = (row.get("Information_Loss") or "").strip()
        cls, _, slot_name = d4d_path.partition(".")

        def record(status, detail="", preview="", rewritten_from=""):
            res.fields.append(FieldResult(d4d_path, source, mtype, loss,
                                          status, detail, preview,
                                          rewritten_from))

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

        crate_value = value
        value, coercion = _coerce(value, slot, sv, project or 'd4d', counter)
        if value is None:
            record("empty", coercion)
            continue
        # Where the DOI rule in `_coerce` wrote something other than the
        # crate's value, the report names the crate's value (#3139). A value
        # the slot's pattern kept verbatim (#2989) is the crate's own.
        rewritten_from = (_preview(crate_value)
                          if slot.name == DOI_SLOT and value != crate_value else "")
        where, slot = target
        record("filled", coercion, _preview(value), rewritten_from)
        if where == "root":
            res.record[slot_name] = value
            filled_by[slot_name] = (res.fields[-1], crate_property(source), crate_value)
        else:
            held.append((res.fields[-1], where, slot_name, value,
                         crate_property(source), crate_value))

    # Second pass: nested rows, now that every Dataset row has been placed.
    for field_result, where, slot_name, value, prop, crate_value in held:
        owner = filled_by.get(where)
        if owner is None:
            nested.setdefault(where, {})[slot_name] = value
            continue
        owner_row, owner_prop, owner_value = owner
        field_result.value_preview = ""
        field_result.rewritten_from = ""
        if prop is not None and prop == owner_prop and crate_value == owner_value:
            field_result.status = "subsumed"
            field_result.detail = (
                f"{owner_row.d4d_path} already carries this crate value "
                f"({prop}); not placed a second time (#2915)")
        else:
            field_result.status = "unplaceable"
            field_result.merge_undecided = True
            what = ("the same crate property with a different value (another "
                    "entity), and merging the two values"
                    if prop is not None and prop == owner_prop else
                    "another crate property, and merging two crate properties")
            field_result.detail = (
                f"{owner_row.d4d_path} already filled {TARGET_CLASS}.{where} from "
                f"{owner_prop or owner_row.source_path}; this row reads "
                f"{prop or field_result.source_path}: {what} into one object is "
                "not decided (#2915, #3270)")

    # The record's own required id: use the crate's identifier rather than
    # minting one, so the D4D record points back at the crate it came from.
    # A DOI is written as the `doi:` CURIE, the form #974's write-time
    # normaliser gives the generated arms, so the two compare as one value.
    if "id" not in res.record and root is not None:
        crate_value = root.get("identifier") or root.get("@id")
        crate_id = crate_value
        if isinstance(crate_id, list):
            crate_id = crate_id[0] if crate_id else None
        if crate_id:
            doi = bare_doi(crate_id)
            res.record["id"] = f"doi:{doi}" if doi else str(crate_id)
            detail = "required by the schema; taken from the crate itself"
            if isinstance(crate_value, list):
                detail += f"; the first of {len(crate_value)} list item(s)"
            if doi:
                detail += "; a DOI is written as the doi: CURIE (#974)"
            # Wherever the id written is not what the crate holds there — the
            # CURIE of a DOI, or one item of a list — the report names the
            # crate's value, as a `doi` row does (#3139).
            rewritten_from = (_preview(crate_value)
                              if res.record["id"] != crate_value else "")
            res.fields.append(FieldResult(
                "Dataset.id", "crate root identifier/@id", "exactMatch", "none",
                "filled", detail, _preview(res.record["id"]), rewritten_from,
                from_table=False))

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
    from data_sheets_schema.resources import linkml_validate, resource_path
    proc = subprocess.run(
        [*linkml_validate(), "-s", str(resource_path(FULL_SCHEMA)),
         "-C", TARGET_CLASS, str(path)],
        capture_output=True, text=True,
    )
    out = (proc.stdout + proc.stderr).strip()
    return "PASS" if proc.returncode == 0 and "No issues found" in out else f"FAIL\n{out}"


def verdict_basis(schema: Path = FULL_SCHEMA, on: str | None = None) -> str:
    """What a validation verdict was reached against, to write beside it (#2916).

    A bare PASS pins nothing: #646 anchored the doi pattern and every crate
    report went on saying PASS over records the schema now rejects. The
    declared version, the sha256 of the merged schema `validate` reads and the
    date let a reader tell a verdict about today's schema from an older one.
    """
    from data_sheets_schema.provenance import declared_schema_version
    from data_sheets_schema.schema_cache import sha256_of
    version = declared_schema_version(schema) or "(no version declared)"
    day = on or datetime.now(timezone.utc).date().isoformat()
    return f"schema {version} / sha256 {sha256_of(schema)} / {day} (`{schema}`)"


class CrateEncodingError(ValueError):
    """A crate's JSON is not UTF-8, so it is not JSON under RFC 8259 (#2969)."""


#: How `read_crate_json`'s refusal ends unless its caller says otherwise:
#: what to do about a crate the static-map arm reads, one crate_manifest.yaml
#: declares, where a project's `encoding_note` records how its crate is
#: written (AI_READI's, #2969).
ENCODING_NOTE_HINT = ("declare or transcode it deliberately (see the "
                      "project's `encoding_note` in crate_manifest.yaml)")

#: How it ends for a crate read from whatever path a user gives, as the
#: FAIRSCAPE converter, `fairscape-cli rocrate-to-d4d` and `fairscape-cli
#: info` read one. The manifest need not declare that crate, so there is
#: no note to point to and nowhere to declare its encoding (#4192).
TRANSCODE_HINT = "transcode it to UTF-8 from the encoding it is written in"


def read_crate_json(path: Path, *, hint: str = ENCODING_NOTE_HINT) -> Any:
    """Parse a crate's ``ro-crate-metadata.json``, refusing one that is not UTF-8.

    The AI_READI crate is windows-1252 (crate_manifest.yaml `encoding_note`),
    and reading it as UTF-8 raised a bare UnicodeDecodeError that ended the
    whole `d4d rocrate map`/`normalize` run at the first such project (#2969).
    No other encoding is tried: bytes that are not UTF-8 decode as *something*
    under most single-byte encodings, so a fallback would be a silent guess,
    and ``raw/`` is the provenance anchor that is never repaired in place. A
    transcode is a curation decision, to be declared, not inferred here.

    `hint` ends the refusal, after "Not decoded under a guessed encoding;".
    The default, `ENCODING_NOTE_HINT`, points to the project's
    `encoding_note`, and `d4d rocrate map` and `normalize` keep it. A caller
    that reads a crate from any path passes `TRANSCODE_HINT` instead,
    since the note need not describe that crate (#4192).
    """
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        # surrogateescape maps each undecodable byte to one lone surrogate,
        # so this counts bytes, not decoding errors.
        bad = sum(1 for ch in data.decode("utf-8", errors="surrogateescape")
                  if "\udc80" <= ch <= "\udcff")
        raise CrateEncodingError(
            f"{path} is not UTF-8, as RFC 8259 requires of JSON: byte "
            f"0x{data[e.start]:02x} at offset {e.start}, {bad} undecodable "
            f"byte(s) in all. Not decoded under a guessed encoding; {hint}"
        ) from e
    return json.loads(text)


def write_provenance(res: MapResult, path: Path, source_file: Path) -> None:
    c = res.counts()
    table_rows = sum(1 for f in res.fields if f.from_table)
    id_rows = len(res.fields) - table_rows
    applied = f"{table_rows} table rows applied" + (
        ", plus the record's `id`, taken from the crate root" if id_rows else "")
    filled_rows = c.get("filled", 0)
    merge_undecided = sum(1 for f in res.fields
                          if f.status == "unplaceable" and f.merge_undecided)
    # A slot is counted once however many rows filled it: nested rows fill
    # one object in their host slot (#2915).
    slots = len([k for k, v in res.record.items() if v not in (None, "", [], {})])
    lines = [
        f"# Crate → D4D Static Mapping — {res.project}",
        "",
        "Produced by `d4d rocrate map`. Every field below was placed by this",
        f"repo's own mapping table (`{MAPPING_TSV}`), not by an upstream",
        "D4D-shaped rendering. No value is inferred: a field is filled only when",
        "its declared path resolves in the crate.",
        "",
        f"- Crate metadata: `{source_file}`",
        f"- Mapping table: `{MAPPING_TSV}` ({applied})",
        f"- Validation: **{res.validation.splitlines()[0]}** — {verdict_basis()}",
        f"- Distinct top-level `{TARGET_CLASS}` slots filled: {slots} "
        f"(from {filled_rows} filled rows"
        + (", the `id` among them)" if id_rows else ")"),
        "",
        "## Outcome",
        "",
        "| Status | Rows | Meaning |",
        "|--------|------|---------|",
        f"| filled | {filled_rows} | path resolved; value placed"
        + (" (includes the record's `id`, which no table row supplies)"
           if id_rows else "") + " |",
        f"| subsumed | {c.get('subsumed',0)} | path resolved, but a `{TARGET_CLASS}` "
        "row already placed the same crate value in the host slot |",
        f"| empty | {c.get('empty',0)} | path valid but the crate has no value there |",
        f"| unresolvable | {c.get('unresolvable',0)} | the table declares no crate path |",
        f"| unplaceable | {c.get('unplaceable',0)} | no route into a `Dataset` record"
        + (f"; {merge_undecided} of them do resolve, but a `{TARGET_CLASS}` row "
           "already filled the host slot, from another crate property or from "
           "the same property with a different value, and merging the two is "
           "not decided" if merge_undecided else "") + " |",
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
        if f.status == "filled" and f.from_table and f.value_preview and f.detail:
            # A filled row's note says what was done to the crate's value on
            # the way in (a date widened, a list joined, values dropped by an
            # enum); showing the value alone presented it as the crate's own
            # (#3191).
            cell = f"{f.value_preview} — {f.detail}"
        if f.rewritten_from:
            # The value written is not the crate's: say what the crate holds
            # at the source path and what was done to it (#3139).
            cell = (f"{f.value_preview} — rewritten from the crate's "
                    f"{f.rewritten_from}" + (f": {f.detail}" if f.detail else ""))
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

    sv = sv or shared_view(FULL_SCHEMA)
    rows = rows if rows is not None else load_mapping()
    graph = read_crate_json(source).get("@graph", [])

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
