"""Offline lifetime and evidence checks; never invokes a provider or real assertion."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import signal
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "notes/claudecode_direct/run_direct_canary_awake.py"
_spec = importlib.util.spec_from_file_location("direct_keep_awake_tested", SCRIPT)
awake = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(awake)


class FakeAPI:
    def __init__(self, fail_at=None, release_result=0):
        self.fail_at = fail_at
        self.release_result = release_result
        self.active = {}
        self.released = []
        self.created = []

    def create(self, kind):
        self.created.append(kind)
        if len(self.created) == self.fail_at:
            raise RuntimeError("synthetic acquisition failure")
        number = len(self.created)
        self.active[number] = kind
        return number

    def release(self, number):
        self.released.append(number)
        del self.active[number]
        return self.release_result


@pytest.mark.parametrize("failure", [1, 2, 3])
def test_partial_acquisition_never_enters_body_and_releases_every_prior_assertion(failure):
    api = FakeAPI(fail_at=failure)
    with pytest.raises(RuntimeError, match="acquisition"):
        with awake.KeepAwake(api):
            pytest.fail("launch body ran despite assertion failure")
    assert not api.active
    assert api.released == list(reversed(range(1, failure)))


@pytest.mark.parametrize("error", [None, ValueError("child failed"), KeyboardInterrupt()])
def test_assertions_cover_body_and_release_on_all_exits(error):
    api = FakeAPI()
    guard = awake.KeepAwake(api)
    try:
        with guard:
            assert tuple(api.active.values()) == awake.ASSERTIONS
            snapshot = guard.snapshot()
            snapshot["assertions"].clear()
            assert len(guard.snapshot()["assertions"]) == 3
            if error:
                raise error
    except BaseException as caught:
        assert caught is error
    assert not api.active and api.released == [3, 2, 1]
    assert guard.snapshot()["status"] == "not_held"
    assert all(row["return_code"] == 0 for row in guard.releases)


def test_unsupported_platform_loads_no_framework(monkeypatch):
    monkeypatch.setattr(awake.sys, "platform", "linux")
    monkeypatch.setattr(awake.ctypes, "CDLL", lambda *_: pytest.fail("loaded native library"))
    with pytest.raises(RuntimeError, match="requires macOS"):
        awake.KeepAwake()


def test_native_binding_checks_return_values_and_releases_cf_strings(monkeypatch):
    class Function:
        def __init__(self, action):
            self.action = action
        def __call__(self, *args):
            return self.action(*args)
    strings, freed, released = [], [], []
    def string(_allocator, raw, encoding):
        assert encoding == 0x08000100
        strings.append(raw.decode())
        return len(strings)
    result = [0]
    def create(kind, level, name, pointer):
        assert (kind, level, name) == (1, 255, 2)
        pointer._obj.value = 41
        return result[0]
    cf = SimpleNamespace(CFStringCreateWithCString=Function(string), CFRelease=Function(freed.append))
    io = SimpleNamespace(IOPMAssertionCreateWithName=Function(create),
                         IOPMAssertionRelease=Function(lambda number: released.append(number) or 0))
    monkeypatch.setattr(awake.sys, "platform", "darwin")
    monkeypatch.setattr(awake.ctypes, "CDLL", lambda path: cf if "CoreFoundation" in path else io)
    api = awake._IOKit()
    assert api.create("PreventUserIdleSystemSleep") == 41
    assert strings == ["PreventUserIdleSystemSleep", "D4D registered direct launch"]
    assert freed == [2, 1]
    assert api.release(41) == 0 and released == [41]
    strings.clear(); freed.clear(); result[0] = -1
    with pytest.raises(RuntimeError, match="IOReturn -1"):
        api.create("PreventUserIdleSystemSleep")
    assert freed == [2, 1]


@pytest.fixture
def registration(tmp_path):
    value = {"kind": "d4d_direct_arm_registration", "schema_version": 1,
             "repository": str(ROOT), "code_commit": awake.subprocess.check_output(
                 ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
             "generation": {"jobs": [{"id": "PUBLIC_direct_rep1", "instruction": "unchanged input"}]},
             "pinned_files": {"original": "untouched"}}
    source = tmp_path / "registration.json"
    source.write_text(json.dumps(value))
    output = tmp_path / "registration-awake.json"
    awake.prepare(source, output)
    return source, output, value


def test_prepare_preserves_original_fields_bytes_and_exclusive_outputs(registration):
    source, output, original = registration
    before = source.read_bytes()
    value = awake.load(output)
    assert value.pop("keep_awake_launcher")["source_registration_sha256"] == awake.sha(source)
    assert value["pinned_files"].pop(str(SCRIPT)) == awake.sha(SCRIPT)
    assert value == original
    with pytest.raises(FileExistsError):
        awake.prepare(source, output)
    assert source.read_bytes() == before
    with pytest.raises(ValueError, match="beside"):
        awake.prepare(source, output.parent / "elsewhere" / "out.json")


@pytest.mark.parametrize("change", ["policy", "source", "pin", "instruction", "consumed"])
def test_changed_registration_or_spent_attempt_refuses_before_acquisition(registration, monkeypatch, change):
    source, output, _ = registration
    value = awake.load(output)
    if change == "policy":
        value["keep_awake_launcher"]["policy"] = "none"
    elif change == "source":
        source.write_text(source.read_text() + "\n")
    elif change == "pin":
        value["pinned_files"][str(SCRIPT)] = "0" * 64
    elif change == "instruction":
        value["generation"]["jobs"][0]["instruction"] = "changed request"
    else:
        (output.parent / "attempts/PUBLIC_direct_rep1").mkdir(parents=True)
    output.write_text(json.dumps(value))
    monkeypatch.setattr(awake, "KeepAwake", lambda: pytest.fail("acquired before rejecting changed input"))
    with pytest.raises(ValueError):
        awake.launch(SimpleNamespace(registration=output, review="review", launch_word="word", job="PUBLIC_direct_rep1"))


def writer(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream)


@pytest.mark.parametrize("outcome", [0, 1, "preflight", "SIGINT", "SIGTERM", "repeated"])
def test_wrapper_lifetime_receipts_signal_status_and_restoration(registration, monkeypatch, outcome):
    source, output, _ = registration
    api = FakeAPI()
    guard = awake.KeepAwake(api)
    monkeypatch.setattr(awake, "KeepAwake", lambda: guard)
    saved_handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    saved_path = awake.sys.path[:]
    before = source.read_bytes(), output.read_bytes()
    attempt = output.parent / "attempts/PUBLIC_direct_rep1"
    module = SimpleNamespace(write_new=writer)
    observed = []
    def main(argv):
        observed.extend(argv)
        assert len(api.active) == 3
        if outcome == "preflight":
            raise ValueError("synthetic preflight refusal")
        module.write_new(attempt / "started.json", {"status": "incomplete"})
        status = "completed" if outcome == 0 else "stopped"
        try:
            if outcome in ("SIGINT", "SIGTERM", "repeated"):
                signum = signal.SIGINT if outcome == "SIGINT" else signal.SIGTERM
                signal.getsignal(signum)(signum, None)
        except awake.LaunchSignal:
            assert len(api.active) == 3  # same exception boundary as native child cleanup
            if outcome == "repeated":
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        finally:
            assert len(api.active) == 3
            module.write_new(attempt / "result.json", {"status": status})
        return outcome if isinstance(outcome, int) else 1
    module.main = main
    monkeypatch.setattr(awake, "load_legacy", lambda: module)
    args = SimpleNamespace(registration=output, review="review", launch_word="word", job="PUBLIC_direct_rep1")
    if outcome == "preflight":
        with pytest.raises(ValueError, match="preflight"):
            awake.launch(args)
        assert not attempt.exists()
    else:
        result = awake.launch(args)
        expected = (130 if outcome == "SIGINT" else 143) if isinstance(outcome, str) else outcome
        assert result == expected
        for name in ("started.json", "result.json"):
            receipt = json.loads((attempt / name).read_text())
            assert receipt["keep_awake"]["status"] == "acquired"
            assert len(receipt["keep_awake"]["assertions"]) == 3
            assert "not proof" in receipt["keep_awake"]["limitations"]
        cleanup = json.loads((attempt / "keep_awake_cleanup.json").read_text())
        assert cleanup["status"] == "released" and len(cleanup["releases"]) == 3
        assert cleanup["registration_sha256"] == awake.sha(output)
    assert not api.active and api.released == [3, 2, 1]
    assert module.write_new is writer
    assert awake.sys.path == saved_path
    assert {sig: signal.getsignal(sig) for sig in saved_handlers} == saved_handlers
    assert (source.read_bytes(), output.read_bytes()) == before
    assert observed == ["--registration", str(output), "--review", "review", "--launch-word", "word",
                        "--job", "PUBLIC_direct_rep1"]


def test_release_failure_is_recorded_and_fails_the_wrapper(registration, monkeypatch):
    _, output, _ = registration
    api = FakeAPI(release_result=-1)
    guard = awake.KeepAwake(api)
    monkeypatch.setattr(awake, "KeepAwake", lambda: guard)
    module = SimpleNamespace(write_new=writer)
    attempt = output.parent / "attempts/PUBLIC_direct_rep1"
    def main(_argv):
        module.write_new(attempt / "started.json", {})
        module.write_new(attempt / "result.json", {"status": "completed"})
        return 0
    module.main = main
    monkeypatch.setattr(awake, "load_legacy", lambda: module)
    with pytest.raises(RuntimeError, match="release failed"):
        awake.launch(SimpleNamespace(registration=output, review="review", launch_word="word", job="PUBLIC_direct_rep1"))
    cleanup = json.loads((attempt / "keep_awake_cleanup.json").read_text())
    assert cleanup["status"] == "release_failed"
    assert [row["return_code"] for row in cleanup["releases"]] == [-1, -1, -1]


@pytest.fixture
def real_direct(tmp_path, monkeypatch):
    """Reuse the established offline direct fixture without collection-time imports."""
    saved_path = awake.sys.path[:]
    spec = importlib.util.spec_from_file_location("awake_direct_fixture", ROOT / "notes/claudecode_direct/test_direct_arm.py")
    fixture = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(fixture)
        prepared = fixture.prepared.__wrapped__(tmp_path, monkeypatch)
        context = fixture.offline_launch.__wrapped__(prepared, tmp_path, monkeypatch)
        launch = next(context)
        try:
            yield fixture, launch
        finally:
            with pytest.raises(StopIteration):
                next(context)
    finally:
        awake.sys.path[:] = saved_path


@pytest.mark.parametrize("outcome", ["success", "nonzero", "signal", "old_review"])
def test_real_legacy_launcher_keeps_guards_and_receipts(real_direct, monkeypatch, outcome):
    fixture, legacy_launch = real_direct
    output = legacy_launch.path.with_name("registration-awake.json")
    awake.prepare(legacy_launch.path, output)
    review, word = fixture.bind(legacy_launch.tmp_path, output, "awake-review.json", "awake-word.json")
    api = FakeAPI()
    guard = awake.KeepAwake(api)
    monkeypatch.setattr(awake, "KeepAwake", lambda: guard)
    monkeypatch.setattr(awake, "load_legacy", lambda: fixture.launcher)
    before = legacy_launch.path.read_bytes(), Path(legacy_launch.registration["generation"]["jobs"][0]["instruction"]).read_bytes()
    child = fixture.fake_child(write_outputs=legacy_launch.write_outputs, exit_code=int(outcome == "nonzero"))
    def execute(*args, **kwargs):
        assert len(api.active) == 3
        result = child(*args, **kwargs)
        if outcome == "signal":
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        return result
    monkeypatch.setattr(fixture.launcher.native, "execute_child", execute)
    args = SimpleNamespace(registration=output, review=legacy_launch.review if outcome == "old_review" else review,
                           launch_word=word, job=fixture.JOB)
    if outcome == "old_review":
        with pytest.raises(fixture.BudgetStop, match="independent approval"):
            awake.launch(args)
        assert not (output.parent / "attempts").exists()
    else:
        assert awake.launch(args) == {"success": 0, "nonzero": 1, "signal": 143}[outcome]
        receipt = fixture.receipt_of(legacy_launch)
        assert receipt["keep_awake"]["status"] == "acquired"
        assert receipt["registration_sha256"] == awake.sha(output)
        assert receipt["status"] == ("completed_pending_independent_review" if outcome == "success" else "stopped")
        cleanup = json.loads((output.parent / "attempts" / fixture.JOB / "keep_awake_cleanup.json").read_text())
        assert cleanup["status"] == "released"
    assert not api.active
    assert before == (legacy_launch.path.read_bytes(), Path(legacy_launch.registration["generation"]["jobs"][0]["instruction"]).read_bytes())


def test_native_process_cleanup_finishes_before_assertions_release(real_direct, monkeypatch, tmp_path):
    fixture, _ = real_direct
    native = fixture.launcher.native
    api = FakeAPI()
    cleaned = []
    class Child:
        returncode = 0
        def poll(self):
            assert len(api.active) == 3
            raise awake.LaunchSignal("synthetic interrupt during child wait")
    process = Child()
    def terminate(child):
        assert child is process and len(api.active) == 3
        cleaned.append(True)
    instruction = tmp_path / "neutral-instruction.txt"
    instruction.write_text("synthetic offline instruction")
    attempt = tmp_path / "neutral-attempt"
    attempt.mkdir()
    monkeypatch.setattr(native.subprocess, "Popen", lambda *a, **kw: process)
    monkeypatch.setattr(native, "terminate_group", terminate)
    with pytest.raises(awake.LaunchSignal):
        with awake.KeepAwake(api):
            native.execute_child(["synthetic-child"], proxy=fixture.launcher.NoProxy(),
                                 instruction=instruction, attempt=attempt, cwd=tmp_path, env={},
                                 deadline_seconds=10, verify_launch=lambda: None)
    assert cleaned == [True] and not api.active
