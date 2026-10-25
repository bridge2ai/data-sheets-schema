"""D-C (owner decision 2026-10-23): the receipted-part floor and the recorded answer envelope.

The two CHORUS generic_v10 canaries had no value without a receipt at receipt
time (never_receipted 0); every miss (5 and 11) was a value reconciliation
added afterwards. A floor over the final record therefore measured how much
the audit found. A registered floor may now name the receipted part as its
basis; a floor without a basis keeps its v2 meaning, byte for byte. Since D37
(2026-10-25, replacing D32) the receipted part is the phase-1 snapshot itself:
the floor gates `with_receipt_at_receipt / receiptable_at_receipt`.
"""
import hashlib
import json

import pytest
import yaml

from data_sheets_schema import receipt_completion as rc
from data_sheets_schema import receipt_completion_policy as cp
from data_sheets_schema import rereceipt


def _policy(floor):
    raw = json.dumps({
        "format": "receipt_completion_registration_v2", "registration_id": "floor-basis-test",
        "condition": "generic_v10", "runtime_policy_sha256": rc.policy_identity(version=2)["sha256"],
        "receipt_instrument_version": 4, "max_output_tokens": 4000, "max_request_bytes": 32000000,
        "context_limit_tokens": 1000000, "context_limit_basis": "test", "coverage_floor": floor,
    }, sort_keys=True).encode("utf-8")
    registration = cp.parse_registration(raw, version=2)
    return {"identity": cp.registration_identity(raw, version=2), "registration": registration,
            "runtime_policy_sha256": registration["runtime_policy_sha256"]}


# 2026-10-22a CHORUS, recomputed read-only from its records under D37: the
# final record has 90 populated, 15 exempt, 75 receiptable and 64 with a
# receipt (0 never receipted, 11 added after the receipt); its phase-1
# snapshot has 64 receiptable, all with a receipt. 2026-10-20a is 58/63 and
# 58/58.
CANARY_22A = {"populated": 90, "exempt": 15, "receiptable": 75, "with_receipt": 64,
              "never_receipted": 0, "added_after_receipt": 11,
              "receiptable_at_receipt": 64, "with_receipt_at_receipt": 64}
FINAL_ONLY_22A = {k: v for k, v in CANARY_22A.items() if not k.endswith("_at_receipt")}
RECEIPTED_19 = {"state": "registered", "numerator": 19, "denominator": 20, "basis": "receipted_part"}
V2_KEYS = {"with_receipt", "receiptable", "floor", "passed", "registration_sha256", "state"}
SNAPSHOT_KEYS = {"receiptable_at_receipt", "with_receipt_at_receipt"}


def test_a_floor_without_basis_keeps_its_v2_meaning_and_shape():
    passed = cp.evaluate_floor(CANARY_22A, _policy({"state": "registered", "numerator": 17, "denominator": 20}))
    assert (passed["state"], passed["with_receipt"], passed["receiptable"]) == ("passed", 64, 75)
    assert set(passed) == V2_KEYS  # recomputing a stored v2 block reproduces it exactly
    failed = cp.evaluate_floor(CANARY_22A, _policy({"state": "registered", "numerator": 19, "denominator": 20}))
    assert failed["state"] == "failed" and failed["passed"] is False


@pytest.mark.parametrize("floor,tail", [
    ({"state": "registered", "numerator": 17, "denominator": 20}, {"state": "passed"}),
    ({"state": "registered", "numerator": 19, "denominator": 20}, {"state": "failed"}),
    ({"state": "pending", "mode": "diagnostic_pilot"},
     {"state": "pending", "reason": "diagnostic pilot; coverage floor not registered"}),
])
@pytest.mark.parametrize("snapshot", [
    {}, {"receiptable_at_receipt": None, "with_receipt_at_receipt": None},
    {"receiptable_at_receipt": 64, "with_receipt_at_receipt": 64},
    {"receiptable_at_receipt": 3, "with_receipt_at_receipt": 0},
])
def test_a_floor_without_basis_is_byte_identical_whatever_the_snapshot_counters(floor, tail, snapshot):
    """The v2 result reads no D37 counter: the bytes, key order included, are
    those the v2 floor wrote before the basis existed."""
    policy = _policy(floor)
    passed = tail["state"] == "passed"
    # The floor as registered: the registration's bytes fix its key order.
    expected = {"with_receipt": 64, "receiptable": 75, "floor": policy["registration"]["coverage_floor"],
                "passed": passed, "registration_sha256": policy["identity"]["sha256"], **tail}
    result = cp.evaluate_floor({**FINAL_ONLY_22A, **snapshot}, policy)
    assert json.dumps(result) == json.dumps(expected)


