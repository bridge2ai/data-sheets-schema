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
import math
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
FORMAT = "native_full_schema_checkpoint_v2"
CHILD_FORMAT = "native_full_schema_checkpoint_child_v2"
CATALOG_FORMAT = "native_full_schema_operations_v1"
COLLECTION_FORMAT = "native_full_schema_operation_collection_v1"
BINDING_FORMAT = "native_full_schema_measurement_binding_v1"
OPERATIONS = (
    ("_load_live", "returned"),
    ("CallbackAdapter._run_fresh_owner", "returned"),
    ("decision_fresh_loaded_run", "returned"),
    ("current_effect_view_fresh_loaded_run", "returned"),
    ("refusal_stale_worker_read_in_memory", "refused"),
    ("refusal_changed_selected_authority_in_memory", "refused"),
)
COUNTERS = ("_load_live", "_decision_at", "_checked_observations", "_Replay.run", "_Replay._packet", "Trace.__init__")
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
    "Each selected pair has its own 600-second diagnostic bound; all four positive and both refusal pairs are required. Missing or failed pairs are never omitted from the denominator.",
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


def operation_catalog():
    return {"format": CATALOG_FORMAT,
            "operations": [{"operation": name, "expected_status": status} for name, status in OPERATIONS]}


def operation_set(statuses):
    """Parent diagnostic completion is distinct from an expected refusal control."""
    require(set(statuses) <= {name for name, _ in OPERATIONS}, "operation set contains another identity")
    completed = [name for name, _ in OPERATIONS if statuses.get(name) == "completed"]
    failed = [name for name, _ in OPERATIONS if name in statuses and statuses[name] != "completed"]
    missing = [name for name, _ in OPERATIONS if name not in statuses]
    return {"required": len(OPERATIONS), "completed": completed, "failed": failed,
            "missing": missing, "complete": not failed and not missing}


def projection_contract():
    return {"scope": "all exposed captured evidence, complete reader state, rendered spec",
            "excluded": ["RunSpec implementation caches", "_CapturedRun._catalogs implementation cache"],
            "decision_and_effect_view": "complete typed return", "refusals": "complete bounded exception graph"}


def ns_clock():
    return time.process_time_ns(), time.perf_counter_ns()


def elapsed_ns(start):
    return {"process_cpu_ns": time.process_time_ns() - start[0],
            "wall_ns": time.perf_counter_ns() - start[1]}


def is_digest(value):
    return type(value) is str and len(value) == 64 and all(ch in '0123456789abcdef' for ch in value)


def validate_timing(value):
    require(type(value) is dict and set(value) == {"process_cpu_ns", "wall_ns"}
            and all(type(item) is int and item >= 0 for item in value.values()), "timing shape or value differs")


def _typed_value_validator():
    """One complete bounded typed-value traversal, shared across an exception graph."""
    typed_nodes = 0
    def typed(item, depth=0):
        nonlocal typed_nodes
        typed_nodes += 1
        require(typed_nodes <= 100000 and depth <= 128, "typed values exceed bound")
        require(type(item) is list and item and type(item[0]) is str, "typed value differs")
        kind = item[0]
        if kind == "none":
            require(len(item) == 1, "none typed value differs")
        elif kind in {"str", "int", "float", "bool"}:
            wanted = {"str": str, "int": int, "float": float, "bool": bool}[kind]
            require(len(item) == 2 and type(item[1]) is wanted, "scalar typed value differs")
            require(kind != "float" or math.isfinite(item[1]), "nonfinite typed float differs")
        elif kind == "bytes":
            require(len(item) == 3 and type(item[1]) is int and item[1] >= 0 and is_digest(item[2]), "byte typed value differs")
        elif kind in {"list", "tuple"}:
            require(len(item) == 2 and type(item[1]) is list, "sequence typed value differs")
            for child in item[1]:
                typed(child, depth + 1)
        elif kind in {"dict", "dataclass"}:
            require(len(item) == (2 if kind == "dict" else 3), "mapping typed value differs")
            if kind == "dataclass":
                require(type(item[1]) is str and item[1], "dataclass identity differs")
            require(type(item[-1]) is list, "mapping entries differ")
            keys = set()
            for pair in item[-1]:
                require(type(pair) is list and len(pair) == 2, "mapping pair differs")
                if kind == "dict":
                    typed(pair[0], depth + 1)
                    key = canonical(pair[0])
                else:
                    require(type(pair[0]) is str, "dataclass field differs")
                    key = pair[0]
                require(key not in keys, "typed mapping key or dataclass field repeats")
                keys.add(key)
                typed(pair[1], depth + 1)
        else:
            raise BoundaryError("unknown typed value")
    return typed


