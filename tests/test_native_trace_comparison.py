"""Portable controls for the bounded constructor diagnostic; no recovered code runs."""
from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import dataclass
import gzip
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "notes/native_trace_comparison_2026-10-08/compare_trace.py"
spec = importlib.util.spec_from_file_location("native_trace_comparison_under_test", SCRIPT)
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


@pytest.fixture
def tools():
    return comparison.utility()


def test_complete_bytes_are_retained_and_typed_values_do_not_collapse():
    raw = b"\x00\xffprivate input\n"
    encoded = comparison.full_typed({"raw": raw, "false": False, "zero": 0, "items": (1, "1")})
    assert encoded[1][0][1] == ["bytes_base64", base64.b64encode(raw).decode("ascii")]
    assert comparison.full_typed(False) != comparison.full_typed(0)
    assert comparison.full_typed([1, 2]) != comparison.full_typed([2, 1])
    assert comparison.full_typed((1,)) != comparison.full_typed([1])
    comparison.validate_typed(encoded)


@pytest.mark.parametrize("value", [
    ["int", True], ["bool", 1], ["float", 1], ["none", None], ["unknown", "x"],
    ["bytes_base64", "YQ==\n"], ["dict", [[["str", "x"], ["none"]], [["str", "x"], ["none"]]]],
    ["tuple", "x"], ["dataclass", "other.Class", []],
])
def test_typed_metadata_cannot_disguise_another_type(value):
    with pytest.raises((comparison.ComparisonError, ValueError)):
        comparison.validate_typed(value)


def test_exception_graph_is_complete_lossless_bounded_and_restores_formatter(tools):
    first = ValueError(b"first")
    second = ValueError(b"first")
    first.__cause__ = RuntimeError("underlying A")
    second.__cause__ = RuntimeError("underlying B")
    first.__context__ = first
    first.add_note("a retained note")
    original = tools.typed_value
    with comparison.lossless_formatter(tools):
        a, b = tools.exception_value(first), tools.exception_value(second)
    assert tools.typed_value is original
    comparison.validate_exception(a)
    comparison.validate_exception(b)
    assert a != b
    assert a["context"] == {"reference": 0}
    assert a["arguments"][1][0] == ["bytes_base64", base64.b64encode(b"first").decode()]
    assert a["notes"] == ["list", [["str", "a retained note"]]]
    for graph in (None, {"reference": 0}, {**a, "suppress_context": 1}, {**a, "node": True}):
        with pytest.raises(comparison.ComparisonError):
            comparison.validate_exception(graph)


def test_payload_round_trip_keeps_full_canonical_document(tools):
    value = {"state": comparison.full_typed({"payload": b"x" * 5000, "decision": False})}
    compressed, pin = comparison.pack_payload(value)
    raw, decoded = comparison.unpack_payload(tools, compressed, pin)
    assert decoded == value
    assert raw == comparison.canonical(value)
    assert comparison.pack_payload(value) == (compressed, pin)


@pytest.mark.parametrize("mutation", ["truncated", "trailing", "second_member", "raw_size", "raw_hash", "compressed_hash"])
def test_payload_rejects_truncation_members_and_rehashed_pin_lies(tools, mutation):
    compressed, pin = comparison.pack_payload({"retained": "x" * 1000})
    if mutation == "truncated":
        compressed = compressed[:-1]
    elif mutation == "trailing":
        compressed += b"extra"
    elif mutation == "second_member":
        compressed += gzip.compress(b"{}", mtime=0)
    elif mutation == "raw_size":
        pin["uncompressed_bytes"] += 1
    elif mutation == "raw_hash":
        pin["uncompressed_sha256"] = "0" * 64
    elif mutation == "compressed_hash":
        pin["compressed_sha256"] = "0" * 64
    if mutation in {"truncated", "trailing", "second_member"}:
        pin["compressed_bytes"], pin["compressed_sha256"] = len(compressed), comparison.sha(compressed)
    with pytest.raises((comparison.ComparisonError, ValueError)):
        comparison.unpack_payload(tools, compressed, pin)


