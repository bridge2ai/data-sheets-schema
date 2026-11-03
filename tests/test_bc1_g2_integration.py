"""Offline G1 x BC1/G2 integration witnesses, 2026-11-03."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import build_api_registrations as builder


def test_relative_manifest_cli_from_outside_checkout(tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    out = tmp_path / 'registrations'
    env = dict(os.environ)
    env.pop('D4D_MANIFEST', None)
    result = subprocess.run([sys.executable, str(Path(builder.__file__).resolve()),
        '-p', 'CHORUS', '-l', 'integration-witness', '--partition', 'chorus',
        '--source-manifest', 'data/preprocessed/source_manifest.yaml',
        '--output-dir', str(out), '--dry-run'], cwd=outside, env=env,
        text=True, capture_output=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'CHORUS' in result.stdout
    assert not out.exists() or not list(out.iterdir())


def test_relative_manifest_coverage_uses_code_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manifest = Path('data/preprocessed/source_manifest.yaml')
    limits = builder.resolve_audit_limits('CHORUS', 'chorus', source_manifest=manifest)
    assert builder.profile_sized('chorus', limits, source_manifest=manifest)


def test_unknown_partition_names_manifest():
    manifest = builder.ROOT / 'data/preprocessed/source_manifest.yaml'
    with pytest.raises(ValueError) as error:
        builder.resolve_audit_limits('CHORUS', 'undeclared-partition', source_manifest=manifest)
    assert str(manifest) in str(error.value)
