"""#4765: real fitness-context wiring, without provider calls or validity claims."""
from dataclasses import replace
import hashlib
import json

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import evidence_score, merge, profiles
from data_sheets_schema.evidence_score import JudgementContext, LLMSlotFitnessScorer
from tests.test_merge_selection_provenance import _sources, _snapshot, _assert_sources_preserved


RECORDS = {
    "cfg_rep1": {"id": "https://example.org/x", "title": "T", "description": "first",
                 "only_first": "a"},
    "cfg_rep2": {"id": "https://example.org/x", "title": "T", "description": "second",
                 "only_second": "b"},
}


@pytest.fixture
def saved(tmp_path, monkeypatch):
    # The real current snapshot determines both context hashes. Only provider
    # resolution is trapped, so a cache miss cannot silently become a paid call.
    context = LLMSlotFitnessScorer(model="offline-test", profile=profiles.NEUTRAL)._context("offline-test")
    context_path = tmp_path / "instrument.json"
    context_path.write_text(json.dumps(context.as_entry()), encoding="utf-8")
    cache = tmp_path / "fitness.jsonl"
    rows = [{**context.as_entry(), "slot": "description", "value": json.dumps(value, sort_keys=True),
             "fitness": score, "failure": "none", "reason": "synthetic control"}
            for value, score in (("first", 0.25), ("second", 0.75))]
    cache.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def forbidden(*args, **kwargs):
        pytest.fail("cache-only merge attempted provider resolution")

    monkeypatch.setattr(LLMSlotFitnessScorer, "_resolve", forbidden)
    return context, context_path, cache, rows


def scorer(saved, **kwargs):
    context, _, cache, _ = saved
    return LLMSlotFitnessScorer(model=context.model, profile=profiles.NEUTRAL,
                                cache_path=cache, expected_context=context, cache_only=True, **kwargs)


def test_real_scorer_selection_and_writer_pin_consumed_bytes(saved, tmp_path):
    sc = scorer(saved)
    original = saved[2].read_bytes()
    # A later file edit does not change the bytes this scorer actually consumed.
    saved[2].write_text("", encoding="utf-8")
    root = tmp_path / "d4d_concatenated"
    paths = _sources(root, RECORDS)
    before = _snapshot(root)
    result = merge.union_merge(RECORDS, scorer=sc, project="P", source_paths=paths)
    assert result.record == {**RECORDS["cfg_rep1"], "description": "second", "only_second": "b"}
    assert result.source_of["description"] == "cfg_rep2"
    assert result.contested == 1 and sc.memo_hits == 2 and sc.calls == 0
    assert result.scorer_instrument["context"] == saved[0].as_entry()
    assert result.scorer_instrument["cache_sha256"] == hashlib.sha256(original).hexdigest()
    assert result.scorer_instrument["cache_bytes"] == len(original)
    output = root / "claudecode_agent" / "derived" / "P_d4d.yaml"
    merge.write_merge(result, output, sources=paths, project="P", method="claudecode_agent", label="derived")
    provenance = yaml.safe_load((root / "claudecode_agent_core" / "derived" / "P_provenance.yaml").read_text())
    _assert_sources_preserved(before, paths, provenance)
    rule = provenance["derivation"]["rule"]
    assert "Pinned fitness context: " + json.dumps(result.scorer_instrument, sort_keys=True) in rule
    assert "was invoked" in rule and "not provider authenticity" in rule


def test_configured_unused_instrument_is_not_reported_as_an_invocation(saved):
    sc = scorer(saved)
    records = {label: {key: value for key, value in record.items() if key != "description"}
               for label, record in RECORDS.items()}
    result = merge.union_merge(records, scorer=sc)
    assert result.contested == 0 and sc.memo_hits == sc.calls == 0
    assert result.scorer_instrument["context"] == saved[0].as_entry()
    assert "supplied scorer was not invoked" in merge._selection_description(result)


@pytest.mark.parametrize("field", ["model", "rubric", "schema", "specification"])
def test_wrong_expected_context_refuses_even_without_contested_slots(saved, field):
    context, _, cache, _ = saved
    expected = replace(context, **{field: getattr(context, field) + "-wrong"})
    # A wrong model is explicit too; the cache's matching rows still cannot be reused.
    sc = LLMSlotFitnessScorer(model=context.model, profile=profiles.NEUTRAL,
                             cache_path=cache, expected_context=expected)
    with pytest.raises(ValueError, match="expected_context"):
        merge.union_merge({"a": {"title": "T"}, "b": {"title": "T"}}, scorer=sc)
    assert sc.memo_hits == sc.calls == 0


@pytest.mark.parametrize("field", ["model", "rubric", "schema", "specification"])
def test_mismatched_saved_rows_are_not_promoted_to_scores(saved, field):
    _, _, cache, rows = saved
    cache.write_text("".join(json.dumps({**row, field: "other"}) + "\n" for row in rows))
    sc = scorer(saved)
    with pytest.raises(ValueError, match="no saved fitness judgement"):
        merge.union_merge(RECORDS, scorer=sc)
    assert sc.calls == sc.memo_hits == 0
    assert sc.cache_skipped[field] == 2


