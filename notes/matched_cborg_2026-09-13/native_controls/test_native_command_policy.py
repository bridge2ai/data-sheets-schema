"""Native permissions and denial judgments share the registered job (#2035/#2041)."""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests.test_generation_manifest_identity import external
from native_command_policy import (build_command_policy, command_guidance,
                                   permission_arguments, program_key, python_commands, validated_command_policy)
from run_native_canary import classify_denials, denial_problems


@pytest.fixture
def registered(external, tmp_path):
    # Every registrable agentic job renders the env form (#2307); the
    # expansion form is refused at preparation (#2369).
    spec = replace(external, method='claudecode_agent', runtime='Claude Code',
                   condition='generic_v9', render_version=12, prompt_text_env=True)
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


def test_standalone_overlay_preparer_without_test_import_paths(registered, tmp_path):
    base, job, _ = registered
    controls = Path(__file__).resolve().parent
    repository = controls.parents[2]
    # Python stands in only for the version-reporting executable; no model or
    # native CLI is invoked. The actual preparer must build and pin the policy.
    base.update(repository=str(repository),
                claude_version=subprocess.check_output([sys.executable, '--version'], text=True).strip(),
                generation={'jobs':[{**job, 'canary':True, 'execution_arm':'agentic', 'profile':'neutral'}],
                            'effort_policy':{'fixture':'offline'}})
    registration = tmp_path/'registration.json'
    registration.write_text(json.dumps(base))
    overlay = tmp_path/'overlay.json'
    result = subprocess.run([sys.executable, str(controls/'prepare_overlay.py'),
        '--registration', str(registration), '--output', str(overlay), '--claude-executable', sys.executable],
        cwd=tmp_path, env={'PATH':os.environ.get('PATH',''), 'PYTHONPATH':str(repository/'src')},
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    value = json.loads(overlay.read_text())
    assert value['per_job_command_policy'][job['id']]['pretool_control']['event'] == 'PreToolUse'
    assert str(controls/'native_control.py') in value['pinned_files']


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
        render_spec=lambda: job['render_spec'], input_identity=lambda: {}, render_version=12, prompt_text_env=True))
    monkeypatch.delenv('CBORG_API_KEY', raising=False)
    monkeypatch.setattr(sys, 'argv', ['run_native_canary', '--overlay', str(overlay),
                                    '--review', str(review), '--job', job['id']])
    with pytest.raises(BudgetStop, match='command policy is invalid'):
        runner.main()
    assert not (tmp_path / 'attempts').exists()


# --- #2369: the controller refuses a spelling the runtime's rules would not admit -----------------

import re

from native_command_policy import (LITERAL_ADMISSION, POLICY_VERSION, _runtime_rules, _unread_shell,
                                   classify_program_command, runtime_literal_problem)


def _roster(policy, *words, manifest=None):
    return shlex.join([policy['python'], '-m', 'data_sheets_schema.cli',
                       *(['--manifest', manifest] if manifest else []), *words])


def _legacy(policy):
    """The same policy as a version-4 recording carries it."""
    return {**{k: v for k, v in policy.items() if k != 'literal_admission'}, 'version': 4}


def test_every_registered_spelling_is_admitted_as_written(registered):
    base, job, policy = registered
    assert policy['version'] == POLICY_VERSION == 5 and policy['literal_admission'] == LITERAL_ADMISSION
    python = policy['python']
    lines = [line.strip() for line in Path(job['instruction']).read_text().splitlines()]
    led = [line for line in lines if line.startswith(python + ' ') and not line.startswith(python + ' -c ')
           and not re.search(r'<[a-z_]+>', line)]
    assert any(' provenance record ' in line for line in led) and any(' receipts check ' in line for line in led)
    for command in [*policy['command_examples'], *led]:
        assert runtime_literal_problem(command, policy) is None, command[:160]
        assert classify_program_command(command, python, set(), policy)[0] == 'prescribed', command[:160]


