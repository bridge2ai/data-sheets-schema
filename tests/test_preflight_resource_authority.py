"""Adversarial #5122 preparation authority checks, 2026-10-28.

Inputs: copied checkout resources and temporary registrations. Outputs: offline
pytest checks for selected-tree provenance, schema closure, and refusal paths.
No provider calls, historical outputs or real checkout resources are modified.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading

import pytest
from click.testing import CliRunner

from scripts import build_api_registrations as builder
from data_sheets_schema import api_runner as api, shared_generation as sg
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_source_heading_runtime_api import draft_files, selected_spec


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def checkout_unchanged(tmp_path_factory):
    """Include ignored files; exclude Git metadata and this run's scratch tree."""
    scratch = tmp_path_factory.getbasetemp().resolve()

    def snapshot():
        entries = {}
        for directory, dirs, files in os.walk(ROOT):
            base = Path(directory)
            dirs[:] = [name for name in dirs
                       if name != ".git" and (base / name).resolve() != scratch]
            for name in dirs + files:
                path = base / name
                if path == ROOT / ".git":
                    continue
                stat = path.lstat()
                entries[str(path.relative_to(ROOT))] = (
                    stat.st_mode, stat.st_size, stat.st_mtime_ns, stat.st_ino,
                )
        return entries

    before = snapshot()
    yield
    assert snapshot() == before, "test changed the checkout outside pytest's scratch tree"


def _registration(directory):
    return builder.build_registration("CHORUS", "authority", partition="chorus", registration_path=directory / "registration.json", write_to_disk=False)


@pytest.fixture
def selected_resources(tmp_path):
    original = _registration(tmp_path)
    selected = tmp_path / "selected"
    selected.mkdir()
    shutil.copyfile(ROOT / "pyproject.toml", selected / "pyproject.toml")
    sources = [pin for key in ("full_schema", "core_schema") for pin in original["inputs"][key]["sources"]]
    sources.extend([original["runtime"]["config"], original["inputs"]["profile"]["vocabulary"]])
    for pin in sources:
        if pin and Path(pin["path"]).is_relative_to(ROOT):
            source = Path(pin["path"])
            target = selected / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for name, raw in sg.captured_assets().items():
        target = selected / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    args = dict(project="CHORUS", label="selected", registration_path=tmp_path / "selected.json",
                bundle_path=original["inputs"]["bundle"]["path"],
                chunk_manifest_path=original["inputs"]["chunk_manifest"]["path"],
                source_manifest_path=original["inputs"]["source_manifest"]["path"],
                context_path=original["inputs"]["context"]["path"], write_to_disk=False,
                worktree=selected, partition="chorus")
    return selected, original, args


def test_explicit_tree_selects_schema_configuration_and_vocabulary(selected_resources):
    selected, _, args = selected_resources
    before = Path.cwd()
    reg = builder.build_registration(**args)
    assert Path.cwd() == before
    for key in ("full_schema", "core_schema"):
        assert Path(reg["inputs"][key]["root"]).is_relative_to(selected)
    assert Path(reg["runtime"]["config"]["path"]).is_relative_to(selected)
    assert Path(reg["inputs"]["profile"]["vocabulary"]["path"]).is_relative_to(selected)
    builder.verify_registration_input_pins(reg, worktree=selected)
    assert Path.cwd() == before


def test_default_kids_first_manifest_comes_from_selected_tree(selected_resources):
    selected, _, args = selected_resources
    relative = Path("notes/matched_cborg_2026-09-13/kids_first/manifest.yaml")
    manifest = selected / relative
    manifest.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / relative, manifest)
    args.pop("source_manifest_path")
    args["project"] = "KIDS_FIRST"
    args.pop("partition")
    # Mechanics-only manifest/authority fixture, not a Kids First sizing claim.
    # A17 requires explicit input sizing outside the CHORUS profile; deliberately
    # declare this fixture's CHORUS record as a stand-in rather than bypassing it.
    args["audit_limits"] = {"max_paths": 80, "max_inventory_bytes": 12288, "max_workers": 4,
                            "aggregate_input_tokens": 4000000}
    args["sizing_record"] = builder.SizingRecord.in_directory(
        ROOT / "tests/fixtures/audit_batches/chorus_v10_2026-10-22a", "CHORUS")
    args["sizing_stand_in"] = True
    reg = builder.build_registration(**args)
    assert reg["inputs"]["source_manifest"] == sg.file_pin(manifest)
    assert reg["inputs"]["profile"]["name"] == "neutral"


