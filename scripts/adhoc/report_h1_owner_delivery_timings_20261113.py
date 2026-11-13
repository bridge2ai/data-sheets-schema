#!/usr/bin/env python3
"""Build the answer-first helper-1 followup handoff, 2026-11-13.
Inputs: saved 6192 verification, local CI run summary, unchanged timing snapshot,
D128 command verification and the assigned branch. Outputs: handoff MD/JSON.
No network, test, scan, native executable or source edit; report refuses overwrite.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
R = E / 'codex-development-efficiency-20261111'
H = R / 'notes/development_efficiency_20261111/handoffs'
S = R / 'scripts/adhoc'
W = E / 'codex-native-h1-ci-followups-20261113'
BASE = 'b70c8a56c47ff4add3d905313adabdce02ee7d5a'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': '/var/empty', 'LC_ALL': 'C',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
       'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': 'file', 'GIT_TERMINAL_PROMPT': '0'}
HELPERS = ['run_h1_ci_followup_tests_20261113.py',
           'summarize_h1_owner_delivery_fix_20261113.py',
           'refresh_h1_d128_20261113.py', 'verify_h1_d128_refresh_20261113.py',
           'report_h1_owner_delivery_timings_20261113.py']


def need(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def evidence(path):
    return {'path': str(path), 'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}


def git(*args):
    return subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
        *args], cwd=W, env=ENV, capture_output=True, check=True).stdout


def main():
    stem = H / 'codex-h1-owner-delivery-and-timings-20261113'
    need(not stem.with_suffix('.md').exists() and not stem.with_suffix('.json').exists(), 'preserve existing handoff')
    owner_path = H / 'codex-h1-6192-owner-delivery-20261113.json'
    owner = json.loads(owner_path.read_bytes())
    ci_path = H / 'lead-ci-run-43420728960-failures-20261113.json'
    ci = json.loads(ci_path.read_bytes())
    need(ci['run_id'] == '43420728960' and ci['head'] == BASE and ci['conclusion'] == 'failure', 'CI identity differs')
    verification_path = H / 'codex-h1-d128-command-verification-20261113.json'
    verification = json.loads(verification_path.read_bytes())
    wrapper = S / 'refresh_h1_d128_20261113.py'
    need(verification['status'] == 'plan_and_controls_passed'
         and verification['wrapper_sha256'] == sha(wrapper.read_bytes()), 'D128 wrapper verification differs')
    weights_path = W / 'utils/ci_test_durations.json'
    weights_raw = weights_path.read_bytes()
    weights = json.loads(weights_raw)
    need(weights_raw == git('show', BASE + ':utils/ci_test_durations.json'), 'timing snapshot unexpectedly changed')
    branch = git('branch', '--show-current').decode().strip()
    need(branch == 'codex/native-h1-ci-followups-20261113', 'wrong assigned branch')
    need(not git('status', '--porcelain').strip(), 'commit assigned work before final report')
    head = git('rev-parse', 'HEAD').decode().strip()
    changed = git('diff', '--name-only', BASE, head).decode().splitlines()
    need(not any(path.startswith('src/') for path in changed), 'production source changed')
    helper_rows = []
    for name in HELPERS:
        raw = (S / name).read_bytes()
        need(raw == (W / 'scripts/adhoc' / name).read_bytes()
             == git('show', head + ':scripts/adhoc/' + name), 'helper commit differs: ' + name)
        helper_rows.append(evidence(S / name))
    rows = []
    for job in ci['jobs']:
        match = re.fullmatch(r'Python 3.12 / shard (\d+)', job['name'])
        if match:
            rows.append({'shard': int(match[1]), 'job_id': job['id'], 'outcome': job['conclusion'],
                         'observed_job_seconds': job['seconds'], 'estimated_case_seconds': None,
                         'observed_junit_case_seconds': None, 'pytest_tail': job['pytest_tail'],
                         'missing': 'No locally staged raw JUnit or artifact roster identified.'})
    rows.sort(key=lambda row: row['shard'])
    need([row['shard'] for row in rows] == list(range(1, 13)), 'ordinary shard roster incomplete')
    command = (
        '/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -S -P -B '
        + str(wrapper) + ' --run --commit FULL_FINAL_CANDIDATE_SHA --label final-head-YYYYMMDD-01'
    )
    search_scope = [str(R / p) for p in ('notes/development_efficiency_20261111/assignments',
        'notes/development_efficiency_20261111/handoffs', '.temp')]
    search_scope += [str(E.parent / 'data-sheets-schema/.temp'), str(E / 'scratch-lead-ci-shards-20261113'),
                    str(E / 'scratch-lead-pytest-20261112'), '~/agent-work/data-sheets-schema (run-labelled paths only)']
    result = {
        'answer': 'Issue 6192 fixed and verified; D128 one-command preparation verified. Shard-weight refresh remains blocked on local JUnit artifacts.',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'branch': branch,
        'head': head, 'base': BASE, 'changed_paths': changed, 'published': False,
        'issue6192': {'status': 'fixed_controlled_reproduction_and_verification', 'evidence': evidence(owner_path),
                     'tested_source': owner['source_commit'], 'ci_worker_order_reproduced': False,
                     'cause': owner['cause'], 'fix': owner['fix'], 'limitations': owner['limitations'],
                     'review_findings': owner['review_findings'], 'cohorts': owner['cohorts']},
        'timings': {'status': 'blocked_missing_local_junit', 'run': '43420728960', 'head': BASE,
                    'run_conclusion': ci['conclusion'], 'summary': evidence(ci_path), 'shards': rows,
                    'weights_retained': evidence(weights_path), 'retained_weight_count': len(weights['file_seconds']),
                    'weights_unmeasured_from_this_run': sorted(weights['file_seconds']),
                    'provenance_unchanged': True, 'estimated_and_case_times_unavailable': True,
                    'search_included_hidden_and_ignored': True, 'bounded_search_scope': search_scope,
                    'absence_scope': 'No matching raw JUnit/roster found in these paths; no claim about GitHub or other local locations.',
                    'needed': 'Staged raw ordinary-shard pytest.xml files and artifact roster with run/head identities. Keep dedicated lanes separate.',
                    'next': 'Use existing utils.update_ci_shard_timings on eligible successful-shard artifacts; retain prior weights and provenance for all unmeasured files. Do not strip failures to bypass its successful-run check. Report failed/cancelled shard exclusions explicitly.'},
        'd128': {'status': 'one_command_prepared_plan_and_controls_verified', 'command': command,
                 'wrapper': evidence(wrapper), 'verification': evidence(verification_path),
                 'scope': 'Any later HEAD of the existing codex/native-main-integration-20261112 checkout, after lead integration; not an arbitrary branch.',
                 'review_commit': '99ac3432daab7f6161b321038986e489d5e6fd14',
                 'new_scan_executed': False, 'run_orchestration_verified_end_to_end': False,
                 'd128_gate_passed': False, 'instrument_approval_changed': False,
                 'review': 'Independent read-only wrapper review found no blocking defects at the verified SHA.',
                 'expected_inputs': 'Clean exact candidate HEAD; full local history and exact FAIRSCAPE gitlink; same reviewed scanner assets; D146 protected hashes and policy; frozen D128 evidence; both pinned saved helpers in R; dependency venv; absent quiet-window lock; fresh output label.'},
        'helpers': helper_rows, 'producer': evidence(Path(__file__)),
        'boundary': 'No source/protected/guard-v1 edits, source publication, network, provider/native calls, new scan cohort or STATUS edit.'}
    raw = (json.dumps(result, indent=2, sort_keys=True).replace(chr(64), '\\u0040') + '\n').encode()
    with stem.with_suffix('.json').open('xb') as stream:
        stream.write(raw)
    lines = [
        '# Helper 1: owner delivery, shard timings and D128 refresh', '', result['answer'], '',
        f'Local branch `{branch}`; head `{head}`; base `{BASE}`. Nothing published.', '',
        '## Issue 6192', '',
        'The fresh-owner test still shared the interpreter dependency guard. Changing JSONEncoder.default reproduces the exact None/None assertion. The original warm/fresh/refusal assertions now run in a fresh Python process with exact checkout origins and mandatory assertions; the contaminated parent remains refused. Production is unchanged.', '',
        'The before-mutation regression fails as expected. The final mutation canary passes, then all 91 tests in the owner-delivery, catalog-reuse and SDK-isolation suite pass. Two earlier implementation canaries exposed mistakes in the new origin witness; both were retained and corrected before expansion. The independent review also closed inherited PYTHONOPTIMIZE suppression.', '',
        f'Tested source: `{owner["source_commit"]}`. Detailed evidence: `{owner_path}` SHA-256 `{sha(owner_path.read_bytes())}`.', '',
        'The exact historical CI worker predecessor was not recovered. This controlled dependency-mutation reproduction is not an exact shard replay; local Python 3.13/macOS with two workers does not prove the four-worker Python 3.12/Linux ordering.', '',
        '## Shard weights: blocked on local JUnit', '',
        f'Run 43420728960 at `{BASE}` concluded failure. The saved job summary supplies these observed elapsed job times, including setup/teardown. They are not summed testcase seconds or wall-time predictions.', '',
        '| Shard | Outcome | Observed job seconds | Estimated case seconds |',
        '|---:|---|---:|---|',
    ]
    lines += [f'| {row["shard"]} | {row["outcome"]} | {row["observed_job_seconds"]:.1f} | unavailable |' for row in rows]
    lines += ['', f'All {len(weights["file_seconds"])} existing per-file weights and their provenance remain byte-identical to the base. Raw JUnit and the artifact roster were not found in the bounded hidden/ignored-inclusive searches listed in the JSON; the earlier artifact-location question remains unanswered. No run-derived weight was invented. The JSON names every retained weight.', '',
        'Shard 4 was cancelled; shards 2, 6 and 11 failed. The existing updater rejects failed XML. When raw artifacts are staged, use the successful ordinary-shard subset with the existing updater and preserve prior values/provenance for unmeasured files; keep dedicated lanes separate. Record exactly which files were measured before reporting a refresh. Estimated shard case-seconds remain unavailable without the run composition; substituting job wall time would change the quantity.', '',
        f'CI summary: `{ci_path}` SHA-256 `{sha(ci_path.read_bytes())}`. Timing snapshot SHA-256 `{sha(weights_raw)}`.', '',
        '## D128: one command', '',
        'After integrating onto the existing candidate branch, replace FULL_FINAL_CANDIDATE_SHA and use a new label:', '',
        '```sh', command, '```', '',
        'Use `--plan` instead of `--run` for read-only preflight. `--self-check` runs only the saved comparator controls. Expected inputs: clean exact HEAD of the candidate checkout, full local history, local FAIRSCAPE gitlink, unchanged reviewed scanner assets, D146 protected/policy bytes, frozen D128 fixture/evidence, two saved pinned helpers in R, dependency venv, no quiet-window lock and a fresh output label.', '',
        'The wrapper invokes the unchanged export helper then the unchanged comparison helper. It computes and verifies the manifest digest, verifies persisted reports, and keeps D128 approval false. Changed scanner/protected pins stop for review; the wrapper cannot approve future bytes. Partial evidence is preserved.', '',
        f'Wrapper SHA-256 `{sha(wrapper.read_bytes())}`. Verification SHA-256 `{sha(verification_path.read_bytes())}`: preflight passed, all 15 synthetic comparator controls passed, wrong-head and invalid-label controls refused; no export/scan directories were created. The new wrapper has not run an end-to-end scan. Both underlying helpers retain their accepted earlier real-comparison evidence.', '',
        '## Handoff boundary', '',
        'Ready: local 6192 test repair and D128 refresh command. Still needed: local JUnit/roster for the weight refresh; lead integration/publication; final-head D128 comparison and owner disposition. No production, protected or guard-v1 edits; no push, network, provider/native calls, new scanner cohort or STATUS edit.', '',
        'Helper provenance is committed on the assigned branch, with matching working copies under R/scripts/adhoc. The saved handoffs remain in R; all command/test outputs are retained.', '',
        f'Full evidence: `{stem.with_suffix(".json")}` SHA-256 `{sha(raw)}`.', '',
    ]
    md = '\n'.join(lines).encode()
    need(b'@' not in md and b'@' not in raw, 'handoff contains at-sign')
    with stem.with_suffix('.md').open('xb') as stream:
        stream.write(md)
    need(stem.with_suffix('.md').read_bytes() == md and stem.with_suffix('.json').read_bytes() == raw, 'handoff readback differs')
    print(json.dumps({'markdown': evidence(stem.with_suffix('.md')), 'json': evidence(stem.with_suffix('.json')), 'head': head}))


if __name__ == '__main__':
    main()