def test_the_rules_decode_to_the_registered_spellings(registered):
    _, _, policy = registered
    exact, prefixes = _runtime_rules(policy)
    python = policy['python']
    for program in policy['programs']:
        spelling = shlex.join([python, '-c', program['code']])
        if program['arguments']:
            assert re.sub(r'[ \t]+', ' ', spelling) in prefixes
        else:
            assert spelling in exact
    for example in policy['command_examples']:
        assert example in exact or any(re.sub(r'[ \t]+', ' ', example).startswith(p + ' ') for p in prefixes)


RESPELLINGS = ['reflowed', 'comment', 'double_quoted_manifest', 'variable', 'braced_variable',
               'continuation', 'glob', 'carriage_return', 'unicode_space']


@pytest.mark.parametrize('name', RESPELLINGS)
def test_a_respelling_is_refused_by_the_controller_and_does_not_disqualify(registered, name):
    _, _, policy = registered
    python = policy['python']
    fixed = next(p['code'] for p in policy['programs'] if not p['arguments'])
    manifest = policy['manifest_paths'][0]
    receipts = _roster(policy, 'receipts', 'check', manifest=manifest)
    command = {
        'reflowed': shlex.join([python, '-c', fixed + '\n\n']),
        'comment': shlex.join([python, '-c', fixed]) + ' # checked',
        'double_quoted_manifest': ' '.join([shlex.join([python, '-m', 'data_sheets_schema.cli']),
                                            '--manifest', '"' + manifest + '"', 'receipts', 'check']),
        'variable': receipts + ' --label $LABEL',
        'braced_variable': receipts + ' --label "${LABEL}"',
        'continuation': receipts + ' \\\n  --strict',
        'glob': receipts + ' --label x*',
        'carriage_return': receipts + ' --label x\ry',
        'unicode_space': receipts + ' --label\u00a0x',
    }[name]
    # The same meaning, as a version-4 recording classifies it: the replay of
    # earlier evidence is unchanged, and this is the call #2369 names.
    assert classify_program_command(command, python, set(), _legacy(policy))[0] == 'prescribed'
    verdict, basis = classify_program_command(command, python, set(), policy)
    assert verdict == 'not_prescribed', basis
    assert 'respelled' in basis and 'does not disqualify the attempt' in basis
    assert denial_problems(classify(policy, command)) == []


def test_runs_of_spaces_between_registered_words_are_admitted(registered):
    _, _, policy = registered
    python = policy['python']
    for sep in ('  ', '\t', ' \t '):
        command = sep.join([shlex.quote(python), '-m', 'data_sheets_schema.cli', 'receipts', 'check', '--strict'])
        assert classify_program_command(command, python, set(), policy)[0] == 'prescribed', repr(sep)


def test_the_refusal_names_the_registered_spelling(registered):
    _, _, policy = registered
    python = policy['python']
    fixed = next(p['code'] for p in policy['programs'] if not p['arguments'])
    example = next(e for e in policy['command_examples'] if shlex.split(e)[2] == fixed)
    _, basis = classify_program_command(shlex.join([python, '-c', fixed + '\n\n']), python, set(), policy)
    assert basis.endswith('run the registered spelling exactly: ' + example)
    manifest = policy['manifest_paths'][0]
    receipts = _roster(policy, 'receipts', 'check', manifest=manifest)
    _, basis = classify_program_command(receipts + ' --label $X', python, set(), policy)
    assert basis.endswith('run the registered spelling exactly: ' + receipts + ' …')


def test_a_registration_whose_recorder_line_the_runtime_would_refuse_is_refused_at_build(external, tmp_path):
    """#2369, #2282: the expansion form would be refused at the run's last step; preparation refuses it."""
    spec = replace(external, method='claudecode_agent', runtime='Claude Code',
                   condition='generic_v9', render_version=12)
    assert '${D4D_LAUNCH_INSTRUCTION' in spec.instruction
    instruction = tmp_path / 'instruction.md'
    instruction.write_text(spec.instruction, encoding='utf-8')
    job = {'id': 'EXTERNAL_agentic_rep1', 'instruction': str(instruction),
           'manifest': str(spec.manifest), 'bundle': str(spec.bundle), 'render_spec': spec.render_spec(),
           'outputs': {'full': str(spec.full_path), 'core': str(spec.core_path), 'report': str(spec.report_path)}}
    with pytest.raises(ValueError, match='not admitted as written .*a \\$ variable or expansion.*provenance record'):
        build_command_policy(job, sys.executable, tmp_path)


