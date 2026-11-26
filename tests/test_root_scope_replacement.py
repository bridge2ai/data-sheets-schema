"""Offline replacement-attempt controls, 2026-11-26.

Synthetic first scores and refused attempts exercise the real pinned scorer,
strict validator and repeat exporter. No retained live output is opened and no
installed scoring executable is called. The replacement-attempt assignment
permits one separately authorized attempt after a terminal refusal only.
"""
import copy
import json
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from tests.test_root_scope_repeats import repeat_helper, sha, synthetic_run


def normalized_cell(directory, helper, shared=None):
    args, tree, tools, evaluation, _ = synthetic_run(directory, shared=shared, project="CHORUS")
    label = helper.LABEL_PREFIX + "1"
    args.label = label
    args.method_directory = helper.METHOD
    record = tree / "data/d4d_concatenated" / helper.METHOD / label / "CHORUS_d4d.yaml"
    record.parent.mkdir(parents=True)
    Path(args.record).rename(record)
    args.record = record
    scope = tree / "data/evaluation_scope/2026-11-25c" / label / "CHORUS.scope.json"
    scope.parent.mkdir(parents=True)
    shutil.copyfile(args.scope_context, scope)
    args.scope_context = scope
    evaluation.update(label=label, method=helper.METHOD, d4d_file=str(record.relative_to(tree)))
    case_path = tools / "case.json"
    case = json.loads(case_path.read_bytes())
    case["evaluation"] = evaluation
    case_path.write_text(json.dumps(case) + "\n")
    pinned = helper._load_scorer(tree)
    plan = helper.in_checkout(tree, pinned.build_plan, args)
    return args, tree, tools, evaluation, plan


def replacement_fixture(directory, kind="refused"):
    helper = repeat_helper()
    helper._checkout = lambda root: None
    baseline = normalized_cell(directory / "baseline", helper)
    helper.in_checkout(baseline[1], helper._load_scorer(baseline[1]).execute, baseline[4], baseline[0])
    first = normalized_cell(directory / "first", helper, shared=baseline)
    runs = directory / "repeat-runs"
    runs.mkdir()
    label = helper.LABEL_PREFIX + "1"
    base_id = f"scoring_rep3__{label}__CHORUS__rubric10"
    first[0].run_directory = runs / base_id
    first[0].authorization_reference = "synthetic original batch authorization"
    first_plan = helper.in_checkout(first[1], helper._load_scorer(first[1]).build_plan, first[0])
    first = (*first[:4], first_plan)
    case_path = first[2] / "case.json"
    case = json.loads(case_path.read_bytes())
    if kind not in ("never", "running"):
        case["exit"] = 0 if kind == "published" else 7
        case_path.write_text(json.dumps(case) + "\n")
        pinned = helper._load_scorer(first[1])
        if kind == "published":
            helper.in_checkout(first[1], pinned.execute, first_plan, first[0])
        else:
            with pytest.raises(ValueError):
                helper.in_checkout(first[1], pinned.execute, first_plan, first[0])
    elif kind == "running":
        first[0].run_directory.mkdir()
        helper.write_json(first[0].run_directory / "plan.json", first_plan)
        helper.write_json(first[0].run_directory / "receipt.json", {
            "status": "STARTED", "authorization_reference": first[0].authorization_reference,
            "plan_sha256": helper.plan_digest(first_plan),
            "started_utc": "2026-11-26T05:00:00+00:00", "auth_copy_absent": False,
        })
    case["exit"] = 0
    case_path.write_text(json.dumps(case) + "\n")
    publication = directory / "publication"
    publication.mkdir()
    baseline_run = Path(baseline[4]["run_directory"])
    baseline_plan, baseline_receipt = baseline_run / "plan.json", baseline_run / "receipt.json"
    baseline_row = {"plan": baseline[4], "plan_path": str(baseline_plan),
                    "receipt_path": str(baseline_receipt), "plan_sha256": sha(baseline_plan.read_bytes()),
                    "receipt_sha256": sha(baseline_receipt.read_bytes())}
    # Roster enumeration and Git identity are independently exercised by real
    # sixty-plan checks. This small fixture preserves every receipt/input check.
    helper._baseline_runs = lambda directory: {(1, "CHORUS", "rubric10"): baseline_row}
    argv = ["--replacement-attempt", "--generation-replicate", "1", "--scoring-replicate", "3",
            "--project", "CHORUS", "--rubric", "rubric10", "--scoring-root-2", str(baseline[1]),
            "--scoring-root-3", str(first[1]), "--baseline-runs", str(baseline_run.parent),
            "--publication-root", str(publication), "--runs-root", str(runs),
            "--validation-venv", str(first[0].validation_venv), "--auth-file", str(first[0].auth_file),
            "--codex-binary", str(first[0].codex_binary), "--poetry-binary", str(first[0].poetry_binary),
            "--plan"]
    args = helper.parser().parse_args(argv)
    calls = []
    original_load = helper._load_scorer

    def counted_load(root):
        module = original_load(root)
        original_main = module.main

        def counted_main(argv):
            calls.append(list(argv))
            return original_main(argv)

        module.main = counted_main
        return module

    helper._load_scorer = counted_load
    return helper, args, baseline, first, base_id, calls


