"""Native permissions and denial judgments share the registered job (#2035/#2041)."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shlex
import sys
from types import SimpleNamespace

import pytest

from tests.test_generation_manifest_identity import external
from native_command_policy import (build_command_policy, command_guidance,
                                   permission_arguments, program_key, python_commands, validated_command_policy)
from run_native_canary import classify_denials, denial_problems


@pytest.fixture
def registered(external, tmp_path):
    spec = replace(external, method='claudecode_agent', runtime='Claude Code',
                   condition='generic_v9', render_version=12)
    instruction = tmp_path / 'instruction.md'
    instruction.write_text(spec.instruction, encoding='utf-8')
    job = {'id': 'EXTERNAL_agentic_rep1', 'instruction': str(instruction),
           'manifest': str(spec.manifest), 'bundle': str(spec.bundle),
           'render_spec': spec.render_spec(),
           'outputs': {'full': str(spec.full_path), 'core': str(spec.core_path),
                       'report': str(spec.report_path)}}
    base = {'python': sys.executable, 'repository': str(tmp_path)}
    return base, job, build_command_policy(job, sys.executable, tmp_path)


def classify(policy, *commands):
    return classify_denials(
        [{'tool_name': 'Bash', 'tool_input': {'command': command}} for command in commands],
        instruction_text='', python=policy['python'], repository='/unused',
        output_directories=[], readable_inputs=[], command_policy=policy)


def test_actual_instruction_and_delegated_playbook_have_five_programs(registered):
    base, job, policy = registered
    programs = [item['code'] for item in policy['programs']]
    assert len(programs) == 5
    for required in ('linkml.validator.cli', 'linkml_term_validator.cli',
                     'check_run', 'check_report', 'original_sha256'):
        assert sum(required in code for code in programs) == 1
    assert all('<full_file>' not in code and '<bundle>' not in code for code in programs)
    commands = policy['command_examples']
    judgments = classify(policy, *commands)
    assert all(item['classification'] == 'prescribed' for item in judgments), judgments
    assert len(denial_problems(judgments)) == len(commands)
    assert all(command in command_guidance(policy) for command in commands)
    # Exact copies of already concrete instruction programs remain allowed;
    # formatting the freeze program must not drop its final newline.
    for argv in python_commands(Path(job['instruction']).read_text(), base['python']):
        assert any(item['code'] == argv[2] for item in policy['programs'])
    delivered = permission_arguments(policy)
    assert delivered[:3] == ['--input-format', 'stream-json', '--settings'] and len(delivered) == 4
    assert json.loads(delivered[3]) == {'permissions': {'allow': policy['allowed_tools']}}


def test_arbitrary_modified_and_other_jobs_programs_are_not_prescribed(registered):
    base, job, policy = registered
    py = base['python']
    good = next(item['code'] for item in policy['programs'] if 'check_report' in item['code'])
    modified = good + '\nprint("extra program")'
    wrong_path = good.replace(job['outputs']['full'], '/another/record.yaml')
    forbidden = [shlex.join([py, '-c', code]) for code in
                 ('print("arbitrary")', modified, wrong_path, 'not valid python !')]
    forbidden += [shlex.join([py, '-c', good, 'extra-argument'])]
    assert all(item['classification'] == 'not_prescribed' for item in classify(policy, *forbidden))


def test_registered_manifest_has_no_any_subcommand_rule(registered):
    base, job, policy = registered
    py = base['python']
    prefix = [py, '-m', 'data_sheets_schema.cli']
    good = [shlex.join([*prefix, '--manifest', path, 'receipts', 'check'])
            for path in policy['manifest_paths']]
    bad = [shlex.join([*prefix, '--manifest', job['manifest'], 'runs', 'select']),
           shlex.join([*prefix, '--manifest', '/another/manifest.yaml', 'runs', 'list'])]
    assert all(x['classification'] == 'prescribed' for x in classify(policy, *good))
    assert all(x['classification'] == 'not_prescribed' for x in classify(policy, *bad))
    assert not any('--manifest *)' in rule or rule == f'Bash({py} -c *)'
                   for rule in policy['allowed_tools'])
    # A wildcard is allowed only at the very end, to admit arguments.
    assert all('*' not in rule.removesuffix(' *)') for rule in policy['allowed_tools'])


@pytest.mark.parametrize('mutation', ['missing', 'extra-rule', 'other-job', 'legacy-global'])
def test_policy_must_rebuild_exactly_before_launch(registered, mutation):
    base, job, policy = registered
    overlay = {'per_job_command_policy': {job['id']: deepcopy(policy)}}
    assert validated_command_policy(overlay, base, job) == policy
    if mutation == 'missing':
        overlay.clear()
    elif mutation == 'extra-rule':
        overlay['per_job_command_policy'][job['id']]['allowed_tools'].append('Bash(*)')
    elif mutation == 'other-job':
        overlay['per_job_command_policy']['another'] = overlay['per_job_command_policy'].pop(job['id'])
    else:
        overlay['allowed_tools'] = ['Bash(*)']
    with pytest.raises(ValueError, match='differs'):
        validated_command_policy(overlay, base, job)


def test_paths_with_quotes_remain_literals_when_binding_python(registered):
    base, job, _ = registered
    special = "out/children's dataset/full.yaml"
    job['outputs']['full'] = special
    job['render_spec']['agentic_artifact_paths']['full'] = special
    policy = build_command_policy(job, base['python'], base['repository'])
    report = next(p['code'] for p in policy['programs'] if 'check_report' in p['code'])
    import ast
    constants = [n.value for n in ast.walk(ast.parse(report)) if isinstance(n, ast.Constant)]
    assert special in constants
    assert all(x['classification'] == 'prescribed' for x in classify(policy, *policy['command_examples']))


def test_a_new_wildcard_program_fails_closed_instead_of_granting_more_python(registered):
    base, job, _ = registered
    instruction = Path(job['instruction'])
    instruction.write_text(instruction.read_text() + '\n' +
                           shlex.join([base['python'], '-c', 'print(*["literal"])']) + '\n')
    with pytest.raises(ValueError, match='literal asterisk'):
        build_command_policy(job, base['python'], base['repository'])


def test_an_unknown_artifact_placeholder_fails_preparation(registered):
    base, job, _ = registered
    instruction = Path(job['instruction'])
    instruction.write_text(instruction.read_text() + '\n' +
                           shlex.join([base['python'], '-c', "print('<unregistered_artifact>')"]) + '\n')
    with pytest.raises(ValueError, match='unbound placeholder'):
        build_command_policy(job, base['python'], base['repository'])


def test_extractor_handles_quoted_python_continuations_and_markdown_indent():
    py = '/installation with spaces/python'
    text = "   '" + py + "' -c \"\n   from pathlib import Path\n   print(Path('a'))\" \\\n     --flag value\n"
    rows = list(python_commands(text, py))
    assert len(rows) == 1 and rows[0][3:] == ['--flag', 'value']
    assert program_key(rows[0][2]) == program_key("from pathlib import Path\nprint(Path('a'))")


def test_permission_program_identity_never_executes_candidate_code(tmp_path):
    marker = tmp_path / 'must-not-exist'
    program_key(f"__import__('pathlib').Path({str(marker)!r}).touch()")
    assert not marker.exists()


def test_controller_rejects_a_widened_policy_before_credentials_or_attempt_creation(registered, tmp_path, monkeypatch):
    import run_native_canary as runner
    from budgeted_cborg import BudgetStop
    base, job, policy = registered
    job.update(canary=True, execution_arm='agentic', output_directories=[], input_identity={})
    base['generation'] = {'jobs': [job], 'canary_order': [job['id']]}
    registration = tmp_path / 'registration.json'
    registration.write_text(json.dumps(base))
    policy['allowed_tools'].append(f"Bash({base['python']} -c *)")
    overlay = tmp_path / 'overlay.json'
    overlay.write_text(json.dumps({
        'registration': str(registration), 'registration_sha256': runner.sha(registration),
        'allowed_jobs': [job['id']], 'pinned_files': {},
        'per_job_command_policy': {job['id']: policy},
        'per_job_environment': {job['id']: {'D4D_LAUNCH_INSTRUCTION': job['instruction']}}}))
    review = tmp_path / 'review.json'
    review.write_text(json.dumps({'verdict': 'approve', 'ci_conclusion': 'success',
        'overlay_sha256': runner.sha(overlay), 'allowed_jobs': [job['id']]}))
    monkeypatch.setattr(runner, 'verify', lambda *args: None)
    monkeypatch.setattr(runner, 'verify_history', lambda *args: None)
    monkeypatch.setattr(runner, 'spec_for', lambda *args: SimpleNamespace(
        render_spec=lambda: job['render_spec'], input_identity=lambda: {}, render_version=12))
    monkeypatch.delenv('CBORG_API_KEY', raising=False)
    monkeypatch.setattr(sys, 'argv', ['run_native_canary', '--overlay', str(overlay),
                                    '--review', str(review), '--job', job['id']])
    with pytest.raises(BudgetStop, match='command policy is invalid'):
        runner.main()
    assert not (tmp_path / 'attempts').exists()
