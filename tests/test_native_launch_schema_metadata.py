"""U3-K schema transfer coverage; no provider/native executable."""
from contextlib import contextmanager
from copy import deepcopy
import os
from pathlib import Path
import sys

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_selection as ordinary
from data_sheets_schema import api_runner as fixture_api
from tests.test_native_shared_selection import declaration, pin, save


@contextmanager
def counted_derivations():
    previous = sys.getprofile()
    calls = []
    def observe(frame, event, argument):
        if (event == 'call' and frame.f_code.co_name == '_schemas'
                and frame.f_code.co_filename.endswith('/native_shared_selection.py')):
            calls.append(frame.f_code.co_filename)
    sys.setprofile(observe)
    try:
        yield calls
    finally:
        sys.setprofile(previous)


def pins():
    return authority.draft._code_pins()


@contextmanager
def loaded(source_pins, *, fixture_roots=True):
    """Isolated schema-root fixture, not full registration admission.

    Real file capture/hash/derivation and A's source guards remain. Reapply only
    the existing declaration fixture's two roots after the verified reload;
    restore them before that source scope exits.
    """
    selected_roots = {name: getattr(fixture_api, name)
                      for name in ('FULL_SCHEMA_PATH', 'CORE_SCHEMA_PATH')}
    with authority.loaded_verified_package_module(
            'data_sheets_schema.native_shared_selection',
            package_sources=source_pins) as module:
        if not fixture_roots:
            yield module
        else:
            from data_sheets_schema import api_runner as loaded_api
            authority.module_source_identity(loaded_api)
            with pytest.MonkeyPatch.context() as roots:
                for name, value in selected_roots.items():
                    roots.setattr(loaded_api, name, value)
                yield module


def warm(module, declaration):
    saved = module.capture(declaration['registration_path'])
    # Accommodate the recognized first-use initialization, then establish a hit.
    saved = module.capture(declaration['registration_path'])
    assert module._schema_dependencies._FUNCTIONS.ready, 'closed dependency registry is not ready'
    assert authority._schema_memo_state(module) is not None, 'recognized dependency state unavailable'
    return saved


def test_two_real_loaded_modules_share_metadata_not_carrier_classes(declaration):
    source_pins = pins()
    with authority.launch_derivations():
        with loaded(source_pins) as first:
            expected = warm(first, declaration)
        with counted_derivations() as calls:
            with loaded(source_pins) as second:
                actual = second.capture(declaration['registration_path'])
                assert not calls
                assert type(actual) is not type(expected)
                assert actual.document() == expected.document()
                assert actual.schemas[0].sources[0].raw == expected.schemas[0].sources[0].raw
        assert first is not second
    assert first._SCHEMA_LAUNCH_CONTEXT is None
    assert second._SCHEMA_LAUNCH_CONTEXT is None
    assert first._SCHEMA_DERIVATIONS.snapshot() == ()
    assert second._SCHEMA_DERIVATIONS.snapshot() == ()


def test_nested_launch_shares_memo_and_next_launch_is_cold(declaration):
    source_pins = pins()
    with authority.launch_derivations():
        outer = authority._LAUNCH_DERIVATIONS.memo
        with loaded(source_pins) as first:
            warm(first, declaration)
        with authority.launch_derivations():
            assert authority._LAUNCH_DERIVATIONS.memo is outer
            with loaded(source_pins) as second, counted_derivations() as calls:
                second.capture(declaration['registration_path'])
                assert not calls
        assert authority._LAUNCH_DERIVATIONS.memo is outer
    assert not hasattr(authority._LAUNCH_DERIVATIONS, 'memo')
    with authority.launch_derivations(), loaded(source_pins) as third:
        with counted_derivations() as calls:
            third.capture(declaration['registration_path'])
            assert calls


