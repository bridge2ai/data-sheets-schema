#!/usr/bin/env python3
# Purpose: prepare pinned offline G2 archives, regenerate the protected proposal,
# and compare exact route bytes with the lead's reviewed comparison functions.
# Inputs: local git ref, archive path, retained capture.py/compare.py and BC1 helper.
# Outputs: scratch archive, proposal diff/JSON and exact byte-delta JSON.
# Assignment G2 tasks 5-7 / F1,F4,F9,N6; 2026-11-01. No network or provider calls.
import argparse
import ast
import difflib
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = 'bab865f2fcae57b639a4447c5d746a500278d73a'
ENV = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='file')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, env=ENV)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, data):
    raw = json.dumps(data, indent=2, sort_keys=True).encode() + b'\n'
    path.write_bytes(raw)
    assert path.read_bytes() == raw


def archive(ref, dest, *, refresh=False):
    commit = git('rev-parse', ref).decode().strip()
    paths = []
    if refresh:
        previous = json.loads((dest / '.g2-archive.json').read_bytes())['commit']
        changes = git('diff', '--name-status', previous, commit).decode().splitlines()
        assert all(row.startswith(('A\t', 'M\t')) for row in changes), 'refresh refuses deletions/renames'
        paths = [row.split('\t')[1] for row in changes]
        paths += ['src/data_sheets_schema/shared_generation.py']
    else:
        dest.mkdir(parents=True, exist_ok=False)
    producer = subprocess.Popen(['git', 'archive', commit, *paths], cwd=ROOT, env=ENV, stdout=subprocess.PIPE)
    unpack = subprocess.run(['tar', '-x', '-C', str(dest)], stdin=producer.stdout, check=False)
    producer.stdout.close()
    assert producer.wait() == 0 and unpack.returncode == 0
    assert (dest / 'scripts/build_api_registrations.py').read_bytes() == git('show', commit + ':scripts/build_api_registrations.py')
    # Initialize the already available, exact CI submodule from local objects only.
    subref = git('ls-tree', commit, 'fairscape_models').decode().split()[2]
    local = ROOT.parent.parent / 'data-sheets-schema/fairscape_models'
    if not refresh:
        producer = subprocess.Popen(['git', 'archive', subref], cwd=local, env=ENV, stdout=subprocess.PIPE)
        unpack = subprocess.run(['tar', '-x', '-C', str(dest / 'fairscape_models')], stdin=producer.stdout, check=False)
        producer.stdout.close()
        assert producer.wait() == 0 and unpack.returncode == 0
    save(dest / '.g2-archive.json', {'commit': commit, 'fairscape_models': subref})
    print(commit, dest, flush=True)


def proposal(output):
    helper = ROOT / 'scripts/adhoc/prepare_wave7_bc1_shared_proposal_20261029.py'
    spec = importlib.util.spec_from_file_location('g2_packet_hooks', helper)
    hooks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hooks)
    before = (ROOT / hooks.SOURCE).read_bytes()
    assert sha(before) == hooks.BC1_SHA
    candidate = hooks.transform(git('show', hooks.D41 + ':' + hooks.SOURCE).decode()).encode()
    ast.parse(candidate)
    patch = ''.join(difflib.unified_diff(before.decode().splitlines(True), candidate.decode().splitlines(True),
        fromfile='a/' + hooks.SOURCE, tofile='b/' + hooks.SOURCE)).encode()
    original = ROOT / 'notes/reviews/wave7_bc1_shared_generation_proposal_2026-10-30.diff'
    assert patch == original.read_bytes(), 'protected proposal differs: review before validation'
    output.write_bytes(patch)
    save(output.with_suffix('.json'), {'base': BASE, 'head': git('rev-parse', 'HEAD').decode().strip(),
        'proposal_sha256': sha(patch), 'branch_source_sha256': sha(before),
        'candidate_source_sha256': sha(candidate), 'unchanged_from_packet': True,
        'canonical_hashes_sha256': sha((ROOT / 'src/download/prompts/canonical_hashes.yaml').read_bytes()),
        'applied_to_branch': False, 'transformer_sha256': sha(helper.read_bytes())})
    print(output, sha(patch), sha(candidate), flush=True)