def test_the_receipted_part_gates_the_phase_one_snapshot():
    result = cp.evaluate_floor(CANARY_22A, _policy(RECEIPTED_19))
    assert result["state"] == "passed" and result["passed"] is True
    assert (result["with_receipt_at_receipt"], result["receiptable_at_receipt"]) == (64, 64)
    # The final record's counters stay beside the gate, for context.
    assert (result["with_receipt"], result["receiptable"], result["basis"]) == (64, 75, "receipted_part")
    assert set(result) == V2_KEYS | SNAPSHOT_KEYS | {"basis"}


def test_never_receipted_values_still_fail_the_receipted_part():
    coverage = {"receiptable": 70, "with_receipt": 60, "never_receipted": 4, "added_after_receipt": 6,
                "receiptable_at_receipt": 64, "with_receipt_at_receipt": 60}
    result = cp.evaluate_floor(coverage, _policy(RECEIPTED_19))
    assert (result["with_receipt_at_receipt"], result["receiptable_at_receipt"]) == (60, 64)
    assert result["state"] == "failed"  # 60/64 < 19/20


@pytest.mark.parametrize("counters", [
    {"receiptable_at_receipt": None, "with_receipt_at_receipt": None},   # no phase-1 snapshot
    {},                                                                  # a block written before D37
    {"added_after_receipt_unmatched": 11},                               # D32's counter is not read
    {"receiptable_at_receipt": 64, "with_receipt_at_receipt": None},
    {"receiptable_at_receipt": None, "with_receipt_at_receipt": 64},
])
def test_the_receipted_part_fails_closed_without_the_snapshot_counters(counters):
    result = cp.evaluate_floor({**FINAL_ONLY_22A, **counters}, _policy(RECEIPTED_19))
    assert result["state"] == "unmeasurable" and result["passed"] is False
    assert "phase-1 snapshot" in result["reason"]


def test_a_snapshot_with_nothing_receiptable_is_not_applicable():
    coverage = {"receiptable": 5, "with_receipt": 0, "never_receipted": 0, "added_after_receipt": 5,
                "receiptable_at_receipt": 0, "with_receipt_at_receipt": 0}
    empty = cp.evaluate_floor(coverage, _policy(RECEIPTED_19))
    assert empty["state"] == "not_applicable" and empty["passed"] is False


def test_inconsistent_counters_are_refused():
    with pytest.raises(ValueError, match="added_after_receipt exceeds"):
        cp.evaluate_floor({"receiptable": 75, "with_receipt": 64, "added_after_receipt": 12}, _policy(RECEIPTED_19))
    with pytest.raises(ValueError, match="with_receipt_at_receipt exceeds receiptable_at_receipt"):
        cp.evaluate_floor({**CANARY_22A, "with_receipt_at_receipt": 65}, _policy(RECEIPTED_19))
    for bad in ({"receiptable_at_receipt": True}, {"receiptable_at_receipt": 64.0},
                {"with_receipt_at_receipt": -1}, {"with_receipt_at_receipt": "64"}):
        with pytest.raises(ValueError, match="must be an integer"):
            cp.evaluate_floor({**CANARY_22A, **bad}, _policy(RECEIPTED_19))


