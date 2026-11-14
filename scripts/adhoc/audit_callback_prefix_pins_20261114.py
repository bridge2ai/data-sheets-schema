"""Issue 6233, 2026-11-14: read-only callback source and pin proposal.

Inputs: assignment base and current checkout, including ignored files.
Output: JSON in assigned scratch. Does not edit any pin or scanner.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from verify_controller_pin_rotation_20261113 import constant, dict_literal, PIN_CONSTANTS, PROTECTED, SCAN


def git(*args):
    return subprocess.check_output(['git', *args])


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    base = 'b35e264571a4e8ba6f152b7fc7053c35758d6823'
    sources = []
    for path in git('diff', '--name-only', base, '--', 'src').decode().splitlines():
        previous = sha(git('show', base + ':' + path))
        search = subprocess.run(['rg', '--hidden', '--no-ignore', '-l', '-F', previous,
                                 '--glob', '!.git', '.'], capture_output=True, text=True)
        if search.returncode not in (0, 1):
            raise RuntimeError(search.stderr)
        sources.append({'path': path, 'base_sha256': previous,
            'current_sha256': sha(Path(path).read_bytes()),
            'base_hash_references_including_ignored': search.stdout.splitlines()})
    controllers = []
    for version in ('v1', 'v2'):
        path = Path(f'src/data_sheets_schema/native_controller_sources_{version}.json')
        document = json.loads(path.read_text())
        for name, pin in document['modules'].items():
            current = sha(Path(pin['path']).read_bytes())
            committed = sha(git('show', document['source_commit'] + ':' + pin['path']))
            controllers.append({'manifest': str(path), 'module': name, 'pin': pin,
                'current': current, 'at_source_commit': committed,
                'matches': current == committed == pin['sha256']})
    constants = [{'path': path, 'constant': name, 'pinned': constant(Path(path), name),
                  'current': sha(Path(target).read_bytes())} for path, name, target in PIN_CONSTANTS]
    constants.append({'path': 'tests/test_native_shared_permission_protocol.py', 'constant': 'CONTROL_SHA',
        'pinned': constant(Path('tests/test_native_shared_permission_protocol.py'), 'CONTROL_SHA'),
        'current': sha(Path('notes/matched_cborg_2026-09-13/native_controls/native_control.py').read_bytes())})
    constants.append({'path': 'src/data_sheets_schema/native_runtime_profiles.py', 'constant': 'SYNTHETIC_PEER_SHA256',
        'pinned': constant(Path('src/data_sheets_schema/native_runtime_profiles.py'), 'SYNTHETIC_PEER_SHA256'),
        'current': sha(Path('tests/fixtures/native_shared_execution/fake_cli.py').read_bytes())})
    scanner = []
    tree = ast.parse(Path(SCAN).read_text())
    for name in ('_NATIVE_V2_RENDER_SOURCES', '_NATIVE_V2_INTEGRATED_RENDER_SOURCES'):
        for path, pinned in dict_literal(tree, name).items():
            previous, current = sha(git('show', base + ':' + path)), sha(Path(path).read_bytes())
            if current != pinned or previous != pinned:
                scanner.append({'table': name, 'path': path, 'pinned': pinned,
                                'base': previous, 'current': current, 'moved_here': previous != current})
    result = {'base': base, 'head': git('rev-parse', 'HEAD').decode().strip(), 'sources': sources,
        'controllers': controllers, 'constants': constants, 'scanner_mismatches': scanner,
        'protected': {path: {'base': sha(git('show', base + ':' + path)),
                            'current': sha(Path(path).read_bytes())} for path in PROTECTED}}
    output = Path(sys.argv[1])
    raw = json.dumps(result, indent=2, sort_keys=True) + '\n'
    output.write_text(raw)
    assert output.read_text() == raw
    print(json.dumps({'path': str(output), 'sha256': sha(raw.encode()), 'sources': sources}, indent=2))


if __name__ == '__main__':
    main()
