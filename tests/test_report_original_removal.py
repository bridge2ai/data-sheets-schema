"""A continued omission is not a removal from the original record (#1808)."""
import pytest

from data_sheets_schema.report_claims import check_report


def check(tmp_path, *, record="both", slot="errata", before=None, full=None, prose=False, version=8):
    report = tmp_path / "report.md"
    report.write_text((f"**Action:** `{slot}` was removed from the {record} record.\n" if prose else
        "## Dispositions\n\n| slot | disposition | record | reason |\n"
        "| --- | --- | --- | --- |\n"
        f"| `{slot}` | removed | {record} | Omitted. |\n"))
    return check_report(report, full if full is not None else {"id": "demo"}, {"id": "demo"},
        {"Dataset": {"id", "errata"}, "CoreDataset": {"id", "errata"}},
        snapshot=before, dispositions_expected=True, instrument_version=version)["findings"]


@pytest.mark.parametrize("record", ["full", "both"])
@pytest.mark.parametrize("before", [{}, {"id": "demo"}])
def test_absence_in_both_versions_is_not_a_removal(tmp_path, record, before):
    findings = check(tmp_path, record=record, before=before)
    assert [(f["kind"], f["slot"], f["record"]) for f in findings] == [
        ("removal_of_absent_slot", "errata", record)]


@pytest.mark.parametrize("value", [None, [], {}, "", [{"description": "old"}]])
def test_a_key_that_existed_can_be_removed(tmp_path, value):
    assert check(tmp_path, before={"id": "demo", "errata": value}) == []


def test_no_original_snapshot_is_not_evidence_of_absence(tmp_path):
    assert check(tmp_path, before=None) == []


@pytest.mark.parametrize("record", ["core", ""])
def test_a_full_snapshot_does_not_establish_a_prior_core(tmp_path, record):
    assert check(tmp_path, record=record, before={}) == []


@pytest.mark.parametrize("slot", ["errata[0]", "errata[0].description", "errata.description"])
def test_nested_entry_identity_is_not_inferred_from_missing_paths(tmp_path, slot):
    assert check(tmp_path, slot=slot, before={}) == []


def test_a_present_final_value_keeps_the_existing_finding(tmp_path):
    findings = check(tmp_path, before={}, full={"errata": ["still here"]})
    assert [f["kind"] for f in findings] == ["removal_not_performed"]


def test_explicit_full_record_prose_uses_the_same_original(tmp_path):
    assert [f["kind"] for f in check(tmp_path, record="full", before={}, prose=True)] == [
        "removal_of_absent_slot"]


def test_explicit_historical_replay_keeps_the_prior_measurement(tmp_path):
    assert check(tmp_path, before={}, version=7) == []
    assert [f["kind"] for f in check(tmp_path, before={})] == ["removal_of_absent_slot"]


@pytest.mark.parametrize("version", [6, 9, "8", 8.0])
def test_unknown_instruments_are_not_mislabelled(tmp_path, version):
    with pytest.raises(ValueError, match="unsupported report-claims"):
        check(tmp_path, before={}, version=version)