def test_compressed_payload_bomb_is_bounded_during_inflation(tools, monkeypatch):
    compressed = gzip.compress(b"x" * 10000, mtime=0)
    monkeypatch.setattr(comparison, "MAX_PAYLOAD_BYTES", 200)
    pin = {"compressed_sha256": comparison.sha(compressed), "compressed_bytes": len(compressed),
           "uncompressed_sha256": comparison.sha(b"x" * 10000), "uncompressed_bytes": 200}
    with pytest.raises(comparison.ComparisonError, match="truncated, oversized"):
        comparison.unpack_payload(tools, compressed, pin)


def test_payload_publication_caps_refuse_without_truncation(monkeypatch):
    monkeypatch.setattr(comparison, "MAX_PAYLOAD_BYTES", 10)
    with pytest.raises(comparison.ComparisonError, match="uncompressed payload"):
        comparison.pack_payload({"large": "x" * 100})
    monkeypatch.setattr(comparison, "MAX_PAYLOAD_BYTES", 10000)
    monkeypatch.setattr(comparison, "MAX_COMPRESSED_BYTES", 10)
    with pytest.raises(comparison.ComparisonError, match="compressed payload"):
        comparison.pack_payload({"large": "x" * 100})


def test_noncanonical_json_and_duplicate_keys_do_not_become_evidence(tools):
    for raw in (b'{ "x": 1 }', b'{"x":1,"x":2}'):
        compressed = gzip.compress(raw, mtime=0)
        pin = {"compressed_bytes": len(compressed), "compressed_sha256": comparison.sha(compressed),
               "uncompressed_bytes": len(raw), "uncompressed_sha256": comparison.sha(raw)}
        with pytest.raises(ValueError):
            comparison.unpack_payload(tools, compressed, pin)


def module_fixture(tmp_path, monkeypatch):
    package = tmp_path / "src/data_sheets_schema"
    package.mkdir(parents=True)
    sources = {
        comparison.MODULES[0]: b"from dataclasses import dataclass\n@dataclass(frozen=True)\nclass Token:\n    value: str\n",
        comparison.MODULES[1]: b"from data_sheets_schema.native_shared_contract import Token\ndef token():\n    return Token('saved')\n",
        comparison.MODULES[2]: b"from data_sheets_schema.native_shared_evidence import token\nclass Trace:\n    def __init__(self):\n        self.token = token()\n",
    }
    for name, raw in sources.items():
        (package / (name + ".py")).write_bytes(raw)
    (package / "__init__.py").write_text("raise RuntimeError('must not import package')\n")
    cache = package / "__pycache__"
    cache.mkdir()
    for name in sources:
        (cache / (name + ".cpython-313.pyc")).write_bytes(b"hostile invalid import cache")
    monkeypatch.setattr(comparison, "MODULE_PINS", {role: {n: comparison.sha(r) for n, r in sources.items()}
                                                  for role in comparison.ROLES})
    return sources


def test_verified_compilation_uses_canonical_identity_not_aliases_or_pyc(tools, tmp_path, monkeypatch):
    sources = module_fixture(tmp_path, monkeypatch)
    sentinel = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "data_sheets_schema", sentinel)
    modules = comparison.compile_modules(tools, tmp_path, "candidate", sources)
    assert sys.modules["data_sheets_schema"] is sentinel
    with comparison.activated(modules):
        value = modules[comparison.MODULES[2]].Trace()
        assert type(value.token) is modules[comparison.MODULES[0]].Token
        assert type(value.token).__module__ == "data_sheets_schema.native_shared_contract"
        assert modules[comparison.MODULES[2]].Trace.__init__.__code__.co_filename.startswith("trace-comparison/candidate/")
    assert sys.modules["data_sheets_schema"] is sentinel


def test_changed_selected_source_refuses_before_compilation(tools, tmp_path, monkeypatch):
    sources = module_fixture(tmp_path, monkeypatch)
    path = tmp_path / "src/data_sheets_schema" / (comparison.MODULES[2] + ".py")
    path.write_bytes(sources[comparison.MODULES[2]] + b"\nchanged=True\n")
    with pytest.raises(ValueError, match="hash differs"):
        comparison.compile_modules(tools, tmp_path, "candidate", sources)