def _receipted_part(original, final):
    """The real validator on the test_receipts fixture, then the 19/20 receipted-part floor."""
    from data_sheets_schema import receipts
    from tests.test_receipts import FULL, _manifest_and_texts, _receipt
    manifest, texts = _manifest_and_texts()
    block = receipts.check(_receipt(manifest["bundle_md5"]), manifest, texts, {**FULL, **final},
                           manifest["bundle_md5"], original={**FULL, **original}, instrument_version=4)
    return block["slots"], cp.evaluate_floor(block["slots"], _policy(RECEIPTED_19))


@pytest.mark.parametrize("original,final,split,at_receipt", [
    # A never-receipted licence renamed to a path the snapshot lacks; and the
    # same value normalised str -> [str] on the way (#899).
    ({"license": "CC-BY"}, {"license_and_use_terms": {"description": "CC-BY"}}, (0, 1), (10, 11)),
    ({"license": "CC-BY"}, {"license_and_use_terms": {"description": ["CC-BY"]}}, (0, 1), (10, 11)),
    # Two never-receipted creators with different key sets, reordered.
    ({"creators": [{"name": "Ada Lovelace", "affiliation": "Univ A"}, {"name": "Bob Smith"}]},
     {"creators": [{"name": "Bob Smith"}, {"name": "Ada Lovelace", "affiliation": "Univ A"}]}, (2, 1), (10, 13)),
    # The audit inserts a 1-leaf purpose ahead of a 3-leaf never-receipted one.
    ({"purposes": [{"name": "glycemic", "description": "study diabetes", "response": "yes"}]},
     {"purposes": [{"description": "a new purpose"},
                   {"name": "glycemic", "description": "study diabetes", "response": "yes"}]}, (1, 3), (10, 13)),
])
def test_a_moved_never_receipted_value_stays_gated(original, final, split, at_receipt):
    """The A13 review of 60634b0c2, F1: by path alone each of these leaves the
    gated part whole or nearly so. On the snapshot each never-receipted value
    is where it was written, without a receipt, and none passes 19/20."""
    slots, floor = _receipted_part(original, final)
    assert (slots["never_receipted"], slots["added_after_receipt"]) == split
    assert (floor["with_receipt_at_receipt"], floor["receiptable_at_receipt"]) == at_receipt
    assert floor["state"] == "failed" and floor["passed"] is False


@pytest.mark.parametrize("original,final", [
    # Case, whitespace, punctuation.
    ({"license": "CC-BY"}, {"license_and_use_terms": {"description": "cc-by"}}),
    ({"license": "CC-BY 4.0"}, {"license_and_use_terms": {"description": "CC-BY 4.0 "}}),
    ({"license": "CC-BY 4.0"}, {"license_and_use_terms": {"description": "CC BY 4.0"}}),
    # A list merged, reordered or split into scalars; a value split into a list.
    ({"themes": ["glucose", "retina"]}, {"topics": ["glucose", "retina", "ecg"]}),
    ({"themes": ["glucose", "retina"]}, {"topics": ["retina", "glucose"]}),
    ({"themes": ["glucose", "retina"]}, {"topic_a": "glucose", "topic_b": "retina"}),
    ({"license": "CC-BY; MIT"}, {"licenses": ["CC-BY", "MIT"]}),
    # A YAML type changed on the way.
    ({"is_deidentified": "true"}, {"deidentification": {"is_deidentified": True}}),
    ({"version": 1}, {"release": {"version": "1"}}),
    # An identifier moved and reformatted, as four ORCID leaves did in two CM4AI v8 records.
    ({"creators": [{"id": "ORCID:0000-0002-1708-8454"}]},
     {"creators": [{"principal_investigator": {"orcid": "0000-0002-1708-8454"}}]}),
])
def test_a_never_receipted_value_moved_and_rewritten_fails_the_floor(original, final):
    """The A13 review of 382b2ad1b, F2: D32's exact value match let each of
    these leave the gate, and 10/11 passed 19/20 as 10/10. The path split
    still calls each an addition; on the snapshot it is a value without a
    receipt, whatever became of it."""
    slots, floor = _receipted_part(original, final)
    assert slots["never_receipted"] == 0 and slots["added_after_receipt"] >= 1
    assert (floor["with_receipt_at_receipt"], floor["receiptable_at_receipt"]) == (10, 11)
    assert floor["state"] == "failed" and floor["passed"] is False


