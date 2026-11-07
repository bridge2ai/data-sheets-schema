"""U3A-R4: derive expected CI checks from workflow files, 2026-11-07.

These are offline declaration-parser tests, not evidence that CI or an actual
execution passed. The workflow oracle is independent of production constants.
"""
from copy import deepcopy
import itertools
import json
import os
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
LARGE_WORKFLOW = '.github/workflows/large-files.yaml'
WORKFLOWS = (WORKFLOW, LARGE_WORKFLOW)
# This synthetic URL never names a run that was requested or fetched.
REPOSITORY_URL = 'https://github.com/synthetic/native-u3a-tests'


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


@pytest.fixture
def local_ci_git(tmp_path):
    """Real local objects; no inherited Git configuration, hooks or remotes used."""
    source = tmp_path / 'synthetic-workflow-source'
    source.mkdir()
    home = tmp_path / 'isolated-git-home'
    home.mkdir()
    template = tmp_path / 'empty-git-template'
    template.mkdir()
    env = {key: value for key, value in os.environ.items()
           if not key.startswith('GIT_') and key not in ('HOME', 'XDG_CONFIG_HOME')}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home), GIT_CONFIG_GLOBAL='/dev/null',
        GIT_CONFIG_SYSTEM='/dev/null', GIT_TERMINAL_PROMPT='0', GIT_ALLOW_PROTOCOL='',
        GIT_AUTHOR_NAME='Synthetic U3A fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
        GIT_COMMITTER_NAME='Synthetic U3A fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid',
        GIT_AUTHOR_DATE='2026-11-07T00:00:00+0000', GIT_COMMITTER_DATE='2026-11-07T00:00:00+0000')

    def git(*args):
        return subprocess.check_output(['git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
            '-c', 'commit.gpgsign=false', '-c', 'protocol.allow=never', *args],
            cwd=source, env=env, text=True, timeout=30).strip()

    git('init', '-q', '--template=' + str(template))
    git('config', '--local', 'remote.origin.url', REPOSITORY_URL + '.git')
    for relative in WORKFLOWS:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    git('add', '--', *WORKFLOWS)
    git('commit', '-qm', 'Synthetic workflow base')
    base = git('rev-parse', 'HEAD')
    git('commit', '--allow-empty', '-qm', 'Synthetic reviewed source')
    head = git('rev-parse', 'HEAD')
    tree = git('rev-parse', head + '^{tree}')
    merge = git('commit-tree', tree, '-p', base, '-p', head, '-m', 'Synthetic PR merge')
    return {'root': source, 'git': git, 'base': base, 'source': head, 'merge': merge,
            'tree': tree, 'environment': env}


@pytest.fixture
def ci_evidence(fabricated_authorizations, local_ci_git, monkeypatch):
    """Only an approval-parser fixture, not valid E or evidence of any CI run."""
    raw, value, records, paths = fabricated_authorizations
    source = local_ci_git['source']
    value['dependencies']['base']['source_commit'] = source
    for record in records.values():
        record['source_commit'] = source
        record['dependencies_sha256'] = c.sha(c.canonical(value['dependencies']))
    monkeypatch.setattr(registration.authority, 'ROOT', local_ci_git['root'])
    return raw, value, records, paths, local_ci_git


def _event_records(records, event, local):
    records = deepcopy(records)
    ci = records['ci']
    ci['workflow_event'] = event
    ci['workflow_ref'] = 'refs/pull/123/merge' if event == 'pull_request' else 'refs/heads/main'
    ci['tested_commit'] = local['merge'] if event == 'pull_request' else local['source']
    paths = WORKFLOWS if event == 'pull_request' else (WORKFLOW,)
    ci['workflow_sha256'] = {path: c.sha((local['root'] / path).read_bytes()) for path in paths}
    row = deepcopy(next(iter(ci['checks'].values())))
    row['head_sha'] = ci['tested_commit']
    row['details_url'] = REPOSITORY_URL + '/actions/runs/1/job/2'
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
def test_complete_current_event_inventory_is_accepted_without_writes(ci_evidence, event):
    raw, value, records, paths, local = ci_evidence
    records = _event_records(records, event, local)
    _write(records, paths)
    before = {key: path.read_bytes() for key, path in paths.items()}
    captured = registration._authorizations(raw, value, **_authorization_kwargs(paths))
    assert captured['ci'].raw == before['ci']
    assert {key: path.read_bytes() for key, path in paths.items()} == before


