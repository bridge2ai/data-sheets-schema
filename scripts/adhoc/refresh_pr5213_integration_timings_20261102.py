#!/usr/bin/env python3
"""#5213 integration, 2026-11-02: preserve main weights and add local measurements.

Inputs: pinned main/round-three Git objects, six explicit top-level round-three
ordinary JUnit/proof files, and the prior #5212 timing evidence. Outputs: fresh
normalized XML, main/timings JSON and provenance; --install resolves only the
duration JSON. No recursive XML discovery, test execution or network access.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
MAIN = 'ddfd45c3b520d37da247cf899401437794880e0c'
ROUND3 = 'd13c1711e19dcdcc7f624b66e15b735ebc0aab8f'
DURATIONS = 'utils/ci_test_durations.json'
UPDATER = 'utils/update_ci_shard_timings.py'
PROOF_FILES = ('plan.json', 'outcome.json', 'nodes.json', 'phase-accounting.json',
               'source-before.json', 'source-after.json', 'hygiene.json',
               'guard-denials.json', 'pytest.xml')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def encode(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def git_environment():
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
               GIT_OPTIONAL_LOCKS='0', GIT_CONFIG_COUNT='1',
               GIT_CONFIG_KEY_0='protocol.allow', GIT_CONFIG_VALUE_0='never')
    return env


def git(tree, *args):
    return subprocess.check_output(['git', '--no-replace-objects', '-c',
        'protocol.allow=never', '-C', str(tree), *args], env=git_environment())


@contextmanager
def builder_git_environment():
    # The unchanged builder invokes git ls-files itself. Apply the same offline
    # Git policy to that subprocess without altering the builder's source.
    original = {key: value for key, value in os.environ.items() if key.startswith('GIT_')}
    for key in list(os.environ):
        if key.startswith('GIT_'):
            del os.environ[key]
    os.environ.update({key: value for key, value in git_environment().items() if key.startswith('GIT_')})
    try:
        yield
    finally:
        for key in list(os.environ):
            if key.startswith('GIT_'):
                del os.environ[key]
        os.environ.update(original)


def module_map(tree, head):
    paths = git(tree, 'ls-tree', '-r', '--name-only', head, '--', 'tests').decode().splitlines()
    return {path[:-3].replace('/', '.'): path for path in paths if path.endswith('.py')}


def case_node(case, modules):
    classname, name = case.attrib['classname'], case.attrib['name']
    matching = [module for module in modules
                if classname == module or classname.startswith(module + '.')]
    require(matching, f'cannot map JUnit case to tracked test module: {classname}::{name}')
    module = max(matching, key=len)
    suffix = classname[len(module):].lstrip('.').replace('.', '::')
    return modules[module], modules[module] + '::' + (suffix + '::' if suffix else '') + name


def extract_shard(root, index, expected_head, modules, added):
    directory = root / f'd13c1-ci-ordinary-{index}'
    raw = {name: (directory / name).read_bytes() for name in PROOF_FILES}
    proof = {name: json.loads(value) for name, value in raw.items() if name.endswith('.json')}
    plan, outcome, phases, nodes = (proof[name] for name in
        ('plan.json', 'outcome.json', 'phase-accounting.json', 'nodes.json'))
    source = proof['source-before.json']
    require(plan['head'] == expected_head and source['head'] == expected_head,
            f'{directory}: wrong measured head')
    require(plan['ci_ordinary_shard_of_6'] == index and plan['targets'] == ['tests']
            and plan['notes_ci_job'] is None and not plan['collect_only'],
            f'{directory}: not the explicit complete ordinary shard')
    require(source == proof['source-after.json'] and source['tracked_exact']
            and source['tree'] == plan['git_tree'], f'{directory}: source proof differs')
    flags = ('source_unchanged', 'helpers_unchanged', 'targets_unchanged', 'hygiene_passed',
             'hygiene_unchanged', 'origins_verified', 'phase_journals_valid',
             'sandbox_loaded', 'zero_guard_denials', 'node_accounting_complete',
             'all_worker_collections_identical')
    require(all(outcome.get(flag) is True for flag in flags)
            and outcome.get('deadline_expired') is False,
            f'{directory}: incomplete or invalid timing provenance')
    require(proof['hygiene.json']['passed'] and proof['guard-denials.json']['zero_denials']
            and phases['all_selected_completed'] and phases['counts'] == outcome['counts'],
            f'{directory}: incomplete phases/hygiene/guard proof')
    require(Counter(row['nodeid'] for row in phases['occurrences']) == Counter(nodes['selected']),
            f'{directory}: selected and phase occurrences differ')
    xml = ET.fromstring(raw['pytest.xml'])
    all_cases = list(xml.iter('testcase'))
    mapped = [(case, *case_node(case, modules)) for case in all_cases]
    require(Counter(node for _, _, node in mapped) == Counter(nodes['selected']),
            f'{directory}: XML and phase rosters differ')
    selected = [(case, path, node) for case, path, node in mapped if path in added]
    selected_nodes = Counter(node for _, _, node in selected)
    relevant_phases = [row for row in phases['occurrences'] if row['nodeid'].split('::', 1)[0] in added]
    require(Counter(row['nodeid'] for row in relevant_phases) == selected_nodes
            and all(row['complete'] and row['status'] == 'passed' for row in relevant_phases),
            f'{directory}: added-file cases are not complete passes')
    normalized, rows = ET.Element('testsuite'), []
    for case, path, node in selected:
        require(not any(case.find(kind) is not None for kind in ('failure', 'error', 'skipped')),
                f'{directory}: unsuccessful added-file case {node}')
        seconds = Decimal(case.attrib['time'])
        require(seconds.is_finite() and seconds >= 0, f'{node}: invalid duration')
        normalized.append(deepcopy(case))
        rows.append({'nodeid': node, 'file': path, 'seconds': float(seconds),
                     'seconds_decimal': str(seconds), 'origin': 'local_round3_junit',
                     'shard': index, 'outcome': 'passed'})
    return normalized, rows, {
        'directory': str(directory), 'head': expected_head, 'shard': index,
        'sha256': {name: sha(value) for name, value in raw.items()},
        'original_counts': outcome['counts'], 'selected_passing_cases': len(rows),
        'original_run_all_passed': outcome['passed'],
        'scope': 'Only added-file passing cases are normalized; original failures remain retained.'}


def additional_measurements(tree, measured_head, collection, runs, required, verifier):
    """Join exact, completed local cohorts before normalizing their JUnit times.

    This round-four mode accepts split SG2 cohorts, never duplicated test
    observations. Full collection defines the required occurrence multiset.
    All original evidence remains external and unchanged.
    """
    full = verifier.run_evidence(collection, measured_head, collection=True)
    expected = Counter(node for node in full['nodes']['collected']
                       if node.split('::', 1)[0] in required)
    require({node.split('::', 1)[0] for node in expected} == set(required),
            'every refreshed module needs a full collected roster')
    modules = module_map(tree, measured_head)
    normalized, rows, proofs, observed = ET.Element('testsuite'), [], [], Counter()
    seen_directories = set()
    for directory in runs:
        directory = Path(directory).resolve(strict=True)
        require(directory not in seen_directories, 'duplicate measurement directory')
        seen_directories.add(directory)
        proof = verifier.run_evidence(directory, measured_head)
        require(proof['outcome']['worker_count'] <= 2, 'round-four worker cap exceeded')
        raw = (directory / 'pytest.xml').read_bytes()
        mapped = [(case, *case_node(case, modules)) for case in ET.fromstring(raw).iter('testcase')]
        require(Counter(node for _, _, node in mapped) == Counter(proof['nodes']['selected']),
                'JUnit does not cover the selected occurrence multiset')
        selected = [(case, path, node) for case, path, node in mapped if path in required]
        require(selected, 'measurement run supplies no requested module')
        phases = [row for row in proof['phases']['occurrences']
                  if row['nodeid'].split('::', 1)[0] in required]
        require(Counter(row['nodeid'] for row in phases) == Counter(node for _, _, node in selected)
                and all(row['complete'] and row['status'] == 'passed' for row in phases),
                'refreshed modules must contain only completed passing cases')
        for case, path, node in selected:
            require(not any(case.find(kind) is not None for kind in ('failure', 'error', 'skipped')),
                    'unsuccessful refreshed case: ' + node)
            seconds = Decimal(case.attrib['time'])
            require(seconds.is_finite() and seconds >= 0, 'invalid measured duration')
            observed[node] += 1
            normalized.append(deepcopy(case))
            rows.append({'nodeid': node, 'file': path, 'seconds': float(seconds),
                         'seconds_decimal': str(seconds), 'outcome': 'passed',
                         'origin': 'local_round4_junit', 'measured_commit': measured_head})
        proofs.append({'directory': str(directory), 'head': measured_head,
                       'files': {**proof['files'], 'pytest.xml': sha(raw)},
                       'original_counts': proof['outcome']['counts'],
                       'original_run_all_passed': proof['outcome']['passed']})
    require(observed == expected, 'measurements must cover each collected occurrence exactly once')
    collection_proof = {'directory': str(collection), 'head': measured_head,
                        'files': full['files'], 'expected_occurrences': dict(expected)}
    return normalized, rows, proofs, collection_proof


def additional_main():
    """Round-four extension of the same integration refresh path, 2026-11-03.

    Inputs: explicit manifest of pinned collection/runs, prior integration
    evidence and base weights. Outputs: new measured weights and linked
    evidence; old measurements never acquire a new source identity.
    """
    parser = argparse.ArgumentParser(description=additional_main.__doc__)
    parser.add_argument('--additional-manifest', type=Path, required=True)
    parser.add_argument('--tree', type=Path, default=ROOT)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    tree = args.tree.resolve(strict=True)
    manifest_raw = args.additional_manifest.read_bytes()
    manifest = json.loads(manifest_raw)
    require(set(manifest) == {'base_commit', 'measured_commit', 'prior_evidence',
                            'prior_evidence_sha256', 'collection', 'runs', 'retired_modules'},
            'unexpected additional measurement manifest fields')
    base, head = manifest['base_commit'], manifest['measured_commit']
    for value in (base, head):
        require(re.fullmatch('[0-9a-f]{40}', value) is not None
                and git(tree, 'rev-parse', value + '^{commit}').decode().strip() == value,
                'full local source commit required')
    git(tree, 'merge-base', '--is-ancestor', base, head)
    git(tree, 'merge-base', '--is-ancestor', head, 'HEAD')
    base_weights = git(tree, 'show', base + ':' + DURATIONS)
    original = json.loads(base_weights)
    prior_path = Path(manifest['prior_evidence'])
    prior_raw, prior = prior_path.read_bytes(), read(prior_path)
    require(sha(prior_raw) == manifest['prior_evidence_sha256']
            and prior['timings_sha256'] == sha(base_weights), 'prior evidence/weights mismatch')
    updater_raw = (tree / UPDATER).read_bytes()
    require(updater_raw == git(tree, 'show', MAIN + ':' + UPDATER), 'main timing builder changed')
    old_hashes = prior['local']['test_source_sha256']
    old_source_commits = prior.get('local_source_commits')
    if old_source_commits is None:
        old_source_commits = {path: prior['local']['measured_commit'] for path in old_hashes}
    require(set(old_source_commits) == set(old_hashes), 'prior per-file source roster differs')
    for path, commit in old_source_commits.items():
        require(re.fullmatch('[0-9a-f]{40}', commit) is not None
                and sha(git(tree, 'show', commit + ':' + path)) == old_hashes[path],
                'prior per-file measured source identity differs')
    current_modules = {path for path in module_map(tree, head).values()
                       if Path(path).name.startswith('test_')}
    retired = set(manifest['retired_modules'])
    require(len(retired) == len(manifest['retired_modules'])
            and retired == set(old_hashes) - current_modules,
            'retirement list must exactly name absent previously measured modules')
    retired_proofs = {}
    for path in sorted(retired):
        before = git(tree, 'show', base + ':' + path)
        require(sha(before) == old_hashes[path], 'retired source differs from historical measurement')
        require(not (tree / path).exists() and not (tree / path).is_symlink(),
                'retired module still exists in working tree')
        retired_proofs[path] = {'base_commit': base, 'source_sha256': sha(before),
                               'absent_at_measured_commit': head}
    hashes = {path: sha(git(tree, 'show', head + ':' + path)) for path in current_modules}
    added = set(git(tree, 'diff', '--name-only', '--diff-filter=A', base, head,
                    '--', 'tests').decode().splitlines())
    required = {path for path in current_modules
                if (path in added and path not in original['file_seconds'])
                or (path in old_hashes and hashes[path] != old_hashes[path])}
    require(required, 'no new or source-changed local module to refresh')
    for path in required:
        require((tree / path).is_file() and not (tree / path).is_symlink()
                and sha((tree / path).read_bytes()) == hashes[path], 'measured/current source mismatch')
    require(not args.output_dir.exists() and not args.output_dir.is_symlink(), 'fresh output required')
    verifier_spec = importlib.util.spec_from_file_location('integration_measurement_verifier',
        Path(__file__).with_name('plan_pr5213_integration_20261102.py'))
    verifier = importlib.util.module_from_spec(verifier_spec)
    verifier_spec.loader.exec_module(verifier)
    xml, rows, proofs, collection_proof = additional_measurements(tree, head, manifest['collection'],
        manifest['runs'], required, verifier)
    args.output_dir.mkdir(parents=True)
    normalized_dir = args.output_dir / 'normalized'
    normalized_dir.mkdir()
    ET.ElementTree(xml).write(normalized_dir / 'pytest.xml', encoding='utf-8', xml_declaration=True)
    builder_spec = importlib.util.spec_from_file_location('unchanged_round4_timing_builder', tree / UPDATER)
    builder = importlib.util.module_from_spec(builder_spec)
    builder_spec.loader.exec_module(builder)
    with builder_git_environment():
        measured = builder.build(normalized_dir, tree, original['source']['run_id'], head)
    require(set(measured['file_seconds']) == required and measured['source']['test_cases'] == len(rows),
            'unchanged builder disagrees with measured roster')
    result = deepcopy(original)
    result['file_seconds'].update(measured['file_seconds'])
    result['file_seconds'] = dict(sorted(result['file_seconds'].items()))
    update = {'kind': 'local_round4_new_or_changed_file_junit', 'measured_commit': head,
              'base_commit': base, 'base_timings_sha256': sha(base_weights),
              'file_seconds': measured['file_seconds'], 'test_cases': len(rows),
              'test_source_sha256': {path: hashes[path] for path in sorted(required)},
              'source_runs': proofs, 'retired_modules': retired_proofs,
              'collection': collection_proof,
              'input_manifest': {'path': str(args.additional_manifest), 'sha256': sha(manifest_raw)},
              'producer_sha256': sha(Path(__file__).read_bytes()), 'updater_sha256': sha(updater_raw),
              'limits': 'Local macOS/Python, at most two workers; scheduling estimates, not CI wall-time guarantees.'}
    result.setdefault('local_overrides', []).append(update)
    require(result['source'] == original['source'] and result['method'] == original['method'],
            'historical main timing provenance changed')
    combined_weights = {path: value for path, value in prior['local']['file_seconds'].items()
                        if path not in retired}
    combined_weights.update(measured['file_seconds'])
    combined_hashes = {path: value for path, value in old_hashes.items() if path not in retired}
    combined_hashes.update(update['test_source_sha256'])
    combined_commits = {path: value for path, value in old_source_commits.items() if path not in retired}
    combined_commits.update({path: head for path in required})
    combined_rows = [row for row in prior['cases'] if row['file'] not in required | retired] + rows
    after = encode(result)
    evidence = {
        'kind': 'composite_local_timing_projection_v1',
        'main_commit': prior['main_commit'], 'round3_commit': prior['round3_commit'],
        'main_entries_and_provenance_preserved': prior['main_entries_and_provenance_preserved'],
        'timings_sha256': sha(after),
        'local': {'kind': 'composite_projection_not_one_measurement',
                  'file_seconds': combined_weights, 'test_source_sha256': combined_hashes,
                  'test_cases': len(combined_rows)},
        'local_source_commits': combined_commits, 'cases': combined_rows,
        'additional_measurements': update,
        'preceding_integration_evidence': {'path': str(prior_path), 'sha256': sha(prior_raw)},
        'prior_timing_evidence': deepcopy(prior['prior_timing_evidence']),
        'installation_requested': args.install,
        'scope': 'Composite projection over explicitly identified source revisions. Historical measurement '
                 'metadata remains unchanged in the hash-linked predecessor; no single current-source measurement is claimed.'}
    target = tree / DURATIONS
    require(target.read_bytes() == base_weights, 'target weights changed since declared base')
    for name, raw in (('timings.json', after), ('evidence.json', encode(evidence))):
        with (args.output_dir / name).open('xb') as stream:
            stream.write(raw)
        require((args.output_dir / name).read_bytes() == raw, 'output persistence mismatch')
    if args.install:
        replacement = target.with_name(target.name + '.pr5213-round4-new')
        require(not replacement.exists() and not replacement.is_symlink(), 'fresh replacement required')
        with replacement.open('xb') as stream:
            stream.write(after)
        replacement.chmod(stat.S_IMODE(target.stat().st_mode))
        require(target.read_bytes() == base_weights, 'target changed before installation')
        os.replace(replacement, target)
        require(target.read_bytes() == after, 'installed weights differ')
        installation = encode({'target': str(target), 'installation_verified': True,
            'target_sha256': sha(target.read_bytes()), 'target_before_sha256': sha(base_weights),
            'generated_timings_sha256': sha((args.output_dir / 'timings.json').read_bytes()),
            'evidence_sha256': sha(encode(evidence)), 'producer_sha256': update['producer_sha256']})
        with (args.output_dir / 'installation.json').open('xb') as stream:
            stream.write(installation)
        require((args.output_dir / 'installation.json').read_bytes() == installation,
                'installation proof persistence mismatch')
    print(json.dumps({'measured_commit': head, 'refreshed_modules': sorted(required),
                      'cases': len(rows), 'retired_modules': sorted(retired),
                      'timings_sha256': sha(after), 'evidence_sha256': sha(encode(evidence)),
                      'installed': args.install}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, default=ROOT)
    parser.add_argument('--main-commit', default=MAIN)
    parser.add_argument('--round3-commit', default=ROUND3)
    parser.add_argument('--round3-evidence', type=Path, required=True)
    parser.add_argument('--prior-timing-evidence', type=Path, required=True)
    parser.add_argument('--fallback-module', action='append', default=[])
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    tree = args.tree.resolve()
    for head in (args.main_commit, args.round3_commit):
        require(re.fullmatch('[0-9a-f]{40}', head) is not None, 'full lowercase commit SHA required')
        require(git(tree, 'rev-parse', head + '^{commit}').decode().strip() == head,
                'commit identity differs')
    require(not args.output_dir.exists() and not args.output_dir.is_symlink(), 'fresh output directory required')
    target = tree / DURATIONS
    require(target.is_file() and not target.is_symlink(), 'regular duration target required')
    target_before = target.read_bytes()  # May contain the explicitly authorized merge conflict.
    main_raw = git(tree, 'show', args.main_commit + ':' + DURATIONS)
    original = json.loads(main_raw)
    require(original['schema_version'] == 1, 'timing schema changed')
    prior_raw = args.prior_timing_evidence.read_bytes()
    prior = json.loads(prior_raw)
    require(prior['refreshed_weights_sha256'] == sha(main_raw), 'prior projection does not bind main weights')
    updater_path = tree / UPDATER
    updater_raw = updater_path.read_bytes()
    require(updater_raw == git(tree, 'show', args.main_commit + ':' + UPDATER),
            'existing timing builder changed from main')
    added = git(tree, 'diff', '--name-only', '--diff-filter=A', args.main_commit,
                args.round3_commit, '--', 'tests').decode().splitlines()
    added = sorted(path for path in added if path.endswith('.py'))
    require(added, 'no added test modules')
    required = set(added) - original['file_seconds'].keys()
    require(required, 'no untimed added modules')
    test_hashes = {}
    for path in required:
        measured = git(tree, 'show', args.round3_commit + ':' + path)
        require((tree / path).read_bytes() == measured, f'{path}: current test differs from measured source')
        test_hashes[path] = sha(measured)
    modules = module_map(tree, args.round3_commit)
    extraction = [extract_shard(args.round3_evidence, index, args.round3_commit, modules, required)
                  for index in range(1, 7)]
    rows = [row for _, batch, _ in extraction for row in batch]
    require({row['file'] for row in rows} == required, 'missing measured added module')
    owners = {}
    for row in rows:
        require(owners.setdefault(row['file'], row['shard']) == row['shard'],
                'added module appears in multiple shards')
    # Preserve repeated parameter labels within the same owning artifact, as
    # the existing builder does; node identities are an occurrence multiset.
    fallback = sorted(set(args.fallback_module))
    for path in fallback:
        rel = Path(path)
        require(rel.parts and not rel.is_absolute() and '..' not in rel.parts and rel.parts[0] == 'tests'
                and path.endswith('.py') and (tree / path).is_file(), 'invalid fallback test module')
        require(path not in required and path not in original['file_seconds'],
                'fallback must be an unmeasured new module')
    # Mutations start only after all input and original-case proofs pass.
    args.output_dir.mkdir(parents=True)
    normalized_dir = args.output_dir / 'normalized'
    normalized_dir.mkdir()
    for index, (xml, batch, _) in enumerate(extraction, 1):
        if batch:
            directory = normalized_dir / f'local-shard{index}'
            directory.mkdir()
            ET.ElementTree(xml).write(directory / 'pytest.xml', encoding='utf-8', xml_declaration=True)
    spec = importlib.util.spec_from_file_location('pr5213_unchanged_timing_builder', updater_path)
    updater = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(updater)
    with builder_git_environment():
        measured = updater.build(normalized_dir, tree, original['source']['run_id'], args.round3_commit)
    require(set(measured['file_seconds']) == required, 'builder produced unexpected file roster')
    require(measured['source']['test_cases'] == len(rows), 'builder case count differs')
    result = deepcopy(original)
    result['file_seconds'] = dict(sorted({**original['file_seconds'], **measured['file_seconds']}.items()))
    require(all(result['file_seconds'][name] == value for name, value in original['file_seconds'].items()),
            'an existing main weight changed')
    local = {
        'kind': 'local_added_file_junit', 'measured_commit': args.round3_commit,
        'base_commit': args.main_commit, 'base_timings_sha256': sha(main_raw),
        'producer_sha256': sha(Path(__file__).read_bytes()), 'updater_sha256': sha(updater_raw),
        'method': 'Unchanged updater Decimal sum of passing local JUnit case times by added file; 0.001-second floor.',
        'file_seconds': measured['file_seconds'], 'test_cases': len(rows),
        'test_source_sha256': dict(sorted(test_hashes.items())),
        'original_shards': [proof for _, _, proof in extraction],
        'normalized_artifacts': measured['source']['artifacts'],
        'unmeasured_modules': fallback,
        'fallback_policy': 'No invented measurement is installed. The unchanged plugin uses the median known collected-file duration.',
        'limits': 'Local macOS/Python3.13, three pytest workers. JUnit case times are not runner-monotonic or CI wall-time guarantees. '
                  'The builder-generated GitHub source label is deliberately not used for these local observations.'}
    result.setdefault('local_overrides', []).append(local)
    require(result['source'] == original['source'] and result['method'] == original['method'],
            'original main provenance changed')
    after = encode(result)
    evidence = {
        'main_commit': args.main_commit, 'round3_commit': args.round3_commit,
        'main_timings_git_blob': git(tree, 'rev-parse', args.main_commit + ':' + DURATIONS).decode().strip(),
        'main_timings_sha256': sha(main_raw), 'timings_sha256': sha(after),
        'producer_sha256': local['producer_sha256'], 'updater_sha256': sha(updater_raw),
        'added_test_modules': added, 'measured_added_modules': sorted(required),
        'retained_main_entry_count': len(original['file_seconds']),
        'main_entries_and_provenance_preserved': True,
        'local': local, 'cases': rows,
        'prior_timing_evidence': {'path': str(args.prior_timing_evidence), 'sha256': sha(prior_raw),
                                  'wall_projection': prior['wall_projection']},
        'partition_status': 'Pending pinned integrated collection and both real plugin layouts; no budget acceptance here.',
        'installation_requested': args.install}
    for name, raw in (('main-timings.json', main_raw), ('timings.json', after), ('evidence.json', encode(evidence))):
        with (args.output_dir / name).open('xb') as stream:
            stream.write(raw)
        require((args.output_dir / name).read_bytes() == raw, f'{name}: output persistence mismatch')
    installed = False
    if args.install:
        require(target.read_bytes() == target_before, 'duration target changed during preparation')
        replacement = target.with_name(target.name + '.pr5213-integration-new')
        require(not replacement.exists() and not replacement.is_symlink(), 'fresh replacement required')
        with replacement.open('xb') as stream:
            stream.write(after)
        replacement.chmod(stat.S_IMODE(target.stat().st_mode))
        os.replace(replacement, target)
        require(target.read_bytes() == after, 'installed durations differ')
        installation = encode({
            'target': str(target), 'installation_verified': True,
            'target_sha256': sha(target.read_bytes()),
            'target_before_sha256': sha(target_before),
            'main_source_sha256': sha(main_raw),
            'generated_timings_sha256': sha((args.output_dir / 'timings.json').read_bytes()),
            'evidence_sha256': sha(encode(evidence)),
            'producer_sha256': local['producer_sha256']})
        with (args.output_dir / 'installation.json').open('xb') as stream:
            stream.write(installation)
        require((args.output_dir / 'installation.json').read_bytes() == installation,
                'installation proof persistence mismatch')
        installed = True
    print(json.dumps({'measured_modules': len(required), 'measured_cases': len(rows),
                      'retained_main_entries': len(original['file_seconds']),
                      'unmeasured_modules': fallback, 'timings_sha256': sha(after),
                      'evidence_sha256': sha(encode(evidence)), 'installed': installed}))


if __name__ == '__main__':
    if '--additional-manifest' in sys.argv:
        additional_main()
    else:
        main()
