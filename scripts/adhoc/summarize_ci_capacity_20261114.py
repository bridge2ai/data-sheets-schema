"""Produce the CI-capacity handoff evidence summary, 2026-11-14.

Inputs: task scratch JUnit/lane JSON, current checkout, assigned base commit.
Outputs: evidence-summary.json and generated verification table in scratch.
Serves the Claude lead assignment and CL196-F2 / #6230; no external actions.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utils.pytest_shard import NATIVE_CAPACITY_CASE_LANES, NATIVE_CASE_LANES, DEDICATED_CASE_LANES

BASE = '6ed891e845c1a46282338794dadb342a6fa6f261'
PROTECTED = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scratch', type=Path)
    parser.add_argument('--handoff', type=Path)
    args = parser.parse_args()
    report = {'base': BASE, 'head': git('rev-parse', 'HEAD'), 'status': git('status', '--porcelain'),
              'commits': git('log', '--reverse', '--format=%H %s', BASE + '..HEAD').splitlines()}
    report['acceptance_head'] = (args.scratch / 'acceptance-head.txt').read_text().strip()
    assert not git('diff', report['acceptance_head'], '--', 'src/', 'tests/', 'utils/', '.github/')
    report['acceptance_inputs_unchanged'] = True
    runs = {}
    rows = ['| Saved run | Passed | Failed | Errors | Skipped | JUnit seconds |',
            '| --- | ---: | ---: | ---: | ---: | ---: |']
    names = ['isolation-before', 'isolation-after', 'module-isolation-before', 'module-isolation-after',
             'layout-canary', 'timing-tests', 'acceptance']
    for name in names:
        path = args.scratch / (name + '.xml')
        log = args.scratch / (name + '.log')
        assert path.stat().st_size and log.stat().st_size
        raw = path.read_bytes()
        tree = ET.fromstring(raw)
        cases = list(tree.iter('testcase'))
        counts, files = Counter(), {}
        for case in cases:
            outcome = next((tag for tag in ('failure', 'error', 'skipped') if case.find(tag) is not None), 'passed')
            counts[outcome] += 1
            files.setdefault(case.attrib['classname'], Counter())[outcome] += 1
        elapsed = sum(float(s.attrib['time']) for s in tree.iter('testsuite'))
        runs[name] = {'counts': dict(counts), 'cases': len(cases), 'seconds': elapsed, 'files': files,
            'xml': str(path), 'xml_sha256': hashlib.sha256(raw).hexdigest(),
            'log': str(log), 'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()}
        rows.append(f"| {name} | {counts['passed']} | {counts['failure']} | {counts['error']} | {counts['skipped']} | {elapsed:.3f} |")
    report['runs'] = runs
    selections = []
    for lane, node in NATIVE_CAPACITY_CASE_LANES.items():
        value = json.loads((args.scratch / (lane + '.json')).read_text())
        assert value['selection_verified'] and value['selected_nodes'] == [node]
        assert value['returncode'] == 1 and len(value['collection_errors']) == 3
        assert not value['execution_pass']
        assert Path(value['log']).stat().st_size
        selections.append(value)
    report['lane_selections'] = selections
    report['new_lanes'] = len(selections)
    report['native_lanes'] = len(NATIVE_CASE_LANES)
    report['dedicated_lanes'] = len(DEDICATED_CASE_LANES)
    workflow = '.github/workflows/main.yaml'
    # Preserve the terminal newline: YAML literal-block scalar values depend
    # on it. The convenience git() helper strips CLI output for hashes/status.
    old_workflow = subprocess.check_output(['git', 'show', BASE + ':' + workflow], cwd=ROOT)
    old_jobs = yaml.safe_load(old_workflow)['jobs']
    new_jobs = yaml.safe_load((ROOT / workflow).read_text())['jobs']
    assert old_jobs['test'] == new_jobs['test']
    for name in old_jobs:
        if name != 'native-public-completion':
            assert old_jobs[name] == new_jobs[name]
    old_native = old_jobs['native-public-completion']
    new_native = new_jobs['native-public-completion']
    assert {k:v for k,v in old_native.items() if k != 'strategy'} == {
        k:v for k,v in new_native.items() if k != 'strategy'}
    assert {k:v for k,v in old_native['strategy'].items() if k != 'matrix'} == {
        k:v for k,v in new_native['strategy'].items() if k != 'matrix'}
    report['aggregate_needs'] = new_jobs['test']['needs']
    report['unchanged_aggregate_and_non_native_jobs'] = True
    report['python_jobs'] = {'pull_request': 12 + len(DEDICATED_CASE_LANES) + 3,
                             'main_manual': 8 + len(DEDICATED_CASE_LANES) + 3}
    report['protected_sha256'] = {}
    for relative in PROTECTED:
        raw = (ROOT / relative).read_bytes()
        old = subprocess.check_output(['git', 'show', BASE + ':' + relative], cwd=ROOT)
        assert old == raw
        report['protected_sha256'][relative] = hashlib.sha256(raw).hexdigest()
    assert not git('diff', BASE, '--', 'utils/update_ci_shard_timings.py',
                   'src/data_sheets_schema/native_execution_registration.py',
                   'src/data_sheets_schema/native_shared_authority_wire.py',
                   'src/data_sheets_schema/native_controller_sources_v2.json')
    report['updater_v1_roster_controller_pins_unchanged'] = True
    report['changed_source_files'] = git('diff', '--name-only', BASE, '--', 'src/').splitlines()
    assert report['changed_source_files'] == ['src/data_sheets_schema/native_execution_registration_v2.py']
    inventory = json.loads((args.scratch / 'capacity-inventory.json').read_text())
    assert inventory['proposed_lanes'] == NATIVE_CAPACITY_CASE_LANES
    report['slow_cases'] = len(inventory['slow_cases'])
    report['slow_dispositions'] = dict(Counter('ordinary' if r['disposition']=='ordinary' else 'dedicated'
                                              for r in inventory['slow_cases']))
    report['timing_refresh'] = json.loads((args.scratch / 'timings-summary.json').read_text())
    (args.scratch / 'verification-table.md').write_text('\n'.join(rows) + '\n')
    (args.scratch / 'evidence-summary.json').write_text(json.dumps(report, indent=2) + '\n')
    if args.handoff:
        acceptance = runs['acceptance']
        assert acceptance['counts'] == {'passed': acceptance['cases']}
        assert not report['status'], 'commit the reporting helper before the final handoff'
        assert runs['isolation-before']['counts'] == {'passed': 1, 'failure': 2}
        assert runs['isolation-after']['counts'] == {'passed': 3}
        assert runs['module-isolation-before']['counts'] == {'passed': 1, 'error': 1}
        assert runs['module-isolation-after']['counts'] == {'passed': 2}
        timing = report['timing_refresh']
        named = [
            'tests/test_native_packet_full_chain.py', 'tests/test_native_canary_packet_rehearsal.py',
            'tests/test_ci_sharding.py', 'tests/test_ci_timing_update.py', 'tests/test_native_execution_ci_v2.py',
            'tests/test_native_execution_round3_v2.py', 'tests/test_native_u3d_guard_contract.py',
            'utils/pytest_shard.py', 'utils/ci_sharding.md', 'utils/ci_test_durations.json',
            'src/data_sheets_schema/native_execution_registration_v2.py', '.github/workflows/main.yaml',
            'scripts/adhoc/audit_ci_capacity_20261114.py', 'scripts/adhoc/install_ci_capacity_20261114.py',
            'scripts/adhoc/refresh_ci_capacity_timings_20261114.py',
            'scripts/adhoc/verify_capacity_lane_collection_20261114.py',
            'scripts/adhoc/summarize_ci_capacity_20261114.py', 'tests/fixtures/ci_timings/43536007079',
            'tests/test_fairscape_integration/test_canonical_routes.py',
            'tests/test_fairscape_integration/test_forward_typed_projections.py',
            'tests/test_fairscape_integration/test_nested_dataset_readback.py',
        ]
        assert all((ROOT / path).exists() for path in named)
        assert all((ROOT / row['file']).exists() for row in inventory['slow_cases'])
        inventory_table = (args.scratch / 'capacity-inventory.md').read_text()
        file_counts = '\n'.join(f"- `{name}`: {sum(counts.values())} passed."
                                for name, counts in acceptance['files'].items())
        commits = '\n'.join('- `' + line.split(' ', 1)[0] + '` — ' + line.split(' ', 1)[1]
                            for line in report['commits'])
        handoff = f"""Implemented and committed the builder isolation, native CI capacity layout and authorized timing refresh. The full local acceptance run passed all {acceptance['cases']} tests. All {report['new_lanes']} new native lanes selected exactly their intended real-suite testcase. No push, GitHub write, provider call, real native-binary call or production launch occurred.

