#!/usr/bin/env python3
"""Stdlib contracts for bounded D76 round-2 coverage joining, PR #5213, 2026-11-01.

Inputs: synthetic node ledgers, notes policies and temporary probe bytes.
Output: unittest results; no repository evidence, provider calls or test launches.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).with_name('join_d76_round2_coverage_20261101.py')
SPEC = importlib.util.spec_from_file_location('round2_coverage', PATH)
JOIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(JOIN)


def nodes(ids):
    return {'collected': list(ids), 'selected': list(ids), 'reports': [
        {'nodeid': node, 'item_index': index, 'worker_id': 'gw' + str(index % 3),
         'when': when, 'outcome': 'passed', 'xfail': None}
        for index, node in enumerate(ids) for when in ('setup', 'call', 'teardown')]}


class CoverageContracts(unittest.TestCase):
    def test_known_full_modules_match_with_duplicate_occurrences(self):
        modules = JOIN.GROUPS['new-regressions']
        ids = [modules[0] + '::test_a[0]', modules[0] + '::test_a[0]', modules[1] + '::test_b']
        JOIN.check_scope('new-regressions', modules)
        value = JOIN.check_selection('new-regressions', modules, nodes(ids), ids)
        self.assertEqual(value['selected_occurrences'], 3)
        self.assertEqual(value['counts']['passed'], 3)
        self.assertTrue(value['all_occurrences_passed'])

    def test_omitted_requested_module_refuses_even_if_remaining_tests_pass(self):
        modules = JOIN.GROUPS['new-regressions']
        full = [modules[0] + '::test_a', modules[1] + '::test_b']
        with self.assertRaisesRegex(ValueError, 'no collected nodes'):
            JOIN.check_selection('new-regressions', modules, nodes(full[:1]), full)
        with self.assertRaisesRegex(ValueError, 'roster differs'):
            JOIN.check_scope('new-regressions', modules[:1])

    def test_shared_deselection_cannot_masquerade_as_complete_module(self):
        module = JOIN.GROUPS['new-regressions'][0]
        ids = [module + '::test_a', module + '::test_b']
        value = nodes(ids)
        value['selected'].pop()
        with self.assertRaisesRegex(ValueError, 'deselected'):
            JOIN.check_selection('new-regressions', [module], value, ids)
        with self.assertRaisesRegex(ValueError, 'differs from full collection'):
            JOIN.check_selection('new-regressions', [module], nodes(ids[:1]), ids)

    def test_notes_own_collection_with_verified_cache_is_accepted(self):
        plan, hygiene = self.notes_policy()
        JOIN.check_notes_job('f5-notes-canary', plan, hygiene)
        modules = JOIN.GROUPS['f5-notes-canary']
        ids = [module + '::test_case' for module in modules]
        value = JOIN.check_selection('f5-notes-canary', modules, nodes(ids), [])
        self.assertTrue(value['coverage_complete'])
        self.assertTrue(all(row['full_collection_occurrences'] is None for row in value['modules']))

    @staticmethod
    def notes_policy():
        mode = 'notes_ci_new_tracked_source_bytecode'
        return ({'notes_ci_job': 'offline-canary', 'notes_ci_pythonpath': list(JOIN.NOTES.CI_PATHS),
                 'hygiene_mode': mode},
                {'passed': True, 'before': '', 'after': 'new retained bytecode', 'hygiene_mode': mode,
                 'removed_paths': [], 'refusals': [],
                 'allowed_new_bytecode': [{'header_and_compiled_payload_verified': True}]})

    def test_wrong_notes_job_or_pythonpath_is_refused(self):
        plan, hygiene = self.notes_policy()
        plan['notes_ci_job'] = 'offline-audit'
        with self.assertRaisesRegex(ValueError, 'wrong notes CI job'):
            JOIN.check_notes_job('f5-notes-canary', plan, hygiene)
        plan['notes_ci_job'] = 'offline-canary'
        plan['notes_ci_pythonpath'] = ['src']
        with self.assertRaisesRegex(ValueError, 'PYTHONPATH'):
            JOIN.check_notes_job('f5-notes-canary', plan, hygiene)

    def test_reviewer_hash_drift_refuses_even_with_unchanged_passing_nodes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / name for name in JOIN.GROUPS['reviewer-codex']]
            for index, path in enumerate(paths):
                path.write_text(f'def test_probe_{index}():\n    pass\n')
            hashes = {str(path): JOIN.sha(path.read_bytes()) for path in paths}
            plan = {'targets': list(hashes), 'target_sha256': hashes, 'worktree': str(root)}
            run = {'plan': plan, 'source': {'entries': {}}}
            frozen = {'target_sha256': deepcopy(hashes)}
            functions = JOIN.verify_targets(JOIN.Evidence(), 'reviewer-codex', list(hashes), run, run, frozen)
            self.assertEqual(len(functions), 2)
            paths[0].write_text('def test_probe_0():\n    assert False\n')
            with self.assertRaisesRegex(ValueError, 'hash differs'):
                JOIN.verify_targets(JOIN.Evidence(), 'reviewer-codex', list(hashes), run, run, frozen)

    def test_reviewer_blank_prefixes_remain_literal_and_all_functions_present(self):
        functions = {'first.py': {'test_a'}, 'second.py': {'test_b'}}
        ids = ['::test_a[zero]', '::test_b']
        value = JOIN.check_selection('reviewer-codex', list(functions), nodes(ids), [], functions)
        self.assertEqual(value['selected_occurrences'], 2)
        with self.assertRaisesRegex(ValueError, 'reviewer test function'):
            JOIN.check_selection('reviewer-codex', list(functions), nodes(ids[:1]), [], functions)

    def test_setup_only_occurrence_is_not_coverage(self):
        module = JOIN.GROUPS['new-regressions'][0]
        ids = [module + '::test_a']
        value = nodes(ids)
        value['reports'] = value['reports'][:1]
        with self.assertRaisesRegex(ValueError, 'incomplete selected phases'):
            JOIN.check_selection('new-regressions', [module], value, ids)

    def test_ambiguous_blank_reviewer_origin_is_refused(self):
        functions = {'first.py': {'test_same'}, 'second.py': {'test_same'}}
        with self.assertRaisesRegex(ValueError, 'ambiguous reviewer function'):
            JOIN.check_selection('reviewer-codex', list(functions), nodes(['::test_same']), [], functions)

    def test_available_reviewer_file_origin_must_match(self):
        functions = {'/frozen/probe.py': {'test_a'}}
        with self.assertRaisesRegex(ValueError, 'different source file'):
            JOIN.check_selection('reviewer-codex', list(functions), nodes(['/foreign/probe.py::test_a']), [], functions)

    def test_skip_is_complete_coverage_but_not_pass(self):
        module = JOIN.GROUPS['new-regressions'][0]
        ids = [module + '::test_a']
        value = nodes(ids)
        value['reports'][1]['outcome'] = 'skipped'
        value = JOIN.check_selection('new-regressions', [module], value, ids)
        self.assertTrue(value['coverage_complete'])
        self.assertFalse(value['all_occurrences_passed'])
        self.assertEqual(value['counts']['skipped'], 1)


if __name__ == '__main__':
    unittest.main()