@pytest.mark.parametrize('event', EVENTS)
def test_each_actual_required_check_is_required_even_with_passing_aggregate(ci_evidence, event):
    raw, value, original, paths, local = ci_evidence
    for missing in _checks_from_workflows(event):
        records = _event_records(original, event, local)
        del records['ci']['checks'][missing]
        _write(records, paths)
        before = {key: path.read_bytes() for key, path in paths.items()}
        with pytest.raises(ValueError, match='CI check roster differs'):
            registration._authorizations(raw, value, **_authorization_kwargs(paths))
        assert {key: path.read_bytes() for key, path in paths.items()} == before


@pytest.mark.parametrize('event', EVENTS)
def test_extra_or_other_event_inventory_cannot_impersonate_exact_roster(ci_evidence, event):
    raw, value, original, paths, local = ci_evidence
    records = _event_records(original, event, local)
    records['ci']['checks']['invented passing check'] = deepcopy(next(iter(records['ci']['checks'].values())))
    _write(records, paths)
    with pytest.raises(ValueError, match='CI check roster differs'):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))
    other = 'push' if event == 'pull_request' else 'pull_request'
    records = _event_records(original, other, local)
    records['ci']['workflow_event'] = event
    _write(records, paths)
    with pytest.raises(ValueError, match='CI check roster differs'):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))


@pytest.mark.parametrize('mutation, refusal', [
    ('digest', 'CI workflow map differs'), ('missing_digest', 'CI evidence fields differ'),
    ('missing_event', 'CI evidence fields differ'), ('boolean_event', 'CI workflow event must'),
    ('unknown_event', 'CI workflow event must'), ('missing_tested', 'CI evidence fields differ'),
    ('missing_ref', 'CI evidence fields differ'), ('missing_large', 'CI workflow map differs'),
    ('extra_workflow', 'CI workflow map differs'), ('scalar_digest', 'CI workflow map differs')])
def test_workflow_identity_and_event_cannot_be_omitted_or_substituted(ci_evidence, mutation, refusal):
    raw, value, original, paths, local = ci_evidence
    records = _event_records(original, 'pull_request', local)
    if mutation == 'digest':
        records['ci']['workflow_sha256'][WORKFLOW] = '0' * 64
    elif mutation == 'missing_digest':
        del records['ci']['workflow_sha256']
    elif mutation == 'missing_event':
        del records['ci']['workflow_event']
    elif mutation == 'boolean_event':
        records['ci']['workflow_event'] = True
    elif mutation == 'unknown_event':
        records['ci']['workflow_event'] = 'schedule'
    elif mutation == 'missing_tested':
        del records['ci']['tested_commit']
    elif mutation == 'missing_ref':
        del records['ci']['workflow_ref']
    elif mutation == 'missing_large':
        del records['ci']['workflow_sha256'][LARGE_WORKFLOW]
    elif mutation == 'extra_workflow':
        records['ci']['workflow_sha256']['unrelated.yaml'] = '0' * 64
    else:
        records['ci']['workflow_sha256'] = '0' * 64
    _write(records, paths)
    with pytest.raises(ValueError, match=refusal):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))


@pytest.mark.parametrize('relative', WORKFLOWS)
def test_current_workflow_digest_cannot_hide_different_source_bytes(ci_evidence, relative):
    raw, value, original, paths, local = ci_evidence
    target = local['root'] / relative
    target.write_bytes(target.read_bytes() + b'\n# Uncommitted synthetic workflow change.\n')
    records = _event_records(original, 'pull_request', local)
    _write(records, paths)
    with pytest.raises(ValueError, match='CI workflow differs from its exact source commit'):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))


