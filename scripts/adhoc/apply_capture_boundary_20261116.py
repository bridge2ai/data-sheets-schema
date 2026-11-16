"""Apply the reviewed boundary proposal for D156 and issue 6207, 2026-11-16.

Inputs: existing proposal generators and current source in this worktree.
Outputs: guard, engine and transport source edits; no pin edits or execution.
"""
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'scripts/adhoc/propose_g2_dispatch_boundary_6207_after6217_20261114.py'
spec = importlib.util.spec_from_file_location('boundary_proposal', PATH)
proposal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proposal)
base = proposal.base
changes = {
    base.GUARD: base.guard_candidate,
    base.ENGINE: proposal.engine_candidate,
    base.TRANSPORT: base.transport_candidate,
}
candidates = {name: transform((ROOT / name).read_text()).encode()
              for name, transform in changes.items()}
proposal.verify_shape(candidates)
for name, raw in candidates.items():
    previous = (ROOT / name).read_bytes()
    # Existing decorators remain; this edit introduces no prohibited character.
    assert raw.count(bytes([64])) == previous.count(bytes([64]))
    (ROOT / name).write_bytes(raw)
    assert (ROOT / name).read_bytes() == raw
    print(name)
