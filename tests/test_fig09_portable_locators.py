"""Relocatable fig09 references retain exact acquired bytes and scope (#4918)."""
import csv
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from tests.test_crate_generation_comparison import prepared_inputs  # noqa: F401


CODE_FILES = (
    "scripts/figures/fig09_mapping_revision.py",
    "src/data_sheets_schema/crate_generation_comparison.py",
    "src/data_sheets_schema/scope.py",
    "src/data_sheets_schema/rocrate_map.py",
    "src/data_sheets_schema/rocrate_sources.py",
    "src/data_sheets_schema/rocrate_assertions.py",
    "src/data_sheets_schema/schema_view.py",
    "src/data_sheets_schema/figure_publication.py",
)


def _seed(prepared_inputs, tmp_path):
    """Reuse the existing real preparation fixture with portable source declarations."""
    module, _, _, _, _ = prepared_inputs
    seed = tmp_path / "portable-seed"
    seed.mkdir()
    for name in ("packages", "new-label", "schema", "mapping_table", "crate.json",
                 "historical.yaml", "historical-manifest.json", "src"):
        source, destination = tmp_path / name, seed / name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copyfile(source, destination)
    source_root = module.ROOT
    for name in CODE_FILES:
        destination = seed / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((source_root / name).read_bytes())
    sidecar_path = seed / "packages/P/processed/P_crate_mapping_sources.json"
    sidecar = json.loads(sidecar_path.read_text())
    for key in ("schema", "mapping_table", "source"):
        sidecar[key]["path"] = str(Path(sidecar[key]["path"]).relative_to(tmp_path))
    sidecar["producer"]["files_sha256"] = {
        name: hashlib.sha256((seed / name).read_bytes()).hexdigest()
        for name in sidecar["producer"]["files_sha256"]}
    sidecar_path.write_text(json.dumps(sidecar))
    # Q exercises the unpublished-project branch without inventing a static record.
    manifest = {"jobs": [
        {"cohort": "v8", "generation_rep": 1, "project": project,
         "input": "historical.yaml"} for project in ("P", "Q")]}
    (seed / "historical-manifest.json").write_text(json.dumps(manifest))
    return module, seed


def _prepare(module, root, monkeypatch):
    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module, "__file__", str(root / CODE_FILES[0]))
    monkeypatch.setattr(module, "PROJECTS", ("P", "Q"))
    return module.prepare(root, root / "packages", root / "new-label",
                          root / "historical-manifest.json")


def _resolve(root, row):
    if row["path_base"] == "repository_root":
        assert not Path(row["path"]).is_absolute()
        assert ".." not in Path(row["path"]).parts
        return root / row["path"]
    assert row["path_base"] == "external_absolute"
    assert Path(row["path"]).is_absolute()
    return Path(row["path"])


