"""U3A-R4: derive expected CI checks from workflow files, 2026-11-07.

These are offline declaration-parser tests, not evidence that CI or an actual
execution passed. The workflow oracle is independent of production constants.
"""
from copy import deepcopy
import itertools
import json
from pathlib import Path
import re
import subprocess

import pytest
import yaml

from data_sheets_schema import native_execution_registration_v2 as registration
from data_sheets_schema import native_shared_contract as c
from tests.test_native_execution_registration_v2 import (
    fabricated_authorizations, _authorization_kwargs,
)


ROOT = Path(__file__).resolve().parents[1]
EVENTS = ('pull_request', 'push', 'workflow_dispatch')
WORKFLOW = '.github/workflows/main.yaml'


def _workflow(path):
    # BaseLoader keeps GitHub's literal "on" key, unlike YAML 1.1 booleans.
    return yaml.load((ROOT / path).read_text(), Loader=yaml.BaseLoader)


def _active(condition, event):
    if condition in (None, 'always()'):
        return True
    match = re.fullmatch(r"github\.event_name (==|!=) '([^']+)'", condition)
    assert match is not None, 'review newly introduced workflow job condition: ' + condition
    equal = event == match[2]
    return equal if match[1] == '==' else not equal


def _axis(values, event):
    if isinstance(values, list):
        return values
    match = re.fullmatch(
        r"\$\{\{ fromJSON\(github\.event_name == '([^']+)' && '(\[[^']+\])' \|\| '(\[[^']+\])'\) \}\}",
        values)
    assert match is not None, 'review newly introduced matrix expression: ' + values
    return json.loads(match[2] if event == match[1] else match[3])


def _job_names(job_id, job, event):
    if not _active(job.get('if'), event):
        return []
    matrix = job.get('strategy', {}).get('matrix', {})
    assert not {'include', 'exclude'}.intersection(matrix), 'review matrix filtering'
    axes = list(matrix)
    combinations = itertools.product(*(_axis(matrix[axis], event) for axis in axes))
    names = []
    for values in combinations:
        selected = dict(zip(axes, values))
        if 'name' in job:
            name = re.sub(r'\$\{\{ matrix\.([A-Za-z_-]+) \}\}',
                          lambda match: str(selected[match[1]]), job['name'])
            assert '${{' not in name, 'review newly introduced job-name expression'
        else:
            # GitHub's unnamed matrix-job display includes its matrix values.
            name = job_id + (' (' + ', '.join(map(str, values)) + ')' if axes else '')
        names.append(name)
    return names


def _checks_from_workflows(event):
    names = []
    for path in (WORKFLOW, '.github/workflows/large-files.yaml'):
        workflow = _workflow(path)
        triggers = workflow['on']
        if event not in triggers:
            continue
        for job_id, job in workflow['jobs'].items():
            names.extend(_job_names(job_id, job, event))
    assert len(names) == len(set(names)), 'workflow names must be unambiguous'
    return tuple(names)


def _write(records, paths):
    records['launch_word']['review_sha256'] = c.sha(c.canonical(records['review']))
    records['launch_word']['ci_sha256'] = c.sha(c.canonical(records['ci']))
    for key, record in records.items():
        paths[key].write_bytes(c.canonical(record))


def _event_records(records, event):
    records = deepcopy(records)
    ci = records['ci']
    ci['workflow_event'] = event
    row = deepcopy(next(iter(ci['checks'].values())))
    ci['checks'] = {name: deepcopy(row) for name in _checks_from_workflows(event)}
    return records


@pytest.mark.parametrize('event', EVENTS)
def test_required_checks_match_actual_workflow_jobs_and_event_matrix(event):
    expected = _checks_from_workflows(event)
    actual = registration.required_checks(event)
    assert type(actual) is tuple
    assert len(actual) == len(set(actual))
    assert set(actual) == set(expected)


@pytest.mark.parametrize('event', [None, True, False, 1, 2, [], {}, '', 'schedule',
                                  'pull_request_target', 'PUSH', 'push '])
def test_unknown_or_nonstring_event_has_no_default_roster(event):
    with pytest.raises(ValueError):
        registration.required_checks(event)


