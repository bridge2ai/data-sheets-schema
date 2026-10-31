#!/usr/bin/env python3
# Purpose: verify deferred #5094 N2/N3 causal results and retained historical/copy bytes.
# Inputs: frozen baseline/canary/targeted result roots and committed VOICE source files.
# Outputs: fresh JSON summary with case counts, source identities and digests; 2026-10-28.
"""No tests, backfill application, provider calls or historical writes."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = '3f202bd3e320672fed8a49b0c4b82ef7e124a43f'
BEFORE = 'dfd0b9d4b0932cf6990971db6d70d39109e404af'
FIXED = 'de56f9dd7efc9009704dec2e24cc3378dbb24f32'
TEST = 'tests/test_wave5_5094_legacy_snapshots.py'
NODE = 'test_committed_voice_ambiguity_is_unchecked_and_preserves_prior'
VOICE = Path('data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1')
FILES = ('VOICE_provenance.yaml', 'VOICE_reconciliation.md',
         'intermediate/VOICE_audit.json', 'intermediate/VOICE_audit_2.json')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT, env=env)


def cases(path):
    result = {}
    for case in ET.parse(path / 'pytest.xml').getroot().iter('testcase'):
        key = case.get('classname') + '::' + case.get('name')
        if key in result:
            raise ValueError('duplicate test identity')
        result[key] = next((tag for tag in ('failure', 'error', 'skipped') if case.find(tag) is not None), 'passed')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'canary', 'targeted', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    sources = {}
    source_bytes = {}
    for relative in FILES:
        path = VOICE / relative
        raw = git('show', BASE + ':' + str(path))
        if (ROOT / path).read_bytes() != raw or git('show', FIXED + ':' + str(path)) != raw:
            raise ValueError('historical evidence changed: ' + str(path))
        source_bytes[relative] = raw
        sources[str(path)] = {'sha256': sha(raw), 'bytes': len(raw),
                              'git_blob': git('rev-parse', BASE + ':' + str(path)).decode().strip()}
    source_function = []
    for head in (BEFORE, FIXED):
        raw = git('show', head + ':' + TEST).decode()
        node = next(item for item in ast.parse(raw).body if isinstance(item, ast.FunctionDef) and item.name == NODE)
        source_function.append(ast.get_source_segment(raw, node))
    if source_function[0] != source_function[1]:
        raise ValueError('baseline/fixed canary function differs')

    runs = {}
    for name, head in (('baseline', BEFORE), ('canary', FIXED), ('targeted', FIXED)):
        path = getattr(args, name).resolve(strict=True)
        outcome = json.loads((path / 'outcome.json').read_text())
        plan = json.loads((path / 'plan.json').read_text())
        if plan['head'] != head or not outcome['source_unchanged'] or not outcome['origins_complete']:
            raise ValueError('source attestation failed: ' + name)
        if (path / 'source-before.json').read_bytes() != (path / 'source-after.json').read_bytes():
            raise ValueError('source inventory changed: ' + name)
        measured = cases(path)
        if name == 'baseline':
            if list(measured.values()) != ['failure'] or outcome['returncode'] != 1:
                raise ValueError('expected baseline failure not reproduced')
            log = (path / 'pytest.log').read_text()
            if not all(text in log for text in ("'raised': 'UsageLedgerError'", 'ambiguous generation ownership',
                                                "'computed_total': 21", "'stated_total': 18", "'status': 'mismatch'")):
                raise ValueError('both N2/N3 failure signatures required')
        elif not outcome['passed'] or any(value != 'passed' for value in measured.values()):
            raise ValueError('fixed run did not pass: ' + name)
        copied = list((path / 'cases').rglob('VOICE_provenance.yaml'))
        if len(copied) != 1:
            raise ValueError('expected one retained VOICE copy per run')
        copy_root = copied[0].parent
        original = yaml.safe_load(source_bytes['VOICE_provenance.yaml'])
        for entry in original['intermediates']:
            name_part = Path(entry['path']).name
            if name_part in ('VOICE_audit.json', 'VOICE_audit_2.json'):
                entry['path'] = str(copy_root / 'intermediate' / name_part)
        if yaml.safe_load(copied[0].read_text()) != original:
            raise ValueError('copied provenance changed beyond declared path rebasing')
        copy_digests = {}
        for relative in FILES:
            copied_file = copy_root / relative
            raw = copied_file.read_bytes()
            if relative != 'VOICE_provenance.yaml' and raw != source_bytes[relative]:
                raise ValueError('copied historical output changed: ' + str(copied_file))
            copy_digests[relative] = sha(raw)
        runs[name] = {'root': str(path), 'head': head, 'case_count': len(measured), 'cases': measured,
                      'outcome': outcome, 'retained_copy_sha256': copy_digests,
                      'result_sha256': {item: sha((path / item).read_bytes()) for item in
                          ('plan.json', 'outcome.json', 'pytest.xml', 'pytest.log', 'source-before.json',
                           'source-after.json', 'origins-before.json', 'origins-after.json')}}
    if set(runs['canary']['cases']) - set(runs['targeted']['cases']):
        raise ValueError('canary not included in final targeted suite')
    if runs['canary']['case_count'] != 1 or runs['targeted']['case_count'] != 100:
        raise ValueError('unexpected test case counts')
    changed = git('diff', '--name-only', BASE, FIXED, '--', 'src', '.claude', 'data',
                  'notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md').decode().splitlines()
    expected = ['src/data_sheets_schema/api_runner.py', 'src/data_sheets_schema/backfill_checks.py']
    if changed != expected or git('diff', FIXED, '--', 'src', 'tests'):
        raise ValueError('production scope or frozen tested source changed')
    summary = {'base': BASE, 'baseline_causal_head': BEFORE, 'tested_fix_head': FIXED,
               'production_changes': changed, 'canary_function_identical': True,
               'canary_function_sha256': sha(source_function[0].encode()),
               'historical_source_files': sources, 'historical_files_unchanged': True,
               'copied_provenance_changes': 'Only declared audit path rebasing; no backfill application',
               'distinct_passing_cases': 100, 'expected_baseline_failures': 1, 'runs': runs}
    with args.output.open('x') as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(str(args.output) + ' SHA256=' + sha(args.output.read_bytes()))


if __name__ == '__main__':
    main()
