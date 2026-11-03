"""#5213 round4, 2026-11-03: contracts for joining measured timing cohorts.

Inputs: synthetic JUnit and independently verified run-shaped records. Outputs:
temporary fixtures and unittest results; no pytest/provider/network execution.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET


SPEC = importlib.util.spec_from_file_location('integration_refresh',
    Path(__file__).with_name('refresh_pr5213_integration_timings_20261102.py'))
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class JoinMeasurements(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.head = 'a' * 40
        self.module = 'tests/test_new.py'
        self.nodes = [self.module + '::test_case[a]', self.module + '::test_case[b]']
        self.collection = self.root / 'collection'
        self.collection.mkdir()
        self.proofs = {self.collection: {'nodes': {'collected': self.nodes[:]},
                                        'files': {'plan.json': 'c' * 64}}}
        self.runs = []
        self.make_run('first', [self.nodes[0]])
        self.make_run('second', [self.nodes[1]])

    def make_run(self, name, nodes):
        directory = self.root / name
        directory.mkdir()
        suite = ET.Element('testsuite')
        for node in nodes:
            ET.SubElement(suite, 'testcase', classname='tests.test_new',
                          name=node.split('::', 1)[1], time='0.125')
        ET.ElementTree(suite).write(directory / 'pytest.xml')
        self.runs.append(directory)
        self.proofs[directory] = {
            'nodes': {'selected': nodes[:]},
            'phases': {'occurrences': [{'nodeid': node, 'complete': True, 'status': 'passed'}
                                       for node in nodes]},
            'outcome': {'worker_count': 2, 'counts': {'passed': len(nodes)}, 'passed': True},
            'files': {'plan.json': 'b' * 64}}

    def join(self, runs=None):
        fixture = self

        class Verifier:
            def run_evidence(self, directory, head, collection=False):
                fixture.assertEqual(head, fixture.head)
                fixture.assertEqual(collection, Path(directory) == fixture.collection)
                return deepcopy(fixture.proofs[Path(directory)])

        with patch.object(helper, 'module_map', return_value={'tests.test_new': self.module}):
            return helper.additional_measurements(self.root, self.head, self.collection,
                self.runs if runs is None else runs, {self.module}, Verifier())

    def test_exact_split_cohorts_keep_each_original_source_and_duration(self):
        xml, rows, proofs, collection = self.join()
        self.assertEqual(len(list(xml)), 2)
        self.assertEqual([row['nodeid'] for row in rows], self.nodes)
        self.assertEqual([row['seconds_decimal'] for row in rows], ['0.125', '0.125'])
        self.assertTrue(all(row['measured_commit'] == self.head for row in rows))
        self.assertEqual([row['directory'] for row in proofs], list(map(str, self.runs)))
        self.assertTrue(all(len(row['files']['pytest.xml']) == 64 for row in proofs))
        self.assertEqual(collection['directory'], str(self.collection))
        self.assertEqual(collection['files'], {'plan.json': 'c' * 64})
        self.assertEqual(collection['expected_occurrences'], dict.fromkeys(self.nodes, 1))

    def test_duplicate_directory_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'duplicate measurement directory'):
            self.join(self.runs + [self.runs[0]])

    def test_duplicate_case_in_distinct_run_is_refused(self):
        self.make_run('duplicate', [self.nodes[0]])
        with self.assertRaisesRegex(ValueError, 'exactly once'):
            self.join()

    def test_missing_case_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'exactly once'):
            self.join(self.runs[:1])

    def test_xml_and_selected_mismatch_is_refused(self):
        self.proofs[self.runs[0]]['nodes']['selected'].append(self.nodes[1])
        with self.assertRaisesRegex(ValueError, 'JUnit'):
            self.join()

    def test_incomplete_failed_or_skipped_phase_is_refused(self):
        for status, complete in [('failed', True), ('skipped', True), ('passed', False)]:
            with self.subTest(status=status, complete=complete):
                row = self.proofs[self.runs[0]]['phases']['occurrences'][0]
                row.update(status=status, complete=complete)
                with self.assertRaisesRegex(ValueError, 'completed passing'):
                    self.join()

    def test_xml_failure_cannot_be_relabelled_by_phase_metadata(self):
        for kind in ('failure', 'error', 'skipped'):
            with self.subTest(kind=kind):
                path = self.runs[0] / 'pytest.xml'
                xml = ET.parse(path)
                case = next(xml.getroot().iter('testcase'))
                for item in list(case):
                    case.remove(item)
                ET.SubElement(case, kind)
                xml.write(path)
                with self.assertRaisesRegex(ValueError, 'unsuccessful'):
                    self.join()

    def test_nonfinite_or_negative_duration_is_refused(self):
        for value in ('NaN', 'Infinity', '-0.1'):
            with self.subTest(value=value):
                path = self.runs[0] / 'pytest.xml'
                xml = ET.parse(path)
                next(xml.getroot().iter('testcase')).set('time', value)
                xml.write(path)
                with self.assertRaisesRegex(ValueError, 'invalid measured duration'):
                    self.join()

    def test_worker_cap_is_enforced(self):
        self.proofs[self.runs[0]]['outcome']['worker_count'] = 3
        with self.assertRaisesRegex(ValueError, 'worker cap'):
            self.join()

    def test_missing_full_collected_module_is_refused(self):
        self.proofs[self.collection]['nodes']['collected'] = []
        with self.assertRaisesRegex(ValueError, 'full collected roster'):
            self.join()

    def test_duplicate_parameter_labels_preserve_occurrence_multiset(self):
        self.proofs[self.collection]['nodes']['collected'] = [self.nodes[0], self.nodes[0]]
        self.make_run('both_occurrences', [self.nodes[0], self.nodes[0]])
        _, rows, _, _ = self.join([self.runs[-1]])
        self.assertEqual([row['nodeid'] for row in rows], [self.nodes[0], self.nodes[0]])


class AdditionalMainRoundTrips(unittest.TestCase):
    """Real local Git, unchanged builder, retirement and chained provenance.

    Only the already-covered completed-run join is supplied as a fixture;
    source commits, duration generation and installation use the real code.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.tree = self.root / 'source'
        self.tree.mkdir()
        (self.tree / 'tests').mkdir()
        (self.tree / 'utils').mkdir()
        helper.git(self.tree, 'init', '-q', '-b', 'timing-roundtrip')
        self.kept = 'tests/test_kept.py'
        self.changed = 'tests/test_changed.py'
        self.retired = 'tests/test_retired.py'
        self.added = 'tests/test_added.py'
        self.unrelated = 'tests/test_main_only.py'
        for path in (self.kept, self.changed, self.retired, self.unrelated):
            (self.tree / path).write_text('def test_case():\n    assert True\n')
        self.updater = (helper.ROOT / helper.UPDATER).read_bytes()
        (self.tree / helper.UPDATER).write_bytes(self.updater)
        self.weights = {'schema_version': 1,
            'source': {'run_id': 123, 'commit': 'historical-ci-source',
                       'test_cases': 4, 'artifacts': ['retained-ci-artifact']},
            'method': 'historical method remains literal',
            'file_seconds': {self.kept: 2.0, self.changed: 3.0,
                             self.retired: 4.0, self.unrelated: 99.0},
            'local_overrides': [{'kind': 'historical-local', 'retained': True}]}
        self.weights_path = self.tree / helper.DURATIONS
        self.weights_path.write_bytes(helper.encode(self.weights))
        self.base_weights = self.weights_path.read_bytes()
        self.base = self.commit('historical measured source and weights')
        self.prior = {'main_commit': self.base, 'round3_commit': self.base,
            'timings_sha256': helper.sha(self.base_weights),
            'main_entries_and_provenance_preserved': True,
            'installation_requested': True,
            'prior_timing_evidence': {'path': 'immutable-prior.json', 'sha256': 'a' * 64,
                                      'wall_projection': {'allowance_minutes': 1}},
            'local': {'kind': 'local_added_file_junit', 'measured_commit': self.base,
                'test_cases': 3, 'original_shards': ['historical-shard'],
                'normalized_artifacts': ['historical-normalized.xml'],
                'file_seconds': {path: self.weights['file_seconds'][path]
                                 for path in (self.kept, self.changed, self.retired)},
                'test_source_sha256': {path: helper.sha((self.tree / path).read_bytes())
                                      for path in (self.kept, self.changed, self.retired)}},
            'cases': [{'nodeid': path + '::test_case', 'file': path,
                       'seconds': self.weights['file_seconds'][path],
                       'outcome': 'passed', 'origin': 'local_round3_junit'}
                      for path in (self.kept, self.changed, self.retired)]}
        self.prior_path = self.root / 'historical-evidence.json'
        self.prior_path.write_bytes(helper.encode(self.prior))
        self.prior_bytes = self.prior_path.read_bytes()
        (self.tree / self.changed).write_text('def test_case():\n    assert 1 == 1\n')
        (self.tree / self.added).write_text('def test_case_a():\n    assert True\n\ndef test_case_b():\n    assert True\n')
        (self.tree / self.retired).unlink()
        self.head = self.commit('new measured tests and explicit retirement')
        self.durations = {self.changed: [('test_case', '0.750')],
                          self.added: [('test_case_a', '0.125'), ('test_case_b', '0.375')]}
        self.manifest = self.root / 'measurements.json'
        self.write_manifest(self.base, self.head, self.prior_path, [self.retired])

    def commit(self, message):
        helper.git(self.tree, 'add', '--all')
        helper.git(self.tree, '-c', 'user.name=Offline timing contract',
                   '-c', 'user.email=timing-contract@localhost', '-c', 'core.hooksPath=/dev/null',
                   'commit', '-q', '-m', message)
        return helper.git(self.tree, 'rev-parse', 'HEAD').decode().strip()

    def write_manifest(self, base, head, prior, retired):
        self.manifest.write_bytes(helper.encode({'base_commit': base, 'measured_commit': head,
            'prior_evidence': str(prior), 'prior_evidence_sha256': helper.sha(prior.read_bytes()),
            'collection': str(self.root / 'full-collection'),
            'runs': [str(self.root / 'measured-run')], 'retired_modules': retired}))

    def join_fixture(self, tree, head, collection, runs, required, verifier):
        self.assertEqual(tree, self.tree)
        self.assertEqual(head, self.head)
        self.assertEqual(set(required), set(self.durations))
        self.assertTrue(callable(verifier.run_evidence))
        suite, rows = ET.Element('testsuite'), []
        for path, cases in self.durations.items():
            for name, seconds in cases:
                ET.SubElement(suite, 'testcase', classname=path[:-3].replace('/', '.'),
                              name=name, time=seconds)
                rows.append({'nodeid': path + '::' + name, 'file': path,
                             'seconds': float(seconds), 'seconds_decimal': seconds,
                             'outcome': 'passed', 'origin': 'local_round4_junit',
                             'measured_commit': head})
        proofs = [{'directory': runs[0], 'head': head, 'files': {'pytest.xml': 'b' * 64}}]
        collection_proof = {'directory': collection, 'head': head,
                            'files': {'nodes.json': 'c' * 64},
                            'expected_occurrences': {row['nodeid']: 1 for row in rows}}
        return suite, rows, proofs, collection_proof

    def refresh(self, name, install=False):
        from contextlib import redirect_stdout
        import io
        import json
        output = self.root / name
        argv = ['refresh', '--additional-manifest', str(self.manifest), '--tree', str(self.tree),
                '--output-dir', str(output)] + (['--install'] if install else [])
        stdout = io.StringIO()
        with patch.object(helper, 'MAIN', self.base), patch.object(helper.sys, 'argv', argv), \
                patch.object(helper, 'additional_measurements', side_effect=self.join_fixture), \
                redirect_stdout(stdout):
            helper.additional_main()
        return output, json.loads(stdout.getvalue())

    def test_dry_run_preserves_history_and_links_complete_collection(self):
        output, summary = self.refresh('preview')
        evidence = helper.read(output / 'evidence.json')
        result = helper.read(output / 'timings.json')
        self.assertEqual(self.weights_path.read_bytes(), self.base_weights)
        self.assertEqual(self.prior_path.read_bytes(), self.prior_bytes)
        self.assertFalse(summary['installed'])
        self.assertFalse(evidence['installation_requested'])
        self.assertFalse((output / 'installation.json').exists())
        self.assertEqual(result['source'], self.weights['source'])
        self.assertEqual(result['method'], self.weights['method'])
        self.assertEqual(result['local_overrides'][:-1], self.weights['local_overrides'])
        self.assertEqual(result['file_seconds'], {**self.weights['file_seconds'],
                                                self.changed: 0.75, self.added: 0.5})
        self.assertEqual(evidence['local']['kind'], 'composite_projection_not_one_measurement')
        self.assertNotIn('measured_commit', evidence['local'])
        self.assertNotIn('original_shards', evidence['local'])
        self.assertNotIn('normalized_artifacts', evidence['local'])
        self.assertEqual(evidence['local']['test_cases'], 4)
        self.assertEqual(len(evidence['cases']), 4)
        self.assertEqual(len({row['nodeid'] for row in evidence['cases']}), 4)
        self.assertEqual(set(evidence['local']['file_seconds']), {self.kept, self.changed, self.added})
        self.assertEqual(evidence['local_source_commits'], {
            self.kept: self.base, self.changed: self.head, self.added: self.head})
        self.assertEqual(evidence['preceding_integration_evidence'], {
            'path': str(self.prior_path), 'sha256': helper.sha(self.prior_bytes)})
        update = evidence['additional_measurements']
        self.assertEqual(update['input_manifest'], {
            'path': str(self.manifest), 'sha256': helper.sha(self.manifest.read_bytes())})
        self.assertEqual(update['collection']['head'], self.head)
        self.assertEqual(update['collection']['files'], {'nodes.json': 'c' * 64})
        self.assertEqual(update['collection']['expected_occurrences'], {
            self.changed + '::test_case': 1, self.added + '::test_case_a': 1,
            self.added + '::test_case_b': 1})
        self.assertEqual(update['retired_modules'], {self.retired: {
            'base_commit': self.base, 'source_sha256': self.prior['local']['test_source_sha256'][self.retired],
            'absent_at_measured_commit': self.head}})
        self.assertEqual((self.tree / helper.UPDATER).read_bytes(), self.updater)

    def test_install_matches_preview_and_persists_actual_installation_proof(self):
        preview, _ = self.refresh('preview')
        output, summary = self.refresh('installed', install=True)
        generated = (output / 'timings.json').read_bytes()
        self.assertEqual(generated, (preview / 'timings.json').read_bytes())
        self.assertEqual(self.weights_path.read_bytes(), generated)
        self.assertTrue(summary['installed'])
        self.assertTrue(helper.read(output / 'evidence.json')['installation_requested'])
        proof = helper.read(output / 'installation.json')
        self.assertTrue(proof['installation_verified'])
        self.assertEqual(proof['target'], str(self.weights_path))
        self.assertEqual(proof['target_sha256'], helper.sha(generated))
        self.assertEqual(proof['generated_timings_sha256'], helper.sha(generated))
        self.assertEqual(proof['target_before_sha256'], helper.sha(self.base_weights))
        self.assertEqual(proof['evidence_sha256'], helper.sha((output / 'evidence.json').read_bytes()))
        self.assertEqual(self.prior_path.read_bytes(), self.prior_bytes)

    def test_second_refresh_retains_each_unmodified_measurement_source(self):
        first, _ = self.refresh('first-installed', install=True)
        first_evidence = (first / 'evidence.json').read_bytes()
        first_head = self.head
        installed_base = self.commit('first measured weights installed')
        (self.tree / self.changed).write_text('def test_case():\n    assert 2 == 2\n')
        self.head = self.commit('second measured test revision')
        self.durations = {self.changed: [('test_case', '1.250')]}
        self.write_manifest(installed_base, self.head, first / 'evidence.json', [])
        second, _ = self.refresh('second-preview')
        evidence = helper.read(second / 'evidence.json')
        self.assertEqual(evidence['local_source_commits'], {
            self.kept: self.base, self.added: first_head, self.changed: self.head})
        self.assertEqual(evidence['local']['file_seconds'], {
            self.kept: 2.0, self.added: 0.5, self.changed: 1.25})
        self.assertEqual(evidence['local']['test_cases'], 4)
        self.assertEqual(len(evidence['cases']), 4)
        self.assertEqual((first / 'evidence.json').read_bytes(), first_evidence)
        self.assertEqual(self.prior_path.read_bytes(), self.prior_bytes)
        self.assertEqual(evidence['preceding_integration_evidence']['sha256'], helper.sha(first_evidence))
        self.assertEqual(evidence['additional_measurements']['retired_modules'], {})

    def test_missing_extra_and_duplicate_retirements_refuse_before_outputs(self):
        for retired in ([], [self.retired, self.kept], [self.retired, self.retired]):
            with self.subTest(retired=retired):
                self.write_manifest(self.base, self.head, self.prior_path, retired)
                with self.assertRaisesRegex(ValueError, 'retirement list'):
                    self.refresh('must-not-write')
                self.assertFalse((self.root / 'must-not-write').exists())
                self.assertEqual(self.weights_path.read_bytes(), self.base_weights)

    def test_main_builder_byte_change_is_refused(self):
        (self.tree / helper.UPDATER).write_bytes(self.updater + b'\n# unreviewed change\n')
        with self.assertRaisesRegex(ValueError, 'main timing builder changed'):
            self.refresh('must-not-write')
        self.assertFalse((self.root / 'must-not-write').exists())

    def test_prior_per_file_commit_cannot_claim_different_test_bytes(self):
        self.prior['local_source_commits'] = {
            self.kept: self.base, self.changed: self.head, self.retired: self.base}
        self.prior_path.write_bytes(helper.encode(self.prior))
        self.write_manifest(self.base, self.head, self.prior_path, [self.retired])
        with self.assertRaisesRegex(ValueError, 'per-file measured source identity'):
            self.refresh('must-not-write')
        self.assertFalse((self.root / 'must-not-write').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
