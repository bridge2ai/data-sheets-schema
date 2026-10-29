"""Offline causal blinding regressions for review findings F3, F4 and F9."""
import pytest
import yaml
from data_sheets_schema.evaluation import blind_review_pack as pack
from tests.test_registered_eval_runner import registration, no_provider, rebind_record, runner


@pytest.mark.parametrize("identity", ["v10", "generic_v10", "claudecode_api"])
def test_f3_declared_comparison_identities_cannot_leak(registration, tmp_path, identity):
    inputs = rebind_record(registration, tmp_path,
                          f'id: example:data\ndescription: Generated under {identity}.\n'.encode())
    with pytest.raises(ValueError, match="generation identity"):
        runner.prepare(**inputs)


def test_f3_input_condition_is_not_a_comparison_identity(registration, tmp_path):
    raw = b'id: example:data\ndescription: "BASELINE (input documents only) analysis is scientific content."\n'
    inputs = rebind_record(registration, tmp_path, raw)
    selected = runner.prepare(**inputs)
    assert yaml.safe_load(selected.blinded) == yaml.safe_load(raw)


def test_f4_structure_and_size_separability_are_private(tmp_path):
    records = []
    scientific = []
    for arm, value in (("first", {"id": "example:data", "title": "Retained scientific title", "nested": {"value": 3}}),
                       ("second", {"id": "example:data"})):
        path = tmp_path / f"{arm}.yaml"
        path.write_text(yaml.safe_dump(value))
        records.append(pack.Record(arm, "EXTERNAL", f"secret-{arm}-label", path))
        scientific.append(value)
    output = tmp_path / "review"
    key = pack.build_blind_review_pack(records, output, key_output=tmp_path / "key.json", seed=123, cohort="synthetic")
    by_arm = {r["arm"]: r for r in key["records"]}
    first = by_arm["first"]["fingerprint_diagnostics"]
    assert first["top_level_slots"] == ["id", "nested", "title"]
    assert first["key_path_count"] == 4
    assert first["blinded_bytes"] == len((output / (by_arm["first"]["blind_id"] + ".yaml")).read_bytes())
    comparison = key["structural_separability"]["EXTERNAL"]["comparisons"][0]
    assert comparison["key_path_separable"] is True
    assert comparison["size_ranges_overlap"] is False
    assert "structure" in key["residual_fingerprint_notice"] and "size" in key["residual_fingerprint_notice"]
    assert {p.name for p in output.iterdir()} == {"blind_01.yaml", "blind_02.yaml", "review_sheet.tsv"}
    assert sorted((yaml.safe_load(p.read_bytes()) for p in output.glob("*.yaml")), key=len) == sorted(scientific, key=len)
