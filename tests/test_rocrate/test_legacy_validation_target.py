"""The API validates produced Dataset records without changing generic defaults."""
import subprocess

import pytest

from data_sheets_schema import legacy_publication as publication
from .test_legacy_creators import input_file, table, TEXT, SENTINEL
from .test_legacy_publication import legacy
from .test_profile_unavailable import module


@pytest.mark.parametrize('selection,expected_class', [
    ({}, None),
    ({'target_class': None}, None),
    ({'target_class': 'Dataset'}, 'Dataset'),
    ({'target_class': 'DatasetCollection'}, 'DatasetCollection'),
])
def test_validate_all_preserves_generic_default_and_forwards_explicit_class(
        module, tmp_path, monkeypatch, selection, expected_class):
    """Only the subprocess boundary is replaced; run syntax and semantic routing."""
    path = tmp_path / 'record.yaml'
    path.write_text('id: https://example.org/record\ntitle: Example\n', encoding='utf-8')
    original = path.read_bytes()
    schema = tmp_path / 'selected-schema.yaml'
    validator = module.UnifiedValidator(schema_path=schema)
    calls = []

    def process(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout='', stderr='')

    monkeypatch.setattr(module, 'LINKML_AVAILABLE', True)
    monkeypatch.setattr(module.subprocess, 'run', process)
    reports = validator.validate_all(
        path, format='yaml', schema='d4d',
        skip_levels=[module.ValidationLevel.PROFILE, module.ValidationLevel.ROUNDTRIP],
        **selection)
    expected = ['linkml-validate', '-s', str(schema), str(path)]
    if expected_class is not None:
        expected.extend(['-C', expected_class])
    assert calls == [(expected, {'capture_output': True, 'text': True, 'timeout': 30})]
    assert set(reports) == {module.ValidationLevel.SYNTAX, module.ValidationLevel.SEMANTIC}
    assert all(report.passed for report in reports.values())
    assert path.read_bytes() == original


@pytest.mark.parametrize('selection', [{}, {'target_class': None}])
def test_default_keeps_existing_semantic_override_call_contract(
        module, tmp_path, monkeypatch, selection):
    path = tmp_path / 'record.yaml'
    path.write_text('title: Example\n', encoding='utf-8')
    validator = module.UnifiedValidator()
    seen = []

    # Existing overrides need not accept a new keyword for the unchanged
    # generic/default route. Explicit class selection is the opt-in boundary.
    def semantic(actual, schema):
        seen.append((actual, schema))
        return module.ValidationReport(level=module.ValidationLevel.SEMANTIC, passed=True)

    monkeypatch.setattr(validator, 'validate_semantic', semantic)
    reports = validator.validate_all(
        path, skip_levels=[module.ValidationLevel.PROFILE, module.ValidationLevel.ROUNDTRIP],
        **selection)
    assert seen == [(path, 'd4d')]
    assert all(report.passed for report in reports.values())


def test_rocrate_semantics_does_not_select_a_d4d_class(module, tmp_path, monkeypatch):
    path = tmp_path / 'crate.json'
    path.write_text('{"@graph": [{"@id": "./", "@type": "Dataset"}]}', encoding='utf-8')
    validator = module.UnifiedValidator()
    seen = []

    def rocrate(actual, report):
        seen.append(actual)
        return report

    def unexpected(*args, **kwargs):
        raise AssertionError('RO-Crate input reached the D4D class validator')

    monkeypatch.setattr(validator, '_validate_rocrate_semantic', rocrate)
    monkeypatch.setattr(validator, '_validate_d4d_semantic', unexpected)
    reports = validator.validate_all(
        path, format='json', schema='rocrate', target_class='Dataset',
        skip_levels=[module.ValidationLevel.PROFILE, module.ValidationLevel.ROUNDTRIP])
    assert seen == [path]
    assert all(report.passed for report in reports.values())


@pytest.mark.parametrize('command', ['transform', 'batch', 'merge'])
def test_real_enabled_cli_validation_refuses_reference_and_preserves_outputs(
        legacy, tmp_path, command):
    """Real producers and LinkML run with the CLI's enabled validation defaults.

    Existing Creator CLI success controls use complete literal descriptions.
    This refusal must occur in requested validation, before publication, and
    cannot be satisfied solely by the later mandatory publication gate.
    """
    _, _, api = legacy
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    good = input_file(inputs / 'a.json', TEXT)
    bad = input_file(inputs / 'z.json', {'@id': 'https://orcid.org/unresolved'})
    mapping = table(tmp_path)
    if command == 'batch':
        output = tmp_path / 'outputs'
        output.mkdir()
        destinations = [output / 'a_d4d.yaml', output / 'z_d4d.yaml']
        arguments = [str(inputs), str(output)]
    else:
        output = tmp_path / 'dataset.yaml'
        destinations = [output]
        arguments = ([str(bad), str(output)] if command == 'transform'
                     else [str(output), str(good), str(bad)])
    for destination in destinations:
        destination.write_bytes(SENTINEL)
    before = {path: path.read_bytes() for path in [good, bad, mapping, *destinations]}
    with pytest.raises(publication.PublicationError,
                       match='requested Dataset validation failed') as caught:
        api.main([command, *arguments, '--result-contract', 'dataset_v1',
                  '--mapping', str(mapping)])
    assert '@id' in str(caught.value)
    assert {path: path.read_bytes() for path in before} == before
