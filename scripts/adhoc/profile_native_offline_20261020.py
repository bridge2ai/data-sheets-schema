"""Profile existing offline native acceptance tests for #4354/#4728 (2026-10-20).

Inputs: an explicitly allowlisted pytest node and this checkout's source.
Outputs: cProfile data, sorted statistics and CPU/wall/load metadata in a fresh
external evidence directory. Profiling timings are diagnostic, not acceptance.
No provider, native binary or test implementation is substituted by this helper.
"""
from __future__ import annotations

import argparse
from collections import Counter
import cProfile
import hashlib
import json
import os
from pathlib import Path
import pstats
import resource
import subprocess
import sys
import threading
import time


# Inert prototype for the explicitly selected origin_resolution benchmark.
# Exact candidate module bytes, retained here for provenance while production
# src/ and its registered dependency identities remain frozen (2026-10-20).
ORIGIN_RESOLUTION_PROTOTYPE = r'''"""Fresh resolution for exact fixed owner-origin spellings only.

No path result is cached. Every call retains its physical observation, and
ordinary Python resolution remains the fallback for aliases and returned
native lookup failures. Python/FFI exceptions propagate after owned cleanup.
"""
from functools import lru_cache
import os
from pathlib import Path
import sys


_PYTHON_RESOLVE = Path.resolve
_CONCRETE_PATH = type(Path())
_CONCRETE_RESOLVE = _CONCRETE_PATH.resolve
_PYTHON_REALPATH = os.path.realpath
_PYTHON_LSTAT = os.lstat
_PYTHON_READLINK = os.readlink


@lru_cache(maxsize=1)
def _native_functions():
    """Retain only libc functions, never an origin, path or authority result."""
    if os.name != 'posix' or sys.platform not in ('darwin', 'linux'):
        return None
    try:
        import ctypes
        library = ctypes.CDLL(
            '/usr/lib/libSystem.B.dylib' if sys.platform == 'darwin' else None,
            use_errno=True)
        resolve, free = library.realpath, library.free
        resolve.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
        resolve.restype = ctypes.c_void_p
        free.argtypes = [ctypes.c_void_p]
        free.restype = None
        return library, resolve, free
    except (ImportError, AttributeError, OSError):
        return None


def _matches_native_spelling(raw):
    functions = _native_functions()
    if functions is None:
        return False
    import ctypes
    _, resolve, free = functions
    pointer = resolve(raw, None)
    if not pointer:
        return False
    try:
        # realpath(NULL) owns a NUL-terminated allocation. Read it before the
        # corresponding libc free, including on read/comparison failure.
        return ctypes.string_at(pointer) == raw
    finally:
        free(pointer)


def resolve_fixed_origin(source, expected):
    """Resolve once, fast only when the fresh result is the fixed spelling.

    Callers retain their original number/order of calls: qualified origins
    resolve BOTH the actual and expected paths; a bare origin resolves the
    actual path against its retained loader spelling. This is not a verdict.
    """
    eligible = (
        type(source) is str and type(expected) is str and source == expected
        and source.startswith('/') and not source.startswith('//')
        and '\0' not in source and str(Path(source)) == source
        and Path.resolve is _PYTHON_RESOLVE
        and _CONCRETE_PATH.resolve is _CONCRETE_RESOLVE
        and os.path.realpath is _PYTHON_REALPATH
        and os.lstat is _PYTHON_LSTAT and os.readlink is _PYTHON_READLINK)
    if eligible:
        try:
            raw = os.fsencode(source)
        except (UnicodeError, ValueError):
            pass
        else:
            if _matches_native_spelling(raw):
                return Path(source)
    # Preserve Python's strict=False behavior for missing paths, symlink
    # loops, unsupported platforms, spelling changes and returned failures.
    return Path(source).resolve()
'''


