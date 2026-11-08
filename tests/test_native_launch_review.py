"""Raw-word/bundle term and independence refusals, no execution/provider."""
from copy import deepcopy
import pytest
from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_guard as wire
from tests.utils.native_u4b_fixtures import bundle_for


@pytest.fixture
def evidence(tmp_path):
    value = {'attempt_id': 'synthetic', 'dependencies': {'base': {'source_commit': 'a' * 40}},
        'permission_probe_sha256': 'b' * 64,
        'runtime': {'budget_guard_usd': '90', 'deadline_seconds': 60,
            'keep_awake': {'policy': 'not_applicable', 'host_platform': 'linux', 'basis': 'fixture'},
            'model': 'claude-opus-5[1m]',
            'environment': {'CLAUDE_CODE_DISABLE_1M_CONTEXT': '0'}}}
    raw = wire.canonical({'authority_version': 2, 'controller_sources_sha256': 'f' * 64,
                          'registration': value})
    bundle, word = bundle_for(raw, tmp_path / 'capture')
    return raw, bundle, word


def test_two_reviews_and_exact_statement(evidence):
    raw, bundle, word = evidence
    result = review.validate_bundle(raw, bundle, word)
    assert result['budget_guard_usd'] == '90'
    assert result['quota_capture']['count'] == 1
    assert set(wire.strict_json(word)) == review.WORD_KEYS


@pytest.mark.parametrize('field,value', [
    ('budget_guard_usd', '90.0'), ('budget_guard_usd', 90), ('deadline_seconds', 61),
    ('deadline_seconds', True), ('max_age_seconds', 0), ('max_age_seconds', True),
    ('max_starting_weekly_utilization', 1), ('max_starting_weekly_utilization', True),
    ('overage', 'enabled'), ('context_mode', 'default'), ('owner', 'different'),
    ('keep_awake', {'policy': 'not_applicable', 'host_platform': 'darwin', 'basis': 'fixture'})])
def test_mutated_terms_refused_even_when_rehashed(evidence, field, value):
    raw, bundle, word = evidence
    body, token = wire.strict_json(bundle), wire.strict_json(word)
    body['owner_statement'][field] = value
    changed = wire.canonical(body)
    token['review_sha256'] = wire.sha(changed)
    with pytest.raises(ValueError):
        review.validate_bundle(raw, changed, wire.canonical(token))


@pytest.mark.parametrize('mutation', ['one', 'three', 'same', 'author', 'operator', 'case',
                                     'not_independent', 'future', 'word_extra', 'word_digest', 'different_operator'])
def test_independence_and_word_refusals(evidence, mutation):
    raw, bundle, word = evidence
    body, token = wire.strict_json(bundle), wire.strict_json(word)
    if mutation == 'one': body['reviews'].pop()
    elif mutation == 'three': body['reviews'].append(deepcopy(body['reviews'][0]))
    elif mutation == 'same': body['reviews'][1]['reviewer'] = body['reviews'][0]['reviewer']
    elif mutation in ('author', 'operator'): body['reviews'][0]['reviewer'] = body[mutation]
    elif mutation == 'case': body['reviews'][0]['reviewer'] = body['author'].upper()
    elif mutation == 'not_independent': body['reviews'][0]['independent'] = 1
    elif mutation == 'future': body['reviews'][0]['reviewed_at'] = '2026-11-09T00:00:00Z'
    elif mutation == 'word_extra': token['quota_capture'] = True
    elif mutation == 'different_operator':
        body['operator'] = 'other operator'
        for item in body['reviews']: item['operator'] = body['operator']
    changed = wire.canonical(body)
    token['review_sha256'] = wire.sha(changed) if mutation != 'word_digest' else '0' * 64
    with pytest.raises(ValueError):
        review.validate_bundle(raw, changed, wire.canonical(token))


@pytest.mark.parametrize('key,value', [('count', 2), ('count', True), ('directory', 'relative'),
    ('deadline_seconds', 61), ('prompt_sha256', '0' * 64), ('max_stdout_bytes', 2000000)])
def test_only_exactly_registered_capture(evidence, key, value):
    raw, bundle, word = evidence
    body, token = wire.strict_json(bundle), wire.strict_json(word)
    body['owner_statement']['quota_capture'][key] = value
    changed = wire.canonical(body); token['review_sha256'] = wire.sha(changed)
    with pytest.raises(ValueError):
        review.validate_bundle(raw, changed, wire.canonical(token))
