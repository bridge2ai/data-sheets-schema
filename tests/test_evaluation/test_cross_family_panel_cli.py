"""CLI registration tests with invented data and no rating execution."""
import json
import socket

from click.testing import CliRunner
import pytest

from data_sheets_schema import cross_family_panel as panel
from data_sheets_schema.cli.evaluate import evaluate
from tests.test_evaluation.test_cross_family_panel import build_fixture, write_declaration


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refused(*args, **kwargs):
        pytest.fail("offline panel command attempted network access")
    monkeypatch.setattr(socket.socket, "connect", refused)


def test_cli_prepares_and_rechecks_without_accepting_ratings(tmp_path):
    root, declaration, path = build_fixture(tmp_path)
    output = tmp_path / "panel"
    before = path.read_bytes()
    runner = CliRunner()
    prepared = runner.invoke(evaluate, ["cross-family-panel", "prepare",
        "--declaration", str(path), "--root", str(root), "--output", str(output)])
    assert prepared.exit_code == 0, prepared.output
    expected = json.loads(prepared.output)
    assert expected == panel.recheck_panel(output)
    assert expected["execution_authorized"] is False
    assert expected["scientific_eligibility"] is False
    assert expected["pending_decisions"]
    checked = runner.invoke(evaluate, ["cross-family-panel", "recheck", "--panel", str(output)])
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.output) == expected
    assert path.read_bytes() == before


def test_cli_rejects_duplicate_attempt_before_output_and_preserves_existing_panel(tmp_path):
    root, declaration, path = build_fixture(tmp_path)
    output = tmp_path / "panel"
    panel.prepare_panel(path, output, root=root)
    before = (output / "panel.json").read_bytes()
    runner = CliRunner()
    repeated = runner.invoke(evaluate, ["cross-family-panel", "prepare",
        "--declaration", str(path), "--root", str(root), "--output", str(output)])
    assert repeated.exit_code != 0 and "Error:" in repeated.output
    assert (output / "panel.json").read_bytes() == before
    declaration["slots"][1]["attempt_id"] = declaration["slots"][0]["attempt_id"]
    write_declaration(path, declaration)
    invalid = tmp_path / "invalid"
    refused = runner.invoke(evaluate, ["cross-family-panel", "prepare",
        "--declaration", str(path), "--root", str(root), "--output", str(invalid)])
    assert refused.exit_code != 0 and "Error:" in refused.output
    assert "duplicate attempt_id" in refused.output
    assert not invalid.exists()
