#!/usr/bin/env python3
"""Record/remove authorized Round 5 pytest basetemps, 2026-11-07.

Inputs: saved test outcomes/JUnit under scratch-native-u3a-r5; --target for
one removal. Outputs: preflight JSON, guarded deletion TSV in that same root.
No source/evidence/venv deletion. Scan includes dotfiles and ignored fixtures.
Run --plan, review it, remove one canary, verify it, then remaining literal paths.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3a-r5'
GUARD = Path('/Users/marcin/.codex/skills/safe-delete/scripts/guarded_rm.sh')


def validate(target):
    assert target.name == 'cases' and target.resolve() == target
    assert target.is_relative_to(SCRATCH) and target.is_dir()
    parent = target.parent
    outcome = json.loads((parent / 'outcome.json').read_bytes())
    assert outcome['cleanup_verified'] and not outcome['observed_surviving_pids']
    assert (parent / 'pytest.xml').stat().st_size and (parent / 'pytest.log').stat().st_size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--target', type=Path)
    parser.add_argument('--remove', action='store_true')
    args = parser.parse_args()
    if args.plan:
        assert not args.target and not args.remove
        assert not (ROOT.parent / 'plans/native_quiet_window.lock').exists()
        targets = sorted(path.parent / 'cases' for path in SCRATCH.rglob('outcome.json')
                         if (path.parent / 'cases').is_dir())
        links = []
        for directory, dirs, files in os.walk(SCRATCH, followlinks=False):
            for name in dirs + files:
                path = Path(directory) / name
                if path.is_symlink():
                    links.append((path, path.resolve()))
        rows = []
        for target in targets:
            validate(target)
            hardlinks = [str(path) for path in target.rglob('*')
                         if not path.is_symlink() and path.is_file() and path.stat().st_nlink > 1]
            inbound = [str(path) for path, resolved in links
                       if resolved.is_relative_to(target) and not path.is_relative_to(target)]
            handles = subprocess.run(['/usr/sbin/lsof', '+D', str(target)], capture_output=True, text=True)
            assert handles.returncode in (0, 1) and not handles.stdout.strip(), handles.stdout
            references = subprocess.run(['rg', '--no-ignore', '--hidden', '-l', '-F', str(target),
                                         str(SCRATCH)], capture_output=True, text=True)
            assert references.returncode in (0, 1)
            row = {'path': str(target), 'hardlinks': hardlinks, 'inbound_symlinks': inbound,
                   'open_handles': [], 'references': references.stdout.splitlines(),
                   'size_kib': int(subprocess.check_output(['/usr/bin/du', '-sk', str(target)]).split()[0])}
            rows.append(row)
            subprocess.run([str(GUARD), '--expect-parent', str(target.parent), '--dry-run', str(target)], check=True)
        with (SCRATCH / 'cleanup-plan.json').open('x') as stream:
            json.dump(rows, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print(json.dumps({'targets': len(rows), 'plan': str(SCRATCH / 'cleanup-plan.json')}))
        return
    assert args.target
    validate(args.target)
    rows = json.loads((SCRATCH / 'cleanup-plan.json').read_bytes())
    row = next(row for row in rows if row['path'] == str(args.target))
    assert not row['inbound_symlinks'], 'review/repoint inbound links before removal'
    command = [str(GUARD), '--expect-parent', str(args.target.parent), '--log', str(SCRATCH / 'deletions.tsv'),
               '--note', 'Authorized recorded Round 5 synthetic pytest basetemp']
    if not args.remove:
        command.append('--dry-run')
    subprocess.run(command + [str(args.target)], check=True)
    if args.remove:
        assert not args.target.exists()
        assert (args.target.parent / 'pytest.xml').stat().st_size
        assert (args.target.parent / 'outcome.json').stat().st_size


if __name__ == '__main__':
    main()
