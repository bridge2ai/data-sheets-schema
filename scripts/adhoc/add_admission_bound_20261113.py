#!/usr/bin/env python3
"""Apply reviewed-source admission edits, 2026-11-13.
Inputs: this worktree's controller/deadline tests. Outputs: exact replacements
for the helper-2 pins/admission assignment. No pin changes or execution.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
p = root / 'notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py'
text = p.read_text()
text = text.replace('from data_sheets_schema.native_attempt_timing import Timing',
    'from data_sheets_schema.native_attempt_timing import Timing\n'
    'from data_sheets_schema.native_admission_timer import AdmissionTimer, AdmissionRefused, ADMISSION_SECONDS')
old = "    timing = Timing(attempt)\n    timing.record('execute_child_entry')\n    process = None"
assert text.count(old) == 1
text = text.replace(old, '    timing = None\n    admission = None\n    process = None')
old = '    try:\n        with ExitStack() as stack:\n            incoming ='
new = ('    try:\n        entry_ns = elapsed_ns()\n'
       '        admission = AdmissionTimer(entry_ns, seconds=ADMISSION_SECONDS, clock=elapsed_ns)\n'
       '        with ExitStack() as stack:\n'
       '            with admission.armed():\n'
       '                timing = Timing(attempt)\n'
       "                timing.record('execute_child_entry', entry_elapsed_ns=entry_ns,\n"
       '                              admission_deadline_elapsed_ns=admission.deadline_ns)\n'
       '                incoming =')
assert text.count(old) == 1
text = text.replace(old, new)
start = text.index("            out = stack.enter_context((attempt/'transcript.jsonl')")
end = text.index('            # Dispatch origin includes', start)
text = text[:start] + ''.join('    ' + line if line.strip() else line
    for line in text[start:end].splitlines(True)) + text[end:]
text = text.replace('            dispatch_ns = elapsed_ns()\n',
    '            dispatch_ns = elapsed_ns()\n            admission.check(dispatch_ns)\n', 1)
text = text.replace("            timing.record('child_dispatch',", "            timing.record('admission_end', status='admitted',\n"
    "                          duration_ns=dispatch_ns-entry_ns, end_elapsed_ns=dispatch_ns)\n"
    "            timing.record('child_dispatch',", 1)
text = text.replace('isinstance(exc, BudgetStop) else', 'isinstance(exc, (BudgetStop, AdmissionRefused)) else', 1)
old = "        timing.record('execute_child_cleanup_entry')\n        timing.close()"
assert text.count(old) == 1
text = text.replace(old, "        if timing is not None:\n"
    "            if process is None:\n"
    "                timing.record('admission_end', status='refused',\n"
    "                              reason_type=type(primary_error).__name__)\n"
    "            timing.record('execute_child_cleanup_entry')\n"
    "            timing.close()")
p.write_text(text)
p = root / 'tests/test_native_attempt_deadline.py'
text = p.read_text().replace("2 * seconds * 10**9  # Slow admission must not consume child time.",
    "899 * 10**9  # Within admission's own bound; excluded from child time.")
text = text.replace("ticks['continuous'] += 10**15", "ticks['continuous'] += 899 * 10**9")
p.write_text(text)
