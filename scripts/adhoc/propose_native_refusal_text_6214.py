"""Produce an UNAPPLIED model-text proposal for PR 5968 issue 6214, 2026-11-14.

Inputs: the two native shared classifier sources. Output: review-only patch
under notes/pr5968_g3. Does not modify either source or rotate any pin.
The owner must decide the refusal policy before this proposal can be applied.
"""
from difflib import unified_diff
from pathlib import Path

root = Path(__file__).resolve().parents[2]
output = root / 'notes/pr5968_g3/6214-review-only.patch'
patch = []
for relative in ('src/data_sheets_schema/native_shared_controls.py',
                 'src/data_sheets_schema/native_shared_results_orchestration.py'):
    original = (root / relative).read_text()
    old = 'This refusal does not disqualify the attempt; quote each '
    new = 'This refusal disqualifies the attempt; in a new attempt, quote each '
    assert original.count(old) == 1
    proposed = original.replace(old, new)
    patch.extend(unified_diff(original.splitlines(keepends=True), proposed.splitlines(keepends=True),
                              fromfile='a/' + relative, tofile='b/' + relative, n=0))
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(''.join(patch))
assert output.stat().st_size
print(output)
