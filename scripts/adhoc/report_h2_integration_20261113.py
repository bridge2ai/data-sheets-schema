#!/usr/bin/env python3
"""Issue 6193-6202 integration handoff, 2026-11-13.
Inputs: saved cohort XML/outcomes/sidecars and local Git source evidence.
Outputs: Markdown and JSON handoff in the lead's report worktree; no publishing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = Path.home() / 'agent-work/data-sheets-schema/helper2-integration-fixes-20261113'
REPORT = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs'


def pin(path):
    return {'path': str(path), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def cohort(path):
    record = {'name': path.name, 'path': str(path)}
    for name in ('plan.json', 'outcome.json', 'pytest-command.json', 'ci-lane.json', 'summary.json'):
        file = path / name
        if file.exists():
            record[name[:-5]] = json.loads(file.read_bytes())
            record[name + '_pin'] = pin(file)
    xml = path / 'pytest.xml'
    if xml.exists():
        cases = [c for c in ET.parse(xml).iter('testcase') if c.get('name')]
        record['junit_pin'] = pin(xml)
        record['counts'] = {'passed': sum(not any(c.find(t) is not None for t in ('failure', 'error', 'skipped')) for c in cases),
            **{t: sum(c.find(t) is not None for c in cases) for t in ('failure', 'error', 'skipped')}}
        record['failures'] = [dict(c.attrib, detail=ET.tostring(c, encoding='unicode')) for c in cases
                              if c.find('failure') is not None or c.find('error') is not None]
        record['skipped_cases'] = [dict(c.attrib, detail=ET.tostring(c, encoding='unicode')) for c in cases
                                   if c.find('skipped') is not None]
    for name in ('pytest.log', 'scanner.json', 'scanner.md'):
        if (path / name).exists():
            record[name + '_pin'] = pin(path / name)
    return record


def main(label):
    cohorts = [cohort(p) for p in sorted((BASE / 'tests').iterdir()) if p.is_dir()]
    source = json.loads((BASE / 'source-audit-final.json').read_bytes())
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == source['head']
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD'], cwd=ROOT, check=True, capture_output=True)
    tested = json.loads((BASE / (label + '.json')).read_bytes())
    subprocess.run(['git', 'diff', '--exit-code', tested['commit'], source['head'], '--',
                    '.', ':(exclude)scripts/adhoc'], cwd=ROOT, check=True, capture_output=True)
    public = []
    for item in cohorts:
        if not any(item['name'].endswith('-' + name) for name in ('correction', 'omissions', 'pending')):
            continue
        summary = item.get('summary', {})
        results = summary.get('public_results', [])
        result = results[0]['result'] if len(results) == 1 else None
        status = ('complete' if result and result['state'].startswith('completed') else
                  (result.get('first_stop') if result else 'no saved public result'))
        public.append({'cohort': item['name'], 'status': status,
            'result_paths': [r['path'] for r in results], 'sidecars': summary.get('sidecars', [])})
    required = [label + '-' + name for name in ('unit-canary', 'native', 'audit', 'budget', 'focused',
        'dependents', 'scanner', 'guards', 'correction', 'omissions', 'pending')]
    completed = {item['name'] for item in cohorts if item.get('outcome', {}).get('cleanup_verified')
                 and (sum(item.get('counts', {}).values()) > 0 or 'scanner.json_pin' in item)}
    not_run = sorted(set(required) - completed)
    failed = [item['name'] for item in cohorts if item['name'] in required
              and item.get('outcome', {}).get('returncode') not in (None, 0)]
    record = {'source': source, 'required_not_completed': not_run, 'required_failed': failed,
        'cohorts': cohorts, 'public': public, 'tested_export': tested,
        'tested_export_pin': pin(BASE / (label + '.json')),
        'tested_non_provenance_bytes_match_final_head': True,
        'issue_snapshots': [pin(path) for path in sorted((BASE / 'issues').glob('*.json'))],
        'held_exports': [pin(BASE / (label + '.hold.json')) for label in ('fixed4', 'fixed6')],
        'process_state_preflight': pin(BASE / 'process-state-preflight/result.json'),
        'unused_ps_copy_attempt': pin(BASE / 'unprivileged-ps-preflight/result.json'),
        'approval_review': {'rejected_action': 'proposed UDP peer selection to a nonlocal documentation address',
            'reason': 'external network activity is outside the offline-only scope', 'executed': False,
            'safe_alternative': pin(BASE / 'loopback-preflight-local-v2/result.json')},
        'compatibility_proof': pin(BASE / 'checkpoint-compatibility.json'),
        'docs_audit': pin(BASE / 'run-limit-audit-final/run-limit-audit.json'),
        'boundary': 'offline local synthetic fixtures; no real native/provider/model calls, capture, reservation, push or GitHub write',
        'interpreter_limit': 'CI step variables, PYTHONPATH and file lists are exact; local macOS CPython 3.13 is not Ubuntu CPython 3.12'}
    answer = ('Not ready for acceptance: required validation failed or remains incomplete.' if failed or not_run else
              'The assigned fixes and required offline validation are complete.')
    lines = [answer, '',
        'The callback preload repair and the assigned CI, alarm, timing-sidecar, test and documentation changes are committed locally. Nothing was published; no production authority is claimed.', '',
        f"Source branch: `codex/native-h2-integration-fixes-20261113`; head `{source['head']}`; base `{source['base']}`.", '',
        f"Final validation export: `{tested['commit']}`. Production code, tests, documentation and CI configuration match the handoff head; only provenance scripts may differ.", '',
        '## Changes and review', '',
        '- 6200: source-verified admission preloads host-power and timing utilities for the full callback lifetime. The regression forbids any module load on the exercised historical worker.',
        '- 6201/6202: event-driven deadline fixtures now drive the enforced continuous clock and anchor at dispatch. Existing early/late limits, interrupt checks, delayed-close negative control and reason-source assertions remain. The checkpoint allowlist update is backed by exact-byte comparison of every extracted definition and constant against accepted fc00ce654; historical v2 and v3-refusal tests remain.',
        '- 6193/6194: expiry latches one exception; queued alarms are inert during unwind. Teardown retries interrupted idempotent steps, waits another polling interval with the alarm blocked, drains pending delivery, restores the mask, and preserves the synchronous dispatch check.',
        '- 6195/6196: timing rows remain bounded in memory throughout each operation. Its outer scope hands them to a bounded daemon queue without waiting for file I/O, after its outcome and registration-lock release. Reservation seals recording; later admission cannot append rows. Queue contention, capacity, process exit and ordinary persistence failures may drop diagnostics; InterruptedError propagates. Tests stall persistence and fill the queue without delaying the completed operation.',
        '- 6197/6198: deadline-origin separation covers each registered duration; suppressed-alarm tests exercise the synchronous dispatch backstop and descriptor cleanup; signal ownership/mask tests and a shared-engine stalled-admission publication test were added.',
        '- 6199: documentation was regenerated from one integrated checkout. D138/D143 limits and freshness margins remain unchanged.', '',
        'The four protected files and guard v1 match the assigned base. ' +
        ('A controller pin proposal is required; see the JSON census.' if source['pin_proposal_required'] else
         'All controller source-manifest entries still match; no pin proposal or scanner pin rotation was needed or applied.'), '',
        'The separate read-only review traced callback utility lifetimes, timer ownership and exceptional cleanup, timing-scope placement outside registration locks, queue bounds and failure handling, the exact-byte compatibility proof, and the unchanged dispatch/deadline assertions. No additional source defect was identified in that pass. Failed validation and its limits are reported below; this review does not substitute for the lead’s independent review.', '',
        '## Saved JUnit counts', '', '| Cohort | Passed | Failed | Errors | Skipped | Cleanup verified |',
        '| --- | ---: | ---: | ---: | ---: | --- |']
    for item in cohorts:
        counts = item.get('counts', {})
        lines.append('| ' + item['name'] + ' | ' + ' | '.join(str(counts.get(name, '—'))
            for name in ('passed', 'failure', 'error', 'skipped')) + ' | ' +
            str(item.get('outcome', {}).get('cleanup_verified', False)) + ' |')
    lines += ['', 'The JSON handoff preserves exact commands, CI step environment, source/export identity, XML hashes, failures and cleanup records. CI lane HTTP fixtures use loopback only; external networking and real native binaries are denied. Local macOS CPython 3.13 does not establish Ubuntu CPython 3.12 equivalence.', '',
              'The initial preload-canary attempt failed during runner bootstrap because its copied command named an unavailable timing plugin; it collected no test result. The runner was corrected and preload-canary2 passed. The original failure and its incomplete cleanup receipt remain in the evidence. The unused fixed2 and fixed3 queues were superseded before starting any tests, with exact-process receipts retained.', '',
              'The fixed4 CI steps failed before pytest because the sandbox used an invalid literal-IP rule. The local-only replacement verifies a localhost exchange and a denied Unix-domain listener. The fixed5 canary then exposed a missing argument in the child-origin witness, also before pytest; that caller was repaired. These are retained harness failures, not product-test failures.', '',
              'The fixed4 focused XML records 210 passes, 14 assertion failures and one worker error. Process-wide signal injection in the new fixtures reached xdist threads, leaving alarm ownership disturbed and causing later admission refusals. The fixtures now direct signals to the blocked test thread. The shared-engine fixture also tried to patch the restricted capability projection; it now injects only a clock into the underlying source-loaded controller. The original failed artifacts are retained. Summarization now records intentional malformed or symlink sidecar fixtures instead of failing on them.', '',
              'The fixed6 native lane recorded 974 passes and 27 failures associated with macOS refusing setuid ps inside the sandbox. The five assigned deadline/reason-source cases passed. A byte-identical ps copy with privilege bits removed was killed before producing output and is not used. The macOS fixture fallback now reads independent status and parent metadata with the existing psutil dependency; an own-child zombie/parent preflight passed inside the unchanged sandbox. The Linux /proc path, controller exit checks and signal assertions remain unchanged. No CPU or load measurements were requested.', '',
              'The fixed6 audit lane passed all 2,168 tests. After its verified cleanup, the held queue stopped before launching its next cohort; the driver’s missing-directory error records that deliberate stop. The revised export then started independently after that cleanup receipt.', '',
              'The five native-lane deadline/reason-source failures and the audit deadline-receipt failure were stale test clock injection: the fixtures replaced time.monotonic while production now enforced elapsed_ns. Only the fixture clock binding changed. The checkpoint failures were an omitted compatibility admission, corrected after exact-byte proof. No deadline, interrupt or delayed-close assertion was weakened.', '',
              '## Public completion and capture-to-reservation', '', '| Cohort | Outcome | Continuous span seconds |', '| --- | --- | ---: |']
    for item in public:
        spans = [span['elapsed_ns'] / 1e9 for sidecar in item['sidecars'] for span in sidecar['spans']]
        lines.append('| ' + item['cohort'] + ' | ' + str(item['status']).replace('|', '/') + ' | ' +
                     (', '.join(f'{value:.6f}' for value in spans) if spans else 'unknown') + ' |')
    lines += ['', 'These are synthetic software results. A complete public result is not scientific acceptance or authorization for a native launch.', '',
              '## Outstanding validation', '', 'Required cohorts without verified completion: ' + (', '.join(not_run) if not_run else 'none') + '.',
              'Required cohorts with a nonzero result: ' + (', '.join(failed) if failed else 'none') + '.',
              'The full repository suite is left to the lead’s CI, as assigned. Exact skipped case names and reasons are retained under skipped_cases in each JSON cohort. No CPU-monitoring diagnostic was run.', '',
              '## Evidence', '', f"- Scratch evidence: `{BASE}`.",
              f"- Compatibility proof: `{BASE / 'checkpoint-compatibility.json'}`.",
              f"- Source and protected-file audit: `{BASE / 'source-audit-final.json'}`.",
              f"- Integrated documentation inventory: `{BASE / 'run-limit-audit-final/run-limit-audit.json'}`.", '',
              'Nothing pushed; no GitHub writes. Stop after this handoff.', '',
              'Automatic approval review rejected the proposed external-address UDP witness because it was outside the offline scope. It was not run. The replacement local-only sandbox checks passed; their receipt is retained in the JSON handoff.', '']
    markdown = '\n'.join(lines)
    assert '@' not in markdown
    md = REPORT / 'codex-h2-integration-fixes-20261113.md'
    js = md.with_suffix('.json')
    if md.exists() or js.exists():
        raise FileExistsError('retain any existing handoff; choose a new reviewed destination')
    with md.open('x') as stream:
        stream.write(markdown)
    with js.open('x') as stream:
        stream.write(json.dumps(record, indent=2).replace('@', '\\u0040') + '\n')
    print(json.dumps({'markdown': pin(md), 'json': pin(js)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', required=True)
    main(parser.parse_args().export)