def test_exception_clears_transfer_without_exporting_partial_scope(declaration):
    source_pins = pins()
    raw = b'id: https://example.org/failing\nname: failing\n'
    with pytest.raises(RuntimeError, match='body failure'):
        with authority.launch_derivations(), loaded(source_pins) as module:
            warm(module, declaration)
            snapshots = module._schema_dependencies.snapshots
            snapshots._metadata(raw)
            assert snapshots._METADATA_DERIVATIONS.snapshot()
            assert snapshots._metadata.cache_info().currsize > 0
            raise RuntimeError('body failure')
    assert not hasattr(authority._LAUNCH_DERIVATIONS, 'memo')
    assert module._SCHEMA_LAUNCH_CONTEXT is None
    assert module._SCHEMA_DERIVATIONS.snapshot() == ()
    assert snapshots._SCHEMA_LAUNCH_CONTEXT is None
    assert snapshots._schema_dependencies is None
    assert snapshots._METADATA_DERIVATIONS.snapshot() == ()
    assert snapshots._metadata.cache_info().currsize == 0


def test_scoped_rebuild_is_pure_and_unscoped_rebuild_stays_cold(declaration, monkeypatch):
    with authority.launch_derivations(), loaded(pins()) as module:
        saved = warm(module, declaration)
        with monkeypatch.context() as trapped:
            def deny(*args, **kwargs):
                raise AssertionError('rebuild attempted ambient I/O')
            for name in ('read_bytes', 'read_text', 'resolve', 'open', 'stat', 'lstat'):
                trapped.setattr(Path, name, deny)
            trapped.setattr(module, 'resource_path', deny)
            with counted_derivations() as calls:
                assert module.rebuild(saved.registration, saved.authority,
                                      saved.schemas, saved.receipt_policy) == saved
                assert not calls
    saved = ordinary.capture(declaration['registration_path'])
    with counted_derivations() as calls:
        ordinary.rebuild(saved.registration, saved.authority, saved.schemas, saved.receipt_policy)
        ordinary.rebuild(saved.registration, saved.authority, saved.schemas, saved.receipt_policy)
        assert len(calls) == 2


def test_changed_same_size_live_bytes_still_refuse_after_hit(declaration):
    path = Path(declaration['inputs']['full_schema']['root'])
    with authority.launch_derivations(), loaded(pins()) as module:
        warm(module, declaration)
        before = path.stat()
        original = path.read_bytes()
        changed = original.replace(b'Dataset:', b'Awayset:')
        assert len(changed) == len(original) and changed != original
        path.write_bytes(changed)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        with pytest.raises(ValueError, match='bytes differ from their registration'):
            module.capture(declaration['registration_path'])


def test_changed_valid_bytes_rekey_then_missing_class_still_refuses(declaration):
    with authority.launch_derivations(), loaded(pins()) as module:
        warm(module, declaration)
        doc = deepcopy(declaration)
        path = Path(doc['inputs']['full_schema']['root'])
        raw = path.read_bytes() + b'description: updated current schema\n'
        path.write_bytes(raw)
        doc['inputs']['full_schema']['sources'][0].update(pin(path, raw))
        save(doc)
        with counted_derivations() as calls:
            updated = module.capture(doc['registration_path'])
            assert calls
        assert updated.schemas[0].sources[0].raw == raw
        raw = raw.replace(b'Dataset:', b'Awayset:')
        path.write_bytes(raw)
        doc['inputs']['full_schema']['sources'][0].update(pin(path, raw))
        save(doc)
        with pytest.raises(ValueError, match='lacks Dataset'):
            module.capture(doc['registration_path'])


def test_full_package_domain_includes_non_python_pins(declaration):
    first_pins = pins()
    changed = dict(first_pins)
    non_python = next(path for path in changed if not path.endswith('.py'))
    changed[non_python] = '0' * 64 if changed[non_python] != '0' * 64 else '1' * 64
    # This isolates derivation identity, not registration admission. Production
    # registration continues verifying every declared package file separately.
    with authority.launch_derivations():
        with loaded(first_pins) as first:
            warm(first, declaration)
        with loaded(changed) as second, counted_derivations() as calls:
            second.capture(declaration['registration_path'])
            assert calls