# The test_receipts fixture's collection with an enum and a boolean leaf,
# receipted through the entry receipt on `file_collections[0]`.
COLLECTION = {"id": "https://x/ds#fc1", "name": "raw", "compression": "none", "is_public": True,
              "resources": [{"id": "https://x/ds#f1", "name": "a.tsv", "md5": "0" * 32}]}


@pytest.mark.parametrize("original,final,final_counts,at_receipt", [
    # The A13 review of 382b2ad1b, F1: an added collection whose enum and
    # boolean repeat receipted snapshot values. D32 failed it 12/14.
    ({"file_collections": [COLLECTION]},
     {"file_collections": [COLLECTION, {"name": "processed", "compression": "none", "is_public": True}]},
     (12, 15), (12, 12)),
    # A `subsets` slot the snapshot never had, its boolean repeating an
    # unrelated `true` (VOICE 2026-09-04d/e). D32 failed it 12/13.
    ({"file_collections": [COLLECTION]},
     {"file_collections": [COLLECTION],
      "subsets": [{"name": "train", "is_subpopulation": True, "is_data_split": False}]},
     (12, 15), (12, 12)),
    # A new path whose value repeats a snapshot value, and one whose value is new.
    ({}, {"alternate_name": "ai-readi"}, (10, 11), (10, 10)),
    ({}, {"version": "3.0.0"}, (10, 11), (10, 10)),
    # A receipted `name` renamed later: a miss in the final record (its
    # receipt names a path that is gone), none on the snapshot. D32 failed it 9/10.
    ({}, {"name": None, "dataset_name": "ai-readi"}, (9, 10), (10, 10)),
])
def test_complete_phase_one_receipts_pass_whatever_a_later_phase_added(original, final, final_counts, at_receipt):
    """D37: the floor measures the receipting, on the record the receipt was
    written against. A later phase's additions are reported (the final record's
    counts beside the gate) and not gated."""
    slots, floor = _receipted_part(original, final)
    assert (floor["with_receipt"], floor["receiptable"]) == final_counts
    assert (floor["with_receipt_at_receipt"], floor["receiptable_at_receipt"]) == at_receipt
    assert floor["state"] == "passed" and floor["passed"] is True


def test_only_instrument_four_carries_the_snapshot_counters():
    from data_sheets_schema import receipts
    from tests.test_receipts import FULL, _manifest_and_texts, _receipt
    manifest, texts = _manifest_and_texts()
    md5 = manifest["bundle_md5"]
    for original in (FULL, None):
        v3 = receipts.check(_receipt(md5), manifest, texts, FULL, md5, original=original)
        assert not (SNAPSHOT_KEYS | {"added_after_receipt_unmatched"}) & set(v3["slots"])
    v4 = receipts.check(_receipt(md5), manifest, texts, FULL, md5, instrument_version=4)["slots"]
    assert all(v4[k] is None for k in SNAPSHOT_KEYS)   # no snapshot: unmeasurable, not 0
    assert "added_after_receipt_unmatched" not in v4
    # An unchanged record counts the same on its snapshot as on itself.
    same = receipts.check(_receipt(md5), manifest, texts, FULL, md5, original=FULL, instrument_version=4)["slots"]
    assert (same["with_receipt_at_receipt"], same["receiptable_at_receipt"]) == (same["with_receipt"],
                                                                                 same["receiptable"]) == (10, 10)


