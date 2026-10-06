"""Same-call catalog reuse against literal 4295709 producer functions."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import types
import __future__

import pytest
from data_sheets_schema import typed_audit as typed, audit_omissions as omissions
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_typed_audit import supplied

PARENT_TYPED = 'class DerivationCache:\n    """Bounded, caller-owned pure packet derivations; never response verdicts.\n\n    Each hit returns decoded private objects, including a NEW frozen Prepared.\n    Final independent checks should receive a fresh instance, so their first\n    derivation is independent of any earlier preparation or runtime cache.\n    """\n    def __init__(self, *, max_entries=8, max_bytes=64_000_000):\n        if (type(max_entries) is not int or not 0 < max_entries <= 32\n                or type(max_bytes) is not int or not 0 < max_bytes <= 128_000_000):\n            raise ValueError(\'derivation cache requires bounded positive integer limits\')\n        self.max_entries, self.max_bytes = max_entries, max_bytes\n        self._rows, self._bytes = {}, 0\n\n    def _derive(self, inputs, schema_rows, project, limits, *, captured_assets=None):\n        def exact_json(value):\n            if type(value) is dict:\n                if any(type(key) is not str for key in value):\n                    raise ValueError(\'derivation cache keys require exact string mapping keys\')\n                for item in value.values():\n                    exact_json(item)\n            elif type(value) is list:\n                for item in value:\n                    exact_json(item)\n            elif type(value) not in (str, int, float, bool, type(None)):\n                raise ValueError(\'derivation cache keys require exact JSON types\')\n        selected = [inputs, schema_rows, project, limits]\n        exact_json(selected)\n        # These bytes are checked on every lookup, not merely when cached.\n        assets = {name: _sha(raw) for name, raw in omissions.captured_asset_bytes(captured_assets).items()}\n        identity = _json([selected, assets] if captured_assets is None else\n                         [\'captured_logical_schema_v1\', selected, assets])\n        key = (len(identity), _sha(identity))\n        encoded = self._rows.get(key)\n        if encoded is None:\n            derived, raw, prepared = _derive(inputs, schema_rows, project, limits, captured_assets=captured_assets)\n            encoded = _json({\'derived\': derived, \'raw\': {name: _blob(value) for name, value in raw.items()},\n                             \'prepared_payload_json\': prepared.payload_json})\n            if len(encoded) <= self.max_bytes:\n                while self._rows and (len(self._rows) >= self.max_entries or self._bytes + len(encoded) > self.max_bytes):\n                    self._bytes -= len(self._rows.pop(next(iter(self._rows))))\n                self._rows[key] = encoded\n                self._bytes += len(encoded)\n        value = json.loads(encoded)\n        return value[\'derived\'], {name: _unblob(blob) for name, blob in value[\'raw\'].items()}, omissions.Prepared(value[\'prepared_payload_json\'])\n\ndef _derive(inputs, schema_rows, project, limits, *, derivations=None, captured_assets=None):\n    if derivations is not None:\n        if type(derivations) is not DerivationCache:\n            raise ValueError(\'derivations must be an explicit DerivationCache\')\n        return derivations._derive(inputs, schema_rows, project, limits, captured_assets=captured_assets)\n    if captured_assets is None:\n        return _derive_uncached(inputs, schema_rows, project, limits)\n    return _derive_uncached(inputs, schema_rows, project, limits, captured_assets=captured_assets)\n\ndef _derive_uncached(inputs, schema_rows, project, limits, *, captured_assets=None):\n    if type(inputs) is not dict or not _REQUIRED <= set(inputs) <= _REQUIRED | _OPTIONAL:\n        raise ValueError("captured input roster differs from protocol")\n    raw = {key: _unblob(value) for key, value in inputs.items()}\n    for key in ("original_full", "original_core"):\n        if key in raw:\n            omissions._mapping(raw[key], key)\n    if ("source_manifest" in raw) != (project is not None):\n        raise ValueError("source manifest and explicit project must be captured together")\n    authority = None\n    if "source_manifest" in raw:\n        authority = _source_authority(raw["source_manifest"], project)\n    _exact(limits, {"max_paths", "max_inventory_bytes", "max_workers", "max_output_tokens", "max_request_bytes"}, "limits")\n    snapshot = _snapshot(schema_rows)\n    prepared = omissions.prepare(record=raw["original_full"], bundle=raw["bundle"],\n        manifest=raw["manifest"], receipt=raw["receipt"], context=raw["context"],\n        schema_path=snapshot.sources[0][1], schema_snapshot=snapshot,\n        max_output_tokens=limits["max_output_tokens"], max_request_bytes=limits["max_request_bytes"],\n        captured_assets=captured_assets)\n    plan = batches.make_plan(raw["original_full"].decode("utf-8"), version=2,\n        **{k: limits[k] for k in ("max_paths", "max_inventory_bytes", "max_workers")})\n    contracts = {stage: {"contract": output_format.contract(stage, version=2),\n                         "rendered": output_format.render(stage, version=2),\n                         "saved_response": {"kind": f"typed_audit_{stage}_response_v1",\n                             "required_fields": ["kind", "packet_sha256", "request_sha256", "response",\n                                                 "worker_id" if stage == "worker" else "typed_index_sha256"],\n                             "response_encoding": "Exact UTF-8 inner JSON bytes as base64, sha256 and bytes.",\n                             "authority": "A declared request/response association, not provider authentication."}}\n                 for stage in ("worker", "integration")}\n    shared = _json({"protocol": audit_protocol.select(audit_protocol.TYPED),\n        "original_full": raw["original_full"].decode("utf-8"),\n        "original_core": raw.get("original_core", b"").decode("utf-8") or None,\n        "bundle": raw["bundle"].decode("utf-8"), "manifest": raw["manifest"].decode("utf-8"),\n        "receipt": raw["receipt"].decode("utf-8"), "context": prepared.request()["payload"]["context"],\n        "schema": prepared.request()["payload"]["schema"], "registered_provenance": authority}).decode("utf-8")\n    workers = {worker["id"]: _json({"stage": "worker", "shared_context_sha256": _sha(shared.encode()),\n        "plan_sha256": plan["sha256"], "assignment": worker, "inventory": plan["inventory"],\n        "output_contract": contracts["worker"]}).decode("utf-8") for worker in plan["workers"]}\n    for tail in workers.values():\n        if len((shared + tail).encode()) > limits["max_request_bytes"]:\n            raise ValueError("complete worker request exceeds max_request_bytes")\n    return {"plan": plan, "omission_request": prepared.request(), "contracts": contracts,\n            "requests": {"assembly_rule": "shared_context UTF-8 bytes followed by the selected stage UTF-8 bytes",\n                         "shared_context": shared, "workers": workers},\n            "registered_provenance": authority}, raw, prepared\n\ndef prepare(*, protocol, original_full, bundle, manifest, receipt, context, schema_path,\n            max_output_tokens, original_core=None, source_manifest=None, project=None,\n            max_request_bytes=32_000_000, max_paths=96, max_inventory_bytes=16384, max_workers=16,\n            schema_snapshot=None, derivations=None, captured_assets=None):\n    """Capture a new packet; no saved response or self-reported success is trusted."""\n    if audit_protocol.select(protocol)["protocol"] != audit_protocol.TYPED:\n        raise ValueError("this consumer requires explicitly selected typed_audit_protocol_v1")\n    inputs = {key: _blob(value) for key, value in dict(original_full=original_full,\n        bundle=bundle, manifest=manifest, receipt=receipt, context=context,\n        original_core=original_core, source_manifest=source_manifest).items() if value is not None}\n    if schema_snapshot is not None:\n        # The omission constructor independently verifies exact transitive\n        # closure/root identity from these bytes, with no ambient import reads.\n        omissions._schema(Path(schema_path), schema_snapshot=schema_snapshot,\n                          logical_paths=captured_assets is not None)\n        rows = _snapshot_rows(schema_snapshot)\n    elif captured_assets is not None:\n        raise ValueError("captured omission assets require the explicit captured schema closure")\n    else:\n        rows = _snapshot_rows(_capture(Path(schema_path)))\n    limits = dict(max_output_tokens=max_output_tokens, max_request_bytes=max_request_bytes,\n                  max_paths=max_paths, max_inventory_bytes=max_inventory_bytes, max_workers=max_workers)\n    derived, _, _ = _derive(inputs, rows, project, limits, derivations=derivations, captured_assets=captured_assets)\n    packet = _seal(dict(kind=PACKET, protocol=audit_protocol.select(protocol), inputs=inputs,\n        schema_sources=rows, project=project, limits=limits, **derived, limitations=list(LIMITATIONS)))\n    _bounded_json(_json(packet), "packet", MAX_PACKET_BYTES)\n    for worker in packet["plan"]["workers"]:\n        worker_request(packet, worker["id"], derivations=derivations, captured_assets=captured_assets)\n    return packet\n\ndef _open(packet, *, derivations=None, captured_assets=None):\n    _exact(packet, {"kind", "protocol", "inputs", "schema_sources", "project", "limits", "plan",\n        "omission_request", "contracts", "requests", "registered_provenance", "limitations", "sha256"}, "packet")\n    if len(_json(packet)) > MAX_PACKET_BYTES or packet["kind"] != PACKET or _json(packet["protocol"]) != _json(audit_protocol.select(audit_protocol.TYPED)):\n        raise ValueError("packet protocol/size mismatch")\n    derived, raw, prepared = _derive(packet["inputs"], packet["schema_sources"], packet["project"], packet["limits"], derivations=derivations, captured_assets=captured_assets)\n    expected = _seal({**{key: packet[key] for key in ("kind", "protocol", "inputs", "schema_sources", "project", "limits")},\n                      **derived, "limitations": list(LIMITATIONS)})\n    if _json(packet) != _json(expected):\n        raise ValueError("packet request/plan/contract/input identity mismatch")\n    return raw, prepared\n\ndef worker_request(packet, worker_id, *, derivations=None, captured_assets=None):\n    """Export a request after packet sealing; identity hashes its exact payload."""\n    _open(packet, derivations=derivations, captured_assets=captured_assets)\n    if type(worker_id) is not str or worker_id not in packet["requests"]["workers"]:\n        raise ValueError("unknown worker request")\n    payload = {"packet_sha256": packet["sha256"], "worker_id": worker_id,\n        "shared_context": packet["requests"]["shared_context"],\n        "stage": packet["requests"]["workers"][worker_id]}\n    request = {"kind": "typed_audit_worker_request_v1", "payload": payload,\n               "request_sha256": _sha(_json(payload))}\n    if len(_json(request)) > packet["limits"]["max_request_bytes"]:\n        raise ValueError("complete worker request exceeds max_request_bytes")\n    return request'

PARENT_OMISSIONS = 'def prepare(*, record: bytes, bundle: bytes, manifest: bytes, receipt: bytes,\n            context: bytes, schema_path: Path, max_output_tokens: int, schema_snapshot=None,\n            max_request_bytes: int = 32_000_000, captured_assets=None) -> Prepared:\n    """Read schema once, capture input bytes, render no transport-specific call."""\n    if any(type(n) is not int or n < 1 for n in (max_output_tokens, max_request_bytes)):\n        raise ValueError("request/output limits must be explicit positive integers")\n    assets = captured_asset_bytes(captured_assets)\n    policy = assets["policy.md"].decode("utf-8")\n    response_schema = json.loads(assets["response.schema.json"])\n    context_schema = json.loads(assets["context.schema.json"])\n    document = _mapping(record, "record")\n    receipt_doc = _mapping(receipt, "receipt")\n    _mapping(manifest, "manifest")\n    context_doc = _mapping(context, "context", json_only=True)\n    if _shape(context_doc, context_schema):\n        raise ValueError("context does not satisfy omission_context_v1")\n    if type(bundle) is not bytes or not bundle or len(bundle) > MAX_INPUT_BYTES:\n        raise ValueError("bundle must be nonempty bytes within the input bound")\n    try:\n        chunks, _pins = evidence.source_chunks_from_bytes(bundle, manifest)\n    except (ValueError, TypeError, KeyError, yaml.YAMLError) as exc:\n        raise ValueError("invalid canonical chunk manifest/bundle binding") from exc\n    if not chunks or len(chunks) > response_schema["properties"]["chunks"]["maxItems"]:\n        raise ValueError("canonical chunk count is outside the response contract")\n    if receipt_doc.get("bundle_md5") != hashlib.md5(bundle).hexdigest():\n        raise ValueError("receipt does not name the captured bundle")\n    entries = receipt_doc.get("chunks")\n    if not isinstance(entries, list):\n        raise ValueError("receipt chunks must be a list")\n    prior = {}\n    for entry in entries:\n        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):\n            raise ValueError("receipt entries must name chunks")\n        key = entry["id"]\n        if key not in chunks or key in prior:\n            raise ValueError("receipt contains unknown or duplicate chunk ids")\n        status = entry.get("status")\n        if status not in {"extracted", "nothing_relevant", "redundant_with", "duplicate_of"}:\n            raise ValueError("receipt contains an unknown chunk status")\n        prior[key] = status\n    try:\n        catalog = _schema(Path(schema_path), schema_snapshot=schema_snapshot,\n                          logical_paths=captured_assets is not None)\n    except (KeyError, TypeError, AttributeError, RecursionError, yaml.YAMLError) as exc:\n        raise ValueError("selected schema cannot be captured unambiguously") from exc\n    owners = _owners(document, catalog, context_doc["vocabulary"])\n    scopes = [s["owner"] for s in context_doc["scopes"]]\n    if "" not in scopes or len(scopes) != len(set(scopes)) or any(s not in owners for s in scopes):\n        raise ValueError("scopes must include root once and name distinct existing typed owners")\n    payload = {"policy": policy, "response_schema": response_schema,\n               "contract_sha256": dict(ASSET_SHA256), "context": context_doc,\n               "record_yaml": record.decode("utf-8"), "receipt_yaml": receipt.decode("utf-8"),\n               "schema": catalog, "owner_classes": owners,\n               "chunks": [{"chunk": key, **value, "prior_receipt_status": prior.get(key, "unreviewed")}\n                          for key, value in chunks.items()],\n               "input_sha256": {k: _sha(v) for k, v in {"record": record, "bundle": bundle,\n                                "manifest": manifest, "receipt": receipt, "context": context}.items()},\n               "limits": {"max_output_tokens": max_output_tokens, "max_request_bytes": max_request_bytes,\n                          "max_input_bytes": MAX_INPUT_BYTES, "max_response_bytes": MAX_RESPONSE_BYTES,\n                          "max_schema_bytes": MAX_SCHEMA_BYTES, "max_nodes": MAX_NODES, "max_depth": MAX_DEPTH}}\n    encoded = _json(payload)\n    if len(_json(Prepared(encoded).request()).encode()) > max_request_bytes:\n        raise ValueError("complete request exceeds max_request_bytes; no partial request returned")\n    return Prepared(encoded)'

def parent():
    # All changed parent definitions share their own mutually bound globals.
    old_om = types.ModuleType('parent_omissions')
    old_om.__dict__.update(vars(omissions))
    exec(compile(PARENT_OMISSIONS, '<literal parent omissions.prepare>', 'exec', flags=__future__.annotations.compiler_flag), old_om.__dict__)
    old = types.ModuleType('parent_typed')
    old.__dict__.update(vars(typed))
    old.omissions = old_om
    exec(compile(PARENT_TYPED, '<literal parent typed producers>', 'exec', flags=__future__.annotations.compiler_flag), old.__dict__)
    return old


def captured(supplied):
    # Native schema carriers originate in exact JSON strings. Direct LinkML
    # capture may preserve URIorCURIE subclasses; that fallback is separate.
    snapshot = typed._snapshot(typed._snapshot_rows(capture_schema(supplied['schema_path'], strict=True)))
    return {'schema_snapshot': snapshot,
            'captured_assets': tuple((n, omissions._asset(n)) for n in omissions.ASSET_SHA256)}


def test_same_call_catalog_and_packet_match_literal_parent(supplied, monkeypatch, tmp_path):
    options = captured(supplied)
    old = parent()
    expected = old.prepare(**supplied, **options, derivations=old.DerivationCache())
    (tmp_path/'parent-packet.json').write_bytes(typed._json(expected))
    calls, original = [], omissions._schema
    def counted(*a, **kw):
        calls.append((a, kw))
        return original(*a, **kw)
    monkeypatch.setattr(omissions, '_schema', counted)
    actual = typed.prepare(**supplied, **options, derivations=typed.DerivationCache())
    (tmp_path/'candidate-packet.json').write_bytes(typed._json(actual))
    assert typed._json(actual) == typed._json(expected)
    assert len(calls) == 1

def error_signature(call):
    try:
        call()
    except Exception as exc:
        def signature(e):
            return (type(e).__module__, type(e).__qualname__, str(e),
                    signature(e.__cause__) if e.__cause__ is not None else None)
        return signature(exc)
    pytest.fail('expected refusal')


@pytest.mark.parametrize('case', ['closure_and_record', 'missing_import', 'reordered', 'duplicate',
    'foreign_path', 'foreign_name', 'record', 'receipt', 'context', 'assets', 'limit'])
def test_first_error_matches_independent_parent(supplied, case):
    options = captured(supplied)
    sources = options['schema_snapshot'].sources
    if case == 'closure_and_record':
        options['schema_snapshot'] = replace(options['schema_snapshot'], sources=(
            (sources[0][0], sources[0][1], b'['), *sources[1:]))
        supplied['original_full'] = b'['
    elif case == 'missing_import':
        options['schema_snapshot'] = replace(options['schema_snapshot'], sources=sources[:-1])
    elif case == 'reordered':
        options['schema_snapshot'] = replace(options['schema_snapshot'], sources=(sources[0], *reversed(sources[1:])))
    elif case == 'duplicate':
        options['schema_snapshot'] = replace(options['schema_snapshot'], sources=(*sources, sources[-1]))
    elif case in ('foreign_path', 'foreign_name'):
        name, path, raw = sources[1]
        row = ('other' if case == 'foreign_name' else name,
               path.with_name('other.yaml') if case == 'foreign_path' else path, raw)
        options['schema_snapshot'] = replace(options['schema_snapshot'], sources=(sources[0], row, *sources[2:]))
    elif case in ('record', 'receipt', 'context'):
        supplied[{'record': 'original_full'}.get(case, case)] = b'['
    elif case == 'assets':
        rows = list(options['captured_assets'])
        rows[0] = (rows[0][0], rows[0][1] + b' changed')
        options['captured_assets'] = tuple(rows)
    else:
        supplied['max_output_tokens'] = 0
    old = parent()
    expected = error_signature(lambda: old.prepare(**supplied, **options, derivations=old.DerivationCache()))
    actual = error_signature(lambda: typed.prepare(**supplied, **options, derivations=typed.DerivationCache()))
    assert actual == expected


@pytest.mark.parametrize('route,expected_calls', [('physical', 2), ('default', 1), ('subclass', 2)])
def test_other_routes_keep_schema_construction_and_output(supplied, monkeypatch, route, expected_calls):
    options = captured(supplied)
    if route == 'default':
        options = {}
    elif route == 'physical':
        options.pop('captured_assets')
    else:
        class Name(str):
            pass
        snapshot = options['schema_snapshot']
        options['schema_snapshot'] = replace(snapshot, sources=tuple(
            (Name(name), path, raw) for name, path, raw in snapshot.sources))
    old = parent()
    expected = old.prepare(**supplied, **options, derivations=old.DerivationCache())
    original, calls = omissions._schema, []
    def counted(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)
    monkeypatch.setattr(omissions, '_schema', counted)
    assert typed.prepare(**supplied, **options, derivations=typed.DerivationCache()) == expected
    assert len(calls) == expected_calls


def test_uncached_prepare_and_fresh_public_worker_recheck(supplied, monkeypatch):
    options, old = captured(supplied), parent()
    expected = old.prepare(**supplied, **options)
    original, calls = omissions._schema, []
    def counted(*a, **kw):
        calls.append(kw)
        return original(*a, **kw)
    monkeypatch.setattr(omissions, '_schema', counted)
    actual = typed.prepare(**supplied, **options)
    assert actual == expected
    assert len(calls) == 1 + len(actual['plan']['workers'])
    for worker in actual['plan']['workers']:
        before = len(calls)
        assert typed.worker_request(actual, worker['id'], captured_assets=options['captured_assets']) == old.worker_request(
            expected, worker['id'], captured_assets=options['captured_assets'])
        assert len(calls) == before + 1


def test_next_call_fresh_validation_mutation_and_failure_not_retained(supplied, monkeypatch):
    import gc
    import weakref
    options, cache = captured(supplied), typed.DerivationCache()
    original, calls, retained = omissions._schema, [], []
    create = typed._SchemaReuse.__init__
    def created(self, *args):
        create(self, *args)
        retained.append(weakref.ref(self))
    def counted(*a, **kw):
        calls.append(kw['schema_snapshot'].sources)
        return original(*a, **kw)
    monkeypatch.setattr(typed._SchemaReuse, '__init__', created)
    monkeypatch.setattr(omissions, '_schema', counted)
    first = typed.prepare(**supplied, **options, derivations=cache)
    expected = deepcopy(first)
    first['omission_request']['payload']['schema']['classes'].clear()
    assert typed.prepare(**supplied, **options, derivations=cache) == expected
    assert len(calls) == 2
    before = dict(cache._rows)
    snapshot = options['schema_snapshot']
    name, path, raw = snapshot.sources[0]
    bad = replace(snapshot, sources=((name, path, b'['), *snapshot.sources[1:]))
    with pytest.raises(ValueError):
        typed.prepare(**supplied, **{**options, 'schema_snapshot': bad}, derivations=cache)
    assert cache._rows == before and len(calls) == 3
    changed = replace(snapshot, sources=((name, path, raw+b'\n'), *snapshot.sources[1:]))
    changed_options = {**options, 'schema_snapshot': changed}
    actual = typed.prepare(**supplied, **changed_options, derivations=cache)
    old = parent()
    assert actual == old.prepare(**supplied, **changed_options, derivations=old.DerivationCache())
    assert actual['sha256'] != expected['sha256']
    gc.collect()
    assert all(ref() is None for ref in retained)
    assert set(vars(cache)) == {'max_entries', 'max_bytes', '_rows', '_bytes'}


def test_mismatched_private_association_falls_back(supplied, monkeypatch):
    options = captured(supplied)
    packet = typed.prepare(**supplied, **options, derivations=typed.DerivationCache())
    old = parent()
    expected = old._derive_uncached(packet['inputs'], packet['schema_sources'], packet['project'],
                                   packet['limits'], captured_assets=options['captured_assets'])
    other = replace(options['schema_snapshot'], sources=tuple(reversed(options['schema_snapshot'].sources)))
    handoff = typed._SchemaReuse(other.sources, {'sources': []})
    original, calls = omissions._schema, []
    def counted(*a, **kw):
        calls.append(kw)
        return original(*a, **kw)
    monkeypatch.setattr(omissions, '_schema', counted)
    actual = typed._derive_uncached(packet['inputs'], packet['schema_sources'], packet['project'], packet['limits'],
        captured_assets=options['captured_assets'], _schema_reuse=handoff)
    assert typed._json(actual[0]) == typed._json(expected[0])
    assert actual[1] == expected[1] and actual[2].payload_json == expected[2].payload_json
    assert len(calls) == 1


def test_independent_threads_keep_private_catalogs(supplied):
    from concurrent.futures import ThreadPoolExecutor
    options = captured(supplied)
    inputs = [dict(supplied), {**supplied, 'original_full': b'name: Other\n'}]
    old = parent()
    expected = [old.prepare(**row, **options, derivations=old.DerivationCache()) for row in inputs]
    def prepare(row):
        return typed.prepare(**row, **options, derivations=typed.DerivationCache())
    with ThreadPoolExecutor(max_workers=2) as pool:
        actual = list(pool.map(prepare, inputs))
    assert actual == expected and actual[0]['sha256'] != actual[1]['sha256']


def test_public_signatures_are_exact_parent():
    import inspect
    old = parent()
    assert inspect.signature(typed.prepare) == inspect.signature(old.prepare)
    assert inspect.signature(omissions.prepare) == inspect.signature(old.omissions.prepare)
