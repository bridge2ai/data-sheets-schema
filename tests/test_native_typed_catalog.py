"""Warm native catalog behavior against the literal 1083 typed entry point.

The small selection adapter is a pure test fixture, not a native run claim.
The genuine archived product control is retained separately by the author.
"""
import __future__
import builtins
from contextlib import contextmanager
from dataclasses import replace
import io
import json
from pathlib import Path
import sys
import types

import pytest
from data_sheets_schema import typed_audit as typed, audit_omissions as omissions
from data_sheets_schema import native_catalog_reuse as guard, native_shared_receipts as nr
from data_sheets_schema import native_shared_contract as contract
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_typed_audit import supplied

# Exact function from 1083b0e19cf169aefd947fde762c614fd240ae37.
PARENT_PREPARE = 'def prepare(*, protocol, original_full, bundle, manifest, receipt, context, schema_path,\n            max_output_tokens, original_core=None, source_manifest=None, project=None,\n            max_request_bytes=32_000_000, max_paths=96, max_inventory_bytes=16384, max_workers=16,\n            schema_snapshot=None, derivations=None, captured_assets=None):\n    """Capture a new packet; no saved response or self-reported success is trusted."""\n    if audit_protocol.select(protocol)["protocol"] != audit_protocol.TYPED:\n        raise ValueError("this consumer requires explicitly selected typed_audit_protocol_v1")\n    inputs = {key: _blob(value) for key, value in dict(original_full=original_full,\n        bundle=bundle, manifest=manifest, receipt=receipt, context=context,\n        original_core=original_core, source_manifest=source_manifest).items() if value is not None}\n    _schema_reuse = None\n    if schema_snapshot is not None:\n        # This first constructor verifies exact transitive\n        # closure/root identity from these bytes, with no ambient import reads.\n        catalog = omissions._schema(Path(schema_path), schema_snapshot=schema_snapshot,\n                                    logical_paths=captured_assets is not None)\n        rows = _snapshot_rows(schema_snapshot)\n        if captured_assets is not None:\n            _schema_reuse = _SchemaReuse(schema_snapshot.sources, catalog)\n    elif captured_assets is not None:\n        raise ValueError("captured omission assets require the explicit captured schema closure")\n    else:\n        rows = _snapshot_rows(_capture(Path(schema_path)))\n    limits = dict(max_output_tokens=max_output_tokens, max_request_bytes=max_request_bytes,\n                  max_paths=max_paths, max_inventory_bytes=max_inventory_bytes, max_workers=max_workers)\n    derived, _, _ = _derive(inputs, rows, project, limits, derivations=derivations, captured_assets=captured_assets, _schema_reuse=_schema_reuse)\n    packet = _seal(dict(kind=PACKET, protocol=audit_protocol.select(protocol), inputs=inputs,\n        schema_sources=rows, project=project, limits=limits, **derived, limitations=list(LIMITATIONS)))\n    _bounded_json(_json(packet), "packet", MAX_PACKET_BYTES)\n    for worker in packet["plan"]["workers"]:\n        worker_request(packet, worker["id"], derivations=derivations, captured_assets=captured_assets)\n    return packet'


def parent():
    old = types.ModuleType('literal1083_typed_prepare')
    old.__dict__.update(vars(typed))
    exec(compile(PARENT_PREPARE, '<literal1083 typed.prepare>', 'exec',
                 flags=__future__.annotations.compiler_flag), old.__dict__)
    return old


def selected(snapshot):
    sources = tuple(contract.CapturedArtifact(contract.ArtifactPin('full:'+str(i),
        str(path), len(raw), contract.sha(raw)), raw) for i, (_name, path, raw) in enumerate(snapshot.sources))
    roles = tuple((name, source.pin.role) for (name, _path, _raw), source in zip(snapshot.sources, sources))
    closure = contract.SchemaClosureCapture(contract.schema_closure_sha(sources, roles), roles,
        'full', 'Dataset', snapshot.sources[0][0], sources)
    declaration = {'root': sources[0].pin.path, 'root_class': 'Dataset', 'sources': [
        {'name': name, 'path': source.pin.path, 'bytes': source.pin.bytes, 'sha256': source.pin.sha256}
        for (name, _path, _raw), source in zip(snapshot.sources, sources)]}
    return types.SimpleNamespace(schemas=(closure,), bounds=lambda:dict(contract.BOUND_CEILINGS),
        document=lambda:{'inputs': {'full_schema': declaration}})


