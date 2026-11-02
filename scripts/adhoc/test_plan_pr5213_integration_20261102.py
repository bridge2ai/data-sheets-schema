#!/usr/bin/env python3
"""Offline stdlib contracts for #5213 integration evidence planning, 2026-11-02.

Inputs: sibling planning helper and unchanged sharding source. Output: unittest
results only, no pytest or real production imports; temporary fixtures are owned.
"""
from collections import Counter
import importlib.util
from pathlib import Path
import sys
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
