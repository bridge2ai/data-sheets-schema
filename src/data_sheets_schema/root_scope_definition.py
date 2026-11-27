"""Compose frozen semantic v6 definitions from pinned v3 text, issue 6358 r2.

2026-11-25. Inputs are immutable source and override bytes; output is the
reviewed definition plus portable provenance. No file is written or executed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat

from data_sheets_schema.resources import resource_path


DEFINITION_PINS = {
    "rubric10": {
        "source_path": ".claude/agents/d4d-rubric10-semantic.md",
        "source_sha256": "c817aa5fefd91552be68016818c8a87ab91b8798ac96666d975bc61af32c7fb3",
        "overrides_path": "data/rubric/root_scope_v6/rubric10_definition_overrides.json",
        "overrides_sha256": "434a4d065a8d64e5de5405be1715fa4c4232a5fb401a39628fc9a32b6164b024",
        "composed_sha256": "84f42966ae968881aa65263c8d4f32a0ffe6988a85d24ea8d5a933e99ee1354d",
    },
    "rubric20": {
        "source_path": ".claude/agents/d4d-rubric20-semantic.md",
        "source_sha256": "35de3a37264e80f48e6e037fed42b6cc586152058d4da6c08bad93b8096f588b",
        "overrides_path": "data/rubric/root_scope_v6/rubric20_definition_overrides.json",
        "overrides_sha256": "f89b265d3c6585766362b2791c0608be69405299866e26a986efedfba3d3551d",
        "composed_sha256": "6beda6a0a46230b9c6128f9251c9eac0b5771f022c10b47cbc752f017432de52",
    },
}


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _parse_overrides(raw: bytes, rubric: str) -> list[dict]:
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate root definition override field")
            value[key] = item
        return value

    def constant(value):
        raise ValueError("nonfinite root definition override value")

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except UnicodeDecodeError as exc:
        raise ValueError("root definition overrides are not Unicode JSON") from exc
    if not isinstance(value, dict) or set(value) != {"version", "rubric", "replacements"}:
        raise ValueError("root definition overrides have missing or unknown fields")
    if value["version"] != "root_scope_definition_overrides_v1" or value["rubric"] != rubric:
        raise ValueError("root definition override identity differs")
    replacements = value["replacements"]
    if not isinstance(replacements, list) or not replacements:
        raise ValueError("root definition overrides require replacements")
    for pair in replacements:
        if not isinstance(pair, dict) or set(pair) != {"original", "replacement"}:
            raise ValueError("root definition replacement has missing or unknown fields")
        if not isinstance(pair["original"], str) or not pair["original"] or not isinstance(pair["replacement"], str):
            raise ValueError("root definition replacement requires exact nonempty original text")
    return replacements


def _apply_replacements(source: bytes, replacements: list[dict]) -> bytes:
    composed = source
    for pair in replacements:
        original = pair["original"].encode("utf-8")
        replacement = pair["replacement"].encode("utf-8")
        if source.count(original) != 1 or composed.count(original) != 1:
            raise ValueError("root definition original passage must occur exactly once")
        composed = composed.replace(original, replacement, 1)
    return composed


def compose_definition(rubric_name: str, repo_root: Path | None = None, resource_reader=None) -> tuple[bytes, dict]:
    """Return exact reviewed v6 bytes and source/override/composed hash identity.

    An explicit root never falls back to the current directory or installed
    files. Otherwise use the package resource reader, with both inputs pinned.
    A captured caller can supply one read-only relative-path byte reader.
    """
    if not isinstance(rubric_name, str):
        raise ValueError("unknown root definition rubric")
    rubric = rubric_name.removesuffix("-semantic")
    if rubric not in DEFINITION_PINS:
        raise ValueError("unknown root definition rubric")
    if repo_root is not None and resource_reader is not None:
        raise ValueError("select one root definition resource reader")
    pins = DEFINITION_PINS[rubric]

    def read(path):
        if resource_reader is not None:
            raw = resource_reader(path)
        else:
            selected = Path(repo_root) / path if repo_root is not None else resource_path(path)
            selected = selected.absolute()
            if any(part.is_symlink() for part in (selected, *selected.parents)):
                raise ValueError("root definition input must not use a symlink")
            info = selected.stat()
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 1024 * 1024:
                raise ValueError("root definition input must be a bounded nonempty regular file")
            with selected.open("rb") as handle:
                raw = handle.read(1024 * 1024 + 1)
        if not isinstance(raw, bytes) or not 0 < len(raw) <= 1024 * 1024:
            raise ValueError("root definition input must be bounded nonempty bytes")
        return raw

    source = read(pins["source_path"])
    if _sha(source) != pins["source_sha256"]:
        raise ValueError("root definition v3 source hash differs")
    overrides = read(pins["overrides_path"])
    if _sha(overrides) != pins["overrides_sha256"]:
        raise ValueError("root definition override hash differs")
    replacements = _parse_overrides(overrides, rubric)
    composed = _apply_replacements(source, replacements)
    if _sha(composed) != pins["composed_sha256"]:
        raise ValueError("root definition composed hash differs from reviewed v6 bytes")
    return composed, dict(pins)
