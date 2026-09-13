"""Public reporting must retain qualifications without rewriting measurements."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reference_rescore_cborg as adapter
import reference_rescore_cborg_batch as batch
import reference_rescore_cborg_deadline as deadline

PLAN = ROOT / f"notes/reference_rescore_{adapter.DATE}"


@pytest.fixture
def reports_in_memory(monkeypatch):
    paths = [PLAN / name for name in (
        "results.json", "results.md", "completion_summary.md", "semantic_review.md")]
    read_bytes, read_text = Path.read_bytes, Path.read_text
    write_bytes, write_text, unlink = Path.write_bytes, Path.write_text, Path.unlink
    before = {p: read_bytes(p) for p in paths}
    files = dict(before)
    monkeypatch.setattr(Path, "read_bytes", lambda p: files[p] if p in files else read_bytes(p))
    monkeypatch.setattr(Path, "read_text", lambda p, *a, **k:
                        files[p].decode(k.get("encoding") or "utf-8") if p in files else read_text(p, *a, **k))

    def put_bytes(path, data):
        if path in before:
            files[path] = bytes(data)
            return len(data)
        return write_bytes(path, data)

    def put_text(path, data, *args, **kwargs):
        if path in before:
            files[path] = data.encode(kwargs.get("encoding") or "utf-8")
            return len(data)
        return write_text(path, data, *args, **kwargs)

    def remove(path, *args, **kwargs):
        if path in before:
            files.pop(path, None)
        else:
            return unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_bytes", put_bytes)
    monkeypatch.setattr(Path, "write_text", put_text)
    monkeypatch.setattr(Path, "unlink", remove)
    # The real completion audit is run separately. These tests exercise the
    # public report path and its publication transaction against real records.
    audit = json.loads(read_bytes(PLAN / "completion_audit.json"))
    monkeypatch.setattr(deadline, "accounted_audit", lambda *a: copy.deepcopy(audit))
    yield files, before
    assert {p: read_bytes(p) for p in paths} == before


def test_public_report_keeps_every_qualification(reports_in_memory):
    files, _ = reports_in_memory
    assert adapter.main(["report"]) == 0
    result = json.loads(files[PLAN / "results.json"])
    assert result["completed"] == 56 and not result["pending"]
    assert len(result["semantic_qualification"]["affected_job_ids"]) == 9
    assert result["cost_accounting"]["cli_reported_total_cost_usd"] is None
    assert len(result["cost_accounting"]["unpriced_excluded_sessions"]) == 2
    assert len(result["evaluation_timestamp_qualification"]["cases"]) == 56
    assert result["evaluation_narrative_qualification"]["issue"] == 1352
    assert result["additional_evaluation_narrative_qualifications"][0]["issue"] == 1355
    assert result["measured_code_archive"]["sha256"] == adapter.MEASURED_SHA256
    assert len(result["execution_permission_boundary"]["accepted_before_job_ids"]) == 5
    assert len(result["execution_deadline_boundary"]["accepted_before_job_ids"]) == 17
    for path, content in files.items():
        if path.suffix == ".md":
            for heading in ("Semantic inspection", "Execution boundary", "Execution deadline",
                            "Incomplete cost accounting", "Evaluation prose", "CM4AI pilot judgments",
                            "Evaluation timing", "Measured code archive"):
                assert heading.encode() in content


@pytest.mark.parametrize("name", ["semantic_review.json", "canary_narrative_qualification.json",
                                  "cm4ai_pilot_narrative_qualification_1355.json"])
def test_missing_qualification_preserves_published_reports(monkeypatch, reports_in_memory, name):
    files, before = reports_in_memory
    read = Path.read_bytes

    def missing(path):
        if path == PLAN / name:
            raise FileNotFoundError(name)
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", missing)
    with pytest.raises(FileNotFoundError):
        adapter.main(["report"])
    assert files == before


def test_wrong_condition_qualification_preserves_reports(monkeypatch, reports_in_memory):
    files, before = reports_in_memory
    read = Path.read_bytes
    path = PLAN / "semantic_review.json"
    wrong = json.loads(read(path))
    wrong["manifest_sha256"] = "0" * 64
    monkeypatch.setattr(Path, "read_bytes", lambda p: json.dumps(wrong).encode() if p == path else read(p))
    with pytest.raises(ValueError, match="another condition"):
        adapter.main(["report"])
    assert files == before


def test_failure_after_raw_write_restores_all_reports(monkeypatch, reports_in_memory):
    files, before = reports_in_memory
    load = batch.load_registered

    def failing_runner():
        r, manifest, registration = load()
        raw = r.report_results

        def fail_after_write(m):
            raw(m)
            assert files[PLAN / "results.json"] != before[PLAN / "results.json"]
            raise RuntimeError("failure after unqualified intermediate write")

        r.report_results = fail_after_write
        return r, manifest, registration

    monkeypatch.setattr(batch, "load_registered", failing_runner)
    with pytest.raises(RuntimeError, match="unqualified intermediate"):
        adapter.main(["report"])
    assert files == before


def test_archive_binding_preserves_manifest_and_honest_file_digests():
    raw = (PLAN / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    before = copy.deepcopy(manifest)
    resolved = adapter.measured_pinned_files(manifest)
    assert manifest == before
    assert adapter.MEASURED_PATH not in resolved
    assert resolved[adapter.MEASURED_ARCHIVE] == adapter.MEASURED_SHA256
    assert hashlib.sha256(raw).hexdigest() == adapter.MEASURED_MANIFEST_SHA256
    r = adapter.load_runner()
    assert r.digest(ROOT / adapter.MEASURED_PATH) != adapter.MEASURED_SHA256
    r.verify_frozen(manifest)


@pytest.mark.parametrize("relative,expected", [
    (adapter.MEASURED_PATH, adapter.MEASURED_SHA256),
    ("scripts/reference_rescore_cborg_batch.py", adapter.MEASURED_SCHEDULER_SHA256),
])
def test_changed_archive_is_rejected(monkeypatch, relative, expected):
    path = adapter.measured_code_path(relative, expected)
    read = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda p: read(p) + b"\n" if p == path else read(p))
    with pytest.raises(ValueError, match="execution bytes changed"):
        adapter.measured_code_path(relative, expected)


def test_changed_manifest_cannot_borrow_historical_code_pin():
    manifest = json.loads((PLAN / "manifest.json").read_bytes())
    manifest["budget_cap_usd_per_attempt"] = 6
    with pytest.raises(ValueError, match="registered manifest"):
        adapter.measured_pinned_files(manifest)


@pytest.mark.parametrize("action", ["freeze", "canary", "remaining", "accept-canary", "--print"])
def test_completed_public_cli_refuses_measurement_actions(action):
    with pytest.raises(SystemExit) as error:
        adapter.main([action])
    assert error.value.code == 2


@pytest.mark.parametrize("action", ["pilot", "accept-pilot", "remaining", "worker"])
def test_completed_batch_cannot_create_new_attempts(action):
    with pytest.raises(ValueError, match="condition is complete"):
        batch.main([action])
