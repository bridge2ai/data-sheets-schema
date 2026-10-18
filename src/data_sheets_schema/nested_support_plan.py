"""Opt-in offline nested support plans; no provider, results or cache execution."""
from __future__ import annotations

from collections import Counter
import importlib.metadata
import json
import math
from pathlib import Path
import sys

from data_sheets_schema import evidence_score, schema_digest, support_judge, support_targets as nested
from data_sheets_schema import support_plan as common
from data_sheets_schema.duplicate_keys import find_duplicate_keys
from data_sheets_schema.evaluation_model import same_family_label
from data_sheets_schema.profiles import profile_named
from data_sheets_schema.schema_snapshot import capture_schema

FORMAT = "d4d-support-plan-v2"
STRATA = ("relationship_edge", "attribute_value", "fitness_top_level")
SCENARIOS = ("uncached", "cache_miss_every_request", "warm_within_record")
BLOCKERS = ["independent_empirical_calibration_3343", "context_projection_review_3342",
            "instrument_review_3342", "scientific_control_acceptance",
            "v3_response_and_execution_registration", "provider_transport_registration",
            "paid_run_authorization"]


def _vocabulary(profile, override: Path | None):
    path = Path(override) if override is not None else profile.pin_path
    raw = path.read_bytes() if path is not None else None
    if raw is None:
        return {}, None, None, "explicit_profile_without_vocabulary"
    if find_duplicate_keys(raw.decode("utf-8")):
        raise common.PlanError("vocabulary snapshot contains duplicate keys")
    document = common._mapping(raw, "vocabulary snapshot")
    vocabularies = document.get("vocabularies")
    if not isinstance(vocabularies, dict) or any(
            not isinstance(name, str) or not name or not isinstance(terms, dict) or not terms or
            any(not isinstance(k, str) or not isinstance(v, str) for k, v in terms.items())
            for name, terms in vocabularies.items()):
        raise common.PlanError("vocabulary snapshot requires named nonempty term-to-label mappings")
    return vocabularies, raw, path, "explicit_vocabulary_override" if override is not None else "explicit_profile_pin"


def _totals():
    return {scenario: Counter(input=0, cache_write=0, cache_read=0, output=0) for scenario in SCENARIOS}


def _request_counts(request, *, support: bool, first: bool):
    encoded = common.canonical(request)
    estimated = math.ceil(len(encoded) / 4)
    prefix = (math.ceil(len((request["system"] + request["messages"][0]["content"][0]["text"]).encode()) / 4)
              if support else 0)
    output = request["max_tokens"]
    return encoded, estimated, prefix, {
        "uncached": dict(input=estimated, cache_write=0, cache_read=0, output=output),
        "cache_miss_every_request": dict(input=estimated-prefix, cache_write=prefix, cache_read=0, output=output),
        "warm_within_record": dict(input=estimated-prefix, cache_write=prefix if first else 0,
                                   cache_read=0 if first else prefix, output=output)}


