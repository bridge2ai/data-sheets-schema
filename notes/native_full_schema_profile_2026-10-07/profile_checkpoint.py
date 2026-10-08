#!/usr/bin/env python3
"""Fresh synthetic 0125 full-schema checkpoint; never a native execution route.

Preparation and measurement are distinct bounded isolated children. Production
source stays unchanged. The retained-prefix utility is a pinned, repo-relative
dependency, loaded from source rather than an import cache.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import fields, replace
import hashlib
import importlib
import importlib.machinery
import importlib.util
import io
import json
import marshal
import os
from pathlib import Path
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import time
from types import ModuleType


UTILITY_RELATIVE = "notes/native_profile_recovery_2026-10-07/trace_prefix_profile.py"
UTILITY_SHA256 = "4097c8dff6e921b146feb49854b67487adc54b5a4da7943e22c9293849df01bf"
SOURCE_COMMIT = "0125eebbc214d0907c3b69d23758cd9441911a78"
FORMAT = "native_full_schema_checkpoint_v1"
CHILD_FORMAT = "native_full_schema_checkpoint_child_v1"
LABEL = "offline-full-schema-4618-v1"
ATTEMPT_ID = "synthetic-full-schema-4618-v1"
PREPARE_WALL_SECONDS = 900
MEASURE_WALL_SECONDS = 600
MAX_REPORT_BYTES = 4 * 1024 * 1024
MAX_TREE_FILES = 10000
MAX_TREE_BYTES = 256 * 1024 * 1024
SCOPE = "New synthetic full-schema checkpoint on recovered 0125; not historical replay or native acceptance"
LIMITATIONS = [
    "All source data, native frames, permissions and supported/unsupported answers are fictional software declarations.",
    "Helpers and native/provider executables never run; helper success frames are synthetic, while capture, seals, core derivation and typed stage checks are real.",
    "Only the receipt and first of three workers are consumed; the next advance is admitted, not published. This is not completed execution.",
    "Plain then instrumented calls share process caches; ordered timings are not a speed comparison or whole-path fraction.",
    "The unavailable 4366 source and historical 900-second acceptance are not reproduced. #4354, #4400 and #4576 remain open.",
    "#4537 and #4576 already cover known parsing work; deferred #4577/#4581 optimizations are not revived here.",
    "Before/after pins and local audit restrictions are checked local evidence, not authenticated execution or complete ABA protection.",
    "loaded_closure pins imported Python/extension bytes, not the complete installed environment or every dependency-resource/OS read; selected schema/policy/runtime/case inputs have separate complete pins.",
]


class BoundaryError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise BoundaryError(reason)


def require_isolation():
    require(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.dont_write_bytecode,
            "diagnostic requires -I -B -S isolation")


def environment_disclosure():
    """Report interpreter/OS identifiers without command-based feature probes."""
    return {"python": sys.version, "platform": sys.platform, "machine": os.uname().machine}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(",", ":")).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utility():
    path = Path(__file__).resolve().parents[2] / UTILITY_RELATIVE
    raw = path.read_bytes()
    require(sha(raw) == UTILITY_SHA256, "reviewed diagnostic utility differs or is unavailable")
    module = ModuleType("_full_schema_trace_utility")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


def tree_manifest(root, *, read=None):
    """Include hidden/ignored files; refuse links, special files and overbounds."""
    root = Path(root)
    require(root.resolve(strict=True) == root.absolute(), "tree root contains a symlink")
    entries, total = {}, 0
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        require(not stat.S_ISLNK(info.st_mode), "tree contains a symlink")
        if stat.S_ISDIR(info.st_mode):
            continue
        require(stat.S_ISREG(info.st_mode), "tree contains a non-regular member")
        raw = read(path) if read else path.read_bytes()
        total += len(raw)
        require(len(entries) < MAX_TREE_FILES and total <= MAX_TREE_BYTES,
                "checkpoint exceeds complete inventory bound")
        entries[path.relative_to(root).as_posix()] = {
            "sha256": sha(raw), "bytes": len(raw), "mode": stat.S_IMODE(info.st_mode)}
    return {"entries": entries, "files": len(entries), "bytes": total}


def validate_git_call(argv, *, cwd, source, executable, input_bytes=None):
    """Only fixed local identity queries; no revision/path/options from a caller."""
    require(type(argv) in (list, tuple) and all(type(x) is str for x in argv),
            "process argv is not an explicit string vector")
    require(argv and argv[0] in ("git", str(executable)), "non-Git process forbidden")
    require(cwd is not None and Path(cwd).resolve() == Path(source).resolve(),
            "Git query has another working directory")
    tail = list(argv[1:])
    require(tail in (["rev-parse", "HEAD"], ["cat-file", "--batch"]),
            "Git query is outside the fixed identity allowlist")
    if tail == ["rev-parse", "HEAD"]:
        require(input_bytes is None, "HEAD query cannot accept stdin")
    elif input_bytes is not None:
        require(type(input_bytes) is bytes and input_bytes.endswith(b"\n"),
                "source-object query lacks complete byte input")
        for line in input_bytes.splitlines():
            prefix = (SOURCE_COMMIT + ":").encode()
            require(line.startswith(prefix), "source-object query names another revision")
            name = line[len(prefix):].decode("utf-8")
            p = Path(name)
            require(name and not p.is_absolute() and ".." not in p.parts
                    and "\\" not in name and "\x00" not in name,
                    "source-object query escapes selected source")
    return [str(executable), *tail]


class SourceImports:
    """Compile exact source; bypass repository and dependency Python bytecode.

    SourceFileLoader also covers direct spec_from_file_location consumers. The
    exec audit closes alternate sourceless loader paths for recovered modules.
    Extension imports must originate in the explicitly selected dependency or
    interpreter directories and their bytes are pinned before module execution.
    """
    def __init__(self, source, dependencies, pins, tools):
        self.source, self.dependencies, self.pins, self.tools = source, dependencies, pins, tools
        self.loaded, self.approved_code = {}, set()
        self.stdlib = Path(os.__file__).resolve().parent
        self.original_code = importlib.machinery.SourceFileLoader.get_code
        self.original_extension = importlib.machinery.ExtensionFileLoader.create_module
        self.original_sourceless = importlib.machinery.SourcelessFileLoader.get_code

    def allowed_dependency(self, path):
        return (path.is_relative_to(self.dependencies) or
                path.is_relative_to(self.stdlib) and
                not {"site-packages", "dist-packages"}.intersection(path.relative_to(self.stdlib).parts))

    def source_code(self, path):
        original = Path(path).absolute()
        path = original.resolve(strict=True)
        require(path == original, "import path contains a symlink")
        raw = self.tools.read_file(path)
        if path.is_relative_to(self.source):
            key = path.relative_to(self.source).as_posix()
            require(key in self.pins and self.pins[key].get("mode") != "160000",
                    "unregistered recovered import")
            require(sha(raw) == self.pins[key]["sha256"], "recovered import source changed")
        else:
            require(self.allowed_dependency(path),
                    "import outside explicit dependency/interpreter roots")
        self.loaded[str(path)] = {"sha256": sha(raw), "bytes": len(raw)}
        code = compile(raw, str(path), "exec", dont_inherit=True)
        self.approved_code.add(sha(marshal.dumps(code)))
        return code

    def helper_definitions(self, relative, names, namespace):
        """Execute unchanged selected fixture helpers, never test decorators."""
        path = self.source / relative
        raw = self.tools.read_file(path, self.pins[relative]["sha256"])
        parsed = ast.parse(raw, filename=str(path))
        body = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in names]
        require({node.name for node in body} == set(names), "fixture helper selection differs")
        code = compile(ast.Module(body=body, type_ignores=[]), str(path), "exec", dont_inherit=True)
        self.approved_code.add(sha(marshal.dumps(code)))
        self.loaded[str(path)] = {"sha256": sha(raw), "bytes": len(raw)}
        exec(code, namespace)
        return namespace

    def audit(self, event, args):
        if event == "exec":
            code = args[0]
            filename = code.co_filename
            if not filename.startswith("<") and Path(filename).is_absolute():
                path = Path(filename).resolve()
                if path.is_relative_to(self.source):
                    require(sha(marshal.dumps(code)) in self.approved_code,
                            "recovered code did not come from verified source compilation")

    def install(self):
        owner = self
        def get_code(loader, fullname):
            return owner.source_code(loader.get_filename(fullname))
        def extension(loader, spec):
            path = Path(spec.origin).resolve(strict=True)
            require(path == Path(spec.origin).absolute(), "extension path contains a symlink")
            require(owner.allowed_dependency(path),
                    "extension outside explicit dependency/interpreter roots")
            raw = owner.tools.read_file(path)
            owner.loaded[str(path)] = {"sha256": sha(raw), "bytes": len(raw)}
            return owner.original_extension(loader, spec)
        def sourceless(loader, fullname):
            original = Path(loader.get_filename(fullname)).absolute()
            path = original.resolve(strict=True)
            require(path == original, "sourceless import path contains a symlink")
            require(not path.is_relative_to(owner.source) and not path.is_relative_to(owner.dependencies),
                    "sourceless recovered/dependency imports are unsupported")
            require(owner.allowed_dependency(path), "sourceless import outside interpreter roots")
            raw = owner.tools.read_file(path)
            owner.loaded[str(path)] = {"sha256": sha(raw), "bytes": len(raw)}
            return owner.original_sourceless(loader, fullname)
        importlib.machinery.SourceFileLoader.get_code = get_code
        importlib.machinery.ExtensionFileLoader.create_module = extension
        importlib.machinery.SourcelessFileLoader.get_code = sourceless
        sys.addaudithook(self.audit)
        sys.path[:0] = [str(self.source / "src"), str(self.source), str(self.dependencies)]

    def verify(self):
        for path, pin in self.loaded.items():
            require(len(self.tools.read_file(Path(path), pin["sha256"])) == pin["bytes"],
                    "loaded dependency changed")
        return [{"origin": ("recovered/" + Path(p).relative_to(self.source).as_posix())
                 if Path(p).is_relative_to(self.source) else
                 ("dependency/" + Path(p).relative_to(self.dependencies).as_posix())
                 if Path(p).is_relative_to(self.dependencies) else
                 "interpreter/" + Path(p).relative_to(self.stdlib).as_posix(), **pin}
                for p, pin in sorted(self.loaded.items())]


class PhasePolicy:
    """Local effect restriction, scoped independently from runtime acceptance."""
    def __init__(self, *, source, write_root, git, tools):
        self.source, self.write_root, self.git, self.tools = source, write_root, git, tools
        self.git_pin = tools.executable_identity(git)
        self.process_calls = Counter()
        self.write_descriptors = {}
        self.git_active = False

    def writable(self, path):
        if isinstance(path, int) and self.git_active and stat.S_ISFIFO(os.fstat(path).st_mode):
            return  # The approved Git query's anonymous stdin pipe, not a file.
        require(self.write_root is not None, "measurement forbids writes")
        if isinstance(path, int):
            info = os.fstat(path)
            require(self.write_descriptors.get(path) == (info.st_dev, info.st_ino, info.st_mode),
                    "write descriptor was not opened in the fresh checkpoint")
            return
        p = Path(os.fsdecode(path)).absolute()
        require(p.resolve() == p and p.is_relative_to(self.write_root),
                "preparation write is outside fresh checkpoint")

    def publication_link(self, source, destination, source_dir_fd, destination_dir_fd):
        require(all(fd is None or type(fd) is int and fd == -1
                    for fd in (source_dir_fd, destination_dir_fd)),
                "publication hard-link dir_fd overrides are forbidden")
        require(not isinstance(source, int) and not isinstance(destination, int),
                "publication hard-link requires absolute paths")
        source, destination = Path(os.fsdecode(source)), Path(os.fsdecode(destination))
        require(source.is_absolute() and destination.is_absolute(),
                "publication hard-link requires absolute paths")
        self.writable(source); self.writable(destination)
        prefix = "." + destination.name + ".pending-"
        require(source.parent == destination.parent and source.name.startswith(prefix)
                and len(source.name) > len(prefix), "hard-link is not a local pending publication")
        require(source.is_file() and not source.is_symlink(), "publication source is not a regular physical file")
        info = source.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                "publication source must have one existing link")
        require(not destination.exists() and not destination.is_symlink(),
                "publication hard-link destination already exists")

    def audit(self, event, args):
        if event.startswith("socket.") or event in {"os.system", "os.exec", "os.posix_spawn", "os.posix_spawnp",
                "os.fork", "os.forkpty", "pty.spawn"}:
            raise BoundaryError("network or unregistered process forbidden")
        if event == "subprocess.Popen":
            executable, argv, cwd, env = args
            require(self.git_active, "Git must use the checked query wrapper")
            require(executable == str(self.git), "process did not use pinned Git executable")
            validate_git_call(argv, cwd=cwd, source=self.source, executable=self.git)
            require(env is not None and env.get("GIT_CONFIG_NOSYSTEM") == "1"
                    and env.get("GIT_CONFIG_GLOBAL") == os.devnull, "Git environment is not isolated")
            self.process_calls[" ".join(argv[1:])] += 1
        if event == "open":
            path, mode, flags = args
            if ((isinstance(mode, str) and any(c in mode for c in "wax+"))
                    or isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
                self.writable(path)
        if event in {"os.mkdir", "os.rmdir", "os.remove", "os.chmod", "os.utime", "os.truncate"}:
            self.writable(args[0])
        if event == "os.rename":
            # The actual publisher replaces only its exact journal after CAS.
            require(len(args) == 4 and all(fd is None or type(fd) is int and fd == -1 for fd in args[2:]),
                    "journal replacement dir_fd overrides are forbidden")
            self.writable(args[0]); self.writable(args[1])
        if event == "os.link":
            require(len(args) == 4, "publication hard-link audit shape differs")
            self.publication_link(*args)
        if event == "os.symlink":
            raise BoundaryError("unregistered filesystem mutation forbidden")

    def install(self):
        original_run = subprocess.run
        original_open = os.open
        owner = self
        def opened(path, flags, mode=0o777, *, dir_fd=None):
            writing = flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            if writing:
                require(dir_fd is None, "relative descriptor writes are unsupported")
                owner.writable(path)
            fd = original_open(path, flags, mode, dir_fd=dir_fd)
            if writing:
                info = os.fstat(fd)
                owner.write_descriptors[fd] = (info.st_dev, info.st_ino, info.st_mode)
            return fd
        def run(argv, *args, **kwargs):
            require(not args and not kwargs.get("shell", False), "process shell/positional options forbidden")
            argv = validate_git_call(argv, cwd=kwargs.get("cwd"), source=owner.source,
                                     executable=owner.git, input_bytes=kwargs.get("input"))
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith("GIT_")}
            environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                               GIT_CONFIG_SYSTEM=os.devnull, GIT_OPTIONAL_LOCKS="0")
            kwargs["env"] = environment
            require(not owner.git_active, "nested Git execution forbidden")
            owner.git_active = True
            try:
                return original_run(argv, **kwargs)
            finally:
                owner.git_active = False
        subprocess.run = run
        os.open = opened
        sys.addaudithook(self.audit)

    def verify(self):
        require(self.tools.executable_identity(self.git) == self.git_pin, "Git executable changed")
        return {"identity": self.git_pin, "calls": dict(self.process_calls)}


def save_new(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def fresh_authority(case, tools, imports):
    from tests.native_shared_fixture import build_native_fixture, _Answers
    from data_sheets_schema import native_shared_contract as c
    from data_sheets_schema import native_shared_controller as controller
    from data_sheets_schema import native_shared_selection as selection
    data = build_native_fixture(case, registered_python=str(Path(sys.executable).resolve()))
    document = data["selection"].document()
    document.update(registration_id=ATTEMPT_ID,
                    registration_path=str(case / "authority/profile-selection.json"),
                    stage_root=str(case / "checkpoint/stages"))
    document["run"]["label"] = LABEL
    save_new(Path(document["registration_path"]), c.canonical(document))
    runtime = c.strict_json(data["runtime_path"].read_bytes())
    runtime["deadline_seconds"] = 900
    runtime_path = case / "authority/profile-runtime.json"
    save_new(runtime_path, c.canonical(runtime))
    spec = replace(data["spec"], label=LABEL, run_date="2026-10-07",
                   native_shared_generation_registration=c.canonical(document).decode())
    controller.bind_runtime(spec, runtime_path, 3)
    instruction = case / "authority/profile-instruction.md"
    save_new(instruction, spec.instruction.encode())
    composition = controller.compose(spec, runtime_path=runtime_path,
                                     instruction_path=instruction, max_draft_checks=3)
    composition_path = case / "authority/profile-composition.json"
    save_new(composition_path, c.canonical(composition))
    cap = selection.capture(document["registration_path"])
    answer = _Answers(cap, data["full_raw"], {"source": "neutral.txt", "chunk": data["chunk_id"],
                                           "quote": data["source_text"].strip()})
    return data, spec, cap, runtime_path, composition, composition_path, answer


def register_synthetic(case, spec, cap, runtime_path, composition, composition_path, imports):
    from data_sheets_schema import native_shared_contract as c
    from data_sheets_schema import native_shared_registration as registration
    from data_sheets_schema import native_shared_policy as policy
    from data_sheets_schema import native_execution_authority as authority
    from data_sheets_schema import native_shared_permissions as permissions
    from data_sheets_schema import native_attribution_controller as controls
    import uuid
    namespace = {"p": permissions, "composition": controls, "Path": Path,
                 "deepcopy": deepcopy, "uuid": uuid, "shlex": shlex}
    imports.helper_definitions("tests/test_native_shared_permissions.py",
                               {"encoded", "member", "fabricated_manifest"}, namespace)
    system = case / "authority/profile-system.txt"
    save_new(system, b"Fictional offline #4618 software checkpoint; no launch authorization.\n")
    reservation_parent = case / "checkpoint"
    reservation_parent.mkdir()
    attempt, evidence = reservation_parent / ATTEMPT_ID, reservation_parent / "evidence"
    expected = registration.permission_expectation(c.strict_json(runtime_path.read_bytes()), composition, spec,
        system.read_text() + policy.command_guidance(composition["policy"]), attempt / "cli_config",
        authority.dependency_identity())
    probe = namespace["fabricated_manifest"](expected, cap.document(), case / "invented-probe", spec.bundle.read_bytes())
    probe_path = case / "authority/fabricated-permission-observations.json"
    save_new(probe_path, c.canonical(probe))
    value = registration.registration(composition_path=composition_path, system_path=system,
        permission_probe_path=probe_path, attempt_id=ATTEMPT_ID,
        attempt_directory=attempt, evidence_directory=evidence, max_draft_checks=3)
    registration._paths(value, composition, fresh=True)
    raw = c.canonical(value)
    save_new(attempt / "registration.json", raw)
    started = c.canonical({"kind": c.KINDS["attempt"], "version": 1, "state": "started",
        "attempt_id": value["attempt_id"], "registration_sha256": c.sha(raw),
        "composition_sha256": value["composition_sha256"], "dispatch_limit": 1})
    save_new(attempt / "started.json", started)
    Path(cap.role("stage_root")).mkdir(parents=True)
    from data_sheets_schema import native_shared_capture as capture
    capture.activate(cap, raw, started)
    return value


class SyntheticFrames:
    """Data-only protocol transport: exact order, no transport/helper execution."""
    def __init__(self, cap, value, composition, imports):
        from data_sheets_schema import native_shared_contract as c
        from data_sheets_schema import native_shared_capture as capture
        from data_sheets_schema.native_shared_streams import stream_files
        self.c, self.capture, self.stream_files = c, capture, stream_files
        self.cap, self.value, self.composition = cap, value, composition
        self.path, self.number = cap.registration.pin.path, 0
        self.withheld_grants = {}
        self.paths = composition["render_spec"]["agentic_artifact_paths"]
        namespace = {"c": c, "Path": Path, "json": json}
        imports.helper_definitions("tests/test_native_shared_live_capture.py", {"native_init"}, namespace)
        native, parent = namespace["native_init"](cap, value, composition)
        self.native = [c.strict_json(row) for row in native.splitlines()]
        self.parent = [c.strict_json(row) for row in parent.splitlines()]
        self.session = self.native[1]["session_id"]
        capture.initialize(self.path, transcript_bytes=len(native), control_bytes=len(parent), **self.stream_capture())

    def stream_capture(self):
        members, prefixes = self.capture._streams(self.value)
        return {"stream_files": self.stream_files(members),
                "observed_prefixes": dict(zip(("transcript", "control"), prefixes))}

    def streams(self):
        for role, rows in (("transcript", self.native), ("control", self.parent)):
            (Path(self.value["attempt_directory"]) / (role + ".jsonl")).write_bytes(
                b"".join(self.c.canonical(row) + b"\n" for row in rows))

    def begin(self, tool, inputs, *, grant=True):
        self.number += 1
        identity = "synthetic-4618-" + str(self.number)
        call = {"type": "assistant", "session_id": self.session, "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": identity, "name": tool, "input": deepcopy(inputs)}]}}
        callback = {"type": "control_request", "request_id": "callback-" + identity, "request": {
            "subtype": "hook_callback", "callback_id": self.composition["policy"]["pretool_control"]["callback_id"],
            "input": {"hook_event_name": "PreToolUse", "cwd": self.value["working_directory"],
                      "tool_use_id": identity, "tool_name": tool, "tool_input": deepcopy(inputs)}}}
        parent = {"kind": "decision", "request": deepcopy(callback), "classification": "prescribed",
            "basis": "selected current effect", "response": {"type": "control_response", "response": {
                "subtype": "success", "request_id": callback["request_id"], "response": {}}}}
        result = {"type": "user", "session_id": self.session, "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": identity, "is_error": False, "content": "checked"}]},
            "tool_use_result": {"stdout": "checked", "stderr": "", "exitCode": 0} if tool == "Bash" else
            {"type": "create", "filePath": inputs["file_path"], "content": inputs.get("content", ""),
             "originalFile": None, "structuredPatch": [], "userModified": False}}
        self.native.extend((call, callback))
        if grant:
            self.parent.append(parent)
        else:
            require(not self.withheld_grants, "another synthetic grant is pending")
            self.withheld_grants[identity] = parent
        self.streams()
        return identity, result

    def grant(self, identity):
        require(set(self.withheld_grants) == {identity}, "synthetic grant is not the sole pending callback")
        self.parent.append(self.withheld_grants.pop(identity))
        self.streams()

    def settle(self, result, value=None):
        text = "checked" if value is None else self.c.canonical(value).decode()
        result["message"]["content"][0]["content"] = text
        if "stdout" in result["tool_use_result"]:
            result["tool_use_result"]["stdout"] = text
        self.native.append(result); self.streams()

    def helper(self, name, value=None):
        _, result = self.begin("Bash", {"command": self.composition["policy"]["native_shared_helpers"][name]})
        self.settle(result, value)

    def write(self, role, raw):
        _, result = self.begin("Write", {"file_path": self.paths[role], "content": raw.decode()})
        save_new(Path(self.paths[role]), raw)
        result["message"]["content"][0]["content"] = "File created successfully at: " + self.paths[role]
        self.native.append(result); self.streams()

    def load(self):
        return self.capture._load_live(self.path)

    def advance(self, *, publish=True):
        from data_sheets_schema import native_shared_stage as stage
        identity, result = self.begin("Bash", {"command": self.composition["policy"]["native_shared_helpers"]["advance"]})
        invocation = self.capture.capture_stage(self.path)
        if not publish:
            return invocation
        selected = (invocation.selection, invocation.execution, invocation.phase1, invocation.history)
        replay = stage._Replay(*selected).run()
        if replay.pending is not None and replay.pending[-1] is not None:
            response, _ = replay.pending[-1]
            proposal = stage.check_response(*selected, replay.pending[2].raw, response.raw)
        else:
            proposal = stage.prepare_next(*selected)
        published = self.capture.publish_stage(invocation, proposal)
        self.settle(result, published)
        self.capture.observe_advance_settled(self.load(), identity)
        require(published["state"] != "failed", "synthetic stage response failed real validation")
        return published

    def respond(self, answer, kind):
        decision = self.load().decision()
        require(decision.state == "awaiting_response" and decision.cursor.kind == kind,
                "synthetic response is not at the exact selected cursor")
        request = decision.request
        identity, result = self.begin("Read", {"file_path": request.pin.path})
        lines = request.raw.decode().split("\n")
        result["message"]["content"][0]["content"] = "\n".join(f"{n}\t{line}" for n, line in enumerate(lines, 1))
        result["tool_use_result"] = {"type": "text", "file": {"filePath": request.pin.path,
            "content": request.raw.decode(), "numLines": len(lines), "startLine": 1, "totalLines": len(lines)}}
        self.native.append(result); self.streams()
        self.capture.observe_request_read(self.load(), identity)
        response = answer(request.raw)
        identity, result = self.begin("Write", {"file_path": decision.response.path, "content": response.decode()}, grant=False)
        self.capture.observe_response_intent(self.load(), identity)
        self.grant(identity)
        save_new(Path(decision.response.path), response)
        result["message"]["content"][0]["content"] = "File created successfully at: " + decision.response.path
        self.native.append(result); self.streams()
        self.capture.observe_response_written(self.load(), identity)


def prepare_checkpoint(case, tools, imports):
    from data_sheets_schema import native_shared_capture as capture, native_shared_stage as stage
    from data_sheets_schema.source_review import inventory
    timings = []
    def step(name, call):
        start, cpu = time.perf_counter(), time.process_time()
        value = call()
        timings.append({"stage": name, "wall_seconds": time.perf_counter() - start,
                        "process_cpu_seconds": time.process_time() - cpu})
        return value
    data, spec, cap, runtime_path, composition, composition_path, answer = step(
        "full_schema_and_fresh_authority", lambda: fresh_authority(case, tools, imports))
    value = step("fabricated_permission_registration", lambda: register_synthetic(
        case, spec, cap, runtime_path, composition, composition_path, imports))
    fixture = step("initialize", lambda: SyntheticFrames(cap, value, composition, imports))
    def phase1():
        fixture.helper("chunk_check"); fixture.helper("source_scope")
        fixture.write("full", data["full_raw"]); fixture.write("receipt", data["receipt_raw"])
        fixture.helper("full_schema"); fixture.helper("full_terms"); fixture.helper("phase1_receipts")
        capture.seal_originals(fixture.load(), "seal_phase1")
    step("phase1_seal", phase1)
    step("admit_receipt", fixture.advance)
    step("receipt_read_intent_write", lambda: fixture.respond(answer, "receipt"))
    step("consume_receipt", fixture.advance)
    if fixture.load().decision().state != "await_core":
        step("publish_await_core", fixture.advance)
    require(fixture.load().decision().state == "await_core", "receipt did not reach await_core")
    def core():
        save_new(Path(fixture.paths["core"]), data["core_raw"])
        fixture.helper("derive_core"); fixture.helper("core_schema"); fixture.helper("pair")
        capture.seal_originals(fixture.load(), "seal_core")
        fixture.helper("original_source_inventory", inventory(data["full_raw"].decode(), "original_full"))
    step("derived_core_seal_and_actual_inventory", core)
    step("admit_worker_one", fixture.advance)
    step("worker_read_intent_write", lambda: fixture.respond(answer, "worker"))
    step("consume_worker_one", fixture.advance)
    step("admit_next_advance_without_publication", lambda: fixture.advance(publish=False))
    run = fixture.load()
    replay = stage._Replay(run.selection, run.binding, run.phase1, run.history).run()
    require(replay.receipt is not None and len(replay.workers) == 1 and replay.packet is not None,
            "checkpoint lacks consumed receipt and one checked worker")
    require(len(replay.packet["plan"]["workers"]) == 3, "checkpoint changed full worker denominator")
    phase, _ = capture.phase_replay(run)
    require(phase["passed"] and phase["core_sealed"] and not phase["complete"], "checkpoint phase is not the intended incomplete prefix")
    return {"selection_relative": Path(fixture.path).relative_to(case).as_posix(),
            "preparation_stages": timings, "checkpoint": checkpoint_summary(run, replay, phase),
            "synthetic_parameters": data["synthetic_parameters"], "declared_deadline_seconds": 900}


def checkpoint_summary(run, replay, phase):
    from data_sheets_schema import native_shared_contract as c
    return {"label": run.selection.document()["run"]["label"],
        "workers_declared": len(replay.packet["plan"]["workers"]), "workers_consumed": len(replay.workers),
        "receipt_consumed": replay.receipt is not None, "core_sealed": phase["core_sealed"],
        "complete": False, "pending_calls": len(phase["pending_tool_ids"]),
        "next_state": run.decision().state, "transcript_lines": run.transcript.lines,
        "control_lines": run.control.lines, "observations": len(run.observations),
        "history_records": len(run.history.records), "selection_sha256": run.selection.registration.pin.sha256,
        "journal_sha256": run.history.journal.pin.sha256, "packet_sha256": c.sha(c.canonical(replay.packet))}


def run_projection(run):
    """Complete exposed evidence + reader state; explicitly exclude implementation caches."""
    expected = {"selection", "value", "composition", "spec", "reader", "pool", "transcript", "control",
                "binding", "history", "observations", "phase1", "_catalogs"}
    require({f.name for f in fields(run)} == expected, "captured run shape changed")
    require(set(vars(run.reader)) == {"selection", "pool", "members", "total"}, "reader shape changed")
    result = {field.name: getattr(run, field.name) for field in fields(run)
              if field.name not in {"spec", "reader", "_catalogs"}}
    result["render_spec"] = run.spec.render_spec()
    result["reader"] = dict(vars(run.reader))
    return result


def measured(call, project, *, instrumented, tools, counters):
    observed = Counter()
    def profile(frame, event, argument):
        if event == "call" and frame.f_code in counters:
            observed[counters[frame.f_code]] += 1
    cpu, wall = time.process_time_ns(), time.perf_counter_ns()
    if instrumented:
        sys.setprofile(profile)
    try:
        try:
            value = call()
            status, refusal = "returned", None
        except ValueError as exc:
            value, status, refusal = None, "refused", tools.exception_value(exc)
    finally:
        if instrumented:
            sys.setprofile(None)
        cpu, wall = time.process_time_ns() - cpu, time.perf_counter_ns() - wall
    semantics = tools.typed_value(project(value)) if status == "returned" else refusal
    return {"status": status, "semantic_sha256": sha(canonical(semantics)), "refusal": refusal,
            "process_cpu_ns": cpu, "wall_ns": wall, "reconstruction_counts": dict(observed)}


def measure_checkpoint(case, declaration, tools):
    from data_sheets_schema import native_shared_capture as capture, native_shared_stage as stage
    from data_sheets_schema import native_shared_controller as controller, native_shared_contract as c
    from data_sheets_schema import native_shared_observations as observed, native_shared_evidence as evidence
    from data_sheets_schema.native_shared_streams import stream_files
    require(declaration["selection_relative"] == "authority/profile-selection.json", "checkpoint selection role differs")
    path = str(case / declaration["selection_relative"])
    counters = {capture._load_live.__code__: "_load_live", capture._decision_at.__code__: "_decision_at",
        capture._checked_observations.__code__: "_checked_observations", stage._Replay.run.__code__: "_Replay.run",
        stage._Replay._packet.__code__: "_Replay._packet", observed.Trace.__init__.__code__: "Trace.__init__"}
    rows = []
    def pair(name, setup, project=lambda x: x):
        results = []
        for instrumented in (False, True):
            call = setup()  # Reconstruct fresh owners outside this operation's timing.
            results.append(measured(call, project, instrumented=instrumented, tools=tools, counters=counters))
        match = [(row["status"], row["semantic_sha256"]) for row in results]
        require(match[0] == match[1], "plain/instrumented complete evidence or refusal differs")
        rows.append({"operation": name, "plain": results[0], "instrumented": results[1], "parity": True})
    pair("_load_live", lambda: lambda: capture._load_live(path), run_projection)
    def adapter_call():
        run = capture._load_live(path)
        adapter = controller.CallbackAdapter(c.canonical(run.composition), execution=run.value,
                                             registration_raw=run.binding.execution.raw)
        members, prefixes = capture._streams(run.value)
        adapter._stream_files = stream_files(members)
        adapter._stream_prefixes = dict(zip(("transcript", "control"), prefixes))
        endpoints = tuple(prefix.bytes for prefix in prefixes)
        return lambda: adapter._run(endpoints)
    pair("CallbackAdapter._run_fresh_owner", adapter_call, run_projection)
    pair("decision_fresh_loaded_run", lambda: capture._load_live(path).decision)
    def effect_call():
        run = capture._load_live(path)
        return lambda: capture.current_effect_view(run)
    pair("current_effect_view_fresh_loaded_run", effect_call)
    run = capture._load_live(path)
    replay = stage._Replay(run.selection, run.binding, run.phase1, run.history).run()
    phase, _ = capture.phase_replay(run)
    require(checkpoint_summary(run, replay, phase) == declaration["checkpoint"],
            "checkpoint declaration differs from actual reconstruction")
    require(run.value["runtime"]["deadline_seconds"] == 900 and
            run.selection.document()["run"]["label"] == LABEL,
            "checkpoint uses another synthetic identity or deadline")
    reads = [(index, c.strict_json(item.raw)) for index, item in enumerate(run.observations)
             if c.strict_json(item.raw)["observation_type"] == "request_read"]
    require(len(reads) == 2, "refusal fixture requires distinct receipt and worker reads")
    index, document = reads[-1]
    document["payload"]["history_sha256"] = reads[0][1]["payload"]["history_sha256"]
    original = run.observations[index]; raw = c.canonical(document)
    replacement = c.CapturedArtifact(replace(original.pin, bytes=len(raw), sha256=c.sha(raw)), raw)
    observations = tuple(replacement if item == original else item for item in run.observations)
    members = []
    for member in run.pool.members:
        if member.captured == original:
            metadata = c.strict_json(member.metadata_json); metadata["size"] = len(raw)
            member = evidence.PoolMember(replacement, c.canonical(metadata))
        members.append(member)
    pool = evidence.CapturePool(tuple(members), run.pool.stream_bindings)
    stale = replace(run, observations=observations, pool=pool, history=replace(run.history, observations=observations),
                    reader=capture._Reader(run.selection, pool=pool))
    def stale_call():
        fresh = replace(stale, reader=capture._Reader(stale.selection, pool=stale.pool))
        return lambda: capture._checked_observations(fresh)
    pair("refusal_stale_worker_read_in_memory", stale_call)
    doc = run.selection.document(); doc["run"]["label"] = "foreign-synthetic-authority"
    raw = c.canonical(doc)
    selected = replace(run.selection, registration=c.CapturedArtifact(
        replace(run.selection.registration.pin, bytes=len(raw), sha256=c.sha(raw)), raw))
    changed = replace(run, selection=selected)
    def changed_call():
        fresh = replace(changed, reader=capture._Reader(changed.selection, pool=changed.pool))
        return lambda: capture._checked_observations(fresh)
    pair("refusal_changed_selected_authority_in_memory", changed_call)
    require(all(row["plain"]["status"] == "returned" for row in rows[:4])
            and all(row["plain"]["status"] == "refused" for row in rows[4:]), "checkpoint controls have unexpected outcomes")
    return {"operations": rows, "projection": {"scope": "all exposed captured evidence, complete reader state, rendered spec",
        "excluded": ["RunSpec implementation caches", "_CapturedRun._catalogs implementation cache"],
        "decision_and_effect_view": "complete typed return", "refusals": "complete bounded exception graph"}}


def child(config):
    require_isolation()
    tools = utility()
    source, recovery, dependencies = (Path(config[k]).resolve(strict=True) for k in ("source", "recovery", "dependencies"))
    require(config.get("mode") in {"prepare", "measure"}, "unknown diagnostic phase")
    case = Path(config["case"])
    require(case.is_absolute() and case.resolve() == case, "checkpoint path is not physical and absolute")
    if config["mode"] == "prepare":
        require(not case.exists() and case.parent.is_dir(), "preparation requires a new checkpoint")
        for protected in (source, recovery, dependencies):
            require(not case.is_relative_to(protected) and not protected.is_relative_to(case),
                    "preparation checkpoint overlaps protected input")
    verified = tools.verify_inputs(source, recovery)
    require(verified["provenance"] == config["recovered_provenance"], "child recovered provenance differs")
    require(sha(tools.read_file(Path(__file__).resolve())) == config["driver_sha256"], "child driver identity differs")
    source_pins = tools.strict_json(tools.read_file(recovery / "artifact/source-before.json"))["entries"]
    python_pin = tools.executable_identity(Path(sys.executable))
    require(python_pin == config["python_identity"], "child interpreter identity differs")
    policy = PhasePolicy(source=source, write_root=case if config["mode"] == "prepare" else None,
                         git=Path(config["git"]), tools=tools)
    require(policy.git_pin == config["git_identity"], "child Git identity differs")
    policy.install()
    imports = SourceImports(source, dependencies, source_pins, tools)
    imports.install()
    if config["mode"] == "prepare":
        result = prepare_checkpoint(case, tools, imports)
    else:
        verify_declared_closure(config["declaration"]["loaded_closure"], imports)
        require(tree_manifest(case, read=tools.read_file) == config["declaration"]["case_inventory"],
                "checkpoint bytes changed before measurement")
        result = measure_checkpoint(case, config["declaration"], tools)
    closure = imports.verify()
    inventory = tree_manifest(case, read=tools.read_file)
    if config["mode"] == "measure":
        require(inventory == config["declaration"]["case_inventory"], "measurement changed checkpoint bytes")
    tools.verify_inputs(source, recovery)
    require(tools.executable_identity(Path(sys.executable)) == python_pin, "child interpreter changed")
    return {"format": CHILD_FORMAT, "mode": config["mode"], **result,
        "case_inventory": inventory, "loaded_closure": closure, "git": policy.verify(),
        "python_identity": python_pin, "flags": {"isolated": sys.flags.isolated, "no_site": sys.flags.no_site,
                                                "dont_write_bytecode": sys.dont_write_bytecode},
        "environment": environment_disclosure(),
        "recovered_provenance": verified["provenance"]}


def verify_declared_closure(rows, imports):
    require(type(rows) is list and rows, "prepared import closure is missing")
    seen = set()
    for row in rows:
        require(type(row) is dict and set(row) == {"origin", "sha256", "bytes"}, "prepared import pin shape differs")
        origin = row["origin"]
        require(type(origin) is str and "/" in origin and origin not in seen, "prepared import identity repeats")
        seen.add(origin)
        role, relative = origin.split("/", 1)
        roots = {"recovered": imports.source, "dependency": imports.dependencies, "interpreter": imports.stdlib}
        require(role in roots and relative and not Path(relative).is_absolute()
                and ".." not in Path(relative).parts and "\\" not in relative, "prepared import escapes its root")
        path = roots[role] / relative
        require(type(row["bytes"]) is int and row["bytes"] >= 0, "prepared import byte count differs")
        require(len(imports.tools.read_file(path, row["sha256"])) == row["bytes"], "prepared dependency changed")


def checkpoint_declaration(report, *, driver_sha256, python_identity, git_identity, recovered_provenance):
    require(type(report) is dict and report.get("format") == FORMAT and report.get("mode") == "prepare"
            and report.get("status") == "completed" and report.get("scientific_eligibility") is False
            and report.get("execution_authorized") is False and report.get("native_acceptance_evaluated") is False
            and report.get("utility_sha256") == UTILITY_SHA256,
            "input is not a completed offline preparation report")
    require(report.get("driver_sha256") == driver_sha256 and report.get("python_identity") == python_identity,
            "preparation driver or parent interpreter differs")
    result = report.get("result")
    require(type(result) is dict and result.get("selection_relative") == "authority/profile-selection.json"
            and type(result.get("declared_deadline_seconds")) is int
            and result.get("declared_deadline_seconds") == 900, "prepared checkpoint role or deadline differs")
    checkpoint = result.get("checkpoint")
    require(type(checkpoint) is dict and checkpoint.get("label") == LABEL and checkpoint.get("complete") is False
            and type(checkpoint.get("workers_declared")) is int and type(checkpoint.get("workers_consumed")) is int
            and checkpoint.get("workers_declared") == 3 and checkpoint.get("workers_consumed") == 1
            and checkpoint.get("receipt_consumed") is True, "prepared checkpoint is not the selected incomplete prefix")
    validate_child_report(result, {"mode": "prepare", "python_identity": python_identity,
                                  "git_identity": git_identity, "recovered_provenance": recovered_provenance})
    return result


def validate_child_report(result, selected):
    common = {"format", "mode", "case_inventory", "loaded_closure", "git", "python_identity", "flags",
              "environment", "recovered_provenance"}
    specific = ({"selection_relative", "preparation_stages", "checkpoint", "synthetic_parameters",
                 "declared_deadline_seconds"} if selected["mode"] == "prepare" else {"operations", "projection"})
    require(type(result) is dict and set(result) == common | specific
            and result["format"] == CHILD_FORMAT and result["mode"] == selected["mode"],
            "child returned another report shape or phase")
    for key in ("python_identity", "recovered_provenance"):
        require(canonical(result[key]) == canonical(selected[key]), "child returned another " + key)
    require(canonical(result["flags"]) == canonical({"isolated": 1, "no_site": 1, "dont_write_bytecode": True}),
            "child returned invalid isolation flags")
    require(type(result["git"]) is dict and set(result["git"]) == {"identity", "calls"}
            and canonical(result["git"]["identity"]) == canonical(selected["git_identity"]),
            "child returned another Git identity")
    calls = result["git"]["calls"]
    require(type(calls) is dict and set(calls) <= {"rev-parse HEAD", "cat-file --batch"}
            and all(type(count) is int and count >= 0 for count in calls.values()), "child Git accounting differs")
    inventory = result["case_inventory"]
    require(type(inventory) is dict and set(inventory) == {"entries", "files", "bytes"}
            and type(inventory["entries"]) is dict and type(inventory["files"]) is int
            and type(inventory["bytes"]) is int and inventory["files"] == len(inventory["entries"]),
            "child checkpoint inventory shape differs")
    require(type(result["loaded_closure"]) is list and result["loaded_closure"], "child imported closure is missing")
    require(type(result["environment"]) is dict and set(result["environment"]) == {"python", "platform", "machine"},
            "child environment disclosure shape differs")


def dispatch(args):
    require_isolation()
    tools = utility()
    source, recovery, dependencies = (Path(getattr(args, k)).resolve(strict=True) for k in ("source", "recovery", "dependencies"))
    output = Path(args.output).absolute()
    require(output.resolve() == output and not output.exists() and output.parent.is_dir(),
            "output must be a new physical directory below an existing parent")
    for protected in (source, recovery, dependencies):
        require(not output.is_relative_to(protected) and not protected.is_relative_to(output), "output overlaps protected inputs")
    executable = Path(sys.executable).resolve(strict=True)
    git = shutil.which("git")
    require(git is not None, "explicit local Git dependency unavailable")
    git = Path(git).resolve(strict=True)
    driver_raw = tools.read_file(Path(__file__).resolve())
    config = {"mode": args.command, "source": str(source), "recovery": str(recovery), "dependencies": str(dependencies),
        "python_identity": tools.executable_identity(executable), "git": str(git),
        "git_identity": tools.executable_identity(git), "driver_sha256": sha(driver_raw),
        "recovered_provenance": tools.verify_inputs(source, recovery)["provenance"]}
    if args.command == "measure":
        checkpoint = Path(args.checkpoint).resolve(strict=True)
        require(not output.is_relative_to(checkpoint) and not checkpoint.is_relative_to(output), "output overlaps checkpoint")
        prepared_raw = tools.read_file(checkpoint / "report.json")
        config["declaration"] = checkpoint_declaration(tools.strict_json(prepared_raw),
            **{key: config[key] for key in ("driver_sha256", "python_identity", "git_identity", "recovered_provenance")})
        config["case"] = str(checkpoint / "case")
        case_before = tree_manifest(Path(config["case"]), read=tools.read_file)
        require(case_before == config["declaration"]["case_inventory"], "checkpoint changed before dispatch")
    else:
        config["case"] = str(output / "case")
    if args.command == "measure":
        require(tools.read_file(checkpoint / "report.json") == prepared_raw,
                "preparation report changed during measurement")
        require(tree_manifest(Path(config["case"]), read=tools.read_file) == case_before,
                "measurement changed checkpoint files")
    output.mkdir()
    bound = PREPARE_WALL_SECONDS if args.command == "prepare" else MEASURE_WALL_SECONDS
    argv = [str(executable), "-I", "-B", "-S", str(Path(__file__).resolve()), "_child"]
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "GIT_"))}
    started = time.perf_counter()
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            cwd=source, env=environment, start_new_session=True)
    timeout = False
    try:
        stdout, stderr = proc.communicate(canonical(config), timeout=bound)
    except subprocess.TimeoutExpired:
        timeout = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # The group exited after the timeout; still reap and verify.
        stdout, stderr = proc.communicate()
    elapsed = time.perf_counter() - started
    require(tools.executable_identity(executable) == config["python_identity"], "parent interpreter changed")
    require(tools.executable_identity(git) == config["git_identity"], "parent Git executable changed")
    require(tools.read_file(Path(__file__).resolve()) == driver_raw, "driver changed during child")
    require(tools.verify_inputs(source, recovery)["provenance"] == config["recovered_provenance"],
            "parent recovered provenance changed")
    if args.command == "measure":
        require(tools.read_file(checkpoint / "report.json") == prepared_raw,
                "preparation report changed during measurement")
        require(tree_manifest(Path(config["case"]), read=tools.read_file) == case_before,
                "measurement changed checkpoint files")
    result = None
    if not timeout and proc.returncode == 0:
        require(len(stdout) <= MAX_REPORT_BYTES, "child result exceeds report bound")
        result = tools.strict_json(stdout)
        validate_child_report(result, config)
        if args.command == "measure":
            require(result["case_inventory"] == case_before, "child returned another checkpoint inventory")
        else:
            require(result["case_inventory"] == tree_manifest(Path(config["case"]), read=tools.read_file),
                    "child preparation inventory differs from actual files")
    report = {"format": FORMAT, "mode": args.command, "scope": SCOPE,
        "status": "diagnostic_timeout" if timeout else "completed" if result is not None else "diagnostic_refused",
        "scientific_eligibility": False, "execution_authorized": False, "historical_capture_complete": False,
        "native_acceptance_evaluated": False, "declared_acceptance_deadline_seconds": 900,
        "diagnostic_wall_bound_seconds": bound, "parent_wall_seconds": elapsed, "child_exit_code": proc.returncode,
        "driver_sha256": sha(driver_raw), "utility_sha256": UTILITY_SHA256,
        "python_identity": config["python_identity"], "stderr_bytes": len(stderr), "stderr_sha256": sha(stderr),
        "stdout_bytes": len(stdout), "stdout_sha256": sha(stdout), "result": result, "limitations": list(LIMITATIONS)}
    raw = canonical(report) + b"\n"
    require(len(raw) <= MAX_REPORT_BYTES, "publication exceeds complete report bound")
    save_new(output / "report.json", raw)
    if result is None:
        # Diagnostic text remains local; it is never an input or success flag.
        save_new(output / "refusal.stderr", stderr[:1024 * 1024])
    return 0 if result is not None else 1


def main(argv=None):
    if (sys.argv[1:] if argv is None else argv) == ["_child"]:
        config = json.loads(sys.stdin.buffer.read(MAX_REPORT_BYTES + 1))
        result = child(config)
        sys.stdout.buffer.write(canonical(result))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "measure"):
        command = commands.add_parser(name)
        for key in ("source", "recovery", "dependencies", "output"):
            command.add_argument("--" + key, required=True)
        if name == "measure":
            command.add_argument("--checkpoint", required=True)
    return dispatch(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
