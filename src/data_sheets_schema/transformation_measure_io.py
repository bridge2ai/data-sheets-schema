"""Read saved records for D105's secondary transformation measurement.

No records are written. Exact input byte hashes supplement the measurement's
typed semantic digests; filenames and wall-clock time do not affect the result.
"""
from __future__ import annotations

import hashlib
import json
import datetime as dt
import math
from pathlib import Path

import yaml

MAX_RECORD_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 128
MAX_NODES = 1_000_000


def validate_record(value: dict) -> None:
    """Bound already-parsed input as well as file-loaded input.

    Reject shared containers/cycles, unsupported values, non-string keys and
    nonfinite numbers. The size limit here applies to canonical JSON bytes
    (dates encoded as ISO text); read_record additionally bounds source bytes.
    A dict cannot reveal duplicate keys or tags discarded by another parser:
    use read_record when those original-syntax checks are needed.
    """
    if type(value) is not dict:
        raise ValueError("record must be a mapping")
    seen, remaining = set(), [MAX_NODES]

    def visit(item, depth):
        remaining[0] -= 1
        if depth > MAX_DEPTH or remaining[0] < 0:
            raise ValueError("record exceeds structural depth/node bounds")
        kind = type(item)
        if kind in (dict, list):
            if id(item) in seen:
                raise ValueError("record aliases or cycles are unsupported")
            seen.add(id(item))
            if kind is dict:
                for key, child in item.items():
                    if not isinstance(key, str):
                        raise ValueError("record mapping keys must be strings")
                    visit(str(key), depth + 1)
                    visit(child, depth + 1)
            else:
                for child in item:
                    visit(child, depth + 1)
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError("record contains a nonfinite number")
        elif not (item is None or kind in (str, int, bool, dt.date, dt.datetime)):
            raise ValueError("unsupported record type: " + kind.__name__)

    visit(value, 1)
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False,
                               separators=(",", ":"), default=lambda x: x.isoformat())
    size = 0
    for chunk in encoder.iterencode(value):
        size += len(chunk.encode("utf-8"))
        if size > MAX_RECORD_BYTES:
            raise ValueError(f"record exceeds {MAX_RECORD_BYTES} canonical JSON bytes")


def _json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate record key: {key!r}")
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError(f"record contains a nonfinite number: {value}")


class _RecordLoader(yaml.SafeLoader):
    """Unambiguous saved YAML/JSON objects, with bounded nesting and no aliases."""

    def __init__(self, stream):
        super().__init__(stream)
        self._depth = 0

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise ValueError("record aliases are unsupported; use expanded values")
        self._depth += 1
        try:
            if self._depth > MAX_DEPTH:
                raise ValueError(f"record nesting exceeds {MAX_DEPTH}")
            return super().compose_node(parent, index)
        finally:
            self._depth -= 1

    def construct_mapping(self, node, deep=False):
        # A merge can silently replace an explicit value. Refuse it rather
        # than attributing a projection to an ambiguous source spelling.
        result = {}
        for key_node, value_node in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise ValueError("record merge keys are unsupported")
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError("record mapping keys must be strings")
            if key in result:
                raise ValueError(f"duplicate record key: {key!r}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def read_record(path: Path) -> tuple[dict, str]:
    """Read one finite, bounded mapping and return its exact SHA-256."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_RECORD_BYTES + 1)
    if len(raw) > MAX_RECORD_BYTES:
        raise ValueError(f"record exceeds {MAX_RECORD_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ValueError(f"invalid UTF-8 record: {exc}") from exc
    # JSON numbers such as 1e5 must retain JSON semantics, even in a YAML-named
    # file containing a complete JSON object. Genuine YAML flow mappings remain
    # supported when their syntax is not JSON. A .json file is strictly JSON.
    try:
        if path.suffix.lower() == ".json" or text.lstrip().startswith(("{", "[")):
            try:
                value = json.loads(text, object_pairs_hook=_json_pairs,
                                   parse_constant=_nonfinite)
            except json.JSONDecodeError as exc:
                if path.suffix.lower() == ".json":
                    raise ValueError(f"invalid JSON record: {exc}") from exc
                value = yaml.load(text, Loader=_RecordLoader)
        else:
            value = yaml.load(text, Loader=_RecordLoader)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML record: {exc}") from exc
    except RecursionError as exc:
        raise ValueError("record exceeds parser nesting bounds") from exc
    validate_record(value)
    return value, hashlib.sha256(raw).hexdigest()


def measure_files(full_path: Path, core_path: Path) -> dict:
    """Measure exactly the bytes read, without altering either input."""
    from data_sheets_schema.transformation_measure import measure

    full, full_sha = read_record(full_path)
    core, core_sha = read_record(core_path)
    result = measure(full, core)
    result["input_file_sha256"] = {"full": full_sha, "core": core_sha}
    return result


def report_text(report: dict) -> str:
    """Canonical readable JSON, including a final newline."""
    return json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False,
                      allow_nan=False) + "\n"
