"""Scheduling hints retain JUnit occurrences without accepting copied inputs."""

import hashlib
from collections import Counter
import subprocess
import xml.etree.ElementTree as ET

import pytest

from utils.update_ci_shard_timings import build


@pytest.fixture
def timing_inputs(tmp_path):
    repository = tmp_path / "repository"
    tests = repository / "tests"
    tests.mkdir(parents=True)
    (tests / "test_budget.py").write_text("def test_budget(): pass\n")
    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    subprocess.run(["git", "add", "tests/test_budget.py"], cwd=repository, check=True)
    results = tmp_path / "results"
    results.mkdir()
    return repository, results


def junit(results, shard, *records):
    path = results / shard / "pytest.xml"
    path.parent.mkdir(parents=True)
    suite = ET.Element("testsuite", tests=str(len(records)))
    for record in records:
        fields = {"classname": "tests.test_budget", "name": "test_budget[00]",
                  "time": "0.014", **record}
        outcome = fields.pop("outcome", None)
        case = ET.SubElement(suite, "testcase", fields)
        if outcome:
            ET.SubElement(case, outcome)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)
    return path


def estimate(timing_inputs):
    repository, results = timing_inputs
    return build(results, repository, run_id=123, commit="a" * 40)


def test_parameter_id_collision_retains_both_occurrences_and_times(timing_inputs):
    _, results = timing_inputs
    # Actual pytest/JUnit shape from #5020: integer 0 and string '00' can
    # produce the same label. They remain two records, not one repeated input.
    source = junit(results, "shard1", {"time": "0.014"}, {"time": "0.015"})
    original = source.read_bytes()

    value = estimate(timing_inputs)

    assert value["source"]["test_cases"] == 2
    assert value["file_seconds"] == {"tests/test_budget.py": 0.029}
    assert value["source"]["artifacts"] == [{
        "path": "shard1/pytest.xml", "sha256": hashlib.sha256(original).hexdigest()}]
    assert source.read_bytes() == original


def test_same_label_in_different_artifacts_is_rejected(timing_inputs):
    _, results = timing_inputs
    junit(results, "shard1", {"time": "0.014"})
    junit(results, "shard2", {"time": "0.015"})
    with pytest.raises(ValueError, match="duplicate case across artifacts"):
        estimate(timing_inputs)


@pytest.mark.parametrize("copy_kind", ["bytes", "symlink"])
def test_copied_or_referenced_artifact_is_rejected(timing_inputs, copy_kind):
    _, results = timing_inputs
    source = junit(results, "shard1", {})
    duplicate = results / "shard2" / "pytest.xml"
    duplicate.parent.mkdir()
    if copy_kind == "bytes":
        duplicate.write_bytes(source.read_bytes())
    else:
        duplicate.symlink_to(source)
    with pytest.raises(ValueError, match="duplicate artifact input"):
        estimate(timing_inputs)


def test_distinct_labels_and_skips_keep_their_record_counts(timing_inputs):
    _, results = timing_inputs
    junit(results, "shard1", {"name": "test_first", "time": "0.014"})
    junit(results, "shard2", {"name": "test_second", "time": "0.015"},
          {"name": "test_skipped", "time": "0", "outcome": "skipped"})
    value = estimate(timing_inputs)
    assert value["source"]["test_cases"] == 3
    assert value["file_seconds"] == {"tests/test_budget.py": 0.029}


@pytest.mark.parametrize("outcome", ["failure", "error"])
def test_unsuccessful_case_still_refuses(timing_inputs, outcome):
    _, results = timing_inputs
    junit(results, "shard1", {"outcome": outcome})
    with pytest.raises(ValueError, match="use a successful run"):
        estimate(timing_inputs)


@pytest.mark.parametrize("duration", ["-0.001", "NaN", "Infinity"])
def test_invalid_duration_still_refuses(timing_inputs, duration):
    _, results = timing_inputs
    junit(results, "shard1", {"time": duration})
    with pytest.raises(ValueError, match="invalid recorded duration"):
        estimate(timing_inputs)


