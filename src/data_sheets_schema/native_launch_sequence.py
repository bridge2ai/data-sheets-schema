"""Reviewed one-attempt native capture, guard v2, and launch sequence.

Amendment N1, 2026-11-12. Runs capture-subscription-event,
prepare-subscription-guard-v2, and launch in strict order with the current
Python interpreter, saving each command's stdout to a new file in the packet
directory before parsing, recording UTC timestamps before and after each
command in sequence.json, and stopping immediately on any refusal, nonzero
exit, malformed JSON, or missing field without retry.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys

from . import native_subscription_guard as guard

SEQUENCE_KIND = "d4d_native_launch_sequence"
SEQUENCE_VERSION = 1
MAX_COMMAND_OUTPUT_BYTES = 32 * 1024 * 1024

CAPTURE_OUTPUT_FILENAME = "capture-command.json"
GUARD_OUTPUT_FILENAME = "guard-command.json"
LAUNCH_OUTPUT_FILENAME = "launch-command.json"
SEQUENCE_OUTPUT_FILENAME = "sequence.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _one_line(reason: str) -> str:
    cleaned = " ".join(str(reason).splitlines()).strip()
    return cleaned if cleaned else "native launch sequence stopped"


def _require_canonical_absolute_path(raw_value: str, label: str) -> Path:
    target = Path(raw_value)
    if not target.is_absolute() or str(target) != str(raw_value):
        raise ValueError(f"{label} requires a canonical absolute path")
    parent = target.parent
    if not parent.exists() or parent.is_symlink() or parent.resolve(strict=True) != parent:
        raise ValueError(f"{label} requires an existing resolved parent directory")
    return target


def _prepare_packet_directory(raw_value: str) -> Path:
    target = Path(raw_value)
    if not target.is_absolute() or str(target) != str(raw_value):
        raise ValueError("packet directory requires a canonical absolute path")
    if target.is_symlink():
        raise ValueError("packet directory must not be a symlink")
    if target.exists():
        if not target.is_dir() or target.resolve(strict=True) != target:
            raise ValueError("packet directory must be a resolved directory")
        return target
    parent = target.parent
    if not parent.exists() or parent.is_symlink() or parent.resolve(strict=True) != parent:
        raise ValueError("packet directory requires an existing resolved parent directory")
    target.mkdir(mode=0o700, exist_ok=False)
    return target


def _require_new_target(path: Path, label: str) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing {label}: {path}")


def _write_new_bytes(path: Path, raw: bytes) -> None:
    if not path.is_absolute() or path.parent.resolve(strict=True) != path.parent:
        raise ValueError(f"output requires a canonical absolute path and resolved parent: {path}")
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing output file: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _write_sequence_record(
    sequence_path: Path,
    *,
    status: str,
    started_at: str,
    completed_at: str,
    stop_reason: str | None,
    capture_manifest: str | None,
    guard_sha256: str | None,
    steps: list[dict[str, object]],
) -> None:
    payload = {
        "kind": SEQUENCE_KIND,
        "version": SEQUENCE_VERSION,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "stop_reason": stop_reason,
        "capture_manifest": capture_manifest,
        "guard_sha256": guard_sha256,
        "steps": steps,
    }
    _write_new_bytes(sequence_path, guard.canonical(payload))


def _parse_saved_step_output(output_path: Path, expected_stdout: bytes, subcommand: str) -> dict[str, object]:
    if output_path.is_symlink() or not output_path.is_file():
        raise ValueError(f"{subcommand} saved output is not a regular file")
    if output_path.stat().st_size == 0:
        raise ValueError(f"{subcommand} produced empty stdout")
    saved_raw = guard.read_regular(output_path, limit=MAX_COMMAND_OUTPUT_BYTES)
    if saved_raw != expected_stdout:
        raise ValueError(f"{subcommand} saved output bytes changed before parsing")
    if not saved_raw.strip():
        raise ValueError(f"{subcommand} produced empty stdout")
    try:
        document = guard.strict_json(saved_raw)
    except Exception as exc:
        raise ValueError(f"{subcommand} output is not valid strict JSON") from exc
    if type(document) is not dict:
        raise ValueError(f"{subcommand} output JSON root must be an object")
    if "command" in document and document["command"] != subcommand:
        raise ValueError(f"{subcommand} output command field mismatch: {document['command']}")
    if "result" not in document or type(document["result"]) is not dict or not document["result"]:
        raise ValueError(f"{subcommand} output is missing a non-empty result object")
    return document["result"]


def _run_step(
    subcommand: str,
    flag_args: list[str],
    output_path: Path,
    steps: list[dict[str, object]],
) -> bytes:
    _require_new_target(output_path, f"{subcommand} output file")
    argv = [
        sys.executable,
        "-m",
        "data_sheets_schema.native_generation",
        subcommand,
        *flag_args,
    ]
    step_started_at = _utc_now()
    completed = subprocess.run(
        argv,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )
    step_completed_at = _utc_now()
    raw_stdout = completed.stdout if isinstance(completed.stdout, bytes) else (completed.stdout or "").encode("utf-8")
    _write_new_bytes(output_path, raw_stdout)
    steps.append(
        {
            "step": subcommand,
            "started_at": step_started_at,
            "completed_at": step_completed_at,
            "return_code": int(completed.returncode),
            "output_path": str(output_path),
            "output_sha256": guard.sha(raw_stdout),
        }
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{subcommand} exited with return code {completed.returncode}")
    return raw_stdout


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    result.add_argument("--registration", required=True, help="Registered native execution document path")
    result.add_argument("--review", required=True, help="Reviewed launch bundle path")
    result.add_argument("--launch-word", required=True, help="Exact one-attempt launch word path")
    result.add_argument("--account-choice", required=True, help="Closed D105/D106 account-choice path")
    result.add_argument("--ci", required=True, help="Exact-head CI evidence path")
    result.add_argument(
        "--output-directory",
        required=True,
        help="Registered capture root directory for capture-subscription-event",
    )
    result.add_argument(
        "--subscription-guard",
        "--output",
        dest="subscription_guard",
        required=True,
        help="New output path for prepare-subscription-guard-v2 and input to launch",
    )
    result.add_argument(
        "--packet-directory",
        "--packet",
        dest="packet_directory",
        required=True,
        help="Directory for capture-command.json, guard-command.json, launch-command.json, and sequence.json",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    sequence_started_at = _utc_now()
    steps: list[dict[str, object]] = []
    capture_manifest: str | None = None
    guard_sha256: str | None = None
    sequence_path: Path | None = None

    try:
        registration_path = _require_canonical_absolute_path(args.registration, "registration")
        review_path = _require_canonical_absolute_path(args.review, "review")
        launch_word_path = _require_canonical_absolute_path(args.launch_word, "launch-word")
        account_choice_path = _require_canonical_absolute_path(args.account_choice, "account-choice")
        ci_path = _require_canonical_absolute_path(args.ci, "ci")
        capture_root_path = _require_canonical_absolute_path(args.output_directory, "output-directory")
        guard_output_path = _require_canonical_absolute_path(args.subscription_guard, "subscription-guard")
        packet_dir = _prepare_packet_directory(args.packet_directory)

        capture_out = packet_dir / CAPTURE_OUTPUT_FILENAME
        guard_out = packet_dir / GUARD_OUTPUT_FILENAME
        launch_out = packet_dir / LAUNCH_OUTPUT_FILENAME
        candidate_sequence_path = packet_dir / SEQUENCE_OUTPUT_FILENAME

        _require_new_target(candidate_sequence_path, SEQUENCE_OUTPUT_FILENAME)
        sequence_path = candidate_sequence_path
        _require_new_target(capture_out, CAPTURE_OUTPUT_FILENAME)
        _require_new_target(guard_out, GUARD_OUTPUT_FILENAME)
        _require_new_target(launch_out, LAUNCH_OUTPUT_FILENAME)
        _require_new_target(guard_output_path, "subscription-guard")
        if guard_output_path in {capture_out, guard_out, launch_out, candidate_sequence_path}:
            raise ValueError("subscription-guard path must not collide with a packet command or sequence file")
        for input_path in (registration_path, review_path, launch_word_path, account_choice_path, ci_path):
            guard.read_regular(input_path)
        if (
            not capture_root_path.exists()
            or not capture_root_path.is_dir()
            or capture_root_path.is_symlink()
            or capture_root_path.resolve(strict=True) != capture_root_path
        ):
            raise ValueError("output-directory must be an existing resolved directory")

        # Step 1: capture-subscription-event
        capture_stdout = _run_step(
            "capture-subscription-event",
            [
                "--registration",
                str(registration_path),
                "--review",
                str(review_path),
                "--launch-word",
                str(launch_word_path),
                "--output-directory",
                str(capture_root_path),
                "--account-choice",
                str(account_choice_path),
            ],
            capture_out,
            steps,
        )
        capture_result = _parse_saved_step_output(capture_out, capture_stdout, "capture-subscription-event")
        raw_manifest = capture_result.get("capture_manifest")
        if type(raw_manifest) is not str or not raw_manifest.strip():
            raise ValueError("capture-subscription-event output is missing result.capture_manifest")
        capture_manifest = raw_manifest

        # Step 2: prepare-subscription-guard-v2
        guard_stdout = _run_step(
            "prepare-subscription-guard-v2",
            [
                "--registration",
                str(registration_path),
                "--review",
                str(review_path),
                "--launch-word",
                str(launch_word_path),
                "--capture",
                capture_manifest,
                "--output",
                str(guard_output_path),
                "--account-choice",
                str(account_choice_path),
            ],
            guard_out,
            steps,
        )
        guard_result = _parse_saved_step_output(guard_out, guard_stdout, "prepare-subscription-guard-v2")
        raw_guard_sha = guard_result.get("guard_sha256")
        if type(raw_guard_sha) is not str or not raw_guard_sha.strip():
            raise ValueError("prepare-subscription-guard-v2 output is missing result.guard_sha256")
        if "path" in guard_result and guard_result["path"] != str(guard_output_path):
            raise ValueError("prepare-subscription-guard-v2 result.path differs from requested guard output path")
        guard_sha256 = raw_guard_sha

        # Step 3: launch
        launch_stdout = _run_step(
            "launch",
            [
                "--registration",
                str(registration_path),
                "--review",
                str(review_path),
                "--ci",
                str(ci_path),
                "--launch-word",
                str(launch_word_path),
                "--subscription-guard",
                str(guard_output_path),
                "--subscription-guard-sha256",
                guard_sha256,
                "--account-choice",
                str(account_choice_path),
            ],
            launch_out,
            steps,
        )
        launch_result = _parse_saved_step_output(launch_out, launch_stdout, "launch")
        if "state" in launch_result and launch_result["state"] == "failed":
            raise RuntimeError("launch reported state=failed")
        if "runtime_gates_passed" in launch_result and launch_result["runtime_gates_passed"] is not True:
            raise RuntimeError("launch reported runtime_gates_passed is not True")

        sequence_completed_at = _utc_now()
        _write_sequence_record(
            sequence_path,
            status="completed",
            started_at=sequence_started_at,
            completed_at=sequence_completed_at,
            stop_reason=None,
            capture_manifest=capture_manifest,
            guard_sha256=guard_sha256,
            steps=steps,
        )
        print(
            guard.canonical(
                {
                    "status": "completed",
                    "sequence_path": str(sequence_path),
                    "capture_manifest": capture_manifest,
                    "guard_sha256": guard_sha256,
                }
            ).decode("utf-8")
        )
        return 0
    except Exception as exc:
        reason = _one_line(str(exc))
        sequence_completed_at = _utc_now()
        if sequence_path is not None and not sequence_path.exists() and not sequence_path.is_symlink():
            try:
                _write_sequence_record(
                    sequence_path,
                    status="stopped",
                    started_at=sequence_started_at,
                    completed_at=sequence_completed_at,
                    stop_reason=reason,
                    capture_manifest=capture_manifest,
                    guard_sha256=guard_sha256,
                    steps=steps,
                )
            except Exception as write_exc:
                reason = _one_line(f"{reason}; sequence.json write failed: {write_exc}")
        print(reason, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
