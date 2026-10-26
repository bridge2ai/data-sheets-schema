"""D4D API Launcher (Step A4b / #4345, #777).

Enforces worktree code isolation, environment variable hygiene, and launch safeguards
for D4D API generation runs and offline checks.

Key safeguards:
1. Changes working directory to the target worktree root (required by batch execution).
2. Strips hazardous environment variables (all ANTHROPIC_* and D4D_* variables, including:
   - ANTHROPIC_API_KEY (would override CBORG API key in api_runner.py)
   - D4D_RECEIPT_FULL_MAX_TOKENS (would lower output token limit below 128,000)
   - D4D_PHASE_WALL_CLOCK_SECONDS (would alter the 3,600s per-call watchdog))
3. Enforces PYTHONUNBUFFERED=1 and PYTHONPATH=<worktree>/src.
4. Requires CBORG_API_KEY to be set in process environment (unless explicitly bypassed for --check-only or --dry-run).
5. Refuses the unbudgeted single-run command 'd4d api run' (D20 requirement) and non-D4D shell commands.
   Note: '--max-cost-dollars' on 'd4d api batch' is checked between runs (not mid-run), so a single run or
   single-run canary is not stopped mid-execution by '--max-cost-dollars'; mid-run monitoring uses dollar_readout.
6. Enforces strict worktree import isolation check:
   - data_sheets_schema.__file__ must be None (namespace package)
   - every entry of list(data_sheets_schema.__path__) must resolve to <worktree>/src/data_sheets_schema
   - required modules (api_runner, shared_generation, typed_audit_runtime, receipt_completion, cli.api)
     must resolve to files under <worktree>/src
7. Supports dry-run, check-only, and detached background launch under caffeinate -ims with nohup logging
   outside the worktree and stdin redirected to /dev/null so detached children never fail in init_sys_streams.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ALLOWED_TOP_COMMANDS = frozenset({
    "d4d",
    "python",
    "python3",
    "api",
    "bundle",
    "download",
    "runs",
    "evaluate",
    "utils",
})

ALLOWED_API_SUBCOMMANDS = frozenset({
    "batch",
    "plan",
    "status",
    "stop",
    "verdict",
    "prompts",
    "check-routing-completed",
})


class LauncherError(Exception):
    """Raised when launcher validation or execution checks fail."""


def _stdin_is_valid() -> bool:
    """Return True if file descriptor 0 is an open valid file descriptor."""
    try:
        os.fstat(0)
        return True
    except OSError:
        return False


IMPORT_CHECK_SNIPPET = """
import os
import sys

worktree = os.path.realpath(sys.argv[1])
expected_schema_dir = os.path.realpath(os.path.join(worktree, "src", "data_sheets_schema"))
expected_src_dir = os.path.realpath(os.path.join(worktree, "src"))

try:
    import data_sheets_schema
except Exception as exc:
    sys.exit(f"Failed to import data_sheets_schema: {exc}")

# Verify data_sheets_schema is a namespace package with no __file__
schema_file = getattr(data_sheets_schema, "__file__", None)
if schema_file is not None:
    sys.exit(f"data_sheets_schema.__file__ must be None (namespace package), got {schema_file!r}")

# Verify every entry of data_sheets_schema.__path__ resolves to <worktree>/src/data_sheets_schema
raw_paths = list(getattr(data_sheets_schema, "__path__", []))
if not raw_paths:
    sys.exit("data_sheets_schema.__path__ is empty")

resolved_paths = [os.path.realpath(p) for p in raw_paths]
for p in resolved_paths:
    if p != expected_schema_dir:
        sys.exit(
            f"data_sheets_schema.__path__ entry {p!r} does not resolve to expected {expected_schema_dir!r} "
            f"(resolved paths: {resolved_paths!r})"
        )

# Verify required submodules resolve strictly under <worktree>/src
required_modules = [
    "data_sheets_schema.api_runner",
    "data_sheets_schema.shared_generation",
    "data_sheets_schema.typed_audit_runtime",
    "data_sheets_schema.receipt_completion",
    "data_sheets_schema.cli.api",
]

