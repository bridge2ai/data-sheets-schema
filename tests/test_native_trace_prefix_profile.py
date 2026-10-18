"""Adversarial checks for the retained-prefix diagnostic, with no native launch."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "notes/native_profile_recovery_2026-10-07/trace_prefix_profile.py"


@pytest.fixture
def profile():
    spec = importlib.util.spec_from_file_location("_trace_profile_adversarial", DRIVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def prefix_case():
    # Unicode separators are content, not physical LF boundaries. The retained
    # stream deliberately includes a later row outside this observation.
    prefix = '{"text":"one\u2028two"}\n{"row":2}\n'.encode()
    raw = prefix + b'{"later":true}\n'
    path = "/original/runner/attempt/transcript.jsonl"
    execution = "a" * 64
    identity = {"domain": "native_shared_stream_v1", "execution_sha256": execution,
                "stream": "transcript", "path": path}
    identity_raw = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ref = {"stream": "transcript", "path": path, "stream_id": digest(identity_raw),
           "through_bytes": len(prefix), "lines": 2, "sha256": digest(prefix)}
    kwargs = {"stream": "transcript", "original_path": path, "execution_sha256": execution}
    return ref, raw, prefix, kwargs


def test_prefix_binds_original_identity_and_only_observed_physical_rows(profile):
    ref, raw, prefix, kwargs = prefix_case()
    original = deepcopy(ref)
    assert profile.verify_prefix(ref, raw, **kwargs) == prefix
    assert profile.verify_prefix(ref, prefix + b'{"different_later":0}\n', **kwargs) == prefix
    assert ref == original
    assert digest(raw) != ref["sha256"]
    assert len(prefix.decode().splitlines()) > ref["lines"]


@pytest.mark.parametrize("field,value", [
    ("through_bytes", True), ("through_bytes", 1.0), ("through_bytes", 0),
    ("through_bytes", -1), ("through_bytes", 10**8),
    ("lines", True), ("lines", 2.0), ("lines", 0), ("lines", 3),
    ("sha256", "0" * 64), ("stream_id", "0" * 64),
    ("stream", "control"), ("path", "/relocated/runner/transcript.jsonl"),
])
def test_prefix_refuses_typed_count_hash_role_and_original_path_mutants(profile, field, value):
    ref, raw, _, kwargs = prefix_case()
    ref[field] = value
    with pytest.raises(profile.ProfileError):
        profile.verify_prefix(ref, raw, **kwargs)


def test_prefix_refuses_foreign_execution_partial_line_and_rehashed_blank_row(profile):
    ref, raw, prefix, kwargs = prefix_case()
    with pytest.raises(profile.ProfileError, match="identity"):
        profile.verify_prefix(ref, raw, **{**kwargs, "execution_sha256": "b" * 64})
    partial = {**ref, "through_bytes": len(prefix) - 1, "sha256": digest(prefix[:-1])}
    with pytest.raises(profile.ProfileError, match="boundary"):
        profile.verify_prefix(partial, raw, **kwargs)
    blank = prefix + b"\n"
    malformed = {**ref, "through_bytes": len(blank), "lines": 3, "sha256": digest(blank)}
    with pytest.raises(profile.ProfileError, match="blank"):
        profile.verify_prefix(malformed, blank, **kwargs)


@pytest.mark.parametrize("mutation", ["extra", "missing"])
def test_prefix_closed_shape(profile, mutation):
    ref, raw, _, kwargs = prefix_case()
    if mutation == "extra":
        ref["metadata"] = {"invented": True}
    else:
        del ref["stream_id"]
    with pytest.raises(profile.ProfileError, match="shape"):
        profile.verify_prefix(ref, raw, **kwargs)


def test_typed_state_distinguishes_types_order_missingness_and_bytes(profile):
    variants = [False, 0, 0.0, "0", None, [], (), {}, b"", "",
                [1, 2], [2, 1], {1: "x"}, {"1": "x"},
                {"first": 1, "second": 2}, {"second": 2, "first": 1}]
    encoded = [profile.canonical(profile.typed_value(value)) for value in variants]
    assert len(set(encoded)) == len(variants)
    original = {"nested": [True, {"raw": b"original"}]}
    snapshot = deepcopy(original)
    frozen = profile.typed_value(original)
    frozen[1].clear()
    assert original == snapshot


def refusal(cause, *, implicit=False, suppress=False):
    def call():
        try:
            raise cause
        except Exception:
            if implicit:
                raise ValueError("same outer refusal")
            if suppress:
                raise ValueError("same outer refusal") from None
            raise ValueError("same outer refusal") from cause
    return call


def test_refusal_comparison_preserves_cause_context_and_suppression(profile):
    calls = [refusal(TypeError("source A")), refusal(TypeError("source B")),
             refusal(KeyError("source A")), refusal(TypeError("source A"), implicit=True),
             refusal(TypeError("source A"), suppress=True)]
    encoded = [profile.canonical(profile.outcome(call)) for call in calls]
    assert len(set(encoded)) == len(calls)


def test_constructor_refusal_fingerprint_preserves_the_same_failure_graph(profile):
    first = profile.measured_trace(refusal(TypeError("source A")), instrumented=False)
    second = profile.measured_trace(refusal(TypeError("source B")), instrumented=False)
    checked = profile.measured_trace(refusal(TypeError("source A")), instrumented=True)
    assert first["status"] == second["status"] == checked["status"] == "refused"
    assert first["semantic_sha256"] != second["semantic_sha256"]
    assert first["semantic_sha256"] == checked["semantic_sha256"]


def test_exception_graph_cycles_are_lossless_and_notes_remain_distinct(profile):
    self_cycle = ValueError("same")
    self_cycle.__cause__ = self_cycle
    other_cycle = ValueError("same")
    child = ValueError("same")
    other_cycle.__cause__ = child
    child.__cause__ = other_cycle
    own = profile.exception_value(self_cycle)
    other = profile.exception_value(other_cycle)
    assert own["cause"] == {"reference": own["node"]}
    assert other["cause"]["cause"] == {"reference": other["node"]}
    assert profile.canonical(own) != profile.canonical(other)
    plain = ValueError("same")
    with_note = ValueError("same")
    with_note.add_note("retained first failure")
    assert profile.exception_value(plain) != profile.exception_value(with_note)


def test_exception_graph_overflow_refuses_instead_of_equal_truncation(profile):
    root = ValueError("first")
    node = root
    for index in range(31):
        following = ValueError(str(index))
        node.__cause__ = following
        node = following
    assert profile.exception_value(root)["node"] == 0
    node.__cause__ = ValueError("unrepresentable 33rd node")
    with pytest.raises(profile.ProfileError, match="graph.*bound"):
        profile.exception_value(root)
    def refused():
        raise root
    with pytest.raises(profile.ProfileError, match="graph.*bound"):
        profile.outcome(refused)


def source_modules(profile, root):
    # Main does not include the unmerged historical native_shared modules.
    # These are explicitly synthetic loader controls; the separate pinned
    # artifact diagnostic is responsible for exercising the real Trace.
    values = {
        "native_shared_contract": (
            b"from dataclasses import dataclass\n"
            b"@dataclass(frozen=True)\n"
            b"class Token:\n"
            b"    label: str\n"),
        "native_shared_evidence": (
            b"from data_sheets_schema.native_shared_contract import Token\n"
            b"def token():\n"
            b"    return Token('synthetic loader control')\n"),
        "native_shared_observations": (
            b"from data_sheets_schema import native_shared_contract as c\n"
            b"from data_sheets_schema.native_shared_evidence import token\n"
            b"class Trace:\n"
            b"    def __init__(self):\n"
            b"        self.token = token()\n"),
    }
    assert set(values) == set(profile.MODULES)
    package = root / "src/data_sheets_schema"
    package.mkdir(parents=True)
    for name, raw in values.items():
        (package / (name + ".py")).write_bytes(raw)
    return package, values


def test_verified_loader_ignores_package_init_and_pyc_and_restores_module_owners(profile, tmp_path, monkeypatch):
    package, values = source_modules(profile, tmp_path)
    (package / "__init__.py").write_text("raise AssertionError('package initializer executed')\n")
    cache = package / "__pycache__"
    cache.mkdir()
    for name in profile.MODULES:
        (cache / f"{name}.{sys.implementation.cache_tag}.pyc").write_bytes(b"hostile cached bytecode")
    sentinel = ModuleType("data_sheets_schema")
    sentinel.__path__ = []
    monkeypatch.setitem(sys.modules, "data_sheets_schema", sentinel)
    before = {name: value for name, value in sys.modules.items()
              if name == "data_sheets_schema" or name.startswith("data_sheets_schema.")}
    with profile.load_modules(tmp_path, values) as loaded:
        observed = loaded["native_shared_observations"]
        assert observed.Trace.__init__.__code__.co_filename == (
            "pinned0125/src/data_sheets_schema/native_shared_observations.py")
        assert observed.c is loaded["native_shared_contract"]
        assert type(observed.Trace().token) is loaded["native_shared_contract"].Token
        assert sys.modules["data_sheets_schema"] is not sentinel
    after = {name: value for name, value in sys.modules.items()
             if name == "data_sheets_schema" or name.startswith("data_sheets_schema.")}
    assert after == before


def test_loader_refuses_changed_source_before_executing_it(profile, tmp_path):
    package, values = source_modules(profile, tmp_path)
    target = package / (profile.MODULES[0] + ".py")
    target.write_bytes(b"raise AssertionError('changed source executed')\n")
    before = {name: value for name, value in sys.modules.items()
              if name == "data_sheets_schema" or name.startswith("data_sheets_schema.")}
    with pytest.raises(profile.ProfileError, match="hash"):
        with profile.load_modules(tmp_path, values):
            pytest.fail("changed source was admitted")
    after = {name: value for name, value in sys.modules.items()
             if name == "data_sheets_schema" or name.startswith("data_sheets_schema.")}
    assert after == before
