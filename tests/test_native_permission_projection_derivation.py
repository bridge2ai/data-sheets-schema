"""Per-projection common derivation, retaining every real effect-view check.

The complete fixture contains fabricated permission observations, not native
evidence. The reference preserves Round 1 policy/recipe reuse and repeats the
former per-view common derivation. No timing assertions.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_effects as effects
from data_sheets_schema import native_shared_permissions as p
from tests.test_native_shared_permissions import fixture, get, prohibit_real_transports


def previous_view(expected, selection, launch, session, context, *, state='awaiting_response', read=False,
                  policy=None, recipe=None):
    contract, _ = p._dependencies()
    basis, fixed, requests, responses = (p._recipe_data(expected, selection, launch, session)
                                         if recipe is None else recipe)
    root = p._path(launch['effect_root'])
    if policy is None:
        policy = p.projected_policy(expected, selection, str(root))
    active = state == 'awaiting_response' and context in p.CONTEXTS
    ordinal = p.CONTEXTS.index(context) + 1 if context in p.CONTEXTS else 1
    cursor = contract.StageCursor(ordinal=ordinal, kind=context,
                                 target_id='worker-000001' if context == 'worker' else context) if active else None
    request_path = str(root / 'requests' / ('%06d.json' % ordinal))
    request = contract.ArtifactPin(**p._artifact('stage_request:' + str(ordinal), request_path,
                                               requests[context])) if active else None
    response = contract.ResponseDestination(role='stage_response:' + str(ordinal),
        path=str(root / 'responses' / ('%06d.bin' % ordinal)), media_type='application/json',
        max_bytes=min(selection['bounds']['max_response_bytes'], 2_097_152)) if active else None
    protected = [contract.RolePath(role=role, path=str(root / relative))
                 for role, relative in sorted(contract.ROLE_RELATIVE_PATHS.items())]
    protected.extend([contract.RolePath(role='stage_root', path=str(root)),
                      contract.RolePath(role='selection', path=expected['selection']['path']),
                      contract.RolePath(role='source', path=expected['source']['path'])])
    sealed = tuple(contract.ArtifactPin(**p._artifact('probe_sealed', path, raw)) for path, raw in sorted(fixed.items()))
    return contract.NativeEffectView(protocol='native_shared_generation_v1',
        selection_sha256=expected['selection']['sha256'],
        execution_binding_sha256=p._sha(p._encoded({**basis, 'identity': 'synthetic-execution-binding'})),
        static_policy_sha256=p._sha(p._encoded(policy)), stage_root=str(root),
        working_directory=expected['policy']['readonly_lookups']['repository'],
        stage_command=expected['commands']['stage'], state=state, cursor=cursor, request=request,
        response=response, sealed=sealed, protected_roles=tuple(protected),
        correction_window=False, pending_advance_tool_use_id=None,
        history_sha256=p._sha(p._encoded({**basis, 'identity': 'synthetic-history', 'context': context, 'state': state})),
        request_read_observation_sha256=(p._sha(p._encoded({**basis, 'identity': 'synthetic-read',
                                                       'context': context})) if read and active else None),
        response_intent_observation_sha256=None)

def previous_projection(expected, selection, launch, session_id):
    """Deterministic software projection; never evidence of a real stage."""
    policy = p.projected_policy(expected, selection, launch['effect_root'])
    recipe = p._recipe_data(expected, selection, launch, session_id)
    states = []
    for context in p.CONTEXTS:
        for read in (False, True):
            states.append({'name': context + ('-read' if read else '-unread'),
                           'view': asdict(previous_view(expected, selection, launch, session_id, context,
                                                       read=read, policy=policy, recipe=recipe))})
    for state in p.NONRESPONSE:
        states.append({'name': state, 'view': asdict(previous_view(expected, selection, launch, session_id,
                                                         'worker', state=state, policy=policy, recipe=recipe))})
    return {'kind': 'native_shared_permission_projection', 'version': p.VERSION,
            'effect_root': launch['effect_root'], 'session_id': session_id, 'states': states,
            'production_policy_sha256': p._sha(p._encoded(expected['policy'])), 'probe_policy': policy,
            'probe_policy_sha256': p._sha(p._encoded(policy)),
            'role_recipe_sha256': expected['probe_recipe']['descriptor_sha256']}


@pytest.fixture
def inputs(fixture):
    launch = get(fixture['manifest'], 'traces/settled/launch.json')
    session = get(fixture['manifest'], 'traces/settled/outcome.json')['session_id']
    return deepcopy(fixture['expected']), deepcopy(fixture['selection']), launch, session


def outcome(function, *args, **kwargs):
    try:
        value = function(*args, **kwargs)
        return 'returned', c.canonical(asdict(value) if type(value) is c.NativeEffectView else value)
    except Exception as error:
        cause = error.__cause__
        return 'raised', type(error), error.args, None if cause is None else (type(cause), cause.args)


def compare(inputs, *, context=None, state='awaiting_response', read=False):
    before = c.canonical(inputs)
    if context is None:
        previous = outcome(previous_projection, *inputs)
        current = outcome(p.projection, *inputs)
    else:
        previous = outcome(previous_view, *inputs, context, state=state, read=read)
        current = outcome(p._view, *inputs, context, state=state, read=read)
    assert current == previous
    assert c.canonical(inputs) == before
    return current


def test_complete_thirteen_states_equal_previous_canonical_projection(inputs):
    old = previous_projection(*inputs)
    current = p.projection(*inputs)
    assert c.canonical(current) == c.canonical(old)
    expected_names = [context + suffix for context in p.CONTEXTS for suffix in ('-unread', '-read')]
    expected_names += list(p.NONRESPONSE)
    assert [row['name'] for row in current['states']] == expected_names
    assert len(current['states']) == 13
    for ordinal, context in enumerate(p.CONTEXTS, 1):
        unread, read = [row['view'] for row in current['states'][2 * ordinal - 2:2 * ordinal]]
        assert unread['cursor']['ordinal'] == read['cursor']['ordinal'] == ordinal
        assert unread['cursor']['kind'] == read['cursor']['kind'] == context
        assert unread['request_read_observation_sha256'] is None
        assert read['request_read_observation_sha256'] is not None
        assert unread['request'] == read['request'] and unread['response'] == read['response']
    for row in current['states'][8:]:
        assert row['view']['state'] == row['name']
        assert all(row['view'][key] is None for key in ('cursor', 'request', 'response', 'request_read_observation_sha256'))


def test_one_common_derivation_still_constructs_validates_and_serializes_thirteen_views(inputs, monkeypatch):
    real_recipe, real_policy = p._recipe_data, p.projected_policy
    real_init, real_validate, real_asdict = c.NativeEffectView.__post_init__, c._validate_carrier, p.asdict
    counts, constructed = Counter(), []

    def recipe(*args, **kwargs):
        counts['recipe'] += 1
        return real_recipe(*args, **kwargs)

    def projected(*args, **kwargs):
        counts['policy'] += 1
        return real_policy(*args, **kwargs)

    def initialize(view):
        counts['construct'] += 1
        real_init(view)
        constructed.append(view)

    def validate(value):
        if type(value) is c.NativeEffectView:
            counts['validate_view'] += 1
        if type(value) is c.RolePath:
            counts['validate_role'] += 1
        return real_validate(value)

    def serialize(value):
        if type(value) is c.NativeEffectView:
            counts['serialize'] += 1
        return real_asdict(value)

    monkeypatch.setattr(p, '_recipe_data', recipe)
    monkeypatch.setattr(p, 'projected_policy', projected)
    monkeypatch.setattr(c.NativeEffectView, '__post_init__', initialize)
    monkeypatch.setattr(c, '_validate_carrier', validate)
    monkeypatch.setattr(p, 'asdict', serialize)
    expected = previous_projection(*inputs)
    old_counts = counts.copy()
    assert old_counts['recipe'] == old_counts['policy'] == 1
    assert old_counts['construct'] == old_counts['validate_view'] == 13
    counts.clear()
    constructed.clear()
    assert c.canonical(p.projection(*inputs)) == c.canonical(expected)
    assert counts['recipe'] == counts['policy'] == 1
    assert counts['construct'] == counts['validate_view'] == counts['serialize'] == 13
    assert old_counts['validate_role'] == counts['validate_role'] * 13
    assert len({id(view) for view in constructed}) == 13
    assert all(type(view) is c.NativeEffectView for view in constructed)
    # The actual class and validator are still installed; spies delegated all
    # construction/validation instead of replacing the strict carrier class.
    assert all(view.protected_roles == constructed[0].protected_roles for view in constructed)
    counts.clear()
    p._view(*inputs, 'receipt')
    p._view(*inputs, 'worker')
    assert counts['recipe'] == counts['policy'] == counts['construct'] == counts['validate_view'] == 2


def test_actual_twenty_five_classifications_keep_independent_view_and_classifier_calls(inputs, monkeypatch):
    cases = p.probe_cases(*inputs)
    assert len(cases) == 25
    controls = p.composition.load_controls()
    actual_view = p._view
    actual_recipe, actual_effect = p._recipe_data, effects.classify_effect
    actual_bash = p.command_policy.classify_bash
    counters = Counter()

    def recipe(*args, **kwargs):
        counters['recipe'] += 1
        return actual_recipe(*args, **kwargs)

    def effect(*args, **kwargs):
        counters['effect'] += 1
        return actual_effect(*args, **kwargs)

    def bash(*args, **kwargs):
        counters['bash'] += 1
        return actual_bash(*args, **kwargs)

    monkeypatch.setattr(p, '_recipe_data', recipe)
    monkeypatch.setattr(effects, 'classify_effect', effect)
    monkeypatch.setattr(p.command_policy, 'classify_bash', bash)

    def run(view_function):
        counters.clear()
        views, results = [], []
        with monkeypatch.context() as patch:
            patch.setattr(p, '_view', view_function)
            for case in cases:
                classification, view = p._classification(*inputs, case, controls)
                views.append(view)
                results.append((classification, asdict(view)))
        assert len({id(view) for view in views}) == 25
        return c.canonical(results), counters.copy()

    previous, old_counts = run(previous_view)
    current, new_counts = run(actual_view)
    assert current == previous and new_counts == old_counts
    assert new_counts['recipe'] == 25
    assert new_counts['effect'] > 0 and new_counts['bash'] > 0


def test_each_projection_uses_current_inputs_and_serialized_states_are_detached(inputs):
    before = c.canonical(inputs)
    original = p.projection(*inputs)
    baseline = c.canonical(original)
    original['states'][0]['view']['protected_roles'][0]['path'] = '/mutated/serialized'
    assert all(row['view']['protected_roles'][0]['path'] != '/mutated/serialized'
               for row in original['states'][1:])
    original['probe_policy']['readonly_lookups']['inputs'].append('/mutated/input')
    assert c.canonical(p.projection(*inputs)) == baseline and c.canonical(inputs) == before
    mutations = [
        ('session', lambda data: data.__setitem__(3, '00000000-0000-4000-8000-000000000099')),
        ('neutral root', lambda data: data[2].update(effect_root=data[2]['effect_root'] + '-new')),
        ('recipe digest', lambda data: data[0]['probe_recipe'].update(descriptor_sha256='9' * 64)),
        ('selection digest', lambda data: data[0]['selection'].update(sha256='8' * 64)),
        ('response bound', lambda data: data[1]['bounds'].update(max_response_bytes=17)),
        ('policy', lambda data: data[0]['policy']['readonly_lookups']['inputs'].append('/fresh/current/input')),
    ]
    for label, mutate in mutations:
        changed = list(deepcopy(inputs))
        mutate(changed)
        assert c.canonical(changed) != before, label
        result = compare(changed)
        assert result[0] == 'returned' and result[1] != baseline, label
        assert c.canonical(p.projection(*inputs)) == baseline, label


def test_malformed_inputs_keep_previous_first_failure_and_inactive_bound_behavior(inputs):
    mutations = [
        ('invalid root before response bound', lambda d: (d[2].update(effect_root='relative'), d[1]['bounds'].pop('max_response_bytes'))),
        ('overlap before response bound', lambda d: (d[2].update(stub_root=d[2]['config_root']), d[1]['bounds'].pop('max_response_bytes'))),
        ('ambiguous output before active bound', lambda d: (d[0]['policy']['readonly_lookups']['output_directories'].append(d[1]['stage_root']), d[1]['bounds'].pop('max_response_bytes'))),
        ('ambiguous input', lambda d: d[0]['policy']['readonly_lookups']['inputs'].append(d[0]['source']['path'])),
        ('unknown mapped leaf', lambda d: d[0]['policy']['readonly_lookups']['inputs'].append(d[1]['stage_root'] + '/unregistered.bin')),
        ('empty write map', lambda d: d[0]['policy']['readonly_lookups'].update(write_paths={})),
        ('invalid write cap', lambda d: d[0]['policy']['readonly_lookups'].update(write_paths={d[1]['stage_root'] + '/responses/000001.bin': True})),
        ('response bound missing', lambda d: d[1]['bounds'].pop('max_response_bytes')),
        ('response bound wrong type', lambda d: d[1]['bounds'].update(max_response_bytes=True)),
        ('stage command wrong type', lambda d: d[0]['commands'].update(stage=[])),
    ]
    for label, mutate in mutations:
        changed = list(deepcopy(inputs))
        mutate(changed)
        assert c.canonical(changed) != c.canonical(inputs), label
        assert compare(changed)[0] == 'raised', label
        assert compare(changed, context='receipt')[0] == 'raised', label
    changed = list(deepcopy(inputs))
    changed[1]['bounds'].pop('max_response_bytes')
    for state in p.NONRESPONSE:
        assert compare(changed, context='worker', state=state)[0] == 'returned'
    assert compare(changed, context='worker')[0] == 'raised'


def test_factory_is_lazy_and_failed_first_carrier_does_not_retain_common_data(inputs, monkeypatch):
    calls = []
    actual_recipe = p._recipe_data

    def recipe(*args, **kwargs):
        calls.append('recipe')
        return actual_recipe(*args, **kwargs)

    monkeypatch.setattr(p, '_recipe_data', recipe)
    changed = list(deepcopy(inputs))
    stage = changed[0]['commands']['stage']
    changed[0]['commands']['stage'] = []
    build = p._view_factory(*changed)
    assert calls == []
    failed = outcome(build, 'receipt')
    assert failed[0] == 'raised'
    assert failed == outcome(previous_view, *changed, 'receipt')
    assert calls == ['recipe', 'recipe']
    changed[0]['commands']['stage'] = stage
    calls.clear()
    current = build('receipt')
    assert calls == ['recipe']
    assert c.canonical(asdict(current)) == c.canonical(asdict(previous_view(*changed, 'receipt')))
    assert len(calls) == 2


def test_inactive_view_does_not_touch_active_bound_property_and_preserves_error_order(inputs):
    class BoundAccess(ValueError):
        pass

    class Bounds(dict):
        def __getitem__(self, key):
            if key == 'max_response_bytes':
                raise BoundAccess('active response bound consulted')
            return super().__getitem__(key)

    class CommandAccess(ValueError):
        pass

    class Commands(dict):
        def __getitem__(self, key):
            if key == 'stage':
                raise CommandAccess('stage command consulted')
            return super().__getitem__(key)

    changed = list(deepcopy(inputs))
    changed[1]['bounds'] = Bounds(changed[1]['bounds'])
    for state in p.NONRESPONSE:
        assert outcome(p._view, *changed, 'worker', state=state) == outcome(previous_view, *changed, 'worker', state=state)
        assert outcome(p._view, *changed, 'worker', state=state)[0] == 'returned'
    changed[0]['commands'] = Commands(changed[0]['commands'])
    active = outcome(p._view, *changed, 'worker')
    assert active == outcome(previous_view, *changed, 'worker')
    assert active[0:3] == ('raised', BoundAccess, ('active response bound consulted',))
    inactive = outcome(p._view, *changed, 'worker', state='await_core')
    assert inactive == outcome(previous_view, *changed, 'worker', state='await_core')
    assert inactive[0:3] == ('raised', CommandAccess, ('stage command consulted',))
