"""Offline integration identities/counts, not model efficacy or calibration."""
from datetime import date
import json

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import evidence_score, support_plan, support_targets
from data_sheets_schema.cli.evaluate import evaluate
from tests.test_evaluation.test_support_plan import fixture, git, rewrite_roster, price_file


def build(fixture, **kwargs):
    root, output = fixture
    options = dict(root=root, profile="neutral", schema_path=root / "schema.yaml",
                   model="judge", plan_version=2, artifact_kind="full")
    options.update(kwargs)
    return support_plan.build_plan(root / "roster.json", output, **options)


def change_record(root, changes):
    path = root / "record.yaml"
    record = yaml.safe_load(path.read_text())
    record.update(changes)
    path.write_text(yaml.safe_dump(record))
    rewrite_roster(root, lambda d: d["pinned_files"].update({"record.yaml": support_plan.sha256(path.read_bytes())}))


def add_slot(root, name, specification):
    path = root / "schema.yaml"
    schema = yaml.safe_load(path.read_text())
    schema["classes"]["Dataset"]["slots"].append(name)
    schema["slots"][name] = specification
    path.write_text(yaml.safe_dump(schema))


def test_nested_strata_and_separate_fitness_mapping_are_complete(fixture):
    root, output = fixture
    before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
    manifest = build(fixture)
    assert manifest["format"] == "d4d-support-plan-v2"
    assert manifest["counts"] == {"records": 1, "populated_top_level_fields": 5,
        "axis_targets": 11, "by_axis": {"grounding_v3": 6, "fitness": 5},
        "support_by_kind": {"relationship_edge": 1, "attribute_value": 5},
        "fitness_top_level": 5, "blocked": 0, "blocked_by_axis": {}, "blocked_by_cause": {}}
    blockers = manifest["readiness"]["blockers"]
    assert "nested_planner_integration_3342" not in blockers
    assert {"context_projection_review_3342", "independent_empirical_calibration_3343",
            "v3_response_and_execution_registration", "paid_run_authorization"} <= set(blockers)
    assert manifest["readiness"]["ready_for_paid_run"] is False
    targets = {t["id"]: t for t in manifest["targets"]}
    for target in targets.values():
        assert target["status"] == "planned_not_measured" and target["propagated"] is False
        if target["axis"] == "grounding_v3":
            mapping = target["fitness_mapping"]
            assert mapping["basis"] == "top_level_only"
            assert targets[mapping["target_id"]]["pointer"] == mapping["pointer"]
            artifact = output / "artifacts" / target["target_artifact"]["sha256"]
            payload = json.loads(artifact.read_text())
            assert payload["context_sha256"] == target["context_sha256"]
    assert before == {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}


def test_every_saved_request_equals_its_pure_builder(fixture):
    root, output = fixture
    manifest = build(fixture, max_tokens=417)
    spec = support_targets.NestedSupportSchema.from_schema(root / "schema.yaml")
    inventory = support_targets.inventory_targets((root / "record.yaml").read_bytes(), spec, artifact_kind="full")
    full = yaml.safe_load((root / "record.yaml").read_bytes())
    fits = json.loads((output / "artifacts" / manifest["schema"]["fitness_specifications"]["sha256"]).read_text())["slots"]
    for target in manifest["targets"]:
        if target["axis"] == "grounding_v3":
            expected = support_targets.render_request(inventory.target(target["pointer"], kind=target["kind"]),
                bundle=(root / "bundle.txt").read_text(), model="judge", max_tokens=417)
        else:
            slot = support_targets.pointer_tokens(target["pointer"])[0]
            expected = evidence_score.fitness_request_arguments(model="judge", max_tokens=417,
                slot=slot, value=full[slot], specification=fits[slot])
        actual = support_plan.materialize_request(output, target["id"])
        assert actual == expected
        assert support_plan.sha256(support_plan.canonical(actual)) == target["request_sha256"]


