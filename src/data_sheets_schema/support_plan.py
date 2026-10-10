"""Offline typed-support/fitness plans (#3341), never an execution route.

The roster is a reference-rescore manifest: primary jobs identify records and
``pinned_files`` binds their bytes. Repeated rubric jobs share one input, but
no judgement is propagated between distinct records. Content-addressed copies
make historical recovery and exact request inspection independent of originals.
"""
from __future__ import annotations

import base64
import copy
from datetime import date, datetime
import hashlib
import importlib.metadata
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from data_sheets_schema import evaluation_model, evidence_score, support_judge, support_targets
from data_sheets_schema.evaluation_model import evaluation_model_settings, same_family_label
from data_sheets_schema.profiles import profile_named
from data_sheets_schema.resources import git_env
from data_sheets_schema.schema_snapshot import capture_schema

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROSTER = Path("notes/reference_rescore_2026-09-11/manifest.json")
FORMAT = "d4d-support-plan-v1"
BLOCKERS = ["nested_granularity_decision_3342", "independent_empirical_calibration_3343",
            "provider_transport_registration", "paid_run_authorization"]


class PlanError(ValueError):
    """An offline plan cannot bind its evidence or requested configuration."""


def canonical(value: Any) -> bytes:
    """Versioned plan JSON encoding, not an SDK wire serialization."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def value_identity(value: Any) -> bytes:
    """Deterministic typed YAML value identity, separate from request JSON.

    Every node is tagged, so a native date cannot collide with either its
    quoted spelling or a mapping that happens to resemble an encoding tag.
    The live judges' YAML rendering and legacy cache keys remain unchanged.
    """
    def node(item):
        if item is None:
            return ["null"]
        if isinstance(item, bool):
            return ["bool", item]
        if isinstance(item, int):
            return ["int", str(item)]
        if isinstance(item, float):
            return ["float", item.hex()]
        if isinstance(item, datetime):  # datetime is a subclass of date.
            return ["datetime", item.isoformat(timespec="microseconds")]
        if isinstance(item, date):
            return ["date", item.isoformat()]
        if isinstance(item, str):
            return ["str", item]
        if isinstance(item, bytes):
            return ["bytes", base64.b64encode(item).decode("ascii")]
        if isinstance(item, dict):
            pairs = [[node(k), node(v)] for k, v in item.items()]
            return ["map", sorted(pairs, key=lambda pair: canonical(pair[0]))]
        if isinstance(item, list):
            return ["list", [node(v) for v in item]]
        if isinstance(item, set):
            return ["set", sorted((node(v) for v in item), key=canonical)]
        raise PlanError(f"unsupported YAML value type: {type(item).__name__}")
    return canonical(node(value))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Artifacts:
    def __init__(self):
        self.blobs: dict[str, bytes] = {}

    def put(self, data: bytes) -> dict:
        digest = sha256(data)
        self.blobs[digest] = data
        return {"sha256": digest, "bytes": len(data)}

    def text(self, text: str) -> dict:
        return {"$text": self.put(text.encode("utf-8"))}


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, env=git_env())
    if result.returncode:
        raise PlanError(f"git {args[0]} failed: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout


def _relative(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise PlanError(f"expected a repository-relative path: {value!r}")
    path = root / value
    if ".." in Path(value).parts or not path.resolve().is_relative_to(root.resolve()):
        raise PlanError(f"path leaves the input repository: {value!r}")
    return path


def _matches(data: bytes, pins: dict) -> bool:
    return all(hashlib.new(algorithm, data).hexdigest() == expected
               for algorithm, expected in pins.items())


def _pinned(root: Path, relative: str, pins: dict, artifacts: Artifacts) -> tuple[bytes, dict]:
    path = _relative(root, relative)
    if not pins or any(not isinstance(value, str) or
                       not re.fullmatch(r"[0-9a-f]{%d}" % (32 if key == "md5" else 64), value)
                       for key, value in pins.items()) or set(pins) - {"md5", "sha256"}:
        raise PlanError(f"missing or malformed original hash: {relative}")
    current = path.read_bytes() if path.is_file() else None
    data, commit = current, None
    if data is None or not _matches(data, pins):
        # Full history, including merged sides; never silently replace a pin
        # with today's bytes, and never interpret shallow history as complete.
        if _git(root, "rev-parse", "--is-shallow-repository").strip() != b"false":
            raise PlanError(f"cannot recover {relative}: complete Git history required")
        data = None
        for candidate in _git(root, "log", "--full-history", "--format=%H", "--", relative).decode().splitlines():
            # A deletion commit has no blob at this path. A failed object read
            # otherwise remains an error rather than evidence of absence.
            if not _git(root, "ls-tree", candidate, "--", relative).strip():
                continue
            content = _git(root, "show", f"{candidate}:{relative}")
            if _matches(content, pins):
                data, commit = content, candidate
                break
        if data is None:
            raise PlanError(f"cannot recover recorded hashes for {relative}")
    return data, {"path": relative, "recorded_hashes": pins,
                  "basis": "git_recovery" if commit else "current_matches_pin",
                  "recovery_commit": commit,
                  "current_sha256": sha256(current) if current is not None else None,
                  "md5": hashlib.md5(data).hexdigest(), **artifacts.put(data)}


def _mapping(data: bytes, name: str) -> dict:
    value = yaml.safe_load(data)
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise PlanError(f"expected a mapping with string keys: {name}")
    return value


def _recipe(request: dict, artifacts: Artifacts) -> dict:
    result = copy.deepcopy(request)
    result["system"] = artifacts.text(result["system"])
    for message in result["messages"]:
        if isinstance(message["content"], str):
            message["content"] = artifacts.text(message["content"])
        else:
            for part in message["content"]:
                part["text"] = artifacts.text(part["text"])
    return result


def _expand(value: Any, directory: Path) -> Any:
    if isinstance(value, dict):
        if set(value) == {"$text"}:
            pin = value["$text"]
            digest = pin.get("sha256", "")
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise PlanError("invalid artifact SHA-256")
            path = directory / "artifacts" / digest
            if not path.resolve().is_relative_to(directory.resolve()):
                raise PlanError("artifact escapes plan directory")
            content = path.read_bytes()
            if sha256(content) != digest or len(content) != pin["bytes"]:
                raise PlanError(f"artifact has changed: {digest}")
            return content.decode("utf-8")
        return {k: _expand(v, directory) for k, v in value.items()}
    return [_expand(v, directory) for v in value] if isinstance(value, list) else value


def materialize_request(directory: Path, target_id: str) -> dict:
    """Verify and reconstruct one pinned call's arguments, without a provider."""
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") not in (FORMAT, "d4d-support-plan-v2"):
        raise PlanError("unknown plan format")
    targets = [t for t in manifest["targets"] if t["id"] == target_id]
    if len(targets) != 1:
        raise PlanError(f"expected one target named {target_id!r}")
    target = targets[0]
    request = _expand(target["request_recipe"], directory)
    encoded = canonical(request)
    if sha256(encoded) != target["request_sha256"] or len(encoded) != target["request_bytes"]:
        raise PlanError("reconstructed request does not match its pin")
    return request


