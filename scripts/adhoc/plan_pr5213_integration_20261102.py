#!/usr/bin/env python3
"""Freeze and audit the #5213/#5212 integration selections, 2026-11-02.

Inputs: exact clean archive, terminal full collection, optional timing provenance
and explicit completed-run manifest. Outputs: new external JSON only. No test
execution, downloads, source edits, moving-ref baseline or outcome relabelling.
"""
import argparse
import ast
from collections import Counter, defaultdict, deque
import hashlib
import heapq
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASELINES = {'main': 'ddfd45c3b520d37da247cf899401437794880e0c',
             'round3': 'd13c1711e19dcdcc7f624b66e15b735ebc0aab8f'}
PATTERN = (r'latch_journal|refuse_legacy_execution|require_selected_resume_owner|'
           r'output_ownership|owned_artifacts|_legacy_evidence|_fresh_location')
EXPLICIT = ('tests/test_abandoned_journal.py', 'tests/test_pr5212_round6_startup.py')
NOTES = 'notes/matched_cborg_2026-09-13/test_budgeted_cborg.py'
SG2_PREFIX = ('tests/test_wave7_5213_d76_registration.py::'
              'test_sg2_root_launch_completes_and_records_registered_paths')
SG2 = [SG2_PREFIX + '[' + kind + ']' for kind in ('none', 'explicit', 'conventional')]
MINIMUM_DIRECT = {
    'test_api_latch_guard.py', 'test_d42_claude_d55.py', 'test_d68_legacy_readonly.py',
    'test_d69_artifact_completeness.py', 'test_d69_fail_closed.py',
    'test_d69_round4_ownership.py', 'test_d69_round5_boundaries.py',
    'test_d69_round5_launch.py', 'test_d70_record_age.py', 'test_download/test_api_runner.py',
    'test_generation_recovery_review.py', 'test_latch_journal.py',
    'test_pr5212_d55_fixes.py', 'test_pr5212_r3_fixes.py', 'test_pr5212_r4_fixes.py',
    'test_pr5212_round7_journal.py', 'test_receipt_completion_runtime.py',
    'test_registered_eval_runner.py', 'test_report_gate.py',
    'test_shared_generation_completed_replay.py', 'test_shared_generation_resources.py',
    'test_shared_generation_runtime.py', 'test_shared_output_ownership.py',
    'test_shared_output_ownership_entrypoints.py', 'test_shared_schema_sync_resources.py',
    'test_thinking_request.py', 'test_unusable_snapshot.py', 'test_usage_ledger.py',
}
PROOFS = ('source_unchanged', 'hygiene_passed', 'origins_verified', 'helpers_unchanged',
          'targets_unchanged', 'sandbox_loaded', 'zero_guard_denials',
          'all_worker_collections_identical', 'phase_journals_valid')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def offline_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')
           and not re.search(r'API_KEY|ACCESS_KEY|SECRET|TOKEN|CREDENTIAL', k, re.I)
           and not k.upper().endswith('_PROXY')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_CONFIG_GLOBAL='/dev/null',
               GIT_CONFIG_NOSYSTEM='1', GIT_OPTIONAL_LOCKS='0',
               GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='protocol.allow', GIT_CONFIG_VALUE_0='never')
    return env