Branch: `codex/native-ci-capacity-20261114`. The worktree is clean. Base: `{BASE}`. Final head: `{report['head']}`.

- W = `{ROOT}`
- S = `{args.scratch}`
- P = `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema`

Commits in integration order:

{commits}

Both isolation commits are required. A real legacy test from shard 8, `tests/test_native_execution.py::test_missing_authority_refuses_before_any_reservation[review_path]`, loads the old controller alias. Before the fix, running it before the standalone full-chain canary and synthetic preparation check produced one pass and two import-origin failures. The same sequence passed all three after applying the existing `isolated_modules` fixture to both builder files.

The read-only review then identified a separate scope problem: the full-chain file's shared fixture starts at module scope, before function-scoped fixture markers. The targeted sequence with `test_source_versions_and_terms` still gave one pass and one setup error. The second isolation commit reuses the same isolation context for that shared fixture's whole lifetime, preserving module reuse and restoring imports at teardown. That sequence now passes both tests. Production import-origin validation is unchanged.

The full acceptance command deliberately starts with the legacy contamination test, then runs both complete builder files, the entire sharding and timing test files, and the three CI-roster contract files. It passed with no failures, errors or skips. Per-file counts from S/evidence-summary.json:

{file_counts}

The acceptance source head was `{report['acceptance_head']}`. The reporting-helper commits change none of its source, test, utility or workflow inputs. S/interpreter.txt records Python 3.13.12; S/dependency-files.sha256 records the repository dependency-file hashes. This is local offline verification, not Python 3.12 CI acceptance.

