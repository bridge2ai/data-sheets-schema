"""Schema-only event reuse retains the original two-pass admission contract."""
from dataclasses import replace

import pytest
import yaml

from data_sheets_schema import audit_omissions as om, typed_audit as ta
from data_sheets_schema.duplicate_keys import nesting_exceeds
from data_sheets_schema.schema_snapshot import capture_schema
from data_sheets_schema.support_targets import _UniqueLoader, _validate_json
from tests.test_typed_audit import supplied  # noqa: F401


def original_read(raw, label, *, json_only=False, limit=om.MAX_INPUT_BYTES):
    """Literal pre-change admission, independent of the replay implementation."""
    if type(raw) is not bytes or not raw or len(raw) > limit:
        raise ValueError(f"{label} must be nonempty bytes within the {limit}-byte bound")
    try:
        text = raw.decode("utf-8")
        if nesting_exceeds(text, yaml.SafeLoader, om.MAX_DEPTH):
            raise ValueError("depth bound exceeded")
        value = om.evidence.load_json(text) if json_only else yaml.load(text, Loader=_UniqueLoader)
        _validate_json(value, max_nodes=om.MAX_NODES, max_depth=om.MAX_DEPTH)
        return value
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, yaml.YAMLError) as exc:
        raise ValueError(f"{label} cannot be read safely ({type(exc).__name__})") from exc


def outcome(call):
    try:
        return ("value", call())
    except Exception as exc:
        chain = []
        while exc is not None:
            chain.append((type(exc), str(exc)))
            exc = exc.__cause__
        return ("error", chain)


YAML_CASES = [
    b"name: example\nslots: {description: {range: string}}\n",
    b"text: |\n  line one\n  line two\nflow: ['x', null, true, 1, 1.5]\n",
    b"date: 2026-10-12\ntime: 2026-10-12T09:00:00Z\nquoted: 'true'\n",
    "\ufeffname: caf\u00e9\nquoted: \"a\\tb\"\n".encode(),
    b"%YAML 1.1\n%TAG !e! tag:yaml.org,2002:\n---\nname: !e!str 12\n",
    b"base: &shared [one, two]\nalias: *shared\n",
    b" ", b"scalar\n", b"[one, two]\n", b"{}\n",
    b"a: 1\na: 2\n", b"1: value\n", b"? [a, b]\n: value\n",
    b"base: &base {x: 1}\nmerged: {<<: *base}\n",
    b"a: &same [1]\nb: &same [2]\n", b"a: *missing\n",
    b"a: &cycle [*cycle]\n", b"a: !!binary YQ==\n", b"a: !unknown x\n",
    b"a: .nan\n", b"a: .inf\n", b"a: 1\n---\nb: 2\n",
    b"a: [unclosed\n", b"\tbad: tab\n", b"a: \x00\n", b"a: \xff\n",
    b"", "not bytes", bytearray(b"a: 1"),
]


@pytest.mark.parametrize("raw", YAML_CASES)
def test_values_and_complete_error_causes_match_original(raw):
    assert outcome(lambda: om._read(raw, "schema", _schema_events=True)) == outcome(
        lambda: original_read(raw, "schema"))


@pytest.mark.parametrize("depth", [64, 65])
@pytest.mark.parametrize("prefix", ["", "a: *missing\n", "a: &same []\nb: &same []\n"])
def test_depth_precedes_composer_errors_after_full_stream_scan(depth, prefix):
    text = prefix + "nested: " + "[" * (depth - 1) + "0" + "]" * (depth - 1) + "\n"
    raw = text.encode()
    expected = outcome(lambda: original_read(raw, "schema"))
    assert outcome(lambda: om._read(raw, "schema", _schema_events=True)) == expected
    if depth > om.MAX_DEPTH:
        assert expected[0] == "error" and expected[1][-1][1] == "depth bound exceeded"
    elif not prefix:
        assert expected[0] == "value"


@pytest.mark.parametrize("prefix", ["a: *missing\n", "a: &same []\nb: &same []\n"])
def test_late_parser_error_keeps_earlier_composer_error(prefix):
    raw = (prefix + "later: [unclosed\n").encode()
    expected = outcome(lambda: original_read(raw, "schema"))
    assert expected[0] == "error" and expected[1][-1][0] is yaml.composer.ComposerError
    assert outcome(lambda: om._read(raw, "schema", _schema_events=True)) == expected


