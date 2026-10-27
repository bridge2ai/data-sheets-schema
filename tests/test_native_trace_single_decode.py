"""#4537: complete constructor parity with the exact literal 0125 source.

Reversing only the reviewed factoring reconstructs the complete original module.
Its fixed SHA256 is checked before compilation, so the oracle neither requires
Git/history at test time nor silently follows an unrelated production change.
The oracle uses the canonical module name; no type-name normalization is needed.
"""
from copy import deepcopy
from dataclasses import fields, is_dataclass, replace
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_observations as observed
from tests.test_native_shared_observations import POLICY, SESSION, events, initial, prefix


PARENT_SHA256 = "3bc93c2d1720d4e41ee83e7be7d8758a56836062c316f75ecc4b505e80b6d3ab"
CONSTRUCTOR_REUSE = '''        # Decode in initialization's original order, then reuse only this
        # constructor's rows for indexing. No parsed state survives in a cache.
        native=list(rows(transcript));parent=list(rows(control))
        initialized,*_=_initialization_from_rows(transcript,control,native,parent,policy=policy,runtime=runtime)
'''
HELPER_SPLIT = '''    return _initialization_from_rows(transcript,control,native,parent,policy=policy,runtime=runtime)


def _initialization_from_rows(transcript,control,native,parent,*,policy,runtime):
    """Validate already decoded rows owned by this one caller."""
'''


@pytest.fixture(scope="module")
def literal_parent():
    source = Path(observed.__file__).read_text(encoding="utf-8")
    substitutions = (
        (CONSTRUCTOR_REUSE, "        initialized,*_=initialization(transcript,control,policy=policy,runtime=runtime)\n"),
        ("        for number,raw,value in native:\n", "        for number,raw,value in rows(transcript):\n"),
        ("        for number,raw,value in parent:\n", "        for number,raw,value in rows(control):\n"),
        (HELPER_SPLIT, ""),
    )
    for candidate, original in substitutions:
        assert source.count(candidate) == 1
        source = source.replace(candidate, original)
    assert hashlib.sha256(source.encode()).hexdigest() == PARENT_SHA256
    namespace = {"__name__": observed.__name__}
    exec(compile(source, "literal0125/native_shared_observations.py", "exec"), namespace)
    return SimpleNamespace(**namespace)


def typed(value):
    """Retain every field, scalar type, sequence type and mapping order."""
    identity = type(value).__module__ + "." + type(value).__qualname__
    if is_dataclass(value):
        return (identity, tuple((field.name, typed(getattr(value, field.name))) for field in fields(value)))
    if type(value) is dict:
        return (identity, tuple((typed(key), typed(item)) for key, item in value.items()))
    if type(value) in (list, tuple):
        return (identity, tuple(map(typed, value)))
    if value is None or type(value) in (str, bytes, int, bool, float):
        return (identity, value)
    raise AssertionError(f"uncovered semantic type {identity}")


def exception_graph(error, seen=None):
    seen = {} if seen is None else seen
    if error is None:
        return None
    if id(error) in seen:
        return ("reference", seen[id(error)])
    number = len(seen)
    seen[id(error)] = number
    return (number, type(error).__module__, type(error).__qualname__, typed(error.args),
            error.__suppress_context__, typed(getattr(error, "__notes__", None)),
            exception_graph(error.__cause__, seen), exception_graph(error.__context__, seen))


def outcome(call):
    try:
        return ("returned", typed(call()))
    except Exception as error:
        return ("refused", exception_graph(error))


def constructor(module, transcript, control, *, runtime, session=SESSION, policy=POLICY):
    trace = module.Trace.__new__(module.Trace)
    try:
        trace.__init__(transcript, control, session_id=session, policy=deepcopy(policy), runtime=deepcopy(runtime))
    except Exception as error:
        return ("refused", exception_graph(error), typed(vars(trace)))
    methods = [("pending", outcome(trace.pending))]
    for identity in (*trace.calls, "missing"):
        for method in ("request", "admitted", "settled"):
            methods.append(((identity, method), outcome(lambda: getattr(trace, method)(identity))))
    return ("returned", typed(vars(trace)), tuple(methods))


def inputs(tool="Read", raw=b'{"value":false,"missing":null,"list":[1,"x"]}\n'):
    native, parent, _ = events(tool, raw)
    initialized, sent, runtime = initial()
    return initialized + native, sent + parent, runtime


@pytest.mark.parametrize("tool", ["Read", "Write"])
@pytest.mark.parametrize("raw", [b"{}", b'{"long":"' + b"a" * 100000 + b'"}\n',
                                '{"text":"α\u2028β","integer":1,"float":1.0}\n'.encode()])
def test_complete_trace_state_and_public_joins_match_literal_parent(literal_parent, tool, raw):
    native, parent, runtime = inputs(tool, raw)
    args = prefix("transcript", native), prefix("control", parent)
    expected = constructor(literal_parent, *args, runtime=runtime)
    assert expected[0] == "returned"
    assert constructor(observed, *args, runtime=runtime) == expected
    assert outcome(lambda: observed.initialization(*args, policy=POLICY, runtime=runtime)) == outcome(
        lambda: literal_parent.initialization(*args, policy=POLICY, runtime=runtime))


