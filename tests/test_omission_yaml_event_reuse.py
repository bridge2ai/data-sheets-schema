"""Strict-reader parity and real parser work; no native execution or timing claim."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import audit_omissions as om
from data_sheets_schema.schema_snapshot import capture_schema
from data_sheets_schema.support_targets import _canonical


# Exact _read source at parent 1f65e86c. Compile with current limit globals so
# the reference also observes each test's explicit bound, without a file read.
LEGACY_READ_SOURCE = '''def _read(raw: bytes, label: str, *, json_only: bool = False, limit: int = MAX_INPUT_BYTES):
    if type(raw) is not bytes or not raw or len(raw) > limit:
        raise ValueError(f"{label} must be nonempty bytes within the {limit}-byte bound")
    try:
        text = raw.decode("utf-8")
        if nesting_exceeds(text, yaml.SafeLoader, MAX_DEPTH):
            raise ValueError("depth bound exceeded")
        value = evidence.load_json(text) if json_only else yaml.load(text, Loader=_UniqueLoader)
        _validate_json(value, max_nodes=MAX_NODES, max_depth=MAX_DEPTH)
        return value
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, yaml.YAMLError) as exc:
        raise ValueError(f"{label} cannot be read safely ({type(exc).__name__})") from exc
'''
LEGACY_READ_CODE = compile(LEGACY_READ_SOURCE, '<parent strict reader>', 'exec')


def legacy(raw, label='test', **kwargs):
    scope = dict(vars(om))
    exec(LEGACY_READ_CODE, scope)
    return scope['_read'](raw, label, **kwargs)


def outcome(reader, raw, **kwargs):
    try:
        value = reader(raw, 'test', **kwargs)
    except Exception as exc:
        chain = []
        while exc is not None:
            chain.append((type(exc).__module__, type(exc).__name__, str(exc)))
            exc = exc.__cause__
        return ('error', chain)
    return ('value', _canonical(value))


def test_valid_yaml_has_one_real_parser_traversal(monkeypatch):
    original = yaml.parser.Parser.parse_stream_start
    calls = []

    def counted(self):
        calls.append(self)
        return original(self)

    monkeypatch.setattr(yaml.parser.Parser, 'parse_stream_start', counted)
    data = b'rows: [{name: example, value: 2}, {name: other, value: false}]\n'
    expected = legacy(data)
    assert len(calls) == 2
    calls.clear()
    assert om._read(data, 'test') == expected
    assert len(calls) == 1


def test_actual_selected_schema_and_catalog_complete_bytes(tmp_path, monkeypatch):
    root = Path(om.__file__).with_name('schema')
    for kind, name in [('full', 'data_sheets_schema_all.yaml'), ('core', 'data_sheets_schema_core_all.yaml')]:
        raw = (root / name).read_bytes()
        before = _canonical(legacy(raw, 'schema')).encode()
        after = _canonical(om._read(raw, 'schema')).encode()
        (tmp_path / (kind + '-parent.json')).write_bytes(before)
        (tmp_path / (kind + '-candidate.json')).write_bytes(after)
        assert before == after
    path = root / 'data_sheets_schema_all.yaml'
    snapshot = capture_schema(path, read_bytes=lambda p: p.read_bytes(), strict=True, logical_paths=True)
    with monkeypatch.context() as old:
        old.setattr(om, '_read', legacy)
        before = _canonical(om._schema_with_root_bases(path, schema_snapshot=snapshot)).encode()
    after = _canonical(om._schema_with_root_bases(path, schema_snapshot=snapshot)).encode()
    (tmp_path / 'catalog-parent.json').write_bytes(before)
    (tmp_path / 'catalog-candidate.json').write_bytes(after)
    assert before == after


@pytest.mark.parametrize('raw', [
    b'name: first\nname: second\n', b'1: one\n',
    b'base: &base {name: value}\nmerged: {<<: *base}\n',
    b'value: !foreign text\n', b'value: *missing\n',
    b'one: &same 1\ntwo: &same 2\n', b'value: &cycle [*cycle]\n',
    b'first: 1\n---\nsecond: 2\n', b'value: [unterminated\n',
    b'one: 1\none: 2\nlast: [unterminated\n',
    b'value: .nan\n', b'value: .inf\n', b'key: "\\udcff"\n',
    b'a: 1\n\xef\xbb\xbf# comment\na: 2\n',
    b'a: x\ty\n', b'value: \0\n', b'key: \xff\n', b'',
])
def test_exact_types_errors_and_marks_match_parent(raw):
    assert outcome(om._read, raw) == outcome(legacy, raw)


@pytest.mark.parametrize('depth', [4, 5])
def test_depth_preflight_and_constructor_error_precedence(monkeypatch, depth):
    monkeypatch.setattr(om, 'MAX_DEPTH', 4)
    raw = b'one: &same 1\ntwo: &same 2\nlast: ' + b'[' * depth + b'1' + b']' * depth + b'\n'
    assert outcome(om._read, raw) == outcome(legacy, raw)


@pytest.mark.parametrize('raw', [b'a: [[[1]]]\n', b'a: [[[[1]]]]\n'])
def test_exact_depth_boundary(monkeypatch, raw):
    monkeypatch.setattr(om, 'MAX_DEPTH', 4)
    assert outcome(om._read, raw) == outcome(legacy, raw)


def test_node_and_supplied_byte_limits(monkeypatch):
    monkeypatch.setattr(om, 'MAX_NODES', 4)
    for raw in (b'a: [1, 2, 3]\n', b'a: [1, 2, 3, 4]\n'):
        assert outcome(om._read, raw) == outcome(legacy, raw)
        assert outcome(om._read, raw, limit=len(raw)-1) == outcome(legacy, raw, limit=len(raw)-1)


def test_scalar_types_anchors_and_no_libyaml(monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError('libyaml is outside this reader')
    monkeypatch.setattr(yaml, 'CSafeLoader', forbidden, raising=False)
    raw = b'a: &a [1, true, 1.5, 2026-10-05, 2026-10-05T01:02:03Z, "1"]\nb: *a\n'
    value = om._read(raw, 'test')
    assert value == legacy(raw) and value['a'] is value['b']
    assert [type(x) for x in value['a']] == [int, bool, float, date, datetime, str]


@pytest.mark.parametrize('raw', [b'{"a":1}', b'{"a":1,"a":2}', b'{"a":[}', b'{"a":"\\udcff"}'])
def test_json_only_remains_on_original_route(monkeypatch, raw):
    def forbidden(*_a, **_k):
        raise AssertionError('YAML replay called for JSON')
    monkeypatch.setattr(om, '_load_yaml', forbidden)
    assert outcome(om._read, raw, json_only=True) == outcome(legacy, raw, json_only=True)


@pytest.mark.parametrize('cap', ['_YAML_REPLAY_MAX_EVENTS', '_YAML_REPLAY_MAX_TEXT_BYTES'])
def test_retention_limit_falls_back_without_new_refusal(monkeypatch, cap):
    monkeypatch.setattr(om, cap, 1)
    for raw in (b'a: [1, 2]\n', b'a: 1\na: 2\n', b'a: [unterminated\n'):
        assert outcome(om._read, raw) == outcome(legacy, raw)


def test_expanded_tags_and_escaped_surrogates_preserve_legacy(monkeypatch):
    monkeypatch.setattr(om, '_YAML_REPLAY_MAX_TEXT_BYTES', 100)
    prefix = b'%TAG !e! tag:example.test,2026:' + b'x' * 200 + b'\n---\na: !e!thing value\n'
    assert outcome(om._read, prefix) == outcome(legacy, prefix)
    raw = b'a: "\\udcff"\n'
    assert outcome(om._read, raw) == outcome(legacy, raw)


def test_owned_event_queues_clear_and_calls_do_not_share_state(monkeypatch):
    loaders = []
    original = om._EventReplayLoader.__init__

    def tracked(self, *args, **kwargs):
        original(self, *args, **kwargs)
        loaders.append(self)

    monkeypatch.setattr(om._EventReplayLoader, '__init__', tracked)
    raws = [b'a: [1, 2]\n', b'a: 1\na: 2\n', b'a: "\\udcff"\n', b'a: [unterminated\n']
    with ThreadPoolExecutor(max_workers=4) as pool:
        actual = list(pool.map(lambda raw: outcome(om._read, raw), raws * 3))
    assert actual == [outcome(legacy, raw) for raw in raws * 3]
    assert loaders and all(not loader._events for loader in loaders)
    value = om._read(raws[0], 'test'); value['a'].clear()
    assert om._read(raws[0], 'test') == {'a': [1, 2]}