@pytest.fixture
def ready(supplied):
    root = supplied['schema_path']
    root.write_text('id: https://example.test/typed\nname: typed\ndefault_range: string\nclasses:\n  Dataset:\n    attributes:\n      name: {}\n      description: {}\n')
    snapshot = typed._snapshot(typed._snapshot_rows(capture_schema(root, strict=True)))
    choice = selected(snapshot)
    snapshot = nr.schema_snapshot(choice)
    supplied.update(schema_snapshot=snapshot,
        captured_assets=tuple((name, omissions._asset(name)) for name in omissions.ASSET_SHA256))
    context = nr._ReceiptCatalogContext()
    context.catalog(choice, snapshot)
    assert context._typed_marker is not None
    assert context._typed_catalog(choice, root, snapshot) is not None
    return supplied, choice, context


@contextmanager
def constructions():
    rows = []
    def event(frame, event, arg):
        if event == 'call' and frame.f_code is omissions._schema_product.__code__:
            rows.append((frame.f_locals.get('logical_paths'), frame.f_locals.get('with_root_bases')))
    previous = sys.getprofile()
    sys.setprofile(event)
    try:
        yield rows
    finally:
        sys.setprofile(previous)


def run(args, choice, context, *, original=False, public=False):
    if original:
        old = parent()
        return old.prepare(**args, derivations=old.DerivationCache())
    if public:
        return typed.prepare(**args, derivations=typed.DerivationCache())
    return typed._prepare(**args, derivations=typed.DerivationCache(),
        _catalog_lookup=guard._CatalogLookup(context, choice))


def error(call):
    try:
        call()
    except Exception as exc:
        def sig(value):
            return (type(value).__module__, type(value).__qualname__, str(value),
                    sig(value.__cause__) if value.__cause__ else None)
        return sig(exc)
    pytest.fail('expected a refusal')


def test_warm_private_reuse_skips_only_initial_constructor_and_detaches_products(ready):
    args, choice, context = ready
    with constructions() as baseline:
        expected = run(args, choice, context, original=True)
    with constructions() as warm:
        actual = run(args, choice, context)
    assert actual == expected and len(baseline) == 1 and len(warm) == 0
    actual['omission_request']['payload']['schema']['classes'].clear()
    assert run(args, choice, context) == expected
    detached = context._typed_catalog(choice, args['schema_path'], args['schema_snapshot'])
    detached['classes'].clear()
    assert context._typed_catalog(choice, args['schema_path'], args['schema_snapshot'])['classes']
    with constructions() as public:
        assert run(args, choice, context, public=True) == expected
    assert len(public) == 1


@pytest.mark.parametrize('mode', ['cold', 'normalized_path', 'subclass', 'wrong_context', 'physical', 'default', 'lower_bound'])
def test_ineligible_routes_keep_original_output_and_construction(ready, mode, monkeypatch):
    args, choice, context = ready
    args = dict(args)
    if mode == 'cold':
        context = nr._ReceiptCatalogContext()
    elif mode == 'normalized_path':
        args['schema_path'] = str(args['schema_path']).replace('/schema.yaml', '//./schema.yaml')
    elif mode == 'subclass':
        class Name(str):
            pass
        snap = args['schema_snapshot']
        args['schema_snapshot'] = replace(snap, sources=tuple((Name(n), p, b) for n,p,b in snap.sources))
    elif mode == 'wrong_context':
        context = object()
    elif mode == 'physical':
        args['captured_assets'] = None
    elif mode == 'default':
        args.pop('schema_snapshot');args['captured_assets'] = None
    else:
        monkeypatch.setattr(nr, '_CATALOG_PAYLOAD_BYTES', context._bytes - 1)
    with constructions() as before:
        expected = run(args, choice, context, original=True)
    with constructions() as after:
        actual = run(args, choice, context)
    assert actual == expected and before == after and before


