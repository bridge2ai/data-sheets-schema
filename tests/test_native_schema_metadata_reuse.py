"""Fresh native metadata shares only an already strict-parsed mapping (#4400).

The four literal oracle functions below are copied from frozen36e, preserving
its original parsers, traversal, closure comparisons and independent view.
"""
import copy
from pathlib import Path
from contextlib import contextmanager
from types import MappingProxyType
from datetime import date, datetime

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_selection as selected
from data_sheets_schema import schema_snapshot as ss
from data_sheets_schema import audit_omissions as omissions
from data_sheets_schema.schema_view import captured_view

_PARENT_METADATA = r'''@functools.lru_cache(maxsize=128)
def _metadata(content: bytes) -> tuple:
    doc = yaml.safe_load(content) or {}
    # Let the installed metamodel normalize its supported mapping/list forms.
    fields = {k: doc[k] for k in
        ("id", "name", "imports", "prefixes", "default_curi_maps") if k in doc}
    # gen-linkml's raw loader derives an omitted name from the schema ID.
    # Metadata discovery must admit the same source documents. The actual
    # view parser still applies its installed SchemaDefinition contract.
    if not fields.get("name") and fields.get("id"):
        fields["name"] = str(fields["id"]).replace("#", "/").rsplit("/", 1)[-1]
    schema = SchemaDefinition(**fields)
    prefixes = tuple((str(p.prefix_prefix), str(p.prefix_reference)) for p in schema.prefixes.values())
    return str(schema.name), tuple(schema.imports), prefixes, tuple(schema.default_curi_maps)
'''

_PARENT_CAPTURE_SCHEMA = r'''def capture_schema(path: str | Path, *, content: bytes | None = None,
                   read_bytes: Callable[[Path], bytes] | None = None,
                   namespace_orders: tuple[bool, ...] | None = None,
                   strict: bool = False, logical_paths: bool = False) -> SchemaSnapshot:
    """Capture both supported namespace-initialization orders (#1273).

    Callers can initialize namespaces before loading imports, or allow the first
    prefixed import to do it. Capture the union without reading any file twice;
    the view later selects bytes using its actual namespace state. An unavailable
    alternative is recorded and fails only if that alternative is selected.
    The source preflight supplies its existing byte capture and requests the
    generator's default traversal alone, with errors raised before generation.
    """
    if type(logical_paths) is not bool:
        raise ValueError("logical_paths must be an explicit boolean")
    if logical_paths:
        # An already captured closure has canonical lexical identities. Never
        # consult today's aliases, resource installation or filesystem metadata.
        root = Path(path)
        if (read_bytes is None or not strict or not root.is_absolute()
                or str(root) != str(path) or '..' in root.parts
                or os.path.normpath(str(root)) != str(root)):
            raise ValueError("logical schema replay requires a strict captured reader and canonical absolute root")
        read = read_bytes
    else:
        from data_sheets_schema.resources import resource_path, physical
        read = read_bytes or Path.read_bytes
        root = physical(resource_path(path))              # from any directory; `..` through the filesystem (#1301, #1570)
    files = {root: read(root) if content is None else content}
    root_meta = _metadata(files[root])
    names = {root: root_meta[0]}
    orders = namespace_orders if namespace_orders is not None else ((False, True) if root_meta[1] else (False,))
    for early in orders:
        metadata = {root_meta[0]: root_meta}

        @functools.lru_cache(maxsize=1)
        def namespaces():
            ns = Namespaces()
            for meta in metadata.values():
                for cmap in root_meta[3]:
                    ns.add_prefixmap(cmap, include_defaults=False)
                for prefix, value in meta[2]:
                    ns[prefix] = value
            return ns

        try:
            if early:
                namespaces()
            pending, visited = [root_meta[0]], set()
            while pending:
                name = pending.pop()
                if name in visited:
                    continue
                visited.add(name)
                source = root if name == root_meta[0] else resolve_import_path(name, root, namespaces)
                if source not in files:
                    try:
                        files[source] = read(source)
                    except OSError as exc:
                        files[source] = exc
                    names[source] = name
                data = files[source]
                if isinstance(data, OSError):
                    raise data
                meta = metadata[name] = _metadata(data)
                for imp in meta[1]:
                    if imp == name:
                        continue
                    if "/" in name and ":" not in imp:
                        imp = os.path.normpath(str(Path(name).parent / imp))
                    pending.append(imp)
        except (OSError, ValueError, TypeError, yaml.YAMLError):
            if strict:
                raise
            # A failed alternate traversal must not reject a valid one. The
            # selected loader below still raises on those captured bytes/errors.
            pass

    identity = []
    for p, data in sorted(files.items()):
        if logical_paths:
            target = str(p)
        else:
            try:
                target = str(p.resolve())
            except (OSError, RuntimeError):
                target = str(p)
        stamp = (f"{type(data).__name__}:{data.errno}" if isinstance(data, OSError)
                 else hashlib.sha256(data).hexdigest())
        identity.append((str(p), target, stamp))
    # Distinct logical aliases may resolve imports differently. Keep each
    # stable alias cached rather than evicting views by their shared target.
    key = (str(root), hashlib.blake2b(
        json.dumps({'domain': 'captured_logical_schema_v1', 'sources': identity}
                   if logical_paths else identity, ensure_ascii=False).encode("utf-8"), digest_size=16).hexdigest())
    return SchemaSnapshot(tuple((names[p], p, data) for p, data in files.items()), key)
'''

