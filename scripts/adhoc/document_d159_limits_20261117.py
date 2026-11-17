"""D159 evidence and external runbook update, 2026-11-17.

Inputs: checkout and sibling plans/runbook. Outputs: ignore-independent inventory,
changed-line JSON, runbook backup and updated runbook. No pins are written.
"""
import json
import difflib
from pathlib import Path
import re
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
base = 'bc61c2b5ccf894a50a386044acf50ac5ee34cb54'
scratch = root.parent / 'scratch-d159-limits-20261117/evidence'
scratch.mkdir(exist_ok=True)
def clean(text):
    return text.replace(chr(64), '[at]')
runbook = root.parent / 'plans/native_post_merge_runbook_DRAFT_20261114.md'
backup = runbook.with_name(runbook.name + '.bak-d159-20261117')
if not backup.exists():
    shutil.copy2(runbook, backup)
text = backup.read_text()
text = text.replace('21600', '28800').replace('21,600', '28,800')
text = text.replace('43200', '57600').replace('43,200', '57,600')
text = text.replace('360.0` min / `6.0` hours', '480.0` min / `8.0` hours')
text = text.replace('28,800` s [`6.0` hour]', '28,800` s [`8.0` hour]')
text = text.replace('1200', '1800').replace('ADMISSION_SECONDS = 900', 'ADMISSION_SECONDS = 1500')
text = text.replace('<= 900', '<= 1500').replace('> 900', '> 1500')
text = text.replace('<= 15.0', '<= 25.0')
text = text.replace('pre-dispatch freshness (`> 1500` s)', 'capture-to-reservation freshness (`> 1500` s) or capture-to-dispatch freshness (`> 1800` s)')
text += '''

## D159 limit amendment, 2026-11-17

The owner-approved increases apply before Gate 4: observer 240 s, callback
response 250 s, callback teardown 4 s, fresh prepared verification 600 s,
Bash default and maximum 1000000 ms, admission 1500 s, usage max age 1800 s,
synthetic attempt 9600 s, CHORUS 28800 s and production including AI_READI
57600 s. Production uses one shared registered pair, so all production cells
receive the same deadline increase. The reservation margin stays 300 s;
the derived latest reservation age is 1800 - 300 = 1500 s.

CI ordinary PR/push shards allow 60/80 min; native-public-long allows 240 min.
The other native execution CI jobs, native-public-completion and offline-canary,
increase from 45 to 60 min under the ruling's over-30-minute scale.
Its 160-minute attempt plus 20-25 minutes setup fits inside that budget.
Other non-protected native work-time waits and polls below five minutes double;
the shared upstream read default rises from 1800 to 2700 s. Freshness windows,
minimum margins and security/refusal bounds remain unchanged except the explicit
usage max-age amendment. The protected LinkML timeout remains 180 s per the lead.
Earlier measured timings and explicit offline qualification gates are evidence,
not new measurements. The delegated-start and host-confirmation age windows
remain 1800 s. Restore the adjacent .bak-d159-20261117 file to undo this update.
'''
if '--inventory-only' not in sys.argv:
    runbook.write_text(text)
result = subprocess.run(['grep', '-rnE', 'timeout|TIMEOUT|deadline|DEADLINE|[Ss][Ee][Cc][Oo][Nn][Dd][Ss]|1200|7200|21600|43200|600000',
    'src', 'notes/matched_cborg_2026-09-13/native_controls', 'tests', 'scripts', 'utils', '.claude', '.github/workflows/main.yaml', str(runbook)],
    cwd=root, capture_output=True, text=True)
(scratch / 'complete-limit-inventory.txt').write_text(clean(result.stdout))
rows = []
for name in subprocess.check_output(['git', 'diff', '--name-only', base], cwd=root, text=True).splitlines():
    if name.startswith(('scripts/adhoc/', 'notes/d159_limits_20261117/')):
        continue
    old = subprocess.check_output(['git', 'show', base+':'+name], cwd=root, text=True)
    new = (root / name).read_text()
    rows.append({'path': name, 'diff': clean(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True))))})
(scratch / 'final-changes.json').write_text(json.dumps(rows, indent=2)+'\n')
(scratch / 'runbook-diff.txt').write_text(clean(''.join(difflib.unified_diff(
    backup.read_text().splitlines(True), runbook.read_text().splitlines(True),
    fromfile=str(backup), tofile=str(runbook)))))
# Sanitize earlier discovery output too; the lead requested no notification glyphs.
for name in ['limit-inventory.txt', 'value-locations.txt']:
    path = scratch / name
    if path.exists():
        path.write_text(clean(path.read_text()))
print(json.dumps({'changed_files': len(rows), 'inventory_bytes': (scratch/'complete-limit-inventory.txt').stat().st_size,
                  'runbook': str(runbook), 'backup': str(backup)}, indent=2))
