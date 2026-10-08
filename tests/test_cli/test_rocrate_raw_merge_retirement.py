"""Real CLI retirement controls: no invented merger or replacement producer."""
import builtins
import importlib
import io
import os
from pathlib import Path

from click.testing import CliRunner
import pytest

from data_sheets_schema.cli import cli


MESSAGE = "Raw RO-Crate merging is retired (#4593)"


def assert_retired(result):
    assert result.exit_code == 1, result.output
    assert MESSAGE in result.output
    assert "Keep source crates separate" in result.output
    assert "Merged RO-Crate saved" not in result.output
    assert "D4D YAML saved" not in result.output
    assert "Merging " not in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize("destination", ["new", "existing", "input", "symlink", "hardlink", "directory"])
def test_real_cli_refusal_preserves_sources_and_every_destination(tmp_path, destination):
    source = tmp_path / "crate.json"
    source.write_bytes(b'{"@context":{},"@graph":[{"@id":"./","@type":"Dataset"}]}\n')
    second = tmp_path / "other.json"
    second.write_bytes(b'{"@context":{},"@graph":[{"@id":"./","@type":"Dataset"}]}\n')
    primary = tmp_path / "primary-alias.json"
    primary.symlink_to(second)
    output = tmp_path / "merged.json"
    if destination == "existing":
        output.write_bytes(b"retained historical output\n")
    elif destination == "input":
        output = source
    elif destination == "symlink":
        output.symlink_to(source)
    elif destination == "hardlink":
        os.link(source, output)
    elif destination == "directory":
        output.mkdir()
        (output / "sentinel").write_bytes(b"retained directory contents\n")
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    result = CliRunner().invoke(cli, ["rocrate", "merge", str(source), str(second),
                                     "--primary", str(primary), "--output", str(output)])
    assert_retired(result)
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before
    assert primary.is_symlink()
    if destination == "new":
        assert not output.exists()
    elif destination == "symlink":
        assert output.is_symlink()
    elif destination == "hardlink":
        assert output.stat().st_ino == source.stat().st_ino


@pytest.mark.parametrize("payload", [b"not JSON", b"\xff\xfe undecodable", b"{}"])
def test_refusal_does_not_depend_on_crate_contents(tmp_path, payload):
    source = tmp_path / "crate.json"
    source.write_bytes(payload)
    output = tmp_path / "new.json"
    result = CliRunner().invoke(cli, ["rocrate", "merge", str(source), "-o", str(output)])
    assert_retired(result)
    assert source.read_bytes() == payload and not output.exists()


def test_refusal_precedes_content_io_repo_setup_and_all_producer_imports(tmp_path, monkeypatch):
    source = tmp_path / "crate.json"
    source.write_bytes(b"source sentinel")
    output = tmp_path / "output.json"
    output.write_bytes(b"output sentinel")
    before = source.read_bytes(), output.read_bytes()
    module = importlib.import_module("data_sheets_schema.cli.rocrate")
    guarded_paths = {source.resolve(), output.resolve()}
    original_open, original_io_open, original_import = builtins.open, io.open, builtins.__import__

    def guard_open(operation):
        def guarded(file, *args, **kwargs):
            if isinstance(file, (str, bytes, os.PathLike)):
                path = Path(os.fsdecode(file)).resolve()
                if path in guarded_paths:
                    pytest.fail("retired raw merge opened source or destination contents")
            return operation(file, *args, **kwargs)
        return guarded

    def guard_import(name, *args, **kwargs):
        if name.rsplit(".", 1)[-1] in {"rocrate_merger", "rocrate_to_d4d", "auto_process_rocrates"}:
            pytest.fail("retired raw merge imported a merger or replacement producer")
        return original_import(name, *args, **kwargs)

    def no_repo_setup(*args, **kwargs):
        pytest.fail("retired command attempted repository/helper setup")

    with monkeypatch.context() as patch:
        patch.chdir(tmp_path)
        patch.setattr(module, "require_repo_context", no_repo_setup)
        patch.setattr(module, "setup_repo_imports", no_repo_setup)
        patch.setattr(builtins, "open", guard_open(original_open))
        patch.setattr(io, "open", guard_open(original_io_open))
        patch.setattr(builtins, "__import__", guard_import)
        result = CliRunner().invoke(cli, ["rocrate", "merge", str(source), "-o", str(output)])
    assert_retired(result)
    assert (source.read_bytes(), output.read_bytes()) == before


def test_help_explains_retirement_and_retains_legacy_options():
    runner = CliRunner()
    help_result = runner.invoke(cli, ["rocrate", "merge", "--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "Retired: raw RO-Crate merging is unsupported (#4593)" in help_result.output
    assert "--output" in help_result.output and "--primary" in help_result.output
    assert "never writes an output" in " ".join(help_result.output.split())
    group_help = runner.invoke(cli, ["rocrate", "--help"])
    assert group_help.exit_code == 0, group_help.output
    assert "merge" in group_help.output and "Retired:" in group_help.output


def test_legacy_required_arguments_still_report_usage_errors(tmp_path):
    output = tmp_path / "new.json"
    result = CliRunner().invoke(cli, ["rocrate", "merge", "-o", str(output)])
    assert result.exit_code == 2
    assert "Missing argument" in result.output and not output.exists()
