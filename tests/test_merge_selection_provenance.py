"""#4770: derived provenance describes selection, without certifying fitness.

All records are synthetic temporary attested sources; no model or provider runs.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import merge


def _sources(root, records):
    paths = {}
    for label, record in records.items():
        full = root / "claudecode_agent" / label / "P_d4d.yaml"
        full.parent.mkdir(parents=True)
        full.write_text(yaml.safe_dump(record), encoding="utf-8")
        core = root / "claudecode_agent_core" / label
        core.mkdir(parents=True)
        (core / "P_d4d_core.yaml").write_text(yaml.safe_dump(record), encoding="utf-8")
        (core / "P_reconciliation.md").write_text("# synthetic reconciliation\n", encoding="utf-8")
        (core / "P_provenance.yaml").write_text(yaml.safe_dump({
            "record_mode": "live",
            "run": {"method": "claudecode_agent", "label": label, "project": "P"},
        }), encoding="utf-8")
        paths[label] = full
    return paths


def _snapshot(root):
    return {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _assert_sources_preserved(before, paths, provenance):
    assert all(path.read_bytes() == raw for path, raw in before.items())
    assert provenance["record_mode"] == "derived"
    assert provenance["record_type"] == "d4d_derived_provenance"
    assert {row["label"] for row in provenance["sources"]} == set(paths)
    for row in provenance["sources"]:
        assert row["sha256"] == hashlib.sha256(before[paths[row["label"]]]).hexdigest()
        assert row["method"] == "claudecode_agent"


def test_actual_writer_reports_base_and_first_holder_instead_of_best_fit(tmp_path):
    records = {
        "rep3": {"id": "https://example.org/x", "title": "T", "keywords": ["third"]},
        "base": {"id": "https://example.org/x", "title": "T", "description": "base text",
                 "base_only": "preserved"},
        "rep1": {"id": "https://example.org/x", "title": "T", "description": "other text",
                 "keywords": ["first"]},
    }
    root = tmp_path / "d4d_concatenated"
    paths = _sources(root, records)
    before = _snapshot(root)
    original_records = deepcopy(records)
    result = merge.union_merge(records, base="base", source_paths=paths, project="P")
    assert result.record == {**records["base"], "keywords": ["first"]}
    assert result.source_of == {"base_only": "base", "description": "base", "id": "base",
                                "keywords": "rep1", "title": "base"}
    assert result.contested == 2
    assert records == original_records
    output = root / "claudecode_agent_merged" / "merged-api" / "P_d4d.yaml"
    merge.write_merge(result, output, sources=paths, project="P", method="claudecode_agent_merged",
                      label="merged-api")
    provenance = yaml.safe_load((root / "claudecode_agent_merged_core" / "merged-api" /
                                 "P_provenance.yaml").read_text())
    assert yaml.safe_load(output.read_text()) == result.record
    _assert_sources_preserved(before, paths, provenance)
    assert {row["label"]: row["contributed_slots"] for row in provenance["sources"]} == {
        "base": 4, "rep1": 1, "rep3": 0}
    rule = provenance["derivation"]["rule"]
    assert "best-fitting" not in rule, rule
    assert "base" in rule and "first" in rule and "sorted" in rule, rule
    assert result.selection_mode == "base_or_first_holder"
    assert result.scorer_identity is None
    assert "No scorer was supplied" in rule


def test_actual_cli_no_scorer_provenance_does_not_claim_fit(tmp_path, monkeypatch):
    from data_sheets_schema import runs
    from data_sheets_schema.cli.runs import runs as runs_cli

    first, second = "2026-08-01_cfg_rep1", "2026-08-01_cfg_rep2"
    records = {
        first: {"id": "https://example.org/x", "title": "T", "description": "base text",
                "keywords": ["first"], "only_first": "a"},
        second: {"id": "https://example.org/x", "title": "T", "description": "other text",
                 "keywords": ["second"], "only_second": "b"},
    }
    root = tmp_path / "d4d_concatenated"
    paths = _sources(root, records)
    before = _snapshot(root)
    monkeypatch.setattr(runs, "CONCAT_DIR", root)
    arguments = ["merge", "--method", "claudecode_agent", "--project", "P",
                 "--config", "2026-08-01_cfg"]
    dry = CliRunner().invoke(runs_cli, arguments)
    assert dry.exit_code == 0, dry.output
    assert "Dry run" in dry.output
    assert _snapshot(root) == before
    actual = CliRunner().invoke(runs_cli, [*arguments, "--execute"])
    assert actual.exit_code == 0, actual.output
    label = "2026-08-01_cfg_merged"
    output = root / "claudecode_agent_merged" / label / "P_d4d.yaml"
    provenance = yaml.safe_load((root / "claudecode_agent_merged_core" / label /
                                 "P_provenance.yaml").read_text())
    assert yaml.safe_load(output.read_text()) == {**records[first], "only_second": "b"}
    _assert_sources_preserved(before, paths, provenance)
    assert {row["label"]: row["contributed_slots"] for row in provenance["sources"]} == {
        first: 5, second: 1}
    rule = provenance["derivation"]["rule"]
    assert "best-fitting" not in rule, rule
    assert first in rule and "first" in rule and "sorted" in rule, rule
    assert "first" in actual.output and "sorted" in actual.output, actual.output


def _publish(root, result, paths, label="merged-api"):
    output = root / "claudecode_agent_merged" / label / "P_d4d.yaml"
    provenance_path = root / "claudecode_agent_merged_core" / label / "P_provenance.yaml"
    merge.write_merge(result, output, sources=paths, project="P", method="claudecode_agent_merged", label=label)
    assert yaml.safe_load(output.read_text()) == result.record
    return yaml.safe_load(provenance_path.read_text())


@pytest.mark.parametrize("guarded", [False, True])
def test_exact_base_label_and_guard_are_disclosed_independently(tmp_path, guarded):
    base = "chosen-replicate"
    records = {
        "z-last": {"id": "https://example.org/x", "title": "T", "keywords": ["last"]},
        base: {"id": "https://example.org/x", "title": "T", "description": "base singleton"},
        "a-first": {"id": "https://example.org/x", "title": "T", "keywords": ["first"]},
    }
    root = tmp_path / "d4d_concatenated"
    paths = _sources(root, records)
    before = _snapshot(root)
    result = merge.union_merge(records, base=base, guarded=guarded, source_paths=paths, project="P")
    assert result.record == {**records[base], "keywords": ["first"]}
    assert result.source_of["description"] == base
    assert result.source_of["keywords"] == "a-first"
    assert result.contested == (1 if guarded else 3)
    provenance = _publish(root, result, paths)
    _assert_sources_preserved(before, paths, provenance)
    rule = provenance["derivation"]["rule"]
    assert f"base `{base}`" in rule
    assert "first holder in sorted label order" in rule
    assert "No scorer was supplied" in rule
    assert ("referent-bearing fields pinned" in rule) is guarded
    assert ("unguarded union" in rule) is not guarded
    assert f"{result.contested} slots were contested" in rule


@pytest.mark.parametrize("kind", ["numeric", "fitness", "supported"])
@pytest.mark.parametrize("identity", [None, '  local "test" scorer\\v1\ncaller label  '])
def test_actual_supplied_scores_preserve_winners_ties_and_declared_identity(tmp_path, kind, identity):
    records = {
        "z-last": {"id": "https://example.org/x", "title": "T", "description": "third",
                   "ties": "third tie", "no_base": "third missing"},
        "chosen": {"id": "https://example.org/x", "title": "T", "description": "base",
                   "ties": "base tie", "only_base": "singleton"},
        "a-first": {"id": "https://example.org/x", "title": "T", "description": "strongest",
                    "ties": "first tie", "no_base": "first missing"},
    }
    calls = []
    def scorer(*, project, slot, value):
        calls.append((project, slot, value))
        score = (10 if value == "strongest" else 1) if slot == "description" else 7
        return score if kind == "numeric" else SimpleNamespace(**{kind: score})

    root = tmp_path / "d4d_concatenated"
    paths = _sources(root, records)
    before = _snapshot(root)
    original_records = deepcopy(records)
    result = merge.union_merge(records, scorer=scorer, scorer_identity=identity, base="chosen",
                               source_paths=paths, project="P")
    assert records == original_records
    assert result.record == {**records["chosen"], "description": "strongest", "no_base": "first missing"}
    assert result.source_of == {"description": "a-first", "id": "chosen", "no_base": "a-first",
                                "only_base": "chosen", "ties": "chosen", "title": "chosen"}
    assert calls == [("P", slot, records[label][slot])
                     for slot in ("description", "no_base", "ties")
                     for label in sorted(records) if slot in records[label]]
    assert len(calls) == 8 and result.contested == 3
    assert result.selection_mode == "maximum_supplied_score"
    assert result.scorer_identity is identity
    provenance = _publish(root, result, paths)
    assert len(calls) == 8  # Publication never invokes the scorer again.
    _assert_sources_preserved(before, paths, provenance)
    assert {row["label"]: row["contributed_slots"] for row in provenance["sources"]} == {
        "a-first": 2, "chosen": 4, "z-last": 0}
    rule = provenance["derivation"]["rule"]
    assert "maximum supplied numeric score" in rule and "ties prefer base `chosen`" in rule
    assert "first holder in sorted label order" in rule
    assert "supplied scorer was invoked for contested slots" in rule
    assert "best-fitting" not in rule
    assert "does not authenticate an instrument, model, calibration or scientific validity" in rule
    if identity is None:
        assert "Scorer identity: unrecorded" in rule
        assert "caller-declared" not in rule
    else:
        assert "Scorer identity: caller-declared " + json.dumps(identity) in rule


@pytest.mark.parametrize("identity", [None, "offline synthetic scorer"])
def test_configured_scorer_with_no_contested_slots_is_not_invoked(tmp_path, identity):
    records = {"base": {"id": "https://example.org/x", "only_base": "a"},
               "other": {"id": "https://example.org/x", "only_other": "b"}}
    def refuse(**kwargs):
        raise AssertionError("a scorer must not run for singleton or guarded slots")
    root = tmp_path / "d4d_concatenated"
    paths = _sources(root, records)
    before = _snapshot(root)
    result = merge.union_merge(records, scorer=refuse, scorer_identity=identity, base="base",
                               source_paths=paths, project="P")
    assert result.record == {**records["base"], "only_other": "b"}
    assert result.contested == 0 and result.selection_mode == "maximum_supplied_score"
    provenance = _publish(root, result, paths)
    _assert_sources_preserved(before, paths, provenance)
    rule = provenance["derivation"]["rule"]
    assert "No contested slots; the supplied scorer was not invoked" in rule
    assert "scorer was invoked" not in rule
    assert "0 slots were contested" in rule


class _StringSubclass(str):
    pass


@pytest.mark.parametrize("identity", ["", " \n\t", False, 1, b"label", ["label"], _StringSubclass("label")])
def test_invalid_identity_is_refused_before_merge_checks_or_callbacks(monkeypatch, identity):
    def refuse(*args, **kwargs):
        raise AssertionError("identity validation must precede merge checks and callbacks")
    monkeypatch.setattr(merge, "check_sources", refuse)
    monkeypatch.setattr(merge, "referent_report", refuse)
    records = {"a": {"keywords": ["a"]}, "b": {"keywords": ["b"]}}
    before = deepcopy(records)
    with pytest.raises(ValueError, match="scorer_identity"):
        merge.union_merge(records, scorer=refuse, scorer_identity=identity,
                          source_paths={"a": Path("never-read")}, project="P")
    assert records == before


@pytest.mark.parametrize("scorer", [None, 42])
def test_identity_requires_an_actual_callable_scorer(scorer):
    with pytest.raises(ValueError, match="scorer_identity requires"):
        merge.union_merge({"a": {"only": "value"}}, scorer=scorer, scorer_identity="caller label")


def test_old_positional_result_remains_usable_without_inventing_selection_history(tmp_path):
    records = {"a": {"keywords": ["a"]}, "b": {"keywords": ["b"]}}
    root = tmp_path / "d4d_concatenated"
    paths = _sources(root, records)
    before = _snapshot(root)
    legacy = merge.MergeResult({"keywords": ["a"]}, {"keywords": "a"}, "a", False, None, 1)
    assert legacy.selection_mode is None and legacy.scorer_identity is None
    provenance = _publish(root, legacy, paths)
    _assert_sources_preserved(before, paths, provenance)
    rule = provenance["derivation"]["rule"]
    assert "Selection mode was not recorded" in rule and "whether a scorer ran is unknown" in rule
    assert "maximum supplied numeric score" not in rule and "No scorer was supplied" not in rule
    assert "best-fitting" not in rule
    assert "1 slots were contested" in rule
    bare = tmp_path / "bare" / "P_d4d.yaml"
    merge.write_merge(merge.MergeResult(record={"title": "manual"}), bare)
    assert yaml.safe_load(bare.read_text()) == {"title": "manual"}
    assert sorted(p.name for p in bare.parent.iterdir()) == ["P_d4d.yaml"]


@pytest.mark.parametrize("mode, identity", [
    ("invented", None), (False, None), (["base_or_first_holder"], None),
    (_StringSubclass("base_or_first_holder"), None),
    ("maximum_supplied_score", ""), ("maximum_supplied_score", " \n"),
    ("maximum_supplied_score", False), ("maximum_supplied_score", _StringSubclass("label")),
    ("base_or_first_holder", "label"), (None, "label"),
])
@pytest.mark.parametrize("with_sources", [False, True])
def test_invalid_result_metadata_refuses_before_output_or_directory_creation(tmp_path, mode, identity,
                                                                           with_sources):
    root = tmp_path / "d4d_concatenated"
    paths = _sources(root, {"a": {"keywords": ["a"]}})
    before = _snapshot(root)
    result = merge.MergeResult(record={"keywords": ["a"]}, source_of={"keywords": "a"}, base="a",
                               selection_mode=mode, scorer_identity=identity)
    output = tmp_path / "uncreated" / "P_d4d.yaml"
    provenance = tmp_path / "uncreated-provenance" / "P_provenance.yaml"
    with pytest.raises(ValueError):
        merge.write_merge(result, output, sources=paths if with_sources else None, project="P",
                          method="claudecode_agent_merged", label="merged", provenance_path=provenance)
    assert not output.parent.exists() and not provenance.parent.exists()
    assert _snapshot(root) == before


def test_referent_guard_and_actual_source_refusals_still_apply(tmp_path):
    records = {"base": {"id": "https://example.org/x", "keywords": ["base"]},
               "other": {"id": "https://example.org/x", "doi": "10.1234/other", "keywords": ["other"]}}
    root = tmp_path / "d4d_concatenated"
    paths = _sources(root, records)
    before = _snapshot(root)
    calls = []
    def scorer(**kwargs):
        calls.append(kwargs)
        return 1
    with pytest.raises(ValueError, match="refusing an unguarded merge"):
        merge.union_merge(records, base="base", guarded=False, scorer=scorer,
                          scorer_identity="test only", source_paths=paths, project="P")
    assert calls == [] and _snapshot(root) == before
    guarded = merge.union_merge(records, base="base", source_paths=paths, project="P")
    assert "doi" not in guarded.record and guarded.record["keywords"] == ["base"]
    assert guarded.report.blocking
    provenance = _publish(root, guarded, paths)
    _assert_sources_preserved(before, paths, provenance)
    # The source's actual mode, not its path spelling, still forbids chaining.
    source_prov = root / "claudecode_agent_core" / "other" / "P_provenance.yaml"
    changed = yaml.safe_load(source_prov.read_text())
    changed["record_mode"] = "derived"
    source_prov.write_text(yaml.safe_dump(changed))
    with pytest.raises(ValueError, match="itself a derived record"):
        merge.union_merge(records, source_paths=paths, project="P")
    source_prov.unlink()
    with pytest.raises(ValueError, match="conditions cannot be established"):
        merge.union_merge(records, source_paths=paths, project="P")
