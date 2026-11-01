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


def archive(ref, dest):
    commit = git('rev-parse', ref).decode().strip()
    dest.mkdir(parents=True, exist_ok=False)
    producer = subprocess.Popen(['git', 'archive', commit], cwd=ROOT, env=ENV, stdout=subprocess.PIPE)
    unpack = subprocess.run(['tar', '-x', '-C', str(dest)], stdin=producer.stdout, check=False)
    producer.stdout.close()
    assert producer.wait() == 0 and unpack.returncode == 0
    assert (dest / 'scripts/build_api_registrations.py').read_bytes() == git('show', commit + ':scripts/build_api_registrations.py')
    # Initialize the already available, exact CI submodule from local objects only.
    subref = git('ls-tree', commit, 'fairscape_models').decode().split()[2]
    local = ROOT.parent.parent / 'data-sheets-schema/fairscape_models'
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


def compare(root):
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
    rows = []
    for name, bp in before['payloads'].items():
        ap = after['payloads'][name]
        a, b = [(root / p['path']).read_bytes() for p in (bp, ap)]
        assert sha(a) == bp['sha256'] and sha(b) == ap['sha256']
        expanded = [ns['expand'](json.loads(raw)) for raw in (a, b)]
        assert all(ns['canon'](ns['collapse'](v)) == raw for v, raw in zip(expanded, (a, b)))
        leaves = ns['differences'](*expanded)
        assert sum(leaf['delta'] for leaf in leaves) == len(b) - len(a)
        rows.append({'name': name, 'before_sha256': sha(a), 'after_sha256': sha(b),
            'before_bytes': len(a), 'after_bytes': len(b), 'identical': a == b, 'differences': leaves})
    save(evidence / 'g2-exact-comparison.json', {'rows': rows, 'identical': all(r['identical'] for r in rows),
        'comparison_source_sha256': sha(source.read_bytes())})
    for row in rows:
        print(row['name'], row['identical'], row['before_sha256'], row['after_sha256'], flush=True)
    return 0 if all(r['identical'] for r in rows) else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['archive', 'proposal', 'compare'])
    parser.add_argument('path', type=Path)
    parser.add_argument('--ref', default='HEAD')
    args = parser.parse_args()
    if args.action == 'archive':
        archive(args.ref, args.path.resolve())
    elif args.action == 'proposal':
        proposal(args.path)
    else:
        raise SystemExit(compare(args.path))
