"""Opt-in macOS keep-awake registration and launcher (#2445).

Preparation is offline. Launch still requires the unchanged direct launcher's
registration, review, CI and launch-word checks; no historical file is edited.
"""
from __future__ import annotations

import argparse
import copy
import ctypes
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
POLICY = "macos_iokit_ims_v1"
ASSERTIONS = ("PreventUserIdleSystemSleep", "PreventDiskIdle", "PreventSystemSleep")
LIMITATIONS = ("API acquisition is observed, not proof that the host never slept; "
               "PreventSystemSleep applies on AC power; forced sleep, lid closure, "
               "thermal/battery policy and power loss are not prevented")


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"duplicate registration key: {key}")
            out[key] = value
        return out
    value = json.loads(Path(path).read_bytes(), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("registration must be an object")
    return value


def overlay(source_path):
    source_path = Path(source_path).resolve(strict=True)
    source = load(source_path)
    if (source.get("kind") != "d4d_direct_arm_registration" or source.get("schema_version") != 1
            or "keep_awake_launcher" in source):
        raise ValueError("requires an original direct-arm registration without a keep-awake overlay")
    if Path(source["repository"]).resolve() != ROOT:
        raise ValueError("registration belongs to another checkout")
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=10).strip()
    if source.get("code_commit") != current:
        raise ValueError("prepare a fresh registration on the current code commit")
    for job in source["generation"]["jobs"]:
        if (source_path.parent / "attempts" / job["id"]).exists():
            raise ValueError("an attempt identity is consumed; register afresh")
    script = str(Path(__file__).resolve())
    source["pinned_files"][script] = sha(script)
    source["keep_awake_launcher"] = {
        "policy": POLICY, "source_registration": str(source_path),
        "source_registration_sha256": sha(source_path), "script": script,
    }
    return source


def prepare(source, output):
    source, output = Path(source).resolve(strict=True), Path(output).absolute()
    if output.parent.resolve() != source.parent:
        raise ValueError("keep the new registration beside its original to preserve attempt identity")
    value = overlay(source)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")
    return output


class _IOKit:
    """The public assertion API used by caffeinate, with checked return values.

    See Apple's IOKitUser/pwr_mgt.subproj/IOPMLib.h and PowerManagement/caffeinate.
    No native library is loaded on unsupported hosts or during preparation.
    """
    def __init__(self):
        if sys.platform != "darwin":
            raise RuntimeError("this keep-awake policy requires macOS; no launch was attempted")
        self.cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        self.io = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
        self.cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        self.cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        self.cf.CFRelease.argtypes = [ctypes.c_void_p]
        self.cf.CFRelease.restype = None
        self.io.IOPMAssertionCreateWithName.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                                        ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        self.io.IOPMAssertionCreateWithName.restype = ctypes.c_int32
        self.io.IOPMAssertionRelease.argtypes = [ctypes.c_uint32]
        self.io.IOPMAssertionRelease.restype = ctypes.c_int32

    def create(self, kind):
        refs = []
        try:
            for text in (kind, "D4D registered direct launch"):
                value = self.cf.CFStringCreateWithCString(None, text.encode(), 0x08000100)  # UTF-8
                if not value:
                    raise RuntimeError("could not allocate the keep-awake assertion name")
                refs.append(value)
            identifier = ctypes.c_uint32()
            result = self.io.IOPMAssertionCreateWithName(refs[0], 255, refs[1], ctypes.byref(identifier))
            if result != 0 or identifier.value == 0:
                raise RuntimeError(f"keep-awake acquisition failed for {kind}: IOReturn {result}")
            return identifier.value
        finally:
            for value in reversed(refs):
                self.cf.CFRelease(value)

    def release(self, identifier):
        return self.io.IOPMAssertionRelease(identifier)