_PARENT_SCHEMAS = r'''def _schemas(doc, artifacts):
    result = []
    for kind, cls in (('full', 'Dataset'), ('core', 'CoreDataset')):
        declaration = doc['inputs'][kind + '_schema']
        sources = tuple(artifacts[f'{kind}_schema:{i}'] for i in range(len(declaration['sources'])))
        rows = tuple((source['name'], artifact.pin.role)
                     for source, artifact in zip(declaration['sources'], sources))
        frozen = {Path(a.pin.path): a.raw for a in sources}

        def read(path):
            if path not in frozen:
                raise ValueError('selected schema import is outside the complete captured closure')
            return frozen[path]

        for artifact in sources:
            omissions._mapping(artifact.raw, 'native schema', limit=contract.HARD_LIMITS['schema_member_bytes'])
        snapshot = capture_schema(Path(declaration['root']), read_bytes=read,
                                  strict=True, logical_paths=True)
        actual = [(str(name), str(path), raw) for name, path, raw in snapshot.sources]
        expected = [(row['name'], a.pin.path, a.raw) for row, a in zip(declaration['sources'], sources)]
        if actual != expected:
            raise ValueError('native schema names, order or import closure differ')
        with captured_view(snapshot) as view:
            if view.get_class(cls) is None:
                raise ValueError('native captured schema lacks ' + cls)
        result.append(contract.SchemaClosureCapture(
            contract.schema_closure_sha(sources, rows), rows, kind, cls,
            declaration['sources'][0]['name'], sources))
    return tuple(result)
'''
_PARENT_RESOLVE_IMPORT_PATH = r'''def resolve_import_path(name, source: Path, namespaces) -> Path:
    """LinkML's import mapping, including installed URL aliases (#1274)."""
    mapped = map_import({"linkml:": str(SCHEMA_DIRECTORY)}, namespaces, name) + ".yaml"
    mapped = str(URI_TO_LOCAL.get(mapped, mapped))
    if "://" in mapped:
        raise ValueError(f"cannot capture remote schema import {name!r}")
    imported = Path(mapped)
    return Path(os.path.abspath(imported if imported.is_absolute() else source.parent / imported))
'''