def test_the_guidance_says_a_respelling_refusal_does_not_disqualify(registered):
    _, _, policy = registered
    assert 'refused before it runs' in command_guidance(policy)
    assert 'does not disqualify the attempt' in command_guidance(policy)
    assert 'does not disqualify' not in command_guidance(_legacy(policy))


@pytest.mark.parametrize('text, reason', [
    ("a '$HOME' b", None), ("a 'x'\"'\"'y' b", None), ('a "x y" b', None), ('a x#y', None),
    ("a 'multi\nline'", None), ('a "$X"', 'a $ variable or expansion'), ('a `x`', 'a backtick'),
    ("a 'x", 'an unterminated quote'), ('a #y', 'a comment'), ('a\nb', 'a line break outside quotes'),
    ('a "\\x"', 'a backslash escape or line continuation'), ('a ~/x', 'a glob, brace or tilde expansion'),
    ('a {b,c}', 'a glob, brace or tilde expansion'), ('a\u2003b', 'a control character or non-ASCII whitespace'),
])
def test_what_the_runtime_reads_literally(text, reason):
    assert _unread_shell(text) == reason


# --- #2398 review: the runtime's own checks before matching, and the surviving mutants ----------

from native_command_policy import _JS_TRIM, _literal_rule, _mask_quoted_braces, _raw_words, _too_complex


RUNTIME_REFUSED = {
    'escaped_space': "--label 'a\\ b'",
    'zsh_equals': '--label =x',
    'zsh_equals_quoted': "--label ' =x'",
    'zsh_range': "--label '<1-2>'",
    'zsh_tilde_bracket': "--label 'a~[b'",
    'zero_width_space_quoted': "--label 'a\u200bb'",
    'zero_width_space': '--label a\u200bb',
    'newline_hash_single': "--label 'a\n#b'",
    'newline_hash_double': '--label "a\n#b"',
    'brace_in_joined_argument': "--label='{\"a\":1,\"b\":2}'",
    'brace_after_apostrophe': "--label 'x'\"'\"'{a,b}'",
    'name_inside_single_quotes': "--label 'a$HOME'",
    'newline_inside_quotes': "--label 'a\nb'",
}


@pytest.mark.parametrize('name', sorted(RUNTIME_REFUSED))
def test_what_the_runtime_refuses_before_matching_is_refused_first(registered, name):
    """The pinned runtime's pre-parse checks read the raw text inside quotes too; its brace check
    reads an argument joined from pieces; it re-quotes text with a newline or $NAME before matching."""
    _, _, policy = registered
    python = policy['python']
    command = _roster(policy, 'receipts', 'check', manifest=policy['manifest_paths'][0]) + ' ' + RUNTIME_REFUSED[name]
    assert classify_program_command(command, python, set(), _legacy(policy))[0] == 'prescribed'
    verdict, basis = classify_program_command(command, python, set(), policy)
    assert verdict == 'not_prescribed' and 'does not disqualify the attempt' in basis, basis


def test_trimming_follows_javascript_not_python(registered):
    """The runtime trims with JavaScript's trim(), which keeps \\x1c-\\x1f and \\x85."""
    _, _, policy = registered
    python = policy['python']
    fixed = next(p['code'] for p in policy['programs'] if not p['arguments'])
    example = shlex.join([python, '-c', fixed])
    for tail in ('\x1f', '\x1c', '\x85'):
        assert (example + tail).strip() == example and (example + tail).strip(_JS_TRIM) != example
        assert classify_program_command(example + tail, python, set(), _legacy(policy))[0] == 'prescribed'
        assert classify_program_command(example + tail, python, set(), policy)[0] == 'not_prescribed', repr(tail)
    for tail in (' ', '\t', '\n', '\u00a0'):                            # trimmed by both
        assert classify_program_command(example + tail, python, set(), policy)[0] == 'prescribed', repr(tail)


