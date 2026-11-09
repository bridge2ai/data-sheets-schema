"""Read saved records for D105's secondary transformation measurement.

No records are written. Exact input byte hashes supplement the measurement's
typed semantic digests; filenames and wall-clock time do not affect the result.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

MAX_RECORD_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 128


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
        value = yaml.load(raw.decode("utf-8"), Loader=_RecordLoader)
    except (UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid UTF-8 YAML/JSON record: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("record must be a mapping")
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
