"""Actual pre-edit historical render identities and selected successor closure."""
import hashlib
import json
from pathlib import Path

import pytest
from data_sheets_schema import api_runner as api, agentic_runtime, shared_generation as shared
from tests import test_renderer_contract_captures as captures

BASELINE = json.loads((Path(__file__).parent / "fixtures/shared_generation_legacy_baseline.json").read_bytes())


def test_selected_assets_are_transitively_bound():
    assert set(shared.captured_assets()) == set(shared.ASSET_HASHES)
    assert shared.descriptor()["runtime"] == api.RUNTIME
    for name in shared.SELECTED_PLAYBOOKS:
        assert name not in agentic_runtime.toolchain()["resources"]


def test_legacy_toolchain_exclusion_is_exact(monkeypatch):
    extra = ".claude/commands/unrelated-v2.md"
    monkeypatch.setattr(agentic_runtime, "resource_names", lambda _: [extra, agentic_runtime.PLAYBOOK, *shared.SELECTED_PLAYBOOKS])
    assert extra in agentic_runtime.toolchain()["resources"]


def test_asset_drift_refuses(monkeypatch, tmp_path):
    from data_sheets_schema import resources
    original = resources.resource_path
    changed = tmp_path / "policy.md"
    changed.write_bytes(original(shared.POLICY).read_bytes() + b" altered")
    monkeypatch.setattr(resources, "resource_path", lambda name: changed if str(name) == shared.POLICY else original(name))
    with pytest.raises(ValueError, match="asset changed"):
        shared.descriptor()


def test_missing_transitive_asset_refuses(monkeypatch, tmp_path):
    from data_sheets_schema import resources
    original = resources.resource_path
    changed = tmp_path / "prompt.md"
    changed.write_bytes(original(shared.PROMPT).read_bytes() + b"\nRead `.claude/commands/unbound.md`.\n")
    monkeypatch.setattr(resources, "resource_path", lambda name: changed if str(name) == shared.PROMPT else original(name))
    monkeypatch.setitem(shared.ASSET_HASHES, shared.PROMPT, shared.sha(changed.read_bytes()))
    with pytest.raises(ValueError, match="unbound selected playbook"):
        shared.captured_assets()


@pytest.fixture(scope="module")
def old_specs(tmp_path_factory):
    path = tmp_path_factory.mktemp("shared-old")
    mp = pytest.MonkeyPatch()
    mp.setattr(agentic_runtime, "toolchain", captures.fixed_toolchain)
    mp.setattr(api, "provider_identity", lambda: {"provider": None, "base_url": None, "key_env": None})
    mp.delenv("D4D_PROFILE", raising=False)
    try:
        yield captures.fixtures(path / "fixtures"), path
    finally:
        mp.undo()


@pytest.mark.parametrize("key,version", [(k, int(v)) for k, rows in BASELINE["instructions"].items() for v in rows])
def test_old_instruction_and_spec_bytes(old_specs, key, version):
    specs, root = old_specs
    spec = captures.replace(specs[key], render_version=version)
    expected = BASELINE["instructions"][key][str(version)]
    text = spec.instruction.replace(str(root), "<BASELINE>")
    raw = json.dumps(spec.render_spec(), sort_keys=True, ensure_ascii=False).replace(str(root), "<BASELINE>")
    assert hashlib.sha256(text.encode()).hexdigest() == expected["instruction_sha256"]
    assert hashlib.sha256(raw.encode()).hexdigest() == expected["spec_sha256"]


def test_old_suffixes_and_assembly_digests():
    for phase, versions in BASELINE["suffixes"].items():
        for version, expected in versions.items():
            assert shared.sha(api.phase_instruction(phase, int(version)).encode()) == expected
    for version, expected in BASELINE["assemblies"].items():
        assert api.assembly_digest(int(version)) == expected


def test_existing_registry_entries_preserved():
    from data_sheets_schema import prompt_registry
    current = prompt_registry.pins()
    for name, entry in BASELINE["registry_entries"]["files"].items():
        assert current[name] == entry
