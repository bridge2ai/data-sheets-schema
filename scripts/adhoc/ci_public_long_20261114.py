# Purpose: implement and report the lead's offline CI split assignment.
# Inputs: workflow, runtime and roster sources; outputs: edited files or evidence.
# Serves CI public-long assignment, related issue 6191; date: 2026-11-14.
from pathlib import Path
import sys
import hashlib

ROOT = Path(__file__).resolve().parents[2]
LONG = ('native-public-correction', 'native-public-variant', 'native-public-pending')

def replace(path, old, new):
    p = ROOT / path
    text = p.read_text()
    assert text.count(old) == 1, (path, old)
    p.write_text(text.replace(old, new))

if sys.argv[1] == 'edit':
    path = ROOT / '.github/workflows/main.yaml'
    text = path.read_text()
    start = text.index('  native-public-completion:')
    end = text.index('  # Run these controls once', start)
    block = text[start:end]
    comment = ('    # A cap, not a duration: the public cases hold a 2,700 s synthetic attempt\n'
               '    # after about 21 minutes of setup (#6094, #6233).\n')
    short = block.replace(comment, '').replace('timeout-minutes: 90', 'timeout-minutes: 45')
    short = short.replace(', '.join(LONG) + ', ', '')
    long = block.replace('native-public-completion:', 'native-public-long:\n    if: github.event_name != \'pull_request\'')
    long = long.replace(comment, '    # Complete synthetic runs have a two-hour attempt budget plus setup.\n')
    long = long.replace('timeout-minutes: 90', 'timeout-minutes: 180')
    axis_start = long.index('        case: [')
    axis_end = long.index('\n', axis_start)
    long = long[:axis_start] + '        case: [' + ', '.join(LONG) + ']' + long[axis_end:]
    path.write_text(text[:start] + short + long + text[end:])
    replace('src/data_sheets_schema/native_runtime_profiles.py', 'SYNTHETIC_DEADLINE_SECONDS = 2700', 'SYNTHETIC_DEADLINE_SECONDS = 7200')
    replace('tests/test_native_synthetic_profiles.py', ' == profiles.SYNTHETIC_DEADLINE_SECONDS == 2700', ' == profiles.SYNTHETIC_DEADLINE_SECONDS')
    replace('src/data_sheets_schema/native_execution_registration_v2.py',
        "        'native-public-correction', 'native-public-variant', 'native-public-pending',\n", '')
    replace('src/data_sheets_schema/native_execution_registration_v2.py',
        "EXECUTION_GATES =", "_LONG_CHECKS = tuple('Python 3.12 / native case ' + name for name in (\n    'native-public-correction', 'native-public-variant', 'native-public-pending'))\nEXECUTION_GATES =")
    replace('src/data_sheets_schema/native_execution_registration_v2.py',
        "+ _COMMON_CHECKS + (('large-files',) if pull else ('schema-examples (3.12)',)))",
        "+ _COMMON_CHECKS + (('large-files',) if pull else\n                _LONG_CHECKS + ('schema-examples (3.12)',)))")
    replace('tests/test_ci_sharding.py', 'ROOT = Path(__file__).resolve().parents[1]',
        'ROOT = Path(__file__).resolve().parents[1]\nLONG_NATIVE_LANES = ' + repr(LONG) + '\nSHORT_NATIVE_LANES = tuple(lane for lane in NATIVE_CASE_LANES if lane not in LONG_NATIVE_LANES)')
    replace('tests/test_ci_sharding.py',
        '    # The native public cases hold a 2,700 s synthetic attempt after about\n    # 21 minutes of setup (#6094, #6233); other native lanes finish early.\n    ("native-public-completion", NATIVE_CASE_LANES, "native", 90),',
        '    ("native-public-completion", SHORT_NATIVE_LANES, "native", 45),\n    ("native-public-long", LONG_NATIVE_LANES, "native", 180),')
    replace('tests/test_ci_sharding.py', '    assert "if" not in job and "needs" not in job',
        '    assert "needs" not in job\n    if job_name == "native-public-long":\n        assert job["if"] == "github.event_name != \'pull_request\'"\n    else:\n        assert "if" not in job\n    assert job["name"] == "Python 3.12 / " + artifact + " case ${{ matrix.case }}"')
    with (ROOT / 'tests/test_ci_sharding.py').open('a') as output:
        output.write('''\n\ndef test_long_native_cases_are_required_only_for_main_and_manual_ci():
    from data_sheets_schema.native_execution_registration_v2 import required_checks
    workflow = yaml.load((ROOT / ".github/workflows/main.yaml").read_text(), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"push", "pull_request", "workflow_dispatch"}
    assert workflow["on"]["push"]["branches"] == ["main"]
    long_checks = {"Python 3.12 / native case " + lane for lane in LONG_NATIVE_LANES}
    assert not long_checks.intersection(required_checks("pull_request"))
    for event in ("push", "workflow_dispatch"):
        assert long_checks.issubset(required_checks(event))
    assert set(SHORT_NATIVE_LANES).isdisjoint(LONG_NATIVE_LANES)
    assert set(SHORT_NATIVE_LANES) | set(LONG_NATIVE_LANES) == set(NATIVE_CASE_LANES)
''')
elif sys.argv[1] == 'report':
    import yaml
    from data_sheets_schema.native_execution_registration_v2 import required_checks
    from data_sheets_schema.native_runtime_profiles import SYNTHETIC_DEADLINE_SECONDS
    workflow = yaml.load((ROOT / '.github/workflows/main.yaml').read_text(), Loader=yaml.BaseLoader)
    print('Workflow YAML parsed; long timeout:', workflow['jobs']['native-public-long']['timeout-minutes'])
    print('Synthetic deadline:', SYNTHETIC_DEADLINE_SECONDS)
    for event in ('pull_request', 'push', 'workflow_dispatch'):
        roster = required_checks(event)
        print(event, 'total checks:', len(roster))
        print('Public checks:', [name for name in roster if '/ native case native-public-' in name])
        print('Full roster:', roster)
    path = ROOT / 'src/data_sheets_schema/native_runtime_profiles.py'
    print('Runtime profile SHA-256:', hashlib.sha256(path.read_bytes()).hexdigest())