def _prices(path: Path | None, model: str, artifacts: Artifacts) -> dict | None:
    if path is None:
        return None
    raw = Path(path).read_bytes()
    price = json.loads(raw)
    if (not isinstance(price, dict) or price.get("model") != model or
            price.get("currency") != "USD" or price.get("per_tokens") != 1_000_000 or
            not isinstance(price.get("source"), str) or not price["source"].strip() or
            not isinstance(price.get("as_of"), str) or not price["as_of"].strip()):
        raise PlanError("prices require matching model, USD per 1000000 tokens, source and as_of")
    rates = price.get("rates")
    if not isinstance(rates, dict) or set(rates) - {"input", "output", "cache_read", "cache_write"}:
        raise PlanError("invalid price rates")
    for rate in rates.values():
        if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate < 0:
            raise PlanError("price rates must be finite nonnegative numbers; omit unknown rates")
    return {**price, "artifact": artifacts.put(raw), "basis": "user_supplied_unverified"}


def _cost(tokens: dict, price: dict | None) -> float | None:
    if price is None or any(count and kind not in price["rates"] for kind, count in tokens.items()):
        return None
    return round(sum(count * price["rates"].get(kind, 0) / 1_000_000
                     for kind, count in tokens.items()), 8)


def plan_model_selection(model: str | None, artifacts: Artifacts) -> dict:
    """Bind one validated evaluator and the exact config used to select it."""
    try:
        settings = (evaluation_model.model_selection(model) if model is not None
                    else copy.deepcopy(evaluation_model_settings()))
    except ValueError as error:
        raise PlanError(str(error)) from error
    if not isinstance(settings["name"], str) or not settings["name"].strip():
        raise PlanError("model must be a nonempty identifier")
    if "configuration" in settings:
        try:
            config_raw = evaluation_model.CONFIG_PATH.read_bytes()
        except OSError as error:
            raise PlanError("evaluation config became unavailable after model selection") from error
        if sha256(config_raw) != settings["configuration"]["sha256"]:
            raise PlanError("evaluation config changed after model selection")
        settings["configuration"]["artifact"] = artifacts.put(config_raw)
    return settings


