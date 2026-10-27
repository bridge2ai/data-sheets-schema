"""Default native front door: offline dispatch and required launch authority (#4354)."""
import pytest

from data_sheets_schema import native_generation as cli
from data_sheets_schema import native_shared_permissions as permissions


def test_validate_probe_uses_saved_bytes_and_never_runs_a_producer(tmp_path, monkeypatch, capsys):
    expected = {"kind": permissions.EXPECTED_KIND}
    expectation = tmp_path / "expectation.json"
    expectation.write_bytes(cli.guard.canonical(expected))
    probe_path = tmp_path / "saved.json"
    probe_path.write_bytes(b"saved synthetic probe")
    calls = []

    def verify(raw, *, expected):
        calls.append((raw, expected))
        return {"saved": True}

    from data_sheets_schema import native_permission_probe
    monkeypatch.setattr(native_permission_probe, "produce_saved_probe",
                        lambda *a, **k: pytest.fail("offline validation launched a probe"))
    monkeypatch.setattr(permissions, "verify_saved_probe", verify)
    assert cli.main(["validate-probe", "--expectation", str(expectation),
                     "--probe", str(probe_path)]) == 0
    assert calls == [(b"saved synthetic probe", expected)]
    assert '"saved":true' in capsys.readouterr().out


@pytest.mark.parametrize("missing", ["subscription-guard", "subscription-guard-sha256"])
def test_launch_requires_both_guard_authorities_before_any_dispatch(monkeypatch, missing):
    from data_sheets_schema import native_shared_execution
    monkeypatch.setattr(native_shared_execution, "launch",
                        lambda *a, **k: pytest.fail("incomplete launch dispatched"))
    args = ["launch"]
    for name in ("registration", "review", "ci", "launch-word",
                 "subscription-guard", "subscription-guard-sha256"):
        if name != missing:
            args.extend(["--" + name, "/invented/" + name])
    with pytest.raises(SystemExit) as exc:
        cli.main(args)
    assert exc.value.code == 2


def test_prepare_guard_joins_saved_authorities_without_launch(tmp_path, monkeypatch):
    from data_sheets_schema import native_shared_registration
    from data_sheets_schema import native_shared_execution
    monkeypatch.setattr(native_shared_execution, "launch",
                        lambda *a, **k: pytest.fail("guard preparation dispatched"))
    runtime = {"synthetic_runtime": True}
    registration_raw = b"synthetic registration"
    word_raw, event_raw = b"synthetic launch word", b"synthetic event"
    paths = {}
    for name, raw in (("registration", registration_raw), ("launch-word", word_raw),
                      ("event", event_raw)):
        paths[name] = tmp_path / name
        paths[name].write_bytes(raw)
    calls = []

    def verify(raw):
        assert raw == registration_raw
        return {"runtime": runtime}

    def prepare(**kwargs):
        calls.append(kwargs)
        return b"synthetic bound guard"

    monkeypatch.setattr(native_shared_registration, "verified", verify)
    monkeypatch.setattr(cli.guard, "prepare_guard", prepare)
    output = tmp_path / "guard.json"
    args = ["prepare-subscription-guard", "--captured-at", "2026-10-25T00:00:00Z",
            "--max-starting-weekly-utilization", "0.8", "--max-age-seconds", "300",
            "--output", str(output)]
    for name, path in paths.items():
        args.extend(["--" + name, str(path)])
    assert cli.main(args) == 0
    assert output.read_bytes() == b"synthetic bound guard"
    assert calls == [{"registration_raw": registration_raw, "runtime": runtime,
                      "launch_word_raw": word_raw, "event_raw": event_raw,
                      "captured_at": "2026-10-25T00:00:00Z",
                      "maximum_starting_utilization": 0.8, "max_age_seconds": 300}]
    with pytest.raises(FileExistsError):
        cli.main(args)
    assert output.read_bytes() == b"synthetic bound guard"
