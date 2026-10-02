#!/usr/bin/env python3
"""
FAIRSCAPE RO-Crate to D4D Converter (Reverse Transformation)

Converts FAIRSCAPE RO-Crate JSON-LD to D4D YAML format.

Features:
- Field mapping written out in this module's extraction methods
- The record describes the crate's root data entity, the one the metadata
  descriptor is `about` (#4072)
- Vocabulary translation (schema.org → dcterms, etc.)
- Pydantic validation of input RO-Crate
- Output fitted to the schema's Dataset class: of what this converter
  reads, a key the class does not declare, a value that cannot be shaped
  to its slot, and any part of a value its slot cannot hold are left out
  and named in `dropped` (#3969, #4073). So is an `additionalProperty`
  entry with no name written as text, whatever it carries; a reference
  there is not looked up in the `@graph` (#4152). A crate property no
  mapping here reads is not listed (#4046).
- The fitted record is then validated in-process with the LinkML check the
  script runs on the file it writes (`record_validator`). Each value the
  validator rejects is left out and named in `dropped` with the
  validator's message, and the record is validated again, until it passes
  (#4098). So every record `convert` returns validates, and every value of
  what it reads that the record does not hold is named in `dropped`. That
  holds whatever the per-slot rules miss. A record with an error that no
  value left out can fix, such as a missing `id`, is an error, not a
  record; there is no other limit (#4126).
- LinkML validation of output D4D
"""

import json
import re
import sys
import yaml
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from data_sheets_schema.resources import resource_path
from data_sheets_schema.rocrate_map import (
    DOI_SLOT,
    FULL_SCHEMA,
    TARGET_CLASS,
    _coerce,
    _normalize_datetime,
    _preview,
    _to_object,
    _type_matches,
    doi_for_slot,
)
from data_sheets_schema.schema_view import shared_view
from data_sheets_schema.scope import _norm, bare_doi

# Add fairscape_models to path
fairscape_path = Path(__file__).parent.parent.parent / 'fairscape_models'
if fairscape_path.exists() and str(fairscape_path) not in sys.path:
    sys.path.insert(0, str(fairscape_path))

try:
    from fairscape_models.rocrate import ROCrateV1_2
    FAIRSCAPE_AVAILABLE = True
except ImportError:
    FAIRSCAPE_AVAILABLE = False
    print("Warning: FAIRSCAPE models not available")


#: An ARK in the shape `grounding` matches, without a resolver: the `ark:`
#: label, an optional `/`, a NAAN of five to nine digits, `/` and the name.
ARK = re.compile(r"^ark:/?\d{5,9}/\S+$", re.IGNORECASE)

#: The global resolver the ARK specification names.
N2T_RESOLVER = "https://n2t.net/"


#: The ranges whose values are identifiers, where `_shape` writes an ARK as
#: its resolver URL (#4074).
IDENTIFIER_RANGES = ("uri", "uriorcurie")

#: The Dataset slots that hold other datasets, each with the one crate
#: property it takes them from and what of that property it takes: the
#: root's `hasPart` members the crate types as datasets (`_parts`), and the
#: references under its `isPartOf` (`_references`). `_build_d4d` records in
#: `dropped` a value any other property maps to one of these slots, such
#: as an `additionalProperty` named "Resources" or "Parent Datasets"
#: (#4073, #4138), and `_fit` a key of either name inside a reference, or
#: in any other nested Dataset, which is neither property (#4153).
DATASET_SLOTS = {
    'resources': ('hasPart', "a hasPart member the crate types as a dataset"),
    'parent_datasets': ('isPartOf', "a reference under the root's `isPartOf`"),
}

#: What a file collection is made from: each property of a `hasPart`
#: member's `@graph` entity that `_build_file_collections` reads, with the
#: FileCollection slot it fills, in the order the collection is written.
#: Both sizes fill `total_bytes`, from a byte count only, and
#: `evi:totalContentSizeBytes` first (#4074). Each value read is kept in
#: the file collection or recorded in `dropped`, so a `hasPart` reference
#: that states one of these as the entity does says nothing more, and any
#: other key it states is recorded (`_keys_not_taken`, #4159).
FILE_COLLECTION_SLOTS = {
    'name': 'name',
    'description': 'description',
    'evi:totalContentSizeBytes': 'total_bytes',
    'contentSize': 'total_bytes',
    'contentUrl': 'path',
    'fileFormat': 'compression',
    # Single-valued in the schema: `_fit` unwraps a one-item list and keeps
    # the first FileCollectionTypeEnum value of a longer one, recording
    # every other value in `dropped`.
    'd4d:collectionType': 'collection_type',
    'd4d:fileCount': 'file_count',
}

#: The `@id` RO-Crate gives the metadata descriptor: `ro-crate-metadata.json`
#: from 1.1, `ro-crate-metadata.jsonld` in 1.0.
DESCRIPTOR_IDS = ("ro-crate-metadata.json", "ro-crate-metadata.jsonld")

#: A size stated as a whole number of bytes: `2048`, `2,048`, `2048 B`,
#: `2048 bytes`, `2,048 BYTES`. The digits may be grouped in threes by
#: commas (#4098). A lower-case `b` alone names a bit, and is not read.
BYTE_COUNT = re.compile(r"^\s*(\d{1,3}(?:,\d{3})+|\d+)\s*(?:B|(?i:bytes?))?\s*$")

#: A size stated in a 1024-based (IEC) unit: `2 GiB`, `2048 KiB` (#4098).
IEC_SIZE = re.compile(
    r"^\s*\d[\d,]*(?:\.\d+)?\s*"
    r"(?i:[KMGTPEZY]iB|(?:kibi|mebi|gibi|tebi|pebi|exbi|zebi|yobi)bytes?)\s*$")

#: A size stated in a unit that can be 1000- or 1024-based: `19.1 TB`,
#: `441.2 GB`, `19.1 tb`, `3 gigabytes`. Text in any other unit is not a
#: size with a unit here, and is reported as not a byte count (#4098).
SIZE_WITH_UNIT = re.compile(
    r"^\s*\d[\d,]*(?:\.\d+)?\s*"
    r"(?i:[KMGTPEZY]B|(?:kilo|mega|giga|tera|peta|exa|zetta|yotta)bytes?)\s*$")

#: What `_normalize_datetime` makes of a calendar date.
MIDNIGHT = re.compile(r"^(\d{4}-\d{2}-\d{2})T00:00:00Z$")

#: A value written as a date, whole or partial, and not as prose: `2022`,
#: `2022-09`, `2022-09-01`, an ISO date-time, `9/1/2022` (#4073).
DATE_WRITTEN = re.compile(
    r"^\s*(?:\d{4}(?:-\d{2}(?:-\d{2}(?:T\S+)?)?)?|\d{1,2}/\d{1,2}/\d{2,4})\s*$")


def resolvable_id(value: Any) -> Any:
    """An ARK as its n2t.net resolver URL; any other value as written (#3969).

    The schema's prefixes declare no `ark`, so `ark:59853/x` expands to
    nothing under them and `identifiers.classify` can only call it
    `uri_unverified`. `https://n2t.net/ark:59853/x` is an absolute IRI at
    the resolver the ARK specification names, which needs no declared
    prefix (`uri`). The ARK is kept as written after the resolver. A value
    already in a resolver's form, or one that is not an ARK, is left as it
    is.
    """
    if isinstance(value, str) and ARK.match(value.strip()):
        return N2T_RESOLVER + value.strip()
    return value


def _plain(value: Any) -> Any:
    """`value` with every mapping key a plain `str`.

    `rocrate_map._coerce` can key an object by a slot's name, a str subclass
    that `yaml.dump` (which `fairscape-cli rocrate-to-d4d` uses) writes as a
    python object tag rather than as the name.
    """
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _as_list(value: Any) -> List[Any]:
    """`value` as a list: JSON-LD writes one item as itself, not a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _ref_id(value: Any) -> Optional[str]:
    """The `@id` a JSON-LD reference names, `{"@id": x}` or a bare `x`."""
    if isinstance(value, dict):
        value = value.get('@id')
    return value.strip() if isinstance(value, str) and value.strip() else None


def _types(entity: Dict[str, Any]) -> List[str]:
    """The entity's `@type`, as a list of strings."""
    return [str(t) for t in _as_list(entity.get('@type')) if t]


def _is_scalar(value: Any) -> bool:
    """Text, a number or a boolean: not an object, a reference or a list."""
    return isinstance(value, (str, int, float, bool))


def _is_text(value: Any) -> bool:
    """Text or a number, which `_shape` may join into one text."""
    return isinstance(value, (str, int, float)) and not isinstance(value, bool)


def _not_scalar(items: List[Any]) -> str:
    """What `items`, none of them text, a number or a boolean, are, as a
    reason names them. A list among the items of a crate's list is a list
    inside a list, not a crate reference or object (#4175)."""
    return ' and '.join(dict.fromkeys(
        'a list inside a list' if isinstance(item, list)
        else 'a crate reference or object' for item in items))


def _same(a: Any, b: Any) -> bool:
    """Whether `a` and `b` are one JSON value (#4159).

    Python's `==` takes `True` for `1` and `False` for `0`, inside lists
    and objects too, where JSON keeps a boolean apart from a number. So a
    boolean is the same only as a boolean. Numbers compare by value, so
    `1` and `1.0` are one number. Two objects have the same keys, as sets,
    and the same value under each; two lists the same values in the same
    places. Every comparison that keeps one of two values as a repeat of
    the other uses this.

    The pairs still to compare wait on a list, not on Python's call stack,
    so a value nested however deep is compared (#4167). Written as a
    recursion, this raised `RecursionError` on a value nested 600 levels
    deep that two properties stated alike, and the conversion ended; the
    `==` it replaced compared that value. A pair of objects or lists is
    opened once. In a value read from JSON no pair comes twice, and in a
    Python value a pair that comes again has its contents on the list or
    compared already, so skipping it changes no answer. It ends the
    comparison of a value that holds itself, which would otherwise go
    round for ever.
    """
    pairs: List[Tuple[Any, Any]] = [(a, b)]
    opened = set()
    while pairs:
        a, b = pairs.pop()
        if isinstance(a, bool) or isinstance(b, bool):
            if not (isinstance(a, bool) and isinstance(b, bool) and a == b):
                return False
        elif isinstance(a, dict) and isinstance(b, dict):
            if a.keys() != b.keys():
                return False
            if (id(a), id(b)) not in opened:
                opened.add((id(a), id(b)))
                pairs.extend((a[key], b[key]) for key in a)
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                return False
            if (id(a), id(b)) not in opened:
                opened.add((id(a), id(b)))
                pairs.extend(zip(a, b))
        elif not a == b:
            return False
    return True


