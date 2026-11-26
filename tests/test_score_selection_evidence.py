"""Synthetic receipt/publication joins for issue 6385; no scorer calls."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema.score_selection import build_evidence_table


INSTRUMENT = "synthetic-instrument"
LABEL = "configuration_rep1"
PROJECT = "Example"
METHOD = "synthetic"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return sha(raw)


def scenario(tmp_path):
    corpus = tmp_path / "corpus"
    metadata_root = tmp_path / "receipts"
    record = corpus / "data/d4d_concatenated" / METHOD / LABEL / (PROJECT + "_d4d.yaml")
    record.parent.mkdir(parents=True)
    record.write_text("id: example:record\ntitle: Synthetic\n")
    entries = {}
    for family, maximum in (("rubric10", 50), ("rubric20", 88)):
        for number in (1, 2, 3):
            run = metadata_root / (family + "-" + str(number))
            directory = (corpus / "data/evaluation_llm" / (family + "_semantic") / "label_aware" / INSTRUMENT
                         if number == 1 else corpus / "data/evaluation_repeats" / INSTRUMENT /
                         ("scoring_rep" + str(number)) / (family + "_semantic"))
            output = directory / (PROJECT + "_" + LABEL + "_evaluation.json")
            identity = {"rubric": family + "-semantic", "version": "6.0", "project": PROJECT,
                        "method": METHOD, "label": LABEL, "instrument_id": INSTRUMENT,
                        "d4d_file": str(record.relative_to(corpus))}
            inputs = {name: {"sha256": sha((family + name).encode())} for name in
                      ("agent-definition.md", "output-schema.json", "evidence-authority.json", "rubric.txt")}
            inputs.update({"record.yaml": {"sha256": sha(record.read_bytes())},
                           "scope-context.json": {"sha256": sha(b"scope")}})
            metadata = {"input_sha256": inputs["record.yaml"]["sha256"],
                        "context_sha256": sha(b"context"),
                        "scope_context_sha256": inputs["scope-context.json"]["sha256"],
                        "rubric_sha256": inputs["rubric.txt"]["sha256"],
                        "instrument_sha256": inputs["agent-definition.md"]["sha256"],
                        "evidence_authority_sha256": inputs["evidence-authority.json"]["sha256"]}
            deterministic = {"metadata": metadata, "evaluation_scope": {"policy": "single_dataset"},
                             "applicability_context": {}}
            plan = {"instrument": INSTRUMENT, "identity": identity, "inputs": inputs,
                    "run_directory": str(run), "output": str(output), "prompt": family,
                    "prompt_sha256": sha(family.encode()), "runner_sha256": sha(b"runner"),
                    "definition_provenance": {"composed_sha256": metadata["instrument_sha256"]},
                    "deterministic_fields": deterministic}
            publication = {**{k: v for k, v in identity.items() if k != "instrument_id"},
                           **deterministic,
                           "scorer_instrument": {"id": INSTRUMENT, "prompt_sha256": plan["prompt_sha256"],
                                                 "runner_sha256": plan["runner_sha256"]},
                           "overall_score": {"total_points": 20 + number, "max_points": maximum,
                                             "adjusted_max_points": maximum}}
            output_sha = write(output, publication)
            plan_sha = write(run / "plan.json", plan)
            receipt = {"status": "VALIDATED_AND_PUBLISHED", "plan_sha256": sha(json.dumps(plan, sort_keys=True).encode()),
                       "codex_exit": 0, "validator_exit": 0, "auth_copy_absent": True,
                       "output": str(output), "output_sha256": output_sha, "validator_input_sha256": output_sha}
            receipt_sha = write(run / "receipt.json", receipt)
            entry = {"plan": plan, "receipt": receipt, "publication": publication, "output": output,
                     "plan_path": run / "plan.json", "receipt_path": run / "receipt.json"}
            if number > 1:
                manifest_path = metadata_root / "export-manifests" / run.name / "manifest.json"
                manifest = {"status": "EXPORTED_VALIDATED_REPEAT", "identity": identity,
                            "scoring_replicate": number, "generation_replicate": 1,
                            "actual_plan": str(run / "plan.json"), "actual_plan_sha256": plan_sha,
                            "actual_receipt": str(run / "receipt.json"), "actual_receipt_sha256": receipt_sha,
                            "destination": str(output), "destination_sha256": output_sha,
                            "source_output_sha256": output_sha, "copy_validator_exit": 0}
                baseline = entries[family, 1]
                manifest.update(baseline_plan=str(baseline["plan_path"]),
                                baseline_plan_sha256=sha(baseline["plan_path"].read_bytes()),
                                baseline_receipt=str(baseline["receipt_path"]),
                                baseline_receipt_sha256=sha(baseline["receipt_path"].read_bytes()))
                write(manifest_path, manifest)
                entry.update(manifest=manifest, manifest_path=manifest_path)
            entries[family, number] = entry
    candidates = [{"label": LABEL, "record": record, "validity": "valid", "slots": 2}]
    return corpus, metadata_root, candidates, entries


def table(case, roots=True):
    corpus, receipts, candidates, _entries = case
    return build_evidence_table(PROJECT, "configuration", INSTRUMENT, candidates=candidates,
                                corpus_root=corpus, evidence_roots=[receipts] if roots else [])


def cell(rows, family="rubric10", number=1):
    return rows[0]["rubrics"][family]["scorings"][number - 1]


def rebind(entry):
    """Bind deliberate synthetic modifications consistently for mutation tests."""
    plan_sha = write(entry["plan_path"], entry["plan"])
    receipt = entry["receipt"]
    receipt["plan_sha256"] = sha(json.dumps(entry["plan"], sort_keys=True).encode())
    output_sha = write(entry["output"], entry["publication"])
    receipt.update(output_sha256=output_sha, validator_input_sha256=output_sha)
    receipt_sha = write(entry["receipt_path"], receipt)
    if "manifest" in entry:
        entry["manifest"].update(actual_plan_sha256=plan_sha, actual_receipt_sha256=receipt_sha,
                                 destination_sha256=output_sha, source_output_sha256=output_sha)
        write(entry["manifest_path"], entry["manifest"])


def rebind_receipt_only(entry):
    digest = write(entry["receipt_path"], entry["receipt"])
    entry["manifest"]["actual_receipt_sha256"] = digest
    write(entry["manifest_path"], entry["manifest"])


def add_refusal(case, family="rubric10", name="original-refusal"):
    directory = case[1] / name
    plan = copy.deepcopy(case[3][family, 3]["plan"])
    plan["run_directory"] = str(directory)
    plan_sha = write(directory / "plan.json", plan)
    receipt = {"status": "REFUSED", "failure": "synthetic refusal",
               "plan_sha256": sha(json.dumps(plan, sort_keys=True).encode())}
    receipt_sha = write(directory / "receipt.json", receipt)
    return {"plan": plan, "receipt": receipt, "plan_path": directory / "plan.json",
            "receipt_path": directory / "receipt.json", "plan_sha256": plan_sha, "receipt_sha256": receipt_sha}


def declare_replacement(case, original, family="rubric10", number=3):
    entry = case[3][family, number]
    entry["manifest"].update(attempt=2,
                             refused_attempt_receipt={"path": str(original["receipt_path"]),
                                                      "sha256": original["receipt_sha256"]},
                             refused_attempt_plan={"path": str(original["plan_path"]),
                                                   "sha256": original["plan_sha256"]})
    write(entry["manifest_path"], entry["manifest"])


def test_isolated_reader_receipt_and_publication_guards(tmp_path):
    """Each mutation changes just one proof, with all other bindings refreshed."""
    cases = ("publication_hash", "receipt_plan", "manifest_output_hash", "validator_input_hash",
             "codex_exit", "validator_exit", "auth_cleanup", "definition_provenance",
             "plan_input_metadata", "receipt_status", "export_status", "copy_validator_exit",
             "publication_identity", "plan_hash_binding", "receipt_hash_binding", "planned_metadata_key")
    for change in cases:
        case = scenario(tmp_path / change)
        entry = case[3]["rubric10", 2]
        if change == "publication_hash":
            entry["publication"]["overall_score"]["total_points"] += 1
            write(entry["output"], entry["publication"])
        elif change == "receipt_plan":
            entry["plan"]["unmeasured_test_annotation"] = "changed"
            entry["manifest"]["actual_plan_sha256"] = write(entry["plan_path"], entry["plan"])
            write(entry["manifest_path"], entry["manifest"])
        elif change == "manifest_output_hash":
            entry["manifest"]["destination_sha256"] = sha(b"wrong exported bytes")
            write(entry["manifest_path"], entry["manifest"])
        elif change == "validator_input_hash":
            entry["receipt"]["validator_input_sha256"] = sha(b"wrong validated bytes")
            rebind_receipt_only(entry)
        elif change in ("codex_exit", "validator_exit", "auth_cleanup", "receipt_status"):
            key = "auth_copy_absent" if change == "auth_cleanup" else "status" if change == "receipt_status" else change
            entry["receipt"][key] = False if change == "auth_cleanup" else "STARTED" if change == "receipt_status" else 1
            rebind_receipt_only(entry)
        elif change == "definition_provenance":
            entry["plan"]["definition_provenance"]["composed_sha256"] = sha(b"other composed definition")
            rebind(entry)
        elif change == "plan_input_metadata":
            entry["plan"]["inputs"]["evidence-authority.json"]["sha256"] = sha(b"other authority")
            rebind(entry)
        elif change in ("export_status", "copy_validator_exit"):
            key = "status" if change == "export_status" else change
            entry["manifest"][key] = "REFUSED" if change == "export_status" else 1
            write(entry["manifest_path"], entry["manifest"])
        elif change == "publication_identity":
            entry["publication"]["label"] = "another_rep1"
            rebind(entry)
        elif change in ("plan_hash_binding", "receipt_hash_binding"):
            key = "actual_plan_sha256" if change == "plan_hash_binding" else "actual_receipt_sha256"
            entry["manifest"][key] = sha(b"incorrect metadata hash")
            write(entry["manifest_path"], entry["manifest"])
        else:
            entry["plan"]["deterministic_fields"] = copy.deepcopy(entry["plan"]["deterministic_fields"])
            entry["plan"]["deterministic_fields"]["metadata"]["required_extra_annotation"] = "must remain"
            rebind(entry)
        result = cell(table(case), number=2)
        assert result["status"] == "not measured", change
        assert result["points"] is None, change


def test_replacement_original_status_and_hash_checks_are_independent(tmp_path):
    for change in ("status", "hash"):
        case = scenario(tmp_path / change)
        original = add_refusal(case)
        declare_replacement(case, original)
        if change == "status":
            original["receipt"]["status"] = "STARTED"
            digest = write(original["receipt_path"], original["receipt"])
        else:
            digest = sha(b"wrong original receipt hash")
        entry = case[3]["rubric10", 3]
        entry["manifest"]["refused_attempt_receipt"]["sha256"] = digest
        write(entry["manifest_path"], entry["manifest"])
        assert cell(table(case), number=3)["status"] == "not measured", change


def test_baseline_is_pinned_by_repeat_receipts_and_not_a_repeat_run(tmp_path):
    case = scenario(tmp_path / "pinned")
    for number in (2, 3):
        entry = case[3]["rubric10", number]
        entry["manifest"]["baseline_receipt_sha256"] = sha(b"different baseline receipt")
        write(entry["manifest_path"], entry["manifest"])
    assert cell(table(case))["status"] == "not measured"
    assert "baseline" in cell(table(case))["reason"]

    unrelated = copy.deepcopy(case[3]["rubric10", 1]["plan"])
    directory = case[1] / "000-unrelated-plan"
    unrelated["run_directory"] = str(directory)
    unrelated["identity"].update(version="different", unrelated_annotation="must not select the manifest filter")
    write(directory / "plan.json", unrelated)
    write(directory / "receipt.json", {"status": "STARTED"})
    assert cell(table(case))["status"] == "not measured"
    assert "baseline" in cell(table(case))["reason"]

    case = scenario(tmp_path / "not-repeat")
    first = case[3]["rubric10", 1]
    first["receipt"]["status"] = "STARTED"
    write(first["receipt_path"], first["receipt"])
    for number in (2, 3):
        entry = case[3]["rubric10", number]
        entry["publication"] = copy.deepcopy(first["publication"])
        entry["manifest"] = {key: value for key, value in entry["manifest"].items() if not key.startswith("baseline_")}
        rebind(entry)
    assert cell(table(case))["status"] == "not measured"


def test_all_refusals_require_exactly_one_declared_replacement(tmp_path):
    for change in ("undeclared", "omitted_attempt", "second_refusal", "multiply_declared"):
        case = scenario(tmp_path / change)
        original = add_refusal(case)
        if change != "undeclared":
            declare_replacement(case, original)
        if change == "omitted_attempt":
            entry = case[3]["rubric10", 3]
            del entry["manifest"]["attempt"]
            write(entry["manifest_path"], entry["manifest"])
        elif change == "second_refusal":
            add_refusal(case, name="second-refusal")
        elif change == "multiply_declared":
            declare_replacement(case, original, number=2)
        rows = table(case)
        assert any("refus" in problem for problem in rows[0]["eligibility_problems"]), change
        assert rows[0]["rubrics"]["rubric10"]["eligibility_problems"], change


def test_every_nonaccepted_matching_run_is_counted_without_reading_its_output(tmp_path, monkeypatch):
    from data_sheets_schema.score_selection import load_evidence_index, pooled_variation

    for kind, status in (("missing", None), ("started", "STARTED"), ("unknown", "INTERRUPTED"),
                         ("no_status", None), ("malformed_status", {"unexpected": True}),
                         ("malformed_receipt", None)):
        case = scenario(tmp_path / kind)
        original = add_refusal(case, name="earlier-attempt")
        forbidden = original["plan_path"].parent / "candidate_evaluation.json"
        write(forbidden, {"must_not_be_read": "not a published measurement"})
        original["plan"]["output"] = str(forbidden)
        write(original["plan_path"], original["plan"])
        original["receipt"]["plan_sha256"] = sha(json.dumps(original["plan"], sort_keys=True).encode())
        if kind == "missing":
            original["receipt_path"].unlink()
        elif kind == "malformed_receipt":
            original["receipt_path"].write_text("{malformed\n")
        else:
            if kind == "no_status":
                original["receipt"].pop("status")
            else:
                original["receipt"]["status"] = status
            write(original["receipt_path"], original["receipt"])
        original_read = Path.read_bytes

        def guarded(path):
            if path == forbidden:
                raise AssertionError("nonaccepted attempt output was opened")
            return original_read(path)

        with monkeypatch.context() as scoped:
            scoped.setattr(Path, "read_bytes", guarded)
            index = load_evidence_index([case[1]])
            rows = table(case)
        assert str(original["plan_path"]) in index["runs"], kind
        if kind == "missing":
            retained = index["runs"][str(original["plan_path"])]
            assert retained["receipt_sha256"] is None
        assert all(item["status"] == "measured" for family in ("rubric10", "rubric20")
                   for item in rows[0]["rubrics"][family]["scorings"]), kind
        assert any("refused attempt is declared by 0 accepted cells" in problem
                   and "earlier-attempt/receipt.json" in problem
                   for problem in rows[0]["eligibility_problems"]), kind
        assert any("earlier-attempt/receipt.json" in reason
                   for reason in pooled_variation(rows)["fallback_reasons"]), kind


def test_unreadable_unrelated_metadata_names_the_specific_file(tmp_path):
    from data_sheets_schema.score_selection import pooled_variation

    for filename in ("plan.json", "receipt.json"):
        case = scenario(tmp_path / filename)
        original = add_refusal(case, name="unrelated-metadata")
        original["plan"]["identity"]["label"] = "another_configuration_rep1"
        write(original["plan_path"], original["plan"])
        (original["plan_path"].parent / filename).write_text("{malformed\n")
        rows = table(case)
        assert all(item["status"] == "measured" for family in ("rubric10", "rubric20")
                   for item in rows[0]["rubrics"][family]["scorings"])
        reasons = pooled_variation(rows)["fallback_reasons"]
        assert any("receipts/unrelated-metadata/" + filename in reason for reason in reasons)
        assert str(case[1]) not in " ".join(reasons)


def test_invalid_unscored_record_is_named_without_excluding_measured_invalid_noise(tmp_path):
    case = scenario(tmp_path)
    case[2][0]["validity"] = "invalid"
    measured = table(case)[0]
    assert measured["eligibility_problems"] == []
    missing = table(case, roots=False)[0]
    assert any(PROJECT + "/" + LABEL + "/" + PROJECT + "_d4d.yaml" in reason
               and "invalid generation record has unmeasured scorings" in reason
               for reason in missing["eligibility_problems"])


def test_orphan_refusal_identity_does_not_depend_on_redundant_instrument(tmp_path, monkeypatch):
    from data_sheets_schema import score_selection as reader

    for change in ("missing", "contradictory"):
        case = scenario(tmp_path / change)
        original = add_refusal(case)
        if change == "missing":
            del original["plan"]["instrument"]
        else:
            original["plan"]["instrument"] = "another-instrument"
        write(original["plan_path"], original["plan"])
        original["receipt"]["plan_sha256"] = sha(json.dumps(original["plan"], sort_keys=True).encode())
        write(original["receipt_path"], original["receipt"])

        # The old shared predicate skipped this refusal without another check
        # firing. Reproduce that behavior in memory, leaving evidence untouched.
        with monkeypatch.context() as prior:
            prior.setattr(reader, "_refusal_identity_matches", reader._identity_matches)
            legacy = table(case)
        assert legacy[0]["eligibility_problems"] == []
        assert legacy[0]["problems"] == []
        assert legacy[0]["paired_numbers"] == [1, 2, 3]

        rows = table(case)
        assert rows[0]["evidence_issues"] == []
        assert all(item["status"] == "measured" for family in ("rubric10", "rubric20")
                   for item in rows[0]["rubrics"][family]["scorings"])
        assert any("refused attempt is declared by 0 accepted cells" in problem
                   for problem in rows[0]["eligibility_problems"])
        assert rows[0]["rubrics"]["rubric10"]["eligibility_problems"]
        variation = reader.pooled_variation(rows)
        assert any("refused attempt is declared by 0 accepted cells" in reason
                   for reason in variation["fallback_reasons"])
        decision = reader.decide(rows, variation, INSTRUMENT)
        assert decision["score_policy"]["rule"] == "policy_fallback"
        assert "refused attempt is declared by 0 accepted cells" in decision["score_policy"]["fallback_reason"]


def test_published_percentage_base_is_required_even_after_rebinding(tmp_path):
    for change in ("missing_maximum", "zero_maximum", "boolean_maximum", "reduced_adjusted"):
        case = scenario(tmp_path / change)
        entry = case[3]["rubric20", 2]
        score = entry["publication"]["overall_score"]
        if change == "missing_maximum":
            del score["max_points"]
        elif change == "zero_maximum":
            score.update(max_points=0, adjusted_max_points=0)
        elif change == "boolean_maximum":
            score.update(total_points=0, max_points=True, adjusted_max_points=True)
        else:
            score["adjusted_max_points"] = 44
        rebind(entry)
        assert cell(table(case), "rubric20", 2)["status"] == "not measured", change
        assert "fixed percentage" in cell(table(case), "rubric20", 2)["reason"]


def test_consistent_other_instrument_maxima_are_read_from_publications(tmp_path):
    case = scenario(tmp_path)
    for family, maximum in (("rubric10", 60), ("rubric20", 100.0)):
        for number in (1, 2, 3):
            entry = case[3][family, number]
            entry["publication"]["overall_score"].update(max_points=maximum, adjusted_max_points=maximum)
            rebind(entry)
        baseline = case[3][family, 1]
        for number in (2, 3):
            entry = case[3][family, number]
            entry["manifest"]["baseline_plan_sha256"] = sha(baseline["plan_path"].read_bytes())
            entry["manifest"]["baseline_receipt_sha256"] = sha(baseline["receipt_path"].read_bytes())
            write(entry["manifest_path"], entry["manifest"])
    rows = table(case)
    assert not rows[0]["problems"]
    for family, maximum in (("rubric10", 60), ("rubric20", 100.0)):
        assert all(item["status"] == "measured" and item["maximum"] == maximum
                   and item["percentage"] == 100 * item["points"] / maximum
                   for item in rows[0]["rubrics"][family]["scorings"])


def test_integral_float_fixed_maxima_are_equivalent_json_numbers(tmp_path):
    case = scenario(tmp_path)
    for family, maximum in (("rubric10", 50.0), ("rubric20", 88.0)):
        entry = case[3][family, 2]
        apply_real_shape(entry)
        entry["publication"]["overall_score"].update(max_points=maximum, adjusted_max_points=maximum)
        rebind(entry)
        result = cell(table(case), family, 2)
        assert result["status"] == "measured"
        assert result["maximum"] == maximum
        assert result["adjusted_max_points"] == maximum
        assert result["percentage"] == 100 / maximum


def test_fourth_scoring_and_unreadable_records_remain_in_the_table(tmp_path):
    case = scenario(tmp_path / "fourth")
    extra = case[0] / "data/evaluation_repeats" / INSTRUMENT / "scoring_rep4/rubric10_semantic" / (PROJECT + "_" + LABEL + "_evaluation.json")
    write(extra, {"do_not_read": "a fourth scoring cannot use the registered three-run threshold"})
    row = table(case)[0]
    assert len(row["rubrics"]["rubric10"]["scorings"]) == 4
    assert row["rubrics"]["rubric10"]["scorings"][3]["status"] == "not measured"
    assert "three" in row["rubrics"]["rubric10"]["scorings"][3]["reason"]
    case[2][0]["record"].write_text("broken: [\n")
    row = table(case)[0]
    assert row["slots"] is None
    assert row["eligibility_problems"]
    assert all(item["status"] == "not measured" for family in ("rubric10", "rubric20")
               for item in row["rubrics"][family]["scorings"])


def test_incomplete_record_coverage_is_none_and_publication_paths_are_relative(tmp_path):
    case = scenario(tmp_path)
    case[2][0].update(validity="incomplete", slots=None)
    row = table(case)[0]
    assert row["slots"] is None
    assert row["slot_names"] == ["id", "title"]
    for family in ("rubric10", "rubric20"):
        for item in row["rubrics"][family]["scorings"]:
            assert not Path(item["publication_path"]).is_absolute()
            assert item["publication_sha256"] == item["sha256"]
            assert item["adjusted_max_points"] == item["maximum"]


def test_copied_and_symlinked_receipt_roots_have_specific_reasons(tmp_path):
    import shutil
    from data_sheets_schema.score_selection import load_evidence_index
    case = scenario(tmp_path / "source")
    copied = tmp_path / "copied"
    shutil.copytree(case[1], copied)
    index = load_evidence_index([copied])
    assert any("copied or relocated" in issue for issue in index["issues"])
    linked = tmp_path / "linked"
    linked.symlink_to(case[1], target_is_directory=True)
    index = load_evidence_index([linked])
    assert index["runs"] == {}
    assert any("symlink" in issue for issue in index["issues"])


def test_malformed_metadata_is_recorded_instead_of_raising(tmp_path):
    for change in ("actual_plan", "baseline_hash", "run_directory"):
        case = scenario(tmp_path / change)
        entry = case[3]["rubric10", 2]
        if change == "run_directory":
            entry["plan"]["run_directory"] = None
            rebind(entry)
        else:
            key = "actual_plan" if change == "actual_plan" else "baseline_plan_sha256"
            entry["manifest"][key] = []
            write(entry["manifest_path"], entry["manifest"])
        rows = table(case)
        assert len(rows) == 1
        assert rows[0]["problems"], change


def test_denied_evidence_directory_enumeration_records_series_fallback(tmp_path, monkeypatch):
    from data_sheets_schema.score_selection import load_evidence_index, pooled_variation
    for kind in ("receipt", "manifest"):
        case = scenario(tmp_path / kind)
        blocked = case[1] if kind == "receipt" else case[1] / "export-manifests"
        original = Path.iterdir
        def denied(path):
            if path == blocked:
                raise PermissionError("synthetic denied directory listing")
            return original(path)
        with monkeypatch.context() as scoped:
            scoped.setattr(Path, "iterdir", denied)
            index = load_evidence_index([case[1]])
            assert any(kind in issue and "could not be enumerated" in issue for issue in index["issues"])
            rows = table(case)
        variation = pooled_variation(rows)
        assert any(kind in reason and "could not be enumerated" in reason
                   for reason in variation["fallback_reasons"])


def apply_real_shape(entry):
    """Use an accepted v6 pair's projected structure with synthetic identities."""
    path = Path(__file__).parent / "fixtures/score_selection/accepted_v6_metadata_extensions.json"
    shape = json.loads(path.read_bytes())
    hashes = copy.deepcopy(entry["plan"]["deterministic_fields"]["metadata"])
    planned = shape["plan_deterministic_fields"]
    publication = shape["published_fields"]
    planned["metadata"] = hashes
    publication["metadata"].update(hashes)
    entry["plan"]["deterministic_fields"] = planned
    entry["publication"].update(publication)
    rebind(entry)