def build_nested_plan(roster: Path, output: Path, *, model: str | None,
                      profile: str, class_name: str, schema_path: Path | None,
                      max_tokens: int, prices: Path | None, root: Path,
                      artifact_kind: str | None, vocabulary_path: Path | None,
                      relationship_policy: str = nested.POLICY,
                      context_policy: str = nested.CONTEXT_POLICY) -> dict:
    """Pin and render draft nested support plus separate top-level fitness.

    One explicit artifact kind/schema/profile per plan. No v2 support request,
    measured verdict, provider transport or judgement-cache reuse is produced.
    """
    instrument, system = nested.policy_instrument(relationship_policy, context_policy=context_policy)
    scalar_policy = relationship_policy == nested.SCALAR_POLICY
    root, output = Path(root).resolve(), Path(output)
    if output.exists() or output.is_symlink():
        raise common.PlanError(f"output already exists: {output}")
    if artifact_kind not in ("full", "core", "collection"):
        raise common.PlanError("plan version 2 requires explicit artifact_kind: full, core or collection")
    if (artifact_kind == "core" and class_name == "Dataset" or
            artifact_kind != "core" and class_name == "CoreDataset"):
        raise common.PlanError("artifact kind and full/core root class disagree")
    if schema_path is None and class_name not in schema_digest.CLASS_SCHEMA:
        raise common.PlanError("this root class requires an explicit schema path")
    if artifact_kind == "collection" and class_name == "Dataset":
        raise common.PlanError("collection requires an explicit collection root class and schema")
    if type(max_tokens) is not int or max_tokens < 1:
        raise common.PlanError("max_tokens must be a positive integer")
    artifacts = common.Artifacts()
    settings = common.plan_model_selection(model, artifacts)
    model = settings["name"]
    price = common._prices(prices, model, artifacts)
    roster_raw = Path(roster).read_bytes()
    grouped, pins = common._roster_records(roster_raw)
    for _identity, jobs in grouped.values():
        if any("artifact_kind" in job and job["artifact_kind"] != artifact_kind for job in jobs):
            raise common.PlanError("roster artifact kind disagrees with the plan")
    selected_profile = profile_named(profile)
    vocabulary, vocabulary_raw, vocabulary_file, vocabulary_basis = _vocabulary(selected_profile, vocabulary_path)
    path = schema_digest.resolve_schema(schema_path or schema_digest.CLASS_SCHEMA[class_name])
    before = capture_schema(path, strict=True)
    captured = nested.NestedSupportSchema.from_schema(path, root_class=class_name, vocabulary=vocabulary)
    generation, fitness_inventory = schema_digest.build_for_judgement(class_name, path)
    fitness_specs = {slot.name: evidence_score._render_slot_spec(slot.name, fitness_inventory, vocabulary)
                     for slot in fitness_inventory.slots}
    fitness_artifact = artifacts.put(json.dumps({"class": class_name, "slots": fitness_specs}, sort_keys=True).encode())
    generation_digest = schema_digest.fingerprint(schema_digest.render(generation, vocabulary=vocabulary))
    if capture_schema(path, strict=True).key != before.key or (
            vocabulary_file is not None and vocabulary_file.read_bytes() != vocabulary_raw):
        raise common.PlanError("schema or vocabulary changed during planning")
    schema_sources = [{"import_key": key, "path": str(source), **artifacts.put(content)}
                      for key, source, content in before.sources]
    records, targets, recovered, missing_joins, all_blocked = [], [], {}, [], []
    representation_issues = []
    totals = _totals()
    by_stratum = {stratum: _totals() for stratum in STRATA}

    def add_request(base, request, *, support, first, stratum):
        encoded, estimated, prefix, counts = _request_counts(request, support=support, first=first)
        for scenario, count in counts.items():
            totals[scenario].update(count)
            by_stratum[stratum][scenario].update(count)
        targets.append({**base, "status": "planned_not_measured", "propagated": False,
                        "request_recipe": common._recipe(request, artifacts),
                        "request_sha256": common.sha256(encoded), "request_bytes": len(encoded),
                        "estimated_input_tokens": estimated, "estimated_cache_prefix_tokens": prefix,
                        "output_token_ceiling": max_tokens,
                        "result_contract": "unregistered_v3_no_cache_or_executor" if support else "legacy_top_level_fitness"})

    for input_path, (identity, jobs) in sorted(grouped.items()):
        project, label, method, cohort, replicate = identity
        record_raw, record_pin, record, provenance_pin, bundle_raw, bundle_pin, bundle, generator = common._record_inputs(
            root, input_path, identity, jobs, pins, artifacts, recovered, artifact_kind=artifact_kind)
        inventory = nested.inventory_targets(record_raw, captured, artifact_kind=artifact_kind,
                                             relationship_policy=relationship_policy,
                                             context_policy=context_policy)
        inventory_doc = inventory.to_dict()
        # This is a plan, not an executable target inventory: only the engineering
        # planner-integration blocker has been completed here.
        inventory_doc["readiness_blockers"] = [b for b in inventory_doc["readiness_blockers"]
                                              if b != "nested_planner_integration_3342"]
        inventory_pin = artifacts.put(common.canonical(inventory_doc))
        record_id = common.sha256(common.canonical({"input": input_path, "identity": identity,
                                                   "artifact_kind": artifact_kind, "plan_format": FORMAT}))[:24]
        blocked = [{"record_id": record_id, "axis": nested.AXIS, **row} for row in inventory_doc["blocked"]]
        populated = sorted(slot for slot, value in record.items() if support_judge.populated(value))
        fitness_slots = [slot for slot in populated if slot in fitness_specs]
        for slot in sorted(set(populated) - fitness_specs.keys()):
            blocked.append({"record_id": record_id, "axis": "fitness", "pointer": "/" + nested._token(slot),
                            "code": "unknown_top_level_slot"})
        all_blocked.extend(blocked)
        join_jobs = []
        for job in jobs:
            join_path = common._relative(root, job["output"])
            entry = {k: job[k] for k in ("id", "rubric", "output")}
            if join_path.is_file():
                entry.update(result_artifact=artifacts.put(join_path.read_bytes()), status="captured_for_later_join")
            else:
                entry.update(result_artifact=None, status="unavailable_locally; materialize sparse paths if tracked")
                missing_joins.append(job["output"])
            join_jobs.append(entry)
        records.append({"id": record_id, "project": project, "label": label, "method": method,
                        "cohort": cohort, "generation_rep": replicate, "artifact_kind": artifact_kind,
                        "record": record_pin, "provenance": provenance_pin, "bundle": bundle_pin,
                        "generator": generator, "same_family": same_family_label(model, generator),
                        "populated_top_level_fields": len(populated),
                        "support_targets_by_kind": inventory_doc["eligible_by_kind"],
                        "fitness_top_level_targets": len(fitness_slots),
                        "blocked_paths": blocked, "blocked_count": len(blocked),
                        "inventory": inventory_pin, "rubric_join_jobs": join_jobs})
        if scalar_policy:
            issues = [{"record_id": record_id, **row} for row in inventory_doc["representation_issues"]]
            records[-1].update(representation_issues=issues, representation_issue_count=len(issues))
            representation_issues.extend(issues)
        fitness_ids = {slot: f"{record_id}:fitness:/{nested._token(slot)}" for slot in fitness_slots}
        for ordinal, target in enumerate(inventory.targets):
            payload = target.to_dict()
            pointer, kind = payload["pointer"], payload["kind"]
            root_slot = nested.pointer_tokens(pointer)[0]
            # Inventory catalog stores the full specification once per record.
            # The recipe stores the exact expanded request, independently hashed.
            target_pin = artifacts.put(target.payload_json.encode())
            base = {"id": f"{record_id}:{nested.AXIS}:{kind}:{pointer}", "record_id": record_id,
                    "axis": nested.AXIS, "kind": kind, "pointer": pointer,
                    "value_sha256": payload["value_sha256"], "context_sha256": payload["context_sha256"],
                    "specification_ref": payload["specification_ref"], "target_artifact": target_pin,
                    "inventory_artifact": inventory_pin,
                    "fitness_mapping": {**payload["fitness"], "target_id": fitness_ids.get(root_slot),
                                        "status": "planned_top_level_only" if root_slot in fitness_ids else "blocked"}}
            request = nested.render_request(target, bundle=bundle, model=model, max_tokens=max_tokens)
            add_request(base, request, support=True, first=ordinal == 0, stratum=kind)
        for slot in fitness_slots:
            value = record[slot]
            request = evidence_score.fitness_request_arguments(model=model, max_tokens=max_tokens,
                       slot=slot, value=value, specification=fitness_specs[slot])
            context = evidence_score.JudgementContext(axis="fitness", model=model,
                rubric=evidence_score.digest_of(request["system"]), corpus="", schema=generation_digest,
                specification=fitness_artifact["sha256"])
            add_request({"id": fitness_ids[slot], "record_id": record_id, "axis": "fitness",
                         "kind": "top_level_field", "pointer": "/" + nested._token(slot),
                         "value_sha256": common.sha256(common.value_identity(value)),
                         "judgement_context": context.as_entry(), "specification_artifact": fitness_artifact},
                        request, support=False, first=False, stratum="fitness_top_level")

    source_files = ["nested_support_plan.py", "support_targets.py", "support_plan.py", "support_judge.py",
                    "evidence_score.py", "schema_digest.py", "schema_snapshot.py", "schema_view.py",
                    "profiles.py", "evaluation_model.py", "duplicate_keys.py", "api_runner.py", "resources.py"]
    blockers = list(BLOCKERS)
    if all_blocked:
        blockers.append("unresolved_target_paths")
    if missing_joins:
        blockers.append("missing_rubric_join_artifacts")

    def scenarios(counts):
        return {name: {"tokens": dict(count), "estimated_usd": common._cost(count, price)}
                for name, count in counts.items()}

    support_counts = Counter({kind: 0 for kind in nested.KINDS})
    for row in records:
        support_counts.update(row["support_targets_by_kind"])
    manifest = {
        "format": FORMAT, "mode": "offline_dry_run", "granularity": "nested_support_and_top_level_fitness",
        "artifact_kind": artifact_kind, "value_identity_encoding": "typed-yaml-v1",
        "readiness": {"ready_for_paid_run": False, "blockers": blockers,
                      "missing_rubric_join_artifacts": sorted(set(missing_joins)),
                      "calibration": "not_performed; software fixtures are not empirical evidence",
                      "schema_validation": "not_performed; selected schema used for target resolution"},
        "roster": {"path": str(roster), **artifacts.put(roster_raw)},
        "planning_code": {"commit": common._git(common.ROOT, "rev-parse", "HEAD").decode().strip(),
                          "source_worktree_dirty": bool(common._git(common.ROOT, "status", "--porcelain", "--",
                              *(f"src/data_sheets_schema/{name}" for name in source_files)).strip()),
                          "files": {name: artifacts.put((common.ROOT / "src/data_sheets_schema" / name).read_bytes()) for name in source_files}},
        "environment": {"python": sys.version.split()[0],
                        "packages": {name: importlib.metadata.version(name) for name in ("PyYAML", "linkml-runtime")}},
        "input_repository_commit": common._git(root, "rev-parse", "HEAD").decode().strip(), "model": settings,
        "schema": {"class": class_name, "profile": profile, "profile_basis": "explicit", "sources": schema_sources,
                   "nested_specification": artifacts.put(captured.payload_json.encode()),
                   "nested_specification_sha256": captured.digest,
                   "fitness_specifications": fitness_artifact, "generation_digest": generation_digest,
                   "vocabulary": artifacts.put(vocabulary_raw) if vocabulary_raw is not None else None,
                   "vocabulary_path": str(vocabulary_file) if vocabulary_file is not None else None,
                   "vocabulary_basis": vocabulary_basis, "vocabulary_names": sorted(vocabulary)},
        "instruments": {nested.AXIS: {"name": instrument, "policy": relationship_policy,
                                      "system": artifacts.put(system.encode())},
                        "fitness": {"name": "LLMSlotFitnessScorer", "granularity": "top_level_field",
                                    "system": artifacts.put(evidence_score.FITNESS_SYSTEM.encode())}},
        "request_boundary": "pure renderer keyword arguments, before unregistered provider transport; canonical UTF-8 JSON, not wire bytes",
        "records": records, "targets": targets, "blocked_paths": all_blocked,
        "counts": {"records": len(records), "populated_top_level_fields": sum(r["populated_top_level_fields"] for r in records),
                   "axis_targets": len(targets), "by_axis": dict(Counter(t["axis"] for t in targets)),
                   "support_by_kind": dict(support_counts), "fitness_top_level": sum(r["fitness_top_level_targets"] for r in records),
                   "blocked": len(all_blocked), "blocked_by_axis": dict(Counter(b["axis"] for b in all_blocked)),
                   "blocked_by_cause": dict(Counter(b["code"] for b in all_blocked))},
        "estimate": {"method": "ceil(canonical request UTF-8 bytes / 4); heuristic, not token count or spend cap",
                     "assumptions": ["one attempt per target; retries excluded", "no judgement-cache reuse credited",
                                     "warm support prefix written once per record across both support kinds, subsequent targets read it",
                                     "prefix includes system plus source block; provider support, expiry and minimum size unverified",
                                     "fitness has no cached source block; fitness does not become a nested verdict",
                                     "output ceiling uses requested max_tokens; transport may cap it"],
                     "prices": price, "scenarios": scenarios(totals),
                     "by_stratum": {name: scenarios(count) for name, count in by_stratum.items()}},
    }
    if context_policy != nested.CONTEXT_POLICY:
        manifest["instruments"][nested.AXIS]["context_policy"] = context_policy
    if scalar_policy:
        manifest["representation_issues"] = representation_issues
        manifest["counts"]["representation_issue_count"] = len(representation_issues)
    encoded_manifest = json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    output.mkdir()
    (output / "artifacts").mkdir()
    for digest, data in artifacts.blobs.items():
        (output / "artifacts" / digest).write_bytes(data)
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        stream.write(encoded_manifest)
    return manifest