def _among(value: Any, values: List[Any]) -> bool:
    """Whether `value` is one of `values`, as JSON reads them (`_same`)."""
    return any(_same(value, other) for other in values)


def _distinct(values: List[Any]) -> List[Any]:
    """`values` in order, each once, as JSON reads them (`_same`)."""
    kept: List[Any] = []
    for value in values:
        if not _among(value, kept):
            kept.append(value)
    return kept


def is_rocrate(entity: Dict[str, Any]) -> bool:
    """ROCrate-typed, by the test `rocrate_map.crate_root` applies."""
    return any('ROCrate' in t for t in _types(entity))


def is_dataset(entity: Dict[str, Any]) -> bool:
    """Typed as a dataset (#4074).

    `Dataset`, or a type IRI ending in it, which `rocrate_map._type_matches`
    reads `https://w3id.org/EVI#Dataset` as; or an RO-Crate, which is a
    dataset of its own.
    """
    return _type_matches(entity, 'Dataset') or is_rocrate(entity)


def root_data_entity(graph: List[Any]) -> Optional[Dict[str, Any]]:
    """The crate's root data entity, by the RO-Crate rule (#4072).

    1. The entity the metadata descriptor (`ro-crate-metadata.json`) names
       in `about`. That is how RO-Crate defines the root.
    2. Otherwise the entity whose `@id` is `./`.
    3. Otherwise the first ROCrate-typed entity, which is the one
       `rocrate_map.crate_root` and FAIRSCAPE's
       `ROCrateV1_2.getCrateMetadata` return.

    A FAIRSCAPE release crate lists its sub-crates in the same `@graph`,
    each typed ROCrate like the release itself. Taking the last such
    entity, as this converter did, described a sub-crate as the release.
    """
    entities = [entity for entity in graph if isinstance(entity, dict)]
    by_id: Dict[str, Dict[str, Any]] = {}
    for entity in entities:
        if isinstance(entity.get('@id'), str):
            by_id.setdefault(entity['@id'], entity)
    # The `@id` itself, not its last path segment: a release crate can list
    # a sub-crate's `<dir>/ro-crate-metadata.json` as a file of its own.
    descriptor = next((by_id[name] for name in DESCRIPTOR_IDS if name in by_id),
                      None)
    if descriptor is not None:
        root = by_id.get(_ref_id(descriptor.get('about')))
        if root is not None and root is not descriptor:
            return root
    if './' in by_id:
        return by_id['./']
    return next((entity for entity in entities if is_rocrate(entity)), None)


def exact_bytes(value: Any) -> Tuple[Optional[int], str]:
    """`value` as a whole number of bytes, or None and the reason (#4074).

    An integer is a byte count, and so is text of digits alone or followed
    by `B` or `bytes` in any case, the digits grouped in threes by commas
    or not (`2,048 bytes`, #4098). A size in a unit (`19.1 TB`, `2 GiB`)
    is not converted. It is given to the precision its digits show, which
    can be rounded, so a number made from it could present an approximate
    size as an exact count. A unit such as `TB` also does not say whether
    it is 1000- or 1024-based; a 1024-based (IEC) unit such as `GiB` does,
    and its reason does not claim otherwise (#4098). The interface mapping
    (d4d_rocrate_interface_mapping.tsv) takes `Dataset.total_size_bytes`
    from `evi:totalContentSizeBytes` and not from `contentSize` for this
    reason. Any other value is not a byte count.

    Digits too many for Python to read as one integer are not read: CPython
    raises past `sys.get_int_max_str_digits()`, 4300 by default. Until
    #4159 that `ValueError` ended the conversion, though the crate could
    hold a byte count the record could take instead.
    """
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value, ''
    if isinstance(value, str):
        count = BYTE_COUNT.match(value)
        if count:
            digits = count.group(1).replace(',', '')
            try:
                return int(digits), ''
            except ValueError:
                return None, (
                    f"{_preview(value)} is {len(digits)} digits long, more "
                    "than Python reads as one integer, so it is not read as "
                    "a byte count")
        why = ("so a number made from it could give an approximate size as an "
               "exact one (the interface mapping takes "
               "Dataset.total_size_bytes from evi:totalContentSizeBytes for "
               "this reason)")
        if IEC_SIZE.match(value):
            return None, (
                f"{value!r} is a size with a 1024-based unit, not a byte "
                f"count: it is given to the precision its digits show, {why}")
        if SIZE_WITH_UNIT.match(value):
            return None, (
                f"{value!r} is a size with a unit, not a byte count: it is "
                "given to the precision its digits show, and the crate does "
                "not state whether the unit is 1000- or 1024-based, " + why)
    return None, f"{_preview(value)} is not a byte count"


@lru_cache(maxsize=None)
def record_validator(schema: str):
    """The LinkML validator `linkml.validator.validate` builds for `schema`.

    It checks a record against the JSON Schema LinkML generates for a closed
    Dataset: a key its class does not declare is an error, and so is a value
    of the wrong type, format, pattern or enum, or an object that lacks a
    required key. LinkML closes every nested class itself; `closed=True`
    closes the record's own top level too. Formats are jsonschema's checks,
    and its `date-time` check needs `rfc3339-validator`, which the lock
    file installs. `_settle` runs it on every record `convert` returns, and
    `_validate_d4d` on the record the script writes (#4098). It is built
    once per schema, because generating that JSON Schema takes seconds.
    """
    from linkml.validator import Validator
    from linkml.validator.plugins import JsonschemaValidationPlugin
    return Validator(schema,
                     validation_plugins=[JsonschemaValidationPlugin(closed=True)])


def _at(record: Any, path: Tuple[Any, ...]) -> Any:
    """The value at `path` in `record`."""
    for part in path:
        record = record[part]
    return record


def _position(record: Any, path: Tuple[Any, ...]) -> Tuple[int, ...]:
    """Where `path` falls in `record`, in the order the record is written."""
    place = []
    for part in path:
        place.append(list(record).index(part) if isinstance(record, dict)
                     else part)
        record = record[part]
    return tuple(place)


#: What `_causes` gives for each value to leave out: the value's path in
#: the record, the path of the error about it, and the validator's message.
Cause = Tuple[Tuple[Any, ...], Tuple[Any, ...], str]


def _causes(error: Any) -> List[Cause]:
    """The values one jsonschema error says to leave out (#4098, #4125).

    An error points at a value, and that value goes: one of the wrong
    type, format, pattern or enum goes alone, and an object that lacks a
    required key goes whole. An `additionalProperties` error points at the
    object, and the keys its class does not declare go by name.

    An `anyOf` error is about a whole value, and the errors each branch
    found are its context. LinkML writes `anyOf` where a slot may hold
    either of two classes, as an item of `parent_datasets` or `resources`
    may be a Dataset or a DataSubset, and where a single-valued slot may
    hold its class or nothing (`human_subject_research`, `updates`). Each
    branch's errors say what would make the value valid under it, so the
    branch that leaves out the fewest values is taken, the earlier of two
    that leave out as many. LinkML writes the slot's own class first. The
    values that branch rejects go, each alone. A branch that rejects the
    value itself, as the branch of nothing (`{"type": "null"}`) rejects
    any object, leaves it out whole, and the value goes whole only when
    every branch does, for the reasons the first branch, the slot's own
    class, gives.

    LinkML reports the `best_match` of each error, which does not find the
    value at fault here. It stops at the `anyOf` error when the two
    branches report the same error, so a reference went whole for one key
    of the wrong type, and otherwise it descends to one error, so an object
    slot lost one wrong value a pass (#4125, #4126).
    """
    here = tuple(error.absolute_path)
    if error.validator == 'anyOf' and error.context:
        branches: Dict[int, List[Any]] = {}
        for sub in error.context:
            branches.setdefault(sub.relative_schema_path[0], []).append(sub)
        options = [[cause for sub in branches[n] for cause in _causes(sub)]
                   for n in sorted(branches)]
        parts = [causes for causes in options
                 if all(value != here for value, _, _ in causes)]
        if parts:
            return min(parts, key=lambda causes: len({value for value, _, _ in causes}))
        return options[0]
    if (error.validator == 'additionalProperties'
            and isinstance(error.instance, dict)
            and isinstance(error.schema, dict)):
        declared = error.schema.get('properties', {})
        patterns = error.schema.get('patternProperties', {})
        keys = [key for key in error.instance if key not in declared
                and not any(re.search(p, key) for p in patterns)]
        if keys:
            return [(here + (key,), here, error.message) for key in keys]
    return [(here, here, error.message)]


def _rejected(results: List[Any]
              ) -> Dict[Tuple[Any, ...], List[Tuple[Tuple[Any, ...], str]]]:
    """The values to leave out of a record the validator rejects, each
    path with the errors about it, as (the error's path, its message)
    (#4098).

    LinkML reports one result for each error the JSON Schema check finds,
    and its `source` is that error's `best_match`, which is not always the
    value at fault. So the error it came from is read whole (`_causes`,
    #4125).
    A value inside one that goes, goes with it, and its errors are given
    with that value's. An error that points at the record itself names
    nothing that can be left out, so the record cannot be made valid this
    way, and that is a ValueError.
    """
    found: Dict[Tuple[Any, ...], List[Tuple[Tuple[Any, ...], str]]] = {}
    read: List[Any] = []
    for result in results:
        error = result.source
        if error is None:
            raise ValueError(f"a validation error with no location: {result.message}")
        while error.parent is not None:
            error = error.parent
        if any(error is other for other in read):
            continue
        read.append(error)
        for value, at, message in _causes(error):
            if not value:
                raise ValueError(
                    "the record cannot be made valid by leaving values out: "
                    f"{message}")
            errors = found.setdefault(value, [])
            if (at, message) not in errors:
                errors.append((at, message))
    outer: Dict[Tuple[Any, ...], List[Tuple[Tuple[Any, ...], str]]] = {}
    for path in sorted(found, key=len):
        holder = next((path[:n] for n in range(1, len(path))
                       if path[:n] in outer), None)
        if holder is None:
            outer[path] = list(found[path])
        else:
            outer[holder] += [e for e in found[path] if e not in outer[holder]]
    return outer


