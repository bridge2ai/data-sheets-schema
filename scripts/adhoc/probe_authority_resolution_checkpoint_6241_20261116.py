"""Probe issue 6241 resolution checkpoint semantics, 2026-11-16.

Input: scratch directory argument. Output: JSON evidence on stdout.
Synthetic source only; no provider or native executable. Compare current
loader with the proposed per-pass Path.resolve memoization in isolation.
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

from data_sheets_schema import native_execution_authority_v2 as authority


def probe(scratch, reuse):
    with tempfile.TemporaryDirectory(dir=scratch) as directory:
        root = Path(directory).resolve()
        package = root / 'src/data_sheets_schema'
        package.mkdir(parents=True)
        source = b'VALUE = 1\n'
        (package / 'fixture.py').write_bytes(source)
        outside = root / 'outside'
        outside.mkdir()
        (outside / 'fixture.py').write_bytes(source)
        pins = {'src/data_sheets_schema/fixture.py': hashlib.sha256(source).hexdigest()}
        original = Path.resolve
        cache = {}
        def resolve(path, strict=False):
            key = (str(path), strict)
            if not reuse or key not in cache:
                result = original(path, strict=strict)
                if reuse:
                    cache[key] = result
                return result
            return cache[key]
        try:
            with patch.object(authority, 'ROOT', root), patch.object(Path, 'resolve', resolve):
                with authority.loaded_verified_package_module(
                        'data_sheets_schema.fixture', package_sources=pins) as module:
                    assert module.VALUE == 1
                    assert authority._package_name(module.__file__) == module.__name__
                    (package / 'fixture.py').rename(package / 'original.py')
                    (package / 'fixture.py').symlink_to(outside / 'fixture.py')
            return {'reuse_resolution': reuse, 'accepted': True, 'diagnostic': None}
        except ValueError as error:
            return {'reuse_resolution': reuse, 'accepted': False, 'diagnostic': str(error)}


if __name__ == '__main__':
    scratch = Path(sys.argv[1])
    results = [probe(scratch, False), probe(scratch, True)]
    print(json.dumps(results, indent=2))
    assert not results[0]['accepted'], results
    assert results[1]['accepted'], results