def _roster_records(roster_raw: bytes) -> tuple[dict, dict]:
    """Shared roster identity checks; no artifact selection or mutation."""
    donor = json.loads(roster_raw)
    if not isinstance(donor, dict) or not isinstance(donor.get("jobs"), list):
        raise PlanError("roster must contain a jobs list")
    pins = donor.get("pinned_files", {})
    if not isinstance(pins, dict):
        raise PlanError("roster pinned_files must be a mapping")
    grouped, ids, identities = {}, set(), {}
    for job in donor["jobs"]:
        if not isinstance(job, dict):
            raise PlanError("roster jobs must be mappings")
        if job.get("purpose") != "primary":
            continue
        required = ("id", "input", "project", "label", "method", "cohort", "generation_rep", "rubric", "output")
        if any(k not in job for k in required):
            raise PlanError(f"incomplete primary job: {job.get('id')}")
        if any(not isinstance(job[k], str) or not job[k].strip()
               for k in required if k != "generation_rep") or (
                type(job["generation_rep"]) is not int or job["generation_rep"] < 1):
            raise PlanError("primary job identity fields must be nonempty strings and replicate a positive integer")
        if job["id"] in ids:
            raise PlanError(f"duplicate primary job: {job['id']}")
        ids.add(job["id"])
        identity = tuple(job[k] for k in ("project", "label", "method", "cohort", "generation_rep"))
        key = job["input"]
        if identity in identities and identities[identity] != key:
            raise PlanError(f"multiple inputs for one record identity: {identity}")
        identities[identity] = key
        if key in grouped and any(j.get("provenance") != job.get("provenance") for j in grouped[key][1]):
            raise PlanError(f"conflicting provenance paths for {key}")
        if key in grouped and grouped[key][0] != identity:
            raise PlanError(f"conflicting identities for {key}")
        grouped.setdefault(key, (identity, []))[1].append(job)
    if not grouped:
        raise PlanError("roster has no primary records")

    return grouped, pins


def _record_inputs(root, input_path, identity, jobs, pins, artifacts, recovered_files, *,
                   artifact_kind="full"):
    """Shared immutable input/provenance/bundle recovery; never infer schema or kind."""
    project, label, method, cohort, replicate = identity
    record_raw, record_pin = _pinned(root, input_path, {"sha256": pins.get(input_path)}, artifacts)
    record = _mapping(record_raw, input_path)
    first = jobs[0]
    provenance_path = first.get("provenance") or (
        f"data/d4d_concatenated/{method}_core/{label}/{project}_provenance.yaml")
    if provenance_path in pins:
        provenance_raw, provenance_pin = _pinned(
            root, provenance_path, {"sha256": pins[provenance_path]}, artifacts)
    else:
        # The historical rubric-only roster did not pin provenance. Bind
        # exactly the local snapshot used, without claiming roster lineage.
        provenance_raw = _relative(root, provenance_path).read_bytes()
        provenance_pin = {"path": provenance_path, "recorded_hashes": {},
                          "basis": "captured_current_unpinned_by_roster",
                          "recovery_commit": None, **artifacts.put(provenance_raw)}
    provenance = _mapping(provenance_raw, provenance_path)
    run = provenance.get("run", {})
    if any(run.get(k) != v for k, v in (("project", project), ("label", label), ("method", method))):
        raise PlanError(f"provenance identity disagrees with roster: {provenance_path}")
    if "replicate" in run and run["replicate"] != replicate:
        raise PlanError(f"provenance replicate disagrees with roster: {provenance_path}")
    declared_full = provenance.get("outputs", {}).get(artifact_kind, {}).get("path")
    if declared_full is not None and declared_full != input_path:
        raise PlanError(f"provenance {artifact_kind}-record path disagrees with roster: {provenance_path}")
    inputs = provenance.get("inputs", {})
    bundle_path = inputs.get("bundle_path") or inputs.get("bundle")
    bundle_pins = {k: inputs[f"bundle_{k}"] for k in ("md5", "sha256") if inputs.get(f"bundle_{k}")}
    bundle_key = (bundle_path, tuple(sorted(bundle_pins.items())))
    if bundle_key not in recovered_files:
        recovered_files[bundle_key] = _pinned(root, bundle_path, bundle_pins, artifacts)
    bundle_raw, bundle_pin = recovered_files[bundle_key]
    bundle = bundle_raw.decode("utf-8")
    if not bundle.strip():
        raise PlanError(f"empty support bundle: {bundle_path}")
    generator = provenance.get("model", {}).get("model")
    return record_raw, record_pin, record, provenance_pin, bundle_raw, bundle_pin, bundle, generator


