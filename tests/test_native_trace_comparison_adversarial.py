"""#4657/#4658/#4661/#4662 independent evidence and parent controls.

All subprocess replies and source admissions below are explicit software
fixtures. These tests do not execute native code, retained captures or providers.
"""
from copy import deepcopy
from pathlib import Path
import base64
import signal
import subprocess
from types import ModuleType, SimpleNamespace

import pytest


DRIVER = Path(__file__).resolve().parents[1] / "notes/native_trace_comparison_2026-10-08/compare_trace.py"


@pytest.fixture
def driver():
    module = ModuleType("_trace_comparison_adversarial")
    module.__file__ = str(DRIVER)
    exec(compile(DRIVER.read_bytes(), str(DRIVER), "exec"), module.__dict__)
    return module


def fixture_payload(driver):
    tools = driver.utility()
    command = "synthetic helper command, never executed"
    state = {"transcript": None, "control": None, "session": "synthetic",
             "policy": {}, "calls": {"tool-1": (3, 0, {"id": "tool-1", "name": "Bash",
                                                       "input": {"command": command}})},
             "callbacks": {}, "results": {},
             "decisions": {}, "frames": {}, "terminal": None}
    positive = {"status": "returned", "semantics": {
        "state": driver.full_typed(state), "pending": driver.full_typed(("tool-1",)),
        "tool_methods": {"tool-1": {name: {"status": "refused", "exception":
            tools.exception_value(ValueError("synthetic unobserved callback"))}
            for name in ("request", "admitted", "settled")}}}}
    admitted = {"status": "returned", "value": driver.full_typed({"synthetic_admission": "tool-1"})}
    positive["semantics"]["tool_methods"]["tool-1"]["request"] = {"status": "returned",
        "value": driver.full_typed({"tool_use_id": "tool-1", "input_json": driver.canonical({"command": command})})}
    positive["semantics"]["tool_methods"]["tool-1"]["admitted"] = deepcopy(admitted)
    positive["semantics"]["current_advance"] = {"tool_use_id": "tool-1", "command": command,
        "exact": admitted, "wrong_command": {"status": "refused",
            "exception": tools.exception_value(ValueError("different synthetic command"))}}
    for index, stream in enumerate(("transcript", "control")):
        raw = b"{}\n"
        values = {"stream": stream, "path": "/synthetic/" + stream, "raw": raw,
                  "bytes": len(raw), "sha256": driver.sha(raw), "lines": 1}
        positive["semantics"]["state"][1][index][1] = ["dataclass",
            "data_sheets_schema.native_shared_contract.EvidencePrefix",
            [[name, driver.full_typed(value)] for name, value in values.items()]]
    return {"format": driver.PAYLOAD_FORMAT, "positive": positive,
            "refusal_controls": [{"control": control, "outcome": {
                "status": "refused", "exception": tools.exception_value(ValueError(control))}}
                for control in driver.CONTROLS]}


