#!/usr/bin/env python3
"""Stdlib contracts for the PR #5213 round-four ledger, 2026-11-03.

Inputs: sibling helper and owned synthetic proof files. Outputs: unittest
results only. Uses the real evidence verifier; no pytest or production imports.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('round4_ledger_contracts', HERE / 'summarize_d76_round4_20261103.py')
helper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helper)


class LedgerContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def save(self, path, data):
        path.write_text(json.dumps(data))

    def fixture(self, name='run', statuses=('passed',), head='a' * 40, required=True,
                selected=None, kind='final'):
        directory = self.root / name
        directory.mkdir()
        selected = selected or ['tests/test_selected.py::test_example[' + str(i) + ']'
                                for i in range(len(statuses))]
        counts = dict.fromkeys(('passed', 'failed', 'errors', 'skipped', 'xpassed',
                                'interrupted', 'not_started', 'unexpected'), 0)
        for status in statuses:
            counts[status] += 1
        raw_counts = {key: counts[key] for key in ('passed', 'failed', 'errors', 'skipped')}
        archive = self.root / (name + '-archive.json')
        self.save(archive, {'head': head, 'git_tree': 'b' * 40, 'destination': '/synthetic/source'})
        self.save(directory / 'plan.json', {'head': head, 'git_tree': 'b' * 40,
                  'archive_proof': str(archive), 'archive_proof_sha256': helper.verification.sha(archive),
                  'worktree': '/synthetic/source', 'collect_only': False, 'targets': ['tests/test_selected.py']})
        source = {'head': head, 'tree': 'b' * 40, 'tracked_exact': True}
        for filename in ('source-before.json', 'source-after.json'):
            self.save(directory / filename, source)
        self.save(directory / 'outcome.json', {
            **{key: True for key in helper.verification.PROOFS}, 'deadline_expired': False,
            'counts': counts, 'raw_junit_counts': raw_counts, 'node_accounting_complete': True,
            'passed': not counts['failed'] and not counts['errors'],
            'returncode': 1 if counts['failed'] or counts['errors'] else 0,
            'wall_seconds': 0.01, 'hygiene_mode': 'strict_unchanged', 'hygiene_unchanged': True})
        self.save(directory / 'nodes.json', {'collected': selected, 'selected': selected})
        self.save(directory / 'phase-accounting.json', {'counts': counts, 'occurrences': [
            {'nodeid': node, 'item_index': ['indexed', index], 'status': status, 'complete': True}
            for index, (node, status) in enumerate(zip(selected, statuses))]})
        self.save(directory / 'pytest-command.json', {'argv': ['python', '-m', 'pytest']})
        self.save(directory / 'hygiene.json', {'unchanged': True})
        self.save(directory / 'guard-denials.json', {'denials': []})
        suite = ET.Element('testsuite')
        for node, status in zip(selected, statuses):
            classname, testname = helper.junit_key(node)
            case = ET.SubElement(suite, 'testcase', classname=classname, name=testname)
            if status != 'passed':
                tag = {'failed': 'failure', 'errors': 'error', 'skipped': 'skipped'}[status]
                ET.SubElement(case, tag, message='literal ' + status).text = 'retained explanation'
        ET.ElementTree(suite).write(directory / 'pytest.xml', encoding='utf-8')
        return {'name': name, 'directory': str(directory), 'head': head, 'kind': kind,
                'classification': 'synthetic contract evidence', 'require_pass': required}

    def edit(self, row, filename, key, value):
        path = Path(row['directory']) / filename
        data = json.loads(path.read_text())
        data[key] = value
        self.save(path, data)

    def test_historical_failure_retains_literal_result_and_its_distinct_head(self):
        current = self.fixture()
        historical = self.fixture('historical', ('failed',), 'c' * 40, False, kind='historical')
        result = helper.summarize({'runs': [current, historical]})
        self.assertTrue(result['required_outcomes_accepted'])
        self.assertFalse(result['all_literal_outcomes_pass'])
        old = result['runs'][1]
        self.assertEqual(old['source_head'], 'c' * 40)
        self.assertEqual(old['counts']['failed'], 1)
        self.assertEqual(old['xml_nonpassing'][0]['messages'][0]['message'], 'literal failed')
        self.assertEqual(old['xml_nonpassing'][0]['nodeid'], 'tests/test_selected.py::test_example[0]')

    def test_required_failure_does_not_become_accepted_from_classification(self):
        row = self.fixture(statuses=('failed',))
        row['classification'] = 'known environment failure; not waived'
        result = helper.summarize({'runs': [row]})
        self.assertTrue(result['all_rows_verified'])
        self.assertFalse(result['required_outcomes_accepted'])
        self.assertFalse(result['runs'][0]['literal_pass'])

    def test_incomplete_and_wrong_source_are_refused_even_for_optional_rows(self):
        for name, file, key, value in (
            ('incomplete', 'outcome.json', 'node_accounting_complete', False),
            ('source', 'source-before.json', 'head', 'd' * 40),
        ):
            with self.subTest(name=name):
                row = self.fixture(name, required=False)
                self.edit(row, file, key, value)
                result = helper.summarize({'runs': [row]})
                self.assertFalse(result['all_rows_verified'])
                self.assertFalse(result['required_outcomes_accepted'])

    def test_repeated_nodes_and_skips_keep_occurrences_and_xml_messages(self):
        row = self.fixture(statuses=('passed', 'skipped'), selected=['tests/test_selected.py::same'] * 2)
        result = helper.summarize({'runs': [row]})
        run = result['runs'][0]
        self.assertTrue(result['required_outcomes_accepted'])
        self.assertEqual(run['selected_occurrences'], 2)
        self.assertEqual(run['raw_junit_counts']['skipped'], 1)
        self.assertEqual(run['xml_nonpassing'][0]['xml_case_index'], 1)
        self.assertEqual(result['verified_execution_observation_totals_including_repeats']['passed'], 1)

    def test_wrong_xml_identity_or_literal_counts_are_refused(self):
        for name, old, new in (('identity', b'test_example', b'another_test'),
                               ('counts', b'<failure', b'<skipped')):
            with self.subTest(name=name):
                row = self.fixture(name, ('failed',), required=False)
                path = Path(row['directory']) / 'pytest.xml'
                raw = path.read_bytes().replace(old, new)
                if name == 'counts':
                    raw = raw.replace(b'</failure>', b'</skipped>')
                path.write_bytes(raw)
                result = helper.summarize({'runs': [row]})
                self.assertFalse(result['all_rows_verified'])

    def test_top_level_proofs_are_hashed_and_nested_xml_is_excluded(self):
        row = self.fixture()
        directory = Path(row['directory'])
        nested = directory / 'child'
        nested.mkdir()
        (nested / 'pytest.xml').write_text('not a second result')
        result = helper.summarize({'runs': [row]})
        hashes = result['runs'][0]['top_level_artifact_sha256']
        self.assertEqual(hashes['pytest.xml'], hashlib.sha256((directory / 'pytest.xml').read_bytes()).hexdigest())
        self.assertTrue(helper.PROOF_FILES <= hashes.keys())
        self.assertNotIn('child/pytest.xml', hashes)

    def test_missing_proof_and_duplicate_directory_cannot_receive_credit(self):
        row = self.fixture()
        duplicate = {**row, 'name': 'repeat'}
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            helper.summarize({'runs': [row, duplicate]})
        (Path(row['directory']) / 'guard-denials.json').unlink()
        result = helper.summarize({'runs': [row]})
        self.assertFalse(result['all_rows_verified'])
        self.assertIn('guard-denials.json', result['runs'][0]['verification_error'])

    def test_phase_occurrence_counter_mismatch_is_refused(self):
        row = self.fixture()
        self.edit(row, 'nodes.json', 'selected', ['tests/test_selected.py::test_example[0]'] * 2)
        self.assertFalse(helper.summarize({'runs': [row]})['all_rows_verified'])

    def test_parameter_spelling_does_not_rewrite_embedded_separators(self):
        self.assertEqual(helper.junit_key('tests/a.py::C::test_x[value::with.parts]'),
                         ('tests.a.C', 'test_x[value::with.parts]'))

    def test_stale_all_passing_xml_identity_is_refused(self):
        row = self.fixture()
        path = Path(row['directory']) / 'pytest.xml'
        tree = ET.parse(path)
        case = next(tree.getroot().iter('testcase'))
        case.set('name', 'test_from_another_run')
        tree.write(path, encoding='utf-8')
        result = helper.summarize({'runs': [row]})
        self.assertFalse(result['all_rows_verified'])
        self.assertFalse(result['required_outcomes_accepted'])

    def test_all_passing_xml_duplicate_cannot_replace_another_selected_occurrence(self):
        row = self.fixture(statuses=('passed', 'passed'), selected=[
            'tests/test_selected.py::first', 'tests/test_selected.py::second'])
        path = Path(row['directory']) / 'pytest.xml'
        tree = ET.parse(path)
        cases = list(tree.getroot().iter('testcase'))
        cases[1].set('name', cases[0].get('name'))
        tree.write(path, encoding='utf-8')
        result = helper.summarize({'runs': [row]})
        self.assertFalse(result['all_rows_verified'])
        self.assertFalse(result['required_outcomes_accepted'])

    def test_raw_xml_failure_cannot_be_accepted_from_passing_phase_claims(self):
        row = self.fixture()
        path = Path(row['directory']) / 'pytest.xml'
        tree = ET.parse(path)
        case = next(tree.getroot().iter('testcase'))
        ET.SubElement(case, 'failure', message='literal failed assertion').text = 'retained failure'
        tree.write(path, encoding='utf-8')
        self.edit(row, 'outcome.json', 'raw_junit_counts',
                  {'passed': 0, 'failed': 1, 'errors': 0, 'skipped': 0})
        result = helper.summarize({'runs': [row]})
        self.assertFalse(result['required_outcomes_accepted'])
        self.assertFalse(result['all_literal_outcomes_pass'])


if __name__ == '__main__':
    unittest.main()