elif sys.argv[1] == 'finish':
    replace('tests/test_ci_sharding.py',
        'assert job["name"] == "Python 3.12 / " + artifact + " case ${{ matrix.case }}"',
        'assert job["name"] == "Python 3.12 / " + (artifact.upper() if artifact != "native" else artifact) + " case ${{ matrix.case }}"')
    replace('.github/workflows/main.yaml',
        '# Every PR runs the complete suite, including the committed corpus (#1361).',
        '# PRs include the committed corpus; long native completion runs on main/manual.')
elif sys.argv[1] == 'summarize':
    import xml.etree.ElementTree as ET
    from collections import Counter
    scratch = Path(sys.argv[2])
    for filename in ('results.xml', 'final-workflow.xml'):
        root = ET.parse(scratch / filename).getroot()
        counts = {}
        for case in root.iter('testcase'):
            status = 'failed' if case.find('failure') is not None else ('error' if case.find('error') is not None else ('skipped' if case.find('skipped') is not None else 'passed'))
            counts.setdefault(case.attrib['classname'], Counter())[status] += 1
            failure = case.find('failure')
            if failure is not None:
                print(filename, 'failure:', case.attrib['name'], failure.attrib.get('message'))
        for name, result in counts.items():
            print(filename, name, dict(result))
    handoff = Path(sys.argv[3])
    assert chr(64) not in handoff.read_text()
    assert handoff.stat().st_size > 0
    print('Handoff SHA-256:', hashlib.sha256(handoff.read_bytes()).hexdigest())
