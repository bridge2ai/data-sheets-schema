#!/usr/bin/env python3
"""Contracts for #5213 final evidence coverage (2026-11-02).

Input: sibling summary helper, synthetic run metadata only. Output: unittest
results; temporary files are owned fixtures. No repository/provider imports.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import summarize_d76_round3_20261102 as summary
import d76_round3_hygiene_20261102 as hygiene


class SummaryContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest = {'head': 'a' * 40, 'runs': []}

    def add_run(self, name, role, nodes, *, argv=(), job=None, targets=(), failed=False):
        root = self.root / name
        root.mkdir()
        archive = root / 'archive-proof.json'
        archive.write_text(json.dumps({'head': self.manifest['head'], 'git_tree': 'c' * 40,
                                       'destination': '/pinned/source'}))
        collection = role == 'collection'
        counts = {'passed': 0 if collection or failed else len(nodes),
                  'failed': len(nodes) if failed else 0}
        outcome = {'counts': counts, 'wall_seconds': 1, 'returncode': int(failed),
                   'passed': not failed, 'collection_passed': collection,
                   'collection_complete': collection, 'node_accounting_complete': not collection,
                   'deadline_expired': False, 'phase_journals_valid': True}
        outcome.update({key: True for key in ('source_unchanged', 'hygiene_passed', 'origins_verified',
            'helpers_unchanged', 'targets_unchanged', 'sandbox_loaded', 'zero_guard_denials',
            'all_worker_collections_identical')})
        payloads = {
            'outcome.json': outcome,
            'plan.json': {'head': self.manifest['head'], 'git_tree': 'c' * 40,
                         'worktree': '/pinned/source', 'archive_proof': str(archive),
                         'archive_proof_sha256': summary.digest(archive),
                         'notes_ci_job': job, 'targets': list(targets)},
            'nodes.json': {'collected': nodes, 'selected': nodes},
            'phase-accounting.json': {'counts': counts, 'occurrences': [] if collection else [
                {'nodeid': node, 'status': 'failed' if failed else 'passed', 'complete': True}
                for node in nodes]},
            'source-before.json': {'head': self.manifest['head'], 'tree': 'c' * 40, 'tracked_exact': True},
            'source-after.json': {'head': self.manifest['head'], 'tree': 'c' * 40, 'tracked_exact': True},
            'pytest-command.json': {'argv': list(argv)},
            'phase-journals.json': {'passed': True},
        }
        for filename, data in payloads.items():
            (root / filename).write_text(json.dumps(data))
        row = {'name': name, 'role': role, 'directory': str(root)}
        self.manifest['runs'].append(row)
        return root, row

    def complete_tests(self):
        nodes = [f'tests/case_{index}' for index in range(10)]
        self.add_run('collection', 'collection', nodes)
        for index in range(6):
            self.add_run(f'ordinary-{index + 1}', 'ordinary', nodes[index:index + 1],
                         argv=[f'--ci-shard={index + 1}/6', '--ci-lane=ordinary'])
        for index, lane in enumerate(('routing-dispatch', 'routing-portable',
                                      'routing-regate', 'routing-default-layout'), 6):
            self.add_run(lane, 'api', nodes[index:index + 1], argv=['--ci-lane=' + lane])

    def test_empty_roster_refuses(self):
        with self.assertRaises(ValueError):
            summary.summarize(self.manifest)

    def test_baseline_cannot_fill_a_final_coverage_role(self):
        root, row = self.add_run('old-shard', 'ordinary', ['tests/one'])
        row['head'] = 'b' * 40
        plan = summary.read(root / 'plan.json')
        plan['head'] = row['head']
        (root / 'plan.json').write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError, 'baseline head'):
            summary.summarize(self.manifest)

    def test_complete_tests_do_not_claim_offline_jobs(self):
        self.complete_tests()
        result = summary.summarize(self.manifest)
        self.assertTrue(result['tests_ci_coverage']['exact'])
        self.assertFalse(result['offline_ci_coverage']['exact'])

    def test_failed_proof_keeps_raw_counters_without_validated_coverage(self):
        self.complete_tests()
        path = self.root / 'ordinary-1/outcome.json'
        data = summary.read(path)
        data['source_unchanged'] = False
        path.write_text(json.dumps(data))
        result = summary.summarize(self.manifest)
        self.assertTrue(result['tests_ci_coverage']['counter_and_commands_exact'])
        self.assertFalse(result['tests_ci_coverage']['exact'])

    def test_all_four_offline_commands_are_required_in_full(self):
        self.complete_tests()
        for name, targets in hygiene.NOTES_TARGETS.items():
            if name.startswith('ci-'):
                self.add_run(name, 'offline', [name + '/test'], job=name, targets=targets)
        result = summary.summarize(self.manifest)
        self.assertTrue(result['offline_ci_coverage']['exact'])
        path = self.root / 'ci-offline-canary-native/plan.json'
        data = summary.read(path)
        data['targets'] = data['targets'][:1]
        path.write_text(json.dumps(data))
        self.assertFalse(summary.summarize(self.manifest)['offline_ci_coverage']['exact'])

    def test_literal_failure_is_preserved(self):
        self.add_run('known-environmental', 'baseline', ['tests/failed'], failed=True)
        result = summary.summarize(self.manifest)
        self.assertFalse(result['all_literal_outcomes_pass'])
        self.assertEqual(result['runs'][0]['counts']['failed'], 1)
        self.assertEqual(result['runs'][0]['failures'][0]['status'], 'failed')

    def test_offline_proof_failure_does_not_taint_raw_roster_or_tests_counter(self):
        self.complete_tests()
        for name, targets in hygiene.NOTES_TARGETS.items():
            if name.startswith('ci-'):
                self.add_run(name, 'offline', [name + '/test'], job=name, targets=targets)
        path = self.root / 'ci-offline-canary-native/outcome.json'
        data = summary.read(path)
        data['deadline_expired'] = True
        path.write_text(json.dumps(data))
        result = summary.summarize(self.manifest)
        self.assertTrue(result['offline_ci_coverage']['roster_and_commands_exact'])
        self.assertFalse(result['offline_ci_coverage']['exact'])
        self.assertTrue(result['tests_ci_coverage']['exact'])

    def test_metadata_mismatch_refuses_proven_coverage(self):
        self.complete_tests()
        path = self.root / 'ordinary-1/source-after.json'
        data = summary.read(path)
        data['head'] = 'b' * 40
        path.write_text(json.dumps(data))
        result = summary.summarize(self.manifest)
        self.assertTrue(result['tests_ci_coverage']['counter_and_commands_exact'])
        self.assertFalse(result['tests_ci_coverage']['exact'])

    def test_phase_journal_digest_is_preserved(self):
        root, _ = self.add_run('one', 'targeted', ['tests/one'])
        result = summary.summarize(self.manifest)
        self.assertEqual(result['runs'][0]['artifact_sha256']['phase-journals.json'],
                         summary.digest(root / 'phase-journals.json'))


if __name__ == '__main__':
    unittest.main()