def test_real_published_shape_keeps_annotations_without_losing_input_identity(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 2]
    apply_real_shape(entry)
    # This is exactly the old reader's false refusal: accepted publication
    # annotations make whole metadata-object equality incorrect.
    assert entry["publication"]["metadata"] != entry["plan"]["deterministic_fields"]["metadata"]
    measured = cell(table(case), number=2)
    assert measured["status"] == "measured"
    assert measured["points"] == 1 and measured["maximum"] == 50
    assert measured["measurement_identity"]["record_sha256"] == sha(case[2][0]["record"].read_bytes())


def test_rebound_publication_still_refuses_each_changed_identity_invariant(tmp_path):
    changes = ("record_hash", "scope_hash", "definition_hash", "instrument_id", "prompt_hash",
               "missing_hash", "metadata_type", "scope_block", "context_block")
    for change in changes:
        case = scenario(tmp_path / change)
        entry = case[3]["rubric10", 2]
        apply_real_shape(entry)
        publication = entry["publication"]
        if change in ("record_hash", "scope_hash", "definition_hash"):
            key = {"record_hash": "input_sha256", "scope_hash": "scope_context_sha256",
                   "definition_hash": "instrument_sha256"}[change]
            publication["metadata"][key] = sha(change.encode())
        elif change in ("instrument_id", "prompt_hash"):
            key = "id" if change == "instrument_id" else "prompt_sha256"
            publication["scorer_instrument"][key] = "different-instrument" if key == "id" else sha(b"different prompt")
        elif change == "missing_hash":
            del publication["metadata"]["evidence_authority_sha256"]
        elif change == "metadata_type":
            publication["metadata"] = []
        elif change == "scope_block":
            publication["evaluation_scope"]["unexpected_extension"] = "not allowed"
        else:
            publication["applicability_context"]["changed"] = True
        # Rebind all ordinary publication/receipt/export hashes, so refusal
        # proves the semantic identity check, rather than a stale byte digest.
        rebind(entry)
        result = cell(table(case), number=2)
        assert result["status"] == "not measured", change
        assert "published bytes" not in result["reason"], change
        assert result["points"] is None and result["percentage"] is None