def test_missing_exact_value_refuses_without_provider(saved):
    sc = scorer(saved)
    with pytest.raises(ValueError, match="no saved fitness judgement"):
        sc(project="P", slot="description", value="First")
    assert sc.memo_hits == sc.calls == 0


def test_context_drift_after_a_cached_value_refuses_the_merge(saved, monkeypatch):
    sc = scorer(saved)
    load = sc._load_cache

    def changed(ctx):
        load(ctx)
        monkeypatch.setattr(evidence_score, "FITNESS_SYSTEM", evidence_score.FITNESS_SYSTEM + " drift")

    monkeypatch.setattr(sc, "_load_cache", changed)
    with pytest.raises(ValueError, match="expected_context"):
        merge.union_merge(RECORDS, scorer=sc)
    assert sc.memo_hits == 1 and sc.calls == 0


def test_bad_pinned_metadata_refuses_before_writer_creates_output(saved, tmp_path):
    result = merge.union_merge(RECORDS, scorer=scorer(saved))
    result.scorer_instrument["cache_sha256"] = "not-a-pin"
    output = tmp_path / "uncreated" / "record.yaml"
    with pytest.raises(ValueError, match="cache pin"):
        merge.write_merge(result, output)
    assert not output.parent.exists()


def test_real_cli_opt_in_and_unscored_default(saved, tmp_path, monkeypatch):
    from data_sheets_schema import runs
    from data_sheets_schema.cli.runs import runs as cli
    root = tmp_path / "d4d_concatenated"
    paths = _sources(root, RECORDS)
    for label in RECORDS:
        path = root / "claudecode_agent_core" / label / "P_provenance.yaml"
        doc = yaml.safe_load(path.read_text())
        doc["schema"] = {"profile": "neutral"}
        path.write_text(yaml.safe_dump(doc))
    before = _snapshot(root)
    monkeypatch.setattr(runs, "CONCAT_DIR", root)
    args = ["merge", "--method", "claudecode_agent", "--project", "P", "--config", "cfg"]
    default = CliRunner().invoke(cli, args)
    assert default.exit_code == 0, default.output
    assert "base's value is used" in default.output and "Pinned fitness context" not in default.output
    assert _snapshot(root) == before
    pinned = [*args, "--fitness-context", str(saved[1]), "--fitness-cache", str(saved[2])]
    dry = CliRunner().invoke(cli, pinned)
    assert dry.exit_code == 0, dry.output
    assert "Pinned fitness context" in dry.output and "no provider calls" in dry.output
    assert _snapshot(root) == before
    actual = CliRunner().invoke(cli, [*pinned, "--execute"])
    assert actual.exit_code == 0, actual.output
    output = root / "claudecode_agent" / "cfg_merged" / "P_d4d.yaml"
    assert yaml.safe_load(output.read_text())["description"] == "second"
    provenance = yaml.safe_load((root / "claudecode_agent_core" / "cfg_merged" / "P_provenance.yaml").read_text())
    _assert_sources_preserved(before, paths, provenance)
    assert saved[0].specification in provenance["derivation"]["rule"]
    assert hashlib.sha256(saved[2].read_bytes()).hexdigest() in provenance["derivation"]["rule"]


def test_cli_context_mismatch_creates_no_output(saved, tmp_path, monkeypatch):
    from data_sheets_schema import runs
    from data_sheets_schema.cli.runs import runs as cli
    root = tmp_path / "d4d_concatenated"
    _sources(root, RECORDS)  # Historical unspecified profile is bridge2ai, not neutral.
    monkeypatch.setattr(runs, "CONCAT_DIR", root)
    before = _snapshot(root)
    # Make the mismatch independent of which vocabulary slots the real schema contains.
    saved[1].write_text(json.dumps({**saved[0].as_entry(), "specification": "mismatched"}))
    result = CliRunner().invoke(cli, ["merge", "--method", "claudecode_agent", "--project", "P",
        "--config", "cfg", "--fitness-context", str(saved[1]), "--fitness-cache", str(saved[2]), "--execute"])
    assert result.exit_code != 0 and "expected_context" in result.output
    assert _snapshot(root) == before


def test_fresh_scorer_checks_the_resolved_model_before_any_judgement(tmp_path, monkeypatch):
    # This is a resolution-mismatch control, not a provider or calibration test.
    context = LLMSlotFitnessScorer(model="offline-test", profile=profiles.NEUTRAL)._context("offline-test")
    sc = LLMSlotFitnessScorer(model="offline-test", profile=profiles.NEUTRAL,
                             expected_context=context)
    monkeypatch.setattr(sc, "_resolve", lambda: (object(), "other-resolved-model"))
    with pytest.raises(ValueError, match="expected_context"):
        merge.union_merge(RECORDS, scorer=sc)
    assert sc.calls == sc.memo_hits == 0


