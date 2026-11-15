"""Issue 6214, 2026-11-15: adapt handoff writer to saved bounded cohort totals."""
from pathlib import Path
p = Path('scripts/adhoc/write_teardown_handoff_20261115.py')
s = p.read_text()
s = s.replace('lines = [', '''counts = summary['totals']
validation = (str(counts.get('call:passed', 0)) + ' passed calls, '
    + str(counts.get('call:failed', 0)) + ' failed calls, '
    + str(counts.get('setup:failed', 0)) + ' setup errors; '
    + str(sum(summary['remaining_by_file'].values())) + ' cases without a completed report.')
lines = [''', 1)
lines = s.splitlines()
for index, line in enumerate(lines):
    if line.startswith("'Focused validation:"):
        lines[index] = "'Focused validation: five tests passed; both real source-loader witnesses passed their in-process lifetime assertions. Combined required-suite recorded outcomes: ' + validation,"
    if line.startswith("'Final required-suite outcomes by file"):
        lines[index] = """'The final full cohort reached its 1,800-second outer bound. Only unfinished node IDs were selected for a separate 900-second continuation. This is combined coverage from bounded runs, not an uninterrupted green suite. Continuation evidence: ' + link(scratch / 'remaining-plan.json') + ', ' + link(scratch / 'remaining-required.json') + ', ' + link(scratch / 'remaining-required.reports.jsonl') + ', ' + link(scratch / 'remaining-required.log') + '.',
'',
'Combined required-suite outcomes by file, generated from saved per-test records:',"""
s = '\n'.join(lines) + '\n'
s = s.replace('Implemented the lead’s bounded-wait', 'Implemented locally, uncommitted because the sandbox refused the index lock: the lead’s bounded-wait')
p.write_text(s)
