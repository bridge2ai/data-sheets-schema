#!/usr/bin/env python3
"""Offline stdlib contracts for #5213 integration evidence planning, 2026-11-02.

Inputs: sibling planning helper and unchanged sharding source. Output: unittest
results only, no pytest or real production imports; temporary fixtures are owned.
"""
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('integration_plan_under_test', HERE / 'plan_pr5213_integration_20261102.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
fake_pytest = types.SimpleNamespace(UsageError=ValueError, hookimpl=lambda **kw: lambda f: f)
with patch.dict(sys.modules, {'pytest': fake_pytest}):
    plugin = helper.load_file('integration_real_plugin_for_contracts', HERE.parents[1] / 'utils/pytest_shard.py')


class PlanningContracts(unittest.TestCase):
    def test_collection_rejects_selectors_and_filtered_counter(self):
        base = {'targets': ['tests'], 'collect_only': True}
        nodes = {'collected': ['a', 'a', 'b'], 'selected': ['a', 'a', 'b']}
        outcome = {'collection_complete': True, 'returncode': 0}
        helper.require_collection(base, nodes, outcome)
        for key, value in (('ci_shard', 1), ('ci_lane', 'ordinary'), ('ci_ordinary_shard_of_6', 1),
                           ('ci_api_lane', 'routing-dispatch'), ('notes_ci_job', 'ci-offline-canary-budget')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                helper.require_collection({**base, key: value}, nodes, outcome)
        with self.assertRaises(ValueError):
            helper.require_collection(base, {**nodes, 'selected': ['a', 'b']}, outcome)

    def test_duplicate_occurrences_are_preserved_in_six_and_four_partitions(self):
        nodes = ['tests/a.py::same', 'tests/a.py::same', 'tests/b.py::one', *plugin.API_CASE_LANES.values()]
        for total in (6, 4):
            shards, api = helper.partition(nodes, plugin, {'tests/a.py': 8, 'tests/b.py': 3}, total)
            joined = Counter(n for group in shards for n in group)
            joined.update(n for group in api.values() for n in group)
            self.assertEqual(joined, Counter(nodes))
            self.assertEqual(sum('tests/a.py::same' in group for group in shards), 1)

    def test_missing_dedicated_case_is_refused(self):
        with self.assertRaises(ValueError):
            helper.partition(['tests/a.py::one'], plugin, {'tests/a.py': 1}, 6)

    def test_projection_retains_duplicate_observations(self):
        rows = [{'nodeid': 'tests/a.py::same', 'seconds': seconds} for seconds in (3, 7)]
        result = helper.projected_shards([['tests/a.py::same'] * 2] + [[]] * 5,
                                        {'tests/a.py': 10}, rows, plugin, 2)
        self.assertEqual(result[0]['simulated_four_worker_seconds'], 7)
        self.assertEqual(result[0]['projected_job_seconds'], 9)

    def test_projection_refuses_missing_or_extra_observations(self):
        for rows in ([], [{'nodeid': 'tests/a.py::one', 'seconds': 1}] * 2):
            with self.assertRaises(ValueError):
                helper.projected_shards([['tests/a.py::one']] + [[]] * 5,
                                        {'tests/a.py': 1}, rows, plugin, 0)

    def test_limits_are_already_eighty_percent(self):
        for total, limit in ((6, 2160), (4, 2880)):
            groups = [['tests/a.py::one']] + [[]] * (total - 1)
            at = helper.projected_shards(groups, {'tests/a.py': 1},
                [{'nodeid': 'tests/a.py::one', 'seconds': limit - 1}], plugin, 1)
            above = helper.projected_shards(groups, {'tests/a.py': 1},
                [{'nodeid': 'tests/a.py::one', 'seconds': limit}], plugin, 1)
            self.assertEqual(at[0]['limit_seconds'], limit)
            self.assertTrue(at[0]['within_limit'])
            self.assertFalse(above[0]['within_limit'])

    def test_invalid_timing_is_not_a_number_or_inf(self):
        for seconds in (True, float('inf'), float('nan'), -1, '1'):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                helper.projected_shards([['tests/a.py::one']] + [[]] * 5,
                    {'tests/a.py': 1}, [{'nodeid': 'tests/a.py::one', 'seconds': seconds}], plugin, 0)

    def test_function_comparison_retains_comments_and_whitespace(self):
        raw = b'@decorator\ndef target():\n    # comment\n    return "  "\n\ndef other():\n    pass\n'
        self.assertEqual(helper.function_bytes(raw, 'target'),
                         b'@decorator\ndef target():\n    # comment\n    return "  "\n')
        with self.assertRaises(ValueError):
            helper.function_bytes(raw, 'missing')

    def test_missing_module_is_not_empty_success(self):
        with self.assertRaises(ValueError):
            helper.module_nodes(['tests/a.py::one'], ['tests/a.py', 'tests/b.py'])

    def test_census_split_preserves_exact_occurrence_union(self):
        full = ['one', 'census', 'census', 'last']
        separate = ['census', 'census']
        grouped = helper.without_occurrences(full, separate)
        self.assertEqual(grouped, ['one', 'last'])
        self.assertEqual(Counter(grouped) + Counter(separate), Counter(full))
        with self.assertRaises(ValueError):
            helper.without_occurrences(full, separate + ['census'])

    def test_sg2_explicit_nodes_are_three_distinct_parameters(self):
        self.assertEqual(len(helper.SG2), 3)
        self.assertEqual(len(set(helper.SG2)), 3)
        self.assertEqual({node.rsplit('[', 1)[-1] for node in helper.SG2},
                         {'none]', 'explicit]', 'conventional]'})


class JournalSelectionContracts(unittest.TestCase):
    def test_three_way_split_retains_other_registration_cases_and_duplicates(self):
        other = [helper.SG2_PREFIX.split('::')[0] + f'::test_other[{i}]' for i in range(10)]
        census = ['census'] * 2
        full = ['journal', 'journal', *census, *helper.SG2, *other]
        grouped, separate = helper.journal_split(full, census, helper.SG2)
        self.assertEqual(grouped, ['journal', 'journal', *other])
        self.assertEqual(Counter(separate), Counter(helper.SG2))
        self.assertEqual(Counter(grouped) + Counter(census) + Counter(separate), Counter(full))

    def test_old_roster_without_sg2_has_no_synthetic_coverage(self):
        full = ['journal', 'census', 'journal']
        grouped, separate = helper.journal_split(full, ['census'], helper.SG2)
        self.assertEqual(grouped, ['journal', 'journal'])
        self.assertEqual(separate, [])
        self.assertEqual(Counter(grouped) + Counter(['census']), Counter(full))

    def test_only_actual_sg2_intersection_is_credited(self):
        full = [helper.SG2[1], 'census', 'journal']
        grouped, separate = helper.journal_split(full, ['census'], helper.SG2)
        self.assertEqual(grouped, ['journal'])
        self.assertEqual(separate, [helper.SG2[1]])

    def test_insufficient_or_overlapping_separate_occurrences_refuse(self):
        for full, census in ((['journal'], ['missing']),
                             ([helper.SG2[0]], [helper.SG2[0]]),
                             ([helper.SG2[0]] * 2, [])):
            with self.subTest(full=full, census=census), self.assertRaises(ValueError):
                helper.journal_split(full, census, helper.SG2)

    def freeze_fixture(self, root, include_registration):
        tree = root / 'source'
        tree.mkdir()
        registration = helper.SG2_PREFIX.split('::')[0]
        journal = 'tests/test_journal_contract.py'
        census = 'tests/test_d69_artifact_completeness.py'
        ordering = 'tests/test_ordering_contract.py'
        ci = 'tests/test_ci_sharding.py'
        other = [registration + f'::test_other[{i}]' for i in range(10)]
        full = [journal + '::test_same'] * 2 + [census + f'::test_census[{i}]' for i in range(11)]
        full += [*helper.SG2, *other, ordering + '::test_order', ci + '::test_shard']
        journal_modules = [journal, census] + ([registration] if include_registration else [])
        for name in [journal, census, registration, ordering, ci, helper.NOTES,
                     'scripts/adhoc/d70_corpus_eligibility_20261030.py']:
            path = tree / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# owned synthetic planning fixture\n')
        args = types.SimpleNamespace(tree=tree, head='a' * 40, collection=root / 'collection',
                                     ordering=ordering, output=root / 'selection')
        evidence = {'plan': {'worktree': str(tree)},
                    'nodes': {'collected': full, 'selected': full}, 'files': {}}
        with ExitStack() as stack:
            stack.enter_context(patch.object(helper, 'source_identity', return_value={
                'head': args.head, 'git_tree': 'b' * 40}))
            stack.enter_context(patch.object(helper, 'producer_identity', return_value={
                'producer_head': 'c' * 40, 'producer_git_tree': 'd' * 40}))
            stack.enter_context(patch.object(helper, 'run_evidence', return_value=evidence))
            stack.enter_context(patch.object(helper, 'roster', return_value=(
                journal_modules, journal_modules, [registration], {})))
            stack.enter_context(patch.object(helper, 'git', return_value=helper.NOTES + '\n'))
            stack.enter_context(patch.object(helper, 'invariants', return_value={}))
            helper.freeze(args)
        return args, other

    def test_freeze_and_report_use_existing_nine_groups_and_distinct_producer(self):
        for present in (False, True):
            with self.subTest(registration_in_journal=present), tempfile.TemporaryDirectory() as temporary:
                args, other = self.freeze_fixture(Path(temporary), present)
                plan_path = args.output / 'plan.json'
                plan = helper.read(plan_path)
                groups = {name: helper.read(value['path']) for name, value in plan['groups'].items()}
                required = set(groups) - {'d76', 'journal-owner-legacy'}
                self.assertEqual(required, {'ordering', 'ci-sharding', 'writer-census',
                    'd76-without-sg2', 'journal-without-census', 'notes-budget',
                    'sg2-none', 'sg2-explicit', 'sg2-conventional'})
                self.assertEqual(plan['head'], 'a' * 40)
                self.assertEqual(plan['producer_head'], 'c' * 40)
                self.assertEqual(plan['journal_separately_scheduled_sg2'], helper.SG2 if present else [])
                self.assertEqual(groups['d76-without-sg2'], other)
                self.assertTrue(set(groups['journal-without-census']).isdisjoint(helper.SG2))
                self.assertEqual(set(other).issubset(groups['journal-without-census']), present)
                self.assertEqual(Counter(groups['journal-without-census'])
                    + Counter(groups['writer-census']) + Counter(plan['journal_separately_scheduled_sg2']),
                    Counter(groups['journal-owner-legacy']))
                manifest = Path(temporary) / 'manifest.json'
                manifest.write_text(json.dumps({'head': args.head,
                    'runs': [{'group': name, 'directory': name} for name in sorted(required)]}))

                def run(group, head):
                    self.assertEqual(head, args.head)
                    nodes = groups[group]
                    return {'plan': {'targets': nodes, 'deadline_seconds': 1800,
                                'notes_ci_job': 'ci-offline-canary-budget' if group == 'notes-budget' else None},
                        'nodes': {'collected': nodes, 'selected': nodes}, 'files': {},
                        'outcome': {'worker_count': 0, 'counts': {'passed': len(nodes)}, 'passed': True},
                        'phases': {'occurrences': [{'nodeid': node, 'status': 'passed'} for node in nodes]}}

                report_args = types.SimpleNamespace(plan=plan_path, manifest=manifest,
                                                     output=Path(temporary) / 'report.json')
                with patch.object(helper, 'run_evidence', side_effect=run), patch.object(
                        helper, 'producer_identity', return_value={'producer_head': 'c' * 40,
                                                                   'producer_git_tree': 'd' * 40}):
                    helper.report(report_args)
                report = helper.read(report_args.output)
                self.assertTrue(report['complete_required_groups'])
                self.assertTrue(report['journal_split_exact_counter'])
                self.assertEqual(report['journal_separately_scheduled_sg2'], helper.SG2 if present else [])
                self.assertEqual(report['head'], 'a' * 40)
                self.assertEqual(report['producer_head'], 'c' * 40)

    def test_report_rejects_grouped_sg2_even_when_selection_hash_is_updated(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, _ = self.freeze_fixture(Path(temporary), True)
            plan_path = args.output / 'plan.json'
            plan = helper.read(plan_path)
            target = plan['groups']['journal-without-census']
            path = Path(target['path'])
            path.write_text(json.dumps(helper.read(path) + [helper.SG2[0]]))
            target['sha256'] = helper.sha(path)
            plan_path.write_text(json.dumps(plan))
            manifest = Path(temporary) / 'manifest.json'
            manifest.write_text(json.dumps({'head': args.head, 'runs': []}))
            with patch.object(helper, 'run_evidence') as run, self.assertRaisesRegex(ValueError, 'journal split'):
                helper.report(types.SimpleNamespace(plan=plan_path, manifest=manifest,
                                                     output=Path(temporary) / 'report.json'))
            run.assert_not_called()


class TimingSourceRevisionContracts(unittest.TestCase):
    """Real local Git blobs/ancestry, isolated beneath an owned temp directory."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.tree = Path(self.temporary.name) / 'source'
        self.tree.mkdir()
        helper.git(self.tree, 'init', '-q', '-b', 'timing-contract')
        (self.tree / 'tests').mkdir()
        (self.tree / 'utils').mkdir()
        self.path = 'tests/case.py'
        self.control = 'tests/control.py'
        self.old = b'def test_case():\n    assert True\n'
        self.revised = b'def test_case():\n    assert True  # reviewed fixture adjustment\n'
        (self.tree / self.path).write_bytes(self.old)
        (self.tree / self.control).write_bytes(b'def test_control():\n    assert True\n')
        self.weights = {'tests/case.py': 13, 'tests/control.py': 2}
        self.weights_path = self.tree / 'utils/ci_test_durations.json'
        self.weights_path.write_text(json.dumps({'schema_version': 1, 'file_seconds': self.weights}))
        self.measured_head = self.commit('measured test source')
        (self.tree / self.path).write_bytes(self.revised)
        self.revised_head = self.commit('reviewed fixture source')
        (self.tree / 'followup.txt').write_text('later evidence helper commit\n')
        self.final_head = self.commit('final source')
        patch_bytes = helper.git(self.tree, 'diff', '--no-ext-diff', '--no-textconv', '--no-renames',
            '--no-color', '--binary', '--full-index', '--src-prefix=a/', '--dst-prefix=b/',
            '--no-relative', '--unified=3', self.measured_head, self.revised_head, '--', self.path).encode()
        self.entry = {'path': self.path, 'measured_commit': self.measured_head,
            'measured_file_sha256': hashlib.sha256(self.old).hexdigest(),
            'revised_commit': self.revised_head,
            'revised_file_sha256': hashlib.sha256(self.revised).hexdigest(),
            'patch_sha256': hashlib.sha256(patch_bytes).hexdigest(),
            'issue': 'local fixture review', 'disposition': 'reuse_prior_revision_measurement'}
        self.manifest = Path(self.temporary.name) / 'source-revisions.json'
        self.write_manifest([self.entry])
        self.evidence = {'round3_commit': self.measured_head,
            'local': {'measured_commit': self.measured_head, 'test_source_sha256': {
                self.path: self.entry['measured_file_sha256'], self.control: helper.sha(self.tree / self.control)}}}

    def commit(self, message):
        helper.git(self.tree, 'add', '--all')
        helper.git(self.tree, '-c', 'user.name=Offline timing contract',
            '-c', 'user.email=timing-contract@localhost', '-c', 'core.hooksPath=/dev/null',
            'commit', '-q', '-m', message)
        return helper.git(self.tree, 'rev-parse', 'HEAD').strip()

    def write_manifest(self, rows):
        self.manifest.write_text(json.dumps({'format': 'timing_source_revisions_v1', 'transitions': rows}))

    def validate(self, evidence=None, head=None):
        return helper.timing_source_revisions(self.tree, evidence or self.evidence,
            self.manifest, head or self.final_head)

    def test_exact_reviewed_ancestor_transition_is_not_a_current_measurement(self):
        applications, proof = self.validate()
        self.assertEqual(applications, {self.path: self.entry})
        self.assertEqual(proof['sha256'], helper.sha(self.manifest))
        self.assertEqual(proof['final_head'], self.final_head)
        self.assertIn('does not establish timing equivalence', proof['scope'])

    def test_missing_transition_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'without a reviewed transition'):
            helper.timing_source_revisions(self.tree, self.evidence, None, self.final_head)
        self.write_manifest([])
        with self.assertRaisesRegex(ValueError, 'missing='):
            self.validate()

    def test_unused_or_duplicate_transition_is_refused(self):
        unused = {**self.entry, 'path': self.control}
        self.write_manifest([self.entry, unused])
        with self.assertRaisesRegex(ValueError, 'extra='):
            self.validate()
        self.write_manifest([self.entry, self.entry])
        with self.assertRaisesRegex(ValueError, 'duplicate timing source-revision transition'):
            self.validate()

    def test_duplicate_json_key_is_refused(self):
        self.manifest.write_text('{"format":"timing_source_revisions_v1",'
                                 '"format":"timing_source_revisions_v1","transitions":[]}')
        with self.assertRaisesRegex(ValueError, 'duplicate timing source-revision key'):
            self.validate()

    def test_wrong_source_hash_or_patch_is_refused(self):
        for key in ('measured_file_sha256', 'revised_file_sha256', 'patch_sha256'):
            with self.subTest(key=key):
                self.write_manifest([{**self.entry, key: '0' * 64}])
                with self.assertRaises(ValueError):
                    self.validate()

    def test_git_blob_check_is_not_replaced_by_metadata_agreement(self):
        evidence = deepcopy(self.evidence)
        evidence['local']['test_source_sha256'][self.path] = '0' * 64
        self.write_manifest([{**self.entry, 'measured_file_sha256': '0' * 64}])
        with self.assertRaisesRegex(ValueError, 'Git blobs differ'):
            self.validate(evidence=evidence)
        self.write_manifest([{**self.entry, 'revised_commit': self.measured_head}])
        with self.assertRaisesRegex(ValueError, 'Git blobs differ'):
            self.validate()

    def test_exact_blob_on_nonancestor_commit_is_refused(self):
        tree = helper.git(self.tree, 'rev-parse', self.revised_head + '^{tree}').strip()
        unrelated = helper.git(self.tree, '-c', 'user.name=Offline timing contract',
            '-c', 'user.email=timing-contract@localhost', 'commit-tree', tree, '-m', 'unrelated source').strip()
        self.write_manifest([{**self.entry, 'revised_commit': unrelated}])
        with self.assertRaisesRegex(ValueError, 'not an ancestor'):
            self.validate()

    def test_additional_unreviewed_source_drift_is_refused(self):
        (self.tree / self.path).write_bytes(self.revised + b'# unreviewed\n')
        with self.assertRaisesRegex(ValueError, 'current source identity'):
            self.validate()
        (self.tree / self.path).write_bytes(self.revised)
        (self.tree / self.control).write_text('def test_control():\n    assert False\n')
        with self.assertRaisesRegex(ValueError, 'missing='):
            self.validate()

    def test_moving_final_reference_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'exact final source HEAD'):
            self.validate(head=self.measured_head)

    def test_all_thirteen_rows_keep_historical_timings_and_metadata(self):
        prior_path = Path(self.temporary.name) / 'prior.json'
        prior_path.write_text(json.dumps({'refreshed_weights_sha256': helper.sha(self.weights_path),
            'cases': [], 'wall_projection': {'allowance_minutes': 2}}))
        rows = [{'file': self.path, 'nodeid': self.path + f'::test_case[{index}]',
                 'seconds': 1, 'origin': 'local_round3_junit', 'outcome': 'passed'} for index in range(13)]
        rows.append({'file': self.control, 'nodeid': self.control + '::test_control',
                     'seconds': 2, 'origin': 'local_round3_junit', 'outcome': 'passed'})
        evidence = {**deepcopy(self.evidence), 'main_commit': self.measured_head,
            'timings_sha256': helper.sha(self.weights_path), 'main_entries_and_provenance_preserved': True,
            'cases': rows, 'prior_timing_evidence': {'path': str(prior_path),
                'sha256': helper.sha(prior_path), 'wall_projection': {'allowance_minutes': 2}}}
        evidence['local']['file_seconds'] = self.weights
        evidence_path = Path(self.temporary.name) / 'timing-evidence.json'
        evidence_path.write_text(json.dumps(evidence))
        before = evidence_path.read_bytes(), self.weights_path.read_bytes()
        full = [row['nodeid'] for row in rows] + list(plugin.API_CASE_LANES.values())
        with patch.dict(helper.BASELINES, {'main': self.measured_head, 'round3': self.measured_head}):
            projected, allowance, proof = helper.projection_rows(self.tree, full, plugin, self.weights,
                evidence_path, self.manifest, self.final_head)
        historical = [row for row in projected if row['timing_basis'] == 'observed_prior_test_revision']
        self.assertEqual(len(historical), 13)
        self.assertEqual([row['seconds'] for row in projected], [row['seconds'] for row in rows])
        self.assertTrue(all(row['source_revision'] == self.entry for row in historical))
        self.assertEqual(projected[-1]['timing_basis'], 'observed')
        self.assertEqual(proof['prior_test_revision_cases'], historical)
        self.assertEqual(allowance, 120)
        self.assertEqual(before, (evidence_path.read_bytes(), self.weights_path.read_bytes()))
        self.assertEqual(evidence['local']['test_source_sha256'][self.path], self.entry['measured_file_sha256'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
