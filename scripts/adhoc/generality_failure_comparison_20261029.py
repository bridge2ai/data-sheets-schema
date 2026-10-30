#!/usr/bin/env python3
# Purpose: classify every complete-matrix failure against corrected-head/base replays.
# Inputs: JUnit directories in command-line order; outputs: external JSON/Markdown
# ledger retaining both failure traces. G1 N1 complete acceptance, 2026-10-30.
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(os.environ.get('G1_CHECKOUT_ROOT', Path(__file__).resolve().parents[2]))
parser = argparse.ArgumentParser()
parser.add_argument('--matrix', type=Path, required=True)
parser.add_argument('--replay', type=Path, action='append', default=[])
parser.add_argument('--base', type=Path, action='append', default=[])
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--require-complete-matrix', action='store_true')
parser.add_argument('--require-complete-acceptance', action='store_true')
args = parser.parse_args()
assert not args.output.resolve().is_relative_to(ROOT.resolve())

# These are bounded corrections made after the complete matrix exposed them.
# Keep causality separate from the observed pass/fail comparison below.
G1_CORRECTIONS = {
    'tests/test_agent_pin.py': 'N8: register the new/edited agent preimages',
    'tests/test_presence_scoping.py': 'N1/F18: date historical profile-less fixtures',
    'tests/test_native_source_attribution.py': 'N1/F17: give the historical stub its generic condition',
    'tests/test_rereceipt_completion.py': 'N1/F17: give the historical stub its generic condition',
    'tests/test_merge_pinned_fitness.py': 'N1/F18: date the historical profile-less fixture',
    'tests/test_grounding_instrument.py': 'N1/F18: date historical profile-less fixtures',
    'tests/test_dc_output_caps.py': 'N2/F10: declare the input bound in the output-cap fixture',
    'tests/test_rocrate/test_committed_outputs.py': 'N7/F6: compare retained sidecars with their exact 3.0.0 release',
    'tests/test_usage_ledger.py': 'N1/F17: use a supported condition for fresh identity change',
    'tests/test_historical_digest.py': 'N1/F18: date the historical profile-less fixture',
    'tests/test_extend_observed.py': 'N1/F18: date the historical profile-less fixture',
    'tests/test_scope.py': 'N1/F17: assert fresh refusal and render tuned only in replay mode',
}
G1_CORRECTION_NODES = {
    'tests/test_arm_comparison.py::test_committed_comparison_matches_current_records':
        'F11: refresh only the changed crate-manifest hash in the current comparison',
}
for filename in ('test_batch_downstream.py', 'test_batch_format_registration.py',
                 'test_batch_navigation_registration.py', 'test_worker_navigation_registration.py'):
    G1_CORRECTIONS['notes/matched_cborg_2026-09-13/audit_controls/' + filename] = (
        'N1/F17: give the historical audit renderer stub its generic condition')


def cases(directory, failures_only=False):
    result = {}
    for path in sorted(directory.glob('*.xml')):
        for case in ET.parse(path).findall('.//testcase'):
            parts = case.get('classname', '').split('.')
            for split in range(len(parts), 0, -1):
                file = '/'.join(parts[:split]) + '.py'
                if (ROOT / file).is_file():
                    node = '::'.join([file, *parts[split:], case.get('name')])
                    break
            else:
                raise ValueError(f'Cannot recover node ID: {case.attrib}')
            problem = case.find('failure')
            if problem is None:
                problem = case.find('error')
            if failures_only and problem is None:
                continue
            result[node] = {
                'status': 'failed' if problem is not None else
                          'skipped' if case.find('skipped') is not None else 'passed',
                'source': str(path),
                'message': problem.get('message') if problem is not None else None,
                'detail': problem.text if problem is not None else None,
            }
    return result


def normalized(message):
    # Preserve exception types, assertion regexes, guard text, keys and values.
    # These ten reviewed base/head differences contain generated identities;
    # the unmodified traces remain in the JSON for independent comparison.
    message = re.sub(r'0x[0-9a-f]+', '<address>', message or '')
    message = re.sub(r'/private/tmp/g1-validation-[^/\s\'"<>]+', '<basetemp>', message)
    for prefix, size in ((r'expected generation=', 32),
                         (r'required event_sha256s=', 64),
                         (r'"event_sha256":"', 64),
                         (r'"canonical_sha256":"', 64),
                         (r'"key":"snapshot:', 64),
                         (r'recorded hash ', 12)):
        message = re.sub('(' + prefix + r')[0-9a-f]{' + str(size) + '}',
                         r'\1<generated-identity>', message)
    return message


initial = cases(args.matrix, failures_only=True)
head = dict(initial)
for directory in args.replay:
    head.update(cases(directory))
unexpected_replay_failures = {node: row for node, row in head.items()
                             if node not in initial and row['status'] == 'failed'}
base = {}
for directory in args.base:
    base.update(cases(directory))
rows = []
for node, original in sorted(initial.items()):
    current, before = head[node], base.get(node)
    if current['status'] != 'failed':
        status = 'resolved-' + current['status']
    elif before is None:
        status = 'needs-base-replay'
    elif before['status'] != 'failed':
        status = 'introduced-or-environment'
    elif normalized(current['message']) == normalized(before['message']):
        status = 'same-base-failure'
    else:
        status = 'base-failure-needs-trace-review'
    rows.append({'nodeid': node, 'classification': status,
                 'message_comparison': ('identical' if before and current['message'] == before['message']
                                        else 'reviewed generated identities' if status == 'same-base-failure'
                                        else None),
                 'correction': G1_CORRECTION_NODES.get(node,
                     G1_CORRECTIONS.get(node.split('::')[0])),
                 'initial': original, 'head': current, 'base': before})
