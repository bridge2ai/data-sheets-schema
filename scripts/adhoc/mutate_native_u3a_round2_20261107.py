#!/usr/bin/env python3
"""U3-A r2: one committed offline mutation and its matched control, 2026-11-07.

Inputs: a local reviewed base commit, one of the fifteen reviewer probe intents,
and the physical dependency venv Python. Default is read-only planning. --run
creates a NEW source copy and matched evidence below one round-4 case folder;
it never resets or
cleans an existing tree. The unchanged targeted tests must pass before the
single source mutation is committed and tested. MA is the required first
end-to-end canary; later cases require its saved, successful result. All tests
use the repository's network-denied, source-isolated, <=3600s, serial runner.
No provider/native binary/GitHub/network operations are implemented here.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def execution_root(source_root):
    """Resolve the global quiet window independently of archive depth."""
    candidates = [path for path in source_root.parents if path.name == 'd4d-executions']
    if (len(candidates) != 1 or candidates[0] != candidates[0].resolve(strict=True)
            or not (candidates[0] / 'plans').is_dir()):
        raise RuntimeError('source must be below the canonical d4d-executions root')
    return candidates[0]


EXECUTIONS = execution_root(ROOT)
SCRATCH = EXECUTIONS / 'scratch-native-u3a-r4'
LOCK = EXECUTIONS / 'plans/native_quiet_window.lock'
SOURCE = 'src/data_sheets_schema/native_execution_registration_v2.py'
SELF = 'scripts/adhoc/mutate_native_u3a_round2_20261107.py'
RUNNER = 'scripts/adhoc/run_native_u3a_tests_20261107.py'
REG = 'tests/test_native_execution_registration_v2.py::'
BRIDGE = 'tests/test_native_execution_bridge_v2.py::'
CI = 'tests/test_native_execution_ci_v2.py::'
APPROVAL = REG + 'test_approval_parser_refuses_each_fabricated_authority_mismatch'
JOIN = REG + 'test_execution_prefix_must_match_rederived_preparation_before_consumer'
CASES = {
    'MA': ('guard', '_authorizations', 'v2 review cannot approve its own author', APPROVAL + '[self_review]'),
    'MB': ('guard', '_authorizations', 'v2 review independence must be explicit', APPROVAL + '[not_independent]'),
    'MC': ('guard', '_authorizations', 'v2 CI check source differs from source commit', APPROVAL + '[ci_head]'),
    'MD': ('guard', '_authorizations', 'v2 CI check conclusion must be success', APPROVAL + '[failed_ci]'),
    'ME': ('commit_call', 'verified', '', BRIDGE + 'test_verified_rechecks_committed_sources_after_preparation'),
    'MF': ('guard', '_consumer', 'v2 execution consumer authority version mismatch',
           BRIDGE + 'test_committed_consumer_rejects_wrong_version_or_interface[version]'),
    'MG': ('envelope_call', '_wire', '', BRIDGE + 'test_wire_still_invokes_pinned_envelope_check_after_structural_precheck'),
    'MI': ('guard', '_closed_execution', 'v2 execution gate obligations mismatch', JOIN + '[gates]'),
    'MJ': ('execution_field', 'verified', 'working_directory', JOIN + '[working_directory]'),
    'MK': ('composition_field', 'verified', 'runtime_sha256', JOIN + '[composition_runtime]'),
    'ML': ('guard', 'verified', 'v2 preparation digest mismatch', JOIN + '[preparation_digest]'),
    'MM': ('execution_field', 'verified', 'runtime_declaration_sha256', JOIN + '[runtime_digest]'),
    'MN': ('guard', '_authorizations', 'v2 owner CI hash differs', APPROVAL + '[owner_ci]'),
    'MO': ('guard', '_consumer', 'v2 execution consumer source differs from the committed package closure',
           BRIDGE + 'test_consumer_refuses_changed_source_despite_valid_committed_name'),
    'MP': ('guard', '_authorizations', 'v2 CI workflow map differs from exact reviewed and tested workflow bytes',
           CI + 'test_workflow_identity_and_event_cannot_be_omitted_or_substituted'),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def environment():
    return {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8',
        'GIT_NO_LAZY_FETCH': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
        'GIT_CONFIG_SYSTEM': os.devnull, 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PIP_NO_INDEX': '1', 'UV_OFFLINE': '1'}


def git(root, *args):
    return subprocess.run(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Offline mutation fixture',
        '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', *args],
        cwd=root, env=environment(), capture_output=True, check=True, timeout=120).stdout


def quiet():
    if LOCK.exists():
        raise RuntimeError('quiet-window lock exists; no scratch preparation or tests started')


def mutate(raw, case):
    """One syntax-identified edit; no mutation source is executed here."""
    text = raw.decode('utf-8')
    tree = ast.parse(text)
    mode, function, target, _ = CASES[case]
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function]
    if len(matches) != 1:
        raise ValueError('review changed mutation function: ' + function)
    function_node = matches[0]
    selected = []
    for node in ast.walk(function_node):
        if mode == 'guard' and isinstance(node, ast.If):
            if any(isinstance(statement, ast.Raise) and isinstance(statement.exc, ast.Call)
                   and isinstance(statement.exc.func, ast.Name) and statement.exc.func.id == 'ValueError'
                   and len(statement.exc.args) == 1 and isinstance(statement.exc.args[0], ast.Constant)
                   and statement.exc.args[0].value == target for statement in node.body):
                if node.orelse:
                    raise ValueError('mutation guard now has an else branch; review required')
                selected.append((node, 'pass  # ' + case + ': deliberately removed refusal'))
        elif mode == 'commit_call' and isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            if ast.unparse(node.value.func) == 'authority.require_committed':
                selected.append((node, 'pass  # ME: deliberately skipped committed closure'))
        elif mode == 'envelope_call' and isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'require_envelope':
                selected.append((node, "inner = value['registration']  # MG: skipped pinned wire check"))
        elif mode in ('execution_field', 'composition_field') and isinstance(node, ast.If):
            prefix = 'v2 execution ' if mode == 'execution_field' else 'v2 composition '
            if any(isinstance(item, ast.Raise) and isinstance(item.exc, ast.Call)
                   and any(isinstance(term, ast.Constant) and term.value == prefix
                           for term in ast.walk(item.exc)) for item in node.body):
                expression = ast.get_source_segment(text, node.test)
                selected.append((node.test, f"key != {target!r} and ({expression})"))
    if len(selected) != 1:
        raise ValueError(f'{case} requires exactly one reviewed edit; found {len(selected)}')
    node, replacement = selected[0]
    lines = text.splitlines(keepends=True)
    if not lines[node.lineno - 1][:node.col_offset].isascii():
        raise ValueError('non-ASCII mutation coordinate requires explicit review')
    start = sum(map(len, lines[:node.lineno - 1])) + node.col_offset
    stop = sum(map(len, lines[:node.end_lineno - 1])) + node.end_col_offset
    changed = (text[:start] + replacement + text[stop:]).encode()
    if changed == raw:
        raise ValueError('mutation made no change')
    compile(changed, SOURCE, 'exec', dont_inherit=True)
    return changed, {'line': node.lineno, 'before': text[start:stop], 'after': replacement}


def new_copy(base, directory):
    """Archive into a fresh repo borrowing existing objects read-only."""
    quiet()
    if (directory != directory.absolute() or directory != directory.resolve()
            or directory == SCRATCH or not directory.is_relative_to(SCRATCH)):
        raise ValueError('source archive must be a new canonical round-4 scratch path')
    if any((parent / '.git').exists() for parent in (directory, *directory.parents)
           if parent.is_relative_to(EXECUTIONS)):
        raise ValueError('source archive must not be nested inside another checkout')
    directory.mkdir(mode=0o700, exist_ok=False)
    process = subprocess.Popen(['/usr/bin/git', '--no-replace-objects', 'archive', '--format=tar', base],
        cwd=ROOT, env=environment(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
            for item in archive:
                if item.name == '.git' or item.name.startswith('.git/'):
                    raise ValueError('archive may not supply repository metadata')
                archive.extract(item, directory, filter='data')
        if process.wait(timeout=120) != 0:
            raise RuntimeError('local source archive failed: ' + process.stderr.read().decode())
    finally:
        if process.poll() is None:
            process.kill(); process.wait(timeout=10)
        process.stdout.close(); process.stderr.close()
    git(directory, 'init', '-q', '-b', 'native-u3a-round2-mutant')
    objects = git(ROOT, 'rev-parse', '--path-format=absolute', '--git-path', 'objects').decode().strip()
    if '\n' in objects or not Path(objects).is_dir():
        raise ValueError('invalid local source object directory')
    (directory / '.git/objects/info/alternates').write_text(objects + '\n')
    git(directory, 'update-ref', 'HEAD', base)
    git(directory, 'read-tree', base)
    if git(directory, 'status', '--porcelain'):
        raise RuntimeError('fresh source archive is not byte-identical to base')


def run_tests(tree, out, python, node):
    quiet()
    command = [str(python), '-S', '-P', '-B', str(tree / RUNNER),
               '--out', str(out), '--workers', '0', node]
    process = subprocess.run(command, cwd=tree, env=environment(), capture_output=True, text=True)
    # The committed runner owns the 3600s limit, lock cooperation and descendant
    # cleanup. A pytest exit alone never establishes valid mutation evidence.
    outcome = json.loads((out / 'outcome.json').read_bytes())
    network = json.loads((out / 'network.json').read_bytes())
    worker = outcome.get('worker') or {}
    if (not outcome.get('cleanup_verified') or not worker.get('source_origin_checks_passed')
            or network.get('network_bind_denied') is not True
            or process.returncode != outcome.get('returncode')):
        raise RuntimeError('invalid source/network/cleanup witness for ' + str(out))
    for filename in ('origins-before.json', 'origins-after.json', 'subprocess-origins.json'):
        if not (out / filename).is_file():
            raise RuntimeError('missing source witness ' + filename)
    cases = list(ET.parse(out / 'pytest.xml').getroot().iter('testcase'))
    totals = {'tests': len(cases),
        'failures': sum(item.find('failure') is not None for item in cases),
        'errors': sum(item.find('error') is not None for item in cases),
        'skipped': sum(item.find('skipped') is not None for item in cases)}
    if not cases or totals['errors'] or totals['skipped'] == totals['tests']:
        raise RuntimeError('collection/setup/empty selection is not a mutation result')
    return {'returncode': process.returncode, **totals,
        'outcome_sha256': sha((out / 'outcome.json').read_bytes()),
        'junit_sha256': sha((out / 'pytest.xml').read_bytes()), 'evidence': str(out)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--case', choices=tuple(CASES), required=True)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--python', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--canary', type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.base):
        parser.error('--base must be the full local reviewed commit SHA')
    base = git(ROOT, 'rev-parse', args.base + '^{commit}').decode().strip()
    raw = git(ROOT, 'show', base + ':' + SOURCE)
    changed, edit = mutate(raw, args.case)
    plan = {'case': args.case, 'base': base, 'source': SOURCE, 'source_sha256': sha(raw),
        'mutated_source_sha256': sha(changed), 'edit': edit, 'test_node': CASES[args.case][3],
        'harness_sha256': sha(Path(__file__).read_bytes()),
        'scratch_root': str(SCRATCH), 'quiet_window_lock': str(LOCK),
        'scope': 'guard regression evidence; synthetic software tests, not native admission'}
    if not args.run:
        print(json.dumps(plan, sort_keys=True)); return 0
    if args.out is None or args.python is None:
        parser.error('--run requires --out and --python')
    if git(ROOT, 'show', base + ':' + SELF) != Path(__file__).read_bytes():
        raise ValueError('commit the exact harness with the reviewed baseline before running')
    if args.case != 'MA':
        if args.canary is None:
            raise ValueError('run MA end to end first; provide its --canary result.json')
        canary_path = args.canary.absolute()
        if canary_path != canary_path.resolve() or not canary_path.is_relative_to(SCRATCH):
            raise ValueError('canary must be this round-4 campaign\'s canonical saved evidence')
        canary = json.loads(args.canary.read_bytes())
        if (canary.get('case') != 'MA' or canary.get('status') != 'killed'
                or canary.get('base') != base or canary.get('harness_sha256') != plan['harness_sha256']):
            raise ValueError('canary does not prove this exact baseline and harness')
    out = args.out.absolute()
    if (out == SCRATCH or not out.is_relative_to(SCRATCH) or out != out.resolve()
            or not re.fullmatch(r'[A-Za-z0-9_-]+', out.name)):
        raise ValueError('output must be a fresh literal case folder under scratch-native-u3a-r4')
    if any((parent / '.git').exists() for parent in (out, *out.parents)
           if parent.is_relative_to(EXECUTIONS)):
        raise ValueError('mutation evidence must be outside every source checkout')
    tree = out / 'source'
    quiet(); out.mkdir(mode=0o700, exist_ok=False)
    save(out / 'plan.json', plan)
    new_copy(base, tree)
    baseline = run_tests(tree, out / 'baseline', args.python, plan['test_node'])
    result = {**plan, 'tree': str(tree), 'baseline': baseline}
    if baseline['returncode'] != 0 or baseline['failures']:
        result['status'] = 'invalid_baseline'
        save(out / 'result.json', result)
        print(json.dumps({'case': args.case, 'status': result['status']})); return 2
    quiet()
    (tree / SOURCE).write_bytes(changed)
    git(tree, 'add', '--', SOURCE)
    git(tree, 'commit', '-qm', 'Synthetic U3-A round2 mutation ' + args.case)
    result['mutant_commit'] = git(tree, 'rev-parse', 'HEAD').decode().strip()
    if git(tree, 'status', '--porcelain') or git(tree, 'show', 'HEAD:' + SOURCE) != changed:
        raise RuntimeError('mutation must be the exact committed, clean source closure')
    tested = run_tests(tree, out / 'mutant', args.python, plan['test_node'])
    result['mutant'] = tested
    result['status'] = ('killed' if tested['returncode'] == 1 and tested['failures']
                        else 'survived' if tested['returncode'] == 0 else 'invalid_run')
    save(out / 'result.json', result)
    print(json.dumps({'case': args.case, 'status': result['status'],
                      'mutant_commit': result['mutant_commit'], 'result': str(out / 'result.json')}))
    return 0 if result['status'] == 'killed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
