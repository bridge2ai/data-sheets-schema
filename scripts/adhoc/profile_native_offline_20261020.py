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
    names = subprocess.check_output([
        "git", "ls-files", "--others", "--exclude-standard", "-z", "--", "src", "tests"
    ]).decode().split("\0")
    return {
        "tracked_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "has_tracked_changes": bool(diff),
        "untracked_sha256": {
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in names if name
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=NODES)
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