def metadata(dest):
    """Give an existing scratch archive exact, detached local Git history.

    Some ordinary-lane tests read the planning commit. No checkout, source
    mutation, branch update, remote, or copy of live worktree contents occurs.
    """
    dest = dest.resolve()
    assert dest.is_relative_to(ROOT.parent / 'scratch-g2')
    marker = json.loads((dest / '.g2-archive.json').read_bytes())
    commit = marker['commit']
    assert git('rev-parse', commit).decode().strip() == commit
    assert not (dest / '.git').exists(), 'metadata already exists'
    subprocess.run(['git', 'init', '--quiet', str(dest)], env=ENV, check=True)
    common = Path(git('rev-parse', '--git-common-dir').decode().strip())
    objects = (ROOT / common / 'objects').resolve()
    assert objects.is_dir()
    (dest / '.git/objects/info/alternates').write_text(str(objects) + '\n')
    subprocess.run(['git', '-C', str(dest), 'update-ref', '--no-deref', 'HEAD', commit],
                   env=ENV, check=True)
    subprocess.run(['git', '-C', str(dest), 'read-tree', commit], env=ENV, check=True)
    actual = subprocess.check_output(['git', '-C', str(dest), 'rev-parse', 'HEAD'], env=ENV)
    assert actual.decode().strip() == commit
    symbolic = subprocess.run(['git', '-C', str(dest), 'symbolic-ref', '-q', 'HEAD'],
                              env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert symbolic.returncode == 1, 'scratch HEAD must be detached'
    save(dest / '.g2-git-metadata.json', {'commit': commit, 'local_objects': str(objects),
        'detached': True, 'working_files_written': False})
    print(commit, 'detached local metadata', dest, flush=True)


def compare(root, *, identity_pin_ruling=False):
    # Reuse the reviewed lossless expansion and exhaustive leaf comparison.
    # Its P4a-specific schema-change assertions/report are not a G2 byte proof.
    source = ROOT / 'scripts/adhoc/g2_bc1_byte_proof/compare.py'
    module = ast.parse(source.read_text())
    prefix = []
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'before' for t in node.targets):
            break
        prefix.append(node)
    ns = {'__file__': str(source), '__name__': 'g2_reviewed_compare'}
    exec(compile(ast.Module(body=prefix, type_ignores=[]), str(source), 'exec'), ns)
    evidence = root / '.bc1-byte-evidence'
    before, after = [json.loads((evidence / name / 'capture.json').read_bytes()) for name in ('before', 'after')]
    assert not before['errors'] and not after['errors']
    assert before['payloads'].keys() == after['payloads'].keys()
    assert before['audit_limits'] == after['audit_limits'] and before['calibration'] == after['calibration']
    assert before['python'] == after['python'] and before['packages'] == after['packages']
    bindings = []
    for side, capture in (('before', before), ('after', after)):
        registration_raw = (evidence / side / 'registration.json').read_bytes()
        assert capture['registration_sha256'] == sha(registration_raw), (side, 'registration metadata')
        packet_digests = set()
        for name, metadata in capture['payloads'].items():
            if not name.startswith('typed_audit_'):
                continue
            payload = json.loads((root / metadata['path']).read_bytes())
            content = payload['messages'][0]['content']
            def embedded(index):
                text = content[index]['text']
                raw = text[text.index('{'):].encode()
                obj = json.loads(raw)
                assert ns['canon'](obj) == raw
                return obj, raw
            binding, _ = embedded(5)
            inner, inner_raw = embedded(6)
            assert binding['registration_sha256'] == sha(registration_raw), (side, name, 'registration binding')
            assert binding['inner_request_sha256'] == sha(inner_raw), (side, name, 'inner request binding')
            packet_digests.add(binding['packet_sha256'])
            if 'packet_sha256' in inner['payload']:
                assert inner['payload']['packet_sha256'] == binding['packet_sha256'], (side, name, 'packet binding')
            verified = ['registration bytes', 'content/6 inner request bytes']
            unavailable = []
            def captured_object(key):
                pin = metadata[key]
                raw = (root / pin['path']).read_bytes()
                assert sha(raw) == pin['sha256'] and len(raw) == pin['bytes'], (side, name, key)
                return json.loads(raw)
            if 'host_packet' in metadata:
                packet = captured_object('host_packet')
                assert packet['sha256'] == sha(ns['canon']({k: v for k, v in packet.items() if k != 'sha256'}))
                assert binding['packet_sha256'] == packet['sha256'], (side, name, 'captured packet')
                verified.append('captured packet seal')
            else:
                unavailable.append('packet seal: complete host packet not captured')
            if 'request_sha256' in inner:
                if 'host_request' in metadata:
                    request = captured_object('host_request')
                    assert request['request_sha256'] == sha(ns['canon'](request['payload']))
                    assert inner['request_sha256'] == request['request_sha256'], (side, name, 'captured request')
                    assert request['payload']['packet_sha256'] == binding['packet_sha256']
                    verified.append('captured host request payload hash')
                else:
                    unavailable.append('request_sha256: complete host request not captured; content/6 is its projection')
            else:
                verified.append('no host request_sha256 field (omission request)')
            bindings.append({'side': side, 'name': name, 'verified': verified, 'unverified': unavailable})
        assert len(packet_digests) <= 1, (side, 'multiple packet bindings in one capture')
    rows = []
    for name, bp in before['payloads'].items():
        ap = after['payloads'][name]
        a, b = [(root / p['path']).read_bytes() for p in (bp, ap)]
        assert sha(a) == bp['sha256'] and sha(b) == ap['sha256']
        assert len(a) == bp['bytes'] and len(b) == ap['bytes']
        expanded = [ns['expand'](json.loads(raw)) for raw in (a, b)]
        assert all(ns['canon'](ns['collapse'](v)) == raw for v, raw in zip(expanded, (a, b)))
        leaves = ns['differences'](*expanded)
        assert sum(leaf['delta'] for leaf in leaves) == len(b) - len(a)
        rows.append({'name': name, 'before_sha256': sha(a), 'after_sha256': sha(b),
            'before_bytes': len(a), 'after_bytes': len(b), 'identical': a == b, 'differences': leaves})
    sizing_totals_equal = before['sizing_totals'] == after['sizing_totals']
    accepted = all(r['identical'] for r in rows) and sizing_totals_equal
    ruling = None
    if identity_pin_ruling:
        allowed = {
            'payload/messages/0/content/5/text/@json/' + key
            for key in ('inner_request_sha256', 'packet_sha256', 'registration_sha256')}
        allowed.update({'payload/messages/0/content/6/text/@json/payload/packet_sha256',
                        'payload/messages/0/content/6/text/@json/request_sha256'})
        expected_code = {'src/data_sheets_schema/bc1_context.py',
                         'src/data_sheets_schema/bc1_registration.py'}
        reg_before, reg_after = [json.loads((evidence / name / 'registration.json').read_bytes())
                                 for name in ('before', 'after')]
        code_before = reg_before['bounded_carry']['contract']['code']
        code_after = reg_after['bounded_carry']['contract']['code']
        assert code_before.keys() == code_after.keys()
        changed_code = {name for name in code_before if code_before[name] != code_after[name]}
        assert changed_code == expected_code, changed_code
        for name in changed_code:
            for capture, pins in ((before, code_before), (after, code_after)):
                assert capture['source_pins'][str(root / name)]['sha256'] == pins[name]
        assert before['source_pins'].keys() == after['source_pins'].keys()
        for path, value in before['source_pins'].items():
            if path not in {str(root / name) for name in changed_code}:
                assert after['source_pins'][path] == value, (path, 'non-code source pin changed')
        # Registration movement must be fully explained by those exact code pins.
        registration_delta = ns['differences'](reg_before, reg_after)
        assert {leaf['path'] for leaf in registration_delta} == {
            'payload/bounded_carry/contract/code/' + name for name in changed_code}
        accepted = sizing_totals_equal and all(row['before_bytes'] == row['after_bytes'] and all(
            leaf['path'] in allowed and leaf['kind'] == 'pins' and leaf['delta'] == 0
            and isinstance(leaf['before'], str) and isinstance(leaf['after'], str)
            and re.fullmatch('[0-9a-f]{64}', leaf['before'])
            and re.fullmatch('[0-9a-f]{64}', leaf['after']) for leaf in row['differences']) for row in rows)
        ruling = {'date': '2026-11-01', 'accepted': bool(accepted),
            'changed_leaf_count': sum(len(row['differences']) for row in rows),
            'changed_code': {name: {'before': code_before[name], 'after': code_after[name]}
                             for name in sorted(changed_code)},
            'allowed_paths': sorted(allowed), 'registration_delta': registration_delta}
    save(evidence / 'g2-exact-comparison.json', {'rows': rows, 'identical': all(r['identical'] for r in rows),
        'accepted': accepted, 'binding_checks': bindings,
        'identity_pin_ruling': ruling,
        'audit_limits_before': before['audit_limits'], 'audit_limits_after': after['audit_limits'],
        'sizing_totals_equal': sizing_totals_equal,
        'registration_before_sha256': before['registration_sha256'],
        'registration_after_sha256': after['registration_sha256'],
        'comparison_source_sha256': sha(source.read_bytes())})
    for row in rows:
        print(row['name'], row['identical'], row['before_sha256'], row['after_sha256'], flush=True)
    return 0 if accepted else 1