for mod_name in required_modules:
    try:
        mod = __import__(mod_name, fromlist=["*"])
    except Exception as exc:
        sys.exit(f"Failed to import submodule {mod_name!r}: {exc}")
    mod_file = getattr(mod, "__file__", None)
    if not mod_file:
        sys.exit(f"Submodule {mod_name!r} has no __file__")
    resolved_mod_file = os.path.realpath(mod_file)
    if not (resolved_mod_file == expected_src_dir or resolved_mod_file.startswith(expected_src_dir + os.sep)):
        sys.exit(
            f"Submodule {mod_name!r} file {resolved_mod_file!r} is not under worktree src {expected_src_dir!r}"
        )

print("IMPORT_CHECK_OK")
"""


def clean_environment(
    worktree_dir: str | Path,
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return a sanitized environment dictionary for child process execution.

    Unsets all ANTHROPIC_* and D4D_* variables (including ANTHROPIC_API_KEY,
    D4D_RECEIPT_FULL_MAX_TOKENS, and D4D_PHASE_WALL_CLOCK_SECONDS).
    Sets PYTHONUNBUFFERED=1 and PYTHONPATH=<worktree>/src.
    """
    env = dict(os.environ if base_env is None else base_env)
    for key in list(env.keys()):
        if key.startswith("ANTHROPIC_") or key.startswith("D4D_"):
            env.pop(key, None)

    resolved_src = str(Path(worktree_dir).resolve() / "src")
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = resolved_src
    return env


def check_cborg_key(env: dict[str, str], allow_missing: bool = False) -> None:
    """Validate that CBORG_API_KEY is present in the environment."""
    if allow_missing:
        return
    key = env.get("CBORG_API_KEY")
    if not key or not key.strip():
        raise LauncherError(
            "CBORG_API_KEY must be set in process environment. "
            "Use --allow-missing-key only for offline dry-runs and checks."
        )


def _parse_batch_options(batch_args: Sequence[str]) -> dict[str, Any]:
    """Parse ``d4d api batch`` options using Click's option definitions from ``batch_cmd``."""
    import copy
    import click
    from data_sheets_schema.cli.api import batch_cmd

    params: list[click.Parameter] = []
    for param in batch_cmd.params:
        p = copy.copy(param)
        p.required = False
        p.callback = None
        if isinstance(p, click.Option) and p.name in {
            "shared_generation_registration",
            "shared_generation_version",
            "expect_sha256",
            "max_cost_dollars",
        }:
            p.multiple = True
            p.default = ()
            p.type = click.UNPROCESSED
        elif isinstance(p, click.Option) and not p.is_flag:
            p.type = click.UNPROCESSED
        params.append(p)
    params.append(click.Option(["--skip-credential-check"], is_flag=True, default=False))
    parser_cmd = click.Command(
        "batch",
        params=params,
        context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    )
    try:
        ctx = parser_cmd.make_context("batch", list(batch_args), resilient_parsing=False)
    except click.ClickException as exc:
        raise LauncherError(f"Invalid 'd4d api batch' arguments: {exc.format_message()}") from exc
    return ctx.params