def test_unknown_and_invalid_nested_paths_are_all_reported(fixture):
    root, _ = fixture
    change_record(root, {"unknown": "claim", "creators": [{"name": "Dana", "unrecognized": "x"}, "bad shape"]})
    manifest = build(fixture)
    blocked = {(b["axis"], b["pointer"], b["code"]) for b in manifest["blocked_paths"]}
    assert blocked == {("grounding_v3", "/unknown", "unknown_schema_slot"),
                       ("grounding_v3", "/creators/0/unrecognized", "unknown_schema_slot"),
                       ("grounding_v3", "/creators/1", "inline_class_requires_mapping"),
                       ("fitness", "/unknown", "unknown_top_level_slot")}
    assert manifest["counts"]["blocked"] == 4
    assert manifest["records"][0]["blocked_count"] == 4
    assert "unresolved_target_paths" in manifest["readiness"]["blockers"]
    assert manifest["counts"]["fitness_top_level"] == 5


def test_explicit_vocabulary_resolves_only_named_registry_and_is_pinned(fixture, monkeypatch):
    root, output = fixture
    add_slot(root, "controlled", {"range": "string", "values_from": ["fixture_terms"]})
    change_record(root, {"controlled": "ex:term"})
    missing = build(fixture)
    assert any(b["code"] == "missing_values_from_vocabulary" for b in missing["blocked_paths"])
    vocabulary = root / "vocabulary.yaml"
    vocabulary.write_text("vocabularies:\n  fixture_terms:\n    ex:term: Term label\n")
    monkeypatch.setenv("D4D_PROFILE", "bridge2ai")
    second = output.with_name("resolved")
    manifest = build((root, second), vocabulary_path=vocabulary)
    assert not manifest["blocked_paths"]
    assert manifest["schema"]["profile"] == "neutral"
    assert manifest["schema"]["vocabulary_basis"] == "explicit_vocabulary_override"
    assert manifest["schema"]["vocabulary"]["sha256"] == support_plan.sha256(vocabulary.read_bytes())
    for target in manifest["targets"]:
        if target["pointer"] == "/controlled":
            request = support_plan.materialize_request(second, target["id"])
            assert "Term label" in json.dumps(request)


def test_explicit_study_profile_overrides_ambient_neutral(fixture, monkeypatch):
    root, _ = fixture
    add_slot(root, "controlled", {"range": "string", "values_from": ["B2AI_TOPIC"]})
    change_record(root, {"controlled": "B2AI_TOPIC:1"})
    monkeypatch.setenv("D4D_PROFILE", "neutral")
    manifest = build(fixture, profile="bridge2ai")
    assert manifest["schema"]["vocabulary_basis"] == "explicit_profile_pin"
    assert "B2AI_TOPIC" in manifest["schema"]["vocabulary_names"]
    assert manifest["schema"]["vocabulary"] is not None
    assert not manifest["blocked_paths"]


@pytest.mark.parametrize("kind,cls", [(None, "Dataset"), ("core", "Dataset"), ("full", "CoreDataset"), ("collection", "Dataset")])
def test_artifact_selection_cannot_silently_use_wrong_default(fixture, kind, cls):
    with pytest.raises(support_plan.PlanError, match="artifact|collection"):
        build(fixture, artifact_kind=kind, class_name=cls)
    assert not fixture[1].exists()


def test_core_uses_its_selected_root_and_provenance_output(fixture):
    root, output = fixture
    path = root / "schema.yaml"
    source = yaml.safe_load(path.read_text())
    source["classes"]["CoreDataset"] = source["classes"].pop("Dataset")
    path.write_text(yaml.safe_dump(source))
    prov_path = root / "provenance.yaml"
    prov = yaml.safe_load(prov_path.read_text())
    prov["outputs"] = {"core": {"path": "record.yaml"}, "full": {"path": "different-full.yaml"}}
    prov_path.write_text(yaml.safe_dump(prov))
    manifest = build(fixture, artifact_kind="core", class_name="CoreDataset")
    assert manifest["schema"]["class"] == "CoreDataset"
    assert manifest["artifact_kind"] == "core"
    target = next(t for t in manifest["targets"] if t["axis"] == "grounding_v3")
    request = support_plan.materialize_request(output, target["id"])
    assert '"kind":"core"' in request["messages"][0]["content"][1]["text"]


