"""Complete BC1 coverage and classify failures against the exact base, 2026-11-07.

Inputs: initial/follow-up pytest events and immutable base archive.
Outputs: exact deselection ledger, candidate continuation and base failure logs.
Only selection changes: existing test bodies and assertions remain untouched.
"""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3b'


def rows(name):
    return [json.loads(line) for line in (SCRATCH / (name + '.events.jsonl')).read_text().splitlines()]


def completed():
    return {row['nodeid'] for row in rows('bc1')
            if row['phase'] == 'call' or row['outcome'] in ('failed', 'skipped')}


def pytest_collection_modifyitems(config, items):
    """Exact node-ID matching; prefix deselection could omit unrelated tests."""
    known = completed()
    removed = [item for item in items if item.nodeid in known]
    items[:] = [item for item in items if item.nodeid not in known]
    config.hook.pytest_deselected(items=removed)


def main():
    assert 'U3B_EXIT=' in (SCRATCH / 'bc1.log').read_text(), 'Initial run must be finished'
    mode = sys.argv[1]
    if mode in ('collect', 'continue'):
        (SCRATCH / 'bc1-completed-before-followup.json').write_text(json.dumps(sorted(completed()), indent=2) + '\n')
        group = 'bc1-pending-collect' if mode == 'collect' else 'bc1-final'
        args = ['--collect-only'] if mode == 'collect' else []
        return subprocess.call([sys.executable, str(ROOT / 'scripts/adhoc/native_u3b_regressions.py'),
                                group, '-p', 'native_u3b_bc1_followup', *args], cwd=ROOT)
    if mode == 'baseline':
        assert 'U3B_EXIT=' in (SCRATCH / 'bc1-final.log').read_text(), 'Continuation must be finished'
        failed = sorted({row['nodeid'] for name in ('bc1', 'bc1-final')
                         for row in rows(name) if row['outcome'] == 'failed'})
        assert failed, 'No failures to classify'
        (SCRATCH / 'bc1-baseline-nodes.json').write_text(json.dumps(failed, indent=2) + '\n')
        return subprocess.call([sys.executable, str(ROOT / 'scripts/adhoc/validate_native_u3b.py'),
            'bc1-base-failures', '--tree', str(SCRATCH / 'base'), *failed, '-q', '--tb=short',
            '--junitxml=' + str(SCRATCH / 'bc1-base-failures.xml')], cwd=ROOT)
    raise SystemExit('Choose collect, continue or baseline')


if __name__ == '__main__':
    raise SystemExit(main())
