"""Pure schema reuse inside owner joins, never cached admission.

One actual ordinary-peer initialized run supplies the live call-path pool. The
other controls use the existing explicitly invented selected saved checkpoint.
No count or timing here establishes full-schema helper or deadline acceptance.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace

import pytest

from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_registration as registration
from data_sheets_schema import native_shared_results as results
from data_sheets_schema import native_shared_selection as selected
from tests.test_native_owner_adapter_capture import (
    adapter_case, adapter_factory, run_to_terminal_refusal)
from tests.test_native_owner_initialized_capture import (
    artifact, member, pool_member, replace_pool_member, selected_case,
    initialized_case, initial_v1)
from tests.test_native_owner_runner import fixed_clock
from tests.test_native_shared_live_capture import started
from tests.test_native_shared_registration import execution, bound, native_spec, declaration
from tests.test_native_shared_schema_derivation_once import _no_io


def fresh_cache(monkeypatch):
    """Counter delegates to the real graph/view, after all fixture setup."""
    cache = selected._SchemaDerivationCache()
    monkeypatch.setattr(selected, '_SCHEMA_DERIVATIONS', cache)
    views = []
    actual = selected.captured_view

    @contextmanager
    def observed(snapshot):
        views.append(str(snapshot.sources[0][1]))
        with actual(snapshot) as view:
            yield view

    monkeypatch.setattr(selected, 'captured_view', observed)
    return cache, views


@contextmanager
def saved_only(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('pure owner reconstruction attempted live authority or I/O')
    with monkeypatch.context() as patch:
        _no_io(patch)
        patch.setattr(evidence, 'read_regular', forbidden)
        patch.setattr(selected, 'capture', forbidden)
        for name in ('dependency_identity', 'require_committed', 'loaded_dependencies'):
            patch.setattr(authority, name, forbidden)
        for name in ('verified', '_verified_in_scope'):
            patch.setattr(registration, name, forbidden)
        yield


def owner_join(case):
    return capture._saved_owner_execution(case['selection'], case['pool'],
                                          case['artifacts']['execution'])


def selection_artifacts(selection):
    return {item.pin.role: item for item in (selection.receipt_policy, *selection.authority,
            *(source for schema in selection.schemas for source in schema.sources))}


def readdress_selection(case, *, replacements=None, edit_document=None, mutations=None):
    """Change detached S inputs and honestly rehash C/E/owner/checkpoint joins.

    Declared schema carriers are intentionally not a validation substitute:
    malformed variants must reach real fresh/warm reconstruction below.
    """
    saved = case['selection']
    artifacts = selection_artifacts(saved)
    doc = saved.document()
    for role, raw in (replacements or {}).items():
        previous = artifacts[role]
        assert type(raw) is bytes and raw != previous.raw
        changed = artifact(role, previous.pin.path, raw)
        artifacts[role] = changed
        pin = {name: getattr(changed.pin, name) for name in ('path', 'bytes', 'sha256')}
        if role.startswith(('full_schema:', 'core_schema:')):
            kind, ordinal = role.split(':')
            doc['inputs'][kind]['sources'][int(ordinal)].update(pin)
        elif role == 'receipt_policy':
            doc[role] = pin
        else:
            doc['inputs'][role] = pin
    if edit_document is not None:
        edit_document(doc)
    raw = c.canonical(doc)
    assert raw != saved.registration.raw
    new_selection = replace(saved,
        registration=artifact('selection', saved.registration.pin.path, raw),
        authority=tuple(artifacts[a.pin.role] for a in saved.authority),
        receipt_policy=artifacts['receipt_policy'],
        schemas=selected._declared_schemas(doc, artifacts),
        bounds_json=c.canonical(doc['bounds']))
    changed = selected_case(case['baseline'], selection=new_selection, mutations=mutations)
    pool = changed['pool']
    for role, item in artifacts.items():
        old = pool_member(pool, role, item.pin.path)
        if old.captured != item:
            pool = replace_pool_member(pool, old, member(item, old))
    changed['pool'] = pool
    assert pool.encode() != case['pool'].encode()
    return changed


def same_selection_refusal(case):
    """Actual uncached oracle and optimized owner path share S refusal."""
    with pytest.raises(ValueError) as fresh:
        capture._saved_selection(case['pool'], case['value'])
    with pytest.raises(ValueError) as warm:
        owner_join(case)
    assert type(warm.value) is type(fresh.value)
    assert str(warm.value) == str(fresh.value)
    return str(warm.value)


def test_actual_initialized_owner_reuses_only_pure_schema_views(adapter_case, monkeypatch):
    """Actual pool may include later buffered stream bytes: no saved-init claim."""
    retained = []
    actual = adapter_case['adapter']._run
    def remember(endpoints=None, **kwargs):
        run = actual(endpoints, **kwargs)
        if not retained:
            assert type(run) is capture._CapturedRun
            assert len(run.history.records) == 2
            assert c.strict_json(run.binding.init_observation.raw)['version'] == 2
            retained.append(run)
        return run
    monkeypatch.setattr(adapter_case['adapter'], '_run', remember)
    run_to_terminal_refusal(adapter_case)
    assert len(retained) == 1
    run = retained[0]
    encoded = run.pool.encode()
    cache, views = fresh_cache(monkeypatch)
    expected_roots = [run.selection.document()['inputs'][k + '_schema']['root']
                      for k in ('full', 'core')]
    with saved_only(monkeypatch):
        first = capture._saved_owner_execution(run.selection, run.pool, run.binding.execution)
        assert first == (run.value, run.composition)
        assert views == expected_roots
        second = capture._saved_owner_execution(run.selection, run.pool, run.binding.execution)
        assert second == first and second[0] is not first[0] and second[1] is not first[1]
        assert views == expected_roots
        second[0]['runtime']['model'] = 'changed detached return'
        second[1]['policy'].clear()
        assert capture._saved_owner_execution(run.selection, run.pool, run.binding.execution) == first
        assert views == expected_roots
    assert run.pool.encode() == encoded
    assert len(cache._entries) == 1
    assert all(type(metadata) is bytes for metadata, _ in cache._entries.values())


def test_selected_saved_entry_always_derives_fresh_graphs(initialized_case, monkeypatch):
    case = initialized_case
    encoded = case['pool'].encode()
    _, views = fresh_cache(monkeypatch)
    with saved_only(monkeypatch):
        assert owner_join(case) == (case['value'], case['composition'])
        assert len(views) == 2
        for _ in range(2):
            before = len(views)
            assert capture._saved_selection(case['pool'], case['value']) == case['selection']
            assert len(views) == before + 2
        documents = []
        for _ in range(2):
            before = len(views)
            result = results.rebuild(case['pool'], case['value'])
            assert type(result) is results._OwnerInitializationEvidence
            assert len(views) == before + 2
            assert not any(hasattr(result, name) for name in ('reader', 'selection', 'decision', 'binding'))
            documents.append(result.as_dict())
        assert documents[0] == documents[1]
        assert documents[0]['counts'] == {'members': len(case['pool'].members),
            'raw_bytes': sum(len(row.captured.raw) for row in case['pool'].members),
            'observations': 1, 'history_records': 2}
    assert case['pool'].encode() == encoded


def test_warm_owner_reextracts_current_pool_and_checks_supplied_projection(initialized_case, monkeypatch):
    case = initialized_case
    _, views = fresh_cache(monkeypatch)
    with saved_only(monkeypatch):
        assert owner_join(case) == (case['value'], case['composition'])
        original_views = len(views)
        target = pool_member(case['pool'], 'context')
        metadata = c.strict_json(target.metadata_json); metadata['mtime_ns'] += 1
        duplicate = evidence.PoolMember(target.captured, c.canonical(metadata))
        assert duplicate.member_id != target.member_id
        variants = {
            'missing': evidence.CapturePool(tuple(m for m in case['pool'].members if m is not target),
                                           case['pool'].stream_bindings),
            'duplicate-role-path': evidence.CapturePool(case['pool'].members + (duplicate,),
                                                      case['pool'].stream_bindings),
            'changed-raw-unregistered': replace_pool_member(case['pool'], target,
                member(artifact('context', target.captured.pin.path, target.captured.raw + b'\n'), target)),
        }
        for label, pool in variants.items():
            assert pool.encode() != case['pool'].encode(), label
            changed = {**case, 'pool': pool}
            assert same_selection_refusal(changed), label
        assert len(views) == original_views  # All three fail before schema derivation.
        schema = case['selection'].schemas[0]
        imports = (('foreign-projection', schema.import_roles[0][1]), *schema.import_roles[1:])
        changed_schema = replace(schema, root_name='foreign-projection', import_roles=imports,
                                 closure_sha256=c.schema_closure_sha(schema.sources, imports))
        projection = replace(case['selection'], schemas=(changed_schema, *case['selection'].schemas[1:]))
        assert projection != case['selection']
        with pytest.raises(ValueError, match='complete captured reconstruction'):
            capture._saved_owner_execution(projection, case['pool'], case['artifacts']['execution'])
        assert len(views) == original_views
        assert owner_join(case) == (case['value'], case['composition'])


def test_warm_schema_does_not_cache_non_schema_authority(initialized_case, monkeypatch):
    case = initialized_case
    context = c.strict_json(case['selection'].raw('context'))
    context['scopes'].append(deepcopy(context['scopes'][0]))
    receipt = c.strict_json(case['selection'].receipt_policy.raw)
    receipt['runtime_policy_sha256'] = 'f' * 64
    variants = {
        'context': readdress_selection(case, replacements={'context': c.canonical(context)}),
        'receipt': readdress_selection(case, replacements={'receipt_policy': c.canonical(receipt)}),
    }
    # A declared input larger than its bound cannot be a NativeSelectionCapture.
    # Retain that malformed raw S in the immutable pool and rehash its E/C
    # declarations, instead of bypassing the carrier constructor to invent one.
    bad_doc = case['selection'].document(); bad_doc['bounds']['max_input_bytes'] = 1
    bad_raw = c.canonical(bad_doc)
    assert bad_raw != case['selection'].registration.raw
    bad = selected_case(case['baseline'], mutations={
        'composition': lambda value: value.update(selection_raw_json=bad_raw.decode(),
                                                  selection_sha256=c.sha(bad_raw)),
        'execution': lambda value: value.update(selection_sha256=c.sha(bad_raw))})
    old = pool_member(bad['pool'], 'selection')
    bad['pool'] = replace_pool_member(bad['pool'], old,
        member(artifact('selection', old.captured.pin.path, bad_raw), old))
    variants['bounds'] = bad
    runtime_changed = selected_case(case['baseline'], mutations={
        'execution': lambda value: value['runtime'].update(deadline_seconds=True)})
    assert type(case['value']['runtime']['deadline_seconds']) is int
    assert runtime_changed['artifacts']['execution'].raw != case['artifacts']['execution'].raw
    _, views = fresh_cache(monkeypatch)
    with saved_only(monkeypatch):
        owner_join(case)
        for label, changed in variants.items():
            assert same_selection_refusal(changed), label
        assert len(views) == 2
        with pytest.raises(ValueError, match='runtime bytes, hashes or typed values disagree'):
            owner_join(runtime_changed)
        assert len(views) == 2
        assert owner_join(case) == (case['value'], case['composition'])


def test_readdressed_schema_bytes_miss_warm_owner_key_and_keep_parser_refusal(initialized_case, monkeypatch):
    case = initialized_case
    full = case['selection'].schemas[0].sources[0]
    valid = readdress_selection(case, replacements={full.pin.role: full.raw + b'\n# same-schema semantics\n'})
    broken_raw = full.raw.replace(b'Dataset:', b'AbsentDataset:')
    assert broken_raw != full.raw
    broken = readdress_selection(case, replacements={full.pin.role: broken_raw})
    _, views = fresh_cache(monkeypatch)
    with saved_only(monkeypatch):
        owner_join(case)
        assert len(views) == 2
        assert owner_join(valid) == (valid['value'], valid['composition'])
        assert len(views) == 4
        assert owner_join(valid) == (valid['value'], valid['composition'])
        assert len(views) == 4
        assert 'lacks Dataset' in same_selection_refusal(broken)
        assert len(views) == 6  # Each actual uncached/warm-path failure builds full once.
        assert owner_join(case) == (case['value'], case['composition'])
        assert len(views) == 6


def test_warm_schema_cannot_replace_complete_saved_stream_metadata_join(initialized_case, monkeypatch):
    case = initialized_case
    target = pool_member(case['pool'], 'transcript')
    metadata = c.strict_json(target.metadata_json); metadata['inode'] += 1
    changed_member = evidence.PoolMember(target.captured, c.canonical(metadata))
    pool = replace_pool_member(case['pool'], target, changed_member)
    assert pool.encode() != case['pool'].encode() and changed_member.captured == target.captured
    _, views = fresh_cache(monkeypatch)
    with saved_only(monkeypatch):
        owner_join(case)
        # E/C/S association does not claim physical stream identity. The full
        # saved initialization consumer must still reject its contradictory join.
        assert capture._saved_owner_execution(case['selection'], pool,
            case['artifacts']['execution']) == (case['value'], case['composition'])
        assert len(views) == 2
        with pytest.raises(ValueError):
            results.rebuild(pool, case['value'])
        assert len(views) == 4
        assert results.rebuild(case['pool'], case['value']).as_dict()['scope'] == 'captured_initialization_only'
        assert len(views) == 6
