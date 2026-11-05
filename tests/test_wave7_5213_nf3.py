"""#5213 NF3: literal replay and independent registration authority, offline.

Inputs are synthetic corpus fixtures; captured stdout records path and instruction
contrasts. Added 2026-10-30 before repairing the packet; no provider requests.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema import api_runner as api, chunking, shared_generation as sg
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_manifest_corpus_root import project_tree  # noqa: F401
from tests.test_shared_generation_selection import registration_for


@pytest.mark.parametrize("remove_inputs", [False, True])
def test_literal_replay_preserves_recorded_paths_at_corpus_root(
    project_tree, monkeypatch, remove_inputs,
):
    root, manifest, bundle = project_tree
    chunks, _ = chunking.write_manifest_for(bundle)
    original = api.RunSpec(
        project="CLINICAL_X", arm="BASELINE (input documents only)", method="external",
        label="nf3_literal_replay", condition="generic_v9", bundle=bundle,
        manifest=manifest, chunk_manifest=chunks.absolute(), runtime="Claude Code",
        provider="offline", render_version=5, run_date="2026-09-13", profile="neutral",
    )
    instruction = original.instruction
    recorded = original.render_spec()
    keys = ("bundle", "manifest", "chunk_manifest")
    assert all(Path(recorded[key]).is_absolute() for key in keys)
    monkeypatch.chdir(root)
    if remove_inputs:
        for path in (bundle, manifest, chunks):
            path.unlink()
    replay = api.RunSpec.from_render_spec(
        recorded, project=original.project, method=original.method, label=original.label,
    )
    restored = replay.render_spec()
    replayed_instruction = replay.instruction
    print(json.dumps({
        "recorded_paths": {key: recorded[key] for key in keys},
        "replayed_paths": {key: restored[key] for key in keys},
        "original_instruction_sha256": hashlib.sha256(instruction.encode()).hexdigest(),
        "replayed_instruction_sha256": hashlib.sha256(replayed_instruction.encode()).hexdigest(),
        "input_files_removed": remove_inputs,
    }, sort_keys=True))
    assert restored == recorded
    assert replayed_instruction == instruction


def test_registration_fixture_authority_remains_absolute_when_inputs_relativize(external, monkeypatch):
    monkeypatch.chdir(external.bundle.parent)
    spec = replace(external)
    assert not spec.bundle.is_absolute()
    reg = registration_for(spec)
    print(json.dumps({"bundle": str(spec.bundle), "registration_path": reg["registration_path"]}, sort_keys=True))
    sg.parse_registration(sg.canonical(reg))
    assert Path(reg["registration_path"]).is_absolute()