@pytest.fixture
def parent():
    ns = dict(vars(ss))
    exec(_PARENT_METADATA + '\n' + _PARENT_RESOLVE_IMPORT_PATH + '\n' + _PARENT_CAPTURE_SCHEMA, ns)
    ns.update(contract=c, omissions=omissions, captured_view=captured_view)
    exec(_PARENT_SCHEMAS, ns)
    return ns


def schema(name, cls='Dataset', extra=b''):
    return f'id: https://example.org/{name}\nname: {name}\nclasses:\n  {cls}: {{}}\n'.encode() + extra


def inputs(tmp_path, full=None, core=None):
    full = full or [('full', tmp_path / 'full.yaml', schema('full'))]
    core = core or [('core', tmp_path / 'core.yaml', schema('core', 'CoreDataset'))]
    doc, artifacts = {'inputs': {}}, {}
    for kind, members in (('full', full), ('core', core)):
        declaration = {'root': str(members[0][1]), 'sources': []}
        for index, (name, path, raw) in enumerate(members):
            role = f'{kind}_schema:{index}'
            value = c.CapturedArtifact(c.ArtifactPin(role, str(path), len(raw), c.sha(raw)), raw)
            artifacts[role] = value
            declaration['sources'].append({'name': name, 'path': str(path), 'bytes': len(raw), 'sha256': c.sha(raw)})
        doc['inputs'][kind + '_schema'] = declaration
    return doc, artifacts


def observed(fn, *args, **kwargs):
    try:
        return ('value', fn(*args, **kwargs))
    except Exception as error:
        chain = []
        while error is not None:
            chain.append((type(error).__module__, type(error).__name__, str(error)))
            error = error.__cause__
        return ('error', chain)


def parity(parent, doc, artifacts):
    expected = observed(parent['_schemas'], doc, artifacts)
    actual = observed(selected._schemas, doc, artifacts)
    assert actual == expected
    return actual


def test_native_reconstruction_eliminates_only_metadata_yaml_reparse(tmp_path, monkeypatch):
    doc, artifacts = inputs(tmp_path)
    calls, strict_calls = [], []
    original = ss.yaml.safe_load
    strict_original = omissions._mapping
    def read(raw):
        calls.append(raw)
        return original(raw)
    ss._metadata.cache_clear()
    monkeypatch.setattr(ss.yaml, 'safe_load', read)
    def strict(raw, label, **kwargs):
        strict_calls.append((raw, label, kwargs))
        return strict_original(raw, label, **kwargs)
    monkeypatch.setattr(omissions, '_mapping', strict)
    assert len(selected._schemas(doc, artifacts)) == 2
    assert calls == []
    assert strict_calls == [(artifacts[kind + '_schema:0'].raw, 'native schema',
                             {'limit': c.HARD_LIMITS['schema_member_bytes']}) for kind in ('full', 'core')]


@pytest.mark.parametrize('extra', [b'', b'prefixes: {ex: https://example.org/}\n',
    b'prefixes: [{prefix_prefix: ex, prefix_reference: "https://example.org/"}]\n',
    b'annotations: {day: 2025-01-02, moment: 2025-01-02T03:04:05Z}\n',
    b'default_prefix: &prefix ex\nprefixes: {ex: "https://example.org/"}\n'])
def test_real_native_views_and_carriers_match_parent(parent, tmp_path, extra):
    doc, artifacts = inputs(tmp_path, full=[('full', tmp_path / 'full.yaml', schema('full', extra=extra))])
    assert parity(parent, doc, artifacts)[0] == 'value'


def test_omitted_name_and_shared_prefix_alias_metadata_match_parent(parent, tmp_path):
    raw = b'id: https://example.org/root\nprefixes: {ex: &uri "https://example.org/", other: *uri}\nclasses: {Dataset: {}}\n'
    path = tmp_path / 'root.yaml'
    old = parent['capture_schema'](path, read_bytes=lambda unused: raw, strict=True, logical_paths=True)
    fresh = ss._capture_native_schema(path, ((path, raw),), member_bytes=8_000_000)
    assert old == fresh and fresh.sources[0][0] == 'root'