def git(tree, *args):
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(tree), *args],
                                   env=offline_env()).decode()


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_identity(tree, head):
    actual = git(tree, 'rev-parse', 'HEAD').strip()
    if actual != head or not re.fullmatch(r'[0-9a-f]{40}', head):
        raise ValueError('exact full source HEAD required')
    if git(tree, 'status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('source must be clean')
    return {'head': head, 'git_tree': git(tree, 'rev-parse', 'HEAD^{tree}').strip()}


def producer_identity():
    """Keep the evidence producer revision distinct from the tested source."""
    tree = HERE.parents[1]
    identity = source_identity(tree, git(tree, 'rev-parse', 'HEAD').strip())
    return {'producer_head': identity['head'], 'producer_git_tree': identity['git_tree']}


def function_bytes(raw, name):
    text = raw.decode('utf-8')
    matches = [node for node in ast.parse(text).body
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    if len(matches) != 1:
        raise ValueError('expected exactly one top-level function: ' + name)
    node = matches[0]
    start = min([node.lineno] + [dec.lineno for dec in node.decorator_list])
    return b''.join(raw.splitlines(keepends=True)[start - 1:node.end_lineno])


def invariants(tree):
    rows = []
    for path, names in (
        ('src/data_sheets_schema/api_runner.py', ['_prelock_checks']),
        ('src/data_sheets_schema/latch_journal.py', ['refuse_legacy_execution', '_legacy_evidence'])):
        main = git(tree, 'show', BASELINES['main'] + ':' + path).encode()
        current = (tree / path).read_bytes()
        for name in names:
            before, after = function_bytes(main, name), function_bytes(current, name)
            if before != after:
                raise ValueError('merged-main function changed: ' + path + ':' + name)
            rows.append({'path': path, 'function': name, 'byte_identical_to_main': True,
                         'sha256': hashlib.sha256(after).hexdigest()})
    protected = ['src/data_sheets_schema/shared_generation.py',
                 'src/download/prompts/canonical_hashes.yaml', '.github', 'data']
    difference = git(tree, 'diff', '--name-only', BASELINES['main'], 'HEAD', '--', *protected)
    if difference:
        raise ValueError('protected paths differ from merged main: ' + difference)
    return {'main_head': BASELINES['main'], 'functions': rows, 'protected_paths': protected,
            'protected_diff_empty': True, 'method': 'Exact UTF-8 source lines including decorators, body and literal whitespace; no ast.unparse.'}


def require_collection(plan, nodes, outcome):
    if not outcome.get('collection_complete') or outcome['returncode'] != 0:
        raise ValueError('complete successful full collection required')
    if (plan['targets'] != ['tests'] or plan.get('collect_only') is not True
            or any(plan.get(key) for key in ('ci_shard', 'ci_lane', 'ci_ordinary_shard_of_6', 'ci_api_lane', 'notes_ci_job'))
            or Counter(nodes['collected']) != Counter(nodes['selected'])):
        raise ValueError('reference must be unfiltered whole tests/ collection')


def run_evidence(directory, head, collection=False):
    directory = Path(directory)
    names = ['plan.json', 'outcome.json', 'nodes.json', 'phase-accounting.json',
             'source-before.json', 'source-after.json', 'pytest-command.json']
    plan, outcome, nodes, phases, before, after, command = [read(directory / n) for n in names]
    if plan['head'] != head or before != after or before.get('head') != head:
        raise ValueError('run source identity differs: ' + str(directory))
    archive = Path(plan['archive_proof'])
    proof = read(archive)
    if (sha(archive) != plan['archive_proof_sha256'] or proof['head'] != head
            or proof['git_tree'] != plan['git_tree'] or before['tree'] != plan['git_tree']
            or proof['destination'] != plan['worktree'] or not before['tracked_exact']):
        raise ValueError('run archive/source pin differs')
    if (not all(outcome.get(key) is True for key in PROOFS)
            or outcome.get('deadline_expired') is not False
            or outcome['counts'] != phases['counts']):
        raise ValueError('run provenance/accounting proof failed: ' + str(directory))
    if collection:
        require_collection(plan, nodes, outcome)
        if any(str(arg).startswith(('--ci-shard', '--ci-lane')) for arg in command['argv']):
            raise ValueError('full collection command contains a CI selector')
    elif not outcome.get('node_accounting_complete'):
        raise ValueError('incomplete test occurrence accounting')
    return {'plan': plan, 'outcome': outcome, 'nodes': nodes, 'phases': phases,
            'command': command, 'files': {n: sha(directory / n) for n in names}}


def roster(tree):
    # -uu searches ignored and hidden files; no following symlinks or Git filters.
    argv = ['rg', '-l', '-uu', '--glob', 'test_*.py', PATTERN, 'tests', 'notes']
    result = subprocess.run(argv, cwd=tree, env=offline_env(), capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError('ignore-independent search failed: ' + result.stderr)
    direct = sorted(set(result.stdout.splitlines()))
    if not {'tests/' + name for name in MINIMUM_DIRECT}.issubset(direct):
        raise ValueError('approved original 28-file roster unexpectedly shrank')
    tracked = set(git(tree, 'ls-files', '-z').split('\0'))
    selected = sorted(set(direct).union(EXPLICIT))
    for name in selected:
        if name not in tracked or (tree / name).is_symlink():
            raise ValueError('matched test is not a frozen regular tracked file: ' + name)
    d76 = sorted(name for name in tracked if re.fullmatch(r'tests/test_wave7_5213_d76_[^/]+\.py', name))
    if not d76:
        raise ValueError('missing D76 modules')
    return direct, selected, d76, {'argv': argv, 'returncode': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr, 'ignored_and_hidden_included': True}


def module_nodes(full, modules):
    modules = set(modules)
    selected = [node for node in full if node.split('::', 1)[0] in modules]
    if {node.split('::', 1)[0] for node in selected} != modules:
        raise ValueError('one or more requested modules have no collected nodes')
    return selected


def without_occurrences(full, separate):
    pending = Counter(separate)
    if pending - Counter(full):
        raise ValueError('separate cohort contains an occurrence outside the full requested roster')
    grouped = []
    for node in full:
        if pending[node]:
            pending[node] -= 1
        else:
            grouped.append(node)
    if Counter(grouped) + Counter(separate) != Counter(full):
        raise ValueError('split cohorts do not exactly cover requested occurrences')
    return grouped


def journal_split(full, census, scheduled_sg2):
    """Credit SG2 only where the already-scheduled occurrences join this roster."""
    overlap = Counter(full) & Counter(scheduled_sg2)
    if overlap & Counter(census):
        raise ValueError('writer census and separately scheduled SG2 must not overlap')
    separate_sg2 = list(overlap.elements())
    grouped = without_occurrences(full, [*census, *separate_sg2])
    if any(node in scheduled_sg2 for node in grouped):
        raise ValueError('journal contains an SG2 occurrence without a separate execution')
    if Counter(grouped) + Counter(census) + overlap != Counter(full):
        raise ValueError('journal groups do not exactly cover requested occurrences')
    return grouped, separate_sg2


def freeze(args):
    identity = source_identity(args.tree, args.head)
    evidence = run_evidence(args.collection, args.head, collection=True)
    if evidence['plan']['worktree'] != str(args.tree):
        raise ValueError('collection must use the exact planning archive')
    full = evidence['nodes']['collected']
    if Counter(full) != Counter(evidence['nodes']['selected']):
        raise ValueError('full collection was filtered')
    direct, journal, d76, search = roster(args.tree)
    if not args.ordering.startswith('tests/') or not args.ordering.endswith('.py'):
        raise ValueError('explicit ordering module required')
    changed_notes = sorted(name for name in git(args.tree, 'diff', '--name-only',
        BASELINES['round3'] + '...' + BASELINES['main'], '--', 'notes').splitlines() if name.endswith('.py'))
    if changed_notes != [NOTES]:
        raise ValueError('incoming notes changes differ; review the scope before running')
    groups = {'d76': module_nodes(full, d76), 'journal-owner-legacy': module_nodes(full, journal),
              'ordering': module_nodes(full, [args.ordering]),
              'ci-sharding': module_nodes(full, ['tests/test_ci_sharding.py']),
              'writer-census': module_nodes(full, ['tests/test_d69_artifact_completeness.py'])}
    if any(Counter(groups['d76'])[node] != 1 for node in SG2):
        raise ValueError('each of the three SG2 cases must appear exactly once')
    groups['d76-without-sg2'] = [node for node in groups['d76'] if node not in SG2]
    groups['journal-without-census'], journal_sg2 = journal_split(
        groups['journal-owner-legacy'], groups['writer-census'], SG2)
    groups['notes-budget'] = [NOTES]
    for node in SG2:
        groups['sg2-' + node.rsplit('[', 1)[1][:-1]] = [node]
    # SG2 is executed once in its serial groups and credited to both applicable
    # rosters. Census and ordering remain separate obligations with honest overlap.
    if args.output.exists():
        raise ValueError('fresh selection directory required')
    args.output.mkdir(parents=True)
    files = {}
    for name, nodes in groups.items():
        path = args.output / (name + '.json')
        save(path, nodes)
        files[name] = {'path': str(path), 'sha256': sha(path), 'occurrences': len(nodes)}
    source_files = sorted(set(journal + d76 + [args.ordering, NOTES, 'tests/test_ci_sharding.py',
        'scripts/adhoc/d70_corpus_eligibility_20261030.py']))
    save(args.output / 'plan.json', {**identity, **producer_identity(),
        'source': str(args.tree), 'baseline_heads': BASELINES,
        'main_invariants': invariants(args.tree),
        'collection': str(args.collection), 'collection_artifact_sha256': evidence['files'],
        'search': search, 'direct_modules': direct, 'explicit_modules': list(EXPLICIT),
        'journal_owner_legacy_modules': journal, 'd76_modules': d76,
        'notes_changed_incoming': changed_notes, 'groups': files,
        'journal_separately_scheduled_sg2': journal_sg2,
        'journal_split_exact_counter': (Counter(groups['journal-without-census'])
            + Counter(groups['writer-census']) + Counter(journal_sg2)
            == Counter(groups['journal-owner-legacy'])),
        'diagnostic_only_groups': ['d76', 'journal-owner-legacy'],
        'source_file_sha256': {name: sha(args.tree / name) for name in source_files},
        'execution': {'maximum_workers': 2, 'one_controller': True, 'sg2_workers': 0,
            'sg2_deadline_seconds': 1800, 'notes_job': 'ci-offline-canary-budget',
            'notes_workers': 0, 'full_shards_permitted': False},
        'census_ref': args.head, 'census_scope': 'both writer/artifact and committed-record eligibility',
        'helper_sha256': sha(__file__)})


def partition(nodes, plugin, weights, total):
    lanes = plugin.partition_lanes(nodes)
    ordinary = lanes['ordinary']
    assignment = plugin.balanced_files({n.split('::', 1)[0] for n in ordinary}, total, weights)
    shards = [[n for n in ordinary if assignment[n.split('::', 1)[0]] == i]
              for i in range(1, total + 1)]
    api = {k: v for k, v in lanes.items() if k != 'ordinary'}
    joined = Counter(n for group in shards for n in group)
    for group in api.values():
        joined.update(group)
    if joined != Counter(nodes):
        raise ValueError('ordinary/API partition does not equal full collection Counter')
    if sum(len(group) for group in shards) != len(ordinary):
        raise ValueError('ordinary occurrence coverage mismatch')
    return shards, api


def projected_shards(shards, weights, rows, plugin, allowance):
    # Reproduce #5212's stable case ordering and four-worker greedy model. The
    # local validation worker cap is two; this estimates the unchanged CI job.
    times = defaultdict(deque)
    for row in rows:
        seconds = row['seconds']
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('invalid case duration')
        times[row['nodeid']].append(seconds)
    output = []
    for index, nodes in enumerate(shards, 1):
        counts = Counter(n.split('::', 1)[0] for n in nodes)
        priorities = plugin._estimates(counts, weights)
        ordered = sorted(nodes, key=lambda n: -priorities[n.split('::', 1)[0]] / counts[n.split('::', 1)[0]])
        workers = [(0.0, worker) for worker in range(4)]
        heapq.heapify(workers)
        for node in ordered:
            if not times[node]:
                raise ValueError('missing measured or declared fallback timing: ' + node)
            free, worker = heapq.heappop(workers)
            heapq.heappush(workers, (free + times[node].popleft(), worker))
        simulated = max(t for t, _ in workers)
        limit = 2160 if len(shards) == 6 else 2880
        output.append({'shard': index, 'cases': len(nodes), 'files': len(counts),
            'simulated_four_worker_seconds': simulated, 'allowance_seconds': allowance,
            'projected_job_seconds': simulated + allowance, 'limit_seconds': limit,
            'within_limit': simulated + allowance <= limit})
    if any(times.values()):
        raise ValueError('unexpected excess timing rows')
    return output


def timing_source_revisions(tree, evidence, manifest_path, final_head):
    """Bind explicitly reviewed source changes without relabelling old timings.

    This checks source identities and review scope, not timing equivalence.
    A prior-revision observation remains an estimate for the revised test.
    """
    measured = evidence['local']['test_source_sha256']
    current = {path: sha(tree / path) for path in measured}
    changed = {path for path in measured if current[path] != measured[path]}
    if manifest_path is None:
        if changed:
            raise ValueError('locally measured test source changed without a reviewed transition: '
                             + ', '.join(sorted(changed)))
        return {}, None

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate timing source-revision key: ' + key)
            result[key] = value
        return result

    raw = Path(manifest_path).read_bytes()
    manifest = json.loads(raw, object_pairs_hook=unique)
    if (type(manifest) is not dict or set(manifest) != {'format', 'transitions'}
            or manifest['format'] != 'timing_source_revisions_v1'
            or type(manifest['transitions']) is not list):
        raise ValueError('invalid timing source-revision manifest')
    fields = {'path', 'measured_commit', 'measured_file_sha256', 'revised_commit',
              'revised_file_sha256', 'patch_sha256', 'issue', 'disposition'}
    entries = {}
    for entry in manifest['transitions']:
        if (type(entry) is not dict or set(entry) != fields
                or any(type(value) is not str or not value.strip() for value in entry.values())
                or entry['disposition'] != 'reuse_prior_revision_measurement'):
            raise ValueError('invalid timing source-revision transition')
        path = entry['path']
        relative = Path(path)
        if (relative.is_absolute() or '..' in relative.parts or relative.as_posix() != path
                or not path.startswith('tests/') or not path.endswith('.py')
                or path not in measured or (tree / path).is_symlink()):
            raise ValueError('invalid measured test path in timing transition: ' + path)
        if path in entries:
            raise ValueError('duplicate timing source-revision transition: ' + path)
        for key in ('measured_commit', 'revised_commit'):
            if not re.fullmatch(r'[0-9a-f]{40}', entry[key]):
                raise ValueError('full source commit required in timing transition')
        for key in ('measured_file_sha256', 'revised_file_sha256', 'patch_sha256'):
            if not re.fullmatch(r'[0-9a-f]{64}', entry[key]):
                raise ValueError('full source/patch digest required in timing transition')
        entries[path] = entry
    if set(entries) != changed:
        raise ValueError('timing transitions must cover exactly the changed measured files; '
                         f'missing={sorted(changed - set(entries))}, extra={sorted(set(entries) - changed)}')
    if not re.fullmatch(r'[0-9a-f]{40}', final_head or '') or git(tree, 'rev-parse', 'HEAD').strip() != final_head:
        raise ValueError('timing transitions require the exact final source HEAD')
    applications = {}
    for path, entry in entries.items():
        if (entry['measured_commit'] != evidence['round3_commit']
                or entry['measured_commit'] != evidence['local']['measured_commit']
                or entry['measured_file_sha256'] != measured[path]
                or entry['revised_file_sha256'] != current[path]):
            raise ValueError('timing transition differs from measured/current source identity: ' + path)
        for key in ('measured_commit', 'revised_commit'):
            if git(tree, 'rev-parse', entry[key] + '^{commit}').strip() != entry[key]:
                raise ValueError('timing transition commit identity differs: ' + path)
        try:
            git(tree, 'merge-base', '--is-ancestor', entry['revised_commit'], final_head)
        except subprocess.CalledProcessError as exc:
            raise ValueError('revised timing source is not an ancestor of final HEAD: ' + path) from exc
        old = git(tree, 'show', entry['measured_commit'] + ':' + path).encode()
        revised = git(tree, 'show', entry['revised_commit'] + ':' + path).encode()
        if (hashlib.sha256(old).hexdigest() != entry['measured_file_sha256']
                or hashlib.sha256(revised).hexdigest() != entry['revised_file_sha256']
                or (tree / path).read_bytes() != revised):
            raise ValueError('timing transition Git blobs differ from declared source: ' + path)
        patch = git(tree, 'diff', '--no-ext-diff', '--no-textconv', '--no-renames',
                    '--no-color', '--binary', '--full-index', '--src-prefix=a/', '--dst-prefix=b/',
                    '--no-relative', '--unified=3', entry['measured_commit'],
                    entry['revised_commit'], '--', path).encode()
        if not patch or hashlib.sha256(patch).hexdigest() != entry['patch_sha256']:
            raise ValueError('reviewed timing source patch differs: ' + path)
        applications[path] = dict(entry)
    return applications, {'path': str(manifest_path), 'sha256': hashlib.sha256(raw).hexdigest(),
        'final_head': final_head, 'transitions': applications,
        'scope': 'Exact reviewed source transitions; reused measurements remain from the prior test revision. '
                 'Source/diff verification does not establish timing equivalence.'}


def projection_rows(tree, full, plugin, weights, evidence_path, source_revisions=None, final_head=None):
    evidence = read(evidence_path)
    if (evidence['main_commit'] != BASELINES['main']
            or evidence['round3_commit'] != BASELINES['round3']
            or evidence['timings_sha256'] != sha(tree / 'utils/ci_test_durations.json')
            or evidence['main_entries_and_provenance_preserved'] is not True):
        raise ValueError('timing provenance does not bind the declared source weights')
    prior_path = Path(evidence['prior_timing_evidence']['path'])
    if sha(prior_path) != evidence['prior_timing_evidence']['sha256']:
        raise ValueError('prior timing evidence changed')
    prior = read(prior_path)
    main_raw = git(tree, 'show', BASELINES['main'] + ':utils/ci_test_durations.json').encode()
    if prior['refreshed_weights_sha256'] != hashlib.sha256(main_raw).hexdigest():
        raise ValueError('prior timing observations do not bind main weights')
    revisions, revision_proof = timing_source_revisions(tree, evidence, source_revisions, final_head)
    local_files = set(evidence['local']['file_seconds'])
    observed = defaultdict(deque)
    for row in prior['cases']:
        if row['file'] not in local_files:
            observed[row['nodeid']].append(row)
    for row in evidence['cases']:
        if row['file'] not in local_files or row['outcome'] != 'passed':
            raise ValueError('invalid local added-file observation')
        observed[row['nodeid']].append(row)
    ordinary = plugin.partition_lanes(full)['ordinary']
    counts = Counter(node.split('::', 1)[0] for node in ordinary)
    estimated = plugin._estimates(counts, weights)
    rows, fallbacks = [], []
    for node in ordinary:
        if observed[node]:
            row = observed[node].popleft()
            revision = revisions.get(row['file'])
            rows.append({**row, 'timing_basis': 'observed_prior_test_revision' if revision else 'observed',
                         **({'source_revision': revision} if revision else {})})
        else:
            module = node.split('::', 1)[0]
            row = {'nodeid': node, 'file': module, 'seconds': estimated[module] / counts[module],
                'origin': 'declared_equal_case_share_of_plugin_file_estimate',
                'timing_basis': 'unmeasured_projection_only',
                'module_weight_basis': 'recorded_weight' if module in weights else 'plugin_median_fallback'}
            rows.append(row)
            fallbacks.append(row)
    projection = prior['wall_projection']
    if projection != evidence['prior_timing_evidence']['wall_projection']:
        raise ValueError('prior empirical projection allowance differs')
    allowance = projection['allowance_minutes'] * 60
    if not math.isfinite(allowance) or allowance < 0:
        raise ValueError('invalid empirical projection allowance')
    return rows, allowance, {'evidence': str(evidence_path), 'sha256': sha(evidence_path),
        'prior_evidence': str(prior_path), 'prior_sha256': sha(prior_path),
        'empirical_allowance': projection, 'unmeasured_cases': fallbacks,
        'reviewed_source_revisions': revision_proof,
        'prior_test_revision_cases': [row for row in rows if row['timing_basis'] == 'observed_prior_test_revision'],
        'unused_prior_observations': [row for queue in observed.values() for row in queue],
        'fallback_limit': 'Equal per-case file share is an explicit assumption, not a measured bound or CI guarantee.'}


def partitions(args):
    identity = source_identity(args.tree, args.head)
    proof = run_evidence(args.collection, args.head, collection=True)
    if proof['plan']['worktree'] != str(args.tree):
        raise ValueError('collection must use the exact partition archive')
    full = proof['nodes']['collected']
    site = Path(sys.executable).parent.parent / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    sys.path.append(str(site))  # no site/.pth execution; frozen plugin needs pytest
    plugin = load_file('integration_pinned_sharding', args.tree / 'utils/pytest_shard.py')
    current = plugin.read_weights(args.tree / 'utils/ci_test_durations.json')
    old_raw = git(args.tree, 'show', BASELINES['main'] + ':utils/ci_test_durations.json')
    old = json.loads(old_raw)['file_seconds']
    rows, allowance, timing_proof = projection_rows(args.tree, full, plugin, current,
        args.timing_evidence, args.timing_source_revisions, args.head)
    ordinary = plugin.partition_lanes(full)['ordinary']
    if Counter(row['nodeid'] for row in rows) != Counter(ordinary):
        raise ValueError('projection timing rows must join the full ordinary occurrence Counter')
    if args.output.exists():
        raise ValueError('fresh partition output required')
    args.output.mkdir(parents=True)
    scenarios = []
    for label, weights in (('before-main-weights', old), ('after-integration-weights', current)):
        for total in (6, 4):
            shards, api = partition(full, plugin, weights, total)
            for i, selected in enumerate(shards, 1):
                save(args.output / f'{label}-{i}-of-{total}.json', selected)
            scenarios.append({'weights': label, 'shards': total,
                'exact_full_counter': True, 'api_lanes': api,
                'projection': projected_shards(shards, weights, rows, plugin, allowance)})
    save(args.output / 'projection-cases.json', rows)
    save(args.output / 'partition-proof.json', {**identity, **producer_identity(),
        'full_occurrences': len(full),
        'unique_nodeids': len(set(full)), 'collection_hashes': proof['files'],
        'plugin_sha256': sha(args.tree / 'utils/pytest_shard.py'),
        'weights_sha256': sha(args.tree / 'utils/ci_test_durations.json'),
        'main_weights_sha256': hashlib.sha256(old_raw.encode()).hexdigest(),
        'projection_provenance': timing_proof,
        'projection_cases_sha256': sha(args.output / 'projection-cases.json'),
        'scenarios': scenarios,
        'all_after_within_limits': all(row['within_limit'] for s in scenarios
            if s['weights'] == 'after-integration-weights' for row in s['projection']),
        'limits_already_eighty_percent': True,
        'scope': 'Exact selection proof and empirical four-worker CI projection; no shards executed, no wall-time guarantee.',
        'helper_sha256': sha(__file__)})


def report(args):
    plan = read(args.plan)
    manifest = read(args.manifest)
    if manifest['head'] != plan['head']:
        raise ValueError('manifest differs from frozen selection head')
    selections = {}
    for group, target in plan['groups'].items():
        if sha(target['path']) != target['sha256']:
            raise ValueError('selection changed')
        selections[group] = read(target['path'])
    scheduled_sg2 = [node for group, nodes in selections.items()
                     if group.startswith('sg2-') for node in nodes]
    if Counter(scheduled_sg2) != Counter(SG2):
        raise ValueError('separately scheduled SG2 selection differs')
    journal_grouped, journal_sg2 = journal_split(selections['journal-owner-legacy'],
        selections['writer-census'], scheduled_sg2)
    if (Counter(journal_grouped) != Counter(selections['journal-without-census'])
            or Counter(journal_sg2) != Counter(plan.get('journal_separately_scheduled_sg2', []))
            or plan.get('journal_split_exact_counter') is not True):
        raise ValueError('frozen journal split differs from its exact occurrence union')
    rows, covered = [], set()
    for item in manifest['runs']:
        group = item['group']
        if group not in plan['groups'] or group in covered:
            raise ValueError('unexpected/repeated group in integration manifest')
        covered.add(group)
        target = plan['groups'][group]
        if sha(target['path']) != target['sha256']:
            raise ValueError('selection changed')
        expected = read(target['path'])
        result = run_evidence(item['directory'], plan['head'])
        if group == 'notes-budget':
            if result['plan']['targets'] != expected or result['plan'].get('notes_ci_job') != 'ci-offline-canary-budget':
                raise ValueError('notes session does not match its separate declared scope')
            expected = result['nodes']['collected']
        if Counter(result['nodes']['selected']) != Counter(expected):
            raise ValueError('run selection differs from exact requested Counter: ' + group)
        if result['outcome']['worker_count'] > 2:
            raise ValueError('integration exceeded two workers')
        if group.startswith('sg2-'):
            if (result['outcome']['worker_count'] != 0
                    or result['plan'].get('deadline_seconds', 1801) > 1800
                    or result['plan']['targets'] != expected):
                raise ValueError('each SG2 case requires its own serial run with deadline at most 1800s')
        if group == 'notes-budget' and result['outcome']['worker_count'] != 0:
            raise ValueError('notes budget session must be serial')
        rows.append({**item, 'counts': result['outcome']['counts'], 'files': result['files'],
            'literal_passed': result['outcome']['passed'], 'exact_counter': True,
            'failures': [row for row in result['phases']['occurrences']
                         if row['status'] not in ('passed', 'skipped')]})
    required = set(plan['groups']) - {'d76', 'journal-owner-legacy'}
    save(args.output, {'head': plan['head'], **producer_identity(),
        'plan_sha256': sha(args.plan),
        'manifest_sha256': sha(args.manifest), 'runs': rows,
        'journal_separately_scheduled_sg2': journal_sg2,
        'journal_split_exact_counter': True,
        'missing_groups': sorted(required - covered),
        'complete_required_groups': required == covered,
        'all_literal_outcomes_pass': required == covered and all(row['literal_passed'] for row in rows),
        'scope': 'Run selections and literal outcomes only; eligibility census and mutation evidence remain separate obligations.'})


def main():
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise ValueError('use -S -P -B')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('freeze', 'partition'):
        p = sub.add_parser(name)
        p.add_argument('--tree', type=Path, required=True)
        p.add_argument('--head', required=True)
        p.add_argument('--collection', type=Path, required=True)
        p.add_argument('--output', type=Path, required=True)
        if name == 'freeze':
            p.add_argument('--ordering', required=True)
        else:
            p.add_argument('--timing-evidence', type=Path, required=True)
            p.add_argument('--timing-source-revisions', type=Path,
                           help='Exact reviewed old/new source identities for reused prior-revision timings')
    p = sub.add_parser('report')
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    {'freeze': freeze, 'partition': partitions, 'report': report}[args.action](args)


if __name__ == '__main__':
    main()
