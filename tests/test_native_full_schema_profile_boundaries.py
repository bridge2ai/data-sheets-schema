"""Independent local protocol and input-boundary controls for #4618.

These tests do not load recovered code or build a native checkpoint. Synthetic
frames exercise the driver's actual persistence order; import controls use small
invented modules. The actual full-schema checkpoint is a separate bounded run.
"""
from copy import deepcopy
from dataclasses import make_dataclass
import importlib.machinery
import json
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest


DRIVER = Path(__file__).resolve().parents[1] / "notes/native_full_schema_profile_2026-10-07/profile_checkpoint.py"


@pytest.fixture
def profile():
    module = ModuleType("_full_schema_boundary_tests")
    module.__file__ = str(DRIVER)
    exec(compile(DRIVER.read_bytes(), str(DRIVER), "exec"), module.__dict__)
    return module


@pytest.fixture
def frames(profile, tmp_path):
    instance = profile.SyntheticFrames.__new__(profile.SyntheticFrames)
    instance.c = SimpleNamespace(canonical=profile.canonical)
    instance.path = str(tmp_path / "selection.json")
    instance.number, instance.session = 0, "invented-session"
    instance.native, instance.parent, instance.withheld_grants = [], [], {}
    instance.value = {"attempt_directory": str(tmp_path), "working_directory": str(tmp_path)}
    instance.composition = {"policy": {"pretool_control": {"callback_id": "invented-callback"},
                                      "native_shared_helpers": {"advance": "never launched"}}}
    response_path = tmp_path / "response.json"
    request = SimpleNamespace(pin=SimpleNamespace(path=str(tmp_path / "request.json")), raw=b'{"invented":true}\n')
    instance.paths = {"full": str(tmp_path / "full.yaml")}
    decision = SimpleNamespace(state="awaiting_response", cursor=SimpleNamespace(kind="worker"),
                               request=request, response=SimpleNamespace(path=str(response_path)))
    events = []

    def observe(name, identity):
        # Inspect persisted bytes at each boundary, including their intermediate
        # states. A later removed early grant must not escape the regression.
        transcript = [json.loads(row) for row in (tmp_path / "transcript.jsonl").read_bytes().splitlines()]
        control = [json.loads(row) for row in (tmp_path / "control.jsonl").read_bytes().splitlines()]
        events.append((name, identity, transcript, control, response_path.exists()))

    def streams():
        profile.SyntheticFrames.streams(instance)
        observe("streams", None)

    instance.streams = streams
    instance.capture = SimpleNamespace(
        _load_live=lambda path: SimpleNamespace(decision=lambda: decision),
        observe_request_read=lambda run, identity: observe("read", identity),
        observe_response_intent=lambda run, identity: observe("intent", identity),
        observe_response_written=lambda run, identity: observe("written", identity))
    return instance, decision, response_path, events


def tool_ids(transcript, tool):
    return [block["id"] for row in transcript for block in row.get("message", {}).get("content", [])
            if block.get("type") == "tool_use" and block.get("name") == tool]


def granted(control, identity):
    return any(row["request"]["request"]["input"]["tool_use_id"] == identity for row in control)


def test_response_intent_is_persisted_before_any_grant_and_file_creation(profile, frames, monkeypatch):
    instance, decision, response_path, events = frames
    original_save = profile.save_new

    def save(path, raw):
        assert path == response_path and not path.exists()
        transcript = [json.loads(row) for row in (path.parent / "transcript.jsonl").read_bytes().splitlines()]
        control = [json.loads(row) for row in (path.parent / "control.jsonl").read_bytes().splitlines()]
        write_id = tool_ids(transcript, "Write")[-1]
        assert any(event[0] == "intent" and event[1] == write_id for event in events)
        assert granted(control, write_id), "response bytes preceded the persisted grant"
        events.append(("save", write_id, transcript, control, path.exists()))
        original_save(path, raw)

    monkeypatch.setattr(profile, "save_new", save)
    answers = []
    instance.respond(lambda raw: answers.append(raw) or b'{"findings":[]}', "worker")
    assert answers == [decision.request.raw]
    assert response_path.read_bytes() == b'{"findings":[]}'
    intents = [event for event in events if event[0] == "intent"]
    assert len(intents) == 1
    intent = intents[0]
    write_id = intent[1]
    intent_index = events.index(intent)
    assert not intent[4] and not granted(intent[3], write_id)
    assert all(not granted(event[3], write_id) for event in events[:intent_index + 1])
    save_index = next(i for i, event in enumerate(events) if event[0] == "save")
    assert events[intent_index + 1][0] == "streams" and granted(events[intent_index + 1][3], write_id)
    assert intent_index + 1 < save_index
    assert events[-1][0] == "written" and events[-1][4] and granted(events[-1][3], write_id)
    assert instance.withheld_grants == {}


