#!/usr/bin/env python3
"""U0 T2 eager-validator synthetic falsification, 2026-11-06.

Read pinned treatment source after early ordinary validator import. Output new
external closure, cache counts and mutation refusals. No recorder or production
edits; child uses existing OS network/source-write denial and allowlisted env.
"""
from __future__ import annotations
import argparse
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys
import time

PIN = '2747e86c3f0521c1ef5c455d9be82428e4ca5be7'


def child(tree, out):
    denied = False
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', 0))
        except OSError as exc:
            denied = exc.errno == errno.EPERM
    if not denied:
        raise RuntimeError('network denial self-check failed')
    import linkml.validator
    import yaml
    from data_sheets_schema import native_shared_capture
    from data_sheets_schema import native_catalog_reuse as catalog
    from data_sheets_schema import native_schema_event_reuse as events
    from data_sheets_schema import audit_omissions as omissions
    closure = runpy.run_path(str(tree / 'scripts/adhoc/native_u0_source_closure_20261106.py'))
    before_closure = closure['assert_source_closure'](tree)
    before = {'catalog_ready': catalog.runtime_token() is not None,
              'event_ready': events._token(8_000_000) is not None,
              'same_error_reader_mark': yaml.error.Mark is yaml.reader.Mark,
              'Mark_in_catalog_alias_names': 'Mark' in catalog._YAML_NAMES}
    schema = b'id: https://example.org/probe\nname: probe\nclasses: {Dataset: {}}\n'
    def native(raw):
        return omissions._mapping(raw, 'native schema', limit=8_000_000, _native_events=True)
    def ordinary(raw):
        return omissions._mapping(raw, 'native schema', limit=8_000_000)
    first, second = native(schema), native(schema)
    assert first == second == ordinary(schema)
    assert first is not second
    counts = events.counters()
    def refusal(fn):
        try:
            return {'value': fn()}
        except Exception as exc:
            chain = []
            while exc is not None:
                chain.append([type(exc).__module__, type(exc).__qualname__, str(exc)])
                exc = exc.__cause__
            return {'error': chain}
    refusal_rows = []
    for raw in (b'x: 1\nx: 2\n', b'x: [unfinished', b'x: *missing\n'):
        a, b = refusal(lambda: native(raw)), refusal(lambda: ordinary(raw))
        refusal_rows.append({'input_hex': raw.hex(), 'equal': a == b, 'native': a, 'ordinary': b})
        assert a == b
    mutation_rows = []
    for owner, name in ((yaml.reader, 'Mark'), (yaml.error, 'Mark'), (yaml, 'parse')):
        prior = getattr(owner, name)
        setattr(owner, name, lambda *a, **k: None)
        try:
            mutation_rows.append({'owner': owner.__name__, 'name': name,
                'catalog_refused': catalog.runtime_token() is None,
                'events_refused': events._token(8_000_000) is None})
        finally:
            setattr(owner, name, prior)
    after_closure = closure['assert_source_closure'](tree)
    outcome = {'network_bind_denied': denied, 'source_head': PIN, 'before': before,
        'two_valid_document_counts': counts, 'refusals': refusal_rows, 'mutations': mutation_rows,
        'source_closure_start': before_closure, 'source_closure_end': after_closure,
        'rawloader_source': str(Path(sys.modules['linkml.utils.rawloader'].__file__).resolve()),
        'rawloader_sha256': hashlib.sha256(Path(sys.modules['linkml.utils.rawloader'].__file__).read_bytes()).hexdigest(),
        'candidate_passes_cold_hit_and_guards': counts['parses'] == 1 and counts['hits'] == 1
            and counts['fallbacks'] == 0 and all(row['catalog_refused'] and row['events_refused'] for row in mutation_rows)}
    (out / 'evidence.json').write_text(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps({key: outcome[key] for key in ('before', 'two_valid_document_counts', 'mutations',
                                                'candidate_passes_cold_hit_and_guards')}))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--child', action='store_true')
    args = parser.parse_args()
    tree, out = args.tree.resolve(strict=True), args.out.absolute()
    if args.child:
        return child(tree, out)
    tool = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('eager_wrapper', tool / 'scripts/adhoc/native_u0_run_20261106.py')
    wrapper = importlib.util.module_from_spec(spec); spec.loader.exec_module(wrapper)
    if wrapper.LOCK_PATH.exists():
        raise RuntimeError('quiet measurement lock exists; probe must pause')
    if (not tree.is_relative_to(wrapper.EXEC_ROOT) or out.is_relative_to(tree)
            or out.is_relative_to(tool) or not out.parent.resolve(strict=True).is_relative_to(wrapper.EXEC_ROOT)):
        raise ValueError('prepared source and fresh external output required')
    if subprocess.check_output(['/usr/bin/git', '-C', str(tree), 'rev-parse', 'HEAD'], text=True).strip() != PIN:
        raise ValueError('treatment pin differs')
    out.mkdir(mode=0o700, exist_ok=False)
    home, temporary = out / 'home', out / 'tmp'
    home.mkdir(); temporary.mkdir()
    env = wrapper.clean_environment(home, temporary)
    env['PYTHONPATH'] = os.pathsep.join(str(tree / p) for p in ('src', 'scripts', '.'))
    env['PYTHONPYCACHEPREFIX'] = str(out / 'pycache')
    command = [str(wrapper.SANDBOX), '-D', 'FROZEN_TREE=' + str(tree), '-D',
        'HOST_SAMPLES=' + str(out / 'unused-samples.jsonl'), '-f', str(wrapper.PROFILE),
        str(args.python.absolute()), '-P', '-B', str(Path(__file__).resolve()),
        '--child', '--tree', str(tree), '--out', str(out)]
    (out / 'command.json').write_text(json.dumps({'command': command, 'environment_names': sorted(env),
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'profile_sha256': hashlib.sha256(wrapper.PROFILE.read_bytes()).hexdigest()}, indent=2) + '\n')
    started = time.monotonic()
    with (out / 'child.log').open('xb') as log:
        complete = subprocess.run(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT,
                                  timeout=120, check=False)
    outcome = {'returncode': complete.returncode, 'wall_seconds': time.monotonic()-started,
               'evidence_exists': (out / 'evidence.json').is_file()}
    (out / 'outcome.json').write_text(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps(outcome))
    return complete.returncode


if __name__ == '__main__':
    raise SystemExit(main())
