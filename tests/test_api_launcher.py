"""Tests for D4D API Launcher (Step A4b / #4345, #777).

Verifies worktree code isolation, environment variable stripping, CBORG_API_KEY enforcement,
D20 subcommand refusal ('d4d api run'), import isolation checks, dry-run, and launch modes.
"""

from __future__ import annotations

import os
import site
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from data_sheets_schema.api_launcher import (
    LauncherError,
    check_cborg_key,
    clean_environment,
    find_venv_and_binaries,
    find_worktree_root,
    launch,
    main,
    resolve_execution_command,
    run_import_check,
    validate_command,
    validate_log_path,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
_CACHED_ISOLATED_VENV: Path | None = None


def _venv_is_isolated_for_repo(venv_dir: Path, repo_root: Path) -> bool:
    """Return True if venv_dir exists and has no .pth pointing outside repo_root/src."""
    if not (venv_dir / "bin" / "python").is_file() or not (venv_dir / "bin" / "d4d").is_file():
        return False
    expected_src = (repo_root / "src").resolve()
    for pth in venv_dir.glob("lib/python*/site-packages/*.pth"):
        for line in pth.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("import "):
                continue
            candidate = Path(stripped)
            if candidate.is_absolute() and candidate.name == "src" and candidate.resolve() != expected_src:
                return False
    return True


def _get_isolated_venv() -> Path:
    """Return REPO_ROOT/.venv if isolated for REPO_ROOT, or build a lightweight isolated venv."""
    global _CACHED_ISOLATED_VENV
    repo_venv = REPO_ROOT / ".venv"
    if _venv_is_isolated_for_repo(repo_venv, REPO_ROOT):
        return repo_venv
    if _CACHED_ISOLATED_VENV is not None and _CACHED_ISOLATED_VENV.is_dir():
        return _CACHED_ISOLATED_VENV

    venv_dir = Path(tempfile.mkdtemp(prefix="d4d_isolated_venv_"))
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(venv_dir)],
        check=True,
        capture_output=True,
    )
    site_Result = list(venv_dir.glob("lib/python*/site-packages"))
    assert site_Result, f"No site-packages created in {venv_dir}"
    venv_site = site_Result[0]

    shared_sites = [p for p in site.getsitepackages() if Path(p).is_dir()]
    deps_lines = [f"import sys; sys.path.append({p!r})" for p in shared_sites]
    (venv_site / "deps.pth").write_text("\n".join(deps_lines) + "\n", encoding="utf-8")
    (venv_site / "data_sheets_schema.pth").write_text(f"{REPO_ROOT / 'src'}\n", encoding="utf-8")

    d4d_bin = venv_dir / "bin" / "d4d"
    d4d_bin.write_text(
        f"#!{venv_dir / 'bin' / 'python'}\n"
        "from data_sheets_schema.cli import main\n"
        "if __name__ == '__main__':\n"
        "    main()\n",
        encoding="utf-8",
    )
    d4d_bin.chmod(d4d_bin.stat().st_mode | stat.S_IEXEC)
    _CACHED_ISOLATED_VENV = venv_dir
    return venv_dir


def _default_venv_arg() -> list[str]:
    venv_dir = _get_isolated_venv()
    if venv_dir != REPO_ROOT / ".venv":
        return ["--venv", str(venv_dir)]
    return []


