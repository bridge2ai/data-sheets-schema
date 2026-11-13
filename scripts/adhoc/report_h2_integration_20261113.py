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
    for name in ('pytest.log', 'scanner.json', 'scanner.md'):
        if (path / name).exists():
            record[name + '_pin'] = pin(path / name)
    return record


def main(label):
    cohorts = [cohort(p) for p in sorted((BASE / 'tests').iterdir()) if p.is_dir()]
    source = json.loads((BASE / 'source-audit-final.json').read_bytes())
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
    completed = {item['name'] for item in cohorts if item.get('outcome', {}).get('cleanup_verified')}
    not_run = sorted(set(required) - completed)
    failed = [item['name'] for item in cohorts if item['name'] in required
              and item.get('outcome', {}).get('returncode') not in (None, 0)]
    record = {'source': source, 'required_not_completed': not_run, 'required_failed': failed,
        'cohorts': cohorts, 'public': public,
        'issue_snapshots': [pin(path) for path in sorted((BASE / 'issues').glob('*.json'))],
        'compatibility_proof': pin(BASE / 'checkpoint-compatibility.json'),
        'docs_audit': pin(BASE / 'run-limit-audit-final/run-limit-audit.json'),
        'boundary': 'offline local synthetic fixtures; no real native/provider/model calls, capture, reservation, push or GitHub write',
        'interpreter_limit': 'CI step variables, PYTHONPATH and file lists are exact; local macOS CPython 3.13 is not Ubuntu CPython 3.12'}
    answer = ('Not ready for acceptance: required validation failed or remains incomplete.' if failed or not_run else
              'The assigned fixes and required offline validation are complete.')
    lines = [answer, '',
        'The callback preload repair and the assigned CI, alarm, timing-sidecar, test and documentation changes are committed locally. Nothing was published; no production authority is claimed.', '',
        f"Source branch: `codex/native-h2-integration-fixes-20261113`; head `{source['head']}`; base `{source['base']}`.", '',
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
        '## Saved JUnit counts', '', '| Cohort | Passed | Failed | Errors | Skipped | Cleanup verified |',
        '| --- | ---: | ---: | ---: | ---: | --- |']
    for item in cohorts:
        counts = item.get('counts', {})
        lines.append('| ' + item['name'] + ' | ' + ' | '.join(str(counts.get(name, '—'))
            for name in ('passed', 'failure', 'error', 'skipped')) + ' | ' +
            str(item.get('outcome', {}).get('cleanup_verified', False)) + ' |')
    lines += ['', 'The JSON handoff preserves exact commands, CI step environment, source/export identity, XML hashes, failures and cleanup records. CI lane HTTP fixtures use loopback only; external networking and real native binaries are denied. Local macOS CPython 3.13 does not establish Ubuntu CPython 3.12 equivalence.', '',
              'The five native-lane deadline/reason-source failures and the audit deadline-receipt failure were stale test clock injection: the fixtures replaced time.monotonic while production now enforced elapsed_ns. Only the fixture clock binding changed. The checkpoint failures were an omitted compatibility admission, corrected after exact-byte proof. No deadline, interrupt or delayed-close assertion was weakened.', '',
              '## Public completion and capture-to-reservation', '', '| Cohort | Outcome | Continuous span seconds |', '| --- | --- | ---: |']
    for item in public:
        spans = [span['elapsed_ns'] / 1e9 for sidecar in item['sidecars'] for span in sidecar['spans']]
        lines.append('| ' + item['cohort'] + ' | ' + str(item['status']).replace('|', '/') + ' | ' +
                     (', '.join(f'{value:.6f}' for value in spans) if spans else 'unknown') + ' |')
    lines += ['', 'These are synthetic software results. A complete public result is not scientific acceptance or authorization for a native launch.', '',
              '## Outstanding validation', '', 'Required cohorts without verified completion: ' + (', '.join(not_run) if not_run else 'none') + '.',
              'Required cohorts with a nonzero result: ' + (', '.join(failed) if failed else 'none') + '.',
              'The full repository suite is left to the lead’s CI, as assigned. No CPU-monitoring diagnostic was run.', '',
              '## Evidence', '', f"- Scratch evidence: `{BASE}`.",
              f"- Compatibility proof: `{BASE / 'checkpoint-compatibility.json'}`.",
              f"- Source and protected-file audit: `{BASE / 'source-audit-final.json'}`.",
              f"- Integrated documentation inventory: `{BASE / 'run-limit-audit-final/run-limit-audit.json'}`.", '',
              'Nothing pushed; no GitHub writes. Stop after this handoff.', '']
    markdown = '\n'.join(lines)
    assert '@' not in markdown
    md = REPORT / 'codex-h2-integration-fixes-20261113.md'
    js = md.with_suffix('.json')
    md.write_text(markdown)
    js.write_text(json.dumps(record, indent=2).replace('@', '\\u0040') + '\n')
    print(json.dumps({'markdown': pin(md), 'json': pin(js)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', required=True)
    main(parser.parse_args().export)