def test_unknown_collected_module_still_refuses(timing_inputs):
    _, results = timing_inputs
    junit(results, "shard1", {"classname": "tests.test_untracked"})
    with pytest.raises(ValueError, match="cannot map collected case"):
        estimate(timing_inputs)


@pytest.mark.parametrize("empty_artifact", [False, True])
def test_empty_input_still_refuses(timing_inputs, empty_artifact):
    _, results = timing_inputs
    if empty_artifact:
        junit(results, "shard1")
    with pytest.raises(ValueError, match="no test cases|no pytest.xml"):
        estimate(timing_inputs)


def test_round7_refresh_preserves_history_and_excludes_dedicated_sg2():
    """The installed hints retain their measured/estimated distinction."""
    import json
    from pathlib import Path
    from decimal import Decimal

    data = json.loads((Path(__file__).resolve().parents[1] / 'utils/ci_test_durations.json').read_text())
    proof = data['ci_refresh_5213_20261105']
    local = {f: v for block in data['local_overrides'] for f, v in block['file_seconds'].items()}
    assert len(local) == len(proof['weights']) == 25
    current_refresh = data['source']['ci_refresh_42916359440_20261111']
    prior_weights = current_refresh['previous_file_seconds']
    # PR5531 fix C adds one measured file without changing the historical
    # round-7 population or its local/CI provenance distinction.
    additions = {'tests/test_pr5531_regressions.py'}
    assert len(set(prior_weights) - set(local) - additions) == 635
    refresh = data['source']['pr5531_fix_c_local_20261108']
    assert set(refresh['file_seconds']) == additions | {'tests/test_bc1_pipeline.py'}
    assert refresh['previous_file_seconds'] == {
        'tests/test_pr5531_regressions.py': None, 'tests/test_bc1_pipeline.py': 47.963}
    ci_refresh = data['source']['pr5531_ci_refresh_5602_20261110']
    assert ci_refresh['run_id'] == 42534095997
    assert ci_refresh['commit'] == '4ac73609c328bce8d7a48469eba4a0c73a07ee49'
    assert ci_refresh['previous_file_seconds'] == refresh['file_seconds']
    assert ci_refresh['file_seconds'] == {
        'tests/test_pr5531_regressions.py': 963.687,
        'tests/test_bc1_pipeline.py': 1337.314,
    }
    for name, seconds in ci_refresh['file_seconds'].items():
        assert seconds > refresh['file_seconds'][name] > 0
        assert prior_weights[name] == seconds
    assert proof['run_id'] == 41990198212
    assert len(proof['sg2_local_seconds']) == 3
    assert Counter(row['basis'] for row in proof['weights']) == {
        'CI JUnit': 18, 'local remainder x 2.1033': 7}
    for row in proof['weights']:
        assert row['before'] == local[row['file']]
        assert row['after'] == prior_weights[row['file']]
        if row['basis'] != 'CI JUnit':
            remainder = Decimal(str(row['before'])) - Decimal(str(row['sg2_deducted']))
            assert row['after'] == float((remainder * Decimal('2.1033')).quantize(Decimal('0.001')))
        if row['sg2_deducted']:
            assert row['sg2_deducted'] == sum(proof['sg2_local_seconds'].values())

    assert current_refresh['run_id'] == 42916359440
    assert current_refresh['commit'] == '6792947ea6558d10c85106065b023cb57838835a'
    assert current_refresh['status'] == 'completed'
    assert current_refresh['conclusion'] == 'success'
    assert current_refresh['test_cases'] == 23270
    assert current_refresh['passed_cases'] == 23222
    assert current_refresh['skipped_cases'] == 48
    expected_artifacts = [
        (13811466815, 'tests-py3.12-shard1', 'f62f0c957a6c51021fa4de1c9285ed8d4aca6f6afb0ff21279ba18f6b33f0099', 'd64f049ed1c10d23c57501ce78f3a23f0a81201f4c769f14b030ee5470f231f3', 3377),
        (13811196151, 'tests-py3.12-shard2', '85d90279dd14d83e88c17abc1648e0dcdd7163419a80f892c10dc81dae5f6c4b', '1637e1f67de363c9f0504d27c176d7fabcf36e4ec1ca21528cce1063ac7fefbc', 2882),
        (13811616484, 'tests-py3.12-shard3', 'c67cbc58d5ce07d4509915cda695fd76c50f02185ec6a7a4ea7c11b14db3b8fa', '38a105b4f1409f85f7413231067fe0bf4fb072788bde600c0a88afa91e084d45', 2079),
        (13811385881, 'tests-py3.12-shard4', '460b328db7e5cf1c0b6a7a3ca3dd6ff7e9457980cff501e2b583d225b4bbe306', '65c18aa21d282a87dcacce4f859a5d640ce981dae5b9c8015abdc3a20dcb0664', 2723),
        (13812880450, 'tests-py3.12-shard5', 'e02b747c4d8114ce3e1fe39ffce33a8869efc3f58b36f2220dd23d2230029263', '1731d8f57a0eaaba7f9f2100b589a037580b72520b0f2180ef9867526e0ea3d4', 2998),
        (13810838458, 'tests-py3.12-shard6', '9bd12394d3a6abce7531eb35220487f4ef7eea5b292dd27e8ffedb1b64c6c28a', '504d4cb3c928c7c0844087798addc3f4ee5a36a087a7f9848a66877d86aae234', 2714),
        (13810813307, 'tests-py3.12-shard7', '7f25ab2bb1bdfde7f7dce8cd2fbe4753447d2509ab1ce2f2c0dccd5a07e22b6d', '3efcec3925760e6266a8e0b9911801c52e75891b78b4f3a042ef356453a60c9d', 3587),
        (13811114126, 'tests-py3.12-shard8', 'd81ff2a44f850ad3703fdfe18c496c0752440fc99e31025e4fd1548f1617bda2', '2c0d4344182c9f245bc1c59ecf1a94fb9542a852fc7fbe9e529c2d190cb69357', 2910),
    ]
    assert [
        (
            item['id'],
            item['name'],
            item['locally_computed_xml_sha256'],
            item['api_reported_archive_sha256'],
            item['test_cases'],
        )
        for item in current_refresh['artifacts']
    ] == expected_artifacts
    assert all(
        item['path'] == f"{item['name']}/pytest.xml"
        and item['sha256'] == item['locally_computed_xml_sha256']
        and item['head_sha'] == '6792947ea6558d10c85106065b023cb57838835a'
        and item['failures'] == 0
        and item['errors'] == 0
        for item in current_refresh['artifacts']
    )
    assert current_refresh['file_seconds'] == data['file_seconds']
    assert set(current_refresh['retired_prior_files']) == set(
        data['local_overrides'][1]['retired_modules']
    )
    assert set(current_refresh['readiness_only_files']) == {
        'tests/test_final_generation_acceptance.py',
        'tests/test_final_record_component_limits.py',
    }
    assert set(data['file_seconds']) == (
        (set(prior_weights) - set(current_refresh['retired_prior_files']))
        | set(current_refresh['newly_timed_main_files'])
        | set(current_refresh['readiness_only_files'])
    )
    assert len(data['file_seconds']) == (
        len(prior_weights)
        - len(current_refresh['retired_prior_files'])
        + len(current_refresh['newly_timed_main_files'])
        + len(current_refresh['readiness_only_files'])
    )
    assert data['file_seconds']['tests/test_bc1_registration.py'] < prior_weights['tests/test_bc1_registration.py']
    assert data['file_seconds']['tests/test_wave7_5213_d76_registration.py'] < 100.0
