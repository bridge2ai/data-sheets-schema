"""Offline causal blinding regressions for review findings F3, F4 and F9."""
import pytest
import yaml
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