counts = dict(Counter(row['classification'] for row in rows))
if args.require_complete_acceptance:
    assert not unexpected_replay_failures, unexpected_replay_failures
    assert all(row['base'] is not None for row in rows), 'base replay incomplete'
    assert set(counts) <= {'same-base-failure', 'resolved-passed', 'resolved-skipped'}, counts
# The final disposition overlays only tested failed nodes; initial successes
# are retained, never described as a second complete suite execution.
matrix_summary = json.loads((args.matrix / 'summary.json').read_text())
units = {}
for unit, value in matrix_summary.items():
    if unit.startswith('collect-'):
        continue
    original_counts = value['counts']
    changes = Counter(row['head']['status'] for row in rows
                      if Path(row['initial']['source']).stem == unit)
    units[unit] = {'initial': original_counts,
                  'after_failed_node_replays': {
                      'passed': original_counts['passed'] + changes['passed'],
                      'skipped': original_counts['skipped'] + changes['skipped'],
                      'pre_existing_failures': changes['failed']},
                  'execution': value['execution']}
corrections = Counter(row['correction'] or 'offline harness/environment'
                      for row in rows if row['head']['status'] != 'failed')
remaining_files = Counter(row['nodeid'].split('::')[0] for row in rows
                          if row['head']['status'] == 'failed')
# The workflow partitions tests/ into six ordinary shards and four API lanes.
# The other offline jobs separately select their controls under notes/.
routed_files = set()
for path in args.matrix.glob('*.result.json'):
    command = json.loads(path.read_text())['command']
    if any(token.startswith('--ci-lane=') for token in command):
        routed_files.add(path.with_name(path.name.replace('.result.json', '.xml')))
routed = Counter()
owners = {}
for path in sorted(routed_files):
    for case in ET.parse(path).findall('.//testcase'):
        parts = case.get('classname').split('.')
        for split in range(len(parts), 0, -1):
            file = '/'.join(parts[:split]) + '.py'
            if (ROOT / file).is_file():
                node = '::'.join([file, *parts[split:], case.get('name')])
                break
        else:
            raise ValueError(case.attrib)
        routed[node] += 1
        owners.setdefault(node, set()).add(path.name)
collected = Counter(line for line in (args.matrix / 'collect-tests.log').read_text().splitlines()
                    if line.startswith('tests/') and '::' in line)
# Pytest 7 emits the same [00] ID for two existing budget parameters.
# Compare collected instances, preserving multiplicity;
# also ensure no ID is assigned to more than one CI unit.
overlaps = {node: sorted(units) for node, units in owners.items() if len(units) > 1}
coverage = {'routed_units': len(routed_files), 'collected_tests': sum(collected.values()),
            'routed_tests': sum(routed.values()), 'routed_unique_ids': len(routed),
            'missing': dict(collected - routed), 'unexpected': dict(routed - collected),
            'cross_unit_overlap': overlaps,
            'repeated_collected_ids': {node: count for node, count in collected.items() if count > 1}}
if args.require_complete_matrix:
    assert len(routed_files) == 10 and not coverage['missing'] and not coverage['unexpected'] and not overlaps, coverage
args.output.write_text(json.dumps({'counts': counts, 'coverage': coverage, 'units': units,
    'resolved_causes': dict(corrections), 'remaining_by_file': dict(remaining_files),
    'unexpected_replay_failures': unexpected_replay_failures, 'nodes': rows}, indent=2) + '\n')
lines = ['# Complete-matrix failure classification', '',
         'All original and replay traces are retained in the adjacent JSON. '
         'Generated generation/event/snapshot identities are normalized only in '
         'the message-equivalence comparison; assertion text and guard outcomes remain exact.', '',
         '| CI unit | Initial pass / skip / fail+error | After failed-node replays: pass / skip / base failure |',
         '|---|---|---|']
for unit, value in units.items():
    old, new = value['initial'], value['after_failed_node_replays']
    lines.append(f"| {unit} | {old['passed']} / {old['skipped']} / {old['failures'] + old['errors']} | "
                 f"{new['passed']} / {new['skipped']} / {new['pre_existing_failures']} |")
lines += ['',
         '| Node | Classification | Correction | Head evidence | Base evidence |',
         '|---|---|---|---|---|']
for row in rows:
    lines.append('| `' + row['nodeid'].replace('|', '\\|') + '` | ' + row['classification'] +
                 ' | ' + (row['correction'] or '') + ' | ' + Path(row['head']['source']).name + ' | ' +
                 (Path(row['base']['source']).name if row['base'] else 'pending') + ' |')
args.output.with_suffix('.md').write_text('\n'.join(lines) + '\n')
print(json.dumps(counts, sort_keys=True))
print('RESOLVED CAUSES', json.dumps(corrections, sort_keys=True))
print('REMAINING FILES', json.dumps(remaining_files, sort_keys=True))
for node, row in unexpected_replay_failures.items():
    print('NEW REPLAY FAILURE', node, row['message'])
for row in rows:
    if row['classification'] not in ('same-base-failure', 'resolved-passed', 'resolved-skipped'):
        print(row['classification'], row['nodeid'])
        if row['base'] is not None:
            print('  HEAD:', (row['head']['message'] or row['head']['status'])[:1200])
            print('  BASE:', (row['base']['message'] or row['base']['status'])[:1200])
