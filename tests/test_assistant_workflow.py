"""Execute assistant preparation/publication shell with only paid/remote calls faked.

#2088 / #5050, 2026-10-16. Real registration preparation consumes a committed
synthetic input checkout. Tests never read provider credentials or call a model.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/d4d-agent.yml"


def workflow():
    return yaml.safe_load(WORKFLOW.read_text())


def steps(job):
    return {s.get("id") or s["name"]: s for s in workflow()["jobs"][job]["steps"]}


# Only the shared API invocation, schema command, and remote publication are
# replaced. Registration/input/schema capture uses the actual checked-in code.
SHIM = r'''import json, os, pathlib, subprocess, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
event = {'command': name, 'args': args}
if name == 'poetry' and args[:2] == ['run', 'python']:
    os.execv(sys.executable, [sys.executable, '-B'] + args[2:])
if name == 'poetry' and args[:4] == ['run', 'd4d', 'api', 'run']:
    registration = pathlib.Path(args[args.index('--shared-generation-registration') + 1])
    event['registration'] = json.loads(registration.read_text())
    target = pathlib.Path(args[args.index('--out-dir') + 1])
    project = args[args.index('--project') + 1]
    for suffix in ['_d4d.yaml', '_d4d_core.yaml', '_reconciliation.md', '_provenance.yaml']:
        (target / (project + suffix)).write_text('synthetic generated artifact\n')
    (target / 'audit').mkdir()
    (target / 'audit' / 'response.json').write_text('{"synthetic":true}\n')
    (target / '.receipt-state').write_text('preserve hidden evidence\n')
    (target / 'Unit_api_progress.json').write_text('{"synthetic_progress": true}\n')
    (target / 'generation.log').write_text('synthetic retained log\n')
elif name == 'poetry' and args[:2] == ['run', 'linkml-validate']:
    assert pathlib.Path(args[-1]).is_file()
    if os.environ.get('FAIL_CORE') and 'CoreDataset' in args:
        raise SystemExit(1)
elif name == 'poetry':
    raise SystemExit('unexpected poetry invocation')
if name == 'git':
    assert args[0] in ['config', 'checkout', 'add', 'commit', 'push', 'rev-parse', 'ls-remote', 'fetch', 'show']
    if args[0] == 'add':
        target = pathlib.Path(args[-1])
        event['staged'] = {p.as_posix(): p.read_bytes().hex() for p in target.rglob('*') if p.is_file()}
    if os.environ.get('REAL_GIT'):
        subprocess.run([os.environ['REAL_GIT']] + args, check=True)
if name == 'gh':
    assert args[:2] in (['pr', 'create'], ['pr', 'list'])
    if args[1] == 'create':
        event['body'] = pathlib.Path(args[args.index('--body-file') + 1]).read_text()
        if os.environ.get('FAIL_CREATE'):
            raise SystemExit('synthetic remote PR failure after successful push')
        print('https://example.invalid/synthetic-pr')
    elif os.environ.get('EXISTING_PR'):
        print(os.environ['EXISTING_PR'])
with open(os.environ['EVENTS'], 'a') as stream:
    stream.write(json.dumps(event) + '\n')
'''


def shim(directory, names):
    directory.mkdir()
    for name in names:
        target = directory / name
        target.write_text('#!' + sys.executable + '\n' + SHIM)
        target.chmod(0o700)


def command(args, cwd):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


@pytest.fixture
def attempt(tmp_path):
    source = tmp_path / 'source'
    inputs = source / 'data/sheets_d4dassistant/inputs/Unit'
    inputs.mkdir(parents=True)
    (inputs / 'one.txt').write_text('Synthetic dataset documentation.\n')
    (inputs / '.hidden.json').write_text('{"synthetic": true}\n')
    # Candidate code must not be imported, installed or executed during prep.
    (source / 'sitecustomize.py').write_text('raise RuntimeError("candidate code executed")\n')
    command(['git', 'init', '-q'], source)
    command(['git', 'add', '.'], source)
    command(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
             'commit', '-qm', 'synthetic source'], source)
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    bindir = tmp_path / 'bin'
    shim(bindir, ['poetry'])
    env = {'PATH': str(bindir) + os.pathsep + os.defpath,
           'HOME': os.environ.get('HOME', str(tmp_path)),
           'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1',
           'GITHUB_WORKSPACE': str(tmp_path), 'RUNNER_TEMP': str(runtime),
           'GITHUB_OUTPUT': str(tmp_path / 'github-output'), 'DATASET': 'Unit',
           'TRUSTED_SHA': command(['git', 'rev-parse', 'HEAD'], ROOT),
           'SOURCE_SHA': command(['git', 'rev-parse', 'HEAD'], source),
           'ATTEMPT_ID': '9001-2', 'PROVIDER': 'cborg',
           'EVENTS': str(tmp_path / 'events.jsonl')}
    return tmp_path, inputs, env


def run(step, env, cwd=ROOT):
    assert '${{' not in step['run'], 'Shell expressions must be passed through env'
    return subprocess.run(['/bin/bash', '-e'], input=step['run'], text=True,
                          cwd=cwd, env=env, capture_output=True, timeout=90)


def prepare(attempt):
    _, _, env = attempt
    result = run(steps('respond-to-mention')['resolve'], env)
    assert result.returncode == 0, result.stderr
    outputs = dict(line.split('=', 1) for line in Path(env['GITHUB_OUTPUT']).read_text().splitlines())
    return {**env, 'REGISTRATION': outputs['registration'], 'LABEL': outputs['label'],
            'OUTPUT_DIR': outputs['output-dir'], 'ATTEMPT_DIR': outputs['attempt-dir']}


def publish_env(tmp_path, env):
    target = Path(env['RUNNER_TEMP']) / 'assistant-evidence'
    shutil.copytree(env['ATTEMPT_DIR'], target)
    bindir = tmp_path / 'publish-bin'
    shim(bindir, ['git', 'gh'])
    work = tmp_path / 'publication'
    work.mkdir()
    command(['git', 'init', '-q'], work)
    (work / '.gitignore').write_text('*_api_progress.json\n*.log\n')
    command(['git', 'add', '.gitignore'], work)
    command(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
             'commit', '-qm', 'publication base'], work)
    remote = tmp_path / 'origin.git'
    command(['git', 'init', '--bare', '-q', str(remote)], work)
    command(['git', 'remote', 'add', 'origin', str(remote)], work)
    command(['git', 'push', '-q', 'origin', 'HEAD:refs/heads/fixture-base'], work)
    return work, {**env, 'PATH': str(bindir) + os.pathsep + os.defpath,
                  'REAL_GIT': shutil.which('git'),
                  'TRUSTED_SHA': command(['git', 'rev-parse', 'HEAD'], work),
                  'TARGET_BRANCH': 'fixture-base',
                  'ITEM_NUMBER': '123', 'RUN_URL': 'https://example.invalid/run/9001'}


def test_real_preparation_and_workflow_publish_complete_unique_attempt(attempt):
    tmp_path, _, _ = attempt
    env = prepare(attempt)
    selected = steps('respond-to-mention')
    for name in ['generate', 'validate']:
        result = run(selected[name], env)
        assert result.returncode == 0, result.stderr
    work, pubenv = publish_env(tmp_path, env)
    old = work / 'data/sheets_d4dassistant/Unit_d4d.yaml'
    old.parent.mkdir(parents=True)
    old.write_text('Historical output is retained.\n')
    result = run(steps('publish')['pr'], pubenv, work)
    assert result.returncode == 0, result.stderr
    events = [json.loads(line) for line in Path(env['EVENTS']).read_text().splitlines()]
    generation = next(e for e in events if e['args'][:4] == ['run', 'd4d', 'api', 'run'])
    assert '--bundle' not in generation['args']
    assert generation['args'][generation['args'].index('--condition') + 1] == 'generic_v10'
    assert generation['args'][generation['args'].index('--shared-generation-version') + 1] == '1'
    assert generation['registration']['runtime']['provider'] == 'LBL CBORG (proxy to Anthropic)'
    validations = [e for e in events if e['args'][:2] == ['run', 'linkml-validate']]
    assert [e['args'][e['args'].index('-C') + 1] for e in validations] == ['Dataset', 'CoreDataset']
    added = next(e for e in events if e['command'] == 'git' and e['args'][0] == 'add')
    destination = f"data/sheets_d4dassistant/attempts/Unit/{env['LABEL']}"
    original = Path(env['ATTEMPT_DIR'])
    expected = {f'{destination}/{p.relative_to(original).as_posix()}': p.read_bytes().hex()
                for p in original.rglob('*') if p.is_file()}
    assert added['staged'] == expected
    assert set(command(['git', 'ls-files', '--', destination], work).splitlines()) == set(expected)
    assert any(p.endswith('/outputs/.receipt-state') for p in added['staged'])
    assert any(p.endswith('/outputs/audit/response.json') for p in added['staged'])
    assert old.read_text() == 'Historical output is retained.\n'
    created = next(e for e in events if e['command'] == 'gh' and e['args'][1] == 'create')
    assert '--body-file' in created['args']
    assert pubenv['TRUSTED_SHA'] in created['body'] and env['SOURCE_SHA'] in created['body']
    assert created['args'][created['args'].index('--base') + 1] == 'fixture-base'
    assert destination in created['body']


@pytest.mark.parametrize('kind', ['untracked', 'modified', 'unsupported'])
def test_real_preparation_refusal_never_admits_generation(attempt, kind):
    _, inputs, env = attempt
    if kind == 'untracked':
        (inputs / '.untracked.txt').write_text('Must not be silently omitted.')
    elif kind == 'modified':
        (inputs / 'one.txt').write_text('Different from the declared commit.')
    else:
        (inputs / 'bad.zip').write_bytes(b'unsupported')
        source = inputs.parents[3]
        command(['git', 'add', '.'], source)
        command(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'unsupported input'], source)
        env['SOURCE_SHA'] = command(['git', 'rev-parse', 'HEAD'], source)
    result = run(steps('respond-to-mention')['resolve'], env)
    assert result.returncode != 0
    assert not Path(env['EVENTS']).exists(), 'No billed or publication command may run'
    assert not Path(env['GITHUB_OUTPUT']).exists()


@pytest.mark.parametrize('kind', ['symlink', 'missing-validation', 'unsafe-label'])
def test_publication_rejects_unchecked_or_nonregular_artifacts(attempt, kind):
    tmp_path, _, _ = attempt
    env = prepare(attempt)
    for name in ['generate', 'validate']:
        assert run(steps('respond-to-mention')[name], env).returncode == 0
    work, env = publish_env(tmp_path, env)
    evidence = Path(env['RUNNER_TEMP']) / 'assistant-evidence'
    if kind == 'symlink':
        (evidence / 'bad.txt').symlink_to('/etc/passwd')
    elif kind == 'missing-validation':
        (evidence / 'validation.txt').unlink()
    else:
        env['LABEL'] = '../escape'
    Path(env['EVENTS']).unlink()
    result = run(steps('publish')['pr'], env, work)
    assert result.returncode != 0
    assert not Path(env['EVENTS']).exists()


def test_core_validation_failure_cannot_create_acceptance_marker(attempt):
    env = prepare(attempt)
    assert run(steps('respond-to-mention')['generate'], env).returncode == 0
    result = run(steps('respond-to-mention')['validate'], {**env, 'FAIL_CORE': '1'})
    assert result.returncode != 0
    assert not (Path(env['ATTEMPT_DIR']) / 'validation.txt').exists()


@pytest.mark.parametrize('existing_pr', ['', 'https://example.invalid/already-created'])
def test_publication_only_retry_reuses_exact_remote_evidence_without_push(attempt, existing_pr):
    tmp_path, _, _ = attempt
    env = prepare(attempt)
    for name in ['generate', 'validate']:
        assert run(steps('respond-to-mention')[name], env).returncode == 0
    work, pubenv = publish_env(tmp_path, env)
    first = run(steps('publish')['pr'], {**pubenv, 'FAIL_CREATE': '1'}, work)
    assert first.returncode != 0 and 'synthetic remote PR failure' in first.stderr
    branch = f"refs/heads/d4dassistant/Unit-{env['ATTEMPT_ID']}"
    remote = tmp_path / 'origin.git'
    original_sha = command(['git', '--git-dir', str(remote), 'rev-parse', branch], work)
    retry = tmp_path / 'retry-publication'
    command(['git', 'clone', '-q', '--no-checkout', str(remote), str(retry)], tmp_path)
    command(['git', 'checkout', '-q', '--detach', pubenv['TRUSTED_SHA']], retry)
    result = run(steps('publish')['pr'], {**pubenv, 'EXISTING_PR': existing_pr}, retry)
    assert result.returncode == 0, result.stderr
    assert command(['git', '--git-dir', str(remote), 'rev-parse', branch], work) == original_sha
    events = [json.loads(line) for line in Path(env['EVENTS']).read_text().splitlines()]
    pushes = [e for e in events if e['command'] == 'git' and e['args'][0] == 'push']
    assert len(pushes) == 1
    assert not any('--force' in e['args'] for e in pushes)
    creates = [e for e in events if e['command'] == 'gh' and e['args'][1] == 'create']
    assert len(creates) == (0 if existing_pr else 1)
    assert f"url={existing_pr or 'https://example.invalid/synthetic-pr'}" in Path(env['GITHUB_OUTPUT']).read_text()


@pytest.mark.parametrize('tampering', ['tree', 'base'])
def test_publication_retry_refuses_existing_branch_with_changed_authority(attempt, tampering):
    tmp_path, _, _ = attempt
    env = prepare(attempt)
    for name in ['generate', 'validate']:
        assert run(steps('respond-to-mention')[name], env).returncode == 0
    work, pubenv = publish_env(tmp_path, env)
    assert run(steps('publish')['pr'], {**pubenv, 'FAIL_CREATE': '1'}, work).returncode != 0
    if tampering == 'tree':
        (work / 'unexpected.txt').write_text('Unrelated work must not be published or overwritten.')
        command(['git', 'add', 'unexpected.txt'], work)
    command(['git', 'commit', '--allow-empty', '-qm', 'Changed remote branch authority'], work)
    command(['git', 'push', '-q'], work)
    remote = tmp_path / 'origin.git'
    branch = f"refs/heads/d4dassistant/Unit-{env['ATTEMPT_ID']}"
    preserved_sha = command(['git', '--git-dir', str(remote), 'rev-parse', branch], work)
    retry = tmp_path / 'retry-publication'
    command(['git', 'clone', '-q', '--no-checkout', str(remote), str(retry)], tmp_path)
    command(['git', 'checkout', '-q', '--detach', pubenv['TRUSTED_SHA']], retry)
    Path(env['EVENTS']).unlink()
    result = run(steps('publish')['pr'], pubenv, retry)
    assert result.returncode != 0
    assert ('different evidence' if tampering == 'tree' else 'different base') in result.stdout
    assert command(['git', '--git-dir', str(remote), 'rev-parse', branch], work) == preserved_sha
    events = [json.loads(line) for line in Path(env['EVENTS']).read_text().splitlines()]
    assert not any(e['command'] == 'gh' or e['args'][0] == 'push' for e in events)


def test_workflow_authority_credentials_failure_retention_and_dispatch_contract():
    jobs = workflow()['jobs']
    generation = jobs['respond-to-mention']
    selected = steps('respond-to-mention')
    assert generation['if'] == "needs.check-mention.outputs.qualified-mention == 'true'"
    assert generation['permissions'] == {'contents': 'read'}
    assert generation['defaults']['run']['working-directory'] == 'trusted'
    checkouts = [s['with'] for s in generation['steps'] if s.get('uses', '').startswith('actions/checkout@')]
    assert checkouts[0]['ref'] == '${{ needs.check-mention.outputs.trusted-sha }}'
    assert checkouts[0]['path'] == 'trusted'
    assert checkouts[1]['ref'] == '${{ needs.check-mention.outputs.source-sha }}'
    assert checkouts[1]['path'] == 'source'
    assert checkouts[1]['sparse-checkout'] == 'data/sheets_d4dassistant/inputs'
    assert all(c['persist-credentials'] is False for c in checkouts)
    assert 'PAT_FOR_PR' not in yaml.safe_dump(generation)
    assert 'secrets.ANTHROPIC_API_KEY' not in yaml.safe_dump(generation)
    assert selected['generate']['env']['ANTHROPIC_API_KEY'] == ''
    assert selected['generate']['env']['CBORG_API_KEY'] == '${{ secrets.CBORG_API_KEY }}'
    assert selected['resolve']['env']['PROVIDER'] == 'cborg'
    assert selected['resolve']['env']['ATTEMPT_ID'] == '${{ github.run_id }}-${{ github.run_attempt }}'
    for name in ['resolve', 'generate', 'validate']:
        assert 'if' not in selected[name]  # Default success dependency preserves fail-closed order.
    evidence = selected['archive']
    assert evidence['if'] == 'always()' and evidence['with']['include-hidden-files'] is True
    assert evidence['with']['if-no-files-found'] == 'error'
    assert generation['outputs']['archive'] == '${{ steps.archive.outcome }}'
    assert selected['Record attempt outcome']['if'] == 'always()'
    assert jobs['publish']['if'] == "needs.respond-to-mention.result == 'success'"
    assert jobs['report']['if'] == "always() && needs.check-mention.outputs.qualified-mention == 'true'"
    assert workflow()['concurrency']['cancel-in-progress'] is False
    producer_artifact = '${{ needs.respond-to-mention.outputs.artifact-name }}'
    assert steps('publish')['Download checked attempt']['with']['name'] == producer_artifact
    assert steps('publish')['pr']['env']['ATTEMPT_ID'] == '${{ needs.respond-to-mention.outputs.attempt-id }}'
    assert generation['outputs']['attempt-id'] == '${{ steps.identity.outputs.attempt-id }}'
    assert generation['outputs']['artifact-name'] == '${{ steps.identity.outputs.artifact-name }}'


def test_early_failure_still_records_artifact_outcome(attempt):
    _, _, env = attempt
    selected = steps('respond-to-mention')['Record attempt outcome']
    result = run(selected, {**env, 'PROVIDER_RESULT': 'failure', 'INSTALL_RESULT': 'skipped',
                           'PREPARATION_RESULT': 'skipped', 'GENERATION_RESULT': 'skipped',
                           'VALIDATION_RESULT': 'skipped'}, Path(env['RUNNER_TEMP']))
    assert result.returncode == 0, result.stderr
    outcome = Path(env['RUNNER_TEMP']) / f"assistant-attempt-{env['ATTEMPT_ID']}/workflow_outcome.txt"
    assert 'provider_configuration=failure' in outcome.read_text()
    assert 'generation=skipped' in outcome.read_text()


def test_missing_cborg_credential_refuses_despite_legacy_anthropic_key(attempt):
    _, _, env = attempt
    result = run(steps('respond-to-mention')['provider'],
                 {**env, 'CBORG_API_KEY': '', 'ANTHROPIC_API_KEY': 'synthetic-unusable-key'})
    assert result.returncode != 0
    assert 'Configure CBORG_API_KEY' in result.stdout
    assert not Path(env['EVENTS']).exists()


REPORT_HARNESS = r'''
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const context = {repo: {owner: 'fixture', repo: 'owned'}};
const github = {rest: {issues: {createComment: async args => process.stdout.write(JSON.stringify(args))}}};
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
new AsyncFunction('github', 'context', input.script)(github, context).catch(error => {
  console.error(error); process.exitCode = 1;
});
'''


@pytest.mark.parametrize('preparation,generation,validation,published,archive,url,expected', [
    ('skipped', 'skipped', 'skipped', 'skipped', 'success', '', 'failed before generation'),
    ('success', 'failure', 'skipped', 'skipped', 'success', '', 'Registered generation failed'),
    ('success', 'failure', 'skipped', 'skipped', 'failure', '', 'Registered generation failed'),
    ('success', 'success', 'failure', 'skipped', 'success', '', 'failed full/core schema validation'),
    ('success', 'success', 'success', 'failure', 'success', '', 'PR publication failed'),
    ('success', 'success', 'success', 'skipped', 'failure', '', 'evidence upload or PR publication failed'),
    ('success', 'success', 'success', 'success', 'success', 'https://example.invalid/pr/1', 'Generated the **Unit**'),
])
def test_actual_report_script_distinguishes_failure_stages(tmp_path, preparation, generation,
                                                         validation, published, archive, url, expected):
    harness = tmp_path / 'report-test.js'
    harness.write_text(REPORT_HARNESS)
    fixture = tmp_path / 'report.json'
    fixture.write_text(json.dumps({'script': steps('report')['Report back on the issue']['with']['script']}))
    env = {'DATASET': 'Unit', 'ITEM_NUMBER': '123', 'PREPARATION': preparation,
           'GENERATION': generation, 'VALIDATION': validation, 'PUBLISH_RESULT': published,
           'ARCHIVE_RESULT': archive,
           'PR_URL': url, 'RUN_URL': 'https://example.invalid/run/9001'}
    result = subprocess.run([shutil.which('node'), str(harness), str(fixture)], env=env,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    reply = json.loads(result.stdout)
    assert reply['issue_number'] == 123
    assert expected in reply['body'] and env['RUN_URL'] in reply['body']
    assert ('evidence is attached' in reply['body']) == (archive == 'success')
    assert ('evidence upload did not complete' in reply['body']) == (archive != 'success')
    if url:
        assert url in reply['body']
