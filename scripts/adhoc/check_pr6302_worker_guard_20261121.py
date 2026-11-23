"""Mutate completed archive guard observations in memory, PR6302, 2026-11-21.

Inputs: successful archive-run evidence root and fresh output JSON path.
Outputs: refusal controls for worker exit status and missing finish evidence.
Original evidence stays byte-identical; this never launches a process or probe.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.adhoc import test_pr6302_round2_20261121 as runner


def main():
    root, output = map(Path, sys.argv[1:])
    root = root.resolve(strict=True)
    if Path(runner.__file__).resolve() != ROOT / 'scripts/adhoc/test_pr6302_round2_20261121.py':
        raise ValueError('guard controls imported another archive runner')
    baseline = runner._guard_results(root)
    if baseline['passed'] is not True:
        raise ValueError('guard controls require a completed successful baseline')
    targets = sorted((root / 'workers').glob('gw*/offline-guard.json'))
    if not targets:
        raise ValueError('guard controls require an actual completed xdist worker')
    target = targets[0]
    raw = target.read_bytes()
    document = json.loads(raw)
    original_read, original_is_file = Path.read_bytes, Path.is_file
    results = []
    mutations = [('absent', None), ('null', None), ('false', False), ('true', True),
                 ('float_zero', 0.0), ('text_zero', '0'), ('failed', 1), ('interrupted', 2)]
    for name, value in mutations:
        changed = deepcopy(document)
        if name == 'absent':
            changed.pop('pytest_exit_code')
        else:
            changed['pytest_exit_code'] = value
        replacement = json.dumps(changed).encode()
        def read(path):
            return replacement if path == target else original_read(path)
        with patch.object(Path, 'read_bytes', read):
            observed = runner._guard_results(root)
        if observed['passed'] is not False:
            raise ValueError('worker exit mutation was accepted: ' + name)
        results.append({'mutation': name, 'refused': True, 'problems': observed['problems']})
    def present(path):
        return False if path == target else original_is_file(path)
    with patch.object(Path, 'is_file', present):
        observed = runner._guard_results(root)
    if observed['passed'] is not False or target.parent.name not in observed['missing_process_finish']:
        raise ValueError('missing worker finish was accepted')
    results.append({'mutation': 'missing_finish', 'refused': True, 'problems': observed['problems']})
    if target.read_bytes() != raw:
        raise ValueError('guard controls changed retained worker evidence')
    record = {'baseline': str(root), 'worker_finish': str(target),
        'worker_finish_sha256': hashlib.sha256(raw).hexdigest(),
        'original_unchanged': True, 'controls': results, 'passed': True}
    with output.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
