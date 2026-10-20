"""Fail-closed saved subscription admission and live event guard (#2370).

No account lookup, executable or provider call occurs here. Saved observations
are caller-supplied evidence, not authenticated quota readings or authorization.
The separately reviewed one-attempt launch word remains mandatory.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import stat

KIND = "d4d_native_subscription_guard"
VERSION = 1
MAX_BYTES = 65536
MAX_AGE_SECONDS = 300
KEYS = {
    "kind", "version", "registration_sha256", "runtime_sha256",
    "launch_word_sha256", "max_starting_weekly_utilization", "max_age_seconds",
    "captured_at", "event_json", "event_sha256",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("subscription evidence has duplicate JSON keys")
            out[key] = value
        return out
    def bad_constant(value):
        raise ValueError("subscription evidence has nonfinite JSON numbers")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError("subscription evidence is not bounded JSON") from exc


def read_regular(path, *, limit=MAX_BYTES):
    """Read one resolved, bounded regular file without following a final link."""
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("subscription evidence requires a resolved absolute file")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= limit:
            raise ValueError("subscription evidence is not a bounded regular file")
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    current = path.stat(follow_symlinks=False)
    if (len(raw) > limit or any(getattr(before, k) != getattr(after, k) for k in fields)
            or any(getattr(after, k) != getattr(current, k) for k in fields)):
        raise ValueError("subscription evidence changed during capture")
    return raw


def _fraction(value, label):
    if type(value) not in (int, float) or not 0 <= value <= 1 or not math.isfinite(value):
        raise ValueError(label + " must be a finite fraction in [0, 1]")
    return value


def _timestamp(value):
    if type(value) is not str or not value.endswith("Z") or len(value) > 40:
        raise ValueError("captured_at must be an explicit UTC timestamp ending Z")
    try:
        result = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("captured_at is not a UTC timestamp") from exc
    if result.utcoffset() is None or result.utcoffset().total_seconds() != 0:
        raise ValueError("captured_at is not UTC")
    return result.timestamp()


def _now():
    return datetime.now(timezone.utc).timestamp()


def weekly_reading(event, *, require_weekly=True):
    """Accept only explicit safe native rate-limit observations.

    Top-level and unified weekly aliases, when both supplied, must agree.
    An unknown status or absent overage flag is not inferred to be safe.
    """
    if type(event) is not dict or event.get("type") != "rate_limit_event":
        raise ValueError("subscription guard requires a native rate_limit_event")
    info = event.get("rate_limit_info")
    if type(info) is not dict or info.get("isUsingOverage") is not False:
        raise ValueError("subscription overage must be explicitly false")
    if info.get("status") not in ("allowed", "allowed_warning"):
        raise ValueError("subscription status is rejected or unknown")
    rows = []
    if info.get("rateLimitType") == "seven_day":
        rows.append(info)
    windows = info.get("unifiedWindows", {})
    if type(windows) is not dict:
        raise ValueError("subscription windows are malformed")
    if "seven_day" in windows:
        rows.append(windows["seven_day"])
    if not rows:
        if require_weekly:
            raise ValueError("subscription evidence has no seven_day window")
        return None
    values = []
    for row in rows:
        if type(row) is not dict:
            raise ValueError("subscription weekly window is malformed")
        utilization = _fraction(row.get("utilization"), "weekly utilization")
        reset = row.get("resetsAt")
        if type(reset) is not int or reset <= 0:
            raise ValueError("subscription weekly reset must be a positive epoch")
        if "isUsingOverage" in row and row["isUsingOverage"] is not False:
            raise ValueError("weekly window contradicts safe overage status")
        if "status" in row and row["status"] not in ("allowed", "allowed_warning"):
            raise ValueError("weekly window contradicts safe status")
        values.append((utilization, reset))
    if len(set(values)) != 1:
        raise ValueError("subscription weekly aliases conflict")
    return {"utilization": values[0][0], "resets_at": values[0][1]}


class SubscriptionGuard:
    """Immutable launch-bound observation, checked again at actual dispatch."""

    def __init__(self, raw, *, expected_sha256, registration_raw, runtime,
                 launch_word_raw, clock=None, check_freshness=True):
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES or sha(raw) != expected_sha256:
            raise ValueError("subscription guard bytes differ from selected SHA256")
        value = strict_json(raw)
        if type(value) is not dict or set(value) != KEYS:
            raise ValueError("subscription guard has missing or unknown fields")
        if value["kind"] != KIND or type(value["version"]) is not int or value["version"] != VERSION:
            raise ValueError("unsupported subscription guard protocol")
        for key, wanted in (
            ("registration_sha256", sha(registration_raw)),
            ("runtime_sha256", sha(canonical(runtime))),
            ("launch_word_sha256", sha(launch_word_raw)),
        ):
            if value[key] != wanted:
                raise ValueError("subscription guard binding differs: " + key)
        auth = runtime.get("auth")
        if (type(auth) is not dict or auth.get("loggedIn") is not True
                or auth.get("authMethod") != "claude.ai"
                or auth.get("apiProvider") != "firstParty"
                or auth.get("expected_api_key_source") != "none"):
            raise ValueError("subscription guard requires selected first-party subscription auth")
        self.maximum = _fraction(value["max_starting_weekly_utilization"], "maximum starting utilization")
        age = value["max_age_seconds"]
        if type(age) is not int or not 0 < age <= MAX_AGE_SECONDS:
            raise ValueError("subscription freshness must be 1..300 seconds")
        event_raw = value["event_json"]
        if type(event_raw) is not str or sha(event_raw.encode()) != value["event_sha256"]:
            raise ValueError("subscription event differs from its captured hash")
        self.reading = weekly_reading(strict_json(event_raw))
        self.captured_at = _timestamp(value["captured_at"])
        self.max_age = age
        self.clock = _now if clock is None else clock
        self.raw = raw
        self.value = value
        self.path = None
        self.dispatched = False
        self.stop_reason = None
        self.observed_events = 0
        if check_freshness:
            self.before_dispatch(check_only=True)

    def before_dispatch(self, *, check_only=False):
        if self.path is not None and read_regular(self.path) != self.raw:
            raise ValueError("subscription guard file changed before dispatch")
        now = self.clock()
        if type(now) not in (int, float) or not math.isfinite(now):
            raise ValueError("subscription guard clock is invalid")
        if not 0 <= now - self.captured_at <= self.max_age:
            raise ValueError("subscription observation is stale or future-dated")
        if self.reading["resets_at"] <= now:
            raise ValueError("subscription window reset since observation")
        if self.reading["utilization"] >= 1 or self.reading["utilization"] > self.maximum:
            raise ValueError("insufficient weekly subscription headroom")
        if self.dispatched:
            raise ValueError("subscription guard dispatch already consumed")
        if not check_only:
            self.dispatched = True

    def observe(self, event):
        if type(event) is not dict or event.get("type") != "rate_limit_event":
            return
        self.observed_events += 1
        try:
            # The starting threshold is not a mid-run quota allowance. During
            # execution reject unsafe/unknown status, overage and exhausted
            # weekly windows, rather than treating a normal rise as a retry.
            reading = weekly_reading(event, require_weekly=False)
            if reading is not None and reading["utilization"] >= 1:
                raise ValueError("weekly subscription window is exhausted")
        except ValueError as exc:
            self.stop_reason = str(exc)
            raise

    def snapshot(self):
        return {
            "kind": KIND, "version": VERSION, "guard_sha256": sha(self.raw),
            "registration_sha256": self.value["registration_sha256"],
            "observation_sha256": self.value["event_sha256"],
            "weekly": self.reading, "maximum_starting_utilization": self.maximum,
            "dispatched": self.dispatched, "observed_rate_limit_events": self.observed_events,
            "stop_reason": self.stop_reason,
            "basis": "caller-supplied saved native event; not authenticated account state",
            "owner_authorization": "separately required; not supplied by this guard",
        }


def load_guard(path, expected_sha256, *, registration_raw, runtime, launch_word_path, clock=None):
    raw = read_regular(path)
    guard = SubscriptionGuard(raw, expected_sha256=expected_sha256,
        registration_raw=registration_raw, runtime=runtime,
        launch_word_raw=read_regular(launch_word_path), clock=clock)
    guard.path = Path(path)
    return guard


def validate_saved_snapshot(raw, snapshot, *, registration_raw, runtime, launch_word_raw):
    """Validate saved metadata against consumed bytes without re-aging a run."""
    if type(snapshot) is not dict:
        raise ValueError("saved subscription snapshot is malformed")
    guard = SubscriptionGuard(raw, expected_sha256=sha(raw),
        registration_raw=registration_raw, runtime=runtime, launch_word_raw=launch_word_raw,
        check_freshness=False)
    if type(snapshot.get("dispatched")) is not bool:
        raise ValueError("saved subscription dispatch state is malformed")
    count = snapshot.get("observed_rate_limit_events")
    stop = snapshot.get("stop_reason")
    if type(count) is not int or count < 0 or (stop is not None and type(stop) is not str):
        raise ValueError("saved subscription observation state is malformed")
    guard.dispatched, guard.observed_events, guard.stop_reason = snapshot["dispatched"], count, stop
    if snapshot != guard.snapshot():
        raise ValueError("saved subscription metadata differs from consumed evidence")
    return guard


def prepare_guard(*, registration_raw, runtime, launch_word_raw, event_raw,
                  captured_at, maximum_starting_utilization, max_age_seconds):
    """Bind an existing observation; never create quota or owner evidence."""
    document = {"kind": KIND, "version": VERSION,
        "registration_sha256": sha(registration_raw), "runtime_sha256": sha(canonical(runtime)),
        "launch_word_sha256": sha(launch_word_raw),
        "max_starting_weekly_utilization": maximum_starting_utilization,
        "max_age_seconds": max_age_seconds, "captured_at": captured_at,
        "event_json": event_raw.decode("utf-8"), "event_sha256": sha(event_raw)}
    raw = canonical(document)
    SubscriptionGuard(raw, expected_sha256=sha(raw), registration_raw=registration_raw,
        runtime=runtime, launch_word_raw=launch_word_raw)
    return raw
