#!/usr/bin/env python3
# Purpose: retain round-2 merge attribution and reproducible integration evidence.
# Inputs: pinned local heads; outputs: scratch and review JSON ledgers. Tasks 2-9,
# 2026-11-03. Offline; no protected source or historical evidence is authored.
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import bc1_g2_merge_audit_20261103 as merge_audit
import bc1_g2_bytes_20261103 as byte_proof
import bc1_g2_validate_20261103 as validation
import g2_bc1_evidence_20261101 as evidence

ROUND1 = '92a1c4afa0df9ebb361f87eab1d5fd5bc0b11054'
G1_FIXES = 'bc8f981f758c46d5bb027c61294d8a67bf70ed30'
MERGE = '2a415eb5f62c1e75474aff32e8324cfaccbb4a8a'


def audit(output):
    merge_audit.TARGET, merge_audit.INCOMING = ROUND1, G1_FIXES
    merge_audit.BASE = subprocess.check_output(
        ['git', 'merge-base', ROUND1, G1_FIXES], cwd=ROOT).decode().strip()
    merge_audit.audit(output, MERGE)
    result = json.loads(output.read_bytes())
    assert not result['unattributed'], result['unattributed']
    assert sum(row['lost_count'] for row in result['files']) == 5


def recapture(root, ref):
    """Preserve both prior captures while reusing their exact absolute root."""
    assert root == ROOT.parent / 'scratch-bc1g2/byte-proof'
    previous_commit = json.loads((root / '.g2-archive.json').read_bytes())['commit']
    previous = root.parent / 'round2' / ('capture-retained-' + previous_commit[:12])
    assert not previous.exists()
    old = json.loads((root / '.bc1-byte-evidence/integration-comparison.json').read_bytes())
    assert old['accepted']
    root.rename(previous)
    evidence.archive(ref, root)
    subprocess.run(['bash', str(byte_proof.PACKET / 'apply_protected.sh'), str(root)], check=True)
    shutil.copytree(previous / '.bc1-byte-evidence', root / '.bc1-byte-evidence')
    byte_proof.capture(root, 'round2')