def test_original_donor_mutation_cannot_be_rebound_by_new_import(declaration, monkeypatch):
    source_pins = pins()
    with authority.launch_derivations():
        with loaded(source_pins) as first:
            warm(first, declaration)
        original = first._schema_dependencies.snapshots._capture_native_schema
        with monkeypatch.context() as changed:
            def replacement(*args, **kwargs):
                return original(*args, **kwargs)
            changed.setattr(first._schema_dependencies.snapshots, '_capture_native_schema',
                            replacement)
            with pytest.raises(
                ValueError,
                match='verified source module identity or callable code changed',
            ):
                with loaded(source_pins):
                    pass
        original_view = first.captured_view
        with monkeypatch.context() as changed:
            def view_replacement(*args, **kwargs):
                return original_view(*args, **kwargs)
            changed.setattr(first, 'captured_view', view_replacement)
            with loaded(source_pins) as second, counted_derivations() as calls:
                assert second._SCHEMA_LAUNCH_CONTEXT[1] is False
                assert second._schema_dependencies.snapshots._SCHEMA_LAUNCH_CONTEXT[1] is False
                second.capture(declaration['registration_path'])
                assert calls


def test_bound_view_projection_matches_existing_dependency_tuple():
    from data_sheets_schema import native_catalog_reuse as guard
    from data_sheets_schema.cache_dependencies import _schema_state
    assert guard._FUNCTIONS.ready
    assert guard._bound_schema_state() == _schema_state(guard._FUNCTIONS)


def test_changed_imported_capture_alias_disables_local_reuse(declaration, monkeypatch):
    with authority.launch_derivations(), loaded(pins()) as module:
        warm(module, declaration)
        original = module._capture_native_schema
        with monkeypatch.context() as changed:
            def replacement(*args, **kwargs):
                return original(*args, **kwargs)
            changed.setattr(module, '_capture_native_schema', replacement)
            with counted_derivations() as calls:
                module.capture(declaration['registration_path'])
                assert calls


def test_recognized_phase_transition_is_rederived_not_refused(declaration, monkeypatch):
    # Unit-only phase sequencing. Real loaded-module coverage above uses the
    # genuine dependency guard without patches to its acceptance function.
    saved = ordinary.capture(declaration['registration_path'])
    doc = saved.document()
    artifacts = {artifact.pin.role: artifact for artifact in
                 (saved.receipt_policy, *saved.authority,
                  *(item for schema in saved.schemas for item in schema.sources))}
    phases = iter((0, 1, 1, 1))
    tokens = (object(), object())
    def state(**kwargs):
        phase = next(phases, 1)
        return phase, tokens[phase]
    from data_sheets_schema import native_catalog_reuse as guard
    ordinary._SCHEMA_DERIVATIONS.clear()
    try:
        with monkeypatch.context() as changed:
            changed.setattr(ordinary, '_SCHEMA_LAUNCH_CONTEXT', (b'phase-unit', True))
            changed.setattr(ordinary, '_schema_dependencies', guard)
            changed.setattr(ordinary._schema_dependencies, 'schema_derivation_state', state)
            with counted_derivations() as calls:
                assert ordinary._launch_cached_schemas(doc, artifacts) == saved.schemas
                assert len(calls) == 2
                assert ordinary._launch_cached_schemas(doc, artifacts) == saved.schemas
                assert len(calls) == 2
    finally:
        ordinary._SCHEMA_DERIVATIONS.clear()


def test_payload_bound_and_metadata_are_immutable():
    cache = ordinary._SchemaDerivationCache()
    for index in range(3):
        cache.put((str(index).encode(), (b'raw',)), b'metadata')
    rows = cache.snapshot()
    assert type(rows) is tuple and len(rows) == 2
    assert all(type(key[0]) is bytes and type(key[1]) is tuple and type(value) is bytes
               for key, value in rows)
    cache.clear()
    assert cache.snapshot() == ()

