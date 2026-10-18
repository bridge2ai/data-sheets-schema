"""Identify the rules behind grounding without rewriting historical evidence (#4090)."""

import hashlib
from types import SimpleNamespace
from unittest import mock

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema.grounding import GROUNDING_INSTRUMENT, check_run


@pytest.fixture
def run_files(tmp_path):
    from data_sheets_schema.backfill_checks import record_paths

    provenance = tmp_path / "claudecode_agent_core" / "label" / "VOICE_provenance.yaml"
    provenance.parent.mkdir(parents=True)
    paths = record_paths(provenance)
    body = {
        "id": "ark:12345/present",
        "doi": "https://doi.org/10.1234/study",
        "creators": [{"id": "ROR:032db5x82"}],
    }
    for name in ("full", "core"):
        paths[name].parent.mkdir(parents=True, exist_ok=True)
        paths[name].write_text(yaml.safe_dump(body), encoding="utf-8")
    bundle = tmp_path / "bundle.txt"
    bundle.write_text("ark:12345/present https://doi.org/10.1234/study\n", encoding="utf-8")
    record = {"record_mode": "reconstructed", "inputs": {
        "bundle_path": str(bundle), "bundle_md5": hashlib.md5(bundle.read_bytes()).hexdigest()}}
    provenance.write_text(yaml.safe_dump(record), encoding="utf-8")
    return SimpleNamespace(full_path=paths["full"], core_path=paths["core"],
                           bundle=bundle, provenance=provenance, record=record)


def test_check_run_names_the_rules_while_retaining_counts_and_findings(run_files):
    spec = run_files
    block = check_run(spec.full_path, spec.core_path, spec.bundle, {"id", "doi"})
    assert block["instrument"] == GROUNDING_INSTRUMENT
    assert block["counts"] == {"grounded": 4, "minted_fragment": 0, "absent": 2}
    assert block["distinct"] == {"grounded": 2, "minted_fragment": 0, "absent": 1}
    assert sorted((f["record"], f["kind"]) for f in block["findings"]) == [
        ("core", "identifier_not_in_bundle"), ("core", "resolver_url_in_identifier_slot"),
        ("full", "identifier_not_in_bundle"), ("full", "resolver_url_in_identifier_slot"),
    ]


@pytest.mark.parametrize("missing", ["bundle", "records"])
def test_check_run_names_the_attempted_instrument_on_early_returns(run_files, missing):
    spec = run_files
    if missing == "bundle":
        spec.bundle.unlink()
    else:
        spec.full_path.unlink()
        spec.core_path.unlink()
    block = check_run(spec.full_path, spec.core_path, spec.bundle)
    assert block["instrument"] == GROUNDING_INSTRUMENT
    assert block["checked"] is False
    assert "counts" not in block
    expected = "absent" if missing == "bundle" else "neither record"
    assert expected in block["reason"]


def test_api_wrapper_keeps_instrument_and_bundle_attestation(run_files):
    from data_sheets_schema.api_runner import grounding_block

    block = grounding_block(run_files)
    assert block["checked"] is True
    assert block["instrument"] == GROUNDING_INSTRUMENT
    assert block["artifacts"]["bundle"] == {
        "path": str(run_files.bundle), "md5": run_files.record["inputs"]["bundle_md5"]}


def test_api_wrapper_names_the_instrument_when_computation_raises(run_files):
    from data_sheets_schema.api_runner import grounding_block

    run_files.full_path.write_text("id: [\n", encoding="utf-8")
    block = grounding_block(run_files)
    assert block["checked"] is False
    assert block["instrument"] == GROUNDING_INSTRUMENT
    assert block["reason"]
    assert "counts" not in block


@pytest.mark.parametrize("case", ["match", "no_hash", "no_bundle", "relative_no_base", "missing", "drift"])
def test_backfill_stamps_computations_and_refusals_without_writing(run_files, case):
    from data_sheets_schema.backfill_checks import RECORDED_BY, compute

    spec = run_files
    if case == "no_bundle":
        spec.record["inputs"] = {}
    elif case == "relative_no_base":
        spec.record["inputs"] = {"bundle_path": "somewhere/bundle.txt"}
    elif case == "no_hash":
        spec.record["inputs"].pop("bundle_md5")
    elif case == "missing":
        spec.bundle.unlink()
    elif case == "drift":
        spec.bundle.write_text("changed bundle\n", encoding="utf-8")
    spec.provenance.write_text(yaml.safe_dump(spec.record), encoding="utf-8")
    before = spec.provenance.read_bytes()
    block = compute(spec.provenance, only={"grounding"})["grounding"]
    assert block["instrument"] == GROUNDING_INSTRUMENT
    assert block["recorded_by"] == RECORDED_BY
    assert block["checked"] is (case in {"match", "no_hash"})
    if block["checked"]:
        assert block["schema_basis"]
        assert block["artifacts"]["bundle"]["md5"]
        assert ("bundle_hash_basis" in block) is (case == "no_hash")
    else:
        expected = {"no_bundle": "names no input bundle", "relative_no_base": "no recorded base",
                    "missing": "declared bundle absent", "drift": "bundle drifted"}
        assert expected[case] in block["reason"]
        assert "counts" not in block
    assert spec.provenance.read_bytes() == before