def validate_typed_value(value):
    """Validate every tag produced by the pinned utility, without decoding objects."""
    _typed_value_validator()(value)


def validate_exception(value):
    """Validate the utility's complete graph representation, without importing exception classes."""
    seen = set()
    typed = _typed_value_validator()
    def node(item):
        if item is None:
            return
        require(type(item) is dict, "exception node differs")
        if set(item) == {"reference"}:
            require(type(item["reference"]) is int and item["reference"] in seen, "exception reference is unresolved")
            return
        require(set(item) == {"node", "type", "arguments", "cause", "context", "suppress_context", "notes"},
                "exception graph omits or adds state")
        require(type(item["node"]) is int and item["node"] == len(seen) and len(seen) < 32,
                "exception node order or bound differs")
        require(type(item["type"]) is str and item["type"] and type(item["suppress_context"]) is bool,
                "exception identity or suppression differs")
        seen.add(item["node"])
        typed(item["arguments"])
        require(item["arguments"][0] == "tuple", "exception arguments are not a tuple")
        typed(item["notes"])
        node(item["cause"])
        node(item["context"])
    require(type(value) is dict and "node" in value, "exception root is missing")
    node(value)
    canonical(value)  # Non-finite typed floats are refused as well.


def validate_pair(row, expected_operation):
    """Recompute agreement; a saved parity flag alone is never sufficient."""
    require(type(expected_operation) is str and expected_operation in dict(OPERATIONS), "unknown selected operation")
    require(type(row) is dict and set(row) == {"operation", "plain", "instrumented", "parity"}
            and row["operation"] == expected_operation, "pair operation or shape differs")
    for arm in ("plain", "instrumented"):
        value = row[arm]
        require(type(value) is dict and set(value) == {"status", "semantic_sha256", "semantics", "refusal", "process_cpu_ns", "wall_ns",
                                                     "reconstruction_counts", "setup", "fingerprint"}, "pair arm shape differs")
        require(value["status"] == dict(OPERATIONS)[expected_operation] and is_digest(value["semantic_sha256"]),
                "operation outcome or semantic digest differs")
        validate_timing({name: value[name] for name in ("process_cpu_ns", "wall_ns")})
        validate_timing(value["setup"]); validate_timing(value["fingerprint"])
        counts = value["reconstruction_counts"]
        require(type(counts) is dict and set(counts) <= set(COUNTERS)
                and all(type(count) is int and count >= 0 for count in counts.values()), "reconstruction counts differ")
        require(arm != "plain" or counts == {}, "plain arm claims instrumentation")
        if value["status"] == "refused":
            require(value["semantics"] is None, "refused operation carries returned semantics")
            validate_exception(value["refusal"])
            require(sha(canonical(value["refusal"])) == value["semantic_sha256"], "refusal graph digest differs")
        else:
            require(value["refusal"] is None, "returned operation carries a refusal")
            validate_typed_value(value["semantics"])
            require(sha(canonical(value["semantics"])) == value["semantic_sha256"], "returned semantics digest differs")
    left, right = row["plain"], row["instrumented"]
    require(left["semantic_sha256"] == right["semantic_sha256"]
            and canonical(left["semantics"]) == canonical(right["semantics"])
            and canonical(left["refusal"]) == canonical(right["refusal"]), "plain/instrumented complete evidence or refusal differs")
    require(row["parity"] is True, "saved pair parity differs from recomputed agreement")
    return True


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
        self.interpreter_only = False
        self.stdlib = Path(os.__file__).resolve().parent
        self.original_code = importlib.machinery.SourceFileLoader.get_code
        self.original_extension = importlib.machinery.ExtensionFileLoader.create_module
        self.original_sourceless = importlib.machinery.SourcelessFileLoader.get_code

    def allowed_dependency(self, path):
        interpreter = self.interpreter_origin(path)
        return interpreter if self.interpreter_only else path.is_relative_to(self.dependencies) or interpreter

    def interpreter_origin(self, path):
        return (path.is_relative_to(self.stdlib)
                and not {"site-packages", "dist-packages"}.intersection(path.relative_to(self.stdlib).parts)
                and not path.is_relative_to(self.source) and not path.is_relative_to(self.dependencies))

    def source_code(self, path):
        original = Path(path).absolute()
        path = original.resolve(strict=True)
        require(path == original, "import path contains a symlink")
        require(not self.interpreter_only or self.interpreter_origin(path),
                "bootstrap import outside selected interpreter")
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
                require(not self.interpreter_only or self.interpreter_origin(path),
                        "bootstrap execution outside selected interpreter")
                if path.is_relative_to(self.source):
                    require(sha(marshal.dumps(code)) in self.approved_code,
                            "recovered code did not come from verified source compilation")

    def install(self, *, add_paths=True):
        owner = self
        def get_code(loader, fullname):
            if owner.interpreter_only and fullname in {"ctypes", "ctypes._endian"}:
                expected = owner.stdlib / ("ctypes/__init__.py" if fullname == "ctypes" else "ctypes/_endian.py")
                require(Path(loader.get_filename(fullname)).absolute() == expected,
                        "ctypes bootstrap source identity differs")
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
        if add_paths:
            self.enable_selected_paths()

    def enable_selected_paths(self):
        require(not self.interpreter_only, "selected paths cannot be exposed during interpreter bootstrap")
        sys.path[:0] = [str(self.source / "src"), str(self.source), str(self.dependencies)]

    def preload_ctypes(self):
        """Pin the selected interpreter's fixed initialization before effect denial.

        This bootstrap exposes no recovered/dependency search paths. Loader and
        exec checks reject such origins before execution, including shadow modules.
        The selected POSIX stdlib initializes its own process handle; subsequent
        ctypes audit events receive no initialization exception from PhasePolicy.
        """
        require(not any(name == "_ctypes" or name == "ctypes" or name.startswith("ctypes.")
                        for name in sys.modules), "ctypes must not precede tracked interpreter bootstrap")
        before = set(sys.modules)
        self.interpreter_only = True
        try:
            importlib.import_module("ctypes")
            for name in set(sys.modules) - before:
                module = sys.modules[name]
                origin = getattr(getattr(module, "__spec__", None), "origin", None)
                if origin in {"built-in", "frozen"}:
                    continue  # These belong to the selected interpreter identity.
                require(type(origin) is str and Path(origin).is_absolute(),
                        "bootstrap module has no physical interpreter origin")
                path = Path(origin)
                require(path.resolve(strict=True) == path and self.interpreter_origin(path)
                        and str(path) in self.loaded, "bootstrap module escaped tracked interpreter imports")
            for name, relative in (("ctypes", "ctypes/__init__.py"), ("ctypes._endian", "ctypes/_endian.py")):
                module = sys.modules.get(name)
                origin = getattr(getattr(module, "__spec__", None), "origin", None)
                require(origin == str(self.stdlib / relative) and origin in self.loaded,
                        "ctypes bootstrap source identity differs")
            extension = sys.modules.get("_ctypes")
            origin = getattr(getattr(extension, "__spec__", None), "origin", None)
            require(type(origin) is str and origin in self.loaded
                    and isinstance(extension.__spec__.loader, importlib.machinery.ExtensionFileLoader),
                    "ctypes bootstrap extension identity differs")
        finally:
            self.interpreter_only = False

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
        if event.startswith("ctypes."):
            raise BoundaryError("direct ctypes effects are forbidden after interpreter bootstrap")
        if event == "os.chdir":
            raise BoundaryError("working-directory changes are forbidden")
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
        descriptor_events = {"os.mkdir": (3, 2), "os.rmdir": (2, 1), "os.remove": (2, 1),
                             "os.chmod": (3, 2), "os.utime": (4, 3)}
        if event in descriptor_events:
            size, descriptor = descriptor_events[event]
            require(len(args) == size, "filesystem mutation audit shape differs")
            fd = args[descriptor]
            require(fd is None or type(fd) is int and fd == -1,
                    "filesystem mutation dir_fd overrides are forbidden")
            require(event in {"os.chmod", "os.utime"} or not isinstance(args[0], int),
                    "filesystem mutation requires a path")
            self.writable(args[0])
        if event == "os.truncate":
            require(len(args) == 2, "filesystem mutation audit shape differs")
            self.writable(args[0])
        if event == "os.rename":
            # The actual publisher replaces only its exact journal after CAS.
            require(len(args) == 4 and all(fd is None or type(fd) is int and fd == -1 for fd in args[2:]),
                    "journal replacement dir_fd overrides are forbidden")
            self.writable(args[0]); self.writable(args[1])
        if event == "os.link":
            require(len(args) == 4, "publication hard-link audit shape differs")
            self.publication_link(*args)
        if event in {"os.symlink", "os.chown", "os.chflags", "os.setxattr", "os.removexattr"}:
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
    failure = None
    if instrumented:
        sys.setprofile(profile)
    try:
        try:
            value = call()
            status = "returned"
        except ValueError as exc:
            value, status, failure = None, "refused", exc
    finally:
        if instrumented:
            sys.setprofile(None)
        cpu, wall = time.process_time_ns() - cpu, time.perf_counter_ns() - wall
    fingerprint_start = ns_clock()
    refusal = tools.exception_value(failure) if failure is not None else None
    semantics = tools.typed_value(project(value)) if status == "returned" else None
    if status == "returned":
        validate_typed_value(semantics)
    else:
        validate_exception(refusal)
    digest = sha(canonical(semantics if status == "returned" else refusal))
    return {"status": status, "semantic_sha256": digest, "semantics": semantics, "refusal": refusal,
            "process_cpu_ns": cpu, "wall_ns": wall, "reconstruction_counts": dict(observed),
            "fingerprint": elapsed_ns(fingerprint_start)}


