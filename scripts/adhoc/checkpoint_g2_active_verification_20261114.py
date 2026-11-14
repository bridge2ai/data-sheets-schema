#!/usr/bin/env python3
# Reusable nonacceptance checkpoint for each G2 long run, 2026-11-14.
# Inputs: --active-cohort/--session-id, dynamic Git HEAD, saved commands/outcomes,
# current helper proof references and sealed H2 evidence. Output: exclusive
# timestamp JSON in S2/checkpoints. No project import, pytest, process inspection,
# probes, signals, source edits, commits or report/closure execution.
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
REPORTS = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs'
SCOPE = ('src', 'tests', 'notes/matched_cborg_2026-09-13', 'pyproject.toml', 'poetry.lock', 'conftest.py', '.github/workflows/main.yaml')
LEGACY = {'tests/test_native_execution.py', 'tests/test_native_receipt_origin_reporting.py'}


def pin(path):
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'stable_during_read': (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)}


def read(path):
    return json.loads(path.read_bytes())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def observation(directory, head):
    command = read(directory / 'command.json')
    argv = command['command']
    bound = all(option + str(directory / name) in argv for option, name in (
        ('--basetemp=', 'cases'), ('--junitxml=', 'pytest.xml')))
    outcome = read(directory / 'outcome.json') if (directory / 'outcome.json').is_file() else None
    changed = git('diff', '--name-only', command['head'], head, '--', *SCOPE).splitlines()
    ancestor = subprocess.run(['git', 'merge-base', '--is-ancestor', command['head'], head],
                              cwd=ROOT, capture_output=True, check=False).returncode == 0
    selectors = [arg for arg in argv if arg.startswith('tests/')]
    code = outcome['returncode'] if outcome else None
    return {'name': directory.name, 'kind': 'cohort' if bound else 'archive; not another invocation',
        'head': command['head'], 'selectors': selectors, 'argv': argv, 'outcome': outcome,
        'state': 'outcome not saved' if code is None else 'interrupted; incomplete' if code == 2
                 else 'nonzero exit; failed' if code != 0 else 'zero-exit saved run; not acceptance',
        'source_equivalence_observation': {'recorded_head_is_ancestor': ancestor, 'changed_paths': changed,
                                         'same_scoped_bytes': ancestor and not changed},
        'artifacts': [pin(directory / name) for name in ('command.json', 'outcome.json', 'pytest.xml', 'pytest.log')
                      if (directory / name).is_file()]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--active-cohort', required=True)
    parser.add_argument('--session-id', required=True, type=int)
    args = parser.parse_args()
    assert re.fullmatch(r'[a-z0-9][a-z0-9-]*', args.active_cohort) and args.session_id > 0
    head = git('rev-parse', 'HEAD')
    active = observation(OUT / args.active_cohort, head)
    assert active['kind'] == 'cohort' and read(OUT / args.active_cohort / 'command.json')['cwd'] == str(ROOT)
    cohorts = [observation(path, head) for path in sorted(OUT.iterdir())
               if path.is_dir() and (path / 'command.json').is_file()]
    selected = lambda name: read(OUT / name / 'command.json')['source_inventory']['selected_paths']
    components = [name for name in selected('final-components') if name not in LEGACY]
    engine = [name for name in selected('engine-admission') if name not in {
        'tests/test_native_attempt_deadline.py', 'tests/test_native_admission_timer.py', 'tests/test_native_pre_dispatch_timing.py'}]
    assert len(components) == 16 and len(engine) == 15
    groups = [('components', components), ('engine', engine)]
    groups += [(Path(name).stem, [name]) for name in selected('final-regressions')]
    plans = []
    for name, files in groups:
        matching = [row['name'] for row in cohorts if row['kind'] == 'cohort' and row['outcome']
                    and row['outcome']['returncode'] == 0 and row['source_equivalence_observation']['same_scoped_bytes']
                    and set(files) <= set(row['selectors'])]
        plans.append({'group': name, 'files': files, 'workers': 4,
            'zero_exit_whole_file_selection_observed': matching,
            'remaining_plan': 'Pending final audit of saved proof; do not rerun solely from this checkpoint.' if matching
                              else 'Finish active run if it selects these files; otherwise this planned group still needs coordinated verification.'})
    sealed = []
    for suffix, digest in (('md', 'c0036c97463b75f6869d5f6004b55ae6b6aace5cb8bc46890d12334d25575b20'),
                           ('json', 'c4a1b52fb3e552b4c5b6677cd4753cb3d4db37b27664539c20a48d31dac0eb68')):
        item = pin(REPORTS / ('codex-h2-integration-fixes-20261113.' + suffix))
        assert item['sha256'] == digest and item['stable_during_read']
        sealed.append(item)
    helper_paths = [ROOT / 'scripts/adhoc' / name for name in ('report_g2_launch_fixes_20261114.py',
        'record_g2_final_review_20261114.py', 'g2_legacy_leaf_reuse_6217_f4_20261114.py', 'run_g2_checks_20261114.py')]
    proof_paths = {OUT / 'legacy-leaf-reuse-6217-f4/reuse.json', OUT / 'legacy-collection-census/census.json',
                   OUT / 'review-6217-f4-confirmed.json', OUT / 'source-bytecode/outcome.json'}
    for helper in helper_paths[:2]:
        for node in ast.walk(ast.parse(helper.read_bytes())):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.endswith('/result.json'):
                relative = Path(node.value)
                if not relative.is_absolute() and '..' not in relative.parts:
                    proof_paths.add(OUT / relative)
    canary = OUT / 'publication-public-canary/cases/popen-gw0/test_public_first_signal_durin0/publication-signals/native-evidence'
    final, marker = pin(canary / 'final.json'), pin(canary / 'published.json')
    assert final['sha256'] == 'f87b665d88ee3d52cba9ddb02f942268232d812e155bea04395217bb8467ef2e'
    assert marker['sha256'] == '06dac49ce4346c67ccdd4e6fd84982262120fe530828fde23b3e705d591c32d2'
    assert read(canary / 'published.json')['final_sha256'] == final['sha256']
    now = datetime.now(timezone.utc)
    value = {'not_acceptance_or_final_handoff': True, 'recorded_at': now.isoformat(), 'head': head,
        'branch': git('branch', '--show-current'), 'working_tree_status': git('status', '--short'),
        'source_test_status': git('status', '--short', '--', 'src', 'tests'),
        'active_cohort': {**active, 'session_id': args.session_id,
            'instruction': 'Resume/poll this existing session. Read any saved outcome before proceeding; do not launch a duplicate.'},
        'saved_cohorts': cohorts, 'remaining_planned_groups': plans,
        'public_canary_side_effects': {'final': final, 'published': marker, 'marker_matches_final': True,
            'outcome': pin(OUT / 'publication-public-canary/outcome.json'), 'limit': 'One public witness; complete publication-file proof remains separately required.'},
        'sealed_h2_head': '64fa2b4b7ac2d1b0767e2d89a5ca4109c945229b', 'sealed_h2_handoffs': sealed,
        'helpers': [pin(path) for path in helper_paths],
        'proof_references': [{'path': str(path), 'present': path.is_file(), **(pin(path) if path.is_file() else {})} for path in sorted(proof_paths)],
        'evidence_scope': 'Hashes are point-in-time observations. Active files may grow; helper proofs are not re-executed or accepted by this checkpoint.',
        'retained_context': ['Production6217 remains2070; F4 oracle corrected at21367471. Legacy149/census149 reuse is limited by its exact saved validator.',
            'Original parallel legacy failures have unresolved cause. Interrupted engine194/190 and publication30/26 evidence remains incomplete.',
            '6207 proposal remains unapplied;6225 remains not fixed. Lead must file all retained review findings.'],
        'after_runs': 'When all source-bound runs are idle, review/commit remaining helpers, perform final source/protected audit, validate final proof pins, then execute closure and answer-first handoff.',
        'constraints': ['Active source-bound runs freeze HEAD/src/tests; helper-only bookkeeping is permitted.',
            'Primary P/.venv/bin/python only, W/src PYTHONPATH, S2 test outputs, one cohort at a time with at most four workers.',
            'No native/provider/model/host probes, CPU diagnostics, signals, protected/pin/guard-v1 edits, GitHub writes or new cleanup.',
            'Preserve sealed H2, all historical proofs/checkpoints, original failures and interrupted records.'],
        'handoff_paths': [str(REPORTS / ('codex-pr5968-launch-fixes-20261114.' + suffix)) for suffix in ('md', 'json')],
        'producer': pin(Path(__file__).resolve())}
    assert git('rev-parse', 'HEAD') == head, 'HEAD changed during checkpoint'
    destination = OUT / 'checkpoints' / ('current-g2-' + now.strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    destination.parent.mkdir(exist_ok=True)
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with destination.open('xb') as stream:
        stream.write(raw)
    assert destination.read_bytes() == raw
    print(json.dumps(pin(destination)))


if __name__ == '__main__':
    main()
