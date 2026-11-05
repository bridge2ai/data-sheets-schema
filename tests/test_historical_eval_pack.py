"""Explicit historical campaign pack admission and preservation for #5126."""
from dataclasses import replace
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation import blind_review_pack as pack
from data_sheets_schema.evaluation import registered_eval_runner as runner
from data_sheets_schema.evaluation.cohort_manifest import read_cohort
from tests.test_historical_eval_admission import (
    binding_document, rebind_provenance, rebind_record,
)
from tests.test_historical_eval_route import historical_inputs
from tests.test_registered_eval_runner import no_provider, sha


def pack_arguments(inputs):
    binding = binding_document(inputs)
    cohort = Path(binding["cohort"]["path"])
    rows, _ = read_cohort(cohort)
    row = rows[0]
    root = inputs["record"].parent
    record = pack.Record(row["arm"], row["project"], row["label"], inputs["record"],
                         inputs["record_sha256"], row["input_arm"])
    return dict(records=[record], output_dir=root / "review",
                key_output=root / "review-key.json", seed="0123456789abcdef" * 4,
                cohort="campaign", cohort_manifest=cohort,
                historical_bindings=[(inputs["registration"], inputs["registration_sha256"])],
                historical_decisions=[Path(binding["decision"]["path"])])


def assert_unpublished(arguments):
    assert not arguments["output_dir"].exists()
    assert not arguments["key_output"].exists()


def cli_parsed_selection(arguments, route):
    """Use the real CLI readers, which do not accept an input_arm field."""
    selected = arguments["records"][0]
    if route == "record":
        parsed = [pack.parse_record(
            f"{selected.arm}:{selected.project}:{selected.label}={selected.source_path}")]
    else:
        manifest = selected.source_path.with_name("cli-selection.json")
        manifest.write_text(json.dumps({"records": [{
            "arm": selected.arm, "project": selected.project, "label": selected.label,
            "source_path": str(selected.source_path), "source_sha256": selected.source_sha256,
        }]}))
        parsed = pack.read_manifest(manifest)
    assert len(parsed) == 1 and parsed[0].input_arm is None
    return parsed


@pytest.mark.parametrize("route", ["record", "manifest"])
@pytest.mark.parametrize("envelope", ["root", "wrapper"])
def test_cli_selection_uses_admitted_input_arm_and_preserves_scientific_baseline(
        historical_inputs, route, envelope):
    scientific = {"id": "example:baseline-measurement", "name": "Fictional scientific dataset",
                  "description": "The baseline assessment precedes the follow-up assessment.",
                  "consented": False, "ordered_values": [None, False, "005", "baseline"]}
    source = {**scientific, "arm": "baseline"}
    if envelope == "wrapper":
        source = {"Dataset": source}
    raw = b"# Arm: baseline\n" + yaml.safe_dump(source, sort_keys=False).encode()
    inputs = rebind_record(historical_inputs, raw)
    arguments = pack_arguments(inputs)
    arguments["records"] = cli_parsed_selection(arguments, route)
    key = pack.build_blind_review_pack(**arguments)
    saved = (arguments["output_dir"] / "blind_01.yaml").read_bytes()
    assert saved and sha(saved) == key["records"][0]["blinded_sha256"]
    doc = yaml.safe_load(saved)
    assert "arm" not in doc
    assert doc.get("Dataset", doc) == scientific
    assert inputs["record"].read_bytes() == raw
    assert json.loads(arguments["key_output"].read_bytes()) == key
    assert key["historical_bindings"][0]["identity"]["normalized_run"]["arm"] == "baseline"


@pytest.mark.parametrize("route", ["record", "manifest"])
def test_cli_selection_still_refuses_conflicting_root_arm(historical_inputs, route):
    inputs = rebind_record(historical_inputs,
        b"id: example:record\nname: Scientific dataset\narm: conflicting-input-arm\n")
    arguments = pack_arguments(inputs)
    arguments["records"] = cli_parsed_selection(arguments, route)
    with pytest.raises(ValueError, match="ambiguous root arm"):
        pack.build_blind_review_pack(**arguments)
    assert_unpublished(arguments)


def test_supplied_input_arm_cannot_override_admitted_historical_run(historical_inputs):
    arguments = pack_arguments(historical_inputs)
    arguments["records"] = [replace(arguments["records"][0], input_arm="crate_only")]
    with pytest.raises(ValueError, match="input.arm"):
        pack.build_blind_review_pack(**arguments)
    assert_unpublished(arguments)