@pytest.mark.parametrize("event,args", [
    ("subprocess.Popen", ("/bin/echo", ["echo"], None, None)),
    ("os.exec", ("/bin/true", ["true"], {})), ("os.posix_spawn", ("/bin/true", ["true"], {})),
    ("socket.connect", (None, ("127.0.0.1", 1))), ("ctypes.dlopen", (None,)),
    ("ctypes.dlsym/handle", (0, "system")), ("os.chmod", (17, 0o777, -1)),
    ("os.truncate", (17, 0)), ("os.utime", (17, None, None, -1)),
    ("os.setxattr", (17, b"user.attribute", b"value", 0)),
    ("os.removexattr", (17, b"user.attribute")), ("os.chflags", ("input", 0, True)),
    ("os.rename", ("a", "b", 10, 11)), ("os.link", ("a", "b", 10, 11)),
    ("open", (17, "w", os.O_WRONLY)), ("open", (17, "r+", 0)),
    ("open", ("x", None, os.O_CREAT | os.O_RDONLY)),
])
def test_worker_effect_boundary_denies_complete_args_and_descriptor_forms(event, args):
    with pytest.raises(comparison.ComparisonError):
        comparison.effect_guard(event, args)


def test_worker_read_boundary_allows_verified_regular_reads_and_descriptors():
    comparison.effect_guard("open", ("input", "r", os.O_RDONLY | os.O_NOFOLLOW))
    comparison.effect_guard("open", (17, "r", 0))


def test_constructor_clock_excludes_full_semantic_readback(monkeypatch):
    clock = {"value": 0}
    monkeypatch.setattr(comparison.time, "thread_time_ns", lambda: clock["value"])
    monkeypatch.setattr(comparison.time, "perf_counter_ns", lambda: clock["value"])
    class Tools:
        typed_value = staticmethod(comparison.full_typed)
        @staticmethod
        def semantic_trace(trace):
            clock["value"] += 1000
            return {"saved": trace}
    def constructor():
        clock["value"] += 7
        return "value"
    monkeypatch.setattr(comparison, "semantic_trace", lambda tools, trace: tools.semantic_trace(trace))
    _, raw, metrics = comparison.construct(Tools, constructor, timed=True)
    assert metrics["thread_cpu_ns"] == metrics["wall_ns"] == 7
    assert metrics["fingerprint_wall_ns"] == 1000
    assert b'"saved":"value"' in raw


def test_current_advance_uses_exact_captured_pending_command_and_retains_wrong_command_graph(tools, monkeypatch):
    command = "selected-helper --argument 'original spelling'"
    calls = []
    class Trace:
        @staticmethod
        def pending():
            return ("pending-id",)
        @staticmethod
        def request(identity):
            assert identity == "pending-id"
            return SimpleNamespace(tool_name="Bash", input_json=comparison.canonical({"command": command}))
        @staticmethod
        def current_advance(identity, selected):
            calls.append((identity, selected))
            if selected != command:
                error = ValueError("not the selected advance")
                error.__cause__ = ValueError("exact command mismatch")
                raise error
            return {"admitted": identity, "command": selected}
    monkeypatch.setattr(tools, "semantic_trace", lambda trace: {})
    with comparison.lossless_formatter(tools):
        result = comparison.semantic_trace(tools, Trace())
    assert calls == [("pending-id", command), ("pending-id", command + comparison.WRONG_COMMAND_SUFFIX)]
    advance = result["current_advance"]
    assert advance["tool_use_id"] == "pending-id" and advance["command"] == command
    assert advance["exact"]["status"] == "returned"
    assert advance["wrong_command"]["status"] == "refused"
    assert advance["wrong_command"]["exception"]["cause"]["arguments"] == comparison.full_typed(("exact command mismatch",))
    comparison.validate_exception(advance["wrong_command"]["exception"])


@pytest.mark.parametrize("pending,tool_name,inputs", [
    ((), "Bash", {"command": "selected"}), (("a", "b"), "Bash", {"command": "selected"}),
    (("a",), "Read", {"command": "selected"}), (("a",), "Bash", {}),
])
def test_current_advance_refuses_another_checkpoint_shape(tools, monkeypatch, pending, tool_name, inputs):
    monkeypatch.setattr(tools, "semantic_trace", lambda trace: {})
    trace = SimpleNamespace(pending=lambda: pending,
        request=lambda identity: SimpleNamespace(tool_name=tool_name, input_json=comparison.canonical(inputs)))
    with pytest.raises(comparison.ComparisonError):
        comparison.semantic_trace(tools, trace)
