"""D143 pair acceptance and byte preservation; inert local evidence only."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import types

import pytest
from data_sheets_schema import native_run_limits as limits
from data_sheets_schema import native_u4b_policy as policy
from data_sheets_schema import native_u4b_runtime as runtime
from data_sheets_schema import native_u4b_probe_sequence as sequence
from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_guard as wire
from data_sheets_schema import native_shared_runtime_values as generic
from tests.test_native_u4b_runtime import runtime_inputs
from tests.test_native_launch_review import evidence
from tests.utils.native_u4b_observation import mint_observation
from tests.utils.native_u4b_fixtures import bundle_for

BASE = '8760de5efe88b5af62e9d77e6335fa7e248017b6'


@pytest.mark.parametrize('pair', limits.REGISTERED_PAIRS)
def test_whole_pair_survives_observation_and_final_runtime(tmp_path, pair):
    value, args = runtime_inputs(tmp_path)
    value.update(zip(('budget_guard_usd', 'deadline_seconds'), pair))
    mint_observation(value, args['probe_init_path'], args['native_request_path'])
    prepared = runtime.prepare_runtime(value, **args)
    assert runtime.validate_prepared_runtime(prepared) == prepared
    assert limits.require_registered_pair(prepared) == pair
    policy.validate_runtime_terms(prepared)
    provisional = json.loads((Path(args['observation_probe_path']).parent.parent / 'provisional-runtime.json').read_bytes())
    assert sequence.validate_provisional_runtime(provisional) == provisional


@pytest.mark.parametrize('pair', [('90',43200),('400',21600),('100',21600),('400',43201),
                                 ('90.0',21600),('400',43200.0),(90,21600),('90',True),
                                 (None,21600),('90',None),([],21600)])
def test_mixed_third_and_missing_values_refused_at_each_boundary(tmp_path, pair):
    value, _ = runtime_inputs(tmp_path)
    value.update(zip(('budget_guard_usd', 'deadline_seconds'), pair))
    for key in ('budget_guard_usd', 'deadline_seconds'):
        if value[key] is None: del value[key]
    for check in (limits.require_registered_pair, runtime._profile,
                  policy.validate_runtime_terms):
        with pytest.raises(ValueError): check(value)


@pytest.mark.parametrize('pair', [('90', 43200), ('400', 21600), ('100', 21600),
                                 ('400', 43201), ('90.0', 21600)])
def test_provisional_refusal_depends_on_registered_pair_check(tmp_path, monkeypatch, pair):
    value, args = runtime_inputs(tmp_path)
    mint_observation(value, args['probe_init_path'], args['native_request_path'])
    provisional = json.loads((Path(args['observation_probe_path']).parent.parent / 'provisional-runtime.json').read_bytes())
    assert sequence.validate_provisional_runtime(provisional) == provisional
    mutated = deepcopy(provisional)
    mutated.update(zip(('budget_guard_usd', 'deadline_seconds'), pair))
    assert generic.validate_runtime_v2(mutated) == mutated
    with pytest.raises(ValueError, match='registered budget/deadline as one complete pair'):
        sequence.validate_provisional_runtime(mutated)
    # Removing only this check must admit these otherwise valid documents.
    # This makes the regression sensitivity executable, not an inferred claim.
    monkeypatch.setattr(limits, 'require_registered_pair', lambda value: None)
    assert sequence.validate_provisional_runtime(mutated) == mutated


@pytest.mark.parametrize('pair', limits.REGISTERED_PAIRS)
def test_review_and_word_bind_the_whole_registered_pair(evidence, tmp_path, pair):
    value = wire.strict_json(evidence[0])
    value['registration']['runtime'].update(zip(('budget_guard_usd','deadline_seconds'),pair))
    raw = wire.canonical(value)
    bundle, word = bundle_for(raw, tmp_path / 'capture')
    terms = review.validate_bundle(raw, bundle, word)
    assert (terms['budget_guard_usd'],terms['deadline_seconds']) == pair
    statement = wire.strict_json(bundle)['owner_statement']
    statement['budget_guard_usd'] = limits.PRODUCTION[0] if pair == limits.CANARY else limits.CANARY[0]
    with pytest.raises(ValueError, match='budget'):
        review.validate_terms(statement,value['registration']['runtime'],word_owner=statement['owner'])


def prior_module(name):
    """Exact local published-base source, no network and no guessed old validator."""
    root = Path(__file__).resolve().parents[1]
    raw = subprocess.check_output(['/usr/bin/git','show',BASE+':src/data_sheets_schema/'+name+'.py'],cwd=root)
    module = types.ModuleType('data_sheets_schema.prior_'+name)
    module.__package__ = 'data_sheets_schema'
    module.__file__ = str(root / 'src/data_sheets_schema' / (name + '.py'))
    exec(compile(raw,BASE+':'+name,'exec'),module.__dict__)
    return module


def test_canary_same_input_runtime_and_saved_registration_bytes_unchanged(tmp_path, evidence):
    old_runtime = prior_module('native_u4b_runtime')
    old_policy = prior_module('native_u4b_policy')
    old_review = prior_module('native_launch_review')
    value,args = runtime_inputs(tmp_path)
    before = old_runtime.prepare_runtime(deepcopy(value), **args)
    after = runtime.prepare_runtime(deepcopy(value), **args)
    assert wire.canonical(before) == wire.canonical(after)
    old_policy.validate_runtime_terms(before)
    policy.validate_runtime_terms(after)
    raw,bundle,word = evidence
    saved = (bytes(raw),bytes(bundle),bytes(word))
    assert old_review.validate_bundle(*saved) == review.validate_bundle(*saved)
    assert saved == evidence
    for name, raw_bytes in {
        'canary-runtime-before.json': wire.canonical(before),
        'canary-runtime-after.json': wire.canonical(after),
        'canary-registration-before.json': saved[0],
        'canary-registration-after.json': evidence[0],
        'canary-review.json': saved[1], 'canary-word.json': saved[2],
    }.items():
        (tmp_path / name).write_bytes(raw_bytes)
    # This is exact saved-registration/parser compatibility, not a claim that
    # fresh registration source/dependency identities survive a source change.
