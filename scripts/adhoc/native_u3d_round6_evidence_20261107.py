#!/usr/bin/env python3
"""U3-D round-six offline integration evidence, 2026-11-07.

Inputs: merged D tree, local pinned FAIRSCAPE objects, retained C/D rosters.
Outputs: scratch-native-u3d/round6-* logs and an artifact manifest. The only
dependency population is the empty pinned submodule directory in this tree.
No network, provider, native binary, branch change or GitHub operation.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
BASE = EXEC / 'scratch-native-u3d'
PYTHON = EXEC.parent / 'data-sheets-schema/.venv/bin/python'
PIN = '8c80311d7d8b0fadac07dca9567d632103691f48'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
       'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': ''}
FORBIDDEN_TEST = 'tests/test_native_u3b_reuse.py::test_native_typed_capture_and_receipt_reconstruction_smoke'
D_MODULES = (
    'native_shared_registration', 'native_shared_permissions',
    'native_permission_projection_derivation', 'native_lexical_ancestry',
    'native_subscription_guard', 'native_execution_engine', 'native_shared_gates',
    'native_shared_results', 'native_shared_publication', 'native_shared_live_capture',
    'native_shared_execution', 'native_shared_execution_variant',
    'native_shared_execution_failure', 'native_initial_structure_mode',
    'native_shared_receipt_readers', 'native_shared_provenance',
    'native_shared_saved_pool_bound', 'native_shared_schema_derivation_once',
    'native_receipt_origin_stage_join', 'native_receipt_origin_reporting',
    'native_shared_schema_gates', 'native_shared_record_contract', 'native_shared_render',
    'native_phase_scope_rendering', 'native_u3d_receipt_policy', 'native_u3d_prompt_cli',
    'native_u3d_runner_evidence', 'native_u3d_guard_contract',
)
SAFE_B = tuple('tests/test_native_u3b_reuse.py::' + name for name in (
    'test_supported_bindings', 'test_owner_association_reuses_catalog_through_real_typed_prepare',
    'test_initialization_transition_and_callback_semantics',
    'test_unknown_typed_lookup_cannot_revive_old_entry',
    'test_target_parser_guard_refuses_warm_catalog', 'test_refusal_parity_no_retention'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd, env=ENV, timeout=60)


def hydrate():
    target = ROOT / 'fairscape_models'
    assert target.is_dir() and not target.is_symlink() and not any(target.iterdir())
    assert git('ls-tree', 'HEAD', 'fairscape_models') == f'160000 commit {PIN}\tfairscape_models\n'.encode()
    raw = git('archive', '--format=tar', PIN,
              cwd=EXEC.parent / 'data-sheets-schema/fairscape_models')
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        members = archive.getmembers()
        for member in members:
            path = Path(member.name)
            assert not path.is_absolute() and '..' not in path.parts and '.git' not in path.parts
            assert member.isfile() or member.isdir()
        archive.extractall(target, members=members, filter='data')
    module = target / 'fairscape_models/rocrate.py'
    assert module.is_file() and module.stat().st_size
    save(BASE / 'round6-fairscape.json', {'pin': PIN,
        'archive_sha256': hashlib.sha256(raw).hexdigest(), 'module_sha256': sha(module),
        'target': str(target), 'scope': 'exact pinned local archive; no installer or network'})


def prior_nodes(path):
    args = json.loads(path.read_bytes())['args']
    return [arg for arg in args if arg.startswith('tests/')]


def nodes(mode):
    if mode == 'canary':
        return ['tests/test_native_shared_capture_integration.py::test_complete_observed_typed_sequence_accounts_for_every_stage_and_source']
    if mode == 'reader-canary':
        return ['tests/test_native_shared_receipt_readers.py::test_final_reader_reconstructs_effective_bytes_and_keeps_original_history']
    if mode == 'guard-canary':
        return ['tests/test_native_execution_round3_v2.py::test_package_guard_census_admits_shared_and_u2_dependencies']
    if mode == 'ca':
        return prior_nodes(EXEC / 'native-u3c-r2-final-combined-20261107/pytest-command.json')
    if mode == 'd':
        return [f'tests/test_{name}.py' for name in D_MODULES] + list(SAFE_B)
    if mode == 'compatibility':
        return prior_nodes(BASE / 'round5-regressions/pytest-command.json')
    if mode == 'collection':
        return ['tests']
    raise ValueError(mode)


def run(mode):
    selected = nodes(mode)
    assert FORBIDDEN_TEST not in selected and 'tests/test_native_u3b_reuse.py' not in selected
    for node in selected:
        assert (ROOT / node.split('::', 1)[0]).exists(), node
    command = [str(PYTHON), '-S', '-P', '-B',
        str(ROOT / 'scripts/adhoc/run_native_u3d_tests_20261107.py'),
        '--out', str(BASE / ('round6-' + mode)), '--workers', '0' if mode == 'collection' else '2']
    if mode == 'collection':
        command.append('--collect-only')
    command += selected
    return subprocess.call(command, cwd=ROOT, env=ENV)


def collect():
    result = {'head': git('rev-parse', 'HEAD').decode().strip(),
        'excluded_test': FORBIDDEN_TEST,
        'scope': 'offline tests with isolated project imports; collection is not test execution', 'runs': {}}
    for plan in sorted(BASE.glob('round6-*/plan.json')):
        directory = plan.parent
        doc = json.loads(plan.read_bytes())
        outcome = json.loads((directory / 'outcome.json').read_bytes())
        assert outcome['cleanup_verified'] and outcome['worker']['source_origin_checks_passed']
        for key, file in [('tested_diff_sha256', 'tested.diff'),
                          ('tested_status_sha256', 'tested.status'),
                          ('tested_untracked_sha256', 'tested-untracked.json')]:
            assert doc[key] == sha(directory / file)
        suites = ET.parse(directory / 'pytest.xml').getroot()
        failures = [{'node': case.get('classname') + '::' + case.get('name'),
                     'message': failed.get('message'), 'detail': failed.text}
                    for case in suites.iter('testcase') for failed in case
                    if failed.tag in ('failure', 'error')]
        retained = directory / 'retained'
        for source in sorted((directory / 'cases').rglob('render-digests.json')):
            dest = retained / source.parent.name
            dest.mkdir(parents=True, exist_ok=True)
            for name in ('render-digests.json', 'normalized-receipt-render.json', 'new-instruction.txt'):
                item = source.parent / name
                if item.exists():
                    shutil.copy2(item, dest / name)
                    assert sha(item) == sha(dest / name)
        result['runs'][directory.name] = {
            'source_commit': doc['source_commit'], 'returncode': outcome['returncode'],
            'seconds': outcome['seconds'], 'failures': failures,
            'junit': [dict(item.attrib) for item in suites.iter('testsuite')],
            'artifacts': {name: sha(directory / name) for name in (
                'plan.json', 'outcome.json', 'pytest-command.json', 'pytest.log', 'pytest.xml',
                'tested.diff', 'tested.status', 'tested-untracked.json', 'network.json',
                'origins-before.json', 'origins-after.json', 'subprocess-origins.json')},
            'retained': {str(item.relative_to(directory)): sha(item)
                         for item in retained.rglob('*') if item.is_file()}}
    save(BASE / 'round6-evidence.json', result)
    print(json.dumps({name: {'junit': value['junit'], 'returncode': value['returncode']}
                      for name, value in result['runs'].items()}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('hydrate', 'canary', 'reader-canary', 'guard-canary',
        'ca', 'd', 'compatibility', 'collection', 'collect'))
    mode = parser.parse_args().mode
    assert not os.path.lexists(EXEC / 'plans/native_quiet_window.lock'), 'quiet window active'
    assert git('branch', '--show-current').decode().strip() == 'codex/native-u3d-integration-20261107'
    if mode == 'hydrate':
        hydrate()
    elif mode == 'collect':
        collect()
    else:
        raise SystemExit(run(mode))


if __name__ == '__main__':
    main()
