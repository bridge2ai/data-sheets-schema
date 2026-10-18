"""Captured, offline two-rater support/fitness panels (#4968).

Existing descriptors, attempts and execution ledgers retain their original
acceptors. A panel adds explicit cross-plan subject equality, never a dispatch.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

from . import cross_family_panel as vocabulary
from . import cross_family_panel_analysis as kernel
from . import nested_support_results as saved
from . import nested_support_execution as executor
from . import top_level_fitness_results as fitness
from . import support_targets as targets
from .evaluation_model import model_family
from .support_plan import canonical, sha256

FORMAT = "cross_family_judge_panel_v1"
RESULTS_FORMAT = "cross_family_judge_results_v1"
DECLARATION_FORMAT = "cross_family_judge_panel_declaration_v1"
SUBMISSIONS_FORMAT = "cross_family_judge_submissions_v1"
ROLES = ("same_family", "cross_family")
PROTOCOLS = (saved.FORMAT, fitness.FORMAT)
MAX_BYTES = saved.MAX_MANIFEST_BYTES
MAX_RECORDS = 10_000
MAX_PAIRS = 100_000
MAX_CELLS = 10_000
LIMITS = {"manifest_bytes": MAX_BYTES, "capture_bytes": saved.MAX_CAPTURE_BYTES,
          "records": MAX_RECORDS, "pairs": MAX_PAIRS, "slots": 2 * MAX_PAIRS,
          "matrix_cells": MAX_CELLS}
DECISIONS = ("selection_policy", "rater_policy", "route", "budget", "scientific_review",
             "context_review", "calibration", "private_control_handling", "canary",
             "execution_authorization")
AUTHORITY = tuple(sorted(set(executor._FITNESS_SOURCE_NAMES + (
    "cross_family_judge_panel.py", "cross_family_judge_analysis.py",
    "cross_family_panel_analysis.py", "cross_family_panel.py", "cross_family_panel_results.py",
    "resources.py", "profiles.py", "evaluation_context.py", "schema_digest.py",
))))
PanelError = vocabulary.PanelError
_need = vocabulary._need
_closed = vocabulary._closed
_identifier = vocabulary._identifier
_text = vocabulary._text
_digest = vocabulary._digest
_list = vocabulary._list
_path = vocabulary._path


def _read(raw, label):
    return saved._read(raw, label, limit=MAX_BYTES)


def _detached(value):
    raw = canonical(value)
    _need(len(raw) + 1 <= MAX_BYTES, "judge package exceeds manifest byte bound")
    return _read(raw, "judge package")


def _pin(value):
    return {k: value[k] for k in ("sha256", "bytes")}


def _authority(capture):
    result = {}
    for name in AUTHORITY:
        path = Path(__file__).parent / name
        raw = saved._file(path, saved.MAX_ARTIFACT_BYTES)
        result[name] = capture.add(raw)
        if isinstance(capture, _Capture):
            capture.watch.file(path, raw)
    return result


def _digest_bytes(capture, digest):
    _digest(digest, "artifact digest")
    if digest in capture.blobs:
        return capture.blobs[digest]
    directory = capture.root / "artifacts"
    _need(directory.is_dir() and not directory.is_symlink(), "unsafe artifact directory")
    raw = saved._file(directory / digest, MAX_BYTES)
    _need(sha256(raw) == digest, "captured artifact digest differs")
    capture.add(raw)
    if isinstance(capture, _Capture):
        capture.watch.file(directory / digest, raw)
    return raw


def _reference(value):
    _closed(value, {"path", "sha256"}, "reference")
    _path(value["path"])
    _digest(value["sha256"], "reference digest")
    return value


class _Watch:
    """Bounded observations of the files actually acquired, not a stability claim."""
    def __init__(self):
        self.files = {}
        self.directories = {}
        self.absent_files = set()

    def file(self, path, raw):
        path = Path(path)
        pin = saved._pin(raw)
        _need(path not in self.files or self.files[path] == pin, "source changed during capture")
        self.files[path] = pin

    def directory(self, path, *, names=None):
        path = Path(path)
        _need(path.is_dir() and not path.is_symlink(), "source directory must be real")
        names = sorted(p.name for p in path.iterdir()) if names is None else sorted(names)
        _need(path not in self.directories or self.directories[path] == names,
              "source directory changed during capture")
        self.directories[path] = names

    def verify(self):
        for path in self.absent_files:
            _need(not path.exists() and not path.is_symlink(), "previously absent source file appeared")
        for path, pin in self.files.items():
            _need(saved._pin(saved._file(path, max(MAX_BYTES, pin["bytes"]))) == pin,
                  "source bytes changed before publication")
        for path, names in self.directories.items():
            _need(path.is_dir() and not path.is_symlink()
                  and sorted(p.name for p in path.iterdir()) == names,
                  "source frontier changed before publication")


class _Capture(saved.Capture):
    def __init__(self, root, watch):
        super().__init__(root)
        self.watch = watch

    def entry(self, name, limit=MAX_BYTES):
        raw = super().entry(name, limit=limit)
        self.watch.file(self.root / name, raw)
        return raw

    def get(self, pin, limit=saved.MAX_ARTIFACT_BYTES):
        missing = pin["sha256"] not in self.blobs
        raw = super().get(pin, limit=limit)
        if missing:
            self.watch.file(self.root / "artifacts" / pin["sha256"], raw)
        return raw


def _copy(into, other):
    for raw in other.blobs.values():
        into.add(raw)


def _inside(root, name):
    relative = _path(name)
    path = root / relative
    for component in [path, *path.parents]:
        if component == root:
            break
        _need(not component.is_symlink(), "input reference cannot traverse a symlink")
    _need(path.resolve().is_relative_to(root), "input reference leaves explicit root")
    return path


def _descriptor(capture, raw, protocol):
    _need(protocol in PROTOCOLS, "unsupported descriptor protocol")
    return (saved if protocol == saved.FORMAT else fitness)._load_descriptor(capture, raw)


def _result(capture, raw, protocol):
    _need(protocol in PROTOCOLS, "unsupported result protocol")
    return (fitness._support if protocol == saved.FORMAT else fitness._recheck_captured)(capture, raw)


class _Reader:
    def __init__(self, root, capture, watch):
        root = Path(root)
        _need(root.is_dir() and not root.is_symlink(), "explicit source root must be real")
        self.root, self.capture, self.watch = root.resolve(), capture, watch
        self.cache = {}
        self.protected = set()

    def read(self, reference, entry=None, protocol=None):
        reference = _reference(reference)
        key = (reference["path"], reference["sha256"], entry, protocol)
        if key in self.cache:
            return self.cache[key]
        path = _inside(self.root, reference["path"])
        self.protected.add(path)
        if entry is None:
            raw = saved._file(path, MAX_BYTES)
            self.watch.file(path, raw)
            self.capture.add(raw)
        else:
            other = _Capture(path, self.watch)
            raw = other.entry(entry)
            if entry == "descriptor.json":
                _descriptor(other, raw, protocol)
            elif entry == "registration.json":
                executor._load(other, raw)
            elif entry == "result.json":
                _result(other, raw, protocol)
            else:
                raise PanelError("unsupported captured entry")
            _copy(self.capture, other)
        _need(sha256(raw) == reference["sha256"], "declared entry bytes differ")
        self.cache[key] = raw
        return raw

    def execution(self, reference):
        _closed(reference, {"path", "registration_sha256"}, "execution source")
        path = _inside(self.root, reference["path"])
        self.protected.add(path)
        _digest(reference["registration_sha256"], "execution registration digest")
        # The historical reader alone admits names/counts and acquires bytes
        # into its bounded Capture. Do not read an unvalidated frontier merely
        # to build preservation observations. The returned ledger is the exact
        # acquired frontier; cached blobs supply every watched byte image.
        other, ledger = executor.capture_run(path)
        observed = _Capture(path, self.watch)
        registration_raw = other.get(ledger["registration"])
        observed.add(registration_raw)
        self.watch.file(path / "registration.json", registration_raw)
        self.watch.directory(path / "attempts", names=[f"{i:06d}" for i in range(len(ledger["attempts"]))])
        for index, row in enumerate(ledger["attempts"]):
            directory = path / "attempts" / f"{index:06d}"
            names = [key + ".json" for key in ("admitted", "response", "settled") if row[key] is not None]
            self.watch.directory(directory, names=names)
            for key in ("admitted", "response", "settled"):
                if row[key] is not None:
                    entry_raw = other.get(row[key])
                    observed.add(entry_raw)
                    self.watch.file(directory / (key + ".json"), entry_raw)
        # Seed only the entry files actually acquired above. Replaying the
        # unchanged checker makes each required artifact a watched cache miss.
        # A deleted/replaced input cannot hide behind the first capture's
        # cache, while naturally computed blobs are never presumed disk files.
        executor.recheck_captured(observed, ledger)
        other = observed
        report_path = path / "report.json"
        report = None
        if report_path.exists() or report_path.is_symlink():
            raw = saved._file(report_path, MAX_BYTES)
            self.watch.file(report_path, raw)
            report = other.add(raw)
        else:
            self.watch.absent_files.add(report_path)
        _copy(self.capture, other)
        _need(ledger["registration"]["sha256"] == reference["registration_sha256"],
              "run registration differs from submission")
        return {"ledger": ledger, "saved_report": report}


def _portable_reader(capture):
    def read(reference, entry=None, protocol=None):
        _reference(reference)
        return _digest_bytes(capture, reference["sha256"])
    return read


def _common_subject(capture, descriptor, selection, cache=None):
    """The fixed axis-specific projection; never compare unused declarations."""
    binding = selection["binding"]
    cache = {} if cache is None else cache
    key = descriptor["plan"]["sha256"]
    if key not in cache:
        manifest = _read(capture.get(descriptor["plan"]), "captured plan")
        cache[key] = (manifest, {r["id"]: r for r in manifest["records"]})
    manifest, records = cache[key]
    record = records[binding["record_id"]]
    schema = manifest["schema"]
    support = binding["axis"] == targets.AXIS
    instrument = manifest["instruments"][binding["axis"]]
    # The support acceptor reconstructs its vocabulary meaning but does not
    # check these planning labels. Validate this finite comparison metadata
    # without invoking the fitness reconstructor or demanding its artifact.
    _text(schema["profile"], "schema profile")
    _need(schema["profile_basis"] == "explicit", "schema profile basis must be explicit")
    vocabulary_names = []
    if schema["vocabulary"] is None:
        _need(schema["vocabulary_basis"] == "explicit_profile_without_vocabulary"
              and schema["vocabulary_path"] is None, "missing vocabulary basis conflicts")
    else:
        _need(schema["vocabulary_basis"] in ("explicit_vocabulary_override", "explicit_profile_pin"),
              "unsupported vocabulary basis")
        _text(schema["vocabulary_path"], "vocabulary lineage")
        vocab = capture.document(schema["vocabulary"], "vocabulary", yaml_allowed=True)["vocabularies"]
        _need(type(vocab) is dict and all(type(k) is str for k in vocab), "invalid vocabulary names")
        vocabulary_names = sorted(vocab)
    _need(schema["vocabulary_names"] == vocabulary_names, "vocabulary names conflict with captured bytes")
    sources = [{"import_key": s["import_key"], **_pin(s)} for s in schema["sources"]]
    projected_schema = {k: schema[k] for k in ("class", "profile", "profile_basis",
                                              "vocabulary_basis", "vocabulary_names")}
    projected_schema.update(root_import_key=schema["sources"][0]["import_key"],
        sources=sorted(sources, key=lambda r: r["import_key"]),
        nested_specification=_pin(schema["nested_specification"]) if support else None,
        nested_specification_sha256=schema["nested_specification_sha256"] if support else None,
        fitness_specifications=None if support else _pin(schema["fitness_specifications"]),
        generation_digest=None if support else schema["generation_digest"],
        vocabulary=None if schema["vocabulary"] is None else _pin(schema["vocabulary"]))
    request = _read(capture.get(binding["request"]), "verified request")
    _closed(request, {"model", "max_tokens", "temperature", "system", "messages"}, "verified request")
    exposure = capture.add(canonical({k: request[k] for k in ("temperature", "system", "messages")}))
    context = None if support else {k: v for k, v in binding["context"].items() if k != "model"}
    return {"record_identity": {k: record[k] for k in ("project", "label", "method", "cohort", "generation_rep")},
        "record": _pin(record["record"]), "provenance": _pin(record["provenance"]),
        "bundle": _pin(record["bundle"]), "artifact_kind": binding["artifact_kind"],
        "schema": projected_schema, "axis": binding["axis"], "kind": binding["kind"],
        "pointer": binding["pointer"], "value_sha256": binding["value_sha256"],
        "instrument": {"name": instrument["name"], "system": _pin(instrument["system"]),
            "support_policy": instrument["policy"] if support else None,
            "support_context_policy": instrument.get("context_policy", targets.CONTEXT_POLICY) if support else None,
            "fitness_granularity": None if support else instrument["granularity"]},
        "support_target": _pin(binding["target"]) if support else None,
        "fitness_context": context, "request_exposure": exposure,
        "generator": {"model": record["generator"], "family": model_family(record["generator"])}}


def _empty_slot(pair_id, role):
    return {"pair_id": pair_id, "role": role, "descriptor": None, "target_id": None,
        "attempt_id": None, "binding": None, "rater": None, "execution_registration": None,
        "slot_state": "unregistered", "assessment_state": None, "dispatch_state": "missing",
        "spent": None, "evidence_basis": "caller_saved", "assessment": None,
        "saved_result": None, "execution": None, "problems": ["unregistered_slot"]}


def _attribution(subject, slots):
    reasons = []
    generator = subject["generator"]["family"]
    families = [s["rater"]["family"] if s["rater"] else None for s in slots]
    if generator is None:
        reasons.append("generator_family_unknown")
    if any(f is None for f in families):
        reasons.append("rater_family_unknown")
    for slot in slots:
        if slot["rater"] is None or slot["rater"]["rater"] is None or slot["rater"]["route"] is None:
            reasons.append("rater_or_route_missing:" + slot["role"])
    if generator is not None and all(f is not None for f in families):
        if sum(f == generator for f in families) != 1:
            reasons.append("exactly_one_matching_family_required")
        if families[0] != generator or families[1] == generator:
            reasons.append("declared_role_family_mismatch")
    return reasons


def _pair(row, subject, slots):
    reasons = _attribution(subject, slots)
    return {"pair_id": row["pair_id"], "record_id": row["record_id"],
        "project": subject["record_identity"]["project"], "cohort": subject["record_identity"]["cohort"],
        "axis": subject["axis"], "kind": subject["kind"], "pointer": subject["pointer"],
        "common_subject": subject, "common_subject_sha256": sha256(canonical(subject)),
        "selection_stratum": row["selection_stratum"], "selected": None,
        "slots": {s["role"]: s for s in slots},
        "compatible_pair": all(s["descriptor"] is not None for s in slots),
        "accepted_pair": False, "attributed_role_pair": not reasons,
        "attribution_reasons": reasons, "operands": None, "mapped_operands": {},
        "gap_values": {}, "eligibility_reasons": ["results_not_supplied"]}


def _panel(capture, declaration_raw, read):
    declared = _closed(_read(declaration_raw, "panel declaration"), {"format", "panel_id",
        "predecessor_sha256", "matrix", "descriptors", "pairs", "decisions"}, "panel declaration")
    _need(declared["format"] == DECLARATION_FORMAT, "unsupported judge panel declaration")
    _identifier(declared["panel_id"], "panel_id")
    if declared["predecessor_sha256"] is not None:
        _digest(declared["predecessor_sha256"], "predecessor digest")
    matrix = _closed(declared["matrix"], {"projects", "cohorts"}, "matrix")
    for name in ("projects", "cohorts"):
        values = _list(matrix[name], name, MAX_CELLS)
        _need(values and len(values) == len(set(_text(v, name) for v in values)), "empty/duplicate matrix axis")
    _need(len(matrix["projects"]) * len(matrix["cohorts"]) <= MAX_CELLS, "matrix cell bound exceeded")
    pending = []
    _closed(declared["decisions"], DECISIONS, "decisions")

    def reference(ref):
        if ref is not None:
            capture.add(read(_reference(ref)))

    for name, decision in declared["decisions"].items():
        _closed(decision, {"status", "reference"}, "decision")
        _need(decision["status"] in ("pending", "declared"), "invalid decision status")
        _need(decision["status"] != "declared" or decision["reference"] is not None, "declared decision needs reference")
        reference(decision["reference"])
        if decision["status"] == "pending":
            pending.append("decisions." + name)
    descriptors, by_id, checked, subject_cache = [], {}, {}, {}
    output_reservation = 0
    for row in _list(declared["descriptors"], "descriptors", 2 * MAX_PAIRS):
        _closed(row, {"descriptor_id", "protocol", "source"}, "descriptor declaration")
        did = _identifier(row["descriptor_id"], "descriptor_id")
        _need(did not in by_id and row["protocol"] in PROTOCOLS, "duplicate/unsupported descriptor")
        raw = read(row["source"], "descriptor.json", row["protocol"])
        descriptor_key = (row["protocol"], sha256(raw))
        if descriptor_key not in checked:
            checked[descriptor_key] = _descriptor(capture, raw, row["protocol"])
        desc = checked[descriptor_key]
        item = {"descriptor_id": did, "protocol": row["protocol"], "source": row["source"],
                "descriptor": capture.add(raw), "selected_target_ids": [s["target_id"] for s in desc["selections"]],
                "panel_target_ids": [], "unselected_target_ids": [],
                "unselected_record_verification": "original_plan_declarations_only"}
        descriptors.append(item)
        by_id[did] = (item, desc, {s["target_id"]: s for s in desc["selections"]})
        output_reservation += len(canonical(item))
        _need(output_reservation <= MAX_BYTES, "panel descriptor output bound exceeded")
    pairs, slots, records = [], [], {}
    used_descriptors, used_slots, subjects, record_keys, pair_ids = set(), set(), set(), {}, set()
    logical_records = {}

    def choose(did, tid):
        _need(did in by_id, "unknown descriptor reference")
        item, desc, index = by_id[did]
        _need(type(tid) is str and tid in index, "target is not an exact selected descriptor target")
        used_descriptors.add(did)
        item["panel_target_ids"].append(tid)
        return item, desc, index[tid]

    for row in _list(declared["pairs"], "pairs", MAX_PAIRS):
        _closed(row, {"pair_id", "record_id", "anchor", "selection_stratum", "slots"}, "pair declaration")
        pid, rid = _identifier(row["pair_id"], "pair_id"), _identifier(row["record_id"], "record_id")
        _need(pid not in pair_ids, "duplicate pair_id")
        pair_ids.add(pid)
        _closed(row["anchor"], {"descriptor_id", "target_id"}, "anchor")
        _, anchor, chosen = choose(row["anchor"]["descriptor_id"], row["anchor"]["target_id"])
        subject = _common_subject(capture, anchor, chosen, subject_cache)
        subject_key = canonical(subject)
        _need(subject_key not in subjects, "duplicate common subject under another pair ID")
        subjects.add(subject_key)
        identity = subject["record_identity"]
        _need(identity["project"] in matrix["projects"] and identity["cohort"] in matrix["cohorts"], "record outside matrix")
        record_key = canonical({k: subject[k] for k in ("record_identity", "record", "provenance", "bundle", "generator")})
        logical_key = canonical(identity)
        logical_binding = (rid, record_key)
        _need(logical_key not in logical_records or logical_records[logical_key] == logical_binding,
              "logical generation has conflicting record identity, content or lineage")
        logical_records[logical_key] = logical_binding
        _need(record_key not in record_keys or record_keys[record_key] == rid, "logical record has two panel IDs")
        record_keys[record_key] = rid
        value = {"record_id": rid, "captured_identity": identity, **{k: subject[k] for k in ("record", "provenance", "bundle", "generator")},
                 "duplicate_input_record_ids": []}
        _need(rid not in records or canonical(records[rid]) == canonical(value), "panel record ID has conflicting identity")
        records[rid] = value
        _need(len(records) <= MAX_RECORDS, "record bound exceeded")
        stratum = _closed(row["selection_stratum"], {"status", "label", "reference"}, "selection stratum")
        labels = ("supported", "unsupported") if subject["axis"] == targets.AXIS else ("fit", "unfit")
        _need(stratum["status"] in ("pending", "declared") and (stratum["label"] is None or stratum["label"] in labels), "invalid selection stratum")
        _need(stratum["status"] != "declared" or stratum["label"] is not None and stratum["reference"] is not None, "declared stratum needs label and reference")
        reference(stratum["reference"])
        if stratum["status"] == "pending":
            pending.append("selection_stratum." + pid)
        _closed(row["slots"], ROLES, "pair slots")
        selected_slots = []
        for role in ROLES:
            requested = row["slots"][role]
            slot = _empty_slot(pid, role)
            if requested is not None:
                _closed(requested, {"descriptor_id", "target_id", "attempt_id", "rater", "execution_registration"}, "slot")
                item, desc, sel = choose(requested["descriptor_id"], requested["target_id"])
                _need(requested["attempt_id"] == sel["attempt_id"], "slot attempt differs from descriptor")
                _need(canonical(_common_subject(capture, desc, sel, subject_cache)) == subject_key, "slot common subject differs")
                key = (item["descriptor"]["sha256"], sel["attempt_id"])
                _need(key not in used_slots, "descriptor attempt reused in multiple slots")
                used_slots.add(key)
                rater = _closed(requested["rater"], {"rater", "route"}, "rater")
                for name in rater:
                    vocabulary._optional_text(rater[name], name)
                registration = None
                if requested["execution_registration"] is not None:
                    raw = read(requested["execution_registration"], "registration.json")
                    reg = executor._load(capture, raw)
                    _need(reg["descriptor"] == item["descriptor"], "registration belongs to a different descriptor")
                    _need(reg["format"] == (executor.FORMAT if item["protocol"] == saved.FORMAT else executor.FITNESS_FORMAT), "execution protocol differs")
                    registration = capture.add(raw)
                model = sel["binding"]["model"]
                slot.update(descriptor=item["descriptor"], target_id=sel["target_id"], attempt_id=sel["attempt_id"],
                    binding=sel["binding"], rater={**rater, "model": model, "family": model_family(model["name"])},
                    execution_registration=registration, slot_state="missing", dispatch_state="missing" if registration else "unknown",
                    evidence_basis="captured_execution" if registration else "caller_saved", problems=["result_missing"])
            selected_slots.append(slot)
            slots.append(slot)
        pair = _pair(row, subject, selected_slots)
        output_reservation += len(canonical(pair)) + len(canonical(selected_slots)) + len(canonical(value))
        _need(output_reservation <= MAX_BYTES, "panel row output bound exceeded")
        pairs.append(pair)
    _need(used_descriptors == set(by_id), "unreferenced descriptor declaration")
    for item in descriptors:
        item["panel_target_ids"] = sorted(set(item["panel_target_ids"]))
        item["unselected_target_ids"] = [tid for tid in item["selected_target_ids"] if tid not in item["panel_target_ids"]]
    content = defaultdict(list)
    for r in records.values():
        content[r["record"]["sha256"]].append(r["record_id"])
    for r in records.values():
        r["duplicate_input_record_ids"] = sorted(content[r["record"]["sha256"]])
    cells = [{"project": p, "cohort": c, "record_ids": sorted(r["record_id"] for r in records.values()
              if r["captured_identity"]["project"] == p and r["captured_identity"]["cohort"] == c),
              "pair_ids": sorted(r["pair_id"] for r in pairs if r["project"] == p and r["cohort"] == c)}
             for p in matrix["projects"] for c in matrix["cohorts"]]
    return _detached({"format": FORMAT, "declaration": capture.add(declaration_raw), "panel_id": declared["panel_id"],
        "predecessor_sha256": declared["predecessor_sha256"], "descriptors": sorted(descriptors, key=lambda r: r["descriptor_id"]),
        "records": sorted(records.values(), key=lambda r: r["record_id"]), "pairs": sorted(pairs, key=lambda r: r["pair_id"]),
        "slots": sorted(slots, key=lambda r: (r["pair_id"], ROLES.index(r["role"]))),
        "coverage": {"matrix": matrix, "cells": cells, "missing_cells": [c for c in cells if not c["record_ids"]],
                     "records": len(records), "expected_pairs": len(pairs), "expected_slots": len(slots)},
        "pending_decisions": sorted(pending), "readiness": {"complete_registration": all(s["descriptor"] is not None for s in slots),
            "pending_decisions": bool(pending), "empirical_completion": False},
        "authority": _authority(capture), "limits": LIMITS, "scientific_eligibility": False, "execution_authorized": False})


def _checked_panel(capture, raw):
    old = _read(raw, "panel")
    _need(type(old) is dict and old.get("format") == FORMAT, "unsupported panel format")
    rebuilt = _panel(capture, capture.get(old["declaration"]), _portable_reader(capture))
    _need(canonical(rebuilt) == canonical(old), "panel differs from exact captured reconstruction")
    return rebuilt


def _results(capture, panel_raw, submissions_raw, read, read_execution):
    panel = _checked_panel(capture, panel_raw)
    declared = _closed(_read(submissions_raw, "submissions"), {"format", "panel_sha256", "slots"}, "submissions")
    _need(declared["format"] == SUBMISSIONS_FORMAT and declared["panel_sha256"] == sha256(panel_raw), "submissions name another panel")
    known = {(s["pair_id"], s["role"]): s for s in panel["slots"]}
    supplied = {}
    for row in _list(declared["slots"], "submitted slots", 2 * MAX_PAIRS):
        _closed(row, {"pair_id", "role", "saved_result", "execution"}, "submission")
        key = (row["pair_id"], row["role"])
        _need(key in known and key not in supplied, "foreign/duplicate submitted slot")
        _need(known[key]["descriptor"] is not None, "cannot submit to an unregistered slot")
        _need(row["saved_result"] is not None or row["execution"] is not None, "empty submission")
        supplied[key] = row
    slots = []
    output_reservation = len(canonical(panel["pairs"]))
    for key, original in known.items():
        slot = _detached(original)
        row = supplied.get(key)
        if row is not None:
            support = slot["binding"]["axis"] == targets.AXIS
            protocol = saved.FORMAT if support else fitness.FORMAT
            result = None
            if row["saved_result"] is not None:
                raw = read(row["saved_result"], "result.json", protocol)
                result = _result(capture, raw, protocol)
                _need(result["descriptor"] == slot["descriptor"] and result["target_id"] == slot["target_id"]
                      and result["attempt_id"] == slot["attempt_id"]
                      and canonical(result["binding"]) == canonical(slot["binding"]), "saved result belongs to another slot")
            execution = None
            dispatch = "missing" if slot["execution_registration"] else "unknown"
            spent = None
            problems = []
            if row["execution"] is not None:
                _need(slot["execution_registration"] is not None, "unregistered execution requires successor panel")
                _closed(row["execution"], {"path", "registration_sha256"}, "execution reference")
                _path(row["execution"]["path"])
                _need(row["execution"]["registration_sha256"] == slot["execution_registration"]["sha256"], "execution registration differs from panel")
                evidence = read_execution(row["execution"], key)
                _need(evidence["ledger"]["registration"] == slot["execution_registration"], "captured registration differs from panel")
                descriptor_raw = capture.get(slot["descriptor"])
                desc = _descriptor(capture, descriptor_raw, protocol)
                rows, execution, _ = fitness._execution(capture, descriptor_raw, desc, evidence, support=support)
                dispatch_row, actual = rows.get(slot["attempt_id"], (None, None))
                if result is not None:
                    _need(actual is not None and canonical(actual) == canonical(result), "standalone result differs from ledger-associated exact result")
                result = actual
                dispatch = dispatch_row["status"] if dispatch_row else "not_started"
                spent = dispatch != "not_started"
                problems.extend(dispatch_row.get("problems", []) if dispatch_row else ["execution_not_started"])
            elif slot["execution_registration"] is not None:
                problems.append("registered_execution_missing")
            assessment = None if result is None else result["assessment"]
            state = assessment["status"] if assessment else "missing"
            if slot["execution_registration"] is not None:
                state = "accepted" if dispatch == "accepted" and state == "accepted" else "rejected" if dispatch == "failed" else "missing"
            if assessment:
                problems.extend(assessment.get("problems", []))
            slot.update(slot_state=state, assessment_state=None if assessment is None else assessment["status"],
                        dispatch_state=dispatch, spent=spent, assessment=assessment, saved_result=result,
                        execution=execution, problems=list(dict.fromkeys(problems)))
        output_reservation += 2 * len(canonical(slot))
        _need(output_reservation <= MAX_BYTES, "result row output bound exceeded")
        slots.append(slot)
    by_pair = defaultdict(dict)
    for slot in slots:
        by_pair[slot["pair_id"]][slot["role"]] = slot
    pairs = []
    for row in panel["pairs"]:
        pair = _detached(row)
        pair["slots"] = by_pair[row["pair_id"]]
        pair["accepted_pair"] = all(pair["slots"][r]["slot_state"] == "accepted" for r in ROLES)
        pair["operands"] = {r: (pair["slots"][r]["assessment"] if pair["slots"][r]["slot_state"] == "accepted" else None) for r in ROLES}
        pair["eligibility_reasons"] = [r + ":" + pair["slots"][r]["slot_state"] for r in ROLES if pair["slots"][r]["slot_state"] != "accepted"]
        pairs.append(pair)
    return _detached({"format": RESULTS_FORMAT, "panel": capture.add(panel_raw), "submissions": capture.add(submissions_raw),
        "slots": slots, "pairs": pairs, "counts": {"expected_slots": len(slots), "slot_states": {
            state: sum(s["slot_state"] == state for s in slots) for state in ("unregistered", "missing", "rejected", "accepted")},
            "expected_pairs": len(pairs), "accepted_pairs": sum(p["accepted_pair"] for p in pairs)},
        "coverage": panel["coverage"], "pending_decisions": panel["pending_decisions"],
        "readiness": {**panel["readiness"], "all_pairs_accepted": all(p["accepted_pair"] for p in pairs)},
        "authority": _authority(capture), "limits": LIMITS, "scientific_eligibility": False, "execution_authorized": False})


def _checked_results(capture, raw):
    old = _read(raw, "judge results")
    _need(type(old) is dict and old.get("format") == RESULTS_FORMAT, "unsupported judge results format")
    evidence = {(s["pair_id"], s["role"]): s["execution"] for s in old["slots"]}
    def execution(ref, key):
        value = evidence[key]
        _need(value is not None, "missing captured execution ledger")
        return {k: value[k] for k in ("ledger", "saved_report")}
    rebuilt = _results(capture, capture.get(old["panel"]), capture.get(old["submissions"]), _portable_reader(capture), execution)
    _need(canonical(old) == canonical(rebuilt), "results differ from exact captured reconstruction")
    return rebuilt


def prepare_panel(declaration: Path, output: Path, *, root: Path) -> dict:
    output = kernel._publication_path(output)
    watch = _Watch()
    capture = _Capture(root, watch)
    raw = saved._file(Path(declaration), MAX_BYTES)
    watch.file(declaration, raw)
    reader = _Reader(root, capture, watch)
    value = _panel(capture, raw, reader.read)
    watch.verify()
    # Here root is a lookup namespace, not one input package. Protect exactly
    # the acquired packages/files while reusing the unmodified publisher.
    view = SimpleNamespace(root=Path(declaration).resolve(), blobs=capture.blobs)
    kernel._publish_new(output, view, "panel.json", value, protected=reader.protected)
    return value


def recheck_panel(directory: Path) -> dict:
    capture = saved.Capture(directory)
    return _checked_panel(capture, capture.entry("panel.json"))


def accept_panel_results(panel: Path, submissions: Path, output: Path, *, root: Path) -> dict:
    output = kernel._publication_path(output)
    watch = _Watch()
    capture = _Capture(panel, watch)
    panel_raw = capture.entry("panel.json")
    raw = saved._file(Path(submissions), MAX_BYTES)
    watch.file(submissions, raw)
    reader = _Reader(root, capture, watch)
    value = _results(capture, panel_raw, raw, reader.read, lambda ref, key: reader.execution(ref))
    watch.verify()
    kernel._publish_new(output, capture, "results.json", value,
                        protected=(*reader.protected, panel, submissions))
    return value


def recheck_panel_results(directory: Path) -> dict:
    capture = saved.Capture(directory)
    return _checked_results(capture, capture.entry("results.json"))