def validate_command(
    cmd_args: Sequence[str],
    *,
    dry_run: bool = False,
    expect_sha256: str | None = None,
    worktree_dir: Path | None = None,
) -> None:
    """Reject forbidden subcommands ('d4d api run' per D20), unbudgeted batch runs, and non-allowlisted entry points."""
    import math

    tokens = list(cmd_args)
    if tokens and tokens[0] == "--":
        tokens = tokens[1:]
    if not tokens:
        raise LauncherError("No command specified.")

    first = tokens[0]
    if first not in ALLOWED_TOP_COMMANDS:
        raise LauncherError(
            f"Command entry point {first!r} is not allowed; must be one of {sorted(ALLOWED_TOP_COMMANDS)}."
        )

    if first in ("python", "python3"):
        allowed_cli_subcommands = {"api", "bundle", "download", "runs", "evaluate", "utils"}
        valid_py = (
            len(tokens) >= 4
            and tokens[1] == "-m"
            and tokens[2] == "data_sheets_schema.cli"
            and tokens[3] in allowed_cli_subcommands
        ) or (
            len(tokens) >= 3
            and tokens[1] == "-m"
            and tokens[2] == "data_sheets_schema.api_launcher"
        )
        if not valid_py:
            raise LauncherError(
                "python/python3 entry point requires '-m data_sheets_schema.cli <subcommand>'; "
                "arbitrary scripts or '-c' are not allowed."
            )

    # Extract non-flag arguments
    words = [arg for arg in tokens if not arg.startswith("-")]
    for i in range(len(words) - 1):
        if words[i] == "api" and words[i + 1] == "run":
            raise LauncherError(
                "Subcommand 'd4d api run' is forbidden by D20; use 'd4d api batch' instead."
            )
    # Check normalized string representation
    joined = " ".join(tokens)
    if "api run" in joined.split(" -- ")[0]:
        split_tokens = joined.split()
        for i in range(len(split_tokens) - 1):
            if split_tokens[i] == "api" and split_tokens[i + 1] == "run":
                raise LauncherError(
                    "Subcommand 'd4d api run' is forbidden by D20; use 'd4d api batch' instead."
                )

    # Identify api subcommand and its argument slice if present
    api_subcmd: str | None = None
    api_subcmd_idx: int | None = None
    if first == "api" and len(tokens) >= 2:
        for j in range(1, len(tokens)):
            if not tokens[j].startswith("-"):
                api_subcmd = tokens[j]
                api_subcmd_idx = j
                break
    elif first in ("d4d", "python", "python3"):
        for i in range(len(tokens) - 1):
            if tokens[i] == "api":
                for j in range(i + 1, len(tokens)):
                    if not tokens[j].startswith("-"):
                        api_subcmd = tokens[j]
                        api_subcmd_idx = j
                        break
                break

    if api_subcmd is not None:
        if api_subcmd == "run":
            raise LauncherError(
                "Subcommand 'd4d api run' is forbidden by D20; use 'd4d api batch' instead."
            )
        if api_subcmd not in ALLOWED_API_SUBCOMMANDS:
            raise LauncherError(
                f"API subcommand {api_subcmd!r} is not allowed; must be one of {sorted(ALLOWED_API_SUBCOMMANDS)}."
            )

    batch_params: dict[str, Any] = {}
    if api_subcmd == "batch" and api_subcmd_idx is not None:
        batch_params = _parse_batch_options(tokens[api_subcmd_idx + 1 :])
        is_dry = dry_run or bool(batch_params.get("dry_run"))
    else:
        is_dry = dry_run or ("--dry-run" in tokens)

    if any(arg == "--skip-credential-check" or arg.startswith("--skip-credential-check=") for arg in tokens):
        if not is_dry:
            raise LauncherError(
                "--skip-credential-check is only permitted when --dry-run is active."
            )

    reg_values: tuple[str, ...] = tuple(str(v) for v in batch_params.get("shared_generation_registration", ()))
    ver_values: tuple[str, ...] = tuple(str(v) for v in batch_params.get("shared_generation_version", ()))
    cmd_expect_values: tuple[str, ...] = tuple(str(v) for v in batch_params.get("expect_sha256", ()))
    cost_values: tuple[str, ...] = tuple(str(v) for v in batch_params.get("max_cost_dollars", ()))

    if len(reg_values) > 1:
        raise LauncherError(
            "Duplicate '--shared-generation-registration' options are not allowed."
        )
    if len(ver_values) > 1:
        raise LauncherError(
            "Duplicate '--shared-generation-version' options are not allowed."
        )
    if len(cmd_expect_values) > 1:
        raise LauncherError(
            "Duplicate '--expect-sha256' options are not allowed."
        )
    if len(cost_values) > 1:
        raise LauncherError(
            "Duplicate '--max-cost-dollars' options are not allowed."
        )

    if api_subcmd == "batch" and not is_dry:
        cap_raw: str | None = cost_values[0] if cost_values else None
        if cap_raw is None:
            raise LauncherError(
                "Live 'd4d api batch' launch requires '--max-cost-dollars <positive_amount>' "
                "(checked between runs; single-run mid-call spend is monitored via dollar_readout)."
            )
        try:
            cap_val = float(cap_raw)
        except ValueError as exc:
            raise LauncherError(
                f"--max-cost-dollars value {cap_raw!r} must be a positive finite number."
            ) from exc
        if not math.isfinite(cap_val) or cap_val <= 0:
            raise LauncherError(
                f"--max-cost-dollars value {cap_raw!r} must be positive and finite."
            )

    effective_expect = expect_sha256
    if cmd_expect_values:
        if effective_expect is not None and effective_expect.strip().lower() != cmd_expect_values[0].strip().lower():
            raise LauncherError(
                "Conflicting '--expect-sha256' values between launcher and batch command."
            )
        effective_expect = cmd_expect_values[0]

    has_shared_reg = bool(reg_values) or any(
        v not in ("0", "") for v in ver_values
    )
    if api_subcmd == "batch" and not is_dry and has_shared_reg and effective_expect is None:
        raise LauncherError(
            "Live shared-generation 'd4d api batch' launch requires '--expect-sha256 <sha256>' (D07)."
        )

    if effective_expect is not None:
        normalized_expected = effective_expect.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", normalized_expected):
            raise LauncherError(
                f"--expect-sha256 value {effective_expect!r} must be a 64-character hex SHA-256 digest."
            )
        reg_raw: str | None = reg_values[0] if reg_values else None
        if not reg_raw:
            raise LauncherError(
                "--expect-sha256 requires '--shared-generation-registration <path>' in the command."
            )
        reg_path = Path(reg_raw)
        if not reg_path.is_absolute() and worktree_dir is not None:
            wt_candidate = (Path(worktree_dir).resolve() / reg_path).resolve()
            if wt_candidate.is_file():
                reg_path = wt_candidate
        reg_path = reg_path.resolve()
        if not reg_path.is_file():
            raise LauncherError(
                f"Registration file for --expect-sha256 does not exist: {reg_path}"
            )
        actual_sha = hashlib.sha256(reg_path.read_bytes()).hexdigest().lower()
        if actual_sha != normalized_expected:
            raise LauncherError(
                f"Registration SHA-256 mismatch for {reg_path}: expected {normalized_expected}, got {actual_sha}"
            )


