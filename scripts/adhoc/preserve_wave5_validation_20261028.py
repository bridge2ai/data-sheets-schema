#!/usr/bin/env python3
# Purpose: preserve compact Wave5 validation results without publishing full source inventories.
# Inputs: completed external evidence roots; output: fresh repository result packet and digests.
# Refs #5211/#5210/#5213 and E3x/#2912; 2026-10-28. Original evidence is read-only.
"""Keep outcomes verbatim; hashes reference external inventories, never replace their evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import archive_n2_restack_validation_20261027 as evidence

RETAIN = frozenset({
    'outcome.json', 'plan.json', 'pytest.log', 'pytest.xml', 'pytest-command.json',
    'bootstrap.json', 'scoring-identity.json', 'command.json', 'environment.json',
    'stdout.log',
})


def snapshot(root):
    root = evidence.physical(root)
    files, directories = {}, []
    for path in sorted(root.iterdir()):
        if path.is_symlink():
            raise ValueError('symlink at evidence boundary: ' + str(path))
        if path.is_dir():
            directories.append(path.name)
        elif path.suffix in {'.json', '.log', '.xml'}:
            files[path.name] = evidence.read_file(path)
    if 'outcome.json' not in files:
        raise ValueError('completed outcome.json required')
    outcome = json.loads(files['outcome.json']['raw'])
    if not isinstance(outcome, dict) or type(outcome.get('returncode')) is not int:
        raise ValueError('terminal integer returncode required; failure results are retained too')
    return files, directories


def preserve(roots, output):
    roots = [evidence.physical(root) for root in roots]
    if len(roots) != len(set(roots)):
        raise ValueError('duplicate evidence roots')
    output = Path(output)
    if (not output.is_absolute() or output.resolve() != output or output.exists()
            or any(output.is_relative_to(root) or root.is_relative_to(output) for root in roots)):
        raise ValueError('fresh physical output outside evidence roots required')
    captured = [(root, *snapshot(root)) for root in roots]
    output.mkdir(parents=True, exist_ok=False)
    runs = []
    for number, (root, files, directories) in enumerate(captured, 1):
        folder = output / f'run-{number:02}'
        folder.mkdir()
        rows = []
        for name, item in files.items():
            retained = name in RETAIN
            if retained:
                target = folder / name
                with target.open('xb') as stream:
                    stream.write(item['raw'])
                target.chmod(item['mode'])
                if evidence.read_file(target) != item:
                    raise ValueError('copied result bytes/mode differ')
            rows.append({'name': name, 'bytes': len(item['raw']),
                         'sha256': evidence.sha(item['raw']),
                         'retention': 'copied_verbatim' if retained else 'external_hash_reference',
                         'reason': 'compact result evidence' if retained else
                         'full source/origin inventories stay external; regenerate using retained plan and helper'})
        runs.append({'original_root': str(root), 'packet_directory': folder.name,
                     'files': rows, 'unread_external_directories': directories,
                     'original_outcome': json.loads(files['outcome.json']['raw']),
                     'pass_claim': 'copied outcome only; no new acceptance inferred'})
    for root, files, directories in captured:
        if snapshot(root) != (files, directories):
            raise ValueError('original evidence changed during preservation')
    helpers = [Path(__file__).resolve(), Path(evidence.__file__).resolve()]
    manifest = {
        'format': 'wave5_compact_validation_evidence_v1',
        'scope': 'compact results, external raw inventory digests, no historical score changes',
        'selection': 'explicit top-level regular JSON/log/XML files, including ignored files',
        'source_and_origin_inventories_embedded': False,
        'helpers': [{'name': path.name, 'sha256': evidence.sha(evidence.read_file(path)['raw'])}
                    for path in helpers],
        'runs': runs,
    }
    with (output / 'manifest.json').open('x') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(output / 'manifest.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    preserve(args.evidence, args.output)


if __name__ == '__main__':
    main()