def test_phase1_full_write_has_grant_before_bytes(profile, frames, monkeypatch):
    instance, _, _, events = frames
    original = profile.save_new

    def save(path, raw):
        latest = events[-1]
        identity = tool_ids(latest[2], "Write")[-1]
        assert granted(latest[3], identity)
        assert not path.exists()
        original(path, raw)

    monkeypatch.setattr(profile, "save_new", save)
    instance.write("full", b"name: invented\n")
    assert Path(instance.paths["full"]).read_bytes() == b"name: invented\n"


def test_wrong_cursor_stops_before_frames_or_answer(profile, frames):
    instance, decision, response_path, events = frames
    decision.cursor.kind = "receipt"
    with pytest.raises(profile.BoundaryError, match="exact selected cursor"):
        instance.respond(lambda *_: pytest.fail("stale cursor was answered"), "worker")
    assert events == [] and instance.native == [] and instance.parent == [] and not response_path.exists()


def test_ungranted_begin_and_wrong_grant_do_not_create_transient_permission(profile, frames):
    instance, _, response_path, events = frames
    identity, _ = instance.begin("Write", {"file_path": str(response_path), "content": "invented"}, grant=False)
    assert all(not granted(event[3], identity) for event in events)
    with pytest.raises(profile.BoundaryError, match="sole pending callback"):
        instance.grant("foreign-callback")
    assert instance.parent == [] and set(instance.withheld_grants) == {identity}
    instance.grant(identity)
    assert granted(events[-1][3], identity)
    with pytest.raises(profile.BoundaryError, match="sole pending callback"):
        instance.grant(identity)


@pytest.fixture
def preparation(profile):
    identities = {"driver_sha256": "d" * 64, "python_identity": {"sha256": "a" * 64},
                  "git_identity": {"sha256": "b" * 64}, "recovered_provenance": {"source_commit": profile.SOURCE_COMMIT}}
    child = {"format": profile.CHILD_FORMAT, "mode": "prepare", "selection_relative": "authority/profile-selection.json",
        "declared_deadline_seconds": 900, "preparation_stages": [], "synthetic_parameters": {"invented": True},
        "checkpoint": {"label": profile.LABEL, "complete": False, "workers_declared": 3,
                       "workers_consumed": 1, "receipt_consumed": True},
        "case_inventory": {"entries": {}, "files": 0, "bytes": 0},
        "loaded_closure": [{"origin": "recovered/fake.py", "sha256": "f" * 64, "bytes": 1}],
        "git": {"identity": identities["git_identity"], "calls": {}},
        "python_identity": identities["python_identity"], "recovered_provenance": identities["recovered_provenance"],
        "flags": {"isolated": 1, "no_site": 1, "dont_write_bytecode": True},
        "environment": {"python": "invented", "platform": "invented", "machine": "invented"}}
    report = {"format": profile.FORMAT, "mode": "prepare", "status": "completed",
        "scientific_eligibility": False, "execution_authorized": False, "native_acceptance_evaluated": False,
        "utility_sha256": profile.UTILITY_SHA256, "driver_sha256": identities["driver_sha256"],
        "python_identity": identities["python_identity"], "result": child}
    return report, identities


@pytest.mark.parametrize("path", ["/outside/selection.json", "../authority/profile-selection.json",
    "authority/../authority/profile-selection.json", "authority/alternate.json", "authority\\profile-selection.json"])