def test_three_scorings_each_rubric_with_identical_measured_inputs(tmp_path):
    case = scenario(tmp_path)
    rows = table(case)
    assert len(rows) == 1
    assert rows[0]["paired"]["count"] == 3
    assert rows[0]["problems"] == []
    for family in ("rubric10", "rubric20"):
        evidence = rows[0]["rubrics"][family]
        assert evidence["count"] == 3 and evidence["spread"] > 0
        assert all(item["attempt"] == 1 for item in evidence["scorings"])
        assert len({item["measurement_identity"]["schema_sha256"] for item in evidence["scorings"]}) == 1
    assert rows[0]["receipt_coverage"] is None
    assert rows[0]["presence_evaluation"] is None
    assert rows[0]["review_verdict_counts"] is None


def test_published_scores_without_receipts_are_not_measurements(tmp_path):
    rows = table(scenario(tmp_path), roots=False)
    assert rows[0]["paired"]["mean"] is None
    assert all(item["points"] is None for family in ("rubric10", "rubric20")
               for item in rows[0]["rubrics"][family]["scorings"])


def test_missing_scoring_remains_explicit_not_zero(tmp_path):
    case = scenario(tmp_path)
    case[3]["rubric10", 3]["output"].unlink()
    row = table(case)
    assert cell(row, number=3)["status"] == "not measured"
    assert cell(row, number=3)["points"] is None
    assert row[0]["paired_numbers"] == [1, 2]


