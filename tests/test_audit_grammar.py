"""Synthetic drafting grammar, with an explicit source-blind boundary."""
import ast
import copy
import inspect
import json

import pytest

from data_sheets_schema import audit_grammar as grammar


def document():
    return {"source": "example.txt", "chunk": "c001", "quote": "A service is planned."}


def claim(*, verdict="revise"):
    return {"text": "The service is deployed.", "verdict": verdict, "attributed_to": [],
            "claim_status": "applied", "source_status": "planned" if verdict == "revise" else "applied",
            "evidence": [document()], "reason": "Synthetic reasoning authored in the draft."}


def audit():
    return {"findings": [{"severity": "medium", "record": "full", "slot": "description",
                         "issue": "Preserve the prospective scope.", "review_paths": ["/description"],
                         "evidence": [{"artifact": "original_full", "path": "/description",
                                       "op": "contains", "quote": "The service is deployed."}, document()]}],
            "summary": "One synthetic finding.",
            "source_review": {"artifact": "original_full", "sha256": "a" * 64,
                              "values": [{"path": "/description", "claims": [claim()]}]}}


def review_claim(value):
    return value["source_review"]["values"][0]["claims"][0]


def check(value):
    return grammar.check(json.dumps(value, ensure_ascii=False, allow_nan=False).encode())


def codes(report):
    return {entry["code"] for entry in report["errors"]}


def assert_bad(value, code):
    report = check(value)
    assert report["passed"] is False
    assert code in codes(report)
    return report


def test_minimal_draft_is_deterministic_and_not_modified():
    value = audit()
    raw = json.dumps(value).encode()
    before = bytes(raw)
    result = grammar.check(raw)
    assert result == {"instrument": "audit_grammar v1", "schema_version": 1,
                      "passed": True, "error_count": 0, "errors": [], "truncated": False}
    assert grammar.check(json.dumps(value, indent=4, sort_keys=True).encode()) == result
    assert raw == before


def test_zero_finding_and_empty_inventory_are_source_blind():
    value = audit()
    value["findings"] = []
    value["source_review"]["values"] = []
    assert check(value)["passed"]


@pytest.mark.parametrize("verdict", ["supported", "revise"])
@pytest.mark.parametrize("status", sorted(grammar.STATUSES))
def test_status_enums_and_supported_agreement(verdict, status):
    value = audit()
    item = review_claim(value)
    item.update(verdict=verdict, claim_status=status, source_status=status)
    if verdict == "supported":
        value["findings"] = []
    assert check(value)["passed"]
    if verdict == "supported":
        item["source_status"] = "unstated"
        assert_bad(value, "supported_status_mismatch")


def test_revise_unstated_and_empty_evidence_are_allowed():
    value = audit()
    review_claim(value).update(source_status="unstated", evidence=[])
    assert check(value)["passed"]
    review_claim(value)["verdict"] = "supported"
    report = assert_bad(value, "array_nonempty")
    assert "supported_status_mismatch" in codes(report)


@pytest.mark.parametrize("field,bad", [("verdict", "accept"), ("claim_status", "unstated"),
                                      ("source_status", "unknown"), ("verdict", {}),
                                      ("source_status", []), ("claim_status", False)])
def test_invalid_claim_enums_do_not_raise(field, bad):
    value = audit()
    review_claim(value)[field] = bad
    assert_bad(value, "enum_value")


@pytest.mark.parametrize("field,bad", [("severity", "critical"), ("record", "original_full"),
                                      ("record", "FULL"), ("record", []), ("severity", True),
                                      ("slot", []), ("issue", " ")])
def test_finding_types_and_exact_namespaces(field, bad):
    value = audit()
    value["findings"][0][field] = bad
    assert_bad(value, "text_nonempty" if field in {"slot", "issue"} else "enum_value")


@pytest.mark.parametrize("record", ["full", "core", "both"])
def test_all_finding_record_routes_are_grammar_valid(record):
    value = audit()
    value["findings"][0]["record"] = record
    assert check(value)["passed"]


@pytest.mark.parametrize("target", ["audit", "finding", "review", "row", "claim", "evidence"])
@pytest.mark.parametrize("mutation", ["extra", "missing", "non_object"])
def test_exact_object_shapes(target, mutation):
    value = audit()
    containers = {
        "audit": (None, None), "finding": (value["findings"], 0),
        "review": (value, "source_review"), "row": (value["source_review"]["values"], 0),
        "claim": (value["source_review"]["values"][0]["claims"], 0),
        "evidence": (review_claim(value)["evidence"], 0),
    }
    parent, key = containers[target]
    selected = value if parent is None else parent[key]
    if mutation == "extra":
        selected["NEVER_ECHO_SECRET_KEY"] = "NEVER_ECHO_SECRET_VALUE"
    elif mutation == "missing":
        del selected[next(iter(selected))]
    elif parent is None:
        value = []
    else:
        parent[key] = []
    report = check(value)
    assert not report["passed"]
    assert "NEVER_ECHO" not in json.dumps(report)


