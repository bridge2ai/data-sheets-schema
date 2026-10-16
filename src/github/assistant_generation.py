#!/usr/bin/env python3
"""Prepare one GitHub request for the registered shared API pipeline (#2088).

Inputs are immutable Git checkouts, explicit operational limits and a provider
selection. Outputs are a fresh attempt directory, caller authority and an
offline request capture. No client, network request or scientific approval is
created here. The workflow executes the ordinary ``d4d api run`` command.
"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

try:
    from . import assistant_bundle
except ImportError:  # direct execution from the trusted checkout
    import assistant_bundle


class PreparationError(ValueError):
    """A named refusal that is safe to include in the workflow log."""


PROVIDERS = {
    "anthropic": ("Anthropic", "https://api.anthropic.com", "ANTHROPIC_API_KEY"),
    "cborg": ("LBL CBORG (proxy to Anthropic)", "https://api.cborg.lbl.gov", "CBORG_API_KEY"),
}


def provider_selection(name, *, require_credential=False):
    if name not in PROVIDERS:
        raise PreparationError("select exactly one supported assistant provider")
    provider, endpoint, key_env = PROVIDERS[name]
    present = [key for _, _, key in PROVIDERS.values() if os.environ.get(key)]
    if len(present) > 1 or (present and key_env not in present):
        raise PreparationError("credential environment conflicts with selected provider")
    if require_credential and key_env not in present:
        raise PreparationError("selected provider credential is missing: " + key_env)
    return {"provider": provider, "base_url": endpoint, "key_env": key_env}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreparationError("duplicate limits key")
        result[key] = value
    return result


def _nonfinite(_value):
    raise PreparationError("nonfinite limits value")


def load_limits(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64000:
        raise PreparationError("limits must be a bounded regular JSON file")
    raw = path.read_bytes()
    value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    if (type(value) is not dict or set(value) != {
            "format", "max_bundle_bytes", "audit_limits", "receipt_limits"}
            or value["format"] != "d4d_assistant_limits_v1"):
        raise PreparationError("assistant limits fields do not match v1")
    cap = value["max_bundle_bytes"]
    if type(cap) is not int or not 0 < cap <= 8_000_000:
        raise PreparationError("max_bundle_bytes must be an integer in 1..8000000")
    if (type(value["receipt_limits"]) is not dict or set(value["receipt_limits"]) != {
            "max_output_tokens", "max_request_bytes", "context_limit_tokens", "context_limit_basis"}):
        raise PreparationError("receipt_limits fields do not match v1")
    # The shared registration parser validates all nested contract values.
    return value, raw


def _git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if result.returncode:
        raise PreparationError("cannot verify the declared Git checkout")
    return result.stdout


def _check_commit(root, commit):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise PreparationError("checkout commit must be an immutable full Git SHA")
    if _git(root, "rev-parse", "HEAD").decode().strip() != commit:
        raise PreparationError("declared commit does not match checkout HEAD")


def _source_tree(source, directory, commit):
    """Every ingested file must belong to the declared commit, including hidden files."""
    prefix = directory.relative_to(source).as_posix() + "/"
    entries = {}
    for row in _git(source, "ls-tree", "-r", "-z", "--full-tree", commit, "--", prefix).split(b"\0"):
        if not row:
            continue
        head, name = row.split(b"\t", 1)
        mode, kind, identity = head.split()
        relative = name.decode("utf-8")[len(prefix):]
        if mode not in (b"100644", b"100755") or kind != b"blob":
            raise PreparationError("input Git tree contains a non-regular document")
        entries[relative] = identity.decode("ascii")
    return entries


def _verify_source_manifest(source, directory, commit, manifest):
    expected = _source_tree(source, directory, commit)
    members = {member["path"] for member in manifest["members"]}
    if members != set(expected):
        raise PreparationError("input membership differs from the declared source commit")
    for member in manifest["members"]:
        raw = (directory / member["path"]).read_bytes()
        object_hash = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if (object_hash != expected[member["path"]]
                or hashlib.sha256(raw).hexdigest() != member["raw_sha256"]):
            raise PreparationError("input content differs from the declared source commit")


@contextmanager
def _cwd(path):
    previous = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(previous)


def _write(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)


def frame_members(bundle, manifest):
    """Versioned outer boundaries prevent embedded FILE labels bleeding into a sibling.

    Document bytes are never escaped or rewritten. Their internal FILE/PATH
    pairs remain structural subdivisions; only the committed outer member is
    evidence of the physical input's origin.
    """
    result = bytearray(b"# D4D assistant complete input bundle v2\n")
    manifest = copy.deepcopy(manifest)
    for ordinal, member in enumerate(manifest["members"], 1):
        content = bundle[member["content_start"]:member["content_end"]]
        member["section_start"] = len(result)
        filename = json.dumps(member["path"], ensure_ascii=False)
        origin = json.dumps(manifest["input_directory"] + "/" + member["path"], ensure_ascii=False)
        header = ("FILE: " + filename + "\nPATH: " + origin + "\n"
                  + "# Source " + str(ordinal) + "; format " + member["format"]
                  + "; " + member["conversion"]["kind"] + "\n\n")
        result.extend(header.encode("utf-8"))
        member["content_start"] = len(result)
        result.extend(content)
        member["content_end"] = len(result)
        result.extend(b"\n# End source\n")
        member["section_end"] = len(result)
    raw = bytes(result)
    manifest["format"] = "d4d-assistant-input-manifest-v2"
    manifest["bundle"] = {"format": "d4d-assistant-input-bundle-v2", "bytes": len(raw),
                          "sha256": hashlib.sha256(raw).hexdigest()}
    return raw, manifest


def chunk_origins(bundle, chunks, manifest):
    """Bind every canonical chunk to its physical member, independent of its label."""
    lines = bundle.split(b"\n")
    # Canonical chunking splits only LF, retaining CR/Unicode separators as data.
    offsets, position = [0], 0
    for line in lines[:-1]:
        position += len(line) + 1
        offsets.append(position)
    if lines[-1]:
        offsets.append(position + len(lines[-1]))
    origins = []
    for chunk in chunks["chunks"]:
        start, end = chunk["lines"]
        first, last = offsets[start - 1], offsets[end]
        owners = [row["path"] for row in manifest["members"]
                  if row["section_start"] <= first and last <= row["section_end"]]
        if not owners and last <= manifest["members"][0]["section_start"]:
            member = None
        elif len(owners) == 1:
            member = owners[0]
        else:
            raise PreparationError("canonical chunk spans ambiguous physical source members")
        origins.append({"chunk": chunk["id"], "member": member})
    return origins


def prepare(*, inputs_root, source_checkout, dataset, source_commit, trusted_commit,
            attempt_id, attempt_dir, provider, limits, require_credential=False):
    """Return workflow outputs after validating and capturing one complete attempt."""
    from data_sheets_schema import api_runner as api, chunking, shared_generation as shared
    from data_sheets_schema import receipt_completion
    from data_sheets_schema.cli.api import ARMS
    from data_sheets_schema.resources import resource_path
    from data_sheets_schema.schema_snapshot import capture_schema

    if assistant_bundle.NAME.fullmatch(dataset) is None or not re.fullmatch(r"[1-9][0-9]*-[1-9][0-9]*", attempt_id):
        raise PreparationError("invalid dataset or GitHub run-attempt identity")
    trusted = Path.cwd().resolve()
    _check_commit(trusted, trusted_commit)
    source = Path(source_checkout).resolve(strict=True)
    _check_commit(source, source_commit)
    inputs_root = Path(inputs_root).absolute()
    directory = inputs_root / dataset
    if source not in directory.resolve().parents:
        raise PreparationError("input directory must belong to the selected source checkout")
    route = provider_selection(provider, require_credential=require_credential)
    bounds, bounds_raw = load_limits(limits)
    attempt = Path(attempt_dir).absolute()
    if any(c in str(attempt) for c in "\r\n") or ".." in attempt.parts:
        raise PreparationError("attempt directory must have a normalized single-line path")
    if attempt.is_symlink() or attempt.exists() or attempt.parent.resolve() != attempt.parent:
        raise PreparationError("attempt directory must be new and have a real parent")
    if source == attempt or source in attempt.parents:
        raise PreparationError("attempt directory must be outside the source checkout")
    attempt.mkdir()
    authority = attempt / "authority"
    authority.mkdir()
    outputs = attempt / "outputs"
    outputs.mkdir()
    label = "assistant-" + attempt_id + "-generic_v10"
    # Only ingestion sees the source checkout as cwd. All prompt/schema readers
    # run in the trusted checkout, including external PR requests.
    with _cwd(source):
        bundle, manifest = assistant_bundle.prepare(inputs_root, dataset, authority, source_commit)
    _verify_source_manifest(source, directory, source_commit, manifest)
    bundle, manifest = frame_members(bundle, manifest)
    if len(bundle) > bounds["max_bundle_bytes"]:
        raise PreparationError("complete bundle exceeds assistant max_bundle_bytes; no truncation")
    bundle_path = authority / "bundle.txt"
    chunks_path = authority / "chunk_manifest.json"
    context_path = authority / "scope_context.json"
    registration_path = authority / "registration.json"
    _write(bundle_path, bundle)
    _write(authority / "input_manifest.json", shared.canonical(manifest))
    _write(authority / "limits.json", bounds_raw)
    chunks = chunking.manifest_from_bytes(bundle, bundle_path.name)
    _write(chunks_path, shared.canonical(chunks))
    context = {"format": "omission_context_v1", "root_class": "Dataset",
        "scopes": [{"owner": "", "referent": "Dataset described by the supplied input documents",
                    "release": None, "scope": "Only the supplied documents; dataset identity, release and member relationships are not declared by the request."}],
        "source_policy": {"priority": [], "basis": "No external source manifest or source-priority declaration was supplied.",
            "chunk_origins": chunk_origins(bundle, chunks, manifest),
            "chunk_origin_basis": "Physical input members verified against source commit " + source_commit
                + "; null denotes bundle framing. FILE/PATH labels within a member are literal structural text, not independent file-origin authority."},
        "vocabulary": {}}
    _write(context_path, shared.canonical(context))
    settings = api._model_settings()
    arm, method = ARMS["baseline"][:2]
    registration = {"format": shared.FORMAT, "registration_id": "github-assistant-" + attempt_id,
        "registration_path": str(registration_path), "selection": shared.descriptor(),
        "run": {"project": dataset, "arm": arm, "method": method, "label": label},
        "inputs": {"project": dataset, "bundle": shared.file_pin(bundle_path),
            "chunk_manifest": shared.file_pin(chunks_path), "source_manifest": None,
            "context": shared.file_pin(context_path),
            "profile": {"name": "neutral", "basis": "stated by the caller", "vocabulary": None},
            "full_schema": shared.schema_pin(capture_schema(api.FULL_SCHEMA_PATH, strict=True)),
            "core_schema": shared.schema_pin(capture_schema(api.CORE_SCHEMA_PATH, strict=True))},
        "runtime": {"provider": route["provider"], "base_url": route["base_url"],
            "model": settings["name"], "temperature": settings["temperature"] if api.accepts_temperature(settings["name"]) else None,
            "thinking": settings.get("thinking"), "effort": settings.get("effort"),
            "config": shared.file_pin(resource_path(settings["config_path"])) if settings.get("config_path") else None},
        "audit_limits": bounds["audit_limits"],
        "audit_transport": {"transport_attempts": 1, "sdk_max_retries": 0, "malformed_response_retries": 0},
        "receipt": {"format": "receipt_completion_registration_v2", "registration_id": "github-assistant-receipt-" + attempt_id,
            "condition": "generic_v10", "runtime_policy_sha256": receipt_completion.policy_identity(version=2)["sha256"],
            "receipt_instrument_version": 4, **bounds["receipt_limits"],
            "coverage_floor": {"state": "pending", "mode": "diagnostic_pilot"}}}
    raw_registration = shared.canonical(registration)
    shared.parse_registration(raw_registration)
    _write(registration_path, raw_registration)
    spec = api.RunSpec(project=dataset, arm=arm, method=method, label=label,
        bundle=bundle_path, chunk_manifest=chunks_path, manifest=None, profile="neutral",
        profile_basis="stated by the caller", out_dir=outputs, condition="generic_v10", render_version=25,
        provider=route["provider"], api_playbook_version=2, receipt_completion_version=2,
        receipt_completion_registration=shared.canonical(registration["receipt"]).decode(),
        shared_generation_version=1, shared_generation_registration=raw_registration.decode())
    spec.bind_api_header_values(settings)
    captured = shared.preflight(spec, settings)
    full_request = api.build_phase(spec, "full", carry={})
    _write(attempt / "prepared_full_request.json", shared.canonical(asdict(full_request)))
    _write(attempt / "rendered_instruction.txt", spec.instruction.encode())
    # Absolute execution paths are retained as identities. Content-addressed
    # copies make the artifact independently inspectable after the runner dies;
    # this is an archive, not permission to rebase or resume the registration.
    snapshots = attempt / "captured_authority"
    snapshots.mkdir()
    index = []
    files = list(captured.files) + list(shared.captured_assets().items())
    for original, raw in files:
        digest = shared.sha(raw)
        target = snapshots / digest
        if not target.exists():
            _write(target, raw)
        index.append({"original_path": original, "sha256": digest, "bytes": len(raw), "archive_path": "captured_authority/" + digest})
    _write(snapshots / "index.json", shared.canonical(index))
    metadata = {"format": "d4d_assistant_preparation_v1", "trusted_commit": trusted_commit,
        "source_commit": source_commit, "dataset": dataset, "attempt_id": attempt_id,
        "label": label, "provider": route, "registration": shared.file_pin(registration_path),
        "limits": shared.file_pin(authority / "limits.json"),
        "scientific_approval": "unverified", "coverage_floor": "pending diagnostic pilot",
        "full_request_sha256": shared.sha((attempt / "prepared_full_request.json").read_bytes()),
        "source_policy": "external bundle; neutral profile; no source manifest"}
    _write(attempt / "preparation.json", shared.canonical(metadata))
    shared.assert_current(spec)
    return {"registration": str(registration_path), "output-dir": str(outputs), "label": label,
        "attempt-dir": str(attempt), "input-manifest": str(authority / "input_manifest.json"),
        "full-path": str(spec.full_path), "core-path": str(spec.core_path)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs-root", "source-checkout", "dataset", "source-commit", "trusted-commit",
                 "attempt-id", "attempt-dir", "provider", "limits", "github-output"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--require-credential", action="store_true")
    args = vars(parser.parse_args(argv))
    github_output = Path(args.pop("github_output"))
    try:
        outputs = prepare(**args)
        with github_output.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("".join(key + "=" + value + "\n" for key, value in outputs.items()))
        print("Prepared registered shared generation: " + outputs["label"])
        return 0
    except Exception as exc:
        # Source/parser payloads and environment credentials never enter logs.
        reason = str(exc) if isinstance(exc, PreparationError) else type(exc).__name__
        print("Assistant registration preparation failed: " + reason, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
