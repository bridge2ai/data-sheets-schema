"""Versioned, fail-closed subscription observations for native U4b (2026-11-08).

No account, executable or provider access. Quota observations, review identities
and timestamps remain supplied evidence, not authenticated account state. The
separate authorization chain must verify the owner statement's review bundle.
No historical v1 guard is selected as a fallback; its file remains unchanged.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat


KIND = "d4d_native_subscription_guard"
VERSION = 2
MAX_BYTES = 65536
MAX_AGE_SECONDS = 300
WINDOWS = ("five_hour", "seven_day")
MAX_WINDOWS = 64
SAFE_STATUSES = ("allowed", "allowed_warning")
KEYS = frozenset({
    "kind", "version", "registration_sha256", "runtime_sha256",
    "launch_word_sha256", "owner_statement_sha256", "max_starting_weekly_utilization",
    "max_starting_five_hour_utilization", "max_age_seconds", "pre_reservation_margin_seconds",
    "captured_at", "event_json", "event_sha256",
})
WORD_KEYS = frozenset({
    "kind", "version", "registration_sha256", "attempt_id", "source_commit",
    "dependencies_sha256", "owner", "authorized_at", "word", "review_sha256",
    "ci_sha256", "permission_probe_sha256",
})


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def strict_json(raw, *, limit=MAX_BYTES):
    if type(raw) is str:
        raw = raw.encode("utf-8")
    if type(raw) is not bytes or not 0 < len(raw) <= limit:
        raise ValueError("subscription evidence is not bounded JSON bytes")

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
    """Read the exact bounded regular file; refuse aliases and changed bytes."""
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("subscription evidence requires a resolved absolute file")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
    except BaseException:
        os.close(fd)
        raise
    if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= limit:
        os.close(fd)
        raise ValueError("subscription evidence is not a bounded regular file")
    with os.fdopen(fd, "rb") as stream:
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
    current = path.stat(follow_symlinks=False)
    if (len(raw) != before.st_size or any(getattr(before, k) != getattr(after, k) for k in fields)
            or any(getattr(after, k) != getattr(current, k) for k in fields)):
        raise ValueError("subscription evidence changed during capture")
    return raw


def _closed(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(label + " has missing or unknown fields")


def _fraction(value, label):
    if type(value) not in (int, float) or not 0 <= value <= 1 or not math.isfinite(value):
        raise ValueError(label + " must be a finite fraction in [0, 1]")
    return value


def _timestamp(value, label):
    if (type(value) is not str or re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z", value) is None):
        raise ValueError(label + " must be an explicit UTC timestamp ending Z")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").timestamp()
    except (ValueError, OverflowError, OSError) as exc:
        raise ValueError(label + " is not a UTC timestamp") from exc


def _now():
    return datetime.now(timezone.utc).timestamp()


def _window_name(name):
    if (type(name) is not str or not name or len(name) > 128
            or any(char in name for char in ("\0", "\r", "\n"))):
        raise ValueError("subscription window name must be bounded nonempty text")
    return name


def _reading(row, info, name):
    if type(row) is not dict:
        raise ValueError(name + " subscription window is malformed")
    allowed = {"utilization", "resetsAt", "status", "isUsingOverage", "rateLimitType"}
    if row is not info and set(row) - allowed:
        raise ValueError(name + " subscription window has unknown fields")
    if "rateLimitType" in row and row["rateLimitType"] != name:
        raise ValueError(name + " subscription window type conflicts")
    utilization = _fraction(row.get("utilization"), name + " utilization")
    reset = row.get("resetsAt")
    if type(reset) is not int or reset <= 0:
        raise ValueError(name + " reset must be a positive epoch")
    status = row.get("status", info.get("status"))
    overage = row.get("isUsingOverage", info.get("isUsingOverage"))
    # Unsafe but parseable rows are retained before refusal, including exhausted
    # maxima. Missing or ambiguous values never become invented readings.
    if type(status) is not str or not status or type(overage) is not bool:
        raise ValueError(name + " window status or overage is unparseable")
    return {"utilization": utilization, "resets_at": reset,
            "status": status, "is_using_overage": overage}


def _inspect(event, *, require_both):
    """Return unambiguous rows and the first deterministic policy refusal."""
    errors, readings, recorded = [], {}, {}
    if type(event) is not dict or event.get("type") != "rate_limit_event":
        return {}, {}, "subscription guard requires a native rate_limit_event"
    try:
        if len(canonical(event)) > MAX_BYTES:
            return {}, {}, "subscription event exceeds its byte bound"
    except (TypeError, ValueError, RecursionError, OverflowError):
        return {}, {}, "subscription event is not finite bounded JSON"
    info = event.get("rate_limit_info")
    if type(info) is not dict:
        return {}, {}, "subscription rate-limit information is malformed"
    if info.get("status") not in SAFE_STATUSES:
        errors.append("subscription top-level status is rejected or unknown")
    if info.get("isUsingOverage") is not False:
        errors.append("subscription overage must be explicitly false")
    allowed = {"status", "isUsingOverage", "rateLimitType", "utilization", "resetsAt", "unifiedWindows",
               "overageStatus", "overageDisabledReason"}
    if set(info) - allowed:
        errors.append("subscription information has unknown fields")
    # First-party allowed events may report disabled overage even when their
    # numerical reading appears only in unifiedWindows. This is evidence of
    # refusal, never permission to use overage or infer subscription headroom.
    if "overageStatus" in info and info["overageStatus"] != "rejected":
        errors.append("subscription overage status must be rejected when present")
    if "overageDisabledReason" in info and (
            info["overageDisabledReason"] != "out_of_credits"
            or info.get("overageStatus") != "rejected"):
        errors.append("subscription overage disabled reason is unknown or inconsistent")
    windows = info.get("unifiedWindows", {})
    if type(windows) is not dict:
        errors.append("subscription windows are malformed")
        windows = {}
    top = info.get("rateLimitType")
    try:
        for name in windows:
            _window_name(name)
        if "rateLimitType" in info:
            _window_name(top)
    except ValueError as exc:
        return {}, {}, str(exc)
    names = set(WINDOWS) | set(windows) | ({top} if top is not None else set())
    if len(names) > MAX_WINDOWS:
        return {}, {}, "subscription window inventory exceeds its bound"
    if "rateLimitType" not in info and any(key in info for key in ("utilization", "resetsAt")):
        errors.append("subscription reading has no declared window type")
    for name in (*WINDOWS, *sorted(names - set(WINDOWS))):
        rows = ([info] if top == name else []) + ([windows[name]] if name in windows else [])
        if not rows:
            if require_both and name in WINDOWS:
                errors.append("subscription evidence has no " + name + " window")
            continue
        if name not in WINDOWS and all(type(row) is dict and "utilization" not in row for row in rows):
            # No numerical claim exists to admit or reject. Preserve every raw
            # window payload, excluding the top row's separate nested-window
            # container so it is neither duplicated nor credited to this name.
            # Opaque metadata never certifies headroom or a reset.
            recorded[name] = [deepcopy({key: value for key, value in row.items()
                                       if row is not info or key != "unifiedWindows"}) for row in rows]
            continue
        values = []
        try:
            for row in rows:
                if row is info and "utilization" not in row:
                    nested = windows.get(name)
                    if type(nested) is not dict or "utilization" not in nested:
                        raise ValueError(name + " subscription alias lacks its nested numerical reading")
                    # A missing top-level utilization is an alias pointer, not
                    # zero. Only the named nested row supplies that number;
                    # reset, status and overage must still agree exactly.
                    pointer = {key: row[key] for key in (
                        "resetsAt", "status", "isUsingOverage", "rateLimitType") if key in row}
                    pointer["utilization"] = nested["utilization"]
                    values.append(_reading(pointer, info, name))
                else:
                    values.append(_reading(row, info, name))
            if any(value != values[0] for value in values[1:]):
                raise ValueError(name + " subscription aliases conflict")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        reading = readings[name] = values[0]
        if reading["status"] not in SAFE_STATUSES:
            errors.append(name + " subscription window is rejected or unknown")
        if reading["is_using_overage"] is not False:
            errors.append(name + " subscription window reports overage")
        if reading["utilization"] >= 1:
            errors.append(name + " subscription window is exhausted")
    if not readings and not recorded and not errors:
        errors.append("subscription event contains no supported window reading")
    return readings, recorded, errors[0] if errors else None


def window_readings(event, *, require_both=True):
    """Validate all numerical windows; unknown nonnumeric rows are record-only."""
    if type(require_both) is not bool:
        raise ValueError("subscription presence selection must be boolean")
    readings, _, refusal = _inspect(event, require_both=require_both)
    if refusal is not None:
        raise ValueError(refusal)
    return readings


def _word(raw, registration_raw):
    value = strict_json(raw)
    _closed(value, WORD_KEYS, "v2 owner word")
    if (value["kind"] != "d4d_native_execution_launch_authorization_v2"
            or type(value["version"]) is not int or value["version"] != 2
            or value["word"] != "AUTHORIZE_ONE_NATIVE_ATTEMPT"
            or value["registration_sha256"] != sha(registration_raw)):
        raise ValueError("owner word does not bind this v2 native registration")
    for key in ("registration_sha256", "dependencies_sha256", "review_sha256", "ci_sha256", "permission_probe_sha256"):
        if type(value[key]) is not str or re.fullmatch(r"[0-9a-f]{64}", value[key]) is None:
            raise ValueError("owner word hash is malformed: " + key)
    if type(value["source_commit"]) is not str or re.fullmatch(r"[0-9a-f]{40}", value["source_commit"]) is None:
        raise ValueError("owner word source commit is malformed")
    for key in ("owner", "attempt_id"):
        if (type(value[key]) is not str or not value[key].strip() or len(value[key]) > 512
                or any(c in value[key] for c in ("\0", "\r", "\n"))):
            raise ValueError("owner word text is malformed: " + key)
    return value, _timestamp(value["authorized_at"], "authorized_at")


def _empty_windows():
    return {name: {"count": 0, "first": None, "last": None, "highest": None} for name in WINDOWS}


def _record(windows, readings, event_index):
    for name, reading in readings.items():
        value = {**reading, "event_index": event_index}
        row = windows.setdefault(name, {"count": 0, "first": None, "last": None, "highest": None})
        row["count"] += 1
        if row["first"] is None:
            row["first"] = value
        row["last"] = value
        if row["highest"] is None or reading["utilization"] > row["highest"]["utilization"]:
            row["highest"] = value


def _record_opaque(windows, recorded, event_index):
    for name, rows in recorded.items():
        value = {"rows": deepcopy(rows), "event_index": event_index}
        row = windows.setdefault(name, {"count": 0, "first": None, "last": None})
        row["count"] += 1
        if row["first"] is None:
            row["first"] = value
        row["last"] = value


def _admission(raw, expected_sha256, registration_raw, runtime, launch_word_raw, owner_statement):
    if type(registration_raw) is not bytes or not registration_raw or type(runtime) is not dict:
        raise ValueError("subscription admission requires captured registration bytes and runtime object")
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES or sha(raw) != expected_sha256:
        raise ValueError("subscription guard bytes differ from selected SHA256")
    value = strict_json(raw)
    _closed(value, KEYS, "v2 subscription guard")
    if value["kind"] != KIND or type(value["version"]) is not int or value["version"] != VERSION:
        raise ValueError("unsupported subscription guard protocol")
    word, authorized = _word(launch_word_raw, registration_raw)
    from .native_launch_review import registration_fields, validate_terms
    # This is an exact outer-byte join, not full registration verification.
    # The caller still must reconstruct and admit the registered execution.
    registered_runtime = registration_fields(registration_raw).get("runtime")
    if type(registered_runtime) is not dict or canonical(registered_runtime) != canonical(runtime):
        raise ValueError("subscription runtime differs from registered runtime bytes")
    statement = validate_terms(owner_statement, runtime, word_owner=word["owner"])
    for key, wanted in (
        ("registration_sha256", sha(registration_raw)),
        ("runtime_sha256", sha(canonical(runtime))),
        ("launch_word_sha256", sha(launch_word_raw)),
        ("owner_statement_sha256", sha(canonical(statement))),
    ):
        if value[key] != wanted:
            raise ValueError("subscription guard binding differs: " + key)
    auth = runtime.get("auth")
    if (type(auth) is not dict or auth.get("loggedIn") is not True
            or auth.get("authMethod") != "claude.ai" or auth.get("apiProvider") != "firstParty"
            or auth.get("expected_api_key_source") != "none"):
        raise ValueError("subscription guard requires selected first-party subscription auth")
    maximum = _fraction(value["max_starting_weekly_utilization"], "maximum starting utilization")
    five_hour_maximum = _fraction(value["max_starting_five_hour_utilization"],
                                 "maximum starting five-hour utilization")
    age = value["max_age_seconds"]
    if type(age) is not int or not 0 < age <= MAX_AGE_SECONDS:
        raise ValueError("subscription freshness must be 1..300 seconds")
    margin = value["pre_reservation_margin_seconds"]
    if type(margin) is not int or not 0 < margin <= age:
        raise ValueError("subscription pre-reservation margin must be an integer within capture age")
    if (maximum != statement["max_starting_weekly_utilization"]
            or five_hour_maximum != statement["max_starting_five_hour_utilization"]
            or age != statement["max_age_seconds"]
            or margin != statement["pre_reservation_margin_seconds"]):
        raise ValueError("subscription guard thresholds, age or margin differ from owner/runtime statement")
    event_raw = value["event_json"]
    if type(event_raw) is not str or sha(event_raw.encode()) != value["event_sha256"]:
        raise ValueError("subscription event differs from its captured hash")
    readings, recorded, refusal = _inspect(strict_json(event_raw), require_both=True)
    if refusal is not None:
        raise ValueError(refusal)
    if readings["seven_day"]["utilization"] > maximum:
        raise ValueError("insufficient weekly subscription headroom")
    if readings["five_hour"]["utilization"] > five_hour_maximum:
        raise ValueError("insufficient five-hour subscription headroom")
    captured = _timestamp(value["captured_at"], "captured_at")
    if captured < authorized:
        raise ValueError("subscription observation predates owner authorization")
    if any(reading["resets_at"] <= captured for reading in readings.values()):
        raise ValueError("subscription window reset is not after its observation")
    return {"value": value, "readings": readings, "record_only": recorded,
            "maximum": maximum, "five_hour_maximum": five_hour_maximum,
            "max_age": age, "margin": margin,
            "captured": captured, "authorized": authorized, "authorized_at": word["authorized_at"]}


class SubscriptionGuard:
    """Bound observation plus ordered delivery state; never standalone authority.

    Public admission properties are detached/read-only. Actual launch callers
    must first derive owner_statement from the exact word-bound review bytes.
    This helper repeats term equality and chronology, not reviewer authenticity.
    """
    __slots__ = ("_raw", "_expected", "_registration", "_runtime_raw", "_word_raw", "_owner_raw",
                 "_clock", "_path", "_dispatched", "_dispatched_at", "_stop", "_count", "_windows", "_record_only")

    def __init__(self, raw, *, expected_sha256, registration_raw, runtime,
                 launch_word_raw, owner_statement, clock=None, check_freshness=True):
        if type(check_freshness) is not bool:
            raise ValueError("subscription freshness selection must be boolean")
        _admission(raw, expected_sha256, registration_raw, runtime, launch_word_raw, owner_statement)
        self._raw, self._expected, self._registration = raw, expected_sha256, registration_raw
        self._runtime_raw, self._word_raw, self._owner_raw = canonical(runtime), launch_word_raw, canonical(owner_statement)
        self._clock = _now if clock is None else clock
        if not callable(self._clock):
            raise ValueError("subscription guard clock must be callable")
        self._path, self._dispatched, self._stop, self._count = None, False, None, 0
        self._dispatched_at = None
        self._windows = _empty_windows()
        self._record_only = {}
        if check_freshness:
            self.before_dispatch(check_only=True)

    def _static(self):
        return _admission(self._raw, self._expected, self._registration,
            strict_json(self._runtime_raw, limit=2 * 1024 * 1024), self._word_raw, strict_json(self._owner_raw))

    raw = property(lambda self: self._raw)
    value = property(lambda self: strict_json(self._raw))
    owner_statement = property(lambda self: strict_json(self._owner_raw))
    maximum = property(lambda self: self._static()["maximum"])
    five_hour_maximum = property(lambda self: self._static()["five_hour_maximum"])
    max_age = property(lambda self: self._static()["max_age"])
    pre_reservation_margin = property(lambda self: self._static()["margin"])
    captured_at = property(lambda self: self._static()["captured"])
    reading = property(lambda self: self._static()["readings"]["seven_day"])
    five_hour = property(lambda self: self._static()["readings"]["five_hour"])
    path = property(lambda self: self._path)
    dispatched = property(lambda self: self._dispatched)
    observed_events = property(lambda self: self._count)
    stop_reason = property(lambda self: self._stop)

    def _fresh(self):
        """Recheck immutable admission and current time without consuming dispatch."""
        bound = self._static()
        if self._path is not None and read_regular(self._path) != self._raw:
            raise ValueError("subscription guard file changed before dispatch")
        now = self._clock()
        if type(now) not in (int, float) or not math.isfinite(now):
            raise ValueError("subscription guard clock is invalid")
        stamp = datetime.fromtimestamp(now, timezone.utc).isoformat().replace("+00:00", "Z")
        now = _timestamp(stamp, "dispatch time")
        if not 0 <= now - bound["captured"] <= bound["max_age"]:
            raise ValueError("subscription observation is stale or future-dated")
        if any(row["resets_at"] <= now for row in bound["readings"].values()):
            raise ValueError("subscription window reset since observation")
        if self._dispatched:
            raise ValueError("subscription guard dispatch already consumed")
        if self._stop is not None:
            raise ValueError(self._stop)
        return bound, now, stamp

    def before_reservation(self):
        """Require the registered preparation margin before attempt reservation.

        This performs no reservation, dispatch or external effect. The caller
        must still run before_dispatch at actual dispatch after preparation.
        """
        bound, now, _ = self._fresh()
        if bound["captured"] + bound["max_age"] - now < bound["margin"]:
            raise ValueError("subscription pre-reservation freshness margin is insufficient")

    def before_dispatch(self, *, check_only=False):
        if type(check_only) is not bool:
            raise ValueError("subscription dispatch selection must be boolean")
        _, _, stamp = self._fresh()
        if not check_only:
            self._dispatched = True
            self._dispatched_at = stamp

    def observe(self, event):
        if type(event) is not dict or event.get("type") != "rate_limit_event":
            return
        # Recheck immutable admission bytes; changes to detached public values
        # cannot weaken the selected policy or manufacture an authorization.
        bound = self._static()
        self._count += 1
        readings, recorded, refusal = _inspect(event, require_both=False)
        if not self._dispatched:
            refusal = "subscription event was delivered before dispatch"
        elif any(row["resets_at"] <= bound["captured"] for row in readings.values()):
            refusal = refusal or "observed subscription reset is not after admission capture"
        elif any(row["resets_at"] <= _timestamp(self._dispatched_at, "dispatch time") for row in readings.values()):
            refusal = refusal or "observed subscription reset is not after dispatch"
        names = set(self._windows) | set(self._record_only) | set(readings) | set(recorded)
        if len(names) > MAX_WINDOWS:
            refusal = refusal or "observed subscription window inventory exceeds its bound"
        else:
            _record(self._windows, readings, self._count)
            _record_opaque(self._record_only, recorded, self._count)
        if refusal is not None and self._stop is None:
            self._stop = refusal
        if self._stop is not None:
            raise ValueError(self._stop)

    def snapshot(self):
        bound = self._static()
        return {"kind": KIND, "version": VERSION, "guard_sha256": sha(self._raw),
            "registration_sha256": bound["value"]["registration_sha256"],
            "observation_sha256": bound["value"]["event_sha256"],
            "owner_statement_sha256": bound["value"]["owner_statement_sha256"],
            "authorized_at": bound["authorized_at"], "captured_at": bound["value"]["captured_at"],
            "weekly": bound["readings"]["seven_day"], "five_hour": bound["readings"]["five_hour"],
            "initial_windows": deepcopy(bound["readings"]),
            "initial_record_only_windows": deepcopy(bound["record_only"]),
            "maximum_starting_utilization": bound["maximum"], "max_age_seconds": bound["max_age"],
            "maximum_starting_five_hour_utilization": bound["five_hour_maximum"],
            "pre_reservation_margin_seconds": bound["margin"],
            "dispatched": self._dispatched, "dispatched_at": self._dispatched_at,
            "observed_rate_limit_events": self._count,
            "observed_windows": deepcopy(self._windows), "stop_reason": self._stop,
            "observed_record_only_windows": deepcopy(self._record_only),
            "after_readings_verified": False,
            "after_readings_basis": "unverified unless complete captured transcript replay succeeds; stopped-attempt readings remain unverified",
            "unknown_window_policy": "utilization present: same numeric/reset/safety checks; utilization absent: raw record only, no safety verdict",
            "basis": "caller-supplied saved native events; not authenticated account state",
            "owner_authorization": "exact review bundle and separate authorization chain remain required"}


def load_guard(path, expected_sha256, *, registration_raw, runtime, launch_word_path,
               owner_statement, clock=None):
    raw = read_regular(path)
    guard = SubscriptionGuard(raw, expected_sha256=expected_sha256,
        registration_raw=registration_raw, runtime=runtime,
        launch_word_raw=read_regular(launch_word_path), owner_statement=owner_statement, clock=clock)
    guard._path = Path(path)
    return guard


def _saved_windows(value, count):
    if type(value) is not dict or not set(WINDOWS) <= set(value) or len(value) > MAX_WINDOWS:
        raise ValueError("saved subscription windows lack required names or exceed their bound")
    for name, row in value.items():
        _window_name(name)
        _closed(row, {"count", "first", "last", "highest"}, "saved " + name + " summary")
        n = row["count"]
        if type(n) is not int or not 0 <= n <= count:
            raise ValueError("saved subscription window count is malformed")
        if n == 0:
            if any(row[key] is not None for key in ("first", "last", "highest")):
                raise ValueError("unobserved subscription window invents a reading")
            continue
        for key in ("first", "last", "highest"):
            item = row[key]
            _closed(item, {"utilization", "resets_at", "status", "is_using_overage", "event_index"},
                    "saved subscription reading")
            _fraction(item["utilization"], "saved utilization")
            if (type(item["resets_at"]) is not int or item["resets_at"] <= 0
                    or type(item["event_index"]) is not int or not 1 <= item["event_index"] <= count
                    or type(item["status"]) is not str or not item["status"]
                    or type(item["is_using_overage"]) is not bool):
                raise ValueError("saved subscription reading is malformed")
        first, last, highest = (row[key] for key in ("first", "last", "highest"))
        if (not first["event_index"] <= highest["event_index"] <= last["event_index"]
                or n > last["event_index"] - first["event_index"] + 1
                or highest["utilization"] < max(first["utilization"], last["utilization"])
                or (n == 1 and not first == last == highest)):
            raise ValueError("saved subscription first/last/highest chronology is inconsistent")


def _saved_record_only(value, count):
    if type(value) is not dict or len(value) > MAX_WINDOWS or set(value) & set(WINDOWS):
        raise ValueError("saved record-only windows are malformed")
    for name, row in value.items():
        _window_name(name)
        _closed(row, {"count", "first", "last"}, "saved record-only summary")
        n = row["count"]
        if type(n) is not int or not 1 <= n <= count:
            raise ValueError("saved record-only count is malformed")
        for key in ("first", "last"):
            item = row[key]
            _closed(item, {"rows", "event_index"}, "saved record-only reading")
            if (type(item["event_index"]) is not int or not 1 <= item["event_index"] <= count
                    or type(item["rows"]) is not list or not 1 <= len(item["rows"]) <= 2
                    or any(type(raw) is not dict or "utilization" in raw for raw in item["rows"])
                    or len(canonical(item["rows"])) > MAX_BYTES):
                raise ValueError("saved record-only reading is malformed")
        if (row["first"]["event_index"] > row["last"]["event_index"]
                or n > row["last"]["event_index"] - row["first"]["event_index"] + 1
                or (n == 1 and row["first"] != row["last"])):
            raise ValueError("saved record-only chronology is inconsistent")


def validate_saved_snapshot(raw, snapshot, *, registration_raw, runtime, launch_word_raw, owner_statement):
    """Check static binding and shape only; dynamic truth requires transcript replay."""
    if type(snapshot) is not dict:
        raise ValueError("saved subscription snapshot is malformed")
    guard = SubscriptionGuard(raw, expected_sha256=sha(raw), registration_raw=registration_raw,
        runtime=runtime, launch_word_raw=launch_word_raw, owner_statement=owner_statement, check_freshness=False)
    if type(snapshot.get("dispatched")) is not bool:
        raise ValueError("saved subscription dispatch state is malformed")
    count, stop = snapshot.get("observed_rate_limit_events"), snapshot.get("stop_reason")
    if (type(count) is not int or count < 0 or (stop is not None and
            (type(stop) is not str or not stop or len(stop) > 1024))):
        raise ValueError("saved subscription observation state is malformed")
    _saved_windows(snapshot.get("observed_windows"), count)
    _saved_record_only(snapshot.get("observed_record_only_windows"), count)
    if len(set(snapshot["observed_windows"]) | set(snapshot["observed_record_only_windows"])) > MAX_WINDOWS:
        raise ValueError("saved subscription window inventory exceeds its bound")
    dispatch = snapshot.get("dispatched_at")
    if snapshot["dispatched"]:
        when = _timestamp(dispatch, "dispatch time")
        bound = guard._static()
        if (not 0 <= when - bound["captured"] <= bound["max_age"]
                or any(row["resets_at"] <= when for row in bound["readings"].values())):
            raise ValueError("saved dispatch time contradicts capture freshness or reset")
    elif dispatch is not None:
        raise ValueError("undispatched subscription snapshot invents dispatch time")
    guard._dispatched, guard._count, guard._stop = snapshot["dispatched"], count, stop
    guard._dispatched_at = dispatch
    guard._windows = deepcopy(snapshot["observed_windows"])
    guard._record_only = deepcopy(snapshot["observed_record_only_windows"])
    # Compare canonical bytes too: Python equality alone treats bool as int.
    if canonical(snapshot) != canonical(guard.snapshot()):
        raise ValueError("saved subscription metadata differs from consumed evidence")
    return guard


def _transcript_replay(raw, *, registration_raw, runtime, launch_word_raw, owner_statement,
                       transcript_raw, continue_after_stop, dispatched_at):
    from .native_shared_contract import HARD_LIMITS
    if (type(transcript_raw) is not bytes or not transcript_raw
            or len(transcript_raw) > HARD_LIMITS["stream_bytes"] or not transcript_raw.endswith(b"\n")):
        raise ValueError("subscription replay requires a complete bounded transcript")
    replay = SubscriptionGuard(raw, expected_sha256=sha(raw), registration_raw=registration_raw,
        runtime=runtime, launch_word_raw=launch_word_raw, owner_statement=owner_statement, check_freshness=False)
    replay._dispatched = dispatched_at is not None
    replay._dispatched_at = dispatched_at
    start, rows = 0, 0
    while start < len(transcript_raw):
        end = transcript_raw.find(b"\n", start)
        line = transcript_raw[start:end]
        start, rows = end + 1, rows + 1
        if rows > HARD_LIMITS["stream_rows"] or not line.strip():
            raise ValueError("subscription transcript row bound or empty row refused")
        event = strict_json(line, limit=16 * 1024 * 1024)
        if type(event) is not dict:
            raise ValueError("subscription replay event must be an object")
        try:
            replay.observe(event)
        except ValueError:
            if not continue_after_stop:
                raise
    return replay


def validate_saved_observations(raw, snapshot, *, registration_raw, runtime,
                                launch_word_raw, owner_statement, transcript_raw, complete):
    """Recompute exact complete delivery; failed buffered suffixes remain unverified."""
    if type(complete) is not bool:
        raise ValueError("saved subscription completion must be boolean")
    validate_saved_snapshot(raw, snapshot, registration_raw=registration_raw, runtime=runtime,
        launch_word_raw=launch_word_raw, owner_statement=owner_statement)
    if not complete:
        result = {"checked": False, "complete": False, "passed": False,
            "basis": "failed attempt: delivered observation prefix is not established; "
                     "saved event count, stop and window readings are not independently verified",
            "transcript_diagnostic": None}
        if transcript_raw is not None:
            try:
                replay = _transcript_replay(raw, registration_raw=registration_raw, runtime=runtime,
                    launch_word_raw=launch_word_raw, owner_statement=owner_statement,
                    transcript_raw=transcript_raw, continue_after_stop=True,
                    dispatched_at=snapshot["dispatched_at"])
                result["transcript_diagnostic"] = {
                    "basis": "all buffered transcript events; not proof of delivered callback prefix",
                    "transcript": {"bytes": len(transcript_raw), "sha256": sha(transcript_raw)},
                    "observed_rate_limit_events": replay.observed_events,
                    "observed_windows": replay.snapshot()["observed_windows"],
                    "observed_record_only_windows": replay.snapshot()["observed_record_only_windows"],
                    "first_stop": replay.stop_reason}
            except ValueError as exc:
                result["transcript_diagnostic"] = {"error": str(exc), "complete": False}
        return result
    if snapshot["dispatched"] is not True or snapshot["stop_reason"] is not None:
        raise ValueError("completed subscription snapshot lacks dispatch or retains a stop")
    replay = _transcript_replay(raw, registration_raw=registration_raw, runtime=runtime,
        launch_word_raw=launch_word_raw, owner_statement=owner_statement,
        transcript_raw=transcript_raw, continue_after_stop=False,
        dispatched_at=snapshot["dispatched_at"])
    if canonical(replay.snapshot()) != canonical(snapshot):
        raise ValueError("saved subscription state differs from ordered transcript replay")
    return {"checked": True, "complete": True, "passed": True,
        "basis": "all ordered rate_limit_event observations in the complete captured transcript",
        "transcript": {"bytes": len(transcript_raw), "sha256": sha(transcript_raw)},
        "observed_rate_limit_events": replay.observed_events,
        "observed_windows": replay.snapshot()["observed_windows"],
        "observed_record_only_windows": replay.snapshot()["observed_record_only_windows"]}


def prepare_guard(*, registration_raw, runtime, launch_word_raw, event_raw, captured_at,
                  maximum_starting_utilization, max_age_seconds, owner_statement, clock=None,
                  maximum_starting_five_hour_utilization=None, pre_reservation_margin_seconds=None):
    """Bind an observation and registered policy, without selecting numeric defaults.

    Raw bundle validation must precede this helper. Omitted new arguments are
    read from the required registered admission object, never ambient policy.
    """
    if type(event_raw) is not bytes:
        raise ValueError("subscription event must be captured bytes")
    from .native_u4b_policy import admission_terms
    admission = admission_terms(runtime)
    if maximum_starting_five_hour_utilization is None:
        maximum_starting_five_hour_utilization = admission["max_starting_five_hour_utilization"]
    if pre_reservation_margin_seconds is None:
        pre_reservation_margin_seconds = admission["pre_reservation_margin_seconds"]
    document = {"kind": KIND, "version": VERSION,
        "registration_sha256": sha(registration_raw), "runtime_sha256": sha(canonical(runtime)),
        "launch_word_sha256": sha(launch_word_raw), "owner_statement_sha256": sha(canonical(owner_statement)),
        "max_starting_weekly_utilization": maximum_starting_utilization,
        "max_starting_five_hour_utilization": maximum_starting_five_hour_utilization,
        "pre_reservation_margin_seconds": pre_reservation_margin_seconds,
        "max_age_seconds": max_age_seconds, "captured_at": captured_at,
        "event_json": event_raw.decode("utf-8"), "event_sha256": sha(event_raw)}
    raw = canonical(document)
    SubscriptionGuard(raw, expected_sha256=sha(raw), registration_raw=registration_raw,
        runtime=runtime, launch_word_raw=launch_word_raw, owner_statement=owner_statement, clock=clock)
    return raw
