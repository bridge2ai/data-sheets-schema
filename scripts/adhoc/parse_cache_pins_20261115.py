"""Search all worktree files, including ignored files, for changed-file pins.

Inputs: git base and output directory. Outputs: hashes and complete grep logs.
Lead parse-cache assignment, 2026-11-15. No pin or scanner is edited.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

base, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
changed = subprocess.check_output(['git', 'diff', '--name-only', base], text=True).splitlines()
changed += subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
if len(sys.argv) > 3:
    changed.append(sys.argv[3])
rows = []
all_patterns = set()
for index, name in enumerate(sorted(set(changed))):
    path = Path(name)
    if not path.is_file():
        continue
    if len(sys.argv) > 3 and name == sys.argv[3]:
        old = hashlib.sha256(Path(sys.argv[4]).read_bytes()).hexdigest()
        new = None  # The external handoff's final digest is printed by its verifier.
    else:
        prior = subprocess.run(['git', 'show', base + ':' + name], capture_output=True)
        old = hashlib.sha256(prior.stdout).hexdigest() if prior.returncode == 0 else None
        new = hashlib.sha256(path.read_bytes()).hexdigest()
    patterns = [name, path.name] + ([old] if old else [])
    all_patterns.update(patterns)
    rows.append(dict(path=name, old_sha256=old, new_sha256=new,
                     patterns=patterns))
command = ['grep', '-r', '-n', '-F']
for pattern in sorted(all_patterns):
    command.extend(['-e', pattern])
command.append('.')
log = out / 'all-references.txt'
with log.open('w') as stream:
    result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=900)
for row in rows:
    row.update(search_command=command, search_exit=result.returncode, references=str(log))
(out / 'hashes.json').write_text(json.dumps(rows, indent=2))
print(json.dumps(rows, indent=2))
