"""Propose, never apply, controller pins for issues 6244 and 6249.

Inputs: checkout bytes and a commit containing the controller fix.
Output: JSON to stdout, including exact in-memory replacement hashes.
Written 2026-11-15; the Claude lead owns the actual pin rotation.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    root = Path(__file__).resolve().parents[2]
    commit = sys.argv[1]
    proposals = []
    candidates = {}

    def replace(path, field, old, new):
        raw = candidates.get(path, (root / path).read_bytes())
        assert old.encode() in raw, (path, field)
        candidates[path] = raw.replace(old.encode(), new.encode())
        proposals.append({'file': path, 'field': field, 'old': old, 'new': new})

    controller = 'notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py'
    controller_raw = (root / controller).read_bytes()
    committed = subprocess.check_output(['git', '-C', str(root), 'show', f'{commit}:{controller}'])
    assert committed == controller_raw
    manifest_hashes = {}
    for version in ('v1', 'v2'):
        path = f'src/data_sheets_schema/native_controller_sources_{version}.json'
        raw = (root / path).read_bytes()
        manifest = json.loads(raw)
        for entry in manifest['modules'].values():
            source = subprocess.check_output(['git', '-C', str(root), 'show', f'{commit}:{entry["path"]}'])
            expected = sha(controller_raw) if entry['path'] == controller else entry['sha256']
            assert sha(source) == expected, entry['path']
        replace(path, 'source_commit', manifest['source_commit'], commit)
        replace(path, 'modules.run_native_canary.sha256',
                manifest['modules']['run_native_canary']['sha256'], sha(controller_raw))
        manifest_hashes[version] = (sha(raw), sha(candidates[path]))

    for filename, field, version in (
        ('native_attribution_controller.py', 'SOURCES_SHA256', 'v1'),
        ('native_attribution_controller_v2.py', 'SOURCES_SHA256', 'v2'),
        ('native_shared_authority_wire.py', 'CONTROLLER_SOURCES_SHA256', 'v2'),
    ):
        replace('src/data_sheets_schema/' + filename, field, *manifest_hashes[version])

    scanner = '.claude/skills/d4d-generation-specificity-audit/scan.py'
    for path in ('src/data_sheets_schema/native_controller_sources_v2.json',
                 'src/data_sheets_schema/native_attribution_controller_v2.py'):
        replace(scanner, '_NATIVE_V2_INTEGRATED_RENDER_SOURCES[' + path + ']',
                sha((root / path).read_bytes()), sha(candidates[path]))

    control = 'notes/matched_cborg_2026-09-13/native_controls/native_control.py'
    report = {'source_commit': commit, 'controller_sha256': sha(controller_raw),
              'proposals': proposals,
              'proposed_file_hashes': {path: sha(raw) for path, raw in candidates.items()},
              'unchanged_CONTROL_SHA': sha((root / control).read_bytes()),
              'verification_script': 'scripts/adhoc/verify_controller_pin_rotation_20261113.py',
              'verification_script_change': 'none; rerun after lead rotation',
              'serialization': 'literal UTF-8 replacements only; preserve all other bytes'}
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
