"""U4b addendum 2 model-label checks, 2026-11-08; no native/provider runs.

The saved historical transcript demonstrates labels, not current account or
execution acceptance. Genuine saved-permission consumers below see fabricated
observations; the gate fixture intentionally lacks the other thirteen gates.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import time
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_gate_engine as engine
from data_sheets_schema import native_model_aliases as subject
from data_sheets_schema import native_permission_probe as producer
from data_sheets_schema import native_probe_provider as provider
from data_sheets_schema import native_shared_contract as c
from tests.test_native_shared_gates import isolated_modules, pure_gate_members
from tests.test_native_shared_permissions import (
    fixture, get, put, put_rows, rows, verify, prohibit_real_transports,
    permission_orchestration, loaded_consumer,
)
from tests.utils.native_shared_consumer_scope import observe_consumer_calls


def runtime():
    return {'model': subject.REQUESTED, 'auxiliary_models': [],
            'limits_basis': json.dumps({'kind': subject.KIND, 'version': 2,
                'model_aliases': {'requested': subject.REQUESTED, 'returned': subject.RETURNED}})}


def test_exact_declared_pair_is_detached_and_has_no_prefix_inference():
    selected = runtime()
    original = deepcopy(selected)
    aliases = subject.model_aliases(selected)
    assert aliases == {'requested': 'claude-opus-5[1m]', 'returned': 'claude-opus-5'}
    aliases['returned'] = 'changed'
    assert selected == original
    assert subject.model_aliases(selected)['returned'] == subject.RETURNED


@pytest.mark.parametrize('change', ['missing_basis', 'text_basis', 'malformed_basis',
    'duplicate_key', 'missing_kind', 'wrong_kind', 'missing_version', 'old_version',
    'bool_version', 'missing_pair', 'extra_pair_field', 'swapped_pair', 'returned_requested',
    'wrong_requested', 'null_returned', 'wrong_model', 'auxiliary'])
def test_undeclared_or_changed_current_pair_refuses(change):
    selected = runtime()
    basis = json.loads(selected['limits_basis'])
    if change == 'missing_basis':
        del selected['limits_basis']
    elif change == 'text_basis':
        selected['limits_basis'] = 'legacy text cannot replace the current declaration'
    elif change == 'malformed_basis':
        selected['limits_basis'] = '{'
    elif change == 'duplicate_key':
        selected['limits_basis'] = selected['limits_basis'].replace('"version": 2', '"version": 2, "version": 2')
    else:
        if change == 'missing_kind': del basis['kind']
        elif change == 'wrong_kind': basis['kind'] = 'other'
        elif change == 'missing_version': del basis['version']
        elif change == 'old_version': basis['version'] = 1
        elif change == 'bool_version': basis['version'] = True
        elif change == 'missing_pair': del basis['model_aliases']
        elif change == 'extra_pair_field': basis['model_aliases']['fallback'] = 'other'
        elif change == 'swapped_pair': basis['model_aliases'] = {'requested': subject.RETURNED, 'returned': subject.REQUESTED}
        elif change == 'returned_requested': basis['model_aliases']['returned'] = subject.REQUESTED
        elif change == 'wrong_requested': basis['model_aliases']['requested'] = subject.REQUESTED + '-new'
        elif change == 'null_returned': basis['model_aliases']['returned'] = None
        elif change == 'wrong_model': selected['model'] = subject.RETURNED
        elif change == 'auxiliary': selected['auxiliary_models'] = ['another-model']
        selected['limits_basis'] = json.dumps(basis)
    with pytest.raises(ValueError):
        subject.model_aliases(selected)


@pytest.mark.parametrize('basis', [None, 'historical text', '{not previously interpreted', '{}'])
def test_other_historical_models_retain_identity_label_behavior(basis):
    selected = {'model': 'other-historical-model', 'limits_basis': basis,
                'environment': {'CLAUDE_CODE_DISABLE_1M_CONTEXT': '0'}}
    aliases = subject.model_aliases(selected)
    assert aliases == {'requested': selected['model'], 'returned': selected['model']}
    subject.require_frame_models({'type': 'assistant', 'message': {}}, aliases)
    subject.require_model_usage({}, aliases)


@pytest.mark.parametrize('kind,expected', [('system', subject.REQUESTED),
                                          ('assistant', subject.RETURNED), ('result', subject.REQUESTED)])
def test_roles_admit_only_their_exact_label(kind, expected):
    aliases = subject.model_aliases(runtime())
    event = {'type': kind, 'model': expected, 'message': {'model': expected}}
    subject.require_frame_models(event, aliases)
    for other in {subject.REQUESTED, subject.RETURNED, 'other', expected + '-latest', None} - {expected}:
        for target in ('frame', 'message'):
            changed = deepcopy(event)
            (changed if target == 'frame' else changed['message'])['model'] = other
            with pytest.raises(ValueError, match='model alias'):
                subject.require_frame_models(changed, aliases)
    if kind == 'assistant':
        with pytest.raises(ValueError, match='lacks'):
            subject.require_frame_models({'type': kind, 'message': {}}, aliases)


@pytest.mark.parametrize('usage', [None, {}, {subject.RETURNED: {}},
    {subject.REQUESTED: None}, {subject.REQUESTED: {}, 'auxiliary-model': {}}])
def test_terminal_usage_requires_requested_identity_without_auxiliary(usage):
    aliases = subject.model_aliases(runtime())
    subject.require_model_usage({'modelUsage': {subject.REQUESTED: {}}}, aliases)
    with pytest.raises(ValueError, match='modelUsage'):
        subject.require_model_usage({'modelUsage': usage}, aliases)


def test_retained_historical_labels_are_checked_without_claiming_full_acceptance():
    path = Path(__file__).resolve().parents[1] / (
        'notes/reference_rescore_2026-09-11/attempts/AI_READI_v7_rep1_r10_rating1/'
        '2026-09-12T08-05-41.050919+00-00/transcript.jsonl')
    raw = path.read_bytes()
    events = [json.loads(line) for line in raw.splitlines() if line]
    initial = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
    assistants = [e for e in events if e.get('type') == 'assistant']
    terminal = [e for e in events if e.get('type') == 'result']
    assert len(initial) == len(terminal) == 1 and len(assistants) == 25
    aliases = subject.model_aliases(runtime())
    assert initial[0]['model'] == aliases['requested']
    for event in [*initial, *assistants, *terminal]:
        subject.require_frame_models(event, aliases)
    assert {e['message']['model'] for e in assistants} == {aliases['returned']}
    assert set(terminal[0]['modelUsage']) == {aliases['requested'], 'claude-haiku-4-5-20251001'}
    # The CBORG historical run has auxiliary usage. Retain and refuse it under
    # this current empty-auxiliary policy; do not erase it to manufacture a pass.
    with pytest.raises(ValueError, match='modelUsage'):
        subject.require_model_usage(terminal[0], aliases)
    assert path.read_bytes() == raw


def current_stream(tmp_path):
    from tests.test_native_execution_gates import selected
    prepared, old_runtime = selected()
    chosen = {**old_runtime, **runtime(), 'effort': 'high',
        'limits': {'contextWindow': 1_000_000, 'maxOutputTokens': 64_000},
        'attempt_directory': str(tmp_path), 'budget_guard_usd': '90'}
    prepared['events'][0]['model'] = subject.REQUESTED
    prepared['events'][0]['permissionMode'] = 'dontAsk'
    prepared['events'][-1]['subtype'] = 'success'
    prepared['events'][1]['message']['model'] = subject.RETURNED
    prepared['events'][-1].update(total_cost_usd=0.01,
        usage={'input_tokens': 1, 'output_tokens': 1, 'cache_read_input_tokens': 0,
               'cache_creation_input_tokens': 0},
        modelUsage={subject.REQUESTED: {**chosen['limits'], 'inputTokens': 1, 'outputTokens': 1,
                    'cacheReadInputTokens': 0, 'cacheCreationInputTokens': 0}})
    control = tmp_path / 'control.jsonl'
    control.write_bytes(c.canonical({'kind': 'decision', 'request': {
        'request': {'input': {'effort': {'level': 'high'}}}}}) + b'\n')
    prepared['snapshot'] = SimpleNamespace(path=lambda path: path)
    return prepared, chosen, {str(control): control}


def gate_result(prepared, runtime, projections, controls):
    return engine.check(prepared, projections, runtime, controls, kind='native_shared',
        exit_code=0, shutdown=None, live={}, first_stop=None,
        runtime_authority={'passed': False}, keep_awake={'passed': False})


def test_real_terminal_and_accounting_gates_keep_alias_roles_separate(tmp_path, pure_gate_members):
    prepared, chosen, projections = current_stream(tmp_path)
    result = gate_result(prepared, chosen, projections, pure_gate_members)
    assert result['terminal']['passed'] is result['accounting']['passed'] is True
    assert len(result) == 15 and not all(row['passed'] for row in result.values())
    for location in ('init', 'assistant', 'terminal_usage', 'auxiliary_usage', 'basis'):
        changed, selected = deepcopy(prepared), deepcopy(chosen)
        if location == 'init': changed['events'][0]['model'] = subject.RETURNED
        elif location == 'assistant': changed['events'][1]['message']['model'] = subject.REQUESTED
        elif location == 'terminal_usage':
            changed['events'][-1]['modelUsage'] = {subject.RETURNED: changed['events'][-1]['modelUsage'][subject.REQUESTED]}
        elif location == 'auxiliary_usage': changed['events'][-1]['modelUsage']['other'] = {}
        else: selected['limits_basis'] = 'missing declaration'
        refused = gate_result(changed, selected, projections, pure_gate_members)
        assert refused['terminal']['passed'] is False, location
        if location in ('terminal_usage', 'auxiliary_usage', 'basis'):
            assert refused['accounting']['passed'] is False, location


@pytest.mark.parametrize('frame,key', [(0, 'permissionMode'), (-1, 'subtype')])
@pytest.mark.parametrize('value', ['missing', None, '', False, 'wrong'])
def test_terminal_requires_explicit_permission_and_success(tmp_path, pure_gate_members, frame, key, value):
    prepared, chosen, projections = current_stream(tmp_path)
    assert gate_result(prepared, chosen, projections, pure_gate_members)['terminal']['passed']
    if value == 'missing':
        del prepared['events'][frame][key]
    else:
        prepared['events'][frame][key] = value
    assert not gate_result(prepared, chosen, projections, pure_gate_members)['terminal']['passed']


@pytest.mark.parametrize('fixture', ['u4b_aliases'], indirect=True)
def test_genuine_saved_permission_consumer_uses_both_labels_and_refuses_mutations(fixture):
    targets = {('native_shared_permissions', '_trace_body'): ()}
    with observe_consumer_calls(targets) as calls:
        result = verify(fixture['manifest'], fixture['expected'])
    assert targets.keys() <= {key for key, _ in calls}
    assert result['checked'] is result['passed'] is True
    assert len(result['traces']) == 7 and len(result['cases']) == 25
    assert 'observation authenticity' in result['unassessed']
    for change in ('init_returned', 'assistant_requested', 'assistant_missing',
                   'usage_returned', 'usage_auxiliary', 'usage_missing'):
        value = deepcopy(fixture['manifest'])
        name = 'traces/settled/transcript.jsonl'
        events = rows(value, name)
        if change == 'init_returned': events[1]['model'] = subject.RETURNED
        elif change == 'assistant_requested': events[2]['message']['model'] = subject.REQUESTED
        elif change == 'assistant_missing': del events[-2]['message']['model']
        elif change == 'usage_returned':
            events[-1]['modelUsage'] = {subject.RETURNED: events[-1]['modelUsage'][subject.REQUESTED]}
        elif change == 'usage_auxiliary': events[-1]['modelUsage']['other'] = {}
        else: del events[-1]['modelUsage']
        put_rows(value, name, events)
        # Re-pin terminal and wrapper digests: refusal must concern the alias
        # observation, not a stale outcome checksum.
        outcome = get(value, 'traces/settled/outcome.json')
        outcome['terminal_sha256'] = c.sha(c.canonical(events[-1]))
        put(value, 'traces/settled/outcome.json', outcome)
        with pytest.raises(ValueError, match='model|returned|native init differs'):
            verify(value, fixture['expected'])


@pytest.mark.parametrize('fixture', ['u4b_aliases'], indirect=True)
def test_probe_adapter_keeps_cli_requested_and_http_returned_without_transport(fixture, tmp_path, monkeypatch):
    calls = []
    class StopBeforeNative(Exception):
        pass
    @contextmanager
    def in_memory_provider(**kwargs):
        calls.append(('provider', kwargs['model']))
        payload = provider.response_payload({'model': kwargs['model'], 'messages': []}, [], kwargs['model'])
        assert payload['model'] == subject.RETURNED
        with pytest.raises(ValueError, match='model differs'):
            provider.response_payload({'model': subject.REQUESTED, 'messages': []}, [], kwargs['model'])
        try:
            yield SimpleNamespace(failure=None), 'http://127.0.0.1:18455'
        finally:
            calls.append(('closed', True))
    def no_native(expected, launch, *args):
        assert launch['argv'][launch['argv'].index('--model') + 1] == subject.REQUESTED
        calls.append(('argv', subject.REQUESTED))
        raise StopBeforeNative()
    monkeypatch.setattr(producer, 'local_provider', in_memory_provider)
    monkeypatch.setattr(producer, '_run_native', no_native)
    with permission_orchestration.loaded_permission_inputs() as (controls, _), \
            loaded_consumer('native_shared_permissions') as consumer:
        with pytest.raises(StopBeforeNative):
            producer._trace(fixture['expected'], tmp_path / 'trace', time.monotonic() + 60,
                controls, consumer, fixture['selection'], None)
    assert calls == [('provider', subject.RETURNED), ('argv', subject.REQUESTED), ('closed', True)]
    assert (tmp_path / 'trace/config_root/settings.json').read_bytes() == b'{}'
