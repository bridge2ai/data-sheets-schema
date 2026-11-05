#!/usr/bin/env python3
"""Stdlib path-boundary contracts for #5213 scratch commits, 2026-11-02.

No Git writes, source mutations, pytest or provider calls. Inputs: sibling helper.
Output: unittest assertions using only owned temporary directories.
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('mutation_commit_under_test', HERE / 'commit_d76_order_mutant_20261102.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class PhysicalPathContracts(unittest.TestCase):
    def test_relative_and_traversing_parent_are_refused(self):
        for path in (Path('relative'), Path('/tmp/../private/tmp')):
            with self.subTest(path=path), self.assertRaises(ValueError):
                helper.physical(path)

    def test_symlinked_parent_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / 'real').mkdir()
            (root / 'link').symlink_to(root / 'real', target_is_directory=True)
            with self.assertRaises(ValueError):
                helper.physical(root / 'link')

    def test_existing_physical_parent_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.assertEqual(helper.physical(root), root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
