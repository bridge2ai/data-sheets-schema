#!/usr/bin/env python3
"""Freeze #5213/D76 round-3 validation selections without launching tests (2026-11-02).

Inputs: clean pinned archive checkout, retained round-2 selection/probes, optional
terminal full collection. Outputs: fresh external rosters, hashes and serial CI
plan. The failures subcommand prepares exact-node baseline reruns; it neither
executes them nor converts reproduced failures into acceptance.
"""
import argparse
import ast
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import textwrap


BASELINES = {
    'round2': '0fa106e4d558c1c119e8f386222e225ac3acca24',
    'main': '87a8e7a80a8c215335ede4774e07193940f155fb',
}
HISTORICAL_SHA = 'fd0c7067b591409683ea92fc6de92cf7e6c730624687a57c5f5451fe5368f13c'
PRIOR_ROSTER_HASHES = {
    'historical107': HISTORICAL_SHA,
    'f5-notes-canary': 'b745a61dac9adb018a74aea7601edbbddaa8105e70b32c0b9a28cfb9f6f44957',
    'f5-notes-audit': 'ba4bf93081d9c8bc82d4762d2c3ac8301174b762cee9e6fd8df5204468a2e78e',
    'f5-tests': 'e4e0d1e90ea6d79643c2e7c0bf303754f89b3b76d5834435cd825d7937a2a856',
}
NEW_BASELINES = {
    'recorder': ('tests/test_wave7_5213_d76_round3_recorder.py',
        'aa48dc2c406a2d55cdcc316d15a238a0f15f7df622888a1e59334ce567781b13',
        '0fa-recorder-baseline9', 8, 1),
    'binding': ('tests/test_wave7_5213_d76_round3_binding.py',
        '2afcff6f1156f8715bc3746d132dd036d5c91d0a2f826b8a6f0a8e6aff3b15c2',
        '0fa-binding-baseline42', 35, 7),
    'replay-flag-v2': ('tests/test_wave7_5213_d76_round3_replay_flag.py',
        '26539d25fa47073e8b33b74661ce23d7fc0771330af1b433e9d40159d015dcba',
        '0fa-replay-flag-v2-baseline6', 6, 0),
}
PROBE_HASHES = {
    'codex-r2-20261101/test_postconstruction_admission.py': 'da5bfe1535cb810ee4b9700adb98d2788ccc86cb92bfb4f00a5a6dbb3591f19c',
    'codex-r2-20261101/test_postconstruction_binding.py': '6f6b0648dd23ad3f7499df4bec908432fb7c6baeeeb9216d3cda1c73f17f294d',
    'codex-r2-20261101/test_prior_adversarial.py': '56299298c1c9e65df8e64e90688481ab93e1e9bcaef2b3b73dc403c6a5cf8482',
    'codex-r2-20261101/test_recheck_edges.py': 'bf64b7e1834bf239331746c54cc60d15fbbe05a5d7a70c701054defd549dbc5a',
    'codex-r2-20261101/test_replace_portable.py': '5ebc95dbb971f9b4690f7ea6161f7be01dabc3fe0a41b0c61f1376218c057e07',
    'codex-r2-20261101/test_round2_adversarial.py': '7fa547b6f4c10e34974fa1ec7d78c33c222718e8a0b409f93e24ddcb775af468',
    'codex-r2-20261101/round2_binding_source.py': '893f136d901579acba2777da87fd475b8db3e71561746f9275f8ccadba540fb2',
    'codex-r2-20261101/round2_recorder_source.py': '52b096e07edcc04a26028ae6f1ef68a140b95a31abd7f7c6b0bbf4249b0edb42',
    'claude-r2-20261101/test_codex_r1_postconstruction_admission_original.py': 'da5bfe1535cb810ee4b9700adb98d2788ccc86cb92bfb4f00a5a6dbb3591f19c',
    'claude-r2-20261101/test_codex_r1_recheck_edges_adapted.py': 'd9975c4a6cea359f03e6965eec6afae4e44e0a2df3389fef1bb61a764d472d16',
    'claude-r2-20261101/test_codex_r1_recheck_edges_original.py': 'bf64b7e1834bf239331746c54cc60d15fbbe05a5d7a70c701054defd549dbc5a',
    'claude-r2-20261101/test_probe_arm_paths_more.py': 'b2a5160884a1c40db466f0cb093774432a3ac0cc9dcee4cf763e9e3252baf3ec',
    'claude-r2-20261101/test_probe_native_source_spelling.py': 'd68beb2a6265f562bd33591b18df6096ad66fec8096d47bec392b93666e26c3b',
    'claude-r2-20261101/test_probe_record_condition_cross_cwd.py': 'eb54229ddde107bb752d6aa46a76538b5bde64a558291b7a3ef7316db3fb44e0',
    'claude-r2-20261101/test_probe_recorder_residuals.py': 'a49fa816ca3b7f35df14bce35dd8778545aa94bf7279cfd102b79ed2ebc891fd',
    'claude-r2-20261101/test_probe_sg1_instruction_cwd.py': '56337856b253774eb4249c365c93be3f5276818c684dda22e81859a794c36ca3',
    'claude-r2-20261101/test_probe_sg2_conventional_manifest.py': 'b9034f02fed0012fa1bfd45d5b2d0c297924bef93190e2975f68d4dd9fda2489',
    'claude-r2-20261101/test_probe_sg2_corpus_root.py': '1487bd39e2052546705abe0dcee0112dae67b18df8b82857b2d1c3d2c2492105',
    'claude-r2-20261101/test_probe_sg2_display_fast.py': 'dde7591b9a51cfbe98695cbd12ab7cc522c3324ec55526dbfa9cea65ab82b84b',
    'claude-r2-20261101/test_r2_boundary_probes.py': 'f5228d207264d341151b493ede89169460ecd183efdf7f9c91226b07fe77d953',
    'claude-r2-20261101/test_r2_classification_proof.py': 'e833471e5cbbbdd1fb8687d823cd80f2956c901467c7813d4aaf8563376324ce',
    'claude-r2-20261101/test_r2_cross_corpus_recorder.py': 'fc21e6a4222af94cdc7c95e9be85e3c94d0a377220ff9cc24e56599fe56cdad8',
}
PROBE_GROUPS = {
    'reviewer-codex-assertions': ['test_prior_adversarial.py', 'test_replace_portable.py'],
    'reviewer-codex-original-diagnostics': ['test_recheck_edges.py'],
    'reviewer-codex-defect-observations': ['test_postconstruction_binding.py', 'test_postconstruction_admission.py'],
    'reviewer-codex-round2-mixed': ['test_round2_adversarial.py'],
    'reviewer-claude-assertions-and-observations': [
        'test_probe_arm_paths_more.py', 'test_probe_native_source_spelling.py',
        'test_probe_record_condition_cross_cwd.py', 'test_probe_recorder_residuals.py',
        'test_probe_sg1_instruction_cwd.py', 'test_probe_sg2_conventional_manifest.py',
        'test_probe_sg2_corpus_root.py', 'test_probe_sg2_display_fast.py',
        'test_r2_boundary_probes.py', 'test_r2_cross_corpus_recorder.py'],
    'reviewer-claude-classification-defect-observations': ['test_r2_classification_proof.py'],
    'reviewer-claude-original-diagnostics-duplicate': ['test_codex_r1_recheck_edges_original.py'],
    'reviewer-claude-adapted-diagnostics-supplement': ['test_codex_r1_recheck_edges_adapted.py'],
    'reviewer-claude-original-defect-duplicate': ['test_codex_r1_postconstruction_admission_original.py'],
}
PROBE_LIMITS = {
    'original_locator_diagnostics': {
        'function': 'test_registered_drift_refuses_before_any_client_access',
        'parameters': ['locator-bundle', 'locator-manifest', 'locator-chunk_manifest'],
        'meaning': 'Original regex expects the later diagnostic; literal failures remain failures. The existing Claude adaptation is supplemental, not a rewrite.'},
    'original_admission': {
        'function': 'test_relative_spelling_after_binding_reaches_provider_boundary',
        'meaning': 'Asserts the old fake-create defect. A failed old assertion may demonstrate a repair, but is never an acceptance pass.'},
    'codex_wrong_exception': {
        'function': 'test_replace_revalidates_and_does_not_copy_cached_instruction_or_binding',
        'meaning': 'Original expects ValueError for replace(init=False); retained TypeError mismatch. test_replace_portable.py is the separate correction.'},
    'claude_classification': {
        'function': 'test_other_names_are_invisible_to_the_roster',
        'parameters': ['input_authority', 'registered_inputs_v2', 'pinned_input_manifest'],
        'meaning': 'Asserts the old incomplete roster. New refusal intentionally fails this original probe; new committed tests prove acceptance.'},
    'print_only': {
        'functions': ['test_private_binding_replacement_bypasses_the_guard',
            'test_explicit_flag_disabled_and_binding_cleared',
            'test_pathlike_with_matching_str_but_other_fspath',
            'test_relative_instruction_from_another_corpus'],
        'meaning': 'Printed observations alone are not refusal/attestation assertions; inspect logs and use committed regressions.'},
    'copies_and_repeats': 'Identical original files in both reviewers and adapted repeats do not establish additional unique coverage.',
    'corpus_root_scope': 'The full six-case original file is retained; the previous Claude queue selected only inputs_dir/False. This plan does not claim the other five previously ran.',
}
WORKFLOW_STEPS = {
    'ordinary': 'Run the suite shard including corpus checks',
    'api': 'Run the required offline API case',
    'ci-offline-canary-budget': 'Exercise experimental canary admission offline',
    'ci-offline-canary-native': 'Exercise native canary transport and shutdown offline',
    'ci-offline-audit': 'Exercise native audit continuation controls offline',
    'ci-offline-evaluation': 'Exercise registered evaluation controls offline',
}
PROOFS = ('source_unchanged', 'hygiene_passed', 'origins_verified', 'helpers_unchanged',
          'targets_unchanged', 'sandbox_loaded', 'all_worker_collections_identical',
          'zero_guard_denials')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('regular existing file required: ' + str(path))
    return path.read_bytes()