def test_equivalent_checkouts_publish_portable_locators_and_identical_data(
        prepared_inputs, tmp_path, monkeypatch):
    module, seed = _seed(prepared_inputs, tmp_path)
    roots = [tmp_path / "checkout-a", tmp_path / "elsewhere/checkout-b"]
    prepared, completed = [], []
    for root in roots:
        shutil.copytree(seed, root)
        item = _prepare(module, root, monkeypatch)
        prepared.append(item)
        completed.append(module.publish(item, root / "new-figure", "f" * 40))
    first, second = completed
    assert first["format_version"] == second["format_version"] == 2
    assert set(first["path_bases"]) == {"repository_root", "external_absolute"}
    assert first["path_bases"] == second["path_bases"]
    assert first["inputs"] == second["inputs"]
    assert {entry["path_base"] for entry in first["inputs"]} == {"repository_root"}
    # Resolve the first publication's locators in the second checkout, not its creator.
    for entry in first["inputs"]:
        assert hashlib.sha256(_resolve(roots[1], entry).read_bytes()).hexdigest() == entry["sha256"]
    for suffix in ("", "_overlap_slots", "_source_observations"):
        name = f"fig09_crate_vs_generation{suffix}.csv"
        assert (roots[0] / "new-figure" / name).read_bytes() == (roots[1] / "new-figure" / name).read_bytes()
    assert prepared[0]["projects"] == prepared[1]["projects"]
    mapped, missing = prepared[0]["projects"]
    assert mapped["static_record"] == "new-label/P_d4d.yaml"
    assert mapped["static_record_path_base"] == "repository_root"
    assert missing["status"] == "no published static-map record"
    with (roots[0] / "new-figure/fig09_crate_vs_generation.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        assert row["generated_record"] == "historical.yaml"
        assert row["generated_record_path_base"] == "repository_root"
        assert (roots[1] / row["generated_record"]).read_bytes() == (seed / "historical.yaml").read_bytes()
    assert rows[0]["original_rows"] == "3" and rows[0]["outcome_retired"] == "1"
    assert rows[1]["original_rows"] == ""  # An unpublished record is not a zero-coverage record.
    for root, report, item in zip(roots, completed, prepared):
        assert report["historical_generated_comparator"] == "generic-v8 rep 1, API arm"
        assert report["scientific_scoring"] is False
        assert len(report["artifacts"]) == 6
        for name, digest in report["artifacts"].items():
            assert hashlib.sha256((root / "new-figure" / name).read_bytes()).hexdigest() == digest
        assert all(path.read_bytes() == raw for path, raw in item["captured"].items())


@pytest.mark.parametrize("acquisition", ["absolute", "relative_escape", "symlink"])
def test_external_acquisitions_are_explicit_and_keep_exact_hashes(
        prepared_inputs, tmp_path, monkeypatch, acquisition):
    module, seed = _seed(prepared_inputs, tmp_path)
    root = tmp_path / "checkout"
    shutil.copytree(seed, root)
    outside = tmp_path / "external-historical.yaml"
    original = (root / "historical.yaml").read_bytes()
    outside.write_bytes(original)
    manifest_path = root / "historical-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if acquisition == "symlink":
        (root / "historical.yaml").unlink()
        (root / "historical.yaml").symlink_to(outside)
    else:
        for row in manifest["jobs"]:
            row["input"] = str(outside) if acquisition == "absolute" else "../external-historical.yaml"
        manifest_path.write_text(json.dumps(manifest))
    item = _prepare(module, root, monkeypatch)
    monkeypatch.setattr(module, "render", lambda *args: None)
    result = module.publish(item, root / "figure", "f" * 40)
    external = [entry for entry in result["inputs"] if entry["path_base"] == "external_absolute"]
    assert external == [{"path": str(outside), "path_base": "external_absolute",
                         "sha256": hashlib.sha256(original).hexdigest()}]
    assert item["captured"][outside] == original
    for project in item["projects"]:
        assert project["generated_record"] == str(outside)
        assert project["generated_record_path_base"] == "external_absolute"
    assert item["projects"][0]["overlap"]["both_agree"] == 2
    for entry in result["inputs"]:
        assert hashlib.sha256(_resolve(root, entry).read_bytes()).hexdigest() == entry["sha256"]
    assert "external_absolute" in (root / "figure/README.txt").read_text()


@pytest.mark.parametrize("when", ["before_publish", "during_render"])
def test_external_input_drift_still_refuses_completion(
        prepared_inputs, tmp_path, monkeypatch, when):
    module, seed = _seed(prepared_inputs, tmp_path)
    root = tmp_path / "checkout"
    shutil.copytree(seed, root)
    outside = tmp_path / "external-historical.yaml"
    outside.write_bytes((root / "historical.yaml").read_bytes())
    manifest_path = root / "historical-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for row in manifest["jobs"]:
        row["input"] = str(outside)
    manifest_path.write_text(json.dumps(manifest))
    item = _prepare(module, root, monkeypatch)
    def change(*args):
        outside.write_bytes(b"title: changed after capture\n")
    if when == "before_publish":
        change()
    else:
        monkeypatch.setattr(module, "render", change)
    with pytest.raises(ValueError, match="figure input changed"):
        module.publish(item, root / "refused", "f" * 40)
    assert not (root / "refused/manifest.json").exists()


def test_equal_content_does_not_turn_an_external_path_into_a_repository_locator(
        prepared_inputs, tmp_path, monkeypatch):
    module, seed = _seed(prepared_inputs, tmp_path)
    root = tmp_path / "checkout"
    shutil.copytree(seed, root)
    outside = tmp_path / "external-historical.yaml"
    outside.write_bytes((root / "historical.yaml").read_bytes())
    manifest_path = root / "historical-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["jobs"][1]["input"] = str(outside)
    manifest_path.write_text(json.dumps(manifest))
    item = _prepare(module, root, monkeypatch)
    monkeypatch.setattr(module, "render", lambda *args: None)
    result = module.publish(item, root / "figure", "f" * 40)
    entries = [entry for entry in result["inputs"]
               if entry["sha256"] == hashlib.sha256(outside.read_bytes()).hexdigest()]
    assert {(entry["path_base"], entry["path"]) for entry in entries} == {
        ("repository_root", "historical.yaml"), ("external_absolute", str(outside))}
    assert [row["generated_record_path_base"] for row in item["projects"]] == [
        "repository_root", "external_absolute"]


def test_external_static_record_keeps_its_acquisition_scope(
        prepared_inputs, tmp_path, monkeypatch):
    module, seed = _seed(prepared_inputs, tmp_path)
    root = tmp_path / "checkout"
    shutil.copytree(seed, root)
    outside = tmp_path / "external-label"
    shutil.copytree(root / "new-label", outside)
    _prepare(module, root, monkeypatch)
    item = module.prepare(root, root / "packages", outside,
                          root / "historical-manifest.json")
    row = item["projects"][0]
    assert row["static_record"] == str(outside / "P_d4d.yaml")
    assert row["static_record_path_base"] == "external_absolute"
    monkeypatch.setattr(module, "render", lambda *args: None)
    result = module.publish(item, root / "figure", "f" * 40)
    external = [entry for entry in result["inputs"] if entry["path_base"] == "external_absolute"]
    assert external == [{"path": str(outside / "P_d4d.yaml"),
                         "path_base": "external_absolute",
                         "sha256": hashlib.sha256((outside / "P_d4d.yaml").read_bytes()).hexdigest()}]
