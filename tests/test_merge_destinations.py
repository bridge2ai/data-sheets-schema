"""#4765: derived publication cannot overwrite a contributor's method family."""

import hashlib
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import merge
from data_sheets_schema.provenance import record_path_for


def _snapshot(root):
    """Include directories, link identities and every byte, without following links."""
    rows = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(directory) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                value = ("symlink", os.readlink(path))
            elif stat.S_ISDIR(info.st_mode):
                value = ("directory",)
            else:
                value = ("file", path.read_bytes(), info.st_ino, info.st_nlink)
            rows[str(path.relative_to(root))] = (stat.S_IMODE(info.st_mode), value)
    return rows


def _case(tmp_path, methods=("claudecode_agent", "claudecode_agent")):
    root = tmp_path / "d4d_concatenated"
    sources, records, provenance, cores = {}, {}, {}, {}
    for number, method in enumerate(methods, 1):
        label = "rep" + str(number)
        record = {"title": "T", "only_" + label: str(number)}
        full = root / method / label / "P_d4d.yaml"
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(yaml.safe_dump(record), encoding="utf-8")
        sidecar = record_path_for("P", method, label, root)
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(yaml.safe_dump({
            "record_mode": "live",
            "inputs": {"bundle_md5": "a", "hash_basis": "verified identical to the bytes consumed"},
            "schema": {"full_md5": "s"}, "model": {"model": "m"},
            "outputs": {"full": {"md5": "x"}},
        }), encoding="utf-8")
        core = sidecar.parent / "P_d4d_core.yaml"
        core.write_text("title: existing contributor core\n", encoding="utf-8")
        sources[label], records[label], provenance[label], cores[label] = full, record, sidecar, core
    # The ordinary eligibility check must accept these fixtures before any
    # destination is tested; a missing-provenance error is not a positive gate.
    merge.check_sources(sources, "P")
    result = merge.union_merge(records, project="P", source_paths=sources, base="rep1")
    return SimpleNamespace(root=root, sources=sources, records=records,
                           provenance=provenance, cores=cores, result=result)


@pytest.fixture
def case(tmp_path):
    return _case(tmp_path)


def _write(case, output, **overrides):
    options = dict(sources=case.sources, project="P", method="independent_union", label="derived")
    options.update(overrides)
    return merge.write_merge(case.result, output, **options)


def _refused_without_publication(tmp_path, case, output, **overrides):
    before = _snapshot(tmp_path)
    with pytest.raises(ValueError):
        _write(case, output, **overrides)
    assert _snapshot(tmp_path) == before


def test_distinct_destination_records_original_contributors(case, tmp_path):
    output = case.root / "independent_union" / "derived" / "P_d4d.yaml"
    expected_provenance = case.root / "independent_union_core" / "derived" / "P_provenance.yaml"
    before = _snapshot(tmp_path)
    selected = merge.check_merge_destination(output, sources=case.sources,
                                             project="P", method="independent_union", label="derived")
    assert selected == expected_provenance
    assert _snapshot(tmp_path) == before  # preflight itself publishes nothing
    assert _write(case, output) == output
    assert yaml.safe_load(output.read_text()) == case.result.record
    record = yaml.safe_load(expected_provenance.read_text())
    assert record["record_mode"] == "derived"
    assert record["run"]["method"] == "independent_union"
    assert record["run"]["label"] == "derived"
    assert {row["method"] for row in record["sources"]} == {"claudecode_agent"}
    assert {row["sha256"] for row in record["sources"]} == {
        hashlib.sha256(path.read_bytes()).hexdigest() for path in case.sources.values()}
    assert sum(row["contributed_slots"] for row in record["sources"]) == len(case.result.record)
    after = _snapshot(tmp_path)
    assert {name: after[name] for name in before} == before


def test_explicit_disjoint_outside_corpus_destination_remains_supported(case, tmp_path):
    output = tmp_path / "elsewhere" / "P_d4d.yaml"
    assert _write(case, output) == output
    provenance = record_path_for("P", "independent_union", "derived", output.parent)
    assert provenance.is_file()
    assert yaml.safe_load(output.read_text()) == case.result.record
    assert yaml.safe_load(provenance.read_text())["record_mode"] == "derived"


def test_source_less_experiment_still_writes_only_the_record(tmp_path):
    result = merge.union_merge({"a": {"title": "T"}, "b": {"extra": "value"}})
    output = tmp_path / "probe" / "record.yaml"
    assert merge.write_merge(result, output) == output
    assert yaml.safe_load(output.read_text()) == result.record
    assert sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()) == ["probe/record.yaml"]


def test_existing_disjoint_output_and_explicit_provenance_can_still_be_replaced(case, tmp_path):
    output = case.root / "independent_union" / "derived" / "P_d4d.yaml"
    output.parent.mkdir(parents=True)
    output.write_text("old: distinct derived artifact\n")
    explicit = tmp_path / "explicit-provenance.yaml"
    explicit.write_text("old: distinct sidecar\n")
    _write(case, output, provenance_path=explicit)
    assert yaml.safe_load(output.read_text()) == case.result.record
    record = yaml.safe_load(explicit.read_text())
    assert record["record_mode"] == "derived"
    assert record["run"]["method"] == "independent_union"
    assert not (case.root / "independent_union_core").exists()


@pytest.mark.parametrize("label", ["rep1", "another_label"])
def test_source_method_is_refused_even_under_another_run_label(case, tmp_path, label):
    output = case.root / "claudecode_agent" / label / "P_d4d.yaml"
    _refused_without_publication(tmp_path, case, output, method="claudecode_agent", label=label)


