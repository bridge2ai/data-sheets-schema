"""U1 #4354 2026-11-06: regenerate pins from the registry CLI scratch output.
Inputs: round-two scratch pin archive produced by native_u1_round2_20261106.py.
Outputs: proposal patch and hashes only; protected worktree stays unchanged.
"""
from native_u1_round2_20261106 import ROOT, SCRATCH, HEAD, PINS, packet, run, sha
import yaml

source=SCRATCH/('pins-'+HEAD[:9])/PINS
raw=source.read_bytes()
before=yaml.safe_load((ROOT/PINS).read_bytes())
after=yaml.safe_load(raw)
assert len(after['files']) == len(before['files'])+2
for key,value in before['files'].items():
    assert after['files'][key]==value
for name in ('generation','receipt_policy'):
    path=f'src/download/prompts/native_shared_{name}_v1.md'
    row=after['files'][path]
    assert row['pinned_at_commit']==HEAD
    assert sha(run(['git','show',HEAD+':'+path]))==row['sha256']
packet('canonical_hashes',PINS,raw,{'producer':'d4d api prompts pin in private scratch archive','existing_pins_unchanged':True})