@pytest.mark.parametrize('mutation', ('name', 'missing_import', 'unused_source', 'root_class'))
def test_warm_cache_keeps_schema_declaration_refusals(declaration, mutation):
    with authority.launch_derivations(), loaded(pins()) as module:
        warm(module, declaration)
        doc = deepcopy(declaration)
        schema = doc['inputs']['full_schema']
        path = Path(schema['root'])
        if mutation == 'name':
            schema['sources'][0]['name'] = 'foreign_name'
        elif mutation == 'root_class':
            schema['root_class'] = 'ForeignClass'
        elif mutation == 'missing_import':
            raw = path.read_bytes() + b'imports:\n  - uncaptured\n'
            path.write_bytes(raw)
            schema['sources'][0].update(pin(path, raw))
        else:
            extra = path.with_name('unused.yaml')
            raw = b'id: https://example.org/unused\nname: unused\nclasses:\n  Unused: {}\n'
            extra.write_bytes(raw)
            schema['sources'].append({'name': 'unused', **pin(extra, raw)})
        save(doc)
        with pytest.raises(ValueError):
            module.capture(doc['registration_path'])

def test_unscoped_source_load_does_not_initialize_new_guard():
    previous = sys.getprofile()
    calls = []
    def observe(frame, event, argument):
        if (event == 'call' and frame.f_code.co_name == '_bind'
                and frame.f_code.co_filename.endswith('/native_catalog_reuse.py')):
            calls.append(frame.f_code.co_filename)
    sys.setprofile(observe)
    try:
        with loaded(pins(), fixture_roots=False) as module:
            assert module._SCHEMA_LAUNCH_CONTEXT is None
            assert module._schema_dependencies is None
        assert not calls
    finally:
        sys.setprofile(previous)


def test_nested_changed_domain_cannot_inherit_or_restore_original_cache(declaration):
    original = pins()
    changed = dict(original)
    non_python = next(path for path in changed if not path.endswith('.py'))
    changed[non_python] = '0' * 64 if changed[non_python] != '0' * 64 else '1' * 64
    with authority.launch_derivations(), loaded(original) as first:
        warm(first, declaration)
        with loaded(changed) as nested, counted_derivations() as calls:
            assert nested is first
            assert nested._SCHEMA_LAUNCH_CONTEXT[1] is False
            assert nested._schema_dependencies.snapshots._SCHEMA_LAUNCH_CONTEXT[1] is False
            nested.capture(declaration['registration_path'])
            assert calls
        assert first._SCHEMA_LAUNCH_CONTEXT[1] is False
        assert first._schema_dependencies.snapshots._SCHEMA_LAUNCH_CONTEXT[1] is False
        with counted_derivations() as calls:
            first.capture(declaration['registration_path'])
            assert calls


def test_unready_guard_is_cold_and_cannot_satisfy_hit_canary(declaration, monkeypatch):
    with authority.launch_derivations(), loaded(pins()) as module:
        warm(module, declaration)
        with monkeypatch.context() as changed:
            changed.setattr(module._schema_dependencies._FUNCTIONS, 'ready', False)
            assert authority._schema_memo_state(module) is None
            with counted_derivations() as calls:
                module.capture(declaration['registration_path'])
                assert calls


@pytest.mark.parametrize('dependency', ('normpath', 'abspath', 'posixpath_os', 'Namespaces', 'deepcopy'))
def test_warm_pure_rebuild_keeps_effective_producer_refusal(
        declaration, monkeypatch, dependency):
    doc = deepcopy(declaration)
    schema = doc['inputs']['full_schema']
    root = Path(schema['root'])
    child = root.with_name('included.yaml')
    child_raw = b'id: https://example.org/included\nname: included\nclasses:\n  Included: {}\n'
    child.write_bytes(child_raw)
    raw = root.read_bytes() + b'imports:\n  - included\n'
    root.write_bytes(raw)
    schema['sources'][0].update(pin(root, raw))
    schema['sources'].append({'name': 'included', **pin(child, child_raw)})
    save(doc)
    with authority.launch_derivations(), loaded(pins()) as module:
        saved = warm(module, doc)
        artifacts = {artifact.pin.role: artifact for artifact in
                     (saved.receipt_policy, *saved.authority,
                      *(item for closure in saved.schemas for item in closure.sources))}
        snapshots = module._schema_dependencies.snapshots
        with monkeypatch.context() as changed:
            def reject(*args, **kwargs):
                raise ValueError('effective producer dependency refused')
            if dependency in ('normpath', 'abspath'):
                changed.setattr(snapshots.os.path, dependency, reject)
            elif dependency == 'posixpath_os':
                real_os = snapshots.os

                class _StrBytesOnlyOS:
                    def __getattr__(self, name):
                        return getattr(real_os, name)

                    @staticmethod
                    def fspath(value):
                        if isinstance(value, (str, bytes)):
                            return value
                        if isinstance(value, real_os.PathLike):
                            reject(value)
                        return real_os.fspath(value)

                changed.setattr(snapshots.os.path, 'os', _StrBytesOnlyOS())
                assert snapshots.os.path.abspath(str(root)) == str(root)
                assert snapshots.os.path.abspath(real_os.fsencode(str(root))) == real_os.fsencode(str(root))
            elif dependency == 'Namespaces':
                changed.setattr(snapshots, 'Namespaces', reject)
            else:
                changed.setitem(module._schema_dependencies.copy._deepcopy_dispatch, dict, reject)
            assert authority._schema_memo_state(module) is None
            with pytest.raises(ValueError) as cold:
                module._schemas(saved.document(), artifacts)
            with pytest.raises(ValueError) as warm_failure:
                module.rebuild(saved.registration, saved.authority,
                               saved.schemas, saved.receipt_policy)
            assert str(warm_failure.value) == str(cold.value)