def test_conflicting_roster_kind_or_provenance_output_refuses(fixture):
    root, output = fixture
    rewrite_roster(root, lambda d: d["jobs"][0].update(artifact_kind="core"))
    with pytest.raises(support_plan.PlanError, match="roster artifact kind"):
        build(fixture)
    rewrite_roster(root, lambda d: d["jobs"][0].pop("artifact_kind"))
    path = root / "provenance.yaml"
    value = yaml.safe_load(path.read_text()); value["outputs"] = {"full": {"path": "other.yaml"}}
    path.write_text(yaml.safe_dump(value))
    with pytest.raises(support_plan.PlanError, match="full-record path"):
        build(fixture)
    assert not output.exists()


def test_dates_escaped_pointers_and_mappings_keep_exact_values(fixture):
    root, output = fixture
    add_slot(root, "issued", {"range": "date"})
    add_slot(root, "a/b~c", {"range": "string"})
    change_record(root, {"issued": date(2026, 1, 2), "a/b~c": "qualifier"})
    manifest = build(fixture)
    by_pointer = [t for t in manifest["targets"] if t["pointer"] == "/a~1b~0c"]
    assert len(by_pointer) == 2
    support = next(t for t in by_pointer if t["axis"] == "grounding_v3")
    assert support["fitness_mapping"]["pointer"] == "/a~1b~0c"
    date_target = next(t for t in manifest["targets"] if t["pointer"] == "/issued" and t["axis"] == "grounding_v3")
    request = support_plan.materialize_request(output, date_target["id"])
    payload = json.loads(request["messages"][0]["content"][1]["text"].split("\n\n", 1)[1])
    assert yaml.safe_load(payload["value_yaml"]) == date(2026, 1, 2)


def test_recovery_and_explicit_provenance_pin_use_existing_strict_helpers(fixture):
    root, output = fixture
    before = (root / "bundle.txt").read_bytes()
    provenance = (root / "provenance.yaml").read_bytes()
    commit = git(root, "rev-parse", "HEAD")
    rewrite_roster(root, lambda d: d["pinned_files"].update({"provenance.yaml": support_plan.sha256(provenance)}))
    (root / "bundle.txt").write_text("new source bytes")
    (root / "provenance.yaml").write_text("not: the original provenance\n")
    manifest = build(fixture)
    row = manifest["records"][0]
    assert row["bundle"]["basis"] == row["provenance"]["basis"] == "git_recovery"
    assert row["bundle"]["recovery_commit"] == commit
    target = next(t for t in manifest["targets"] if t["axis"] == "grounding_v3")
    request = support_plan.materialize_request(output, target["id"])
    assert request["messages"][0]["content"][0]["text"].endswith(before.decode())
    assert (root / "provenance.yaml").read_text() == "not: the original provenance\n"


def test_cache_cost_scenarios_sum_across_separate_strata(fixture):
    root, _ = fixture
    manifest = build(fixture, prices=price_file(root), max_tokens=123)
    estimate = manifest["estimate"]
    for name, total in estimate["scenarios"].items():
        for token, count in total["tokens"].items():
            assert count == sum(v[name]["tokens"][token] for v in estimate["by_stratum"].values())
        assert total["estimated_usd"] == support_plan._cost(total["tokens"], estimate["prices"])
    assert estimate["scenarios"]["uncached"]["tokens"]["output"] == 11 * 123
    assert estimate["by_stratum"]["fitness_top_level"]["warm_within_record"]["tokens"]["cache_read"] == 0