def find_worktree_root(worktree_arg: str | Path | None = None) -> Path:
    """Resolve and validate the worktree directory."""
    if worktree_arg is not None:
        target = Path(worktree_arg).resolve()
    else:
        # Default to current working directory
        target = Path.cwd().resolve()

    schema_dir = target / "src" / "data_sheets_schema"
    if not schema_dir.is_dir():
        raise LauncherError(
            f"Worktree directory {target} does not contain valid src/data_sheets_schema. "
            "Specify a valid path with --worktree <path>."
        )
    return target


def find_venv_and_binaries(
    worktree_dir: Path,
    venv_arg: str | Path | None = None,
) -> tuple[Path, Path, Path]:
    """Locate the virtual environment, python executable, and d4d binary for the worktree.

    Returns:
        (venv_dir, python_bin, d4d_bin)
    """
    resolved_wt = worktree_dir.resolve()
    candidates: list[Path] = []

    if venv_arg is not None:
        candidates.append(Path(venv_arg).resolve())
    else:
        candidates.append(resolved_wt / ".venv")
        candidates.append(resolved_wt / "venv")

        # If sys.prefix has d4d and is under resolved_wt
        current_prefix = Path(sys.prefix).resolve()
        if (current_prefix / "bin" / "d4d").exists():
            candidates.append(current_prefix)

    for venv_path in candidates:
        py_bin = venv_path / "bin" / "python"
        d4d_bin = venv_path / "bin" / "d4d"
        if py_bin.is_file() and os.access(py_bin, os.X_OK):
            if d4d_bin.is_file() and os.access(d4d_bin, os.X_OK):
                return venv_path, py_bin, d4d_bin

    # If python exists but d4d doesn't, or neither found
    searched = ", ".join(str(c) for c in candidates)
    raise LauncherError(
        f"Could not find valid virtual environment with python and d4d binaries in {resolved_wt}. "
        f"Searched: {searched}. Specify --venv <path>."
    )


