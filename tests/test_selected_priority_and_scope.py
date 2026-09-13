"""Every playbook decision uses the same selected source registry."""
import copy
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import source_priority
from data_sheets_schema.cli import cli
from tests.test_agentic_selected_playbook import selected, commands
from tests.test_generation_manifest_identity import external


@pytest.fixture
def rankings(tmp_path, monkeypatch):
    selected_data = {"projects": {"EXTERNAL": {"sources": [
        {"id": "source_a", "source_type": "first"}, {"id": "source_b", "source_type": "second"}]}},
        "source_priority": {1: ["first"], 2: ["second"]}}
    ambient = copy.deepcopy(selected_data)
    ambient["source_priority"] = {1: ["second"], 2: ["first"]}
    monkeypatch.setattr(source_priority, "_manifest", lambda: ambient)
    path = tmp_path / "chosen registry.yaml"
    path.write_text(yaml.safe_dump(selected_data))
    return path


@pytest.mark.parametrize("selector", ["root", "environment"])
@pytest.mark.parametrize("operation", ["list", "decide", "tiers", "strict", "strict-decide"])
def test_priority_helpers_obey_selected_registry_even_when_ambient_priorities_conflict(rankings, selector, operation):
    prefix = ["--manifest", str(rankings)] if selector == "root" else []
    env = {"D4D_MANIFEST": str(rankings)} if selector == "environment" else {}
    args = ["download", "priority"]
    if operation != "tiers":
        args += ["--project", "EXTERNAL"]
    if operation in {"decide", "strict-decide"}:
        args += ["--decide", "source_a,source_b"]
    if operation.startswith("strict"):
        data = yaml.safe_load(rankings.read_bytes())
        data["projects"]["EXTERNAL"]["sources"].append({"id": "unranked", "source_type": "uncovered"})
        rankings.write_text(yaml.safe_dump(data))
        args += ["--strict"]
    result = CliRunner().invoke(cli, prefix + args, env=env)
    assert result.exit_code == (1 if operation.startswith("strict") else 0), result.output
    if operation in {"decide", "strict-decide"}:
        assert "winner: source_a" in result.output
    elif operation == "tiers":
        assert "tier 1  first" in result.output
    else:
        assert result.output.index("source_a") < result.output.index("source_b")
    if operation.startswith("strict"):
        assert "uncovered" in result.output


@pytest.mark.parametrize("shape", ["list", "mapping"])
@pytest.mark.parametrize("known", [False, True])
def test_prescribed_scope_commands_accept_both_source_shapes_and_refuse_unknown_references(selected, shape, known):
    spec = selected
    data = yaml.safe_load(spec.manifest.read_bytes())
    entry = data["projects"][spec.project]
    if shape == "list":
        data["projects"][spec.project] = entry["sources"]
    data["scope"][spec.project]["related_but_distinct"][0]["in_bundle"] = "protocol" if known else "absent-source"
    spec.manifest.write_text(yaml.safe_dump(data))
    for path in (spec.full_path, spec.core_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("id: example:cohort\n")
    for args in commands(spec):
        if args[:2] != ["download", "scope"]:
            continue
        result = CliRunner().invoke(cli, args)
        assert result.exit_code == (0 if known else 1), result.output
        if known and "--check" in args:
            assert "2 record(s) checked" in result.output
        if not known:
            assert "absent-source" in result.output
