"""Offline unit and subprocess tests for native_launch_sequence.

Never invokes the real native_generation subcommands, any provider, model, or
native binary. Tests both patched subprocess.run and real module invocation
(-m data_sheets_schema.native_launch_sequence) with a fake native_generation
placed first on the child module path.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from data_sheets_schema import native_launch_sequence as seq
from data_sheets_schema import native_subscription_guard as guard


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
WORKTREE_SRC = WORKTREE_ROOT / "src"
SCRATCH_ROOT = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-agy2-launch-sequence-20261112"
)


def pytest_configure(config: pytest.Config) -> None:
    if getattr(config.option, "basetemp", None) is None and SCRATCH_ROOT.parent.is_dir():
        basetemp = SCRATCH_ROOT / "basetemp"
        basetemp.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(basetemp)


def _make_paths(tmp_path: Path) -> dict[str, Path]:
    base = tmp_path.resolve()
    inputs_dir = base / "inputs"
    inputs_dir.mkdir(mode=0o700)
    capture_root = base / "captures"
    capture_root.mkdir(mode=0o700)
    packet_dir = base / "packet"
    packet_dir.mkdir(mode=0o700)

    paths = {
        "registration": inputs_dir / "registration.json",
        "review": inputs_dir / "review-bundle.json",
        "launch_word": inputs_dir / "launch-word.json",
        "account_choice": inputs_dir / "account-choice.json",
        "ci": inputs_dir / "ci-evidence.json",
        "output_directory": capture_root,
        "subscription_guard": base / "guard-v2.json",
        "packet_directory": packet_dir,
    }
    for key in ("registration", "review", "launch_word", "account_choice", "ci"):
        paths[key].write_bytes(b"{}\n")
    return paths


def _cli_argv(paths: dict[str, Path], *, use_output_alias: bool = False) -> list[str]:
    guard_flag = "--output" if use_output_alias else "--subscription-guard"
    return [
        "--registration",
        str(paths["registration"]),
        "--review",
        str(paths["review"]),
        "--launch-word",
        str(paths["launch_word"]),
        "--account-choice",
        str(paths["account_choice"]),
        "--ci",
        str(paths["ci"]),
        "--output-directory",
        str(paths["output_directory"]),
        guard_flag,
        str(paths["subscription_guard"]),
        "--packet-directory",
        str(paths["packet_directory"]),
    ]


def _expected_subcommand_argvs(
    paths: dict[str, Path],
    capture_manifest: str,
    guard_sha256: str,
) -> list[list[str]]:
    return [
        [
            sys.executable,
            "-m",
            "data_sheets_schema.native_generation",
            "capture-subscription-event",
            "--registration",
            str(paths["registration"]),
            "--review",
            str(paths["review"]),
            "--launch-word",
            str(paths["launch_word"]),
            "--output-directory",
            str(paths["output_directory"]),
            "--account-choice",
            str(paths["account_choice"]),
        ],
        [
            sys.executable,
            "-m",
            "data_sheets_schema.native_generation",
            "prepare-subscription-guard-v2",
            "--registration",
            str(paths["registration"]),
            "--review",
            str(paths["review"]),
            "--launch-word",
            str(paths["launch_word"]),
            "--capture",
            capture_manifest,
            "--output",
            str(paths["subscription_guard"]),
            "--account-choice",
            str(paths["account_choice"]),
        ],
        [
            sys.executable,
            "-m",
            "data_sheets_schema.native_generation",
            "launch",
            "--registration",
            str(paths["registration"]),
            "--review",
            str(paths["review"]),
            "--ci",
            str(paths["ci"]),
            "--launch-word",
            str(paths["launch_word"]),
            "--subscription-guard",
            str(paths["subscription_guard"]),
            "--subscription-guard-sha256",
            guard_sha256,
            "--account-choice",
            str(paths["account_choice"]),
        ],
    ]


def _assert_iso_utc(timestamp: object) -> datetime:
    assert isinstance(timestamp, str) and timestamp.endswith("Z")
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def test_three_commands_run_in_order_and_forward_manifest_and_guard_sha_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _make_paths(tmp_path)
    exact_manifest = str(paths["output_directory"] / "word-slot-1" / "capture-1" / "capture.json")
    exact_guard_sha = "ab" * 32
    calls: list[tuple[list[str], dict[str, object]]] = []

    responses = {
        "capture-subscription-event": guard.canonical(
            {
                "command": "capture-subscription-event",
                "result": {
                    "capture_manifest": exact_manifest,
                    "sha256": "11" * 32,
                },
            }
        ),
        "prepare-subscription-guard-v2": guard.canonical(
            {
                "command": "prepare-subscription-guard-v2",
                "result": {
                    "guard_sha256": exact_guard_sha,
                    "path": str(paths["subscription_guard"]),
                },
            }
        ),
        "launch": guard.canonical(
            {
                "command": "launch",
                "result": {
                    "attempt_id": "chorus-attempt-1",
                    "state": "completed_pending_independent_review",
                    "runtime_gates_passed": True,
                },
            }
        ),
    }

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append((list(argv), dict(kwargs)))
        assert "env" not in kwargs or kwargs["env"] is None
        subcommand = argv[3]
        return subprocess.CompletedProcess(argv, 0, stdout=responses[subcommand], stderr=b"")

    monkeypatch.setattr(seq.subprocess, "run", fake_run)

    rc = seq.main(_cli_argv(paths))
    assert rc == 0

    expected_argvs = _expected_subcommand_argvs(paths, exact_manifest, exact_guard_sha)
    assert [c[0] for c in calls] == expected_argvs
    assert len(calls) == 3

    # Verify each command's stdout was saved to its packet output file
    packet = paths["packet_directory"]
    assert (packet / "capture-command.json").read_bytes() == responses["capture-subscription-event"]
    assert (packet / "guard-command.json").read_bytes() == responses["prepare-subscription-guard-v2"]
    assert (packet / "launch-command.json").read_bytes() == responses["launch"]

    # Verify sequence.json timestamps and contents
    seq_doc = guard.strict_json((packet / "sequence.json").read_bytes())
    assert seq_doc["kind"] == "d4d_native_launch_sequence"
    assert seq_doc["version"] == 1
    assert seq_doc["status"] == "completed"
    assert seq_doc["stop_reason"] is None
    assert seq_doc["capture_manifest"] == exact_manifest
    assert seq_doc["guard_sha256"] == exact_guard_sha
    t_start = _assert_iso_utc(seq_doc["started_at"])
    t_end = _assert_iso_utc(seq_doc["completed_at"])
    assert t_start <= t_end

    assert len(seq_doc["steps"]) == 3
    assert [s["step"] for s in seq_doc["steps"]] == [
        "capture-subscription-event",
        "prepare-subscription-guard-v2",
        "launch",
    ]
    for step_rec in seq_doc["steps"]:
        s_start = _assert_iso_utc(step_rec["started_at"])
        s_end = _assert_iso_utc(step_rec["completed_at"])
        assert t_start <= s_start <= s_end <= t_end
        assert step_rec["return_code"] == 0
        out_file = Path(step_rec["output_path"])
        assert out_file.exists()
        assert step_rec["output_sha256"] == guard.sha(out_file.read_bytes())

    out_summary = guard.strict_json(capsys.readouterr().out.encode("utf-8"))
    assert out_summary["status"] == "completed"
    assert out_summary["capture_manifest"] == exact_manifest
    assert out_summary["guard_sha256"] == exact_guard_sha


def test_stdout_is_written_to_packet_before_json_parsing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _make_paths(tmp_path)
    exact_manifest = str(paths["output_directory"] / "capture.json")
    exact_guard_sha = "cd" * 32
    observed_files_during_parse: list[tuple[str, bool, bytes]] = []

    real_parse = seq._parse_saved_step_output

    def recording_parse(output_path: Path, expected_stdout: bytes, subcommand: str) -> dict[str, object]:
        exists_now = output_path.exists()
        disk_bytes = output_path.read_bytes() if exists_now else b""
        observed_files_during_parse.append((subcommand, exists_now, disk_bytes))
        return real_parse(output_path, expected_stdout, subcommand)

    monkeypatch.setattr(seq, "_parse_saved_step_output", recording_parse)

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        subcommand = argv[3]
        if subcommand == "capture-subscription-event":
            payload = {"result": {"capture_manifest": exact_manifest}}
        elif subcommand == "prepare-subscription-guard-v2":
            payload = {"result": {"guard_sha256": exact_guard_sha}}
        else:
            payload = {"result": {"state": "completed_pending_independent_review", "runtime_gates_passed": True}}
        return subprocess.CompletedProcess(argv, 0, stdout=guard.canonical(payload), stderr=b"")

    monkeypatch.setattr(seq.subprocess, "run", fake_run)

    assert seq.main(_cli_argv(paths, use_output_alias=True)) == 0
    assert len(observed_files_during_parse) == 3
    for subcommand, existed, raw in observed_files_during_parse:
        assert existed is True, f"Output file for {subcommand} was not on disk before parsing"
        assert len(raw) > 0


@pytest.mark.parametrize(
    ("failing_step_index", "failing_subcommand"),
    [
        (0, "capture-subscription-event"),
        (1, "prepare-subscription-guard-v2"),
        (2, "launch"),
    ],
)
def test_nonzero_exit_at_each_step_stops_immediately_and_never_starts_later_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failing_step_index: int,
    failing_subcommand: str,
) -> None:
    paths = _make_paths(tmp_path)
    started_subcommands: list[str] = []

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        subcommand = argv[3]
        started_subcommands.append(subcommand)
        idx = len(started_subcommands) - 1
        if idx == failing_step_index:
            return subprocess.CompletedProcess(argv, 17, stdout=b'{"error":"refused"}\n', stderr=b"boom\n")
        if subcommand == "capture-subscription-event":
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=guard.canonical({"result": {"capture_manifest": "/tmp/cap.json"}}),
                stderr=b"",
            )
        if subcommand == "prepare-subscription-guard-v2":
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=guard.canonical({"result": {"guard_sha256": "ef" * 32}}),
                stderr=b"",
            )
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=guard.canonical({"result": {"attempt_id": "ok"}}),
            stderr=b"",
        )

    monkeypatch.setattr(seq.subprocess, "run", fake_run)

    rc = seq.main(_cli_argv(paths))
    assert rc == 1

    all_subcommands = ["capture-subscription-event", "prepare-subscription-guard-v2", "launch"]
    assert started_subcommands == all_subcommands[: failing_step_index + 1]
    assert len(started_subcommands) == len(set(started_subcommands))

    err_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]
    assert len(err_lines) == 1
    assert f"{failing_subcommand} exited with return code 17" in err_lines[0]

    packet = paths["packet_directory"]
    seq_doc = guard.strict_json((packet / "sequence.json").read_bytes())
    assert seq_doc["status"] == "stopped"
    assert f"{failing_subcommand} exited with return code 17" in seq_doc["stop_reason"]
    assert len(seq_doc["steps"]) == failing_step_index + 1
    assert seq_doc["steps"][-1]["step"] == failing_subcommand
    assert seq_doc["steps"][-1]["return_code"] == 17

    output_files = ["capture-command.json", "guard-command.json", "launch-command.json"]
    for idx, filename in enumerate(output_files):
        if idx <= failing_step_index:
            assert (packet / filename).exists()
        else:
            assert not (packet / filename).exists()


@pytest.mark.parametrize(
    ("bad_step", "bad_stdout", "expected_substring"),
    [
        ("capture-subscription-event", b"{not-json", "not valid strict JSON"),
        ("capture-subscription-event", b"", "empty stdout"),
        ("capture-subscription-event", b'{"result":{"a":1,"a":2}}', "not valid strict JSON"),
        ("capture-subscription-event", b"[]", "root must be an object"),
        ("capture-subscription-event", b"{}", "missing a non-empty result object"),
        ("capture-subscription-event", b'{"result":{}}', "missing a non-empty result object"),
        ("capture-subscription-event", b'{"result":{"other":"x"}}', "missing result.capture_manifest"),
        ("capture-subscription-event", b'{"result":{"capture_manifest":""}}', "missing result.capture_manifest"),
        ("capture-subscription-event", b'{"command":"launch","result":{"capture_manifest":"/x"}}', "command field mismatch"),
        ("prepare-subscription-guard-v2", b"not-json", "not valid strict JSON"),
        ("prepare-subscription-guard-v2", b'{"result":{}}', "missing a non-empty result object"),
        ("prepare-subscription-guard-v2", b'{"result":{"path":"/x"}}', "missing result.guard_sha256"),
        ("prepare-subscription-guard-v2", b'{"result":{"guard_sha256":""}}', "missing result.guard_sha256"),
        (
            "prepare-subscription-guard-v2",
            b'{"result":{"guard_sha256":"aa","path":"/wrong/path.json"}}',
            "result.path differs",
        ),
        ("launch", b"{bad", "not valid strict JSON"),
        ("launch", b'{"result":{}}', "missing a non-empty result object"),
        ("launch", b'{"result":{"state":"failed"}}', "state=failed"),
        ("launch", b'{"result":{"runtime_gates_passed":false}}', "runtime_gates_passed is not True"),
    ],
)
def test_malformed_json_or_missing_field_stops_sequence_without_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    bad_step: str,
    bad_stdout: bytes,
    expected_substring: str,
) -> None:
    paths = _make_paths(tmp_path)
    started: list[str] = []

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        subcommand = argv[3]
        started.append(subcommand)
        if subcommand == bad_step:
            return subprocess.CompletedProcess(argv, 0, stdout=bad_stdout, stderr=b"")
        if subcommand == "capture-subscription-event":
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=guard.canonical({"result": {"capture_manifest": "/tmp/m.json"}}),
                stderr=b"",
            )
        if subcommand == "prepare-subscription-guard-v2":
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=guard.canonical({"result": {"guard_sha256": "22" * 32}}),
                stderr=b"",
            )
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=guard.canonical({"result": {"attempt_id": "ok"}}),
            stderr=b"",
        )

    monkeypatch.setattr(seq.subprocess, "run", fake_run)

    rc = seq.main(_cli_argv(paths))
    assert rc == 1
    assert started.count(bad_step) == 1
    if bad_step == "capture-subscription-event":
        assert started == ["capture-subscription-event"]
    elif bad_step == "prepare-subscription-guard-v2":
        assert started == ["capture-subscription-event", "prepare-subscription-guard-v2"]
    else:
        assert started == ["capture-subscription-event", "prepare-subscription-guard-v2", "launch"]

    err_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]
    assert len(err_lines) == 1
    assert expected_substring in err_lines[0]

    seq_doc = guard.strict_json((paths["packet_directory"] / "sequence.json").read_bytes())
    assert seq_doc["status"] == "stopped"
    assert expected_substring in seq_doc["stop_reason"]
    assert len(seq_doc["steps"]) == len(started)


@pytest.mark.parametrize(
    "existing_target",
    [
        "capture-command.json",
        "guard-command.json",
        "launch-command.json",
        "sequence.json",
        "subscription_guard",
    ],
)
def test_existing_output_file_is_refused_before_any_command_starts_and_never_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    existing_target: str,
) -> None:
    paths = _make_paths(tmp_path)
    sentinel = b'{"sentinel":"must-not-be-overwritten"}\n'
    if existing_target == "subscription_guard":
        target_path = paths["subscription_guard"]
    else:
        target_path = paths["packet_directory"] / existing_target
    target_path.write_bytes(sentinel)

    def forbidden_run(*args: object, **kwargs: object) -> None:
        pytest.fail("subprocess.run must not be called when an output file already exists")

    monkeypatch.setattr(seq.subprocess, "run", forbidden_run)

    rc = seq.main(_cli_argv(paths))
    assert rc == 1
    assert target_path.read_bytes() == sentinel

    err_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]
    assert len(err_lines) == 1
    assert "refusing to overwrite existing" in err_lines[0]

    seq_file = paths["packet_directory"] / "sequence.json"
    if existing_target == "sequence.json":
        assert seq_file.read_bytes() == sentinel
    else:
        assert seq_file.exists()
        seq_doc = guard.strict_json(seq_file.read_bytes())
        assert seq_doc["status"] == "stopped"
        assert seq_doc["steps"] == []
        assert "refusing to overwrite existing" in seq_doc["stop_reason"]


def test_real_module_execution_with_fake_native_generation_first_on_pythonpath(
    tmp_path: Path,
) -> None:
    paths = _make_paths(tmp_path)
    fake_root = tmp_path.resolve() / "fake_pkg"
    fake_pkg = fake_root / "data_sheets_schema"
    fake_pkg.mkdir(parents=True, mode=0o700)
    invocation_log = tmp_path.resolve() / "child_invocations.jsonl"
    manifest_out = str(paths["output_directory"] / "slot-1" / "capture.json")
    guard_sha = "99" * 32

    (fake_pkg / "__init__.py").write_text(
        f"import pathlib\n__path__.append({str(WORKTREE_SRC / 'data_sheets_schema')!r})\n",
        encoding="utf-8",
    )
    (fake_pkg / "native_generation.py").write_text(
        f"""from __future__ import annotations