def evidence(driver):
    binding, python_pin, driver_pin = {"synthetic_capture": "a" * 64}, {"sha256": "b" * 64}, "c" * 64
    execution = "d" * 64
    binding["checkpoint"] = {"execution_sha256": execution, "session_id": "synthetic",
        "policy_sha256": driver.sha(driver.canonical({})), "streams": {}}
    for stream in ("transcript", "control"):
        binding["checkpoint"]["streams"][stream] = {"stream": stream, "through_bytes": 3,
            "lines": 1, "sha256": driver.sha(b"{}\n"), "stream_id": driver.sha(driver.canonical({
                "domain": "native_shared_stream_v1", "execution_sha256": execution,
                "stream": stream, "path": "/synthetic/" + stream}))}
    payload = fixture_payload(driver)
    compressed, pin = driver.pack_payload(payload)
    required = {"timed_constructors": 6, "decode_checks": 2, "refusal_controls": 6,
                "instance_checks": 2, "advance_controls": 4}
    summary = {"format": driver.FORMAT, "scope": driver.SCOPE, "status": "completed",
        "binding": binding, "driver_sha256": driver_pin, "utility_sha256": driver.UTILITY_SHA256,
        "python_identity": python_pin, "startup_flags": {"isolated": 1, "no_site": 1, "dont_write_bytecode": True},
        "samples": [{"sample": index, "role": role, "timed": True, "thread_cpu_ns": 10,
                     "wall_ns": 20, "fingerprint_wall_ns": 5, "status": "returned",
                     "semantic_sha256": driver.sha(driver.canonical(payload["positive"]))}
                    for index, role in enumerate(driver.ORDER)],
        "decode_counts": {"baseline": {"transcript": 2, "control": 2},
                          "candidate": {"transcript": 1, "control": 1}},
        "instance_independence": {role: True for role in driver.ROLES},
        "payloads": {role + ".json.gz": deepcopy(pin) for role in driver.ROLES},
        "required": required, "completed": dict(required), "failed": [], "missing": [],
        "parity_passed": True, "inputs_unchanged": True,
        "environment": {"python": "synthetic", "platform": "synthetic", "machine": "synthetic"},
        "worker_wall_ns": 100, "overhead": {"setup_wall_ns": 10, "final_verification_wall_ns": 10,
                                           "evidence_pack_wall_ns": 10},
        "execution_authorized": False, "native_acceptance_evaluated": False, "scientific_eligibility": False,
        "limitations": list(driver.LIMITATIONS)}
    return SimpleNamespace(summary=summary, payload=payload, binding=deepcopy(binding),
        blobs={role + ".json.gz": compressed for role in driver.ROLES},
        python_pin=python_pin, driver_pin=driver_pin)


def validate(driver, case):
    return driver.summary_validation(driver.utility(), case.summary, case.blobs,
                                     case.binding, case.driver_pin, case.python_pin)


def repack(driver, case, payload, roles=None):
    compressed, pin = driver.pack_payload(payload)
    for role in driver.ROLES if roles is None else roles:
        name = role + ".json.gz"
        case.blobs[name], case.summary["payloads"][name] = compressed, deepcopy(pin)
        for sample in case.summary["samples"]:
            if sample["role"] == role:
                sample["semantic_sha256"] = driver.sha(driver.canonical(payload["positive"]))


def test_complete_synthetic_evidence_is_accepted_without_mutating_inputs(driver):
    case = evidence(driver)
    before = deepcopy(vars(case))
    assert validate(driver, case) == case.summary
    assert vars(case) == before


@pytest.mark.parametrize("mutation", [
    "missing_semantics", "empty_semantics", "missing_state", "missing_pending", "missing_methods",
    "extra_semantics", "null_refusal", "empty_refusal", "wrong_refusal_type", "missing_control",
    "duplicate_control", "reordered_controls", "extra_payload", "extra_positive", "bad_typed_scalar",
])
def test_rehashed_equal_payloads_cannot_replace_complete_evidence(driver, mutation):
    case = evidence(driver)
    payload = deepcopy(case.payload)
    if mutation == "missing_semantics": del payload["positive"]["semantics"]
    elif mutation == "empty_semantics": payload["positive"]["semantics"] = {}
    elif mutation == "missing_state": del payload["positive"]["semantics"]["state"]
    elif mutation == "missing_pending": del payload["positive"]["semantics"]["pending"]
    elif mutation == "missing_methods": del payload["positive"]["semantics"]["tool_methods"]
    elif mutation == "extra_semantics": payload["positive"]["semantics"]["unbound"] = True
    elif mutation == "null_refusal": payload["refusal_controls"][0]["outcome"]["exception"] = None
    elif mutation == "empty_refusal": payload["refusal_controls"][0]["outcome"]["exception"] = {}
    elif mutation == "wrong_refusal_type": payload["refusal_controls"][0]["outcome"]["exception"]["type"] = False
    elif mutation == "missing_control": payload["refusal_controls"].pop()
    elif mutation == "duplicate_control": payload["refusal_controls"][1] = deepcopy(payload["refusal_controls"][0])
    elif mutation == "reordered_controls": payload["refusal_controls"].reverse()
    elif mutation == "extra_payload": payload["unbound"] = True
    elif mutation == "extra_positive": payload["positive"]["unbound"] = True
    elif mutation == "bad_typed_scalar": payload["positive"]["semantics"]["pending"] = ["bool", 1]
    repack(driver, case, payload)
    with pytest.raises(driver.ComparisonError):
        validate(driver, case)