def authorize(args):
    args.plan, args.execute = False, True
    args.replacement_authorization_reference = "synthetic separate owner replacement authorization"


def retained_bytes(first):
    run = Path(first[4]["run_directory"])
    return {name: (run / name).read_bytes() for name in ("plan.json", "receipt.json")}


def assert_retained(first, before):
    run = Path(first[4]["run_directory"])
    assert {name: (run / name).read_bytes() for name in before} == before


def test_replacement_plan_preserves_both_measurement_bindings_and_is_read_only(tmp_path):
    helper, args, baseline, first, base_id, calls = replacement_fixture(tmp_path)
    before = retained_bytes(first)
    original_open = Path.open
    allowed = {first[0].run_directory / name for name in ("plan.json", "receipt.json")}

    def blinded_open(path, *positional, **keywords):
        if path.is_relative_to(first[0].run_directory) and path not in allowed:
            raise AssertionError("replacement planning opened refused output or transcript evidence")
        return original_open(path, *positional, **keywords)

    with patch.object(Path, "open", blinded_open):
        bundle = helper.build_batch(args)
    assert bundle["mode"] == "REPLACEMENT_PLAN"
    assert bundle["job_count"] == 1
    job = bundle["jobs"][0]
    assert job["attempt"] == 2
    assert job["id"] == base_id + "__attempt2"
    assert Path(job["plan"]["run_directory"]) == args.runs_root / (base_id + "__attempt2")
    assert Path(job["export_directory"]) == args.runs_root / "export-manifests" / (base_id + "__attempt2")
    helper.verify_plan_identity(job["plan"], first[4])
    helper.verify_plan_identity(job["plan"], baseline[4])
    assert job["plan"]["prompt"].encode() == first[4]["prompt"].encode() == baseline[4]["prompt"].encode()
    assert job["plan"]["identity"] == first[4]["identity"] == baseline[4]["identity"]
    assert not Path(job["plan"]["run_directory"]).exists()
    assert not Path(job["export_directory"]).exists()
    assert Path(job["replacement_record"]) == args.runs_root / "replacement-attempts" / (base_id + "__attempt2.json")
    assert not Path(job["replacement_record"]).exists()
    assert not Path(job["destination"]).exists()
    assert calls == []
    assert_retained(first, before)


def test_replacement_refuses_never_run_running_and_published_cells(tmp_path, kind):
    helper, args, _, _, _, calls = replacement_fixture(tmp_path, kind=kind)
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.build_batch(args)
    assert calls == []


test_replacement_refuses_never_run_running_and_published_cells = pytest.mark.parametrize(
    "kind", ("never", "running", "published")
)(test_replacement_refuses_never_run_running_and_published_cells)