import json, os, sys
from pathlib import Path

log_path = Path({str(invocation_log)!r})
subcommand = sys.argv[1]
with log_path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps({{
        "argv": sys.argv[1:],
        "sentinel_env": os.environ.get("D4D_TEST_UNEDITED_ENV_SENTINEL"),
    }}) + "\\n")

if subcommand == "capture-subscription-event":
    print(json.dumps({{
        "command": subcommand,
        "result": {{"capture_manifest": {manifest_out!r}, "sha256": "aa" * 32}},
    }}))
elif subcommand == "prepare-subscription-guard-v2":
    print(json.dumps({{
        "command": subcommand,
        "result": {{"guard_sha256": {guard_sha!r}, "path": {str(paths["subscription_guard"])!r}}},
    }}))
elif subcommand == "launch":
    print(json.dumps({{
        "command": subcommand,
        "result": {{"attempt_id": "subproc-1", "state": "completed_pending_independent_review", "runtime_gates_passed": True}},
    }}))
else:
    raise SystemExit(2)
""",
        encoding="utf-8",
    )

    child_env = dict(os.environ)
    child_env["PYTHONPATH"] = f"{fake_root}{os.pathsep}{WORKTREE_SRC}"
    child_env["D4D_TEST_UNEDITED_ENV_SENTINEL"] = "untouched-value-42"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "data_sheets_schema.native_launch_sequence",
            *_cli_argv(paths),
        ],
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

    recorded = [
        json.loads(line)
        for line in invocation_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(recorded) == 3
    assert [r["argv"][0] for r in recorded] == [
        "capture-subscription-event",
        "prepare-subscription-guard-v2",
        "launch",
    ]
    assert all(r["sentinel_env"] == "untouched-value-42" for r in recorded)

    seq_doc = guard.strict_json((paths["packet_directory"] / "sequence.json").read_bytes())
    assert seq_doc["status"] == "completed"
    assert seq_doc["capture_manifest"] == manifest_out
    assert seq_doc["guard_sha256"] == guard_sha
    assert len(seq_doc["steps"]) == 3


def test_native_launch_sequence_introduces_no_run_spec_boundaries() -> None:
    from tests.utils.run_spec_boundaries import discover

    hits = [
        item
        for item in discover(WORKTREE_ROOT)
        if item.path == "src/data_sheets_schema/native_launch_sequence.py"
    ]
    assert hits == []


def test_input_preflight_refuses_missing_input_or_reserved_packet_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _make_paths(tmp_path)

    def forbidden_run(*args: object, **kwargs: object) -> None:
        pytest.fail("subprocess.run must not be called on preflight failure")

    monkeypatch.setattr(seq.subprocess, "run", forbidden_run)

    # Collision: --subscription-guard pointing to packet/capture-command.json
    colliding = dict(paths)
    colliding["subscription_guard"] = paths["packet_directory"] / "capture-command.json"
    rc = seq.main(_cli_argv(colliding))
    assert rc == 1
    err = capsys.readouterr().err
    assert "must not collide with a packet command or sequence file" in err

    # Missing registration file with a fresh packet directory
    paths["packet_directory"] = tmp_path.resolve() / "packet_missing_reg"
    paths["registration"].unlink()
    rc2 = seq.main(_cli_argv(paths))
    assert rc2 == 1
    err2 = capsys.readouterr().err
    assert "No such file or directory" in err2


@pytest.mark.parametrize(
    "forbidden_flag",
    [
        "--skip",
        "--resume",
        "--reuse-capture",
        "--continue-on-error",
    ],
)
def test_parser_rejects_skip_resume_reuse_or_continue_flags(
    tmp_path: Path,
    forbidden_flag: str,
) -> None:
    paths = _make_paths(tmp_path)
    with pytest.raises(SystemExit):
        seq.parser().parse_args([*_cli_argv(paths), forbidden_flag])
