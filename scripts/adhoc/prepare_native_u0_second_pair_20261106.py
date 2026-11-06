#!/usr/bin/env python3
"""Prepare U0 treatment-1 vs treatment-1+2 diagnostic sources, 2026-11-06.

Inputs: frozen first-treatment Git objects and committed local tooling (D92).
Outputs: two new execution worktrees/commits and one exclusive pin manifest.
No measurements, provider, network, production change or guard bypass.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
FIRST_TREATMENT = '2747e86c3f0521c1ef5c455d9be82428e4ca5be7'
FROZEN = '01969cbed8eed93f420c640c1f1c306e5f58b033'
OBSERVER = 'scripts/adhoc/native_recorder_second_cpu_20261106.py'
TREATMENT = 'scripts/adhoc/native_u0_second_treatment_20261106.py'
PAYLOAD = 'scripts/adhoc/native_u0_catalog_initialization_payload_20261106.py'
COMMON = ('scripts/adhoc/native_recorder_observer_20261026.py',
          'scripts/adhoc/native_recorder_thread_cpu_20261106.py',
          'scripts/adhoc/native_u0_source_closure_20261106.py')
PROTECTED = ('src/data_sheets_schema/shared_generation.py',
             'src/download/prompts/canonical_hashes.yaml')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pair = load('scripts/adhoc/prepare_native_u0_causal_pair_20261106.py', 'u0_pair1_preparer')
base, EXEC = pair.base, pair.EXEC
DESTINATIONS = {arm: EXEC / ('codex-native-u0-second-' + arm + '-20261106')
                for arm in ('control', 'treatment')}
BRANCHES = {arm: 'codex/native-u0-second-' + arm + '-20261106' for arm in DESTINATIONS}


def new_tree(arm, parent):
    tree = DESTINATIONS[arm]
    base.git(ROOT, 'worktree', 'add', '--no-checkout', '-b', BRANCHES[arm], str(tree), parent)
    base.git(tree, 'sparse-checkout', 'init', '--cone')
    base.git(tree, 'sparse-checkout', 'set', 'src', 'scripts', 'tests', 'utils', '.claude', 'notes')
    base.git(tree, 'read-tree', '-mu', 'HEAD')  # New empty worktree only.
    return tree


def cli_bootstrap(original, bindings):
    parsed = ast.parse(original)
    if not isinstance(parsed.body[0], ast.Expr) or not isinstance(parsed.body[0].value, ast.Constant):
        raise ValueError('expected leading original CLI docstring')
    block = (
        '# Diagnostic-only U0 second pair: identical source-bound observer in both arms.\n'
        'import sys as _u0_second_sys\n'
        'if _u0_second_sys.argv[1:3] == ["provenance", "record"]:\n'
        '    import hashlib as _u0_second_hashlib\n'
        '    import runpy as _u0_second_runpy\n'
        '    from pathlib import Path as _u0_second_Path\n'
        '    _u0_second_root = _u0_second_Path(__file__).resolve().parents[3]\n'
        '    for _u0_second_rel, _u0_second_sha in ' + repr(bindings) + '.items():\n'
        '        if _u0_second_hashlib.sha256((_u0_second_root / _u0_second_rel).read_bytes()).hexdigest() != _u0_second_sha:\n'
        '            raise RuntimeError("U0 second pair helper hash differs")\n'
        '    _u0_second_runpy.run_path(str(_u0_second_root / "' + OBSERVER + '"))["install_from_config"](_u0_second_root)\n')
    lines = original.splitlines(keepends=True)
    split = parsed.body[0].end_lineno
    insertion = b'\n' + block.encode() + b'\n'
    patched = b''.join(lines[:split]) + insertion + b''.join(lines[split:])
    if patched.replace(insertion, b'', 1) != original:
        raise ValueError('original CLI bytes must remain in order')
    ast.parse(patched)
    return patched


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    manifest = args.manifest.absolute()
    if (manifest.exists() or manifest.is_symlink()
            or manifest.parent.resolve(strict=True) != EXEC / 'native-u0-20261106'):
        raise ValueError('manifest must be new external execution evidence')
    if (EXEC / 'plans/native_quiet_window.lock').exists():
        raise ValueError('quiet lock exists; source preparation must pause')
    for tree in DESTINATIONS.values():
        if tree.exists() or tree.is_symlink() or tree.parent.resolve(strict=True) != EXEC:
            raise ValueError('second-pair source destinations must be new direct execution children')
    if base.git(ROOT, 'status', '--porcelain').strip():
        raise ValueError('commit all tooling before source preparation')
    tooling_head = base.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    for path in (OBSERVER, TREATMENT, PAYLOAD, *COMMON):
        if (ROOT / path).read_bytes() != base.git(ROOT, 'show', tooling_head + ':' + path):
            raise ValueError('tool differs from committed blob: ' + path)
    observer = load(OBSERVER, 'u0_second_observer_preparation')
    treatment = load(TREATMENT, 'u0_second_treatment_preparation')
    config_path = 'scripts/adhoc/' + observer.CONFIG_NAME
    output = Path(json.loads(observer.CONFIG_BYTES)['output_parent'])
    if output != EXEC / 'native-u0-20261106/second-observer-output':
        raise ValueError('unexpected second observer output parent')
    output.mkdir(mode=0o700, exist_ok=False)
    inherited = {path: base.git(ROOT, 'show', FIRST_TREATMENT + ':' + path) for path in COMMON}
    for path, raw in inherited.items():
        if raw != (ROOT / path).read_bytes():
            raise ValueError('frozen first-pair instrumentation differs: ' + path)
    added = {OBSERVER: (ROOT / OBSERVER).read_bytes(), config_path: observer.CONFIG_BYTES}
    bindings = {path: base.sha(raw) for path, raw in {**inherited, **added}.items()}
    original = base.git(ROOT, 'show', FROZEN + ':' + base.BOOT_PATH)
    boot = cli_bootstrap(original, bindings)
    control = new_tree('control', FIRST_TREATMENT)
    for path, raw in added.items():
        with (control / path).open('xb') as stream:
            stream.write(raw)
    (control / base.BOOT_PATH).write_bytes(boot)
    ctl = pair.finish(control, FIRST_TREATMENT, [*added, base.BOOT_PATH],
                      'Observe remaining U0 treatment-1 CPU and cache eligibility only')
    variant = new_tree('treatment', ctl['head'])
    changed = treatment.apply_treatment(variant)
    expected = sorted(changed['changed_paths'])
    actual = sorted(row[3:] for row in base.git(variant, 'status', '--porcelain',
                    '--untracked-files=all').decode().splitlines())
    if actual != expected:
        raise ValueError('second treatment changed path roster differs')
    trt = pair.finish(variant, ctl['head'], expected,
                      'Apply second U0 diagnostic treatment without changing validation authority')
    for path, raw in {**inherited, **added, base.BOOT_PATH: boot}.items():
        if (variant / path).read_bytes() != raw:
            raise ValueError('second treatment changed common instrumentation: ' + path)
    for arm in (ctl, trt):
        if base.git(ROOT, 'diff', '--name-only', FIRST_TREATMENT, arm['head'], '--', *PROTECTED).strip():
            raise ValueError('protected source differs')
    result = {'format': 'native_u0_second_pair_sources_v1', 'base': FROZEN,
        'first_treatment': FIRST_TREATMENT, 'tooling_head': tooling_head,
        'control': ctl, 'treatment': trt, 'treatment_manifest': changed,
        'common_instrumentation_byte_identical': True,
        'limits': {'helper_seconds': 180, 'attempt_seconds': 900},
        'scope': 'diagnostic copies only; T1 vs T1+T2; one pair; no production fix or N=10'}
    with manifest.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'control': ctl['head'], 'treatment': trt['head'],
                     'manifest': str(manifest), 'sha256': base.sha(manifest.read_bytes())}))


if __name__ == '__main__':
    main()
