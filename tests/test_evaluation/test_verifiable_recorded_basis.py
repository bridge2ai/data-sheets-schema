"""Historical token denominators and source bytes must stay independently bound."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import verifiable as vf
from data_sheets_schema.cli.evaluate import evaluate
from data_sheets_schema.run_schema import TODAY

ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_SHA = "533f561ba3c85a31486ff2ff962be83555a9d81ac57a0891aaf39b411d283f4b"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def schema_bytes(*, grantor="Grantor", citation="string", root="Dataset"):
    return yaml.safe_dump({
        "id": "https://example.org/neutral-schema", "name": "neutral",
        "prefixes": {"linkml": "https://w3id.org/linkml/"}, "imports": ["linkml:types"],
        "default_range": "string",
        "slots": {"id": {"identifier": True}, "description": {}, "name": {},
                  "grantor": {"range": grantor}, "citation": {"range": citation}},
        "classes": {root: {"slots": ["id", "description", "grantor", "citation"]},
                    "Grantor": {"slots": ["id", "name"]}},
    }).encode()


def fixture(tmp_path, *, raw=None, document=None, source=None, kind="full"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    schema = tmp_path / "schema.yaml"
    schema.write_bytes(raw or schema_bytes(root="CoreDataset" if kind == "core" else "Dataset"))
    bundle = tmp_path / "source.txt"
    bundle.write_bytes(source or b"Released on 2026-01-01.\n")
    record = tmp_path / "EXAMPLE_d4d.yaml"
    record.write_text(yaml.safe_dump(document or {"id": "example:dataset", "description": "Released on 2026-01-01.",
                                                "grantor": "https://example.invalid/constructed"}))
    provenance = tmp_path / "EXAMPLE_provenance.yaml"
    data = {"schema": {f"{kind}_path": str(schema), f"{kind}_sha256": sha(schema.read_bytes())},
            "inputs": {"bundle_path": str(bundle), "bundle_sha256": sha(bundle.read_bytes()),
                       "bundle_md5": hashlib.md5(bundle.read_bytes()).hexdigest()}}
    provenance.write_text(yaml.safe_dump(data))
    return SimpleNamespace(record=record, provenance=provenance, schema=schema, bundle=bundle, data=data, kind=kind)


def measure(case, **kw):
    paths = (case.record, case.provenance, case.schema, case.bundle)
    before = {str(path): path.read_bytes() for path in paths if path.exists()}
    result = vf.check_run(case.record, case.provenance, kind=case.kind, project="EXAMPLE", label="neutral", **kw)
    assert before == {str(path): path.read_bytes() for path in paths if path.exists()}
    return result


def update(case):
    case.provenance.write_text(yaml.safe_dump(case.data))


def test_actual_historical_grantor_exemption_restores_denominator_without_rewriting(tmp_path):
    # Public merged schema copied byte-for-byte from git commit 88142c4fc0bbc2d...
    raw = gzip.decompress((ROOT / "tests/fixtures/verifiable/historical_full_88142c4.yaml.gz").read_bytes())
    assert sha(raw) == HISTORICAL_SHA
    case = fixture(tmp_path, raw=raw, document={"id": "example:dataset", "description": "Released on 2026-01-01.",
                                              "funders": [{"grantor": "https://example.invalid/constructed"}]})
    unchanged_hash = sha(case.record.read_bytes())
    current = vf.check_record(yaml.safe_load(case.record.read_bytes()), case.bundle.read_text())
    assert (current.stated, current.grounded) == (2, 1)
    historical = measure(case)
    assert historical["checked"] is True
    assert (historical["stated"], historical["grounded"], historical["rate"]) == (1, 1, 1.0)
    assert historical["record_sha256"] == unchanged_hash
    assert historical["schema_basis"]["actual_sha256"] == HISTORICAL_SHA
    assert historical["schema_basis"]["status"] == historical["source_basis"]["status"] == "recorded"


def test_opposite_schema_decisions_are_per_run_and_nested_assertions_remain(tmp_path):
    doc = {"id": "example:d", "description": "Released on 2026-01-01.",
           "grantor": "https://example.invalid/grantor", "citation": "https://example.invalid/citation"}
    a = measure(fixture(tmp_path / "a", document=doc))
    b = measure(fixture(tmp_path / "b", raw=schema_bytes(grantor="string", citation="Grantor"), document=doc))
    assert [c["slot"] for c in a["claims"] if not c["grounded"]] == ["citation"]
    assert [c["slot"] for c in b["claims"] if not c["grounded"]] == ["grantor"]
    assert a["schema_basis"]["actual_sha256"] != b["schema_basis"]["actual_sha256"]
    doc["grantor"] = {"name": "https://example.invalid/unattested-name"}
    c = measure(fixture(tmp_path / "nested", document=doc))
    assert any(claim["slot"] == "name" and not claim["grounded"] for claim in c["claims"])


def test_core_uses_its_own_captured_schema(tmp_path):
    case = fixture(tmp_path, kind="core", raw=schema_bytes(grantor="string", root="CoreDataset"))
    case.data["schema"].update(full_path="/no/current/full.yaml", full_sha256="0" * 64)
    update(case)
    result = measure(case)
    assert result["checked"] and result["stated"] == 2
    assert result["schema_basis"]["kind"] == "core"
    assert result["schema_basis"]["actual_sha256"] == sha(case.schema.read_bytes())


@pytest.mark.parametrize("why", ["the record names no merged schema by path and hash", "no committed version matches"])
def test_unrecoverable_schema_fallback_is_current_and_hashed(tmp_path, monkeypatch, why):
    case = fixture(tmp_path)
    current = tmp_path / "current.yaml"
    current.write_bytes(schema_bytes(grantor="string"))
    monkeypatch.setattr(vf, "FULL_SCHEMA", current)
    with patch("data_sheets_schema.run_schema.run_schema_bytes", return_value=(None, {"source": TODAY, "reason": why})):
        result = measure(case)
    assert result["checked"] and result["stated"] == 2
    assert result["schema_basis"]["status"] == "current_fallback"
    assert result["schema_basis"]["actual_sha256"] == sha(current.read_bytes())
    assert result["schema_basis"]["reason"] == why


@pytest.mark.parametrize("raw", [b"[not, a, schema]\n", schema_bytes(root="WrongRoot"), b"id: example:x\nname: bad\nclasses:\n  Dataset:\n    is_a: MissingClass\n"])
def test_unusable_recovered_authority_is_not_a_current_success(tmp_path, raw):
    case = fixture(tmp_path, raw=raw)
    result = measure(case)
    assert result["checked"] is False and result["stated"] is None
    assert result["rate"] is None and "reason" in result


def test_schema_capture_survives_path_mutation(tmp_path):
    case = fixture(tmp_path)
    captured = case.schema.read_bytes()
    def select(*args, **kw):
        case.schema.write_bytes(schema_bytes(grantor="string"))
        return captured, {"source": "the run's schema, on disk"}
    with patch("data_sheets_schema.run_schema.run_schema_bytes", side_effect=select):
        result = vf.check_run(case.record, case.provenance)
    assert result["checked"] and result["stated"] == 1
    assert result["schema_basis"]["actual_sha256"] == sha(captured)
    assert result["schema_basis"]["actual_sha256"] != sha(case.schema.read_bytes())


def test_changed_bundle_recovers_pinned_bytes_not_current_support(tmp_path):
    case = fixture(tmp_path, source=b"Released on 2025-01-01.\n")
    original = case.bundle.read_bytes()
    case.bundle.write_text("Released on 2026-01-01.\n")
    with patch("data_sheets_schema.provenance.bundle_bytes_for", return_value=(original, {"commit": "a" * 40, "matched_on": ["md5", "sha256"]})) as recover:
        result = measure(case)
    assert recover.call_count == 1
    assert result["checked"] and (result["grounded"], result["stated"], result["rate"]) == (0, 1, 0.0)
    assert result["source_basis"]["actual_sha256"] == sha(original)
    assert result["source_basis"]["source"] == "git blob"


def test_unrecoverable_pinned_source_is_unchecked(tmp_path):
    case = fixture(tmp_path, source=b"Released on 2025-01-01.\n")
    case.bundle.write_text("Released on 2026-01-01.\n")
    with patch("data_sheets_schema.provenance.bundle_bytes_for", return_value=None):
        result = measure(case)
    assert result["checked"] is False
    assert result["grounded"] is result["stated"] is result["rate"] is None
    assert "recorded source unavailable" in result["reason"]


@pytest.mark.parametrize("fault", ["contradictory", "malformed_sha", "blank_md5", "no_path", "bad_section", "bad_decode"])
def test_invalid_source_authority_never_becomes_legacy_current(tmp_path, fault):
    case = fixture(tmp_path)
    if fault == "contradictory": case.data["inputs"]["bundle_md5"] = "0" * 32
    elif fault == "malformed_sha": case.data["inputs"]["bundle_sha256"] = True
    elif fault == "blank_md5": case.data["inputs"]["bundle_md5"] = ""
    elif fault == "no_path": case.data["inputs"].pop("bundle_path")
    elif fault == "bad_section": case.data["inputs"] = []
    else:
        case.bundle.write_bytes(b"\xff invalid UTF8")
        case.data["inputs"].update(bundle_md5=hashlib.md5(case.bundle.read_bytes()).hexdigest(), bundle_sha256=sha(case.bundle.read_bytes()))
    update(case)
    with patch("data_sheets_schema.provenance.bundle_bytes_for", return_value=None):
        result = measure(case)
    assert not result["checked"] and result["rate"] is None
    assert result["source_basis"] is None or result["source_basis"]["status"] != "legacy_current_unverified"


def test_recovery_result_is_rechecked_against_every_source_pin(tmp_path):
    case = fixture(tmp_path)
    with patch("data_sheets_schema.name_grounding.record_bundle_bytes", return_value=(b"substituted", {"source": "git blob"})):
        result = measure(case)
    assert not result["checked"] and "contradict" in result["reason"]


def test_source_capture_is_used_for_hash_decode_and_measurement(tmp_path):
    from data_sheets_schema.name_grounding import record_bundle_bytes
    case = fixture(tmp_path)
    original = case.bundle.read_bytes()
    def recover(*args):
        result = record_bundle_bytes(*args)
        case.bundle.write_text("Unrelated later contents.")
        return result
    with patch("data_sheets_schema.name_grounding.record_bundle_bytes", side_effect=recover):
        result = vf.check_run(case.record, case.provenance)
    assert result["checked"] and result["grounded"] == 1
    assert result["source_basis"]["actual_sha256"] == sha(original)
    assert result["source_basis"]["actual_sha256"] != sha(case.bundle.read_bytes())


def test_legacy_source_without_pins_has_explicit_unverified_basis(tmp_path):
    case = fixture(tmp_path)
    case.data["inputs"] = {"bundle_path": str(case.bundle)}
    update(case)
    result = measure(case)
    assert result["checked"] and result["grounded"] == 1
    assert result["source_basis"]["status"] == "legacy_current_unverified"
    assert result["source_basis"]["actual_sha256"] == sha(case.bundle.read_bytes())


def test_missing_provenance_has_two_explicit_fallbacks(tmp_path, monkeypatch):
    case = fixture(tmp_path)
    case.provenance.unlink()
    monkeypatch.setattr(vf, "FULL_SCHEMA", case.schema)
    result = measure(case, fallback_bundle=case.bundle)
    assert result["checked"]
    assert result["schema_basis"]["status"] == "current_fallback"
    assert result["source_basis"]["status"] == "legacy_current_unverified"
    assert result["provenance_sha256"] is None


@pytest.mark.parametrize("body", ["[]", "null", "schema: []", "schema:\n  full_sha256: false",
                                 "inputs: {}\ninputs: {}\n", "schema: {}\nschema: {}\n"])
def test_malformed_provenance_is_unchecked(tmp_path, body):
    case = fixture(tmp_path)
    case.provenance.write_text(body)
    result = measure(case)
    assert not result["checked"] and result["rate"] is None


def test_ambiguous_record_values_are_not_last_wins_grounding(tmp_path):
    case = fixture(tmp_path)
    case.record.write_text("description: Released on 2025-01-01.\ndescription: Released on 2026-01-01.\n")
    result = measure(case)
    assert not result["checked"] and "duplicate mapping key" in result["reason"]


def invoke(cases, *args):
    runs = [SimpleNamespace(method="claudecode_agent_core" if c.kind == "core" else "claudecode_agent",
                           label=str(i), projects=["EXAMPLE"], is_core=c.kind == "core", deterministic=False)
            for i, c in enumerate(cases)]
    with patch("data_sheets_schema.runs.discover", return_value=runs), \
         patch("data_sheets_schema.runs.record_path", side_effect=lambda method,label,project: cases[int(label)].record), \
         patch("data_sheets_schema.provenance.record_path_for", side_effect=lambda project,method,label: cases[int(label)].provenance):
        return CliRunner().invoke(evaluate, ["verifiable", "--project", "EXAMPLE", *args])


def test_cli_keeps_per_record_basis_and_unknown_rows_without_zero_scores(tmp_path):
    first = fixture(tmp_path / "first")
    second = fixture(tmp_path / "second", raw=schema_bytes(grantor="string"))
    broken = fixture(tmp_path / "broken")
    broken.data["inputs"]["bundle_sha256"] = "malformed"
    update(broken)
    result = invoke([first, second, broken], "--json")
    assert result.exit_code == 1, result.output
    rows = json.loads(result.output)["records"]
    assert [r["stated"] for r in rows] == [1, 2, None]
    assert rows[0]["schema_basis"]["actual_sha256"] != rows[1]["schema_basis"]["actual_sha256"]
    assert rows[2]["grounded"] is rows[2]["rate"] is None
    assert all(r["record_sha256"] == sha(c.record.read_bytes()) for r, c in zip(rows, [first, second, broken]))
    rendered = invoke([first, second, broken])
    assert rendered.exit_code == 1
    assert "UNCHECKED" in rendered.output and "2 measured record(s); 1 unchecked" in rendered.output
    assert "totals can combine different bases" in rendered.output
    assert sha(first.schema.read_bytes()) in rendered.output


def test_cli_honors_core_variant_and_exposes_legacy_source(tmp_path):
    case = fixture(tmp_path, kind="core")
    case.data["inputs"] = {"bundle_path": str(case.bundle)}
    update(case)
    result = invoke([case], "--method", "claudecode_agent_core", "--json")
    assert result.exit_code == 0, result.output
    row = json.loads(result.output)["records"][0]
    assert row["schema_basis"]["kind"] == "core"
    assert row["source_basis"]["status"] == "legacy_current_unverified"


def test_cli_does_not_silently_drop_missing_selected_record(tmp_path):
    case = fixture(tmp_path)
    run = SimpleNamespace(method="claudecode_agent", label="missing-neutral", projects=["EXAMPLE"],
                          is_core=False, deterministic=False)
    with patch("data_sheets_schema.runs.discover", return_value=[run]), \
         patch("data_sheets_schema.runs.record_path", return_value=None), \
         patch("data_sheets_schema.provenance.record_path_for", return_value=case.provenance):
        result = CliRunner().invoke(evaluate, ["verifiable", "--json"])
    assert result.exit_code == 1
    rows = json.loads(result.output)["records"]
    assert len(rows) == 1 and not rows[0]["checked"]
    assert rows[0]["rate"] is None and "FileNotFoundError" in rows[0]["reason"]


@pytest.mark.parametrize("placement", ["slot_usage", "attributes"])
@pytest.mark.parametrize("global_range,effective_range,stated", [
    ("string", "Grantor", 1), ("Grantor", "string", 2)])
def test_recorded_exclusion_uses_induced_owner_slot(tmp_path, placement, global_range, effective_range, stated):
    schema = yaml.safe_load(schema_bytes(grantor=global_range))
    schema["classes"]["Dataset"][placement] = {"grantor": {"range": effective_range}}
    result = measure(fixture(tmp_path, raw=yaml.safe_dump(schema).encode()))
    assert result["checked"] and result["stated"] == stated
    assert result["schema_basis"]["claim_exclusion_rule"] == "actual_owner_induced_slots_v1"


@pytest.mark.parametrize("global_range", ["Grantor", "string"])
@pytest.mark.parametrize("inheritance", ["is_a", "mixins"])
def test_same_name_resolves_separate_nested_and_inherited_owners(tmp_path, global_range, inheritance):
    schema = yaml.safe_load(schema_bytes(grantor=global_range))
    schema["classes"].update({
        "RefParent": {"slots": ["grantor"], "slot_usage": {"grantor": {"range": "Grantor"}}},
        "RefOwner": {inheritance: "RefParent" if inheritance == "is_a" else ["RefParent"]},
        "TextOwner": {"slots": ["grantor"], "slot_usage": {"grantor": {"range": "string"}}},
    })
    for name, owner in (("ref_items", "RefOwner"), ("text_items", "TextOwner")):
        schema["slots"][name] = {"range": owner, "multivalued": True, "inlined_as_list": True}
        schema["classes"]["Dataset"]["slots"].append(name)
    document = {"description": "Released on 2026-01-01.",
                "ref_items": [{"grantor": "https://example.invalid/reference"}],
                "text_items": [{"grantor": "https://example.invalid/literal"}]}
    result = measure(fixture(tmp_path, raw=yaml.safe_dump(schema).encode(), document=document))
    assert result["checked"], result
    assert (result["stated"], result["grounded"], result["rate"]) == (2, 1, 0.5)
    assert [c["value"] for c in result["claims"] if c["kind"] == "url"] == ["https://example.invalid/literal"]


@pytest.mark.parametrize("identifier", [True, False])
def test_local_identifier_override_controls_only_its_owner(tmp_path, identifier):
    schema = yaml.safe_load(schema_bytes(grantor="string"))
    schema["slots"]["grantor"]["identifier"] = not identifier
    schema["classes"]["Dataset"]["slot_usage"] = {"grantor": {"identifier": identifier}}
    result = measure(fixture(tmp_path, raw=yaml.safe_dump(schema).encode()))
    assert result["checked"]
    assert result["stated"] == (1 if identifier else 2)


def test_keyed_entities_and_mixed_references_use_the_declared_class(tmp_path):
    schema = yaml.safe_load(schema_bytes())
    schema["slots"].update({
        "keyed": {"range": "Grantor", "multivalued": True, "inlined": True, "inlined_as_list": False},
        "mixed": {"range": "Grantor", "multivalued": True, "inlined_as_list": True}})
    schema["classes"]["Dataset"]["slots"].extend(["keyed", "mixed"])
    document = {"description": "Released on 2026-01-01.",
                "keyed": {"https://example.invalid/key": {"name": "https://example.invalid/keyed-assertion"}},
                "mixed": ["https://example.invalid/reference", {"name": "https://example.invalid/list-assertion"}]}
    result = measure(fixture(tmp_path, raw=yaml.safe_dump(schema).encode(), document=document))
    assert result["checked"] and (result["stated"], result["grounded"]) == (3, 1), result
    assert {c["value"] for c in result["claims"] if c["kind"] == "url"} == {
        "https://example.invalid/keyed-assertion", "https://example.invalid/list-assertion"}


@pytest.mark.parametrize("fault", ["unknown_slot", "scalar_container", "unknown_range", "union_range",
                                  "type_designator", "ancestor_rules", "unestablished_keyed_map"])
def test_unestablished_ownership_cannot_report_a_measurement(tmp_path, fault):
    schema = yaml.safe_load(schema_bytes())
    document = {"description": "Released on 2026-01-01.", "grantor": "https://example.invalid/reference"}
    if fault == "unknown_slot":
        document["unregistered"] = "https://example.invalid/assertion"
    elif fault == "scalar_container":
        document["description"] = {"id": "https://example.invalid/not-an-identifier-owner"}
    elif fault == "unknown_range":
        schema["slots"]["grantor"]["range"] = "MissingOwner"
    elif fault == "union_range":
        schema["slots"]["grantor"]["any_of"] = [{"range": "Grantor"}, {"range": "string"}]
    elif fault == "type_designator":
        schema["slots"]["grantor"]["designates_type"] = True
    elif fault == "ancestor_rules":
        schema["classes"]["Parent"] = {"rules": [{"preconditions": {"slot_conditions": {
            "description": {"value_presence": "PRESENT"}}}, "postconditions": {"slot_conditions": {
            "grantor": {"range": "string"}}}}]}
        schema["classes"]["Dataset"]["is_a"] = "Parent"
    else:
        schema["slots"]["grantor"].update(multivalued=True, inlined_as_list=True)
        document["grantor"] = {"arbitrary-key": {"name": "https://example.invalid/assertion"}}
    result = measure(fixture(tmp_path, raw=yaml.safe_dump(schema).encode(), document=document))
    assert not result["checked"] and result["stated"] is result["grounded"] is result["rate"] is None
    assert result["schema_basis"]["status"] == "recorded"


def test_low_level_legacy_explicit_global_exclusions_remain_available():
    document = {"first": {"grantor": "https://example.invalid/reference"},
                "second": {"grantor": "https://example.invalid/literal"}}
    assert vf.check_record(document, "", skip_slots={"grantor"}).stated == 0
    assert vf.check_record(document, "", skip_slots=set()).stated == 2
