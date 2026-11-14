#!/usr/bin/env python3
"""Extract D128's finite scanner approval, 2026-11-09 (U3-J2/P3-1).

Input: the SHA-pinned, retained U3-H itemized comparison; never a new scan.
Output: a fresh tests/fixtures/native_d128_approved.json in this checkout.
Standard-library/offline only. Preserve every occurrence and full changed
object, plus hashes of complete ordered arrays and the nine full violations.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
SOURCE = EXEC / 'scratch-native-u1u3/u3h/itemized-scanner-comparison.json'
SOURCE_SHA256 = '98e6d082db4df2176a452ab60bc83280406333ba339a96e30ae501aeb6957ada'
BASELINE = 'cf50d9a1c059f3b5030103378ccef33619475dde'
REFERENCE = '660b2d884c3032f0eca61fcfd3ae523fcbbe9614'
TOOL = 'e0b964b0e182548411045c5f6186b7d4ee64b8ec'
ARRAYS = ('hits', 'violations', 'test_dependencies')


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def source_identity(value):
    source = value['source']
    return {name: source[name] for name in ('commit', 'tree', 'physical_input_mask',
        'committed_roster_sha256', 'physical_inputs_sha256')}


def main():
    if (EXEC / 'plans/native_quiet_window.lock').exists():
        raise RuntimeError('quiet-window lock active')
    if ROOT.name != 'codex-native-u1u3':
        raise RuntimeError('assigned U3-J2 worktree required')
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise RuntimeError('original approved comparison bytes changed')
    data = json.loads(raw)
    before = next(row for row in data['inputs'] if row['label'] == 'saved_main_cf50')
    after = next(row for row in data['inputs'] if row['label'] == 'candidate')
    comparison = next(row for row in data['comparisons']
                      if (row['before'], row['after']) == ('saved_main_cf50', 'candidate'))
    assert before['source']['commit'] == BASELINE and after['source']['commit'] == REFERENCE
    assert before['tool_commit'] == after['tool_commit'] == TOOL
    assert before['tool_assets_sha256'] == after['tool_assets_sha256']
    assert before['derivation_complete'] is after['derivation_complete'] is True
    assert before['arrays']['violations'] == after['arrays']['violations']
    assert len(before['arrays']['violations']) == 9
    hits = comparison['arrays']['hits']
    assert (hits['before_count'], hits['after_count'], hits['exact_match_count'],
            len(hits['relocations']), len(hits['changed_fields']), len(hits['added']),
            len(hits['removed'])) == (5292, 5293, 5229, 57, 6, 1, 0)
    dependencies = comparison['arrays']['test_dependencies']
    assert (dependencies['before_count'], dependencies['after_count'],
            dependencies['exact_match_count'], len(dependencies['added'])) == (101, 103, 101, 2)
    assert not any(dependencies[key] for key in ('relocations', 'changed_fields', 'removed'))
    arrays = {}
    for name in ARRAYS:
        source = comparison['arrays'][name]
        rows = {key: [{k: v for k, v in row.items() if k != 'disposition'} for row in source[key]]
                for key in ('relocations', 'changed_fields', 'removed', 'added')}
        arrays[name] = dict(before_count=source['before_count'], after_count=source['after_count'],
            before_sha256=digest(before['arrays'][name]), after_sha256=digest(after['arrays'][name]),
            exact_matches=[[row['before_index'], row['after_index']] for row in source['exact_matches']],
            **rows)
    result = dict(kind='native_d128_finite_scanner_approval', version=1, decision='D128',
        source_evidence_sha256=SOURCE_SHA256,
        baseline=source_identity(before), reference_candidate=source_identity(after),
        tool_commit=TOOL, tool_assets_sha256=before['tool_assets_sha256'],
        arrays=arrays, exact_violations=before['arrays']['violations'],
        scope='Only the finite approved objects and occurrence mapping. No normalization, '
              'new finding approval, native acceptance, or automatic golden refresh.')
    target = ROOT / 'tests/fixtures/native_d128_approved.json'
    output = (json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    with target.open('xb') as stream:
        stream.write(output)
    assert target.read_bytes() == output
    print(json.dumps(dict(path=str(target), bytes=len(output), sha256=hashlib.sha256(output).hexdigest())))


if __name__ == '__main__':
    main()
