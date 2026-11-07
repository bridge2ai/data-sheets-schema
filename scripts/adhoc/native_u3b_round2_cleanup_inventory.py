"""Inventory explicitly named round-2 basetemps before removal, 2026-11-07.

Inputs: round-2 evidence directory and literal completed basetemp paths.
Output: cleanup-inventory.json; no deletions. Includes ignored files and links,
open handles, size and inbound references without spawning Python per symlink.
Serves the ruling's authorized transient-basetemp cleanup, preserving evidence.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
targets = [Path(value) for value in sys.argv[2:]]
assert all(p.is_absolute() and p.parent == root and p.name.endswith('-tmp')
           and p.is_dir() and not p.is_symlink() for p in targets)
links = []
for directory, dirs, files in os.walk(root):
    for name in dirs + files:
        path = Path(directory) / name
        if path.is_symlink():
            links.append((str(path), path.resolve()))
result = []
for target in targets:
    name = target.name.removesuffix('-tmp')
    log = root / (name + '.log')
    assert 'U3B_EXIT=' in log.read_text(), 'run is still active'
    handles = subprocess.run(['/usr/sbin/lsof', '+D', str(target)], capture_output=True, text=True)
    assert handles.returncode in (0, 1), handles.stderr
    inbound = [path for path, resolved in links if resolved == target or target in resolved.parents]
    outside_links = [path for path in inbound if not Path(path).is_relative_to(target)]
    # pytest's *current symlinks are disposable basetemp aliases, not evidence.
    unexpected = [path for path in outside_links if not Path(path).name.endswith('current')]
    refs = subprocess.run(['rg', '-l', '-uu', '-F', str(target), str(root),
                           '-g', '!*-tmp/**'], capture_output=True, text=True)
    result.append({'target': str(target), 'run_finished': True,
        'du': subprocess.check_output(['du', '-sk', str(target)], text=True).strip(),
        'open_handles': handles.stdout, 'inbound_links': inbound,
        'unexpected_external_links': unexpected, 'recorded_references': refs.stdout.splitlines()})
    assert not handles.stdout and not unexpected, result[-1]
out = root / 'cleanup-inventory.json'
ordinal = 2
while out.exists():
    out = root / f'cleanup-inventory-{ordinal}.json'
    ordinal += 1
out.write_text(json.dumps(result, indent=2) + '\n')
print(out)