def test_backfill_exclusion_does_not_emit_or_compute_grounding(run_files):
    from data_sheets_schema.backfill_checks import compute

    with mock.patch("data_sheets_schema.grounding.check_run", side_effect=AssertionError("not selected")):
        assert compute(run_files.provenance, only=set()) == {}


@pytest.mark.parametrize("instrument", [None, "v0 historical rules"])
def test_backfill_preserves_historical_identity_until_explicit_overwrite(run_files, instrument):
    from data_sheets_schema.backfill_checks import apply, compute

    spec = run_files
    old = {"checked": True, "counts": {"grounded": 99}}
    if instrument is not None:
        old["instrument"] = instrument
    spec.record["grounding"] = old
    spec.provenance.write_text("# original evidence\n" + yaml.safe_dump(spec.record), encoding="utf-8")
    before = spec.provenance.read_bytes()
    blocks = compute(spec.provenance, only={"grounding"})
    assert not apply(spec.provenance, blocks)
    assert spec.provenance.read_bytes() == before
    assert apply(spec.provenance, blocks, overwrite=True)
    written = yaml.safe_load(spec.provenance.read_text(encoding="utf-8"))
    assert written["grounding"]["instrument"] == GROUNDING_INSTRUMENT
    assert written["grounding"]["counts"]["grounded"] != 99


def test_a_stamped_refusal_cannot_overwrite_a_historical_measurement(run_files):
    from data_sheets_schema.backfill_checks import apply, compute

    spec = run_files
    spec.record["grounding"] = {"checked": True, "distinct": {"absent": 0}}
    spec.provenance.write_text(yaml.safe_dump(spec.record), encoding="utf-8")
    before = spec.provenance.read_bytes()
    spec.bundle.write_text("changed\n", encoding="utf-8")
    blocks = compute(spec.provenance, only={"grounding"})
    withheld = []
    assert not apply(spec.provenance, blocks, overwrite=True, withheld=withheld)
    assert withheld == ["grounding"]
    assert spec.provenance.read_bytes() == before


def test_inline_recorder_stamps_an_unchecked_block(run_files):
    from data_sheets_schema.cli.provenance import _inline_checks

    run_files.bundle.unlink()
    _inline_checks(run_files.provenance)
    block = yaml.safe_load(run_files.provenance.read_text(encoding="utf-8"))["grounding"]
    assert block["instrument"] == GROUNDING_INSTRUMENT
    assert block["checked"] is False
    assert block["recorded_by"] == "d4d provenance record"


