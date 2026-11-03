# Purpose: prove, without editing the checkout, that round 3's closed RunSpec field
#   roster (tests/test_wave7_5213_d76_round2_binding.py) fails for ANY unclassified new
#   field, including names without a _registration/_version suffix (Claude R2-5).
#   A dataclass subclass with one extra field is monkeypatched in as api.RunSpec.
# Inputs: the checkout's test module. Outputs: pytest results. Date: 2026-11-02. Offline.
from dataclasses import dataclass

import pytest

from data_sheets_schema import api_runner as api
import tests.test_wave7_5213_d76_round2_binding as r2

ROSTER = r2.test_all_runspec_registration_and_version_axes_have_a_binding_classification


def _with_extra(name):
    namespace = {"__annotations__": {name: "str | None"}, name: None}
    return dataclass(type("RunSpecPlus", (api.RunSpec,), namespace))


def test_unmodified_roster_passes():
    ROSTER()


@pytest.mark.parametrize("name", ["input_authority", "registered_inputs_v2", "pinned_input_manifest",
                                  "typed_audit_registration", "native_execution_version", "_private_inputs"])
def test_any_unclassified_field_fails_the_roster(monkeypatch, name):
    monkeypatch.setattr(r2.api, "RunSpec", _with_extra(name))
    with pytest.raises(AssertionError):
        ROSTER()
    print("roster refused unclassified field:", name)
