"""Historical artifact admission mutations for #5126; offline fixture bytes only."""
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation import historical_eval_binding as historical
from data_sheets_schema.evaluation import registered_eval_runner as runner
from data_sheets_schema.evaluation.cohort_manifest import read_cohort
from data_sheets_schema.latch_journal import D41_COMMIT
from tests.test_historical_eval_route import historical_inputs
from tests.test_registered_eval_runner import install_cli, no_provider, sha


def binding_document(inputs):
    return json.loads(inputs["registration"].read_bytes())


def write_binding(inputs, document):
    inputs["registration"].write_bytes(runner.shared.canonical(document))
    return {**inputs, "registration_sha256": sha(inputs["registration"].read_bytes())}


def rebind_evidence(inputs, name, raw, *, path=None):
    """Re-pin intentional fixture mutations so the semantic guard is exercised."""
    binding = binding_document(inputs)
    path = Path(path) if path is not None else Path(binding[name]["path"])
    path.write_bytes(raw)
    binding[name] = runner.shared.file_pin(path, raw)
    updates = {name: path, name + "_sha256": sha(raw)} if name in {"record", "provenance"} else {}
    return write_binding({**inputs, **updates}, binding)


def rebind_provenance(inputs, document):
    return rebind_evidence(inputs, "provenance", yaml.safe_dump(document).encode())


def rebind_record(inputs, raw):
    inputs = rebind_evidence(inputs, "record", raw)
    prior = yaml.safe_load(inputs["provenance"].read_bytes())
    prior["validation"]["artifacts"]["full"] = {"path": str(inputs["record"]), "sha256": sha(raw)}
    return rebind_provenance(inputs, prior)


@pytest.mark.parametrize("mutation,reason", [
    ("missing", "condition pointer is missing"),
    ("conflict", "condition evidence conflicts"),
    ("empty", "condition must be"),
    ("nonstring", "condition must be"),
    ("pointer", "unsupported historical condition pointer"),
])
def test_condition_uses_only_the_declared_pointer(historical_inputs, mutation, reason):
    inputs = historical_inputs
    prior = yaml.safe_load(inputs["provenance"].read_bytes())
    if mutation == "pointer":
        binding = binding_document(inputs)
        binding["condition_pointer"] = "/run/condition"
        inputs = write_binding(inputs, binding)
    else:
        spec = prior["prompts"]["request"]["spec"]
        if mutation == "missing":
            prior["run"]["condition"] = spec.pop("condition")
        elif mutation == "conflict":
            prior["run"]["condition"] = "different-condition"
        else:
            spec["condition"] = "" if mutation == "empty" else False
        inputs = rebind_provenance(inputs, prior)
    with pytest.raises(ValueError, match=reason):
        runner.prepare_historical(**inputs)


@pytest.mark.parametrize("authority", [None, {}, {"authority": "not-a-registration"}])
def test_historical_route_never_falls_back_from_shared_generation(historical_inputs, authority):
    prior = yaml.safe_load(historical_inputs["provenance"].read_bytes())
    prior["shared_generation"] = authority
    inputs = rebind_provenance(historical_inputs, prior)
    with pytest.raises(ValueError, match="without shared generation"):
        runner.prepare_historical(**inputs)


def test_post_d41_missing_integrity_refuses_with_positive_commit_evidence(historical_inputs):
    prior = yaml.safe_load(historical_inputs["provenance"].read_bytes())
    prior["repo"] = {"commit": D41_COMMIT}
    inputs = rebind_provenance(historical_inputs, prior)
    with pytest.raises(ValueError, match="post-D41: missing runtime_integrity block"):
        runner.prepare_historical(**inputs)