class TestLauncherEnvironment:
    """Tests for environment sanitization and key validation."""

    def test_clean_environment_strips_hazardous_vars(self, tmp_path: Path):
        dirty_env = {
            "ANTHROPIC_API_KEY": "sk-ant-secret",
            "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
            "D4D_RECEIPT_FULL_MAX_TOKENS": "64000",
            "D4D_PHASE_WALL_CLOCK_SECONDS": "1800",
            "D4D_CUSTOM_OVERRIDE": "true",
            "CBORG_API_KEY": "valid-cborg-key",
            "USER": "tester",
        }
        cleaned = clean_environment(tmp_path, dirty_env)

        assert "ANTHROPIC_API_KEY" not in cleaned
        assert "ANTHROPIC_BASE_URL" not in cleaned
        assert "D4D_RECEIPT_FULL_MAX_TOKENS" not in cleaned
        assert "D4D_PHASE_WALL_CLOCK_SECONDS" not in cleaned
        assert "D4D_CUSTOM_OVERRIDE" not in cleaned
        assert cleaned["PYTHONUNBUFFERED"] == "1"
        assert cleaned["PYTHONPATH"] == str((tmp_path / "src").resolve())
        assert cleaned["CBORG_API_KEY"] == "valid-cborg-key"
        assert cleaned["USER"] == "tester"

    def test_check_cborg_key_missing_raises(self):
        with pytest.raises(LauncherError, match="CBORG_API_KEY must be set"):
            check_cborg_key({})

        with pytest.raises(LauncherError, match="CBORG_API_KEY must be set"):
            check_cborg_key({"CBORG_API_KEY": "   "})

    def test_check_cborg_key_present(self):
        check_cborg_key({"CBORG_API_KEY": "some-key"})

    def test_check_cborg_key_allow_missing(self):
        check_cborg_key({}, allow_missing=True)

    def test_allow_missing_key_rejected_for_real_launch(self):
        with pytest.raises(LauncherError, match="only permitted with --check-only or --dry-run"):
            launch(
                worktree_arg=REPO_ROOT,
                cmd_args=["d4d", "api", "batch", "--manifest", "data/preprocessed/source_manifest.yaml"],
                allow_missing_key=True,
                check_only=False,
                dry_run=False,
            )


class TestCommandValidation:
    """Tests for rejecting forbidden subcommands (D20 requirement)."""

    def test_reject_d4d_api_run(self):
        with pytest.raises(LauncherError, match="forbidden by D20"):
            validate_command(["d4d", "api", "run", "--project", "CHORUS"])

    def test_reject_bare_api_run(self):
        with pytest.raises(LauncherError, match="forbidden by D20"):
            validate_command(["api", "run", "--project", "CHORUS"])

    def test_reject_interleaved_flags_api_run(self):
        with pytest.raises(LauncherError, match="forbidden by D20"):
            validate_command(["d4d", "--manifest", "foo.yaml", "api", "run", "--project", "CHORUS"])

    def test_reject_unallowed_top_command(self):
        with pytest.raises(LauncherError, match="is not allowed"):
            validate_command(["bash", "-c", "echo hi"])

    def test_accept_api_batch(self):
        validate_command([
            "d4d", "api", "batch",
            "--manifest", "data/preprocessed/source_manifest.yaml",
            "--max-cost-dollars", "15.0",
        ])

    def test_reject_api_batch_without_max_cost_dollars(self):
        with pytest.raises(LauncherError, match="requires '--max-cost-dollars"):
            validate_command(["d4d", "api", "batch", "--manifest", "data/preprocessed/source_manifest.yaml"])

    def test_reject_python_cli_api_batch_without_max_cost_dollars(self):
        with pytest.raises(LauncherError, match="requires '--max-cost-dollars"):
            validate_command([
                "python", "-m", "data_sheets_schema.cli",
                "api", "batch", "--manifest", "data/preprocessed/source_manifest.yaml",
            ])

    def test_accept_api_batch_dry_run_without_max_cost_dollars(self):
        validate_command(
            ["d4d", "api", "batch", "--manifest", "data/preprocessed/source_manifest.yaml"],
            dry_run=True,
        )
        validate_command(
            ["d4d", "api", "batch", "--dry-run", "--manifest", "data/preprocessed/source_manifest.yaml"],
            dry_run=False,
        )

    def test_reject_skip_credential_check_without_dry_run(self):
        with pytest.raises(LauncherError, match="--skip-credential-check is only permitted"):
            validate_command([
                "d4d", "api", "batch",
                "--skip-credential-check",
                "--max-cost-dollars", "15.0",
            ])
        validate_command(
            ["d4d", "api", "batch", "--skip-credential-check", "--dry-run"],
            dry_run=False,
        )

    def test_reject_unknown_api_subcommand(self):
        with pytest.raises(LauncherError, match="API subcommand 'unknown-sub' is not allowed"):
            validate_command(["d4d", "api", "unknown-sub"])

    def test_accept_other_gates(self):
        validate_command(["d4d", "api", "prompts", "check", "--strict"])
        validate_command(["d4d", "bundle", "chunk", "--check", "--strict"])
        validate_command(["d4d", "download", "audit-bundles", "--strict"])
        validate_command(["d4d", "download", "scope", "--check", "--strict"])
        validate_command(["d4d", "runs", "check", "--strict"])


