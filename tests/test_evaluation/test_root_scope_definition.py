"""Frozen composition and strict acceptance controls, issue 6358 r2, 2026-11-25.

Inputs are the pinned source and overrides plus synthetic drift in memory.
Only pytest scratch artifacts are written; no model or scoring process runs.
"""
import hashlib
import json
import os
from unittest.mock import patch

import pytest

from data_sheets_schema import root_scope_definition as definitions
from data_sheets_schema.evaluation.validate import validate_outputs
from tests.test_evaluation.test_root_scope_instrument import ROOT, root_fixture


# Frozen independently from the reviewed files at commit 26b74b67e.
FROZEN = {
    "rubric10": "84f42966ae968881aa65263c8d4f32a0ffe6988a85d24ea8d5a933e99ee1354d",
    "rubric20": "6beda6a0a46230b9c6128f9251c9eac0b5771f022c10b47cbc752f017432de52",
}


def source_inputs(rubric):
    pins = definitions.DEFINITION_PINS[rubric]
    return {pins[key]: (ROOT / pins[key]).read_bytes() for key in ("source_path", "overrides_path")}


def test_composed_bytes_match_the_frozen_reviewed_v6_definitions():
    for rubric, digest in FROZEN.items():
        composed, provenance = definitions.compose_definition(rubric, repo_root=ROOT)
        assert hashlib.sha256(composed).hexdigest() == digest
        assert provenance["composed_sha256"] == digest
        assert provenance["source_sha256"] == hashlib.sha256((ROOT / provenance["source_path"]).read_bytes()).hexdigest()
        assert provenance["overrides_sha256"] == hashlib.sha256((ROOT / provenance["overrides_path"]).read_bytes()).hexdigest()
        assert set(provenance) == {"source_path", "source_sha256", "overrides_path", "overrides_sha256", "composed_sha256"}
        assert not provenance["source_path"].startswith("/")
        assert not provenance["overrides_path"].startswith("/")
        inputs = source_inputs(rubric)
        reads = []

        def reader(path):
            reads.append(path)
            return inputs[path]

        assert definitions.compose_definition(rubric + "-semantic", resource_reader=reader) == (composed, provenance)
        assert reads == [provenance["source_path"], provenance["overrides_path"]]


def test_source_override_and_composed_hash_drift_are_independently_refused():
    for rubric in FROZEN:
        pins = definitions.DEFINITION_PINS[rubric]
        for key, expected in (("source_path", "v3 source hash"), ("overrides_path", "override hash")):
            inputs = source_inputs(rubric)
            inputs[pins[key]] += b"\n"
            with pytest.raises(ValueError, match=expected):
                definitions.compose_definition(rubric, resource_reader=inputs.__getitem__)
        altered_pins = {**pins, "composed_sha256": "0" * 64}
        with patch.dict(definitions.DEFINITION_PINS, {rubric: altered_pins}):
            with pytest.raises(ValueError, match="composed hash"):
                definitions.compose_definition(rubric, repo_root=ROOT)


def test_original_passages_must_exist_exactly_once_and_cannot_be_introduced():
    assert definitions._apply_replacements(b"one unique passage", [{"original": "unique", "replacement": "reviewed"}]) == b"one reviewed passage"
    cases = [
        (b"one passage", [{"original": "missing", "replacement": "new"}]),
        (b"same same", [{"original": "same", "replacement": "new"}]),
        (b"original", [{"original": "original", "replacement": "new"}, {"original": "new", "replacement": "later"}]),
        (b"long passage", [{"original": "long passage", "replacement": "new"}, {"original": "passage", "replacement": "later"}]),
    ]
    for source, replacements in cases:
        with pytest.raises(ValueError, match="exactly once"):
            definitions._apply_replacements(source, replacements)


def test_override_format_is_closed_and_refuses_duplicate_keys():
    valid = {"version": "root_scope_definition_overrides_v1", "rubric": "rubric10",
             "replacements": [{"original": "old", "replacement": "new"}]}
    assert definitions._parse_overrides(json.dumps(valid).encode(), "rubric10") == valid["replacements"]
    mutations = [{**valid, "extra": "unknown"}, {**valid, "version": "another"},
                 {**valid, "rubric": "rubric20"}, {**valid, "replacements": []},
                 {**valid, "replacements": [{"original": "", "replacement": "new"}]},
                 {**valid, "replacements": [{"original": "old", "replacement": "new", "extra": 1}]}]
    for value in mutations:
        with pytest.raises(ValueError):
            definitions._parse_overrides(json.dumps(value).encode(), "rubric10")
    for raw in (b'{"version":1,"version":2}', b"NaN", b"\xff"):
        with pytest.raises(ValueError):
            definitions._parse_overrides(raw, "rubric10")


def test_explicit_root_never_falls_back_to_cwd_or_default_resource_tree(tmp_path, monkeypatch):
    expected = definitions.compose_definition("rubric10", repo_root=ROOT)
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(outside)
    assert definitions.compose_definition("rubric10") == expected
    hostile = tmp_path / "hostile"
    source = hostile / definitions.DEFINITION_PINS["rubric10"]["source_path"]
    source.parent.mkdir(parents=True)
    source.write_bytes(b"unregistered source in another working directory\n")
    monkeypatch.chdir(hostile)
    with pytest.raises(ValueError, match="v3 source hash"):
        definitions.compose_definition("rubric10")
    assert definitions.compose_definition("rubric10", repo_root=ROOT) == expected
    with pytest.raises(FileNotFoundError):
        definitions.compose_definition("rubric10", repo_root=outside)
    with pytest.raises(ValueError, match="one root definition resource reader"):
        definitions.compose_definition("rubric10", repo_root=ROOT, resource_reader=lambda path: b"unused")


def test_strict_validator_refuses_changed_definition_even_with_matching_output_hash(tmp_path):
    for rubric in FROZEN:
        result, _, _, output, kwargs = root_fixture(tmp_path / rubric, rubric)
        assert validate_outputs([output], **kwargs) == 0
        definition = kwargs["definition_path"]
        definition.write_bytes(definition.read_bytes() + b"\nUnregistered text.\n")
        result["metadata"]["instrument_sha256"] = hashlib.sha256(definition.read_bytes()).hexdigest()
        output.write_text(json.dumps(result))
        assert validate_outputs([output], **kwargs) == 1
        definition.write_bytes((ROOT / definitions.DEFINITION_PINS[rubric]["source_path"]).read_bytes())
        result["metadata"]["instrument_sha256"] = hashlib.sha256(definition.read_bytes()).hexdigest()
        output.write_text(json.dumps(result))
        assert validate_outputs([output], **kwargs) == 1


def test_composition_refuses_nonregular_unbounded_and_symlink_sources(tmp_path):
    relative = definitions.DEFINITION_PINS["rubric10"]["source_path"]
    for name in ("fifo", "directory", "oversized", "symlink"):
        tree = tmp_path / name
        source = tree / relative
        source.parent.mkdir(parents=True)
        if name == "fifo":
            os.mkfifo(source)
        elif name == "directory":
            source.mkdir()
        elif name == "oversized":
            source.write_bytes(b"x" * (1024 * 1024 + 1))
        else:
            source.symlink_to(ROOT / relative)
        with pytest.raises(ValueError, match="regular file|symlink"):
            definitions.compose_definition("rubric10", repo_root=tree)
