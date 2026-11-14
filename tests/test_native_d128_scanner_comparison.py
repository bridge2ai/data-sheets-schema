"""D128's finite generation-specificity-audit comparison, not a count waiver.

The fixture comes only from the approved U3-H evidence. New source heads must
reproduce those exact ordered arrays and occurrence mappings. A new difference
requires review; this test never updates its expectations from a new scan.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.adhoc import native_u5_inputs_20261108 as inputs
from tests.test_native_u5_scanner_comparison import require_scanner_inventory


FIXTURE = Path(__file__).with_name('fixtures') / 'native_d128_approved.json'
FIXTURE_SHA256 = '65330131940ca8be1cd4288ed3cca9ca980eafc665faa964fa443e8f44d63399'
EVIDENCE_SHA256 = '98e6d082db4df2176a452ab60bc83280406333ba339a96e30ae501aeb6957ada'
BASELINE = 'cf50d9a1c059f3b5030103378ccef33619475dde'
REFERENCE_CANDIDATE = '660b2d884c3032f0eca61fcfd3ae523fcbbe9614'
SKILL = '.claude/skills/d4d-generation-specificity-audit'
ARRAYS = ('hits', 'violations', 'test_dependencies')


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def approval():
    raw = FIXTURE.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256, 'D128 approval fixture changed')
    value = json.loads(raw)
    require(value['decision'] == 'D128' and value['version'] == 1
            and value['source_evidence_sha256'] == EVIDENCE_SHA256
            and value['baseline']['commit'] == BASELINE
            and value['reference_candidate']['commit'] == REFERENCE_CANDIDATE,
            'D128 source approval identity differs')
    return value


def complete_arrays(run):
    require(run.get('returncode') in (0, 1) and run.get('derivation_complete') is True,
            'D128 requires complete scanner derivation; absent arrays are not zero findings')
    arrays = run.get('arrays')
    require(type(arrays) is dict and set(arrays) == set(ARRAYS)
            and all(type(arrays[name]) is list and all(type(row) is dict for row in arrays[name])
                    for name in ARRAYS), 'D128 requires all complete finding arrays')
    return arrays


def require_approved_arrays(before, after, approved):
    """Check complete arrays and finite full-object mappings; never normalize.

    Canonical hashes retain list order, duplicate occurrences and JSON types.
    Occurrence accounting then checks the approved explanation of each array.
    Neither matching counts nor a set comparison is sufficient.
    """
    require(set(before) == set(after) == set(ARRAYS), 'D128 array roster differs')
    for name in ARRAYS:
        old, new, ledger = before[name], after[name], approved['arrays'][name]
        require(type(old) is list and type(new) is list, name + ': arrays must be lists')
        require(len(old) == ledger['before_count'] and len(new) == ledger['after_count'],
                name + ': complete array count differs')
        require(digest(old) == ledger['before_sha256'] and digest(new) == ledger['after_sha256'],
                name + ': complete ordered objects differ from D128 approval')
        before_indices, after_indices = [], []

        def index(value, bound):
            require(type(value) is int and 0 <= value < bound, name + ': invalid occurrence index')
            return value

        for pair in ledger['exact_matches']:
            require(type(pair) is list and len(pair) == 2, name + ': malformed exact pair')
            i, j = index(pair[0], len(old)), index(pair[1], len(new))
            require(encoded(old[i]) == encoded(new[j]), name + ': exact pair changed')
            before_indices.append(i)
            after_indices.append(j)
        for kind in ('relocations', 'changed_fields'):
            for row in ledger[kind]:
                i, j = index(row['before_index'], len(old)), index(row['after_index'], len(new))
                require(encoded(old[i]) == encoded(row['before'])
                        and encoded(new[j]) == encoded(row['after']),
                        name + ': approved changed object differs')
                fields = sorted(key for key in set(old[i]) | set(new[j])
                                if (key in old[i]) != (key in new[j])
                                or encoded(old[i].get(key)) != encoded(new[j].get(key)))
                require(fields == row['differing_fields'], name + ': changed-field account differs')
                if kind == 'relocations':
                    require(fields == ['line'], name + ': relocation changed more than its line')
                before_indices.append(i)
                after_indices.append(j)
        for row in ledger['removed']:
            i = index(row['before_index'], len(old))
            require(encoded(old[i]) == encoded(row['before']), name + ': removed object differs')
            before_indices.append(i)
        for row in ledger['added']:
            j = index(row['after_index'], len(new))
            require(encoded(new[j]) == encoded(row['after']), name + ': added object differs')
            after_indices.append(j)
        require(sorted(before_indices) == list(range(len(old)))
                and sorted(after_indices) == list(range(len(new))),
                name + ': duplicate, missing or extra occurrence accounting')
    violations = approved['exact_violations']
    require(len(violations) == 9 and encoded(before['violations']) == encoded(violations)
            and encoded(after['violations']) == encoded(violations),
            'D128 requires the exact ordered nine violation objects')


def scan(source, manifest, tool, assets, output):
    output.mkdir()
    env = {key: os.environ[key] for key in ('PATH', 'HOME', 'TMPDIR', 'VIRTUAL_ENV') if key in os.environ}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', PIP_NO_INDEX='1', UV_OFFLINE='1')
    command = [sys.executable, '-P', '-B', str(tool), '--root', str(source),
               '--report', str(output / 'scan.md'), '--json', str(output / 'scan.json'),
               '--tokens', str(tool.with_name('tokens.yaml')),
               '--exceptions', str(tool.with_name('exceptions.yaml')), '--full-json']
    result = subprocess.run(command, cwd=source, env=env, capture_output=True, timeout=600)
    (output / 'stdout.txt').write_bytes(result.stdout)
    (output / 'stderr.txt').write_bytes(result.stderr)
    arrays = None
    if result.returncode in (0, 1):
        document = json.loads((output / 'scan.json').read_bytes())
        arrays = {name: document[name] for name in ARRAYS}
    row = dict(returncode=result.returncode, derivation_complete=arrays is not None,
               arrays=arrays, commit=manifest['commit'], commit_tree=manifest['commit_tree'],
               input_mask=manifest['path_mask'], entry_count=manifest['entry_count'],
               total_blob_bytes=manifest['total_blob_bytes'], tool_assets_sha256=assets,
               stderr=result.stderr.decode(errors='replace'))
    (output / 'run.json').write_text(json.dumps(row, indent=2, sort_keys=True) + '\n')
    return row


def test_d128_final_composition_has_only_the_finite_approved_scanner_differences(tmp_path, monkeypatch):
    approved = approval()
    candidate_head = inputs.git('rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
    exports = tmp_path / 'exports'
    exports.mkdir()
    monkeypatch.setattr(inputs, 'SCRATCH', exports)
    selected = {}
    # checked_scanner_input admits immutable scanner-candidate labels for any
    # full SHA; the old historical-baseline label and BASE constant stay intact.
    for name, commit in (('before', BASELINE), ('after', candidate_head)):
        label = 'scanner-candidate-' + commit[:9]
        inputs.materialize(label, commit, inputs.BASE_SCAN_PATHS)
        tree, manifest = inputs.checked_scanner_input(label, commit)
        require_scanner_inventory(manifest)
        selected[name] = (tree, manifest, label)
    require(selected['before'][1]['commit_tree'] == approved['baseline']['tree'],
            'D128 saved-main tree differs')
    require(selected['before'][1]['path_mask'] == approved['baseline']['physical_input_mask']
            == approved['reference_candidate']['physical_input_mask'], 'D128 comparison scope differs')
    candidate = selected['after'][0]
    tool = candidate / SKILL / 'scan.py'
    names = inputs.git('ls-tree', '-r', '--name-only', candidate_head, '--', SKILL).decode().splitlines()
    assets = {name: hashlib.sha256((candidate / name).read_bytes()).hexdigest() for name in names}
    require(assets == approved['tool_assets_sha256'], 'D128 requires the exact approved scanner assets')
    evidence = dict(decision='D128', baseline=BASELINE, candidate=candidate_head,
                    approved_reference_candidate=REFERENCE_CANDIDATE,
                    approval_fixture_sha256=FIXTURE_SHA256, runs={}, status='incomplete')
    try:
        arrays = {}
        for name in ('before', 'after'):
            source, manifest, _ = selected[name]
            run = scan(source, manifest, tool, assets, tmp_path / name)
            evidence['runs'][name] = {key: value for key, value in run.items() if key != 'arrays'}
            arrays[name] = complete_arrays(run)
        require_approved_arrays(arrays['before'], arrays['after'], approved)
        for source, manifest, label in selected.values():
            inputs.checked_scanner_input(label, manifest['commit'])
        require(inputs.git('rev-parse', '--verify', 'HEAD^{commit}').decode().strip() == candidate_head,
                'D128 candidate HEAD moved')
        require({name: hashlib.sha256((candidate / name).read_bytes()).hexdigest() for name in names}
                == assets, 'D128 scanner assets changed')
        evidence['status'] = 'finite_approved_comparison_passed_no_other_differences'
    except Exception as exc:
        evidence['failure'] = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        (tmp_path / 'd128-comparison.json').write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')


def test_d128_approval_fixture_retains_the_exact_owner_disposition():
    value = approval()
    hits, dependencies = value['arrays']['hits'], value['arrays']['test_dependencies']
    assert (hits['before_count'], hits['after_count'], len(hits['exact_matches']),
            len(hits['relocations']), len(hits['changed_fields']), len(hits['added']),
            len(hits['removed'])) == (5292, 5293, 5229, 57, 6, 1, 0)
    assert (dependencies['before_count'], dependencies['after_count'], len(dependencies['exact_matches']),
            len(dependencies['added'])) == (101, 103, 101, 2)
    assert not any(dependencies[key] for key in ('relocations', 'changed_fields', 'removed'))
    assert len(value['exact_violations']) == 9


def toy_comparison():
    """Invented small controls for the validator, never D128 source evidence."""
    a = dict(path='a.py', line=1, snippet='neutral', role='old')
    b = dict(path='b.py', line=8, snippet='neutral', role='old')
    old = dict(hits=[a, deepcopy(a), b],
               violations=[dict(path=str(i) + '.py', line=i + 1, violation=True) for i in range(9)],
               test_dependencies=[dict(path='test_unit.py', line=1)])
    new = dict(hits=[deepcopy(a), dict(a, line=2), dict(b, role='new'), dict(path='new.py', line=4)],
               violations=deepcopy(old['violations']),
               test_dependencies=[deepcopy(old['test_dependencies'][0]), dict(path='test_extra.py', line=2)])
    ledgers = {}
    for name in ARRAYS:
        ledgers[name] = dict(before_count=len(old[name]), after_count=len(new[name]),
            before_sha256=digest(old[name]), after_sha256=digest(new[name]),
            exact_matches=[[i, i] for i in range(len(old[name]))],
            relocations=[], changed_fields=[], removed=[], added=[])
    hits = ledgers['hits']
    hits.update(exact_matches=[[0, 0]],
        relocations=[dict(before_index=1, after_index=1, before=deepcopy(old['hits'][1]),
                          after=deepcopy(new['hits'][1]), differing_fields=['line'])],
        changed_fields=[dict(before_index=2, after_index=2, before=deepcopy(old['hits'][2]),
                             after=deepcopy(new['hits'][2]), differing_fields=['role'])],
        added=[dict(after_index=3, after=deepcopy(new['hits'][3]))])
    ledgers['test_dependencies']['added'] = [dict(after_index=1, after=deepcopy(new['test_dependencies'][1]))]
    return old, new, dict(arrays=ledgers, exact_violations=deepcopy(old['violations']))


def test_d128_finite_validator_accepts_complete_occurrence_accounting():
    require_approved_arrays(*toy_comparison())


@pytest.mark.parametrize('change', ['extra_hit', 'missing_hit', 'duplicate_hit', 'hit_order',
    'line', 'field', 'extra_field', 'bool_line', 'violation', 'violation_order',
    'extra_violation', 'missing_violation', 'test_dependency', 'test_dependency_order',
    'missing_dependency', 'extra_dependency', 'baseline', 'duplicate_accounting',
    'missing_accounting', 'changed_approved_object'])
def test_d128_finite_validator_refuses_unapproved_changes(change):
    old, new, approved = toy_comparison()
    if change == 'extra_hit': new['hits'].append(dict(path='unapproved.py', line=1))
    elif change == 'missing_hit': new['hits'].pop(0)
    elif change == 'duplicate_hit': new['hits'].append(deepcopy(new['hits'][0]))
    elif change == 'hit_order': new['hits'][0], new['hits'][2] = new['hits'][2], new['hits'][0]
    elif change == 'line': new['hits'][1]['line'] = 3
    elif change == 'field': new['hits'][2]['role'] = 'unapproved'
    elif change == 'extra_field': new['hits'][0]['unexpected'] = True
    elif change == 'bool_line': new['hits'][0]['line'] = True
    elif change == 'violation': new['violations'][0]['violation'] = False
    elif change == 'violation_order': new['violations'].reverse()
    elif change == 'extra_violation': new['violations'].append(deepcopy(new['violations'][0]))
    elif change == 'missing_violation': new['violations'].pop()
    elif change == 'test_dependency': new['test_dependencies'][0]['line'] = 2
    elif change == 'test_dependency_order': new['test_dependencies'].reverse()
    elif change == 'missing_dependency': new['test_dependencies'].pop()
    elif change == 'extra_dependency': new['test_dependencies'].append(dict(path='extra.py', line=1))
    elif change == 'baseline': old['hits'][0]['line'] = 2
    elif change == 'duplicate_accounting': approved['arrays']['hits']['exact_matches'].append([0, 0])
    elif change == 'missing_accounting': approved['arrays']['hits']['exact_matches'] = []
    else: approved['arrays']['hits']['relocations'][0]['after']['line'] = 3
    with pytest.raises(ValueError):
        require_approved_arrays(old, new, approved)


@pytest.mark.parametrize('change', ['exit_two', 'not_complete', 'missing_arrays', 'missing_array', 'wrong_shape'])
def test_d128_incomplete_scan_never_becomes_empty_acceptance(change):
    old, _, _ = toy_comparison()
    run = dict(returncode=1, derivation_complete=True, arrays=old)
    if change == 'exit_two': run['returncode'] = 2
    elif change == 'not_complete': run['derivation_complete'] = False
    elif change == 'missing_arrays': run['arrays'] = None
    elif change == 'missing_array': run['arrays'].pop('test_dependencies')
    else: run['arrays']['hits'] = {}
    with pytest.raises(ValueError, match='complete'):
        complete_arrays(run)