class KeepAwake:
    def __init__(self, api=None):
        self.api = _IOKit() if api is None else api
        self.active = []
        self.releases = []
        self.acquired_at = None
        self.released_at = None

    def __enter__(self):
        try:
            for kind in ASSERTIONS:
                self.active.append({"type": kind, "id": self.api.create(kind)})
            self.acquired_at = now()
            return self
        except BaseException:
            self.close()
            raise

    def snapshot(self):
        return {"policy": POLICY, "pid": os.getpid(), "acquired_at": self.acquired_at,
                "status": "acquired" if len(self.active) == len(ASSERTIONS) else "not_held",
                "assertions": copy.deepcopy(self.active), "limitations": LIMITATIONS,
                "cleanup_receipt": "keep_awake_cleanup.json"}

    def close(self):
        for item in reversed(self.active):
            try:
                outcome = {"return_code": self.api.release(item["id"])}
            except BaseException as error:
                outcome = {"error_type": type(error).__name__}
            self.releases.append({**item, **outcome})
        self.active.clear()
        self.released_at = now()

    def __exit__(self, *_):
        self.close()


class LaunchSignal(KeyboardInterrupt):
    pass


def load_legacy():
    # A private module instance keeps the receipt adapter out of other callers.
    spec = importlib.util.spec_from_file_location("_d4d_awake_legacy", HERE / "run_direct_canary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def launch(args):
    path = Path(args.registration).resolve(strict=True)
    registration = load(path)
    policy = registration.get("keep_awake_launcher")
    if not isinstance(policy, dict) or policy.get("policy") != POLICY:
        raise ValueError("prepare and independently review the keep-awake registration first")
    source = Path(policy["source_registration"]).resolve(strict=True)
    if path.parent != source.parent or registration != overlay(source):
        raise ValueError("keep-awake registration or its original inputs/pins changed")
    # overlay() rechecks unused identities; legacy main repeats its own checks.
    signals = []
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    old_path = sys.path[:]
    guard = KeepAwake()
    attempt = path.parent / "attempts" / args.job
    wrote_started = False
    legacy = None
    writer = None

    def interrupt(signum, _frame):
        signals.append(signum)
        if len(signals) == 1:
            raise LaunchSignal(f"launcher received signal {signum}")
        # Repeated signals must not interrupt the native child's cleanup.

    try:
        for sig in previous:
            signal.signal(sig, interrupt)
        with guard:
            sys.path.insert(0, str(HERE))
            legacy = load_legacy()
            writer = legacy.write_new

            def receipt_writer(target, value):
                nonlocal wrote_started
                if Path(target) in (attempt / "started.json", attempt / "result.json"):
                    value["keep_awake"] = {**guard.snapshot(), "signals_received": list(signals)}
                writer(target, value)
                if Path(target) == attempt / "started.json":
                    wrote_started = True

            legacy.write_new = receipt_writer
            code = legacy.main(["--registration", str(path), "--review", str(args.review),
                                "--launch-word", str(args.launch_word), "--job", args.job])
        return 128 + signals[0] if signals else code
    except LaunchSignal:
        return 128 + signals[0]
    finally:
        if legacy is not None:
            legacy.write_new = writer
        sys.path[:] = old_path
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        failed_release = any(row.get("return_code") != 0 for row in guard.releases)
        if wrote_started:
            writer(attempt / "keep_awake_cleanup.json", {
                "policy": POLICY, "registration_sha256": sha(path), "pid": os.getpid(),
                "released_at": guard.released_at, "releases": guard.releases,
                "status": "release_failed" if failed_release else "released",
                "signals_received": signals,
            })
        if failed_release:
            raise RuntimeError("keep-awake release failed; inspect the cleanup receipt; process exit releases assertions")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    offline = commands.add_parser("prepare", help="write a fresh opt-in registration; no launch or login probe")
    offline.add_argument("--registration", type=Path, required=True)
    offline.add_argument("--out", type=Path, required=True)
    run = commands.add_parser("launch", help="run one already authorized fresh direct canary on macOS")
    for name in ("registration", "review", "launch-word"):
        run.add_argument("--" + name, type=Path, required=True)
    run.add_argument("--job", required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        prepare(args.registration, args.out)
        return 0
    return launch(args)


if __name__ == "__main__":
    raise SystemExit(main())