def _calendar_date(value: Any) -> Tuple[Optional[str], str]:
    """The `YYYY-MM-DD` date in `value`, or None and the reason (#4073).

    Dates are read by the static-map arm's rule
    (`rocrate_map._normalize_datetime`). It refuses `9/1/2022`, where
    either number could be the month, rather than guess. That rule widens
    a date to a date-time, which a `date` slot does not accept, so the date
    part is kept.
    """
    widened, note = _normalize_datetime(value)
    if widened is None:
        return None, note
    date = MIDNIGHT.match(widened) if isinstance(widened, str) else None
    if date is None:
        return None, f"not a calendar date: {_preview(value)}"
    return date.group(1), ''


class FairscapeToD4DConverter:
    """Convert FAIRSCAPE RO-Crate to D4D YAML."""

    # Until #3884 the constructor took an SSSOM table (`--sssom`, defaulting
    # to the retired d4d_rocrate_sssom_mapping.tsv) and loaded it into an
    # attribute nothing read: the output was identical with it, with another
    # table and with none, apart from the `generated_date` timestamp each run
    # then stamped (#3969 removed the stamp). The field mapping is the code
    # below.

    def __init__(self):
        #: What the last `convert` read but could not place, as (source,
        #: reason) pairs: a whole value, or the part of one its slot could
        #: not hold (#3969, #4073). The source is the crate property, or the
        #: path inside an object this converter built. The reason names the
        #: slot, so a value one slot could not hold may still be in another:
        #: an `identifier` written as the `id` is not a DOI for `doi`.
        #:
        #: A path numbers the items of a list the crate's way (#4126): an
        #: object is named by its position in the list the converter read
        #: for that slot, before any item was shaped or left out, so
        #: `creators[1]` is the object made from the crate's second
        #: `author`. That is the one numbering every item has, an item that
        #: yields no object and one validation leaves out included, and no
        #: validation pass changes it. Where the converter makes the list
        #: itself, the position is in that list: the names in an author
        #: text, the one timeframe a start and an end date make, the file
        #: collections in `@graph` order, and, for a slot two properties
        #: fill, the items of the property read first, then those of the
        #: other that are not among them (`_place`). A text or a number in
        #: a list is named by its value in the reason, not by a position.
        self.dropped: List[Tuple[str, str]] = []
        self._view = None
        self._slots: Dict[str, Dict[str, Any]] = {}
        self._minted: Dict[str, int] = {}
        #: The `@graph`'s entities by `@id`, the first of any that share one,
        #: and the root's parts written as file collections, by `@id`, each
        #: with the entity its file collection is made from, for `_parts`.
        self._described: Dict[str, Dict[str, Any]] = {}
        self._collected: Dict[str, Dict[str, Any]] = {}
        #: Each object `_shape_objects` built for a list, by `id()`, with
        #: its position in the list it was read from, for `_named`. The
        #: object is kept with it, so no other object can take its `id()`
        #: while the entry is here, as one could once it was left out.
        self._read_at: Dict[int, Tuple[Dict[str, Any], int]] = {}
        #: `dropped` entries for a value a top-level single-valued slot did
        #: not take, by index, with the slot: once the record is valid,
        #: `_settle` says which value the slot holds instead (#4125).
        self._instead: List[Tuple[int, str]] = []

    def convert(self, rocrate_input: Any) -> Dict[str, Any]:
        """
        Convert FAIRSCAPE RO-Crate to D4D dictionary.

        Args:
            rocrate_input: FAIRSCAPE RO-Crate (dict, Path, or ROCrateV1_2)

        Returns:
            D4D dictionary, which the schema accepts as a Dataset (#4098)

        Raises:
            ValueError: the input is not a crate this reads (a type it does
                not take, or a file Python cannot read as JSON, such as one
                holding a number of more digits than Python reads as one
                integer); the crate has no root data entity; or the record
                has an error no value left out can fix, such as a missing
                `id` (`_settle`). A byte count written as text, however
                long, is recorded in `dropped` instead (#4159).
        """
        self.dropped = []
        self._minted = {}
        self._read_at = {}
        self._instead = []

        # Load RO-Crate data
        if isinstance(rocrate_input, dict):
            rocrate_data = rocrate_input
        elif isinstance(rocrate_input, (str, Path)):
            with open(rocrate_input) as f:
                rocrate_data = json.load(f)
        elif FAIRSCAPE_AVAILABLE and isinstance(rocrate_input, ROCrateV1_2):
            rocrate_data = rocrate_input.model_dump(by_alias=True, exclude_none=True)
        else:
            raise ValueError(f"Unsupported input type: {type(rocrate_input)}")

        # Validate with Pydantic if available
        if FAIRSCAPE_AVAILABLE and isinstance(rocrate_data, dict):
            try:
                rocrate_model = ROCrateV1_2(**rocrate_data)
                print("✓ Input RO-Crate validated with FAIRSCAPE Pydantic models")
            except Exception as e:
                print(f"⚠ Warning: RO-Crate validation failed: {e}")

        # The crate's root data entity, and the datasets its hasPart names
        dataset, nested_datasets = self._extract_datasets(rocrate_data)

        if not dataset:
            raise ValueError(
                "No root data entity in the RO-Crate `@graph`: the metadata "
                "descriptor's `about` names no entity in it, no entity has "
                "`@id` './', and none is typed ROCrate")

        # Convert to D4D
        d4d_dict = self._build_d4d(dataset, nested_datasets, rocrate_data)

        return d4d_dict

    def _extract_datasets(self, rocrate_data: Dict) -> Tuple[Optional[Dict], List[Dict]]:
        """The crate's root data entity and the datasets its `hasPart` names.

        The root is the one the RO-Crate rule picks (`root_data_entity`),
        and every value in the record is read from it (#4072). It used to
        be the last entity typed `Dataset` whose `@id` was `./` or that was
        typed EVI#ROCrate. In a FAIRSCAPE release crate, which lists its
        sub-crates in the same `@graph` and types them ROCrate too, that
        was a sub-crate, so the release was described by one of its parts.
        Each sub-crate's `hasPart` was also collected, so the record listed
        itself among its own file collections. A root typed only
        `https://w3id.org/EVI#Dataset` (CHORUS, VOICE) was not found at all.

        A nested dataset is an entity of the `@graph` that the root's
        `hasPart` names and that is typed as a dataset (`is_dataset`), in
        `@graph` order. Of the nodes that share an `@id`, the first typed
        as a dataset is taken, and its `hasPart` reference is compared with
        that node (`_keys_not_taken`, #4167). The parts of a sub-crate are
        that sub-crate's, not the root's.

        Returns:
            Tuple of (root, nested_datasets_list)
        """
        graph = [entity for entity in rocrate_data.get('@graph', [])
                 if isinstance(entity, dict)]
        root = root_data_entity(graph)
        if root is None:
            return None, []

        part_ids = {_ref_id(part) for part in _as_list(root.get('hasPart'))}
        part_ids.discard(None)
        nested_datasets, seen = [], set()
        for entity in graph:
            entity_id = entity.get('@id')
            if (entity is not root and entity_id in part_ids
                    and entity_id != root.get('@id') and entity_id not in seen
                    and is_dataset(entity)):
                nested_datasets.append(entity)
                seen.add(entity_id)

        return root, nested_datasets

    def _build_d4d(self, dataset: Dict, nested_datasets: List[Dict], full_rocrate: Dict) -> Dict[str, Any]:
        """
        Build D4D dictionary from RO-Crate Dataset entity.

        The mappings name the D4D slot each crate property goes to. The
        record is then fitted to the schema's Dataset class (`_fit`), so it
        carries only keys the class declares, each shaped to its slot's
        range; what cannot be placed is recorded in `dropped` (#3969).
        Last, it is validated, and each value the schema rejects is left
        out and recorded in `dropped` with the validator's message, until
        it validates (`_settle`, #4098). The record no longer carries the
        converter's own `schema_version`, `generated_date` and `source`
        stamps, which are not D4D slots.

        Args:
            dataset: Main Dataset entity
            nested_datasets: Nested Dataset entities (FileCollections)
            full_rocrate: Full RO-Crate data

        Returns:
            D4D dictionary
        """
        d4d: Dict[str, Any] = {}
        # slot -> the crate property it was filled from, for `dropped`
        origin: Dict[str, str] = {}
        # single-valued slot -> the other (crate property, value) pairs that
        # map to it, in the order the slot takes them (`_place`)
        rivals: Dict[str, List[Tuple[str, Any]]] = {}
        self._described = {}
        for entity in full_rocrate.get('@graph', []):
            if isinstance(entity, dict) and isinstance(entity.get('@id'), str):
                self._described.setdefault(entity['@id'], entity)
        # A hasPart member converted to a FileCollection is not repeated
        # under resources, and its reference is compared with the entity
        # the file collection is made from (`_parts`). Where two `@graph`
        # nodes share its `@id`, that is the one `_extract_datasets`
        # selected, which need not be the first, the one `_described`
        # holds (#4167).
        self._collected = {entity.get('@id'): entity
                           for entity in nested_datasets}

        record_id, id_source = self._record_id(dataset)
        if record_id:
            d4d['id'] = record_id
            origin['id'] = id_source

        # Convert nested Datasets to FileCollections
        file_collections = (self._build_file_collections(nested_datasets)
                            if nested_datasets else [])
        if file_collections:
            d4d['file_collections'] = file_collections
            origin['file_collections'] = 'hasPart'

        # Read in this order. A single-valued slot holds the first value it
        # can hold, in the order `_place` puts its values: a dedicated
        # property before an `additionalProperty` entry, whichever is read
        # first, and otherwise the later mapping first (#4139). So
        # `license`, read before the `additionalProperty` entries, still
        # comes before an entry named "License".
        for prop, slot, value in (self._map_basic_properties(dataset)
                                  + self._map_complex_properties(dataset)
                                  # EVI properties (computational provenance)
                                  + self._map_evi_properties(dataset)
                                  # RAI properties (responsible AI)
                                  + self._map_rai_properties(dataset)
                                  # custom D4D properties
                                  + self._map_d4d_properties(dataset)):
            only = DATASET_SLOTS.get(slot)
            if only is not None and prop != only[0]:
                # `resources` and `parent_datasets` hold other datasets,
                # which the crate names by reference under `hasPart` and
                # `isPartOf`. An additionalProperty named "Resources" or
                # "Parent Datasets" is a name and a value, not one of those
                # references. In `resources`, an item that was not a
                # mapping crashed the conversion (#4073). In
                # `parent_datasets`, text became a parent whose `id`
                # `_to_object` minted, asserting a dataset the crate does
                # not identify, with nothing recorded (#4138); `_references`
                # records `isPartOf` text for the same reason (#4125).
                self._not_a_dataset_slot_value(prop, slot, value)
                continue
            self._place(d4d, origin, rivals, slot, value, prop)

        fitted = self._fit(d4d, TARGET_CLASS, origin, rivals=rivals)
        return self._settle(fitted, origin, rivals)

    def _not_a_dataset_slot_value(self, source: str, slot: str,
                                  value: Any) -> None:
        """Record in `dropped` that `slot`, one of `DATASET_SLOTS`, does not
        take `value`, which `source` gives it: no `id` is minted for it, as
        `_to_object` would mint one for text (#4138, #4153). An empty value
        is not recorded; `_place` and `_take` place none either."""
        if value not in (None, '', [], {}):
            self.dropped.append((source, (
                f"not placed in `{slot}`: {_preview(value)} is not "
                f"{DATASET_SLOTS[slot][1]}, which is all `{slot}` holds")))

    def _record_id(self, dataset: Dict) -> Tuple[Optional[str], Optional[str]]:
        """The record's required `id` and the crate property it came from.

        The root's `identifier`, else its `@id` (#3969), the rule
        `rocrate_map.map_crate` applies to the root it picks. It is never a
        minted value, so the record points back at the crate it came from.
        A DOI is written as the `doi:` CURIE (#974). Where the root's
        `identifier` is text, both converters name the same identifier,
        apart from the form of an ARK: this converter writes it as its
        n2t.net resolver URL, where `map_crate` keeps it as written. A list
        gives its first text item, where `map_crate` takes its first item,
        and its other items are recorded in `dropped` (#4073).

        An `identifier` that holds no text, such as a reference
        (`{"@id": …}`), an object, a number or blank text, is recorded in
        `dropped`, and the root's `@id` is the record's `id`. `map_crate`
        writes such a value as `str()` gives it, or for `[""]` writes no
        `id` (#4100). A root whose only identifier is an attached crate's
        `./` gives `./`, which is all such a crate supplies.
        """
        for source in ('identifier', '@id'):
            items = [item for item in _as_list(dataset.get(source))
                     if item not in (None, '', [], {})]
            first = next((item for item in items
                          if isinstance(item, str) and item.strip()), None)
            if first is None:
                if items:
                    self.dropped.append((source, (
                        f"not placed in `id`: {_preview(items)} holds no "
                        "identifier written as text")))
                continue
            kept = items.index(first)
            rest = [item for n, item in enumerate(items)
                    if n != kept and not _same(item, first)]
            if rest:
                self.dropped.append((source, (
                    f"part of the value not placed in `id`: {_preview(rest)} "
                    f"(the record's `id` holds one identifier, {first!r}, "
                    f"the first of {len(items)} list items)")))
            doi = bare_doi(first)
            return (f"doi:{doi}" if doi else resolvable_id(first.strip())), source
        return None, None

    def _place(self, d4d: Dict[str, Any], origin: Dict[str, str],
               rivals: Dict[str, List[Tuple[str, Any]]],
               slot: str, value: Any, prop: str) -> None:
        """Put `value`, read from crate property `prop`, in `slot`.

        Two crate properties can map to one slot: an `additionalProperty`
        entry and the property it duplicates, or the FAIRSCAPE spelling of
        a key and the one this repo's d4d_to_fairscape.py writes. A
        multivalued slot keeps each distinct value of both, so neither is
        chosen over the other.

        A single-valued slot holds one value. Its values are put in order
        here, and which one it holds is decided only once they are shaped
        (`_fit`) and validated (`_settle`): the first in that order that
        its slot can hold, the others recorded as dropped (#4098). Until
        #4098 the first was chosen here, on the crate's values, so a value
        that could not be shaped left the slot empty, and the usable value
        behind it was recorded as superseded by it. The order puts a
        dedicated property before an `additionalProperty` entry, which is
        FAIRSCAPE's own precedence (its datasheet mapping reads each
        dedicated key first and falls back to the `additionalProperty`
        entry), and otherwise the later mapping first. `d4d[slot]` holds
        the first value and `rivals[slot]` the rest.

        A value two properties state alike is kept once, as JSON reads
        them (`_same`, #4159): `true` is not `1`, and `1` and `1.0` are one
        number. Python's `==` took a dedicated `true` for an
        `additionalProperty` entry's `1`, and dropped it as a repeat; the
        schema then rejected the `1`, and the slot ended empty. A repeat
        takes the higher of the two places in the order. Until #4159 it was
        dropped wherever it ranked, so `evi:totalContentSizeBytes` stating
        what an `additionalProperty` entry stated ranked behind a
        `contentSize` it supersedes, and the slot held that `contentSize`.
        """
        if value in (None, '', [], {}):
            return
        if slot not in d4d:
            d4d[slot], origin[slot] = value, prop
            return
        held = d4d[slot]
        if _same(held, value):
            return
        declared = self._class_slots(TARGET_CLASS).get(slot)
        if declared is not None and declared.multivalued:
            items = list(held) if isinstance(held, list) else [held]
            for item in (value if isinstance(value, list) else [value]):
                if not _among(item, items):
                    items.append(item)
            d4d[slot], origin[slot] = items, f"{origin[slot]} + {prop}"
            return
        fallback = 'additionalProperty['
        order = [(origin[slot], held)] + rivals.get(slot, [])
        # The latest mapping goes before every value of its own kind, and a
        # dedicated property before every additionalProperty entry
        at = next((n for n, (source, _) in enumerate(order)
                   if source.startswith(fallback)
                   or not prop.startswith(fallback)), len(order))
        same = next((n for n, (_, other) in enumerate(order)
                     if _same(value, other)), None)
        if same is not None:
            if same <= at:
                return
            del order[same]
        order.insert(at, (prop, value))
        (origin[slot], d4d[slot]), rivals[slot] = order[0], order[1:]

    def _schema_view(self):
        """The merged schema, read from any working directory (#1301)."""
        if self._view is None:
            self._view = shared_view(resource_path(FULL_SCHEMA))
        return self._view

    def _class_slots(self, cls: str) -> Dict[str, Any]:
        """The induced slots of `cls`, by name."""
        if cls not in self._slots:
            self._slots[cls] = {
                s.name: s for s in self._schema_view().class_induced_slots(cls)
            }
        return self._slots[cls]

    def _fit(self, obj: Dict[str, Any], cls: str, origin: Dict[str, str],
             where: str = '',
             rivals: Optional[Dict[str, List[Tuple[str, Any]]]] = None
             ) -> Dict[str, Any]:
        """`obj` with only the keys `cls` declares, each value shaped to its
        slot by `_shape`.

        A key the class does not declare, a value `_shape` cannot fit to
        its slot, and each part of a value its slot cannot hold are left
        out and recorded in `dropped` (#3969, #4073). `where` is the path of
        a nested object, which names what was dropped from it. `rivals`
        holds, for a single-valued slot that two crate properties fill, the
        values after the one `obj` holds (`_place`): the slot takes the
        first of them it can hold (`_take`), and the rest wait for
        `_settle`.

        In a nested object, a key that names a slot holding datasets
        (`DATASET_SLOTS`) is recorded too, text and references alike, where
        the slot ranges over Dataset: in a Dataset, such as an `isPartOf` or
        `hasPart` reference, and in a DataSubset. Those slots take only the
        root's `isPartOf` and `hasPart`, and a key inside a nested object is
        neither. Its text became a dataset whose `id` `_to_object` minted,
        with nothing recorded (#4153). A FileCollection's `resources` holds
        Files, and is fitted like any other slot.
        """
        slots = self._class_slots(cls)
        fitted: Dict[str, Any] = {}
        for key, value in obj.items():
            source = origin.get(key) or f"{where}{key}"
            waiting = rivals.pop(key, []) if rivals is not None else []
            slot = slots.get(key)
            if slot is None:
                for each, _ in [(source, value)] + waiting:
                    self.dropped.append(
                        (each, f"the schema declares no `{key}` slot on {cls}"))
                continue
            if where and key in DATASET_SLOTS and slot.range == 'Dataset':
                self._not_a_dataset_slot_value(source, key, value)
                continue
            self._take(fitted, origin, key, slot, [(source, value)] + waiting,
                       where, rivals)
        return fitted

    def _take(self, record: Dict[str, Any], origin: Dict[str, str], key: str,
              slot: Any, candidates: List[Tuple[str, Any]], where: str,
              rivals: Optional[Dict[str, List[Tuple[str, Any]]]]) -> bool:
        """Put in `record[key]` the first of `candidates`, (crate property,
        value) pairs, that `_shape` can fit to `slot` (#4098).

        Each candidate that cannot be shaped is recorded in `dropped` with
        the reason. For a top-level slot, `_settle` adds to that entry which
        value the slot holds instead, once the record is valid, and only if
        the slot then holds one: the schema may yet reject the value placed
        here, and every value after it (#4125). The candidates after the one
        placed wait in `rivals[key]`: `_settle` tries them if the schema
        rejects the value placed, and records the rest as superseded. Each
        part of a value its slot does not hold is recorded as before
        (#4073). False when no candidate fits.
        """
        while candidates:
            source, value = candidates.pop(0)
            if value in (None, '', [], {}):
                continue
            shaped, why, left = self._shape(value, slot, f"{where}{key}")
            for part, reason in left:
                self.dropped.append((source, (
                    f"part of the value not placed in `{key}`: "
                    f"{_preview(part)} ({reason})")))
            if shaped is None:
                self.dropped.append((source, f"not placed in `{key}`: {why}"))
                if rivals is not None:
                    self._instead.append((len(self.dropped) - 1, key))
                continue
            record[key], origin[key] = shaped, source
            if candidates and rivals is not None:
                rivals[key] = candidates
            return True
        return False

    def _say_instead(self, record: Dict[str, Any],
                     origin: Dict[str, str]) -> None:
        """Add to each `dropped` entry for a value a single-valued slot did
        not take which crate property's value the slot holds instead, from
        the record as `_settle` returns it (#4125).

        An entry for a slot that ends empty says nothing more: the values
        it might have held are each recorded as left out. Until #4125 the
        clause was written as soon as a value was placed, so it could name
        a value the schema then rejected, or a slot that ended empty.
        """
        for n, key in self._instead:
            if key in record:
                source, reason = self.dropped[n]
                self.dropped[n] = (source, f"{reason}; `{key}` holds the value "
                                           f"of {origin[key]} instead")
        self._instead = []

    def _settle(self, record: Dict[str, Any], origin: Dict[str, str],
                rivals: Dict[str, List[Tuple[str, Any]]]) -> Dict[str, Any]:
        """`record` once the schema accepts it (#4098).

        The record is validated with `record_validator`, the check the
        script runs on the file it writes. Each value the validator rejects
        is left out and recorded in `dropped` with the validator's message
        (`_rejected`, `_leave_out`), and the record is validated again. A
        single-valued slot left empty takes the next value waiting for it,
        if any can be shaped (`_take`). The per-slot rules in `_shape`
        already fit most values. This makes every value the schema still
        rejects a `dropped` entry: a date-time `_coerce` leaves as written
        (`11/17/25`), a count written as text, an object that lacks a
        required key.

        The passes end, and need no limit (#4126). Each one finds the
        record valid, or leaves out at least one value, or raises: an error
        that names no value to leave out (an `id` the record lacks) is a
        ValueError. A value left out does not come back, and a value
        waiting for a slot enters the record at most once, when the slot
        takes it. So there are no more passes than the values that enter
        the record, plus the one that finds it valid: the values it holds
        at the start and those each waiting value brings as `_shape` writes
        it, nested ones included in both (#4139). A waiting value can cost
        more than one pass. Once placed it is validated like any other
        value, and a value nested in it can be left out a pass before the
        object that then lacks it. When `human_subject_research` holds a
        value with a software whose `id` is not text, and five such values
        wait for it, there are 13 validations: two for each of the six
        values for the slot, and the one that finds the record valid.
        Until #4126 the passes stopped at 20. An object slot then lost one
        wrong value a pass, and a slot still tries its waiting values one a
        pass, so 21 of either made an error of a crate that leaving them
        out makes valid.

        Once the record is valid, the values still waiting for a slot that
        holds a value are recorded as superseded by it, and each entry for
        a value a slot did not take says which value it holds instead
        (`_say_instead`).
        """
        validator = record_validator(str(resource_path(FULL_SCHEMA)))
        order = list(record)
        while True:
            results = list(validator.iter_results(record, TARGET_CLASS))
            if not results:
                break
            entries = self._leave_out(record, origin, _rejected(results))
            for key in [key for key in rivals if key not in record]:
                self._instead += [(n, key) for n in entries.get(key, [])]
                self._take(record, origin, key,
                           self._class_slots(TARGET_CLASS)[key],
                           rivals.pop(key), '', rivals)
            record = {key: record[key]
                      for key in sorted(record, key=order.index)}
        for key, waiting in rivals.items():
            for source, _ in waiting:
                self.dropped.append((source, (
                    f"superseded by {origin[key]}, which also maps to `{key}`")))
        self._say_instead(record, origin)
        return record

    def _named(self, value: Any, path: Tuple[Any, ...]) -> str:
        """`path`, from `value` down, as `dropped` names it: `creators[1].name`.

        An object in a list is numbered by its position in the list it was
        read from (`_read_at`), not by where it now is in the record, which
        changes as earlier items are left out (#4126). An object this
        converter did not build keeps its place in the record. A text or a
        number in a list is not numbered: the reason quotes it.
        """
        text = ''
        for part in path:
            if isinstance(part, int):
                held = value[part]
                if isinstance(held, dict):
                    read = self._read_at.get(id(held))
                    text += f"[{read[1] if read else part}]"
            else:
                text += f".{part}" if text else str(part)
            value = value[part]
        return text

    def _leave_out(self, record: Dict[str, Any], origin: Dict[str, str],
                   rejected: Dict[Tuple[Any, ...],
                                  List[Tuple[Tuple[Any, ...], str]]]
                   ) -> Dict[str, List[int]]:
        """Move each value `rejected` names out of `record` and into
        `dropped`, with the validator's messages as the reason (#4098).

        A value of a top-level slot, or an item of one, is named by the
        crate property the slot was filled from, as `_fit` names it. A value
        inside an object is named by its path, as `_object` names it: an
        object in a list by its position in the list it was read from
        (`_named`), whichever pass leaves the value out (#4126).

        The reason gives jsonschema's message for each error. An error
        about a value inside the one left out says where, below it. LinkML
        adds a pointer into the record as that pass validated it, which
        numbers the items of a list otherwise, and is not repeated (#4126).

        An object or list left empty is removed, since the record writes no
        empty value, and holds nothing left to report. Returns the indexes
        of the `dropped` entries made, by top-level slot.
        """
        order = sorted(rejected, key=lambda path: _position(record, path))
        entries: Dict[str, List[int]] = {}
        for path in order:
            key = next(part for part in reversed(path) if isinstance(part, str))
            item = isinstance(path[-1], int)
            part = item and len(_at(record, path[:-1])) > 1
            if len(path) == 1 or (len(path) == 2 and item):
                source = origin.get(path[0]) or path[0]
            else:
                source = self._named(record, path[:-1] if item else path)
            value = _at(record, path)
            said = []
            for at, message in rejected[path]:
                below = self._named(value, at[len(path):])
                said.append(f"{message} in `{below}`" if below else message)
            self.dropped.append((source, (
                f"{'part of the value ' if part else ''}not placed in "
                f"`{key}`: {_preview(value)} (the schema rejects "
                f"it: {'; '.join(said)})")))
            entries.setdefault(path[0], []).append(len(self.dropped) - 1)
        # Last first, so no index a later deletion uses has moved
        for path in reversed(order):
            del _at(record, path[:-1])[path[-1]]
            path = path[:-1]
            while path and _at(record, path) in ({}, []):
                del _at(record, path[:-1])[path[-1]]
                path = path[:-1]
        return entries

    def _shape(self, value: Any, slot: Any,
               where: str) -> Tuple[Any, str, List[Tuple[Any, str]]]:
        """`(value, note, left)`: `value` shaped to `slot`'s range and
        cardinality, what was done to it, and each part of it the slot does
        not hold, with the reason (#4073). The value is None, with the
        reason, when no part of it can be shaped to the slot.

        A slot whose range is a class is filled by `_shape_objects`. Other
        values go through the static-map arm's coercion
        (`rocrate_map._coerce`): a DOI is the bare DOI, a date written
        `YYYY-MM-DD` or as an unambiguous slash date with a four-digit year
        is widened to the date-time a date-time slot takes, enum values are
        kept only where permitted, and a scalar is wrapped for a
        multivalued slot. `_coerce` leaves any other date-time text as
        written; the schema rejects it, and `_settle` leaves it out with
        the validator's message (#4098). A one-item list for a
        single-valued slot is unwrapped before `_coerce` reads it. Until
        #4109 that was a departure too: `_coerce` read a date before it
        unwrapped the list, so `["2026-06-30"]` stayed a date the date-time
        slot does not accept (#4098). `_coerce` now unwraps a one-item list
        of text before its date rule, and the two agree. This converter
        departs from `_coerce` in four places:

        - A reference or an object is not text, and a slot whose range is
          not a class does not hold it. `_coerce` would keep it as it is, or
          join its Python repr into one text.
        - A single-valued slot whose range is not text (an identifier, a
          number, a date) keeps the first item of a list, as `id` and an
          enum slot do. `_coerce` would join the items into a text that is
          none of them.
        - A `date` slot takes the calendar date (`_calendar_date`), where
          `_coerce` writes a date-time that the slot does not accept.
        - An ARK in a slot whose range is `uri` or `uriorcurie` is written
          as its resolver URL (`resolvable_id`).

        Whatever part of the value `_coerce` leaves out is returned in
        `left`. That covers enum values that are not permitted, the
        permitted values after the first in a single-valued slot, and the
        items of a list that are not the DOI a `doi` slot keeps.
        """
        view = self._schema_view()
        if slot.range and view.get_class(slot.range):
            return self._shape_objects(value, slot, slot.range, where)
        left: List[Tuple[Any, str]] = []
        items = [item for item in _as_list(value) if item is not None]
        scalars = [item for item in items if _is_scalar(item)]
        if not scalars:
            return None, ((f"{_not_scalar(items)}, which a "
                           f"`{slot.range}` slot does not hold: "
                           f"{_preview(value)}") if items else
                          f"no value in {_preview(value)}"), []
        left += [(item, f"{_not_scalar([item])}, which a "
                        f"`{slot.range}` slot does not hold")
                 for item in items if not _is_scalar(item)]
        value = scalars if isinstance(value, list) else scalars[0]
        if isinstance(value, list) and len(value) == 1 and not slot.multivalued:
            value = value[0]
        enum = view.get_enum(slot.range) if slot.range else None
        if (isinstance(value, list) and len(value) > 1 and not slot.multivalued
                and not enum and slot.name != DOI_SLOT
                and slot.range != 'string'):
            left += [(item, f"`{slot.name}` is single-valued and holds the "
                            f"first of {len(value)} list items")
                     for item in value[1:] if not _same(item, value[0])]
            value = value[0]
        if slot.range == 'date':
            dates = []
            for item in _as_list(value):
                date, why = _calendar_date(item)
                if date is None:
                    if not slot.multivalued:
                        return None, why, left
                    left.append((item, why))
                else:
                    dates.append(date)
            if not dates:
                return None, f"no calendar date in {_preview(value)}", left
            shaped, note = (dates if slot.multivalued else dates[0]), ''
        else:
            shaped, note = _coerce(value, slot, view, 'fairscape', self._minted)
            if shaped is None:
                return None, note, left
        left += self._not_kept(value, shaped, slot, enum)
        if slot.range in IDENTIFIER_RANGES:
            shaped = ([resolvable_id(item) for item in shaped]
                      if isinstance(shaped, list) else resolvable_id(shaped))
        return _plain(shaped), note, left

    @staticmethod
    def _not_kept(value: Any, shaped: Any, slot: Any,
                  enum: Any) -> List[Tuple[Any, str]]:
        """The parts of `value` that `_coerce` shaped into `shaped` without
        keeping, each with the reason (#4073).

        `_coerce` keeps only permitted enum values and, for a single-valued
        enum slot, only the first of them. For a list in a `doi` slot it
        keeps the one DOI among its items. It does not report any of these,
        and for a single-valued enum slot given two permitted values it
        writes no note at all. Each value is reported once, as JSON reads
        them (`_same`, #4159): `dict.fromkeys` took `true` for `1`.
        """
        items = _as_list(value)
        kept = _as_list(shaped)
        if enum:
            permitted = set(enum.permissible_values)
            return [(item, f"not a {slot.range} value" if item not in permitted
                     else f"`{slot.name}` is single-valued and holds "
                          f"{kept[0]!r}")
                    for item in _distinct(items) if not _among(item, kept)]
        if slot.name == DOI_SLOT and isinstance(value, list):
            doi = _norm(shaped)
            left = []
            for item in items:
                form, _ = doi_for_slot(item, slot.pattern)
                if form is None or _norm(form) != doi:
                    left.append((item, f"not the DOI `{slot.name}` holds, the "
                                       f"one DOI among {len(items)} list items"))
            return left
        return []

    def _shape_objects(self, value: Any, slot: Any, cls: str,
                       where: str) -> Tuple[Any, str, List[Tuple[Any, str]]]:
        """`value` as the `cls` objects `slot` holds (#3969, #4073).

        Each item becomes one object (`_object`). A single-valued slot
        given a list of text holds one object made from the text joined
        with `; `. `_coerce` makes each item an object first and then joins
        the objects. A list holding a reference, an object or another list
        is not joined, because joining it would write its Python repr, and
        it is not placed. `_coerce` drops a list inside the list and
        shapes the rest (#4183), so for a single-valued slot given text
        beside such a list it keeps the text, where this places nothing.
        Each part that is left out is recorded in `dropped` by
        `_object` or `_fit`. Those name the path inside the object, so
        `left` is always empty here.

        An item of a multivalued slot is named by its position in the list
        read, `None` items counted, and its object is kept with that
        position (`_read_at`), so that `_leave_out` names it the same way
        in every pass, however many items before it yield nothing or are
        left out (#4126).
        """
        items = _as_list(value)
        present = [item for item in items if item is not None]
        if not slot.multivalued and len(present) > 1:
            if not all(_is_text(item) for item in present):
                return None, (
                    f"{len(present)} values for a single-valued slot, not all "
                    f"of them text: text is joined into one {cls}, and a "
                    "reference, an object or a list inside the list is not"), []
            items = ['; '.join(str(item) for item in present)]
        built = []
        for n, item in enumerate(items):
            if item is None:
                continue
            path = f"{where}[{n}]." if slot.multivalued else f"{where}."
            obj = self._object(item, cls, slot, path)
            if obj:
                built.append(obj)
                if slot.multivalued:
                    self._read_at[id(obj)] = (obj, n)
        if not built:
            return None, f"no part of it could be placed in a {cls}", []
        return (built if slot.multivalued else built[0]), '', []

    def _object(self, item: Any, cls: str, slot: Any,
                path: str) -> Optional[Dict[str, Any]]:
        """One `cls` object from a crate value, or None (#4073).

        A mapping is fitted key by key (`_fit`). A JSON-LD reference keeps
        its `@id` as the object's `id`, an ARK as its resolver URL, and its
        other keys are fitted the same way. `@type` and `@context` are
        JSON-LD framing, not values. `rocrate_map._to_object` kept only a
        reference's `@id`, `name` and `description` and dropped its other
        keys without a word. Text becomes an object by the static-map arm's
        rule (`_to_object`). Whatever is left out is recorded in `dropped`
        under `path`.
        """
        where = path.rstrip('.')
        if isinstance(item, dict):
            fields = {key: val for key, val in item.items()
                      if not str(key).startswith('@')}
            obj = self._fit(fields, cls, {}, path) if fields else {}
            ref = _ref_id(item)
            if '@id' in item:
                if ref is None:
                    self.dropped.append((f"{path}@id", (
                        f"not placed in `id`: {_preview(item['@id'])} is not "
                        "an identifier")))
                elif 'id' not in self._class_slots(cls):
                    self.dropped.append((f"{path}@id", (
                        f"the schema declares no `id` slot on {cls}")))
                elif 'id' in obj:
                    self.dropped.append((f"{path}@id", (
                        f"not placed in `id`: {ref!r}; the object's own "
                        f"`id`, {obj['id']!r}, is kept")))
                else:
                    obj = {'id': resolvable_id(ref), **obj}
            for key in item:
                if (str(key).startswith('@')
                        and key not in ('@id', '@type', '@context')):
                    self.dropped.append((f"{path}{key}", (
                        f"the JSON-LD keyword `{key}` is not a value a {cls} "
                        "holds")))
            return obj or None
        if _is_text(item):
            obj, _ = _to_object(item, cls, self._schema_view(), 'fairscape',
                                slot.name, self._minted)
            if isinstance(obj, dict):
                return _plain(obj)
            self.dropped.append((where, (
                f"not placed: no {cls} slot holds text: {_preview(item)}")))
            return None
        self.dropped.append((where, (
            f"not placed: {_preview(item)} is neither text nor an object a "
            f"{cls} holds")))
        return None

    def _build_file_collections(self, nested_datasets: List[Dict]) -> List[Dict[str, Any]]:
        """
        Convert nested RO-Crate Datasets to D4D FileCollections.

        A file collection is made from the entity's `@id` and the
        properties `FILE_COLLECTION_SLOTS` names, and from nothing else
        (#4159).

        Args:
            nested_datasets: List of nested Dataset entities from RO-Crate

        Returns:
            List of FileCollection dictionaries
        """
        file_collections = []

        for dataset in nested_datasets:
            collection = {}

            # Map basic properties
            if '@id' in dataset:
                collection['id'] = resolvable_id(dataset['@id'])

            # Note: encodingFormat, sha256, md5, format, bytes, encoding are now
            # file-level properties (on File objects), not FileCollection properties
            for prop, slot in FILE_COLLECTION_SLOTS.items():
                if prop not in dataset:
                    continue
                if slot != 'total_bytes':
                    collection[slot] = dataset[prop]
                    continue
                # The aggregate size, from a byte count only (#4074):
                # evi:totalContentSizeBytes first, the property the interface
                # mapping declares for a byte size, then a contentSize written
                # in bytes. A contentSize with a unit (`441.2 GB`) is not
                # converted.
                size, why = exact_bytes(dataset[prop])
                where = f"{dataset.get('@id')}.{prop}"
                if size is None:
                    self.dropped.append((where, f"not placed in `total_bytes`: {why}"))
                elif 'total_bytes' not in collection:
                    collection['total_bytes'] = size
                elif size != collection['total_bytes']:
                    self.dropped.append((where, (
                        f"not placed in `total_bytes`: {size}; superseded by "
                        f"evi:totalContentSizeBytes, {collection['total_bytes']}")))

            # TODO: Parse nested Dataset's hasPart to build FileCollection.resources
            # Currently, file-level information in RO-Crate File entities is not converted
            # to FileCollection.resources (File objects). Future work: parse dataset['hasPart'],
            # fetch referenced File entities, and convert to D4D File objects in resources.

            # Only add non-empty collections
            if collection:
                file_collections.append(collection)

        return file_collections

    def _map_basic_properties(self, dataset: Dict) -> List[Tuple[str, str, Any]]:
        """Map basic Schema.org properties to D4D, as (crate property, slot, value)."""

        mapping = {
            # Direct mappings (same name)
            'name': 'title',
            'description': 'description',
            'keywords': 'keywords',
            'version': 'version',
            'license': 'license',
            'publisher': 'publisher',

            # Property name differences
            'identifier': 'doi',
            'datePublished': 'issued',
            'dateCreated': 'created_on',
            'dateModified': 'last_updated_on',
            'author': 'creators',
            'url': 'page',
            'contentUrl': 'download_url',
            # The schema has no Dataset `bytes`; its byte-size slot is
            # `total_size_bytes` (dcat:byteSize) (#3969). It takes a
            # contentSize written in bytes only. A size with a unit
            # (`19.1 TB`) is not converted, and evi:totalContentSizeBytes,
            # read after it, supersedes it (#4074).
            'contentSize': 'total_size_bytes',
        }

        found = []

        for rocrate_prop, d4d_prop in mapping.items():
            if rocrate_prop in dataset:
                value = dataset[rocrate_prop]

                # Handle special transformations
                if rocrate_prop == 'author' and isinstance(value, str):
                    # Convert semicolon-separated string to Creator list
                    value = self._parse_authors(value)
                elif rocrate_prop == 'contentSize':
                    size, why = exact_bytes(value)
                    if size is None:
                        self.dropped.append(
                            (rocrate_prop, f"not placed in `{d4d_prop}`: {why}"))
                        continue
                    value = size

                found.append((rocrate_prop, d4d_prop, value))

        return found

    def _map_complex_properties(self, dataset: Dict) -> List[Tuple[str, str, Any]]:
        """Map complex/nested properties, as (crate property, slot, value)."""

        found = []

        # hasPart → resources (schema:hasPart), its members typed as
        # datasets only (#4074). JSON-LD writes one reference as itself.
        if 'hasPart' in dataset:
            found.append(('hasPart', 'resources',
                          self._parts(dataset['hasPart'], dataset.get('@id'))))

        # isPartOf → parent_datasets, the Dataset slot whose slot_uri is
        # schema:isPartOf; there is no `is_part_of` slot (#3969). What the
        # crate names there is not checked to be a dataset (#4047). Each
        # reference's keys are fitted to Dataset or recorded (#4098), and
        # text, which is not a reference, is recorded (#4125). The slot
        # takes nothing from any other property (`DATASET_SLOTS`, #4138).
        if 'isPartOf' in dataset:
            found.append(('isPartOf', 'parent_datasets',
                          self._references('isPartOf',
                                           _as_list(dataset['isPartOf']))))

        # additionalProperty → custom metadata
        if 'additionalProperty' in dataset:
            found.extend(self._parse_additional_properties(
                _as_list(dataset['additionalProperty'])))

        return found

    def _parts(self, has_part: Any, root_id: Any) -> List[Dict[str, Any]]:
        """The root's `hasPart` members `resources` holds (#4074).

        `resources` ranges over Dataset ("component datasets"), so a member
        is written there only when the crate types it as a dataset
        (`is_dataset`). There are four cases:

        - A member the `@graph` describes as a dataset is already a file
          collection (`_extract_datasets`) and is not repeated. The file
          collection is made from the `@graph`'s entity, so a key the
          reference states that the entity does not, or states otherwise,
          is recorded in `dropped` (`_keys_not_taken`, #4098), and so is
          one the file collection does not read from the entity, whatever
          the entity states (#4159). Where two `@graph` nodes share the
          member's `@id`, the entity is the one the file collection is made
          from, the first typed as a dataset (#4167).
        - A member the `@graph` describes as anything else (a person, a
          defined term, software, a computation, a schema) is not a dataset
          part, and is recorded in `dropped`.
        - A member the `@graph` does not describe, whose reference types it
          as a dataset, is a component dataset: it is written to
          `resources`, and `_object` fits the reference's keys to Dataset,
          recording each it does not declare (#4098), and a `resources` or
          `parent_datasets` key too, since those slots take nothing from a
          reference (`_fit`, #4153). Until #4098 only its `@id` was kept,
          and its other keys were lost without a word.
        - Any other member the `@graph` does not describe has no type, or
          one that is not a dataset, so nothing in the crate says it is a
          dataset, and it is recorded in `dropped`.

        Until #4074 every member was written as a Dataset, whatever its
        type.

        The list keeps each part at its position in the crate's `hasPart`,
        with None for a member that is not written to `resources`, so a
        `dropped` path counts the crate's members (#4126). None when no
        member is written there.
        """
        parts: List[Optional[Dict[str, Any]]] = []
        for item in _as_list(has_part):
            parts.append(None)
            ref = _ref_id(item)
            if ref is None:
                self.dropped.append(('hasPart', f"an entry with no `@id`: {_preview(item)}"))
                continue
            if ref in self._collected:
                self._keys_not_taken(item, ref, self._collected[ref])
                continue
            if ref == root_id:
                self.dropped.append(('hasPart', (
                    f"{ref}: the root names itself as one of its parts")))
                continue
            entity = self._described.get(ref)
            if entity is None and isinstance(item, dict) and item.get('@type'):
                entity = item
            if entity is None:
                self.dropped.append(('hasPart', (
                    f"{ref}: the crate's `@graph` does not describe it, so "
                    "nothing in the crate says it is a dataset; `resources` "
                    "holds the dataset's component datasets")))
            elif not is_dataset(entity):
                self.dropped.append(('hasPart', (
                    f"{ref}: the crate types it {_types(entity)}, not as a "
                    "dataset; `resources` holds the dataset's component "
                    "datasets")))
            else:
                # Only a reference that types itself reaches here: one the
                # `@graph` describes as a dataset is a file collection.
                parts[-1] = item
        return parts if any(part is not None for part in parts) else None

    def _keys_not_taken(self, item: Any, ref: str,
                        entity: Dict[str, Any]) -> None:
        """Record each key a `hasPart` reference states that the member's
        file collection does not take from it (#4098, #4159).

        The file collection is made from `entity`, the `@graph`'s entity for
        the member, from the properties `FILE_COLLECTION_SLOTS` names, and
        each value read from them is kept there or recorded in `dropped`
        (`_build_file_collections`). A reference may state such a value
        again, as CHORUS's root does with `name`, and then says nothing the
        entity does not. Any other key it states is not in the record: one
        the entity does not carry, or carries with another value, and one
        the file collection does not read, whatever the entity carries.
        Until #4159 every key the entity carried with the same value was
        passed over, so a `parent_datasets` or a `license` both stated
        reached neither the record nor `dropped`. Values compare as JSON
        values (`_same`). An empty value states nothing and is not
        recorded, as `_place` and `_take` record none.

        `entity` is the node `_extract_datasets` selected and
        `_build_file_collections` read: of the `@graph` nodes that share
        the member's `@id`, the first typed as a dataset. Until #4167 the
        reference was compared with the first node of that `@id`
        (`_described`), which can be another. A value the reference stated
        as that node did was passed over while the file collection held
        the other node's, so it was in neither the record nor `dropped`.
        """
        if not isinstance(item, dict):
            return
        for key, value in item.items():
            if key in ('@id', '@type', '@context') or value in (None, '', [], {}):
                continue
            same = _same(entity.get(key), value)
            if same and key in FILE_COLLECTION_SLOTS:
                continue
            said = ("and the `@graph`'s entity for it both state, is not a "
                    "property its file collection is made from" if same else
                    "states for it, is not what the `@graph`'s entity for it "
                    "states, and its file collection is made from that entity")
            self.dropped.append(('hasPart', (
                f"{ref}: `{key}` {_preview(value)}, which the root's `hasPart` "
                f"{said}")))

    def _references(self, prop: str, items: List[Any]
                    ) -> Optional[List[Optional[Dict[str, Any]]]]:
        """The crate references `items`, for a Dataset-ranged slot (#4098).

        A reference keeps its `@id` as the object's `id`, an ARK as its
        resolver URL, and `_object` fits its other keys to Dataset: a key
        the class declares, such as `name` or `description`, is kept, and
        any other is recorded in `dropped`, as is a `parent_datasets` or
        `resources` key, since those slots take nothing from a reference
        (`_fit`, #4153). Until #4098 only the `@id` was kept, and every other
        key was lost without a word.

        An entry with no `@id` is recorded in `dropped`, and so is text
        (#4125). JSON-LD reads a string under `isPartOf` as text, not as a
        reference, unless the context types the property `@id`, and
        RO-Crate's context does not; `{"@value": …}` is the same text
        written out, and was already recorded. Text names no dataset the
        record can point at. It was written as the reference's `id`, so a
        name (`Cell Maps for AI project`) went where an identifier goes, and
        the record still validated. This converter reads a crate as
        RO-Crate's context writes it, and does not apply a crate's own
        `@context`. A `hasPart` member written as text is looked up among
        the `@graph`'s entities instead (`_parts`), and is never written as
        an `id` itself.

        The text is recorded rather than placed in another slot. A parent
        needs an `id`, which `_to_object` would mint, asserting a dataset
        the crate does not identify; `related_datasets` can say
        `is_part_of`, but needs the dataset's identifier or URL as its
        `target_dataset` just as much. That leaves `notes`, and this
        converter moves no value it cannot place into a slot other than
        its own. For the same reason `parent_datasets` takes only these
        references: a value another property maps to it, such as an
        `additionalProperty` named "Parent Datasets", is recorded by
        `_build_d4d` (`DATASET_SLOTS`, #4138), and so is a
        `parent_datasets` key inside a reference, by `_fit` (#4153).

        The list keeps each reference at its position in the crate's list,
        with None for an entry that is not one, so a `dropped` path counts
        the crate's entries (#4126). None when no entry is a reference.
        """
        references: List[Optional[Dict[str, Any]]] = []
        for item in items:
            if isinstance(item, dict) and _ref_id(item) is not None:
                references.append(item)
                continue
            references.append(None)
            if isinstance(item, str) and item.strip():
                self.dropped.append((prop, (
                    f"text, not a reference: {_preview(item)} (under "
                    f"RO-Crate's context JSON-LD reads text under `{prop}` as "
                    "a literal, which names no dataset the record can point "
                    "at; a reference is written `{\"@id\": …}`)")))
            else:
                self.dropped.append((prop, f"an entry with no `@id`: {_preview(item)}"))
        return references if any(ref is not None for ref in references) else None

    def _map_evi_properties(self, dataset: Dict) -> List[Tuple[str, str, Any]]:
        """Map EVI (Evidence) namespace properties, as (crate property, slot, value).

        `evi:formats` and `evi:totalContentSizeBytes` have Dataset slots. The
        roll-up counts and the checksums name none, and `_fit` records them
        as dropped (#3969).
        """

        evi_mapping = {
            'evi:datasetCount': 'dataset_count',
            'evi:computationCount': 'computation_count',
            'evi:softwareCount': 'software_count',
            'evi:schemaCount': 'schema_count',
            'evi:totalEntities': 'total_entities',
            'evi:formats': 'distribution_formats',
            # The crate's exact byte count, the source the interface mapping
            # declares for Dataset.total_size_bytes. Read after contentSize,
            # so it supersedes a contentSize that disagrees (#4074).
            'evi:totalContentSizeBytes': 'total_size_bytes',
            'evi:md5': 'md5',
            'evi:sha256': 'sha256',
        }

        found = []
        for evi_prop, d4d_prop in evi_mapping.items():
            if evi_prop not in dataset:
                continue
            value = dataset[evi_prop]
            if d4d_prop == 'total_size_bytes':
                value, why = exact_bytes(value)
                if value is None:
                    self.dropped.append((evi_prop, f"not placed in `{d4d_prop}`: {why}"))
                    continue
            found.append((evi_prop, d4d_prop, value))
        return found

    def _map_rai_properties(self, dataset: Dict) -> List[Tuple[str, str, Any]]:
        """Map RAI (Responsible AI) properties, as (crate property, slot, value)."""

        rai_mapping = {
            'rai:dataUseCases': 'intended_uses',
            'rai:dataBiases': 'known_biases',
            'rai:dataLimitations': 'known_limitations',
            'rai:dataCollection': 'acquisition_methods',
            'rai:dataCollectionMissingData': 'missing_data_documentation',
            'rai:dataCollectionRawData': 'raw_data_sources',
            'rai:dataCollectionTimeframe': 'collection_timeframes',
            # FAIRSCAPE's ROCrateMetadataElem declares these three as
            # unprefixed `prohibitedUses` and `ethicalReview` and as
            # `rai:dataImputationProtocol`, so the `rai:` spellings never
            # matched a FAIRSCAPE crate (#3973). The `rai:` spellings stay
            # because d4d_to_fairscape.py writes them, and this repo's own
            # round trip reads them back. The three slots are multivalued,
            # so a crate carrying both spellings keeps both values (`_place`).
            'rai:prohibitedUses': 'prohibited_uses',
            'prohibitedUses': 'prohibited_uses',
            'rai:ethicalReview': 'ethical_reviews',
            'ethicalReview': 'ethical_reviews',
            'rai:personalSensitiveInformation': 'confidential_elements',
            'rai:dataSocialImpact': 'data_protection_impacts',
            'rai:dataReleaseMaintenancePlan': 'updates',
            'rai:dataPreprocessingProtocol': 'preprocessing_strategies',
            'rai:dataAnnotationProtocol': 'labeling_strategies',
            'rai:dataAnnotationAnalysis': 'annotation_analyses',
            # MachineAnnotationTools is the class the schema maps to
            # rai:machineAnnotationTools; there is no
            # `machine_annotation_analyses` slot (#3969).
            'rai:machineAnnotationTools': 'machine_annotation_tools',
            'rai:imputationProtocol': 'imputation_protocols',
            'rai:dataImputationProtocol': 'imputation_protocols',
        }

        found = []
        for rai_prop, d4d_prop in rai_mapping.items():
            if rai_prop not in dataset:
                continue
            value = dataset[rai_prop]
            if rai_prop == 'rai:dataCollectionTimeframe':
                value = self._timeframe(rai_prop, value)
            found.append((rai_prop, d4d_prop, value))
        return found

    def _timeframe(self, prop: str, value: Any) -> Any:
        """`rai:dataCollectionTimeframe` as one CollectionTimeframe (#4073).

        Croissant RAI defines the property as the start and end date of the
        collection process, and FAIRSCAPE writes it as a two-item list
        (`["9/1/2022", "1/31/2026"]`). That is one window. `_coerce` made it
        two CollectionTimeframes, each named by a single date, and left
        `start_date` and `end_date` empty. A two-item list with an item
        written as a date becomes one object with those two dates, which
        `_shape` reads as calendar dates (`_calendar_date`). A date that rule
        cannot read, such as the ambiguous `9/1/2022`, is recorded in
        `dropped` and not guessed. A longer list with a date in it is not a
        start and an end, so it is recorded in `dropped` whole.

        A value with no item written as a date is prose about the
        collection period (the VOICE crate writes two sentences). It is not
        a start and an end, and is shaped as before: each text becomes one
        timeframe described by it.
        """
        if (not isinstance(value, list) or len(value) < 2
                or not any(isinstance(item, str) and DATE_WRITTEN.match(item)
                           for item in value)):
            return value
        if len(value) == 2:
            return [{'start_date': value[0], 'end_date': value[1]}]
        self.dropped.append((prop, (
            f"not placed in `collection_timeframes`: {len(value)} items, where "
            "Croissant RAI defines this property as the start and end date of "
            "the collection")))
        return None

    def _map_d4d_properties(self, dataset: Dict) -> List[Tuple[str, str, Any]]:
        """Map D4D-specific namespace properties, as (crate property, slot, value)."""

        d4d_mapping = {
            'd4d:addressingGaps': 'addressing_gaps',
            'd4d:dataAnomalies': 'anomalies',
            'd4d:contentWarning': 'content_warnings',
            'd4d:informedConsent': 'informed_consent',
            'd4d:humanSubject': 'human_subject_research',
            # The slot whose slot_uri is d4d:atRiskPopulations; there is no
            # `vulnerable_populations` slot (#3969).
            'd4d:atRiskPopulations': 'at_risk_populations',
        }

        return [(d4d_ns_prop, d4d_prop, dataset[d4d_ns_prop])
                for d4d_ns_prop, d4d_prop in d4d_mapping.items()
                if d4d_ns_prop in dataset]

    def _parse_authors(self, author_string: str) -> List[Dict[str, str]]:
        """Parse semicolon-separated author string to Creator list.

        A Creator declares no `type` slot, so none is written (#3969).
        """
        authors = []

        for name in author_string.split(';'):
            name = name.strip()
            if name:
                authors.append({'name': name})

        return authors

    def _parse_additional_properties(self, additional: List[Dict]) -> List[Tuple[str, str, Any]]:
        """Parse additionalProperty list to D4D fields, as (source, slot, value).

        `Completeness` and `Data Governance Committee` name no Dataset slot,
        and `_fit` records them as dropped, as it does any other name that
        is not one (#3969). An entry that is not a PropertyValue is recorded
        in `dropped` too (#4073), and so is one with no name written as
        text, whatever else it carries (#4073, #4152), and one whose name
        maps to `resources` or `parent_datasets`, which hold only the
        datasets the root's `hasPart` and `isPartOf` name (`DATASET_SLOTS`,
        #4073, #4138).

        A nameless entry may be a reference (`{"@id": …}`), as in
        RO-Crate's flattened form, where the entity it names states the
        name and the value. That entity is not looked up in the `@graph`,
        so the reference is recorded like any other nameless entry, its
        `@id` in the reason.
        """
        found = []

        for n, prop in enumerate(additional):
            # schema:additionalProperty ranges over PropertyValue, so an
            # entry that states no `@type` is read as one.
            if not isinstance(prop, dict) or (
                    prop.get('@type') and not _type_matches(prop, 'PropertyValue')):
                self.dropped.append((f"additionalProperty[{n}]",
                                     f"not a PropertyValue: {_preview(prop)}"))
                continue

            name = prop.get('name')
            value = prop.get('value')

            if not isinstance(name, str) or not name.strip():
                # An entry is read by its name. Until #4152 one with none
                # was recorded only when it held a `value`, so a reference
                # reached neither the record nor `dropped`.
                ref = _ref_id(prop)
                self.dropped.append((f"additionalProperty[{n}]", (
                    "a PropertyValue with no name written as text, so no slot "
                    f"to read it into: {_preview(prop)}"
                    + (f" (a reference to {ref}, which is not looked up in "
                       "the `@graph`)" if ref else ""))))
                continue

            # Map known additional properties to D4D fields
            name_mapping = {
                'Completeness': 'completeness',
                'Human Subject': 'human_subject_research',
                'Prohibited Uses': 'prohibited_uses',
                'Data Governance Committee': 'data_governance_committee',
            }

            d4d_field = name_mapping.get(name, name.lower().replace(' ', '_'))
            found.append((f"additionalProperty[{name}]", d4d_field, value))

        return found

    def convert_and_save(
        self,
        rocrate_input: Any,
        output_file: Path,
        validate: bool = True
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Convert RO-Crate to D4D and save as YAML.

        Args:
            rocrate_input: FAIRSCAPE RO-Crate input
            output_file: Output YAML file path
            validate: Validate against D4D schema

        Returns:
            (d4d_dict, is_valid)
        """
        # Convert
        d4d_dict = self.convert(rocrate_input)

        # Save
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            yaml.safe_dump(d4d_dict, f, default_flow_style=False, sort_keys=False)

        print(f"✓ D4D YAML saved to {output_file}")

        if self.dropped:
            print(f"⚠ {len(self.dropped)} crate value(s) not placed in the record:")
            for source, reason in self.dropped:
                print(f"  - {source}: {reason}")

        # Validate if requested
        is_valid = True
        if validate:
            is_valid = self._validate_d4d(output_file)

        return d4d_dict, is_valid

    def _validate_d4d(self, d4d_file: Path) -> bool:
        """Validate D4D YAML against schema.

        The file is read back and checked by `record_validator`, the
        validator `linkml.validator.validate` builds, which `convert` has
        already run on the record. So this checks what the YAML on disk
        holds, not a different rule.
        """
        try:
            # From any working directory (#1301). A schema that cannot be
            # found means the record was not validated, which is not a pass
            # (#3969).
            schema_file = resource_path(FULL_SCHEMA)

            if not schema_file.exists():
                print(f"✗ Schema not found: {schema_file}; the record was not validated")
                return False

            # Load D4D data
            with open(d4d_file) as f:
                d4d_data = yaml.safe_load(f)

            # Validate
            report = record_validator(str(schema_file)).validate(
                d4d_data, TARGET_CLASS)

            if report.results:
                print(f"✗ Validation failed with {len(report.results)} errors")
                for result in report.results[:5]:  # Show first 5 errors
                    print(f"  - {result.message}")
                return False
            else:
                print("✓ D4D YAML validated against schema")
                return True

        except Exception as e:
            print(f"⚠ Validation error: {e}")
            return False


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert FAIRSCAPE RO-Crate to D4D YAML'
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input FAIRSCAPE RO-Crate JSON file'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output D4D YAML file'
    )
    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Skip D4D schema validation'
    )

    args = parser.parse_args()

    # Convert
    converter = FairscapeToD4DConverter()

    print(f"\nConverting FAIRSCAPE RO-Crate → D4D YAML...")
    print(f"  Input:  {args.input}")
    print(f"  Output: {args.output}")

    try:
        d4d_dict, is_valid = converter.convert_and_save(
            Path(args.input),
            Path(args.output),
            validate=not args.no_validate
        )

        print(f"\n✓ Conversion complete")
        print(f"  D4D fields: {len(d4d_dict)}")
        print(f"  Validation: {'✓ PASSED' if is_valid else '✗ FAILED'}")

        return 0 if is_valid else 1

    except Exception as e:
        print(f"\n✗ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