def test_other_instrument_and_changed_record_are_not_mixed(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 2]
    entry["plan"]["instrument"] = "another-instrument"
    entry["plan"]["identity"]["instrument_id"] = "another-instrument"
    rebind(entry)
    assert cell(table(case), number=2)["status"] == "not measured"
    case[2][0]["record"].write_text("id: example:changed\n")
    assert cell(table(case))["status"] == "not measured"
    assert "changed record" in cell(table(case))["reason"]


def test_schema_or_measured_input_drift_invalidates_repeated_mean(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 3]
    entry["plan"]["inputs"]["output-schema.json"]["sha256"] = sha(b"different schema")
    rebind(entry)
    rows = table(case)
    assert rows[0]["rubrics"]["rubric10"]["mean"] is None
    assert any("measured inputs differ" in problem for problem in rows[0]["problems"])


def test_refused_scoring_never_opens_its_published_or_raw_output(tmp_path, monkeypatch):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 3]
    entry["receipt"].update(status="REFUSED", failure="synthetic refusal")
    rebind(entry)
    original = Path.read_bytes
    def guarded(path):
        if path == entry["output"] or path.name in ("candidate_evaluation.json", "raw-response.json"):
            raise AssertionError("refused output was opened")
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", guarded)
    assert cell(table(case), number=3)["status"] == "not measured"