def test_metadata_alternative_is_structural_not_an_exemption_decision():
    value = audit()
    value["findings"] = []
    # The final inventory, not this parser, decides eligibility of this path.
    value["source_review"]["values"] = [{"path": "/invented/path", "metadata_reason": "Structure."}]
    assert check(value)["passed"]
    value["source_review"]["values"][0]["claims"] = [claim()]
    assert_bad(value, "object_keys")


def test_raw_revision_linkage_checks_both_directions_without_source_paths_in_output():
    value = audit()
    value["source_review"]["values"] += [
        {"path": "/SECRET_SUPPORTED_PATH", "claims": [claim(verdict="supported")]},
        {"path": "/SECRET_METADATA_PATH", "metadata_reason": "A structural declaration."},
        {"path": "/SECRET_REVISE_PATH", "claims": [claim()]},
    ]
    value["findings"][0]["review_paths"] += ["/SECRET_SUPPORTED_PATH", "/SECRET_METADATA_PATH", "/SECRET_UNKNOWN_PATH"]
    result = check(value)
    assert result["error_count"] == 4
    assert [e["code"] for e in result["errors"]].count("review_path_without_revise") == 3
    assert {"code": "revise_without_finding", "path": "/source_review/values/3"} in result["errors"]
    assert "SECRET" not in json.dumps(result)
    value["findings"][0]["review_paths"] = ["/description", "/SECRET_REVISE_PATH"]
    assert check(value)["passed"]


def test_duplicate_rows_and_empty_link_list_are_rejected():
    value = audit()
    value["source_review"]["values"] *= 2
    assert_bad(value, "duplicate_review_path")
    value = audit()
    value["findings"][0]["review_paths"] = []
    report = assert_bad(value, "array_nonempty")
    assert "revise_without_finding" in codes(report)


def test_supported_subclauses_do_not_prevent_linking_a_revised_value():
    value = audit()
    value["source_review"]["values"][0]["claims"].insert(0, claim(verdict="supported"))
    assert check(value)["passed"]


@pytest.mark.parametrize("pointer", ["/x~0y", "/x~1y", "/items/0/name", "/", "/01"])
def test_valid_pointer_syntax_does_not_infer_source_container_types(pointer):
    value = audit()
    value["source_review"]["values"][0]["path"] = pointer
    value["findings"][0]["review_paths"] = [pointer]
    assert check(value)["passed"]


@pytest.mark.parametrize("pointer", ["", "relative", "@header", "/bad~", "/bad~2", None, 1, [], {}])
def test_invalid_review_pointers(pointer):
    value = audit()
    value["source_review"]["values"][0]["path"] = pointer
    value["findings"][0]["review_paths"] = [pointer]
    assert_bad(value, "pointer_syntax")


@pytest.mark.parametrize("artifact", ["original_full", "original_core"])
@pytest.mark.parametrize("op", ["contains", "lacks"])
def test_finding_artifact_evidence_and_header_shape(artifact, op):
    value = audit()
    value["findings"][0]["evidence"][0].update(artifact=artifact, path="@header", op=op)
    assert check(value)["passed"]


@pytest.mark.parametrize("op", ["not_contains", None, ["contains"]])
def test_artifact_operator_enum(op):
    value = audit()
    value["findings"][0]["evidence"][0]["op"] = op
    assert_bad(value, "enum_value")


def provenance(field="effective_priority", value=2):
    return {"provenance": "source_manifest", "sha256": "b" * 64, "source_id": "example",
            "source": "example.txt", "field": field, "value": value}


@pytest.mark.parametrize("field,scalar", [("effective_priority", 99), ("priority_basis", "unranked"),
                                         ("priority_basis", "source_override"), ("priority_basis", "source_type"),
                                         ("source_type", "publication"), ("captured_at", "2030-01-01"),
                                         ("superseded_by", "another-source")])
def test_provenance_field_types_without_authority_comparison(field, scalar):
    value = audit()
    review_claim(value).update(claim_status="fact", source_status="fact", evidence=[provenance(field, scalar)])
    assert check(value)["passed"]


