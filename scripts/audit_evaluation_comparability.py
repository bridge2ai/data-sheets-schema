#!/usr/bin/env python3
"""Audit historical evaluation identity/condition gaps without rewriting evidence.

Purpose: deterministic Step E0/E4 inventory for #2911, #2912 and #1077.
Inputs: selected checkout's generation provenance/artifacts, two direct
label_aware stores and explicit registered-rating directories; selected targets.
Outputs: JSON or Markdown on stdout only. No scoring, provider calls or writes.
Date: 2026-10-23; registered ingestion serves #5125. Other retained ratings need review;
an absent qualifying rating here does not prove no such rating exists elsewhere.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_DOWN
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_sheets_schema import agent_pin
from data_sheets_schema.evaluation_context import context_digest, normalize_context, unwrap_document
from data_sheets_schema.evaluation.validate import validate_evaluation
from data_sheets_schema.evaluation.run_identity import same_run, blinding_identity, forbidden_blinding_identities
from data_sheets_schema.evaluation.cohort_manifest import read_cohort
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from data_sheets_schema.semantic_scope import validate_scope

RUBRICS = ("rubric10", "rubric20")
MAX_BYTES = 32 * 1024 * 1024
MAX_REGISTERED_BYTES = 256 * 1024 * 1024
HEX = re.compile(r"[0-9a-fA-F]{64}\Z")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def mapping(value):
    return value if isinstance(value, dict) else {}


def pre_three_version(value):
    """Flag numeric earlier versions without treating arbitrary tags as versions."""
    return (isinstance(value, str)
            and re.fullmatch(r"[0-2](?:\.\d+)*", value) is not None)


def read(path):
    """Bound reads and refuse symlink escapes; caller selects canonical paths."""
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_BYTES:
            raise ValueError("not a bounded nonempty regular file")
        raw = stream.read(MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
    if len(raw) > MAX_BYTES or any(getattr(before, key) != getattr(after, key) for key in
                                  ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")):
        raise ValueError("file changed during capture")
    return raw


class UniqueLoader(getattr(yaml, "CSafeLoader", yaml.SafeLoader)):
    pass


UniqueLoader.yaml_implicit_resolvers = {
    key: [(tag, expression) for tag, expression in resolvers
          if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in UniqueLoader.yaml_implicit_resolvers.items()
}


def finite_tree(value, ancestors=None, depth=0, budget=None):
    """Bound malformed YAML aliases/depth and reject non-JSON scientific scalars."""
    ancestors = set() if ancestors is None else ancestors
    budget = [500_000] if budget is None else budget
    budget[0] -= 1
    if budget[0] < 0 or depth > 64:
        raise ValueError("document exceeds structural bounds")
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float and math.isfinite(value):
        return
    if not isinstance(value, (dict, list)) or id(value) in ancestors:
        raise ValueError("document contains nonfinite, unsupported or recursive values")
    if isinstance(value, dict) and any(not isinstance(key, str) for key in value):
        raise ValueError("document has nonstring mapping keys")
    ancestors.add(id(value))
    for child in value.values() if isinstance(value, dict) else value:
        finite_tree(child, ancestors, depth + 1, budget)
    ancestors.remove(id(value))


def unique_mapping(loader, node):
    out = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in out:
            raise ValueError("mapping has duplicate or nonstring keys")
        out[key] = loader.construct_object(value_node)
    return out


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def document(raw, *, json_only=False):
    if json_only:
        def pairs(rows):
            result = {}
            for key, value in rows:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result
        def invalid(value):
            raise ValueError("nonfinite JSON value")
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    else:
        value = yaml.load(raw, Loader=UniqueLoader)
    if not isinstance(value, dict):
        raise ValueError("document is not a mapping")
    finite_tree(value)
    return value


def local_path(root, value):
    if not isinstance(value, str) or not value:
        return None
    try:
        path = root / value
        if ".." in path.parts:
            return None
        resolved = path.resolve()
        resolved.relative_to(root)
        return resolved
    except (ValueError, OSError, RuntimeError):
        return None


def relative(root, path):
    return path.relative_to(root).as_posix()


def read_local(root, path):
    selected = local_path(root, str(path))
    if selected is None:
        raise ValueError("selected file escapes checkout")
    return read(selected)


def load_record(root, arm, project, label, replicate=None):
    """One exact provenance identity; never choose an ambiguous method copy."""
    paths = sorted((root / "data/d4d_concatenated").glob(f"*_core/{label}/{project}_provenance.yaml"))
    result = {"arm": arm, "project": project, "label": label,
        "provenance_files": [relative(root, path) for path in paths], "canonical": False,
        "record_path": None, "record_sha256": None, "validation_passed": None,
        "generation_method": None, "reasons": []}
    if len(paths) != 1:
        result["reasons"].append("provenance_missing" if not paths else "provenance_ambiguous")
        return result, None
    try:
        raw = read_local(root, paths[0])
        rec = document(raw)
        result["provenance_sha256"] = sha(raw)
    except (OSError, ValueError, yaml.YAMLError, UnicodeError, RecursionError):
        result["reasons"].append("provenance_unreadable")
        return result, None
    run = mapping(rec.get("run"))
    result["canonical"] = "canonical" in rec
    result["canonical_criterion"] = mapping(rec.get("canonical")).get("criterion")
    result["generation_method"] = run.get("method")
    result["validation_passed"] = mapping(rec.get("validation")).get("passed")
    if (rec.get("record_type") != "d4d_generation_provenance" or run.get("project") != project
            or run.get("label") != label or run.get("method") != paths[0].parents[1].name.removesuffix("_core")
            or (run.get("replicate") is not None and
                (type(run["replicate"]) is not int or run["replicate"] != replicate))):
        result["reasons"].append("provenance_identity_conflict")
    outputs = mapping(mapping(rec.get("outputs")).get("full"))
    artifact = mapping(mapping(mapping(rec.get("validation")).get("artifacts")).get("full"))
    name = artifact.get("path") or outputs.get("path")
    path = local_path(root, name)
    if path is None:
        result["reasons"].append("generation_artifact_path_missing_or_external")
        return result, None
    result["record_path"] = relative(root, path)
    if outputs.get("path") and local_path(root, outputs["path"]) != path:
        result["reasons"].append("generation_artifact_paths_conflict")
    try:
        full_raw = read(path)
        result["record_sha256"] = sha(full_raw)
    except (OSError, ValueError):
        result["reasons"].append("generation_artifact_unavailable")
        return result, None
    pins = [(key, value) for entry in (artifact, outputs) for key, value in entry.items()
            if key in ("md5", "sha256")]
    if not pins:
        result["reasons"].append("generation_artifact_hash_missing")
    elif any(not isinstance(value, str) or hashlib.new(key, full_raw).hexdigest() != value.lower()
             for key, value in pins):
        result["reasons"].append("generation_artifact_hash_mismatch")
    if result["validation_passed"] is False:
        result["reasons"].append("generation_record_declared_invalid")
    elif result["validation_passed"] is not True:
        result["reasons"].append("generation_validation_unknown")
    return result, full_raw


def evaluations(root):
    """Direct filesystem glob includes ignored/hidden entries in selected stores."""
    rows, problems, stores = [], [], []
    for rubric in RUBRICS:
        folder = root / "data/evaluation_llm" / (rubric + "_semantic") / "label_aware"
        stores.append({"rubric": rubric, "path": relative(root, folder),
                       "exists": folder.is_dir(), "glob": "*.json (nonrecursive)"})
        for path in sorted(folder.glob("*.json")):
            try:
                raw = read_local(root, path)
                doc = document(raw, json_only=True)
                rows.append({"store": rubric, "path": relative(root, path), "sha256": sha(raw), "doc": doc})
            except (OSError, ValueError, UnicodeError, RecursionError):
                problems.append({"path": relative(root, path), "reason": "evaluation_unreadable_or_invalid_json"})
    return rows, problems, stores


def instrument(rubric, version):
    selected = select_semantic_instrument(rubric, version)
    paths = (selected.definition_path, selected.rubric_path, selected.schema_path, selected.evidence_authority_path)
    resources = {name: read(ROOT / name) for name in paths}
    return selected, resources


class RegisteredRefusal(ValueError):
    """Stable inventory reason, without exposing arbitrary parser exception text."""


def require(condition, reason):
    if not condition:
        raise RegisteredRefusal(reason)


def checked_pin(value):
    require(isinstance(value, dict) and set(value) == {"path", "sha256", "bytes"}
            and isinstance(value["path"], str) and Path(value["path"]).is_absolute()
            and ".." not in Path(value["path"]).parts
            and isinstance(value["sha256"], str) and HEX.fullmatch(value["sha256"])
            and type(value["bytes"]) is int and 0 < value["bytes"] <= MAX_BYTES,
            "registered_pin_invalid")
    return value


class RegisteredCapture:
    """One bounded read snapshot; never follows a manifest outside --root."""

    def __init__(self, root, directory, authority_roots=()):
        self.root = root
        self.roots = (root, *(Path(path).resolve(strict=True) for path in authority_roots))
        self.logical_directory = root / directory
        self.directory = local_path(root, str(self.logical_directory))
        require(self.directory is not None and self.directory.is_dir(),
                "registered_directory_missing_or_external")
        info = self.directory.stat()
        self.directory_identity = (info.st_dev, info.st_ino)
        self.logical_paths = {}
        self.files = {}
        self.total = 0

    def locate(self, logical):
        for root in self.roots:
            path = local_path(root, str(logical))
            if path is not None:
                return path
        return None

    def read_inside(self, path):
        """Hold directory descriptors, refusing a parent-symlink replacement."""
        root = next(root for root in self.roots if path.is_relative_to(root))
        parts = path.relative_to(root).parts
        require(bool(parts) and ".." not in parts, "registered_authority_missing_or_external")
        directories = [os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)]
        try:
            for part in parts[:-1]:
                directories.append(os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                           dir_fd=directories[-1]))
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=directories[-1])
            with os.fdopen(fd, "rb") as stream:
                before = os.fstat(stream.fileno())
                require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= MAX_BYTES,
                        "registered_file_not_bounded_regular")
                raw = stream.read(MAX_BYTES + 1)
                after = os.fstat(stream.fileno())
            require(len(raw) <= MAX_BYTES and all(getattr(before, key) == getattr(after, key)
                    for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")),
                    "registered_evidence_changed")
            return raw
        finally:
            for fd in reversed(directories):
                os.close(fd)

    def take(self, name):
        logical = self.logical_directory / name
        path = self.locate(logical)
        require(path is not None, "registered_authority_missing_or_external")
        require(logical not in self.logical_paths or self.logical_paths[logical] == path,
                "registered_evidence_changed")
        raw = self.read_inside(path)
        require(self.locate(logical) == path, "registered_evidence_changed")
        if path in self.files:
            require(self.files[path] == raw, "registered_evidence_changed")
        else:
            self.total += len(raw)
            require(self.total <= MAX_REGISTERED_BYTES, "registered_evidence_byte_limit")
            self.files[path] = raw
        self.logical_paths[logical] = path
        return raw

    def pinned(self, pin):
        pin = checked_pin(pin)
        raw = self.take(pin["path"])
        require(len(raw) == pin["bytes"] and sha(raw) == pin["sha256"],
                "registered_authority_pin_mismatch")
        return raw

    def unchanged(self):
        def bindings_current():
            require(local_path(self.root, str(self.logical_directory)) == self.directory,
                    "registered_evidence_changed")
            info = self.directory.stat()
            require((info.st_dev, info.st_ino) == self.directory_identity,
                    "registered_evidence_changed")
            for logical, path in self.logical_paths.items():
                require(self.locate(logical) == path, "registered_evidence_changed")

        bindings_current()
        for path, raw in self.files.items():
            require(self.locate(path) == path and self.read_inside(path) == raw,
                    "registered_evidence_changed")
        bindings_current()


def registered_attempt_names(directory, count):
    """Enumerate the small package root without materializing an unbounded glob."""
    names = []
    with os.scandir(directory) as entries:
        for position, entry in enumerate(entries, 1):
            require(position <= 128, "registered_directory_entry_limit")
            if entry.name.startswith("rating-"):
                require(re.fullmatch(r"rating-\d{3}", entry.name) is not None
                        and entry.is_dir(follow_symlinks=False), "registered_attempt_directory_invalid")
                names.append(entry.name)
                require(len(names) <= count, "registered_attempt_directories_mismatch")
    return sorted(names)


def committed_package(capture):
    """Check the captured package bytes against HEAD, not merely the index."""
    try:
        result = subprocess.run(["git", "-C", str(capture.root), "rev-parse", "--show-toplevel"],
                                capture_output=True, text=True, check=True, timeout=5)
        git_root = Path(result.stdout.strip()).resolve()
        for path, raw in capture.files.items():
            if path.is_relative_to(capture.directory):
                result = subprocess.run(["git", "-C", str(git_root), "show",
                                         "HEAD:" + path.relative_to(git_root).as_posix()],
                                        capture_output=True, check=True, timeout=5)
                if result.stdout != raw:
                    return False
        return True
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def registered_run(root, arm, directory, *, snapshots, evaluator_model, contexts, authority_roots=(),
                   execution_lock_root=None, roster=()):
    """Read saved E1 evidence, then reuse its actual offline acceptance validator.

    This does not call prepare/assert_current, execute historical code, read a
    runtime binary, recertify generation, or treat receipt claims as signatures.
    """
    from data_sheets_schema.evaluation import registered_eval_runner as runner
    from data_sheets_schema.evaluation import blind_review_pack as blind
    from data_sheets_schema.provenance import resolve_record_input

    capture = RegisteredCapture(root, directory, authority_roots)
    package = {"arm": arm, "path": relative(root, capture.directory), "reasons": [],
               "attempts": [], "record": None, "rows": [], "generation_acceptance_verified": False,
               "lock_verified": False, "lock_status": "not_checked", "committed_package": False}
    try:
        manifest_raw = capture.take("registration.json")
        plan = document(manifest_raw, json_only=True)
        receipt_raw = capture.take("receipt.json")
        receipt = document(receipt_raw, json_only=True)
        require(receipt.get("format") in (None, runner.RECEIPT_FORMAT), "registered_receipt_format_unsupported")
        marked_receipt = receipt.get("format") is not None
        package.update(manifest_sha256=sha(manifest_raw), receipt_sha256=sha(receipt_raw))
        require(plan.get("format") == runner.FORMAT and runner.shared.canonical(plan) == manifest_raw,
                "registered_manifest_format_or_encoding")
        require(plan.get("execution_mode") == "isolated_no_tools_controller_validation",
                "registered_execution_mode_unsupported")
        require(receipt.get("plan_sha256") == sha(manifest_raw) and receipt.get("plan") == plan,
                "registered_receipt_plan_mismatch")
        require(receipt.get("status") in {"validated", "incomplete"}, "registered_receipt_status")
        declared_rubric = str(mapping(plan.get("instrument")).get("rubric", "")).removesuffix("-semantic")
        package["rubric"] = declared_rubric if declared_rubric in RUBRICS else None
        run = mapping(plan.get("generation_run"))
        require(set(run) == {"arm", "project", "label", "method"}
                and all(isinstance(value, str) and value.strip() and len(value) <= 4096
                        for value in run.values()), "registered_run_identity_invalid")
        package["generation_run"] = run
        record = {"arm": arm, "project": run["project"], "label": run["label"],
            "replicate": None, "canonical": False, "provenance_files": [], "record_path": None,
            "record_sha256": None, "validation_passed": None, "generation_method": run["method"],
            "record_role": plan.get("record_role"), "registered_run": run, "reasons": []}
        require(plan.get("record_role") == "full", "unsupported_for_full_audit")
        require(type(plan.get("repeat_count")) is int and 1 <= plan["repeat_count"] <= 100,
                "registered_repeat_count_invalid")
        authority_list = plan.get("authorities")
        require(isinstance(authority_list, list) and 0 < len(authority_list) <= 1024,
                "registered_authorities_invalid")
        authorities = {}
        for entry in authority_list:
            entry = checked_pin(entry)
            require(entry["path"] not in authorities, "registered_authorities_ambiguous")
            authorities[entry["path"]] = entry

        def original_pin(key):
            pin = checked_pin(plan.get(key))
            require(authorities.get(pin["path"]) == pin, "registered_authority_not_captured")
            return capture.pinned(pin)

        generation_raw = original_pin("generation_registration")
        generation = document(generation_raw, json_only=True)
        require(generation.get("format") == runner.shared.FORMAT
                and generation.get("registration_path") == plan["generation_registration"]["path"]
                and generation.get("run") == run, "registered_generation_identity_mismatch")
        # The supported shared-v1 parser checks its immutable descriptor and
        # structural contracts, not equality to a historical executable tree.
        try:
            runner.shared.parse_registration(generation_raw)
        except (ValueError, RuntimeError, OSError):
            raise RegisteredRefusal("registered_generation_registration_unsupported") from None
        provenance_raw = original_pin("generation_provenance")
        provenance = document(provenance_raw)
        require(provenance.get("record_type") == "d4d_generation_provenance"
                and same_run(provenance.get("run"), run),
                "registered_provenance_identity_mismatch")
        assignments = [entry for entry in roster if entry["arm"] == arm
                       and entry["project"] == run["project"] and entry["label"] == run["label"]]
        require(len(assignments) == 1 and same_run(
            {**assignments[0], "arm": assignments[0]["input_arm"]}, run)
            and assignments[0]["condition"] == provenance["run"].get("condition")
            and provenance["run"].get("replicate") in (None, assignments[0]["replicate"]),
            "registered_arm_mapping_undeclared_or_mismatched")
        prior = mapping(mapping(provenance.get("shared_generation")).get("authority"))
        require(prior.get("registration") == {"sha256": sha(generation_raw),
                "raw_json": generation_raw.decode()}, "registered_provenance_registration_mismatch")
        inputs = mapping(generation.get("inputs"))
        pins = [inputs[key] for key in ("bundle", "chunk_manifest", "source_manifest", "context")
                if inputs.get(key) is not None]
        for name in ("full_schema", "core_schema"):
            sources = mapping(inputs.get(name)).get("sources")
            require(isinstance(sources, list) and 0 < len(sources) <= 256,
                    "registered_generation_sources_invalid")
            pins.extend(sources)
        pins.extend(pin for pin in (mapping(inputs.get("profile")).get("vocabulary"),
                                    mapping(generation.get("runtime")).get("config")) if pin)
        pins.append(plan["generation_registration"])
        expected = {}
        for pin in pins:
            checked_pin(pin)
            require(pin["path"] not in expected or expected[pin["path"]] == pin,
                    "registered_generation_sources_conflict")
            require(authorities.get(pin["path"]) == pin, "registered_generation_source_not_captured")
            expected[pin["path"]] = pin
        require(prior.get("files") == [expected[key] for key in sorted(expected)]
                and plan.get("omission_context") == inputs.get("context"),
                "registered_provenance_capture_mismatch")
        original = original_pin("record")
        require(capture.take("original.yaml") == original, "registered_original_copy_mismatch")
        artifact = mapping(mapping(mapping(provenance.get("validation")).get("artifacts")).get("full"))
        resolved = (resolve_record_input(Path(artifact["path"]), Path(plan["generation_provenance"]["path"]))
                    if isinstance(artifact.get("path"), str) else None)
        require(resolved is not None and local_path(root, str(resolved)) == local_path(root, plan["record"]["path"]),
                "registered_provenance_full_path_mismatch")
        hashes = {key: artifact[key] for key in ("md5", "sha256") if key in artifact}
        require(hashes and all(isinstance(value, str) and hashlib.new(key, original).hexdigest() == value
                              for key, value in hashes.items()), "registered_provenance_full_hash_mismatch")
        record.update(record_path=relative(root, local_path(root, plan["record"]["path"])),
            record_sha256=sha(original), provenance_sha256=sha(provenance_raw),
            provenance_files=[relative(root, local_path(root, plan["generation_provenance"]["path"]))],
            validation_passed=mapping(provenance.get("validation")).get("passed"))
        require(record["validation_passed"] is not False, "generation_record_declared_invalid")
        require(record["validation_passed"] is None or type(record["validation_passed"]) is bool,
                "registered_generation_validation_invalid")
        # Only this fully joined generation identity may participate in record
        # merging. Later package failures belong to the package, not the record.
        package["record"] = record
        blinding = plan.get("blinding")
        require(blinding == blinding_identity(run, provenance["run"], mapping(blinding).get("arm"), blind.BLINDING_VERSION),
                "registered_blinding_unsupported_or_mismatched")
        blinded = blind.blind_input(original, blind.Record(blinding["arm"], run["project"], run["label"],
            Path(plan["record"]["path"]), sha(original), input_arm=run["arm"]), forbidden=(
                plan["generation_registration"]["path"], plan["generation_provenance"]["path"],
                *forbidden_blinding_identities(blinding)))
        require(capture.take("record.yaml") == blinded and plan.get("blinded_input_sha256") == sha(blinded),
                "registered_blinded_input_mismatch")
        context_raw = original_pin("applicability_context")
        context = normalize_context(document(context_raw))
        saved_context = capture.take("context.json")
        require(document(saved_context, json_only=True) == context
                and saved_context == runner.shared.canonical(context)
                and context_digest(context) == plan.get("context_sha256"), "registered_context_mismatch")
        selected_instrument = mapping(plan.get("instrument"))
        rubric = str(selected_instrument.get("rubric", "")).removesuffix("-semantic")
        require(rubric in RUBRICS, "registered_rubric_unsupported")
        selected, current_resources = snapshots[rubric]
        require(selected_instrument.get("version") == selected.version
                and selected_instrument.get("agent") == selected.agent,
                "registered_instrument_version_unsupported")
        resources = {}
        for name, current in current_resources.items():
            raw = capture.take("instrument/" + name)
            matches = [entry for path, entry in authorities.items() if path.endswith("/" + name)]
            require(len(matches) == 1 and matches[0]["sha256"] == sha(raw)
                    and matches[0]["bytes"] == len(raw) and raw == current,
                    "registered_instrument_resource_unsupported_or_mismatched")
            resources[name] = raw
        for key, name in (("definition_sha256", selected.definition_path),
                          ("rubric_sha256", selected.rubric_path),
                          ("evidence_authority_sha256", selected.evidence_authority_path)):
            require(selected_instrument.get(key) == sha(resources[name]), "registered_instrument_pin_mismatch")
        predecessor_raw = capture.take("predecessor.md")
        require(selected_instrument.get("predecessor_sha256") == sha(predecessor_raw),
                "registered_predecessor_pin_mismatch")
        known_predecessor = (read(ROOT / select_semantic_instrument("rubric20", "3.0").definition_path).decode()
                             if selected.version == "4.0" else agent_pin._previous_text(selected.agent))
        require(known_predecessor is not None and predecessor_raw.decode() == known_predecessor,
                "registered_predecessor_unsupported")
        preamble = agent_pin.spawn_preamble(selected.agent, predecessor_text=predecessor_raw.decode())
        require(selected_instrument.get("preamble_sha256") == sha(preamble.encode()),
                "registered_challenge_unsupported_or_mismatched")
        adapter_raw, system_raw = capture.take("execution_adapter.txt"), capture.take("effective_system.txt")
        adapter = mapping(plan.get("execution_adapter"))
        require(adapter.get("name") == "no_tools_controller_validation_v1"
                and adapter_raw == runner.EXECUTION_ADAPTER.encode()
                and adapter.get("sha256") == sha(adapter_raw)
                and system_raw == resources[selected.definition_path] + b"\n\n" + adapter_raw
                and adapter.get("effective_system_sha256") == sha(system_raw),
                "registered_adapter_unsupported_or_mismatched")
        runtime = mapping(plan.get("runtime"))
        require(runtime.get("provider") == "LBL CBORG" and runtime.get("base_url") == runner.CBORG_BASE_URL
                and runtime.get("api_key_source") == "ANTHROPIC_API_KEY"
                and runtime.get("credential_source") == "CBORG_API_KEY"
                and runtime.get("binary_pin_supplied") is True
                and runtime.get("effort") in {"low", "medium", "high", "max"}
                and all(isinstance(runtime.get(key), str) and runtime[key].strip()
                        for key in ("model", "canonical_model"))
                and type(runtime.get("context_window")) is int and runtime["context_window"] > 0
                and isinstance(runtime.get("version"), str)
                and re.fullmatch(r"\d+\.\d+\.\d+", runtime["version"]), "registered_runtime_unsupported")
        # Binary bytes are never opened/executed during retrospective ingestion.
        binary = runtime.get("binary")
        require(isinstance(binary, dict) and set(binary) == {"path", "sha256", "bytes"}
                and isinstance(binary["path"], str) and Path(binary["path"]).is_absolute()
                and type(binary["bytes"]) is int and 0 < binary["bytes"] <= 512_000_000
                and isinstance(binary["sha256"], str) and HEX.fullmatch(binary["sha256"]),
                "registered_runtime_pin_missing")
        require(runtime["model"] == runtime["canonical_model"] or (
            runtime["model"] == runtime["canonical_model"] + "[1m]" and runtime["context_window"] == 1_000_000),
            "registered_runtime_selector_mismatch")
        cap = runner._money(plan.get("max_cost_dollars"), "max_cost_dollars")
        reserved = runner._money(plan.get("reserved_cost_dollars_per_attempt"), "reserved_cost_dollars_per_attempt")
        require(reserved == (cap / plan["repeat_count"]).quantize(Decimal("0.000001"), rounding=ROUND_DOWN),
                "registered_cost_reservation_mismatch")
        prepared = runner.PreparedEvaluation(manifest_raw, (), tuple(resources.items()), original, blinded,
            saved_context, resources[selected.definition_path], system_raw, predecessor_raw.decode(), preamble)
        require(capture.take("prompt.txt") == runner.rating_prompt(prepared).encode(),
                "registered_prompt_unsupported_or_mismatched")
        implementation_pins = [entry for path, entry in sorted(authorities.items()) if path.endswith(".py")]
        for name in ("evaluation/registered_eval_runner.py", "evaluation/blind_review_pack.py"):
            require(sum(entry["path"].endswith("/" + name) for entry in implementation_pins) == 1,
                    "registered_blinding_implementation_pin_missing")
        condition = {"source": "registered_blinded", "record_role": "full", "original_sha256": sha(original),
            "blinded_sha256": sha(blinded), "blinding": blinding, "adapter": adapter,
            "instrument": selected_instrument, "runtime": runtime, "implementation_pins": implementation_pins}
        ratings, attempts = receipt.get("ratings"), receipt.get("attempts")
        require(isinstance(ratings, list) and isinstance(attempts, list)
                and len(ratings) <= len(attempts) <= plan["repeat_count"], "registered_attempt_roster_invalid")
        by_index = {}
        for attempt in attempts:
            require(isinstance(attempt, dict) and type(attempt.get("rating")) is int
                    and 1 <= attempt["rating"] <= plan["repeat_count"] and attempt["rating"] not in by_index,
                    "registered_attempt_identity_invalid")
            by_index[attempt["rating"]] = attempt
        require(list(by_index) == list(range(1, len(attempts) + 1)), "registered_attempt_order_invalid")
        seen_ratings, sessions = set(), set()
        for rating in ratings:
            require(isinstance(rating, dict) and type(rating.get("rating")) is int
                    and rating["rating"] in by_index and rating["rating"] not in seen_ratings,
                    "registered_rating_identity_invalid")
            index = rating["rating"]
            seen_ratings.add(index)
            attempt = by_index[index]
            require(rating.get("status") == attempt.get("status") == "validated"
                    and type(attempt.get("exit_code")) is int and attempt["exit_code"] == 0,
                    "registered_rating_not_validated")
            prefix = f"rating-{index:03d}/"
            evaluation_raw, trace_raw = capture.take(prefix + "evaluation.json"), capture.take(prefix + "transcript.jsonl")
            doc = document(evaluation_raw, json_only=True)
            require(sha(evaluation_raw) == rating.get("evaluation_sha256")
                    and runner.shared.canonical(doc) == evaluation_raw,
                    "registered_evaluation_pin_mismatch")
            require(rating.get("transcript_sha256", sha(trace_raw)) == sha(trace_raw),
                    "registered_transcript_pin_mismatch")
            if marked_receipt:
                require(rating.get("transcript_sha256") == attempt.get("transcript_sha256") == sha(trace_raw),
                        "registered_transcript_pin_mismatch")
                stderr_raw = capture.take(prefix + "stderr.txt")
                require(rating.get("stderr_sha256") == attempt.get("stderr_sha256") == sha(stderr_raw),
                        "registered_stderr_pin_mismatch")
                require(rating.get("files") == attempt.get("files") == ["evaluation.json", "stderr.txt", "transcript.jsonl"]
                        and sorted(p.name for p in (capture.directory / prefix).iterdir()) == rating["files"],
                        "registered_attempt_files_mismatch")
            events = [document(line, json_only=True) for line in trace_raw.splitlines() if line.strip()]
            accepted, cost = runner._accept(prepared, events)
            require(accepted == doc, "registered_transcript_evaluation_mismatch")
            session = next(event["session_id"] for event in events if event.get("type") == "result")
            require(rating.get("session_id") == session and session not in sessions,
                    "registered_session_reused_or_mismatched")
            sessions.add(session)
            require(rating.get("check_echo") == "passed" and rating.get("instrument_version") == selected.version
                    and str(cost) == str(rating.get("estimated_cost_usd"))
                    and str(cost) == str(attempt.get("estimated_cost_usd")), "registered_rating_receipt_mismatch")
            reasons = []
            pending = []
            if evaluator_model is None:
                pending.append("target_evaluator_not_selected")
            elif runtime.get("canonical_model") != evaluator_model:
                reasons.append("evaluator_differs_from_target")
            if run["project"] not in contexts:
                pending.append("target_context_not_selected")
            elif context != contexts[run["project"]]:
                reasons.append("applicability_context_differs_from_target")
            package["rows"].append({"path": relative(root, capture.directory / prefix / "evaluation.json"),
                "sha256": sha(evaluation_raw), "rubric": rubric, "version": selected.version,
                "evaluator": runtime["canonical_model"], "model_name": runtime["canonical_model"],
                "context_block_present": True, "context_hash": plan["context_sha256"],
                "input_hashes": {"input_sha256": sha(blinded)}, "session_id": session,
                "declared_repeat_n": plan["repeat_count"], "reasons": reasons, "pending": pending,
                "contract_checked": True, "eligible_for_condition_review": not reasons and not pending,
                "source": "registered_blinded", "input_condition": condition,
                "manifest_sha256": sha(manifest_raw), "receipt_sha256": sha(receipt_raw),
                "transcript_sha256": sha(trace_raw), "transcript_pin_supplied": "transcript_sha256" in rating,
                "rating_index": index, "original_sha256": sha(original), "record_role": "full"})
        require([row["rating"] for row in ratings] == list(range(1, len(ratings) + 1)),
                "registered_rating_order_invalid")
        for index, attempt in by_index.items():
            require((attempt.get("status") == "validated") == (index in seen_ratings),
                    "registered_attempt_rating_mismatch")
            package["attempts"].append({"rating": index, "status": attempt.get("status"),
                "reason": None if index in seen_ratings else "registered_attempt_failed_or_incomplete"})
        if receipt["status"] == "validated":
            require(len(ratings) == plan["repeat_count"], "registered_validated_panel_incomplete")
        actual = registered_attempt_names(capture.directory, len(attempts))
        require(actual == [f"rating-{index:03d}" for index in by_index], "registered_attempt_directories_mismatch")
        if marked_receipt:
            for index, attempt in by_index.items():
                if index in seen_ratings or attempt.get("status") == "started":
                    continue
                folder = capture.directory / f"rating-{index:03d}"
                names = sorted(p.name for p in folder.iterdir())
                require(attempt.get("files") == names and set(names) <= {"evaluation.json", "transcript.jsonl", "stderr.txt"},
                        "registered_attempt_files_mismatch")
                for name, field in (("transcript.jsonl", "transcript_sha256"), ("stderr.txt", "stderr_sha256")):
                    expected = sha(capture.take(f"rating-{index:03d}/" + name)) if name in names else None
                    require(attempt.get(field) == expected, "registered_" + field.replace("sha256", "pin_mismatch"))
        lock_root = (Path(execution_lock_root) if execution_lock_root is not None else Path(runner.LOCK_DIR)).resolve()
        package["lock_status"] = "store_unavailable"
        if lock_root.is_dir():
            package["lock_status"] = "missing"
            lock_path = lock_root / (sha(manifest_raw) + ".json")
            require(lock_path.is_file(), "registered_execution_lock_missing")
            lock_capture = RegisteredCapture(lock_root.resolve(), lock_root.resolve())
            lock = document(lock_capture.take(lock_path), json_only=True)
            package["lock_status"] = "mismatched"
            require(lock.get("plan_sha256") == sha(manifest_raw) and lock.get("receipt_sha256") == sha(receipt_raw)
                    and (not marked_receipt or (lock.get("attempts") == attempts and lock.get("ratings") == ratings)),
                    "registered_execution_lock_mismatch")
            lock_capture.unchanged()
            package.update(lock_verified=True, lock_status="verified")
        package["committed_package"] = committed_package(capture)
        capture.unchanged()
        require(registered_attempt_names(capture.directory, len(attempts)) == actual,
                "registered_attempt_directories_changed")
        package["status"] = "bound_ratings" if package["rows"] else "no_validated_ratings"
        package["receipt_status"] = receipt["status"]
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, yaml.YAMLError, RecursionError,
            agent_pin.StaleAgentDefinition, agent_pin.NoDiscriminatingChallenge) as exc:
        reason = str(exc) if isinstance(exc, RegisteredRefusal) else "registered_evidence_invalid_or_unavailable"
        package["reasons"] = [reason]
        package["rows"] = []
        package["status"] = "refused"
    return package


def association(root, evaluation, record):
    """Content labels or exact recorded artifact paths only; filenames never join."""
    doc = evaluation["doc"]
    metadata = mapping(doc.get("metadata"))
    labels = {value for value in (doc.get("label"), metadata.get("label")) if isinstance(value, str)}
    named = doc.get("project") == record["project"] and record["label"] in labels
    path = local_path(root, doc.get("d4d_file"))
    exact_path = record["record_path"] is not None and path == root / record["record_path"]
    return named or exact_path


def inspect_evaluation(root, evaluation, record, full_raw, *, version, evaluator_model, target_context,
                       instrument_snapshot=None):
    rubric, doc = evaluation["store"], evaluation["doc"]
    metadata, model = mapping(doc.get("metadata")), mapping(doc.get("model"))
    labels = [value for value in (doc.get("label"), metadata.get("label")) if value is not None]
    reasons, pending = [], []
    row = {key: evaluation[key] for key in ("path", "sha256")}
    row.update(rubric=doc.get("rubric"), version=doc.get("version"),
        evaluator=model.get("evaluator_model") or model.get("name"),
        model_name=model.get("name"), context_block_present=isinstance(doc.get("applicability_context"), dict),
        context_hash=metadata.get("context_sha256"), input_hashes={},
        session_id=metadata.get("session_id") or doc.get("session_id"),
        declared_repeat_n=mapping(doc.get("repeat_panel")).get("n"),
        reasons=reasons, pending=pending, source="legacy_label_aware",
        input_condition={"source": "legacy_label_aware", "record_role": "full",
                         "original_sha256": record["record_sha256"],
                         "blinding": "unblinded_or_unrecorded", "execution_adapter": "unrecorded"})
    if doc.get("rubric") != rubric + "-semantic":
        reasons.append("rubric_disagrees_with_store")
    if doc.get("version") != version:
        reasons.append("pre_3_instrument" if pre_three_version(doc.get("version")) else "instrument_version_mismatch")
    if doc.get("project") != record["project"] or any(value != record["label"] for value in labels):
        reasons.append("evaluation_run_identity_conflict")
    if doc.get("method") is not None and doc["method"] != record["generation_method"]:
        reasons.append("evaluation_method_conflict")
    path = local_path(root, doc.get("d4d_file"))
    if record["record_path"] is None or path != root / record["record_path"]:
        reasons.append("evaluation_input_path_unverified")
    hashes = {key: metadata[key] for key in ("input_sha256", "d4d_file_hash") if key in metadata}
    row["input_hashes"] = hashes
    if not hashes:
        reasons.append("evaluation_input_hash_missing")
    elif any(not isinstance(value, str) or not HEX.fullmatch(value) or value.lower() != record["record_sha256"]
             for value in hashes.values()):
        reasons.append("evaluation_input_hash_mismatch")
    if not isinstance(row["evaluator"], str) or not row["evaluator"].strip():
        reasons.append("evaluator_model_missing")
    elif model.get("name") and model.get("evaluator_model") and model["name"] != model["evaluator_model"]:
        reasons.append("evaluator_model_fields_conflict")
    if evaluator_model is None:
        pending.append("target_evaluator_not_selected")
    elif row["evaluator"] != evaluator_model:
        reasons.append("evaluator_differs_from_target")
    normalized = None
    if not row["context_block_present"]:
        reasons.append("applicability_context_missing")
    else:
        try:
            normalized = normalize_context(doc["applicability_context"])
            computed = context_digest(normalized)
            if not isinstance(row["context_hash"], str) or row["context_hash"] != computed:
                reasons.append("applicability_context_hash_missing_or_mismatched")
        except (TypeError, ValueError):
            reasons.append("applicability_context_invalid")
    if target_context is None:
        pending.append("target_context_not_selected")
    elif normalized != target_context:
        reasons.append("applicability_context_differs_from_target")
    selected, resources = instrument_snapshot or instrument(rubric, version)
    for key, name in (("instrument_sha256", selected.definition_path), ("rubric_sha256", selected.rubric_path),
                      ("evidence_authority_sha256", selected.evidence_authority_path)):
        if metadata.get(key) != sha(resources[name]):
            reasons.append(key + "_missing_or_mismatched")
    echo = metadata.get("definition_echo") or doc.get("definition_echo")
    if not isinstance(echo, str):
        reasons.append("definition_echo_evidence_missing")
    else:
        try:
            predecessor = read(ROOT / select_semantic_instrument("rubric20", "3.0").definition_path).decode() if version == "4.0" else None
            agent_pin.verify_echo(selected.agent, echo, predecessor_text=predecessor)
        except (ValueError, OSError, RuntimeError):
            reasons.append("definition_echo_not_verified")
    row["contract_checked"] = False
    if doc.get("version") == version and full_raw is not None and normalized is not None:
        row["contract_checked"] = True
        try:
            valid, errors = validate_evaluation(doc, json.loads(resources[selected.schema_path]),
                                               resource_reader=resources.__getitem__)
            if not valid:
                raise ValueError("; ".join(errors[:3]))
            validate_scope(doc, document=unwrap_document(document(full_raw)),
                input_sha256=sha(full_raw), expected_context=normalized, resource_reader=resources.__getitem__)
        except (ValueError, TypeError, KeyError, yaml.YAMLError):
            reasons.append("current_semantic_contract_invalid")
    row["reasons"] = sorted(set(reasons))
    row["pending"] = sorted(set(pending))
    row["eligible_for_condition_review"] = not reasons and not pending and not record["reasons"]
    return row


def repeat_panel(rows):
    """Three generation replicates or a reported n are not three ratings."""
    groups = {}
    for row in rows:
        if row["reasons"]:
            continue
        key = (row["version"], row["evaluator"], row["context_hash"],
               json.dumps(row.get("input_condition"), sort_keys=True, allow_nan=False))
        groups.setdefault(key, []).append(row)
    best = max(groups.values(), key=lambda group: len({row["session_id"] for row in group
        if isinstance(row["session_id"], str) and row["session_id"].strip()}), default=[])
    sessions = {row["session_id"] for row in best if isinstance(row["session_id"], str) and row["session_id"].strip()}
    # Independent sessions can legitimately return byte-identical score JSON.
    distinct = len(sessions)
    return {"declared_n": sorted({row["declared_repeat_n"] for row in rows
            if type(row["declared_repeat_n"]) is int and row["declared_repeat_n"] >= 0}),
        "contract_valid_rating_files": len(best), "distinct_reported_sessions": distinct,
        "target_conditions_selected": bool(best) and all(not row["pending"] for row in best),
        "reported_n_at_least_three": any(type(row["declared_repeat_n"]) is int and row["declared_repeat_n"] >= 3 for row in rows),
        "three_distinct_session_claims_present": distinct >= 3,
        "independence_verified": False,
        "condition_groups": len(groups),
        "basis": "Distinct reported sessions of one fixed input/condition; registered rows additionally join retained transcripts and receipts. Neither proves independent evaluators or human approval."}


def audit(root, *, roster_manifest, rubric20_version="3.0", evaluator_model=None, contexts=None,
          registered_evaluations=(), authority_roots=(), execution_lock_root=None):
    root = Path(root).resolve()
    roster, roster_pin = read_cohort(roster_manifest)
    if rubric20_version not in ("3.0", "4.0"):
        raise ValueError("rubric20 target must be 3.0 or 4.0")
    contexts = {} if contexts is None else contexts
    normalized_contexts = {project: normalize_context(value) for project, value in contexts.items()}
    registered_evaluations = tuple(registered_evaluations)
    require(len(registered_evaluations) <= 1000, "too many explicit registered directories")
    snapshots = {rubric: instrument(rubric, "3.0" if rubric == "rubric10" else rubric20_version)
                 for rubric in RUBRICS}
    evaluations_found, problems, stores = evaluations(root)
    records, rescore, excluded, associated = [], [], [], set()
    for declared in roster:
        arm, project, label = (declared[key] for key in ("arm", "project", "label"))
        record, raw = load_record(root, arm, project, label, declared["replicate"])
        record["replicate"] = declared["replicate"]
        record["evaluations"] = {}
        for rubric in RUBRICS:
            candidates = [evaluation for evaluation in evaluations_found
                          if evaluation["store"] == rubric and association(root, evaluation, record)]
            associated.update(evaluation["path"] for evaluation in candidates)
            rows = [inspect_evaluation(root, evaluation, record, raw,
                version="3.0" if rubric == "rubric10" else rubric20_version,
                evaluator_model=evaluator_model, target_context=normalized_contexts.get(project),
                instrument_snapshot=snapshots[rubric]) for evaluation in candidates]
            record["evaluations"][rubric] = {"files": rows}
        records.append(record)
    # Evidence with a selected label but an undeclared project stays visible.
    for arm, label in sorted({(r["arm"], r["label"]) for r in roster}):
        projects = {r["project"] for r in roster if r["arm"] == arm and r["label"] == label}
        for path in sorted((root / "data/d4d_concatenated").glob(f"*_core/{label}/*_provenance.yaml")):
            project = path.name.removesuffix("_provenance.yaml")
            if project not in projects:
                declared_valid, exclusion = None, "outside_selected_arm_project_roster"
                try:
                    declaration = document(read_local(root, path))
                    declared_valid = mapping(declaration.get("validation")).get("passed")
                    if declared_valid is False:
                        exclusion = "declared_invalid_generation_outside_selected_roster"
                except (OSError, ValueError, yaml.YAMLError, UnicodeError, RecursionError):
                    exclusion = "unreadable_provenance_outside_selected_roster"
                excluded.append({"arm": arm, "project": project, "label": path.parent.name,
                    "provenance": relative(root, path), "validation_passed": declared_valid,
                    "reason": exclusion})
    packages, seen_directories, seen_attempts = [], set(), {}
    for arm, directory in sorted(registered_evaluations, key=lambda item: (str(item[0]), str(item[1]))):
        require(isinstance(arm, str) and arm.strip() and len(arm) <= 4096,
                "registered audit arm requires a bounded nonempty string")
        selected_dir = local_path(root, str(directory))
        try:
            if selected_dir is not None:
                identity = selected_dir.stat()
                identity = (identity.st_dev, identity.st_ino)
                require(identity not in seen_directories, "registered_directory_duplicate")
                seen_directories.add(identity)
            package = registered_run(root, arm, directory, snapshots=snapshots,
                                     evaluator_model=evaluator_model, contexts=normalized_contexts,
                                     authority_roots=authority_roots, execution_lock_root=execution_lock_root,
                                     roster=roster)
        except (OSError, ValueError) as exc:
            package = {"arm": arm, "path": str(directory), "status": "refused", "record": None,
                "rows": [], "attempts": [], "reasons": [str(exc) if isinstance(exc, RegisteredRefusal)
                    else "registered_directory_missing_or_external"]}
        packages.append(package)
        candidate = package["record"]
        if candidate is None or candidate.get("record_role") != "full":
            continue
        matches = [record for record in records if all(record[key] == candidate[key]
                    for key in ("arm", "project", "label"))]
        if matches:
            record = matches[0]
            if (record["reasons"] == ["provenance_missing"] and not record["provenance_files"]
                    and record["record_path"] is None):
                record.update(candidate)
                record["replicate"] = next(r["replicate"] for r in roster
                    if (r["arm"], r["project"], r["label"]) == (arm, candidate["project"], candidate["label"]))
            same = (len(matches) == 1 and all(record.get(key) == candidate.get(key)
                    for key in ("record_sha256", "record_path", "provenance_sha256", "generation_method")))
            if not same:
                package["reasons"] = sorted(set(package["reasons"]) | {"registered_record_linkage_conflict"})
                record["reasons"] = sorted(set(record["reasons"]) | {"registered_record_linkage_conflict"})
                package["rows"] = []
            else:
                record["registered_run"] = candidate["registered_run"]
        else:
            record = candidate
            record["evaluations"] = {rubric: {"files": []} for rubric in RUBRICS}
            records.append(record)
        if package["reasons"]:
            record.setdefault("registered_input_problems", []).append({"path": package["path"],
                "rubric": package.get("rubric"), "reasons": package["reasons"]})
        for row in package["rows"]:
            identity = (row["manifest_sha256"], row["rating_index"])
            previous = seen_attempts.get(identity)
            if previous is not None:
                reason = ("registered_attempt_duplicate" if all(previous[key] == row[key] for key in
                    ("sha256", "transcript_sha256", "session_id")) else "registered_attempt_conflict")
                row["reasons"] = sorted(set(row["reasons"]) | {reason})
                row["eligible_for_condition_review"] = False
                if reason.endswith("conflict"):
                    previous["reasons"] = sorted(set(previous["reasons"]) | {reason})
                    previous["eligible_for_condition_review"] = False
            else:
                seen_attempts[identity] = row
            record["evaluations"][row["rubric"]]["files"].append(row)
    records.sort(key=lambda row: tuple(row[key] for key in ("arm", "project", "label")))
    # An artifact path can be reused by more than one provenance identity.
    # A label/path disagreement is therefore visible in every candidate record;
    # never resolve it by selecting the first or by trusting a filename.
    links = {}
    for record in records:
        for rubric, block in record["evaluations"].items():
            for row in block["files"]:
                links.setdefault(row["path"], []).append((record, rubric, block, row))
    for candidates in links.values():
        if len(candidates) <= 1:
            continue
        for record, rubric, block, row in candidates:
            row["reasons"] = sorted(set(row["reasons"]) | {"evaluation_linkage_ambiguous"})
            row["eligible_for_condition_review"] = False
    rescore = []
    for record in records:
        for rubric, block in record["evaluations"].items():
            rows = block["files"]
            for row in rows:
                row["eligible_for_condition_review"] = not row["reasons"] and not row["pending"] and not record["reasons"]
            reasons = set(record["reasons"])
            if not rows:
                reasons.add("evaluation_missing_from_selected_stores")
            elif not any(not row["reasons"] for row in rows):
                reasons.update(reason for row in rows for reason in row["reasons"])
            if not any(not row["reasons"] for row in rows):
                reasons.update(reason for problem in record.get("registered_input_problems", [])
                               if problem["rubric"] in (None, rubric) for reason in problem["reasons"])
            block.update(file_count=len(rows), reasons=sorted(reasons),
                pending=sorted({reason for row in rows for reason in row["pending"]}),
                repeat_panel=repeat_panel(rows) if rubric == "rubric20" else None,
                comparable_for_final_v10=False,
                status="rescore_or_ingestion_required" if reasons else "condition_review_pending")
            if reasons:
                rescore.append({**{key: record[key] for key in ("arm", "project", "label")},
                    "rubric": rubric, "target_version": "3.0" if rubric == "rubric10" else rubric20_version,
                    "reasons": sorted(reasons), "action": "ingest_bound_current_rating_or_rescore"})
    rescore.sort(key=lambda item: tuple(item[key] for key in ("arm", "project", "label", "rubric")))
    summary = []
    for arm in sorted({row["arm"] for row in records}):
        for project in sorted({row["project"] for row in records if row["arm"] == arm}):
            group = [row for row in records if row["arm"] == arm and row["project"] == project]
            summary.append({"arm": arm, "project": project, "expected_records": len(group),
                "bound_generation_runs": [row["registered_run"] for row in group if row.get("registered_run")],
                "canonical_labels": [row["label"] for row in group if row["canonical"]],
                "provenance_present": sum(bool(row["provenance_files"]) for row in group),
                "evaluations_present": {rubric: sum(row["evaluations"][rubric]["file_count"] > 0 for row in group) for rubric in RUBRICS},
                "rescore_or_ingestion_tuples": sum(item["arm"] == arm and item["project"] == project for item in rescore)})
    repeat_gaps = []
    for project in sorted({row["project"] for row in records}):
        candidates = [{"arm": row["arm"], "project": project, "label": row["label"], "rubric": "rubric20"}
                      for row in records if row["project"] == project and not row["reasons"]
                      and row["evaluations"]["rubric20"]["repeat_panel"]["three_distinct_session_claims_present"]]
        repeat_gaps.append({"project": project, "status": "independence_and_selection_review_pending" if candidates
                            else "fixed_record_selection_and_repeat_ratings_pending",
                            "three_session_candidate_tuples": candidates,
                            "action": "Select one fixed record per project; ingest or obtain >=3 ratings under the selected conditions, then authenticate separate rating sessions.",
                            "independence_verified": False})
    return {"format": "historical_evaluation_comparability_audit_v1",
        "scope": {"stores": stores, "filesystem_globs_include_ignored_and_hidden": True,
            "roster_manifest": roster_pin,
            "other_evaluation_directories_audited": bool(registered_evaluations), "historical_files_mutated": False,
            "absence_basis": "Only named nonrecursive label_aware stores, selected provenance paths and explicitly supplied registered directories.",
            "repeat_policy": "At least three independent ratings of one fixed selected record per project; no requirement to repeat every generation replicate."},
        "targets": {"rubric10": "3.0", "rubric20": rubric20_version,
            "evaluator_model": evaluator_model, "context_digests": {key: context_digest(value) for key, value in sorted(normalized_contexts.items())},
            "context_human_review_verified": False},
        "totals": {"expected_records": len(records), "parseable_files_in_selected_stores": len(evaluations_found),
            "associated_evaluation_files": len(associated), "rescore_or_ingestion_tuples": len(rescore),
            "excluded_records": len(excluded), "unreadable_evaluation_files": len(problems),
            "unassociated_evaluation_files": len(evaluations_found) - len(associated),
            "registered_directories": len(packages),
            "bound_registered_rating_files": sum(not row["reasons"] for package in packages for row in package["rows"]),
            "projects_with_repeat_actions": len(repeat_gaps)},
        "summary": summary, "records": records, "rescore_tuples": rescore,
        "registered_evaluations": [{key: value for key, value in package.items() if key not in {"record", "rows"}}
                                   for package in packages],
        "repeat_panel_actions": repeat_gaps,
        "excluded_records": excluded, "unreadable_evaluations": problems,
        "unassociated_evaluations": [{key: row[key] for key in ("path", "store", "sha256")}
                                    for row in evaluations_found if row["path"] not in associated],
        "interpretation": "Bound means internally consistent retained evidence, not proof of provider execution. Final claims require committed, unchanged packages plus separate scientific and independence review. Presence, hashes, model names and repeat counts do not establish human approval, runtime authenticity or scientific comparability. Review retained ratings outside these stores before commissioning rescoring."}


def markdown(result):
    def esc(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["# Historical evaluation comparability audit", "", result["interpretation"], "",
        f"Targets: rubric10 {result['targets']['rubric10']}; rubric20 {result['targets']['rubric20']}.",
        f"Expected records: {result['totals']['expected_records']}; associated evaluation files: {result['totals']['associated_evaluation_files']}; rescore/ingestion tuples: {result['totals']['rescore_or_ingestion_tuples']}.",
        "Applicability context presence is not human review. Counts cover only the named stores.", "",
        "| Arm | Project | Records | Provenance | Rubric10 present | Rubric20 present | Rescore/ingestion tuples |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for row in result["summary"]:
        lines.append("| " + " | ".join(esc(value) for value in (row["arm"], row["project"], row["expected_records"],
            row["provenance_present"], row["evaluations_present"]["rubric10"], row["evaluations_present"]["rubric20"],
            row["rescore_or_ingestion_tuples"])) + " |")
    lines += ["", "Canonical labels are provenance declarations, not independently reselected winners.",
              "", "## Recorded conditions", "", "| Arm | Project | Label | Rubric | File | Version | Evaluator | Context block/hash | Repeat evidence |",
              "|---|---|---|---|---|---|---|---|---|"]
    for record in result["records"]:
        for rubric, block in record["evaluations"].items():
            for row in block["files"]:
                panel = block["repeat_panel"]
                repeat = "not requested" if panel is None else f"{panel['distinct_reported_sessions']} distinct session claims; independence unverified"
                lines.append("| " + " | ".join(esc(value) for value in (record["arm"], record["project"], record["label"], rubric,
                    row["path"], row["version"], row["evaluator"], f"{row['context_block_present']} / {row['context_hash'] or 'missing'}", repeat)) + " |")
    lines += ["", "## Exact rescore or ingestion queue", "", "| Arm | Project | Label | Rubric | Target | Reasons |",
              "|---|---|---|---|---|---|"]
    for row in result["rescore_tuples"]:
        lines.append("| " + " | ".join(esc(value) for value in (row["arm"], row["project"], row["label"], row["rubric"],
            row["target_version"], "; ".join(row["reasons"]))) + " |")
    lines += ["", "No automatic rescore is authorized. First check retained ratings outside the selected stores.",
              f"Excluded records: {len(result['excluded_records'])}; unassociated evaluation files: {len(result['unassociated_evaluations'])}; unreadable files: {len(result['unreadable_evaluations'])}.", ""]
    lines += ["## Repeat-panel action queue", ""]
    for row in result["repeat_panel_actions"]:
        lines.append(f"- {row['project']}: {row['status']}. {row['action']}")
    lines += ["", "## Canonical declarations and excluded records", ""]
    for row in result["summary"]:
        lines.append(f"- {row['arm']} / {row['project']}: canonical labels: {', '.join(row['canonical_labels']) or 'none recorded'}.")
    for row in result["excluded_records"]:
        lines.append(f"- Excluded: {row['arm']} / {row['project']} / {row['label']}: {row['reason']}.")
    if result.get("registered_evaluations"):
        lines += ["", "## Explicit registered evaluation inputs", "",
                  "Captured transcript hashes and joins are audit evidence, not producer signatures or human approval.", ""]
        for row in result["registered_evaluations"]:
            bound = row.get("generation_run", {})
            lines.append(f"- {esc(row['arm'])} / {esc(row['path'])}: {esc(row['status'])}; "
                         f"{esc('; '.join(row['reasons']) or 'no package-level refusal')}; "
                         f"lock_verified={row.get('lock_verified', False)} ({row.get('lock_status', 'not_checked')}); "
                         f"committed_package={row.get('committed_package', False)}; "
                         f"bound arm={esc(bound.get('arm', 'unavailable'))}, "
                         f"method={esc(bound.get('method', 'unavailable'))}, label={esc(bound.get('label', 'unavailable'))}")
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--roster-manifest", type=Path, required=True,
                        help="Explicit evaluation_cohort_v1 manifest; no default campaign")
    parser.add_argument("--authority-root", type=Path, action="append", default=[],
                        help="Additional trusted authority directory; repeatable, read-only")
    parser.add_argument("--execution-lock-root", type=Path,
                        help="Execution lock store; defaults to the runner's local Git-common-dir store")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--rubric20-version", choices=("3.0", "4.0"), default="3.0")
    parser.add_argument("--evaluator-model", help="Explicit final-condition evaluator; no alias equivalence inferred")
    parser.add_argument("--context", action="append", default=[], metavar="PROJECT=PATH",
                        help="Independently selected context to compare, not a human-approval attestation")
    parser.add_argument("--registered-evaluation", action="append", default=[], metavar="ARM=DIR",
                        help="Explicit retained E1 directory inside --root; does not select a campaign comparator")
    args = parser.parse_args(argv)
    root, contexts = args.root.resolve(), {}
    roster, _ = read_cohort(args.roster_manifest)
    projects = {row["project"] for row in roster}
    for item in args.context:
        project, separator, name = item.partition("=")
        path = local_path(root, name)
        if (not separator or project in contexts or path is None
                or project not in projects):
            parser.error("--context requires a manifest project and unique PROJECT=PATH inside the checkout")
        contexts[project] = document(read(path))
    registered = []
    for item in args.registered_evaluation:
        arm, separator, name = item.partition("=")
        if not separator or not arm.strip() or not name or local_path(root, name) is None:
            parser.error("--registered-evaluation requires ARM=DIR inside the selected checkout")
        registered.append((arm, name))
    result = audit(root, roster_manifest=args.roster_manifest, rubric20_version=args.rubric20_version,
                   evaluator_model=args.evaluator_model, contexts=contexts, registered_evaluations=registered,
                   authority_roots=args.authority_root, execution_lock_root=args.execution_lock_root)
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) if args.format == "json" else markdown(result), end="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
