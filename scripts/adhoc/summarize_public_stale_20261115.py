"""Summarize saved offline stale-observation measurements, 2026-11-15.

Inputs: scratch phase JSONL, partial cProfile, manifest, and saved test logs.
Output: summary.json and phase table on stdout for the lead assignment.
"""
import json
from pathlib import Path
import pstats
import sys
import hashlib
import subprocess
import xml.etree.ElementTree as ET

scratch = Path(sys.argv[1]).resolve()
rows = [json.loads(line) for line in (scratch / 'phases.jsonl').read_text().splitlines()]
groups = {}
for row in rows:
    key = row['file'] + ':' + row['function']
    group = groups.setdefault(key, {'calls': 0, 'seconds': 0.0, 'maximum': 0.0})
    group['calls'] += 1
    group['seconds'] += row['seconds']
    group['maximum'] = max(group['maximum'], row['seconds'])
profile = pstats.Stats(str(scratch / 'baseline.prof'))
top = sorted(({'file': key[0], 'line': key[1], 'function': key[2],
               'calls': value[1], 'self_seconds': value[2], 'cumulative_seconds': value[3]}
              for key, value in profile.stats.items()), key=lambda row: row['cumulative_seconds'], reverse=True)[:35]
manifest = json.loads((scratch / 'baseline/authority/preparation-environment.json').read_text())
summary = {'phase_aggregates': groups, 'completed_phase_rows': len(rows),
           'latest_phase_end': max((row['start']+row['seconds'] for row in rows), default=0),
           'partial_profile': top,
           'environment': {'distributions': len(manifest['distributions']),
               'record_entries': sum(len(row['file_stats']) for row in manifest['distributions']),
               'verified_bytes': sum(row['verified_files']['bytes'] for row in manifest['distributions']),
               'unowned_files': len(manifest['unowned_files'])}}
