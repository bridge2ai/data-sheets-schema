#!/usr/bin/env python3
"""PR #5213 round-2 classifier contracts; synthetic files only, 2026-11-01.

Input: stdlib temporary directories. Output: unittest verdicts; no production/network.
"""
import hashlib
import importlib.util
from pathlib import Path
import py_compile
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('round2_hygiene', HERE / 'd76_round2_hygiene_20261101.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HygieneContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'notes' / 'fixture.py'
        self.source.parent.mkdir()
        self.source.write_text('VALUE = 3\n')
        self.snapshot = {'entries': {'notes/fixture.py': {
            'mode': '100644', 'sha256': hashlib.sha256(self.source.read_bytes()).hexdigest()}}}
        self.before = MODULE.notes_listing(self.root)

    def make_cache(self, mode=py_compile.PycInvalidationMode.TIMESTAMP):
        cache = self.source.parent / '__pycache__' / ('fixture.' + sys.implementation.cache_tag + '.pyc')
        py_compile.compile(str(self.source), cfile=str(cache), doraise=True, invalidation_mode=mode)
        return cache

    def classify(self, cache, before_status=''):
        relative = str(cache.relative_to(self.root))
        return MODULE.classify(self.root, self.snapshot, self.before, before_status, '!! ' + relative + '\0')

    def test_valid_timestamp_bytecode_is_retained_and_explicitly_not_pristine(self):
        cache = self.make_cache()
        result = self.classify(cache)
        self.assertTrue(result['passed'], result)
        self.assertFalse(result['unchanged'])
        self.assertEqual(result['allowed_new_bytecode'][0]['header_kind'], 'timestamp')
        self.assertTrue(cache.is_file())
        self.assertIn('!! ', result['after'])

    def test_valid_checked_hash_bytecode(self):
        result = self.classify(self.make_cache(py_compile.PycInvalidationMode.CHECKED_HASH))
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['allowed_new_bytecode'][0]['header_kind'], 'checked_hash')

    def test_valid_unchecked_hash_still_requires_exact_compiled_payload(self):
        result = self.classify(self.make_cache(py_compile.PycInvalidationMode.UNCHECKED_HASH))
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['allowed_new_bytecode'][0]['header_kind'], 'unchecked_hash')

    def test_symlinked_bytecode_is_refused(self):
        cache = self.make_cache()
        foreign = self.root / 'saved.pyc'
        cache.rename(foreign)
        cache.symlink_to(foreign)
        self.assertFalse(self.classify(cache)['passed'])

    def test_non_bytecode_is_refused(self):
        junk = self.source.parent / '__pycache__' / 'artifact.json'
        junk.parent.mkdir()
        junk.write_text('{}')
        self.assertFalse(self.classify(junk)['passed'])

    def test_symlinked_source_is_refused_even_with_matching_bytes(self):
        cache = self.make_cache()
        foreign = self.root / 'saved-source.py'
        self.source.rename(foreign)
        self.source.symlink_to(foreign)
        self.assertFalse(self.classify(cache)['passed'])

    def test_changed_source_is_refused(self):
        cache = self.make_cache()
        self.source.write_text('VALUE = 9\n')
        self.assertFalse(self.classify(cache)['passed'])

    def test_unknown_source_is_refused(self):
        cache = self.make_cache()
        self.snapshot['entries'].clear()
        self.assertFalse(self.classify(cache)['passed'])

    def test_forged_payload_with_correct_header_is_refused(self):
        cache = self.make_cache()
        cache.write_bytes(cache.read_bytes()[:16] + b'not compiled source')
        self.assertFalse(self.classify(cache)['passed'])

    def test_modified_header_is_refused(self):
        cache = self.make_cache()
        raw = bytearray(cache.read_bytes())
        raw[8] ^= 1
        cache.write_bytes(raw)
        self.assertFalse(self.classify(cache)['passed'])

    def test_parent_traversal_and_foreign_paths_are_refused(self):
        for path in ('notes/../fixture.pyc', '/notes/fixture.pyc', 'src/__pycache__/fixture.pyc'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                MODULE.bytecode_record(self.root, path, self.snapshot)

    def test_other_global_status_is_refused(self):
        cache = self.make_cache()
        result = MODULE.classify(self.root, self.snapshot, self.before, '',
            '!! ' + str(cache.relative_to(self.root)) + '\0?? unexpected.txt\0')
        self.assertFalse(result['passed'])

    def test_nonempty_starting_status_is_refused(self):
        self.assertFalse(self.classify(self.make_cache(), '!! preexisting.pyc\0')['passed'])

    def test_missing_status_evidence_is_refused(self):
        self.make_cache()
        result = MODULE.classify(self.root, self.snapshot, self.before, '', '')
        self.assertFalse(result['passed'])

    def test_empty_notes_run_remains_pristine(self):
        result = MODULE.classify(self.root, self.snapshot, self.before, '', '')
        self.assertTrue(result['passed'])
        self.assertTrue(result['unchanged'])

    def test_mixed_or_broad_notes_targets_are_refused(self):
        for targets in (['tests/test_x.py'], ['notes'],
                        [MODULE.NOTES_TARGETS['offline-audit'][0]]):
            with self.subTest(targets=targets), self.assertRaises(ValueError):
                MODULE.validate_targets('offline-canary', targets)

    def test_exact_notes_targets_and_single_canary_are_admitted(self):
        MODULE.validate_targets('offline-canary', list(MODULE.NOTES_TARGETS['offline-canary']))
        MODULE.validate_targets('offline-canary', [MODULE.NOTES_TARGETS['offline-canary'][0] + '::test_case'])

    def tracked_note(self, relative):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('VALUE = 1\n')
        self.snapshot['entries'][relative] = {'mode': '100644', 'sha256': MODULE.sha(path.read_bytes())}
        return path

    def test_foreign_known_package_and_submodule_are_refused(self):
        source = self.tracked_note(MODULE.MATCHED + '/audit_controls/native.py')
        foreign = self.root / 'foreign.py'
        foreign.write_bytes(source.read_bytes())
        for name, module in (
            ('audit_controls', SimpleNamespace(__file__=None, __path__=[str(self.root)])),
            ('audit_controls.native', SimpleNamespace(__file__=str(foreign))),
        ):
            with self.subTest(name=name), patch.dict(sys.modules, {name: module}), self.assertRaises(ValueError):
                MODULE.notes_origins(self.root, self.snapshot)

    def test_tracked_namespace_and_submodule_are_attested(self):
        source = self.tracked_note(MODULE.MATCHED + '/audit_controls/native.py')
        modules = {'audit_controls': SimpleNamespace(__file__=None, __path__=[str(source.parent)]),
                   'audit_controls.native': SimpleNamespace(__file__=str(source))}
        with patch.dict(sys.modules, modules):
            result = MODULE.notes_origins(self.root, self.snapshot)
        self.assertTrue(result['audit_controls']['namespace_verified_against_tracked_source'])
        self.assertEqual(result['audit_controls.native']['sha256'], MODULE.sha(source.read_bytes()))

    def test_direct_helper_foreign_origin_is_refused(self):
        source = self.tracked_note('notes/claudecode_direct/prepare_direct.py')
        foreign = self.root / 'foreign.py'
        foreign.write_bytes(source.read_bytes())
        with patch.dict(sys.modules, {'prepare_direct': SimpleNamespace(__file__=str(foreign))}), self.assertRaises(ValueError):
            MODULE.notes_origins(self.root, self.snapshot)

    def test_namespace_cannot_add_a_foreign_search_path(self):
        source = self.tracked_note(MODULE.MATCHED + '/audit_controls/native.py')
        module = SimpleNamespace(__file__=None, __path__=[str(source.parent), str(self.root)])
        with patch.dict(sys.modules, {'audit_controls': module}), self.assertRaises(ValueError):
            MODULE.notes_origins(self.root, self.snapshot)


if __name__ == '__main__':
    unittest.main(verbosity=2)