def summary(root):
    import collections
    import xml.etree.ElementTree as ET
    document = json.loads((root / 'byte-proof/.bc1-byte-evidence/g2-exact-comparison.json').read_bytes())
    rows = document['rows']
    print('Payloads:', len(rows), 'identical:', sum(row['identical'] for row in rows))
    for row in rows:
        print(row['name'], row['before_bytes'], row['after_bytes'],
              collections.Counter(leaf['kind'] for leaf in row['differences']))
        if row['differences']:
            print('  leaves:', [leaf['path'] for leaf in row['differences']])
    print('Audit limits:', document['audit_limits_before'])
    print('Sizing totals identical:', document['sizing_totals_equal'])
    for xml in sorted(root.glob('*.xml')):
        tree = ET.parse(xml)
        print(xml.name, [suite.attrib for suite in tree.iter('testsuite')])
    for module, variable in [('shared_generation.py', 'ROUTING_CODE'), ('bc1_selection.py', 'EXTRA_CODE')]:
        tree = ast.parse(git('show', BASE + ':src/data_sheets_schema/' + module))
        value = next(node.value for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == variable for t in node.targets))
        changed = []
        for path in ast.literal_eval(value):
            old, new = git('show', BASE + ':' + path), (ROOT / path).read_bytes()
            if old != new:
                changed.append({'path': path, 'before': sha(old), 'after': sha(new)})
        print(variable, changed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['archive', 'metadata', 'proposal', 'compare', 'summary'])
    parser.add_argument('path', type=Path)
    parser.add_argument('--ref', default='HEAD')
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--identity-pin-ruling', action='store_true')
    args = parser.parse_args()
    if args.action == 'archive':
        archive(args.ref, args.path.resolve(), refresh=args.refresh)
    elif args.action == 'metadata':
        metadata(args.path)
    elif args.action == 'proposal':
        proposal(args.path)
    elif args.action == 'compare':
        raise SystemExit(compare(args.path, identity_pin_ruling=args.identity_pin_ruling))
    else:
        summary(args.path)