@pytest.mark.parametrize('change', ['protocol', 'encoded_input', 'schema_record', 'wrong_path', 'duplicate',
    'record', 'receipt', 'context', 'assets', 'limits', 'changed_schema'])
def test_original_failure_precedence_on_warm_lookup(ready, change):
    args, choice, context = ready
    args = dict(args)
    snap = args['schema_snapshot']
    name, path, raw = snap.sources[0]
    if change == 'protocol':
        args.update(protocol='invalid', original_full=object())
    elif change == 'encoded_input':
        args.update(original_full=object(), schema_path=Path('/wrong'))
    elif change == 'schema_record':
        args['schema_snapshot'] = replace(snap, sources=((name,path,b'['),))
        args['original_full'] = b'['
    elif change == 'wrong_path':
        args['schema_path'] = Path('/wrong')
    elif change == 'duplicate':
        args['schema_snapshot'] = replace(snap, sources=snap.sources+snap.sources)
    elif change in ('record','receipt','context'):
        args[{'record':'original_full'}.get(change, change)] = b'['
    elif change == 'assets':
        args['captured_assets'] = (('policy.md', b'changed'),)
    elif change == 'limits':
        args['max_output_tokens'] = 0
    else:
        args['schema_snapshot'] = replace(snap, sources=((name,path,raw.replace(b'  Dataset:',b'  Other:')),))
    expected = error(lambda:run(args,choice,context,original=True))
    actual = error(lambda:run(args,choice,context))
    assert actual == expected


def test_new_schema_bytes_and_lookup_authority_cannot_reuse_old_catalog(ready):
    args, choice, context = ready
    snap = args['schema_snapshot'];name,path,raw = snap.sources[0]
    updated = replace(snap, sources=((name,path,raw.replace(b'description: {}',b'description: {description: Updated}')),))
    changed = selected(updated)
    newargs = {**args,'schema_snapshot':updated}
    with constructions() as calls:
        actual = run(newargs,changed,context)
    assert len(calls) == 1 and actual == run(newargs,changed,context,original=True)
    assert actual != run(args,choice,context)


def test_changed_runtime_at_fill_never_gets_a_retroactive_marker(ready, monkeypatch):
    args,choice,_ = ready
    original = omissions._schema_with_root_bases
    context = nr._ReceiptCatalogContext()
    with monkeypatch.context() as mutation:
        mutation.setattr(omissions,'_schema_with_root_bases',lambda *a,**k:original(*a,**k))
        context.catalog(choice,args['schema_snapshot'])
        assert context._typed_marker is None
    assert guard.runtime_token() is not None
    assert context._typed_catalog(choice,args['schema_path'],args['schema_snapshot']) is None
    context.catalog(choice,args['schema_snapshot'])
    assert context._typed_marker is None
    with constructions() as calls:
        assert run(args,choice,context) == run(args,choice,context,original=True)
    assert len(calls) == 2


@pytest.mark.parametrize('which', ['schema_wrapper','event_constructor','view_method'])
def test_runtime_mutation_preserves_original_constructor_refusal(ready, monkeypatch, which):
    args,choice,context = ready
    def refuse(*a,**k):
        raise ValueError('actual effective dependency changed')
    if which == 'schema_wrapper':
        monkeypatch.setattr(omissions,'_schema',refuse)
    elif which == 'event_constructor':
        monkeypatch.setattr(guard.yaml.events.ScalarEvent,'__init__',refuse)
    else:
        monkeypatch.setattr(guard.views._ReleasableView,'get_class',refuse)
    assert guard.runtime_token() is None
    expected=error(lambda:run(args,choice,context,original=True))
    assert error(lambda:run(args,choice,context)) == expected


def test_captured_cold_and_ineligible_routes_do_not_add_ambient_reads(ready, monkeypatch):
    args,choice,context=ready
    denied=[]
    def no_read(*a,**k):
        denied.append(a);raise AssertionError('ambient read')
    monkeypatch.setattr(builtins,'open',no_read)
    monkeypatch.setattr(io,'open',no_read)
    monkeypatch.setattr(Path,'resolve',no_read)
    original=run(args,choice,context,original=True)
    assert run(args,choice,context) == original
    assert run(args,choice,nr._ReceiptCatalogContext()) == original
    assert run(args,choice,object()) == original
    assert denied == []
