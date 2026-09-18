"""The new native phase rules have a distinct, replayable instruction identity."""
from dataclasses import replace

import pytest

from data_sheets_schema import api_runner as api
from tests.test_evidence_generation_gate import specification


@pytest.mark.parametrize('runtime', ['Claude Code', 'Claude API (direct)'])
def test_phase_scope_is_opted_in_and_replays_with_the_selected_arm(tmp_path, runtime):
    base = specification(tmp_path, runtime)
    old = replace(base, render_version=12)
    new = replace(base, render_version=13)
    text = new.instruction
    replay = api.RunSpec.from_render_spec(new.render_spec(), project=new.project,
                                         method=new.method, label=new.label)
    assert replay.instruction == text
    assert new.render_spec()['render_version'] == 13
    assert api.resolved_prompt_digest(new) != api.resolved_prompt_digest(old)
    assert api.assembly_digest(13) != api.assembly_digest(12)
    assert '## Evidence protocol v3' in old.instruction
    assert '## Evidence protocol v3' in text
    if new.is_agentic:
        assert api.NATIVE_PHASE1_RECEIPTS in text
        assert api.NATIVE_EVIDENCE_STOP in text
        assert 'Stop on any failed check.' not in text
        assert 'agent stopped on any failed check' not in text
        assert 'Stop on any failed check.' in old.instruction
        assert api.NATIVE_PHASE1_RECEIPTS not in old.instruction
    else:
        # This clarification does not give the API phase loop native repair
        # permissions or replace its existing terminal evidence behavior.
        assert api.NATIVE_PHASE1_RECEIPTS not in text
        assert api.NATIVE_EVIDENCE_STOP not in text
        assert 'A failed source review is terminal for this attempt' in text


def test_phase_guidance_is_part_of_the_versioned_assembly_identity(monkeypatch):
    old, new = api.assembly_digest(12), api.assembly_digest(13)
    monkeypatch.setattr(api, 'NATIVE_PHASE1_RECEIPTS', api.NATIVE_PHASE1_RECEIPTS + '\nChanged rule.\n')
    assert api.assembly_digest(13) != new
    assert api.assembly_digest(12) == old
