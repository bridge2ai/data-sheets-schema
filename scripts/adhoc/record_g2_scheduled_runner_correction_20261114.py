#!/usr/bin/env python3
# Record the one-line scheduled-runner F1 correction, 2026-11-14. Inputs:
# immutable before-driver, reviewed corrected driver, unchanged base runner.
# Outputs: immutable corrected snapshot/patch/companion in S2. Static byte
# comparison only; scheduled canary/runtime success is explicitly unverified.
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
DEST = OUT / 'scheduled-runner-review-20261114'
SOURCE = ROOT / 'scripts/adhoc/run_g2_scheduled_checks_20261114.py'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw
    return pin(path)


def main():
    assert not (DEST / 'correction.json').exists()
    before_path = DEST / 'before-driver.py'
    before, after = before_path.read_text(), SOURCE.read_text()
    old = "    subprocess.check_call(['git', 'diff', '--exit-code', 'HEAD', '--', 'src', 'tests', *inventory['selected_paths']], cwd=ROOT)\n"
    new = "    subprocess.check_call(['git', 'diff', '--exit-code', 'HEAD', '--', *SOURCE_SCOPE, *inventory['selected_paths']], cwd=ROOT)\n"
    assert before.count(old) == 1 and before.replace(old, new) == after, 'correction exceeds the reviewed one-line scope'
    base = pin(ROOT / 'scripts/adhoc/run_g2_checks_20261114.py')
    assert base['sha256'] == 'dff66b0c12df58b65c9e1a7b395cccf472bf040edbe86fec193e727b46934675'
    corrected = save(DEST / 'corrected-driver.py', after.encode())
    patch = save(DEST / 'correction.patch', ''.join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile='before-driver.py', tofile='corrected-driver.py')).encode())
    value = {'finding_id': 'G2-REVIEW-SCHEDULED-RUNNER-F1',
        'status': 'bounded correction recorded and independently reviewed; scheduled canary not yet run',
        'original_review': pin(OUT / 'review-scheduled-runner.json'),
        'before_helper': pin(before_path), 'corrected_snapshot': corrected,
        'current_driver': pin(SOURCE), 'base_runner': base, 'patch': patch,
        'static_proof': 'The entire corrected file differs by exactly the reviewed pre-run SOURCE_SCOPE expansion; all other driver bytes match.',
        'separate_review': 'No new findings; shared pre-run path checks full SOURCE_SCOPE before cohort creation or pytest invocation.',
        'scheduled_canary_required': {'cohort': 'scheduled-canary', 'workers': 4, 'cases': 1,
            'must_pass': True, 'must_persist_nonempty_case_artifacts': True},
        'runtime_verified': False, 'tests_or_canary_executed_by_this_producer': False,
        'lead_filing_required': True, 'github_write_performed': False,
        'producer': pin(Path(__file__).resolve())}
    result = save(DEST / 'correction.json', (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'correction': result, 'current_driver': pin(SOURCE)}, indent=2))


if __name__ == '__main__':
    main()