@contextmanager
def counted_metadata_calls():
    previous = sys.getprofile()
    calls = {'safe_load': 0, 'metadata_document': 0}
    def observe(frame, event, argument):
        if event != 'call':
            return
        name = frame.f_code.co_name
        filename = frame.f_code.co_filename
        if name == 'safe_load' and filename.endswith('/yaml/__init__.py'):
            calls['safe_load'] += 1
        elif name == '_metadata_document' and filename.endswith('/schema_snapshot.py'):
            calls['metadata_document'] += 1
    sys.setprofile(observe)
    try:
        yield calls
    finally:
        sys.setprofile(previous)


def test_cross_loaded_module_metadata_reuses_yaml_parse_and_preserves_prefix_order(declaration):
    source_pins = pins()
    raw = (
        b'id: https://example.org/ordered\n'
        b'name: ordered\n'
        b'imports:\n  - linkml:types\n'
        b'prefixes:\n  z: https://example.org/z/\n  a: https://example.org/a/\n'
        b'default_curi_maps:\n  - semweb_context\n'
        b'classes:\n  Ordered: {}\n'
    )
    with authority.launch_derivations():
        with loaded(source_pins) as first:
            warm(first, declaration)
            first_snapshots = first._schema_dependencies.snapshots
            expected = first_snapshots._metadata(raw)
            assert expected[2] == (
                ('z', 'https://example.org/z/'),
                ('a', 'https://example.org/a/'),
            )
        with loaded(source_pins) as second:
            second_snapshots = second._schema_dependencies.snapshots
            assert second_snapshots is not first_snapshots
            assert second_snapshots._metadata.cache_info().currsize == 0
            with counted_metadata_calls() as calls:
                actual = second_snapshots._metadata(raw)
            assert actual == expected
            assert calls['safe_load'] == 0
            assert calls['metadata_document'] >= 1
            info = second_snapshots._metadata.cache_info()
            assert info.hits == 0 and info.misses == 1
            with counted_metadata_calls() as repeat_calls:
                assert second_snapshots._metadata(raw) == expected
            assert repeat_calls == {'safe_load': 0, 'metadata_document': 0}
            assert second_snapshots._metadata.cache_info().hits == 1
    assert first_snapshots._SCHEMA_LAUNCH_CONTEXT is None
    assert first_snapshots._schema_dependencies is None
    assert first_snapshots._METADATA_DERIVATIONS.snapshot() == ()
    assert first_snapshots._metadata.cache_info().currsize == 0
    assert second_snapshots._SCHEMA_LAUNCH_CONTEXT is None
    assert second_snapshots._schema_dependencies is None
    assert second_snapshots._METADATA_DERIVATIONS.snapshot() == ()
    assert second_snapshots._metadata.cache_info().currsize == 0