The audit found {report['slow_cases']} ordinary-shard testcase records over 120 seconds in the eleven available JUnit artifacts. It moves all {report['slow_dispositions']['dedicated']} measured native runtime cases to `native-capacity-01` through `native-capacity-33`, and additionally moves the three public retention cases from cancelled shard 6. Shard 6 has no completed JUnit artifact; those three are selected from the lead's timeout finding and are explicitly not counted as measured cases.

The remaining {report['slow_dispositions']['ordinary']} slow cases stay ordinary. Native scanner fixtures have no native runtime freshness window. Non-native cases' owning shards completed within the job budget, and keeping their modules together preserves module-fixture reuse. Every case, its file, shard, measured duration and disposition appears in the generated inventory below. Timings include JUnit setup/call/teardown and are scheduling hints, not additive wall-time predictions.

W/utils/pytest_shard.py, W/.github/workflows/main.yaml and the v2 check roster in W/src/data_sheets_schema/native_execution_registration_v2.py agree on {report['native_lanes']} native lanes. The existing native-public-completion matrix now includes the new cases. There are {report['python_jobs']['pull_request']} Python jobs on PRs and {report['python_jobs']['main_manual']} on main/manual runs. This adds runner setup overhead; the next CI run must establish the actual runtime and timeout outcome. Parsed YAML confirms that the aggregate job and its complete dependency list are unchanged, as are every other job and all native-job fields outside the matrix. No deadline, protected file, historical v1 roster or controller/prompt pin changed.

W/tests/test_ci_sharding.py preserves the exact case IDs, fixture partition coverage and fail-closed dedicated-lane rules. Its complete suite includes the aggregate truth-table check. W/utils/ci_sharding.md describes the layout and timing limits.

All {report['new_lanes']} real-suite lane collections selected their singleton. They report only the three expected uninitialized FAIRSCAPE errors in test_canonical_routes.py, test_forward_typed_projections.py and test_nested_dataset_readback.py. Each collection returns 1 and is recorded as selection verified, execution not passed. These are not clean full-suite collection results and do not execute the dedicated native cases. The collection canary used the same launcher, environment, output directory and two-process executor as the remainder; its persisted JSON and log were checked before fan-out.

