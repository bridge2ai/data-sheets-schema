#!/usr/bin/env python3
"""Diagnose PR6302 archive source-object proof failures, 2026-11-21.

Inputs: archive checkout, fresh evidence directory. Outputs: exact Git query,
raw stdout/stderr and typed header proof. Read-only to the supplied checkout.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def main():
    root, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    paths = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r', '--name-only', head,
                                     '--', 'src/data_sheets_schema'], text=True).splitlines()
    environment = None
    if '--authority' in sys.argv:
        sys.path[:] = [value for value in sys.path if not (Path(value) / 'data_sheets_schema').is_dir()]
        sys.path.insert(0, str(root / 'src'))
        from data_sheets_schema import native_execution_authority_v2 as authority
        identity = authority.dependency_identity()
        (out / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
        base = identity['base']
        head = base['source_commit']
        pins = dict(base['package_sources'])
        pins.update({pin['path']: pin['sha256'] for pin in base['modules'].values()})
        pins.update({pin['path']: pin['sha256'] for pin in identity['additional_modules'].values()})
        paths = list(pins)
        environment = authority.git_env()
    query = ''.join(head + ':' + path + '\n' for path in sorted(paths)).encode()
    result = subprocess.run(['git', '--no-replace-objects', 'cat-file', '--batch'], cwd=root,
                            input=query, capture_output=True, timeout=60, check=True, env=environment)
    (out / 'query.txt').write_bytes(query)
    (out / 'stdout.bin').write_bytes(result.stdout)
    (out / 'stderr.bin').write_bytes(result.stderr)
    offset, records = 0, []
    for path in sorted(paths):
        end = result.stdout.find(b'\n', offset)
        header = result.stdout[offset:end]
        match = re.fullmatch(rb'([0-9a-f]{40}|[0-9a-f]{64}) blob (0|[1-9][0-9]*)', header)
        if not match:
            records.append({'path': path, 'offset': offset, 'invalid_header_hex': header[:1000].hex()})
            break
        size = int(match[2])
        raw = result.stdout[end + 1:end + 1 + size]
        offset = end + size + 2
        records.append({'path': path, 'bytes': size, 'sha256': hashlib.sha256(raw).hexdigest(),
                        'matches_archive_file': raw == (root / path).read_bytes()})
    proof = {'head': head, 'paths': len(paths), 'records': records,
             'parsed_all_bytes': offset == len(result.stdout), 'stdout_bytes': len(result.stdout)}
    (out / 'proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({key: value for key, value in proof.items() if key != 'records'}))
    print(json.dumps(records[-1]))


if __name__ == '__main__':
    main()
