#!/usr/bin/env python3
# Checkpoint G2 after the committed publication-test oracle correction,
# 2026-11-14. Inputs: saved cohort records, Git state, sealed H2 handoffs and
# helper/evidence files. Output: exclusive timestamp JSON in S2/checkpoints.
# No project imports, tests, probes, process calls, signals or Git mutations.
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
REPORTS = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs'
HEAD = '21367471df2e7d2f761153e1b91b218a705c62c6'
ACTIVE = 'publication-public-canary'
NODE = 'tests/test_native_publication_signals.py::test_public_first_signal_during_publication_keeps_exact_readback[2]'
LEGACY = {'tests/test_native_execution.py', 'tests/test_native_receipt_origin_reporting.py'}


def pin(path):
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'retry checkpoint after concurrent file write'
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(path.read_bytes())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def cohort(path):
    command = read(path / 'command.json')
    evidence = {name: pin(path / name) for name in ('command.json', 'outcome.json', 'pytest.xml', 'pytest.log') if (path / name).is_file()}
    outcome = read(path / 'outcome.json') if 'outcome.json' in evidence else None
    argv = command['command']
    bound = ('--basetemp=' + str(path / 'cases') in argv and '--junitxml=' + str(path / 'pytest.xml') in argv)
    status = ('incomplete; outcome absent' if outcome is None else 'interrupted; ineligible completed proof'
              if outcome['returncode'] == 2 else 'failed; retain evidence' if outcome['returncode'] != 0
              else 'zero-exit saved run; acceptance remains separately gated')
    return {'name': path.name, 'kind': 'cohort invocation' if bound else 'archived artifacts; not another invocation',
            'status': status, 'head': command['head'], 'evidence': evidence, 'outcome': outcome}