def measure_checkpoint(case, declaration, tools, operation):
    require(type(operation) is str and operation in dict(OPERATIONS), "unknown selected operation")
    verification_start = ns_clock()
    from data_sheets_schema import native_shared_capture as capture, native_shared_stage as stage
    from data_sheets_schema import native_shared_controller as controller, native_shared_contract as c
    from data_sheets_schema import native_shared_observations as observed, native_shared_evidence as evidence
    from data_sheets_schema.native_shared_streams import stream_files
    require(declaration["selection_relative"] == "authority/profile-selection.json", "checkpoint selection role differs")
    path = str(case / declaration["selection_relative"])
    counters = {capture._load_live.__code__: "_load_live", capture._decision_at.__code__: "_decision_at",
        capture._checked_observations.__code__: "_checked_observations", stage._Replay.run.__code__: "_Replay.run",
        stage._Replay._packet.__code__: "_Replay._packet", observed.Trace.__init__.__code__: "Trace.__init__"}
    checked = capture._load_live(path)
    replay = stage._Replay(checked.selection, checked.binding, checked.phase1, checked.history).run()
    phase, _ = capture.phase_replay(checked)
    require(checkpoint_summary(checked, replay, phase) == declaration["checkpoint"],
            "checkpoint declaration differs from actual reconstruction")
    require(checked.value["runtime"]["deadline_seconds"] == 900 and
            checked.selection.document()["run"]["label"] == LABEL,
            "checkpoint uses another synthetic identity or deadline")
    checkpoint_verification = elapsed_ns(verification_start)
    del checked, replay, phase

    def adapter_call():
        run = capture._load_live(path)
        adapter = controller.CallbackAdapter(c.canonical(run.composition), execution=run.value,
                                             registration_raw=run.binding.execution.raw)
        members, prefixes = capture._streams(run.value)
        adapter._stream_files = stream_files(members)
        adapter._stream_prefixes = dict(zip(("transcript", "control"), prefixes))
        endpoints = tuple(prefix.bytes for prefix in prefixes)
        return lambda: adapter._run(endpoints)
    def effect_call():
        run = capture._load_live(path)
        return lambda: capture.current_effect_view(run)

    def stale_call():
        # Each arm gets a real fresh owner; mutations never touch case files.
        run = capture._load_live(path)
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
        fresh = replace(run, observations=observations, pool=pool, history=replace(run.history, observations=observations),
                        reader=capture._Reader(run.selection, pool=pool))
        return lambda: capture._checked_observations(fresh)

    def changed_call():
        run = capture._load_live(path)
        doc = run.selection.document(); doc["run"]["label"] = "foreign-synthetic-authority"
        raw = c.canonical(doc)
        selected = replace(run.selection, registration=c.CapturedArtifact(
            replace(run.selection.registration.pin, bytes=len(raw), sha256=c.sha(raw)), raw))
        fresh = replace(run, selection=selected, reader=capture._Reader(selected, pool=run.pool))
        return lambda: capture._checked_observations(fresh)

    setups = {"_load_live": lambda: lambda: capture._load_live(path),
              "CallbackAdapter._run_fresh_owner": adapter_call,
              "decision_fresh_loaded_run": lambda: capture._load_live(path).decision,
              "current_effect_view_fresh_loaded_run": effect_call,
              "refusal_stale_worker_read_in_memory": stale_call,
              "refusal_changed_selected_authority_in_memory": changed_call}
    project = run_projection if operation in {"_load_live", "CallbackAdapter._run_fresh_owner"} else lambda x: x
    arms = []
    for instrumented in (False, True):
        started = ns_clock()
        call = setups[operation]()
        setup_time = elapsed_ns(started)
        value = measured(call, project, instrumented=instrumented, tools=tools, counters=counters)
        value["setup"] = setup_time
        arms.append(value)
    row = {"operation": operation, "plain": arms[0], "instrumented": arms[1], "parity": True}
    validate_pair(row, operation)
    return {"operation": operation, "operations": [row], "checkpoint_verification": checkpoint_verification,
            "projection": projection_contract()}