NODES = {
    "phase": "tests/test_native_shared_phase_replay.py::test_actual_phase_matches_original_with_fewer_real_reconstructions",
    "initial": "tests/test_native_shared_initial_receipts.py::test_initial_success_uses_only_captured_authority_and_has_no_final_claim",
    "neutral": "tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion",
    "omission": "tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses",
    "owner_stage": "tests/test_native_owner_stage_helper.py::test_registered_helper_process_publishes_first_receipt_stage_with_real_clock",
    "owner_receipt": "tests/test_native_owner_receipt_process.py::test_registered_receipt_process_reads_current_inputs_with_real_clock",
}


class ThreadSamples:
    """Bounded diagnostic stacks from real owner/observer threads (2026-10-20).

    Inputs are Python frame identities only; no locals, arguments or data bytes
    are captured. Sampling never substitutes the registered clock or deadline.
    """
    def __init__(self):
        self.stop = threading.Event()
        self.counts = Counter()
        self.samples = self.dropped = 0
        self.thread = threading.Thread(target=self._sample, name="native-diagnostic-sampler",
                                       daemon=True)

    def _sample(self):
        while not self.stop.wait(0.02):
            names = {thread.ident: thread.name for thread in threading.enumerate()}
            for ident, frame in sys._current_frames().items():
                if ident == self.thread.ident:
                    continue
                stack = []
                while frame is not None and len(stack) < 80:
                    stack.append((frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name))
                    frame = frame.f_back
                key = (names.get(ident, "unlisted-thread"), tuple(stack))
                if self.samples >= 50000 or (key not in self.counts and len(self.counts) >= 5000):
                    self.dropped += 1
                    continue
                self.counts[key] += 1
                self.samples += 1

    def finish(self, output):
        self.stop.set()
        self.thread.join(2)
        if self.thread.is_alive():
            raise RuntimeError("diagnostic sampler did not stop")
        result = {
            "interval_seconds": 0.02, "samples": self.samples, "dropped": self.dropped,
            "scope": "Diagnostic Python thread stacks; not acceptance timing or subprocess profiling.",
            "stacks": [{"thread": thread, "count": count,
                        "frames_leaf_first": [{"path": path, "line": line, "function": function}
                                              for path, line, function in stack]}
                       for (thread, stack), count in self.counts.most_common()],
        }
        (output / "thread-samples.json").write_text(json.dumps(result, indent=2) + "\n")
        self.write_summary(output, result)

    @staticmethod
    def write_summary(output, result):
        leaf, inclusive = Counter(), Counter()
        for row in result["stacks"]:
            thread = row["thread"]
            if thread.startswith("Thread-") and "(" in thread:
                thread = thread[thread.index("("):]
            count = row["count"]
            stack = [(frame["path"], frame["line"], frame["function"])
                     for frame in row["frames_leaf_first"]]
            if stack:
                path, _, function = stack[0]
                leaf[(thread, path, function)] += count
            for path, function in {(path, function) for path, _, function in stack}:
                inclusive[(thread, path, function)] += count
        with (output / "thread-summary.txt").open("w") as stream:
            stream.write("Diagnostic sample counts, not CPU or wall-time estimates.\n")
            for label, counts in (("Leaf frames", leaf), ("Inclusive frames", inclusive)):
                stream.write("\n" + label + "\n")
                for (thread, path, function), count in counts.most_common(100):
                    stream.write(f"{count:6d} {thread} {path}:{function}\n")


def source_state():
    """Bind both tracked edits and newly added source/tests in a shared lane."""
    diff = subprocess.check_output(["git", "diff", "--binary", "HEAD", "--", "src", "tests"])
    # Include ignored files: they can still be consumed by source discovery.
    names = subprocess.check_output([
        "git", "ls-files", "--others", "-z", "--", "src", "tests"
    ]).decode().split("\0")
    return {
        "tracked_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "has_tracked_changes": bool(diff),
        "untracked_sha256": {
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in names if name
        },
    }