@pytest.mark.parametrize("field,scalar,code", [("effective_priority", True, "positive_integer_required"),
                                              ("effective_priority", 2.0, "positive_integer_required"),
                                              ("effective_priority", "2", "positive_integer_required"),
                                              ("effective_priority", 0, "positive_integer_required"),
                                              ("priority_basis", "manual", "enum_value"),
                                              ("source_id", "example", "enum_value"),
                                              ("captured_at", [], "text_nonempty")])
def test_invalid_provenance_fields(field, scalar, code):
    value = audit()
    review_claim(value).update(claim_status="fact", source_status="fact", evidence=[provenance(field, scalar)])
    assert_bad(value, code)


def test_evidence_routes_remain_distinct_and_attribution_typed():
    value = audit()
    item = review_claim(value)
    item.update(claim_status="fact", source_status="fact", evidence=[provenance(), document()])
    assert_bad(value, "object_keys")
    item["evidence"] = [provenance()]
    item["attributed_to"] = ["example.txt"]
    assert_bad(value, "provenance_attribution")
    item["attributed_to"] = []
    item["source_status"] = "planned"
    assert_bad(value, "provenance_status")
    item.update(evidence=[document()], source_status="fact", attributed_to=[{"source": "example.txt"}])
    assert_bad(value, "text_nonempty")
    item["attributed_to"] = ["example.txt", "example.txt"]
    assert_bad(value, "duplicate_attribution")
    item["attributed_to"] = "example.txt"
    assert_bad(value, "array_required")


def test_artifact_evidence_cannot_substitute_for_claim_source_evidence():
    value = audit()
    review_claim(value)["evidence"] = [value["findings"][0]["evidence"][0]]
    assert_bad(value, "object_keys")


def test_provenance_cannot_substitute_for_finding_evidence():
    value = audit()
    value["findings"][0]["evidence"] = [provenance()]
    assert_bad(value, "object_keys")


@pytest.mark.parametrize("removal", [{"path": "/contacts"},
                                     {"path": "/roles/0", "identity": "/person/name"},
                                     {"path": "/roles/0/details"},
                                     {"path": "/roles/0", "match": "anonymous_structure_v1", "original_full_sha256": "c" * 64}])
def test_all_singleton_removal_forms_are_only_shape_checked(removal):
    value = audit()
    value["findings"][0]["remove_relationship"] = removal
    assert check(value)["passed"]


@pytest.mark.parametrize("removal,code", [([{ "path": "/roles/0"}], "object_required"),
                                         ({"path": "/roles/0", "identity": "/description"}, "identity_field"),
                                         ({"path": "/roles/0", "identity": None}, "pointer_syntax"),
                                         ({"path": "/roles/0", "extra": "secret"}, "object_keys"),
                                         ({"path": "/roles/0", "match": "guess"}, "enum_value"),
                                         ({"path": "/roles/0", "match": "anonymous_structure_v1", "original_full_sha256": "bad"}, "digest_syntax"),
                                         ({"path": "/roles/0", "match": "anonymous_structure_v1", "original_full_sha256": "c" * 64, "identity": "/id"}, "object_keys")])
def test_removal_shape_errors(removal, code):
    value = audit()
    value["findings"][0]["remove_relationship"] = removal
    assert_bad(value, code)


@pytest.mark.parametrize("raw,code", [(b'{"x":1,"x":2}', "json_duplicate_key"),
                                     (b'{"x":{"q":1,"q":2}}', "json_duplicate_key"),
                                     (b'{"x":1,"\\u0078":2}', "json_duplicate_key"),
                                     (b'{"x":NaN}', "json_nonfinite"), (b'{"x":Infinity}', "json_nonfinite"),
                                     (b'{"x":-Infinity}', "json_nonfinite"), (b'{"x":1e99999}', "json_nonfinite"),
                                     (b'{"x":"\xff"}', "json_unicode"), (b'{"x":"\\ud800"}', "json_unicode"),
                                     (b'{"\\udfff":1}', "json_unicode"),
                                     (b'{} {}', "json_syntax"), (b'```json\n{}\n```', "json_syntax"),
                                     (b'{} trailing', "json_syntax"), (b'', "json_syntax"),
                                     (b'\xef\xbb\xbf{}', "json_syntax"), (b'{"x": /* no */ 1}', "json_syntax"),
                                     ("{}", "input_bytes_required"), (None, "input_bytes_required")])
def test_strict_json_returns_only_fixed_parse_error(raw, code):
    result = grammar.check(raw)
    assert result["errors"] == [{"code": code, "path": ""}]
    assert result["error_count"] == 1 and result["passed"] is False


def test_deep_nesting_and_size_bound_do_not_escape_as_exceptions():
    assert grammar.check(b'[' * 10000 + b']' * 10000)["errors"] == [{"code": "json_syntax", "path": ""}]
    assert grammar.check(b' ' * (grammar.MAX_BYTES + 1))["errors"] == [{"code": "input_too_large", "path": ""}]


