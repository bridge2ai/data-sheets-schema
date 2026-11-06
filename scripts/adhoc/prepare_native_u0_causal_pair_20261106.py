#!/usr/bin/env python3
"""Prepare U0's diagnostic-only causal pair, #4354, 2026-11-06.

Inputs: frozen 01969cbed Git objects and committed local instrumentation/tools.
Outputs: two fresh isolated execution worktrees, commits and a pin manifest.
No trials, production fixes, guard exceptions, network or publication.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('u0_prepare_base',
    Path(__file__).with_name('prepare_native_u0_cpu_copy_20261106.py'))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
EXEC = base.EXEC
BRANCHES = {'control': 'codex/native-u0-pair-control-20261106',
            'treatment': 'codex/native-u0-pair-treatment-20261106'}
DESTINATIONS = {arm: EXEC / ('codex-native-u0-pair-' + arm + '-20261106') for arm in BRANCHES}
HELPERS = ('scripts/adhoc/native_recorder_observer_20261026.py',
           'scripts/adhoc/native_recorder_thread_cpu_20261106.py',
           'scripts/adhoc/native_u0_source_closure_20261106.py')
TREATMENT = 'scripts/adhoc/native_u0_parser_event_treatment_20261106.py'
PAYLOAD = 'scripts/adhoc/native_u0_parser_event_reuse_payload_20261106.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def new_tree(arm, parent):
    tree = DESTINATIONS[arm]
    base.git(ROOT, 'worktree', 'add', '--no-checkout', '-b', BRANCHES[arm], str(tree), parent)
    base.git(tree, 'sparse-checkout', 'init', '--cone')
    base.git(tree, 'sparse-checkout', 'set', 'src', 'scripts', 'tests', 'utils', '.claude', 'notes')
    base.git(tree, 'read-tree', '-mu', 'HEAD')  # Only the newly created, empty worktree.
    return tree


def finish(tree, parent, paths, message):
    base.git(tree, 'add', '--', *paths)
    actual = base.git(tree, 'diff', '--cached', '--name-only').decode().splitlines()
    if sorted(actual) != sorted(paths):
        raise ValueError('unexpected staged diagnostic paths')
    base.git(tree, 'diff', '--cached', '--check')
    base.git(tree, 'commit', '-m', message)
    head = base.git(tree, 'rev-parse', 'HEAD').decode().strip()
    if base.git(tree, 'show', '-s', '--format=%P', 'HEAD').decode().strip() != parent:
        raise ValueError('unexpected diagnostic parent')
    if base.git(tree, 'status', '--porcelain').strip():
        raise ValueError('diagnostic worktree is not clean')
    pins = {path: {'bytes': len((tree / path).read_bytes()),
                   'sha256': base.sha((tree / path).read_bytes())} for path in paths}
    return {'head': head, 'parent': parent, 'worktree': str(tree),
            'branch': base.git(tree, 'branch', '--show-current').decode().strip(),
            'changed_paths': sorted(actual), 'files': pins}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    manifest = args.manifest.absolute()
    if (manifest.exists() or manifest.is_symlink()
            or not manifest.parent.resolve(strict=True).is_relative_to(EXEC)):
        raise ValueError('manifest must be a new external execution evidence file')
    if (EXEC / 'plans/native_quiet_window.lock').exists():
        raise ValueError('quiet measurement lock exists; preparation must pause')
    for tree in DESTINATIONS.values():
        if tree.exists() or tree.is_symlink() or tree.parent.resolve(strict=True) != EXEC:
            raise ValueError('pair source destinations must be new direct execution children')
    if base.git(ROOT, 'status', '--porcelain').strip():
        raise ValueError('commit all tooling before source preparation')
    tooling_head = base.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    for path in (*HELPERS, TREATMENT, PAYLOAD, 'scripts/adhoc/prepare_native_u0_cpu_copy_20261106.py'):
        if (ROOT / path).read_bytes() != base.git(ROOT, 'show', tooling_head + ':' + path):
            raise ValueError('tool differs from committed blob: ' + path)
    closure = load(HELPERS[2], 'u0_source_closure_preparation')
    observer = load(HELPERS[1], 'u0_thread_cpu_preparation')
    treatment = load(TREATMENT, 'u0_parser_treatment_preparation')
    config_path = 'scripts/adhoc/' + observer.CONFIG_NAME
    helper_raw = {path: (ROOT / path).read_bytes() for path in HELPERS}
    helper_raw[config_path] = observer.CONFIG_BYTES
    parent = Path(json.loads(observer.CONFIG_BYTES)['output_parent'])
    if parent.resolve(strict=True) != parent or not parent.is_relative_to(EXEC):
        raise ValueError('observer evidence parent must already exist outside source trees')
    bindings = {path: base.sha(raw) for path, raw in helper_raw.items()}
    bootstrap = (
        '# Instrumentation-only U0 causal pair; committed source binding unchanged.\n'
        'import sys as _u0_thread_sys\n'
        'if _u0_thread_sys.argv[1:3] == ["provenance", "record"]:\n'
        '    import hashlib as _u0_thread_hashlib\n'
        '    import runpy as _u0_thread_runpy\n'
        '    from pathlib import Path as _u0_thread_Path\n'
        '    _u0_thread_root = _u0_thread_Path(__file__).resolve().parents[3]\n'
        '    for _u0_thread_rel, _u0_thread_sha in ' + repr(bindings) + '.items():\n'
        '        if _u0_thread_hashlib.sha256((_u0_thread_root / _u0_thread_rel).read_bytes()).hexdigest() != _u0_thread_sha:\n'
        '            raise RuntimeError("U0 causal pair helper hash differs")\n'
        '    _u0_thread_runpy.run_path(str(_u0_thread_root / "' + HELPERS[1] + '"))["install_from_config"](_u0_thread_root)\n')
    original = base.git(ROOT, 'show', base.BASE + ':' + base.BOOT_PATH)
    parsed = ast.parse(original)
    if not isinstance(parsed.body[0], ast.Expr) or not isinstance(parsed.body[0].value, ast.Constant):
        raise ValueError('expected leading CLI docstring')
    lines = original.splitlines(keepends=True)
    split = parsed.body[0].end_lineno
    patched = b''.join(lines[:split]) + b'\n' + bootstrap.encode() + b'\n' + b''.join(lines[split:])
    if patched.replace(b'\n' + bootstrap.encode() + b'\n', b'', 1) != original:
        raise ValueError('CLI original bytes must remain in order')
    ast.parse(patched)
    pkg = 'src/data_sheets_schema/__init__.py'
    package_bytes = closure.package_bootstrap(bindings[HELPERS[2]])
    ast.parse(package_bytes)
    control = new_tree('control', base.BASE)
    if (control / pkg).exists():
        raise ValueError('expected frozen namespace package without __init__.py')
    for path, raw in helper_raw.items():
        dest = control / path
        if dest.exists():
            raise ValueError('unexpected existing diagnostic helper: ' + path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    (control / pkg).write_bytes(package_bytes)
    (control / base.BOOT_PATH).write_bytes(patched)
    ctl = finish(control, base.BASE, [*helper_raw, pkg, base.BOOT_PATH],
                 'Isolate source and record thread CPU for U0 control only')
    variant = new_tree('treatment', ctl['head'])
    changed = treatment.apply_treatment(variant)
    paths = base.git(variant, 'status', '--porcelain', '--untracked-files=all').decode().splitlines()
    # The treatment helper supplies its exact changed path roster; independently
    # bind all tracked/untracked modifications before committing.
    expected = sorted(changed['changed_paths'])
    observed = sorted(row[3:] for row in paths)
    if observed != expected:
        raise ValueError('treatment changed paths differ from its declared roster')
    trt = finish(variant, ctl['head'], expected,
                 'Apply bounded native schema parser-event reuse for U0 diagnostic only')
    for path, raw in {**helper_raw, pkg: package_bytes, base.BOOT_PATH: patched}.items():
        if (variant / path).read_bytes() != raw:
            raise ValueError('treatment changed common instrumentation: ' + path)
    protected = ('src/data_sheets_schema/shared_generation.py', 'canonical_hashes.yaml')
    for arm in (ctl, trt):
        if base.git(ROOT, 'diff', '--name-only', base.BASE, arm['head'], '--', *protected).strip():
            raise ValueError('protected source differs')
    result = {'format': 'native_u0_causal_pair_sources_v1', 'base': base.BASE,
              'tooling_head': tooling_head, 'control': ctl, 'treatment': trt,
              'treatment_manifest': changed, 'common_instrumentation_byte_identical': True,
              'limits': {'helper_seconds': 180, 'attempt_seconds': 900},
              'scope': 'diagnostic copies only; no production fix; one CPU pair; no N=10'}
    with manifest.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'control': ctl['head'], 'treatment': trt['head'],
                      'manifest': str(manifest), 'sha256': base.sha(manifest.read_bytes())}))


if __name__ == '__main__':
    main()
