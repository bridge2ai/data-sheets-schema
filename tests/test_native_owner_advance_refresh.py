"""Same-callback reconstruction ordering for #4354, 2026-10-20.

Inputs: explicit adapter boundary spies; output: offline ordering assertions.
No real owner admission or native compatibility is claimed. The actual
_observe/_phase_state code runs; _run is a counted capture boundary and phase
consumers are spies. The real settlement entry is used for the refusal case.
"""
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema.native_shared_controller import CallbackAdapter


class FixtureStop(RuntimeError):
    pass


def prepare(monkeypatch, *, selected, failure=None):
    adapter = object.__new__(CallbackAdapter)
    adapter.failure = None
    adapter._activated = adapter._initialized = True
    adapter._phase_cache = None
    adapter.recorder_call = None
    adapter.recorder_done = False
    adapter.policy = {'native_shared_helpers': {
        'advance': 'fixed advance', 'final_evidence': 'different final helper',
    }}
    adapter.controls = {'budgeted_cborg': SimpleNamespace(BudgetStop=FixtureStop)}
    owner = object() if selected else None
    endpoints = (101, 202)
    events, runs = [], []
    changed = [False]
    trace = SimpleNamespace(calls={'advance-1': (1, 0, {
        'name': 'Bash', 'input': {'command': 'fixed advance'},
    })})

    def observed(event, *, owner_context=None):
        assert owner_context is owner
        return endpoints

    def reconstructed(actual, *, owner_context=None):
        assert actual == endpoints and owner_context is owner
        events.append(('capture', len(runs) + 1))
        if changed[0]:
            raise ValueError('injected changed source after settlement')
        number = len(runs) + 1
        run = SimpleNamespace(number=number, trace=lambda: trace,
                              decision=lambda: 'decision-' + str(number))
        runs.append(run)
        return run

    def phase(event, *, stage_decision):
        events.append(('phase', stage_decision))
        return []

    def state(event, **kwargs):
        events.append(('state',))

    def settled(run, identity):
        assert identity == 'advance-1'
        events.append(('settled', run.number))
        if failure == 'post_settlement':
            changed[0] = True

    adapter._observed_endpoint = observed
    adapter._run = reconstructed
    adapter.phase = SimpleNamespace(observe=phase)
    adapter.state = SimpleNamespace(observe=state, report=lambda: {'problems': []})
    adapter._final_unchanged = lambda run: events.append(('final', run.number))
    if failure == 'settlement_guard':
        # Keep the real observe_advance_settled entry. Its first authority
        # boundary must reject before trace interpretation or publication.
        def refused(run):
            events.append(('settlement_guard', run.number))
            raise ValueError('injected changed owner at settlement')
        monkeypatch.setattr(capture, '_require_run_effect', refused)
    else:
        monkeypatch.setattr(capture, 'observe_advance_settled', settled)
    event = {'type': 'user', 'message': {'content': [
        {'type': 'tool_result', 'tool_use_id': 'advance-1'},
    ]}}
    return adapter, owner, event, events, runs


@pytest.mark.parametrize('selected', [False, True])
def test_settled_advance_retains_fresh_selected_capture_and_default_refresh(monkeypatch, selected):
    adapter, owner, event, events, runs = prepare(monkeypatch, selected=selected)
    adapter._observe(event, owner_context=owner)
    before = 1 if selected else 2
    total = before + 1
    assert len(runs) == total
    assert events == (
        [('capture', number) for number in range(1, before + 1)]
        + [('settled', before), ('capture', total), ('phase', 'decision-' + str(total)),
           ('state',), ('final', total)])
    if selected:
        assert adapter._phase_cache is None
    else:
        assert adapter._phase_cache == (runs[-1], 'decision-' + str(total))


@pytest.mark.parametrize('selected', [False, True])
@pytest.mark.parametrize('failure', ['settlement_guard', 'post_settlement'])
def test_settlement_and_post_settlement_refusals_precede_phase_credit(monkeypatch, selected, failure):
    adapter, owner, event, events, runs = prepare(monkeypatch, selected=selected, failure=failure)
    message = 'changed owner at settlement' if failure == 'settlement_guard' else 'changed source after settlement'
    with pytest.raises(FixtureStop, match=message):
        adapter._observe(event, owner_context=owner)
    before = 1 if selected else 2
    expected = [('capture', number) for number in range(1, before + 1)]
    expected += ([('settlement_guard', before)] if failure == 'settlement_guard' else
                 [('settled', before), ('capture', before + 1)])
    assert events == expected
    assert len(runs) == before
