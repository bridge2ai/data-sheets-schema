"""Write the Claude lead G2 CI-lane handoff, 2026-11-14.

Inputs: retained scratch lane mapping, collection JSON, pytest JUnit and logs.
Output: assigned Markdown handoff and scratch evidence-summary.json.
Run after all checks finish; no network or provider calls.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-ci-lanes-g2-heavy-20261114'
HANDOFF = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-ci-lanes-g2-heavy-20261114.md'
lanes = json.loads((SCRATCH / 'lane-map.json').read_text())


def result(name):
    path = SCRATCH / (name + '.xml')
    cases = list(ET.parse(path).iter('testcase'))
    assert cases
    failures = sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
    skipped = sum(c.find('skipped') is not None for c in cases)
    return dict(cases=len(cases), failures=failures, skipped=skipped,
                passed=len(cases) - failures - skipped,
                case_seconds=sum(float(c.attrib['time']) for c in cases),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


results = {name: result(name) for name in ('sharding', 'lane-binding', 'heavy-committed', 'discovery')}
assert all(row['failures'] == row['skipped'] == 0 for row in results.values()), results
collections = {}
for lane, node in lanes.items():
    path = SCRATCH / ('collection-' + lane + '.json')
    row = json.loads(path.read_text())
    assert row['verified'] and row['selected'] == [node] and row['exit_code'] == 1
    assert Path(row['log']).is_file()
    collections[lane] = row
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
measurement_commit = (SCRATCH / 'commit-head.txt').read_text().strip()
summary = dict(commit=commit, measurement_commit=measurement_commit, results=results, collections=collections)
(SCRATCH / 'evidence-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
lines = [f"Added {len(lanes)} lanes, native-capacity-34 through native-capacity-45. "
         f"Sharding tests: {results['sharding']['passed']} passed; "
         f"final independent inventory check: {results['discovery']['passed']} passed; "
         f"native/workflow lane binding: {results['lane-binding']['passed']} passed.", '']
lines += [f'- `{lane}` → `{node}`' for lane, node in lanes.items()]
lines += ['', f'Local branch: `codex/ci-lanes-g2-heavy-20261114`; HEAD `{commit}`. '
          'No push, pull request, GitHub write, provider call, or real native launch.', '',
          'Scope and review', '',
          '- All twelve cases build the complete make_case fixture: ten deadline cases and two publication-signal cases. '
          'The six requested files were inspected, including both launch-sequence siblings. '
          'Sequence/start cases use lightweight fake packets, mocked commands, or copied fake subprocesses; none builds the full fixture.',
          '- The lane map, workflow matrix, exact v2 CI roster, and sharding expectations agree. '
          'Only _COMMON_CHECKS changed in native_execution_registration_v2.py, for coordination with the manifest branch.',
          '- The final inventory check discovers make_case/synthetic_launch test functions from source and compares '
          'their actual parameterized collection with the new lanes. This replaced a duplicated expected map while '
          'the full sharding run was active; the final changed test was run separately and passed.',
          '- The aggregate test job and its needs are unchanged. No production deadline or existing assertion changed. '
          'Every new lane exercises the existing unqualified setup/call/teardown pass requirement in the sharding tests.',
          '- A separate read-only diff review found no implementation defect. Git diff whitespace validation passed. '
          'The offline assignment prohibits GitHub issue creation; the local validation incidents below are retained for the lead.', '',
          'Measurements and limits', '',
          '- The lead g2-run.log records 266 passed and four failures in 8168.98 seconds, but no per-test durations. '
          'An ignore-independent search of the G2 scratch tree found no JUnit XML for that run.',
          f"- One committed heavy case passed: native-capacity-41, JUnit setup/call/teardown total "
          f"{results['heavy-committed']['case_seconds']:.3f} seconds. The call-only measurement is in heavy-committed.log. "
          f'Measured commit: {measurement_commit}. '
          'This is one local macOS/Python 3.13 sample, not a Linux CI duration or proof of all heavy cases.',
          '- utils/ci_test_durations.json is unchanged. The existing updater requires a CI run identifier and constructs '
          'a GitHub Actions URL; it has no honest local-run provenance mode. Per the assignment fallback, no fabricated '
          'CI identity or local weight was inserted. Untimed light remainders retain the median fallback.',
          '- The initial timing attempt failed during fixture construction because the registration edit was not committed. '
          'Its 109.26-second call is not a completed launch measurement. After the required local commit, the same test passed. '
          'Both logs and XML files remain in scratch.',
          '- An unnecessarily broad native CI-evidence run was interrupted after 21 passes; its binding.log and binding.xml '
          'are retained. The requested focused binding checks completed separately.', '',
          'Collection verification', '',
          f'- All {len(collections)} real collections selected exactly their mapped node. Each exited 1 at the unchanged '
          'dedicated execution gate, which correctly refuses to treat collect-only as a passing execution.',
          '- The runner invokes the supplied interpreter with PYTHONPATH set to this worktree src, tests as the collection '
          'root, -p no:cacheprovider -p utils.pytest_shard --ci-lane, --collect-only, and a unique scratch basetemp. '
          'Only tests/test_fairscape_integration is ignored because the submodule is unavailable locally. '
          'Exact command arrays are retained in every collection JSON.',
          '- The first collection canary was verified before the remaining lanes ran through the same runner. '
          'This proves node selection and fail-closed collection behavior, not successful execution of the other eleven heavy cases.', '',
          'Evidence and reproduction', '', f'Worktree: `{ROOT}`', '', f'Scratch: `{SCRATCH}`', '',
          '- lane-map.json, inventory.log, heavy-source-inventory.txt, and g2-changed-files.txt record the inventory.',
          '- sharding.log and sharding.xml contain the full tests/test_ci_sharding.py run with two xdist workers.',
          '- lane-binding.log and lane-binding.xml contain the required-check event-matrix and workflow-lane checks.',
          '- discovery.log and discovery.xml contain the final independent inventory regression check.',
          '- heavy-measure.log and heavy-measure.xml retain the initial refusal; '
          'heavy-committed.log and heavy-committed.xml retain the completed measurement.',
          '- collection-native-capacity-34.json through collection-native-capacity-45.json retain exact commands and selections; '
          'matching logs retain pytest summaries.',
          '- evidence-summary.json contains test counts, JUnit hashes, the commit, and all collection commands.', '',
          'Committed helper scripts:', '',
          '- scripts/adhoc/wire_g2_heavy_ci_lanes_20261114.py: reproduce the scoped wiring from the baseline inventory.',
          '- scripts/adhoc/collect_g2_heavy_ci_lanes_20261114.py: --canary, verify, then --remaining.',
          '- scripts/adhoc/report_g2_heavy_ci_lanes_20261114.py: generate this handoff from retained evidence.', '',
          'All pytest basetemps and outputs are under the assigned scratch directory. No poetry invocation.']
text = '\n'.join(lines) + '\n'
assert chr(64) not in text
for name in ('lane-map.json', 'inventory.log', 'heavy-source-inventory.txt', 'g2-changed-files.txt',
             'binding.log', 'binding.xml', 'heavy-measure.log', 'heavy-measure.xml',
             'sharding.log', 'lane-binding.log', 'heavy-committed.log', 'discovery.log', 'evidence-summary.json'):
    assert (SCRATCH / name).is_file(), name
HANDOFF.write_text(text)
assert HANDOFF.stat().st_size
print(HANDOFF)
print(hashlib.sha256(HANDOFF.read_bytes()).hexdigest())
