"""U3-E 2026-11-08 final offline supplemental comparisons and coverage.
Inputs: saved main, retained plans/XML and committed harness; outputs: only
scratch-native-u1u3. One supervised invocation at a time; final SG2 last.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import hashlib
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u1u3'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/adhoc' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def run(label, nodes, runner='run_native_u1u3_20261108.py', workers=2, basis=None):
    while os.path.lexists(LOCK):
        print('Quiet window: waiting 60 seconds', flush=True)
        time.sleep(60)
    env = dict(os.environ)
    if basis:
        env['U3E_PARITY_BASIS'] = basis
    command = [str(PYTHON), '-S', '-P', '-B', str(ROOT / 'scripts/adhoc' / runner),
               '--out', str(OUT / label), '--workers', str(workers), *nodes]
    print('START ' + label, flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env)
    print('END ' + label + ' exit=' + str(result.returncode), flush=True)
    outcome_path = OUT / label / 'outcome.json'
    if not outcome_path.exists():
        raise RuntimeError('supervisor refused before outcome; retain startup log and stop')
    outcome = json.loads(outcome_path.read_text())
    if outcome.get('observed_surviving_pids') != [] or result.returncode not in (0, 1):
        raise RuntimeError('stop at infrastructure interruption; retain evidence')
    return result.returncode
def prepare():
    c = load('compose_native_u1u3_20261108')
    tree = OUT / 'baseline-parity'
    tree.mkdir()
    c.extract(OUT / 'baseline.tar', tree)
    paths = ['tests/test_native_u1_api_parity.py', 'scripts/adhoc/u3e_parity_plugin_20261108.py']
    for relative in paths:
        (tree / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, tree / relative)
    c.git('init', cwd=tree)
    objects = c.git('rev-parse', '--path-format=absolute', '--git-path', 'objects').decode().strip()
    (tree / '.git/objects/info/alternates').write_text(objects + '\n')
    # Preserve all tracked-but-ignored files and every Gitlink, not a fresh add.
    c.git('read-tree', 'cf50d9a1c059f3b5030103378ccef33619475dde', cwd=tree)
    c.git('add', '--', *paths, cwd=tree)
    c.git('commit', '-m', 'Offline saved-main parity with identical test harness', cwd=tree)
    manifest = {'baseline': 'cf50d9a1c059f3b5030103378ccef33619475dde',
                'private_commit': c.git('rev-parse', 'HEAD', cwd=tree).decode().strip(),
                'harness_only_additions': {p: hashlib.sha256((tree / p).read_bytes()).hexdigest() for p in paths}}
    (OUT / 'baseline-parity-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
def repair_baseline():
    c = load('compose_native_u1u3_20261108')
    tree = OUT / 'baseline-parity'
    base = 'cf50d9a1c059f3b5030103378ccef33619475dde'
    before = c.git('rev-parse', 'HEAD', cwd=tree).decode().strip()
    assert not c.git('status', '--porcelain', cwd=tree).strip()
    pin = c.git('ls-tree', base, 'fairscape_models').decode().split()
    assert pin[:2] == ['160000', 'commit']
    objects = c.git('rev-parse', '--path-format=absolute', '--git-path', 'objects').decode().strip()
    (tree / '.git/objects/info/alternates').write_text(objects + '\n')
    expected = ['scripts/adhoc/u3e_parity_plugin_20261108.py', 'tests/test_native_u1_api_parity.py']
    c.git('read-tree', base, cwd=tree)
    c.git('add', '--', *expected, cwd=tree)
    assert sorted(c.git('diff', '--cached', '--name-only', base, cwd=tree).decode().splitlines()) == expected
    c.git('commit', '-m', 'Restore complete saved-main index including ignored tracked evidence', cwd=tree)
    delta = c.git('diff', '--name-only', base, 'HEAD', cwd=tree).decode().splitlines()
    assert sorted(delta) == expected
    assert not c.git('status', '--porcelain', cwd=tree).strip()
    manifest = {'baseline': base, 'previous_private_commit': before,
                'private_commit': c.git('rev-parse', 'HEAD', cwd=tree).decode().strip(),
                'gitlink': pin[2], 'exact_delta_from_baseline': delta,
                'read_only_alternate_objects': objects}
    (OUT / 'baseline-parity-repaired-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
def plans():
    old = json.loads((OUT / 'suite-plan.json').read_text())
    covered = {x.split('::')[0] for name, values in old.items() if name != 'collection' for x in values}
    covered.update(x.split('::')[0] for _, values in json.loads((OUT / 'continuation-plan.json').read_text()) for x in values)
    missing = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'tests').rglob('test_*.py')
                     if p.name.startswith(('test_receipt', 'test_shared')) and str(p.relative_to(ROOT)) not in covered)
    groups = [('supplement-' + str(i // 4 + 1), missing[i:i+4]) for i in range(0, len(missing), 4)]
    (OUT / 'extra-plan.json').write_text(json.dumps(groups, indent=2) + '\n')
    return groups
def parity():
    prefix = 'tests/test_native_u1_api_parity.py::'
    canary = prefix + 'test_existing_conditions[generic]'
    remaining = [prefix + 'test_existing_conditions[' + c + ']' for c in ['tuned', *['generic_v' + str(n) for n in range(2, 10)]]]
    remaining += [prefix + 'test_shared_v1', prefix + 'test_shared_v2[declared_heading_spans_v1]',
                  prefix + 'test_shared_v2[captured_json_values_v1]', prefix + 'test_bc1']
    for basis in ('baseline', 'candidate', 'packet'):
        assert run('parity2-canary-' + basis, [canary], 'parity_native_u1u3_20261108.py', basis=basis) == 0
        artifact = OUT / ('parity2-canary-' + basis) / 'parity/generic.txt'
        assert artifact.stat().st_size > 0
    for basis in ('candidate', 'packet'):
        assert (OUT / 'parity2-canary-baseline/parity/generic.txt').read_bytes() == (OUT / ('parity2-canary-' + basis) / 'parity/generic.txt').read_bytes()
    for basis in ('baseline', 'candidate', 'packet'):
        assert run('parity2-rest-' + basis, remaining, 'parity_native_u1u3_20261108.py', basis=basis) == 0
    files = {basis: {p.name: p for part in ('canary', 'rest') for p in (OUT / ('parity2-' + part + '-' + basis) / 'parity').glob('*.txt')} for basis in ('baseline', 'candidate', 'packet')}
    for basis in ('candidate', 'packet'):
        assert files['baseline'].keys() == files[basis].keys() and len(files['baseline']) == 14
        rows = []
        for name in sorted(files['baseline']):
            a, b = (files[key][name].read_bytes() for key in ('baseline', basis))
            rows.append({'name': name, 'basis': basis, 'before_sha256': hashlib.sha256(a).hexdigest(),
                         'after_sha256': hashlib.sha256(b).hexdigest(), 'before_bytes': len(a), 'after_bytes': len(b), 'equal': a == b})
        (OUT / ('api-render-parity.json' if basis == 'candidate' else 'packet-api-render-parity.json')).write_text(json.dumps(rows, indent=2) + '\n')
        print('Raw API parity ' + basis + ': ' + str(sum(r['equal'] for r in rows)) + '/14', flush=True)
def main():
    action = sys.argv[1]
    if action == 'prepare':
        prepare()
        plans()
    elif action == 'repair-baseline':
        repair_baseline()
    elif action == 'final':
        parity()
        packet_runner = str(OUT / 'packet-parity-composition/tree/scripts/adhoc/run_native_u1u3_20261108.py')
        run('packet-specificity-hooks', [
            'tests/test_generation_specificity_skill.py::TestGeneralityRetirementDerivation::test_unproved_replay_flag_still_refuses_derivation',
            'tests/test_generation_specificity_skill.py::TestGeneralityRetirementDerivation::test_retired_condition_changes_the_derived_domain',
            'tests/test_generation_specificity_skill.py::TestOfflineDraftSurface::test_declared_offline_prompt_is_scanned_without_live_delivery_claim'], runner=packet_runner)
        for variant in ('none', 'explicit', 'conventional'):
            run('final-sg2-' + variant, ['tests/test_wave7_5213_d76_registration.py::test_sg2_root_launch_completes_and_records_registered_paths[' + variant + ']'])
    elif action == 'run':
        run('census-serial-recheck', ['tests/test_native_u3c_round4_helpers.py::test_actual_c_and_overlay_d_graphs_are_accepted'], workers=0)
        run('baseline-legacy-deadlines', [
            'tests/test_native_attribution_results.py::test_actual_completed_recorder_retains_live_file_requirements[hardlink]',
            'tests/test_native_attribution_results.py::test_actual_correction_and_recorder_saved_trace[recorder]'],
            'baseline_native_u1u3_20261108.py')
        run('baseline-schema', ['tests/test_schema'], 'baseline_native_u1u3_20261108.py')
        run('baseline-specificity', ['tests/test_generation_specificity_skill.py'], 'baseline_native_u1u3_20261108.py')
        for label, nodes in json.loads((OUT / 'extra-plan.json').read_text()):
            run(label, nodes)
        parity()
        for variant in ('none', 'explicit', 'conventional'):
            run('final-sg2-' + variant, ['tests/test_wave7_5213_d76_registration.py::test_sg2_root_launch_completes_and_records_registered_paths[' + variant + ']'])
    else:
        raise SystemExit('choose prepare, repair-baseline, run or final')
if __name__ == '__main__':
    main()

