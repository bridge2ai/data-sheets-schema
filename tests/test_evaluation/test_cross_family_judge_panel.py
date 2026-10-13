"""Invented offline panels exercise original authorities, never model accuracy."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import cross_family_judge_panel as panel
from data_sheets_schema import cross_family_judge_analysis as analysis
from data_sheets_schema import cross_family_panel_analysis as kernel
from data_sheets_schema import nested_support_results as support
from data_sheets_schema import top_level_fitness_results as fitness
from data_sheets_schema import nested_support_execution as execution
from data_sheets_schema.cli.evaluate import evaluate
from data_sheets_schema.support_plan import canonical, sha256
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401
from tests.test_evaluation.test_nested_support_plan import build
from tests.test_evaluation.test_nested_support_execution import declaration as execution_declaration

ROLES = ("same_family", "cross_family")
AXES = ("grounding_v3", "fitness")
DECISIONS = ("selection_policy", "rater_policy", "route", "budget", "scientific_review",
             "context_review", "calibration", "private_control_handling", "canary",
             "execution_authorization")
PANEL_KEYS = {"format", "declaration", "panel_id", "predecessor_sha256", "descriptors",
              "records", "pairs", "slots", "coverage", "pending_decisions", "readiness",
              "authority", "limits", "scientific_eligibility", "execution_authorized"}
RESULT_KEYS = {"format", "panel", "submissions", "slots", "pairs", "counts", "coverage",
               "pending_decisions", "readiness", "authority", "limits",
               "scientific_eligibility", "execution_authorized"}


def write(path, value):
    path.write_bytes(canonical(value))
    return path


def ref(root, directory, name):
    return {"path": directory.relative_to(root).as_posix(),
            "sha256": sha256((directory / name).read_bytes())}


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts}


def native(axis, model, value=None, *, rejected=False):
    payload = ({"verdict": "supported", "reason": "Invented software control."}
               if axis == "grounding_v3" else
               {"fitness": 0.75, "failure": "none", "reason": "Invented software control."})
    if value is not None:
        payload.update(value)
    return canonical({"id": "invented-message", "type": "message", "role": "assistant",
        "model": model, "stop_reason": "max_tokens" if rejected else "end_turn",
        "stop_sequence": None, "usage": {"input_tokens": 12, "output_tokens": 23,
            "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
        "content": [{"type": "text", "text": json.dumps(payload)}]})


def make_case(fixture, tmp_path, *, count=1, axes=AXES, pointers=("/count", "/enabled"),
              models=("claude-opus-5", "gpt-5"), caps=(417, 418), same_input=False,
              change_declaration=None, before_second=None, execution_bound=False,
              prepare=True):
    """Build two real plans and their ordinary axis-specific descriptors."""
    source, _ = fixture
    jobs, pins = [], {}
    bundle = (source / "bundle.txt").read_bytes()
    for i in range(count):
        record = {"id": "ex:shared" if same_input else f"ex:record-{i}",
                  "title": "Invented record", "count": 0, "enabled": False,
                  "creators": [{"name": "Dana"}], "notes": None}
        record_path = source / f"record-{i}.yaml"
        record_path.write_text(yaml.safe_dump(record), encoding="utf-8")
        pins[record_path.name] = sha256(record_path.read_bytes())
        provenance = {"run": {"project": "Harbor", "label": f"condition_rep{i + 1}", "method": "api"},
                      "model": {"model": "claude-opus-5"},
                      "inputs": {"bundle_path": "bundle.txt", "bundle_md5": hashlib.md5(bundle).hexdigest()}}
        provenance_path = source / f"provenance-{i}.yaml"
        provenance_path.write_text(yaml.safe_dump(provenance), encoding="utf-8")
        for rubric in ("rubric10", "rubric20"):
            jobs.append({"id": f"record-{i}-{rubric}", "input": record_path.name,
                "project": "Harbor", "label": f"condition_rep{i + 1}", "method": "api",
                "cohort": "v7", "generation_rep": i + 1, "purpose": "primary", "rubric": rubric,
                "output": f"record-{i}-{rubric}.json", "provenance": provenance_path.name})
    write(source / "roster.json", {"jobs": jobs, "pinned_files": pins})
    declaration = {"format": "cross_family_judge_panel_declaration_v1", "panel_id": "invented-panel",
        "predecessor_sha256": None, "matrix": {"projects": ["Harbor"], "cohorts": ["v7"]},
        "descriptors": [], "pairs": [],
        "decisions": {k: {"status": "pending", "reference": None} for k in DECISIONS}}
    descriptors, lookups, plans, executions = {}, {}, [], {}
    for role_index, role in enumerate(ROLES):
        if role_index and before_second:
            source = before_second(source) or source
        plan_path = tmp_path / f"plan-{role}"
        manifest = build((source, plan_path), model=models[role_index], max_tokens=caps[role_index])
        plans.append((plan_path, manifest))
        record_indices = {r["id"]: r["generation_rep"] - 1 for r in manifest["records"]}
        for axis in axes:
            api = support if axis == "grounding_v3" else fitness
            selected = [t for t in manifest["targets"] if t["axis"] == axis and t["pointer"] in pointers]
            selected.sort(key=lambda t: (record_indices[t["record_id"]], t["pointer"], t["kind"]))
            selections = [{"target_id": t["id"], "attempt_id": f"attempt-{i}"}
                          for i, t in enumerate(selected)]
            descriptor_id = role + "-" + axis
            directory = tmp_path / ("descriptor-" + descriptor_id)
            document = api.prepare(plan_path, directory, selections=selections, protocol=api.FORMAT)
            descriptors[descriptor_id] = (directory, document, api)
            declaration["descriptors"].append({"descriptor_id": descriptor_id, "protocol": api.FORMAT,
                "source": ref(tmp_path, directory, "descriptor.json")})
            for t, selection in zip(selected, selections):
                key = (record_indices[t["record_id"]], axis, t["pointer"])
                lookups[(role, key)] = {"descriptor_id": descriptor_id, **selection,
                    "rater": {"rater": "invented-" + role, "route": "offline-fixture"},
                    "execution_registration": None}
            if execution_bound:
                run_path = tmp_path / ("run-" + descriptor_id)
                declared = execution_declaration({"url": "http://127.0.0.1:9/v1/messages"}, run_path)
                declared["format"] = execution.FORMAT if axis == "grounding_v3" else execution.FITNESS_FORMAT
                declared["transport"]["model"] = models[role_index]
                n = len(selections)
                declared["limits"].update(max_calls=n, total_response_bytes=n * 50_001,
                    input_scheduling_threshold=n * 100,
                    output_scheduling_threshold=n * caps[role_index])
                path = write(tmp_path / (descriptor_id + "-execution.json"), declared)
                registration = tmp_path / ("registration-" + descriptor_id)
                execution.prepare(directory, path, registration)
                executions[descriptor_id] = (registration, run_path)
                for (found_role, _), slot in lookups.items():
                    if found_role == role and slot["descriptor_id"] == descriptor_id:
                        slot["execution_registration"] = ref(tmp_path, registration, "registration.json")
    keys = sorted(key for role, key in lookups if role == ROLES[0])
    for ordinal, key in enumerate(keys):
        i, axis, pointer = key
        same = lookups[(ROLES[0], key)]
        declaration["pairs"].append({"pair_id": f"pair-{ordinal:03}", "record_id": f"record-{i}",
            "anchor": {k: same[k] for k in ("descriptor_id", "target_id")},
            "selection_stratum": {"status": "pending", "label": None, "reference": None},
            "slots": {role: deepcopy(lookups[(role, key)]) for role in ROLES}})
    if change_declaration:
        change_declaration(declaration)
    path = write(tmp_path / "panel-declaration.json", declaration)
    case = SimpleNamespace(root=tmp_path, source=source, plans=plans, descriptors=descriptors,
        declaration=declaration, declaration_path=path, panel_path=tmp_path / "panel", executions=executions,
        models=dict(zip(ROLES, models)), axes=axes)
    case.panel = panel.prepare_panel(path, case.panel_path, root=tmp_path) if prepare else None
    return case


def make_results(case, *, values=None, omitted=(), rejected=(), name="results", entries=None):
    """Every supplied saved result is produced by the unchanged strict acceptor."""
    submissions = {"format": "cross_family_judge_submissions_v1",
                   "panel_sha256": sha256((case.panel_path / "panel.json").read_bytes()), "slots": []}
    saved_results, raws = {}, {}
    if entries is None:
        for pair in case.panel["pairs"]:
            for role in ROLES:
                key = (pair["pair_id"], role)
                declared_pair = next(p for p in case.declaration["pairs"] if p["pair_id"] == pair["pair_id"])
                slot = declared_pair["slots"][role]
                if slot is None or key in omitted:
                    continue
                directory, _, api = case.descriptors[slot["descriptor_id"]]
                value = values(pair, role) if values else None
                raw = native(pair["axis"], case.models[role], value, rejected=key in rejected)
                response = case.root / (name + "-" + pair["pair_id"] + "-" + role + ".json")
                response.write_bytes(api.package_response((directory / "descriptor.json").read_bytes(),
                    attempt_id=slot["attempt_id"], native_message=raw))
                output = case.root / (name + "-saved-" + pair["pair_id"] + "-" + role)
                result = api.accept(directory, response, output, attempt_id=slot["attempt_id"])
                saved_results[key], raws[key] = (output, result), raw
                submissions["slots"].append({"pair_id": pair["pair_id"], "role": role,
                    "saved_result": ref(case.root, output, "result.json"), "execution": None})
    else:
        submissions["slots"] = entries
    path = write(case.root / (name + "-submissions.json"), submissions)
    output = case.root / name
    report = panel.accept_panel_results(case.panel_path, path, output, root=case.root)
    return SimpleNamespace(path=output, report=report, submissions=submissions,
                           submissions_path=path, saved=saved_results, raws=raws)


def test_real_both_axis_packages_omit_opposite_spec_and_relocate(fixture, tmp_path, monkeypatch):
    case = make_case(fixture, tmp_path)
    before = snapshot(case.source)
    assert set(case.panel) == PANEL_KEYS
    for descriptor_id, (directory, document, _) in case.descriptors.items():
        manifest = json.loads((directory / "artifacts" / document["plan"]["sha256"]).read_bytes())
        opposite = "fitness_specifications" if descriptor_id.endswith("grounding_v3") else "nested_specification"
        assert not (directory / "artifacts" / manifest["schema"][opposite]["sha256"]).exists()
    result = make_results(case)
    assert set(result.report) == RESULT_KEYS
    assert len(result.report["slots"]) == 8
    assert {s["slot_state"] for s in result.report["slots"]} == {"accepted"}
    for pair in result.report["pairs"]:
        schema = pair["common_subject"]["schema"]
        if pair["axis"] == "grounding_v3":
            assert schema["nested_specification"] and schema["nested_specification_sha256"]
            assert schema["fitness_specifications"] is None and schema["generation_digest"] is None
        else:
            assert schema["fitness_specifications"] and schema["generation_digest"]
            assert schema["nested_specification"] is None and schema["nested_specification_sha256"] is None
    assert before == snapshot(case.source)
    moved = tmp_path / "portable-results"
    shutil.copytree(result.path, moved)
    for path in [case.source, case.panel_path, result.path, *[p for p, _ in case.plans],
                 *[d for d, _, _ in case.descriptors.values()], *[p for p, _ in result.saved.values()]]:
        path.rename(path.with_name(path.name + "-unavailable"))
    original = Path.read_bytes
    def only_capture(path):
        assert path.is_relative_to(moved), path
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", only_capture)
    assert panel.recheck_panel_results(moved) == result.report
    assert result.report["scientific_eligibility"] is False
    assert result.report["execution_authorized"] is False


def test_missing_rejected_unregistered_and_false_zero_subjects_are_distinct(fixture, tmp_path):
    def pending(d):
        d["pairs"][0]["slots"]["cross_family"] = None
    case = make_case(fixture, tmp_path, change_declaration=pending)
    ids = [p["pair_id"] for p in case.panel["pairs"]]
    result = make_results(case, omitted={(ids[1], "same_family")}, rejected={(ids[2], "cross_family")})
    states = {(s["pair_id"], s["role"]): s for s in result.report["slots"]}
    assert states[ids[0], "cross_family"]["slot_state"] == "unregistered"
    assert states[ids[1], "same_family"]["slot_state"] == "missing"
    assert states[ids[2], "cross_family"]["slot_state"] == "rejected"
    assert states[ids[2], "cross_family"]["assessment_state"] == "rejected"
    assert len(states) == 8 and len(result.report["pairs"]) == 4
    assert {p["pointer"] for p in result.report["pairs"]} == {"/count", "/enabled"}
    assert len({p["common_subject"]["value_sha256"] for p in result.report["pairs"]}) == 2
    assert all(s["dispatch_state"] == "unknown" and s["spent"] is None
               for s in states.values() if s["slot_state"] == "accepted")


def test_both_pending_slots_still_require_and_preserve_real_anchor(fixture, tmp_path):
    def pending(d):
        for p in d["pairs"]:
            p["slots"] = dict.fromkeys(ROLES)
        d["descriptors"] = [v for v in d["descriptors"] if v["descriptor_id"].startswith("same_family-")]
    case = make_case(fixture, tmp_path, change_declaration=pending)
    result = make_results(case)
    assert len(result.report["pairs"]) == 4 and len(result.report["slots"]) == 8
    assert all(p["common_subject_sha256"] and p["common_subject"]["record"] for p in result.report["pairs"])
    assert {s["slot_state"] for s in result.report["slots"]} == {"unregistered"}
    broken = deepcopy(case.declaration)
    broken["pairs"][0]["anchor"]["target_id"] = "invented-target"
    with pytest.raises(ValueError):
        panel.prepare_panel(write(tmp_path / "broken.json", broken), tmp_path / "broken", root=tmp_path)


@pytest.mark.parametrize("seam", ["subject_alias", "attempt_descriptor_alias", "extra_key", "outside_root"])
def test_closed_registration_and_real_identity_refuse_aliases(fixture, tmp_path, seam):
    case = make_case(fixture, tmp_path, prepare=False)
    d = case.declaration
    if seam == "subject_alias":
        duplicate = deepcopy(d["pairs"][0]); duplicate["pair_id"] = "another-pair"
        d["pairs"].append(duplicate)
    elif seam == "attempt_descriptor_alias":
        original = d["descriptors"][0]
        duplicate = deepcopy(original); duplicate["descriptor_id"] = "descriptor-alias"
        d["descriptors"].append(duplicate)
        slot = deepcopy(d["pairs"][0]["slots"]["same_family"])
        slot["descriptor_id"] = "descriptor-alias"
        d["pairs"][0]["slots"]["cross_family"] = slot
    elif seam == "extra_key":
        d["pairs"][0]["slots"]["same_family"]["family"] = "claimed-family"
    else:
        d["descriptors"][0]["source"]["path"] = "../outside"
    with pytest.raises(ValueError):
        panel.prepare_panel(write(case.declaration_path, d), case.panel_path, root=tmp_path)
    assert not case.panel_path.exists()


@pytest.mark.parametrize("seam", ["record", "bundle", "schema"])
def test_independently_valid_descriptors_cannot_hide_exposure_changes(fixture, tmp_path, seam):
    def change(source):
        if seam == "record":
            path = source / "record-0.yaml"
            value = yaml.safe_load(path.read_text()); value["count"] = 1
            path.write_text(yaml.safe_dump(value))
            roster = json.loads((source / "roster.json").read_bytes())
            roster["pinned_files"][path.name] = sha256(path.read_bytes())
            write(source / "roster.json", roster)
        elif seam == "bundle":
            raw = b"FILE: other.txt\nA different captured source.\n"
            (source / "bundle.txt").write_bytes(raw)
            path = source / "provenance-0.yaml"
            p = yaml.safe_load(path.read_text()); p["inputs"]["bundle_md5"] = hashlib.md5(raw).hexdigest()
            path.write_text(yaml.safe_dump(p))
        else:
            path = source / "schema.yaml"
            value = yaml.safe_load(path.read_text()); value["slots"]["count"]["description"] = "A changed constraint description."
            path.write_text(yaml.safe_dump(value))
    case = make_case(fixture, tmp_path, before_second=change, prepare=False)
    for directory, expected, api in case.descriptors.values():
        assert api._load_descriptor(support.Capture(directory), (directory / "descriptor.json").read_bytes()) == expected
    visible_differences = []
    for axis in AXES:
        left_dir, left, _ = case.descriptors["same_family-" + axis]
        right_dir, right, _ = case.descriptors["cross_family-" + axis]
        for a, b in zip(left["selections"], right["selections"]):
            qa = json.loads((left_dir / "artifacts" / a["binding"]["request"]["sha256"]).read_bytes())
            qb = json.loads((right_dir / "artifacts" / b["binding"]["request"]["sha256"]).read_bytes())
            for allowed in ("model", "max_tokens"):
                qa.pop(allowed); qb.pop(allowed)
            visible_differences.append(canonical(qa) != canonical(qb))
    assert any(visible_differences), "this negative must actually change a model-visible request"
    with pytest.raises(ValueError):
        panel.prepare_panel(case.declaration_path, case.panel_path, root=tmp_path)
    assert not case.panel_path.exists()


def test_relocated_schema_source_locators_are_not_new_exposure(fixture, tmp_path):
    def relocate(source):
        moved = tmp_path / "same-source-at-new-location"
        shutil.copytree(source, moved)
        return moved
    # Support uses its verified nested specification; the unneeded fitness
    # generation digest is deliberately outside this axis's common identity.
    case = make_case(fixture, tmp_path, axes=("grounding_v3",), before_second=relocate)
    left, right = [m for _, m in case.plans]
    assert [v["path"] for v in left["schema"]["sources"]] != [v["path"] for v in right["schema"]["sources"]]
    assert left["schema"]["nested_specification"] == right["schema"]["nested_specification"]
    assert len(case.panel["pairs"]) == 2
    assert all(p["compatible_pair"] for p in case.panel["pairs"])
    assert all(p["accepted_pair"] for p in make_results(case).report["pairs"])


def test_reordering_and_returned_object_mutation_do_not_change_captured_identity(fixture, tmp_path):
    case = make_case(fixture, tmp_path)
    expected = deepcopy(case.panel)
    case.panel["pairs"][0]["common_subject"]["pointer"] = "/invented"
    assert panel.recheck_panel(case.panel_path) == expected
    d = deepcopy(case.declaration); d["pairs"].reverse(); d["descriptors"].reverse()
    reordered = panel.prepare_panel(write(tmp_path / "reordered.json", d), tmp_path / "reordered", root=tmp_path)
    assert reordered["pairs"] == expected["pairs"]
    assert reordered["slots"] == expected["slots"]
    assert reordered["records"] == expected["records"]


@pytest.mark.parametrize("seam", ["assessment", "artifact", "foreign_pair", "duplicate_submission"])
def test_results_recheck_refuses_tampering_instead_of_reclassifying_missing(fixture, tmp_path, seam):
    case = make_case(fixture, tmp_path)
    result = make_results(case)
    submissions = deepcopy(result.submissions)
    if seam == "assessment":
        path, doc = next(iter(result.saved.values()))
        altered = deepcopy(doc); altered["assessment"]["status"] = "rejected"
        write(path / "result.json", altered)
        submissions["slots"][0]["saved_result"] = ref(tmp_path, path, "result.json")
    elif seam == "artifact":
        path, doc = next(iter(result.saved.values()))
        (path / "artifacts" / doc["response"]["sha256"]).write_bytes(b"changed")
    elif seam == "foreign_pair":
        submissions["slots"][0]["pair_id"] = "foreign-pair"
    else:
        submissions["slots"].append(deepcopy(submissions["slots"][0]))
    with pytest.raises(ValueError):
        panel.accept_panel_results(case.panel_path, write(tmp_path / "tampered.json", submissions),
                                   tmp_path / "tampered", root=tmp_path)
    assert not (tmp_path / "tampered").exists()


@pytest.mark.parametrize("axis", AXES, ids=["support", "fitness"])
@pytest.mark.parametrize("outcome", ["accepted", "http_failure", "admission_interruption"])
def test_real_execution_precedence_and_spent_state(fixture, tmp_path, monkeypatch, axis, outcome):
    case = make_case(fixture, tmp_path, axes=(axis,), pointers=("/count",), execution_bound=True)
    entries = []
    for role in ROLES:
        descriptor_id = role + "-" + axis
        registration, run_path = case.executions[descriptor_id]
        def dispatch(*args, **kwargs):
            if outcome == "admission_interruption":
                raise OSError("invented interruption after durable admission")
            return {"status_code": 429 if outcome == "http_failure" else 200,
                    "request_id": "invented", "body_complete": True, "failure": None,
                    "duration_seconds": 0, "stage": "complete"}, native(axis, case.models[role])
        monkeypatch.setattr(execution, "_dispatch", dispatch)
        if outcome == "admission_interruption":
            with pytest.raises(OSError, match="invented interruption"):
                execution.run(registration)
        else:
            execution.run(registration)
        entries.append({"pair_id": case.panel["pairs"][0]["pair_id"], "role": role,
            "saved_result": None, "execution": {"path": run_path.relative_to(tmp_path).as_posix(),
                "registration_sha256": sha256((registration / "registration.json").read_bytes())}})
    monkeypatch.setattr(execution, "_dispatch", lambda *a, **k: pytest.fail("offline acceptance dispatched"))
    result = make_results(case, entries=entries)
    expected = {"accepted": ("accepted", "accepted"), "http_failure": ("rejected", "failed"),
                "admission_interruption": ("missing", "spent_unknown")}[outcome]
    for slot in result.report["slots"]:
        assert (slot["slot_state"], slot["dispatch_state"]) == expected
        assert slot["spent"] is True and slot["evidence_basis"] == "captured_execution"
        if outcome != "admission_interruption":
            assert slot["assessment_state"] == "accepted"
    assert panel.recheck_panel_results(result.path) == result.report


@pytest.mark.parametrize("same_reply", [True, False], ids=["matching-reply-stays-failed", "different-reply-refuses"])
def test_saved_reply_must_match_failed_execution_and_cannot_replace_it(fixture, tmp_path, monkeypatch, same_reply):
    case = make_case(fixture, tmp_path, axes=("fitness",), pointers=("/count",), execution_bound=True)
    registrations = case.executions
    for role in ROLES:
        registration, _ = registrations[role + "-fitness"]
        monkeypatch.setattr(execution, "_dispatch", lambda *a, _role=role, **k: (
            {"status_code": 429, "request_id": "invented", "body_complete": True,
             "failure": None, "duration_seconds": 0, "stage": "complete"},
            native("fitness", case.models[_role], {"fitness": 0.25})))
        execution.run(registration)
    # Capture a different, independently accepted saved reply without using the panel acceptor.
    entries = []
    for role in ROLES:
        slot = case.declaration["pairs"][0]["slots"][role]
        directory, _, api = case.descriptors[slot["descriptor_id"]]
        response = tmp_path / (role + "-different.json")
        response.write_bytes(api.package_response((directory / "descriptor.json").read_bytes(),
            attempt_id=slot["attempt_id"], native_message=native("fitness", case.models[role], {"fitness": 0.25 if same_reply else 0.9})))
        saved_path = tmp_path / (role + "-different")
        assert api.accept(directory, response, saved_path, attempt_id=slot["attempt_id"])["assessment"]["status"] == "accepted"
        registration, run_path = registrations[role + "-fitness"]
        entries.append({"pair_id": case.panel["pairs"][0]["pair_id"], "role": role,
            "saved_result": ref(tmp_path, saved_path, "result.json"),
            "execution": {"path": run_path.relative_to(tmp_path).as_posix(),
                          "registration_sha256": sha256((registration / "registration.json").read_bytes())}})
    if same_reply:
        result = make_results(case, entries=entries)
        assert {s["slot_state"] for s in result.report["slots"]} == {"rejected"}
        assert {s["assessment_state"] for s in result.report["slots"]} == {"accepted"}
        assert {s["dispatch_state"] for s in result.report["slots"]} == {"failed"}
    else:
        with pytest.raises(ValueError):
            make_results(case, entries=entries)
        assert not (tmp_path / "results").exists()


def test_registered_execution_cannot_downgrade_to_saved_capture(fixture, tmp_path):
    case = make_case(fixture, tmp_path, axes=("fitness",), pointers=("/count",), execution_bound=True)
    result = make_results(case)
    assert {s["evidence_basis"] for s in result.report["slots"]} == {"captured_execution"}
    assert {s["slot_state"] for s in result.report["slots"]} == {"missing"}
    assert {s["assessment_state"] for s in result.report["slots"]} == {"accepted"}
    assert not result.report["pairs"][0]["accepted_pair"]


@pytest.mark.parametrize("winner", ["empty", "nonempty"])
def test_atomic_registration_refuses_racing_output_without_overwrite(fixture, tmp_path, monkeypatch, winner):
    case = make_case(fixture, tmp_path, prepare=False)
    before = snapshot(case.source)
    original = kernel._rename_new
    def race(source, destination):
        destination.mkdir()
        if winner == "nonempty":
            (destination / "sentinel").write_bytes(b"other writer")
        return original(source, destination)
    monkeypatch.setattr(kernel, "_rename_new", race)
    with pytest.raises((ValueError, OSError)):
        panel.prepare_panel(case.declaration_path, case.panel_path, root=tmp_path)
    assert snapshot(case.panel_path) == ({} if winner == "empty" else {"sentinel": b"other writer"})
    assert before == snapshot(case.source)


def test_mid_artifact_failure_never_publishes_partial_panel(fixture, tmp_path, monkeypatch):
    case = make_case(fixture, tmp_path, prepare=False)
    before = snapshot(tmp_path)
    original, calls = kernel._write_bytes, []
    def fail(path, raw):
        calls.append(path)
        if len(calls) == 2:
            raise OSError("invented mid-artifact write failure")
        return original(path, raw)
    monkeypatch.setattr(kernel, "_write_bytes", fail)
    with pytest.raises(OSError, match="mid-artifact"):
        panel.prepare_panel(case.declaration_path, case.panel_path, root=tmp_path)
    assert len(calls) == 2 and not case.panel_path.exists()
    assert before == snapshot(tmp_path)


def test_public_nul_and_existing_output_refuse_before_writes(fixture, tmp_path):
    case = make_case(fixture, tmp_path)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError):
        panel.prepare_panel(case.declaration_path, tmp_path / "truncated\0suffix", root=tmp_path)
    with pytest.raises((ValueError, OSError)):
        panel.prepare_panel(case.declaration_path, case.panel_path, root=tmp_path)
    assert before == snapshot(tmp_path)
    assert not (tmp_path / "truncated").exists()


def test_real_offline_cli_prepare_accept_and_recheck(fixture, tmp_path):
    case = make_case(fixture, tmp_path, prepare=False)
    runner = CliRunner()
    result = runner.invoke(evaluate, ["cross-family-judges", "prepare", "--declaration",
        str(case.declaration_path), "--output", str(case.panel_path), "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    case.panel = json.loads(result.output)
    checked = runner.invoke(evaluate, ["cross-family-judges", "recheck", "--panel", str(case.panel_path)])
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.output) == case.panel
    captured = make_results(case)
    accepted_path = tmp_path / "cli-results"
    accepted = runner.invoke(evaluate, ["cross-family-judges", "accept-results", "--panel", str(case.panel_path),
        "--submissions", str(captured.submissions_path), "--output", str(accepted_path), "--root", str(tmp_path)])
    assert accepted.exit_code == 0, accepted.output
    assert json.loads(accepted.output) == captured.report
    result = runner.invoke(evaluate, ["cross-family-judges", "recheck-results", "--results", str(accepted_path)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == captured.report


def test_failed_first_execution_preserves_registered_not_started_partner(fixture, tmp_path, monkeypatch):
    case = make_case(fixture, tmp_path, axes=("fitness",), execution_bound=True)
    entries = []
    for role in ROLES:
        registration, run_path = case.executions[role + "-fitness"]
        calls = []
        def failed(*args, _role=role, **kwargs):
            calls.append(True)
            return {"status_code": 429, "request_id": "invented", "body_complete": True,
                    "failure": None, "duration_seconds": 0, "stage": "complete"}, native("fitness", case.models[_role])
        monkeypatch.setattr(execution, "_dispatch", failed)
        execution.run(registration)
        assert calls == [True]
        for p in case.panel["pairs"]:
            entries.append({"pair_id": p["pair_id"], "role": role, "saved_result": None,
                "execution": {"path": run_path.relative_to(tmp_path).as_posix(),
                              "registration_sha256": sha256((registration / "registration.json").read_bytes())}})
    result = make_results(case, entries=entries)
    for slot in result.report["slots"]:
        if slot["attempt_id"] == "attempt-0":
            assert (slot["slot_state"], slot["dispatch_state"], slot["spent"]) == ("rejected", "failed", True)
            assert slot["assessment_state"] == "accepted"
        else:
            assert (slot["slot_state"], slot["dispatch_state"], slot["spent"]) == ("missing", "not_started", False)
            assert slot["assessment_state"] is None
    assert len(result.report["slots"]) == 4 and not any(p["accepted_pair"] for p in result.report["pairs"])


@pytest.mark.parametrize("changed", ["record", "provenance"])
@pytest.mark.parametrize("axis", AXES, ids=["support", "fitness"])
def test_one_logical_generation_cannot_be_two_conflicting_panel_records(fixture, tmp_path, changed, axis):
    """Each version has compatible genuine rater slots; only the cross-record identity conflicts."""
    case = make_case(fixture, tmp_path, axes=(axis,), pointers=("/count",))
    declared = deepcopy(case.declaration)
    first_record = case.plans[0][1]["records"][0]
    if changed == "record":
        path = case.source / "record-0.yaml"
        record = yaml.safe_load(path.read_text()); record["count"] = 1
        path.write_text(yaml.safe_dump(record), encoding="utf-8")
        roster = json.loads((case.source / "roster.json").read_bytes())
        roster["pinned_files"][path.name] = sha256(path.read_bytes())
        write(case.source / "roster.json", roster)
    else:
        # Valid YAML and the same parsed logical metadata, but distinct captured lineage bytes.
        path = case.source / "provenance-0.yaml"
        path.write_bytes(path.read_bytes() + b"\n# Another captured provenance version.\n")
    slots = {}
    api = support if axis == "grounding_v3" else fitness
    for role in ROLES:
        plan_path = tmp_path / ("second-version-plan-" + role)
        manifest = build((case.source, plan_path), model=case.models[role], max_tokens=417)
        record = manifest["records"][0]
        logical_keys = ("project", "label", "method", "cohort", "generation_rep")
        assert {k: record[k] for k in logical_keys} == {k: first_record[k] for k in logical_keys}
        assert record[changed]["sha256"] != first_record[changed]["sha256"]
        target = next(t for t in manifest["targets"] if t["axis"] == axis and t["pointer"] == "/count")
        directory = tmp_path / ("second-version-descriptor-" + role)
        selected = {"target_id": target["id"], "attempt_id": "second-version-attempt"}
        expected = api.prepare(plan_path, directory, selections=[selected], protocol=api.FORMAT)
        assert api._load_descriptor(support.Capture(directory), (directory / "descriptor.json").read_bytes()) == expected
        did = "second-version-" + role
        declared["descriptors"].append({"descriptor_id": did, "protocol": api.FORMAT,
                                      "source": ref(tmp_path, directory, "descriptor.json")})
        slots[role] = {"descriptor_id": did, **selected,
                       "rater": {"rater": "invented-" + role, "route": "offline-fixture"},
                       "execution_registration": None}
    second_pair = {"pair_id": "second-version-pair", "record_id": "different-caller-record-id",
        "anchor": {k: slots["same_family"][k] for k in ("descriptor_id", "target_id")},
        "selection_stratum": {"status": "pending", "label": None, "reference": None}, "slots": slots}
    # Positive: the second version alone is a genuine internally compatible panel.
    alone = deepcopy(declared)
    alone["descriptors"] = [d for d in alone["descriptors"] if d["descriptor_id"].startswith("second-version-")]
    alone["pairs"] = [deepcopy(second_pair)]
    second = panel.prepare_panel(write(tmp_path / "second-version-alone.json", alone),
                                 tmp_path / "second-version-alone", root=tmp_path)
    assert second["pairs"][0]["compatible_pair"] and len(second["records"]) == 1
    declared["pairs"].append(second_pair)
    path = write(tmp_path / "conflicting-generations.json", declared)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError):
        panel.prepare_panel(path, tmp_path / "conflicting-generations", root=tmp_path)
    assert not (tmp_path / "conflicting-generations").exists()
    assert before == snapshot(tmp_path)


def _one_actual_execution(case, monkeypatch):
    """Run the original finite executor with only its network dispatch replaced."""
    role = "same_family"
    registration, run_path = case.executions[role + "-fitness"]
    def dispatch(*args, **kwargs):
        return {"status_code": 200, "request_id": "invented", "body_complete": True,
                "failure": None, "duration_seconds": 0, "stage": "complete"}, native("fitness", case.models[role])
    monkeypatch.setattr(execution, "_dispatch", dispatch)
    actual = execution.run(registration)
    assert actual["all_selected_accepted"] is True
    monkeypatch.setattr(execution, "_dispatch", lambda *a, **k: pytest.fail("capture unexpectedly dispatched"))
    entry = {"pair_id": case.panel["pairs"][0]["pair_id"], "role": role, "saved_result": None,
        "execution": {"path": run_path.relative_to(case.root).as_posix(),
                      "registration_sha256": sha256((registration / "registration.json").read_bytes())}}
    return run_path, entry


@pytest.mark.parametrize("malformation", ["unexpected_file", "noncontiguous_frontier", "over_count"])
def test_malformed_execution_frontier_refuses_before_unadmitted_payload_read(fixture, tmp_path, monkeypatch, malformation):
    case = make_case(fixture, tmp_path, axes=("fitness",), pointers=("/count",), execution_bound=True)
    run_path, entry = _one_actual_execution(case, monkeypatch)
    attempts = run_path / "attempts"
    if malformation == "unexpected_file":
        forbidden = attempts / "000000" / "unrelated.dat"
        forbidden.write_bytes(b"not an admitted execution artifact")
        forbidden_paths = {forbidden}
    elif malformation == "noncontiguous_frontier":
        (attempts / "000000").rename(attempts / "000001")
        forbidden_paths = {p for p in (attempts / "000001").iterdir() if p.is_file()}
    else:
        # Exercise the old real frontier count gate without allocating a large hostile tree.
        monkeypatch.setattr(execution, "MAX_CALLS", 1)
        extra = attempts / "000001"
        extra.mkdir()
        (extra / "admitted.json").write_bytes(b"not an admitted second call")
        forbidden_paths = {p for d in attempts.iterdir() for p in d.iterdir() if p.is_file()}
    before = snapshot(tmp_path)
    original, acquired = support._file, []
    def observe(path, *args, **kwargs):
        acquired.append(Path(path))
        return original(path, *args, **kwargs)
    monkeypatch.setattr(support, "_file", observe)
    with pytest.raises(ValueError):
        make_results(case, entries=[entry], name="malformed-results")
    # A later shape error is insufficient: these bytes must never be acquired.
    assert forbidden_paths.isdisjoint(acquired), [str(p) for p in acquired if p in forbidden_paths]
    assert not (tmp_path / "malformed-results").exists()
    after = snapshot(tmp_path)
    # The explicit submission is authored by the fixture, outside the operation's output package.
    after.pop("malformed-results-submissions.json")
    assert before == after


def test_execution_source_change_after_valid_capture_still_refuses_publication(fixture, tmp_path, monkeypatch):
    case = make_case(fixture, tmp_path, axes=("fitness",), pointers=("/count",), execution_bound=True)
    run_path, entry = _one_actual_execution(case, monkeypatch)
    admitted = run_path / "attempts" / "000000" / "admitted.json"
    original_bytes = admitted.read_bytes()
    real, captures = execution.capture_run, []
    def capture_then_change(path):
        result = real(path)
        if Path(path) == run_path:
            captures.append(True)
            admitted.write_bytes(original_bytes + b" ")
        return result
    monkeypatch.setattr(execution, "capture_run", capture_then_change)
    try:
        with pytest.raises(ValueError):
            make_results(case, entries=[entry], name="changed-source-results")
        assert captures == [True]
        assert not (tmp_path / "changed-source-results").exists()
    finally:
        admitted.write_bytes(original_bytes)
    assert admitted.read_bytes() == original_bytes


@pytest.mark.parametrize("artifact", ["response_body", "descriptor"])
@pytest.mark.parametrize("change", ["delete", "replace"])
def test_required_execution_artifact_change_after_capture_refuses_publication(fixture, tmp_path, monkeypatch, artifact, change):
    case = make_case(fixture, tmp_path, axes=("fitness",), pointers=("/count",), execution_bound=True)
    run_path, entry = _one_actual_execution(case, monkeypatch)
    actual_capture, observed = execution.capture_run, []
    def capture_then_change(path):
        captured, ledger = actual_capture(path)
        if Path(path) == run_path:
            if artifact == "response_body":
                outcome = json.loads(captured.get(ledger["attempts"][0]["response"]))
                required_pin = outcome["body"]
            else:
                registration = json.loads(captured.get(ledger["registration"]))
                required_pin = registration["descriptor"]
            source = run_path / "artifacts" / required_pin["sha256"]
            original = source.read_bytes()
            assert original == captured.get(required_pin)
            observed.append((source, original))
            if change == "delete":
                source.unlink()
            else:
                source.write_bytes(original + b" ")
        return captured, ledger
    monkeypatch.setattr(execution, "capture_run", capture_then_change)
    try:
        with pytest.raises(ValueError):
            make_results(case, entries=[entry], name="artifact-change-results")
        assert len(observed) == 1
        assert not (tmp_path / "artifact-change-results").exists()
    finally:
        for source, original in observed:
            source.write_bytes(original)
    assert all(source.read_bytes() == original for source, original in observed)


def test_genuine_derived_response_envelope_need_not_exist_as_input_artifact(fixture, tmp_path, monkeypatch):
    case = make_case(fixture, tmp_path, axes=("fitness",), pointers=("/count",), execution_bound=True)
    run_path, entry = _one_actual_execution(case, monkeypatch)
    execution_report = json.loads((run_path / "report.json").read_bytes())
    saved_result = execution_report["rows"][0]["saved_result"]
    envelope_pin = saved_result["response_envelope"]
    registration = json.loads((run_path / "registration.json").read_bytes())
    assert envelope_pin["sha256"] not in {saved_result["response"]["sha256"], registration["descriptor"]["sha256"]}
    envelope_path = run_path / "artifacts" / envelope_pin["sha256"]
    envelope_bytes = envelope_path.read_bytes()
    # It is derived by the unchanged executor from the still-present native body.
    # Removal precedes acquisition; this is not deletion of an observed source.
    envelope_path.unlink()
    before = snapshot(run_path)
    original, observed = execution.capture_run, []
    def capture_and_observe(path):
        captured, ledger = original(path)
        if Path(path) == run_path:
            assert not envelope_path.exists()
            assert captured.get(envelope_pin) == envelope_bytes
            observed.append(True)
        return captured, ledger
    monkeypatch.setattr(execution, "capture_run", capture_and_observe)
    result = make_results(case, entries=[entry], name="computed-envelope-results")
    assert observed == [True]
    selected = next(s for s in result.report["slots"] if s["role"] == "same_family")
    assert (selected["slot_state"], selected["dispatch_state"], selected["spent"]) == ("accepted", "accepted", True)
    assert not envelope_path.exists() and snapshot(run_path) == before
    assert panel.recheck_panel_results(result.path) == result.report


def test_relocated_custom_fitness_context_refuses_even_with_equal_rendered_requests(fixture, tmp_path):
    def relocate(source):
        moved = tmp_path / "same-source-at-new-location"
        shutil.copytree(source, moved)
        return moved
    case = make_case(fixture, tmp_path, axes=("fitness",), before_second=relocate, prepare=False)
    left_manifest, right_manifest = [m for _, m in case.plans]
    assert left_manifest["schema"]["fitness_specifications"] == right_manifest["schema"]["fitness_specifications"]
    assert left_manifest["schema"]["generation_digest"] != right_manifest["schema"]["generation_digest"]
    left_dir, left, left_api = case.descriptors["same_family-fitness"]
    right_dir, right, right_api = case.descriptors["cross_family-fitness"]
    for directory, expected, api in ((left_dir, left, left_api), (right_dir, right, right_api)):
        assert api._load_descriptor(support.Capture(directory), (directory / "descriptor.json").read_bytes()) == expected
    for a, b in zip(left["selections"], right["selections"]):
        first, second = a["binding"], b["binding"]
        assert first["pointer"] == second["pointer"]
        assert first["context"]["schema"] != second["context"]["schema"]
        qa = json.loads((left_dir / "artifacts" / first["request"]["sha256"]).read_bytes())
        qb = json.loads((right_dir / "artifacts" / second["request"]["sha256"]).read_bytes())
        for allowed in ("model", "max_tokens"):
            qa.pop(allowed); qb.pop(allowed)
        assert canonical(qa) == canonical(qb)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match="common subject"):
        panel.prepare_panel(case.declaration_path, case.panel_path, root=tmp_path)
    assert not case.panel_path.exists() and before == snapshot(tmp_path)