CL196-F2 / issue 6230 is addressed. Every historical assertion remains unchanged in W/tests/test_ci_timing_update.py, applied to the preserved previous map. A new contract decompresses pinned original JUnit, resolves testcase modules independently, removes the dedicated nodes, sums Decimal durations, reconstructs the filtered XML and checks the unchanged updater's result. It also reconstructs and hashes the entire previous duration document, checks the complete active overlay and retains unmeasured values. The active weights no longer depend on accepting a self-reported new map.

The refresh uses successful ordinary shards {', '.join(map(str, timing['selected_shards']))} from run 43536007079. Failed shards 1, 8 and 10, cancelled shard 6, and all dedicated cases are excluded. It contains {timing['test_cases']} retained testcase records, excludes {timing['excluded_cases']} newly dedicated records from those inputs, measures {timing['measured_files']} files, adds {timing['added_files']} previously untimed files and preserves {timing['retained_unmeasured_files']} unmeasured weights. Lossless originals occupy {timing['fixture_bytes']} compressed bytes under W/tests/fixtures/ci_timings/43536007079. The run as a whole failed; this is a partial refresh from its successful shards. The single-artifact timing canary verified persistence, decompression and the unchanged updater before the batch. The full contract additionally verifies all dedicated-case exclusions.

Review finding CL196-CI-R1, fixed: function-scoped isolation alone did not cover module-scoped builder setup. Its failing and passing evidence is retained in the module-isolation logs. Reporting finding CL196-CI-R2, fixed: the initial summary helper stripped the trailing newline from git-show output, changing the parsed final YAML literal scalar and falsely reporting an aggregate-job difference. S/report-initial-error.log retains the failure. The helper now parses the exact original bytes and keeps the equality assertion intact; the workflow did not change. The lead should record both findings; no GitHub issue was filed because the assignment forbids GitHub writes. No unresolved implementation finding remains from the read-only review. Existing unrelated CI failures in the lead's run summary were not repaired here. Corrected builder duration in Linux CI and actual execution of the newly dedicated lanes remain unverified.

Saved verification runs (generated from JUnit by W/scripts/adhoc/summarize_ci_capacity_20261114.py):

{chr(10).join(rows)}

Recorded validation commands, from W with P and S set to the roots above. Use a fresh scratch root for any new test execution so the reported evidence remains intact; the summarizer reads the original task S.

```sh
PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 "$P/.venv/bin/python" -m pytest \\
  'tests/test_native_execution.py::test_missing_authority_refuses_before_any_reservation[review_path]' \\
  tests/test_native_packet_full_chain.py tests/test_native_canary_packet_rehearsal.py \\
  tests/test_ci_sharding.py tests/test_ci_timing_update.py \\
  tests/test_native_execution_ci_v2.py tests/test_native_execution_round3_v2.py \\
  tests/test_native_u3d_guard_contract.py -q -p no:cacheprovider \\
  --basetemp="$S/acceptance-tmp" --junitxml="$S/acceptance.xml"

PYTHONDONTWRITEBYTECODE=1 "$P/.venv/bin/python" \\
  scripts/adhoc/verify_capacity_lane_collection_20261114.py "$S" --canary
# Verify the persisted canary before the remainder.
PYTHONDONTWRITEBYTECODE=1 "$P/.venv/bin/python" \\
  scripts/adhoc/verify_capacity_lane_collection_20261114.py "$S" --remaining

PYTHONDONTWRITEBYTECODE=1 "$P/.venv/bin/python" \\
  scripts/adhoc/summarize_ci_capacity_20261114.py "$S"
```

The inventory command takes the artifact root, lead failure-summary JSON and S as its three positional arguments. The timing helper takes those same arguments; its sequence was --canary, plan without flags, then --apply. It intentionally refuses a second application. Replaying a refresh requires a fresh scratch directory and the pre-refresh duration snapshot; the current timing test reconstructs the installed refresh directly from its committed fixtures. The lane installer takes S/capacity-inventory.json and intentionally applies only to the pre-layout source. All helper scripts are retained on the branch. Primary and lead worktrees were not edited, except this explicitly assigned handoff.

The complete generated slow-case inventory follows. Its source is S/capacity-inventory.json; the table is produced by W/scripts/adhoc/audit_ci_capacity_20261114.py.

{inventory_table}"""
        assert chr(64) not in handoff
        args.handoff.write_text(handoff)
        assert args.handoff.stat().st_size
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