@pytest.mark.parametrize('relative', WORKFLOWS)
def test_pr_workflow_map_cannot_hide_different_tested_merge_bytes(ci_evidence, relative):
    raw, value, original, paths, local = ci_evidence
    target = local['root'] / relative
    current = target.read_bytes()
    target.write_bytes(current + b'\n# Different workflow on tested merge tree.\n')
    local['git']('add', '--', relative)
    tree = local['git']('write-tree')
    merge = local['git']('commit-tree', tree, '-p', local['base'], '-p', local['source'],
                         '-m', 'Synthetic changed workflow merge')
    target.write_bytes(current)
    records = _event_records(original, 'pull_request', {**local, 'merge': merge})
    _write(records, paths)
    with pytest.raises(ValueError, match='CI tested workflow differs from reviewed source workflow'):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))


@pytest.mark.parametrize('mutation, refusal', [
    ('source_only', 'tested commit must merge the exact source as second parent'),
    ('reversed_parents', 'tested commit must merge the exact source as second parent'),
    ('wrong_second_parent', 'tested commit must merge the exact source as second parent'),
    ('head_ref', 'requires the tested pull-request merge ref'),
    ('unknown_commit', 'local CI Git object or configuration is unavailable'),
    ('short_commit', 'CI tested commit must be an exact local Git commit identity'),
    ('source_in_rows', 'CI check source differs from tested commit')])
def test_pr_ci_binds_tested_merge_and_exact_source_parent(ci_evidence, mutation, refusal):
    raw, value, original, paths, local = ci_evidence
    records = _event_records(original, 'pull_request', local)
    ci = records['ci']
    if mutation == 'source_only':
        ci['tested_commit'] = local['source']
    elif mutation == 'reversed_parents':
        ci['tested_commit'] = local['git']('commit-tree', local['tree'], '-p', local['source'],
            '-p', local['base'], '-m', 'Synthetic reversed merge')
    elif mutation == 'wrong_second_parent':
        foreign = local['git']('commit-tree', local['tree'], '-p', local['base'], '-m', 'Other source')
        ci['tested_commit'] = local['git']('commit-tree', local['tree'], '-p', local['base'],
            '-p', foreign, '-m', 'Synthetic unrelated merge')
    elif mutation == 'head_ref':
        ci['workflow_ref'] = 'refs/pull/123/head'
    elif mutation == 'unknown_commit':
        ci['tested_commit'] = '0' * 40
    elif mutation == 'short_commit':
        ci['tested_commit'] = local['merge'][:12]
    else:
        for row in ci['checks'].values():
            row['head_sha'] = local['source']
    _write(records, paths)
    with pytest.raises(ValueError, match=refusal):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))


@pytest.mark.parametrize('event, mutation, refusal', [
    ('push', 'branch', 'push CI requires refs/heads/main'),
    ('push', 'commit', 'non-PR CI tested commit differs from source commit'),
    ('workflow_dispatch', 'commit', 'non-PR CI tested commit differs from source commit'),
    ('workflow_dispatch', 'tag', 'manual CI requires an explicit branch ref')])
def test_non_pr_ci_binds_source_and_supported_ref(ci_evidence, event, mutation, refusal):
    raw, value, original, paths, local = ci_evidence
    records = _event_records(original, event, local)
    if mutation == 'branch':
        records['ci']['workflow_ref'] = 'refs/heads/other'
    elif mutation == 'commit':
        records['ci']['tested_commit'] = local['base']
    else:
        records['ci']['workflow_ref'] = 'refs/tags/main'
    _write(records, paths)
    with pytest.raises(ValueError, match=refusal):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))


@pytest.mark.parametrize('url', [
    REPOSITORY_URL + '/actions/runs/1?anything=true',
    REPOSITORY_URL + '/actions/runs/1#fragment',
    REPOSITORY_URL + '/actions/SYNTHETIC-NOT-A-RUN',
    REPOSITORY_URL + '/actions/runs/1/foreign',
    REPOSITORY_URL + '-foreign/actions/runs/1',
    'https://github.com/foreign/repo/actions/runs/1',
    'https://github.com.evil.invalid/synthetic/native-u3a-tests/actions/runs/1',
    REPOSITORY_URL + '/actions/runs/0', None, True])
