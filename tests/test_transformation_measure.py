"""D105 secondary full-to-core leaf measurements, offline, 2026-11-09.

Synthetic projection payloads exercise typed lineage without claiming schema
validation. Three saved corpus pairs retain their actual current-rule outcome.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.d4d_pair_consistency import load_pair_schema
from data_sheets_schema.derive_core import derive_core
from data_sheets_schema import transformation_measure as subject
from data_sheets_schema import transformation_measure_io as io
from data_sheets_schema import transformation_receipts as legacy
from scripts.adhoc.d105_review_oracle_20261109 import oracle as review_oracle


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pair_schema():
    return load_pair_schema()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def leaves(value, path=""):
    """Independent JSON-pointer inventory, including structural empty leaves."""
    if isinstance(value, dict) and value:
        for key, child in value.items():
            token = key.replace("~", "~0").replace("/", "~1")
            yield from leaves(child, path + "/" + token)
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            yield from leaves(child, path + "/" + str(index))
    else:
        yield path


def rows(result):
    values = result["diagnostic"]["core_leaves"]
    by_path = {row["target_path"]: row for row in values}
    assert len(by_path) == len(values), "one measurement per target leaf"
    return by_path


def assert_inventory(result, core):
    by_path = rows(result)
    assert set(by_path) == set(leaves(core))
    diagnostic = result["diagnostic"]
    counts = diagnostic["counts"]
    assert counts["core_leaves"] == len(by_path)
    for status in ("matched", "mismatched", "unattributed", "entry_mismatched"):
        assert counts[status] == sum(row["status"] == status for row in by_path.values())
    for rule in ("copied", "normalised", "synthesised"):
        assert counts[rule] == sum(row["rule"] == rule for row in by_path.values())
    assert counts["dropped_full_leaves"] == len(diagnostic["dropped_full_leaves"])
    assert counts["missing_core_leaves"] == len(diagnostic["missing_core_leaves"])


def assert_separate(result):
    assert result["instrument"] == legacy.TRANSFORMATION_RECEIPT_INSTRUMENT
    assert result["scope"]["secondary"] is True
    assert result["scope"]["gating"] is False
    assert result["scope"]["primary_receipt_instrument"] == "v4"

    assert result["diagnostic"]["format"] == "d105-full-to-core-leaf-lineage-v1"
    assert result["diagnostic"]["not_an_instrument"] is True
    instruments = []

    def visit(value):
        if isinstance(value, dict):
            assert "receipts" not in value and "tool_receipts" not in value
            if "instrument" in value:
                instruments.append(value["instrument"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(result)
    assert instruments == [legacy.TRANSFORMATION_RECEIPT_INSTRUMENT]


def assert_primary_receipt(result, full, core, pair_schema):
    """Compare against the existing emitter/verifier, independently of measure."""
    expected = legacy.emit_transformation_receipt(full, core, pair_schema=pair_schema)
    assert {key: result[key] for key in expected} == expected
    checked = legacy.verify_transformation_receipt(full, core, expected, pair_schema=pair_schema)
    assert checked["instrument"] == result["instrument"]
    assert result["verification_result"] == {key: value for key, value in checked.items() if key != "instrument"}
    assert_separate(result)


def assert_review_oracle(result, full, pair_schema):
    expected = review_oracle(full, pair_schema)
    assert set(expected) == set(leaves(derive_core(full, pair_schema)))
    matched = [row for row in result["diagnostic"]["core_leaves"] if row["status"] == "matched"]
    assert matched
    for row in matched:
        # The oracle describes deterministic target coordinates. A relocated
        # observed object explicitly identifies its expected coordinate.
        target = row.get("expected_path", row["target_path"])
        assert (row["rule"], row["source_paths"]) == expected[target], target


def test_independent_review_oracle_matches_synthetic_nested_case(pair_schema):
    # Retained from the review's independent_oracle.py rather than generated
    # from the production diagnostic's mapping or path-map implementation.
    full = {"id": "ex:n", "title": "T", "resources": [
        "junk", {"id": "ex:a", "title": "A", "resources": [None, {
            "id": "ex:aa", "name": "AA", "file_collections": [{"id": "ex:aafc", "total_bytes": 3,
                "resources": [{"id": "ex:f", "md5": "m"}]}]}],
            "file_collections": [{"name": "c", "resources": [None, {"format": "CSV"}]}]},
        {"unknown": 1}, {"id": "ex:a", "title": "A2", "file_collections": [
            {"id": "ex:last", "total_bytes": 9}]}],
        "file_collections": [{"total_bytes": 0}, {"id": "ex:fc", "resources": [
            {"id": "ex:f1", "dialect": {"d": ","}}, {"id": "ex:f2", "dialect": {"d": ","}}]}]}
    core = derive_core(full, pair_schema)
    result = subject.measure(full, core, pair_schema=pair_schema)
    assert result["diagnostic"]["matches_derived_core"] is True
    assert result["diagnostic"]["counts"]["matched"] == len(review_oracle(full, pair_schema))
    assert_review_oracle(result, full, pair_schema)
    assert_inventory(result, core)
    assert_primary_receipt(result, full, core, pair_schema)


def test_primary_uses_actual_legacy_emitter_then_verifier(pair_schema, monkeypatch):
    full = {"id": "example:primary", "title": "Original receipt identity"}
    core = derive_core(full, pair_schema)
    emit, verify = legacy.emit_transformation_receipt, legacy.verify_transformation_receipt
    events, receipts = [], []

    def observed_emit(*args, **kwargs):
        events.append("emit")
        receipt = emit(*args, **kwargs)
        receipts.append(receipt)
        return receipt

    def observed_verify(*args, **kwargs):
        assert receipts and any(value is receipts[0] for value in args[:3])
        events.append("verify")
        return verify(*args, **kwargs)

    monkeypatch.setattr(legacy, "emit_transformation_receipt", observed_emit)
    monkeypatch.setattr(legacy, "verify_transformation_receipt", observed_verify)
    result = subject.measure(full, core, pair_schema=pair_schema)
    assert events == ["emit", "verify"]
    expected = emit(full, core, pair_schema=pair_schema)
    checked = verify(full, core, expected, pair_schema=pair_schema)
    assert {key: result[key] for key in expected} == expected
    assert result["verification_result"] == {key: value for key, value in checked.items() if key != "instrument"}
    assert_separate(result)


def test_copied_leaf_inventory_is_typed_escaped_deterministic_and_secondary(pair_schema):
    # Deliberately unvalidated projection payload: preservation is not a claim
    # that a mapping-valued description satisfies the schema's description type.
    full = {"id": "example:dataset", "title": "α title\nsecond line", "description": {
        "a/b": {"~key": False}, "": [0, None, [], {}]}, "keywords": ["one", "two"]}
    core = derive_core(full, pair_schema)
    before_full, before_core = encoded(full), encoded(core)
    result = subject.measure(full, core, pair_schema=pair_schema)
    assert encoded(result) == encoded(subject.measure(full, core, pair_schema=pair_schema))
    assert encoded(full) == before_full and encoded(core) == before_core
    assert result["diagnostic"]["matches_derived_core"] is True
    assert_inventory(result, core)
    assert_primary_receipt(result, full, core, pair_schema)
    by_path = rows(result)
    for path in ("/title", "/description/a~1b/~0key", "/description//0",
                 "/description//1", "/description//2", "/description//3", "/keywords/1"):
        assert by_path[path]["status"] == "matched"
        assert by_path[path]["rule"] == "copied"
        assert by_path[path]["source_paths"] == [path]
        assert isinstance(by_path[path]["operation"], str) and by_path[path]["operation"]
    for path in ("/conforms_to_class", "/conforms_to_schema"):
        assert by_path[path]["rule"] == "synthesised"
        assert by_path[path]["source_paths"] == []


@pytest.mark.parametrize("original,replacement", [(False, 0), (0, False), (0, 0.0), (None, "None")])
def test_equal_python_values_do_not_mask_typed_target_mismatch(pair_schema, original, replacement):
    full = {"id": "example:dataset", "description": {"value": original}}
    core = derive_core(full, pair_schema)
    core["description"]["value"] = replacement
    result = subject.measure(full, core, pair_schema=pair_schema)
    row = rows(result)["/description/value"]
    assert result["diagnostic"]["matches_derived_core"] is False
    assert result["diagnostic"]["input_digests"]["core"] != result["diagnostic"]["input_digests"]["expected_core"]
    assert row["status"] == "mismatched"
    assert row["rule"] is None and row["source_paths"] == []
    assert_inventory(result, core)
    assert_primary_receipt(result, full, core, pair_schema)


@pytest.mark.parametrize("original,replacement", [(["same"], {"0": "same"}),
                                                  ({"0": "same"}, ["same"])])
def test_equal_pointer_and_value_do_not_hide_parent_shape_change(pair_schema, original, replacement):
    full = {"id": "example:shape", "description": original}
    core = derive_core(full, pair_schema)
    core["description"] = replacement
    result = subject.measure(full, core, pair_schema=pair_schema)
    row = rows(result)["/description/0"]
    assert result["diagnostic"]["matches_derived_core"] is False
    assert row["status"] == "mismatched"
    assert row["rule"] is None and row["source_paths"] == []
    assert_inventory(result, core)


def test_collection_and_file_distribution_lineage_uses_actual_filtered_positions(pair_schema):
    full = {"id": "example:dataset", "file_collections": [
        None, {"collection_type": "not projected"},
        {"id": "example:collection", "bytes": 999, "total_bytes": 0,
         "collection_type": "processed", "resources": [
             None, {"unknown": "not projected"},
             {"id": "example:file", "bytes": 4, "sha256": "a" * 64}]}]}
    core = derive_core(full, pair_schema)
    assert core["distributions"][0]["bytes"] == 0
    assert core["distributions"][1]["bytes"] == 4
    result = subject.measure(full, core, pair_schema=pair_schema)
    by_path = rows(result)
    assert by_path["/distributions/0/bytes"]["rule"] == "normalised"
    assert by_path["/distributions/0/bytes"]["source_paths"] == ["/file_collections/2/total_bytes"]
    assert by_path["/distributions/1/bytes"]["rule"] == "copied"
    assert by_path["/distributions/1/bytes"]["source_paths"] == ["/file_collections/2/resources/2/bytes"]
    assert by_path["/distributions/1/sha256"]["source_paths"] == ["/file_collections/2/resources/2/sha256"]
    dropped = {row["source_path"]: row for row in result["diagnostic"]["dropped_full_leaves"]}
    for path in ("/file_collections/2/bytes", "/file_collections/2/collection_type"):
        assert dropped[path]["rule"] == "dropped"
    assert result["diagnostic"]["matches_derived_core"] is True
    assert_inventory(result, core)


def test_nested_resource_identity_and_last_duplicate_distribution_source_are_distinct(pair_schema):
    full = {"id": "example:dataset", "resources": [None,
        {"id": "example:duplicate", "title": "first", "file_collections": [
            {"id": "example:first", "total_bytes": 1}]},
        {"id": "example:duplicate", "title": "last", "file_collections": [
            {"id": "example:last", "total_bytes": 7}]}]}
    core = derive_core(full, pair_schema)
    assert [item["title"] for item in core["resources"]] == ["first", "last"]
    assert [item["distributions"][0]["bytes"] for item in core["resources"]] == [7, 7]
    result = subject.measure(full, core, pair_schema=pair_schema)
    by_path = rows(result)
    assert by_path["/resources/0/title"]["source_paths"] == ["/resources/1/title"]
    assert by_path["/resources/1/title"]["source_paths"] == ["/resources/2/title"]
    for index in (0, 1):
        assert by_path[f"/resources/{index}/distributions/0/bytes"]["source_paths"] == [
            "/resources/2/file_collections/0/total_bytes"]
    assert result["diagnostic"]["matches_derived_core"] is True
    assert_inventory(result, core)


def reordered_pair(kind, pair_schema):
    """Review C2/C3: different entities with equal-valued sibling properties."""
    if kind == "resources":
        full = {"id": "ex:c2", "resources": [
            {"id": "ex:x", "title": "X", "license": "CC-BY-4.0", "version": "1"},
            {"id": "ex:y", "title": "Y", "license": "CC-BY-4.0", "version": "1"}]}
        core = derive_core(full, pair_schema)
        core["resources"].reverse()
        return full, core, "resources", 0, "/resources/1", "/resources/1", "license"
    full = {"id": "ex:c3", "file_collections": [{"id": "ex:fc", "resources": [
        {"id": "ex:f1", "format": "CSV", "media_type": "text/csv", "md5": "1" * 32},
        {"id": "ex:f2", "format": "CSV", "media_type": "text/csv", "md5": "2" * 32}]}]}
    core = derive_core(full, pair_schema)
    first, second = core["distributions"][1:]
    core["distributions"][1:] = [second, first]
    return full, core, "distributions", 1, "/distributions/2", "/file_collections/0/resources/1", "format"


@pytest.mark.parametrize("kind", ["resources", "distributions"])
def test_review_c2_c3_reordered_objects_claim_only_their_own_entity(pair_schema, kind):
    full, core, collection, index, expected, source, shared_key = reordered_pair(kind, pair_schema)
    result = subject.measure(full, core, pair_schema=pair_schema)
    prefix = f"/{collection}/{index}"
    measured = rows(result)
    for suffix in leaves(core[collection][index]):
        row = measured[prefix + suffix]
        assert row["status"] == "matched"
        assert row["source_paths"] == [source + suffix]
        assert row["expected_path"] == expected + suffix
        assert row["moved_from"] == expected
    assert measured[prefix + "/" + shared_key]["source_paths"] != [prefix + "/" + shared_key]
    assert result["diagnostic"]["matches_derived_core"] is False
    assert_inventory(result, core)
    assert_primary_receipt(result, full, core, pair_schema)


@pytest.mark.parametrize("kind", ["resources", "distributions"])
@pytest.mark.parametrize("damage", ["id", "value", "missing", "extra"])
def test_one_damaged_object_withholds_all_equal_sibling_claims(pair_schema, kind, damage):
    full, core, collection, index, _, _, shared_key = reordered_pair(kind, pair_schema)
    entry = core[collection][index]
    if damage == "id":
        entry["id"] = "ex:unregistered-entity"
    elif damage == "value":
        entry[shared_key] = "corrupted value"
    elif damage == "missing":
        del entry[shared_key]
    else:
        entry["extra"] = entry[shared_key]
    result = subject.measure(full, core, pair_schema=pair_schema)
    prefix = f"/{collection}/{index}"
    affected = [row for path, row in rows(result).items() if path.startswith(prefix + "/")]
    assert affected
    assert all(row["status"] == "entry_mismatched" for row in affected)
    assert all(row["rule"] is None and row["source_paths"] == [] for row in affected)
    assert rows(result)["/conforms_to_class"]["status"] == "matched"
    assert_inventory(result, core)


@pytest.mark.parametrize("damage", ["swap", "one_value"])
def test_duplicate_ids_do_not_authorize_relocation_or_partial_object_claims(pair_schema, damage):
    full = {"id": "ex:duplicates", "resources": [
        {"id": "ex:same", "title": "First", "license": "CC-BY-4.0"},
        {"id": "ex:same", "title": "Second", "license": "CC-BY-4.0"}]}
    core = derive_core(full, pair_schema)
    if damage == "swap":
        core["resources"].reverse()
    else:
        core["resources"][0]["title"] = "Changed"
    result = subject.measure(full, core, pair_schema=pair_schema)
    by_path = rows(result)
    affected = (0, 1) if damage == "swap" else (0,)
    for index in affected:
        for suffix in leaves(core["resources"][index]):
            row = by_path[f"/resources/{index}" + suffix]
            assert row["status"] == "entry_mismatched"
            assert row["rule"] is None and row["source_paths"] == []
    if damage == "one_value":
        assert by_path["/resources/1/license"]["source_paths"] == ["/resources/1/license"]
    assert_inventory(result, core)


@pytest.mark.parametrize("damage", ["value", "reorder"])
def test_nested_entry_change_withholds_claims_from_its_ancestor_object(pair_schema, damage):
    full = {"id": "ex:nested", "resources": [{"id": "ex:parent", "title": "Parent", "resources": [
        {"id": "ex:child1", "title": "One", "license": "CC-BY-4.0"},
        {"id": "ex:child2", "title": "Two", "license": "CC-BY-4.0"}]}]}
    core = derive_core(full, pair_schema)
    if damage == "value":
        core["resources"][0]["resources"][0]["title"] = "Corrupted child"
    else:
        core["resources"][0]["resources"].reverse()
    result = subject.measure(full, core, pair_schema=pair_schema)
    descendants = [row for path, row in rows(result).items() if path.startswith("/resources/0/")]
    assert descendants
    assert all(row["status"] == "entry_mismatched" for row in descendants)
    assert all(row["rule"] is None and row["source_paths"] == [] for row in descendants)
    assert_inventory(result, core)


def test_consensus_dialect_names_every_contributor_and_disagreement_is_dropped(pair_schema):
    full = {"id": "example:dataset", "file_collections": [{"id": "example:collection", "resources": [
        {"id": "example:f1", "dialect": {"delimiter": ",", "header": False}},
        {"id": "example:f2", "dialect": {"delimiter": ",", "header": False}}]}]}
    core = derive_core(full, pair_schema)
    result = subject.measure(full, core, pair_schema=pair_schema)
    for leaf in ("delimiter", "header"):
        row = rows(result)["/dialect/" + leaf]
        assert row["rule"] == "normalised"
        assert row["source_paths"] == [
            f"/file_collections/0/resources/{index}/dialect/{leaf}" for index in (0, 1)]
    full["file_collections"][0]["resources"][1]["dialect"]["delimiter"] = "\t"
    core = derive_core(full, pair_schema)
    assert "dialect" not in core
    result = subject.measure(full, core, pair_schema=pair_schema)
    dropped = {row["source_path"] for row in result["diagnostic"]["dropped_full_leaves"]}
    assert "/file_collections/0/resources/0/dialect/delimiter" in dropped
    assert "/file_collections/0/resources/1/dialect/delimiter" in dropped
    assert_inventory(result, core)


def test_observed_missing_and_extra_leaves_do_not_change_expected_drop_ledger(pair_schema):
    full = {"id": "example:dataset", "title": "source title", "description": "source title"}
    expected = derive_core(full, pair_schema)
    correct = subject.measure(full, expected, pair_schema=pair_schema)
    actual = deepcopy(expected)
    del actual["title"]
    actual["unsupported"] = "source title"
    actual["description"] = "unrelated text"
    result = subject.measure(full, actual, pair_schema=pair_schema)
    assert result["diagnostic"]["matches_derived_core"] is False
    assert "/title" in {row["target_path"] for row in result["diagnostic"]["missing_core_leaves"]}
    assert result["diagnostic"]["dropped_full_leaves"] == correct["diagnostic"]["dropped_full_leaves"]
    by_path = rows(result)
    assert by_path["/unsupported"]["status"] == "unattributed"
    assert by_path["/description"]["status"] == "mismatched"
    for path in ("/unsupported", "/description"):
        assert by_path[path]["rule"] is None and by_path[path]["source_paths"] == []
    assert_inventory(result, actual)


def test_stale_pair_schema_is_recaptured_before_projection_and_basis_pinning(tmp_path, monkeypatch):
    folder = tmp_path / "src/data_sheets_schema/schema"
    folder.mkdir(parents=True)
    full_path = folder / "data_sheets_schema_all.yaml"
    core_path = folder / "data_sheets_schema_core_all.yaml"
    for destination in (full_path, core_path):
        destination.write_bytes((ROOT / "src/data_sheets_schema/schema" / destination.name).read_bytes())
    stale = load_pair_schema(full_path, core_path)
    old_description = stale.full_view.schema.description
    full = {"id": "example:stale-schema", "title": "Unchanged projection"}
    core = derive_core(full, stale)
    previous_raw = full_path.read_bytes()
    changed = yaml.safe_load(previous_raw)
    fresh_description = "Synthetic newly saved full-schema description for the D105 stale-view regression."
    assert old_description != fresh_description
    changed["description"] = fresh_description
    full_path.write_text(yaml.safe_dump(changed, sort_keys=False, allow_unicode=True), encoding="utf-8")
    changed_raw = full_path.read_bytes()
    assert changed_raw != previous_raw
    assert stale.full_view.schema.description == old_description

    # Keep the real mapping validator: its relative schema declarations now
    # identify these two scratch copies. Copy the exact mapping bytes too, so
    # every selected input is explicit and the source specification stays intact.
    mapping_raw = subject.legacy.DEFAULT_MAPPING_PATH.read_bytes()
    mapping_path = tmp_path / subject.legacy.DEFAULT_MAPPING_PATH.relative_to(ROOT)
    mapping_path.parent.mkdir(parents=True)
    mapping_path.write_bytes(mapping_raw)
    # This case isolates stale-view recapture within one coherent fixture
    # checkout. Separate CLI tests exercise genuine foreign-root refusals.
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "data-sheets-schema"\n', encoding="utf-8")
    monkeypatch.setattr(subject.legacy, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(subject.legacy, "DEFAULT_MAPPING_PATH", mapping_path)
    monkeypatch.setattr(subject.resources, "CHECKOUT_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    original_emit = subject.legacy.emit_transformation_receipt
    observed = []

    def inspect_fresh_view(document, core=None, *, pair_schema=None, **kwargs):
        assert pair_schema is not stale
        assert pair_schema.full_view.schema.description == fresh_description
        assert pair_schema.full_view.schema.description != old_description
        observed.append(pair_schema.full_view.schema.description)
        return original_emit(document, core, pair_schema=pair_schema, **kwargs)

    monkeypatch.setattr(subject.legacy, "emit_transformation_receipt", inspect_fresh_view)
    result = subject.measure(full, core, pair_schema=stale)
    assert observed and all(value == fresh_description for value in observed)
    assert result["basis"]["schemas"]["full"]["sha256"] == hashlib.sha256(changed_raw).hexdigest()
    assert result["basis"]["schemas"]["full"]["sha256"] != hashlib.sha256(previous_raw).hexdigest()
    assert result["diagnostic"]["matches_derived_core"] is True
    assert full_path.read_bytes() == changed_raw
    assert mapping_path.read_bytes() == mapping_raw
    assert stale.full_view.schema.description == old_description
    assert_inventory(result, core)


@pytest.mark.corpus
@pytest.mark.parametrize("project,label", [
    ("CHORUS", "2026-09-04f_claude-opus-5-api-generic-v8_rep2"),
    ("VOICE", "2026-09-04f_claude-opus-5-api-generic-v8_rep2"),
    ("CM4AI", "2026-09-04g_claude-opus-5-api-generic-v8_rep2"),
])
def test_saved_corpus_pair_is_measured_without_rewriting_or_assuming_current_parity(
        pair_schema, project, label, tmp_path, record_property):
    full_path = ROOT / "data/d4d_concatenated/claudecode_api" / label / f"{project}_d4d.yaml"
    core_path = ROOT / "data/d4d_concatenated/claudecode_api_core" / label / f"{project}_d4d_core.yaml"
    full_raw, core_raw = full_path.read_bytes(), core_path.read_bytes()
    (full, full_sha), (core, core_sha) = io.read_record(full_path), io.read_record(core_path)
    assert full_sha == hashlib.sha256(full_raw).hexdigest()
    assert core_sha == hashlib.sha256(core_raw).hexdigest()
    before_full, before_core = deepcopy(full), deepcopy(core)
    result = subject.measure(full, core, pair_schema=pair_schema)
    repeated = subject.measure(full, core, pair_schema=pair_schema)
    assert encoded(result) == encoded(repeated)
    assert full == before_full and core == before_core
    assert full_path.read_bytes() == full_raw and core_path.read_bytes() == core_raw
    assert type(result["diagnostic"]["matches_derived_core"]) is bool
    assert_inventory(result, core)
    assert_primary_receipt(result, full, core, pair_schema)
    assert_review_oracle(result, full, pair_schema)
    artifact = tmp_path / f"{project}_transformation_measure.json"
    artifact.write_text(encoded(result) + "\n", encoding="utf-8")
    assert artifact.stat().st_size > 0
    assert json.loads(artifact.read_text(encoding="utf-8")) == result
    record_property("project", project)
    record_property("transformation_counts", encoded(result["diagnostic"]["counts"]))
    record_property("matches_current_derived_core", result["diagnostic"]["matches_derived_core"])