def test_a_receipt_path_the_snapshot_does_not_resolve_earns_nothing_there():
    """Credit on the snapshot is where the receipt path was written, and a
    path the snapshot does not resolve earns none, as in the final record."""
    from data_sheets_schema import receipts
    from tests.test_receipts import FULL, _manifest_and_texts, _receipt
    manifest, texts = _manifest_and_texts()
    md5 = manifest["bundle_md5"]
    receipt = _receipt(md5)
    # A path into structure a later phase added: no leaf on the snapshot to cover.
    receipt["chunks"][1]["extracted"].append({"slot": "version", "snippet": "a longitudinal, multimodal study"})
    snapshot = {**FULL, "license": "CC-BY"}
    final = {**snapshot, "version": "3.0.0"}
    slots = receipts.check(receipt, manifest, texts, final, md5, original=snapshot, instrument_version=4)["slots"]
    assert slots["path_not_in_snapshot_count"] == 1
    assert (slots["with_receipt_at_receipt"], slots["receiptable_at_receipt"]) == (10, 11)
    assert (slots["with_receipt"], slots["receiptable"]) == (10, 12)
    # A path the grammar refuses, though a leaf's own path is spelled the same:
    # credited by spelling it would be 11/11; the final-record join gives it none.
    receipt["chunks"][1]["extracted"].append({"slot": "file-format", "snippet": "a longitudinal, multimodal study"})
    snapshot = {**FULL, "file-format": "TSV"}
    slots = receipts.check(receipt, manifest, texts, snapshot, md5, original=snapshot, instrument_version=4)["slots"]
    assert (slots["with_receipt_at_receipt"], slots["receiptable_at_receipt"]) == (10, 11)
    assert (slots["with_receipt"], slots["receiptable"]) == (10, 11)


def _cli_floor_line(tmp_path, monkeypatch, snapshot):
    """`d4d receipts check --strict` on the test_receipts fixture under a 19/20
    receipted-part registration: (exit code, the registered-coverage line, the
    whole output)."""
    from click.testing import CliRunner
    import data_sheets_schema.cli.receipts as cli
    from data_sheets_schema.chunking import build_manifest, dump_manifest
    from tests.test_receipts import BUNDLE, FULL, _receipt
    bundle, full, manifest = tmp_path / "P.txt", tmp_path / "P_d4d.yaml", tmp_path / "chunks.yaml"
    bundle.write_text(BUNDLE)
    md5 = hashlib.md5(bundle.read_bytes()).hexdigest()
    final = {**FULL, "file_collections": [COLLECTION, {"name": "processed", "compression": "none", "is_public": True}]}
    full.write_text(f"# Source bundle: {bundle}\n" + yaml.safe_dump(final))
    (tmp_path / "P_coverage_receipt.yaml").write_text(yaml.safe_dump(_receipt(md5)))
    manifest.write_text(dump_manifest(build_manifest(bundle)))
    if snapshot is not None:
        (tmp_path / "intermediate").mkdir()
        (tmp_path / "intermediate" / "P_full.yaml").write_text(yaml.safe_dump(snapshot))
    provenance = tmp_path / "P_provenance.yaml"
    provenance.write_text(yaml.safe_dump({"run": {"project": "P"}, "inputs": {
        "bundle_path": str(bundle), "bundle_md5": md5, "receipt_expected": True}}))
    monkeypatch.setattr(cli, "_run_paths", lambda *args: {"core_dir": tmp_path, "full": full, "provenance": provenance})
    # A real v2 selection also needs the shared-generation registration; what
    # is under test is the floor the check computes and the line it prints.
    selected = _policy(RECEIPTED_19)
    monkeypatch.setattr(cp, "select_policy", lambda render_spec=None, record=None: selected)
    result = CliRunner().invoke(cli.check, ["--method", "claudecode_api", "--label", "L", "--project", "P",
                                            "--strict", "--chunk-manifest", str(manifest)])
    lines = [line for line in result.output.splitlines() if "registered receipt coverage" in line]
    assert len(lines) == 1, result.output
    return result.exit_code, lines[0], result.output


def test_the_cli_shows_the_phase_one_record_it_gates(tmp_path, monkeypatch):
    """A13 review F5: the line names the snapshot's counts (12/12), not the
    final record's (12/15), which the summary line above it carries."""
    from tests.test_receipts import FULL
    code, line, output = _cli_floor_line(tmp_path, monkeypatch, {**FULL, "file_collections": [COLLECTION]})
    assert "registered receipt coverage: passed (12/12 of the phase-1 record (receipted part))" in line
    assert "slots 12/15 with a receipt" in output
    assert code == 0