@pytest.mark.parametrize('raw', [b'x: 1\nx: 2\n', b'1: value\n', b'x: &x {a: *x}\n',
    b'x: &base {a: 1}\ny: {<<: *base}\n', b'- list\n', b'x: .inf\n', b'x: [unfinished',
    b'x: !foreign value\n', b'prefixes: 7\n', b'id: https://example.org/full\nname: full\nimports: [absent]\n',
    b'id: https://example.org/full\nname: full\nunknown_metamodel_field: value\nclasses: {Dataset: {}}\n',
    b'id: https://example.org/full\nname: full\nimports: [null]\n'])
def test_real_refusal_type_message_cause_parity(parent, tmp_path, raw):
    doc, artifacts = inputs(tmp_path, full=[('full', tmp_path / 'full.yaml', raw)])
    assert parity(parent, doc, artifacts)[0] == 'error'


@pytest.mark.parametrize('limit,value,raw', [('MAX_DEPTH', 2, b'a: {b: {c: 1}}\n'),
    ('MAX_NODES', 3, b'a: [1, 2, 3, 4]\n')])
def test_depth_and_node_limits_are_still_strict_first(parent, tmp_path, monkeypatch, limit, value, raw):
    monkeypatch.setattr(omissions, limit, value)
    doc, artifacts = inputs(tmp_path, full=[('full', tmp_path / 'full.yaml', raw)])
    assert parity(parent, doc, artifacts)[0] == 'error'


def test_member_byte_bound_exact_then_one_over(parent, tmp_path, monkeypatch):
    raw = schema('full')
    doc, artifacts = inputs(tmp_path, full=[('full', tmp_path / 'full.yaml', raw)],
                            core=[('core', tmp_path / 'core.yaml', b'id: urn:c\nname: core\nclasses: {CoreDataset: {}}\n')])
    monkeypatch.setattr(c, 'HARD_LIMITS', MappingProxyType(dict(c.HARD_LIMITS, schema_member_bytes=len(raw))))
    assert parity(parent, doc, artifacts)[0] == 'value'
    monkeypatch.setattr(c, 'HARD_LIMITS', MappingProxyType(dict(c.HARD_LIMITS, schema_member_bytes=len(raw) - 1)))
    assert parity(parent, doc, artifacts)[0] == 'error'


def test_all_member_strict_errors_precede_root_metadata_errors(parent, tmp_path):
    members = [('full', tmp_path / 'full.yaml', b'prefixes: 7\n'),
               ('unused', tmp_path / 'unused.yaml', b'later: 1\nlater: 2\n')]
    result = parity(parent, *inputs(tmp_path, full=members))
    assert result[0] == 'error' and 'duplicate record key' in str(result)


def test_root_metadata_error_precedes_import_metadata_error(parent, tmp_path):
    members = [('full', tmp_path / 'full.yaml', b'prefixes: 7\n'),
               ('base', tmp_path / 'base.yaml', b'prefixes: [7]\n')]
    result = parity(parent, *inputs(tmp_path, full=members))
    root_only = observed(parent['_metadata'], members[0][2])
    assert result == root_only and result[0] == 'error'


def test_full_view_failure_precedes_core_strict_error(parent, tmp_path):
    doc, artifacts = inputs(tmp_path, full=[('full', tmp_path / 'full.yaml', schema('full', 'Other'))],
                            core=[('core', tmp_path / 'core.yaml', b'c: 1\nc: 2\n')])
    result = parity(parent, doc, artifacts)
    assert result[0] == 'error' and 'lacks Dataset' in str(result)