@pytest.mark.parametrize("recorded_at,expected_age", [
    (None, "age unestablished"), ("2026-01-01T00:00:00+00:00", "pre-D41"),
])
def test_pre_d41_and_unknown_age_remain_eligible_without_invented_controls(
        historical_inputs, recorded_at, expected_age):
    prior = yaml.safe_load(historical_inputs["provenance"].read_bytes())
    if recorded_at:
        prior["record_generated_at"] = recorded_at
    inputs = rebind_provenance(historical_inputs, prior)
    prepared = runner.prepare_historical(**inputs)
    assert prepared.generation_record_age == expected_age
    assert prepared.document()["generation_acceptance_verified"] is False
    assert "model" not in yaml.safe_load(inputs["provenance"].read_bytes())


@pytest.mark.parametrize("raw", [b'{"format":', b'{"format":1,"format":2}', b'{"format":NaN}'])
def test_binding_json_refuses_malformed_duplicate_and_nonfinite_values(historical_inputs, raw):
    historical_inputs["registration"].write_bytes(raw)
    inputs = {**historical_inputs, "registration_sha256": sha(raw)}
    with pytest.raises(ValueError):
        runner.prepare_historical(**inputs)


@pytest.mark.parametrize("suffix", [
    b"\nrun: [", b"\nrecord_type: d4d_generation_provenance\n",
    b"\nnonfinite: .nan\n", b"\ncycle: &cycle [*cycle]\n",
])
def test_provenance_yaml_refuses_malformed_duplicate_nonfinite_and_cycles(historical_inputs, suffix):
    raw = historical_inputs["provenance"].read_bytes() + suffix
    inputs = rebind_evidence(historical_inputs, "provenance", raw)
    with pytest.raises(ValueError):
        runner.prepare_historical(**inputs)


@pytest.mark.parametrize("component", ["record", "provenance", "cohort", "decision"])
def test_evidence_bytes_cannot_change_behind_the_binding(historical_inputs, component):
    path = Path(binding_document(historical_inputs)[component]["path"])
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="SHA256 pin differs"):
        runner.prepare_historical(**historical_inputs)


@pytest.mark.parametrize("wrong", ["md5", "sha256"])
def test_all_declared_artifact_hashes_must_agree(historical_inputs, wrong):
    raw = historical_inputs["record"].read_bytes()
    prior = yaml.safe_load(historical_inputs["provenance"].read_bytes())
    artifact = prior["validation"]["artifacts"]["full"]
    artifact.update(md5=hashlib.md5(raw).hexdigest(), sha256=sha(raw))
    artifact[wrong] = "0" * (32 if wrong == "md5" else 64)
    inputs = rebind_provenance(historical_inputs, prior)
    with pytest.raises(ValueError, match="full output hash differs"):
        runner.prepare_historical(**inputs)


@pytest.mark.parametrize("mutation", ["path", "md5", "sha256", "null-path", "null-full", "null-outputs"])
def test_retained_outputs_description_cannot_conflict_with_validated_artifact(historical_inputs, mutation):
    raw = historical_inputs["record"].read_bytes()
    prior = yaml.safe_load(historical_inputs["provenance"].read_bytes())
    output = {"path": str(historical_inputs["record"]),
              "md5": hashlib.md5(raw).hexdigest(), "sha256": sha(raw)}
    prior["outputs"] = {"full": output}
    if mutation == "path":
        copy = historical_inputs["record"].with_name("contradictory-full.yaml")
        copy.write_bytes(raw)
        output["path"] = str(copy)
    elif mutation in {"md5", "sha256"}:
        output[mutation] = "0" * (32 if mutation == "md5" else 64)
    elif mutation == "null-path":
        output["path"] = None
    elif mutation == "null-full":
        prior["outputs"]["full"] = None
    else:
        prior["outputs"] = None
    inputs = rebind_provenance(historical_inputs, prior)
    with pytest.raises(ValueError, match="historical (full output|outputs)"):
        runner.prepare_historical(**inputs)


