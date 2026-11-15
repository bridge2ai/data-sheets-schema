"""Issue 6214, 2026-11-15: save review findings and validate changed-file scope."""
import json
from pathlib import Path
import subprocess

scratch = Path('../scratch-callback-teardown-20261115')
changed = subprocess.check_output(['git', 'diff', '--name-only'], text=True).splitlines()
assert changed == ['src/data_sheets_schema/native_shared_controller_orchestration.py'], changed
new_files = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
for name in new_files:
    assert name.startswith(('scripts/adhoc/', 'tests/test_native_shared_callback_report_bound.py')), name
    assert chr(64) not in Path(name).read_text(), name
result = dict(source_changes=changed, new_files=new_files, findings=[
    dict(finding='A stuck non-daemon worker still prevents interpreter exit.', disposition='Report only; worker termination is outside the accepted lock-bound design.'),
    dict(finding='Retained generator scopes emit ignored errors during interpreter finalization.', disposition='Existing retention-design limit; retained in focused logs, no late cleanup added.'),
    dict(finding='Uncommitted source prevents reviewed-head integration checks.', disposition='Add and commit were attempted and refused; lead must commit and rerun affected integration tests.')],
    review='Read-only final-source and test review completed before recording this ledger; no additional in-scope defect found.')
(scratch / 'report-review.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
