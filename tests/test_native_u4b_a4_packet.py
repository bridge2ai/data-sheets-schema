"""D114 proposal-only byte/AST contract; no protected source edits or execution."""
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / 'scripts/adhoc/propose_native_u4b_a4_packet_20261108.py'
SPEC = importlib.util.spec_from_file_location('a4_packet_proposal', PATH)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


def test_proposal_preserves_packet_changes_and_selects_only_native_one():
    packet = b'class Spec:\n    def build(self):\n        if True:\n            self._agentic_toolchain = toolchain()\n'
    original = packet + b'# prior unpatched marker\n'
    proposed = helper.prepare(original, packet,
        {'preimage_sha256': helper.sha(original), 'postimage_sha256': helper.sha(packet)})
    assert b'prior unpatched marker' not in proposed
    namespace = {'toolchain': lambda **kwargs: kwargs}
    exec(compile(proposed, 'synthetic-packet-fixture', 'exec'), namespace)
    for version, expected in ((0, False), (1, True)):
        value = namespace['Spec']()
        value.native_shared_generation_version = version
        value.build()
        assert value._agentic_toolchain == {'native_shared': expected}


@pytest.mark.parametrize('change', ['original', 'packet', 'ambiguous'])
def test_proposal_refuses_drift_or_ambiguous_old_call(change):
    old = b'class Spec:\n    def build(self):\n        if True:\n            self._agentic_toolchain = toolchain()\n'
    metadata = {'preimage_sha256': helper.sha(old), 'postimage_sha256': helper.sha(old)}
    original, packet = old, old
    if change == 'original':
        original += b'\n'
    elif change == 'packet':
        packet += b'\n'
    else:
        packet += b'            self._agentic_toolchain = toolchain()\n'
        metadata['postimage_sha256'] = helper.sha(packet)
    with pytest.raises(ValueError):
        helper.prepare(original, packet, metadata)
