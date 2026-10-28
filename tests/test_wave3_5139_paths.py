"""Replay the unchanged #5139 historical/scope probe, 2026-10-27.

Inputs: cached canary records at their exact Git head and this candidate checkout.
Outputs: pytest assertions and a temporary JSON observation artifact. No providers,
registrations, or historical run files are written; serves the independent #5139 review.
"""

import json
from pathlib import Path
import socket
import sys

from data_sheets_schema.evaluation import arm_comparison
from scripts.adhoc import review_5139_paths_20261026 as probe


ROOT = Path(__file__).resolve().parents[1]
HISTORY = "ada98b56b73b60217ccacf02fef2af4393d6ecae"
RECORD_HASHES = {
    "2026-10-20a": "3590ec17006cbbdf2f64f47bd5965b8e3453fe388202853531b289d31a1f36df",
    "2026-10-22a": "c0d336563612b4e2244a1438ba0298bde1ad1a76623e622c2036718a94333eca",
}


def test_historical_canaries_and_disclosed_writer_scope(tmp_path, monkeypatch):
    assert Path(arm_comparison.__file__).resolve() == (
        ROOT / "src/data_sheets_schema/evaluation/arm_comparison.py"
    )
    output = tmp_path / "path_observations.json"
    monkeypatch.chdir(ROOT)
    # The original standalone helper changes this directly. Register its prior
    # value so pytest restores it after the unchanged helper completes.
    monkeypatch.setattr(socket.socket, "connect", socket.socket.connect)
    monkeypatch.setattr(sys, "argv", [
        str(ROOT / "scripts/adhoc/review_5139_paths_20261026.py"),
        "--root", str(ROOT), "--history-repo", str(ROOT),
        "--history-ref", HISTORY, "--output", str(output),
    ])
    probe.main()
    observed = json.loads(output.read_text())

    assert observed["history_head"] == HISTORY
    assert len(observed["historical"]) == 2
    for row, (date, expected_hash) in zip(observed["historical"], RECORD_HASHES.items()):
        assert row["record"] == (
            "data/ATTIC/d4d_concatenated_archived/claudecode_api_core/"
            f"{date}_claude-opus-5-api-generic-v10_rep1/CHORUS_provenance.yaml"
        )
        assert row["record_sha256"] == expected_hash
        drift = row["bundle_drift"]
        assert drift["recorded_md5"] == "9b2ef4b65d67957f79362266cab0bc7a"
        assert drift["disk_status"] == "match"
        assert drift["manifest_status"] == "match"
        assert drift["manifest_basis"] == "pinned manifest on disk"
        assert row["recovered_chunk_count"] == 8
        assert row["recovered_chunk_basis"] == "bundle on disk"

    spec = observed["new_runspec"]
    assert spec["bundle"] == "data/preprocessed/concatenated/CHORUS_preprocessed.txt"
    assert spec["manifest"] == "data/preprocessed/source_manifest.yaml"
    for field in ("bundle", "manifest", "chunks"):
        assert not Path(spec[field]).is_absolute()
        assert spec[field].startswith("data/preprocessed/")
    # These writers intentionally retain absolute owner-bound locators. Passing
    # this assertion documents the remaining portability scope; it does not
    # claim that moving their records to another checkout is supported.
    for paths in (
        spec["progress_input_paths"],
        observed["new_flat_provenance_paths"],
        observed["new_registration_paths"],
    ):
        for value in paths.values():
            assert Path(value).is_absolute()
            assert Path(value).is_relative_to(ROOT)
    assert observed["registration_written"] is False