def read(path):
    return json.loads(regular(path))


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def git_command(root, *args):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
    return ['git', '--no-replace-objects', '-c', 'protocol.allow=never', '-C', str(root), *args], env


def git(root, *args):
    command, env = git_command(root, *args)
    return subprocess.check_output(command, env=env)


def fresh_output(output, root):
    output = output.resolve()
    if output.exists() or output.is_relative_to(root):
        raise ValueError('fresh external output directory required')
    return output


def checked_head(root, expected):
    if not re.fullmatch('[0-9a-f]{40}', expected):
        raise ValueError('full source commit SHA required')
    if git(root, 'rev-parse', 'HEAD').decode().strip() != expected:
        raise ValueError('checkout HEAD differs')
    if git(root, 'status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('clean pinned source checkout required')
    return git(root, 'rev-parse', 'HEAD^{tree}').decode().strip()


def source_file(root, head, relative):
    raw = regular(root / relative)
    committed = git(root, 'show', head + ':' + relative)
    if raw != committed:
        raise ValueError('source bytes differ from pinned commit: ' + relative)
    return {'sha256': sha(raw), 'bytes': len(raw)}


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_functions(path):
    # Inventory only: do not import probes or execute parametrization/fixtures.
    names = []
    for node in ast.parse(regular(path)).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_'):
            names.append(node.name)
        elif isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
            names.extend(node.name + '.' + child.name for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith('test_'))
    return names


def workflow_commands(root):
    text = regular(root / '.github/workflows/main.yaml').decode()
    steps = {}
    for key, name in WORKFLOW_STEPS.items():
        match = re.search(r'^      - name: ' + re.escape(name) + r'\n(?P<body>.*?)(?=^      - |^  \S|\Z)', text, re.M | re.S)
        if not match:
            raise ValueError('missing frozen workflow step: ' + name)
        run = re.search(r'^        run: [>|]-?\n(?P<run>(?:^          .*\n|^\n)+)', match['body'], re.M)
        if not run:
            raise ValueError('unsupported workflow run form: ' + name)
        literal = textwrap.dedent(run['run']).rstrip()
        steps[key] = {'step_name': name, 'literal_run': literal}
    ordinary = steps['ordinary']['literal_run']
    for value in ('--ci-shard=${{ matrix.shard }}', '--ci-lane=ordinary', '-n logical', '--maxprocesses=4', '--dist load', '--maxschedchunk=1'):
        if value not in ordinary:
            raise ValueError('ordinary workflow contract changed: ' + value)
    if "'[1, 2, 3, 4, 5, 6]'" not in text:
        raise ValueError('workflow no longer selects six PR shards')
    for key in WORKFLOW_STEPS:
        if not key.startswith('ci-offline-'):
            continue
        command = shlex.split(steps[key]['literal_run'].replace('\\\n', ' '))
        start = command.index('pytest') + 1
        targets = []
        for value in command[start:]:
            if value.startswith('-'):
                break
            targets.append(value)
        steps[key]['targets'] = targets
    return steps


def terminal_run(directory, expected, collection=False):
    files = {name: read(directory / (name + '.json')) for name in
             ('plan', 'outcome', 'nodes', 'source-before', 'source-after')}
    plan, outcome = files['plan'], files['outcome']
    if plan['head'] != expected or files['source-before']['head'] != expected:
        raise ValueError('evidence head differs: ' + str(directory))
    if files['source-before'] != files['source-after'] or not all(outcome.get(key) is True for key in PROOFS):
        raise ValueError('evidence source/harness/import/hygiene proofs incomplete')
    if outcome.get('deadline_expired') or outcome.get('guard_denial_count') != 0:
        raise ValueError('deadline or guard-denial evidence cannot establish a terminal selection')
    # The reviewed failing-before cohorts use the retained round-2 phase-ledger
    # runner, which predates durable journals. Round-3 evidence must attest them.
    journal_runner = any(Path(value).name == 'run_d76_round3_validation_20261102.py'
                         for value in plan.get('command', []) if type(value) is str)
    if (journal_runner or 'phase_journals_valid' in outcome) and outcome.get('phase_journals_valid') is not True:
        raise ValueError('round3 phase journal proof missing or invalid')
    if collection:
        if not outcome.get('collection_passed') or plan.get('targets') != ['tests']:
            raise ValueError('successful full tests collection required')
    elif not outcome.get('node_accounting_complete'):
        raise ValueError('complete phase accounting required for failure extraction')
    return files


def before_manifest(root, head, evidence):
    result = {}
    for name, (module, digest, directory, failed, passed) in NEW_BASELINES.items():
        if source_file(root, head, module)['sha256'] != digest:
            raise ValueError('new regression differs from frozen failing-before blob: ' + module)
        row = {'final_module': module, 'sha256': digest, 'baseline_directory': directory,
               'reported_before_counts': {'failed': failed, 'passed': passed},
               'actual_before_verified': False}
        if evidence:
            run = evidence / directory
            files = terminal_run(run, BASELINES['round2'])
            targets = files['plan']['targets']
            if len(targets) != 1 or '::' in targets[0]:
                raise ValueError('new regression baseline requires exactly its frozen module target')
            target = Path(targets[0])
            if not target.is_absolute():
                raise ValueError('baseline must identify the exported original module absolutely')
            if sha(regular(target)) != digest or files['plan']['target_sha256'].get(str(target)) != digest:
                raise ValueError('baseline exported regression hash differs')
            counts = files['outcome']['counts']
            if counts.get('failed') != failed or counts.get('passed') != passed or any(
                    value for key, value in counts.items() if key not in ('failed', 'passed')):
                raise ValueError('baseline actual counts differ from reviewed disposition')
            mapping = []
            for node in files['nodes']['selected']:
                prefix, separator, suffix = node.partition('::')
                if not separator or not suffix or prefix not in ('', str(target), target.name):
                    raise ValueError('unrecognized single-file baseline node prefix: ' + node)
                mapping.append({'baseline_nodeid': node, 'final_nodeid': module + '::' + suffix})
            row.update(actual_before_verified=True, actual_before_counts=counts,
                exact_file_node_mapping=mapping,
                evidence_sha256={file: sha(regular(run / file)) for file in ('plan.json', 'outcome.json', 'nodes.json', 'pytest.xml')})
        result[name] = row
    return {'modules': result,
        'causal_limits': 'Controls need not fail before. The corrected G1 unshared-plan case reaches a later wrong chunk-identity refusal, not a write/spend boundary; five other corrected G1 cases expose bypasses. Original flawed G1 v1 evidence is retained but excluded from this exact manifest.',
        'join_policy': 'Map only a single hash-bound exported file to its exact final module; preserve the complete parameter suffix and occurrence multiplicity. No function-name glob or cross-file matching.'}


def freeze(args):
    root = args.tree.resolve(strict=True)
    output = fresh_output(args.output, root)
    tree_sha = checked_head(root, args.expect_head)
    probes = args.probes.resolve(strict=True)
    prior = args.prior_selection.resolve(strict=True)
    rosters, copied, hashes = {}, {}, {}
    for name, count in (('historical107', 107), ('f5-notes-canary', 3), ('f5-notes-audit', 4), ('f5-tests', 6)):
        raw = regular(prior / (name + '.json'))
        values = json.loads(raw)
        if not isinstance(values, list) or len(values) != count or len(set(values)) != count or not all(type(value) is str for value in values):
            raise ValueError('invalid retained roster: ' + name)
        if sha(raw) != PRIOR_ROSTER_HASHES[name]:
            raise ValueError('selection differs from retained exact bytes: ' + name)
        rosters[name], copied[name] = values, raw
    d76_files = sorted((root / 'tests').glob('test_wave7_5213_d76_*.py'))
    rosters['all-d76'] = [str(path.relative_to(root)) for path in d76_files if test_functions(path)]
    if not rosters['all-d76']:
        raise ValueError('empty D76 module roster')
    helpers_only = [str(path.relative_to(root)) for path in d76_files if not test_functions(path)]
    for relative in helpers_only:
        hashes[relative] = source_file(root, args.expect_head, relative)
    rosters['round3-new'] = [value for value in rosters['all-d76'] if '_round3_' in value]
    rosters['full-collection'] = ['tests']
    before = before_manifest(root, args.expect_head, args.baseline_evidence)
    for group, names in PROBE_GROUPS.items():
        reviewer = 'codex' if group.startswith('reviewer-codex') else 'claude'
        rosters[group] = [str(probes / (reviewer + '-r2-20261101') / name) for name in names]
    probe_inventory = {}
    for relative, digest in PROBE_HASHES.items():
        path = probes / relative
        raw = regular(path)
        if sha(raw) != digest:
            raise ValueError('original reviewer bytes changed: ' + relative)
        probe_inventory[relative] = {'sha256': digest, 'bytes': len(raw),
            'role': 'pytest module' if path.name.startswith('test_') else 'imported frozen fixture/classification helper',
            'top_level_test_functions': test_functions(path)}
    for reviewer in ('codex', 'claude'):
        actual = {str(path.relative_to(probes)) for path in (probes / (reviewer + '-r2-20261101')).glob('test_*.py')}
        expected = {name for name in PROBE_HASHES if name.startswith(reviewer + '-') and Path(name).name.startswith('test_')}
        if actual != expected:
            raise ValueError('reviewer test-file roster changed: ' + reviewer)
    for values in rosters.values():
        for value in values:
            path = Path(value.split('::', 1)[0])
            if value == 'tests':
                continue  # Whole tree is pinned; terminal collection supplies the node roster.
            if path.is_absolute():
                hashes[str(path)] = {'sha256': sha(regular(path)), 'bytes': path.stat().st_size}
            else:
                hashes[str(path)] = source_file(root, args.expect_head, str(path))
    steps = workflow_commands(root)
    hygiene_path = 'scripts/adhoc/d76_round3_hygiene_20261102.py'
    hashes[hygiene_path] = source_file(root, args.expect_head, hygiene_path)
    hygiene = load_module(root / hygiene_path, 'd76_plan_notes')
    notes_jobs = []
    for name, step in steps.items():
        if not name.startswith('ci-offline-'):
            continue
        if step['targets'] != list(hygiene.NOTES_TARGETS[name]):
            raise ValueError('runner notes targets differ from frozen workflow: ' + name)
        rosters[name] = step['targets']
        notes_jobs.append({'name': name, 'targets_json': name + '.json', 'workers': 0,
            'runner_flags': ['--notes-ci-job', name], 'fresh_archive_required': True,
            'collection_scope': 'own session only; not part of pytest tests collection',
            'pythonpath': list(hygiene.ci_paths(name)), 'workflow': step})
        for target in step['targets']:
            path = root / target
            # Directory selections are frozen by both commit and complete Python roster.
            members = [path] if path.is_file() else sorted(path.rglob('*.py'))
            if not members:
                raise ValueError('empty notes source selection: ' + target)
            for member in members:
                relative = str(member.relative_to(root))
                hashes[relative] = source_file(root, args.expect_head, relative)
    for relative in ('.github/workflows/main.yaml', 'utils/pytest_shard.py', 'utils/ci_test_durations.json'):
        hashes[relative] = source_file(root, args.expect_head, relative)
    selector = load_module(root / 'utils/pytest_shard.py', 'd76_plan_selector')
    api_lanes = list(selector.API_CASE_LANES)
    matrix = 'case: [' + ', '.join(api_lanes) + ']'
    if matrix not in (root / '.github/workflows/main.yaml').read_text():
        raise ValueError('API lane roster differs from workflow matrix')
    ci = [{'name': 'ordinary-' + str(index), 'targets': ['tests'], 'workers': 3,
           'runner_flags': ['--ci-shard', str(index)], 'workflow': steps['ordinary'],
           'pytest_selection_argv': ['tests', '-v', '-p', 'no:cacheprovider', '-p', 'utils.pytest_shard',
               '--ci-shard=' + str(index) + '/6', '--ci-shard-timings=utils/ci_test_durations.json',
               '--ci-lane=ordinary', '--durations=25', '-n', '3', '--dist', 'load', '--maxschedchunk=1'],
           'local_override': 'Task7 explicitly caps local workers at3; workflow uses -n logical --maxprocesses=4. Output/log/observer/sandbox options are runner additions.'}
          for index in range(1, 7)]
    ci += [{'name': 'api-' + lane, 'targets': ['tests'], 'workers': 0,
            'runner_flags': ['--ci-lane', lane], 'workflow': steps['api'],
            'pytest_selection_argv': ['tests', '-v', '-p', 'no:cacheprovider', '-p', 'utils.pytest_shard',
                '--ci-lane=' + lane, '--durations=25']} for lane in api_lanes]
    ci += notes_jobs
    collection = None
    if args.collection_run:
        files = terminal_run(args.collection_run, args.expect_head, collection=True)
        nodes = files['nodes']['collected']
        lanes = selector.partition_lanes(nodes)
        assignment = selector.balanced_files((node.split('::', 1)[0] for node in lanes['ordinary']),
                                             6, selector.read_weights(root / 'utils/ci_test_durations.json'))
        partitions = {'ci-ordinary-' + str(index) + '-expected': [node for node in lanes['ordinary']
            if assignment[node.split('::', 1)[0]] == index] for index in range(1, 7)}
        partitions.update({'ci-api-' + lane + '-expected': lanes[lane] for lane in api_lanes})
        if sum((Counter(values) for values in partitions.values()), Counter()) != Counter(nodes):
            raise ValueError('CI partition does not preserve full collection occurrence multiset')
        collected_modules = {node.split('::', 1)[0] for node in nodes}
        if not set(rosters['all-d76']) <= collected_modules:
            raise ValueError('full collection omitted a D76 test module')
        rosters.update(partitions)
        collection = {'run': str(args.collection_run), 'nodes_sha256': sha(regular(args.collection_run / 'nodes.json')),
                      'counts': {name: len(values) for name, values in partitions.items()},
                      'all_test_occurrences': len(nodes), 'exact_partition_verified': True}
    plan = {'head': args.expect_head, 'git_tree': tree_sha, 'tree': str(root),
        'planner_sha256': sha(regular(Path(__file__))), 'source_hashes': hashes,
        'historical_and_f5_input_hashes': {name: sha(raw) for name, raw in copied.items()},
        'target_counts': {name: len(values) for name, values in rosters.items()},
        'before_after_manifest': before,
        'helper_only_d76_files': helpers_only, 'reviewer_inventory': probe_inventory,
        'reviewer_dispositions': PROBE_LIMITS, 'ci_serial_sequence': ci, 'collection': collection,
        'f5_notes_sessions': {'f5-notes-canary': 'offline-canary', 'f5-notes-audit': 'offline-audit'},
        'execution_policy': 'No execution by planner. Targeted canary first, targeted cohorts, full collection, then 14 serial CI commands. Max3 workers; API/notes serial. Fresh notes archive per session.',
        'baseline_policy': {'heads': BASELINES, 'same_harness': 'Use the frozen final runner/helper bytes at both baseline heads; no production shims. Every failure requires literal trace classification; recurrence alone does not establish cause.',
            'absent_test': 'If an exact node file does not exist at a baseline, retain that fact and obtain an explicit frozen-test export; never silently substitute or drop it.'},
        'limits': 'Planning is not collection/execution/acceptance. Preserve duplicate occurrences. Historical/F5/probe repeats must not be summed as unique. No Linux/Python3.12, provider or scientific acceptance.'}
    checked_head(root, args.expect_head)
    output.mkdir(parents=True)
    for name, values in rosters.items():
        if name in copied:
            with (output / (name + '.json')).open('xb') as stream:
                stream.write(copied[name])
        else:
            save(output / (name + '.json'), values)
    plan['roster_sha256'] = {name: sha(regular(output / (name + '.json'))) for name in rosters}
    save(output / 'plan.json', plan)
    print(json.dumps({'head': args.expect_head, 'output': str(output), 'plan_sha256': sha(regular(output / 'plan.json'))}))


def failures(args):
    root = args.tree.resolve(strict=True)
    output = fresh_output(args.output, root)
    files = terminal_run(args.run, args.expect_head)
    phases = read(args.run / 'phase-accounting.json')
    if not phases.get('all_selected_completed'):
        raise ValueError('interrupted or unstarted failure run cannot supply a complete roster')
    occurrences = [row for row in phases['occurrences'] if row['status'] in ('failed', 'errors', 'xpassed')]
    if Counter(row['nodeid'] for row in phases['occurrences']) != Counter(files['nodes']['selected']):
        raise ValueError('phase occurrence roster differs from selected nodes')
    targets = list(dict.fromkeys(row['nodeid'] for row in occurrences))
    source_rows = {}
    for node in targets:
        relative = node.split('::', 1)[0]
        row = {'nodeid': node, 'source_file': relative, 'baseline_blobs': {}}
        for name, commit in BASELINES.items():
            if not relative or Path(relative).is_absolute():
                row['baseline_blobs'][name] = {'available': False, 'reason': 'external or blank-prefix node requires original probe provenance mapping'}
                continue
            command, env = git_command(root, 'show', commit + ':' + relative)
            completed = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            row['baseline_blobs'][name] = ({'available': True, 'sha256': sha(completed.stdout)} if completed.returncode == 0
                else {'available': False, 'reason': 'file absent at baseline; do not silently omit or substitute'})
        source_rows[node] = row
    plan = files['plan']
    result = {'final_head': args.expect_head, 'run': str(args.run), 'baseline_heads': BASELINES,
        'failed_occurrences': occurrences, 'unique_rerun_targets': targets, 'source_availability': source_rows,
        'original_selected_occurrences': len(files['nodes']['selected']), 'helpers': plan.get('helpers'),
        'notes_ci_job': plan.get('notes_ci_job'), 'workers': plan.get('workers'),
        'evidence_sha256': {name: sha(regular(args.run / name)) for name in
            ('plan.json', 'outcome.json', 'nodes.json', 'phase-accounting.json', 'pytest.xml', 'source-before.json', 'source-after.json')},
        'policy': 'Run each exact target at both named baseline heads under the same final harness and sandbox. Keep notes jobs separate. Original duplicate failures retained; rerun targets unique because the runner requires distinct target arguments. Recurrence is evidence, not automatic environmental attribution or a pass.',
        'acceptance': 'not_assessed', 'executed': False}
    output.mkdir(parents=True)
    save(output / 'targets.json', targets)
    save(output / 'failure-baseline-plan.json', result)
    print(json.dumps({'output': str(output), 'failed_occurrences': len(occurrences), 'unique_targets': len(targets)}))


def main():
    if not sys.dont_write_bytecode:
        raise ValueError('run this planning helper with Python -B; frozen sources must not gain bytecode')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('freeze', 'failures'):
        sub = commands.add_parser(name)
        sub.add_argument('--tree', type=Path, required=True)
        sub.add_argument('--expect-head', required=True)
        sub.add_argument('--output', type=Path, required=True)
        if name == 'freeze':
            sub.add_argument('--probes', type=Path, required=True, help='scratch-5213r2check/scripts/adhoc')
            sub.add_argument('--prior-selection', type=Path, required=True, help='round2/0fa-selection')
            sub.add_argument('--collection-run', type=Path, help='terminal final-head full-collection evidence; optional before collection')
            sub.add_argument('--baseline-evidence', type=Path, help='round3 evidence root; verifies exact single-file failing-before mappings')
        else:
            sub.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    (freeze if args.command == 'freeze' else failures)(args)


if __name__ == '__main__':
    main()
