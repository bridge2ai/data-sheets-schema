"""Real-filesystem publication regressions for the completed CBORG reports."""
from contextlib import nullcontext
import errno
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cborg_publication_tests",
    ROOT / "notes/reference_rescore_2026-09-12_cborg_runtime/execution_tools/write_completion_summary.py")
reporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reporter)


@pytest.fixture
def report_files(tmp_path):
    plan = tmp_path / "published"
    plan.mkdir()
    before = {name: ("old qualified " + name).encode() for name in reporter.REPORT_NAMES}
    for name, data in before.items():
        (plan / name).write_bytes(data)
    r = SimpleNamespace(PLAN=plan, canary_lock=nullcontext)
    return r, plan, before


def forbid_content_writes(monkeypatch):
    def full(*args, **kwargs):
        raise OSError(errno.ENOSPC, "persistent storage write failure")
    monkeypatch.setattr(Path, "write_text", full)
    monkeypatch.setattr(Path, "write_bytes", full)


def test_publication_needs_no_content_writes_after_staging(report_files, monkeypatch):
    r, plan, before = report_files
    with reporter.staged_publication(r) as staging:
        for name in reporter.REPORT_NAMES:
            (staging / name).write_bytes(b"new qualified " + name.encode())
        forbid_content_writes(monkeypatch)
    assert r.PLAN == plan
    for name in before:
        assert (plan / name).read_bytes() == b"new qualified " + name.encode()
    assert not list(plan.glob(".report-staging-*"))


@pytest.mark.parametrize("fail_at", [1, 2, 3])
def test_partial_publication_restores_original_inodes_without_writes(report_files, monkeypatch, fail_at):
    r, plan, before = report_files
    inodes = {name: (plan / name).stat().st_ino for name in before}
    replace = os.replace
    published = 0

    def fail_new_files(source, target):
        nonlocal published
        if source.parent.name.startswith(".report-staging-"):
            if published == fail_at:
                raise OSError(errno.ENOSPC, "new report renames refused")
            published += 1
        return replace(source, target)

    with pytest.raises(OSError, match="renames refused"):
        with reporter.staged_publication(r) as staging:
            for name in reporter.REPORT_NAMES:
                (staging / name).write_bytes(b"new qualified " + name.encode())
            forbid_content_writes(monkeypatch)
            monkeypatch.setattr(os, "replace", fail_new_files)
    assert r.PLAN == plan
    assert {name: (plan / name).read_bytes() for name in before} == before
    assert {name: (plan / name).stat().st_ino for name in before} == inodes
    assert not list(plan.glob(".report-staging-*"))


def test_failed_rollback_retains_all_original_backups(report_files, monkeypatch):
    r, plan, before = report_files
    replace = os.replace
    calls = 0

    def fail_after_first_rename(source, target):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise OSError(errno.ENOSPC, "publication and rollback renames refused")
        return replace(source, target)

    with pytest.raises(reporter.ReportRecoveryError, match="backups retained"):
        with reporter.staged_publication(r) as staging:
            for name in reporter.REPORT_NAMES:
                (staging / name).write_bytes(b"new qualified " + name.encode())
            forbid_content_writes(monkeypatch)
            monkeypatch.setattr(os, "replace", fail_after_first_rename)
    assert r.PLAN == plan
    assert {name: (staging / "backups" / name).read_bytes() for name in before} == before
    assert (plan / "results.json").read_bytes() == b"new qualified results.json"


def test_interrupt_after_rename_still_restores_prior_reports(report_files, monkeypatch):
    r, plan, before = report_files
    replace = os.replace

    def interrupt_after_rename(source, target):
        replace(source, target)
        if source.parent.name.startswith(".report-staging-"):
            raise KeyboardInterrupt("interrupted after successful replacement")

    with pytest.raises(KeyboardInterrupt, match="successful replacement"):
        with reporter.staged_publication(r) as staging:
            for name in reporter.REPORT_NAMES:
                (staging / name).write_bytes(b"new qualified " + name.encode())
            monkeypatch.setattr(os, "replace", interrupt_after_rename)
    assert r.PLAN == plan
    assert {name: (plan / name).read_bytes() for name in before} == before
    assert not list(plan.glob(".report-staging-*"))


@pytest.mark.parametrize("cancellation", [KeyboardInterrupt, SystemExit])
def test_cancelled_rollback_retains_original_reports(report_files, monkeypatch, cancellation):
    r, plan, before = report_files
    replace = os.replace
    publications = 0
    interrupted = False

    def fail_publication_then_cancel_rollback(source, target):
        nonlocal publications, interrupted
        if source.parent.name.startswith(".report-staging-"):
            publications += 1
            if publications == 2:
                raise OSError(errno.ENOSPC, "second publication rename refused")
        replace(source, target)
        if source.parent.name == "backups" and not interrupted:
            interrupted = True
            raise cancellation("rollback interrupted after a rename")

    with pytest.raises(reporter.ReportRecoveryError, match="backups retained") as error:
        with monkeypatch.context() as failures:
            failures.setattr(os, "replace", fail_publication_then_cancel_rollback)
            with reporter.staged_publication(r) as staging:
                for name in reporter.REPORT_NAMES:
                    (staging / name).write_bytes(b"new qualified " + name.encode())
    assert interrupted and r.PLAN == plan
    assert staging.is_dir()
    assert str(staging / "backups") in str(error.value)
    assert cancellation.__name__ in str(error.value)
    for name, original in before.items():
        backup = staging / "backups" / name
        assert ((plan / name).read_bytes() == original
                or (backup.is_file() and backup.read_bytes() == original))


def test_backup_failure_leaves_published_files_unchanged(report_files, monkeypatch):
    r, plan, before = report_files

    def fail_link(*args, **kwargs):
        raise OSError(errno.ENOSPC, "backup link refused")

    with pytest.raises(OSError, match="backup link refused"):
        with reporter.staged_publication(r) as staging:
            for name in reporter.REPORT_NAMES:
                (staging / name).write_bytes(b"new qualified " + name.encode())
            monkeypatch.setattr(os, "link", fail_link)
    assert {name: (plan / name).read_bytes() for name in before} == before
    assert not list(plan.glob(".report-staging-*"))