def test_different_complete_payloads_refuse_even_when_each_hash_is_correct(driver):
    case = evidence(driver)
    changed = deepcopy(case.payload)
    changed["refusal_controls"][0]["outcome"]["exception"]["arguments"] = driver.full_typed(("changed",))
    repack(driver, case, changed, ("candidate",))
    with pytest.raises(driver.ComparisonError, match="payloads differ"):
        validate(driver, case)


@pytest.mark.parametrize("mutation", ["session", "policy", "stream_path", "stream_bytes"])
def test_equal_rehashed_states_cannot_substitute_a_different_captured_input(driver, mutation):
    case = evidence(driver)
    payload = deepcopy(case.payload)
    state = {key[1]: value for key, value in payload["positive"]["semantics"]["state"][1]}
    if mutation == "session": state["session"][1] = "another session"
    elif mutation == "policy": state["policy"][1] = [[driver.full_typed("changed"), driver.full_typed(False)]]
    else:
        slots = dict(state["transcript"][2])
        if mutation == "stream_path": slots["path"][1] = "/different/transcript"
        else:
            raw = b'{"changed":true}\n'
            slots["raw"][1] = base64.b64encode(raw).decode("ascii")
            slots["bytes"][1], slots["sha256"][1], slots["lines"][1] = len(raw), driver.sha(raw), 1
    repack(driver, case, payload)
    with pytest.raises(driver.ComparisonError, match="checkpoint"):
        validate(driver, case)


@pytest.mark.parametrize("mutation", ["missing", "identity", "command", "exact_refused", "wrong_returned", "different_admission"])
def test_current_advance_observations_are_complete_and_match_the_admitted_call(driver, mutation):
    case = evidence(driver)
    payload = deepcopy(case.payload)
    semantics = payload["positive"]["semantics"]
    advance = semantics["current_advance"]
    if mutation == "missing": del semantics["current_advance"]
    elif mutation == "identity": advance["tool_use_id"] = "different-tool"
    elif mutation == "command": advance["command"] += " changed"
    elif mutation == "exact_refused": advance["exact"] = deepcopy(advance["wrong_command"])
    elif mutation == "wrong_returned": advance["wrong_command"] = deepcopy(advance["exact"])
    elif mutation == "different_admission":
        advance["exact"]["value"] = driver.full_typed({"synthetic_admission": "foreign"})
    repack(driver, case, payload)
    with pytest.raises(driver.ComparisonError):
        validate(driver, case)


@pytest.mark.parametrize("mutation", [
    "binding", "driver", "utility", "python", "scope", "limitations", "startup_bool",
    "decode_bool", "sample_bool", "sample_role", "sample_order", "sample_hash", "sample_missing",
    "timing_bool", "negative_timing", "failed", "missing", "completed", "independence_false",
    "independence_extra", "acceptance", "parity_false", "inputs_false", "extra_summary", "advance_denominator",
])
def test_summary_identity_denominator_and_interpretation_cannot_be_forged(driver, mutation):
    case = evidence(driver)
    value = case.summary
    if mutation == "binding": value["binding"]["synthetic_capture"] = "0" * 64
    elif mutation == "driver": value["driver_sha256"] = "0" * 64
    elif mutation == "utility": value["utility_sha256"] = "0" * 64
    elif mutation == "python": value["python_identity"] = {"sha256": "0" * 64}
    elif mutation == "scope": value["scope"] = "whole native acceptance"
    elif mutation == "limitations": value["limitations"] = []
    elif mutation == "startup_bool": value["startup_flags"]["isolated"] = True
    elif mutation == "decode_bool": value["decode_counts"]["candidate"]["transcript"] = True
    elif mutation == "sample_bool": value["samples"][1]["sample"] = True
    elif mutation == "sample_role": value["samples"][0]["role"] = "candidate"
    elif mutation == "sample_order": value["samples"].reverse()
    elif mutation == "sample_hash": value["samples"][0]["semantic_sha256"] = "0" * 64
    elif mutation == "sample_missing": value["samples"].pop()
    elif mutation == "timing_bool": value["samples"][0]["wall_ns"] = True
    elif mutation == "negative_timing": value["samples"][0]["thread_cpu_ns"] = -1
    elif mutation == "failed": value["failed"] = ["candidate"]
    elif mutation == "missing": value["missing"] = ["candidate"]
    elif mutation == "completed": value["completed"]["timed_constructors"] = 5
    elif mutation == "independence_false": value["instance_independence"]["candidate"] = False
    elif mutation == "independence_extra": value["instance_independence"]["unknown"] = True
    elif mutation == "acceptance": value["execution_authorized"] = True
    elif mutation == "parity_false": value["parity_passed"] = False
    elif mutation == "inputs_false": value["inputs_unchanged"] = False
    elif mutation == "extra_summary": value["unbound"] = True
    elif mutation == "advance_denominator":
        del value["required"]["advance_controls"]
        del value["completed"]["advance_controls"]
    with pytest.raises(driver.ComparisonError):
        validate(driver, case)