@pytest.mark.parametrize("claims", ["path", "hash", "both", "description"])
def test_retained_outputs_description_allows_agreeing_or_unknown_claims(historical_inputs, claims):
    raw = historical_inputs["record"].read_bytes()
    prior = yaml.safe_load(historical_inputs["provenance"].read_bytes())
    output = {"description": "Retained source text, not inferred authority"}
    if claims in {"path", "both"}:
        output["path"] = str(historical_inputs["record"])
    if claims in {"hash", "both"}:
        output.update(md5=hashlib.md5(raw).hexdigest(), sha256=sha(raw))
    prior["outputs"] = {"full": output}
    inputs = rebind_provenance(historical_inputs, prior)
    runner.prepare_historical(**inputs)
    assert yaml.safe_load(inputs["provenance"].read_bytes())["outputs"]["full"] == output


@pytest.mark.parametrize("mutation,reason", [
    ("binding-core", "full-artifact binding"),
    ("selected-core", "comparison arm/full role differs"),
    ("provenance-core", "bind its full output"),
    ("validation-false", "validation must explicitly pass"),
])
def test_full_output_and_validation_are_explicit(historical_inputs, mutation, reason):
    inputs = historical_inputs
    if mutation == "binding-core":
        binding = binding_document(inputs)
        binding["record_role"] = "core"
        inputs = write_binding(inputs, binding)
    elif mutation == "selected-core":
        inputs = {**inputs, "record_role": "core"}
    else:
        prior = yaml.safe_load(inputs["provenance"].read_bytes())
        if mutation == "provenance-core":
            artifacts = prior["validation"]["artifacts"]
            artifacts["core"] = artifacts.pop("full")
        else:
            prior["validation"]["passed"] = False
        inputs = rebind_provenance(inputs, prior)
    with pytest.raises(ValueError, match=reason):
        runner.prepare_historical(**inputs)


@pytest.mark.parametrize("bind_copy", [False, True])
def test_same_bytes_at_another_path_do_not_replace_selected_output(historical_inputs, bind_copy):
    copied = historical_inputs["record"].with_name("unselected-copy.yaml")
    copied.write_bytes(historical_inputs["record"].read_bytes())
    inputs = {**historical_inputs, "record": copied}
    reason = "selected paths differ"
    if bind_copy:
        inputs = rebind_evidence(inputs, "record", copied.read_bytes(), path=copied)
        reason = "full output path differs"
    with pytest.raises(ValueError, match=reason):
        runner.prepare_historical(**inputs)


@pytest.mark.parametrize("component", ["record", "provenance", "cohort", "decision"])
def test_historical_authority_aliases_refuse_even_with_matching_bytes(historical_inputs, component):
    binding = binding_document(historical_inputs)
    original = Path(binding[component]["path"])
    alias = original.with_name("alias-" + original.name)
    alias.symlink_to(original)
    binding[component]["path"] = str(alias)
    inputs = write_binding(historical_inputs, binding)
    with pytest.raises(ValueError, match="canonical absolute paths without aliases"):
        runner.prepare_historical(**inputs)


@pytest.mark.parametrize("field,value", [
    ("replicates", [2]), ("condition", "different-condition"),
    ("projects", ["ANOTHER_STUDY"]), ("method", "claudecode_agent"),
])
def test_pinned_cohort_must_contain_the_exact_run(historical_inputs, field, value):
    binding = binding_document(historical_inputs)
    cohort = yaml.safe_load(Path(binding["cohort"]["path"]).read_bytes())
    cohort["cells"][0][field] = value
    inputs = rebind_evidence(historical_inputs, "cohort", yaml.safe_dump(cohort).encode())
    with pytest.raises(ValueError, match="absent or ambiguous"):
        runner.prepare_historical(**inputs)


@pytest.mark.parametrize("digest", [None, "not-a-digest", "0" * 64])
def test_binding_requires_an_independently_supplied_matching_digest(historical_inputs, digest):
    with pytest.raises(ValueError, match="binding SHA256|SHA256 pin differs"):
        runner.prepare_historical(**{**historical_inputs, "registration_sha256": digest})