def build_plan(roster: Path, output: Path, *, model: str | None = None,
               profile: str, class_name: str = "Dataset", schema_path: Path | None = None,
               max_tokens: int = 8000, prices: Path | None = None,
               root: Path = ROOT, plan_version: int = 1,
               artifact_kind: str | None = None, vocabulary_path: Path | None = None,
               relationship_policy: str = support_targets.POLICY,
               context_policy: str = support_targets.CONTEXT_POLICY) -> dict:
    """Freeze a fresh offline plan. Failure never changes existing artifacts.

    ``root`` anchors roster paths and recovery history. Profile selection is
    explicit, so ambient study/neutral defaults cannot change the instrument.
    All inputs are validated before creating the exclusive output directory.
    """
    if type(plan_version) is not int or plan_version not in (1, 2):
        raise PlanError("plan_version must be 1 or 2")
    if plan_version == 2:
        from data_sheets_schema.nested_support_plan import build_nested_plan
        return build_nested_plan(roster, output, model=model, profile=profile,
            class_name=class_name, schema_path=schema_path, max_tokens=max_tokens,
            prices=prices, root=root, artifact_kind=artifact_kind, vocabulary_path=vocabulary_path,
            relationship_policy=relationship_policy, context_policy=context_policy)
    if relationship_policy != support_targets.POLICY:
        raise PlanError("nondefault relationship_policy requires plan_version=2")
    if type(context_policy) is not str or context_policy != support_targets.CONTEXT_POLICY:
        raise PlanError("nondefault context_policy requires plan_version=2")
    if artifact_kind is not None or vocabulary_path is not None:
        raise PlanError("artifact_kind and vocabulary_path require plan_version=2")
    root, output = Path(root).resolve(), Path(output)
    if output.exists() or output.is_symlink():
        raise PlanError(f"output already exists: {output}")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1:
        raise PlanError("max_tokens must be a positive integer")
    artifacts = Artifacts()
    settings = plan_model_selection(model, artifacts)
    model = settings["name"]
    selected_profile = profile_named(profile)
    price = _prices(prices, model, artifacts)
    roster_raw = Path(roster).read_bytes()
    grouped, pins = _roster_records(roster_raw)

    from data_sheets_schema import schema_digest
    path = schema_digest.resolve_schema(schema_path or schema_digest.CLASS_SCHEMA[class_name])
    before = capture_schema(path, strict=True)
    vocabulary_raw = (selected_profile.pin_path.read_bytes()
                      if selected_profile.pin_path is not None else None)
    schema, inventory, vocabulary, specification = evidence_score.slot_specification_snapshot(
        class_name, path, profile=selected_profile)
    if capture_schema(path, strict=True).key != before.key or (
            vocabulary_raw is not None and selected_profile.pin_path.read_bytes() != vocabulary_raw):
        raise PlanError("schema or vocabulary changed during planning")
    specs = {s.name: evidence_score._render_slot_spec(s.name, inventory, vocabulary)
             for s in inventory.slots}
    nested = {n.name for n in inventory.nested}
    relationships = {s.name for s in inventory.slots if s.inlined or s.range in nested}
    schema_sources = [{"import_key": key, "path": str(source), **artifacts.put(content)}
                      for key, source, content in before.sources]
    # Use the instrument's own byte encoding, not the request encoding, so
    # the captured specification artifact hashes to its cache identity.
    spec_artifact = artifacts.put(json.dumps({"class": class_name, "slots": specs},
                                             sort_keys=True).encode("utf-8"))
    if spec_artifact["sha256"] != specification:
        raise PlanError("rendered specifications disagree with the captured instrument")
    records, targets = [], []
    recovered_files = {}
    missing_joins = []
    totals = {name: Counter(input=0, cache_write=0, cache_read=0, output=0)
              for name in ("uncached", "cache_miss_every_request", "warm_within_record")}
    for input_path, (identity, jobs) in sorted(grouped.items()):
        project, label, method, cohort, replicate = identity
        record_raw, record_pin, record, provenance_pin, bundle_raw, bundle_pin, bundle, generator = _record_inputs(
            root, input_path, identity, jobs, pins, artifacts, recovered_files)
        populated = [slot for slot, value in record.items() if support_judge.populated(value)]
        unknown = sorted(set(populated) - specs.keys())
        if unknown:
            raise PlanError(f"unknown populated slots in {input_path}: {unknown}")
        record_id = sha256(canonical({"input": input_path, "identity": identity}))[:24]
        join_jobs = []
        for job in jobs:
            join_path = _relative(root, job["output"])
            entry = {k: job[k] for k in ("id", "rubric", "output")}
            if join_path.is_file():
                entry["result_artifact"] = artifacts.put(join_path.read_bytes())
                entry["status"] = "captured_for_later_join"
            else:
                entry["result_artifact"] = None
                entry["status"] = "unavailable_locally; materialize sparse paths if tracked"
                missing_joins.append(job["output"])
            join_jobs.append(entry)
        row = {"id": record_id, "project": project, "label": label, "method": method,
               "cohort": cohort, "generation_rep": replicate, "record": record_pin,
               "provenance": provenance_pin,
               "bundle": bundle_pin, "generator": generator,
               "same_family": same_family_label(model, generator),
               "populated_top_level_fields": len(populated), "axis_targets": len(populated) * 2,
               "targets_by_axis": {support_judge.AXIS: len(populated), "fitness": len(populated)},
               "rubric_join_jobs": join_jobs}
        records.append(row)
        first_support = True
        for slot in sorted(populated):
            value = record[slot]
            vctx = support_judge.build_value_context(record, slot, relationship=slot in relationships)
            requests = {
                support_judge.AXIS: support_judge.request_arguments(
                    model=model, max_tokens=max_tokens, bundle=bundle,
                    value_text=support_judge.render_request(slot, value, specs[slot], vctx)),
                "fitness": evidence_score.fitness_request_arguments(
                    model=model, max_tokens=max_tokens, slot=slot, value=value, specification=specs[slot])}
            for axis, request in requests.items():
                encoded = canonical(request)
                estimated_input = math.ceil(len(encoded) / 4)
                prefix = (math.ceil(len((request["system"] + request["messages"][0]["content"][0]["text"]).encode("utf-8")) / 4)
                          if axis == support_judge.AXIS else 0)
                cold = dict(input=estimated_input, cache_write=0, cache_read=0, output=max_tokens)
                misses = dict(input=estimated_input-prefix, cache_write=prefix, cache_read=0, output=max_tokens)
                warm = dict(input=estimated_input-prefix, cache_write=prefix if first_support else 0,
                            cache_read=0 if first_support else prefix, output=max_tokens)
                if axis == support_judge.AXIS:
                    first_support = False
                for scenario, count in (("uncached", cold), ("cache_miss_every_request", misses), ("warm_within_record", warm)):
                    totals[scenario].update(count)
                context = evidence_score.JudgementContext(
                    axis=axis, model=model, rubric=evidence_score.digest_of(request["system"]),
                    corpus=evidence_score.digest_of(bundle) if axis == support_judge.AXIS else "",
                    schema=schema if axis == "fitness" else "", specification=specification)
                target_id = f"{record_id}:{axis}:{slot}"
                targets.append({"id": target_id, "record_id": record_id, "axis": axis,
                                "pointer": "/" + slot.replace("~", "~0").replace("/", "~1"),
                                "value_sha256": sha256(value_identity(value)),
                                "value_context_digest": vctx.digest() if axis == support_judge.AXIS else None,
                                "judgement_context": context.as_entry(), "propagated": False,
                                "status": "planned_not_measured", "request_recipe": _recipe(request, artifacts),
                                "request_sha256": sha256(encoded), "request_bytes": len(encoded),
                                "estimated_input_tokens": estimated_input, "estimated_cache_prefix_tokens": prefix,
                                "output_token_ceiling": max_tokens,
                                "intended_cache": f"results/{record_id}/{axis}.jsonl"})

    code_root = ROOT
    source_files = ["support_plan.py", "support_judge.py", "evidence_score.py", "schema_digest.py",
                    "schema_snapshot.py", "profiles.py", "evaluation_model.py", "duplicate_keys.py",
                    "api_runner.py", "resources.py"]
    manifest = {
        "format": FORMAT, "mode": "offline_dry_run", "granularity": "top_level_field",
        "value_identity_encoding": "typed-yaml-v1",
        "readiness": {"ready_for_paid_run": False, "blockers": list(BLOCKERS) + (["missing_rubric_join_artifacts"] if missing_joins else []),
                      "missing_rubric_join_artifacts": sorted(set(missing_joins)),
                      "calibration": "not_performed; software fixtures are not empirical evidence"},
        "roster": {"path": str(roster), **artifacts.put(roster_raw)},
        "planning_code": {"commit": _git(code_root, "rev-parse", "HEAD").decode().strip(),
                          "source_worktree_dirty": bool(_git(code_root, "status", "--porcelain", "--",
                              *(f"src/data_sheets_schema/{name}" for name in source_files)).strip()),
                          "files": {name: artifacts.put((code_root / "src/data_sheets_schema" / name).read_bytes()) for name in source_files}},
        "environment": {"python": sys.version.split()[0],
                        "packages": {name: importlib.metadata.version(name) for name in ("PyYAML", "linkml-runtime")}},
        "input_repository_commit": _git(root, "rev-parse", "HEAD").decode().strip(),
        "model": settings,
        "schema": {"class": class_name, "profile": profile, "profile_basis": "explicit",
                   "generation_digest": schema, "specification_sha256": specification,
                   "rendered_specifications": spec_artifact, "sources": schema_sources,
                   "vocabulary": artifacts.put(vocabulary_raw) if vocabulary_raw is not None else None},
        "instruments": {support_judge.AXIS: {"name": support_judge.INSTRUMENT,
                                           "system": artifacts.put(support_judge.SUPPORT_V2_SYSTEM.encode())},
                        "fitness": {"name": "LLMSlotFitnessScorer", "system": artifacts.put(evidence_score.FITNESS_SYSTEM.encode())}},
        "request_boundary": "_call_with_retry keyword arguments, before provider transport; canonical UTF-8 JSON, not wire bytes",
        "records": records, "targets": targets,
        "counts": {"records": len(records), "populated_top_level_fields": sum(r["populated_top_level_fields"] for r in records),
                   "axis_targets": len(targets), "by_axis": dict(Counter(t["axis"] for t in targets))},
        "canary_record_ids": [next(r["id"] for r in records if r["project"] == project) for project in sorted({r["project"] for r in records})],
        "estimate": {"method": "ceil(canonical request UTF-8 bytes / 4); heuristic, not token count or spend cap",
                     "assumptions": ["one attempt per target; retries excluded", "no judgement-cache reuse credited",
                                     "warm scenario: support prefix written once per record, subsequent fields read it",
                                     "prefix includes system plus source block; provider support, expiry and minimum size unverified",
                                     "fitness has no cached source block", "output ceiling uses requested max_tokens; transport may cap it"],
                     "prices": price,
                     "scenarios": {name: {"tokens": dict(count), "estimated_usd": _cost(count, price)} for name, count in totals.items()}},
    }
    # Validate final serializability before publishing any artifact. A failed
    # write leaves an incomplete fresh directory without manifest.json; no
    # existing plan or original is ever removed to make room for a retry.
    encoded_manifest = json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    output.mkdir()
    (output / "artifacts").mkdir()
    for digest, data in artifacts.blobs.items():
        (output / "artifacts" / digest).write_bytes(data)
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        stream.write(encoded_manifest)
    return manifest