@pytest.mark.parametrize("bound", ["MAX_SCHEMA_EVENTS", "MAX_SCHEMA_EVENT_CHARS"])
def test_retention_overflow_falls_back_without_weakening_admission(monkeypatch, bound):
    monkeypatch.setattr(om, bound, 1)
    cases = [b"a: [one, two]\n", b"a: 1\na: 2\n", b"a: *missing\nlater: [broken\n",
             ("deep: " + "[" * 65 + "0" + "]" * 65).encode()]
    for raw in cases:
        assert outcome(lambda: om._read(raw, "schema", _schema_events=True)) == outcome(
            lambda: original_read(raw, "schema"))


def test_replay_avoids_second_parse_and_overflow_uses_original_loader(monkeypatch):
    original, loads = yaml.load, []

    def load(*args, **kwargs):
        loads.append(kwargs.get("Loader"))
        return original(*args, **kwargs)

    monkeypatch.setattr(yaml, "load", load)
    raw = b"a: [one, two]\n"
    assert om._read(raw, "schema", _schema_events=True) == {"a": ["one", "two"]}
    assert loads == []
    monkeypatch.setattr(om, "MAX_SCHEMA_EVENTS", 1)
    assert om._read(raw, "schema", _schema_events=True) == {"a": ["one", "two"]}
    assert loads == [_UniqueLoader]


def test_alias_identity_is_local_and_traversal_limits_still_apply(monkeypatch):
    raw = b"a: &shared [one, two]\nb: *shared\n"
    first = om._read(raw, "schema", _schema_events=True)
    second = om._read(raw, "schema", _schema_events=True)
    assert first["a"] is first["b"] and second["a"] is second["b"]
    assert first["a"] is not second["a"]
    first["a"].clear()
    assert second["a"] == ["one", "two"]
    monkeypatch.setattr(om, "MAX_NODES", 5)
    expected = outcome(lambda: original_read(raw, "schema"))
    assert expected[0] == "error"
    assert outcome(lambda: om._read(raw, "schema", _schema_events=True)) == expected


def test_non_schema_yaml_and_json_keep_original_reader(monkeypatch):
    def forbidden(*args):
        raise AssertionError("schema-only optimization entered by record/JSON reader")

    monkeypatch.setattr(om, "_schema_yaml", forbidden)
    assert om._read(b"name: record\n", "record") == {"name": "record"}
    assert om._read(b'{"name":"record"}', "record", json_only=True) == {"name": "record"}
    assert om._read(b'{"name":"record"}', "record", json_only=True,
                    _schema_events=True) == {"name": "record"}


def test_real_schema_catalog_and_typed_capture_equal_original(supplied, monkeypatch):
    path = supplied["schema_path"]
    captured = capture_schema(path, strict=True)
    actual = om._schema(path, schema_snapshot=captured)
    actual_sources = ta._capture(path)

    def original_yaml(text):
        if nesting_exceeds(text, yaml.SafeLoader, om.MAX_DEPTH):
            raise ValueError("depth bound exceeded")
        return yaml.load(text, Loader=_UniqueLoader)

    monkeypatch.setattr(om, "_schema_yaml", original_yaml)
    assert om._schema(path, schema_snapshot=captured) == actual
    assert ta._capture(path) == actual_sources


def test_schema_admission_remains_fresh_before_root_and_closure_checks(supplied):
    path = supplied["schema_path"]
    captured = capture_schema(path, strict=True)
    expected = om._schema(path, schema_snapshot=captured)
    name, selected, raw = captured.sources[0]
    bad = replace(captured, sources=((name, selected, b"name: one\nname: two\n"),
                                    *captured.sources[1:]))
    # Even a mismatching root must not hide the earlier invalid schema bytes.
    with pytest.raises(ValueError, match="schema cannot be read safely") as exc:
        om._schema(path.with_name("other.yaml"), schema_snapshot=bad)
    assert "duplicate record key" in str(exc.value.__cause__)
    with pytest.raises(ValueError, match="root differs"):
        om._schema(path.with_name("other.yaml"), schema_snapshot=captured)
    with pytest.raises(ValueError, match="outside the captured closure"):
        om._schema(path, schema_snapshot=replace(captured, sources=captured.sources[:1]))
    path.write_bytes(raw + b"\n# fresh source identity\n")
    assert om._schema(path) != expected
    assert om._schema(path, schema_snapshot=captured) == expected