(scratch / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print('| Phase | Completed calls | Cumulative seconds | Maximum seconds |')
print('| --- | ---: | ---: | ---: |')
for key, group in sorted(groups.items()):
    print(f"| {key} | {group['calls']} | {group['seconds']:.3f} | {group['maximum']:.3f} |")
print(json.dumps(summary['environment'], sort_keys=True))

if '--report' in sys.argv or '--handoff' in sys.argv:
    root = Path(__file__).resolve().parents[2]
    report_path = root / 'notes/reviews/public_stale_20261115.md'
    data_path = report_path.with_suffix('.json')
    suites = ET.parse(scratch / 'tests-focused.xml').getroot()
    cases = list(suites.iter('testcase'))
    assert not any(case.find('failure') is not None or case.find('error') is not None for case in cases)
    summary['focused_test_cases'] = len(cases)
    collection = [line for line in (scratch / 'wide-collection.log').read_text().splitlines()
                  if line.startswith('tests/') and '::' in line]
    progress = (scratch / 'tests-baseline.log').read_text().split('Traceback', 1)[0]
    completed_count = progress.count('.')
    summary['interrupted_batch'] = {
        'completed_progress_markers': completed_count,
        'completed_nodeids': collection[:completed_count],
        'next_nodeid': collection[completed_count],
        'clean_summary': False,
    }
    assert ('tests/test_native_execution_registration_v2.py::test_prepare_rederives_real_native26_and_all_pins_without_effects'
            in summary['interrupted_batch']['completed_nodeids'])
    table = ['| Phase | Completed calls | Cumulative seconds | Maximum seconds |',
             '| --- | ---: | ---: | ---: |']
    for key, group in sorted(groups.items()):
        table.append(f"| {key} | {group['calls']} | {group['seconds']:.3f} | {group['maximum']:.3f} |")
    evidence = [scratch / name for name in (
        'isolation.json', 'baseline.prof', 'baseline-profile.txt', 'baseline.log',
        'phases.jsonl', 'phases.log', 'tests-baseline.log', 'tests-focused.log',
        'tests-focused.xml', 'collection.log', 'wide-collection.log', 'ci-correction.log', 'ci-variant.log',
        'ci-pending.log', 'ci-public-status.jsonl', 'comparison-numstat.txt', 'guard-6243.diff')]
    assert all(path.is_file() and path.stat().st_size for path in evidence)
    summary['evidence'] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in evidence}
    text = f"""The environment manifest's repeated live filesystem census is a measured major preparation cost. Stop for a design decision; no production fix, fixture restamping, pin rotation, or successful public launch is claimed.

The first completed fixture-building phase took {groups['native_shared_fixture.py:build_native_fixture']['seconds']:.3f} seconds locally. It called manifest verification {groups['native_environment_manifest.py:verify']['calls']} times, totaling {groups['native_environment_manifest.py:verify']['seconds']:.3f} cumulative seconds. A cached full verdict still runs a complete light census. This is not repeated full payload hashing alone. The source change for issue 6243 only changes window parsing and checks; it adds no environment traversal. The comparison against 725a9e5fe shows the manifest is new, while the guard and synthetic evidence fixture are byte-identical. No historical checkout timing was run.

Scope and limits: the full cProfile run was interrupted after its first manifest write and during preparation, preserving its profile. The lower-overhead phase run was stopped at the design boundary after the first fixture builder completed, during the second manifest write. Its external process-group watchdog recorded the termination in phases.log. Consequently, the exact full make_case duration, capture-to-launch interval, and allocation of every second of the CI failure remain unmeasured. These are partial diagnostics, not a completed public-case reproduction or a demonstrated speedup. Local CPython 3.13 on macOS differs from CI CPython 3.12, and another local Codex task was running.

The measured environment contains {summary['environment']['distributions']} third-party distributions, {summary['environment']['record_entries']} RECORD entries, {summary['environment']['verified_bytes']} verified payload bytes, and {summary['environment']['unowned_files']} unowned files. The primary virtual environment was copied with cp -R into the assignment scratch directory. Only the copied project path file was redirected; its adjacent backup and undo instruction are in isolation.json. The primary virtual environment was not changed.

Completed phase measurements follow. Rows overlap: caller times include callees, so do not sum the table. The table is generated from phases.jsonl by scripts/adhoc/summarize_public_stale_20261115.py.

""" + '\n'.join(table) + f"""

The partial cProfile recorded 11,050,979 lstat calls with 80.505 seconds of self time; pathlib.resolve accumulated 108.588 seconds, and the first manifest write accumulated 205.226 seconds under full profiling. These rounded values are retained in baseline-profile.txt and the structured partial_profile data. The lower-overhead trace measured the first manifest write at {groups['native_environment_manifest.py:write']['seconds']:.3f} seconds. Pure metadata validation memoization would not remove the dominant repeated ancestor traversal.

Recommended decision: authorize a separately reviewed census-scoped path-resolution design, with fresh RECORD and metadata reads, every included file checked, exact implementation identity, and end-of-census revalidation of all reused ancestor and symlink identities. Require adversarial ancestor replacement, symlink retargeting, same-size payload edits, metadata changes, and implementation changes before acceptance. The decision is whether that snapshot proof is an acceptable replacement for repeatedly resolving identical ancestor chains for every entry. Do not simply reuse a successful live census across calls, key a new verdict only on stat data, or move freshness checks. Also evaluate seeding the existing full-verification memo from write's first successful generation, retaining its race checks; that is a proposal, not an implemented or measured improvement. A patch would need a scanner source-pin proposal and the lead's review; no pin is changed here.

Observation order: tests/utils/native_synthetic_evidence.py authority_for first verifies registration, constructs and activates the invented owner word, reconstructs capture authority and reserves the synthetic slot. It then stamps capture_now immediately before constructing the invented event, claim, observations and capture manifest. current_guard_preparation runs afterward, and launch_case calls synthetic_launch after make_case returns. The production capture loop in src/data_sheets_schema/native_subscription_capture.py stamps a rate_limit_event when it is read, before guard preparation and dispatch as well. Thus the fixture already follows the production observation-before-guard order. Moving its timestamp after guard reconstruction would conceal real elapsed time, not correct fixture parity. src/data_sheets_schema/native_u4b_policy.py registers max_age_seconds as 1200. Freshness, margins, all windows and deadlines are unchanged.

CI confirmation: correction failed with stale-or-future-dated observation after 2421.65 seconds; pending after 3017.04 seconds; variant after 3048.60 seconds. All three logs are saved. Pending job 132959954885 and variant job 132959954692 were fetched after completion using read-only gh api. Total test duration is not observation age; the logs do not establish the missing capture-to-launch breakdown.

Validation: {len(cases)} focused manifest, mode, scanner, registration-shape and subscription-guard cases passed, with JUnit evidence. The wider suite was interrupted after its real registration rederivation test completed and the next parameterized fixture began. Pytest then raised a tmp_path stash KeyError during interruption cleanup; that batch has no clean final summary and must not be reported as a passing full registration suite. The complete shared-registration matrix remains unverified. Collection found 27521 tests and the three expected missing fairscape_models.rocrate errors. No complete public case was launched locally: preparation alone is already expensive, and this assignment stops for the design ruling. The diagnostic runs were bounded by an external process-group watchdog; no inherited alarm was used. No Claude binary, provider, capture, production launch, GitHub write or push occurred.

Files changed are diagnostic scripts and this report/data pair only. The four protected files, production code, tests, prompts and controller pins are untouched. The lead should record the unresolved census-design finding as an issue; this helper has no GitHub-write permission. There is no review-only pin diff because no pinned implementation changed.

Commit blocked: git add could not create the worktree index.lock because the sandbox returned Operation not permitted. Per assignment, no escalation or commit was attempted after that refusal. The following files remain uncommitted on codex/public-stale-20261115:

- scripts/adhoc/profile_public_stale_20261115.py
- scripts/adhoc/summarize_public_stale_20261115.py
- notes/reviews/public_stale_20261115.md
- notes/reviews/public_stale_20261115.json

Reproduce the retained summary from the worktree root:

```text
PYTHONPATH=$PWD/src {scratch}/isolated-venv/bin/python scripts/adhoc/summarize_public_stale_20261115.py {scratch} --report
```

The profiling producer is scripts/adhoc/profile_public_stale_20261115.py. It provides configure, bounded, phases, and cProfile modes. Use a fresh scratch case name for another cProfile run; the phases mode also consumes a fresh phases directory and must not overwrite retained evidence. The executed watchdog commands, elapsed times and return codes are saved in baseline.log, phases.log, tests-focused.log and collection.log. The interrupted wider pytest command is documented in the assignment session; tests-baseline.log preserves its output.

Evidence paths and SHA-256 values are recorded in {data_path}. Retained evidence files:

""" + '\n'.join('- ' + str(path) for path in evidence) + '\n'
    assert chr(64) not in text
    assert chr(64) not in json.dumps(summary)
    if '--report' in sys.argv:
        data_path.write_text(json.dumps(summary, indent=2) + '\n')
        report_path.write_text(text)
    if '--handoff' in sys.argv:
        handoff = root.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-public-stale-20261115.md'
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        text += '\nUnchanged base commit: ' + commit + '. Diagnostic files remain uncommitted. No push was made.\n'
        handoff.write_text(text)
        assert handoff.read_text() == text
        print(str(handoff))
        print(hashlib.sha256(handoff.read_bytes()).hexdigest())