def run_import_check(
    python_bin: Path,
    worktree_dir: Path,
    env: dict[str, str],
) -> None:
    """Execute the import check in the worktree's venv python to verify strict code isolation."""
    cmd = [str(python_bin), "-c", IMPORT_CHECK_SNIPPET, str(worktree_dir)]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(worktree_dir),
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise LauncherError(f"Failed to execute import check with {python_bin}: {exc}") from exc

    if proc.returncode != 0:
        err_msg = proc.stderr.strip() or proc.stdout.strip()
        raise LauncherError(
            f"Worktree import isolation check failed (exit code {proc.returncode}):\n{err_msg}"
        )

    if "IMPORT_CHECK_OK" not in proc.stdout:
        raise LauncherError(
            f"Worktree import isolation check did not report success:\n{proc.stdout.strip()}"
        )


def validate_log_path(log_path: str | Path | None, worktree_dir: Path) -> Path:
    """Ensure that the log file is specified and is located outside the worktree."""
    if log_path is None:
        raise LauncherError(
            "--launch / --background requires --log <path> to specify an output log destination."
        )

    resolved_log = Path(log_path).resolve()
    resolved_wt = worktree_dir.resolve()

    try:
        resolved_log.relative_to(resolved_wt)
        is_inside = True
    except ValueError:
        is_inside = False

    if is_inside or resolved_log == resolved_wt:
        raise LauncherError(
            f"Log file {resolved_log} must be located outside the worktree ({resolved_wt}) to avoid "
            "polluting run worktrees with output artifacts (#795)."
        )

    return resolved_log


def resolve_execution_command(
    cmd_args: Sequence[str],
    python_bin: Path,
    d4d_bin: Path,
) -> list[str]:
    """Resolve the command tokens into an executable command line."""
    if not cmd_args:
        return []

    tokens = list(cmd_args)
    if tokens and tokens[0] == "--":
        tokens = tokens[1:]

    if not tokens:
        return []

    first = tokens[0]
    if first == "d4d":
        return [str(d4d_bin)] + tokens[1:]
    elif first in ("python", "python3"):
        return [str(python_bin)] + tokens[1:]
    elif first == "api" or first in ("bundle", "download", "runs", "evaluate", "utils"):
        # Convenience: bare subcommand implies d4d
        return [str(d4d_bin)] + tokens
    else:
        return tokens


