"""Inventory native model-label consumers including ignored files, 2026-11-19.

Inputs: assigned checkout src, tests, scripts and notes trees.
Outputs: retained rg matches plus source changes and protected-file comparison.
Serves the native CLI model-label amendment; read-only outside its scratch output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = 'e7721b603763ec131540c5e1a8a1d4ab16df5a1c'
PROTECTED = ('src/data_sheets_schema/shared_generation.py',
             'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml',
             'tests/utils/run_spec_boundary_contracts.json')
PATTERNS = {
    'requested_label_reads': r"(?:pair|aliases)\[['\"]requested['\"]\]",
    'runtime_label_reads': r"(?:modelUsage|init|model_accounting).*runtime\[['\"]model['\"]\]",
    'alias_consumers': r"model_aliases\(|require_frame_models\(|require_model_usage\(|reported_model\(",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    record = dict(root=str(ROOT), base=BASE, ignored_and_hidden_included=True,
                  scopes=['src', 'tests', 'scripts', 'notes'], searches={}, protected={})
    for name, pattern in PATTERNS.items():
        command = ['rg', '--hidden', '--no-ignore', '--line-number', '--glob', '*.py',
                   pattern, *record['scopes']]
        result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr.decode())
        path = args.output / (name + '.txt')
        path.write_bytes(result.stdout)
        record['searches'][name] = dict(command=command, returncode=result.returncode,
            matches=len(result.stdout.splitlines()), path=str(path),
            sha256=hashlib.sha256(result.stdout).hexdigest())
    for name in PROTECTED:
        before = subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT)
        after = (ROOT / name).read_bytes()
        record['protected'][name] = dict(base_sha256=hashlib.sha256(before).hexdigest(),
            current_sha256=hashlib.sha256(after).hexdigest(), unchanged=before == after)
    record['changed'] = subprocess.check_output(
        ['git', 'diff', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
    (args.output / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(str(args.output / 'result.json'))
    print(json.dumps({name: row['matches'] for name, row in record['searches'].items()}))
    if not all(row['unchanged'] for row in record['protected'].values()):
        raise SystemExit('protected source changed')


if __name__ == '__main__':
    main()
