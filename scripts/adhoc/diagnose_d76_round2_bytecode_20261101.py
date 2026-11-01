#!/usr/bin/env python3
"""D76-R2-H2: compare fresh source compilation with py_compile payload bytes.

Input: fresh external output directory. Output: synthetic source/pyc and JSON.
No unmarshalling, cached-code loading, provider or network; 2026-11-01, PR #5213.
"""
import argparse
import hashlib
import json
import marshal
from pathlib import Path
import py_compile


def describe(candidate, actual):
    return {'equal': candidate == actual, 'sha256': hashlib.sha256(candidate).hexdigest(),
            'bytes': len(candidate), 'first_differences': [index for index, (left, right)
                in enumerate(zip(candidate, actual)) if left != right][:20]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.output / 'fixture.py'
    source.write_text('VALUE = 3\n')
    cache = args.output / 'fixture.pyc'
    py_compile.compile(str(source), cfile=str(cache), doraise=True)
    actual = cache.read_bytes()[16:]
    raw = source.read_bytes()
    inline = marshal.dumps(compile(raw, str(source), 'exec', dont_inherit=True, optimize=0))
    compiled = compile(raw, str(source), 'exec', dont_inherit=True, optimize=0)
    held_code = marshal.dumps(compiled)
    source_name = str(source)
    compiled_with_name = compile(raw, source_name, 'exec', dont_inherit=True, optimize=0)
    held_name_and_code = marshal.dumps(compiled_with_name)
    result = {'actual_sha256': hashlib.sha256(actual).hexdigest(),
              'inline': describe(inline, actual), 'held_code': describe(held_code, actual),
              'held_name_and_code': describe(held_name_and_code, actual)}
    (args.output / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
