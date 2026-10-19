"""Review exact saved request sizes without contacting a provider (#5072).

This is an evidence reader, not a registration builder or a launch gate. A
request can fit its declared window while the unconstructed rest of a run is
still unknown. Neither a successful count nor these checks establishes billing,
streaming support, scientific acceptance, or permission to run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


FORMAT = "d4d_offline_sizing_v1"
COUNT_FORMAT = "d4d_saved_token_count_v1"
MAX_BYTES = 64_000_000
MAX_ROWS = 1024
PHASES = frozenset({"full", "full_readdress", "full_receipt_completion",
    "typed_audit_worker", "typed_audit_omission", "typed_audit_integration",
    "reconcile_full", "report", "report_regate", "repair_full", "report_after_repair"})


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(rows):
    result = {}
    for key, value in rows:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f"nonfinite JSON number: {value}")


def _json(raw):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError("expected bounded strict UTF-8 JSON") from exc


def _read(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("input exceeds offline sizing byte bound")
    return raw


def _keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f"{label} requires exactly {sorted(keys)}")


def _integer(value, label, minimum=0):
    if type(value) is not int or not minimum <= value <= 10**12:
        raise ValueError(f"{label} requires a bounded integer >= {minimum}")
    return value


def _text(value, label):
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} requires nonblank text")
    return value


def pin(path, raw=None):
    path = Path(path).resolve()
    raw = _read(path) if raw is None else raw
    return {"path": str(path), "sha256": sha(raw), "bytes": len(raw)}


def _pinned(value):
    _keys(value, {"path", "sha256", "bytes"}, "file pin")
    path = Path(_text(value["path"], "pin path"))
    if not path.is_absolute():
        raise ValueError("pin path must be absolute")
    if type(value["sha256"]) is not str or not re.fullmatch(r"[a-f0-9]{64}", value["sha256"]):
        raise ValueError("pin requires SHA256")
    _integer(value["bytes"], "pin bytes")
    raw = _read(path)
    if sha(raw) != value["sha256"] or len(raw) != value["bytes"]:
        raise ValueError(f"stale file pin: {path}")
    return raw


def window_status(input_tokens, output_tokens, window_tokens, margin_tokens):
    """Arithmetic only; every capacity and margin is supplied explicitly."""
    _integer(input_tokens, "input tokens")
    _integer(output_tokens, "output tokens", 1)
    _integer(window_tokens, "context window", 1)
    _integer(margin_tokens, "required margin")
    if margin_tokens >= window_tokens:
        raise ValueError("required margin leaves no request capacity")
    clearance = window_tokens - input_tokens - output_tokens
    return {"status": "FAIL" if clearance < margin_tokens else "PASS",
            "input_tokens": input_tokens, "max_output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens, "clearance_tokens": clearance,
            "fits_window": clearance >= 0, "fits_margin": clearance >= margin_tokens}


def _payload(raw):
    value = _json(raw)
    required = {"model", "messages", "max_tokens"}
    allowed = required | {"system", "thinking", "temperature", "output_config"}
    if type(value) is not dict or not required <= set(value) <= allowed:
        raise ValueError("request must be a logical provider payload, without transport credentials")
    _text(value["model"], "request model")
    _integer(value["max_tokens"], "request max_tokens", 1)
    if type(value["messages"]) is not list or not value["messages"]:
        raise ValueError("request requires messages")
    for message in value["messages"]:
        _keys(message, {"role", "content"}, "message")
        if message["role"] not in {"user", "assistant"} or type(message["content"]) not in (str, list):
            raise ValueError("invalid request message")
    return value


def review(manifest_path, *, dry_run=False):
    """Validate pinned files and replay saved count arithmetic; never call a client.

    A null request/count is an explicit unknown. A supplied but missing or stale
    file refuses. Full-run readiness always stays UNKNOWN because callers may
    list a subset or scenarios, rather than the eventual worker/phase roster.
    """
    raw = _read(manifest_path)
    manifest = _json(raw)
    _keys(manifest, {"format", "scope", "inputs", "requests"}, "sizing manifest")
    if manifest["format"] != FORMAT:
        raise ValueError("unsupported sizing manifest")
    _text(manifest["scope"], "manifest scope")
    inputs = manifest["inputs"]
    if type(inputs) is not list or not 0 < len(inputs) <= MAX_ROWS:
        raise ValueError("manifest requires a bounded nonempty input inventory")
    names = set()
    for item in inputs:
        _pinned(item)
        resolved = str(Path(item["path"]).resolve())
        if resolved in names:
            raise ValueError("duplicate input path")
        names.add(resolved)
    inputs_sha256 = sha(canonical(inputs))
    selected = manifest["requests"]
    if type(selected) is not list or not 0 < len(selected) <= MAX_ROWS:
        raise ValueError("manifest requires a bounded nonempty request roster")
    rows, identities = [], set()
    for item in selected:
        _keys(item, {"id", "phase", "request", "count", "basis", "context_limit_tokens",
                    "context_limit_basis", "required_margin_tokens", "margin_basis"}, "request row")
        identity = _text(item["id"], "request id")
        if identity in identities:
            raise ValueError("duplicate request id")
        identities.add(identity)
        if item["phase"] not in PHASES or item["basis"] not in {"exact", "scenario"}:
            raise ValueError("unknown phase or request basis")
        window = _integer(item["context_limit_tokens"], "context window", 1)
        margin = _integer(item["required_margin_tokens"], "required margin")
        if margin >= window:
            raise ValueError("required margin leaves no request capacity")
        _text(item["context_limit_basis"], "context limit basis")
        _text(item["margin_basis"], "margin basis")
        row = {**item, "status": "UNKNOWN", "payload_bytes": None,
               "canonical_request_sha256": None, "max_output_tokens": None,
               "input_tokens": None, "reason": "request not constructed"}
        if item["request"] is None:
            if item["count"] is not None:
                raise ValueError("count supplied without a request")
            rows.append(row)
            continue
        payload_raw = _pinned(item["request"])
        payload = _payload(payload_raw)
        digest = sha(canonical(payload))
        row.update(payload_bytes=len(canonical(payload)), canonical_request_sha256=digest,
                   max_output_tokens=payload["max_tokens"], reason="count evidence missing")
        if item["count"] is not None:
            evidence = _json(_pinned(item["count"]))
            _keys(evidence, {"format", "request_id", "request_sha256", "inputs_sha256",
                             "method", "input_tokens"}, "saved count evidence")
            if (evidence["format"] != COUNT_FORMAT or evidence["method"] != "endpoint messages.count_tokens"
                    or evidence["request_id"] != identity or evidence["request_sha256"] != digest
                    or evidence["inputs_sha256"] != inputs_sha256):
                raise ValueError("saved count is not bound to this request and input inventory")
            verdict = window_status(evidence["input_tokens"], payload["max_tokens"], window, margin)
            row.update(verdict)
            row["reason"] = "saved count arithmetic against caller-declared capacity and margin"
            if item["basis"] == "scenario" or dry_run:
                row["arithmetic_status"] = verdict["status"]
                row["status"] = "UNKNOWN"
                row["reason"] = "scenario or dry-run cannot clear an exact request"
        rows.append(row)
    return {"format": "d4d_offline_sizing_report_v1", "manifest": pin(manifest_path, raw),
            "scope": manifest["scope"], "inputs": inputs, "inputs_sha256": inputs_sha256,
            "requests": rows, "full_run_readiness": "UNKNOWN",
            "scope_limit": "Only declared payloads checked; future stages, worker roster and record growth are not certified.",
            "binding_authority": "Caller-supplied pins and saved counts; not provider authentication.",
            "provider_support": "not checked", "billing": "not verified", "network_calls": 0,
            "launch_authorization": "none", "dry_run": dry_run}


def full_request(spec):
    """Render the production full-request body without execute(), a client or mocks."""
    from . import api_runner as api, receipt_completion as rc, shared_generation as sg
    settings = api._model_settings(spec.condition)
    captured = sg.preflight(spec, settings)
    request = api.build_phase(spec, "full", carry={})
    cap = api.phase_max_tokens(spec, "full", settings["max_tokens"], model=settings["name"])
    payload = rc.request_payload(request, settings, {"max_output_tokens": cap})
    sg.assert_current(spec)
    inputs = [pin(path, data) for path, data in captured.files]
    # Include runtime source in addition to the registration's captured inputs.
    for module in (api, rc, sg):
        selected = pin(module.__file__)
        if selected["path"] not in {item["path"] for item in inputs}:
            inputs.append(selected)
    return payload, sorted(inputs, key=lambda value: value["path"])


def _spec_from_registration(path):
    from . import api_runner as api, shared_generation as sg
    raw = _read(path)
    reg = sg.parse_registration(raw)
    if Path(path).absolute() != Path(reg["registration_path"]):
        raise ValueError("registration path differs from its declared authority")
    run, selected, source = reg["run"], reg["selection"], reg["inputs"]
    return api.RunSpec(**run, condition=selected["condition"], condition_stated=True,
        render_version=selected["renderer"], bundle=Path(source["bundle"]["path"]),
        chunk_manifest=Path(source["chunk_manifest"]["path"]),
        manifest=None if source["source_manifest"] is None else Path(source["source_manifest"]["path"]),
        profile=source["profile"]["name"], profile_basis=source["profile"]["basis"],
        runtime=api.RUNTIME, provider=reg["runtime"]["provider"],
        shared_generation_version=selected["version"], shared_generation_registration=raw.decode(),
        api_playbook_version=selected["api_playbook_version"],
        receipt_completion_version=selected["receipt_completion_version"],
        receipt_completion_registration=sg.canonical(reg["receipt"]).decode())


def prepare_full(registration, output_dir, *, context_limit_tokens, context_limit_basis,
                 required_margin_tokens, margin_basis):
    payload, inputs = full_request(_spec_from_registration(registration))
    window_status(0, payload["max_tokens"], context_limit_tokens, required_margin_tokens)
    _text(context_limit_basis, "context limit basis")
    _text(margin_basis, "margin basis")
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    request_path = output / "full-request.json"
    request_path.write_bytes(canonical(payload))
    row = {"id": "full", "phase": "full", "request": pin(request_path), "count": None,
           "basis": "exact", "context_limit_tokens": context_limit_tokens,
           "context_limit_basis": context_limit_basis, "required_margin_tokens": required_margin_tokens,
           "margin_basis": margin_basis}
    # Explicit placeholders prevent a single full request from looking like a
    # completed campaign sizing table. Workers need their actual eventual IDs.
    pending = [{**row, "id": phase, "phase": phase, "request": None} for phase in sorted(PHASES - {"full"})]
    manifest = {"format": FORMAT, "scope": "Production full request; later stages unconstructed",
                "inputs": inputs, "requests": [row, *pending]}
    path = output / "sizing-manifest.json"
    path.write_bytes(canonical(manifest))
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="review saved evidence; never call a provider")
    check.add_argument("manifest", type=Path)
    check.add_argument("--dry-run", action="store_true", help="keep request verdicts UNKNOWN")
    check.add_argument("--out", type=Path, help="create a new JSON report; refuse overwrite")
    prepare = commands.add_parser("prepare-full", help="export the registered production full request offline")
    prepare.add_argument("registration", type=Path)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--context-limit-tokens", type=int, required=True)
    prepare.add_argument("--context-limit-basis", required=True)
    prepare.add_argument("--required-margin-tokens", type=int, required=True)
    prepare.add_argument("--margin-basis", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare-full":
            path = prepare_full(args.registration, args.output_dir,
                context_limit_tokens=args.context_limit_tokens, context_limit_basis=args.context_limit_basis,
                required_margin_tokens=args.required_margin_tokens, margin_basis=args.margin_basis)
            print(path)
            return 0
        report = review(args.manifest, dry_run=args.dry_run)
        raw = canonical(report) + b"\n"
        if args.out:
            with args.out.open("xb") as stream:
                stream.write(raw)
        else:
            print(raw.decode(), end="")
        return 0 if all(row["status"] == "PASS" for row in report["requests"]) else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"offline sizing refused: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