def test_real_campaign_pack_keeps_scientific_values_and_historical_evidence(historical_inputs):
    inputs = rebind_record(historical_inputs, historical_inputs["record"].read_bytes() + (
        "generation_metadata:\n  model: opaque-fixture-generator\n"
        "consented: false\nmissing: null\n"
        "ordered_values: [null, false, '005', second, first]\n"
        "source_text: |\n  Original source wording, punctuation, and 005 remain.\n"
    ).encode())
    root = inputs["record"].parent
    old_rating = root / "retained-prior-rating.json"
    old_rating.write_text('{"fixture":"historical rating retained verbatim"}\n')
    before = {path: path.read_bytes() for path in root.iterdir() if path.is_file()}
    arguments = pack_arguments(inputs)
    key = pack.build_blind_review_pack(**arguments)
    assert json.loads(arguments["key_output"].read_bytes()) == key
    assert key["scientific_approval"] is False and key["cohort"] == "campaign"
    assert len(key["records"]) == len(key["historical_bindings"]) == 1
    assert key["historical_bindings"][0]["binding"]["sha256"] == inputs["registration_sha256"]
    assert key["historical_bindings"][0]["identity"]["evidence_status"] == {
        "generation_registration": "not_recorded", "generation_acceptance": "not_established",
    }
    output = arguments["output_dir"]
    assert {path.name for path in output.iterdir()} == {"blind_01.yaml", "review_sheet.tsv"}
    raw = (output / "blind_01.yaml").read_bytes()
    assert raw and sha(raw) == key["records"][0]["blinded_sha256"]
    assert (output / "review_sheet.tsv").stat().st_size > 0
    doc = yaml.safe_load(raw)
    assert "run_label" not in doc and "generation_metadata" not in doc
    assert b"opaque-fixture-generator" not in raw
    assert doc["consented"] is False and doc["missing"] is None
    assert doc["ordered_values"] == [None, False, "005", "second", "first"]
    assert doc["source_text"] == "Original source wording, punctuation, and 005 remain.\n"
    assert before == {path: path.read_bytes() for path in before}


def test_historical_nested_condition_is_not_admitted_without_explicit_opt_in(historical_inputs):
    arguments = pack_arguments(historical_inputs)
    # Supply ordinary sibling provenance so refusal tests the missing explicit
    # historical identity adapter, rather than a missing file.
    sibling = historical_inputs["record"].with_name("FICTIONAL_STUDY_provenance.yaml")
    sibling.write_bytes(historical_inputs["provenance"].read_bytes())
    arguments.update(historical_bindings=[], historical_decisions=[])
    with pytest.raises(ValueError, match="identity differs from the declared cohort"):
        pack.build_blind_review_pack(**arguments)
    assert_unpublished(arguments)


@pytest.mark.parametrize("mutation,reason", [
    ("missing", "condition pointer is missing"),
    ("conflict", "condition evidence conflicts"),
    ("decision-copy", "decision differs from selected authority"),
    ("reference-swap", "historical binding SHA256 differs"),
])
def test_campaign_requires_the_bound_historical_identity_and_decision(historical_inputs, mutation, reason):
    inputs = historical_inputs
    if mutation in {"missing", "conflict"}:
        prior = yaml.safe_load(inputs["provenance"].read_bytes())
        if mutation == "missing":
            prior["prompts"]["request"]["spec"].pop("condition")
        else:
            prior["run"]["condition"] = "conflicting-condition"
        inputs = rebind_provenance(inputs, prior)
    arguments = pack_arguments(inputs)
    if mutation == "decision-copy":
        selected = arguments["historical_decisions"][0]
        copy = selected.with_name("unselected-decision.md")
        copy.write_bytes(selected.read_bytes())
        arguments["historical_decisions"] = [copy]
    elif mutation == "reference-swap":
        binding = binding_document(inputs)
        binding["decision_reference"] = "unselected-reference"
        inputs["registration"].write_bytes(runner.shared.canonical(binding))
    with pytest.raises(ValueError, match=reason):
        pack.build_blind_review_pack(**arguments)
    assert_unpublished(arguments)


@pytest.mark.parametrize("component", ["registration", "provenance", "cohort", "decision"])
def test_captured_authority_change_before_publication_refuses(historical_inputs, component, monkeypatch):
    binding = binding_document(historical_inputs)
    target = (historical_inputs[component] if component in {"registration", "provenance"}
              else Path(binding[component]["path"]))
    arguments = pack_arguments(historical_inputs)
    original_write, changed = pack._write, []

    def mutate_after_staging(path, raw):
        original_write(path, raw)
        if not changed:
            target.write_bytes(target.read_bytes() + b"\n")
            changed.append(target)

    monkeypatch.setattr(pack, "_write", mutate_after_staging)
    with pytest.raises(ValueError, match="historical authority changed during review pack preparation"):
        pack.build_blind_review_pack(**arguments)
    assert changed == [target]
    assert_unpublished(arguments)


def test_same_bytes_copy_does_not_satisfy_bound_campaign_source(historical_inputs):
    arguments = pack_arguments(historical_inputs)
    copied = historical_inputs["record"].with_name("unselected-full-copy.yaml")
    copied.write_bytes(historical_inputs["record"].read_bytes())
    arguments["records"] = [replace(arguments["records"][0], source_path=copied)]
    with pytest.raises(ValueError, match="selected record differs from its binding"):
        pack.build_blind_review_pack(**arguments)
    assert_unpublished(arguments)


def test_synthetic_mode_cannot_bypass_explicit_historical_cohort_admission(historical_inputs):
    arguments = pack_arguments(historical_inputs)
    arguments["cohort"] = "synthetic"
    with pytest.raises(ValueError, match="historical campaign binding requires cohort and selected decision"):
        pack.build_blind_review_pack(**arguments)
    assert_unpublished(arguments)
