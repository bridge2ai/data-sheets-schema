#!/usr/bin/env python3
# Purpose: reproduce paired integrated BC1 captures and check P4a amendment v3.
# Inputs: local incoming/integrated commits, historical CHORUS bytes and reviewed
# overlays. Outputs: exact payloads and exhaustive leaf/binding evidence in scratch.
# Integration task 7, 2026-11-03. No provider, network or live protected edits.
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import g2_bc1_evidence_20261101 as evidence

OLD = '9fca277e851660ae5ccb8455505535bd0eb85925'
OLD_PATCH = ROOT.parent / 'plans/reviews/g2_bc1_shared_generation_proposal_resumed_final_2026-11-01.diff'
PACKET = ROOT.parent / 'plans/reviews/bc1_g2_integration_2026-11-03/protected'
HISTORY = ROOT.parent / ('codex-x-generality-g1/data/ATTIC/d4d_concatenated_archived/'
    'claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1/intermediate')


def changes(a, b, path='registration'):
    if a == b:
        return []
    if isinstance(a, dict) and isinstance(b, dict):
        return [row for key in sorted(set(a) | set(b))
                for row in changes(a.get(key), b.get(key), path + '/' + key)]
    return [{'path': path, 'before': a, 'after': b}]


def capture(root, side):
    launcher = ROOT / 'scripts/adhoc/g2_bc1_offline_20261101.py'
    env = dict(os.environ, G1_CHECKOUT_ROOT=str(root), G2_BC1_ARCHIVE=str(HISTORY))
    env.pop('D4D_MANIFEST', None)
    with (root.parent / ('capture-' + side + '.log')).open('w') as log:
        subprocess.run([sys.executable, '-S', '-B', str(launcher),
            str(root / 'scripts/adhoc/g2_bc1_byte_proof/capture.py'), side], cwd=root,
            env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=3600)
    doc = json.loads((root / '.bc1-byte-evidence' / side / 'capture.json').read_bytes())
    assert not doc['errors'] and len(doc['payloads']) == 20
    for pin in doc['payloads'].values():
        raw = (root / pin['path']).read_bytes()
        assert raw and len(raw) == pin['bytes'] and evidence.sha(raw) == pin['sha256']
    reg = json.loads((root / '.bc1-byte-evidence' / side / 'registration.json').read_bytes())
    # Extend evidence only: verify every closure file, including final D41's
    # latch_journal and G1 modules that the original six-file observer omitted.
    for name, digest in reg['bounded_carry']['contract']['code'].items():
        raw = (root / name).read_bytes()
        assert evidence.sha(raw) == digest, name
        doc['source_pins'][str(root / name)] = {'sha256': digest, 'bytes': len(raw)}
    evidence.save(root / '.bc1-byte-evidence' / side / 'capture.json', doc)
    print(side, len(doc['payloads']), 'nonempty payloads verified', flush=True)


def pair(root, ref):
    evidence.archive(OLD, root)
    assert evidence.sha(OLD_PATCH.read_bytes()) == '274411de3448c32be0600bec33fd794bce747e24bffa7eff6dede01eb568c719'
    subprocess.run(['git', 'apply', str(OLD_PATCH)], cwd=root, check=True)
    capture(root, 'before')  # End-to-end capture canary before replacing any input.
    retained = root.with_name(root.name + '-before-retained')
    assert not retained.exists()
    root.rename(retained)
    evidence.archive(ref, root)
    subprocess.run(['bash', str(PACKET / 'apply_protected.sh'), str(root)], check=True)
    shutil.copytree(retained / '.bc1-byte-evidence', root / '.bc1-byte-evidence')
    capture(root, 'after')


