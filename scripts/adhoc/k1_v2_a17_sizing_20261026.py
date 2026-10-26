#!/usr/bin/env python3
"""K1 v2/A17 request sizing, 2026-10-26; refs #5155 and #5150.

Inputs: A16 analysis tree plus exact A17 audit_batches.py, retained original
records and prior K1 planning sensitivity. Outputs: pinned JSON request rows,
plans and payloads in a new analysis directory. No provider/tokenizer endpoint.
The inherited A1 receipt/index stand-ins and tiny synthetic audit answers remain
explicit sizing assumptions, not real model outputs or acceptance evidence.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types
from typing import Any


A16 = "56c41163f"
A17 = "8285172d0"
PLANNER = "src/data_sheets_schema/audit_batches.py"
SIZING_SOURCE = "src/data_sheets_schema/offline_sizing.py"
SIZING_COMMIT = "4c52b8e6f"
BUILDER_COMMIT = "502d5ce3f"
BUILDER_PATH = "scripts/build_api_registrations.py"
D39 = "5e198ba12"
A17_LIMITS = {"max_paths": 80, "max_inventory_bytes": 12_288, "max_workers": 16}
CHORUS_LIMITS = {**A17_LIMITS, "max_workers": 4}
LARGE = {"AI_READI", "CM4AI", "VOICE"}


class AnalysisError(RuntimeError):
    """A sizing-helper failure must not masquerade as production refusal."""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root)


def authority(root):
    """Require exactly the declared production composition, including worktree."""
    expected = git(root, "show", f"{A17}:{PLANNER}")
    actual = (root / PLANNER).read_bytes()
    if expected != actual:
        raise ValueError("planner differs from exact A17 commit bytes")
    changed = git(root, "diff", "--name-only", A16, "--", "src", "scripts/build_api_registrations.py").decode().splitlines()
    expected_sizing = git(root, "show", f"{SIZING_COMMIT}:{SIZING_SOURCE}")
    if (root / SIZING_SOURCE).read_bytes() != expected_sizing:
        raise ValueError("inherited sizing module differs from its exact cached source")
    if sorted(changed) != sorted([PLANNER, SIZING_SOURCE]):
        raise ValueError(f"unregistered production composition: {changed!r}")
    return {"base_commit": git(root, "rev-parse", A16).decode().strip(),
            "planner_commit": git(root, "rev-parse", A17).decode().strip(),
            "planner_git_blob": git(root, "rev-parse", f"{A17}:{PLANNER}").decode().strip(),
            "planner": pin(root / PLANNER),
            "inherited_sizing": {**pin(root / SIZING_SOURCE), "commit": SIZING_COMMIT},
            "later_D39_not_applied": git(root, "rev-parse", D39).decode().strip(),
            "tracked_production_delta_from_base": changed,
            "scope": "A16 runtime plus A17 planner only; not the full A17 branch or a launch candidate."}


def builder_sizer(root, m):
    """Compile only the exact cached builder's pure sizing declarations."""
    from dataclasses import dataclass
    import yaml
    raw = git(root, "show", f"{BUILDER_COMMIT}:{BUILDER_PATH}")
    source = ast.parse(raw)
    wanted = {"SizingRecord", "_typed_contracts", "render_typed_audit_inputs", "size_typed_audit_input"}
    constants = {"SIZING_INSTRUMENT", "SIZING_BYTES_PER_TOKEN", "SIZING_INPUT_TOKENS_PER_RESPONSE_TOKEN",
                 "_STAND_IN_DIGEST", "_SIZING_CATALOGS", "_BINDING_SCOPE", "_GENERATION_SCOPE", "PARTITION_KEYS"}
    selected = []
    for node in source.body:
        names = ({node.name} if isinstance(node, (ast.FunctionDef, ast.ClassDef)) else
                 {node.target.id} if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) else
                 {t.id for t in node.targets if isinstance(t, ast.Name)} if isinstance(node, ast.Assign) else set())
        if names & (wanted | constants):
            selected.append(node)
    found = {node.name for node in selected if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    if found != wanted:
        raise ValueError("cached #5155 sizing declarations differ")
    namespace = {"__name__": __name__, "Path": Path, "Any": Any, "dataclass": dataclass,
                 "copy": copy, "types": types, "json": json, "math": math, "yaml": yaml,
                 "api": m.api, "sg": m.sg, "rc": m.rc}
    selected_tree = ast.Module(body=selected, type_ignores=[])
    exec(compile(selected_tree, f"git:{BUILDER_COMMIT}:{BUILDER_PATH}", "exec"), namespace)
    return namespace, {"commit": git(root, "rev-parse", BUILDER_COMMIT).decode().strip(),
                       "path": BUILDER_PATH, "source_sha256": digest(raw),
                       "selected_ast_sha256": digest(ast.dump(selected_tree, include_attributes=False).encode()),
                       "declarations": sorted(wanted | constants),
                       "scope": "Exact #5155 pure sizing functions against this analysis composition; builder is not installed or used to admit a run."}


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
    return pin(path)


def plan_summary(batches, plan):
    inventory = plan["inventory"]["values"]
    values = {row["path"]: row for row in inventory}
    workers = []
    for worker in plan["workers"]:
        rows = [values[path] for path in worker["paths"]]
        size = len(batches.canonical_bytes(rows))
        if size != worker["inventory_bytes"]:
            raise AssertionError("worker inventory size does not match exact assigned rows")
        workers.append({"id": worker["id"], "paths": len(rows), "roots": worker["roots"],
                        "assigned_inventory_bytes": size,
                        "fraction_of_12288_inventory_bound": size / 12_288})
    return {"sha256": plan["sha256"], "limits": plan["limits"],
            "worker_count": len(workers), "workers": workers,
            "full_inventory_rows": len(inventory),
            "full_inventory_bytes": len(batches.canonical_bytes(plan["inventory"])),
            "full_inventory_values_bytes": len(batches.canonical_bytes(inventory)),
            "largest_worker_inventory_bytes": max(row["assigned_inventory_bytes"] for row in workers),
            "largest_worker_paths": max(row["paths"] for row in workers),
            "inventory_scope": "Assigned-row bound is not full request size or an output-token guarantee; every worker tail repeats the whole inventory."}


def worker_shared(m, payload, inner):
    shared = inner["payload"]["shared_context"]
    fields = json.loads(shared)
    trimmed = copy.deepcopy(payload)
    matched = 0
    for message in trimmed["messages"]:
        for part in message["content"]:
            if not isinstance(part, dict) or not isinstance(part.get("text"), str):
                continue
            header = "# Exact typed stage request\n\n"
            if part["text"].startswith(header):
                body = json.loads(part["text"][len(header):])
                if body != inner:
                    raise AssertionError("outer typed stage differs from exported request")
                body["payload"]["shared_context"] = ""
                part["text"] = header + m.sg.canonical(body).decode()
                matched += 1
    if matched != 1:
        raise AssertionError("worker requires one exact typed request block")
    return {"shared_context_utf8_bytes": len(shared.encode()),
            "shared_context_sha256": digest(shared.encode()),
            "shared_context_outer_payload_byte_contribution": len(m.sg.canonical(payload)) - len(m.sg.canonical(trimmed)),
            "shared_fields_utf8_bytes": {key: len(m.typed._json(value)) for key, value in fields.items()},
            "scope": "Shared semantic content; no cache breakpoint is installed. Field JSON sizes are diagnostic and not additive outer payload bytes."}


def aggregate(stages):
    values = list(stages)
    return {"call_count": len(values),
            "a1_estimated_input_tokens": sum(row["estimated_input_tokens"] for row in values),
            "a1_estimated_input_range": [sum(row["estimated_in_flight_range"][i] - row["max_output_tokens"]
                                                  for row in values) for i in (0, 1)],
            "placeholder_tokens": sum(row.get("placeholder_tokens", 0) for row in values),
            "payload_bytes": sum(row["payload_bytes"] for row in values),
            "scope": "One roster only, using inherited byte ratios and explicit carry assumptions; root cost model recalibrates expected outputs. Not a hard runtime bound or admission."}


def measure(sizing, m, project, label, files, limits, folder, summarize_payload, common_worker_prefix, builder):
    """Build once per staged scenario, retaining all requests and components."""
    folder.mkdir(parents=True, exist_ok=False)
    source_pins = {name: pin(path) for name, path in files.items() if path is not None}
    selected = {}
    for name, path in files.items():
        if path is None:
            selected[name] = None
            continue
        target = folder / "source_records" / (name + path.suffix)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        if pin(target)["sha256"] != source_pins[name]["sha256"]:
            raise ValueError("retained source changed during copy")
        selected[name] = target
    bundle, manifest, context, missing = sizing.inputs_for(m.root, project)
    output = {"project": project, "label": label, "arm": "baseline", "selected_limits": limits,
              "record_proxy_for": sizing.PROXY.get(project), "source_files": source_pins,
              "payloads": [], "measurements": {"status": "UNKNOWN", "stages": {}}}
    if missing:
        output["measurements"]["reason"] = "missing inputs: " + ", ".join(missing)
        return output
    try:
        spec, reg, settings, staging = sizing.stage_run(m, project, selected, bundle, manifest, context,
            limits, folder / "sizing", "2026-10-20a_claude-opus-5-api-generic-v10_rep1",
            proxy=project in sizing.PROXY)
    except Exception as exc:
        output["measurements"].update(status="REFUSED", reason=f"registration/staging: {type(exc).__name__}: {exc}")
        return output
    measured = output["measurements"]
    measured.update(status="MEASURED", staging=staging, audit_limits=reg["audit_limits"],
                    bundle_bytes=bundle.stat().st_size, original_full_bytes=files["original_full"].stat().st_size,
                    thinking=settings["thinking"], label=label, record_project=sizing.PROXY.get(project, project))
    output["registration"] = pin(folder / "sizing" / f"{project}_registration.json")
    output["registration_input_authority"] = reg
    staged = Path(spec.out_dir) / "intermediate" / f"{project}_full.yaml"
    output["staged_original_full"] = pin(staged)
    output["source_files_unchanged"] = all(pin(value["path"]) == value for value in source_pins.values())
    if not output["source_files_unchanged"]:
        raise RuntimeError("retained source changed during sizing")

    def retain(name, payload, *, phase, placeholder_tokens=0, placeholder_sources=None, inner=None):
        raw = m.sg.canonical(payload)
        path = folder / "payloads" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
        try:
            row = {"name": name, "phase": phase, "payload": pin(path),
                   "max_output_tokens": payload["max_tokens"], "placeholder_tokens": placeholder_tokens,
                   "placeholder_sources": placeholder_sources or {},
                   "parts": summarize_payload(payload)}
            if inner is not None:
                row["shared_prefix"] = worker_shared(m, payload, inner)
        except Exception as exc:
            raise AnalysisError(f"request diagnostic failed for {name}: {exc}") from exc
        output["payloads"].append(row)
        return row

    count, audit_floor = limits["max_workers"], None
    measured["findings_basis"] = "max_workers: typed stage refused"
    try:
        with sizing.offline_receipt_and_index(m):
            packet = m.tar.prepare_packet(spec)
            output["plan"] = plan_summary(m.audit_batches, packet["plan"])
            output["plan_artifact"] = save_json(folder / "plan.json", packet["plan"])
            workers, envelopes, worker_payloads = [], {}, []
            for worker in packet["plan"]["workers"]:
                stage = {"phase": m.tar.WORKER_PHASE, "worker_id": worker["id"]}
                _, payload, inner = m.tar.build_request(spec, packet, stage, workers={}, omission=None, settings=settings)
                floor = sizing.response_floor(packet["plan"], worker,
                    lambda raw, plan, worker_id: m.audit_batches.check_worker(raw, plan, worker_id, version=2))
                request = retain(worker["id"], payload, phase=m.tar.WORKER_PHASE, inner=inner)
                worker_payloads.append(payload)
                row = {"worker_id": worker["id"], "paths": len(worker["paths"]),
                       "inventory_bytes": worker["inventory_bytes"], "response_floor": floor,
                       "response_floor_tokens_at_4_bytes": sizing.floor_tokens(floor["bytes"]),
                       "request_name": request["name"],
                       **sizing.estimate(project, m.tar.WORKER_PHASE, len(m.sg.canonical(payload)), payload["max_tokens"])}
                workers.append(row)
                if floor["passed"]:
                    answer = sizing.floor_variants(packet["plan"], worker)[floor["variant"]]
                    envelopes[worker["id"]] = m.typed.capture_response(inner, answer)
            _, omission, _ = m.tar.build_request(spec, packet, {"phase": m.tar.OMISSION_PHASE}, workers={}, omission=None, settings=settings)
            retain("omission", omission, phase=m.tar.OMISSION_PHASE)
            integrations = []
            for index, answers in enumerate([{}, envelopes] if len(envelopes) == len(workers) else [{}]):
                _, payload, _ = m.tar.build_request(spec, packet, {"phase": m.tar.INTEGRATION_PHASE},
                    workers=answers, omission=b"", settings=settings)
                integrations.append(payload)
                tokens = (sum(w["max_output_tokens"] for w in workers) if index == 0 else 0) + omission["max_tokens"]
                retain("integration_caps" if index == 0 else "integration_floor", payload,
                       phase=m.tar.INTEGRATION_PHASE, placeholder_tokens=tokens,
                       placeholder_sources={"worker_outputs": sum(w["max_output_tokens"] for w in workers) if index == 0 else 0,
                                            "omission_response": omission["max_tokens"]})
            output["current_wire_common_worker_prefix"] = common_worker_prefix(worker_payloads)
            output["hypothetical_shared_prefix_identical"] = len({r["shared_prefix"]["shared_context_sha256"]
                for r in output["payloads"] if "shared_prefix" in r}) == 1
        count = len(workers)
        measured.update(findings_basis="this run's worker count", typed={"status": "MEASURED", "worker_count": count, "workers": workers})
        measured["stages"]["typed_audit_omission"] = sizing.estimate(project, "typed_audit_omission",
            sizing.nbytes(m, omission), omission["max_tokens"])
        measured["stages"]["typed_audit_integration"], chosen = sizing.integration_estimate(m, project, workers, omission, integrations)
        output["selected_integration_payload_sha256"] = digest(m.sg.canonical(chosen))
        output["derived_typed_aggregate"] = aggregate([*workers, measured["stages"]["typed_audit_omission"],
                                                       measured["stages"]["typed_audit_integration"]])
        if len(integrations) > 1:
            audit_floor = sizing.floor_assembly(m.audit_batches, packet["plan"])
        measured["audit_floor_bytes"] = len(audit_floor.encode()) if audit_floor is not None else None
        if audit_floor is not None:
            measured["audit_floor_terminal_check"] = sizing.terminal_check(m, spec, packet, audit_floor)
    except Exception as exc:
        if isinstance(exc, (AnalysisError, AssertionError)):
            raise
        measured["typed"] = {"status": "REFUSED", "reason": f"{type(exc).__name__}: {exc}"}
    try:
        capture = m.sg.assert_current(spec)
        record = builder["SizingRecord"](full=staged,
            core=Path(spec.out_dir) / "intermediate" / f"{project}_core.yaml",
            receipt=Path(spec.out_dir) / f"{project}_coverage_receipt.yaml")
        side = builder["size_typed_audit_input"](project, reg["audit_limits"], reg,
            sizing_record=record, context=Path(reg["inputs"]["context"]["path"]).read_bytes(),
            schema_snapshot=capture.full_schema)
        output["builder_5155_allowance"] = {"status": "SIZED", **side,
            "scope": "Largest permitted roster at max_workers, 2 bytes/input token and 3.5 input tokens/response token. Separate from actual-roster costs; not a validated future output bound.",
            "actual_typed_status": measured.get("typed", {}).get("status")}
    except Exception as exc:
        output["builder_5155_allowance"] = {"status": "REFUSED", "reason": f"{type(exc).__name__}: {exc}"}
    try:
        ordinary, bases = sizing.measure_ordinary(m, project, spec, settings, reg, selected, count, audit_floor)
        for phase, (payload, placeholder) in ordinary.items():
            family = "report_regate" if phase == "report_regate_with_v8_report" else phase
            sources = {}
            if placeholder:
                if phase == "full_receipt_completion_after_readdress":
                    sources["readdress_response"] = placeholder
                else:
                    rejected = sizing.cap(m, spec, settings, "report") if phase == "report_regate" else 0
                    sources = {"assembled_audit": placeholder - rejected, "rejected_report": rejected}
            retain(phase, payload, phase=family, placeholder_tokens=placeholder, placeholder_sources=sources)
            measured["stages"][phase] = sizing.estimate(project, family, sizing.nbytes(m, payload),
                                                       payload["max_tokens"], placeholder_tokens=placeholder)
            if phase in bases:
                measured["stages"][phase]["carry_basis"] = bases[phase]
        measured["stages"]["report_after_repair"] = {**measured["stages"]["report"],
            "note": "Same request as report, sized from reconciled proxy records."}
    except Exception as exc:
        if isinstance(exc, (AnalysisError, AssertionError)):
            raise
        measured["ordinary"] = {"status": "REFUSED", "reason": f"{type(exc).__name__}: {exc}"}
    output["source_files_unchanged"] = all(pin(value["path"]) == value for value in source_pins.values())
    if not output["source_files_unchanged"]:
        raise RuntimeError("retained source changed during measurement")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--historical-root", required=True, type=Path)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--projects", nargs="+")
    parser.add_argument("--modes", nargs="+", choices=("a17", "k1_minimum"), default=["a17", "k1_minimum"])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--primary-only", action="store_true")
    group.add_argument("--nonprimary-only", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    workdir = args.workdir.resolve()
    if not workdir.is_relative_to(root):
        raise ValueError("measurement scratch must stay inside the selected tree")
    sys.path[:0] = [str(root), str(root / "src")]
    from scripts import offline_sizing as sizing
    from scripts.adhoc.k1_size_requests_20261025 import chorus_files
    from scripts.adhoc.k1_v2_request_parts_20261026 import summarize_payload, common_worker_prefix
    sizing.block_network()
    os.chdir(root)
    os.environ.pop("D4D_RECEIPT_FULL_MAX_TOKENS", None)
    composition = authority(root)
    m = sizing.load(root)
    builder, builder_authority = builder_sizer(root, m)
    from data_sheets_schema import resources
    if Path(resources.resource_root()[0]).resolve() != root:
        raise ValueError("resource origin differs from selected tree")
    context = root / "data/omission_contexts/kids_first_omission_context.json"
    kids_pin = pin(context)
    def actual_kids_context(project, *, context_path, write_to_disk, **kwargs):
        if project != "KIDS_FIRST" or write_to_disk is not True or pin(context) != kids_pin:
            raise ValueError("unproved Kids First context staging")
        Path(context_path).write_bytes(context.read_bytes())
        return json.loads(context.read_bytes())
    m.build_draft_context = actual_kids_context
    prior_path = root / "notes/k1_cost_model_2026-10-25/plan-sensitivity.json"
    prior = json.loads(prior_path.read_bytes())
    primary_path = root / "notes/k1_cost_model_2026-10-25/request-sizing-primary.json"
    primary = json.loads(primary_path.read_bytes())
    workdir.mkdir(parents=True, exist_ok=False)
    report = {"format": "k1_v2_a17_requests_v1", "complete": False, "composition": composition,
              "analysis_head": git(root, "rev-parse", "HEAD").decode().strip(),
              "script": pin(__file__), "prior_planning": pin(prior_path), "source_helper": pin(sizing.__file__),
              "component_helper": pin(root / "scripts/adhoc/k1_v2_request_parts_20261026.py"),
              "builder_sizing_authority": builder_authority, "prior_primary": pin(primary_path),
              "kids_context": kids_pin, "rows": [],
              "limits": ["Historical conformed records are proxies for unknown v10 outputs.",
                         "Kids First uses actual current context, with AI_READI record/minimal receipt proxy; incompatibility remains a refusal.",
                         "A1 receipt recovery and omission-index stand-ins remain active only during offline request construction.",
                         "Carry floors and registered caps are scenarios, not a hard total context or cost bound.",
                         "No typed cache breakpoint is implemented; shared-byte exports support a hypothetical comparison.",
                         "Later D39 contract text/digest changes are not applied; this is not current final launch wire."]}
    for project in args.projects or sizing.PROJECTS:
        labels = sizing.RUNS[sizing.PROXY.get(project, project)]
        if project == "CHORUS":
            labels = ["2026-10-22a_claude-opus-5-api-generic-v10_rep1", "2026-10-20a_claude-opus-5-api-generic-v10_rep1"]
        primary_label = labels[0]
        if args.nonprimary_only:
            labels = labels[1:] if project in LARGE else []
        elif project != "CHORUS" and (args.primary_only or project not in LARGE):
            labels = labels[:1]
        for label in labels:
            files = (chorus_files(args.historical_root.resolve(), label) if project == "CHORUS"
                     else sizing.run_files(root, sizing.PROXY.get(project, project), label))
            if project == "CHORUS":
                matched = next(row for row in primary["rows"] if row["project"] == project and row["label"] == label)
                prior_row = {"planning": {"componentwise_minimum": CHORUS_LIMITS},
                             "staged_sha256": matched["staged_record_sha256"]}
            else:
                prior_row = next(row for row in prior["projects"][project]["rows"] if row["label"] == label)
            for mode in args.modes:
                limits = (CHORUS_LIMITS if project == "CHORUS" else A17_LIMITS if mode == "a17"
                          else prior_row["planning"]["componentwise_minimum"])
                folder = workdir / project / label / mode
                row = measure(sizing, m, project, label, files, dict(limits), folder,
                              summarize_payload, common_worker_prefix, builder)
                row.update(plan_mode=mode, primary=label == primary_label,
                           prior_k1_plan_limits=prior_row["planning"]["componentwise_minimum"],
                           prior_k1_staged_sha256=prior_row["staged_sha256"])
                if row.get("staged_original_full", {}).get("sha256") not in (None, prior_row["staged_sha256"]):
                    raise ValueError("staged record differs from prior K1 planning authority")
                report["rows"].append(row)
                report["network_attempts"] = list(sizing.NETWORK_ATTEMPTS)
                partial = args.out.with_suffix(args.out.suffix + ".partial")
                partial.parent.mkdir(parents=True, exist_ok=True)
                partial.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
                print(f"{project} {label} {mode}: {sizing._summary(row['measurements'])}", flush=True)
    if authority(root) != composition or sizing.loaded_from(root) or sizing.NETWORK_ATTEMPTS or pin(context) != kids_pin:
        raise RuntimeError("source, origin, context, or network invariant changed")
    for key in ("script", "source_helper", "component_helper"):
        if pin(report[key]["path"]) != report[key]:
            raise RuntimeError(f"analysis helper changed during sizing: {key}")
    report["runtime_module_files_after"] = {name: pin(module.__file__) for name, module in list(sys.modules.items())
        if name.split(".")[0] in ("data_sheets_schema", "scripts") and getattr(module, "__file__", None)}
    report["runtime_pin_scope"] = "Source snapshots after construction; selected module origins and tracked production composition verified before/after. Does not attest arbitrary runtime injection."
    report["complete"] = True
    save_json(args.out, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
