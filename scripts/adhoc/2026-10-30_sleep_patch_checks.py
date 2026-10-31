"""Run offline sleep-patch checks and retain timings/optional wait stacks.

Inputs: interpreter, pytest arguments and local checkout. Outputs: logs, JUnit,
environment identity and wall times under test-results/sleep-patch/. Serves
main's red CI run 41092033720; 2026-10-30. No provider keys or remote access.
"""
import argparse
from collections import Counter
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "test-results" / "sleep-patch"
# Native permission fixtures require probes outside the source checkout. The
# task explicitly places pytest basetemps under d4d-executions/.
TEMPORARIES = ROOT.parent / "plans" / "codex_logs" / "sleep-patch-20261030"


def child(args):
    if args.trace_waits:
        original = subprocess.Popen.wait
        counts = Counter()
        stacks = {}

        def wait(process, timeout=None):
            if timeout is not None:
                stack = "".join(traceback.format_stack(limit=16))
                key = str(process.args)
                counts[key] += 1
                stacks.setdefault(key, stack)
            return original(process, timeout=timeout)

        subprocess.Popen.wait = wait
    import pytest
    try:
        return pytest.main(args.pytest_args)
    finally:
        if args.trace_waits:
            (RESULTS / args.label / "waits.json").write_text(json.dumps(
                {key: {"count": count, "stack": stacks[key]} for key, count in counts.items()},
                indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("--trace-waits", action="store_true")
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--baseline-ref", help="Temporarily measure this local ref in the same checkout")
    parser.add_argument("--power-history-date", help="Save this day's macOS sleep/wake events instead of running pytest")
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.pytest_args[:1] == ["--"]:
        args.pytest_args.pop(0)
    if args.power_history_date:
        if args.pytest_args or args.baseline_ref or args.trace_waits or args.child:
            parser.error("power-history capture cannot be combined with a test run")
        output = RESULTS / args.label
        output.mkdir(parents=True, exist_ok=False)
        history = subprocess.check_output(["/usr/bin/pmset", "-g", "log"], text=True)
        events = [line for line in history.splitlines()
                  if line.startswith(args.power_history_date + " ")
                  and any(kind in line for kind in ("Entering Sleep", "Wake from", "DarkWake from"))]
        path = output / "sleep-events.log"
        path.write_text("\n".join(events) + "\n")
        print(f"Saved {len(events)} sleep/wake events to {path}")
        return 0
    if args.child:
        return child(args)
    if args.trace_waits and args.baseline_ref:
        parser.error("baseline runs use pytest directly, without trace instrumentation")
    original_branch = None
    if args.baseline_ref:
        subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=ROOT, check=True)
        original_branch = subprocess.check_output(
            ["git", "symbolic-ref", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        subprocess.run(["git", "switch", "--detach", args.baseline_ref], cwd=ROOT, check=True)
    try:
        return measure(args)
    finally:
        if original_branch is not None:
            subprocess.run(["git", "switch", original_branch], cwd=ROOT, check=True)


def measure(args):
    output = RESULTS / args.label
    output.mkdir(parents=True, exist_ok=False)
    temporary = TEMPORARIES / args.label / "tmp"
    temporary.mkdir(parents=True, exist_ok=False)
    environment = {key: value for key, value in os.environ.items()
                   if not any(word in key.upper() for word in ("API_KEY", "AUTH_TOKEN", "ACCESS_TOKEN"))
                   and key not in ("PYTEST_ADDOPTS", "D4D_INSTALL_TESTS")}
    environment.update(PYTHONPATH=os.pathsep.join(map(str, (ROOT / "src", ROOT, ROOT / "fairscape_models"))),
                       PYTHONPYCACHEPREFIX=str(RESULTS / "pycache"), TMPDIR=str(temporary),
                       MPLCONFIGDIR=str(RESULTS / "matplotlib"), XDG_CACHE_HOME=str(RESULTS / "cache"),
                       GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0", GIT_ALLOW_PROTOCOL="file",
                       PIP_NO_INDEX="1", UV_OFFLINE="1")
    pytest_args = [*args.pytest_args, "-p", "no:cacheprovider", "--durations=0",
                   f"--basetemp={temporary.parent / 'basetemp'}", f"--junitxml={output / 'pytest.xml'}"]
    # Allow local process/socket tests while denying external network connections.
    profile = '(version 1)(allow default)(deny network-outbound)(allow network-outbound (remote ip "localhost:*"))'
    # Keep the Mac awake only for this subprocess. An idle-sleep interruption
    # affected the follow-up comparison's wall clock, so record both clocks too.
    command = ["/usr/bin/caffeinate", "-is", "/usr/bin/sandbox-exec", "-p", profile, sys.executable]
    if args.trace_waits:
        command.extend([str(Path(__file__).resolve()), "--child", "--trace-waits", args.label, "--", *pytest_args])
    else:
        # This also works when measuring main, where this branch's helper file
        # is absent. The already-running parent retains its code in memory.
        command.extend(["-m", "pytest", *pytest_args])
    packages = sorted(f"{d.metadata['Name']}=={d.version}" for d in metadata.distributions())
    (output / "packages.txt").write_text("\n".join(packages) + "\n")
    identity = {"python": sys.version, "executable": sys.executable,
                "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "poetry_lock_sha256": hashlib.sha256((ROOT / "poetry.lock").read_bytes()).hexdigest(),
                "packages_sha256": hashlib.sha256((output / "packages.txt").read_bytes()).hexdigest(),
                "pytest_args": pytest_args, "load_before": os.getloadavg(),
                "wake_assertion": "caffeinate -is",
                "elapsed_clock": time.get_clock_info("monotonic").implementation}
    for argument in pytest_args:
        if argument.startswith("--ci-shard-timings="):
            raw = (ROOT / argument.split("=", 1)[1]).read_bytes()
            (output / "ci_test_durations.input.json").write_bytes(raw)
            identity["ci_test_durations_sha256"] = hashlib.sha256(raw).hexdigest()
    print(f"Starting {args.label}; output: {output}", flush=True)
    started_clock = time.time()
    started = time.monotonic()
    with (output / "pytest.log").open("w") as log:
        result = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
    elapsed = time.monotonic() - started
    finished_clock = time.time()
    identity.update(wall_seconds=elapsed, clock_wall_seconds=finished_clock - started_clock,
                    started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started_clock)),
                    finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(finished_clock)),
                    exit_code=result.returncode,
                    load_after=os.getloadavg())
    (output / "measurement.json").write_text(json.dumps(identity, indent=2) + "\n")
    print(json.dumps({key: identity[key] for key in ("wall_seconds", "clock_wall_seconds", "exit_code")}), flush=True)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