def test_replacement_is_one_scoring_and_keeps_refused_receipt_provenance(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric20", 3]
    refused_path = case[1] / "refused-rubric20-3"
    old_plan = copy.deepcopy(entry["plan"])
    old_plan["run_directory"] = str(refused_path)
    old_plan_sha = write(refused_path / "plan.json", old_plan)
    refused = {"status": "REFUSED", "failure": "synthetic non-score refusal",
               "plan_sha256": sha(json.dumps(old_plan, sort_keys=True).encode())}
    refused_sha = write(refused_path / "receipt.json", refused)
    entry["manifest"].update(attempt=2, refused_attempt_receipt={"path": str(refused_path / "receipt.json"),
                                                             "sha256": refused_sha},
                             refused_attempt_plan={"path": str(refused_path / "plan.json"), "sha256": old_plan_sha})
    write(entry["manifest_path"], entry["manifest"])
    rows = table(case)
    assert rows[0]["rubrics"]["rubric20"]["count"] == 3
    replaced = cell(rows, "rubric20", 3)
    assert replaced["attempt"] == 2
    assert replaced["refused_attempt"]["sha256"] == refused_sha
    assert replaced["refused_attempt"]["plan_sha256"] == old_plan_sha
    assert replaced["refused_attempt"]["reason"] == "UnspecifiedError: synthetic non-score refusal"
    assert rows[0]["paired_numbers"] == [1, 2, 3]
    old_plan["inputs"]["output-schema.json"]["sha256"] = sha(b"different refused schema")
    old_plan_sha = write(refused_path / "plan.json", old_plan)
    refused["plan_sha256"] = sha(json.dumps(old_plan, sort_keys=True).encode())
    refused_sha = write(refused_path / "receipt.json", refused)
    entry["manifest"]["refused_attempt_plan"]["sha256"] = old_plan_sha
    entry["manifest"]["refused_attempt_receipt"]["sha256"] = refused_sha
    write(entry["manifest_path"], entry["manifest"])
    assert cell(table(case), "rubric20", 3)["status"] == "not measured"
    assert "refused measured inputs" in cell(table(case), "rubric20", 3)["reason"]


def test_replacement_reason_is_bounded_before_evidence_table_disclosure(tmp_path):
    case = scenario(tmp_path)
    original = add_refusal(case)
    original["receipt"]["failure"] = "ScorerError: validation failed for file:/private/hidden run/candidate.json afterwards"
    original["receipt_sha256"] = write(original["receipt_path"], original["receipt"])
    declare_replacement(case, original)
    result = cell(table(case), "rubric10", 3)
    assert result["status"] == "measured"
    assert result["refused_attempt"]["reason"] == "ScorerError: validation failed for"
    assert result["refused_attempt"]["sha256"] == original["receipt_sha256"]
    assert result["refused_attempt"]["plan_sha256"] == original["plan_sha256"]


def test_changed_receipt_or_publication_is_not_a_measurement(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 2]
    entry["output"].write_text("{}\n")
    assert cell(table(case), number=2)["status"] == "not measured"
    entry = case[3]["rubric20", 2]
    entry["receipt"]["auth_copy_absent"] = False
    write(entry["receipt_path"], entry["receipt"])
    assert cell(table(case), "rubric20", 2)["status"] == "not measured"


def test_duplicate_export_is_reported_not_counted_twice(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 3]
    write(case[1] / "export-manifests/duplicate/manifest.json", entry["manifest"])
    assert cell(table(case), number=3)["status"] == "not measured"
    assert "ambiguous" in cell(table(case), number=3)["reason"]


def test_missing_schema_binding_cannot_be_supplied_by_published_metadata(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 2]
    del entry["plan"]["inputs"]["output-schema.json"]
    rebind(entry)
    assert cell(table(case), number=2)["status"] == "not measured"


def test_unrelated_malformed_presence_is_not_measured_without_hiding_scores(tmp_path):
    case = scenario(tmp_path)
    broken = case[0] / "data/evaluation/unrelated/scores.json"
    broken.parent.mkdir(parents=True)
    broken.write_text("{broken\n")
    rows = table(case)
    assert rows[0]["presence_evaluation"] is None
    assert rows[0]["paired"]["count"] == 3


def test_missing_record_has_no_zero_coverage_and_malformed_cell_is_missing(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric20", 2]
    entry["plan"]["inputs"] = []
    rebind(entry)
    assert cell(table(case), "rubric20", 2)["status"] == "not measured"
    case[2][0]["record"].unlink()
    case[2][0]["slots"] = 0
    rows = table(case)
    assert rows[0]["slots"] is None
    assert rows[0]["paired"]["mean"] is None


def test_optional_columns_require_checked_or_record_bound_evidence(tmp_path):
    case = scenario(tmp_path)
    corpus, _receipts, candidates, _entries = case
    record_sha = sha(candidates[0]["record"].read_bytes())
    provenance_path = (corpus / "data/d4d_concatenated" / (METHOD + "_core") /
                       LABEL / (PROJECT + "_provenance.yaml"))
    slots = {"with_receipt": 1, "receiptable": 2}
    verdicts = {"slot_receipted": {"supported": 1, "weak": 1}}
    provenance = {"receipts": {"checked": True, "slots": slots},
                  "review": {"checked": True, "adverse": 1, "by_kind": verdicts,
                             "findings": [], "unanswered": [], "unanswered_truncated": None}}
    # JSON is a YAML subset and retains the exact synthetic provenance shape.
    write(provenance_path, provenance)
    presence_path = corpus / "data/evaluation/synthetic-presence/scores.json"
    presence = {"project": PROJECT, "method": METHOD, "label": LABEL,
                "instrument": {"kind": "deterministic_presence", "input_sha256": record_sha},
                "rubric10": {"total": 2, "max": 4, "percentage": 50},
                "rubric20": {"total": 1, "max": 4, "percentage": 25}}
    write(presence_path, [presence])
    row = table(case)[0]
    assert row["receipt_coverage"] == slots
    assert row["review_verdict_counts"] == verdicts
    assert len(row["presence_evaluation"]) == 1
    assert row["presence_evaluation"][0]["rubric10"] == presence["rubric10"]
    assert row["presence_evaluation"][0]["rubric20"] == presence["rubric20"]
    assert row["presence_evaluation"][0]["instrument"]["input_sha256"] == record_sha

    provenance["receipts"]["checked"] = False
    provenance["review"]["checked"] = False
    write(provenance_path, provenance)
    del presence["instrument"]["input_sha256"]
    write(presence_path, [presence])
    row = table(case)[0]
    assert row["receipt_coverage"] is None
    assert row["review_verdict_counts"] is None
    assert row["presence_evaluation"] is None
    assert row["paired"]["count"] == 3