def test_cli_requires_both_offline_options(saved):
    from data_sheets_schema.cli.runs import runs as cli
    for option, path in (("--fitness-context", saved[1]), ("--fitness-cache", saved[2])):
        result = CliRunner().invoke(cli, ["merge", "--method", "claudecode_agent", "--project", "P",
                                         "--config", "unused", option, str(path)])
        assert result.exit_code != 0 and "must be supplied together" in result.output


@pytest.mark.parametrize("declared", [
    ["neutral"], {"name": "neutral"}, False, 0, 0.0, "", "   ", [], {},
], ids=["list", "mapping", "false", "zero", "float-zero", "empty-name", "blank-name",
        "empty-list", "empty-mapping"])
def test_cli_refuses_malformed_explicit_profile_before_lookup(saved, tmp_path, monkeypatch, declared):
    """#4858: real opt-in route refuses shapes without a fake scorer/attestation."""
    from data_sheets_schema import runs
    from data_sheets_schema.cli.runs import runs as cli
    root = tmp_path / "d4d_concatenated"
    _sources(root, RECORDS)
    for label in RECORDS:
        path = root / "claudecode_agent_core" / label / "P_provenance.yaml"
        document = yaml.safe_load(path.read_text())
        document["schema"] = {"profile": declared if label == "cfg_rep1" else "neutral"}
        path.write_text(yaml.safe_dump(document))
    monkeypatch.setattr(runs, "CONCAT_DIR", root)
    before = _snapshot(root)
    context_before, cache_before = saved[1].read_bytes(), saved[2].read_bytes()
    result = CliRunner().invoke(cli, ["merge", "--method", "claudecode_agent", "--project", "P",
        "--config", "cfg", "--fitness-context", str(saved[1]), "--fitness-cache", str(saved[2]), "--execute"])
    assert result.exit_code == 1, result.output
    assert "Error: source provenance 'cfg_rep1': schema.profile must be a nonempty profile name or null" in result.output
    assert not isinstance(result.exception, TypeError)
    assert _snapshot(root) == before  # includes no derived output and unchanged source sidecars
    assert saved[1].read_bytes() == context_before and saved[2].read_bytes() == cache_before


@pytest.mark.parametrize("declaration", ["omitted", "null"])
def test_cli_retains_historical_profile_absence_with_real_saved_scores(saved, tmp_path, monkeypatch, declaration):
    """None/omitted keeps the existing study profile; it is not an explicit false value."""
    from data_sheets_schema import runs
    from data_sheets_schema.cli.runs import runs as cli
    context = LLMSlotFitnessScorer(model="offline-test", profile=profiles.BRIDGE2AI)._context("offline-test")
    saved[1].write_text(json.dumps(context.as_entry()))
    saved[2].write_text("".join(json.dumps({**row, **context.as_entry()}) + "\n" for row in saved[3]))
    root = tmp_path / "d4d_concatenated"
    paths = _sources(root, RECORDS)
    if declaration == "null":
        for label in RECORDS:
            path = root / "claudecode_agent_core" / label / "P_provenance.yaml"
            document = yaml.safe_load(path.read_text())
            document["schema"] = {"profile": None}
            path.write_text(yaml.safe_dump(document))
    monkeypatch.setattr(runs, "CONCAT_DIR", root)
    # Neither unscored default nor the historical profile follows this override.
    monkeypatch.setenv("D4D_PROFILE", "neutral")
    before = _snapshot(root)
    context_before, cache_before = saved[1].read_bytes(), saved[2].read_bytes()
    args = ["merge", "--method", "claudecode_agent", "--project", "P", "--config", "cfg"]
    default = CliRunner().invoke(cli, args)
    assert default.exit_code == 0, default.output
    assert "base's value is used" in default.output and "Pinned fitness context" not in default.output
    assert _snapshot(root) == before
    result = CliRunner().invoke(cli, [*args, "--fitness-context", str(saved[1]),
                                    "--fitness-cache", str(saved[2]), "--execute"])
    assert result.exit_code == 0, result.output
    assert '"profile": "bridge2ai"' in result.output
    output = root / "claudecode_agent" / "cfg_merged" / "P_d4d.yaml"
    assert yaml.safe_load(output.read_text()) == {**RECORDS["cfg_rep1"], "description": "second", "only_second": "b"}
    provenance = yaml.safe_load((root / "claudecode_agent_core" / "cfg_merged" / "P_provenance.yaml").read_text())
    _assert_sources_preserved(before, paths, provenance)
    rule = provenance["derivation"]["rule"]
    assert context.specification in rule and '"profile": "bridge2ai"' in rule
    assert hashlib.sha256(cache_before).hexdigest() in rule
    assert saved[1].read_bytes() == context_before and saved[2].read_bytes() == cache_before
