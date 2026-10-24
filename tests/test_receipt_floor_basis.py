"""D-C (owner decision 2026-10-23): the receipted-part floor and the recorded answer envelope.

The two CHORUS generic_v10 canaries had no value without a receipt at receipt
time (never_receipted 0); every miss (5 and 11) was a value reconciliation
added afterwards. A floor over the final record therefore measured how much
the audit found. A registered floor may now name the receipted part as its
basis; a floor without a basis keeps its v2 meaning, byte for byte.
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


# 2026-10-22a CHORUS: 90 populated, 15 exempt, 75 receiptable, 64 with a receipt,
# 0 never receipted, 11 added after the receipt; none of the 11 values occurs
# anywhere in the phase-1 snapshot (A13 review F1).
CANARY_22A = {"populated": 90, "exempt": 15, "receiptable": 75, "with_receipt": 64,
              "never_receipted": 0, "added_after_receipt": 11, "added_after_receipt_unmatched": 11}
RECEIPTED_19 = {"state": "registered", "numerator": 19, "denominator": 20, "basis": "receipted_part"}
V2_KEYS = {"with_receipt", "receiptable", "floor", "passed", "registration_sha256", "state"}


def test_a_floor_without_basis_keeps_its_v2_meaning_and_shape():
    passed = cp.evaluate_floor(CANARY_22A, _policy({"state": "registered", "numerator": 17, "denominator": 20}))
    assert (passed["state"], passed["with_receipt"], passed["receiptable"]) == ("passed", 64, 75)
    assert set(passed) == V2_KEYS  # recomputing a stored v2 block reproduces it exactly
    failed = cp.evaluate_floor(CANARY_22A, _policy({"state": "registered", "numerator": 19, "denominator": 20}))
    assert failed["state"] == "failed" and failed["passed"] is False


def test_the_receipted_part_excludes_values_added_after_the_receipt():
    result = cp.evaluate_floor(CANARY_22A, _policy({"state": "registered", "numerator": 19, "denominator": 20,
                                                    "basis": "receipted_part"}))
    assert result["state"] == "passed" and result["passed"] is True
    assert (result["with_receipt"], result["eligible"], result["receiptable"]) == (64, 64, 75)
    assert result["added_after_receipt"] == 11 and result["basis"] == "receipted_part"
    assert result["added_after_receipt_unmatched"] == 11


def test_never_receipted_values_still_fail_the_receipted_part():
    coverage = {"receiptable": 70, "with_receipt": 60, "never_receipted": 4, "added_after_receipt": 6,
                "added_after_receipt_unmatched": 6}
    result = cp.evaluate_floor(coverage, _policy({"state": "registered", "numerator": 19, "denominator": 20,
                                                  "basis": "receipted_part"}))
    assert (result["eligible"], result["state"]) == (64, "failed")  # 60/64 < 19/20


def test_the_receipted_part_needs_the_phase_one_split():
    coverage = {"receiptable": 75, "with_receipt": 64, "never_receipted": None, "added_after_receipt": None}
    result = cp.evaluate_floor(coverage, _policy({"state": "registered", "numerator": 19, "denominator": 20,
                                                  "basis": "receipted_part"}))
    assert result["state"] == "unmeasurable" and result["passed"] is False
    # A block written before the value-aware counter has the path split only.
    path_only = {k: v for k, v in CANARY_22A.items() if k != "added_after_receipt_unmatched"}
    old = cp.evaluate_floor(path_only, _policy(RECEIPTED_19))
    assert old["state"] == "unmeasurable" and old["eligible"] is None
    nothing_receipted = {"receiptable": 5, "with_receipt": 0, "never_receipted": 0, "added_after_receipt": 5,
                         "added_after_receipt_unmatched": 5}
    empty = cp.evaluate_floor(nothing_receipted, _policy({"state": "registered", "numerator": 19, "denominator": 20,
                                                          "basis": "receipted_part"}))
    assert empty["state"] == "not_applicable" and empty["passed"] is False


def test_inconsistent_counters_are_refused():
    bad = {"receiptable": 75, "with_receipt": 64, "added_after_receipt": 12}
    with pytest.raises(ValueError, match="added_after_receipt exceeds"):
        cp.evaluate_floor(bad, _policy({"state": "registered", "numerator": 19, "denominator": 20,
                                        "basis": "receipted_part"}))
    with pytest.raises(ValueError, match="added_after_receipt_unmatched exceeds added_after_receipt"):
        cp.evaluate_floor({**CANARY_22A, "added_after_receipt": 10, "never_receipted": 1}, _policy(RECEIPTED_19))
    with pytest.raises(ValueError, match="added_after_receipt_unmatched exceeds added_after_receipt"):
        cp.evaluate_floor({**CANARY_22A, "added_after_receipt": None, "never_receipted": None}, _policy(RECEIPTED_19))


def _receipted_part(original, final):
    """The real validator on the test_receipts fixture, then the 19/20 receipted-part floor."""
    from data_sheets_schema import receipts
    from tests.test_receipts import FULL, _manifest_and_texts, _receipt
    manifest, texts = _manifest_and_texts()
    block = receipts.check(_receipt(manifest["bundle_md5"]), manifest, texts, {**FULL, **final},
                           manifest["bundle_md5"], original={**FULL, **original}, instrument_version=4)
    return block["slots"], cp.evaluate_floor(block["slots"], _policy(RECEIPTED_19))


@pytest.mark.parametrize("original,final,split,ratio", [
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
                   {"name": "glycemic", "description": "study diabetes", "response": "yes"}]}, (1, 3), (10, 14)),
    # A new path whose value repeats one the snapshot had is gated: stricter, never looser.
    ({}, {"alternate_name": "ai-readi"}, (0, 1), (10, 11)),
])
def test_a_moved_never_receipted_value_stays_gated(original, final, split, ratio):
    """A13 review F1: by path alone each of these would leave the gated part
    whole (10/10 or near it); by path and value none passes 19/20."""
    slots, floor = _receipted_part(original, final)
    assert (slots["never_receipted"], slots["added_after_receipt"]) == split
    assert slots["added_after_receipt_unmatched"] == 0
    assert (floor["with_receipt"], floor["eligible"]) == ratio
    assert floor["state"] == "failed" and floor["passed"] is False


def test_a_new_value_at_a_new_path_is_still_not_gated():
    slots, floor = _receipted_part({}, {"version": "3.0.0"})
    assert (slots["added_after_receipt"], slots["added_after_receipt_unmatched"]) == (1, 1)
    assert (floor["with_receipt"], floor["eligible"], floor["receiptable"]) == (10, 10, 11)
    assert floor["state"] == "passed"


def test_instrument_three_blocks_carry_no_value_aware_counter():
    from data_sheets_schema import receipts
    from tests.test_receipts import FULL, _manifest_and_texts, _receipt
    manifest, texts = _manifest_and_texts()
    for original in (FULL, None):
        v3 = receipts.check(_receipt(manifest["bundle_md5"]), manifest, texts, FULL, manifest["bundle_md5"],
                            original=original)
        assert "added_after_receipt_unmatched" not in v3["slots"]
    v4 = receipts.check(_receipt(manifest["bundle_md5"]), manifest, texts, FULL, manifest["bundle_md5"],
                        instrument_version=4)
    assert v4["slots"]["added_after_receipt_unmatched"] is None   # no snapshot: unmeasurable, not 0


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

