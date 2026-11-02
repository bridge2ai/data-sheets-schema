#!/usr/bin/env python3
"""Stdlib contracts for the PR #5213 round-3 planner (2026-11-02).

Inputs: synthetic evidence in TemporaryDirectory and mocked local Git reads.
Outputs: unittest results only; no pytest, production imports, providers or Git
writes. These contracts test refusal/mapping, not scientific or suite acceptance.
Run with Python -B after the parent freezes this file and schedules validation.
"""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


MODULE = Path(__file__).with_name('plan_d76_round3_validation_20261102.py')
SPEC = importlib.util.spec_from_file_location('d76_round3_planner_contract_target', MODULE)
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)


class PlannerContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='d76-planner-contract-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.head = planner.BASELINES['round2']

    def write_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + '\n')

    def evidence(self, name='evidence', *, selected=None, target=None):
        run = self.directory / name
        run.mkdir()
        plan = {'head': self.head, 'targets': [target or 'tests/test_synthetic.py'],
                'command': ['python', '/frozen/run_d76_validation_20261031.py'],
                'helpers': {'/frozen/helper.py': 'a' * 64}}
        outcome = {key: True for key in planner.PROOFS}
        outcome.update(guard_denial_count=0, deadline_expired=False,
            node_accounting_complete=True, passed=False, collection_passed=False,
            counts={'failed': 1, 'passed': 2, 'errors': 0, 'skipped': 0,
                    'interrupted': 0, 'not_started': 0, 'unexpected': 0, 'xpassed': 0})
        nodes = {'selected': selected or ['::test_case[parameter]', '::test_control', '::test_control_two'],
                 'collected': [], 'reports': []}
        source = {'head': self.head, 'tree': 'b' * 40, 'entries': {}}
        for key, value in (('plan', plan), ('outcome', outcome), ('nodes', nodes),
                           ('source-before', source), ('source-after', source)):
            self.write_json(run / (key + '.json'), value)
        (run / 'pytest.xml').write_text('<testsuites/>\n')
        return run

    def change(self, run, filename, **changes):
        data = planner.read(run / (filename + '.json'))
        data.update(changes)
        self.write_json(run / (filename + '.json'), data)

    def mapping_fixture(self):
        raw = b'# frozen synthetic regression\ndef test_case():\n    pass\n'
        relative = 'tests/test_regression.py'
        root = self.directory / 'source'
        (root / 'tests').mkdir(parents=True)
        (root / relative).write_bytes(raw)
        exported = self.directory / 'export' / 'test_regression.py'
        exported.parent.mkdir()
        exported.write_bytes(raw)
        digest = planner.sha(raw)
        selected = ['::test_case[parameter::with/slash]',
                    '::test_case[parameter::with/slash]', '::test_control']
        run = self.evidence('before', selected=selected, target=str(exported))
        self.change(run, 'plan', target_sha256={str(exported): digest})
        roster = {'synthetic': (relative, digest, 'before', 1, 2)}
        return root, exported, run, raw, roster

    def map_before(self, root, raw, roster, evidence=True):
        # Mock only the local Git blob read. Actual final/exported files, hashes,
        # evidence parsing, target mapping and refusals run unchanged.
        with mock.patch.dict(planner.NEW_BASELINES, roster, clear=True), \
                mock.patch.object(planner, 'git', return_value=raw):
            return planner.before_manifest(root, self.head, self.directory if evidence else None)

    def test_terminal_failure_stays_failure_observation(self):
        run = self.evidence()
        result = planner.terminal_run(run, self.head)
        self.assertFalse(result['outcome']['passed'])
        self.assertEqual(result['outcome']['counts']['failed'], 1)

    def test_mixed_head_refused_for_plan_and_source(self):
        for field in ('plan', 'source-before'):
            with self.subTest(field=field):
                run = self.evidence(field)
                self.change(run, field, head='c' * 40)
                with self.assertRaisesRegex(ValueError, 'head differs'):
                    planner.terminal_run(run, self.head)

    def test_source_change_refused(self):
        run = self.evidence()
        self.change(run, 'source-after', tree='c' * 40)
        with self.assertRaisesRegex(ValueError, 'proofs incomplete'):
            planner.terminal_run(run, self.head)

    def test_incomplete_execution_is_not_failure_roster(self):
        run = self.evidence()
        self.change(run, 'outcome', node_accounting_complete=False)
        with self.assertRaisesRegex(ValueError, 'complete phase accounting'):
            planner.terminal_run(run, self.head)

    def test_guard_denial_and_deadline_refuse_terminal_selection(self):
        for name, change in (('denial', {'guard_denial_count': 1}),
                             ('deadline', {'deadline_expired': True})):
            with self.subTest(name=name):
                run = self.evidence(name)
                self.change(run, 'outcome', **change)
                with self.assertRaisesRegex(ValueError, 'deadline or guard-denial'):
                    planner.terminal_run(run, self.head)

    def test_new_runner_requires_journal_old_runner_remains_readable(self):
        run = self.evidence()
        planner.terminal_run(run, self.head)
        self.change(run, 'plan', command=['python', '/frozen/run_d76_round3_validation_20261102.py'])
        with self.assertRaisesRegex(ValueError, 'journal proof'):
            planner.terminal_run(run, self.head)
        self.change(run, 'outcome', phase_journals_valid=True)
        planner.terminal_run(run, self.head)
        self.change(run, 'outcome', phase_journals_valid=False)
        with self.assertRaisesRegex(ValueError, 'journal proof'):
            planner.terminal_run(run, self.head)

    def test_collection_needs_success_and_exact_tests_root(self):
        run = self.evidence()
        self.change(run, 'plan', targets=['tests'])
        with self.assertRaisesRegex(ValueError, 'successful full tests collection'):
            planner.terminal_run(run, self.head, collection=True)
        self.change(run, 'outcome', collection_passed=True)
        planner.terminal_run(run, self.head, collection=True)
        self.change(run, 'plan', targets=['tests/test_synthetic.py'])
        with self.assertRaisesRegex(ValueError, 'successful full tests collection'):
            planner.terminal_run(run, self.head, collection=True)

    def test_exact_file_mapping_preserves_parameter_suffix_and_duplicates(self):
        root, exported, run, raw, roster = self.mapping_fixture()
        result = self.map_before(root, raw, roster)['modules']['synthetic']
        self.assertTrue(result['actual_before_verified'])
        mapped = result['exact_file_node_mapping']
        self.assertEqual([row['final_nodeid'] for row in mapped], [
            'tests/test_regression.py::test_case[parameter::with/slash]',
            'tests/test_regression.py::test_case[parameter::with/slash]',
            'tests/test_regression.py::test_control'])
        self.assertEqual(result['actual_before_counts']['failed'], 1)
        self.assertEqual(result['actual_before_counts']['passed'], 2)

    def test_same_function_from_foreign_file_is_not_joined(self):
        root, exported, run, raw, roster = self.mapping_fixture()
        self.change(run, 'nodes', selected=['test_other.py::test_case[parameter::with/slash]'])
        with self.assertRaisesRegex(ValueError, 'unrecognized single-file'):
            self.map_before(root, raw, roster)

    def test_exported_blob_drift_is_refused(self):
        root, exported, run, raw, roster = self.mapping_fixture()
        exported.write_bytes(raw + b'# changed\n')
        with self.assertRaisesRegex(ValueError, 'exported regression hash differs'):
            self.map_before(root, raw, roster)

    def test_recorded_export_hash_drift_is_refused(self):
        root, exported, run, raw, roster = self.mapping_fixture()
        self.change(run, 'plan', target_sha256={str(exported): 'd' * 64})
        with self.assertRaisesRegex(ValueError, 'exported regression hash differs'):
            self.map_before(root, raw, roster)

    def test_final_regression_drift_is_refused(self):
        root, exported, run, raw, roster = self.mapping_fixture()
        changed = raw + b'# changed final\n'
        (root / 'tests/test_regression.py').write_bytes(changed)
        with self.assertRaisesRegex(ValueError, 'differs from frozen failing-before blob'):
            self.map_before(root, changed, roster)

    def test_multiple_export_files_cannot_map_blank_prefixes(self):
        root, exported, run, raw, roster = self.mapping_fixture()
        self.change(run, 'plan', targets=[str(exported), str(exported.with_name('other.py'))])
        with self.assertRaisesRegex(ValueError, 'exactly its frozen module target'):
            self.map_before(root, raw, roster)

    def test_unchecked_before_count_is_explicitly_unverified(self):
        root, exported, run, raw, roster = self.mapping_fixture()
        row = self.map_before(root, raw, roster, evidence=False)['modules']['synthetic']
        self.assertFalse(row['actual_before_verified'])
        self.assertNotIn('actual_before_counts', row)
        self.assertNotIn('exact_file_node_mapping', row)

    def test_retained_selection_drift_refuses_before_any_outputs(self):
        root = self.directory / 'tree'
        prior = self.directory / 'prior'
        probes = self.directory / 'probes'
        root.mkdir()
        probes.mkdir()
        self.write_json(prior / 'historical107.json', [f'tests/wrong.py::test_{n}' for n in range(107)])
        output = self.directory / 'output'
        args = SimpleNamespace(tree=root, expect_head=self.head, output=output,
            prior_selection=prior, probes=probes, baseline_evidence=None)
        with mock.patch.object(planner, 'checked_head', return_value='b' * 40):
            with self.assertRaisesRegex(ValueError, 'selection differs from retained exact bytes'):
                planner.freeze(args)
        self.assertFalse(output.exists())

    def test_git_reads_scrub_redirection_and_disable_remote_fetch(self):
        with mock.patch.dict(os.environ, {'GIT_DIR': '/foreign', 'GIT_WORK_TREE': '/foreign',
                                         'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'url.x.insteadOf'}):
            command, environment = planner.git_command(self.directory, 'show', self.head + ':tests/x.py')
        self.assertIn('--no-replace-objects', command)
        self.assertIn('protocol.allow=never', command)
        self.assertNotIn('GIT_DIR', environment)
        self.assertNotIn('GIT_WORK_TREE', environment)
        self.assertNotIn('GIT_CONFIG_COUNT', environment)
        self.assertEqual(environment['GIT_NO_LAZY_FETCH'], '1')
        self.assertEqual(environment['GIT_CONFIG_GLOBAL'], '/dev/null')
        self.assertEqual(environment['GIT_CONFIG_NOSYSTEM'], '1')
        self.assertEqual(environment['GIT_OPTIONAL_LOCKS'], '0')

    def test_inventory_does_not_execute_test_or_fixture_module(self):
        path = self.directory / 'test_fixture.py'
        path.write_text('raise RuntimeError("must not import")\n'
                        'def fixture_only(): pass\n'
                        'def test_function(): pass\n'
                        'class TestCases:\n    def test_method(self): pass\n')
        self.assertEqual(planner.test_functions(path), ['test_function', 'TestCases.test_method'])

    def test_existing_evidence_cannot_be_overwritten(self):
        path = self.directory / 'existing.json'
        path.write_bytes(b'original evidence\n')
        with self.assertRaises(FileExistsError):
            planner.save(path, {'replacement': True})
        self.assertEqual(path.read_bytes(), b'original evidence\n')


if __name__ == '__main__':
    unittest.main()