def test_a_command_longer_than_the_runtime_parses_is_refused(registered):
    _, _, policy = registered
    python = policy['python']
    base = _roster(policy, 'receipts', 'check', manifest=policy['manifest_paths'][0])
    assert classify_program_command(base + ' --label ' + 'x' * (9_990 - len(base)), python, set(), policy)[0] == 'prescribed'
    assert classify_program_command(base + ' --label ' + 'x' * 10_000, python, set(), policy)[0] == 'not_prescribed'


def _argument_program_policy(code):
    python = sys.executable
    prefix = shlex.join([python, '-c', code])
    return python, prefix, {'version': 5, 'literal_admission': LITERAL_ADMISSION, 'python': python,
                            'manifest_paths': [], 'programs': [{'code': code, 'arguments': True}],
                            'command_examples': [prefix + ' out/full.yaml'],
                            'allowed_tools': [_literal_rule(prefix, arguments=True)]}


def test_an_argument_rule_reads_backslash_pairs_as_the_runtime_does():
    """Surviving mutant M03: the runtime reads `\\\\` in an argument rule as one backslash, so a
    registered program carrying two is refused as written; one is admitted."""
    python, prefix, policy = _argument_program_policy('print("a\\nb")')
    assert runtime_literal_problem(prefix + ' out/full.yaml', policy) is None
    python, prefix, policy = _argument_program_policy('print("a\\\\b")')
    assert runtime_literal_problem(prefix + ' out/full.yaml', policy) == 'a spelling no registered permission rule admits'


def test_an_argument_rule_reads_runs_of_spaces_as_one():
    """Surviving mutant M02: the rule's own prefix is normalised like the command."""
    python, prefix, policy = _argument_program_policy('x  =\t1;print(x)')
    assert runtime_literal_problem(prefix + ' out/full.yaml', policy) is None
    assert runtime_literal_problem(prefix.replace('  ', ' ') + ' out/full.yaml', policy) is None


def test_a_bound_inline_program_the_runtime_would_refuse_fails_preparation(registered, tmp_path):
    """Surviving mutant M14c: the bound examples are checked, not only the instruction's CLI lines."""
    base, job, _ = registered
    python = base['python']
    instruction = Path(job['instruction'])
    extra = tmp_path / 'with_program.md'
    extra.write_text(instruction.read_text() + '\n' + python + ' -c ' + shlex.quote('print("a\\\\b")') + ' <full_file>\n')
    with pytest.raises(ValueError, match='not admitted as written'):
        build_command_policy({**job, 'instruction': str(extra)}, python, tmp_path)


def test_a_program_too_deep_to_parse_is_refused_not_a_controller_failure(registered):
    _, _, policy = registered
    python = policy['python']
    for program in ('1' + '+1' * 5000, 'not ' * 5000 + 'x'):
        verdict, basis = classify_program_command(shlex.join([python, '-c', program]), python, set(), policy)
        assert (verdict, basis) == ('not_prescribed', 'an invalid inline Python program')


def test_the_runtime_helpers_read_quotes_as_the_runtime_does():
    assert _mask_quoted_braces("a '{x}' \"{y}\" {z}") == "a ' x}' \" y}\" {z}"
    assert _raw_words("a 'b c' --o='{x,y}' \"d\"'e'") == [('a', 1), ("'b c'", 1), ("--o='{x,y}'", 2), ('"d"\'e\'', 2)]
    assert _too_complex("x '{\"a\":1,\"b\":2}'") is None                 # one quoted piece: admitted
    assert _too_complex("x --o='{\"a\":1,\"b\":2}'") == 'a brace pattern in an argument joined from quoted pieces'
    assert _too_complex('x {"a"}') == 'a brace followed by a quote'
