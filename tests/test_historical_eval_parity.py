"""#5126 preparation differentials; no claim of complete historical runtime parity.

The pinned base prepare() runs against the same current globals and source
resources as today's shared adapter. Source-file pins therefore describe the
current checkout in both results, rather than pretending to replay old code.
"""
import ast
import os
from pathlib import Path
import subprocess

import pytest
import yaml

from data_sheets_schema.evaluation import registered_eval_runner as runner
from data_sheets_schema.evaluation.evaluation_identity import evaluation_condition_key, repeat_key
from tests.test_historical_eval_admission import (
    binding_document, rebind_evidence, rebind_provenance, rebind_record,
)
from tests.test_historical_eval_route import historical_inputs
from tests.test_registered_eval_runner import no_provider, registration, sha

BASE = "d0974d4bcc0f254272ec5a95e94d83ae801bbd38"
RUNNER_PATH = "src/data_sheets_schema/evaluation/registered_eval_runner.py"
INSTRUMENTS = [("rubric10", "3.0"), ("rubric10", "5.0"),
               ("rubric20", "3.0"), ("rubric20", "4.0"), ("rubric20", "5.0")]


@pytest.fixture(scope="module")
def base_prepare():
    """Compile only the pinned prepare definition, with no old module import."""
    root = Path(__file__).resolve().parents[1]
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_NO_LAZY_FETCH="1", GIT_CONFIG_GLOBAL="/dev/null",
               GIT_CONFIG_NOSYSTEM="1", GIT_OPTIONAL_LOCKS="0", GIT_ALLOW_PROTOCOL="")
    result = subprocess.run(
        ["git", "--no-replace-objects", "-c", "protocol.allow=never", "-C", str(root),
         "show", BASE + ":" + RUNNER_PATH],
        check=True, capture_output=True, timeout=15, env=env,
    )
    source = ast.parse(result.stdout.decode(), filename=BASE + ":" + RUNNER_PATH)
    definitions = {node.name: node for node in source.body if isinstance(node, ast.FunctionDef)}
    assert "prepare" in definitions and not definitions["prepare"].decorator_list
    current = ast.parse(Path(runner.__file__).read_text())
    current_definitions = {node.name: node for node in current.body if isinstance(node, ast.FunctionDef)}
    # Both differential results use this renderer. Check it is still the base
    # renderer instead of accidentally proving equality with a changed oracle.
    assert ast.dump(definitions["rating_prompt"], include_attributes=False) == ast.dump(
        current_definitions["rating_prompt"], include_attributes=False)
    namespace = vars(runner).copy()
    module = ast.Module(body=[definitions["prepare"]], type_ignores=[])
    exec(compile(module, BASE + ":" + RUNNER_PATH, "exec"), namespace)
    return namespace["prepare"]


def equivalent_historical_inputs(shared_inputs, historical_inputs):
    """Keep fixture authorities distinct while matching admitted scientific input."""
    inputs = rebind_record(historical_inputs, shared_inputs["record"].read_bytes())
    prior = yaml.safe_load(inputs["provenance"].read_bytes())
    shared_prior = yaml.safe_load(shared_inputs["provenance"].read_bytes())
    prior["run"] = dict(shared_prior["run"])
    condition = prior["run"].pop("condition")
    prior["prompts"]["request"]["spec"]["condition"] = condition
    prior["historical_only_note"] = "provenance-only-sentinel-should-not-reach-evaluator"
    inputs = rebind_provenance(inputs, prior)
    binding = binding_document(inputs)
    cohort = yaml.safe_load(Path(binding["cohort"]["path"]).read_bytes())
    row = cohort["cells"][0]
    run = prior["run"]
    row.update(projects=[run["project"]], replicates=[run["replicate"]],
               label_template=run["label"], method=run["method"], input_arm=run["arm"],
               condition=condition, comparison_arm=shared_inputs["comparison_arm"])
    inputs = rebind_evidence(inputs, "cohort", yaml.safe_dump(cohort).encode())
    inputs["context"].write_bytes(shared_inputs["context"].read_bytes())
    inputs["context_sha256"] = sha(inputs["context"].read_bytes())
    for key in ("rubric", "instrument_version", "repeat_count", "model", "canonical_model",
                "base_url", "context_window", "runtime", "runtime_sha256", "runtime_version",
                "max_cost_dollars", "comparison_arm", "effort"):
        if key in shared_inputs:
            inputs[key] = shared_inputs[key]
    return inputs


