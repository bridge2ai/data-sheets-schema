"""Offline planning and request fidelity, never model efficacy/calibration."""
import hashlib
from datetime import date, datetime, timedelta, timezone
import json
import socket
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import api_runner, evidence_score, support_judge, support_plan
from data_sheets_schema.cli.evaluate import evaluate

SCHEMA = '''id: https://example.org/plan
name: plan
imports:
  - linkml:types
prefixes:
  linkml: https://w3id.org/linkml/
  ex: https://example.org/
default_prefix: ex
classes:
  Dataset:
    slots: [id, title, count, enabled, creators, notes]
  Creator:
    attributes:
      name:
        range: string
slots:
  id:
    range: uriorcurie
    identifier: true
  title:
    range: string
  count:
    range: integer
  enabled:
    range: boolean
  notes:
    range: string
  creators:
    range: Creator
    multivalued: true
    inlined_as_list: true
'''


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.STDOUT).decode().strip()


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("provider/network resolution is forbidden in an offline plan")
    monkeypatch.setattr(api_runner, "_client", forbidden)
    monkeypatch.setattr(api_runner, "_call_with_retry", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    root = tmp_path / "source"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Offline test")
    (root / "schema.yaml").write_text(SCHEMA)
    record = {"id": "ex:harbor", "title": "Harbor", "count": 0, "enabled": False,
              "creators": [{"name": "Dana"}], "notes": None}
    raw = yaml.safe_dump(record).encode()
    (root / "record.yaml").write_bytes(raw)
    bundle = b"FILE: survey.txt\nHarbor is a survey. Dana prepared the data.\n"
    (root / "bundle.txt").write_bytes(bundle)
    provenance = {"run": {"project": "Harbor", "label": "condition_rep1", "method": "api"},
                  "model": {"model": "claude-opus-5"},
                  "inputs": {"bundle_path": "bundle.txt", "bundle_md5": hashlib.md5(bundle).hexdigest()}}
    (root / "provenance.yaml").write_text(yaml.safe_dump(provenance))
    jobs = [{"id": f"harbor_{rubric}", "input": "record.yaml", "project": "Harbor",
             "label": "condition_rep1", "method": "api", "cohort": "v7", "generation_rep": 1,
             "purpose": "primary", "rubric": rubric, "output": f"{rubric}.json",
             "provenance": "provenance.yaml"} for rubric in ("rubric10", "rubric20")]
    roster = {"jobs": jobs, "pinned_files": {"record.yaml": support_plan.sha256(raw)}}
    (root / "roster.json").write_text(json.dumps(roster))
    git(root, "add", ".")
    git(root, "commit", "-qm", "original fixture")
    return root, tmp_path / "plan"


def build(fixture, **kwargs):
    root, output = fixture
    return support_plan.build_plan(root / "roster.json", output, root=root,
                                   profile="neutral", schema_path=root / "schema.yaml", **kwargs)


def rewrite_roster(root, change):
    path = root / "roster.json"
    doc = json.loads(path.read_text())
    change(doc)
    path.write_text(json.dumps(doc))


def test_manifest_is_blocked_own_record_inventory_not_calibration(fixture, monkeypatch):
    root, output = fixture
    before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
    monkeypatch.setattr(support_plan, "evaluation_model_settings", lambda: {
        "name": "claude-opus-5", "basis": "defaults_to_generation_model"})
    manifest = build(fixture)
    assert manifest["counts"] == {"records": 1, "populated_top_level_fields": 5, "axis_targets": 10,
                                  "by_axis": {"grounding_v2": 5, "fitness": 5}}
    assert manifest["schema"]["rendered_specifications"]["sha256"] == manifest["schema"]["specification_sha256"]
    assert manifest["model"]["basis"] == "defaults_to_generation_model"
    assert manifest["records"][0]["same_family"] == "yes"
    assert manifest["readiness"]["ready_for_paid_run"] is False
    assert {"nested_granularity_decision_3342", "independent_empirical_calibration_3343", "paid_run_authorization"} <= set(manifest["readiness"]["blockers"])
    assert {t["status"] for t in manifest["targets"]} == {"planned_not_measured"}
    assert all(t["propagated"] is False for t in manifest["targets"])
    assert {t["judgement_context"]["specification"] for t in manifest["targets"]} == {manifest["schema"]["specification_sha256"]}
    assert all(s["estimated_usd"] is None for s in manifest["estimate"]["scenarios"].values())
    assert manifest["estimate"]["scenarios"]["uncached"]["tokens"]["output"] == 80000
    assert before == {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
    assert len(list((output / "artifacts").iterdir())) < 50  # Source bundle shared, not copied per call.


@pytest.mark.parametrize("model,expected", [("gpt-5", "no"), ("unknown-model", "unknown")])
def test_explicit_evaluator_basis_and_family(fixture, model, expected):
    manifest = build(fixture, model=model)
    assert manifest["model"] == {"name": model, "basis": "explicit_override"}
    assert manifest["records"][0]["same_family"] == expected


def test_default_evaluator_config_is_copied_and_requests_survive_its_removal(fixture, monkeypatch):
    from data_sheets_schema import evaluation_model
    root, output = fixture
    config = root / "judge.yaml"
    raw = b"version: 1\nmodel: independent-judge\n"
    config.write_bytes(raw)
    monkeypatch.setattr(evaluation_model, "CONFIG_PATH", config)
    manifest = build(fixture)
    selection = manifest["model"]
    assert selection["name"] == "independent-judge"
    assert selection["basis"] == "evaluation_config"
    pin = selection["configuration"]["artifact"]
    assert pin == {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    assert (output / "artifacts" / pin["sha256"]).read_bytes() == raw
    assert "duplicate_keys.py" in manifest["planning_code"]["files"]
    config.unlink()
    for target in manifest["targets"]:
        assert support_plan.materialize_request(output, target["id"])["model"] == "independent-judge"


@pytest.mark.parametrize("remove", [False, True])
def test_default_config_race_fails_before_publishing(fixture, monkeypatch, remove):
    from data_sheets_schema import evaluation_model
    root, output = fixture
    config = root / "judge.yaml"
    config.write_text("version: 1\nmodel: initial-judge\n")
    monkeypatch.setattr(evaluation_model, "CONFIG_PATH", config)
    def resolve_then_change():
        selected = evaluation_model.evaluation_model_settings()
        if remove:
            config.unlink()
        else:
            config.write_text("version: 1\nmodel: later-judge\n")
        return selected
    monkeypatch.setattr(support_plan, "evaluation_model_settings", resolve_then_change)
    with pytest.raises(support_plan.PlanError, match="evaluation config .*after model selection"):
        build(fixture)
    assert not output.exists()


def test_explicit_plan_model_does_not_read_default_config(fixture, monkeypatch):
    from data_sheets_schema import evaluation_model
    monkeypatch.setattr(evaluation_model, "CONFIG_PATH", fixture[0] / "missing-config.yaml")
    manifest = build(fixture, model="explicit-judge")
    assert manifest["model"] == {"name": "explicit-judge", "basis": "explicit_override"}


def test_saved_request_equals_both_live_judge_boundaries(fixture, monkeypatch):
    root, output = fixture
    manifest = build(fixture, model="judge", max_tokens=417)
    record = yaml.safe_load((root / "record.yaml").read_text())
    bundle = (root / "bundle.txt").read_text()
    from data_sheets_schema.profiles import NEUTRAL
    spec = support_judge.SupportSpecification.from_schema(schema_path=root / "schema.yaml", profile=NEUTRAL)
    support = support_judge.SupportJudgeV2(client=object(), model="judge", specification=spec, max_tokens=417)
    fitness = evidence_score.LLMSlotFitnessScorer(client=object(), model="judge", schema_path=root / "schema.yaml", profile=NEUTRAL, max_tokens=417)
    class Captured(Exception):
        pass
    captured = []
    def capture(client, **kwargs):
        captured.append(kwargs)
        raise Captured()
    monkeypatch.setattr(api_runner, "_call_with_retry", capture)
    for target in manifest["targets"]:
        slot = target["pointer"][1:]
        with pytest.raises(Captured):
            if target["axis"] == "grounding_v2":
                support.judge(project="Harbor", record=record, slot=slot, bundle=bundle)
            else:
                fitness(project="Harbor", slot=slot, value=record[slot])
        assert support_plan.materialize_request(output, target["id"]) == captured[-1]
    # Reconstruction is a pinned artifact operation, not a re-render under a new prompt.
    monkeypatch.setattr(support_judge, "SUPPORT_V2_SYSTEM", "Changed after planning")
    assert support_plan.materialize_request(output, manifest["targets"][0]["id"])["system"] != "Changed after planning"


def test_recovers_original_record_and_bundle_without_rewriting(fixture):
    root, output = fixture
    commit = git(root, "rev-parse", "HEAD")
    (root / "bundle.txt").write_text("today's changed source")
    (root / "record.yaml").write_text("title: changed record\n")
    manifest = build(fixture, model="judge")
    row = manifest["records"][0]
    for pin in (row["record"], row["bundle"]):
        assert pin["basis"] == "git_recovery"
        assert pin["recovery_commit"] == commit
        assert support_plan.sha256((output / "artifacts" / pin["sha256"]).read_bytes()) == pin["sha256"]
    assert (root / "bundle.txt").read_text() == "today's changed source"
    assert (root / "record.yaml").read_text() == "title: changed record\n"
    assert manifest["counts"]["populated_top_level_fields"] == 5


def test_unrecoverable_bundle_and_second_hash_disagreement_refuse(fixture):
    root, output = fixture
    path = root / "provenance.yaml"
    doc = yaml.safe_load(path.read_text())
    doc["inputs"]["bundle_sha256"] = "0" * 64
    path.write_text(yaml.safe_dump(doc))
    with pytest.raises(support_plan.PlanError, match="cannot recover"):
        build(fixture, model="judge")
    assert not output.exists()


def test_missing_record_pin_is_not_new_reference_measurement(fixture):
    root, output = fixture
    rewrite_roster(root, lambda d: d.update(pinned_files={}))
    with pytest.raises(support_plan.PlanError, match="original hash"):
        build(fixture, model="judge")
    assert not output.exists()


@pytest.mark.parametrize("mutation", [
    lambda d: d["jobs"].append(d["jobs"][0].copy()),
    lambda d: d["jobs"][1].update(project="Other"),
    lambda d: d["jobs"][1].update(input="other.yaml"),
])
def test_conflicting_or_duplicate_roster_is_rejected(fixture, mutation):
    root, output = fixture
    rewrite_roster(root, mutation)
    with pytest.raises(support_plan.PlanError, match="duplicate|conflicting|multiple"):
        build(fixture, model="judge")
    assert not output.exists()


def test_unknown_populated_field_is_not_dropped(fixture):
    root, output = fixture
    path = root / "record.yaml"
    path.write_text(path.read_text() + "unknown_claim: data\n")
    rewrite_roster(root, lambda d: d["pinned_files"].update({"record.yaml": support_plan.sha256(path.read_bytes())}))
    with pytest.raises(support_plan.PlanError, match="unknown populated slots"):
        build(fixture, model="judge")
    assert not output.exists()


def test_request_tampering_and_overwrite_refused(fixture):
    _, output = fixture
    manifest = build(fixture, model="judge")
    with pytest.raises(support_plan.PlanError, match="already exists"):
        build(fixture, model="judge")
    target = manifest["targets"][0]
    digest = target["request_recipe"]["system"]["$text"]["sha256"]
    (output / "artifacts" / digest).write_text("tampered")
    with pytest.raises(support_plan.PlanError, match="artifact has changed"):
        support_plan.materialize_request(output, target["id"])


def price_file(root, rates=None):
    path = root / "prices.json"
    path.write_text(json.dumps({"model": "judge", "currency": "USD", "per_tokens": 1000000,
                                "source": "synthetic test prices; not a rate card", "as_of": "2026-10-02",
                                "rates": rates or {"input": 2, "output": 3, "cache_read": .2, "cache_write": 2.5}}))
    return path


def test_local_price_arithmetic_and_named_cache_assumptions(fixture):
    root, _ = fixture
    manifest = build(fixture, model="judge", prices=price_file(root))
    for scenario in manifest["estimate"]["scenarios"].values():
        t = scenario["tokens"]
        expected = (t["input"]*2 + t["output"]*3 + t["cache_read"]*.2 + t["cache_write"]*2.5)/1e6
        assert scenario["estimated_usd"] == pytest.approx(expected)
    s = manifest["estimate"]["scenarios"]
    assert s["warm_within_record"]["tokens"]["cache_read"] > 0
    assert s["cache_miss_every_request"]["tokens"]["cache_read"] == 0
    assert "no judgement-cache reuse credited" in manifest["estimate"]["assumptions"]
    assert manifest["estimate"]["prices"]["basis"] == "user_supplied_unverified"


def test_missing_cache_prices_do_not_become_zero(fixture):
    root, _ = fixture
    m = build(fixture, model="judge", prices=price_file(root, {"input": 2, "output": 3}))
    assert m["estimate"]["scenarios"]["uncached"]["estimated_usd"] is not None
    assert m["estimate"]["scenarios"]["warm_within_record"]["estimated_usd"] is None


@pytest.mark.parametrize("key,value", [("per_tokens", 1000), ("currency", "EUR"), ("model", "other"),
                                       ("rates", {"input": -1}), ("rates", {"input": float("nan")}),
                                       ("rates", {"input": True})])
def test_bad_prices_rejected_before_output(fixture, key, value):
    root, output = fixture
    path = price_file(root)
    doc = json.loads(path.read_text()); doc[key] = value
    path.write_text(json.dumps(doc))
    with pytest.raises(support_plan.PlanError):
        build(fixture, model="judge", prices=path)
    assert not output.exists()


def test_cli_build_and_request_are_offline_and_report_blockers(fixture, monkeypatch):
    root, output = fixture
    real_build = support_plan.build_plan
    monkeypatch.setattr(support_plan, "build_plan", lambda *args, **kwargs: real_build(*args, **kwargs, root=root))
    runner = CliRunner()
    result = runner.invoke(evaluate, ["support-plan", "--roster", str(root / "roster.json"),
                                    "--output", str(output), "--profile", "neutral", "--model", "judge",
                                    "--schema", str(root / "schema.yaml")])
    assert result.exit_code == 0, result.output
    assert "BLOCKED for paid use" in result.output
    assert "unknown" in result.output
    manifest = json.loads((output / "manifest.json").read_text())
    result = runner.invoke(evaluate, ["support-request", "--plan", str(output), "--target", manifest["targets"][0]["id"]])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["model"] == "judge"


def test_repeat_plan_is_deterministic_and_missing_joins_are_explicit(fixture):
    root, output = fixture
    first = build(fixture, model="judge")
    second = build((root, output.with_name("second")), model="judge")
    assert first == second
    assert "missing_rubric_join_artifacts" in first["readiness"]["blockers"]
    assert first["readiness"]["missing_rubric_join_artifacts"] == ["rubric10.json", "rubric20.json"]


def test_join_results_are_pinned_when_available(fixture):
    root, _ = fixture
    for name in ("rubric10", "rubric20"):
        (root / f"{name}.json").write_text(json.dumps({"test_fixture": True, "rubric": name}))
    manifest = build(fixture, model="judge")
    assert "missing_rubric_join_artifacts" not in manifest["readiness"]["blockers"]
    for job in manifest["records"][0]["rubric_join_jobs"]:
        assert job["result_artifact"]["sha256"] == support_plan.sha256((root / job["output"]).read_bytes())


def test_shallow_recovery_and_outside_repository_paths_fail_closed(fixture):
    root, output = fixture
    original_git = support_plan._git
    from unittest.mock import patch
    (root / "bundle.txt").write_text("drift")
    def shallow(repo, *args):
        return b"true\n" if args == ("rev-parse", "--is-shallow-repository") else original_git(repo, *args)
    with patch.object(support_plan, "_git", shallow):
        with pytest.raises(support_plan.PlanError, match="complete Git history"):
            build(fixture, model="judge")
    rewrite_roster(root, lambda d: [j.update(input="../outside.yaml") for j in d["jobs"]])
    with pytest.raises(support_plan.PlanError, match="leaves the input repository"):
        build(fixture, model="judge")
    assert not output.exists()


def test_default_model_resolver_has_no_provider_access(fixture, monkeypatch):
    monkeypatch.setattr(api_runner, "_model_settings", lambda: {"name": "claude-opus-5"})
    manifest = build(fixture)
    assert manifest["model"]["basis"] == "defaults_to_generation_model"
    assert manifest["model"]["generation_model"] == "claude-opus-5"


@pytest.mark.parametrize("value", [
    pytest.param(date(2026, 1, 2), id="date"),
    pytest.param(datetime(2026, 1, 2, 3, 4, 5), id="datetime"),
    pytest.param(datetime(2026, 1, 2, 3, 4, 5, 123456,
        tzinfo=timezone(timedelta(hours=5, minutes=30))), id="aware-datetime"),
    pytest.param({"history": [date(2026, 1, 2),
                             {"created": datetime(2026, 1, 2, tzinfo=timezone.utc)}]}, id="nested"),
])
def test_yaml_temporal_values_have_typed_identity_and_unchanged_requests(fixture, value):
    root, output = fixture
    schema = yaml.safe_load((root / "schema.yaml").read_text())
    schema["slots"]["notes"]["range"] = "date"
    (root / "schema.yaml").write_text(yaml.safe_dump(schema))
    path = root / "record.yaml"
    doc = yaml.safe_load(path.read_text()); doc["notes"] = value
    path.write_text(yaml.safe_dump(doc))
    rewrite_roster(root, lambda d: d["pinned_files"].update({"record.yaml": support_plan.sha256(path.read_bytes())}))
    m = build(fixture, model="judge")
    assert m["value_identity_encoding"] == "typed-yaml-v1"
    assert m["counts"]["axis_targets"] == 12
    targets = [t for t in m["targets"] if t["pointer"] == "/notes"]
    assert {t["value_sha256"] for t in targets} == {support_plan.sha256(support_plan.value_identity(value))}
    assert support_plan.value_identity(value) != support_plan.value_identity(str(value))
    from data_sheets_schema.profiles import NEUTRAL
    spec = support_judge.SupportSpecification.from_schema(schema_path=root / "schema.yaml", profile=NEUTRAL)
    context = support_judge.build_value_context(doc, "notes", relationship=spec.relationship("notes"))
    expected = {
        "grounding_v2": support_judge.request_arguments(model="judge", max_tokens=8000,
            bundle=(root / "bundle.txt").read_text(),
            value_text=support_judge.render_request("notes", value, spec.render("notes"), context)),
        "fitness": evidence_score.fitness_request_arguments(model="judge", max_tokens=8000,
            slot="notes", value=value, specification=spec.render("notes"))}
    for target in targets:
        assert support_plan.materialize_request(output, target["id"]) == expected[target["axis"]]


def test_typed_identity_distinguishes_scalar_types_without_tag_collisions():
    values = [0, False, "0", 0.0, -0.0, None, "None", date(2026, 1, 2), "2026-01-02",
              ["date", "2026-01-02"], {"type": "date", "value": "2026-01-02"},
              datetime(2026, 1, 2), datetime(2026, 1, 2, tzinfo=timezone.utc)]
    assert len({support_plan.value_identity(v) for v in values}) == len(values)
    assert support_plan.value_identity({"a": date(2026, 1, 2), "b": [False]}) == support_plan.value_identity({"b": [False], "a": date(2026, 1, 2)})


@pytest.mark.parametrize("drift", [False, True])
def test_supplied_provenance_pin_controls_identity_and_bundle(fixture, drift):
    root, output = fixture
    path = root / "provenance.yaml"
    original = path.read_bytes()
    pin = support_plan.sha256(original)
    rewrite_roster(root, lambda d: d["pinned_files"].update({"provenance.yaml": pin}))
    if drift:
        replacement = b"Unrelated later evidence under the same run label"
        (root / "replacement.txt").write_bytes(replacement)
        doc = yaml.safe_load(original)
        doc["inputs"] = {"bundle_path": "replacement.txt", "bundle_sha256": support_plan.sha256(replacement)}
        path.write_text(yaml.safe_dump(doc))
    current = path.read_bytes()
    manifest = build(fixture, model="judge")
    row = manifest["records"][0]
    assert row["provenance"]["sha256"] == pin
    assert row["provenance"]["basis"] == ("git_recovery" if drift else "current_matches_pin")
    assert row["provenance"]["recorded_hashes"] == {"sha256": pin}
    assert row["bundle"]["path"] == "bundle.txt"
    assert (output / "artifacts" / pin).read_bytes() == original
    assert path.read_bytes() == current


@pytest.mark.parametrize("pin", ["0"*64, "malformed", None])
def test_unrecoverable_or_malformed_supplied_provenance_pin_refuses(fixture, pin):
    root, output = fixture
    rewrite_roster(root, lambda d: d["pinned_files"].update({"provenance.yaml": pin}))
    with pytest.raises(support_plan.PlanError, match="cannot recover|original hash"):
        build(fixture, model="judge")
    assert not output.exists()


def test_old_roster_labels_captured_unpinned_provenance(fixture):
    m = build(fixture, model="judge")
    assert m["records"][0]["provenance"]["basis"] == "captured_current_unpinned_by_roster"
    assert m["records"][0]["provenance"]["recorded_hashes"] == {}


def test_git_repository_overrides_cannot_change_code_input_or_recovery(fixture, monkeypatch):
    root, _ = fixture
    code_commit = git(support_plan.ROOT, "rev-parse", "HEAD")
    input_commit = git(root, "rev-parse", "HEAD")
    original_bundle = (root / "bundle.txt").read_bytes()
    (root / "bundle.txt").write_text("drift requires history from the correct repository")
    other = root.parent / "unrelated"
    other.mkdir()
    git(other, "init", "-q")
    git(other, "config", "user.email", "test@example.invalid")
    git(other, "config", "user.name", "Unrelated fixture")
    (other / "bundle.txt").write_text("Unrelated history")
    git(other, "add", "."); git(other, "commit", "-qm", "unrelated")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    monkeypatch.setenv("GIT_COMMON_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(other / ".git/index"))
    m = build(fixture, model="judge")
    assert m["planning_code"]["commit"] == code_commit
    assert m["input_repository_commit"] == input_commit
    bundle = m["records"][0]["bundle"]
    assert bundle["basis"] == "git_recovery" and bundle["recovery_commit"] == input_commit
    assert bundle["sha256"] == support_plan.sha256(original_bundle)
