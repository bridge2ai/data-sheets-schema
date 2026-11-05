"""D63 exact-pair and stale-sidecar guards for the BC1 Wave7 packet (2026-10-29)."""
from copy import deepcopy
from fractions import Fraction
import math

import pytest

from data_sheets_schema import bc1_registration as registration
from tests.test_bc1_context import fixture as context_fixture
from tests.test_bc1_registration import sizing_fixture


def test_reported_worker_pair_and_display_precision_do_not_change_gate():
    policy = registration.calibration()
    measurement = policy["request_measurement"]
    assert measurement["canonical_payload_bytes"] == 1185329
    assert measurement["input_tokens"] == 432784
    assert measurement["request_sha256"] == "c2087a5a3ad9eddae8d42393a96d71a9d200bee749d02b76e75ee286311f70c9"
    assert policy["future_response_bytes_per_token"] == 1.75
    assert policy["future_response_escape_factor"] == 1.25
    assert policy["gated_scenarios"] == [registration.FLOOR, registration.CAPS]
    assert registration._components(1185329, 1185329, registration.FLOOR, policy)["estimated_input_tokens"] == 432784
    # A rounded display denominator must not silently become the gate's ratio.
    policy["request_bytes_per_token"] = 2.74
    assert registration._components(1185329, 1185329, registration.FLOOR, policy)["estimated_input_tokens"] == 432784


@pytest.mark.parametrize("request_bytes,future", [
    (1, 0), (1, 1), (1, 2), (1185328, 0), (1185329, 0), (1185330, 0),
    (1185329, 7), (10**24 + 3, 10**23 + 1),
])
@pytest.mark.parametrize("scenario", [registration.FLOOR, registration.CAPS, "visible_cap_escaped_bound"])
def test_one_outer_ceiling_preserves_d62_future_policy_at_boundaries(request_bytes, future, scenario):
    expansion = Fraction(5, 4) if scenario == registration.CAPS else Fraction(1)
    planning_future = math.ceil(future * expansion)
    expected = math.ceil(Fraction(request_bytes * 432784, 1185329) + Fraction(planning_future * 4, 7))
    result = registration._components(request_bytes + future, request_bytes, scenario, registration.calibration())
    assert result == {"request_bytes": request_bytes, "future_wire_bytes": future,
                      "planning_future_wire_bytes": planning_future,
                      "planning_wire_bytes": request_bytes + planning_future,
                      "estimated_input_tokens": expected}
    if request_bytes == 1 and future in (1, 2) and scenario == registration.CAPS:
        assert expected == future + 1


@pytest.mark.parametrize("mutation,message", [
    ("old_format", "actual project/arm sizing record"),
    ("old_ratio", "component calibration"),
    ("count", "component calibration"),
    ("request_hash", "component calibration"),
    ("source", "code/contract identity is stale"),
    ("estimate", "calibrated wire bytes"),
])
def test_d63_sidecar_rejects_stale_policy_source_and_forged_estimates(sizing_fixture, mutation, message):
    selected, files, inputs = sizing_fixture
    sizing = registration.size_inputs(selected, sizing_record=files,
        context_raw=inputs["context"], schema_snapshot=inputs["schema_snapshot"])
    registration.check_sizing_record(selected, sizing)
    changed = deepcopy(sizing)
    if mutation == "old_format":
        changed["format"] = "bc1_input_sizing_v3"
    elif mutation == "old_ratio":
        changed["calibration"]["request_bytes_per_token"] = 2.48
    elif mutation == "count":
        changed["calibration"]["request_measurement"]["input_tokens"] -= 1
    elif mutation == "request_hash":
        changed["calibration"]["request_measurement"]["request_sha256"] = "0" * 64
    elif mutation == "source":
        changed["source_identity"]["code"]["src/data_sheets_schema/bc1_registration.py"] = "0" * 64
    elif mutation == "estimate":
        changed["rows"][0]["estimated_input_tokens"] -= 1
    else:
        pytest.fail("undeclared mutation")
    with pytest.raises(ValueError, match=message):
        registration.check_sizing_record(selected, changed)
