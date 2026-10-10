"""Registered, one-attempt HTTP execution of two explicit instruments (#4458/59).

The original draft descriptor remains draft. Local call association is an
auditable execution record, not cryptographic provider authentication or human
scientific approval. No legacy judge, cache or retry behavior is selected here.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from decimal import Context, Decimal, DecimalException, DivisionByZero, InvalidOperation, Overflow, localcontext, ROUND_HALF_EVEN
import hashlib
from importlib.metadata import version
import ipaddress
import json
import math
import os
from pathlib import Path
import platform
import time
from urllib.parse import urlsplit

from . import nested_support_results as saved
from .support_plan import canonical

FORMAT = "nested_support_execution_v1"
FITNESS_FORMAT = "top_level_fitness_execution_v1"
ADAPTER = "native_message_http_json_v1"
MAX_REGISTRATION_BYTES = 4_000_000
MAX_CALLS = 100_000
LIMITATIONS = [
    "Execution records local invocation association, not cryptographic provider authentication.",
    "Decision references are caller declarations, not verification of scientific truth or human identity.",
    "Input reservations are provisional scheduling thresholds; a first-call input overrun is possible.",
    "No hard actual input-token or monetary ceiling is established; prices are caller supplied.",
    "timeout_ms bounds HTTP connect/read/write/pool inactivity, not a total wall-clock deadline.",
    "Mechanical response acceptance does not establish calibration or scientific accuracy.",
    "Fitness is a separate instrument and is not executed by this protocol.",
]
_SOURCE_NAMES = (
    "nested_support_execution.py", "nested_support_results.py", "support_targets.py",
    "support_plan.py", "support_judge.py", "evidence_assertions.py", "duplicate_keys.py",
    "schema_snapshot.py", "schema_view.py", "evaluation_model.py",
)
_FITNESS_SOURCE_NAMES = _SOURCE_NAMES + (
    "top_level_fitness_results.py", "schema_digest.py", "evidence_score.py",
)


class ExecutionError(ValueError):
    """Execution or its captured evidence does not meet the declared contract."""


def _need(condition, message):
    if not condition:
        raise ExecutionError(message)


def _keys(value, keys, label):
    _need(type(value) is dict and set(value) == set(keys), f"{label} requires exactly {sorted(keys)}")


def _text(value, label):
    _need(type(value) is str and bool(value) and value == value.strip(), f"{label} must be nonempty trimmed text")


def _int(value, label, *, maximum=None):
    _need(type(value) is int and value > 0 and (maximum is None or value <= maximum),
          f"{label} must be a positive bounded integer")


def _json(raw, label, *, limit=MAX_REGISTRATION_BYTES):
    return saved._read(raw, label, limit=limit)


def _header(value, label):
    _text(value, label)
    _need(all(32 <= ord(c) < 127 for c in value), f"{label} must be printable ASCII without control characters")


def _pin(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _adapter(protocol):
    # This closed dispatch table selects a captured instrument, not a caller
    # supplied implementation or a transport callback.
    if protocol == FORMAT:
        return saved
    if protocol == FITNESS_FORMAT:
        from . import top_level_fitness_results
        return top_level_fitness_results
    raise ExecutionError("explicit execution protocol required")


def _source_names(protocol):
    _adapter(protocol)
    return _SOURCE_NAMES if protocol == FORMAT else _FITNESS_SOURCE_NAMES


def _limitations(protocol):
    values = list(LIMITATIONS)
    if protocol == FITNESS_FORMAT:
        values[-1] = "Top-level fitness is separate from nested support; accepted replies are not scientific scores."
    return values


def _identity(protocol=FORMAT):
    # Called only at registration/admission. Offline recheck never reads code or
    # installed package metadata as a substitute for captured input authority.
    root = Path(__file__).parent
    return {"python": platform.python_version(),
            "packages": {name: version(name) for name in ("httpx", "httpcore", "h11", "PyYAML", "linkml-runtime")},
            "sources": {name: _pin((root / name).read_bytes()) for name in _source_names(protocol)}}


def _price(value):
    if value is None:
        return
    _keys(value, {"currency", "per_tokens", "source", "as_of", "rates"}, "prices")
    for key in ("currency", "source", "as_of"):
        _text(value[key], f"prices.{key}")
    _int(value["per_tokens"], "prices.per_tokens", maximum=10 ** 18)
    _need(type(value["rates"]) is dict and set(value["rates"]) <= {
        "input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"}, "unknown price rate")
    for rate in value["rates"].values():
        _need(type(rate) is str and len(rate) <= 64, "price rates must be bounded decimal strings")
        try:
            number = Decimal(rate)
        except InvalidOperation as exc:
            raise ExecutionError("invalid decimal price") from exc
        _need(number.is_finite() and number >= 0, "price must be finite and nonnegative")
        parts = number.as_tuple()
        _need(len(parts.digits) <= 32 and -18 <= parts.exponent <= 18,
              "price precision/exponent exceeds the registered arithmetic bounds")


def _declaration(value, descriptor):
    _keys(value, {"format", "registration_id", "purpose", "run_output", "transport",
                  "limits", "decisions", "prices"}, "declaration")
    _need(descriptor["format"] == _adapter(value["format"]).FORMAT, "descriptor differs from selected execution instrument")
    _text(value["registration_id"], "registration_id")
    _text(value["run_output"], "run_output")
    _need(Path(value["run_output"]).is_absolute(), "run_output must be absolute")
    purpose = value["purpose"]
    _need(purpose in {"local_fixture", "calibration", "cohort"}, "unknown execution purpose")
    t = value["transport"]
    _keys(t, {"adapter", "url", "model", "auth", "anthropic_version", "timeout_ms",
              "thinking", "effort", "retries", "redirects", "environment_proxies"}, "transport")
    _need(t["adapter"] == ADAPTER and type(t["retries"]) is int and t["retries"] == 0
          and t["redirects"] is False and t["environment_proxies"] is False,
          "transport requires the fixed adapter, zero retries, no redirects or environment proxies")
    for key in ("url", "model", "anthropic_version"):
        _text(t[key], f"transport.{key}")
    _header(t["anthropic_version"], "anthropic_version")
    u = urlsplit(t["url"])
    _need(u.hostname and u.path.endswith("/messages") and u.username is None and u.password is None
          and not u.query and not u.fragment
          and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in t["url"]), "invalid messages endpoint")
    try:
        u.port
    except ValueError as exc:
        raise ExecutionError("invalid endpoint port") from exc
    if purpose == "local_fixture":
        try:
            loopback = ipaddress.ip_address(u.hostname).is_loopback
        except ValueError:
            loopback = False
        _need(u.scheme == "http" and loopback and t["auth"] == "none",
              "local_fixture requires a literal loopback HTTP address and no credentials")
    else:
        _need(u.scheme == "https" and t["auth"] in {"bearer", "x-api-key"}, "paid routes require HTTPS and explicit authentication")
    _int(t["timeout_ms"], "timeout_ms", maximum=3_600_000)
    _need(t["thinking"] is None or (type(t["thinking"]) is dict and t["thinking"] == {"type": "adaptive"}),
          "thinking must be explicit null or adaptive")
    _need(t["effort"] is None or t["effort"] in {"low", "medium", "high", "max"}, "unknown explicit effort")
    limits = value["limits"]
    _keys(limits, {"max_calls", "request_bytes", "response_bytes", "total_response_bytes",
                  "input_reservation_per_call", "input_scheduling_threshold", "output_scheduling_threshold"}, "limits")
    for key, number in limits.items():
        _int(number, key)
    _need(limits["max_calls"] <= MAX_CALLS and len(descriptor["selections"]) <= limits["max_calls"], "call ceiling exceeded")
    _need(limits["request_bytes"] <= saved.MAX_ARTIFACT_BYTES and limits["response_bytes"] <= saved.MAX_RESPONSE_BYTES
          and limits["total_response_bytes"] <= saved.MAX_CAPTURE_BYTES, "capture limits exceed fixed contract")
    d = value["decisions"]
    required = {"instrument_review", "context_review", "controls_review", "private_control_handling",
                "paid_authorization", "calibration_acceptance", "canary_acceptance"}
    _keys(d, required, "decisions")
    for decision in d.values():
        if decision is not None:
            _keys(decision, {"reference", "sha256"}, "decision reference")
            _text(decision["reference"], "decision reference")
            _need(type(decision["sha256"]) is str and bool(saved._SHA.fullmatch(decision["sha256"])), "invalid decision digest")
    if purpose == "local_fixture":
        _need(all(x is None for x in d.values()), "local fixtures cannot declare scientific or paid approval")
    else:
        needed = required if purpose == "cohort" else required - {"calibration_acceptance", "canary_acceptance"}
        _need(all(d[x] is not None for x in needed), "explicit reviewed/paid decision references required")
    _price(value["prices"])


def _requests(capture, descriptor, declaration):
    rows = []
    for selection in descriptor["selections"]:
        binding = selection["binding"]
        request = saved._read(capture.get(binding["request"]), "planned request")
        _keys(request, {"model", "max_tokens", "temperature", "system", "messages"}, "planned request")
        _need(request["model"] == declaration["transport"]["model"] == binding["model"]["name"], "model differs from captured plan")
        _need(request["max_tokens"] == binding["max_tokens"] and request["temperature"] is None,
              "unsupported planned request; no silent cap or temperature override")
        body = {k: v for k, v in request.items() if k != "temperature"}
        body["stream"] = False
        t = declaration["transport"]
        if t["thinking"] is not None:
            body["thinking"] = t["thinking"]
        if t["effort"] is not None:
            body["output_config"] = {"effort": t["effort"]}
        raw = canonical(body)
        _need(len(raw) <= declaration["limits"]["request_bytes"], "request byte bound exceeded")
        rows.append({"target_id": selection["target_id"], "attempt_id": selection["attempt_id"],
                     "kind": binding["kind"], "planned_request": binding["request"],
                     "effective_request": capture.add(raw), "max_tokens": binding["max_tokens"]})
    return rows


def _registration(capture, descriptor_raw, declaration, identity):
    protocol = declaration["format"]
    descriptor = _adapter(protocol)._load_descriptor(capture, descriptor_raw)
    _declaration(declaration, descriptor)
    _keys(identity, {"python", "packages", "sources"}, "implementation identity")
    _text(identity["python"], "Python identity")
    _keys(identity["packages"], {"httpx", "httpcore", "h11", "PyYAML", "linkml-runtime"}, "package identity")
    for package_version in identity["packages"].values():
        _text(package_version, "package version")
    _need(type(identity["sources"]) is dict and set(identity["sources"]) == set(_source_names(protocol)), "implementation source roster differs")
    for pin in identity["sources"].values():
        _keys(pin, {"sha256", "bytes"}, "source pin")
        _need(type(pin["sha256"]) is str and bool(saved._SHA.fullmatch(pin["sha256"])), "invalid source digest")
        _int(pin["bytes"], "source bytes")
    requests = _requests(capture, descriptor, declaration)
    # Reserve serialized response, envelope, result and report overhead before
    # any paid admission. These conservative storage bounds do not estimate tokens.
    overhead = len(canonical(descriptor)) + 16_384 * len(requests)
    response_budget = declaration["limits"]["total_response_bytes"]
    _need(8 * response_budget + 2 * overhead <= saved.MAX_MANIFEST_BYTES, "declared responses exceed bounded report storage")
    result = {"format": protocol, "kind": "registration", "descriptor": capture.add(descriptor_raw),
            "declaration": declaration, "implementation": identity,
            "requests": requests,
            "original_readiness": descriptor["readiness"], "scientific_eligibility": False,
            "limitations": _limitations(protocol)}
    if "representation_accounting" in descriptor:
        result["representation_accounting"] = descriptor["representation_accounting"]
    return result


def _load(capture, raw):
    value = _json(raw, "registration")
    expected = _registration(capture, capture.get(value["descriptor"], limit=saved.MAX_MANIFEST_BYTES),
                             value["declaration"], value["implementation"])
    _need(raw == canonical(expected) + b"\n", "registration differs from its canonical reconstructed authority")
    return expected


def prepare(descriptor: Path, declaration: Path, output: Path):
    """Register exact captured authority and caller decisions; never dispatch."""
    capture = saved.Capture(descriptor)
    descriptor_raw = capture.entry("descriptor.json")
    declared = _json(saved._file(Path(declaration), MAX_REGISTRATION_BYTES), "declaration")
    target = Path(declared["run_output"])
    _need(not target.exists() and not target.is_symlink(), "declared run output already exists")
    _need(str(target.resolve()) == str(target), "run_output must have its canonical absolute spelling")
    for source in (Path(descriptor).resolve(), Path(declaration).resolve(), Path(output).resolve()):
        _need(not target.is_relative_to(source) and not source.is_relative_to(target), "run output overlaps input/registration")
    result = _registration(capture, descriptor_raw, declared, _identity(declared["format"]))
    _need(len(canonical(result)) <= MAX_REGISTRATION_BYTES, "registration exceeds byte bound")
    capture.add(canonical(result) + b"\n")
    _reserve_storage(capture, result)
    saved._write_new(output, capture, "registration.json", result, protected=(declaration,))
    return result


def _reserve_storage(capture, registration):
    limit = registration["declaration"]["limits"]["total_response_bytes"]
    descriptor_size = registration["descriptor"]["bytes"]
    _need(capture.total + 8 * limit + 2 * descriptor_size + 16_384 * len(registration["requests"]) <= saved.MAX_CAPTURE_BYTES,
          "declared responses exceed remaining captured storage")


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _exclusive(path, raw):
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_dir(Path(path).parent)


def _store(output, raw):
    pin = _pin(raw)
    path = Path(output) / "artifacts" / pin["sha256"]
    if path.exists():
        _need(saved._file(path, saved.MAX_ARTIFACT_BYTES) == raw, "existing content-addressed artifact differs")
    else:
        _exclusive(path, raw)
    return pin


def _admission(registration_raw, request, index, started, *, protocol=FORMAT):
    return {"format": protocol, "index": index, "registration": _pin(registration_raw),
            "target_id": request["target_id"], "attempt_id": request["attempt_id"],
            "effective_request": request["effective_request"], "started_at": started}


def _dispatch(transport, raw, cap, credential):
    """One actual non-streaming messages POST; capture response-body bytes."""
    import httpx
    headers = {"content-type": "application/json", "accept": "application/json",
               "accept-encoding": "identity", "anthropic-version": transport["anthropic_version"]}
    if transport["auth"] == "bearer":
        headers["authorization"] = "Bearer " + credential
    elif transport["auth"] == "x-api-key":
        headers["x-api-key"] = credential
    body = bytearray()
    outcome = {"status_code": None, "request_id": None, "body_complete": False,
               "failure": None, "duration_seconds": None, "stage": "connect_or_send"}
    started = time.monotonic()
    try:
        with httpx.Client(transport=httpx.HTTPTransport(retries=0, trust_env=False), trust_env=False,
                          follow_redirects=False, timeout=transport["timeout_ms"] / 1000) as client:
            with client.stream("POST", transport["url"], headers=headers, content=raw) as response:
                outcome["stage"] = "response_body"
                outcome["status_code"] = response.status_code
                outcome["request_id"] = response.headers.get("request-id")
                for chunk in response.iter_raw():
                    remaining = cap + 1 - len(body)
                    body.extend(chunk[:remaining])
                    if len(body) > cap:
                        outcome["failure"] = "response_byte_limit_exceeded"
                        break
                else:
                    outcome["body_complete"] = True
                    outcome["stage"] = "complete"
                if outcome["failure"] is None and response.headers.get("content-encoding", "identity") != "identity":
                    outcome["failure"] = "unsupported_content_encoding"
    except httpx.TimeoutException:
        outcome["failure"] = "transport_timeout"
    except httpx.HTTPError as exc:
        # Do not copy exceptions containing arbitrary URLs, headers or secrets.
        outcome["failure"] = "transport_" + type(exc).__name__
    outcome["duration_seconds"] = time.monotonic() - started
    return outcome, bytes(body)


def _usage(assessment):
    raw = assessment.get("usage") if assessment else None
    keys = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    counters = {k: raw.get(k) if type(raw) is dict else None for k in keys}
    valid = lambda v: type(v) is int and v >= 0
    known = all(valid(v) for v in counters.values())
    total = sum(counters[k] for k in keys if k != "output_tokens") if known else None
    return {"counters": counters, "accounting_complete": known, "total_input_tokens": total,
            "output_tokens": counters["output_tokens"] if valid(counters["output_tokens"]) else None}


def _cost_context():
    return Context(prec=64, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
                   traps=[InvalidOperation, DivisionByZero, Overflow])


def _cost(usage, price):
    if price is None or not usage["accounting_complete"]:
        return None
    if any(k not in price["rates"] for k in usage["counters"]):
        return None
    # Explicit deterministic arithmetic, independent of ambient decimal context.
    # Large observed usage cannot turn a preserved failure into an exception.
    try:
        with localcontext(_cost_context()):
            total = sum(Decimal(price["rates"][k]) * v for k, v in usage["counters"].items()) / price["per_tokens"]
            return format(total, "f")
    except DecimalException:
        return None


def _transport_state(response, body, limit):
    """Check the combinations produced by the fixed dispatcher, before use."""
    _need(response["body"] == _pin(body), "HTTP body identity differs")
    stage, failure = response["stage"], response["failure"]
    transport_failures = {"transport_timeout", *("transport_" + name for name in (
        "HTTPError", "RequestError", "TransportError", "NetworkError", "ReadError",
        "WriteError", "ConnectError", "CloseError", "ProxyError", "UnsupportedProtocol",
        "ProtocolError", "LocalProtocolError", "RemoteProtocolError", "DecodingError",
        "TooManyRedirects", "HTTPStatusError"))}
    _need(failure is None or failure in transport_failures | {
        "response_byte_limit_exceeded", "unsupported_content_encoding"}, "unknown transport failure")
    _need(response["body_complete"] is (stage == "complete"), "transport stage/completeness conflict")
    _need((response["status_code"] is None) == (stage == "connect_or_send"),
          "transport stage/HTTP status conflict")
    if stage == "connect_or_send":
        _need(not body and response["request_id"] is None and failure in transport_failures,
              "pre-header transport state conflicts")
    elif stage == "response_body":
        _need(failure in transport_failures or failure == "response_byte_limit_exceeded",
              "interrupted body requires a transport or byte-limit failure")
    if failure == "response_byte_limit_exceeded":
        _need(stage == "response_body" and len(body) == limit + 1, "overflow state conflicts")
    else:
        _need(len(body) <= limit, "body exceeds limit without overflow evidence")
    if failure == "unsupported_content_encoding":
        _need(stage == "complete", "encoding failure requires a completed raw body")


def _assessment(capture, registration, selection, response, body):
    _keys(response, {"status_code", "request_id", "body_complete", "failure", "duration_seconds", "body", "stage"}, "HTTP outcome")
    _need(response["status_code"] is None or type(response["status_code"]) is int and 100 <= response["status_code"] <= 599,
          "invalid HTTP status")
    _keys(response["body"], {"sha256", "bytes"}, "HTTP body pin")
    _need(response["stage"] in {"connect_or_send", "response_body", "complete"}, "invalid transport stage")
    _need(type(response["body_complete"]) is bool, "invalid body completeness")
    _need(type(response["duration_seconds"]) in (int, float) and math.isfinite(response["duration_seconds"]) and response["duration_seconds"] >= 0, "invalid duration")
    _need(response["failure"] is None or type(response["failure"]) is str, "invalid failure")
    _need(response["request_id"] is None or type(response["request_id"]) is str, "invalid request identifier")
    _transport_state(response, body, registration["declaration"]["limits"]["response_bytes"])
    result = None
    # Raw native assessment is distinct from HTTP success. Complete failed HTTP
    # replies may still report usage; preserve it without accepting the call.
    if response["body_complete"]:
        descriptor_raw = capture.get(registration["descriptor"], limit=saved.MAX_MANIFEST_BYTES)
        adapter = _adapter(registration["format"])
        envelope = adapter.package_response(descriptor_raw, attempt_id=selection["attempt_id"], native_message=body)
        result = copy.deepcopy(adapter._attempt(capture, descriptor_raw, envelope, selection["attempt_id"]))
    assessment = result["assessment"] if result else None
    usage = _usage(assessment)
    problems = [] if result and assessment["status"] == "accepted" else ["response_not_accepted"]
    if response["status_code"] != 200 or response["failure"] is not None or not response["body_complete"]:
        problems.append("transport_not_successful")
    if not usage["accounting_complete"]:
        problems.append("usage_unknown_or_incomplete")
    limits = registration["declaration"]["limits"]
    if usage["accounting_complete"] and usage["total_input_tokens"] > limits["input_reservation_per_call"]:
        problems.append("input_exceeds_provisional_reservation")
    return {"target_id": selection["target_id"], "attempt_id": selection["attempt_id"],
            "kind": selection["kind"], "status": "accepted" if not problems else "failed",
            "problems": problems, "saved_result": result, "usage": usage,
            "cost": _cost(usage, registration["declaration"]["prices"])}


def _can_admit(limits, calls, input_used, output_used, response_used, request):
    return (calls < limits["max_calls"]
            and input_used + limits["input_reservation_per_call"] <= limits["input_scheduling_threshold"]
            and output_used + request["max_tokens"] <= limits["output_scheduling_threshold"]
            and response_used + limits["response_bytes"] + 1 <= limits["total_response_bytes"])


def run(registration: Path, *, credential: str | None = None):
    """Dispatch once into the registration's fresh bound output directory.

    Existing destinations are spent even after interruption. Recheck recovers
    captured responses without networking; it never purchases replacements.
    """
    capture = saved.Capture(registration)
    raw = capture.entry("registration.json", limit=MAX_REGISTRATION_BYTES)
    reg = _load(capture, raw)
    _need(reg["implementation"] == _identity(reg["format"]), "execution implementation/runtime differs from registration")
    _reserve_storage(capture, reg)
    declared = reg["declaration"]
    if declared["purpose"] == "local_fixture":
        _need(credential is None, "local fixtures reject credentials")
    else:
        _header(credential, "explicit runtime credential")
    output = Path(declared["run_output"])
    _need(str(output.resolve()) == str(output), "run output path changed")
    saved._write_new(output, capture, "registration.json", reg)
    _fsync_dir(output / "artifacts")
    _fsync_dir(output)
    _fsync_dir(output.parent)
    attempts = output / "attempts"
    attempts.mkdir()
    _fsync_dir(output)
    calls = input_used = output_used = response_used = 0
    limits = declared["limits"]
    for index, request in enumerate(reg["requests"]):
        if not _can_admit(limits, calls, input_used, output_used, response_used, request):
            break
        directory = attempts / f"{index:06d}"
        directory.mkdir()
        _fsync_dir(attempts)
        admitted = _admission(raw, request, index, datetime.now(timezone.utc).isoformat(), protocol=reg["format"])
        _exclusive(directory / "admitted.json", canonical(admitted))
        response, body = _dispatch(declared["transport"], capture.get(request["effective_request"]),
                                   limits["response_bytes"], credential)
        response["body"] = _store(output, body)
        # This durable boundary precedes semantic parsing and any accounting.
        _exclusive(directory / "response.json", canonical(response))
        row = _assessment(capture, reg, request, response, body)
        for artifact in capture.blobs.values():
            _store(output, artifact)
        _exclusive(directory / "settled.json", canonical(row))
        calls += 1
        response_used += len(body)
        if row["status"] != "accepted":
            break
        input_used += row["usage"]["total_input_tokens"]
        output_used += row["usage"]["output_tokens"]
    checked = recheck(output)
    _exclusive(output / "report.json", canonical(checked))
    return checked


def capture_run(output: Path):
    """Capture the closed durable ledger, without trusting derived status flags."""
    capture = saved.Capture(output)
    registration_raw = capture.entry("registration.json", limit=MAX_REGISTRATION_BYTES)
    registration = capture.add(registration_raw)
    protocol = _json(registration_raw, "registration")["format"]
    attempts = Path(output) / "attempts"
    _need(attempts.is_dir() and not attempts.is_symlink(), "missing or unsafe attempts directory")
    entries = sorted(attempts.iterdir())
    _need(len(entries) <= MAX_CALLS and [p.name for p in entries] == [f"{i:06d}" for i in range(len(entries))],
          "attempt directories must be a contiguous selected prefix")
    rows = []
    for directory in entries:
        _need(directory.is_dir() and not directory.is_symlink(), "unsafe attempt directory")
        names = {p.name for p in directory.iterdir()}
        _need(names <= {"admitted.json", "response.json", "settled.json"}, "unknown attempt artifact")
        rows.append({key: capture.add(saved._file(directory / (key + ".json"),
                         saved.MAX_MANIFEST_BYTES if key == "settled" else MAX_REGISTRATION_BYTES))
                     if key + ".json" in names else None for key in ("admitted", "response", "settled")})
    ledger = {"format": protocol, "registration": registration, "attempts": rows}
    # Materialize the exact closure into this capture, for portable indexes.
    recheck_captured(capture, ledger)
    return capture, ledger


def recheck_captured(capture, ledger):
    """Reconstruct from a captured ledger; no original paths, runtime or calls."""
    _keys(ledger, {"format", "registration", "attempts"}, "captured ledger")
    _adapter(ledger["format"])
    _need(type(ledger["attempts"]) is list, "unknown ledger attempts")
    raw = capture.get(ledger["registration"], limit=MAX_REGISTRATION_BYTES)
    reg = _load(capture, raw)
    _need(ledger["format"] == reg["format"], "ledger differs from registered instrument")
    entries = ledger["attempts"]
    _need(len(entries) <= len(reg["requests"]), "attempts exceed selected requests")
    rows = []
    input_used = output_used = response_used = 0
    stopped = False
    limits = reg["declaration"]["limits"]
    for index, entry in enumerate(entries):
        if index:
            _need(entries[index - 1]["settled"] is not None,
                  "later admission requires the preceding durable settlement")
        _keys(entry, {"admitted", "response", "settled"}, "attempt ledger entry")
        _need(not stopped, "invalid attempt after terminal/unknown state")
        request = reg["requests"][index]
        _need(_can_admit(limits, index, input_used, output_used, response_used, request), "admission exceeded scheduling thresholds")
        if entry["admitted"] is None:
            _need(entry["response"] is None and entry["settled"] is None, "response without admission")
            _need(index == len(entries) - 1, "unadmitted empty entry must be terminal")
            stopped = True
            break
        admission = _json(capture.get(entry["admitted"], limit=MAX_REGISTRATION_BYTES), "admission")
        _text(admission.get("started_at"), "admission time")
        _need(canonical(admission) == canonical(_admission(raw, request, index, admission["started_at"], protocol=reg["format"])), "admission differs from bound request")
        if entry["response"] is None:
            _need(entry["settled"] is None, "settlement without response")
            rows.append({"target_id": request["target_id"], "attempt_id": request["attempt_id"],
                         "kind": request["kind"], "status": "spent_unknown", "problems": ["admitted_response_not_preserved"]})
            stopped = True
            continue
        response = _json(capture.get(entry["response"], limit=MAX_REGISTRATION_BYTES), "HTTP outcome")
        body = capture.get(response["body"], limit=limits["response_bytes"] + 1)
        response_used += len(body)
        _need(response_used <= limits["total_response_bytes"], "aggregate response byte bound exceeded")
        if len(body) > limits["response_bytes"]:
            _need(response["failure"] == "response_byte_limit_exceeded" and response["body_complete"] is False, "oversize response claimed complete")
        row = _assessment(capture, reg, request, response, body)
        if entry["settled"] is not None:
            _need(capture.get(entry["settled"], limit=saved.MAX_MANIFEST_BYTES) == canonical(row), "settled result differs from raw evidence")
        rows.append(row)
        if row["status"] == "accepted":
            input_used += row["usage"]["total_input_tokens"]
            output_used += row["usage"]["output_tokens"]
        else:
            stopped = True
    counts = {kind: {"selected": 0, "accepted": 0, "failed": 0, "spent_unknown": 0, "not_started": 0}
              for kind in (("relationship_edge", "attribute_value") if reg["format"] == FORMAT else ("fitness_top_level",))}
    for i, request in enumerate(reg["requests"]):
        count = counts[request["kind"]]
        count["selected"] += 1
        count[rows[i]["status"] if i < len(rows) else "not_started"] += 1
    usage_keys = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    observed = {k: [r.get("usage", {}).get("counters", {}).get(k) for r in rows] for k in usage_keys}
    totals = {k: sum(v) if all(type(x) is int and x >= 0 for x in v) else None for k, v in observed.items()}
    costs = [r.get("cost") for r in rows]
    with localcontext(_cost_context()):
        cost = format(sum((Decimal(x) for x in costs), Decimal(0)), "f") if costs and all(x is not None for x in costs) else None
    result = {"format": reg["format"], "kind": "execution_report", "registration": _pin(raw),
              "purpose": reg["declaration"]["purpose"], "selected_counts": counts, "rows": rows,
              "admitted_calls": len(rows), "observed_usage_totals": totals, "observed_cost": cost,
              "cost_currency": reg["declaration"]["prices"]["currency"] if reg["declaration"]["prices"] else None,
              "accepted_accounted_input_tokens": input_used,
              "accepted_accounted_output_tokens": output_used, "response_bytes": response_used,
              "all_selected_accepted": len(rows) == len(reg["requests"]) and all(r["status"] == "accepted" for r in rows),
              "original_readiness": reg["original_readiness"], "scientific_eligibility": False,
              "fitness": "separate_and_unscored", "limitations": _limitations(reg["format"])}
    if reg["format"] == FITNESS_FORMAT:
        result["axis"] = "fitness"
    if "representation_accounting" in reg:
        result["representation_accounting"] = reg["representation_accounting"]
    _need(len(canonical(result)) <= saved.MAX_MANIFEST_BYTES, "report exceeds storage bound")
    return result


def recheck(output: Path):
    """Captured readback; incomplete admitted calls stay spent/unknown."""
    capture, ledger = capture_run(output)
    result = recheck_captured(capture, ledger)
    report = Path(output) / "report.json"
    if report.exists():
        _need(saved._file(report, saved.MAX_MANIFEST_BYTES) == canonical(result), "report differs from captured reconstruction")
    return result
