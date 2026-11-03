#!/usr/bin/env python3
"""PR #5213 round-four evidence ledger, 2026-11-03.

Input: explicit JSON {runs: [{name, directory, head, kind, classification,
require_pass}]}. Output: fresh external JSON; never searches child XML files,
runs tests, edits evidence, or converts diagnostic failures into passes.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
VERIFIER = HERE / 'plan_pr5213_integration_20261102.py'
_spec = importlib.util.spec_from_file_location('round4_existing_evidence_verifier', VERIFIER)
verification = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verification)

REQUIRED = {'name', 'directory', 'head', 'kind', 'classification', 'require_pass'}
PROOF_FILES = {'plan.json', 'outcome.json', 'nodes.json', 'phase-accounting.json',
               'source-before.json', 'source-after.json', 'pytest-command.json',
               'pytest.xml', 'hygiene.json', 'guard-denials.json'}


def top_files(directory):
    """Hash immediate regular files only; reject evidence-file indirection."""
    files = {}
    for path in sorted(directory.iterdir()):
        if path.is_symlink():
            raise ValueError('top-level evidence symlink is unsupported: ' + str(path))
        if path.is_file():
            files[path.name] = verification.sha(path)
        elif not path.is_dir():
            raise ValueError('nonregular top-level evidence entry: ' + str(path))
    return files


def junit_key(node):
    # Match pytest's mangle_test_address without importing pytest/production.
    path, bracket, parameters = node.partition('[')
    names = path.split('::')
    names[0] = re.sub(r'\.py$', '', names[0].replace('/', '.'))
    names[-1] += bracket + parameters
    return '.'.join(names[:-1]), names[-1]


def xml_outcomes(directory, selected, expected):
    identities = defaultdict(set)
    for node in selected:
        identities[junit_key(node)].add(node)
    counts = Counter(passed=0, failed=0, errors=0, skipped=0)
    observations = []
    cases = list(ET.parse(directory / 'pytest.xml').getroot().iter('testcase'))
    for index, case in enumerate(cases):
        details = [child for child in case if child.tag in ('failure', 'error', 'skipped')]
        status = ('errors' if any(item.tag == 'error' for item in details) else
                  'failed' if any(item.tag == 'failure' for item in details) else
                  'skipped' if details else 'passed')
        counts[status] += 1
        if not details:
            continue
        key = case.get('classname', ''), case.get('name', '')
        matches = identities.get(key, set())
        if len(matches) != 1:
            raise ValueError('JUnit nonpassing identity is absent or ambiguous: ' + repr(key))
        observations.append({'xml_case_index': index, 'nodeid': next(iter(matches)),
                             'status': status, 'classname': key[0], 'name': key[1],
                             'messages': [{'tag': item.tag, 'message': item.get('message'),
                                           'text': item.text or ''} for item in details]})
    if dict(counts) != expected:
        raise ValueError('top-level JUnit literal counts differ from runner raw_junit_counts')
    return dict(counts), observations


def verified_row(row, directory):
    collection = row['kind'] == 'collection'
    evidence = verification.run_evidence(directory, row['head'], collection=collection)
    plan, outcome, nodes, phases = (evidence[key] for key in ('plan', 'outcome', 'nodes', 'phases'))
    if bool(plan.get('collect_only')) != collection:
        raise ValueError('manifest kind disagrees with collection/execution command')
    occurrences = phases['occurrences']
    if not collection:
        if (not occurrences or not all(item['complete'] is True for item in occurrences)
                or Counter(item['nodeid'] for item in occurrences) != Counter(nodes['selected'])
                or Counter(item['status'] for item in occurrences) != Counter(outcome['counts'])):
            raise ValueError('selected occurrence/complete phase/count join differs')
    raw_counts, messages = xml_outcomes(directory, nodes['selected'], outcome['raw_junit_counts'])
    phase_nonpassing = [{key: item[key] for key in ('nodeid', 'item_index', 'status', 'complete')}
                        for item in occurrences if item['status'] != 'passed']
    if not collection:
        for item in phase_nonpassing:
            if item['status'] in ('failed', 'errors', 'skipped') and not any(
                    message['nodeid'] == item['nodeid'] for message in messages):
                raise ValueError('nonpassing phase occurrence has no JUnit message')
    literal_pass = (outcome.get('collection_passed') is True if collection else
                    outcome.get('passed') is True)
    literal_pass = literal_pass and outcome['returncode'] == 0
    if not collection:
        literal_pass = literal_pass and not any(
            value for status, value in outcome['counts'].items() if status not in ('passed', 'skipped'))
    return {**row, 'verified': True, 'complete': True,
            'source_head': plan['head'], 'source_tree': plan['git_tree'],
            'counts': outcome['counts'], 'raw_junit_counts': raw_counts,
            'selected_occurrences': len(nodes['selected']),
            'collected_occurrences': len(nodes['collected']),
            'phase_nonpassing': phase_nonpassing, 'xml_nonpassing': messages,
            'literal_pass': literal_pass, 'requirement_met': not row['require_pass'] or literal_pass,
            'returncode': outcome['returncode'], 'runner_monotonic_seconds': outcome['wall_seconds'],
            'command': evidence['command'], 'proofs': {key: outcome[key] for key in verification.PROOFS},
            'hygiene_mode': outcome.get('hygiene_mode'), 'hygiene_unchanged': outcome.get('hygiene_unchanged'),
            'archive_proof': plan['archive_proof'], 'archive_proof_sha256': plan['archive_proof_sha256']}


def summarize(manifest):
    rows = manifest.get('runs')
    if not isinstance(rows, list) or not rows:
        raise ValueError('explicit nonempty run manifest required')
    names, directories, results = set(), set(), []
    for row in rows:
        if (not isinstance(row, dict) or set(row) != REQUIRED
                or type(row['require_pass']) is not bool
                or any(not isinstance(row[key], str) or not row[key].strip()
                       for key in REQUIRED - {'require_pass'})
                or not re.fullmatch(r'[0-9a-f]{40}', row['head'])):
            raise ValueError('each manifest row requires the six explicit typed fields and a full HEAD')
        path = Path(row['directory'])
        if not path.is_absolute() or path.resolve(strict=True) != path or not path.is_dir():
            raise ValueError('physical absolute evidence directory required')
        if row['name'] in names or str(path) in directories:
            raise ValueError('duplicate manifest name or evidence directory')
        names.add(row['name'])
        directories.add(str(path))
        files = top_files(path)
        try:
            missing = sorted(PROOF_FILES - files.keys())
            if missing:
                raise ValueError('missing top-level proof files: ' + ', '.join(missing))
            result = verified_row(row, path)
        except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as exc:
            result = {**row, 'verified': False, 'complete': False, 'requirement_met': False,
                      'verification_error': f'{type(exc).__name__}: {exc}'}
        if top_files(path) != files:
            raise ValueError('evidence changed during ledger read: ' + str(path))
        result['top_level_artifact_sha256'] = files
        results.append(result)
    totals = Counter()
    for row in results:
        if row['verified'] and row['kind'] != 'collection':
            totals.update(row['counts'])
    return {'runs': results, 'all_rows_verified': all(row['verified'] for row in results),
            'all_rows_complete': all(row['complete'] for row in results),
            'required_outcomes_accepted': all(row['requirement_met'] for row in results),
            'all_literal_outcomes_pass': all(row.get('literal_pass') is True for row in results),
            'verified_execution_observation_totals_including_repeats': dict(totals),
            'scientific_acceptance': 'not_assessed',
            'limits': ['Counts are per-run observations; overlapping cohorts and repeated nodes are not unique tests.',
                       'Classification is supplied context, never a conversion of a literal failure into a pass.',
                       'JUnit messages join exact node identity, not xdist worker/occurrence indices; XML indices retain repeats.',
                       'Only listed directories and their top-level files are read; child XML is never included.',
                       'This ledger does not establish that the supplied roster covers every required task or CI lane.',
                       'Invalid or incomplete proof rows remain nonaccepted even when require_pass is false.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source = HERE.parents[1]
    producer = verification.producer_identity()
    raw = args.manifest.read_bytes()
    manifest_sha = hashlib.sha256(raw).hexdigest()
    output = args.output
    if (not output.is_absolute() or '..' in output.parts or output.exists() or output.is_symlink()
            or output.parent.resolve(strict=True) != output.parent or output.is_relative_to(source)):
        raise ValueError('fresh physical absolute output outside the producer worktree required')
    manifest = json.loads(raw)
    for row in manifest.get('runs', []):
        if output.is_relative_to(Path(row['directory']).resolve(strict=True)):
            raise ValueError('output must not alter an evidence directory')
    result = summarize(manifest)
    result.update(producer, manifest_path=str(args.manifest.resolve()), manifest_sha256=manifest_sha,
                  producer_sha256=verification.sha(Path(__file__)), verifier_sha256=verification.sha(VERIFIER))
    if args.manifest.read_bytes() != raw or verification.producer_identity() != producer:
        raise ValueError('manifest or producer source changed while summarizing')
    encoded = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    with output.open('xb') as stream:
        stream.write(encoded)
    if output.read_bytes() != encoded:
        raise ValueError('persisted ledger differs')
    print(json.dumps({'output': str(output), 'sha256': verification.sha(output),
                      'required_outcomes_accepted': result['required_outcomes_accepted']}))
    return 0 if result['required_outcomes_accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