@pytest.mark.parametrize("rubric,version", INSTRUMENTS)
def test_historical_and_shared_adapters_have_identical_model_facing_bytes(
        registration, historical_inputs, rubric, version):
    # The older shared fixture deliberately permits an unknown replicate. Make
    # a separate, explicitly declared synthetic counterpart for the historical
    # contract, which requires a positive replicate; never restamp the fixture.
    shared_prior = yaml.safe_load(registration["provenance"].read_bytes())
    shared_prior["run"]["replicate"] = 17
    shared_provenance = historical_inputs["record"].parent / "shared-counterpart-provenance.yaml"
    shared_provenance.write_text(yaml.safe_dump(shared_prior))
    shared_inputs = {**registration, "rubric": rubric, "instrument_version": version, "repeat_count": 1,
                     "provenance": shared_provenance, "provenance_sha256": sha(shared_provenance.read_bytes())}
    historical_options = equivalent_historical_inputs(shared_inputs, historical_inputs)
    historical_paths = [Path(pin["path"]) for name, pin in binding_document(historical_options).items()
                        if name in {"record", "provenance", "cohort", "decision"}]
    historical_paths += [historical_options["registration"], historical_options["context"]]
    before = {path: path.read_bytes() for path in historical_paths}
    shared = runner.prepare(**shared_inputs)
    retrospective = runner.prepare_historical(**historical_options)
    left, right = shared.document(), retrospective.document()
    assert left["generation_authority_kind"] == "shared_generation_v1"
    assert right["generation_authority_kind"] == "historical_provenance_v1"
    assert evaluation_condition_key(left) == evaluation_condition_key(right)
    assert repeat_key(left) != repeat_key(right)
    assert left["generation_registration"] is not None
    assert right["generation_registration"] is None
    assert shared.original == retrospective.original
    assert shared.blinded == retrospective.blinded
    assert shared.context == retrospective.context
    assert shared.resources == retrospective.resources
    assert left["instrument"] == right["instrument"]
    assert left["runtime"] == right["runtime"]
    assert shared.definition == retrospective.definition
    assert shared.preamble == retrospective.preamble
    assert shared.system_prompt == retrospective.system_prompt
    prompt = runner.rating_prompt(shared).encode()
    assert prompt == runner.rating_prompt(retrospective).encode()
    model_facing = prompt + b"\n" + shared.system_prompt
    hidden = {
        left["generation_run"]["project"], left["generation_run"]["label"],
        left["generation_run"]["method"], left["generation_run"]["arm"],
        left["blinding"]["condition"], left["blinding"]["replicate_token"],
        "provenance-only-sentinel-should-not-reach-evaluator",
        "historical_artifact_binding_v1", "historical_provenance_v1",
        "shared_generation_registration_v1",
    }
    for plan in (left, right):
        for field in ("record", "generation_provenance", "generation_registration", "historical_binding"):
            if plan.get(field):
                hidden.update((plan[field]["path"], plan[field]["sha256"]))
    for token in hidden:
        assert token.encode() not in model_facing, token
    assert before == {path: path.read_bytes() for path in before}
    assert all(Path(path).read_bytes() == raw for path, raw in shared.authorities)


@pytest.mark.parametrize("rubric,version", INSTRUMENTS)
def test_shared_preparation_differs_from_pinned_base_only_by_explicit_kind(
        registration, base_prepare, rubric, version):
    """Same current resources/globals, not an old-runtime or provider replay."""
    options = {**registration, "rubric": rubric, "instrument_version": version, "repeat_count": 1}
    before = {options[key]: options[key].read_bytes()
              for key in ("registration", "record", "provenance", "context", "runtime")}
    expected = base_prepare(**options)
    actual = runner.prepare(**options)
    actual_plan = actual.document()
    assert actual_plan.pop("generation_authority_kind") == "shared_generation_v1"
    assert actual_plan == expected.document()
    from dataclasses import replace
    assert replace(actual, manifest=expected.manifest) == expected
    assert runner.rating_prompt(actual).encode() == runner.rating_prompt(expected).encode()
    assert actual.system_prompt == expected.system_prompt
    assert before == {path: path.read_bytes() for path in before}