@pytest.mark.parametrize("resource", ["prompt", "config", "vocabulary", "full_schema", "core_schema"])
def test_missing_selected_resource_refuses_without_fallback(selected_resources, resource):
    selected, original, args = selected_resources
    if resource == "prompt":
        relative = next(iter(sg.ASSET_HASHES))
    elif resource == "config":
        relative = Path(original["runtime"]["config"]["path"]).relative_to(ROOT)
    elif resource == "vocabulary":
        relative = Path(original["inputs"]["profile"]["vocabulary"]["path"]).relative_to(ROOT)
    else:
        relative = Path(original["inputs"][resource]["root"]).relative_to(ROOT)
    target = selected / relative
    target.unlink()
    before = Path.cwd()
    with pytest.raises((OSError, ValueError)):
        builder.build_registration(**args)
    assert Path.cwd() == before
    assert (ROOT / relative).is_file()  # The other checkout still supplies it.


def test_selected_prompt_drift_is_not_hidden_by_callers_valid_prompt(selected_resources):
    selected, _, args = selected_resources
    prompt = selected / next(iter(sg.ASSET_HASHES))
    prompt.write_bytes(prompt.read_bytes() + b"\n")
    before = Path.cwd()
    with pytest.raises(ValueError, match="asset|SHA|hash"):
        builder.build_registration(**args)
    assert Path.cwd() == before


def test_check_uses_selected_prompt_authority_and_restores_cwd(selected_resources):
    selected, _, args = selected_resources
    reg = builder.build_registration(**args)
    prompt = selected / next(iter(sg.ASSET_HASHES))
    prompt.write_bytes(prompt.read_bytes() + b"\n")
    before = Path.cwd()
    with pytest.raises(ValueError, match="asset|SHA|hash"):
        builder.verify_registration_input_pins(reg, worktree=selected)
    assert Path.cwd() == before


def test_positional_draft_context_worktree_selects_vocabulary(selected_resources, checkout_unchanged):
    selected, _, _ = selected_resources
    assert not builder.DEFAULT_VOCABULARIES_PATH.is_absolute()
    vocabulary = selected / "src/data_sheets_schema/b2ai_registry_vocabularies.yaml"
    vocabulary.write_text("vocabularies:\n  SELECTED_TREE: [selected-only]\n")
    before = Path.cwd()
    doc = builder.build_draft_context("CHORUS", None, None, False, selected)
    assert doc["vocabulary"] == {"SELECTED_TREE": ["selected-only"]}
    assert Path.cwd() == before


def test_foreign_tree_refused_while_other_thread_active(selected_resources):
    _, _, args = selected_resources
    stop = threading.Event()
    thread = threading.Thread(target=stop.wait)
    before = Path.cwd()
    thread.start()
    try:
        with pytest.raises(ValueError, match="single-threaded"):
            builder.build_registration(**args)
    finally:
        stop.set()
        thread.join(timeout=5)
    assert not thread.is_alive()
    assert Path.cwd() == before


@pytest.mark.parametrize("invalid", ["missing", "unknown_profile", "aggregate"])
def test_partition_refusal_precedes_draft_context_writes(tmp_path, selected_resources, invalid):
    _, _, args = selected_resources
    output = tmp_path / "must-stay-absent"
    args.pop("context_path")
    args.update(registration_path=output / "registration.json", context_dir=output / "contexts",
                synthesize_draft_context=True, write_to_disk=True)
    if invalid == "missing":
        args.pop("partition")
    elif invalid == "unknown_profile":
        args["partition"] = "unknown"
    else:
        args["audit_limits"] = {"aggregate_output_tokens": 1}
    with pytest.raises(ValueError, match="partition|aggregate_output_tokens"):
        builder.build_registration(**args)
    assert not output.exists(), "refused registration created draft output before validating bounds"


def test_valid_partition_still_publishes_requested_draft(tmp_path, selected_resources):
    _, _, args = selected_resources
    output = tmp_path / "valid-draft"
    args.pop("context_path")
    args.update(registration_path=output / "registration.json", context_dir=output / "contexts",
                synthesize_draft_context=True, write_to_disk=True)
    reg = builder.build_registration(**args)
    assert Path(reg["registration_path"]).is_file()
    assert Path(reg["inputs"]["context"]["path"]) == output / "contexts" / "chorus_omission_context.json"
    assert reg["inputs"]["context"] == sg.file_pin(Path(reg["inputs"]["context"]["path"]))
    assert reg["audit_limits"] == builder.resolve_audit_limits("CHORUS", "chorus")


