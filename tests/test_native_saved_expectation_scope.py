"""Real saved CLI and verified origin regression; offline fixtures, PR 5968."""
import json
import os
from pathlib import Path
import subprocess
import shutil

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]


def run_packet(tmp_path, project):
    if shutil.which('sandbox-exec') is None:
        pytest.skip('offline saved-step regression requires macOS sandbox-exec')
    # This allowlist excludes the Claude binary and blocks network access even
    # for subprocesses. The inert fingerprint placeholder must never execute.
    allowed = {str(Path(sys.executable).resolve()), '/usr/bin/git',
        '/Library/Developer/CommandLineTools/usr/bin/git',
        '/Applications/Xcode.app/Contents/Developer/usr/bin/git'}
    profile = tmp_path / 'offline.sb'
    profile.write_text('(version 1)\n(allow default)\n(deny network*)\n'
        + '(deny process-exec (require-all '
        + ' '.join('(require-not (literal ' + json.dumps(p) + '))' for p in sorted(allowed))
        + '))\n')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
        GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='', GIT_CONFIG_GLOBAL='/dev/null',
        GIT_CONFIG_SYSTEM='/dev/null', GIT_OPTIONAL_LOCKS='0')
    for name in tuple(env):
        if name.endswith('_API_KEY') or name in ('PYTHONPATH', 'PYTHONPYCACHEPREFIX',
                'CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_AUTH_TOKEN'):
            env.pop(name, None)
    command = ['/usr/bin/sandbox-exec', '-f', str(profile), sys.executable, '-P', '-B',
        str(ROOT / 'scripts/adhoc/expectation_scope_regression_20261116.py'),
        '--project', project, '--scratch', str(tmp_path / 'packet-work')]
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=2400)
    (tmp_path / 'command.json').write_text(json.dumps(command))
    (tmp_path / 'stdout.log').write_bytes(result.stdout)
    (tmp_path / 'stderr.log').write_bytes(result.stderr)
    assert result.returncode == 0, result.stdout.decode() + result.stderr.decode()
    evidence = json.loads((tmp_path / 'packet-work/packets' / project / 'regression-result.json').read_bytes())
    assert evidence['verified_consumer_matches_cli']
    assert 'registered inputs have no construction origin' in evidence['foreign_origin_refusal']
    assert not evidence['native_execution']


def test_chorus_saved_expectation_cli_and_foreign_origin(tmp_path):
    run_packet(tmp_path, 'CHORUS')


def test_ai_readi_saved_expectation_cli_and_foreign_origin(tmp_path):
    run_packet(tmp_path, 'AI_READI')