def compare_pins(root):
    """Only this round's one closure pin and its derived seals may move."""
    folder = root / '.bc1-byte-evidence'
    sides = ('after', 'round2')
    evidence.compare(root, sides=sides, output_name='round2-pins-exact.json')
    result = json.loads((folder / 'round2-pins-exact.json').read_bytes())
    captures = [json.loads((folder / side / 'capture.json').read_bytes()) for side in sides]
    registrations = [json.loads((folder / side / 'registration.json').read_bytes()) for side in sides]
    old, new = registrations
    codes = [reg['bounded_carry']['contract']['code'] for reg in registrations]
    assert codes[0].keys() == codes[1].keys()
    moved = {name: {'before': codes[0][name], 'after': codes[1][name]}
             for name in codes[0] if codes[0][name] != codes[1][name]}
    assert set(moved) == {'src/data_sheets_schema/latch_journal.py'}, moved
    assert captures[0]['source_pins'].keys() == captures[1]['source_pins'].keys()
    for capture, code in zip(captures, codes):
        for name, digest in code.items():
            assert capture['source_pins'][str(root / name)]['sha256'] == digest, name
    for path, pin in captures[0]['source_pins'].items():
        if path not in {str(root / name) for name in moved}:
            assert captures[1]['source_pins'][path] == pin, ('non-code source changed', path)
    for name in moved:
        assert evidence.sha((root / name).read_bytes()) == moved[name]['after']
    normalized = copy.deepcopy(new)
    normalized['bounded_carry']['contract']['code'] = codes[0]
    stages = [reg['selection']['stage_contracts']['request_code_sha256'] for reg in registrations]
    assert stages[0].keys() == stages[1].keys()
    assert {name for name in stages[0] if stages[0][name] != stages[1][name]} == set(moved)
    for stage, code in zip(stages, codes):
        assert all(stage[name] == code[name] for name in moved)
    normalized['selection']['stage_contracts']['request_code_sha256'] = stages[0]
    assert normalized == old, byte_proof.changes(old, normalized)
    packets = []
    for capture in captures:
        host_pins = [pin['host_packet'] for name, pin in capture['payloads'].items()
                     if name.startswith('typed_audit_')]
        hosts = [json.loads((root / pin['path']).read_bytes()) for pin in host_pins]
        assert hosts and all(host == hosts[0] for host in hosts)
        packets.append(hosts[0])
    normalized_packet = copy.deepcopy(packets[1])
    for packet, reg in zip(packets, registrations):
        assert packet['selection']['bounded_carry'] == reg['bounded_carry']
        assert packet['selection']['selection'] == reg['selection']
    normalized_packet['sha256'] = packets[0]['sha256']
    normalized_packet['selection']['bounded_carry']['contract']['code'] = codes[0]
    normalized_packet['selection']['selection']['stage_contracts']['request_code_sha256'] = stages[0]
    assert normalized_packet == packets[0], byte_proof.changes(packets[0], normalized_packet, 'packet')
    allowed = {'payload/messages/0/content/5/text/@json/' + key
               for key in ('inner_request_sha256', 'packet_sha256', 'registration_sha256')}
    allowed.update({'payload/messages/0/content/6/text/@json/payload/packet_sha256',
                    'payload/messages/0/content/6/text/@json/request_sha256'})
    valid_leaves = all(row['before_bytes'] == row['after_bytes'] and all(
        leaf['path'] in allowed and leaf['kind'] == 'pins' and leaf['delta'] == 0
        and all(isinstance(leaf[side], str) and re.fullmatch('[0-9a-f]{64}', leaf[side])
                for side in ('before', 'after')) for leaf in row['differences']) for row in result['rows'])
    result.update(accepted=bool(result['sizing_totals_equal'] and valid_leaves), moved_code=moved,
                  registration_changes=byte_proof.changes(old, new),
                  host_packet_delta=byte_proof.changes(*packets, 'packet'),
                  changed_leaf_count=sum(len(row['differences']) for row in result['rows']))
    evidence.save(folder / 'round2-pin-comparison.json', result)
    assert result['accepted'], 'STOP: non-pin or sizing difference against round 1'
    print(json.dumps({key: result[key] for key in ('accepted', 'moved_code', 'changed_leaf_count')}), flush=True)


def compare(root):
    compare_pins(root)
    byte_proof.compare(root, sides=('before', 'round2'), output_name='round2-amendment.json',
                       exact_name='round2-amendment-exact.json')


def scope(output):
    previous = ROOT.parent / 'scratch-bc1g2/validation-scope.json'
    selected = json.loads(previous.read_bytes())
    touched = subprocess.check_output(['git', 'diff', '--name-only', ROUND1, 'HEAD', '--', 'tests'], cwd=ROOT)
    added = sorted(set(touched.decode().splitlines()) - set(selected['files']))
    assert all(path.endswith('.py') for path in added)
    selected['files'] = sorted([*selected['files'], *added])
    selected['groups'][11].extend(added)
    selected.update(round1_manifest_sha256=evidence.sha(previous.read_bytes()), round2_added=added)
    evidence.save(output, selected)


def batch(tree, output, manifest):
    """Serial groups, two workers each; nested-xdist CI checks run serially."""
    selected = json.loads(manifest.read_bytes())
    for index, files in enumerate(selected['groups']):
        files = [name for name in files if name != 'tests/test_ci_sharding.py']
        code = validation.run(tree, output / f'group-{index:02}', [*files, '-n', '2', '--maxschedchunk=1', '-q'])
        assert code in (0, 1), ('validation did not complete', index, code)
    for name, files, args in (
        ('ci-sharding', ['tests/test_ci_sharding.py'], ['-q']),
        ('extra', ['tests/test_neutral_generation_schema.py', 'tests/test_external_dataset_onboarding.py'],
         ['-n', '2', '--maxschedchunk=1', '-q']),
        ('collect', ['tests'], ['--collect-only', '-q'])):
        code = validation.run(tree, output / name, [*files, *args])
        assert code in (0, 1), ('validation did not complete', name, code)


