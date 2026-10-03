"""The registered successor satisfies the legacy scope/receipt obligations.

Use invented local source content under each public project name. These are
complete selected instructions, not a replacement of RunSpec or a trimmed
base-template check; no factual corpus or model execution is involved.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re

import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking
from data_sheets_schema import receipt_completion_policy as policy
from data_sheets_schema.constants import PROJECTS
from tests.test_shared_generation_selection import (  # noqa: F401
    external, offline, registration_for, selected_spec,
)

ALL_PROJECTS = tuple(dict.fromkeys((*PROJECTS, "VOICE_PEDIATRIC")))


@pytest.mark.parametrize("project", ALL_PROJECTS)
def test_registered_instruction_owns_its_project_bundle_and_receipt(external, project):
    bundle = external.bundle.with_name(f"{project}_preprocessed.txt")
    bundle.write_bytes(external.bundle.read_bytes())
    chunks, _ = chunking.write_manifest_for(bundle)
    manifest = yaml.safe_load(external.manifest.read_bytes())
    manifest["projects"] = {project: manifest["projects"]["EXTERNAL"]}
    manifest["projects"][project]["bundle"] = str(bundle)
    manifest["naming"] = {project: manifest["naming"]["EXTERNAL"]}
    external.manifest.write_text(yaml.safe_dump(manifest))
    base = replace(external, project=project, bundle=bundle, chunk_manifest=chunks)
    spec = selected_spec(base, registration_for(base))
    spec.bind_api_header_values(api._model_settings())
    instruction = spec.instruction
    assert "Shared generation rules v1" in instruction
    assert "Role relationship review v1" in instruction
    assert str(bundle) in instruction
    # Word boundaries retain the adult/pediatric distinction, rather than
    # treating VOICE's prefix in VOICE_PEDIATRIC as another project.
    for other in ALL_PROJECTS:
        if other != project:
            assert re.search(rf"\b{re.escape(other)}\b", instruction) is None
            assert f"{other}_preprocessed.txt" not in instruction
    assert set(re.findall(r"[\w.-]+_preprocessed\.txt", instruction)) == {bundle.name}
    assert spec.condition in api.RECEIPT_CONDITIONS
    assert spec.writes_receipt is True
    selected = policy.select_policy(render_spec=spec.render_spec())
    assert selected["registration"]["condition"] == "generic_v10"
    assert selected["registration"]["format"] == "receipt_completion_registration_v2"
    # The new receipt obligation does not grant legacy/native admission.
    with pytest.raises(ValueError, match="requires shared generation 1"):
        replace(base, condition="generic_v10")
    with pytest.raises(ValueError):
        replace(spec, runtime="Claude Code")


def test_installed_guard_identity_does_not_invent_a_predecessor(tmp_path, monkeypatch):
    from data_sheets_schema import agent_pin, resources

    name = "d4d-provenance-guard-v2"
    root = Path(__file__).resolve().parents[1]
    installed = tmp_path / "package-resources"
    for relative in (f".claude/agents/{name}.md", ".claude/agents/_preimages.json"):
        target = installed / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / relative).read_bytes())
    raw = (installed / f".claude/agents/{name}.md").read_bytes()
    row = json.loads((installed / ".claude/agents/_preimages.json").read_bytes())["agents"][name]
    assert row == {"current_sha256": hashlib.sha256(raw).hexdigest(),
                   "previous_text": None, "previous_sha256": None}
    monkeypatch.setattr(resources, "resource_root", lambda: (installed, "install"))
    monkeypatch.setattr(resources, "resource_path", lambda relative: installed / relative)
    monkeypatch.setattr(agent_pin, "_git", lambda *a, **k: pytest.fail("installed identity consulted Git"))
    assert agent_pin.agent_digest(name) == row["current_sha256"]
    assert agent_pin._previous_text(name) is None
    assert agent_pin.challenge(name) is None
    with pytest.raises(agent_pin.NoDiscriminatingChallenge):
        agent_pin.spawn_preamble(name)
    with pytest.raises(agent_pin.NoDiscriminatingChallenge):
        agent_pin.verify_echo(name, raw.decode())
    assert agent_pin.echoed(name, raw.decode()) is False