class TestWorktreeAndVenvDiscovery:
    """Tests for worktree and virtual environment discovery."""

    def test_find_worktree_root_valid(self):
        wt = find_worktree_root(REPO_ROOT)
        assert wt == REPO_ROOT.resolve()

    def test_find_worktree_root_invalid(self, tmp_path: Path):
        with pytest.raises(LauncherError, match="does not contain valid src/data_sheets_schema"):
            find_worktree_root(tmp_path)

    def test_find_venv_and_binaries_in_repo(self):
        venv_dir, py_bin, d4d_bin = find_venv_and_binaries(REPO_ROOT, venv_arg=_get_isolated_venv())
        assert py_bin.is_file()
        assert d4d_bin.is_file()
        assert os.access(py_bin, os.X_OK)
        assert os.access(d4d_bin, os.X_OK)

    def test_find_venv_and_binaries_custom_venv(self, tmp_path: Path):
        wt = tmp_path / "wt"
        wt.mkdir()
        (wt / "src" / "data_sheets_schema").mkdir(parents=True)

        fake_venv = tmp_path / "custom_venv"
        bin_dir = fake_venv / "bin"
        bin_dir.mkdir(parents=True)
        py = bin_dir / "python"
        d4d = bin_dir / "d4d"
        py.write_text("#!/bin/sh\nexit 0\n")
        d4d.write_text("#!/bin/sh\nexit 0\n")
        py.chmod(py.stat().st_mode | stat.S_IEXEC)
        d4d.chmod(d4d.stat().st_mode | stat.S_IEXEC)

        resolved_venv, resolved_py, resolved_d4d = find_venv_and_binaries(wt, venv_arg=fake_venv)
        assert resolved_venv == fake_venv.resolve()
        assert resolved_py == py.resolve()
        assert resolved_d4d == d4d.resolve()


class TestLogPathValidation:
    """Tests for validating log file destination."""

    def test_log_inside_worktree_rejected(self, tmp_path: Path):
        wt = tmp_path / "worktree"
        wt.mkdir()
        internal_log = wt / "logs" / "run.log"
        with pytest.raises(LauncherError, match="must be located outside the worktree"):
            validate_log_path(internal_log, wt)

    def test_log_outside_worktree_accepted(self, tmp_path: Path):
        wt = tmp_path / "worktree"
        wt.mkdir()
        external_log = tmp_path / "external_logs" / "run.log"
        resolved = validate_log_path(external_log, wt)
        assert resolved == external_log.resolve()

    def test_log_none_rejected(self, tmp_path: Path):
        with pytest.raises(LauncherError, match="requires --log <path>"):
            validate_log_path(None, tmp_path)


class TestCommandResolution:
    """Tests for command string resolution."""

    def test_resolve_d4d_binary(self, tmp_path: Path):
        py = tmp_path / "python"
        d4d = tmp_path / "d4d"
        resolved = resolve_execution_command(["d4d", "api", "batch", "--foo"], py, d4d)
        assert resolved == [str(d4d), "api", "batch", "--foo"]

    def test_resolve_python_binary(self, tmp_path: Path):
        py = tmp_path / "python"
        d4d = tmp_path / "d4d"
        resolved = resolve_execution_command(["python", "script.py"], py, d4d)
        assert resolved == [str(py), "script.py"]

    def test_resolve_bare_subcommand(self, tmp_path: Path):
        py = tmp_path / "python"
        d4d = tmp_path / "d4d"
        resolved = resolve_execution_command(["api", "prompts", "check"], py, d4d)
        assert resolved == [str(d4d), "api", "prompts", "check"]


