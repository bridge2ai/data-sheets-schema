"""Map the original A4/A5 118 nonpasses to explicit U3-G run series, 2026-11-09.

Inputs: retained A4/A5 manifests/XML plus explicitly named current run directories.
Output: one fresh JSON under scratch-native-u1u3/u3g. Standard-library evidence
reads only; no production/test imports, launches, Git or network. Exact XML
classname::name identities are retained. Every observation and its actual source
commit remains visible; a later pass never erases an earlier nonpass.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EXECUTIONS = ROOT.parent
HISTORICAL = EXECUTIONS / 'scratch-native-u4b'
OUT = EXECUTIONS / 'scratch-native-u1u3/u3g'
PINNED = {
    'validation-addendum4.json': 'f7f28ed5c700399805e71d5db8a416ce998faa5cb387dfa257a622136e8b77d7',
    'validation-addendum5.json': '5f4afb80ab87f0a26b21b061065802a3a9e6b4b13e06c4af952bb60d4ea45763',
}


def need(value, message):
    if not value:
        raise ValueError(message)


def quiet():
    need(not os.path.lexists(EXECUTIONS / 'plans/native_quiet_window.lock'), 'quiet window active')


def read(path, hashes):
    quiet()
    need(path.resolve(strict=True) == path and path.is_relative_to(EXECUTIONS),
         'nonphysical or unassigned evidence: ' + str(path))
    with path.open('rb') as stream:
        raw = stream.read(64_000_001)
    need(0 < len(raw) <= 64_000_000, 'empty or oversized evidence: ' + str(path))
    hashes[str(path)] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    return raw


def load(path, hashes):
    return json.loads(read(path, hashes))


def cases(path, hashes):
    rows = []
    for case in ET.fromstring(read(path, hashes)).iter('testcase'):
        state, detail, message = 'passed', '', ''
        for tag, selected in (('failure', 'failed'), ('error', 'errors'), ('skipped', 'skipped')):
            element = case.find(tag)
            if element is not None:
                state, detail, message = selected, element.text or '', element.get('message', '')
                break
        rows.append({'node': case.get('classname', '') + '::' + case.get('name', ''),
            'state': state, 'message': message, 'trace': detail,
            'xml': str(path), 'xml_sha256': hashes[str(path)]['sha256'],
            'xml_attributes': dict(case.attrib)})
    return rows


def historical(hashes):
    rosters, witness = [], []
    for filename, expected in PINNED.items():
        path = HISTORICAL / filename
        document = load(path, hashes)
        need(hashes[str(path)]['sha256'] == expected, 'historical manifest changed: ' + filename)
        roster = {row['node']: row for row in document['latest_nonpassing']}
        need(len(roster) == len(document['latest_nonpassing']) == 118, 'original roster is not 118 unique nodes')
        by_run = {run['name']: run for run in document['runs']}
        parsed = {}
        for run in sorted({row['run'] for row in roster.values()}):
            xml = HISTORICAL / run / 'pytest.xml'
            parsed[run] = cases(xml, hashes)
            need(hashes[str(xml)] == by_run[run]['artifacts']['pytest.xml'],
                 'historical XML differs from manifest: ' + run)
        for node, row in roster.items():
            matches = [case for case in parsed[row['run']] if case['node'] == node]
            need(len(matches) == 1 and matches[0]['state'] == row['state'],
                 'historical XML does not prove listed state: ' + node)
            need(by_run[row['run']]['source_stability']['before']['head'] == row['head'],
                 'historical source head mismatch: ' + node)
            witness.append({'manifest': filename, 'node': node, 'group': row['group'],
                'source_commit': row['head'], 'run': row['run'], **matches[0]})
        rosters.append(roster)
    identities = lambda roster: {node: (row['state'], row['group']) for node, row in roster.items()}
    need(identities(rosters[0]) == identities(rosters[1]), 'A4/A5 node/state/group rosters differ')
    return rosters[1], witness


def current_run(label, hashes):
    need(re.fullmatch('[a-z0-9][a-z0-9_-]*', label), 'unsafe run label')
    folder = OUT / label
    missing = [name for name in ('plan.json', 'outcome.json', 'source-stability.json', 'pytest.xml')
               if not (folder / name).is_file()]
    plan = load(folder / 'plan.json', hashes) if (folder / 'plan.json').is_file() else {}
    outcome = load(folder / 'outcome.json', hashes) if (folder / 'outcome.json').is_file() else {}
    stable = load(folder / 'source-stability.json', hashes) if (folder / 'source-stability.json').is_file() else {}
    errors, rows = [], []
    if (folder / 'pytest.xml').is_file():
        try:
            rows = cases(folder / 'pytest.xml', hashes)
        except ET.ParseError as error:
            errors.append('malformed pytest XML: ' + str(error))
    source = plan.get('source_commit')
    source_match = (source is not None and stable.get('before', {}).get('head') == source
                    and stable.get('after', {}).get('head') == source)
    valid = (not missing and not errors and source_match and stable.get('unchanged') is True
             and stable.get('before', {}).get('status') == stable.get('after', {}).get('status') == ''
             and outcome.get('cleanup_verified') is True and not outcome.get('interrupted')
             and outcome.get('worker', {}).get('source_origin_checks_passed') is True)
    return {'run': label, 'source_commit': source, 'source_root': plan.get('source_root'),
        'missing_artifacts': missing, 'parse_errors': errors, 'source_identity_matches': source_match,
        'evidence_complete_and_clean': valid, 'returncode': outcome.get('returncode'),
        'counts': dict(Counter(row['state'] for row in rows)), 'nodes': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--series', required=True, action='append', nargs='+', metavar='LABEL_OR_RUN',
        help='Series label then explicit run labels, in declared chronological order; repeat for each series.')
    args = parser.parse_args()
    quiet()
    need(EXECUTIONS.name == 'd4d-executions' and EXECUTIONS.resolve() == EXECUTIONS,
         'helper must run from the assigned physical worktree')
    need(args.output.is_absolute() and args.output.parent == OUT and args.output.resolve() == args.output
         and not os.path.lexists(args.output), 'output must be a fresh literal file directly under U3-G scratch')
    need(all(len(group) >= 2 for group in args.series), 'each series needs at least one explicit run')
    need(len({group[0] for group in args.series}) == len(args.series), 'duplicate series label')
    hashes = {}
    roster, old = historical(hashes)
    series, cache = [], {}
    for name, *labels in args.series:
        need(re.fullmatch('[a-z0-9][a-z0-9_-]*', name) and len(set(labels)) == len(labels),
             'unsafe series label or duplicated run')
        runs = []
        for label in labels:
            if label not in cache:
                cache[label] = current_run(label, hashes)
            runs.append(cache[label])
        mapped = []
        for node, original in sorted(roster.items()):
            observations = [{**row, 'run': run['run'], 'source_commit': run['source_commit'],
                'run_evidence_complete_and_clean': run['evidence_complete_and_clean']}
                for run in runs for row in run['nodes'] if row['node'] == node]
            latest = observations[-1] if observations else None
            state = 'missing' if latest is None else latest['state']
            verified_pass = bool(latest and state == 'passed' and latest['run_evidence_complete_and_clean'])
            mapped.append({'node': node, 'historical_group': original['group'],
                'historical_state': original['state'], 'observations': observations,
                'latest_selected_state': state, 'latest_selected_observation': latest,
                'verified_latest_node_pass': verified_pass,
                'distinct_observed_states': sorted({row['state'] for row in observations}),
                'unresolved': not verified_pass})
        series.append({'series': name, 'explicit_run_order': labels,
            'source_commits': sorted({run['source_commit'] for run in runs if run['source_commit']}),
            'counts': dict(Counter(row['latest_selected_state'] for row in mapped)),
            'verified_latest_node_passes': sum(row['verified_latest_node_pass'] for row in mapped),
            'unresolved_nodes': [row['node'] for row in mapped if row['unresolved']],
            'runs': runs, 'mapping': mapped})
    result = {'kind': 'native_u3g_historical_118_comparison', 'version': 1,
        'scope': 'Exact node evidence only; no historical run is relabeled as current HEAD. Latest is '
                 'explicit caller run order; all prior observations remain. Missing/skipped/failed/error '
                 'or incomplete-source evidence stays unresolved. No launch or full-suite acceptance.',
        'historical_node_count': len(roster),
        'historical_group_counts': dict(Counter(row['group'] for row in roster.values())),
        'historical_a4_a5_exact_node_state_group_equal': True,
        'historical_observations': old, 'series': series, 'artifact_sha256': hashes,
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    encoded = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    quiet()
    with args.output.open('xb') as stream:
        stream.write(encoded)
    need(args.output.read_bytes() == encoded, 'report readback differs')
    print(json.dumps({'report': str(args.output), 'sha256': hashlib.sha256(encoded).hexdigest(),
        'series': [{'series': row['series'], 'counts': row['counts'],
                    'verified_latest_node_passes': row['verified_latest_node_passes'],
                    'unresolved': len(row['unresolved_nodes'])} for row in series]}))


if __name__ == '__main__':
    main()