def test_exact_registered_byte_boundary_is_accepted():
    raw = json.dumps(audit()).encode()
    raw += b' ' * (grammar.MAX_BYTES - len(raw))
    assert grammar.check(raw)["passed"]
    assert grammar.check(raw + b' ')["errors"] == [{"code": "input_too_large", "path": ""}]


def test_unicode_surrogate_pair_and_literal_quotes_remain_legal():
    value = audit()
    value["summary"] = 'The literal "quoted term" and emoji \U0001f680.'
    review_claim(value)["text"] = 'The literal "quoted term".'
    raw = json.dumps(value, ensure_ascii=True).encode()
    assert b'\\ud83d\\ude80' in raw
    assert grammar.check(raw)["passed"]


def test_diagnostics_are_bounded_and_dont_echo_untrusted_values_or_keys():
    value = audit()
    value["findings"] = [False] * 1000
    review_claim(value).update(verdict="supported", source_status="applied")
    report = check(value)
    assert report["error_count"] == 1000 and report["truncated"] is True
    assert len(report["errors"]) == grammar.MAX_ERRORS == 20
    assert len(json.dumps(report).encode()) < 8192
    secret = 'SECRET/source~1path with text'
    for raw in [json.dumps({secret: "SECRET_PROSE"}).encode(),
                ('{"' + secret + '":1,"' + secret + '":2}').encode(),
                b'{"SECRET_PROSE": bad-json}']:
        assert "SECRET" not in json.dumps(grammar.check(raw))


def test_source_blindness_is_deliberate_even_with_consistent_false_claims(monkeypatch):
    value = audit()
    value["findings"] = []
    value["source_review"]["sha256"] = "0" * 64  # Well-formed, not a proven artifact hash.
    value["source_review"]["values"][0]["path"] = "/unknown_field"
    item = review_claim(value)
    item.update(text="An invented quotation containing two unsplit assertions.", verdict="supported",
                claim_status="fact", source_status="fact", attributed_to=["does-not-exist.txt"],
                evidence=[{"source": "other-nonexistent.txt", "chunk": "missing", "quote": "Fabricated source."}])
    monkeypatch.setattr("builtins.open", lambda *a, **k: pytest.fail("unexpected file access"))
    assert check(value)["passed"]  # Final evidence checking and review must reject unsupported science.


def test_module_has_no_source_checker_or_io_dependencies():
    tree = ast.parse(inspect.getsource(grammar))
    dependencies = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            dependencies.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            dependencies.add(node.module)
    assert dependencies == {"__future__", "json", "math", "re"}


def test_repeated_check_has_no_state_or_repair_effect():
    value = audit()
    review_claim(value).update(verdict="supported")
    original = copy.deepcopy(value)
    first = check(value)
    second = check(value)
    assert first == second and not first["passed"]
    assert value == original


@pytest.mark.parametrize("replacement", [None, False, 1, [], {}, ["private marker"], ""])
@pytest.mark.parametrize("location", [
    ("summary",), ("findings",), ("findings", 0),
    ("findings", 0, "record"), ("findings", 0, "evidence"),
    ("findings", 0, "review_paths"), ("source_review",),
    ("source_review", "artifact"), ("source_review", "sha256"),
    ("source_review", "values"), ("source_review", "values", 0),
    ("source_review", "values", 0, "path"),
    ("source_review", "values", 0, "claims"),
    ("source_review", "values", 0, "claims", 0),
    ("source_review", "values", 0, "claims", 0, "verdict"),
    ("source_review", "values", 0, "claims", 0, "claim_status"),
    ("source_review", "values", 0, "claims", 0, "source_status"),
    ("source_review", "values", 0, "claims", 0, "evidence"),
    ("source_review", "values", 0, "claims", 0, "attributed_to"),
])
def test_malformed_type_sweep_returns_private_bounded_reports(location, replacement):
    value = audit()
    target = value
    for component in location[:-1]:
        target = target[component]
    target[location[-1]] = replacement
    result = check(value)
    assert type(result["passed"]) is bool
    assert result["passed"] == (result["error_count"] == 0)
    assert len(result["errors"]) == min(result["error_count"], grammar.MAX_ERRORS)
    assert "private marker" not in json.dumps(result)
    # Empty evidence is legal on revise; source names are not resolved here.
    allowed_empty = location[-1] in {"evidence", "attributed_to"} and "claims" in location
    allowed_name = location[-1] == "attributed_to" and replacement == ["private marker"]
    assert result["passed"] == ((allowed_empty and replacement == []) or allowed_name)