def launch(
    worktree_arg: str | Path | None = None,
    venv_arg: str | Path | None = None,
    cmd_args: Sequence[str] | None = None,
    check_only: bool = False,
    dry_run: bool = False,
    background: bool = False,
    log_file: str | Path | None = None,
    allow_missing_key: bool = False,
    expect_sha256: str | None = None,
) -> int:
    """Main launcher entry point with validation, import verification, and process launch."""
    if allow_missing_key and not (check_only or dry_run):
        raise LauncherError(
            "--allow-missing-key is only permitted with --check-only or --dry-run."
        )

    worktree_dir = find_worktree_root(worktree_arg)
    venv_dir, python_bin, d4d_bin = find_venv_and_binaries(worktree_dir, venv_arg)

    clean_env = clean_environment(worktree_dir)
    check_cborg_key(clean_env, allow_missing=allow_missing_key)

    # Always verify import isolation
    run_import_check(python_bin, worktree_dir, clean_env)

    if check_only:
        print(
            f"[OK] Worktree import isolation check passed for {worktree_dir} "
            f"using python {python_bin} and d4d {d4d_bin}."
        )
        return 0

    tokens = list(cmd_args or [])
    if tokens and tokens[0] == "--":
        tokens = tokens[1:]

    if not tokens:
        raise LauncherError(
            "No command specified. Provide a command to run (e.g. 'd4d api batch ...') "
            "or use --check-only."
        )

    validate_command(tokens, dry_run=dry_run, expect_sha256=expect_sha256, worktree_dir=worktree_dir)
    final_cmd = resolve_execution_command(tokens, python_bin, d4d_bin)
    if (
        expect_sha256 is not None
        and "batch" in tokens
        and not any(tok == "--expect-sha256" or tok.startswith("--expect-sha256=") for tok in final_cmd)
    ):
        final_cmd = list(final_cmd) + ["--expect-sha256", expect_sha256.strip().lower()]

    if background:
        resolved_log = validate_log_path(log_file, worktree_dir)
        caffeinate_bin = shutil.which("caffeinate")
        if caffeinate_bin:
            launch_cmd = [caffeinate_bin, "-ims"] + final_cmd
        else:
            launch_cmd = final_cmd

        if dry_run:
            print("[DRY-RUN] Worktree launch configuration:")
            print(f"  Mode:        Background detached (nohup / caffeinate)")
            print(f"  Worktree:    {worktree_dir}")
            print(f"  Venv:        {venv_dir}")
            print(f"  Command:     {' '.join(launch_cmd)}")
            print(f"  Log:         {resolved_log}")
            print(f"  PYTHONPATH:  {clean_env.get('PYTHONPATH')}")
            print(f"  Unset keys:  ANTHROPIC_API_KEY, D4D_RECEIPT_FULL_MAX_TOKENS, D4D_PHASE_WALL_CLOCK_SECONDS")
            return 0

        resolved_log.parent.mkdir(parents=True, exist_ok=True)
        with open(resolved_log, "a", encoding="utf-8") as out:
            proc = subprocess.Popen(
                launch_cmd,
                cwd=str(worktree_dir),
                env=clean_env,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        print(f"[LAUNCHED] Background process PID {proc.pid}")
        print(f"  Command: {' '.join(launch_cmd)}")
        print(f"  Log:     {resolved_log}")
        return 0

    # Foreground execution
    if dry_run:
        print("[DRY-RUN] Worktree launch configuration:")
        print(f"  Mode:        Foreground")
        print(f"  Worktree:    {worktree_dir}")
        print(f"  Venv:        {venv_dir}")
        print(f"  Command:     {' '.join(final_cmd)}")
        print(f"  PYTHONPATH:  {clean_env.get('PYTHONPATH')}")
        print(f"  Unset keys:  ANTHROPIC_API_KEY, D4D_RECEIPT_FULL_MAX_TOKENS, D4D_PHASE_WALL_CLOCK_SECONDS")
        return 0

    res = subprocess.run(
        final_cmd,
        cwd=str(worktree_dir),
        env=clean_env,
        stdin=None if _stdin_is_valid() else subprocess.DEVNULL,
    )
    return res.returncode


def build_arg_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for api_launcher."""
    parser = argparse.ArgumentParser(
        description="D4D API Launcher (Step A4b / #4345, #777) - worktree code isolation & execution manager."
    )
    parser.add_argument(
        "--worktree", "-w",
        type=Path,
        default=None,
        help="Path to worktree root containing src/data_sheets_schema. Defaults to current directory.",
    )
    parser.add_argument(
        "--venv",
        type=Path,
        default=None,
        help="Path to virtual environment for the worktree. Defaults to <worktree>/.venv.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Perform worktree and import isolation checks and exit.",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Validate worktree, import isolation, and command without executing.",
    )
    parser.add_argument(
        "--launch", "--background",
        dest="background",
        action="store_true",
        help="Launch command in background detached under caffeinate -ims with nohup logging.",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Destination log file for --launch. Must be located outside the worktree.",
    )
    parser.add_argument(
        "--allow-missing-key",
        action="store_true",
        help="Allow missing CBORG_API_KEY (for offline tests and gates).",
    )
    parser.add_argument(
        "--expect-sha256",
        default=None,
        help="Require --shared-generation-registration in the command and verify its SHA-256 digest before launch.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run in worktree (e.g. 'd4d api batch ...' or 'api prompts check --strict').",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_arg_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        return launch(
            worktree_arg=args.worktree,
            venv_arg=args.venv,
            cmd_args=args.command,
            check_only=args.check_only,
            dry_run=args.dry_run,
            background=args.background,
            log_file=args.log,
            allow_missing_key=args.allow_missing_key,
            expect_sha256=args.expect_sha256,
        )
    except LauncherError as err:
        sys.stderr.write(f"api_launcher: error: {err}\n")
        return 1