def scan(tree, output):
    output.mkdir(parents=True, exist_ok=False)
    launcher = ROOT / 'scripts/adhoc/g2_bc1_offline_20261101.py'
    import os
    env = dict(os.environ, G1_CHECKOUT_ROOT=str(tree), PYTHONDONTWRITEBYTECODE='1')
    command = [sys.executable, '-S', '-B', str(launcher),
               str(tree / '.claude/skills/d4d-generation-specificity-audit/scan.py'),
               '--root', str(tree), '--report', str(output / 'audit.md'), '--json', str(output / 'audit.json')]
    with (output / 'scan.log').open('w') as log:
        result = subprocess.run(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=3600)
    reports = {name: evidence.sha((output / name).read_bytes())
               for name in ('audit.md', 'audit.json') if (output / name).is_file()}
    evidence.save(output / 'result.json', {'returncode': result.returncode, 'command': command,
        'archive': json.loads((tree / '.g2-archive.json').read_bytes()), 'reports': reports})
    print('scanner exit', result.returncode, 'reports', reports, flush=True)
    return result.returncode


def summarize(output):
    scratch = ROOT.parent / 'scratch-bc1g2/round2'
    output.mkdir(parents=True, exist_ok=True)
    units, totals = {}, {}
    for mode in ('without', 'with'):
        counts = Counter()
        for result_path in sorted((scratch / mode).glob('*/result.json')):
            unit = json.loads(result_path.read_bytes())
            assert unit['returncode'] in (0, 1), result_path
            name = str(result_path.parent.relative_to(scratch))
            target = output / name
            target.mkdir(parents=True, exist_ok=True)
            for filename in ('started.json', 'result.json', 'pytest.log', 'junit.xml', 'events.jsonl',
                             'failures.jsonl', 'collected.json'):
                source = result_path.parent / filename
                if source.is_file():
                    shutil.copyfile(source, target / filename)
            if result_path.parent.name == 'collect':
                continue
            for suite in unit['suites']:
                for key in ('tests', 'errors', 'failures', 'skipped'):
                    counts[key] += int(suite[key])
            failures = result_path.with_name('failures.jsonl')
            unit['failures'] = [json.loads(line) for line in failures.read_text().splitlines()] if failures.exists() else []
            units[name] = unit
        counts['passed'] = counts['tests'] - counts['errors'] - counts['failures'] - counts['skipped']
        totals[mode] = dict(counts)
    byte_folder = ROOT.parent / 'scratch-bc1g2/byte-proof/.bc1-byte-evidence'
    comparisons = {}
    for filename in ('round2-pin-comparison.json', 'round2-amendment.json'):
        shutil.copyfile(byte_folder / filename, output / filename)
        comparisons[filename] = json.loads((byte_folder / filename).read_bytes())
    for filename in ('merge-lost-lines.json', 'merge-preview.log', 'scope.json'):
        shutil.copyfile(scratch / filename, output / filename)
    summary = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        'commits': subprocess.check_output(['git', 'log', '--first-parent', '--format=%H %s', ROUND1 + '..HEAD'],
                                         cwd=ROOT).decode().splitlines(),
        'totals': totals, 'units': units,
        'byte_proofs': {name: {key: doc[key] for key in ('accepted', 'moved_code', 'sizing_totals_equal')}
                       for name, doc in comparisons.items()}}
    evidence.save(output / 'summary.json', summary)
    print(json.dumps(totals, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('audit', 'recapture', 'compare', 'scope', 'batch', 'scan', 'summarize'))
    parser.add_argument('output', type=Path)
    parser.add_argument('--ref')
    parser.add_argument('--tree', type=Path)
    parser.add_argument('--scope', type=Path)
    args = parser.parse_args()
    if args.action == 'recapture':
        recapture(args.output.resolve(), args.ref)
    elif args.action == 'batch':
        batch(args.tree.resolve(), args.output.resolve(), args.scope.resolve())
    elif args.action == 'scan':
        raise SystemExit(scan(args.tree.resolve(), args.output.resolve()))
    else:
        globals()[args.action](args.output.resolve())