def test_same_length_changed_imports_and_prefixes_miss_metadata_transfer(declaration):
    source_pins = pins()
    base = (
        b'id: https://example.org/schema\n'
        b'name: schema\n'
        b'imports:\n  - alpha\n'
        b'prefixes:\n  z: https://example.org/z/\n'
    )
    changed_imports = base.replace(b'  - alpha\n', b'  - bravo\n')
    changed_prefixes = base.replace(b'  z: https://example.org/z/\n', b'  y: https://example.org/y/\n')
    assert len(changed_imports) == len(base)
    assert len(changed_prefixes) == len(base)
    with authority.launch_derivations():
        with loaded(source_pins) as first:
            warm(first, declaration)
            first_snapshots = first._schema_dependencies.snapshots
            first_snapshots._metadata(base)
        with loaded(source_pins) as second:
            second_snapshots = second._schema_dependencies.snapshots
            assert second_snapshots is not first_snapshots
            with counted_metadata_calls() as imp_calls:
                imp_meta = second_snapshots._metadata(changed_imports)
            assert imp_calls['safe_load'] == 1
            assert imp_meta[1] == ('bravo',)
            with counted_metadata_calls() as pref_calls:
                pref_meta = second_snapshots._metadata(changed_prefixes)
            assert pref_calls['safe_load'] == 1
            assert pref_meta[2] == (('y', 'https://example.org/y/'),)


@pytest.mark.parametrize('raw', (
    b'id: 2026-11-10\nname: dated\n',
    b'id: https://example.org/s\nname: s\nimports: !!set {a: null}\n',
    b'id: https://example.org/s\nname: s\nprefixes:\n  1: https://example.org/one/\n',
    b'id: https://example.org/s\nname: s\nprefixes:\n  a: &p\n    prefix_prefix: a\n    prefix_reference: https://example.org/a/\n  b: *p\n',
))
def test_non_json_or_aliased_metadata_fields_take_cold_path_uncached(declaration, raw):
    source_pins = pins()
    with authority.launch_derivations(), loaded(source_pins) as module:
        warm(module, declaration)
        snapshots = module._schema_dependencies.snapshots
        expected_error = None
        expected_value = None
        try:
            expected_value = snapshots._cold_metadata(raw)
        except Exception as exc:
            expected_error = (type(exc), str(exc))
        snapshots._METADATA_DERIVATIONS.clear()
        snapshots._metadata.cache_clear()
        with counted_metadata_calls() as calls:
            if expected_error is None:
                assert snapshots._metadata(raw) == expected_value
            else:
                with pytest.raises(expected_error[0]) as actual_exc:
                    snapshots._metadata(raw)
                assert str(actual_exc.value) == expected_error[1]
        assert calls['safe_load'] == 1
        assert snapshots._METADATA_DERIVATIONS.snapshot() == ()


@pytest.mark.parametrize('target_attr', (
    '_metadata_document', '_encode_metadata_fields', 'SchemaDefinition', 'safe_load',
))
def test_donor_or_parser_mutation_disables_metadata_transfer(declaration, monkeypatch, target_attr):
    source_pins = pins()
    raw = b'id: https://example.org/s\nname: s\nimports:\n  - linkml:types\n'
    with authority.launch_derivations():
        with loaded(source_pins) as first:
            warm(first, declaration)
            first_snapshots = first._schema_dependencies.snapshots
            first_snapshots._metadata(raw)
        owner = first_snapshots.yaml if target_attr == 'safe_load' else first_snapshots
        original = getattr(owner, target_attr)
        with monkeypatch.context() as changed:
            def replacement(*args, **kwargs):
                return original(*args, **kwargs)
            changed.setattr(owner, target_attr, replacement)
            if target_attr in ('_metadata_document', '_encode_metadata_fields'):
                with pytest.raises(
                    ValueError,
                    match='verified source module identity or callable code changed',
                ):
                    with loaded(source_pins):
                        pass
            else:
                with loaded(source_pins) as second:
                    second_snapshots = second._schema_dependencies.snapshots
                    assert second_snapshots is not first_snapshots
                    assert second_snapshots._SCHEMA_LAUNCH_CONTEXT[1] is False
                    with counted_metadata_calls() as calls:
                        second_snapshots._metadata(raw)
                    assert calls['safe_load'] == 1


