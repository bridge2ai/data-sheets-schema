#!/usr/bin/env python3
"""Sanitize the spent CLI observation into offline model-label fixtures.

Inputs: explicit read-only observation leaf with stdout, request and invocation.
Outputs: tests/fixtures/native_cli_2_1_325 and source/output hash provenance.
Serves the 2026-11-19 native CLI model-label amendment. No binary is invoked.
Private text, paths, identifiers and account metadata are replaced; model labels,
limits, ordering and the known scripted-provider dummy key are retained.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'tests/fixtures/native_cli_2_1_325'
DUMMY_KEY = 'd4d-local-permission-probe-token'
SESSION = '00000000-0000-4000-8000-000000000325'
KEPT_TEXT_KEYS = {'type', 'subtype', 'role', 'model', 'canonicalModel', 'provider',
    'apiKeySource', 'claude_code_version', 'permissionMode', 'stop_reason',
    'terminal_reason', 'costBasis', 'effort'}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sanitize(value, key=''):
    if isinstance(value, dict):
        return {name: sanitize(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item, key) for item in value]
    if isinstance(value, str):
        if key in KEPT_TEXT_KEYS:
            return value
        if key == 'session_id':
            return SESSION
        if key == 'uuid':
            return '00000000-0000-4000-8000-000000000001'
        if key == 'timestamp':
            return 'FIXTURE_RELATIVE_UTC'
        if key in ('cwd', 'original_cwd'):
            return '/fixture/cwd'
        if value.startswith('/'):
            return '/fixture/sanitized-path'
        if key in ('text', 'content', 'result'):
            return 'Sanitized offline fixture text.'
        return 'sanitized'
    return value


def invocation_fixture(original):
    value = deepcopy(original)
    argv = value['argv']
    assert argv[argv.index('--model') + 1] == 'claude-opus-5[1m]'
    assert argv[-1] == 'Reply with OK.'
    argv[0] = '/fixture/claude'
    # The source invocation contains only fixed isolation flags, JSON empty
    # configuration, literal scalar choices and this public scripted prompt.
    for index, word in enumerate(argv[1:], 1):
        if word.startswith('/'):
            argv[index] = '/fixture/sanitized-path'
        else:
            assert word.startswith('--') or word in {
                '', 'false', 'stream-json', 'dontAsk', '{"mcpServers":{}}',
                '{"disableAllHooks":true}', 'claude-opus-5[1m]', 'high', '90', 'Reply with OK.'}
    env = value['environment']
    assert env['ANTHROPIC_API_KEY'] == DUMMY_KEY
    assert env['CLAUDE_CODE_DISABLE_1M_CONTEXT'] == '0'
    for key in list(env):
        if key == 'ANTHROPIC_API_KEY':
            continue
        if key == 'ANTHROPIC_BASE_URL':
            env[key] = 'http://127.0.0.1:18455'
        elif key == 'PATH':
            env[key] = '/fixture/bin:/usr/bin:/bin'
        elif key in ('HOME', 'CLAUDE_CONFIG_DIR', 'CLAUDE_SECURESTORAGE_CONFIG_DIR', 'PYSTOW_HOME'):
            env[key] = '/fixture/' + key.lower().replace('_', '-')
        else:
            assert env[key] in ('0', '1', '1000000'), key
    value['cwd'] = '/fixture/cwd'
    assert value['stdin'] == 'DEVNULL' and value['process_limit'] == 1
    assert value['prompt_sha256'] == digest(b'Reply with OK.')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    assert not OUTPUT.exists(), 'fixture output must be fresh'
    selected = {'stdout.jsonl': source / 'stdout.jsonl',
                'request.json': source / 'requests/000001.json',
                'invocation.json': source / 'invocation.json'}
    assert all(path.is_file() and not path.is_symlink() for path in selected.values())
    originals = {name: path.read_bytes() for name, path in selected.items()}
    rows = [json.loads(line) for line in originals['stdout.jsonl'].splitlines()]
    assert [(x['type'], x.get('subtype')) for x in rows] == [
        ('system', 'ui_invalidate'), ('system', 'init'), ('assistant', None), ('result', 'success')]
    assert rows[1]['model'] == rows[2]['message']['model'] == 'claude-opus-5'
    own = rows[-1]['modelUsage']['claude-opus-5']
    assert set(rows[-1]['modelUsage']) == {'claude-opus-5'}
    assert own['contextWindow'] == 1000000 and own['maxOutputTokens'] == 64000
    assert own['canonicalModel'] == 'claude-opus-5' and own['provider'] == 'firstParty'
    request = json.loads(originals['request.json'])
    assert request['model'] == 'claude-opus-5' and request['max_tokens'] == 64000
    assert request['thinking'] == {'type': 'adaptive'} and request['output_config'] == {'effort': 'high'}
    sanitized = {
        'stdout.jsonl': b''.join(encoded(sanitize(row)) + b'\n' for row in rows),
        'request.json': encoded(sanitize(request)) + b'\n',
        'invocation.json': encoded(invocation_fixture(json.loads(originals['invocation.json']))) + b'\n'}
    for raw in sanitized.values():
        assert bytes([64]) not in raw and b'/Users/' not in raw
    OUTPUT.mkdir()
    for name, raw in sanitized.items():
        with (OUTPUT / name).open('xb') as stream:
            stream.write(raw)
        assert (OUTPUT / name).read_bytes() == raw
    provenance = {'kind': 'sanitized_spent_cli_model_shape', 'version': 1,
        'source_role': 'CHORUS cell 1 spent D117 observation, 2026-11-19',
        'cli_version': '2.1.325', 'source_is_successful_admission': False,
        'source_files': {name: {'bytes': len(raw), 'sha256': digest(raw)} for name, raw in originals.items()},
        'fixture_files': {name: {'bytes': len(raw), 'sha256': digest(raw)} for name, raw in sanitized.items()},
        'generator_sha256': digest(Path(__file__).read_bytes()),
        'sanitization': ['Private prompts and reply text replaced.',
            'Account metadata, paths and identifiers replaced.',
            'Timestamp replaced with a relative-date placeholder expanded by tests.',
            'Record order, model fields, numeric limits and known dummy API key retained.'],
        'authority': 'Offline parser fixture only; no authorization, login proof or native acceptance.'}
    with (OUTPUT / 'provenance.json').open('xb') as stream:
        stream.write(encoded(provenance) + b'\n')
    assert all(path.read_bytes() == originals[name] for name, path in selected.items())
    print(json.dumps({'output': str(OUTPUT), 'fixture_files': provenance['fixture_files'],
                      'spent_sources_unchanged': True}, indent=2))


if __name__ == '__main__':
    main()
