"""G2 round 2 review regressions; offline authority and pre-billing checks, 2026-11-01."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import audit_omissions as om, bc1_context as bc, profiles
from data_sheets_schema.schema_snapshot import capture_schema
from scripts import build_api_registrations as builder
from tests.test_bc1_context import fixture, policy
from tests.test_bc1_context import fixture as context_fixture
from tests.test_bc1_registration import sizing_fixture
from tests.test_bc1_selection import external, simulated_hooks, registered
from tests.utils.partition_resources import copy_partition_resources


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


@pytest.fixture
def declaration(tmp_path, monkeypatch):
    """Isolated config authority; real CHORUS calibration bytes, no data edits."""
    root = tmp_path / "checkout"
    (root / "config").mkdir(parents=True)
    copy_partition_resources(root)
    manifest = tmp_path / "manifest.yaml"
    original = builder.ROOT / "data/preprocessed/source_manifest.yaml"
    manifest.write_bytes(original.read_bytes())
    config = root / builder.AUDIT_PARTITION_FILES[0]
    doc = yaml.safe_load(config.read_bytes())
    row = doc["projects"]["CHORUS"]["audit_partition"]
    # Compatible with the reviewed head, which has no manifest pin yet.
    row.pop("source_manifest_sha256", None)
    for value in row["sizing_record"].values():
        value["path"] = str(root / value["path"])
    config.write_text(yaml.safe_dump(doc))
    monkeypatch.setattr(builder, "ROOT", root)
    monkeypatch.chdir(root)
    return root, manifest, config, doc


def save(config, doc):
    config.write_text(yaml.safe_dump(doc))


def calibration_case(sizing_fixture, tmp_path, monkeypatch, project):
    """A real, explicitly sized bundle; config authority is an explicit worktree."""
    registration, files, inputs = sizing_fixture
    root = tmp_path / "calibration-root"
    (root / "config").mkdir(parents=True)
    copy_partition_resources(root)
    (root / "src").symlink_to(builder.ROOT / "src", target_is_directory=True)
    (root / ".github").symlink_to(builder.ROOT / ".github", target_is_directory=True)
    (root / ".claude").symlink_to(builder.ROOT / ".claude", target_is_directory=True)
    (root / "pyproject.toml").write_bytes((builder.ROOT / "pyproject.toml").read_bytes())
    config = root / builder.AUDIT_PARTITION_FILES[0]
    save(config, {"projects": {}})
    monkeypatch.setattr(builder.api, "FULL_SCHEMA_PATH", inputs["schema_path"])
    monkeypatch.setattr(builder.api, "CORE_SCHEMA_PATH", inputs["schema_path"])
    manifest = Path(registration["inputs"]["source_manifest"]["path"])
    save(manifest, {"profile": "neutral", "projects": {project: {"sources": [
        {"id": "source", "processed_file": "source.txt", "source_type": "documentation"}]}}})
    for key in ("full", "core"):
        path = getattr(files, key)
        path.write_bytes(path.read_bytes().replace(b"KIDS_FIRST", project.encode()).replace(
            b"# Arm: de novo", ("# Arm: " + builder.ARMS["baseline"][0]).encode()))
    limits = {"max_paths": 80, "max_inventory_bytes": 12288, "max_workers": 4,
              "aggregate_input_tokens": 4000000}
    options = dict(source_manifest_path=manifest, worktree=root, audit_limits=limits,
        bundle_path=registration["inputs"]["bundle"]["path"],
        chunk_manifest_path=registration["inputs"]["chunk_manifest"]["path"],
        context_path=registration["inputs"]["context"]["path"], profile_name="neutral",
        registration_path=tmp_path / "calibration.json")
    reg, _, sized = builder.prepare_registration(project, "calibration", **options,
        sizing_record=builder.SizingRecord(files.full, files.core, files.receipt))
    entry = {"name": "fixture", "arms": ["baseline"], "limits": limits,
        "source_manifest_sha256": pin(manifest)["sha256"],
        "sizing_record": {key: pin(getattr(files, key)) for key in ("full", "core", "receipt")}}
    def covered(value, **overrides):
        save(config, {"projects": {project: {"audit_partition": value}}})
        return builder.profile_covered(project, "baseline", {**reg["audit_limits"], **value["limits"], **overrides},
            source_manifest=manifest, root_dir=root, registration=reg)
    assert sized["aggregate_input_tokens"] < limits["aggregate_input_tokens"]
    assert covered(entry)
    return entry, covered, options, reg, files


@pytest.mark.parametrize("project", ["CHORUS", "SYNTHETIC"])
@pytest.mark.parametrize("damage", ["missing_manifest_pin", "foreign_manifest", "full", "core", "receipt", "low_allowance"])
def test_calibration_must_be_earned(sizing_fixture, tmp_path, monkeypatch, project, damage):
    profile, covered, _, _, _ = calibration_case(sizing_fixture, tmp_path, monkeypatch, project)
    profile = deepcopy(profile)
    if damage == "missing_manifest_pin":
        del profile["source_manifest_sha256"]
    elif damage == "foreign_manifest":
        profile["source_manifest_sha256"] = "0" * 64
    elif damage in {"full", "core", "receipt"}:
        path = tmp_path / ("invalid-" + damage + ".yaml")
        path.write_text("not a coverage receipt\n" if damage == "receipt" else
            f"# D4D Datasheet for {project} Dataset\n# Arm: {builder.ARMS['baseline'][0]}\nnot: [valid\n")
        profile["sizing_record"][damage] = pin(path)
    else:
        profile["limits"]["aggregate_input_tokens"] = 1000
    assert not covered(profile)


@pytest.mark.parametrize("project", ["CHORUS", "SYNTHETIC"])
def test_real_1000_token_preparation_requires_sizing(sizing_fixture, tmp_path, monkeypatch, project):
    entry, covered, options, _, _ = calibration_case(sizing_fixture, tmp_path, monkeypatch, project)
    assert builder.prepare_registration(project, "positive", **options, sizing_record=None)[2] is None
    entry["limits"]["aggregate_input_tokens"] = 1000
    covered(entry)  # Persist the one changed allowance; the manifest pin stays valid.
    with pytest.raises(ValueError, match="needs a sizing record"):
        builder.prepare_registration(project, "round2-low", **options, sizing_record=None)
    assert not options["registration_path"].exists()


@pytest.mark.parametrize("project", ["CHORUS", "SYNTHETIC"])
@pytest.mark.parametrize("damage", ["bundle_md5", "chunk_id", "both"])
def test_foreign_receipt_cannot_earn_coverage(sizing_fixture, tmp_path, monkeypatch, project, damage):
    entry, covered, options, _, files = calibration_case(sizing_fixture, tmp_path, monkeypatch, project)
    assert builder.prepare_registration(project, "positive", **options)[2] is None
    receipt = yaml.safe_load(files.receipt.read_bytes())
    if damage in {"bundle_md5", "both"}:
        receipt["bundle_md5"] = "0" * 32
    if damage in {"chunk_id", "both"}:
        receipt["chunks"][0]["id"] = "unrelated-bundle-chunk"
    save(files.receipt, receipt)
    entry["sizing_record"]["receipt"] = pin(files.receipt)
    assert not covered(entry)
    with pytest.raises(ValueError, match="needs a sizing record"):
        builder.prepare_registration(project, "foreign", **options)
    # Explicit historical sizing keeps its permissive byte-estimation contract.
    assert builder.prepare_registration(project, "explicit", **options,
        sizing_record=builder.SizingRecord(files.full, files.core, files.receipt))[2]


@pytest.mark.parametrize("project", ["CHORUS", "SYNTHETIC"])
def test_declared_historical_bundle_is_verified(sizing_fixture, tmp_path, monkeypatch, project):
    from data_sheets_schema.chunking import manifest_from_bytes
    entry, covered, _, _, files = calibration_case(sizing_fixture, tmp_path, monkeypatch, project)
    bundle = tmp_path / "historical.txt"
    bundle.write_bytes(b"FILE: historical.txt\nPATH: historical.txt\nAn older source.\n")
    chunks = tmp_path / "historical-chunks.yaml"
    mapping = manifest_from_bytes(bundle.read_bytes(), bundle.name)
    save(chunks, mapping)
    save(files.receipt, {"bundle_md5": mapping["bundle_md5"], "chunks": [
        {"id": item["id"], "status": "nothing_relevant"} for item in mapping["chunks"]]})
    entry["sizing_record"]["receipt"] = pin(files.receipt)
    assert not covered(entry)
    entry["calibration_bundle"] = {"bundle": pin(bundle), "chunk_manifest": pin(chunks)}
    assert covered(entry)
    bundle.write_bytes(bundle.read_bytes() + b"changed\n")
    with pytest.raises(ValueError, match="pin changed"):
        covered(entry)


def test_conflicting_authorities_name_both_files_and_project(declaration):
    root, manifest, config, doc = declaration
    row = deepcopy(doc["projects"]["CHORUS"])
    row["sources"] = []
    row["audit_partition"]["limits"]["max_workers"] = 16
    manifest.write_text(yaml.safe_dump({"projects": {"CHORUS": row}}))
    with pytest.raises(ValueError) as error:
        builder.partition_profiles(manifest)
    assert all(text in str(error.value) for text in (str(manifest), str(config), "CHORUS"))


def test_identical_authorities_are_allowed(declaration):
    root, manifest, config, doc = declaration
    row = deepcopy(doc["projects"]["CHORUS"])
    row["sources"] = []
    manifest.write_text(yaml.safe_dump({"projects": {"CHORUS": row}}))
    assert builder.resolve_audit_limits("CHORUS", "chorus", source_manifest=manifest)["max_workers"] == 4


@pytest.mark.parametrize("bad", [None, [], {}, {"projects": []}, {"projects": {"CHORUS": None}},
                                     {"projects": {"CHORUS": {"audit_partition": None}}}])
def test_bad_external_shape_names_its_file(declaration, bad):
    root, manifest, config, doc = declaration
    save(config, bad)
    with pytest.raises(ValueError, match=str(config)):
        builder.partition_profiles(manifest)


def test_bad_inline_entry_names_manifest(declaration):
    root, manifest, config, doc = declaration
    save(config, {"projects": {}})
    manifest.write_text("projects: {CHORUS: {sources: [], audit_partition: null}}\n")
    with pytest.raises(ValueError, match=str(manifest)):
        builder.partition_profiles(manifest)


@pytest.mark.parametrize("cwd", ["tmp", "src", "outside", "planted"])
def test_partition_authority_ignores_cwd(tmp_path, monkeypatch, cwd):
    source = builder.ROOT
    where = source / "src" if cwd == "src" else tmp_path / cwd
    where.mkdir(exist_ok=True)
    if cwd == "planted":
        (where / "config").mkdir()
        (where / "config/audit_partitions.yaml").write_text("projects: {CHORUS: null}\n")
    monkeypatch.chdir(where)
    limits = builder.resolve_audit_limits("CHORUS", "chorus",
        source_manifest=source / "data/preprocessed/source_manifest.yaml")
    assert limits["max_workers"] == 4


def test_explicit_root_selects_config_and_relative_pins(declaration, monkeypatch, tmp_path):
    root, manifest, config, doc = declaration
    record = doc["projects"]["CHORUS"]["audit_partition"]["sizing_record"]
    for key, value in record.items():
        target = root / (key + ".yaml")
        target.write_bytes(Path(value["path"]).read_bytes())
        value["path"] = target.name
    save(config, doc)
    monkeypatch.setattr(builder, "ROOT", Path(builder.__file__).resolve().parents[1])
    monkeypatch.chdir(tmp_path)
    assert builder.partition_profiles(manifest, root_dir=root)["chorus"]["limits"]["max_workers"] == 4


@pytest.mark.parametrize("missing", ["config", "full"])
def test_partition_io_error_names_file(declaration, missing):
    root, manifest, config, doc = declaration
    target = config if missing == "config" else root / "absent-full.yaml"
    if missing == "config":
        config.unlink()
    else:
        doc["projects"]["CHORUS"]["audit_partition"]["sizing_record"]["full"]["path"] = str(target)
        save(config, doc)
    with pytest.raises(ValueError, match=str(target)):
        builder.partition_profiles(manifest)


def change_annotation(fixture, annotation):
    selection, inputs = fixture
    schema = yaml.safe_load(inputs["schema_path"].read_bytes())
    schema["classes"]["Instance"]["attributes"]["data_substrate"]["annotations"] = {"d4d:termSources": annotation}
    inputs["schema_path"].write_text(yaml.safe_dump(schema))
    inputs["schema_snapshot"] = capture_schema(inputs["schema_path"], strict=True)
    selection["inputs"]["full_schema"] = bc._schema_pin(inputs["schema_snapshot"])


@pytest.mark.parametrize("label", ["EDAM Data", "EDAM Format", "IANA media types"])
def test_unusable_label_refuses_at_derivation(fixture, label):
    change_annotation(fixture, label)
    with pytest.raises(ValueError, match=label):
        policy(fixture)


def test_synthetic_prefix_derives_and_validates_populated_record(fixture):
    selection, inputs = fixture
    schema = yaml.safe_load(inputs["schema_path"].read_bytes())
    schema.setdefault("prefixes", {})["SYNTHETIC"] = "https://example.test/synthetic/"
    schema["classes"]["Instance"]["attributes"]["data_substrate"]["annotations"] = {
        "d4d:termSources": "SYNTHETIC",
        "d4d:termSourceIdentifierForms": json.dumps({"version": 1, "sources": [
            {"id": "synthetic", "label": "SYNTHETIC",
             "curies": [{"prefix": "SYNTHETIC", "local_prefix": ""}],
             "iri_bases": ["https://example.test/synthetic/"]},
        ]})}
    inputs["schema_path"].write_text(yaml.safe_dump(schema))
    inputs["schema_snapshot"] = capture_schema(inputs["schema_path"], strict=True)
    selection["inputs"]["full_schema"] = bc._schema_pin(inputs["schema_snapshot"])
    inputs["record"] = b"name: Example\ninstances:\n- data_substrate: SYNTHETIC:123\n"
    assert om.prepare(**inputs, term_policy=policy(fixture)).request()["payload"]["record_yaml"].encode() == inputs["record"]


def catalog(text):
    return {"classes": {"Instance": {"slots": {"data_substrate": {"definition": {
        "annotations": {"d4d:termSources": text}}}}}}}


@pytest.mark.parametrize("text,expected", [("A, B, and C", ["A", "B", "C"]),
    ("Gene and Protein Ontology", ["Gene and Protein Ontology"]), ("A; and B", ["A", "B"])])
def test_source_list_grammar(text, expected):
    assert bc._sources(catalog(text))["Instance"]["data_substrate"]["sources"] == expected


@pytest.mark.parametrize("char", ["\x00", "\u200b", "\u202e", "\u2028", "\u2029"])
def test_source_list_rejects_unicode_controls(char):
    with pytest.raises(ValueError, match="syntax"):
        bc._sources(catalog("A" + char + "B"))


@pytest.mark.parametrize("name,pin_value", [("bridge2ai", None), ("neutral", {"path": "/wrong", "sha256": "a" * 64}),
    ("bridge2ai", {"path": "/wrong", "sha256": "a" * 64})])
def test_profile_pin_must_match_declared_profile(fixture, name, pin_value):
    fixture[0]["inputs"]["profile"].update(name=name, vocabulary=pin_value)
    with pytest.raises(ValueError, match="vocabulary pin"):
        policy(fixture)


def test_capture_refuses_registered_profile_pin_mismatch(registered, simulated_hooks, monkeypatch):
    # Exercise the existing protected guard, with a RunSpec selected normally.
    monkeypatch.setitem(profiles.PROFILES, registered.profile,
        profiles.Profile(registered.profile, vocabulary_pin=Path("/wrong/vocabulary.yaml")))
    with pytest.raises(ValueError, match="registered profile vocabulary differs from selected profile"):
        simulated_hooks.capture(registered)


def test_bc1_sizing_refuses_null_manifest(sizing_fixture):
    from data_sheets_schema import bc1_registration
    registration, files, inputs = sizing_fixture
    registration["inputs"]["source_manifest"] = None
    with pytest.raises(ValueError, match="manifest"):
        bc1_registration.size_inputs(registration, sizing_record=files,
            context_raw=inputs["context"], schema_snapshot=inputs["schema_snapshot"])


def test_incomplete_registration_cannot_borrow_calibration(tmp_path):
    manifest = builder.ROOT / "data/preprocessed/source_manifest.yaml"
    limits = builder.resolve_audit_limits("CHORUS", "chorus")
    registration = {"run": {"project": "CHORUS", "arm": builder.ARMS["baseline"][0]},
        "audit_limits": limits, "inputs": {"source_manifest": pin(manifest)}}
    with pytest.raises(ValueError, match="no partition profile covers"):
        builder.check_registration_sizing(tmp_path / "incomplete.json", json.dumps(registration).encode())


@pytest.mark.parametrize("exists", [False, True])
def test_all_refuses_empty_registry(tmp_path, exists):
    manifest = tmp_path / "empty.yaml"
    if exists:
        manifest.write_text("projects: {}\n")
    out = tmp_path / "output"
    result = CliRunner().invoke(builder.cli, ["--all", "--source-manifest", str(manifest),
        "--label", "round2", "--dry-run", "--output-dir", str(out)])
    assert result.exit_code != 0
    assert str(manifest) in result.output
    assert ("exists" if exists else "missing") in result.output
    assert not out.exists()


def test_unmocked_all_dry_run_builds_two_synthetic_projects(sizing_fixture, tmp_path, monkeypatch):
    registration, files, inputs = sizing_fixture
    monkeypatch.setattr(builder.api, "FULL_SCHEMA_PATH", inputs["schema_path"])
    monkeypatch.setattr(builder.api, "CORE_SCHEMA_PATH", inputs["schema_path"])
    manifest = tmp_path / "two-projects.yaml"
    manifest.write_text(yaml.safe_dump({"profile": "neutral", "projects": {
        project: {"bundle": registration["inputs"]["bundle"]["path"],
                  "sources": [{"id": "source", "processed_file": "source.txt", "source_type": "documentation"}]}
        for project in ("SYNTHETIC_ONE", "SYNTHETIC_TWO")}}))
    output = tmp_path / "dry-output"
    args = ["--all", "--source-manifest", str(manifest), "--label", "round2", "--dry-run",
        "--output-dir", str(output), "--profile", "neutral", "--max-paths", "80",
        "--max-inventory-bytes", "12288", "--max-workers", "4", "--aggregate-input-tokens", "4000000"]
    args += ["--context-dir", str(tmp_path)]
    from data_sheets_schema.chunking import manifest_for
    chunk_path = manifest_for(Path(registration["inputs"]["bundle"]["path"]), source_manifest=manifest)
    chunk_path.parent.mkdir(parents=True, exist_ok=True)
    chunk_path.write_bytes(inputs["manifest"])
    for project in ("SYNTHETIC_ONE", "SYNTHETIC_TWO"):
        (tmp_path / f"{project.lower()}_omission_context.json").write_bytes(inputs["context"])
        directory = tmp_path / project
        directory.mkdir()
        for key, suffix in [("full", "full"), ("core", "core"), ("receipt", "coverage_receipt")]:
            content = getattr(files, key).read_bytes().replace(b"KIDS_FIRST", project.encode()).replace(
                b"# Arm: de novo", ("# Arm: " + builder.ARMS["baseline"][0]).encode())
            (directory / f"{project}_{suffix}.yaml").write_bytes(content)
        args += ["--sizing-record", f"{project}={directory}"]
    result = CliRunner().invoke(builder.cli, args)
    assert result.exit_code == 0, result.output + repr(result.exception)
    assert all(f"✓ {project}:" in result.output for project in ("SYNTHETIC_ONE", "SYNTHETIC_TWO"))
    assert not output.exists()


@pytest.mark.parametrize("project", ["CHORUS", "SYNTHETIC"])
def test_valid_calibration_and_single_variable_negative_controls(sizing_fixture, tmp_path, monkeypatch, project):
    registration, files, inputs = sizing_fixture
    root = tmp_path / "root"
    (root / "config").mkdir(parents=True)
    copy_partition_resources(root)
    config = root / builder.AUDIT_PARTITION_FILES[0]
    save(config, {"projects": {}})
    monkeypatch.setattr(builder, "ROOT", root)
    monkeypatch.setattr(builder.api, "FULL_SCHEMA_PATH", inputs["schema_path"])
    monkeypatch.setattr(builder.api, "CORE_SCHEMA_PATH", inputs["schema_path"])
    manifest = Path(registration["inputs"]["source_manifest"]["path"])
    manifest.write_text(yaml.safe_dump({"profile": "neutral", "projects": {project: {"sources": [
        {"id": "source", "processed_file": "source.txt", "source_type": "documentation"}]}}}))
    for key in ("full", "core"):
        path = getattr(files, key)
        path.write_bytes(path.read_bytes().replace(b"KIDS_FIRST", project.encode()).replace(
            b"# Arm: de novo", ("# Arm: " + builder.ARMS["baseline"][0]).encode()))
    limits = {"max_paths": 80, "max_inventory_bytes": 12288, "max_workers": 4, "aggregate_input_tokens": 4000000}
    reg, _, sized = builder.prepare_registration(project, "calibration", source_manifest_path=manifest,
        bundle_path=registration["inputs"]["bundle"]["path"],
        chunk_manifest_path=registration["inputs"]["chunk_manifest"]["path"],
        context_path=registration["inputs"]["context"]["path"], profile_name="neutral",
        registration_path=tmp_path / "calibration.json", audit_limits=limits,
        sizing_record=builder.SizingRecord(files.full, files.core, files.receipt))
    entry = {"name": "fixture", "arms": ["baseline"], "limits": limits,
        "source_manifest_sha256": pin(manifest)["sha256"],
        "sizing_record": {key: pin(getattr(files, key)) for key in ("full", "core", "receipt")}}
    def covered(value):
        save(config, {"projects": {project: {"audit_partition": value}}})
        return builder.profile_covered(project, "baseline", {**reg["audit_limits"], **value["limits"]},
            source_manifest=manifest, registration=reg)
    assert sized["aggregate_input_tokens"] < 4000000
    assert covered(entry)
    for damage in ("full", "core", "receipt", "foreign_manifest", "low_allowance"):
        changed = deepcopy(entry)
        if damage in {"full", "core", "receipt"}:
            path = tmp_path / ("bad-" + damage + ".yaml")
            path.write_text("not a coverage receipt\n" if damage == "receipt" else
                f"# D4D Datasheet for {project} Dataset\n# Arm: {builder.ARMS['baseline'][0]}\nnot: [valid\n")
            changed["sizing_record"][damage] = pin(path)
        elif damage == "foreign_manifest":
            changed["source_manifest_sha256"] = "0" * 64
        else:
            changed["limits"]["aggregate_input_tokens"] = 1000
        assert not covered(changed), damage