def origin_resolution_benchmark(root, output, *, contended=False):
    """Bounded fixed-owner-origin comparison for #4354/#4728, 2026-10-20.

    Inputs: fixed current controller/profile paths and inert prototype above.
    Output: diagnostic JSON only; no pytest, native binary, provider or owner
    authorization. Cold initialization and warm batches are separate. The
    explicit contended case adds one bounded pure-Python CPU thread, retaining
    the interpreter's configured switch interval and the exact prototype.
    """
    prototype = ORIGIN_RESOLUTION_PROTOTYPE.encode('utf-8')
    started_import = time.perf_counter()
    namespace = {'__name__': '_d4d_origin_resolution_prototype'}
    exec(compile(prototype, '<retained-origin-resolution-prototype>', 'exec'), namespace)
    resolve = namespace['resolve_fixed_origin']
    imported = time.perf_counter()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    before = source_state()
    manifest = json.loads((root / 'src/data_sheets_schema/native_controller_sources_v1.json').read_bytes())
    relatives = {row['path'] for row in manifest['modules'].values()}
    relatives.update('src/data_sheets_schema/' + name + '.py' for name in (
        'native_stream_coordination_v1', 'native_owner_control_v1',
        'native_owner_runner_v1', 'native_clock_domain_v1'))
    paths = tuple(str(root / relative) for relative in sorted(relatives))
    if any(str(Path(path).resolve()) != path or not Path(path).is_file() for path in paths):
        raise ValueError('benchmark requires current exact fixed source spellings')
    first = time.perf_counter()
    if resolve(paths[0], paths[0]) != Path(paths[0]):
        raise ValueError('prototype cold call differs from fixed physical origin')
    first_seconds = time.perf_counter() - first
    available = namespace['_native_functions']() is not None
    all_paths = paths
    if contended:
        # Two paths from each end of the fixed roster, identical in every
        # batch. This bounds competing-GIL work without changing resolution.
        paths = tuple(dict.fromkeys((*paths[:2], *paths[-2:])))
    sweeps = 2 if contended else 100
    deadline = time.monotonic() + (7 if contended else 30)
    load_before = os.getloadavg()
    rows = []
    stop, ready = threading.Event(), threading.Event()
    competitor_result = {}

    def compete():
        """Pure Python arithmetic; bounded even if the parent exits early."""
        started = time.thread_time()
        value = rounds = 0
        ready.set()
        try:
            while not stop.is_set() and time.monotonic() < deadline:
                for index in range(1024):
                    value = (value * 33 + index) & 0xffff
                rounds += 1
        finally:
            competitor_result.update(rounds=rounds, checksum=value,
                                     thread_cpu_seconds=time.thread_time() - started)

    competitor = (threading.Thread(target=compete, name='origin-gil-competitor',
                                   daemon=True) if contended else None)
    error = None
    benchmark_started = time.perf_counter()
    try:
        if competitor is not None:
            competitor.start()
            if not ready.wait(1):
                raise TimeoutError('origin contention thread did not become ready')
        for name in ('python', 'native', 'native', 'python'):
            wall, cpu, thread_cpu = time.perf_counter(), time.process_time(), time.thread_time()
            calls = 0
            row = {'implementation': name, 'expected_physical_resolution_calls': 2 * len(paths) * sweeps,
                   'complete': False}
            try:
                for _ in range(sweeps):
                    for path in paths:
                        if time.monotonic() >= deadline:
                            raise TimeoutError('bounded origin benchmark exceeded its deadline')
                        if name == 'python':
                            # Preserve the two fresh qualified-origin observations.
                            actual, expected = Path(path).resolve(), Path(path).resolve()
                        else:
                            actual, expected = resolve(path, path), resolve(path, path)
                        calls += 2
                        if actual != expected or actual != Path(path):
                            raise ValueError('fixed physical origin changed during benchmark')
                row['complete'] = True
            finally:
                row.update(physical_resolution_calls=calls,
                           wall_seconds=time.perf_counter() - wall,
                           cpu_seconds=time.process_time() - cpu,
                           calling_thread_cpu_seconds=time.thread_time() - thread_cpu)
                rows.append(row)
    except Exception as caught:
        error = {'type': type(caught).__name__, 'message': str(caught)}
    finally:
        stop.set()
        if competitor is not None:
            competitor.join(1)
    competitor_stopped = competitor is None or not competitor.is_alive()
    if not competitor_stopped and error is None:
        error = {'type': 'RuntimeError', 'message': 'origin contention thread did not stop'}
    benchmark_seconds = time.perf_counter() - benchmark_started
    after = source_state()
    case = 'origin_resolution_contended' if contended else 'origin_resolution'
    result = {
        'case': case, 'head': head, 'paths': paths, 'fixed_path_roster': all_paths,
        'prototype_sha256': hashlib.sha256(prototype).hexdigest(),
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_before': before, 'source_after': after,
        'source_unchanged': before == after, 'python': sys.version,
        'native_available': available,
        'cold_module_initialization_seconds': imported - started_import,
        'cold_first_call_seconds': first_seconds, 'warm_batches': rows,
        'load_before': load_before, 'load_after': os.getloadavg(),
        'benchmark_seconds_including_cleanup': benchmark_seconds,
        'error': error,
        'contention': {'enabled': contended, 'threads': int(contended),
                       'switch_interval_seconds': sys.getswitchinterval(),
                       'thread_stopped': competitor_stopped, **competitor_result},
        'scope': 'Isolated prototype diagnostic; no owner-gate or acceptance claim.',
    }
    (output / (case.replace('_', '-') + '.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    return 0 if before == after and error is None and competitor_stopped else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=(*NODES, 'origin_resolution', 'origin_resolution_contended'))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample-threads", action="store_true",
                        help="Sample Python stacks instead of cProfile; preserves owner-thread execution.")
    parser.add_argument("--summarize-existing", action="store_true",
                        help="Rebuild only a saved thread-summary.txt; do not run tests.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if Path.cwd().resolve() != root:
        parser.error("run from this helper's checkout root")
    output = args.output.resolve()
    if output == root or root in output.parents:
        parser.error("evidence output must be outside the checkout")
    if args.summarize_existing:
        ThreadSamples.write_summary(output, json.loads((output / "thread-samples.json").read_text()))
        return 0
    output.mkdir(parents=True, exist_ok=False)
    if args.case in ('origin_resolution', 'origin_resolution_contended'):
        if args.sample_threads:
            parser.error('origin-resolution comparison does not run a sampler')
        return origin_resolution_benchmark(
            root, output, contended=args.case == 'origin_resolution_contended')
    import data_sheets_schema.native_shared_capture as capture
    if root / "src" not in Path(capture.__file__).resolve().parents:
        parser.error("native source imported from another checkout")
    import pytest
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    source_before = source_state()
    before = [resource.getrusage(kind) for kind in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
    load_before = os.getloadavg()
    started = time.perf_counter()
    profile = cProfile.Profile()
    sampler = ThreadSamples() if args.sample_threads else None
    if sampler is None:
        profile.enable()
    else:
        sampler.thread.start()
    try:
        code = pytest.main(["-q", "-p", "no:cacheprovider",
                            "--basetemp", str(output / "cases"), NODES[args.case]])
    finally:
        if sampler is None:
            profile.disable()
        else:
            sampler.finish(output)
        elapsed = time.perf_counter() - started
        after = [resource.getrusage(kind) for kind in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
        if sampler is None:
            profile.dump_stats(output / "profile.pstats")
            with (output / "profile.txt").open("w") as stream:
                pstats.Stats(profile, stream=stream).sort_stats("cumulative").print_stats(100)
        cpu = [b.ru_utime + b.ru_stime - a.ru_utime - a.ru_stime
               for a, b in zip(before, after)]
        source_after = source_state()
        summary = {
            "case": args.case, "node": NODES[args.case], "head": head,
            "source_before": source_before, "source_after": source_after,
            "source_unchanged": source_before == source_after,
            "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "wall_seconds": elapsed,
            "cpu_self_seconds": cpu[0], "cpu_child_seconds": cpu[1],
            "load_before": load_before, "load_after": os.getloadavg(),
            "python": sys.version, "pytest_rc": int(code) if "code" in locals() else None,
            "timing_scope": ("Thread-sampled diagnostic pytest process; not acceptance timing."
                             if sampler is not None else
                             "cProfile-instrumented parent pytest process; child CPU included separately"),
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary), flush=True)
    return int(code) if source_before == source_after else 2


if __name__ == "__main__":
    raise SystemExit(main())
