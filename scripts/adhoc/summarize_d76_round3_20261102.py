#!/usr/bin/env python3
"""Account for PR #5213 round-three evidence, 2026-11-02.

Input: JSON manifest {head, runs:[{name, role, directory}]} plus completed run
artifacts. Roles: collection, ordinary, api, offline, targeted, probe, baseline,
diagnostic. Output: a new JSON summary with hashes, literal outcomes and exact
CI collection coverage. Never promotes an expected or environmental failure.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def summarize(manifest):
    if not manifest['runs']:
        raise ValueError('explicit nonempty run roster required')
    if len({row['name'] for row in manifest['runs']}) != len(manifest['runs']):
        raise ValueError('run names must be unique; preserve repeats as separate observations')
    runs = []
    collected, ci_selected = Counter(), Counter()
    ci_plans = []
    offline = []
    coverage_proofs = []
    offline_proofs = []
    for row in manifest['runs']:
        root = Path(row['directory']).resolve(strict=True)
        names = ('outcome.json', 'plan.json', 'nodes.json', 'phase-accounting.json',
                 'source-before.json', 'source-after.json', 'pytest-command.json')
        missing = [name for name in names if not (root / name).is_file()]
        if missing:
            runs.append({**row, 'complete': False, 'missing_artifacts': missing})
            continue
        outcome, plan, nodes, phases = (read(root / name) for name in names[:4])
        role = row['role']
        expected_head = row.get('head', manifest['head'])
        if role not in ('baseline', 'diagnostic') and expected_head != manifest['head']:
            raise ValueError(f"{row['name']}: a final coverage run cannot use a baseline head")
        if plan['head'] != expected_head:
            raise ValueError(f"{row['name']}: unexpected source head")
        if outcome['counts'] != phases['counts']:
            raise ValueError(f"{row['name']}: outcome/phase counts disagree")
        if role == 'collection':
            if collected:
                raise ValueError('one final complete collection must define CI coverage')
            collected = Counter(nodes['collected'])
        if role in ('ordinary', 'api'):
            ci_selected.update(nodes['selected'])
            ci_plans.append({'name': row['name'], 'role': role,
                             'argv': read(root / 'pytest-command.json')['argv']})
        if role == 'offline':
            offline.append({'name': row['name'], 'job': plan.get('notes_ci_job'),
                            'targets': plan['targets']})
        is_final_coverage = role in ('collection', 'ordinary', 'api', 'offline')
        archive_path = Path(plan['archive_proof']) if plan.get('archive_proof') else None
        archive_bound = bool(archive_path and archive_path.is_file()
                             and digest(archive_path) == plan.get('archive_proof_sha256'))
        before, after = (read(root / name) for name in ('source-before.json', 'source-after.json'))
        linked_source = (before == after and before.get('head') == plan['head']
                         and before.get('tree') == plan.get('git_tree')
                         and before.get('tracked_exact') is True)
        if archive_bound:
            archived = read(archive_path)
            archive_bound = (archived.get('head') == plan['head']
                             and archived.get('git_tree') == plan.get('git_tree')
                             and archived.get('destination') == plan.get('worktree'))
        proofs = {key: outcome.get(key) for key in (
            'source_unchanged', 'hygiene_passed', 'origins_verified', 'helpers_unchanged',
            'targets_unchanged', 'sandbox_loaded', 'zero_guard_denials', 'all_worker_collections_identical')}
        complete = bool(outcome.get('collection_complete') if role == 'collection'
                        else outcome.get('node_accounting_complete'))
        identity_valid = (complete and all(value is True for value in proofs.values())
                          and archive_bound and linked_source and outcome.get('deadline_expired') is False
                          and outcome.get('phase_journals_valid') is True)
        if is_final_coverage:
            (offline_proofs if role == 'offline' else coverage_proofs).append(
                {'name': row['name'], 'valid': identity_valid})
        failures = [{key: occurrence[key] for key in ('nodeid', 'status', 'complete')}
                    for occurrence in phases['occurrences']
                    if occurrence['status'] not in ('passed', 'skipped')]
        evidence = {name: digest(root / name) for name in names}
        for name in ('pytest.xml', 'pytest.log', 'hygiene.json', 'guard-denials.json'):
            if (root / name).is_file():
                evidence[name] = digest(root / name)
        for name in ('deadline.json', 'phase-journals.json'):
            if (root / name).is_file():
                evidence[name] = digest(root / name)
        runs.append({**row, 'head': plan['head'], 'complete': complete,
            'counts': outcome['counts'], 'wall_seconds': outcome['wall_seconds'],
            'passed': outcome.get('collection_passed') if role == 'collection' else outcome['passed'],
            'returncode': outcome['returncode'], 'failures': failures,
            'proofs': proofs, 'hygiene_unchanged': outcome.get('hygiene_unchanged'),
            'archive_proof_sha256': plan.get('archive_proof_sha256'), 'archive_proof_matches': archive_bound,
            'linked_source_matches': linked_source,
            'deadline_expired': outcome.get('deadline_expired'),
            'phase_journals_valid': outcome.get('phase_journals_valid'),
            'coverage_identity_valid': identity_valid if is_final_coverage else None,
            'artifact_sha256': evidence})
    ordinary = [row for row in ci_plans if row['role'] == 'ordinary']
    api = [row for row in ci_plans if row['role'] == 'api']
    expected_shards = {f'--ci-shard={index}/6' for index in range(1, 7)}
    actual_shards = {arg for row in ordinary for arg in row['argv'] if arg.startswith('--ci-shard=')}
    expected_api = {'--ci-lane=' + name for name in (
        'routing-dispatch', 'routing-portable', 'routing-regate', 'routing-default-layout')}
    actual_api = {arg for row in api for arg in row['argv'] if arg.startswith('--ci-lane=')}
    coverage = {'collected_occurrences': sum(collected.values()),
                'ci_selected_occurrences': sum(ci_selected.values()),
                'missing': dict(collected - ci_selected), 'extra': dict(ci_selected - collected),
                'six_ordinary_commands_present': len(ordinary) == 6 and actual_shards == expected_shards,
                'four_api_commands_present': len(api) == 4 and actual_api == expected_api}
    coverage['counter_and_commands_exact'] = bool(collected) and collected == ci_selected and all(
        coverage[key] for key in ('six_ordinary_commands_present', 'four_api_commands_present'))
    coverage['proofs'] = coverage_proofs
    coverage['exact'] = coverage['counter_and_commands_exact'] and all(row['valid'] for row in coverage_proofs)
    hygiene_path = Path(__file__).with_name('d76_round3_hygiene_20261102.py')
    module_spec = importlib.util.spec_from_file_location('round3_expected_notes_rosters', hygiene_path)
    hygiene = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(hygiene)
    expected_jobs = {name: list(paths) for name, paths in hygiene.NOTES_TARGETS.items()
                     if name.startswith('ci-')}
    jobs = Counter(row['job'] for row in offline)
    offline_coverage = {
        'required_jobs': expected_jobs, 'observed': offline,
        'roster_helper_sha256': digest(hygiene_path),
        'roster_and_commands_exact': jobs == Counter({job: 1 for job in expected_jobs}) and all(
            row['targets'] == expected_jobs.get(row['job']) for row in offline),
        'proofs': offline_proofs,
    }
    offline_coverage['exact'] = offline_coverage['roster_and_commands_exact'] and all(
        row['valid'] for row in offline_proofs)
    return {'head': manifest['head'], 'runs': runs, 'tests_ci_coverage': coverage,
            'offline_ci_coverage': offline_coverage,
            'all_manifest_runs_complete': all(row['complete'] for row in runs),
            'all_literal_outcomes_pass': all(row.get('passed') for row in runs),
            'scientific_acceptance': 'not_assessed',
            'counting_rule': 'Per-run counts retain repeats, controls, failures and skips; no summed unique acceptance claim.',
            'classification_rule': 'Manual dispositions require linked evidence; this tool never converts failures into passes.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = summarize(read(args.manifest))
    result['manifest_sha256'] = digest(args.manifest)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(args.output)
    print(digest(args.output))


if __name__ == '__main__':
    main()
