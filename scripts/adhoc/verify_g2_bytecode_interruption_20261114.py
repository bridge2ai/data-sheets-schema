#!/usr/bin/env python3
# Verify BYTECODE-F1 using isolated synthetic files and real local rename,
# 2026-11-14. Inputs: immutable pre-fix helper and corrected helper source.
# Outputs: exclusive three-case proof/fixtures in bytecode-preservation-verification.
# Never executes either helper's main, touches the real source cache, imports
# project code, runs pytest, or creates a commit.
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114/bytecode-preservation-verification'
TARGET = ROOT / 'scripts/adhoc/preserve_g2_source_bytecode_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def document(path, value):
    save(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    return pin(path)


def functions(path):
    tree = ast.parse(path.read_bytes(), filename=str(path))
    names = {'fingerprint', 'expected', 'observe_location', 'reconcile_rename', 'rename_and_verify'}
    chosen = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in chosen} == names
    main, = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main']
    assert any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
               and node.func.id == 'rename_and_verify' for node in ast.walk(main))
    namespace = {'stat': stat, 'hashlib': hashlib}
    exec(compile(ast.Module(body=chosen, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


def fixture(name, behavior):
    directory = OUT / name
    directory.mkdir()
    original, preserved, source = directory / 'original.pyc', directory / 'preserved.pyc', directory / 'source.py'
    save(original, b'synthetic cached bytes; never imported\n')
    save(source, b'# synthetic helper source; never executed\n')
    namespace = functions(TARGET)
    before_cache, before_source = namespace['fingerprint'](original), namespace['fingerprint'](source)
    cache_identity = {key: before_cache[key] for key in ('bytes', 'sha256')}
    source_identity = {key: before_source[key] for key in ('bytes', 'sha256')}

    def interrupted_rename(old, new):
        if behavior == 'before':
            raise KeyboardInterrupt('injected immediately before rename')
        os.rename(old, new)
        if behavior == 'ambiguous':
            save(old, b'unexpected new synthetic bytes at original location\n')
        raise KeyboardInterrupt('injected immediately after successful real rename')

    namespace.update(os=SimpleNamespace(rename=interrupted_rename),
        EXPECTED_CACHE=cache_identity, EXPECTED_SOURCE=source_identity,
        inventory=lambda: ['synthetic-original.pyc'],
        document=lambda name, value: document(directory / name, value),
        git=lambda *args: (_ for _ in ()).throw(AssertionError('Git must not run in an interruption case')))
    arguments = (original, preserved, source, before_cache, before_source,
                 ['synthetic-original.pyc'], 'synthetic-head', '', {'fixture': name})
    return namespace, arguments, directory


def main():
    assert OUT.is_dir() and not (OUT / 'result.json').exists()
    reviewed = OUT / 'reviewed-preserve-helper.py'
    save(reviewed, TARGET.read_bytes())
    # Reproduce the original defect from its actual saved try/except AST,
    # without executing its preflight/main or accessing the real cache.
    old = OUT / 'before-preserve-helper.py'
    assert pin(old)['sha256'] == '4a30efddba94c294e9bcc0b776d07ca96866131dd902d4f51bb4614623c81b61'
    tree = ast.parse(old.read_bytes())
    old_main, = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main']
    old_try, = [node for node in old_main.body if isinstance(node, ast.Try)]
    namespace, arguments, directory = fixture('before-fix-counterexample', 'after')
    names = ('original', 'preserved', 'source', 'before_cache', 'before_source',
             'before_inventory', 'head', 'tracked', 'plan')
    namespace.update(zip(names, arguments))
    namespace['moved'] = False
    try:
        exec(compile(ast.Module(body=[old_try], type_ignores=[]), str(old), 'exec'), namespace)
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError('original counterexample did not interrupt')
    baseline = json.loads((directory / 'outcome.json').read_bytes())
    assert baseline['rename_completed'] is False
    assert not arguments[0].exists() and arguments[1].is_file()
    baseline_proof = {'false_negative_reproduced': True, 'outcome': pin(directory / 'outcome.json'),
                      'preserved': pin(arguments[1])}
    cases = []
    for name, behavior, expected_state in (
        ('interruption_after_rename', 'after', 'observed_at_preserved_path'),
        ('interruption_before_rename', 'before', 'observed_at_original_path'),
        ('ambiguous_locations', 'ambiguous', 'unknown')):
        namespace, arguments, directory = fixture(name, behavior)
        try:
            namespace['rename_and_verify'](*arguments)
        except KeyboardInterrupt:
            pass
        else:
            raise AssertionError('injected interruption did not propagate: ' + name)
        outcome = json.loads((directory / 'outcome.json').read_bytes())
        observation = outcome['rename_observation']
        assert observation['state'] == expected_state, observation
        assert 'rename_completed' not in outcome
        assert namespace['fingerprint'](arguments[2]) == arguments[4], 'synthetic source changed'
        retained = arguments[0] if behavior == 'before' else arguments[1]
        assert namespace['fingerprint'](retained) == arguments[3], 'synthetic cache bytes lost'
        cases.append({'case': name, 'passed': True, 'observed_state': expected_state,
                      'outcome': pin(directory / 'outcome.json'), 'retained': pin(retained)})
    result = {'finding_id': 'G2-REVIEW-BYTECODE-F1', 'status': 'verified',
        'verified_entrypoint': 'rename_and_verify', 'helper': pin(TARGET),
        'producer': pin(Path(__file__).resolve()), 'reviewed_source': pin(reviewed),
        'ledger': pin(OUT.parent / 'review-bytecode.json'), 'cases': cases, 'passed': 3, 'failed': 0,
        'original_counterexample': baseline_proof,
        'scope': 'Actual saved helper functions on isolated synthetic files; real rename with injected interruption. No actual source-cache preservation, project import, pytest or commit.'}
    output = document(OUT / 'result.json', result)
    print(json.dumps({'output': output, 'passed': 3, 'failed': 0}, indent=2))


if __name__ == '__main__':
    main()
