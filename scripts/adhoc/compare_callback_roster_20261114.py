"""Issue 6233, 2026-11-14: compare the unchanged scanner on exact producer files.

Inputs: assignment base and current five roster producers. Outputs: bounded
source copies and JSON in assigned scratch; no scanner mutation or Git writes.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.test_generation_specificity_delegated import ROOT, scan


def main():
    scratch = Path(sys.argv[1])
    report = {}
    names = ('native_shared_stage/__init__', 'native_shared_receipts',
             'typed_audit', 'audit_omissions', 'native_shared_render')
    for label in ('base', 'current'):
        root = scratch / label
        hashes = {}
        for name in names:
            relative = 'src/data_sheets_schema/' + name + '.py'
            raw = (subprocess.check_output(['git', 'show', '6802d5987:' + relative])
                   if label == 'base' else (ROOT / relative).read_bytes())
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            assert target.read_bytes() == raw
            hashes[relative] = hashlib.sha256(raw).hexdigest()
        try:
            result = scan.derive_native_shared_procedure(root)
            report[label] = {'derived': True, 'formula': result['protocol_responses']['formula'], 'sources': hashes}
        except scan.ConfigError as error:
            report[label] = {'derived': False, 'error': str(error), 'sources': hashes}
    assert not report['base']['derived'] and report['current']['derived']
    (scratch / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