@pytest.mark.parametrize("schema", ["full_schema", "core_schema"])
@pytest.mark.parametrize("mutation", ["drift", "missing", "unregistered_import", "extra_source"])
def test_schema_import_closure_refuses_changes(tmp_path, schema, mutation):
    reg = _registration(tmp_path)
    root = tmp_path / "schema.yaml"
    imported = tmp_path / "part.yaml"
    root.write_text("id: https://example.org/root\nname: root\nimports: [part]\n")
    imported.write_text("id: https://example.org/part\nname: part\nclasses:\n  Dataset: {}\n")
    reg["inputs"][schema] = sg.schema_pin(capture_schema(root, strict=True))
    builder.verify_registration_input_pins(reg)
    if mutation == "drift":
        imported.write_bytes(imported.read_bytes() + b"\n")
    elif mutation == "missing":
        imported.unlink()
    elif mutation == "unregistered_import":
        reg["inputs"][schema]["sources"] = reg["inputs"][schema]["sources"][:1]
    else:
        extra = tmp_path / "unused.yaml"
        extra.write_text("id: https://example.org/extra\nname: extra\n")
        reg["inputs"][schema]["sources"].append(sg.file_pin(extra))
    with pytest.raises((OSError, ValueError)):
        builder.verify_registration_input_pins(reg)


@pytest.mark.parametrize("mutation", ["drift", "missing"])
def test_v2_routing_artifact_pin_refuses_changes(tmp_path, draft_files, mutation):
    spec = selected_spec(tmp_path, draft_files)
    reg = sg.parse_registration(spec.shared_generation_registration.encode())
    assert reg["format"] == sg.ROUTING_FORMAT
    builder.verify_registration_input_pins(reg)
    artifact = Path(reg["routing"]["artifact"]["path"])
    if mutation == "drift":
        artifact.write_bytes(artifact.read_bytes() + b"\n")
    else:
        artifact.unlink()
    with pytest.raises((OSError, ValueError), match=r"routing\.artifact"):
        builder.verify_registration_input_pins(reg)


@pytest.mark.parametrize("options", [lambda p: ["--worktree", p], lambda p: ["--worktree=" + p], lambda p: ["-w", p], lambda p: ["-w" + p]])
def test_bootstrap_parses_supported_worktree_spellings(tmp_path, options):
    assert builder._bootstrap_worktree(["--label", "--worktree", *options(str(tmp_path))]) == tmp_path
    assert builder._bootstrap_worktree(["--label", "--worktree"]) is None


