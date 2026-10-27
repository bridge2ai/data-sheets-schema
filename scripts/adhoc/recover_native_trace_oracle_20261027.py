#!/usr/bin/env python3
# Purpose: preserve the exact #4537 literal Trace oracle and prove its source history.
# Inputs: local 0125/a8/a462 Git objects and current recovered test/production bytes.
# Outputs: inert pinned test fixture and provenance JSON/diff under notes.
# Refs #4537, #4354; 2026-10-27. Offline only; no production or historical run edits.
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MODULE = 'src/data_sheets_schema/native_shared_observations.py'
TEST = 'tests/test_native_trace_single_decode.py'
BASE = '0125eebbc214d0907c3b69d23758cd9441911a78'
SINGLE = 'a8c11973da120cc0f792eef2d574dab7d910b09d'
CACHED = 'a462dcfecb55503f6f8227e4908b56133b2c7572'
RECOVERED = '0d5bddbc03b02cfa3efdea312c10aca002f6d85c'
PINS = {
    BASE: '3bc93c2d1720d4e41ee83e7be7d8758a56836062c316f75ecc4b505e80b6d3ab',
    SINGLE: '4dc91259ecb079e8efe3067b0eeb01e584b575bdda813fcc6e7494bf39bcbba4',
    CACHED: '41459563575a0c9e0c396c488cb25afbd0f8421896b904ecfc290972ca1b3ae2',
}
TEST_PIN = '8bfdc119517b4799419f318acd93148723b59633f7ac62576a139040cf83f0e7'
FIXTURE = 'tests/fixtures/native_trace/native_shared_observations_0125eebbc.py.txt'
OUTPUT = 'notes/native_trace_oracle_20261027'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT, env=env)


def main():
    sources = {commit: git('show', commit + ':' + MODULE) for commit in PINS}
    for commit, raw in sources.items():
        if sha(raw) != PINS[commit]:
            raise ValueError('historical module differs: ' + commit)
    old_test = git('show', SINGLE + ':' + TEST)
    if sha(old_test) != TEST_PIN or git('show', RECOVERED + ':' + TEST) != old_test:
        raise ValueError('recovered test is not the exact single-decode test')
    if git('show', RECOVERED + ':' + MODULE) != sources[CACHED] or (ROOT / MODULE).read_bytes() != sources[CACHED]:
        raise ValueError('recovered/current module differs from exact later cache source')
    constants = {}
    for node in ast.parse(old_test).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in {'CONSTRUCTOR_REUSE', 'HELPER_SPLIT'}:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
    substitutions = (
        (constants['CONSTRUCTOR_REUSE'], '        initialized,*_=initialization(transcript,control,policy=policy,runtime=runtime)\n'),
        ('        for number,raw,value in native:\n', '        for number,raw,value in rows(transcript):\n'),
        ('        for number,raw,value in parent:\n', '        for number,raw,value in rows(control):\n'),
        (constants['HELPER_SPLIT'], ''),
    )
    reconstructed = {}
    for commit in (SINGLE, CACHED):
        text = sources[commit].decode()
        for candidate, original in substitutions:
            if text.count(candidate) != 1:
                raise ValueError('historical reversal is ambiguous: ' + commit)
            text = text.replace(candidate, original)
        reconstructed[commit] = text.encode()
    if reconstructed[SINGLE] != sources[BASE]:
        raise ValueError('original single-decode reversal no longer reproduces literal0125')
    fixture = ROOT / FIXTURE
    output = ROOT / OUTPUT
    if fixture.exists() or output.exists():
        raise ValueError('fresh oracle fixture and evidence directory required')
    fixture.parent.mkdir(parents=True, exist_ok=True)
    with fixture.open('xb') as stream:
        stream.write(sources[BASE])
    output.mkdir()
    delta = ''.join(difflib.unified_diff(sources[SINGLE].decode().splitlines(keepends=True),
                                       sources[CACHED].decode().splitlines(keepends=True),
                                       fromfile=SINGLE + '/' + MODULE, tofile=CACHED + '/' + MODULE)).encode()
    (output / 'later-cache-change.diff').write_bytes(delta)
    report = {
        'scope': 'Exact historical module oracle; not a reconstructed whole historical runtime.',
        'helper': {'path': str(Path(__file__)), 'sha256': sha(Path(__file__).read_bytes())},
        'source_head_at_recovery': git('rev-parse', 'HEAD').decode().strip(),
        'historical_modules': [{'commit': commit, 'path': MODULE, 'bytes': len(raw), 'sha256': sha(raw),
                               'git_blob': git('rev-parse', commit + ':' + MODULE).decode().strip()}
                              for commit, raw in sources.items()],
        'historical_test': {'commit': SINGLE, 'recovery_commit': RECOVERED,
                            'path': TEST, 'sha256': TEST_PIN, 'recovered_bytes_equal_original': True},
        'original_a8_reversal_equals_0125_bytes': True,
        'later_cache_source_reversal_sha256': sha(reconstructed[CACHED]),
        'later_cache_source_reversal_is_original_oracle': reconstructed[CACHED] == sources[BASE],
        'recovered_and_current_module_equal_later_cache_commit': True,
        'fixture': {'path': FIXTURE, 'bytes': len(sources[BASE]), 'sha256': sha(sources[BASE]),
                    'bytes_equal_original_git_blob': fixture.read_bytes() == sources[BASE]},
        'delta': {'path': 'later-cache-change.diff', 'bytes': len(delta), 'sha256': sha(delta)},
        'pytest_dependency_scope': 'Canonical module name and current production dependencies, as in original test; no Git needed at test time.',
    }
    (output / 'recovery.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'fixture': str(fixture), 'report': str(output / 'recovery.json'),
                      'literal_sha256': sha(sources[BASE]), 'later_reversal_sha256': sha(reconstructed[CACHED])}))


if __name__ == '__main__':
    main()