@pytest.fixture
def report_tree(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def add(block, *, method="claudecode_agent", label="2026-07-10_test_rep1", project="VOICE"):
        base = tmp_path / "data" / "d4d_concatenated"
        full = base / method / label / f"{project}_d4d.yaml"
        core = base / f"{method}_core" / label / f"{project}_d4d_core.yaml"
        for path in (full, core):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("id: https://example.org/dataset\nname: Test\n", encoding="utf-8")
        core.with_name(f"{project}_reconciliation.md").write_text("# report\n", encoding="utf-8")
        provenance = core.with_name(f"{project}_provenance.yaml")
        record = {"record_mode": "reconstructed", "validation": {
            "passed": True, "artifacts": {
                name: {"path": str(path), "md5": hashlib.md5(path.read_bytes()).hexdigest()}
                for name, path in (("full", full), ("core", core))}}}
        if block is not None:
            record["grounding"] = block
        provenance.write_text(yaml.safe_dump(record), encoding="utf-8")
        return {"method": method, "label": label, "project": project}, provenance

    return add


@pytest.mark.parametrize("instrument, expected", [
    (GROUNDING_INSTRUMENT, "v1"), ("v1 differently described", "v1"),
    (None, "none declared"), ("  \t", "none declared"),
    ("v0 old", "v0"), ("v999 future", "v999"), ("unrecognized", "unrecognized"),
    (17, "invalid instrument"), ({"version": "v1"}, "invalid instrument"),
])
def test_report_handles_missing_different_and_malformed_instruments(report_tree, capsys, instrument, expected):
    from data_sheets_schema.cli.runs import _report_grounding_instruments

    row, provenance = report_tree({"checked": True, "instrument": instrument, "distinct": {"absent": 0}})
    before = provenance.read_bytes()
    with mock.patch("data_sheets_schema.grounding.check_run", side_effect=AssertionError("must not recompute")):
        _report_grounding_instruments([row])
    output = capsys.readouterr().out
    assert f"grounding blocks by instrument: {expected} 1 (current v1)" in output
    assert ("never fatal" in output) is (expected != "v1")
    assert (f"{row['method']}/{row['label']}/{row['project']}" in output) is (expected != "v1")
    assert "older" not in output
    assert provenance.read_bytes() == before


@pytest.mark.parametrize("block", [None, {"checked": False}, {"checked": False, "instrument": GROUNDING_INSTRUMENT}])
def test_unchecked_or_unrecorded_is_not_reported_as_a_stale_measurement(report_tree, capsys, block):
    from data_sheets_schema.cli.runs import _report_grounding_instruments

    row, _ = report_tree(block)
    _report_grounding_instruments([row])
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("case, expected", [("missing", ""), ("directory", "could not read"),
                                           ("yaml", "could not read"), ("list", "malformed provenance")])
def test_instrument_reader_reports_unreadable_provenance(report_tree, capsys, case, expected):
    from data_sheets_schema.cli.runs import _report_grounding_instruments

    row, provenance = report_tree(None)
    if case in {"missing", "directory"}:
        provenance.unlink()
        if case == "directory":
            provenance.mkdir()
    else:
        provenance.write_text("x: [\n" if case == "yaml" else "- x\n", encoding="utf-8")
    _report_grounding_instruments([row])
    output = capsys.readouterr().out
    if expected:
        assert expected in output
        assert f"{row['method']}/{row['label']}/{row['project']}" in output
    else:
        assert output == ""


def test_instrument_report_bounds_the_identity_list(report_tree, capsys):
    from data_sheets_schema.cli.runs import _report_grounding_instruments

    rows = [report_tree({"checked": True}, label=f"old_{n:02d}")[0] for n in range(43)]
    _report_grounding_instruments(rows)
    output = capsys.readouterr().out
    assert "none declared 43" in output
    assert output.count("claudecode_agent/old_") == 40
    assert "… 3 more" in output


@pytest.mark.parametrize("strict", [False, True])
def test_runs_check_reports_zero_finding_unversioned_measurements_nonfatally(report_tree, strict):
    from data_sheets_schema.cli import cli

    row, provenance = report_tree({"checked": True, "distinct": {"absent": 0}})
    before = provenance.read_bytes()
    with mock.patch("data_sheets_schema.grounding.check_run", side_effect=AssertionError("must not recompute")):
        result = CliRunner().invoke(cli, ["runs", "check", *(["--strict"] if strict else [])])
    assert result.exit_code == 0, result.output
    assert "grounding blocks by instrument: none declared 1" in result.output
    assert f"{row['method']}/{row['label']}/{row['project']} (none declared)" in result.output
    assert "never fatal" in result.output
    assert provenance.read_bytes() == before


def test_instrument_warning_does_not_excuse_an_existing_strict_failure(report_tree):
    from data_sheets_schema.backfill_checks import record_paths
    from data_sheets_schema.cli import cli

    _, provenance = report_tree({"checked": True, "distinct": {"absent": 0}})
    record_paths(provenance)["full"].write_text("id: changed\n", encoding="utf-8")
    result = CliRunner().invoke(cli, ["runs", "check", "--strict"])
    assert result.exit_code == 1, result.output
    assert "none declared 1" in result.output
    assert "1 failing" in result.output


def test_runs_check_instrument_report_uses_each_filter_and_disambiguates_methods(report_tree):
    from data_sheets_schema.cli import cli

    block = {"checked": True, "distinct": {"absent": 0}}
    label = "2026-07-10_test_rep1"
    report_tree(block, method="claudecode_agent", label=label, project="VOICE")
    report_tree(block, method="claudecode_api", label=label, project="VOICE")
    report_tree(block, method="claudecode_agent", label=label, project="CM4AI")
    report_tree(block, method="claudecode_agent", label="2026-07-09_test_rep1", project="VOICE")
    unfiltered = CliRunner().invoke(cli, ["runs", "check"])
    assert unfiltered.exit_code == 0, unfiltered.output
    assert "none declared 4" in unfiltered.output
    for method in ("claudecode_agent", "claudecode_api"):
        assert f"{method}/{label}/VOICE (none declared)" in unfiltered.output
    filtered = CliRunner().invoke(cli, ["runs", "check", "--method", "claudecode_agent",
                                      "--label", label, "--project", "VOICE", "--strict"])
    assert filtered.exit_code == 0, filtered.output
    assert "none declared 1" in filtered.output
    assert f"claudecode_agent/{label}/VOICE (none declared)" in filtered.output
    assert "claudecode_api/" not in filtered.output
    assert "CM4AI (none declared)" not in filtered.output
    assert "2026-07-09_test_rep1/" not in filtered.output


def test_canary_counts_do_not_change_with_instrument_identity():
    from data_sheets_schema.canary import counts_from

    block = {"checked": True, "distinct": {"absent": 3, "minted_fragment": 2},
             "findings": [{"kind": "resolver_url_in_identifier_slot", "value": "https://doi.org/10.1234/x"}]}
    expected = counts_from({"grounding": block})
    for instrument in (GROUNDING_INSTRUMENT, "v0 historical", "v999 future"):
        assert counts_from({"grounding": {**block, "instrument": instrument}}) == expected
    assert expected["ungrounded identifiers"] == 3
    assert expected["resolver URLs in identifier slots"] == 1