@pytest.mark.parametrize("method", ["", " ", ".", "..", "../escape", "nested/method", "nested\\method", "/absolute", "claudecode_agent_core", "independent_union_core"])
def test_invalid_or_core_alias_method_refuses_before_creating_a_destination(case, tmp_path, method):
    output = case.root / "independent_union" / "derived" / "P_d4d.yaml"
    _refused_without_publication(tmp_path, case, output, method=method)


@pytest.mark.parametrize("label", ["", " ", ".", "..", "../escape", "nested/run", "nested\\run", "/absolute"])
def test_label_cannot_escape_the_declared_method(case, tmp_path, label):
    output = case.root / "independent_union" / "derived" / "P_d4d.yaml"
    _refused_without_publication(tmp_path, case, output, label=label)


@pytest.mark.parametrize("project", ["", "../P", "nested/P"])
def test_project_component_cannot_redirect_provenance(case, tmp_path, project):
    output = case.root / "independent_union" / "derived" / "P_d4d.yaml"
    _refused_without_publication(tmp_path, case, output, project=project)


@pytest.mark.parametrize("path_method,path_label", [("different_union", "derived"), ("independent_union", "wrong_label"), ("claudecode_agent", "derived")])
def test_conventional_output_path_must_match_declared_method_and_label(case, tmp_path, path_method, path_label):
    output = case.root / path_method / path_label / "P_d4d.yaml"
    _refused_without_publication(tmp_path, case, output)


def test_destination_must_differ_from_every_contributing_method(tmp_path):
    case = _case(tmp_path, methods=("claudecode_agent", "claudecode_github"))
    output = case.root / "claudecode_github" / "new_label" / "P_d4d.yaml"
    _refused_without_publication(tmp_path, case, output, method="claudecode_github", label="new_label")


@pytest.mark.parametrize("alias", ["full_method", "full_run", "core_method", "core_run"])
def test_symlinked_destination_cannot_alias_source_full_or_core_tree(case, tmp_path, alias):
    output = case.root / "independent_union" / "derived" / "P_d4d.yaml"
    if alias == "full_method":
        (case.root / "independent_union").symlink_to(case.root / "claudecode_agent", target_is_directory=True)
    elif alias == "full_run":
        output.parent.parent.mkdir()
        output.parent.symlink_to(case.sources["rep1"].parent, target_is_directory=True)
    elif alias == "core_method":
        (case.root / "independent_union_core").symlink_to(case.root / "claudecode_agent_core", target_is_directory=True)
    else:
        core_parent = case.root / "independent_union_core"
        core_parent.mkdir()
        (core_parent / "derived").symlink_to(case.provenance["rep1"].parent, target_is_directory=True)
    _refused_without_publication(tmp_path, case, output)


@pytest.mark.parametrize("protected", ["full", "provenance", "core"])
@pytest.mark.parametrize("destination", ["full", "provenance"])
def test_existing_hardlink_to_any_contributor_artifact_is_refused(case, tmp_path, protected, destination):
    source = {"full": case.sources, "provenance": case.provenance, "core": case.cores}[protected]["rep1"]
    output = case.root / "independent_union" / "derived" / "P_d4d.yaml"
    explicit = tmp_path / "sidecars" / "derived.yaml"
    link = output if destination == "full" else explicit
    link.parent.mkdir(parents=True)
    os.link(source, link)
    options = {} if destination == "full" else {"provenance_path": explicit}
    _refused_without_publication(tmp_path, case, output, **options)


@pytest.mark.parametrize("protected", ["full", "provenance", "core"])
def test_explicit_provenance_cannot_overwrite_a_contributor(case, tmp_path, protected):
    target = {"full": case.sources, "provenance": case.provenance, "core": case.cores}[protected]["rep1"]
    output = case.root / "independent_union" / "derived" / "P_d4d.yaml"
    _refused_without_publication(tmp_path, case, output, provenance_path=target)


@pytest.mark.parametrize("method", ["claudecode_agent", "claudecode_agent_core"])
def test_explicit_provenance_cannot_create_a_new_run_in_a_source_family(case, tmp_path, method):
    target = case.root / method / "uncreated_label" / "P_provenance.yaml"
    output = case.root / "independent_union" / "derived" / "P_d4d.yaml"
    _refused_without_publication(tmp_path, case, output, provenance_path=target)


@pytest.mark.parametrize("kind", ["same_path", "hardlink"])
def test_full_and_provenance_destinations_cannot_overwrite_each_other(case, tmp_path, kind):
    output = case.root / "independent_union" / "derived" / "P_d4d.yaml"
    explicit = output
    if kind == "hardlink":
        output.parent.mkdir(parents=True)
        output.write_bytes(b"existing distinct derived artifact\n")
        explicit = tmp_path / "linked-provenance.yaml"
        os.link(output, explicit)
    _refused_without_publication(tmp_path, case, output, provenance_path=explicit)


@pytest.mark.parametrize("fault", ["missing_attestation", "derived_mode"])
def test_source_eligibility_refusal_precedes_all_output_creation(case, tmp_path, fault):
    sidecar = case.provenance["rep1"]
    if fault == "missing_attestation":
        sidecar.unlink()
    else:
        body = yaml.safe_load(sidecar.read_text())
        body["record_mode"] = "derived"
        sidecar.write_text(yaml.safe_dump(body))
    output = case.root / "independent_union" / "derived" / "P_d4d.yaml"
    _refused_without_publication(tmp_path, case, output)
    assert not output.parent.parent.exists()
    assert not (case.root / "independent_union_core").exists()