@pytest.mark.parametrize('event', EVENTS)
def test_complete_current_event_inventory_is_accepted_without_writes(fabricated_authorizations, event):
    raw, value, records, paths = fabricated_authorizations
    records = _event_records(records, event)
    _write(records, paths)
    before = {key: path.read_bytes() for key, path in paths.items()}
    captured = registration._authorizations(raw, value, **_authorization_kwargs(paths))
    assert captured['ci'].raw == before['ci']
    assert {key: path.read_bytes() for key, path in paths.items()} == before


@pytest.mark.parametrize('event', EVENTS)
def test_each_actual_required_check_is_required_even_with_passing_aggregate(fabricated_authorizations, event):
    raw, value, original, paths = fabricated_authorizations
    for missing in _checks_from_workflows(event):
        records = _event_records(original, event)
        del records['ci']['checks'][missing]
        _write(records, paths)
        before = {key: path.read_bytes() for key, path in paths.items()}
        with pytest.raises(ValueError):
            registration._authorizations(raw, value, **_authorization_kwargs(paths))
        assert {key: path.read_bytes() for key, path in paths.items()} == before


@pytest.mark.parametrize('event', EVENTS)
def test_extra_or_other_event_inventory_cannot_impersonate_exact_roster(fabricated_authorizations, event):
    raw, value, original, paths = fabricated_authorizations
    records = _event_records(original, event)
    records['ci']['checks']['invented passing check'] = deepcopy(next(iter(records['ci']['checks'].values())))
    _write(records, paths)
    with pytest.raises(ValueError):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))
    other = 'push' if event == 'pull_request' else 'pull_request'
    records = _event_records(original, other)
    records['ci']['workflow_event'] = event
    _write(records, paths)
    with pytest.raises(ValueError):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))


@pytest.mark.parametrize('mutation', ['digest', 'missing_digest', 'missing_event', 'boolean_event', 'unknown_event'])
def test_workflow_identity_and_event_cannot_be_omitted_or_substituted(fabricated_authorizations, mutation):
    raw, value, records, paths = fabricated_authorizations
    if mutation == 'digest':
        records['ci']['workflow_sha256'] = '0' * 64
    elif mutation == 'missing_digest':
        del records['ci']['workflow_sha256']
    elif mutation == 'missing_event':
        del records['ci']['workflow_event']
    elif mutation == 'boolean_event':
        records['ci']['workflow_event'] = True
    else:
        records['ci']['workflow_event'] = 'schedule'
    _write(records, paths)
    with pytest.raises(ValueError):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))


def test_current_workflow_digest_cannot_hide_different_named_commit_bytes(fabricated_authorizations, tmp_path, monkeypatch):
    """A tiny isolated Git fixture proves the named-object check is substantive."""
    raw, value, records, paths = fabricated_authorizations
    source = tmp_path / 'synthetic-workflow-source'
    target = source / WORKFLOW
    target.parent.mkdir(parents=True)
    current = (ROOT / WORKFLOW).read_bytes()
    target.write_bytes(current + b'\n# Synthetic different committed workflow.\n')
    def git(*args):
        return subprocess.check_output(['git', '-c', 'user.name=U3A Test',
            '-c', 'user.email=u3a-test@example.invalid', *args], cwd=source, text=True).strip()
    git('init', '-q')
    git('add', '--', WORKFLOW)
    git('-c', 'commit.gpgsign=false', 'commit', '-qm', 'Synthetic workflow identity fixture')
    head = git('rev-parse', 'HEAD')
    target.write_bytes(current)
    monkeypatch.setattr(registration.authority, 'ROOT', source)
    value['dependencies']['base']['source_commit'] = head
    for record in records.values():
        record['source_commit'] = head
        record['dependencies_sha256'] = c.sha(c.canonical(value['dependencies']))
    for row in records['ci']['checks'].values():
        row['head_sha'] = head
    records['ci']['workflow_sha256'] = c.sha(current)
    _write(records, paths)
    with pytest.raises(ValueError):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))
    assert target.read_bytes() == current
