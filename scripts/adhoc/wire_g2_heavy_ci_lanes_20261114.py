"""Wire G2 full-fixture cases into CI lanes, 2026-11-14.

Input: saved pytest inventory in assignment scratch. Outputs: four scoped
source edits and lane-map.json for the Claude lead shard-overflow handoff.
Run once on the assigned baseline; no provider or network calls.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-ci-lanes-g2-heavy-20261114'
names = (
    'test_unplug_before_reservation_keeps_attempt_unspent',
    'test_unplug_after_reservation_retains_reading_without_consuming_dispatch',
    'test_slow_power_probe_cannot_age_an_already_checked_reservation_margin',
    'test_dispatch_guard_refusal_precedes_stage_activation',
    'test_public_first_signal_during_publication_keeps_exact_readback',
)
nodes = [line for line in (SCRATCH / 'inventory.log').read_text().splitlines()
         if line.startswith('tests/') and '::' in line
         and line.split('::')[1].split('[')[0] in names]
assert len(nodes) == len(set(nodes)) == 12
lanes = {f'native-capacity-{number}': node for number, node in enumerate(nodes, 34)}
(SCRATCH / 'lane-map.json').write_text(json.dumps(lanes, indent=2) + '\n')
path = ROOT / 'utils/pytest_shard.py'
text = path.read_text()
anchor = "    'native-retention-stable':"
assert text.count(anchor) == 1 and 'native-capacity-34' not in text
text = text.replace(anchor, '    # G2 full-fixture deadline and publication cases overflowed shard 9.\n'
                    + ''.join(f'    {lane!r}: {node!r},\n' for lane, node in lanes.items()) + anchor)
text = text.replace('isolates sixty-three slow', 'isolates seventy-five slow')
path.write_text(text)
path = ROOT / '.github/workflows/main.yaml'
text = path.read_text()
assert text.count('native-capacity-33, ') == 1
path.write_text(text.replace('native-capacity-33, ', 'native-capacity-33, ' + ', '.join(lanes) + ', '))
path = ROOT / 'src/data_sheets_schema/native_execution_registration_v2.py'
text = path.read_text()
anchor = "        'native-capacity-33',\n"
assert text.count(anchor) == 1
path.write_text(text.replace(anchor, anchor + ''.join(f'        {lane!r},\n' for lane in lanes)))
path = ROOT / 'tests/test_ci_sharding.py'
text = path.read_text()
text = text.replace('"native-capacity-05", "native-retention-changing"]',
                    '"native-capacity-05", "native-retention-changing",\n'
                    '                                  *[f"native-capacity-{n}" for n in range(34, 46)]]')
text += '''

def test_g2_full_fixture_cases_have_exact_dedicated_lanes(tmp_path):
    import ast

    paths = sorted({*ROOT.glob("tests/test_native_launch_sequence*.py"),
                    ROOT / "tests/test_native_attempt_deadline.py",
                    ROOT / "tests/test_native_publication_signals.py",
                    ROOT / "tests/test_native_sequence_start.py"})
    heavy_functions = set()
    for path in paths:
        for function in ast.parse(path.read_text()).body:
            if not isinstance(function, ast.FunctionDef) or not function.name.startswith("test_"):
                continue
            calls = [node.func for node in ast.walk(function) if isinstance(node, ast.Call)]
            if any((isinstance(call, ast.Name) and call.id == "make_case")
                   or (isinstance(call, ast.Attribute) and call.attr == "synthetic_launch")
                   for call in calls):
                heavy_functions.add(str(path.relative_to(ROOT)) + "::" + function.name)
    result = _run(ROOT, *(str(path.relative_to(ROOT)) for path in paths),
                  "--collect-only", f"--basetemp={tmp_path / 'collection'}")
    assert result.returncode == 0, result.stdout + result.stderr
    collected = [line for line in result.stdout.splitlines()
                 if line.startswith("tests/") and "::" in line]
    expected = [node for node in collected if node.split("[", 1)[0] in heavy_functions]
    actual = [NATIVE_CASE_LANES[f"native-capacity-{n}"] for n in range(34, 46)]
    assert expected and set(expected) == set(actual)
    assert len(expected) == len(actual)
    split = partition_lanes([*DEDICATED_CASE_LANES.values(),
                             *(node for node in collected if node not in actual)])
    assert not set(expected).intersection(split["ordinary"])
'''
path.write_text(text)
print(json.dumps(lanes, indent=2))
