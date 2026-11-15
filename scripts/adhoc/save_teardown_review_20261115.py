"""Issue 6214, 2026-11-15: save read-only review findings and sanitized diff."""
import json
from pathlib import Path
import subprocess
scratch = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-callback-teardown-20261115')
diff = subprocess.check_output(['git', 'diff', '--', 'src/data_sheets_schema/native_shared_callback_orchestration.py', 'tests/test_native_shared_callback_preloading.py'], text=True)
(scratch / 'review.diff').write_text(diff.replace(chr(64), '[at]'))
findings = [
    dict(id='R1', finding='A reused poisoned stack scope can enter its body before teardown refuses.', disposition='Fix by checking poison before yielding the stack.'),
    dict(id='R2', finding='Module-local retention alone need not survive removal of dynamically loaded module bindings.', disposition='Root retained stacks in sys for process lifetime.'),
    dict(id='R3', finding='CallbackAdapter.report acquires the worker lock without a bound before scope teardown.', disposition='Report to lead: out of the assigned locked-stack change; no global shutdown bound claimed.'),
    dict(id='R4', finding='Read denial case asserts full successful completion and replay in ordinary CI shards.', disposition='Recommend split focused denial coverage and dedicated full completion coverage; no change.')]
(scratch / 'review-findings.json').write_text(json.dumps(findings, indent=2) + '\n')
