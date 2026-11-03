#!/usr/bin/env python3
# Purpose: recompute BC1's protected-source proposal after the pinned-main merge.
# Inputs: exact local main/D41/BC1 parents, preserved SG and the reviewed hook transformer.
# Outputs: NEW dated diff/proof; never edits SG, canonical hashes, or historical evidence.
# Refs: Wave7 reboot recovery, BC1/#5162/#5212; 2026-10-30. Offline only.
import ast
import difflib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
MAIN = '50bc50af678ae5216b3985c340fe1344da26c05e'
PACKET = 'd00acf1e7d6d485abb4776f9ffb1cd12d2640baf'
TRANSFORMER_SHA = 'ccf8ed59a509be7a0f0f4ea7d928c6b969d98bb9c1b959bb0a969793a4109651'
CANONICAL_SHA = '39b93c009457681a1d8d8b8afee5a869bbd6f5e70b6f4332522db5d7e22d0584'


def main():
    if not sys.flags.no_site or not sys.flags.dont_write_bytecode:
        raise ValueError('run proposal preparation with -S -B')
    path = ROOT / 'scripts/adhoc/prepare_wave7_bc1_shared_proposal_20261029.py'
    import hashlib
    sha = lambda raw: hashlib.sha256(raw).hexdigest()
    if sha(path.read_bytes()) != TRANSFORMER_SHA:
        raise ValueError('reviewed six-hook transformer changed')
    spec = importlib.util.spec_from_file_location('bc1_reviewed_hooks', path)
    hooks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hooks)
    head = hooks.git('rev-parse', 'HEAD').decode().strip()
    if hooks.git('status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('commit the reviewed helper before preparing the proposal')
    for ancestor in (MAIN, PACKET):
        hooks.git('merge-base', '--is-ancestor', ancestor, head)
    source = ROOT / hooks.SOURCE
    before = source.read_bytes()
    canonical = (ROOT / 'src/download/prompts/canonical_hashes.yaml').read_bytes()
    if sha(before) != hooks.BC1_SHA or sha(canonical) != CANONICAL_SHA:
        raise ValueError('protected branch source/canonical pins differ')
    original = hooks.git('show', hooks.BC1 + ':' + hooks.SOURCE)
    base = hooks.git('show', hooks.BASE + ':' + hooks.SOURCE)
    d41 = hooks.git('show', hooks.D41 + ':' + hooks.SOURCE)
    current_main = hooks.git('show', MAIN + ':' + hooks.SOURCE)
    journal = b'                "src/data_sheets_schema/latch_journal.py",\n'
    if (original != before or sha(d41) != hooks.D41_SHA or d41.count(journal) != 1
            or d41.replace(journal, b'', 1) != current_main
            or hooks.transform(original.decode(), remove=True).encode() != base):
        raise ValueError('main/D41/BC1 identity or exact parent composition differs')
    candidate = hooks.transform(d41.decode()).encode()
    if hooks.transform(candidate.decode(), remove=True).encode() != d41:
        raise ValueError('candidate does not preserve complete main plus D41')
    ast.parse(candidate)
    patch = ''.join(difflib.unified_diff(before.decode().splitlines(True), candidate.decode().splitlines(True),
        fromfile='a/' + hooks.SOURCE, tofile='b/' + hooks.SOURCE)).encode()
    if not patch or source.read_bytes() != before or (ROOT / 'src/download/prompts/canonical_hashes.yaml').read_bytes() != canonical:
        raise ValueError('empty proposal or protected source changed')
    stem = ROOT / 'notes/reviews/wave7_bc1_shared_generation_proposal_2026-10-30'
    output, proof = stem.with_suffix('.diff'), stem.with_suffix('.json')
    if output.exists() or proof.exists():
        raise ValueError('never overwrite a dated proposal/proof')
    evidence = {'format': 'wave7_bc1_protected_proposal_v2', 'date': '2026-10-30',
        'packet_head_before_proposal': head, 'protected_source': hooks.SOURCE,
        'branch_source_sha256': sha(before), 'candidate_source_sha256': sha(candidate), 'proposal_sha256': sha(patch),
        'candidate_bytes': len(candidate), 'proposal_bytes': len(patch), 'applied': False,
        'sources': {'main': MAIN, 'prior_packet': PACKET, 'bc1': hooks.BC1, 'pre_bc1': hooks.BASE, 'd41': hooks.D41},
        'd41_equals_main_plus_unique_journal_dependency': True, 'six_bc1_hooks_exact_parent_delta': True,
        'removing_hooks_yields_exact_d41_source': True, 'branch_protected_source_unchanged': True,
        'canonical_hashes_sha256': sha(canonical), 'helper_sha256': sha(Path(__file__).read_bytes()),
        'reviewed_transformer_sha256': TRANSFORMER_SHA,
        'repin': 'Only fresh private validation archive; no publication or protected branch edit.'}
    with output.open('xb') as stream:
        stream.write(patch)
    with proof.open('x') as stream:
        json.dump(evidence, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'proposal': str(output), 'proof': str(proof), **evidence}, sort_keys=True))


if __name__ == '__main__':
    main()