@pytest.fixture
def parent_case(driver, tmp_path, monkeypatch):
    tools = driver.utility()
    roots = {name: tmp_path / name for name in ("baseline", "candidate", "recovery", "preparation", "runtime")}
    for path in roots.values(): path.mkdir()
    preparation = roots["preparation"] / "report.json"
    preparation.write_bytes(b"explicit synthetic preparation\n")
    interpreter = roots["runtime"] / "python"
    interpreter.write_bytes(b"never executed interpreter fixture\n")
    interpreter.chmod(0o700)
    fake_driver = tmp_path / "driver_checkout/notes/comparison/compare.py"
    fake_driver.parent.mkdir(parents=True)
    fake_driver.write_bytes(b"never executed driver fixture\n")
    monkeypatch.setattr(driver, "DRIVER", fake_driver)
    monkeypatch.setattr(driver, "utility", lambda: tools)
    monkeypatch.setattr(driver, "sys", SimpleNamespace(executable=str(interpreter), base_prefix=str(roots["runtime"]),
        flags=SimpleNamespace(isolated=1, no_site=1), dont_write_bytecode=True))
    case = evidence(driver)
    case.python_pin = tools.executable_identity(interpreter)
    case.driver_pin = driver.sha(fake_driver.read_bytes())
    case.summary.update(driver_sha256=case.driver_pin, python_identity=case.python_pin)
    calls = []
    def verify(selected_tools, baseline, candidate, recovery, selected_preparation):
        assert selected_tools is tools
        assert (baseline, candidate, recovery, selected_preparation) == (
            roots["baseline"], roots["candidate"], roots["recovery"], preparation)
        calls.append(True)
        return {"binding": deepcopy(case.binding)}
    monkeypatch.setattr(driver, "verify_inputs", verify)
    return SimpleNamespace(**vars(case), roots=roots, preparation=preparation, interpreter=interpreter,
        fake_driver=fake_driver, tools=tools, verifications=calls, output=tmp_path / "new-output")


def wire(driver, case):
    return driver.canonical({"summary": case.summary, "payloads_base64": {
        name: base64.b64encode(raw).decode("ascii") for name, raw in case.blobs.items()}})


def run(driver, case, output=None):
    return driver.run_comparison(case.roots["baseline"], case.roots["candidate"], case.roots["recovery"],
                                 case.preparation, case.output if output is None else output)


def test_parent_fixed_isolation_bound_and_complete_sidecars(driver, parent_case, monkeypatch):
    case, calls = parent_case, []
    def dispatch(argv):
        calls.append(argv)
        return 0, wire(driver, case), b"", False, False
    monkeypatch.setattr(driver, "dispatch", dispatch)
    result = run(driver, case)
    assert result["status"] == "completed" and result["diagnostic_wall_bound_seconds"] == 120
    assert len(case.verifications) == 2
    assert calls == [[str(case.interpreter), "-I", "-B", "-S", str(case.fake_driver), "--worker",
        "--baseline", str(case.roots["baseline"]), "--candidate", str(case.roots["candidate"]),
        "--recovery", str(case.roots["recovery"]), "--preparation", str(case.preparation)]]
    assert set(p.name for p in case.output.iterdir()) == {"report.json", "baseline.json.gz", "candidate.json.gz"}
    for name, raw in case.blobs.items(): assert (case.output / name).read_bytes() == raw
    assert case.tools.strict_json((case.output / "report.json").read_bytes()) == result