def test_duplicate_path_last_bytes_and_every_occurrence_validation(parent, tmp_path):
    path = tmp_path / 'full.yaml'
    first, last = schema('discarded'), schema('full')
    members = ((path, first), (path, last))
    old = parent['capture_schema'](path, read_bytes=lambda unused: dict(members)[path], strict=True, logical_paths=True)
    assert ss._capture_native_schema(path, members, member_bytes=8_000_000) == old
    # Selected carriers still reject a declared roster inconsistent with the actual closure.
    assert parity(parent, *inputs(tmp_path, full=[('discarded', path, first), ('full', path, last)]))[0] == 'error'
    with pytest.raises(ValueError, match='cannot be read safely') as error:
        ss._capture_native_schema(path, ((path, b'a: 1\na: 2\n'), (path, last)), member_bytes=8_000_000)
    assert str(error.value.__cause__) == "duplicate record key 'a'"


def test_real_import_traversal_and_declared_order(parent, tmp_path, monkeypatch):
    full = [('full', tmp_path / 'full.yaml', schema('full', extra=b'imports: [a, b]\n')),
            ('b', tmp_path / 'b.yaml', schema('b', 'B')),
            ('a', tmp_path / 'a.yaml', schema('a', 'A'))]
    def no_ambient(*args, **kwargs):
        pytest.fail('captured schema reopened an ambient file')
    monkeypatch.setattr(Path, 'read_bytes', no_ambient)
    monkeypatch.setattr(Path, 'resolve', no_ambient)
    assert parity(parent, *inputs(tmp_path, full=full))[0] == 'value'
    assert parity(parent, *inputs(tmp_path, full=[full[0], full[2], full[1]]))[0] == 'error'
    assert parity(parent, *inputs(tmp_path, full=full[:-1]))[0] == 'error'


def test_both_namespace_orders_and_relative_imports(parent, tmp_path):
    old, new = tmp_path / 'old', tmp_path / 'new'
    root = tmp_path / 'root.yaml'
    raw = (f'id: urn:root\nname: root\nprefixes: {{local: "{old}/"}}\n'
           'imports: [local:second, first]\nclasses: {Dataset: {}}\n').encode()
    members = [(root, raw), (tmp_path / 'first.yaml',
                f'id: urn:first\nname: first\nprefixes: {{local: "{new}/"}}\n'.encode()),
               (new / 'second.yaml', schema('new')), (old / 'second.yaml', schema('old'))]
    frozen = dict(members)
    before = parent['capture_schema'](root, read_bytes=frozen.__getitem__, strict=True, logical_paths=True)
    after = ss._capture_native_schema(root, tuple(members), member_bytes=8_000_000)
    assert before == after and {row[1] for row in after.sources} == set(frozen)
    path = tmp_path / 'nested.yaml'
    other = [(root, b'id: urn:root\nname: root\nimports: [folder/first]\n'),
             (tmp_path / 'folder/first.yaml', b'id: urn:first\nname: first\nimports: [../nested]\n'),
             (path, schema('nested'))]
    assert parent['capture_schema'](root, read_bytes=dict(other).__getitem__, strict=True, logical_paths=True) == \
        ss._capture_native_schema(root, tuple(other), member_bytes=8_000_000)


def test_legacy_public_parser_and_lru_semantics_unchanged(parent, tmp_path, monkeypatch):
    raw, path = schema('full'), tmp_path / 'full.yaml'
    real, calls = ss.yaml.safe_load, []
    def read(value):
        calls.append(value)
        return real(value)
    monkeypatch.setattr(ss.yaml, 'safe_load', read)
    ss._metadata.cache_clear()
    args = dict(read_bytes=lambda unused: raw, strict=True, logical_paths=True)
    first = ss.capture_schema(path, **args)
    assert ss.capture_schema(path, **args) == first
    assert calls == [raw]
    calls.clear()
    expected = parent['capture_schema'](path, **args)
    assert parent['capture_schema'](path, **args) == expected == first
    assert calls == [raw]
    assert observed(ss.capture_schema, path, logical_paths=True) == observed(parent['capture_schema'], path, logical_paths=True)