def test_the_cli_says_the_receipted_part_is_unmeasurable_without_a_snapshot(tmp_path, monkeypatch):
    code, line, _output = _cli_floor_line(tmp_path, monkeypatch, None)
    assert "registered receipt coverage: unmeasurable (receipted part unmeasurable: no phase-1 snapshot)" in line
    assert code == 1   # --strict fails closed


def test_only_a_known_basis_is_accepted():
    with pytest.raises(ValueError, match="coverage floor basis must be one of"):
        _policy({"state": "registered", "numerator": 19, "denominator": 20, "basis": "final_record"})
    with pytest.raises(ValueError, match="exact numerator/denominator"):
        _policy({"state": "registered", "numerator": 19, "denominator": 20, "basis": "receipted_part", "x": 1})
    with pytest.raises(ValueError, match="explicit diagnostic_pilot"):
        _policy({"state": "pending", "mode": "diagnostic_pilot", "basis": "receipted_part"})


@pytest.mark.parametrize("text,envelope", [
    ("rereceipt: []\n", "bare"),
    ("```yaml\nrereceipt: []\n```\n", "yaml_fence"),
    ("```\nrereceipt: []\n```", "yaml_fence"),
])
def test_the_answer_envelope_is_named(text, envelope):
    assert rereceipt.parse_answers_envelope(text.encode()) == ([], envelope)
    assert rereceipt.parse_answers(text.encode()) == []


def test_prose_around_a_fence_is_still_refused():
    # The YAML reader refuses it; the runtime treats either error as an unusable response.
    with pytest.raises((ValueError, yaml.YAMLError)):
        rereceipt.parse_answers_envelope(b"Here are the answers:\n```yaml\nrereceipt: []\n```\n")


def test_a_result_saved_before_the_envelope_fields_still_verifies(monkeypatch):
    current = {"state": "answers_complete", "counts": {"requested": 1}, "answer_envelope": "yaml_fence",
               "answer_parser": dict(rereceipt.ANSWER_PARSER)}
    monkeypatch.setattr(rc, "_result", lambda inputs, raw, **kw: json.loads(json.dumps(current)))
    response = {"text": "```yaml\nrereceipt: []\n```", "stop_reason": "end_turn"}
    legacy = {k: v for k, v in current.items() if k not in ("answer_envelope", "answer_parser")}
    assert rc._checked_result(None, response, legacy) == legacy
    assert rc._checked_result(None, response, dict(current)) == current
    from data_sheets_schema.usage_ledger import UsageLedgerError
    with pytest.raises(UsageLedgerError):
        rc._checked_result(None, response, {**legacy, "state": "answers_incomplete"})
    with pytest.raises(UsageLedgerError):
        rc._checked_result(None, response, {**current, "answer_envelope": "bare"})


def test_a_basis_is_refused_outside_v2_registrations():
    """Only generic_v10's v2 registration may name a basis; v1 keeps the exact numerator/denominator form."""
    def v1(floor):
        return json.dumps({
            "format": "receipt_completion_registration_v1", "registration_id": "v1-basis-test",
            "condition": "generic_v8", "runtime_policy_sha256": rc.policy_identity(version=1)["sha256"],
            "receipt_instrument_version": 4, "max_output_tokens": 4000, "max_request_bytes": 32000000,
            "context_limit_tokens": 1000000, "context_limit_basis": "test", "coverage_floor": floor,
        }, sort_keys=True).encode("utf-8")
    plain = {"state": "registered", "numerator": 19, "denominator": 20}
    with pytest.raises(ValueError, match="exact numerator/denominator$"):
        cp.parse_registration(v1({**plain, "basis": "receipted_part"}), version=1)
    # The same floor without the basis is still a valid v1 registration.
    assert cp.parse_registration(v1(plain), version=1)["coverage_floor"] == plain


def test_the_recorded_parser_identity_follows_the_fence_pattern():
    import hashlib as _h
    assert rereceipt.ANSWER_PARSER["fence_pattern_sha256"] == _h.sha256(rereceipt.ANSWER_FENCE.encode()).hexdigest()

