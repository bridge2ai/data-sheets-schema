"""Automatically dated runs can resume the next day without changing instruments."""
from datetime import datetime, timezone
from dataclasses import replace

import pytest
from click.testing import CliRunner

from data_sheets_schema import api_runner as api, usage_ledger as ledger, provenance
from data_sheets_schema.cli import cli
from tests.test_download.test_api_runner import FakeClient
from tests.test_generation_manifest_identity import external, offline, snapshot  # noqa: F401


class Clock(datetime):
    day = 12

    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, cls.day, 12, tzinfo=timezone.utc)


def construct(original, **changes):
    # Reconstruct the same way a CLI invocation does, without carrying a date.
    return api.RunSpec(project=original.project, arm=original.arm, method=original.method,
                       bundle=original.bundle, label=original.label, condition=original.condition,
                       manifest=original.manifest, chunk_manifest=original.chunk_manifest,
                       out_dir=original.out_dir, **changes)


@pytest.mark.parametrize("completed,journal", [(False, True), (True, True), (True, False)])
def test_automatic_date_is_restored_before_cached_instruction_or_portable_checks(external, monkeypatch, completed, journal):
    monkeypatch.setattr(api, "datetime", Clock)
    Clock.day = 12
    original = construct(external)
    first = FakeClient()
    if not completed:
        first.messages.fail_on = "audit"
        with pytest.raises(RuntimeError, match="boom"):
            api.execute(original, client=first)
    else:
        api.execute(original, client=first)
    if not journal:
        ledger.ledger_path(original).unlink()
    before = snapshot(original.out_dir)
    Clock.day = 13
    resumed = construct(external)
    current_day_instruction = resumed.instruction  # batch plans before execute
    client = FakeClient()
    result = api.execute(resumed, client=client)
    assert resumed.run_date == "2026-09-12"
    assert resumed.instruction == original.instruction != current_day_instruction
    if completed:
        assert result["already_complete"] and not client.messages.calls
        assert snapshot(original.out_dir) == before
    else:
        assert "full" in result["skipped"] and "core" in result["skipped"]
        assert len(client.messages.calls) == 3 and len(result["usage"]) == 4


def test_explicit_changed_date_is_refused_without_spending_or_writing(external, monkeypatch):
    monkeypatch.setattr(api, "datetime", Clock)
    Clock.day = 12
    original = construct(external)
    api.execute(original, client=FakeClient())
    before = snapshot(original.out_dir)
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="input identity changed"):
        api.execute(construct(external, run_date="2026-09-13"), client=client)
    assert client.messages.calls == [] and snapshot(original.out_dir) == before


@pytest.mark.parametrize("mode", ["fresh", "foreign"])
def test_new_generation_does_not_inherit_a_predecessors_date(external, monkeypatch, mode):
    monkeypatch.setattr(api, "datetime", Clock)
    Clock.day = 12
    api.execute(construct(external), client=FakeClient())
    Clock.day = 13
    seed = replace(external, label="another-label") if mode == "foreign" else external
    current = construct(seed)
    client = FakeClient()
    api.execute(current, resume=mode != "fresh", client=client)
    assert current.run_date == "2026-09-13"
    assert len(client.messages.calls) == 4


def test_restored_automatic_date_does_not_hide_changed_instruction(external, monkeypatch):
    monkeypatch.setattr(api, "datetime", Clock)
    Clock.day = 12
    api.execute(construct(external), client=FakeClient())
    before = snapshot(external.out_dir)
    Clock.day = 13
    render = api.resolve_prompt
    monkeypatch.setattr(api, "resolve_prompt", lambda spec: render(spec) + "\nChanged scoring request.\n")
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="input identity changed"):
        api.execute(construct(external), client=client)
    assert not client.messages.calls and snapshot(external.out_dir) == before


@pytest.mark.parametrize("completed", [False, True])
def test_batch_reconstructs_an_automatic_date_and_resumes_next_day(external, monkeypatch, completed):
    monkeypatch.setattr(api, "datetime", Clock)
    Clock.day = 12
    # Keep all actual CLI planning, construction and execution, with isolated
    # output roots and a fake provider. The canary comparison is orthogonal.
    root = external.out_dir / "batch"
    monkeypatch.setattr(provenance, "CONCAT_DIR", root)
    monkeypatch.setattr(api, "CONCAT_DIR", root)
    client = FakeClient()
    monkeypatch.setattr(api, "_client", lambda: client)
    from data_sheets_schema import run_lock
    monkeypatch.setattr(run_lock, "acquire", lambda *args: external.out_dir / "unused-lock")
    monkeypatch.setattr(run_lock, "release", lambda *args: None)
    args = ["api", "batch", "--projects", external.project, "--manifest", str(external.manifest),
            "--project-bundle", f"{external.project}={external.bundle}", "--replicates", "1",
            "--condition", "generic_v6", "--label-prefix", "midnight-generic-v6", "--no-branch-guard", "--yes"]
    if not completed:
        client.messages.fail_on = "audit"
    first = CliRunner().invoke(cli, args)
    assert first.exit_code == (0 if completed else 1), first.output
    # The fake records the failed audit attempt as well as the delivered full phase.
    assert len(client.messages.calls) == (4 if completed else 2)
    Clock.day = 13
    client = FakeClient()
    second = CliRunner().invoke(cli, args)
    assert second.exit_code == 0, second.output
    assert len(client.messages.calls) == (0 if completed else 3)
