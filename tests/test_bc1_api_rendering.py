"""Model/host carry boundary under explicitly simulated BC1 hooks, offline."""
from copy import deepcopy

from data_sheets_schema import api_runner as api, bc1_audit, bc1_codec, bc1_runtime
from tests.test_bc1_selection import external, simulated_hooks, registered  # noqa: F401


def test_downstream_uses_exact_projection_and_keeps_complete_host_carry(registered, monkeypatch):
    spec = registered
    spec.bind_api_header_values(api._model_settings(spec.condition))
    full = 'name: Example\n'
    complete = '{"findings":[],"source_review":{"complete_host_only":"retain"}}'
    projected = bc1_codec.encode_candidate({'kind': 'ConcernPacketV1', 'findings': []},
        dictionary=bc1_codec.build_dictionary(chunks={})).decode()
    seen = []
    def checked_projection(selected, text):
        assert selected is spec and text == complete
        seen.append(text)
        return projected
    monkeypatch.setattr(bc1_runtime, 'model_carry', checked_projection)
    carry = {'Completed full record': full, 'Audit findings': complete}
    original = deepcopy(carry)
    request = api.build_phase(spec, 'reconcile_full', carry=carry)
    blocks = [part['text'] for message in request.messages for part in message['content']
              if part['type'] == 'text']
    assert seen == [complete] and carry == original
    assert sum(projected in block for block in blocks) == 1
    assert all(complete not in block for block in blocks)
    contract = bc1_codec.canonical(bc1_audit.downstream_contract()).decode()
    assert blocks.count(contract) == 1
    assert any('BC1 COMPLETE CAPTURED SCHEMA CONTEXT' in block for block in blocks)
    assert all(type(block) is str for block in blocks)


def test_new_assembly_condition_has_distinct_identity_without_changing_old_default():
    args = dict(shared_generation_version=1, api_playbook_version=2, receipt_completion_version=2)
    old = api.assembly_digest(25, **args)
    assert api.assembly_digest(25, bounded_carry_version=0, **args) == old
    assert api.assembly_digest(25, bounded_carry_version=1, **args)['sha256'] != old['sha256']