class TestImportIsolationCheck:
    """Tests for verifying worktree import isolation."""

    def test_import_check_passes_on_current_repository(self):
        venv_dir, py_bin, d4d_bin = find_venv_and_binaries(REPO_ROOT, venv_arg=_get_isolated_venv())
        clean_env = clean_environment(REPO_ROOT)
        clean_env["CBORG_API_KEY"] = "dummy"
        # Should execute and pass without error
        run_import_check(py_bin, REPO_ROOT, clean_env)

    def test_import_check_fails_if_init_py_present(self, tmp_path: Path):
        # Create a mock worktree that has an __init__.py in data_sheets_schema
        wt = tmp_path / "wt_with_init"
        schema_dir = wt / "src" / "data_sheets_schema"
        schema_dir.mkdir(parents=True)
        (schema_dir / "__init__.py").write_text("# non-namespace init\n")

        # Copy the submodules so imports don't fail immediately on missing module
        for mod in ["api_runner", "shared_generation", "typed_audit_runtime", "receipt_completion"]:
            (schema_dir / f"{mod}.py").write_text("# stub\n")
        cli_dir = schema_dir / "cli"
        cli_dir.mkdir()
        (cli_dir / "api.py").write_text("# stub\n")

        _, py_bin, _ = find_venv_and_binaries(REPO_ROOT, venv_arg=_get_isolated_venv())
        clean_env = clean_environment(wt)
        with pytest.raises(LauncherError, match="must be None"):
            run_import_check(py_bin, wt, clean_env)

    def test_import_check_fails_if_path_points_to_external_checkout(self, tmp_path: Path):
        # Create mock worktree
        wt = tmp_path / "wt"
        schema_dir = wt / "src" / "data_sheets_schema"
        schema_dir.mkdir(parents=True)

        for mod in ["api_runner", "shared_generation", "typed_audit_runtime", "receipt_completion"]:
            (schema_dir / f"{mod}.py").write_text("# stub\n")
        cli_dir = schema_dir / "cli"
        cli_dir.mkdir()
        (cli_dir / "api.py").write_text("# stub\n")

        _, py_bin, _ = find_venv_and_binaries(REPO_ROOT, venv_arg=_get_isolated_venv())
        # Construct PYTHONPATH pointing to both external REPO_ROOT/src and wt/src
        clean_env = clean_environment(wt)
        clean_env["PYTHONPATH"] = f"{REPO_ROOT / 'src'}:{wt / 'src'}"

        with pytest.raises(LauncherError, match="does not resolve to expected"):
            run_import_check(py_bin, wt, clean_env)


