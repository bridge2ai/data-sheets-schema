"""Install the audited case roster for the 2026-11-14 CI capacity assignment.

Input: audit_ci_capacity_20261114.py's JSON inventory. Outputs: lane constants,
workflow matrix and matching v2 evidence roster. No aggregate or pin changes.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('inventory', type=Path)
args = parser.parse_args()
lanes = json.loads(args.inventory.read_text())['proposed_lanes']


def replace(relative, old, new):
    path = ROOT / relative
    text = path.read_text()
    assert text.count(old) == 1, relative
    path.write_text(text.replace(old, new))


block = '# Run 43536007079: measured native cases over 120 s, plus the three\n'
block += '# public retention cases in cancelled shard 6 (no completed JUnit).\n'
block += 'NATIVE_CAPACITY_CASE_LANES = {\n'
block += ''.join(f'    {lane!r}: {node!r},\n' for lane, node in lanes.items())
block += '}\n'
block += 'NATIVE_CASE_LANES = {**NATIVE_PUBLIC_CASE_LANES, **NATIVE_FAILURE_CASE_LANES,\n'
block += '                     **NATIVE_CAPACITY_CASE_LANES}'
replace('utils/pytest_shard.py',
        'NATIVE_CASE_LANES = {**NATIVE_PUBLIC_CASE_LANES, **NATIVE_FAILURE_CASE_LANES}', block)
replace('utils/pytest_shard.py', 'isolates twenty-seven slow offline API, SG2 and native',
        'isolates sixty-three slow offline API, SG2 and native')
replace('.github/workflows/main.yaml', 'native-failure-16, native-failure-17]',
        'native-failure-16, native-failure-17, ' + ', '.join(lanes) + ']')
replace('src/data_sheets_schema/native_execution_registration_v2.py',
        "        'native-failure-16', 'native-failure-17',)) + (",
        "        'native-failure-16', 'native-failure-17',\n" +
        ''.join(f'        {name!r},\n' for name in lanes) + '    )) + (')
print(json.dumps({'new_lanes': len(lanes), 'aggregate_dependency_list_changed': False}))