@pytest.mark.parametrize("failure", ["timeout", "overflow", "nonzero"])
def test_failed_child_cannot_publish_partial_measurements(driver, parent_case, monkeypatch, failure):
    case = parent_case
    monkeypatch.setattr(driver, "dispatch", lambda argv: (
        -9 if failure != "nonzero" else 1, wire(driver, case), b"partial diagnostic",
        failure == "timeout", failure == "overflow"))
    result = run(driver, case)
    assert result["status"] == ("diagnostic_timeout" if failure == "timeout" else "diagnostic_refused")
    assert result["parity_passed"] is False
    assert result["completed"] == {} and result["missing"] and result["failed"]
    assert set(p.name for p in case.output.iterdir()) == {"report.json"}


@pytest.mark.parametrize("destination", ["baseline", "candidate", "recovery", "preparation", "runtime", "driver", "existing", "alias", "dangling"])
def test_output_protection_refuses_before_child_or_input_admission(driver, parent_case, monkeypatch, tmp_path, destination):
    case = parent_case
    if destination in case.roots:
        output = case.roots[destination] / "new-output"
    elif destination == "driver": output = case.fake_driver.parents[2] / "new-output"
    elif destination == "existing":
        output = case.output
        output.mkdir()
        (output / "keep").write_bytes(b"keep")
    elif destination == "alias":
        alias = tmp_path / "alias"
        alias.symlink_to(case.roots["candidate"], target_is_directory=True)
        output = alias / "new-output"
    else:
        output = case.output
        output.symlink_to(tmp_path / "absent")
    monkeypatch.setattr(driver, "dispatch", lambda *a, **k: pytest.fail("launched before output refusal"))
    with pytest.raises(driver.ComparisonError): run(driver, case, output)
    assert not case.verifications
    if destination == "existing": assert (output / "keep").read_bytes() == b"keep"


@pytest.mark.parametrize("mutation", ["binding", "driver", "interpreter", "replaced_interpreter"])
def test_parent_rechecks_inputs_and_runtime_after_child_before_publication(driver, parent_case, monkeypatch, mutation):
    case = parent_case
    def dispatch(argv):
        raw = wire(driver, case)
        if mutation == "binding": case.binding["synthetic_capture"] = "0" * 64
        elif mutation == "driver": case.fake_driver.write_bytes(b"changed driver")
        elif mutation == "interpreter": case.interpreter.write_bytes(b"changed interpreter")
        else:
            replacement = case.interpreter.with_name("replacement")
            replacement.write_bytes(case.interpreter.read_bytes())
            replacement.chmod(0o700)
            replacement.replace(case.interpreter)
        return 0, raw, b"", False, False
    monkeypatch.setattr(driver, "dispatch", dispatch)
    with pytest.raises(driver.ComparisonError, match="changed"):
        run(driver, case)
    assert not case.output.exists()


@pytest.mark.parametrize("mutation", ["stderr", "wire_cap", "unknown_wire", "missing_blob", "bad_base64"])
def test_zero_exit_unaccepted_wire_never_publishes_success(driver, parent_case, monkeypatch, mutation):
    case = parent_case
    document = case.tools.strict_json(wire(driver, case))
    if mutation == "wire_cap": monkeypatch.setattr(driver, "MAX_WIRE_BYTES", 3)
    elif mutation == "unknown_wire": document["unbound"] = True
    elif mutation == "missing_blob": del document["payloads_base64"]["candidate.json.gz"]
    elif mutation == "bad_base64": document["payloads_base64"]["candidate.json.gz"] = "not base64!"
    monkeypatch.setattr(driver, "dispatch", lambda argv: (
        0, driver.canonical(document), b"unexpected diagnostic" if mutation == "stderr" else b"", False, False))
    with pytest.raises(ValueError): run(driver, case)
    assert not case.output.exists()


