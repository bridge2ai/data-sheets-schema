"""Add native failure CI lanes for PR 5968, 2026-11-13.

Inputs: helper-1's exact-node proposal and existing source files.
Outputs: lane constants, CI matrix/roster, fixture tests and documentation.
Run once on the assigned candidate worktree; guarded replacements refuse drift.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-h1-shard4-layout-v2-20261113.md'
lanes = dict(re.findall(r'\| `(native-failure-\d+)` \| `([^`]+)` \|', PROPOSAL.read_text()))
assert list(lanes) == [f'native-failure-{i:02}' for i in range(1, 18)]


def replace(path, old, new):
    target = ROOT / path
    text = target.read_text()
    assert text.count(old) == 1, (path, old)
    target.write_text(text.replace(old, new))


replace('utils/pytest_shard.py',
        'isolates ten slow offline API, SG2 and native public-path\ncases',
        'isolates twenty-seven slow offline API, SG2 and native\ncases')
entries = '\n'.join(f'    {lane!r}: {node!r},' for lane, node in lanes.items())
replace('utils/pytest_shard.py',
        'DEDICATED_CASE_LANES = {**API_CASE_LANES, **SG2_CASE_LANES, **NATIVE_PUBLIC_CASE_LANES}',
        '# Failure cases share the expensive native fixture and each need their own lane.\n'
        + 'NATIVE_FAILURE_CASE_LANES = {\n' + entries + '\n}\n'
        + 'NATIVE_CASE_LANES = {**NATIVE_PUBLIC_CASE_LANES, **NATIVE_FAILURE_CASE_LANES}\n'
        + 'DEDICATED_CASE_LANES = {**API_CASE_LANES, **SG2_CASE_LANES, **NATIVE_CASE_LANES}')
replace('.github/workflows/main.yaml', 'name: Python 3.12 / native public case ${{ matrix.case }}',
        'name: Python 3.12 / native case ${{ matrix.case }}')
replace('.github/workflows/main.yaml',
        'case: [native-public-correction, native-public-variant, native-public-pending]',
        'case: [native-public-correction, native-public-variant, native-public-pending, '
        + ', '.join(lanes) + ']')
replace('src/data_sheets_schema/native_execution_registration_v2.py',
        "'Python 3.12 / native public case ' + name for name in (\n"
        "        'native-public-correction', 'native-public-variant', 'native-public-pending'))",
        "'Python 3.12 / native case ' + name for name in (\n"
        "        'native-public-correction', 'native-public-variant', 'native-public-pending',\n"
        + '\n'.join('        ' + ', '.join(repr(lane) for lane in list(lanes)[i:i+3]) + ','
                    for i in range(0, len(lanes), 3)) + '))')
replace('tests/test_ci_sharding.py',
        'SG2_CASE_LANES, NATIVE_PUBLIC_CASE_LANES, DEDICATED_CASE_LANES,',
        'SG2_CASE_LANES, NATIVE_PUBLIC_CASE_LANES, NATIVE_FAILURE_CASE_LANES, NATIVE_CASE_LANES, DEDICATED_CASE_LANES,')
replace('tests/test_ci_sharding.py', '(188 if lanes else 172)', '(205 if lanes else 172)')
replace('tests/test_ci_sharding.py', '    return path\n', '''    # Preserve exact real parameter IDs, including spaces and dots. Group by
    # function so parameterized nodes are collected once rather than overwritten.
    groups = {}
    for lane, node in NATIVE_FAILURE_CASE_LANES.items():
        relative, case = node.split("::")
        name, bracket, parameter = case.partition("[")
        groups.setdefault((relative, name), []).append((lane, parameter[:-1] if bracket else None))
    text = "import pytest\\n" + (fixture if target in NATIVE_FAILURE_CASE_LANES else "")
    for (_, name), cases in groups.items():
        own = any(lane == target for lane, _ in cases)
        if cases[0][1] is not None:
            ids = [parameter for _, parameter in cases]
            text += f"@pytest.mark.parametrize('case_id', {ids!r}, ids={ids!r})\\n"
            args = "case_id"
        else:
            args = ""
        text += (decorator if own else "") + f"def {name}({args}):\\n    "
        text += (body if own else "assert True") + "\\n"
    (root / "tests/test_native_shared_execution_failure.py").write_text(text)
    return path
''')
replace('tests/test_ci_sharding.py',
        '["routing-dispatch", *SG2_CASE_LANES, "native-public-correction"]',
        '["routing-dispatch", *SG2_CASE_LANES, "native-public-correction", "native-failure-16"]')
replace('tests/test_ci_sharding.py',
        '("native-public-completion", NATIVE_PUBLIC_CASE_LANES, "native")',
        '("native-public-completion", NATIVE_CASE_LANES, "native")')
replace('utils/ci_sharding.md', '## Required long API cases', '## Required long API, SG2 and native cases')
replace('utils/ci_sharding.md',
        'ten dedicated lanes for long offline API, SG2 and native public-path cases.',
        'twenty-seven dedicated lanes for long offline API, SG2 and native cases.')
replace('utils/ci_sharding.md',
        '`NATIVE_PUBLIC_CASE_LANES`.\n`partition_lanes` requires all ten exact nodes',
        '`NATIVE_CASE_LANES` (three public-path and seventeen failure cases).\n'
        '`partition_lanes` requires all twenty-seven exact nodes')
replace('utils/ci_sharding.md',
        'The aggregate requires the entire API, SG2 and native public-path matrices to succeed on PR, main and\n'
        'manual events, as well as the existing jobs. PRs have twenty-five required successes\n'
        'plus the expected schema/example skip; main/manual have twenty-two (twenty-one\n'
        'Python jobs and the schema/example build). Across PR, manual and the separate\n'
        'large-files check this is forty-eight required successes and one expected skip,\n'
        'without counting unrelated automation.',
        'The aggregate requires the entire API, SG2 and native matrices to succeed on PR, main and\n'
        'manual events, as well as the existing jobs. PRs have 25 + 17 = 42 Python jobs\n'
        '(12 ordinary + 4 API + 3 SG2 + 20 native + 3 offline), plus the expected\n'
        'schema/example skip. Main/manual have 21 + 17 = 38 Python jobs\n'
        '(8 ordinary + 4 API + 3 SG2 + 20 native + 3 offline), plus the schema/example build.\n'
        'Across PR, manual and the separate large-files check this is 42 + 38 + 1 + 1\n'
        '= 82 required job successes and one expected skip, excluding aggregate checks\n'
        'and unrelated automation.')
replace('utils/ci_sharding.md', '## Native public-path cases (#6191, 2026-11-13)',
        '## Native cases (#6191, 2026-11-13)\n\n'
        '`NATIVE_FAILURE_CASE_LANES` isolates all seventeen cases in\n'
        '`tests/test_native_shared_execution_failure.py` as `native-failure-01` through\n'
        '`native-failure-17`. Each builds the expensive native fixture.\n'
        '`NATIVE_CASE_LANES` combines these with the three public-path cases, in that\n'
        'order, in the existing `native-public-completion` matrix. Display names are\n'
        '`Python 3.12 / native case <lane>` and match the v2 launch-evidence roster.\n'
        'The aggregate dependency list and its exhaustive truth-table size are unchanged.\n'
        'The failure file has no ordinary cases; its retained historical weight is ignored\n'
        'by ordinary partitioning. Isolation does not fix failures within those tests.')
print('Updated five assigned files; added 17 exact native failure lanes.')
