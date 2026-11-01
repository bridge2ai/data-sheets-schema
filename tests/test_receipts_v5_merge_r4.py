"""R4: historical receipt markers remain diagnostics; v5 mismatches still gate."""
from pathlib import Path
import shutil

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import canary, receipts as rc
from data_sheets_schema.cli import receipts as cli
from tests.test_receipt_completion_policy import declaration, disk  # noqa: F401


@pytest.fixture
def historical_record(tmp_path):
    """Copy the reviewer's v3 example; never modify retained run evidence."""
    root = Path(__file__).resolve().parents[1]
    label = "2026-09-12_claude-opus-5-api-generic-v9_rep1"
    corpus = root / "data/d4d_concatenated"
    core = corpus / "claudecode_api_core" / label
    for name in ("CHORUS_coverage_receipt.yaml", "CHORUS_provenance.yaml",
                 "intermediate/CHORUS_full.yaml"):
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(core / name, destination)
    full = tmp_path / "CHORUS_d4d.yaml"
    shutil.copyfile(corpus / "claudecode_api" / label / full.name, full)
    return {"core_dir": tmp_path, "full": full,
            "provenance": tmp_path / "CHORUS_provenance.yaml"}


@pytest.mark.corpus
def test_r4_v3_marker_is_reported_and_strict_passes(historical_record, monkeypatch):
    receipt = historical_record["core_dir"] / "CHORUS_coverage_receipt.yaml"
    receipt.write_text("receipt_format_version: 5\n" + receipt.read_text())
    monkeypatch.setattr(cli, "_run_paths", lambda *args: historical_record)
    blocks = []
    original = rc.block_for

    def capture(*args, **kwargs):
        block = original(*args, **kwargs)
        blocks.append(block)
        return block

    monkeypatch.setattr(rc, "block_for", capture)
    result = CliRunner().invoke(cli.check, ["--method", "claudecode_api", "--label", "fixture",
                                           "--project", "CHORUS", "--strict"])
    assert blocks, result.output
    block = blocks[0]
    assert block["checked"], block
    assert block["instrument"] == rc.receipt_instrument(3)
    assert {"kind": "receipt_format_version_mismatch", "declared": 5, "selected": 3} in block["findings"]
    assert (block["slots"]["with_receipt"], block["slots"]["receiptable"]) == (115, 129)
    assert block["findings_gated"] == 0
    assert canary.receipt_floors(block)["receipt findings"] == 0
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("marker", ["4", 3])
def test_r4_registered_v4_marker_is_reported_not_gated(disk, marker):
    receipt = yaml.safe_load(disk["receipt"].read_text())
    receipt["receipt_format_version"] = marker
    disk["receipt"].write_text(yaml.safe_dump(receipt))
    snapshot = disk["receipt"].parent / "intermediate/P_full.yaml"
    snapshot.parent.mkdir()
    shutil.copyfile(disk["full_path"], snapshot)
    block = rc.block_for(**disk, receipt_render_spec=declaration())
    assert block["checked"], block
    assert block["instrument"] == rc.receipt_instrument(4)
    assert {"kind": "receipt_format_version_mismatch", "declared": marker, "selected": 4} in block["findings"]
    assert block["findings_gated"] == 0
    assert canary.receipt_floors(block)["receipt findings"] == 0
    assert not cli.strict_failure(block)


@pytest.mark.parametrize("marker", ["5", 4])
def test_r4_v5_marker_still_gates(marker):
    receipt = {"bundle_md5": "abc", "chunks": []}
    clean = rc.check(receipt, {"bundle_md5": "abc", "chunks": []}, {}, {}, "abc", instrument_version=5)
    block = rc.check({**receipt, "receipt_format_version": marker},
                     {"bundle_md5": "abc", "chunks": []}, {}, {}, "abc", instrument_version=5)
    assert clean["findings_gated"] == 0
    assert block["findings"] == [{"kind": "receipt_format_version_mismatch", "declared": marker, "selected": 5}]
    assert block["findings_gated"] == 1
    assert canary.receipt_floors(block)["receipt findings"] == 1
    assert cli.strict_failure(block)