def fake_dispatch(driver, monkeypatch, *, pipe_data=b"ok", early_exit_wait=False, kill_race=False, spent=0):
    """Only OS/selector seams are simulated; real dispatch must own the deadline."""
    waits, kills, popens, closed, clock = [], [], [], [], [0.0]
    class Pipe:
        def __init__(self, number): self.number = number
        def fileno(self): return self.number
        def close(self): closed.append(self.number)
    streams = {101: [pipe_data, b""], 102: [b""]}
    class Child:
        pid = 43210
        returncode = None
        stdout, stderr = Pipe(101), Pipe(102)
        def poll(self): return self.returncode
        def wait(self, timeout=None):
            waits.append(timeout)
            if early_exit_wait and not kills:
                assert timeout is not None and 0 < timeout <= 120, "post-EOF wait lost the hard deadline"
                clock[0] += timeout
                raise subprocess.TimeoutExpired("synthetic child", timeout)
            self.returncode = -9 if kills else 0
            return self.returncode
    child = Child()
    class Selector:
        def __init__(self): self.members = {}
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def register(self, stream, events, name):
            self.members[stream.fileno()] = SimpleNamespace(fileobj=stream, data=name)
        def get_map(self): return self.members
        def unregister(self, stream): del self.members[stream.fileno()]
        def select(self, timeout=None):
            clock[0] = max(clock[0], spent)
            return [(value, 1) for value in list(self.members.values())]
    def launch(argv, **kwargs):
        popens.append((argv, kwargs))
        return child
    def kill(pid, how):
        kills.append((pid, how))
        if kill_race: raise ProcessLookupError()
    monkeypatch.setattr(driver.subprocess, "Popen", launch)
    monkeypatch.setattr(driver.selectors, "DefaultSelector", Selector)
    monkeypatch.setattr(driver.os, "set_blocking", lambda fd, value: None)
    monkeypatch.setattr(driver.os, "read", lambda fd, limit: streams[fd].pop(0))
    monkeypatch.setattr(driver.os, "killpg", kill)
    monkeypatch.setattr(driver.time, "monotonic", lambda: clock[0])
    return SimpleNamespace(waits=waits, kills=kills, popens=popens, closed=closed)


def test_dispatch_closes_pipes_and_reaps_with_fixed_launch_contract(driver, monkeypatch):
    case = fake_dispatch(driver, monkeypatch)
    assert driver.dispatch(["explicit", "child"]) == (0, b"ok", b"", False, False)
    assert case.popens == [(["explicit", "child"], {"stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE, "start_new_session": True})]
    assert case.waits and not case.kills and set(case.closed) == {101, 102}


@pytest.mark.parametrize("race", [False, True])
def test_early_pipe_eof_cannot_escape_process_deadline(driver, monkeypatch, race):
    case = fake_dispatch(driver, monkeypatch, early_exit_wait=True, kill_race=race, spent=37)
    code, stdout, stderr, timed_out, overflow = driver.dispatch(["explicit", "child"])
    assert (code, stdout, stderr, timed_out, overflow) == (-9, b"ok", b"", True, False)
    assert case.kills == [(43210, signal.SIGKILL)]
    assert case.waits == [83, None] and set(case.closed) == {101, 102}


def test_stream_capture_itself_keeps_the_original_wall_deadline(driver, monkeypatch):
    case = fake_dispatch(driver, monkeypatch, spent=121)
    assert driver.dispatch(["explicit", "child"]) == (-9, b"ok", b"", True, False)
    assert case.kills == [(43210, signal.SIGKILL)]


def test_pipe_overflow_is_bounded_killed_and_retained_as_failure(driver, monkeypatch):
    monkeypatch.setattr(driver, "MAX_WIRE_BYTES", 4)
    case = fake_dispatch(driver, monkeypatch, pipe_data=b"0123456789")
    assert driver.dispatch(["explicit", "child"]) == (-9, b"0123", b"", False, True)
    assert case.kills == [(43210, signal.SIGKILL)]
