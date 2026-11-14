#!/usr/bin/env python3
"""Compare retained U3-L scanner runs without changing D128, 2026-11-09.

Purpose: U3J2-10 instrument evidence and D128's mandatory new-difference stop.
Inputs: --before-main, --after-main and --candidate are physical absolute run
directories under scratch-native-u1u3. Each uses the unchanged U3-H run.json
interface: source_commit, tool_commit, command (--root, --json scanner.json,
--full-json), exit_code, seconds, process_group_gone, tool_unchanged,
tool_assets_unchanged, tool_sha256, tool_assets_sha256, scanner_json_sha256.
The first source must be saved main cf50 with the U3-K 2c6537d0f instrument;
the second uses the same immutable source with the new committed instrument;
the candidate uses that same new instrument on a clean private composition.
All four exact D127 postimages must be present in the candidate. U3-H load_run
and source_inputs recheck complete physical inputs, ignored extras, source Git
identity, the committed scanner asset roster and persisted full output arrays.

Output: --out is a fresh .json file below scratch-native-u1u3/u3l. It retains
all five full ordered array sets (three runs and two frozen D128 inputs), full
occurrence ledgers, positional differences, tool changes and strict hashes.
Optional --markdown writes a fresh adjacent .md index into that JSON. No scan,
source import, source write, network, golden refresh or gate waiver occurs.
--self-check --out PATH exercises tiny invented duplicate/type/order arrays
only; it neither loads source runs nor qualifies any scanner or native path.

Exit 0: diagnostic finished with exact approved arrays and scanner assets, or
the explicitly labelled invented self-check passed. Exit 1: new array changes
or changed scanner assets. Exit 2: evidence validation failed/incomplete.
No exit value means the independently run, unchanged D128 pytest gate passed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1u3'
OUT_ROOT = SCRATCH / 'u3l'
MAIN = 'cf50d9a1c059f3b5030103378ccef33619475dde'
OLD_TOOL = '2c6537d0f84b6ac562887bd67bd564bd1f6c312e'
REFERENCE = '660b2d884c3032f0eca61fcfd3ae523fcbbe9614'
EVIDENCE = SCRATCH / 'u3h/itemized-scanner-comparison.json'
EVIDENCE_SHA = '98e6d082db4df2176a452ab60bc83280406333ba339a96e30ae501aeb6957ada'
FIXTURE = ROOT / 'tests/fixtures/native_d128_approved.json'
FIXTURE_SHA = '65330131940ca8be1cd4288ed3cca9ca980eafc665faa964fa443e8f44d63399'
READER_SHA = '815548c7dde99692d9dec8bca390103f1d58e36319b729e741d5097973c09c5c'
GATE = 'tests/test_native_d128_scanner_comparison.py'
ARRAYS = ('hits', 'violations', 'test_dependencies')
D127 = {
    'src/data_sheets_schema/shared_generation.py': '2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781',
    'src/data_sheets_schema/api_runner.py': '3e8b7e5d3cc13c5ebc508e33f865e9ac484056fde16126118719d740656a4fb7',
    'src/download/prompts/canonical_hashes.yaml': '543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252',
    'tests/utils/run_spec_boundary_contracts.json': 'b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce',
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_digest(value):
    return sha(encoded(value))


def same(left, right):
    return encoded(left) == encoded(right)


def fields(before, after):
    return sorted(key for key in set(before) | set(after)
                  if (key in before) != (key in after)
                  or not same(before.get(key), after.get(key)))


def diff_array(before, after):
    """Account for each occurrence once, using type-sensitive JSON equality."""
    need(type(before) is list and type(after) is list
         and all(type(row) is dict for row in before + after), 'finding arrays must contain objects')
    remaining_before, remaining_after = set(range(len(before))), set(range(len(after)))

    def pair(key):
        available = defaultdict(deque)
        for j in sorted(remaining_after):
            available[key(after[j])].append(j)
        pairs = []
        for i in sorted(remaining_before):
            available_matches = available[key(before[i])]
            if available_matches:
                pairs.append((i, available_matches.popleft()))
        for i, j in pairs:
            remaining_before.remove(i)
            remaining_after.remove(j)
        return pairs

    exact = pair(encoded)
    relocations = pair(lambda row: encoded({k: v for k, v in row.items() if k != 'line'}))
    # A presentation anchor only: it does not approve or normalize any field.
    anchors = ('path', 'category', 'pattern', 'match', 'context', 'snippet')
    changed = pair(lambda row: encoded({k: row[k] for k in anchors if k in row}))

    def record(indices, kind):
        i, j = indices
        return dict(before_index=i, after_index=j, before=before[i], after=after[j],
                    differing_fields=fields(before[i], after[j]), disposition=kind)

    relocated = [record(indices, 'coordinate_change_requires_review') for indices in relocations]
    need(all(row['differing_fields'] == ['line'] for row in relocated),
         'a relocation changed more than its line')
    semantic = [record(indices, 'field_change_requires_review') for indices in changed]
    removed = [dict(before_index=i, before=before[i], disposition='removal_requires_review')
               for i in sorted(remaining_before)]
    added = [dict(after_index=j, after=after[j], disposition='addition_requires_review')
             for j in sorted(remaining_after)]
    before_indices = [i for i, _ in exact + relocations + changed] + sorted(remaining_before)
    after_indices = [j for _, j in exact + relocations + changed] + sorted(remaining_after)
    need(sorted(before_indices) == list(range(len(before)))
         and sorted(after_indices) == list(range(len(after))), 'occurrence conservation failed')
    # Full positional records expose every ordered-array difference, including
    # a pure permutation that the occurrence pairing would otherwise hide.
    positional = []
    for index in range(max(len(before), len(after))):
        old_present, new_present = index < len(before), index < len(after)
        if old_present and new_present and same(before[index], after[index]):
            continue
        row = dict(index=index, before_present=old_present, after_present=new_present)
        if old_present:
            row['before'] = before[index]
        if new_present:
            row['after'] = after[index]
        if old_present and new_present:
            row['differing_fields'] = fields(before[index], after[index])
        positional.append(row)
    equal = same(before, after)
    return dict(before_count=len(before), after_count=len(after),
                before_sha256=strict_digest(before), after_sha256=strict_digest(after),
                exact_arrays_equal=equal,
                exact_matches=[dict(before_index=i, after_index=j) for i, j in exact],
                exact_match_count=len(exact), relocations=relocated, changed_fields=semantic,
                removed=removed, added=added, positional_differences=positional,
                only_order_changed=(not equal and not relocated and not semantic and not removed and not added),
                occurrence_conservation=True)


def compare(label, before, after):
    need(set(before) == set(after) == set(ARRAYS), label + ': incomplete array roster')
    arrays = {name: diff_array(before[name], after[name]) for name in ARRAYS}
    return dict(label=label, exact_arrays_equal=all(row['exact_arrays_equal'] for row in arrays.values()),
                arrays=arrays)


def reader():
    path = ROOT / 'scripts/adhoc/compare_native_u3h_scanners_20261109.py'
    need(path.resolve(strict=True) == path and sha(path.read_bytes()) == READER_SHA,
         'reviewed U3-H comparison helper changed')
    spec = importlib.util.spec_from_file_location('u3l_retained_h_comparator', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, dict(path=str(path), sha256=sha(path.read_bytes()))


def pinned_json(path, expected):
    need(path.resolve(strict=True) == path and path.is_file() and not path.is_symlink(),
         'pinned evidence is not a physical file: ' + str(path))
    raw = path.read_bytes()
    need(sha(raw) == expected, 'pinned evidence changed: ' + str(path))
    return json.loads(raw)


def frozen_approval():
    approved = pinned_json(FIXTURE, FIXTURE_SHA)
    evidence = pinned_json(EVIDENCE, EVIDENCE_SHA)
    need(approved['decision'] == 'D128' and type(approved['version']) is int
         and approved['version'] == 1 and approved['source_evidence_sha256'] == EVIDENCE_SHA
         and approved['baseline']['commit'] == MAIN
         and approved['reference_candidate']['commit'] == REFERENCE, 'frozen D128 identity differs')
    selected = {}
    for key, label, commit, prefix in (
            ('baseline', 'saved_main_cf50', MAIN, 'before'),
            ('reference_candidate', 'candidate', REFERENCE, 'after')):
        rows = [row for row in evidence['inputs'] if row['label'] == label]
        need(len(rows) == 1, 'frozen evidence input is not unique: ' + label)
        row = rows[0]
        need(row['derivation_complete'] is True and row['source']['commit'] == commit
             and same(row['tool_assets_sha256'], approved['tool_assets_sha256']),
             'frozen complete input identity differs: ' + label)
        need(set(row['arrays']) == set(ARRAYS), 'frozen input array roster differs')
        for name in ARRAYS:
            need(strict_digest(row['arrays'][name]) == approved['arrays'][name][prefix + '_sha256']
                 and len(row['arrays'][name]) == approved['arrays'][name][prefix + '_count'],
                 'frozen full-array approval differs: ' + label + '/' + name)
        need(same(row['arrays']['violations'], approved['exact_violations'])
             and len(row['arrays']['violations']) == 9, 'frozen exact-nine objects differ')
        selected[key] = row
    return approved, selected


def read_run(h, label, directory, *, source=None, tool=None):
    directory = h.physical(directory)
    metadata, _ = h.read_json(h.physical(directory / 'run.json'))
    for name in ('source_commit', 'tool_commit'):
        need(type(metadata.get(name)) is str
             and re.fullmatch('[0-9a-f]{40}', metadata[name]) is not None,
             label + ': full commit identity missing: ' + name)
    if source is not None:
        need(metadata['source_commit'] == source, label + ': wrong source commit')
    if tool is not None:
        need(metadata['tool_commit'] == tool, label + ': wrong tool commit')
    run = h.load_run(label, directory, metadata['source_commit'], metadata['tool_commit'])
    need(run['derivation_complete'] is True, label + ': incomplete derivation is not zero findings')
    run['ordered_arrays_sha256'] = {name: strict_digest(run['arrays'][name]) for name in ARRAYS}
    return run


def asset_delta(before, after):
    rows = []
    for path in sorted(set(before) | set(after)):
        if path in before and path in after and same(before[path], after[path]):
            continue
        row = dict(path=path, before_present=path in before, after_present=path in after)
        if path in before:
            row['before_sha256'] = before[path]
        if path in after:
            row['after_sha256'] = after[path]
        rows.append(row)
    return rows


def diagnostic(args, result):
    h, helper = reader()
    h.quiet()
    approved, frozen = frozen_approval()
    result.update(retained_reader=helper,
                  approval=dict(fixture_path=str(FIXTURE), fixture_sha256=FIXTURE_SHA,
                                source_evidence_path=str(EVIDENCE), source_evidence_sha256=EVIDENCE_SHA,
                                frozen_fixture=approved), frozen_inputs=frozen)
    runs = result['runs'] = {}
    runs['before_main'] = read_run(h, 'before_main', args.before_main, source=MAIN, tool=OLD_TOOL)
    runs['after_main'] = read_run(h, 'after_main', args.after_main, source=MAIN)
    new_tool = runs['after_main']['tool_commit']
    need(new_tool != OLD_TOOL, 'instrument comparison requires a new committed tool')
    runs['candidate'] = read_run(h, 'candidate', args.candidate, tool=new_tool)
    need(same(runs['before_main']['source'], runs['after_main']['source']),
         'old/new instrument source inventories differ on saved main')
    need(same(runs['before_main']['tool_assets_sha256'], approved['tool_assets_sha256']),
         'U3-K old instrument differs from frozen D128 assets')
    need(same(runs['after_main']['tool_assets_sha256'], runs['candidate']['tool_assets_sha256']),
         'new main and candidate do not use identical complete scanner assets')
    for key in runs:
        need(same(runs[key]['source']['physical_input_mask'], approved['baseline']['physical_input_mask']),
             key + ': physical comparison scope differs')
    candidate_root = Path(runs['candidate']['source_root'])
    postimages = {name: sha((candidate_root / name).read_bytes()) for name in D127}
    need(same(postimages, D127), 'candidate is missing exact approved D127 postimages')
    result['candidate_d127_postimages_sha256'] = postimages
    gate_bytes = h.git('show', OLD_TOOL + ':' + GATE)
    need((ROOT / GATE).read_bytes() == gate_bytes
         and (candidate_root / GATE).read_bytes() == gate_bytes,
         'unchanged D128 pytest gate source differs from U3-K')
    result['unchanged_d128_gate'] = dict(path=GATE, sha256=sha(gate_bytes), source_commit=OLD_TOOL)
    comparisons = result['comparisons'] = []

    def add(label, old, new):
        row = compare(label, old['arrays'], new['arrays'])
        comparisons.append(row)
        return row

    add('saved_main_instrument_before_after', runs['before_main'], runs['after_main'])
    add('new_instrument_saved_main_vs_integrated_candidate', runs['after_main'], runs['candidate'])
    checks = [
        add('frozen_approved_main_vs_old_instrument_main', frozen['baseline'], runs['before_main']),
        add('frozen_approved_main_vs_new_instrument_main', frozen['baseline'], runs['after_main']),
        add('frozen_approved_candidate_vs_new_integrated_candidate', frozen['reference_candidate'], runs['candidate']),
    ]
    unapproved = [dict(comparison=row['label'], array=name,
                       ledger_json_pointer='/comparisons/' + str(comparisons.index(row)) + '/arrays/' + name,
                       before_sha256=ledger['before_sha256'], after_sha256=ledger['after_sha256'],
                       before_count=ledger['before_count'], after_count=ledger['after_count'],
                       positional_difference_count=len(ledger['positional_differences']),
                       only_order_changed=ledger['only_order_changed'])
                  for row in checks for name, ledger in row['arrays'].items()
                  if not ledger['exact_arrays_equal']]
    changes = asset_delta(approved['tool_assets_sha256'], runs['after_main']['tool_assets_sha256'])
    result.update(unapproved_arrays=unapproved, mandatory_stop=bool(unapproved),
                  approved_arrays_match=not unapproved, tool_asset_delta=changes,
                  strict_d128_assets_match=not changes, d128_gate_passed=False,
                  d128_gate_status=('unchanged_gate_not_executed_by_this_diagnostic' if not changes else
                                    'unchanged_gate_asset_pin_rejects_new_instrument_before_array_comparison'),
                  status=('mandatory_stop_new_unapproved_differences' if unapproved else
                          'diagnostic_only_arrays_match_but_strict_asset_pin_differs' if changes else
                          'diagnostic_only_finite_arrays_and_assets_match'))
    # Recheck evidence and live inputs after comparison, not only before it.
    frozen_approval()
    for key, directory in (('before_main', args.before_main), ('after_main', args.after_main),
                           ('candidate', args.candidate)):
        checked = read_run(h, key, directory, source=runs[key]['source']['commit'],
                           tool=runs[key]['tool_commit'])
        need(same(checked, runs[key]), key + ': retained evidence changed during comparison')
    need(sha(Path(helper['path']).read_bytes()) == helper['sha256'], 'retained comparison helper changed')
    h.quiet()
    return 1 if unapproved or changes else 0


def self_check():
    a = dict(path='a.py', line=1, category='invented', match='x', snippet='x')
    b = dict(path='b.py', line=2, category='invented', match='y', snippet='y')
    old = [deepcopy(a), deepcopy(a), deepcopy(b), dict(path='gone.py')]
    new = [deepcopy(a), dict(a, line=3), dict(b, role='changed'), dict(path='new.py')]
    ledger = diff_array(old, new)
    need(ledger['exact_matches'] == [dict(before_index=0, after_index=0)]
         and len(ledger['relocations']) == len(ledger['changed_fields'])
         == len(ledger['removed']) == len(ledger['added']) == 1,
         'duplicate occurrence canary failed')
    reorder = diff_array([a, b, a], [a, a, b])
    need(reorder['only_order_changed'] and len(reorder['positional_differences']) == 2,
         'ordered-array canary failed')
    bool_line = diff_array([a], [dict(a, line=True)])
    need(not bool_line['exact_arrays_equal'] and bool_line['relocations'][0]['differing_fields'] == ['line']
         and bool_line['before_sha256'] != bool_line['after_sha256'], 'Boolean/integer canary failed')
    float_line = diff_array([a], [dict(a, line=1.0)])
    need(not float_line['exact_arrays_equal']
         and float_line['relocations'][0]['differing_fields'] == ['line'], 'integer/float canary failed')
    null_field = diff_array([a], [dict(a, extra=None)])
    need(null_field['changed_fields'][0]['differing_fields'] == ['extra'], 'missing/null canary failed')
    nested = diff_array([dict(a, detail=[1])], [dict(a, detail=[True])])
    need(nested['changed_fields'][0]['differing_fields'] == ['detail'], 'nested JSON type canary failed')
    need(diff_array([a, a], [a, a])['exact_arrays_equal'], 'unchanged duplicate canary failed')
    return dict(status='invented_comparator_self_check_passed', mandatory_stop=False,
                d128_gate_passed=False, real_scans_or_approval_checks_performed=False,
                controls=['duplicate_occurrences', 'pure_order', 'bool_vs_int', 'float_vs_int',
                          'missing_vs_null', 'nested_json_types', 'unchanged_duplicates'],
                illustrative_ledgers=dict(duplicate=ledger, order=reorder, typed_line=bool_line))


def markdown(result, json_path):
    lines = ['# U3-L scanner diagnostic', '',
             'Status: `' + result['status'] + '`.', '',
             'D128 gate passed: **false**. This is a separate diagnostic, not a replacement gate.', '',
             'Complete arrays, full objects and occurrence/position ledgers: `' + str(json_path) + '`.', '']
    if 'failure' in result:
        lines.extend(['Evidence validation refused: ' + result['failure'], ''])
    for row in result.get('unapproved_arrays', []):
        lines.append('- `' + row['comparison'] + ' / ' + row['array'] + '` ('
                     + str(row['before_count']) + ' → ' + str(row['after_count']) + ' objects): `'
                     + row['ledger_json_pointer'] + '`.')
    if result.get('tool_asset_delta'):
        lines.extend(['', 'Scanner assets differ from D128’s frozen map; its unchanged asset pin refuses.', ''])
        lines.extend('- `' + row['path'] + '`.' for row in result['tool_asset_delta'])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-main', type=Path)
    parser.add_argument('--after-main', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--markdown', action='store_true')
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    need(ROOT.name == 'codex-native-u1u3' and ROOT.parent.name == 'd4d-executions',
         'assigned worktree required')
    need(not os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'), 'quiet window is active')
    need(args.out.is_absolute() and args.out.suffix == '.json'
         and args.out.parent.resolve(strict=True) == args.out.parent
         and args.out.is_relative_to(OUT_ROOT) and not os.path.lexists(args.out),
         'output must be fresh, physical and below assigned u3l scratch')
    md_path = args.out.with_suffix('.md')
    need(not args.markdown or not os.path.lexists(md_path), 'Markdown sidecar must be fresh')
    selections = (args.before_main, args.after_main, args.candidate)
    need((args.self_check and all(path is None for path in selections))
         or (not args.self_check and all(path is not None for path in selections)),
         'choose three run directories or --self-check alone')
    result = dict(kind='native_u3l_scanner_diagnostic', version=1,
                  helper_sha256=sha(Path(__file__).read_bytes()), status='incomplete',
                  mandatory_stop=True, d128_gate_passed=False,
                  equality='canonical JSON bytes; ordered lists and duplicate occurrences retained',
                  scope='Offline evidence only; frozen D128 approval and historical evidence unchanged.')
    if not args.self_check:
        result['input_directories'] = dict(before_main=str(args.before_main),
                                          after_main=str(args.after_main), candidate=str(args.candidate))
    try:
        if args.self_check:
            result.update(self_check())
            code = 0
        else:
            code = diagnostic(args, result)
    except Exception as exc:
        result.update(status='refused_incomplete_evidence', mandatory_stop=True,
                      d128_gate_passed=False, failure=type(exc).__name__ + ': ' + str(exc))
        code = 2
    need(not os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'), 'quiet window is active')
    raw = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()
    with args.out.open('xb') as stream:
        stream.write(raw)
    need(args.out.read_bytes() == raw, 'diagnostic output did not persist unchanged')
    if args.markdown:
        rendered = markdown(result, args.out).encode('utf-8')
        with md_path.open('xb') as stream:
            stream.write(rendered)
        need(md_path.read_bytes() == rendered, 'Markdown output did not persist unchanged')
    print(json.dumps(dict(path=str(args.out), bytes=len(raw), sha256=sha(raw), status=result['status'],
                          mandatory_stop=result['mandatory_stop'], d128_gate_passed=False)))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