def main():
    assert git('rev-parse', 'HEAD') == HEAD
    command = read(OUT / ACTIVE / 'command.json')
    assert command['head'] == HEAD and command['cwd'] == str(ROOT)
    assert command['command'][6:-4] == [NODE] and command['command'][-4:-2] == ['-n', '4']
    component = read(OUT / 'final-components/command.json')['source_inventory']['selected_paths']
    component = [name for name in component if name not in LEGACY]
    engine = read(OUT / 'engine-admission/command.json')['source_inventory']['selected_paths']
    engine = [name for name in engine if name not in {'tests/test_native_attempt_deadline.py',
              'tests/test_native_admission_timer.py', 'tests/test_native_pre_dispatch_timing.py'}]
    assert len(component) == 16 and len(engine) == 15
    interrupted = read(OUT / 'final-regressions/outcome.json')
    assert interrupted['returncode'] == 2 and interrupted['counts'] == {'total': 30, 'failed': 1, 'error': 0, 'skipped': 0}
    junit = list(ET.parse(OUT / 'final-regressions/pytest.xml').iter('testcase'))
    assert len(junit) == 30 and sum(node.find('failure') is not None for node in junit) == 1
    log = (OUT / 'final-regressions/pytest.log').read_text(errors='replace')
    summary = [line for line in log.splitlines() if re.search(r'1 failed, 25 passed\b.*\bin [\d.]+s', line)]
    assert summary, 'retain exact interrupted log accounting'
    cleanups = sorted((OUT / 'final-regressions-interruption-6217-oracle').glob('cleanup-*.json'))
    cleanup = read(cleanups[-1])
    assert cleanup['safe_to_release_source_freeze'] is True
    assert all(row['original_reaped'] for row in [cleanup['coordinator'], cleanup['runner'], *cleanup['workers'], *cleanup['observed_descendants']])
    legacy = read(OUT / 'legacy-full-serial/outcome.json')
    census = read(OUT / 'legacy-collection-census/census.json')
    assert legacy['returncode'] == 0 and legacy['counts'] == {'total': 149, 'failed': 0, 'error': 0, 'skipped': 0}
    assert census['status'] == 'verified' and census['node_count'] == 149
    sealed = []
    for suffix, digest in (('md', 'c0036c97463b75f6869d5f6004b55ae6b6aace5cb8bc46890d12334d25575b20'),
                           ('json', 'c4a1b52fb3e552b4c5b6677cd4753cb3d4db37b27664539c20a48d31dac0eb68')):
        record = pin(REPORTS / ('codex-h2-integration-fixes-20261113.' + suffix))
        assert record['sha256'] == digest
        sealed.append(record)
    bytecode = pin(OUT / 'source-bytecode/outcome.json')
    assert bytecode['sha256'] == 'd0e2a91ea573e1995d78c47aca8b7915907c6c2a5019797dfed21b62a3f4795a'
    assert read(OUT / 'source-bytecode/outcome.json')['status'] == 'preserved-and-verified'
    now = datetime.now(timezone.utc)
    names = ('report_g2_launch_fixes_20261114.py', 'record_g2_final_review_20261114.py',
             'g2_legacy_leaf_reuse_6217_f4_20261114.py', 'run_g2_checks_20261114.py')
    record = {'not_acceptance_or_final_handoff': True, 'recorded_at': now.isoformat(), 'head': HEAD,
        'branch': git('branch', '--show-current'), 'status': git('status', '--short'),
        'source_test_status': git('status', '--short', '--', 'src', 'tests'),
        'active_cohort': {'name': ACTIVE, 'session': 87417, 'workers': 4, 'node': NODE,
            'command': pin(OUT / ACTIVE / 'command.json'), 'outcome_present': (OUT / ACTIVE / 'outcome.json').is_file(),
            'next_action': 'Poll/resume the existing session; do not start a duplicate. Read any newly saved outcome before proceeding.'},
        'source_state': 'F4 oracle fix committed; production unchanged by F4. Source freeze remains active during the canary.',
        'saved_cohorts': [cohort(path) for path in sorted(OUT.iterdir()) if path.is_dir() and (path / 'command.json').is_file()],
        'interrupted_final_regressions': {'outcome': pin(OUT / 'final-regressions/outcome.json'),
            'seconds': interrupted['seconds'], 'log_summary': summary[-1], 'log_passed': 25, 'log_failed': 1,
            'junit_entries': 30, 'abandoned_entries': 4, 'individual_empty_junit_passes_unconfirmed': True,
            'cleanup': pin(cleanups[-1]), 'all_observed_processes_reaped': True,
            'reason': 'Confirmed compact-versus-pretty publication witness serialization oracle defect at test line157; no runtime-hang claim.'},
        'legacy_saved_proof': {'passed': 149, 'census_nodes': 149, 'outcome': pin(OUT / 'legacy-full-serial/outcome.json'),
            'census': pin(OUT / 'legacy-collection-census/census.json'),
            'disposition': 'Retain original failed parallel run and unresolved cause. Narrow149 reuse after F4 is pending audit-agent validation; this checkpoint grants no reuse.'},
        'sealed_h2_head': '64fa2b4b7ac2d1b0767e2d89a5ca4109c945229b', 'sealed_h2_handoffs': sealed,
        'source_bytecode_preservation': bytecode,
        'review_6217_f4': pin(OUT / 'review-6217-f4.json'),
        'helper_fingerprints': [pin(ROOT / 'scripts/adhoc' / name) for name in names if (ROOT / 'scripts/adhoc' / name).is_file()],
        'helper_hash_scope': 'Point-in-time hashes; report/closure/shared validator may be under authorized revision. Revalidate final helper proofs after revisions.',
        'remaining_work': [
            {'task': 'Finish public SIGINT canary and verify retained publication/readback side effects.', 'session': 87417},
            {'task': 'Fresh zero-exit component cohort.', 'workers': 4, 'files': component},
            {'task': 'Fresh full publication and deadline files after corrected canary.', 'workers': 4,
             'files': ['tests/test_native_publication_signals.py', 'tests/test_native_attempt_deadline.py']},
            {'task': 'Fresh required engine cohort.', 'workers': 4, 'files': engine},
            {'task': 'Complete narrow legacy149/census reuse validation and F4 report/closure binding; retain original ledgers and all failed/interrupted evidence.'},
            {'task': 'Once tests idle, commit helpers, perform final audit, refresh current helper proofs, then final closure and answer-first handoff.'}],
        'constraints': ['No source/test changes or commits during active cohorts; helper bookkeeping only.',
            'No provider/native/model/host probes, CPU diagnostics, protected/pinned edits, guard-v1 changes or GitHub writes.',
            'Only primary P/.venv/bin/python; W/src PYTHONPATH; all test outputs in S2; one cohort, at most four workers.',
            'No repeated tests, restarts, signals or further bytecode moves are implied by this checkpoint.',
            'H2 handoffs and all historical review/proof artifacts remain immutable. Findings require lead filing.'],
        'handoff_paths': [str(REPORTS / ('codex-pr5968-launch-fixes-20261114.' + suffix)) for suffix in ('md', 'json')],
        'producer': pin(Path(__file__).resolve())}
    directory = OUT / 'checkpoints'
    directory.mkdir(exist_ok=True)
    path = directory / ('current-g2-after-f4-' + now.strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    raw = (json.dumps(record, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw
    print(json.dumps(pin(path)))


if __name__ == '__main__':
    main()