def test_native_private_fields_and_second_call_are_fresh(parent, tmp_path, monkeypatch):
    path = tmp_path / 'full.yaml'
    raw = schema('full', extra=b'prefixes: {ex: "https://example.org/"}\n')
    real, seen = ss._metadata_document, []
    def mutate_after_result(doc):
        seen.append(copy.deepcopy(doc))
        value = real(doc)
        doc.clear()
        return value
    monkeypatch.setattr(ss, '_metadata_document', mutate_after_result)
    first = ss._capture_native_schema(path, ((path, raw),), member_bytes=8_000_000)
    assert ss._capture_native_schema(path, ((path, raw),), member_bytes=8_000_000) == first
    assert seen[0] == seen[1] and seen[0]['prefixes'] == {'ex': 'https://example.org/'}
    changed = raw.replace(b'https://example.org/', b'https://changed.example/')
    assert ss._capture_native_schema(path, ((path, changed),), member_bytes=8_000_000) != first
    assert seen[-1]['prefixes'] == {'ex': 'https://changed.example/'}
    with pytest.raises(ValueError, match='safely'):
        ss._capture_native_schema(path, ((path, raw + b'name: duplicate\n'),), member_bytes=8_000_000)


def test_independent_linkml_view_remains_real(parent, tmp_path, monkeypatch):
    count = []
    real = selected.captured_view
    @contextmanager
    def view(snapshot):
        with real(snapshot) as actual:
            count.append(tuple(actual.all_classes()))
            yield actual
    monkeypatch.setattr(selected, 'captured_view', view)
    assert parity(parent, *inputs(tmp_path))[0] == 'value'
    assert count == [('Dataset',), ('CoreDataset',)]


def test_actual_full_core_sources_match_parent_and_remain_captured_only(parent, monkeypatch):
    from data_sheets_schema import api_runner
    from data_sheets_schema.resources import resource_path
    members = {}
    for kind, path in [('full', api_runner.FULL_SCHEMA_PATH), ('core', api_runner.CORE_SCHEMA_PATH)]:
        root = resource_path(path).absolute()
        snap = parent['capture_schema'](root, strict=True)
        members[kind] = list(snap.sources)
    doc, artifacts = inputs(Path('/synthetic/unused'), **members)
    def no_ambient(*args, **kwargs):
        pytest.fail('actual captured products used ambient files')
    monkeypatch.setattr(Path, 'read_bytes', no_ambient)
    monkeypatch.setattr(Path, 'resolve', no_ambient)
    result = parity(parent, doc, artifacts)
    assert result[0] == 'value' and len(result[1]) == 2
    assert sum(len(a.raw) for item in result[1] for a in item.sources) > 2_000_000


@pytest.mark.parametrize('field', ['id', 'name', 'prefix_reference'])
@pytest.mark.parametrize('scalar,expected_type', [('2025-01-02', date), ('2025-01-02T03:04:05Z', datetime)])
def test_typed_metadata_scalars_match_parent_normalization(parent, tmp_path, field, scalar, expected_type):
    path = tmp_path / 'typed.yaml'
    if field == 'prefix_reference':
        raw = f'id: urn:typed\nname: typed\nprefixes: {{ex: {scalar}}}\n'.encode()
        document = omissions._mapping(raw, 'native schema')
        value = document['prefixes']['ex']
    else:
        other = 'name: typed' if field == 'id' else 'id: urn:typed'
        raw = f'{other}\n{field}: {scalar}\n'.encode()
        document = omissions._mapping(raw, 'native schema')
        value = document[field]
    assert type(value) is expected_type
    expected = observed(parent['capture_schema'], path, read_bytes=lambda unused: raw,
                        strict=True, logical_paths=True)
    actual = observed(ss._capture_native_schema, path, ((path, raw),), member_bytes=8_000_000)
    assert actual == expected