def compare(root):
    # Includes exact registration, packet, request and host-to-model bindings;
    # the identity-only verdict is not used for this declared schema amendment.
    evidence.compare(root)
    folder = root / '.bc1-byte-evidence'
    result = json.loads((folder / 'g2-exact-comparison.json').read_bytes())
    captures = [json.loads((folder / side / 'capture.json').read_bytes()) for side in ('before', 'after')]
    registrations = [json.loads((folder / side / 'registration.json').read_bytes()) for side in ('before', 'after')]
    before, after = registrations
    old_code, new_code = [reg['bounded_carry']['contract']['code'] for reg in registrations]
    assert old_code.keys() == new_code.keys()
    moved = {name: {'before': old_code[name], 'after': new_code[name]} for name in old_code
             if old_code[name] != new_code[name]}
    for side, code, capture_doc in zip(('before', 'after'), (old_code, new_code), captures):
        for name, digest in code.items():
            assert capture_doc['source_pins'][str(root / name)]['sha256'] == digest, (side, name)
    assert captures[0]['source_pins'].keys() == captures[1]['source_pins'].keys()
    for path, old_pin in captures[0]['source_pins'].items():
        if path not in {str(root / name) for name in moved} and '/src/data_sheets_schema/schema/' not in path:
            assert captures[1]['source_pins'][path] == old_pin, ('unexpected source change', path)
    # Only captured schema pins and code closure pins may move registration.
    import copy
    normalized = copy.deepcopy(after)
    normalized['bounded_carry']['contract']['code'] = old_code
    old_stage, new_stage = [reg['selection']['stage_contracts']['request_code_sha256'] for reg in registrations]
    assert old_stage.keys() == new_stage.keys()
    for stage, code in ((old_stage, old_code), (new_stage, new_code)):
        assert all(code[name] == digest for name, digest in stage.items() if name in code), 'stage code differs from verified closure'
    assert all(new_stage[name] == digest for name, digest in old_stage.items() if name not in old_code), 'non-closure stage code moved'
    normalized['selection']['stage_contracts']['request_code_sha256'] = old_stage
    for name in ('full_schema', 'core_schema'):
        normalized['inputs'][name] = before['inputs'][name]
    unexplained = changes(before, normalized)
    result.update(accepted=False, moved_code=moved, registration_changes=changes(before, after),
                  unexplained_registration_changes=unexplained)
    evidence.save(folder / 'integration-comparison.json', result)
    assert not unexplained, ('registration change outside schema/code pins', unexplained)
    failures = []
    for row in result['rows']:
        name = row['name']
        expected = (624 if name.startswith('typed_audit_') else
                    135 if name in ('full', 'full_receipt_completion') else 324)
        delta = row['after_bytes'] - row['before_bytes']
        wanted = (Counter({'description_full': 1, 'description_core': 1,
                           'termSources_full': 1, 'termSources_core': 1})
                  if expected == 624 else Counter({'digest': 1, **({'description_full': 1} if expected == 324 else {})}))
        actual = Counter(leaf['kind'] for leaf in row['differences'] if leaf['kind'] != 'pins')
        if delta != expected or actual != wanted:
            failures.append({'name': name, 'delta': delta, 'expected': expected, 'kinds': dict(actual)})
        for leaf in row['differences']:
            kind = leaf['kind']
            required = 0 if kind == 'pins' else 135 if kind == 'digest' else 189 if kind.startswith('description_') else 123
            if leaf['delta'] != required or kind == 'other':
                failures.append({'name': name, 'leaf': leaf})
            if kind == 'pins':
                a, b = leaf['before'], leaf['after']
                valid = (isinstance(a, str) and isinstance(b, str) and len(a) == len(b)
                         and len(a) in (32, 64) and re.fullmatch('[0-9a-f]+', a)
                         and re.fullmatch('[0-9a-f]+', b))
                valid = valid or (leaf['path'].endswith('/bytes') and type(a) is int and type(b) is int)
                if not valid:
                    failures.append({'name': name, 'invalid_identity_leaf': leaf})
            if kind.startswith('termSources_') and (leaf['before'] is not None or leaf['after'] != {
                'd4d:termSources': {'tag': 'd4d:termSources', 'value': 'EDAM Data, EDAM Format, IANA media types'}}):
                failures.append({'name': name, 'unexpected_annotation': leaf})
    result.update(accepted=not failures, amendment='P4a amendment 1 v3', moved_code=moved,
                  amendment_failures=failures,
                  sizing_note='Expected schema growth is accounted per payload; identical sizing totals are not claimed.')
    evidence.save(folder / 'integration-comparison.json', result)
    print(json.dumps({'accepted': not failures, 'moved_code': moved, 'failures': failures}, indent=2))
    assert not failures, 'STOP: difference outside the approved schema amendment'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('pair', 'compare'))
    parser.add_argument('root', type=Path)
    parser.add_argument('--ref')
    args = parser.parse_args()
    pair(args.root.resolve(), args.ref) if args.action == 'pair' else compare(args.root.resolve())