def test_checkpoint_only_accepts_exact_retained_selection_role(profile, preparation, path):
    report, identities = preparation
    assert profile.checkpoint_declaration(report, **identities) == report["result"]
    changed = deepcopy(report)
    changed["result"]["selection_relative"] = path
    with pytest.raises(profile.BoundaryError, match="role or deadline"):
        profile.checkpoint_declaration(changed, **identities)


@pytest.mark.parametrize("field,value", [("workers_declared", 1), ("workers_consumed", 0),
    ("workers_consumed", True), ("workers_declared", 3.0), ("receipt_consumed", False),
    ("complete", True), ("complete", 0), ("label", "historical-native-run")])
def test_checkpoint_cannot_claim_tiny_or_completed_work(profile, preparation, field, value):
    report, identities = preparation
    report["result"]["checkpoint"][field] = value
    with pytest.raises(profile.BoundaryError, match="incomplete prefix"):
        profile.checkpoint_declaration(report, **identities)


def test_projection_uses_dataclass_order_and_retains_reader_state(profile):
    names = ["selection", "value", "composition", "spec", "reader", "pool", "transcript", "control",
             "binding", "history", "observations", "phase1", "_catalogs"]
    # Different declaration orders make a set-iteration implementation fail
    # deterministically, without depending on the test process's hash seed.
    for ordered in (names, list(reversed(names)), names[4:] + names[:4]):
        cls = make_dataclass("SyntheticCapturedRun", [(name, object) for name in ordered])
        values = {name: {"invented": name} for name in names}
        values["spec"] = SimpleNamespace(render_spec=lambda: {"bound": "rendered"})
        values["reader"] = SimpleNamespace(selection={"pin": "selected"}, pool=None,
                                           members={"one": b"captured"}, total=8)
        run = cls(**values)
        projected = profile.run_projection(run)
        assert list(projected) == [name for name in ordered if name not in {"spec", "reader", "_catalogs"}] + ["render_spec", "reader"]
        assert projected["reader"] == vars(run.reader)
        assert projected["pool"] == values["pool"] and projected["history"] == values["history"]
        run.reader.unregistered = "state"
        with pytest.raises(profile.BoundaryError, match="reader shape changed"):
            profile.run_projection(run)


@pytest.fixture
def imports(profile, tmp_path):
    source, dependencies = tmp_path / "source", tmp_path / "dependencies"
    source.mkdir(); dependencies.mkdir()
    tools = profile.utility()
    path = source / "example.py"
    raw = b"VALUE = 'verified source'\n"
    path.write_bytes(raw)
    pins = {"example.py": {"sha256": profile.sha(raw), "mode": "100644"}}
    return profile.SourceImports(source, dependencies, pins, tools), path


def test_source_loader_uses_verified_py_and_refuses_symlink_or_changed_bytes(profile, imports, tmp_path):
    owner, path = imports
    path.with_suffix(".pyc").write_bytes(b"hostile bytecode must not be read")
    namespace = {}
    code = owner.source_code(path)
    owner.audit("exec", (code,))
    exec(code, namespace)
    assert namespace["VALUE"] == "verified source"
    forged = compile("VALUE = 'forged'", str(path), "exec")
    with pytest.raises(profile.BoundaryError, match="verified source compilation"):
        owner.audit("exec", (forged,))
    alias = owner.source / "alias.py"
    alias.symlink_to(path)
    with pytest.raises(profile.BoundaryError, match="symlink"):
        owner.source_code(alias)
    path.write_bytes(b"VALUE = 'changed'\n")
    with pytest.raises(profile.BoundaryError, match="source changed"):
        owner.source_code(path)


def test_sourceless_dependency_import_is_refused_before_execution(profile, imports, monkeypatch):
    owner, _ = imports
    # Register restoration before install's direct assignments. No permanent
    # audit hook is installed in the pytest process.
    with monkeypatch.context() as local:
        for cls, method in ((importlib.machinery.SourceFileLoader, "get_code"),
                            (importlib.machinery.ExtensionFileLoader, "create_module"),
                            (importlib.machinery.SourcelessFileLoader, "get_code")):
            local.setattr(cls, method, getattr(cls, method))
        local.setattr(sys, "addaudithook", lambda *_: None)
        local.setattr(sys, "path", list(sys.path))
        owner.install()
        bytecode = owner.dependencies / "foreign.pyc"
        bytecode.write_bytes(b"must refuse without loading bytecode")
        loader = importlib.machinery.SourcelessFileLoader("foreign", str(bytecode))
        with pytest.raises(profile.BoundaryError, match="sourceless recovered/dependency"):
            loader.get_code("foreign")


