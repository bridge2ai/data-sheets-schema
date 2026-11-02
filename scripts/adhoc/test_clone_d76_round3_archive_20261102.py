#!/usr/bin/env python3
"""PR #5213 task7, 2026-11-02: clone isolation and inventory failure contracts.

Inputs: sibling clone helper; outputs: unittest results and owned temporary files.
No repository, existing evidence, provider or GitHub mutation.
"""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clone_d76_round3_archive_20261102 as clone


class CloneContracts(unittest.TestCase):
    def test_traversal_failure_is_not_an_empty_success(self):
        def unreadable(root, **kwargs):
            if kwargs.get('onerror'):
                kwargs['onerror'](PermissionError('unreadable evidence directory'))
            return iter(())
        with patch.object(clone.os, 'walk', side_effect=unreadable):
            with self.assertRaisesRegex(PermissionError, 'unreadable evidence directory'):
                clone.inventory(Path('/unused'))

    @unittest.skipUnless(sys.platform == 'darwin', 'requires actual macOS clonefile')
    def test_actual_clone_has_distinct_files_and_copy_on_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / 'source', root / 'target'
            source.mkdir()
            (source / 'nested').mkdir()
            original = source / 'nested' / 'payload'
            original.write_bytes(b'original clone bytes\n')
            (source / 'literal-link').symlink_to('nested/payload')
            rows = clone.inventory(source)
            clone.clone_tree(source, target, rows)
            self.assertEqual(rows, clone.inventory(source))
            self.assertEqual(rows, clone.inventory(target))
            copied = target / 'nested' / 'payload'
            self.assertNotEqual(original.stat().st_ino, copied.stat().st_ino)
            copied.write_bytes(b'changed cloned bytes\n')
            self.assertEqual(original.read_bytes(), b'original clone bytes\n')
            self.assertEqual((target / 'literal-link').readlink(), Path('nested/payload'))
            with self.assertRaises(FileExistsError):
                clone.clone_tree(source, target, rows)
            self.assertEqual(copied.read_bytes(), b'changed cloned bytes\n')

    @unittest.skipUnless(sys.platform == 'darwin', 'requires actual macOS clonefile')
    def test_clone_error_never_falls_back_to_full_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / 'source', root / 'target'
            source.mkdir()
            (source / 'payload').write_bytes(b'original')
            class RefusedClone:
                def __call__(self, *args):
                    clone.ctypes.set_errno(45)
                    return -1
            class Library:
                clonefile = RefusedClone()
            with patch.object(clone.ctypes, 'CDLL', return_value=Library()):
                with self.assertRaises(OSError):
                    clone.clone_tree(source, target, clone.inventory(source))
            self.assertFalse((target / 'payload').exists())
            self.assertEqual((source / 'payload').read_bytes(), b'original')


if __name__ == '__main__':
    unittest.main()