def test_replacement_requires_terminal_hash_bound_and_clean_refusal_metadata(tmp_path, defect):
    helper, args, _, first, _, calls = replacement_fixture(tmp_path)
    receipt_path = first[0].run_directory / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    if defect == "missing_finish":
        receipt.pop("finished_utc")
    elif defect == "auth_cleanup_false":
        receipt["auth_copy_absent"] = False
    elif defect == "auth_copy_present":
        (first[0].run_directory / "codex-home/auth.json").write_text("synthetic retained credential copy\n")
    else:
        receipt["plan_sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt) + "\n")
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.build_batch(args)
    assert calls == []


test_replacement_requires_terminal_hash_bound_and_clean_refusal_metadata = pytest.mark.parametrize(
    "defect", ("missing_finish", "auth_cleanup_false", "auth_copy_present", "plan_binding")
)(test_replacement_requires_terminal_hash_bound_and_clean_refusal_metadata)


def test_replacement_refuses_a_copied_refusal_under_another_run_root(tmp_path):
    helper, args, _, first, base_id, calls = replacement_fixture(tmp_path)
    before = retained_bytes(first)
    another = tmp_path / "copied-refusal-root"
    another.mkdir()
    copied = another / base_id
    copied.mkdir()
    for name, raw in before.items():
        (copied / name).write_bytes(raw)
    args.runs_root = another
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.build_batch(args)
    assert calls == []
    assert_retained(first, before)


def test_replacement_requires_all_four_explicit_cell_coordinates(tmp_path, field):
    helper, args, _, _, _, calls = replacement_fixture(tmp_path)
    setattr(args, field, None)
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.build_batch(args)
    assert calls == []


test_replacement_requires_all_four_explicit_cell_coordinates = pytest.mark.parametrize(
    "field", ("generation_replicate", "scoring_replicate", "project", "rubric")
)(test_replacement_requires_all_four_explicit_cell_coordinates)


def test_replacement_refuses_existing_export_destination_and_second_attempt_paths(tmp_path, occupied):
    helper, args, _, first, base_id, calls = replacement_fixture(tmp_path)
    before = retained_bytes(first)
    bundle = helper.build_batch(args)
    job = bundle["jobs"][0]
    paths = {"destination": Path(job["destination"]),
             "first_manifest": args.runs_root / "export-manifests" / base_id / "manifest.json",
             "replacement_claim": Path(job["replacement_record"]),
             "second_run": Path(job["plan"]["run_directory"]),
             "second_export": Path(job["export_directory"])}
    target = paths[occupied]
    if occupied in ("second_run", "second_export"):
        target.mkdir(parents=True)
        (target / "retained-marker.txt").write_text("prior attempt remains evidence\n")
    else:
        target.parent.mkdir(parents=True)
        target.write_text("already occupied; never overwrite\n")
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.build_batch(args)
    assert target.exists()
    assert calls == []
    assert_retained(first, before)


test_replacement_refuses_existing_export_destination_and_second_attempt_paths = pytest.mark.parametrize(
    "occupied", ("destination", "first_manifest", "replacement_claim", "second_run", "second_export")
)(test_replacement_refuses_existing_export_destination_and_second_attempt_paths)


def test_replacement_requires_its_own_authorization_before_any_call(tmp_path, authorization):
    helper, args, _, first, _, calls = replacement_fixture(tmp_path)
    bundle = helper.build_batch(args)
    authorize(args)
    args.replacement_authorization_reference = authorization
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.execute_batch(bundle, args)
    assert calls == []
    assert not Path(bundle["jobs"][0]["plan"]["run_directory"]).exists()
    assert json.loads((first[0].run_directory / "receipt.json").read_bytes())["status"] == "REFUSED"


test_replacement_requires_its_own_authorization_before_any_call = pytest.mark.parametrize(
    "authorization", (None, "", "   ", "synthetic original batch authorization")
)(test_replacement_requires_its_own_authorization_before_any_call)


def test_replacement_rejects_batch_authorization_and_canary_options(tmp_path, field):
    helper, args, _, _, _, calls = replacement_fixture(tmp_path)
    setattr(args, field, "synthetic batch value")
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.build_batch(args)
    assert calls == []


test_replacement_rejects_batch_authorization_and_canary_options = pytest.mark.parametrize(
    "field", ("authorization_reference", "accepted_canary")
)(test_replacement_rejects_batch_authorization_and_canary_options)


def test_replacement_refuses_a_coordinated_record_and_scope_change(tmp_path):
    helper, args, _, first, _, calls = replacement_fixture(tmp_path)
    before = retained_bytes(first)
    record = Path(first[0].record)
    record.write_bytes(record.read_bytes() + b"description: synthetic measured input changed\n")
    scope = first[0].scope_context
    value = json.loads(scope.read_bytes())
    value["input_sha256"] = sha(record.read_bytes())
    scope.write_text(json.dumps(value) + "\n")
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.build_batch(args)
    assert calls == []
    assert_retained(first, before)


def test_replacement_rechecks_the_first_refusal_before_execution(tmp_path):
    helper, args, _, first, _, calls = replacement_fixture(tmp_path)
    bundle = helper.build_batch(args)
    receipt = first[0].run_directory / "receipt.json"
    receipt.write_bytes(receipt.read_bytes() + b"\n")
    authorize(args)
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.execute_batch(bundle, args)
    assert calls == []
    assert not Path(bundle["jobs"][0]["plan"]["run_directory"]).exists()


def test_replacement_execution_rejects_a_multi_job_or_wrong_mode_bundle(tmp_path):
    helper, args, _, first, _, calls = replacement_fixture(tmp_path)
    bundle = helper.build_batch(args)
    before = retained_bytes(first)
    authorize(args)
    for defect in ("two_jobs", "wrong_plan_mode", "replacement_mode_disabled"):
        candidate, trial_args = copy.deepcopy(bundle), copy.copy(args)
        if defect == "two_jobs":
            candidate["jobs"].append(copy.deepcopy(candidate["jobs"][0]))
            candidate["job_count"] = 2
        elif defect == "wrong_plan_mode":
            candidate["mode"] = "REPEAT_PLAN"
        else:
            trial_args.replacement_attempt = False
            trial_args.replacement_authorization_reference = None
            trial_args.authorization_reference = "synthetic ordinary batch authorization"
        with pytest.raises((OSError, ValueError, RuntimeError)):
            helper.execute_batch(candidate, trial_args)
        assert calls == []
        assert not Path(bundle["jobs"][0]["plan"]["run_directory"]).exists()
        assert not Path(bundle["jobs"][0]["replacement_record"]).exists()
        assert_retained(first, before)


def test_replacement_manifest_labels_attempt_two_and_binds_the_first_refusal(tmp_path):
    helper, args, baseline, first, base_id, calls = replacement_fixture(tmp_path)
    before = retained_bytes(first)
    baseline_bytes = Path(baseline[4]["output"]).read_bytes()
    bundle = helper.build_batch(args)
    job = bundle["jobs"][0]
    authorize(args)
    result = helper.execute_batch(bundle, args)
    assert result["job_count"] == 1
    assert len(calls) == 1
    manifest = json.loads(Path(job["manifest_path"]).read_bytes())
    assert manifest["status"] == "EXPORTED_VALIDATED_REPEAT"
    assert manifest["attempt"] == 2
    assert manifest["refused_attempt_receipt"] == {
        "path": str(first[0].run_directory / "receipt.json"), "sha256": sha(before["receipt.json"])}
    assert manifest["refused_attempt_plan"] == {
        "path": str(first[0].run_directory / "plan.json"), "sha256": sha(before["plan.json"])}
    assert Path(job["destination"]) == helper._destination(args.publication_root, 3, job["plan"]["identity"])
    assert Path(job["destination"]).read_bytes() == Path(job["plan"]["output"]).read_bytes()
    actual_receipt = json.loads((Path(job["plan"]["run_directory"]) / "receipt.json").read_bytes())
    assert actual_receipt["authorization_reference"] == args.replacement_authorization_reference
    assert actual_receipt["status"] == "VALIDATED_AND_PUBLISHED"
    assert Path(job["replacement_record"]).is_file()
    assert_retained(first, before)
    assert Path(baseline[4]["output"]).read_bytes() == baseline_bytes
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.build_batch(args)
    assert len(calls) == 1


def test_second_refusal_leaves_cell_unpublished_and_forbids_another_replacement(tmp_path):
    helper, args, _, first, _, calls = replacement_fixture(tmp_path)
    before = retained_bytes(first)
    bundle = helper.build_batch(args)
    job = bundle["jobs"][0]
    case_path = first[2] / "case.json"
    case = json.loads(case_path.read_bytes())
    case["exit"] = 9
    case_path.write_text(json.dumps(case) + "\n")
    authorize(args)
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.execute_batch(bundle, args)
    assert len(calls) == 1
    second = Path(job["plan"]["run_directory"])
    second_receipt = json.loads((second / "receipt.json").read_bytes())
    assert second_receipt["status"] == "REFUSED"
    assert second_receipt["codex_exit"] == 9
    assert second_receipt["auth_copy_absent"] is True
    assert Path(job["replacement_record"]).is_file()
    assert not Path(job["destination"]).exists()
    assert not Path(job["plan"]["output"]).exists()
    assert not Path(job["manifest_path"]).exists()
    assert_retained(first, before)
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.build_batch(args)
    new_root = tmp_path / "another-root"
    new_root.mkdir()
    args.runs_root = new_root
    with pytest.raises((OSError, ValueError, RuntimeError)):
        helper.build_batch(args)
    assert len(calls) == 1

