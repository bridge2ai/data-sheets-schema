"""Same-capture effect views keep genuine stage and event checks.

Synthetic native frames populate the real tiny-schema capture. No native/model
process is run. The full parent return is the oracle, including spent-response
and protected-output effects, and public calls retain fresh reconstruction.
"""
from collections import Counter
from dataclasses import FrozenInstanceError

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_effects as effects
from data_sheets_schema import native_shared_stage as stage
from tests.test_native_shared_observation_replay import (
    worker_run, offline, native_spec, basic_native_spec, basic_declaration,
    declaration, started, execution, bound)

_PARENT = 'def current_effect_view(run, *, correction_window=False, exclude_pending=None):\n    """Derive the restrictive overlay solely from captured state and events."""\n    decision = run.decision()\n    state = decision.state if decision is not None else \'request_ready\'\n    request = decision.request if decision is not None else None\n    response = decision.response if decision is not None else None\n    read = intent = None\n    if decision is not None and state == \'awaiting_response\':\n        for item in run.observations:\n            doc = _document(item.raw, \'stage observation\'); payload = doc[\'payload\']\n            if payload.get(\'history_sha256\') != run.history.journal.pin.sha256:\n                continue\n            if doc[\'observation_type\'] == \'request_read\' and payload[\'request\'] == c.pin_dict(request.pin):\n                read = item.pin.sha256\n            elif doc[\'observation_type\'] == \'response_intent\' and payload[\'request\'] == c.pin_dict(request.pin):\n                intent = item.pin.sha256\n        # A consumed response remains spent even after journal advancement.\n        request_hash = c.strict_json(request.raw, max_bytes=run.selection.bounds()[\'max_request_bytes\'])[\'request_sha256\']\n        for row in stage._history(run.selection, run.binding, run.history)[0]:\n            if row[\'record_type\'] == \'response_consumed\' and row[\'payload\'][\'request_sha256\'] == request_hash:\n                pin = row[\'payload\'][\'response_observation\']\n                intent = pin[\'sha256\']\n    protected = list(run.selection.roles)\n    protected += [c.RolePath(\'authority_\' + str(index), path) for index, path in enumerate(\n        run.composition[\'policy\'][\'readonly_lookups\'][\'inputs\']) if path not in {role.path for role in protected}]\n    if run.phase1 is not None:\n        protected.append(c.RolePath(\'sealed_original_receipt_output\', run.spec._agentic_artifact_paths[\'receipt\']))\n    pending = [identity for identity in run.trace().pending() if identity != exclude_pending\n               and run.trace().calls[identity][2].get(\'input\', {}).get(\'command\') == run.composition[\'policy\'][\'native_shared_helpers\'][\'advance\']]\n    if len(pending) > 1:\n        raise ValueError(\'overlapping selected advance effects\')\n    return c.NativeEffectView(correction_window=correction_window, cursor=None if decision is None else decision.cursor,\n        execution_binding_sha256=run.binding.binding_artifact.pin.sha256, history_sha256=run.history.journal.pin.sha256,\n        pending_advance_tool_use_id=pending[0] if pending else None, protected_roles=tuple(protected),\n        protocol=c.NAME, request=None if request is None else request.pin,\n        request_read_observation_sha256=read, response=response, response_intent_observation_sha256=intent,\n        sealed=() if decision is None else decision.sealed, selection_sha256=run.selection.registration.pin.sha256,\n        stage_command=run.composition[\'policy\'][\'native_shared_helpers\'][\'advance\'], stage_root=run.selection.role(\'stage_root\'),\n        state=state, static_policy_sha256=run.composition[\'policy_sha256\'], working_directory=run.binding.working_directory)'
_PARENT_SHA = 'f0162a4b9c6108301b65bb73cc4453b034138f32a4498cc6a25cf8a24588adf1'


def parent_view():
    assert c.sha(_PARENT.encode()) == _PARENT_SHA
    namespace = dict(capture.__dict__)
    exec(compile(_PARENT, '<current_effect_view at 43fa317d>', 'exec'), namespace)
    return namespace['current_effect_view']


def test_same_stack_reuses_decision_and_preserves_full_view_and_effects(worker_run, monkeypatch):
    owner = ['parent']; decisions = Counter(); packets = Counter()
    decide, packet = capture._CapturedRun.decision, stage._Replay._packet
    def counted_decision(run):
        decisions[owner[0]] += 1
        return decide(run)
    def counted_packet(*args, **kwargs):
        packets[owner[0]] += 1
        return packet(*args, **kwargs)
    monkeypatch.setattr(capture._CapturedRun, 'decision', counted_decision)
    monkeypatch.setattr(stage._Replay, '_packet', counted_packet)
    inputs = (worker_run.selection, worker_run.binding, worker_run.phase1,
              worker_run.history, worker_run.observations, worker_run.transcript, worker_run.control)
    for correction in (False, True):
        owner[0] = 'parent'
        first = worker_run.decision()
        expected = parent_view()(worker_run, correction_window=correction)
        owner[0] = 'candidate'
        current = worker_run.decision()
        actual = capture._effect_view_from_decision(worker_run, current, correction_window=correction)
        assert current == first and actual == expected
        assert type(actual) is c.NativeEffectView
        assert actual.response_intent_observation_sha256 is not None
        for target in (current.response.path, worker_run.selection.registration.pin.path):
            kwargs = {'tool_name': 'Write', 'tool_input': {'file_path': target, 'content': '{}'}}
            assert effects.classify_effect(actual, **kwargs) == effects.classify_effect(expected, **kwargs)
            assert effects.classify_effect(actual, **kwargs)[0] != 'prescribed'
        with pytest.raises(FrozenInstanceError):
            actual.state = 'assembly_complete'
    assert decisions == {'parent': 4, 'candidate': 2}
    assert packets == {'parent': 4, 'candidate': 2}
    assert inputs == (worker_run.selection, worker_run.binding, worker_run.phase1,
                      worker_run.history, worker_run.observations, worker_run.transcript, worker_run.control)


def test_public_view_reconstructs_and_preserves_first_error_each_time(worker_run, monkeypatch):
    expected = parent_view()(worker_run)
    assert capture.current_effect_view(worker_run) == expected
    calls = []
    def changed(run):
        calls.append(run)
        raise ValueError('changed captured stage refuses')
    monkeypatch.setattr(capture._CapturedRun, 'decision', changed)
    for function in (parent_view(), capture.current_effect_view, capture.current_effect_view):
        with pytest.raises(ValueError, match='^changed captured stage refuses$'):
            function(worker_run)
    assert calls == [worker_run] * 3


def test_public_view_has_no_caller_supplied_decision(worker_run):
    current = worker_run.decision()
    for function in (parent_view(), capture.current_effect_view):
        with pytest.raises(TypeError, match='unexpected keyword argument'):
            function(worker_run, decision=current)
