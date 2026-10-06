"""Bounded text reuse must not retain live authority or change renderer results."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
import hashlib
import subprocess

import pytest

from data_sheets_schema import historical_digest as history, schema_view
from tests.test_historical_digest import SCHEMA, PATH, VOCABULARY, GOLDEN, candidate


@pytest.fixture(autouse=True)
def empty_cache():
    # LinkML initializes the loader's class constructor tables on first use.
    schema_view.version_document(b'name: initialize\n')
    history._text_cache_clear()
    yield
    history._text_cache_clear()


def render(raw=SCHEMA, path=PATH, family='canonical_paths', vocabulary=VOCABULARY):
    return history.render_captured(raw, path, family, vocabulary_bytes=vocabulary)


def count_inventory(monkeypatch):
    calls, original = [], history._inventory

    def inventory(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(history, '_inventory', inventory)
    return calls


@pytest.mark.parametrize('family', tuple(GOLDEN))
def test_cold_warm_disabled_and_literal_values_agree(monkeypatch, family):
    vocabulary = VOCABULARY if history.POLICIES[family].vocabulary else None
    calls = count_inventory(monkeypatch)
    assert render(family=family, vocabulary=vocabulary) == GOLDEN[family]
    assert render(family=family, vocabulary=vocabulary) == GOLDEN[family]
    assert len(calls) == 1 and history._text_cache_info()['entries'] == 1
    monkeypatch.setattr(history, '_TEXT_CACHE_MAX_ENTRIES', 0)
    assert render(family=family, vocabulary=vocabulary) == GOLDEN[family]
    assert len(calls) == 2 and history._text_cache_info()['entries'] == 0


@pytest.mark.parametrize('change', ['raw', 'path', 'vocabulary', 'policy', 'full_path',
                                  'universal', 'helper', 'helper_code', 'helper_defaults',
                                  'view_constructor', 'schema_constructor', 'nested_constructor',
                                  'view_method', 'parser', 'yaml_constructor'])
def test_complete_effective_input_changes_miss_the_warm_cache(monkeypatch, change):
    from linkml_runtime.linkml_model import meta
    calls = count_inventory(monkeypatch)
    before = render()
    raw, path, vocabulary = SCHEMA, PATH, VOCABULARY
    if change == 'raw':
        raw = SCHEMA.replace(b'count:', b'number:')
    elif change == 'path':
        path = './different/custom.yaml'
    elif change == 'vocabulary':
        vocabulary = VOCABULARY.replace(b'First', b'Changed label')
    elif change == 'policy':
        monkeypatch.setitem(history.POLICIES, 'canonical_paths', replace(history.POLICIES['canonical_paths'], enum_limit=1))
    elif change == 'full_path':
        monkeypatch.setattr(history, 'FULL_SCHEMA_PATH', 'changed/data_sheets_schema_all.yaml')
    elif change == 'universal':
        monkeypatch.setattr(history, '_UNIVERSAL', frozenset({'id', 'count'}))
    elif change in ('helper', 'helper_code', 'helper_defaults'):
        if change == 'helper':
            original = history._terms
            monkeypatch.setattr(history, '_terms', lambda *a: 'changed ' + (original(*a) or ''))
        elif change == 'helper_code':
            def changed(names, vocabulary):
                return 'changed terms'
            monkeypatch.setattr(history._terms, '__code__', changed.__code__)
        else:
            original = history._terms
            def changed(names, vocabulary, prefix='before '):
                return prefix + (original(names, vocabulary) or '')
            monkeypatch.setattr(history, '_terms', changed)
            before = render()
            monkeypatch.setattr(changed, '__defaults__', ('after ',))
    elif change in ('view_constructor', 'schema_constructor', 'nested_constructor'):
        cls = {'view_constructor': schema_view._ReleasableView,
               'schema_constructor': schema_view.SchemaDefinition,
               'nested_constructor': meta.SlotDefinition}[change]
        name = '__init__' if change == 'view_constructor' else '__post_init__'
        original = getattr(cls, name)
        def changed(self, *args, **kwargs):
            original(self, *args, **kwargs)
            if change == 'nested_constructor':
                self.description = 'Changed effective nested constructor'
        monkeypatch.setattr(cls, name, changed)
    elif change == 'view_method':
        original = schema_view._ReleasableView.get_enum
        # The effective descriptor's function can change without its identity.
        function = original.function
        monkeypatch.setattr(original, 'function', lambda self, name, **kw: function(self, name, **kw))
    elif change == 'parser':
        original = schema_view.version_document
        monkeypatch.setattr(schema_view, 'version_document', lambda *a: original(*a))
    else:
        constructors = schema_view.DupCheckYamlLoader.yaml_constructors
        original = constructors['tag:yaml.org,2002:str']
        monkeypatch.setitem(constructors, 'tag:yaml.org,2002:str', lambda *a, **kw: original(*a, **kw))
    built_before = len(calls)
    after = render(raw, path, vocabulary=vocabulary)
    assert len(calls) == built_before + 1
    assert after == history._render_captured(raw, path, 'canonical_paths', vocabulary_bytes=vocabulary)
    if change in ('raw', 'path', 'vocabulary', 'policy', 'full_path', 'universal',
                  'helper', 'helper_code', 'helper_defaults', 'nested_constructor'):
        assert after != before


@pytest.mark.parametrize('raw,vocabulary,family', [
    (b'not: [valid', VOCABULARY, 'canonical_paths'),
    (SCHEMA, None, 'canonical_paths'),
    (SCHEMA, b'vocabularies: false\n', 'canonical_paths'),
    (SCHEMA, b'vocabularies: []\n', 'canonical_paths'),
    (SCHEMA, b'vocabularies:\n  TOPIC: false\n', 'canonical_paths'),
    (SCHEMA, VOCABULARY, 'required_enum40'),
    (SCHEMA + b'imports: [linkml:types]\n', VOCABULARY, 'canonical_paths'),
])
def test_warm_invalid_inputs_preserve_public_exception_and_are_not_retained(raw, vocabulary, family):
    render()
    entries = history._text_cache_info()['entries']
    with pytest.raises(Exception) as original:
        history._render_captured(raw, PATH, family, vocabulary_bytes=vocabulary)
    for _ in range(2):
        with pytest.raises(type(original.value)) as cached:
            render(raw, family=family, vocabulary=vocabulary)
        assert str(cached.value) == str(original.value)
    assert history._text_cache_info()['entries'] == entries


@pytest.mark.parametrize('missing', [False, True])
def test_warm_runtime_is_checked_again(monkeypatch, missing):
    render()
    def unavailable(_):
        if missing:
            raise ModuleNotFoundError('runtime removed')
        return 'unavailable-version'
    monkeypatch.setattr(history, 'version', unavailable)
    with pytest.raises(ModuleNotFoundError if missing else ValueError):
        render()


@pytest.mark.parametrize('change', ['digest', 'schema_hash', 'second_hash', 'path', 'commit',
                                  'source_map', 'vocabulary_pin', 'missing_source', 'missing_vocab'])
def test_warm_text_never_attests_record_or_git_authority(candidate, monkeypatch, change):
    root, record = candidate
    calls = count_inventory(monkeypatch)
    original_git, reads = history._git_blob, []
    def reading(commit, path, root):
        reads.append(path)
        return original_git(commit, path, root)
    monkeypatch.setattr(history, '_git_blob', reading)
    first = history.reconstruct(record, SCHEMA, PATH, git_root=root)
    assert first['status'] == 'reproduced'
    # Returned mutable metadata is owned by the caller, never by the text cache.
    first['candidate']['vocabulary'].clear()
    if change == 'digest': record['schema']['digest_md5'] = '0' * 32
    elif change == 'schema_hash': record['schema']['full_sha256'] = '0' * 64
    elif change == 'second_hash': record['schema']['full_md5'] = '0' * 32
    elif change == 'path': record['schema']['full_path'] = './' + PATH
    elif change == 'commit': record['repo']['commit'] = '0' * 40
    elif change == 'source_map': monkeypatch.setattr(history, 'SOURCE_FAMILIES', {})
    elif change == 'vocabulary_pin': monkeypatch.setattr(history, 'VOCABULARY_SHA256', '0' * 64)
    else:
        absent = history.RENDERER_PATH if change == 'missing_source' else history.VOCABULARY_PATH
        def unavailable(commit, path, root):
            if path == absent: raise ValueError('historical Git object unavailable')
            return reading(commit, path, root)
        monkeypatch.setattr(history, '_git_blob', unavailable)
    after = history.reconstruct(record, SCHEMA, PATH, git_root=root)
    assert after['status'] == ('not_reproduced' if change == 'digest' else 'unavailable')
    assert after['consumed_implementation_identity'] == 'unrecorded'
    assert len(calls) == 1
    if change == 'digest':
        assert len(reads) == 4 and after['candidate']['vocabulary']['sha256']


def test_key_or_accounting_failure_uses_original_path(monkeypatch):
    calls = count_inventory(monkeypatch)
    assert render() == GOLDEN['canonical_paths']
    def unsupported(*args): raise TypeError('unsupported cache state')
    with monkeypatch.context() as patch:
        patch.setattr(history, '_text_key', unsupported)
        assert render() == GOLDEN['canonical_paths']
    history._text_cache_clear()
    monkeypatch.setattr(history, '_text_retained_bytes', unsupported)
    assert render() == GOLDEN['canonical_paths']
    assert len(calls) == 3 and history._text_cache_info()['entries'] == 0


def test_limits_charge_keys_text_and_evict_oldest(monkeypatch):
    calls = count_inventory(monkeypatch)
    monkeypatch.setattr(history, '_TEXT_CACHE_MAX_ENTRIES', 2)
    render(path='one.yaml'); render(path='two.yaml'); render(path='one.yaml')
    assert len(calls) == 2
    render(path='three.yaml')
    assert history._text_cache_info()['entries'] == 2
    render(path='two.yaml')
    assert len(calls) == 4
    key, (text, weight) = next(iter(history._TEXT_CACHE.items()))
    assert weight == history._text_retained_bytes((key, text)) + 256
    assert weight > len(SCHEMA) + len(VOCABULARY) + len(text)
    assert history._text_cache_info()['bytes'] == sum(v[1] for v in history._TEXT_CACHE.values())
    monkeypatch.setattr(history, '_TEXT_CACHE_MAX_ENTRIES', 1)
    render(path='two.yaml')
    assert len(calls) == 4 and history._text_cache_info()['entries'] == 1
    monkeypatch.setattr(history, '_TEXT_CACHE_MAX_BYTES', 0)
    render(path='two.yaml')
    assert len(calls) == 5 and history._text_cache_info()['bytes'] == 0


def test_exact_byte_boundary_oversize_and_byte_eviction(monkeypatch):
    render()
    weight = history._text_cache_info()['bytes']
    history._text_cache_clear()
    monkeypatch.setattr(history, '_TEXT_CACHE_MAX_BYTES', weight - 1)
    assert render() == GOLDEN['canonical_paths']
    assert history._text_cache_info()['entries'] == 0
    monkeypatch.setattr(history, '_TEXT_CACHE_MAX_BYTES', weight)
    assert render() == GOLDEN['canonical_paths']
    assert history._text_cache_info()['entries'] == 1 and history._text_cache_info()['bytes'] == weight
    render(path=PATH.replace('/captured/', '/different/'))
    assert history._text_cache_info()['entries'] <= 1 and history._text_cache_info()['bytes'] <= weight


def test_concurrent_misses_retain_one_immutable_text_and_exact_accounting():
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(lambda _: render(), range(8)))
    assert values == [GOLDEN['canonical_paths']] * 8
    assert history._text_cache_info()['entries'] == 1
    assert history._text_cache_info()['bytes'] == sum(v[1] for v in history._TEXT_CACHE.values())
    assert all(type(value[0]) is str for value in history._TEXT_CACHE.values())


def test_snapshot_survives_mutation_during_warm_git_read(candidate, monkeypatch):
    root, record = candidate
    before = deepcopy(record)
    expected = history.reconstruct(record, SCHEMA, PATH, git_root=root)
    original = history._git_blob
    def mutating(commit, path, root):
        record['schema']['digest_md5'] = '0' * 32
        record['repo']['commit'] = '0' * 40
        return original(commit, path, root)
    monkeypatch.setattr(history, '_git_blob', mutating)
    assert history.reconstruct(record, SCHEMA, PATH, git_root=root) == expected
    assert record != before


def test_actual_git_replacement_still_cannot_redirect_a_warm_candidate(candidate):
    root, record = candidate
    expected = history.reconstruct(record, SCHEMA, PATH, git_root=root)
    original = history._git_blob(record['repo']['commit'], history.RENDERER_PATH, root)
    (root / history.RENDERER_PATH).write_bytes(b'replacement renderer bytes\n')
    subprocess.check_call(['git', '-C', str(root), 'add', '.'])
    subprocess.check_call(['git', '-C', str(root), '-c', 'user.name=Fixture',
                           '-c', 'user.email=fixture@example.org', 'commit', '-qm', 'replacement'])
    replacement = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD']).decode().strip()
    subprocess.check_call(['git', '-C', str(root), 'replace', record['repo']['commit'], replacement])
    redirected = subprocess.check_output(['git', '-C', str(root), 'show',
        record['repo']['commit'] + ':' + history.RENDERER_PATH])
    assert redirected != original[0]
    assert history.reconstruct(record, SCHEMA, PATH, git_root=root) == expected