def test_v1_default_and_explicit_v1_are_identical_and_reject_new_options(fixture):
    root, output = fixture
    args = dict(root=root, profile="neutral", schema_path=root / "schema.yaml", model="judge")
    first = support_plan.build_plan(root / "roster.json", output, **args)
    second_dir = output.with_name("explicit-v1")
    second = support_plan.build_plan(root / "roster.json", second_dir, plan_version=1, **args)
    assert first == second
    for target in first["targets"]:
        assert support_plan.materialize_request(output, target["id"]) == support_plan.materialize_request(second_dir, target["id"])
    with pytest.raises(support_plan.PlanError, match="require plan_version=2"):
        support_plan.build_plan(root / "roster.json", output.with_name("bad"), artifact_kind="full", **args)


def test_cli_opt_in_and_saved_request_tampering(fixture, monkeypatch):
    root, output = fixture
    # The CLI has no input-repository override; this wrapper selects the fixture
    # without changing the independently recorded code-root provenance.
    original = support_plan.build_plan
    monkeypatch.setattr(support_plan, "build_plan", lambda *a, **kw: original(*a, root=root, **kw))
    result = CliRunner().invoke(evaluate, ["support-plan", "--roster", str(root / "roster.json"),
        "--output", str(output), "--profile", "neutral", "--schema", str(root / "schema.yaml"),
        "--model", "judge", "--plan-version", "2", "--artifact-kind", "full"])
    assert result.exit_code == 0, result.output
    assert "BLOCKED for paid use" in result.output
    manifest = json.loads((output / "manifest.json").read_text())
    target = manifest["targets"][0]
    path = output / "artifacts" / target["request_recipe"]["system"]["$text"]["sha256"]
    path.write_text("changed")
    with pytest.raises(support_plan.PlanError, match="artifact has changed"):
        support_plan.materialize_request(output, target["id"])


def test_explicit_collection_schema_keeps_wrapped_resource_identity(fixture):
    root, output = fixture
    path = root / "schema.yaml"
    source = yaml.safe_load(path.read_text())
    source["classes"]["DatasetCollection"] = {"attributes": {
        "resources": {"range": "Dataset", "multivalued": True, "inlined_as_list": True}}}
    path.write_text(yaml.safe_dump(source))
    record_path = root / "record.yaml"
    record_path.write_text("resources:\n- title: Inner resource\n  creators:\n  - name: Dana\n")
    rewrite_roster(root, lambda d: d["pinned_files"].update({"record.yaml": support_plan.sha256(record_path.read_bytes())}))
    manifest = build(fixture, artifact_kind="collection", class_name="DatasetCollection")
    edge = next(t for t in manifest["targets"] if t["pointer"] == "/resources/0/creators/0")
    assert edge["fitness_mapping"]["pointer"] == "/resources"
    request = support_plan.materialize_request(output, edge["id"])
    payload = json.loads(request["messages"][0]["content"][1]["text"].split("\n\n", 1)[1])
    assert payload["context"]["containing_entity"]["pointer"] == "/resources/0"
    assert payload["artifact"]["root_class"] == "DatasetCollection"
    assert manifest["counts"]["fitness_top_level"] == 1


@pytest.mark.parametrize("text", ["vocabularies: []\n", "vocabularies: {terms: {}}\n",
                                "vocabularies: {terms: {x: null}}\n", "vocabularies: {}\nvocabularies: {}\n"])
def test_malformed_explicit_vocabulary_is_not_an_empty_authority(fixture, text):
    root, output = fixture
    vocabulary = root / "vocabulary.yaml"
    vocabulary.write_text(text)
    with pytest.raises(support_plan.PlanError, match="vocabulary"):
        build(fixture, vocabulary_path=vocabulary)
    assert not output.exists()