@pytest.mark.parametrize("component", ["registration", "record", "provenance", "cohort", "decision", "context", "runtime"])
def test_changed_authority_before_execute_refuses_without_calls_or_outputs(
        historical_inputs, component, monkeypatch):
    prepared = runner.prepare_historical(**historical_inputs)
    path = (Path(binding_document(historical_inputs)[component]["path"])
            if component in {"cohort", "decision"} else historical_inputs[component])
    path.write_bytes(path.read_bytes() + b"\n")
    output = historical_inputs["record"].parent / "must-not-exist"
    calls = install_cli(monkeypatch, prepared)
    with pytest.raises(ValueError, match="prepared authority changed|prepared runtime binary changed"):
        runner.execute(prepared, output, plan_sha256=prepared.digest,
                       environ={"CBORG_API_KEY": "synthetic-never-sent"})
    assert calls == [] and not output.exists()
    assert not (Path(runner.LOCK_DIR) / (prepared.digest + ".json")).exists()


def test_d64_declared_data_admits_all_nine_members_and_excludes_historical_ai_readi(historical_inputs):
    """Actual roster data, synthetic output bytes; no retained record is modified."""
    path = Path(__file__).resolve().parents[1] / "configs/evaluation/d64_retained_v8_comparator.yaml"
    rows, pin = read_cohort(path)
    assert len(rows) == 9
    assert {(row["project"], row["replicate"]) for row in rows} == {
        (project, replicate) for project in ("CHORUS", "CM4AI", "VOICE") for replicate in (1, 2, 3)
    }
    assert all(row["project"] != "AI_READI" for row in rows)
    binding = binding_document(historical_inputs)
    binding["cohort"] = pin
    inputs = write_binding(historical_inputs, binding)
    for row in rows:
        prior = yaml.safe_load(inputs["provenance"].read_bytes())
        prior["run"] = {key: row[key] for key in ("project", "label", "method", "replicate")}
        prior["run"]["arm"] = row["input_arm"]
        prior["prompts"]["request"]["spec"]["condition"] = row["condition"]
        inputs = rebind_provenance(inputs, prior)
        admitted = historical.admit(inputs["registration"].read_bytes(),
            lambda selected: Path(selected["path"]).read_bytes(), binding_path=str(inputs["registration"]))
        assert admitted["cohort_entry"] == row
    prior["run"]["project"] = "AI_READI"
    prior["run"]["label"] = next(row["label"] for row in rows if row["project"] == "CM4AI")
    prior["run"]["replicate"] = 1
    inputs = rebind_provenance(inputs, prior)
    with pytest.raises(ValueError, match="absent or ambiguous"):
        historical.admit(inputs["registration"].read_bytes(),
            lambda selected: Path(selected["path"]).read_bytes(), binding_path=str(inputs["registration"]))


def test_retained_d64_records_admit_read_only_under_explicit_pins(historical_inputs):
    """Admission smoke check of retained bytes, without preparing or rating them."""
    root = Path(__file__).resolve().parents[1]
    rows, cohort_pin = read_cohort(root / "configs/evaluation/d64_retained_v8_comparator.yaml")
    binding = binding_document(historical_inputs)
    binding["cohort"] = cohort_pin
    for row in rows:
        record = root / "data/d4d_concatenated" / row["method"] / row["label"] / (row["project"] + "_d4d.yaml")
        provenance = root / "data/d4d_concatenated" / (row["method"] + "_core") / row["label"] / (row["project"] + "_provenance.yaml")
        before = {path: path.read_bytes() for path in (record, provenance)}
        binding["record"] = runner.shared.file_pin(record, before[record])
        binding["provenance"] = runner.shared.file_pin(provenance, before[provenance])
        raw = runner.shared.canonical(binding)
        admitted = historical.admit(raw, lambda pin: runner._read(Path(pin["path"])),
                                    binding_path=str(historical_inputs["registration"]))
        assert admitted["cohort_entry"] == row
        assert before == {path: path.read_bytes() for path in before}