@pytest.mark.parametrize("change", [
    "missing_init", "duplicate_init", "late_init", "wrong_model", "wrong_runtime",
    "wrong_policy", "wrong_session", "empty_session", "child_call", "wrong_role",
    "duplicate_call", "duplicate_result", "duplicate_callback", "foreign_callback",
    "callback_after_result", "different_decision", "contradictory_admission",
    "terminal_then_event", "cancel", "bad_content", "bad_block", "bad_tool",
    "malformed_callback", "untyped_callback", "wrong_streams",
])
def test_complete_constructor_refusal_and_partial_state_match_literal_parent(literal_parent, change):
    native, parent, runtime = inputs()
    policy, session = deepcopy(POLICY), SESSION
    if change == "missing_init": native = native[2:]
    elif change == "duplicate_init": native.insert(1, deepcopy(native[1]))
    elif change == "late_init": native = native[2:] + native[:2]
    elif change == "wrong_model": native[1]["model"] = "foreign"
    elif change == "wrong_runtime": runtime["model"] = "foreign"
    elif change == "wrong_policy": policy["pretool_control"]["matcher"] = "Read"
    elif change == "wrong_session": session = "foreign"
    elif change == "empty_session": session = ""
    elif change == "child_call": native[2]["parent_tool_use_id"] = "parent"
    elif change == "wrong_role": native[2]["message"]["role"] = "user"
    elif change == "duplicate_call": native.insert(3, deepcopy(native[2]))
    elif change == "duplicate_result": native.append(deepcopy(native[-1]))
    elif change == "duplicate_callback": native.insert(4, deepcopy(native[3]))
    elif change == "foreign_callback": native[3]["request"]["input"]["tool_input"]["file_path"] = "/other"
    elif change == "callback_after_result": native[3], native[4] = native[4], native[3]
    elif change == "different_decision": parent[-1]["request"]["request"]["input"]["tool_name"] = "Write"
    elif change == "contradictory_admission": parent[-1]["response"]["response"]["response"] = {"deny": True}
    elif change == "terminal_then_event": native.insert(2, {"type": "result", "session_id": SESSION})
    elif change == "cancel": native.append({"type": "control_cancel_request"})
    elif change == "bad_content": native[2]["message"]["content"] = None
    elif change == "bad_block": native[2]["message"]["content"] = [None]
    elif change == "bad_tool": native[2]["message"]["content"][0]["name"] = "WebFetch"
    elif change == "malformed_callback": native[3]["request"]["input"] = None
    elif change == "untyped_callback": native[3]["request"] = None
    args = prefix("transcript", native), prefix("control", parent)
    if change == "wrong_streams": args = args[::-1]
    expected = constructor(literal_parent, *args, runtime=runtime, session=session, policy=policy)
    assert expected[0] == "refused"
    assert constructor(observed, *args, runtime=runtime, session=session, policy=policy) == expected


def with_raw(value, raw):
    return replace(value, raw=raw, bytes=len(raw), sha256=observed.c.sha(raw), lines=raw.count(b"\n"))


@pytest.mark.parametrize("native_raw,parent_raw", [
    (b"not JSON\n", b"also invalid\n"), (b"[]\n", b"not JSON\n"),
    (b"\n", b"not JSON\n"), (b'{"a":1,"a":2}\n', b"not JSON\n"),
    (None, b"not JSON\n"), (b"{}\n", b"not JSON\n"),
])
def test_decode_and_initialization_error_precedence(literal_parent, native_raw, parent_raw):
    native, parent, runtime = inputs()
    transcript, control = prefix("transcript", native), prefix("control", parent)
    if native_raw is not None: transcript = with_raw(transcript, native_raw)
    control = with_raw(control, parent_raw)
    expected = constructor(literal_parent, transcript, control, runtime=runtime, session="foreign")
    assert expected[0] == "refused"
    assert constructor(observed, transcript, control, runtime=runtime, session="foreign") == expected
    assert outcome(lambda: observed.initialization(transcript, control, policy=POLICY, runtime=runtime)) == outcome(
        lambda: literal_parent.initialization(transcript, control, policy=POLICY, runtime=runtime))


def test_each_constructor_decodes_each_stream_once_in_the_original_order(monkeypatch, literal_parent):
    native, parent, runtime = inputs()
    args = prefix("transcript", native), prefix("control", parent)
    calls, original = [], observed.rows
    def counted(value):
        calls.append(value.stream)
        return original(value)
    monkeypatch.setattr(observed, "rows", counted)
    assert constructor(observed, *args, runtime=runtime) == constructor(literal_parent, *args, runtime=runtime)
    assert calls == ["transcript", "control"]
    calls.clear()
    observed.initialization(*args, policy=POLICY, runtime=runtime)
    assert calls == ["transcript", "control"]


def test_changed_capture_and_independent_mutable_trace_state(literal_parent):
    native, parent, runtime = inputs()
    args = prefix("transcript", native), prefix("control", parent)
    first = observed.Trace(*args, session_id=SESSION, policy=deepcopy(POLICY), runtime=runtime)
    first.frames[3]["message"]["content"][0]["input"]["file_path"] = "/mutated"
    first.callbacks["tool-1"][1]["request"]["input"]["tool_input"].clear()
    first.decisions["tool-1"][1]["response"].clear()
    assert constructor(observed, *args, runtime=runtime) == constructor(literal_parent, *args, runtime=runtime)
    native[2]["message"]["model"] = "changed"
    changed = prefix("transcript", native), args[1]
    expected = constructor(literal_parent, *changed, runtime=runtime)
    assert expected[0] == "refused"
    assert constructor(observed, *changed, runtime=runtime) == expected


@pytest.mark.parametrize("parent_decision", [False, True])
def test_pending_call_join_results_match(literal_parent, parent_decision):
    native, parent, runtime = inputs()
    args = prefix("transcript", native[:-1]), prefix("control", parent if parent_decision else parent[:-1])
    expected = constructor(literal_parent, *args, runtime=runtime)
    assert expected[0] == "returned"
    assert constructor(observed, *args, runtime=runtime) == expected