def test_declared_import_closure_binds_exact_bytes_and_rejects_escape(profile, imports):
    owner, path = imports
    raw = path.read_bytes()
    row = {"origin": "recovered/example.py", "sha256": profile.sha(raw), "bytes": len(raw)}
    profile.verify_declared_closure([row], owner)
    for origin in ("recovered/../example.py", "recovered//outside.py", "foreign/example.py"):
        with pytest.raises(profile.BoundaryError, match="escapes"):
            profile.verify_declared_closure([{**row, "origin": origin}], owner)
    with pytest.raises(profile.BoundaryError, match="repeats"):
        profile.verify_declared_closure([row, row], owner)
    path.write_bytes(b"changed declared dependency")
    with pytest.raises(ValueError):
        profile.verify_declared_closure([row], owner)


@pytest.mark.parametrize("event,args", [("os.exec", ("/bin/echo", ["echo"], {})),
    ("os.system", (b"echo ignored",)), ("os.posix_spawn", ("/bin/echo", [], {})),
    ("socket.connect", (None, ("example.invalid", 443))),
    ("os.symlink", ("target", "link", -1)), ("os.link", ("source", "target", -1, -1))])
def test_measurement_refuses_process_network_and_link_events(profile, tmp_path, event, args):
    policy = profile.PhasePolicy(source=tmp_path, write_root=None, git=tmp_path / "not-executed-git",
        tools=SimpleNamespace(executable_identity=lambda _: {"invented": True}))
    with pytest.raises(profile.BoundaryError):
        policy.audit(event, args)


def test_measurement_write_denial_and_exact_readonly_git_allowlist(profile, tmp_path):
    git = tmp_path / "not-executed-git"
    policy = profile.PhasePolicy(source=tmp_path, write_root=None, git=git,
        tools=SimpleNamespace(executable_identity=lambda _: {"invented": True}))
    with pytest.raises(profile.BoundaryError, match="measurement forbids writes"):
        policy.audit("open", (str(tmp_path / "output"), "w", os.O_WRONLY | os.O_CREAT))
    assert profile.validate_git_call(["git", "rev-parse", "HEAD"], cwd=tmp_path, source=tmp_path,
                                     executable=git) == [str(git), "rev-parse", "HEAD"]
    for argv in (["git", "status"], ["git", "checkout", "main"], ["sh", "-c", "git rev-parse HEAD"]):
        with pytest.raises(profile.BoundaryError):
            profile.validate_git_call(argv, cwd=tmp_path, source=tmp_path, executable=git)
    query = (profile.SOURCE_COMMIT + ":src/example.py\n").encode()
    profile.validate_git_call(["git", "cat-file", "--batch"], cwd=tmp_path, source=tmp_path,
                              executable=git, input_bytes=query)
    with pytest.raises(profile.BoundaryError, match="another revision"):
        profile.validate_git_call(["git", "cat-file", "--batch"], cwd=tmp_path, source=tmp_path,
                                  executable=git, input_bytes=b"HEAD:src/example.py\n")


def test_tree_inventory_includes_hidden_ignored_files_and_refuses_links(profile, tmp_path):
    root = tmp_path / "checkpoint"
    root.mkdir()
    (root / ".gitignore").write_bytes(b"ignored.bin\n")
    (root / "ignored.bin").write_bytes(b"retained bytes")
    (root / ".hidden").write_bytes(b"hidden evidence")
    inventory = profile.tree_manifest(root)
    assert set(inventory["entries"]) == {".gitignore", "ignored.bin", ".hidden"}
    (root / "alias").symlink_to(root / "ignored.bin")
    with pytest.raises(profile.BoundaryError, match="symlink"):
        profile.tree_manifest(root)