def test_ci_run_url_is_exact_configured_repository_run(ci_evidence, url):
    raw, value, original, paths, local = ci_evidence
    records = _event_records(original, 'workflow_dispatch', local)
    next(iter(records['ci']['checks'].values()))['details_url'] = url
    _write(records, paths)
    with pytest.raises(ValueError, match='CI check URL differs from the configured repository Actions run'):
        registration._authorizations(raw, value, **_authorization_kwargs(paths))


@pytest.mark.parametrize('origin', [REPOSITORY_URL, REPOSITORY_URL + '.git',
    'git@github.com:synthetic/native-u3a-tests.git',
    'ssh://git@github.com/synthetic/native-u3a-tests.git'])
def test_repository_actions_url_comes_from_actual_local_origin(local_ci_git, monkeypatch, origin):
    local_ci_git['git']('config', '--local', 'remote.origin.url', origin)
    monkeypatch.setattr(registration.authority, 'ROOT', local_ci_git['root'])
    assert registration._ci_repository_url() == REPOSITORY_URL


def test_named_local_repository_configuration_takes_precedence(local_ci_git, monkeypatch):
    local_ci_git['git']('config', '--local', 'd4d.ciRepositoryUrl', 'https://github.com/another/repository')
    monkeypatch.setattr(registration.authority, 'ROOT', local_ci_git['root'])
    assert registration._ci_repository_url() == 'https://github.com/another/repository'


@pytest.mark.parametrize('origin', ['https://github.com.evil.invalid/o/r.git',
    'https://user:password@github.com/o/r.git', 'file:///tmp/other', '/tmp/other',
    'https://github.com/owner/repo?extra=true', 'https://github.com/owner/repo/actions/runs/1',
    'https://github.com/../repo', 'https://github.com/owner/..'])
def test_repository_configuration_refuses_noncanonical_origin(local_ci_git, monkeypatch, origin):
    local_ci_git['git']('config', '--local', 'remote.origin.url', origin)
    monkeypatch.setattr(registration.authority, 'ROOT', local_ci_git['root'])
    with pytest.raises(ValueError, match='v2 CI repository'):
        registration._ci_repository_url()


def test_missing_repository_configuration_refuses_instead_of_defaulting(local_ci_git, monkeypatch):
    local_ci_git['git']('config', '--local', '--unset', 'remote.origin.url')
    monkeypatch.setattr(registration.authority, 'ROOT', local_ci_git['root'])
    with pytest.raises(ValueError, match='requires local d4d.ciRepositoryUrl or origin'):
        registration._ci_repository_url()


def test_ci_git_ignores_ambient_configuration_hooks_and_borrowed_repository(local_ci_git, monkeypatch, tmp_path):
    marker = tmp_path / 'HOOK-MUST-NOT-RUN'
    hostile = tmp_path / 'hostile-global-config'
    hostile.write_text('[remote "origin"]\n\turl = https://github.com/foreign/repository.git\n'
                       '[core]\n\thooksPath = ' + str(tmp_path / 'foreign-hooks') + '\n')
    hooks = tmp_path / 'foreign-hooks'
    hooks.mkdir()
    hook = hooks / 'post-checkout'
    hook.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\n')
    hook.chmod(0o700)
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', str(hostile))
    monkeypatch.setenv('GIT_CONFIG_SYSTEM', str(hostile))
    monkeypatch.setenv('GIT_DIR', str(tmp_path / 'wrong-git'))
    monkeypatch.setenv('GIT_CONFIG_COUNT', '1')
    monkeypatch.setenv('GIT_CONFIG_KEY_0', 'remote.origin.url')
    monkeypatch.setenv('GIT_CONFIG_VALUE_0', 'https://github.com/foreign/repository.git')
    monkeypatch.setattr(registration.authority, 'ROOT', local_ci_git['root'])
    assert registration._ci_repository_url() == REPOSITORY_URL
    assert not marker.exists()