def test_tampered_snapshot_binding_refuses_source_identity(monkeypatch):
    with authority.launch_derivations(), loaded(pins(), fixture_roots=False) as module:
        snapshots = module._schema_dependencies.snapshots
        with monkeypatch.context() as changed:
            changed.setattr(snapshots, '_SCHEMA_LAUNCH_CONTEXT', (b'forged', True))
            with pytest.raises(ValueError, match='verified schema transfer context changed'):
                authority.module_source_identity(snapshots)


def test_context_transitions_retire_local_metadata_lru_on_retained_module(declaration, monkeypatch):
    original = pins()
    changed = dict(original)
    non_python = next(path for path in changed if not path.endswith('.py'))
    changed[non_python] = '0' * 64 if changed[non_python] != '0' * 64 else '1' * 64
    raw = b'id: https://example.org/retained\nname: retained\n'
    with authority.launch_derivations(), loaded(original) as first:
        warm(first, declaration)
        snapshots = first._schema_dependencies.snapshots
        snapshots._metadata(raw)
        assert snapshots._metadata.cache_info().currsize > 0
        with loaded(original) as same_domain:
            assert same_domain is first
            assert same_domain._schema_dependencies.snapshots is snapshots
            assert snapshots._metadata.cache_info().currsize > 0
        original_safe_load = snapshots.yaml.safe_load
        with monkeypatch.context() as mutated:
            def replacement(*args, **kwargs):
                return original_safe_load(*args, **kwargs)
            mutated.setattr(snapshots.yaml, 'safe_load', replacement)
            with loaded(original) as same_domain_mutated:
                assert same_domain_mutated is first
                assert same_domain_mutated._schema_dependencies.snapshots is snapshots
                assert snapshots._METADATA_DERIVATIONS.snapshot() == ()
                assert snapshots._metadata.cache_info().currsize == 0
                with counted_metadata_calls() as mutated_calls:
                    assert snapshots._metadata(raw)[0] == 'retained'
                assert mutated_calls['safe_load'] == 1
        snapshots._metadata(raw)
        assert snapshots._metadata.cache_info().currsize > 0
        with loaded(changed) as nested:
            assert nested is first
            assert nested._schema_dependencies.snapshots is snapshots
            assert snapshots._SCHEMA_LAUNCH_CONTEXT[1] is False
            assert snapshots._METADATA_DERIVATIONS.snapshot() == ()
            assert snapshots._metadata.cache_info().currsize == 0
            with counted_metadata_calls() as nested_calls:
                assert snapshots._metadata(raw)[0] == 'retained'
            assert nested_calls['safe_load'] == 1
    assert snapshots._metadata.cache_info().currsize == 0


def test_metadata_cache_two_entry_bound_and_three_document_eviction(declaration):
    source_pins = pins()
    docs = tuple(
        f'id: https://example.org/doc{i}\nname: doc{i}\n'.encode('utf-8')
        for i in range(3)
    )
    with authority.launch_derivations():
        with loaded(source_pins) as first:
            warm(first, declaration)
            expected_schema_rows = first._SCHEMA_DERIVATIONS.snapshot()
            assert expected_schema_rows
            first_snapshots = first._schema_dependencies.snapshots
            for raw in docs:
                first_snapshots._metadata(raw)
            assert first._SCHEMA_DERIVATIONS.snapshot() == expected_schema_rows
            assert len(first_snapshots._METADATA_DERIVATIONS.snapshot()) == 2
        with loaded(source_pins) as second:
            second_snapshots = second._schema_dependencies.snapshots
            assert second_snapshots is not first_snapshots
            assert second._SCHEMA_DERIVATIONS.snapshot() == expected_schema_rows
            assert len(second_snapshots._METADATA_DERIVATIONS.snapshot()) == 2
            with counted_metadata_calls() as warm_calls:
                assert second_snapshots._metadata(docs[1])[0] == 'doc1'
                assert second_snapshots._metadata(docs[2])[0] == 'doc2'
            assert warm_calls['safe_load'] == 0
            with counted_metadata_calls() as evicted_calls:
                assert second_snapshots._metadata(docs[0])[0] == 'doc0'
            assert evicted_calls['safe_load'] == 1