def child(config):
    preflight_start = ns_clock()
    require_isolation()
    require(config.get("mode") in {"prepare", "measure"}, "unknown diagnostic phase")
    if config["mode"] == "measure":
        require(type(config.get("operation")) is str and config["operation"] in dict(OPERATIONS), "unknown selected operation")
    tools = utility()
    source, recovery, dependencies = (Path(config[k]).resolve(strict=True) for k in ("source", "recovery", "dependencies"))
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
    imports = SourceImports(source, dependencies, source_pins, tools)
    imports.install(add_paths=False)
    imports.preload_ctypes()
    policy.install()
    imports.enable_selected_paths()
    if config["mode"] == "measure":
        verify_declared_closure(config["declaration"]["loaded_closure"], imports)
        require(tree_manifest(case, read=tools.read_file) == config["declaration"]["case_inventory"],
                "checkpoint bytes changed before measurement")
    preflight = elapsed_ns(preflight_start)
    if config["mode"] == "prepare":
        result = prepare_checkpoint(case, tools, imports)
    else:
        result = measure_checkpoint(case, config["declaration"], tools, config["operation"])
    final_start = ns_clock()
    closure = imports.verify()
    inventory = tree_manifest(case, read=tools.read_file)
    if config["mode"] == "measure":
        require(inventory == config["declaration"]["case_inventory"], "measurement changed checkpoint bytes")
    tools.verify_inputs(source, recovery)
    require(tools.executable_identity(Path(sys.executable)) == python_pin, "child interpreter changed")
    git_state, environment = policy.verify(), environment_disclosure()
    return {"format": CHILD_FORMAT, "mode": config["mode"], **result,
        "case_inventory": inventory, "loaded_closure": closure, "git": git_state,
        "phase_overhead": {"preflight": preflight, "final_verification": elapsed_ns(final_start)},
        "python_identity": python_pin, "flags": {"isolated": sys.flags.isolated, "no_site": sys.flags.no_site,
                                                "dont_write_bytecode": sys.dont_write_bytecode},
        "environment": environment,
        "recovered_provenance": verified["provenance"]}