@pytest.mark.parametrize("option", ["--worktree=", "-w"])
def test_copied_cli_selects_foreign_tree_from_another_checkout(tmp_path, option, checkout_unchanged):
    selected = tmp_path / "selected"
    selected.mkdir()
    shutil.copyfile(ROOT / "pyproject.toml", selected / "pyproject.toml")
    shutil.copytree(ROOT / "src" / "data_sheets_schema", selected / "src" / "data_sheets_schema",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name, raw in sg.captured_assets().items():
        target = selected / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    config = selected / api.DETERMINISTIC_CONFIG
    config.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / api.DETERMINISTIC_CONFIG, config)
    for relative in ("data/preprocessed/source_manifest.yaml", "data/preprocessed/concatenated/CHORUS_preprocessed.txt",
                     "data/preprocessed/chunks/CHORUS_chunks.yaml", "data/omission_contexts/chorus_omission_context.json"):
        target = selected / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    copied = tmp_path / "caller-inputs" / "build_api_registrations.py"
    copied.parent.mkdir()
    shutil.copyfile(Path(builder.__file__), copied)
    # No site initialization or editable .pth files; dependencies remain the
    # existing interpreter's physical packages. This subprocess only prepares.
    site = Path(sys.executable).parent.parent / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    env = dict(os.environ)
    for key in tuple(env):
        if key.startswith(("ANTHROPIC_", "CBORG_", "OPENAI_", "D4D_")) or key.endswith(("_API_KEY", "_AUTH_TOKEN", "_ACCESS_TOKEN")):
            env.pop(key)
    env.update(PYTHONPATH=str(site), PYTHONDONTWRITEBYTECODE="1", GIT_NO_LAZY_FETCH="1")
    selection = [option + str(selected)] if option.endswith("=") else [option, str(selected)]
    # Python 3.9/3.10 have no -P; the copied script's directory is isolated
    # and contains no importable dependencies on those supported interpreters.
    safe_path = ["-P"] if sys.version_info >= (3, 11) else []
    command = [sys.executable, "-S", *safe_path, "-B", str(copied), "-p", "CHORUS", "--partition", "chorus", "-l", "foreign", "-o", "prepared", *selection]
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    path = selected / "prepared" / "registration_chorus_foreign.json"
    reg = json.loads(path.read_text())
    for key in ("bundle", "chunk_manifest", "source_manifest", "context"):
        assert Path(reg["inputs"][key]["path"]).is_relative_to(selected)
    for key in ("full_schema", "core_schema"):
        assert Path(reg["inputs"][key]["root"]).is_relative_to(selected)
    assert Path(reg["inputs"]["profile"]["vocabulary"]["path"]).is_relative_to(selected)
    assert Path(reg["runtime"]["config"]["path"]).is_relative_to(selected)
    check = subprocess.run([*command, "--check"], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    assert check.returncode == 0, check.stdout + check.stderr


@pytest.mark.parametrize("kind", ["subdirectory", "nested"])
def test_worktree_must_be_checkout_root(selected_resources, kind):
    selected, _, args = selected_resources
    target = selected / kind
    target.mkdir()
    if kind == "nested":
        shutil.copyfile(selected / "pyproject.toml", target / "pyproject.toml")
        (target / "src/data_sheets_schema").mkdir(parents=True)
    args["worktree"] = target
    before = Path.cwd()
    with pytest.raises(ValueError, match="--worktree must be the root of a data-sheets-schema checkout"):
        builder.build_registration(**args)
    assert Path.cwd() == before


@pytest.mark.parametrize("missing_package", [False, True], ids=["mixed-namespace", "missing-package"])
def test_copied_cli_refuses_invalid_import_authority(tmp_path, missing_package):
    selected = tmp_path / "selected"
    package = selected / "src/data_sheets_schema"
    package.mkdir(parents=True)
    if not missing_package:
        (package / "api_runner.py").write_text("# Namespace portion; never execute it.\n")
    copied = tmp_path / "build_api_registrations.py"
    shutil.copyfile(Path(builder.__file__), copied)
    site = Path(sys.executable).parent.parent / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    env = dict(os.environ)
    for key in tuple(env):
        if key.startswith(("ANTHROPIC_", "CBORG_", "OPENAI_", "D4D_")) or key.endswith(("_API_KEY", "_AUTH_TOKEN", "_ACCESS_TOKEN")):
            env.pop(key)
    env.update(PYTHONPATH=os.pathsep.join((str(ROOT / "src"), str(site))), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [sys.executable, "-S", "-B", str(copied), "--worktree", str(selected), "--help"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
    )
    expected = ("--worktree must contain the data_sheets_schema source package" if missing_package
                else "--worktree package imports are mixed with another checkout")
    assert result.returncode != 0
    assert expected in result.stderr
    if not missing_package:
        assert "selected checkout's own venv" in result.stderr
        assert "python -S with site-packages on PYTHONPATH" in result.stderr


def test_synthesized_context_requires_selected_vocabulary(selected_resources, tmp_path):
    selected, original, _ = selected_resources
    (selected / "src/data_sheets_schema/b2ai_registry_vocabularies.yaml").unlink()
    out_dir = tmp_path / "synthesized"
    args = ["-p", "CHORUS", "--partition", "chorus", "-l", "missing_vocab", "-o", str(out_dir),
            "--worktree", str(selected), "--synthesize-draft-context"]
    for option, key in (("--bundle", "bundle"), ("--chunk-manifest", "chunk_manifest"),
                        ("--source-manifest", "source_manifest")):
        args.extend([option, original["inputs"][key]["path"]])
    before = Path.cwd()
    result = CliRunner().invoke(builder.cli, args)
    # A17's prepare-then-write CLI reports preparation failures as Click errors.
    assert result.exit_code == 1, result.output
    assert "selected worktree vocabulary is missing:" in result.output
    assert not out_dir.exists(), "refusal must precede writing a draft context"
    assert Path.cwd() == before
