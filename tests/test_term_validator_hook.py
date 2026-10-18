"""Hook status describes the selected bytes, without invoking ontology services."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest


SCHEMA_DIRECTORY = Path("src/data_sheets_schema/schema")
GENERATED_SCHEMA = "data_sheets_schema_all.yaml"


@pytest.fixture
def hook(monkeypatch, tmp_path):
    source = Path(__file__).resolve().parents[1] / ".claude/hooks/term_validator_hook.py"
    spec = importlib.util.spec_from_file_location("term_validator_hook_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    (tmp_path / SCHEMA_DIRECTORY).mkdir(parents=True)

    def forbidden(*args, **kwargs):
        pytest.fail("unexpected validator invocation")

    monkeypatch.setattr(module.subprocess, "run", forbidden)
    return module


def invoke(hook, monkeypatch, capsys, paths, tool="Edit"):
    tool_input = ({"edits": [{"file_path": str(path)} for path in paths]} if tool == "MultiEdit"
                  else {"file_path": str(paths[0])})
    monkeypatch.setattr(hook.sys, "stdin", io.StringIO(json.dumps({"tool_name": tool, "tool_input": tool_input})))
    with pytest.raises(SystemExit) as stopped:
        hook.main()
    assert stopped.value.code == 0
    return capsys.readouterr()


@pytest.mark.parametrize("name", ["D4D_Metadata.yaml", "data_sheets_schema.yaml"])
def test_source_edit_reports_pending_without_checking_stale_generated_file(hook, monkeypatch, tmp_path, capsys, name):
    schema = tmp_path / SCHEMA_DIRECTORY
    source = schema / name
    source.write_text("new source bytes\n")
    (schema / GENERATED_SCHEMA).write_text("old merged bytes\n")
    output = invoke(hook, monkeypatch, capsys, [source])
    assert "pending regeneration" in output.out and "has not validated the edited source" in output.out
    assert "make regen-all" in output.out and "validate-schema" in output.out
    assert "passed" not in output.out and not output.err
    success, message = hook.validate_ontology_terms(str(source))
    assert success and "pending regeneration" in message and "passed" not in message


@pytest.mark.parametrize("relative", ["D4D_Metadata.yaml", "elsewhere/D4D_Metadata.yaml",
    "elsewhere/data_sheets_schema.yaml", "elsewhere/data_sheets_schema_all.yaml",
    "src/data_sheets_schema/schema/nested/D4D_Metadata.yaml", "src/data_sheets_schema/schema/other.yaml"])
def test_same_basename_outside_schema_directory_does_not_trigger(hook, monkeypatch, capsys, relative):
    output = invoke(hook, monkeypatch, capsys, [relative])
    assert not output.out and not output.err


def test_relative_paths_and_absent_project_variable_use_project_cwd(hook, monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("CLAUDE_PROJECT_DIR")
    monkeypatch.chdir(tmp_path)
    selected = SCHEMA_DIRECTORY / "D4D_Metadata.yaml"
    output = invoke(hook, monkeypatch, capsys, [selected], tool="Write")
    assert "pending regeneration" in output.out
    assert hook.is_d4d_schema_file(str(tmp_path / selected))
    assert not hook.is_d4d_schema_file("D4D_Metadata.yaml")


def test_relative_path_uses_declared_project_from_another_cwd(hook, monkeypatch, tmp_path, capsys):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    selected = SCHEMA_DIRECTORY / ".." / "schema" / "D4D_Metadata.yaml"
    output = invoke(hook, monkeypatch, capsys, [selected])
    assert "pending regeneration" in output.out and not output.err


def test_schema_symlink_to_an_unrelated_file_is_not_a_project_source(hook, monkeypatch, tmp_path, capsys):
    outside = tmp_path / "outside.yaml"
    outside.write_text("unrelated\n")
    alias = tmp_path / SCHEMA_DIRECTORY / "D4D_Metadata.yaml"
    try:
        alias.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")
    output = invoke(hook, monkeypatch, capsys, [alias])
    assert not output.out and not output.err


def test_generated_edit_checks_that_exact_file_once_and_limits_success_claim(hook, monkeypatch, tmp_path, capsys):
    generated = tmp_path / SCHEMA_DIRECTORY / GENERATED_SCHEMA
    generated.write_text("selected merged bytes\n")
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        assert Path(args[-1]).read_text() == "selected merged bytes\n"
        return SimpleNamespace(returncode=0, stdout="INFO noise\n", stderr="")

    monkeypatch.setattr(hook.subprocess, "run", run)
    output = invoke(hook, monkeypatch, capsys, [generated, SCHEMA_DIRECTORY / GENERATED_SCHEMA], tool="MultiEdit")
    assert calls == [(["poetry", "run", "linkml-term-validator", "validate-schema", str(generated)],
                     {"capture_output": True, "text": True, "timeout": 60, "cwd": tmp_path})]
    assert f"passed for generated schema: {generated}" in output.out
    assert "synchronization is not established" in output.out and not output.err


@pytest.mark.parametrize("source_first", [False, True])
def test_source_and_generated_batch_stays_pending_in_both_orders(hook, monkeypatch, tmp_path, capsys, source_first):
    generated = tmp_path / SCHEMA_DIRECTORY / GENERATED_SCHEMA
    generated.write_text("old merged bytes\n")
    source = generated.with_name("D4D_Metadata.yaml")
    paths = [source, generated] if source_first else [generated, source]
    output = invoke(hook, monkeypatch, capsys, paths, tool="MultiEdit")
    assert output.out.count("pending regeneration") == 1
    assert "passed" not in output.out and not output.err


@pytest.mark.parametrize("outcome", ["failure", "timeout", "missing_tool", "error", "missing_file"])
def test_generated_failures_and_skips_remain_warning_only(hook, monkeypatch, tmp_path, capsys, outcome):
    generated = tmp_path / SCHEMA_DIRECTORY / GENERATED_SCHEMA
    if outcome != "missing_file":
        generated.write_text("selected\n")

        def run(*args, **kwargs):
            if outcome == "timeout":
                raise subprocess.TimeoutExpired("validator", 60)
            if outcome == "missing_tool":
                raise FileNotFoundError("poetry")
            if outcome == "error":
                raise OSError("validator unavailable")
            return SimpleNamespace(returncode=1, stdout="INFO noise\nDEBUG noise\nunknown term\n", stderr="bad ontology\n")

        monkeypatch.setattr(hook.subprocess, "run", run)
    output = invoke(hook, monkeypatch, capsys, [generated])
    assert "passed" not in output.out + output.err
    if outcome == "failure":
        assert "Warning:" in output.err and "unknown term" in output.err and "bad ontology" in output.err
        assert "noise" not in output.err and not output.out
    else:
        assert "skipping" in output.out and not output.err


def test_unhandled_tool_and_invalid_json_remain_noops(hook, monkeypatch, capsys):
    selected = SCHEMA_DIRECTORY / GENERATED_SCHEMA
    output = invoke(hook, monkeypatch, capsys, [selected], tool="Bash")
    assert not output.out and not output.err
    monkeypatch.setattr(hook.sys, "stdin", io.StringIO("not JSON"))
    with pytest.raises(SystemExit) as stopped:
        hook.main()
    assert stopped.value.code == 0
    assert not capsys.readouterr().out