def validate_loaded_closure(rows):
    """Check captured import declarations without reopening their original paths."""
    require(type(rows) is list and rows, "import closure is missing")
    by_origin = {}
    for row in rows:
        require(type(row) is dict and set(row) == {"origin", "sha256", "bytes"}, "import pin shape differs")
        origin = row["origin"]
        require(type(origin) is str and "/" in origin and origin not in by_origin, "import identity differs or repeats")
        role, relative = origin.split("/", 1)
        require(role in {"recovered", "dependency", "interpreter"}
                and all(part not in {"", ".", ".."} for part in relative.split("/"))
                and "\\" not in relative and "\x00" not in relative, "import origin is not canonical role-relative identity")
        require(is_digest(row["sha256"]) and type(row["bytes"]) is int and row["bytes"] >= 0,
                "import digest or byte count differs")
        by_origin[origin] = row
    return by_origin


def verify_declared_closure(rows, imports):
    for origin, row in validate_loaded_closure(rows).items():
        role, relative = origin.split("/", 1)
        roots = {"recovered": imports.source, "dependency": imports.dependencies, "interpreter": imports.stdlib}
        path = roots[role] / relative
        require(len(imports.tools.read_file(path, row["sha256"])) == row["bytes"], "prepared dependency changed")


def checkpoint_declaration(report, *, driver_sha256, python_identity, git_identity, recovered_provenance):
    require(type(report) is dict and set(report) == PARENT_REPORT_FIELDS, "preparation parent report shape differs")
    require(report.get("format") == FORMAT and report.get("mode") == "prepare"
            and report.get("report_role") == "checkpoint_preparation" and report.get("operation") is None
            and canonical(report.get("operation_catalog")) == canonical(operation_catalog())
            and report.get("measurement_binding") is None and report.get("status") == "completed"
            and report.get("utility_sha256") == UTILITY_SHA256,
            "input is not a completed offline preparation report")
    require(all(report[key] is False for key in ("scientific_eligibility", "execution_authorized",
                "native_acceptance_evaluated", "historical_capture_complete")), "preparation report changes eligibility")
    require(report["scope"] == SCOPE and canonical(report["limitations"]) == canonical(LIMITATIONS),
            "preparation scope or limitations differ")
    require(canonical(report["operation_set"]) == canonical(operation_set({})), "preparation operation denominator differs")
    require(type(report["diagnostic_wall_bound_seconds"]) is int
            and report["diagnostic_wall_bound_seconds"] == PREPARE_WALL_SECONDS
            and type(report["declared_acceptance_deadline_seconds"]) is int
            and report["declared_acceptance_deadline_seconds"] == 900, "preparation report changes limits")
    require(type(report["parent_wall_seconds"]) in (int, float) and report["parent_wall_seconds"] >= 0
            and (type(report["parent_wall_seconds"]) is int or math.isfinite(report["parent_wall_seconds"])),
            "preparation parent duration differs")
    require(type(report["child_exit_code"]) is int and report["child_exit_code"] == 0,
            "completed preparation lacks successful child")
    for name in ("stdout", "stderr"):
        require(type(report[name + "_bytes"]) is int and report[name + "_bytes"] >= 0
                and is_digest(report[name + "_sha256"]), "preparation child stream identity differs")
    require(report.get("driver_sha256") == driver_sha256
            and canonical(report.get("python_identity")) == canonical(python_identity),
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
    stdout = canonical(result)
    require(report["stdout_sha256"] == sha(stdout) and report["stdout_bytes"] == len(stdout),
            "completed preparation child output pin differs")
    return result


def validate_child_report(result, selected):
    common = {"format", "mode", "case_inventory", "loaded_closure", "git", "python_identity", "flags",
              "environment", "recovered_provenance", "phase_overhead"}
    specific = ({"selection_relative", "preparation_stages", "checkpoint", "synthetic_parameters",
                 "declared_deadline_seconds"} if selected["mode"] == "prepare" else
                {"operation", "operations", "projection", "checkpoint_verification"})
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
    loaded = validate_loaded_closure(result["loaded_closure"])
    require(type(result["environment"]) is dict and set(result["environment"]) == {"python", "platform", "machine"},
            "child environment disclosure shape differs")
    require(all(type(value) is str for value in result["environment"].values()), "child environment value differs")
    require(type(result["phase_overhead"]) is dict and set(result["phase_overhead"]) == {"preflight", "final_verification"},
            "child phase overhead differs")
    for value in result["phase_overhead"].values():
        validate_timing(value)
    if selected["mode"] == "measure":
        prepared = validate_loaded_closure(selected["declaration"]["loaded_closure"])
        require(all(canonical(loaded[origin]) == canonical(prepared[origin]) for origin in loaded.keys() & prepared.keys()),
                "child import pin differs from prepared origin")
        require(result["operation"] == selected["operation"] and type(result["operations"]) is list
                and len(result["operations"]) == 1, "child returned another operation or pair denominator")
        validate_pair(result["operations"][0], selected["operation"])
        validate_timing(result["checkpoint_verification"])
        require(canonical(result["projection"]) == canonical(projection_contract()), "child evidence projection contract differs")


def measurement_binding(prepared_raw, declaration, selected):
    inventory, closure = declaration["case_inventory"], declaration["loaded_closure"]
    return {"format": BINDING_FORMAT, "preparation_report": {"sha256": sha(prepared_raw), "bytes": len(prepared_raw)},
        "case_inventory": {"sha256": sha(canonical(inventory)), "files": inventory["files"], "bytes": inventory["bytes"]},
        "checkpoint": deepcopy(declaration["checkpoint"]), "selection_relative": declaration["selection_relative"],
        "prepared_loaded_closure": {"sha256": sha(canonical(closure)), "entries": len(closure)},
        **{key: deepcopy(selected[key]) for key in ("driver_sha256", "python_identity", "git_identity", "recovered_provenance")},
        "utility_sha256": UTILITY_SHA256, "operation_catalog": operation_catalog(),
        "diagnostic_wall_bound_seconds": MEASURE_WALL_SECONDS, "declared_acceptance_deadline_seconds": 900}


def read_report(path, tools):
    path = Path(path).absolute()
    require(path.stat().st_size <= MAX_REPORT_BYTES, "report exceeds complete report bound")
    raw = tools.read_file(path)
    require(len(raw) <= MAX_REPORT_BYTES, "report exceeds complete report bound")
    try:
        document = tools.strict_json(raw)
    except (ValueError, RecursionError) as exc:
        raise BoundaryError("report is not bounded strict JSON") from exc
    require(type(document) is dict, "report root is not an object")
    return raw, document


PARENT_REPORT_FIELDS = frozenset({
    "format", "mode", "scope", "status", "scientific_eligibility", "execution_authorized",
    "historical_capture_complete", "native_acceptance_evaluated", "declared_acceptance_deadline_seconds",
    "diagnostic_wall_bound_seconds", "parent_wall_seconds", "child_exit_code", "driver_sha256", "utility_sha256",
    "python_identity", "stderr_bytes", "stderr_sha256", "stdout_bytes", "stdout_sha256", "result", "limitations",
    "report_role", "operation", "operation_catalog", "measurement_binding", "operation_set",
})


def dispatch(args):
    require_isolation()
    require(args.command in {"prepare", "measure"}, "unknown dispatch phase")
    if args.command == "measure":
        require(type(args.operation) is str and args.operation in dict(OPERATIONS), "unknown selected operation")
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
        prepared_raw, prepared = read_report(checkpoint / "report.json", tools)
        config["declaration"] = checkpoint_declaration(prepared,
            **{key: config[key] for key in ("driver_sha256", "python_identity", "git_identity", "recovered_provenance")})
        config["operation"] = args.operation
        config["measurement_binding"] = measurement_binding(prepared_raw, config["declaration"], config)
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
    report.update(report_role="checkpoint_preparation" if args.command == "prepare" else "measured_operation_pair",
                  operation=config.get("operation"), operation_catalog=operation_catalog(),
                  measurement_binding=config.get("measurement_binding"),
                  operation_set=operation_set({args.operation: report["status"]} if args.command == "measure" else {}))
    raw = canonical(report) + b"\n"
    if len(raw) > MAX_REPORT_BYTES and result is not None:
        # Keep the verified child's exact stream identities and successful exit,
        # but do not publish an incomplete/truncated evidence projection.
        result = None
        report.update(status="diagnostic_publication_refused", result=None)
        report["operation_set"] = operation_set({args.operation: report["status"]} if args.command == "measure" else {})
        raw = canonical(report) + b"\n"
    require(len(raw) <= MAX_REPORT_BYTES, "publication exceeds complete report bound")
    save_new(output / "report.json", raw)
    if result is None:
        # Diagnostic text remains local; it is never an input or success flag.
        save_new(output / "refusal.stderr", stderr[:1024 * 1024])
    return 0 if result is not None else 1


def collect_reports(checkpoint, reports, output):
    """Read selected local artifacts only; never load/re-execute their original paths."""
    require_isolation()
    tools = utility()
    checkpoint, output = Path(checkpoint).absolute(), Path(output).absolute()
    require(checkpoint.resolve(strict=True) == checkpoint, "checkpoint path contains a symlink")
    require(output.resolve() == output and not output.exists() and output.parent.is_dir(),
            "output must be a new physical directory below an existing parent")
    paths = [Path(path).absolute() for path in reports]
    require(len(paths) <= len(OPERATIONS), "too many selected operation reports")
    for protected in (checkpoint, Path(__file__).resolve(), *paths):
        require(not output.is_relative_to(protected) and not protected.is_relative_to(output), "collection output overlaps input")
    driver_raw = tools.read_file(Path(__file__).resolve())
    prepared_raw, prepared = read_report(checkpoint / "report.json", tools)
    result = prepared.get("result")
    require(type(result) is dict and type(result.get("git")) is dict, "preparation result identity is missing")
    selected = {"driver_sha256": sha(driver_raw), "python_identity": prepared.get("python_identity"),
                "git_identity": result["git"].get("identity"), "recovered_provenance": result.get("recovered_provenance")}
    declaration = checkpoint_declaration(prepared, **selected)
    require(type(selected["recovered_provenance"]) is dict
            and selected["recovered_provenance"].get("source_commit") == SOURCE_COMMIT, "prepared recovered source differs")
    inventory = tree_manifest(checkpoint / "case", read=tools.read_file)
    require(canonical(inventory) == canonical(declaration["case_inventory"]), "current checkpoint differs from preparation")
    binding = measurement_binding(prepared_raw, declaration, selected)
    rows, statuses, retained = [], {}, []
    for path in paths:
        raw, report = read_report(path, tools)
        require(set(report) == PARENT_REPORT_FIELDS, "operation parent report shape differs")
        require(report.get("format") == FORMAT and report.get("mode") == "measure"
                and report.get("report_role") == "measured_operation_pair", "input is not an operation report")
        require(report["scope"] == SCOPE and canonical(report["limitations"]) == canonical(LIMITATIONS),
                "operation scope or limitations differ")
        operation = report.get("operation")
        require(type(operation) is str and operation in dict(OPERATIONS), "report selects another operation")
        require(operation not in statuses, "duplicate selected operation report")
        require(canonical(report.get("measurement_binding")) == canonical(binding), "operation report has another measurement binding")
        require(canonical(report.get("operation_catalog")) == canonical(operation_catalog()), "operation catalog differs")
        require(report.get("driver_sha256") == binding["driver_sha256"]
                and report.get("utility_sha256") == UTILITY_SHA256
                and canonical(report.get("python_identity")) == canonical(binding["python_identity"]), "operation report identity differs")
        require(all(report.get(key) is False for key in ("scientific_eligibility", "execution_authorized",
                    "native_acceptance_evaluated", "historical_capture_complete")), "operation report changes eligibility")
        require(type(report.get("diagnostic_wall_bound_seconds")) is int and report["diagnostic_wall_bound_seconds"] == 600
                and type(report.get("declared_acceptance_deadline_seconds")) is int
                and report["declared_acceptance_deadline_seconds"] == 900, "operation report changes limits")
        require(type(report.get("parent_wall_seconds")) in (int, float) and report["parent_wall_seconds"] >= 0,
                "parent duration differs")
        for name in ("stdout", "stderr"):
            require(type(report.get(name + "_bytes")) is int and report[name + "_bytes"] >= 0
                    and is_digest(report.get(name + "_sha256")), "child stream identity differs")
        require(type(report.get("child_exit_code")) is int, "child exit code differs")
        status, child_result = report.get("status"), report.get("result")
        require(status in {"completed", "diagnostic_timeout", "diagnostic_refused", "diagnostic_publication_refused"},
                "unknown diagnostic status")
        pair = None
        if status == "completed":
            require(report["child_exit_code"] == 0 and type(child_result) is dict, "completed report lacks successful child")
            validate_child_report(child_result, {"mode": "measure", "operation": operation,
                                                 "declaration": declaration, **selected})
            require(canonical(child_result["case_inventory"]) == canonical(inventory), "operation child captured another case")
            stdout = canonical(child_result)
            require(report["stdout_sha256"] == sha(stdout) and report["stdout_bytes"] == len(stdout),
                    "completed child output pin differs")
            pair = deepcopy(child_result["operations"][0])
            validate_pair(pair, operation)
        else:
            require(child_result is None, "failed diagnostic claims completed results")
            if status == "diagnostic_refused":
                require(report["child_exit_code"] != 0, "refused diagnostic has successful child")
            if status == "diagnostic_publication_refused":
                require(report["child_exit_code"] == 0, "publication refusal lacks successful child")
        statuses[operation] = status
        require(canonical(report.get("operation_set")) == canonical(operation_set({operation: status})),
                "saved operation denominator differs")
        rows.append({"operation": operation, "report": {"sha256": sha(raw), "bytes": len(raw)}, "status": status,
                     "pair": pair, "parent_wall_seconds": report["parent_wall_seconds"],
                     "loaded_closure": {"sha256": sha(canonical(child_result["loaded_closure"])),
                                        "entries": len(child_result["loaded_closure"])} if pair else None,
                     "checkpoint_verification": deepcopy(child_result["checkpoint_verification"]) if pair else None,
                     "phase_overhead": deepcopy(child_result["phase_overhead"]) if pair else None})
        retained.append((path, raw))
    denominator = operation_set(statuses)
    rows.sort(key=lambda row: [name for name, _ in OPERATIONS].index(row["operation"]))
    collected = {"format": COLLECTION_FORMAT, "report_role": "operation_collection", "scope": SCOPE,
        "status": "complete" if denominator["complete"] else "incomplete", "operation_catalog": operation_catalog(),
        "measurement_binding": binding, "operation_set": denominator, "reports": rows,
        "scientific_eligibility": False, "execution_authorized": False, "native_acceptance_evaluated": False,
        "historical_capture_complete": False, "limitations": list(LIMITATIONS) +
        ["Collection verifies current selected case/report bytes and their declarations; it does not authenticate past execution or reopen historical source/runtime paths."]}
    raw = canonical(collected) + b"\n"
    require(len(raw) <= MAX_REPORT_BYTES, "publication exceeds complete report bound")
    require(tools.read_file(Path(__file__).resolve()) == driver_raw, "collector driver changed")
    require(tools.read_file(checkpoint / "report.json") == prepared_raw, "preparation report changed during collection")
    require(canonical(tree_manifest(checkpoint / "case", read=tools.read_file)) == canonical(inventory),
            "checkpoint changed during collection")
    for path, before in retained:
        require(tools.read_file(path) == before, "operation report changed during collection")
    output.mkdir()
    save_new(output / "report.json", raw)
    return collected


def main(argv=None):
    if (sys.argv[1:] if argv is None else argv) == ["_child"]:
        require_isolation()
        raw = sys.stdin.buffer.read(MAX_REPORT_BYTES + 1)
        require(len(raw) <= MAX_REPORT_BYTES, "child configuration exceeds report bound")
        config = utility().strict_json(raw)
        result = child(config)
        encoded = canonical(result)
        require(len(encoded) <= MAX_REPORT_BYTES, "child publication exceeds complete report bound")
        sys.stdout.buffer.write(encoded)
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "measure"):
        command = commands.add_parser(name)
        for key in ("source", "recovery", "dependencies", "output"):
            command.add_argument("--" + key, required=True)
        if name == "measure":
            command.add_argument("--checkpoint", required=True)
            command.add_argument("--operation", choices=[name for name, _ in OPERATIONS], required=True)
    collect = commands.add_parser("collect")
    collect.add_argument("--checkpoint", required=True)
    collect.add_argument("--reports", nargs="*", default=[])
    collect.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.command == "collect":
        result = collect_reports(args.checkpoint, args.reports, args.output)
        return 0 if result["operation_set"]["complete"] else 1
    return dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())
