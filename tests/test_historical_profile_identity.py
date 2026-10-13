"""Historical profile checks preserve unknowns and the source they describe."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema import profile_identity, profiles, provenance, run_schema, schema_digest, schema_view


SCHEMA = b'''id: https://example.org/profile-fixture
name: profile_fixture
imports: [linkml:types]
prefixes:
  linkml: https://w3id.org/linkml/
  ex: https://example.org/
default_prefix: ex
default_range: string
classes:
  Dataset:
    attributes:
      topic:
        range: string
        values_from: [B2AI_TOPIC]
'''
VOCABULARY = b'vocabularies:\n  B2AI_TOPIC:\n    ex:term: Synthetic topic\n'


@pytest.fixture
def historical(tmp_path, monkeypatch):
    schema = tmp_path / 'historical.yaml'
    schema.write_bytes(SCHEMA)
    pin = tmp_path / 'vocabulary.yaml'
    pin.write_bytes(VOCABULARY)
    monkeypatch.setattr(schema_digest, 'VOCABULARY_PIN', pin)
    candidates = {name: schema_digest.fingerprint(schema_digest.digest_text(
        'Dataset', schema_path=schema, profile=profile)) for name, profile in profiles.PROFILES.items()}
    assert candidates['neutral'] != candidates['bridge2ai']
    record = {'schema': {'full_path': str(schema), 'full_sha256': hashlib.sha256(SCHEMA).hexdigest(),
                          'full_md5': hashlib.md5(SCHEMA).hexdigest(),
                          'profile': 'neutral', 'digest_md5': candidates['neutral']}}
    return record, candidates, schema, pin


@pytest.mark.parametrize('profile', ['neutral', 'bridge2ai'])
@pytest.mark.parametrize('matched', [True, False])
def test_real_renderer_match_and_opposite_profile(historical, profile, matched):
    record, candidates, path, pin = historical
    record['schema']['profile'] = profile
    other = 'neutral' if profile == 'bridge2ai' else 'bridge2ai'
    record['schema']['digest_md5'] = candidates[profile if matched else other]
    before = deepcopy(record), path.read_bytes(), pin.read_bytes()
    findings, context = provenance.profile_assessment(record)
    assert context['status'] == ('match' if matched else 'mismatch')
    assert bool(findings) is not matched
    assert context['candidate_digests'] == candidates
    assert context['schema_sha256'] == hashlib.sha256(SCHEMA).hexdigest()
    assert context['vocabularies']['bridge2ai']['sha256'] == hashlib.sha256(VOCABULARY).hexdigest()
    assert context['renderer']['source_sha256'] == hashlib.sha256(Path(schema_digest.__file__).read_bytes()).hexdigest()
    assert context['renderer']['linkml_runtime_version']
    assert (record, path.read_bytes(), pin.read_bytes()) == before
    assert json.loads(json.dumps(context)) == context


def test_equal_profiles_prefer_the_stated_profile(historical):
    record, _, path, pin = historical
    pin.write_text('vocabularies: {}\n')
    record['schema']['digest_md5'] = schema_digest.fingerprint(schema_digest.digest_text(
        'Dataset', schema_path=path, profile=profiles.NEUTRAL))
    context = profile_identity.capture(record)
    assert context['status'] == 'match' and context['finding'] is None
    assert len(set(context['candidate_digests'].values())) == 1


def test_unmatched_history_does_not_consult_current_digest(historical, monkeypatch):
    record, _, _, _ = historical
    record['schema']['digest_md5'] = '0' * 32
    monkeypatch.setattr(schema_digest, 'digest_text', lambda *a, **k: pytest.fail('current digest fallback'))
    context = profile_identity.capture(record)
    assert context['status'] == 'unknown' and context['finding'] is None
    assert 'not reproduced' in context['reason']


@pytest.mark.parametrize('field,value', [('full_path', None), ('full_path', ''),
    ('full_sha256', None), ('full_sha256', []), ('full_sha256', 'f' * 63),
    ('full_sha256', 'F' * 64), ('full_md5', ''), ('full_md5', 4)])
def test_partial_or_malformed_authority_cannot_fall_back(historical, monkeypatch, field, value):
    record, _, _, _ = historical
    record['schema'][field] = value
    monkeypatch.setattr(run_schema, 'run_schema_bytes', lambda *a, **k: pytest.fail('invalid authority resolved'))
    monkeypatch.setattr(schema_digest, 'digest_text', lambda *a, **k: pytest.fail('current fallback'))
    context = profile_identity.capture(record)
    assert context['status'] == 'unknown' and context['finding'] is None


@pytest.mark.parametrize('case', ['missing_path', 'missing_hashes', 'mixed_hashes', 'missing_history'])
def test_history_authority_never_silently_weakens(historical, monkeypatch, case):
    record, _, _, _ = historical
    if case == 'missing_path':
        del record['schema']['full_path']
    elif case == 'missing_hashes':
        for key in ('full_sha256', 'full_md5'):
            del record['schema'][key]
    elif case == 'mixed_hashes':
        record['schema']['full_md5'] = '0' * 32
        monkeypatch.setattr(run_schema, 'run_schema_bytes', lambda *a, **k: (SCHEMA, {'source': 'test resolver'}))
    else:
        monkeypatch.setattr(run_schema, 'run_schema_bytes', lambda *a, **k: (None, {'source': run_schema.TODAY, 'reason': 'not recovered'}))
    monkeypatch.setattr(schema_digest, 'digest_text', lambda *a, **k: pytest.fail('current fallback'))
    context = profile_identity.capture(record)
    assert context['status'] == 'unknown' and context['finding'] is None


@pytest.mark.parametrize('raw', [b'[]', b'name: x\nname: y\n',
    SCHEMA.replace(b'classes:\n', b'classes:\n  Unused: {}\n').replace(b'  Dataset:', b'  Other:'),
    SCHEMA.replace(b'[linkml:types]', b'[unrecorded-local-import]')])
def test_invalid_or_incomplete_historical_schema_is_unknown(historical, raw):
    record, _, path, _ = historical
    path.write_bytes(raw)
    record['schema'].update(full_sha256=hashlib.sha256(raw).hexdigest(), full_md5=hashlib.md5(raw).hexdigest())
    context = profile_identity.capture(record)
    assert context['status'] == 'unknown' and context['finding'] is None
    assert 'unavailable' in context['reason']


@pytest.mark.parametrize('vocabulary', [None, b'[]', b'vocabularies: [broken]\n',
    b'vocabularies: {}\nvocabularies: {}\n'])
def test_missing_or_malformed_vocabulary_stays_unknown(historical, vocabulary):
    record, _, _, pin = historical
    if vocabulary is None:
        pin.unlink()
    else:
        pin.write_bytes(vocabulary)
    context = profile_identity.capture(record)
    assert context['status'] == 'unknown' and context['finding'] is None
    assert context['vocabularies']['bridge2ai']['source'] == 'unavailable current profile vocabulary'


def test_record_schema_and_vocab_captured_once_and_view_released(historical, monkeypatch):
    record, _, schema, pin = historical
    expected = deepcopy(record)
    real_resolve, real_read, real_view = run_schema.run_schema_bytes, Path.read_bytes, schema_view.version_view
    resolves, reads, views = [], [], []

    def resolve(snapshot, **kwargs):
        resolves.append(deepcopy(snapshot))
        record['schema']['profile'] = 'bridge2ai'
        record['schema']['digest_md5'] = '0' * 32
        return real_resolve(snapshot, **kwargs)

    def read(path):
        if path in (schema, pin):
            reads.append(path)
        return real_read(path)

    @contextmanager
    def view(*args, **kwargs):
        with real_view(*args, **kwargs) as selected:
            views.append('opened')
            yield selected
        views.append('closed')

    monkeypatch.setattr(run_schema, 'run_schema_bytes', resolve)
    monkeypatch.setattr(Path, 'read_bytes', read)
    monkeypatch.setattr(schema_view, 'version_view', view)
    context = profile_identity.capture(record)
    assert context['status'] == 'match'
    assert resolves == [expected]
    assert reads == [schema, pin]
    assert views == ['opened', 'closed']
    assert context['effective_profile'] == 'neutral'
    assert context['recorded_digest_md5'] == expected['schema']['digest_md5']


def test_contexts_are_detached_and_no_historical_view_enters_shared_cache(historical, monkeypatch):
    record, _, _, _ = historical
    monkeypatch.setattr(schema_view, 'shared_view', lambda *a, **k: pytest.fail('historical shared view'))
    first = profile_identity.capture(record)
    first['schema_basis']['source'] = 'caller mutation'
    first['vocabularies']['bridge2ai']['sha256'] = 'caller mutation'
    second = profile_identity.capture(record)
    assert second['status'] == 'match'
    assert second['schema_basis']['source'] != 'caller mutation'
    assert second['vocabularies']['bridge2ai']['sha256'] == hashlib.sha256(VOCABULARY).hexdigest()


@pytest.mark.parametrize('record', [{}, {'schema': {}}, {'schema': {'digest_md5': None}},
    {'schema': {'digest_md5': ''}}])
def test_no_recorded_digest_is_distinct_from_unknown(record):
    assert profile_identity.capture(record)['status'] == 'no_recorded_digest'


def test_md5_only_historical_record_remains_supported(historical):
    record, _, _, _ = historical
    del record['schema']['full_sha256']
    assert profile_identity.capture(record)['status'] == 'match'


@pytest.mark.parametrize('value', ['[]', 'false', '0', '""', 'null'])
@pytest.mark.parametrize('level', ['outer', 'nested'])
def test_falsey_malformed_vocabulary_cannot_certify_a_match(historical, level, value):
    record, candidates, _, pin = historical
    record['schema'].update(profile='bridge2ai', digest_md5=candidates['neutral'])
    pin.write_text('vocabularies: ' + (value if level == 'outer' else '\n  B2AI_TOPIC: ' + value) + '\n')
    context = profile_identity.capture(record)
    assert context['status'] == 'unknown'
    assert context['finding'] is None and context['candidate_digests'] == {}


@pytest.mark.parametrize('raw', [b'other: {}\n', b'vocabularies:\n  1: {}\n',
    b'vocabularies:\n  B2AI_TOPIC:\n    1: term\n',
    b'vocabularies:\n  B2AI_TOPIC:\n    ex:term: false\n',
    b'vocabularies:\n  B2AI_TOPIC:\n    ex:term: {}\n'])
def test_malformed_vocabulary_structure_stays_unknown(historical, raw):
    record, _, _, pin = historical
    pin.write_bytes(raw)
    context = profile_identity.capture(record)
    assert context['status'] == 'unknown' and context['finding'] is None


def test_legitimate_empty_named_vocabulary_keeps_own_match(historical):
    record, candidates, _, pin = historical
    record['schema'].update(profile='bridge2ai', digest_md5=candidates['neutral'])
    pin.write_text('vocabularies:\n  B2AI_TOPIC: {}\n')
    context = profile_identity.capture(record)
    assert context['status'] == 'match' and context['finding'] is None
    assert len(set(context['candidate_digests'].values())) == 1