class TestLauncherCLI:
    """Integration tests for CLI flags and execution modes."""

    def test_check_only_mode(self):
        ret = main(["--check-only", "--allow-missing-key", "--worktree", str(REPO_ROOT)] + _default_venv_arg())
        assert ret == 0

    def test_dry_run_batch_command(self, capsys):
        ret = main([
            "--dry-run",
            "--allow-missing-key",
            "--worktree", str(REPO_ROOT),
            *_default_venv_arg(),
            "d4d", "api", "batch", "--manifest", "data/preprocessed/source_manifest.yaml"
        ])
        assert ret == 0
        captured = capsys.readouterr()
        assert "[DRY-RUN] Worktree launch configuration:" in captured.out
        assert "d4d api batch" in captured.out or "bin/d4d api batch" in captured.out
        assert "Unset keys:  ANTHROPIC_API_KEY" in captured.out

    def test_dry_run_forbidden_api_run(self, capsys):
        ret = main([
            "--dry-run",
            "--allow-missing-key",
            "--worktree", str(REPO_ROOT),
            *_default_venv_arg(),
            "d4d", "api", "run", "--project", "CHORUS"
        ])
        assert ret == 1
        captured = capsys.readouterr()
        assert "forbidden by D20" in captured.err

    def test_dry_run_background_launch(self, tmp_path: Path, capsys):
        external_log = tmp_path / "logs" / "run.log"
        ret = main([
            "--dry-run",
            "--launch",
            "--log", str(external_log),
            "--allow-missing-key",
            "--worktree", str(REPO_ROOT),
            *_default_venv_arg(),
            "d4d", "api", "batch", "--manifest", "data/preprocessed/source_manifest.yaml"
        ])
        assert ret == 0
        captured = capsys.readouterr()
        assert "Background detached" in captured.out
        assert str(external_log.resolve()) in captured.out

    def test_background_launch_redirects_stdin_and_survives_closed_fd0(self, tmp_path: Path, monkeypatch):
        """Regression test (#5115, R4 F8): --launch must pass stdin=DEVNULL so detached children do not inherit fd 0 as the write-only log file."""
        external_log = tmp_path / "logs" / "detached_run.log"
        script = REPO_ROOT / "scripts" / "api_launcher.py"

        # 1. Build a custom venv whose bin/d4d reads from sys.stdin before invoking CLI main().
        # Without stdin=subprocess.DEVNULL on Popen, fd 0 after os.close(0) is the write-only
        # external_log opened by launch(), so sys.stdin.read() raises UnsupportedOperation.
        base_venv = _get_isolated_venv()
        custom_venv = tmp_path / "stdin_check_venv"
        (custom_venv / "bin").mkdir(parents=True)
        (custom_venv / "bin" / "python").symlink_to(base_venv / "bin" / "python")
        for lib_dir in base_venv.glob("lib"):
            (custom_venv / "lib").symlink_to(lib_dir)
        d4d_bin = custom_venv / "bin" / "d4d"
        d4d_bin.write_text(
            f"#!{custom_venv / 'bin' / 'python'}\n"
            "import sys\n"
            "stdin_bytes = sys.stdin.read()\n"
            "print(f'DETACHED_STDIN_EOF={stdin_bytes == \"\"}', flush=True)\n"
            "from data_sheets_schema.cli import cli\n"
            "if __name__ == '__main__':\n"
            "    cli()\n",
            encoding="utf-8",
        )
        d4d_bin.chmod(d4d_bin.stat().st_mode | stat.S_IEXEC)

        wrapper_code = (
            "import os, subprocess, sys\n"
            "os.close(0)\n"
            "sys.argv = [sys.argv[1]] + sys.argv[2:]\n"
            "import runpy\n"
            "runpy.run_path(sys.argv[0], run_name='__main__')\n"
        )
        env = dict(os.environ)
        env["CBORG_API_KEY"] = "dummy-test-key"
        env["PYSTOW_HOME"] = str(tmp_path / "pystow")
        res = subprocess.run(
            [
                sys.executable,
                "-c",
                wrapper_code,
                str(script),
                "--worktree",
                str(REPO_ROOT),
                "--venv",
                str(custom_venv),
                "--launch",
                "--log",
                str(external_log),
                "--",
                "d4d",
                "api",
                "prompts",
                "check",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert res.returncode == 0, f"Launcher failed: {res.stderr}\n{res.stdout}"
        assert "[LAUNCHED] Background process PID" in res.stdout

        deadline = time.monotonic() + 10.0
        log_text = ""
        while time.monotonic() < deadline:
            if external_log.is_file():
                log_text = external_log.read_text(encoding="utf-8", errors="replace")
                if "0 not at their pin" in log_text or "UnsupportedOperation" in log_text or "Fatal Python error" in log_text:
                    break
            time.sleep(0.1)

        assert "Fatal Python error" not in log_text
        assert "Bad file descriptor" not in log_text
        assert "UnsupportedOperation" not in log_text
        assert "DETACHED_STDIN_EOF=True" in log_text
        assert "0 not at their pin" in log_text

        # 2. Direct in-process check that Popen receives stdin=subprocess.DEVNULL
        captured_popen: dict[str, object] = {}

        class _DummyProc:
            pid = 42424

        def _fake_popen(cmd, **kwargs):
            captured_popen["cmd"] = cmd
            captured_popen.update(kwargs)
            return _DummyProc()

        monkeypatch.setattr(subprocess, "Popen", _fake_popen)
        monkeypatch.setattr("data_sheets_schema.api_launcher.run_import_check", lambda *a, **k: None)
        monkeypatch.setenv("CBORG_API_KEY", "dummy-test-key")
        rc = launch(
            worktree_arg=REPO_ROOT,
            venv_arg=base_venv,
            cmd_args=["d4d", "api", "prompts", "check"],
            background=True,
            log_file=tmp_path / "logs" / "unit_popen.log",
        )
        assert rc == 0
        assert captured_popen.get("stdin") == subprocess.DEVNULL

    def test_validate_command_restricts_python_entrypoint(self, tmp_path: Path):
        with pytest.raises(LauncherError, match="requires '-m data_sheets_schema.cli <subcommand>'"):
            validate_command(["python", "-c", "print(1)"])
        with pytest.raises(LauncherError, match="requires '-m data_sheets_schema.cli <subcommand>'"):
            validate_command(["python", "some_script.py"])
        validate_command(["python", "-m", "data_sheets_schema.cli", "api", "prompts", "check"])

    def test_expect_sha256_verifies_shared_generation_registration(self, tmp_path: Path):
        import hashlib
        reg_file = tmp_path / "reg.json"
        reg_file.write_text('{"format": "shared_generation_registration_v1"}\n', encoding="utf-8")
        digest = hashlib.sha256(reg_file.read_bytes()).hexdigest()

        cmd = [
            "python",
            "-m",
            "data_sheets_schema.cli",
            "api",
            "batch",
            "--max-cost-dollars",
            "10.0",
            f"--shared-generation-registration={reg_file}",
        ]
        validate_command(cmd, expect_sha256=digest)

        # Live shared-generation batch launch without --expect-sha256 is refused (R4 F3 / D07)
        with pytest.raises(LauncherError, match="requires '--expect-sha256 <sha256>'"):
            validate_command(cmd)

        # Dry-run without --expect-sha256 is allowed
        validate_command(cmd + ["--dry-run"])

        # Duplicate --shared-generation-registration is refused (R4 F3)
        decoy = tmp_path / "decoy.json"
        decoy.write_text('{"format": "shared_generation_registration_v1", "decoy": 1}\n', encoding="utf-8")
        decoy_sha = hashlib.sha256(decoy.read_bytes()).hexdigest()
        with pytest.raises(LauncherError, match="Duplicate '--shared-generation-registration'"):
            validate_command(
                cmd + ["--shared-generation-registration", str(decoy)],
                expect_sha256=decoy_sha,
            )

        with pytest.raises(LauncherError, match="Registration SHA-256 mismatch"):
            validate_command(cmd, expect_sha256="0" * 64)

        with pytest.raises(LauncherError, match="requires '--shared-generation-registration <path>'"):
            validate_command(
                ["python", "-m", "data_sheets_schema.cli", "api", "prompts", "check"],
                expect_sha256=digest,
            )

    def test_canary_baseline_dry_run_value_does_not_enable_dry_run(self):
        """R4 F15: '--canary-baseline --dry-run' passes '--dry-run' as option value, not flag."""
        with pytest.raises(LauncherError, match="requires '--max-cost-dollars"):
            validate_command([
                "d4d", "api", "batch",
                "--projects", "CHORUS",
                "--label-prefix", "2026-10-25_test",
                "--canary-baseline", "--dry-run",
            ])

    def test_launch_forwards_expect_sha256_to_batch_command(self, tmp_path: Path, capsys):
        """R4 F3: launch forwards --expect-sha256 to d4d api batch."""
        import hashlib
        reg_file = tmp_path / "reg.json"
        reg_file.write_text('{"format": "shared_generation_registration_v1"}\n', encoding="utf-8")
        digest = hashlib.sha256(reg_file.read_bytes()).hexdigest()
        ret = main([
            "--dry-run",
            "--allow-missing-key",
            "--worktree", str(REPO_ROOT),
            *_default_venv_arg(),
            "--expect-sha256", digest,
            "--",
            "d4d", "api", "batch",
            "--max-cost-dollars", "15.0",
            "--shared-generation-registration", str(reg_file),
        ])
        assert ret == 0
        out = capsys.readouterr().out
        assert f"--expect-sha256 {digest}" in out

    def test_scripts_api_launcher_executable(self):
        script = REPO_ROOT / "scripts" / "api_launcher.py"
        res = subprocess.run(
            [sys.executable, str(script), "--check-only", "--allow-missing-key", "--worktree", str(REPO_ROOT), *_default_venv_arg()],
            capture_output=True,
            text=True,
            check=False,
        )
        assert res.returncode == 0
        assert "[OK] Worktree import isolation check passed" in res.stdout
