"""Renderer16's emitted commands and final native checks share authority (#2172)."""
from dataclasses import replace
import json
from pathlib import Path
import shlex

import pytest

from data_sheets_schema import api_runner as api, evidence_assertions as evidence
from native_phase_history import _classify, phase_history
from run_native_canary import native_evidence_check
from tests.test_source_metadata_renderer import fixture, audit, report, RAW
from tests.test_source_review import review_for


def commands(spec):
    return [line for line in api.native_evidence_instructions(spec).splitlines()
            if ' -m data_sheets_schema.evidence_assertions ' in line]


def classify(spec, command):
    return _classify(command, spec, Path.cwd(),
                     {'programs': [], 'manifest_paths': [str(spec.manifest)]})


@pytest.mark.parametrize('selection', ['selected', 'absent', 'unused'])
@pytest.mark.parametrize('version', [15, 16])
def test_actual_rendered_evidence_commands_are_recognized(tmp_path, version, selection):
    spec, _ = fixture(tmp_path, 'Claude Code')
    spec = replace(spec, render_version=version)
    if selection == 'absent':
        spec = replace(spec, manifest=None)
    elif selection == 'unused':
        spec = replace(spec, manifest_line='# Source manifest: not used')
    calls = commands(spec)
    assert len(calls) == 2
    assert [classify(spec, call) for call in calls] == [('evidence', None)] * 2
    expected = version == 16 and selection == 'selected'
    assert all(('--source-manifest' in call) == expected for call in calls)


@pytest.mark.parametrize('mutation', ['omit_manifest', 'omit_project', 'wrong_manifest',
                                    'wrong_project', 'path_like_project', 'duplicate', 'extra'])
@pytest.mark.parametrize('stage', [0, 1])
def test_history_rejects_authority_not_selected_for_this_run(tmp_path, mutation, stage):
    spec, _ = fixture(tmp_path, 'Claude Code')
    args = shlex.split(commands(spec)[stage])
    if mutation.startswith('omit_'):
        option = '--source-manifest' if mutation == 'omit_manifest' else '--project'
        index = args.index(option)
        del args[index:index + 2]
    elif mutation == 'wrong_manifest':
        args[args.index('--source-manifest') + 1] = str(tmp_path / 'other.yaml')
    elif mutation in {'wrong_project', 'path_like_project'}:
        args[args.index('--project') + 1] = 'OTHER' if mutation == 'wrong_project' else './EXAMPLE'
    elif mutation == 'duplicate':
        args += ['--project', spec.project]
    else:
        args += ['--extra', 'not registered']
    assert classify(spec, shlex.join(args)) == ('evidence', 'helper arguments differ from the selected run')


@pytest.mark.parametrize('selection', ['absent', 'unused', 'legacy'])
def test_unselected_or_legacy_manifest_options_cannot_be_smuggled_into_history(tmp_path, selection):
    spec, _ = fixture(tmp_path, 'Claude Code')
    authority = spec.manifest
    spec = (replace(spec, manifest=None) if selection == 'absent' else
            replace(spec, manifest_line='# Source manifest: not used') if selection == 'unused' else
            replace(spec, render_version=15))
    for command in commands(spec):
        command += ' ' + shlex.join(['--source-manifest', str(authority), '--project', spec.project])
        assert classify(spec, command) == ('evidence', 'helper arguments differ from the selected run')


def prepared(spec, assertion, *, document_only=False):
    directory = spec.metadata_dir / 'evidence'
    directory.mkdir(parents=True, exist_ok=True)
    for variant in ('full', 'core'):
        (directory / f'original_{variant}.yaml').write_text(RAW)
    for path in (spec.full_path, spec.core_path, spec.report_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    spec.full_path.write_text(RAW)
    spec.core_path.write_text(RAW)
    if document_only:
        chunks, _ = evidence.source_chunks(spec.bundle, spec.chunk_manifest)
        audit_value = {'findings': [], 'summary': 'Synthetic document review',
                       'source_review': review_for(RAW, chunks=chunks)}
        report_text = '## Evidence assertions\n```json\n' + json.dumps({'claims': [],
            'source_review': review_for(RAW, artifact='final_full', chunks=chunks)}) + '\n```\n'
    else:
        audit_value, report_text = audit(assertion), report(assertion)
    (directory / 'audit.json').write_text(json.dumps(audit_value))
    spec.report_path.write_text(report_text)


@pytest.mark.parametrize('mutation', [None, 'bytes', 'value', 'project', 'omitted', 'unused'])
def test_real_native_final_check_matches_exact_registered_authority(tmp_path, mutation):
    spec, assertion = fixture(tmp_path, 'Claude Code')
    if mutation == 'value':
        assertion['value'] = 4
    elif mutation == 'project':
        spec.project = 'OTHER'
    prepared(spec, assertion)
    if mutation == 'bytes':
        spec.manifest.write_bytes(spec.manifest.read_bytes() + b'\n')
    elif mutation == 'omitted':
        spec = replace(spec, manifest=None)
    elif mutation == 'unused':
        spec = replace(spec, manifest_line='# Source manifest: not used')
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    if mutation == 'project':
        with pytest.raises(ValueError, match='project is not declared'):
            native_evidence_check(spec)
    else:
        result = native_evidence_check(spec)
        assert bool(result['findings']) == (mutation is not None)
        if mutation is None:
            assert result['artifact_sha256']['source_manifest'] == assertion['sha256']
            assert result['source_review_original']['claims_checked'] == result['source_review_final']['claims_checked'] == 1
    assert before == {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


@pytest.mark.parametrize('selection', ['absent', 'unused'])
def test_native_document_only_v5_never_reads_unselected_manifest(tmp_path, monkeypatch, selection):
    spec, assertion = fixture(tmp_path, 'Claude Code')
    manifest = spec.manifest
    spec = replace(spec, manifest=None) if selection == 'absent' else replace(spec, manifest_line='# Source manifest: not used')
    prepared(spec, assertion, document_only=True)
    read = Path.read_bytes
    def guarded(path):
        if path == manifest:
            pytest.fail('Native final check read an unselected source manifest')
        return read(path)
    monkeypatch.setattr(Path, 'read_bytes', guarded)
    result = native_evidence_check(spec)
    assert result['findings'] == [] and 'source_manifest' not in result['artifact_sha256']


def test_actual_failed_v5_evidence_result_is_terminal_in_phase_history(tmp_path):
    spec, assertion = fixture(tmp_path, 'Claude Code')
    assertion['value'] = 4
    prepared(spec, assertion)
    checked = native_evidence_check(spec)
    assert checked['findings']
    call = {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': 'evidence',
             'name': 'Bash', 'input': {'command': commands(spec)[0]}}]}}
    result = {'type': 'user', 'message': {'content': [{'type': 'tool_result',
               'tool_use_id': 'evidence', 'is_error': True, 'content': json.dumps(checked)}]}}
    out = phase_history([call, result], spec)
    assert len(out['terminal_failures']) == 1
    assert not any('arguments differ' in problem for problem in out['problems'])
