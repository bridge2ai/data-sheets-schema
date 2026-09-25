"""Native permissions and denial judgments share the registered job (#2035/#2041)."""
import copy
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


def _registered(external, tmp_path, monkeypatch, render_version):
    # Every registrable agentic job renders the env form (#2307); the
    # expansion form is refused at preparation (#2369). Jobs are rendered
    # from the corpus root, as the preparers are, so the artifact paths keep
    # their portable spelling wherever the policy is later rebuilt (#2444).
    monkeypatch.chdir(tmp_path)
    # Registered jobs keep the default output paths, which the launcher's run
    # specification recomputes (#2444); no preparer sets out_dir.
    spec = replace(external, method='claudecode_agent', runtime='Claude Code',
                   condition='generic_v9', render_version=render_version, prompt_text_env=True, out_dir=None)
    instruction = tmp_path / 'instruction.md'
    instruction.write_text(spec.instruction, encoding='utf-8')
    job = {'id': 'EXTERNAL_agentic_rep1', 'instruction': str(instruction),
           'manifest': str(spec.manifest), 'bundle': str(spec.bundle),
           'render_spec': spec.render_spec(),
           # What a rendered job carries for the launcher's run specification (#2444).
           'project': spec.project, 'method': spec.method, 'label': spec.label,
           'chunks': str(spec.chunk_manifest), 'profile': spec.profile, 'runtime': spec.runtime,
           'run_date': spec.run_date, 'prompt_text_env': True,
           'outputs': {'full': str(spec.full_path), 'core': str(spec.core_path),
                       'report': str(spec.report_path)}}
    base = {'python': sys.executable, 'repository': str(tmp_path)}
    return base, job, build_command_policy(job, sys.executable, tmp_path)


@pytest.fixture
def registered(external, tmp_path, monkeypatch):
    return _registered(external, tmp_path, monkeypatch, 12)


@pytest.fixture
def phased(external, tmp_path, monkeypatch):
    """A renderer with phase history, whose helper arguments the controller enforces (#2444)."""
    return _registered(external, tmp_path, monkeypatch, 15)


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
    good = [shlex.join([*prefix, '--manifest', path, 'runs', 'check'])
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


def test_paths_with_quotes_remain_literals_when_binding_python(registered, monkeypatch):
    import prepare_registration
    base, job, _ = registered
    special = "out/children's dataset/full.yaml"
    # The instruction's registered helper lines name the same path, shell-quoted (#2444).
    instruction = Path(job['instruction'])
    def rebound(line):
        words = shlex.split(line) if line.strip().startswith(base['python'] + ' -m ') else None
        if not words or job['outputs']['full'] not in words:
            return line
        return shlex.join([special if word == job['outputs']['full'] else word for word in words])
    instruction.write_text('\n'.join(rebound(line) for line in instruction.read_text().split('\n')))
    job['outputs']['full'] = special
    job['render_spec']['agentic_artifact_paths']['full'] = special
    real = prepare_registration.spec_for
    def launched(value):
        spec = real(value)
        spec._agentic_artifact_paths = {**spec._agentic_artifact_paths, 'full': special}
        return spec
    monkeypatch.setattr(prepare_registration, 'spec_for', launched)
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
    later = ('literal_admission', 'lookup_literal_admission', 'helper_arguments')
    return {**{k: v for k, v in policy.items() if k not in later}, 'version': 4}


def test_every_registered_spelling_is_admitted_as_written(registered):
    base, job, policy = registered
    assert policy['version'] == POLICY_VERSION == 6 and policy['literal_admission'] == LITERAL_ADMISSION
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
    receipts = _roster(policy, 'runs', 'check', manifest=manifest)
    command = {
        'reflowed': shlex.join([python, '-c', fixed + '\n\n']),
        'comment': shlex.join([python, '-c', fixed]) + ' # checked',
        'double_quoted_manifest': ' '.join([shlex.join([python, '-m', 'data_sheets_schema.cli']),
                                            '--manifest', '"' + manifest + '"', 'runs', 'check']),
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
        command = sep.join([shlex.quote(python), '-m', 'data_sheets_schema.cli', 'runs', 'check', '--strict'])
        assert classify_program_command(command, python, set(), policy)[0] == 'prescribed', repr(sep)


def test_the_refusal_names_the_registered_spelling(registered):
    _, _, policy = registered
    python = policy['python']
    fixed = next(p['code'] for p in policy['programs'] if not p['arguments'])
    example = next(e for e in policy['command_examples'] if shlex.split(e)[2] == fixed)
    _, basis = classify_program_command(shlex.join([python, '-c', fixed + '\n\n']), python, set(), policy)
    assert basis.endswith('run the registered spelling exactly: ' + example)
    manifest = policy['manifest_paths'][0]
    receipts = _roster(policy, 'runs', 'check', manifest=manifest)
    _, basis = classify_program_command(receipts + ' --label $X', python, set(), policy)
    assert basis.endswith('run the registered spelling exactly: ' + receipts + ' …')


def test_a_registration_whose_recorder_line_the_runtime_would_refuse_is_refused_at_build(external, tmp_path):
    """#2369, #2282: the expansion form would be refused at the run's last step; preparation refuses it."""
    spec = replace(external, method='claudecode_agent', runtime='Claude Code',
                   condition='generic_v9', render_version=12, out_dir=None)
    assert '${D4D_LAUNCH_INSTRUCTION' in spec.instruction
    instruction = tmp_path / 'instruction.md'
    instruction.write_text(spec.instruction, encoding='utf-8')
    job = {'id': 'EXTERNAL_agentic_rep1', 'instruction': str(instruction),
           'manifest': str(spec.manifest), 'bundle': str(spec.bundle), 'render_spec': spec.render_spec(),
           'project': spec.project, 'method': spec.method, 'label': spec.label,
           'chunks': str(spec.chunk_manifest), 'profile': spec.profile, 'runtime': spec.runtime,
           'run_date': spec.run_date,
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
    command = _roster(policy, 'runs', 'check', manifest=policy['manifest_paths'][0]) + ' ' + RUNTIME_REFUSED[name]
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
    base = _roster(policy, 'runs', 'check', manifest=policy['manifest_paths'][0])
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
    assert _raw_words("a 'b c' --o='{x,y}' \"d\"'e'") == [
        ('a', 1, 'a'), ("'b c'", 1, 'b c'), ("--o='{x,y}'", 2, '--o={x,y}'), ('"d"\'e\'', 2, 'de')]
    assert _too_complex("x '{\"a\":1,\"b\":2}'") is None                 # one quoted piece: admitted
    assert _too_complex("x --o='{\"a\":1,\"b\":2}'") == 'a brace pattern in an argument joined from quoted pieces'
    assert _too_complex('x {"a"}') == 'a brace followed by a quote'


# --- #2398 verification: the rest of the joined-argument checks, the boundary and the handlers -----

JOINED_REFUSED = {
    'collapsed_equals': "--label '='x",
    'collapsed_equals_after_empty': '--label ""=y',
    'collapsed_equals_after_space': '--note "a "=b',
    'collapsed_tilde_bracket': "--label '~''['",
    'escaped_brace_joined': "--pattern='\\{x\\}'",
    'escaped_close_brace': "--label a'{\\}'",
    'escaped_open_brace': "--label x'{\\{'",
    'range_joined': "--label='{1..3}'",
    'nel_inside_joined_brace': "--label x'{a" + chr(0x85) + ",b}'",
    'bare_equals': '--label =',
    'proc_environ': '--label /proc/self/environ',
    'proc_environ_quoted': "--label '/proc/1/environ'",
    'lone_surrogate': "--label '" + chr(0xD800) + "'",
}


@pytest.mark.parametrize('name', sorted(JOINED_REFUSED))
def test_the_rest_of_what_the_runtime_refuses_is_refused_first(registered, name):
    """The runtime's joined-argument checks (`si`, `ai`, `oin` and `sin` once quotes are removed,
    `ii` with JavaScript's whitespace), its parse error on a bare `=`, its /proc/*/environ check,
    and its lone-surrogate check, which must refuse, not crash the controller."""
    _, _, policy = registered
    python = policy['python']
    command = _roster(policy, 'runs', 'check', manifest=policy['manifest_paths'][0]) + ' ' + JOINED_REFUSED[name]
    assert classify_program_command(command, python, set(), _legacy(policy))[0] == 'prescribed'
    verdict, basis = classify_program_command(command, python, set(), policy)
    assert verdict == 'not_prescribed' and 'does not disqualify the attempt' in basis, basis


@pytest.mark.parametrize('code', [0xA0, 0x3000, 0x0D, 0x0B, 0x0C])
def test_trailing_characters_the_runtime_checks_before_trimming_are_refused(registered, code):
    """The Kjn and zm checks read the untrimmed text: a trailing one on an argument-rule command is
    refused even though the trim removes it before the rule is matched."""
    _, _, policy = registered
    python = policy['python']
    command = _roster(policy, 'runs', 'check', manifest=policy['manifest_paths'][0]) + ' --strict' + chr(code)
    assert classify_program_command(command, python, set(), _legacy(policy))[0] == 'prescribed'
    assert classify_program_command(command, python, set(), policy)[0] == 'not_prescribed'


def test_the_parse_limit_is_ten_thousand_utf16_units(registered):
    _, _, policy = registered
    python = policy['python']
    base = _roster(policy, 'runs', 'check', manifest=policy['manifest_paths'][0]) + ' --label '
    judge = lambda command: classify_program_command(command, python, set(), policy)[0]
    assert judge(base + 'x' * (10_000 - len(base))) == 'prescribed'
    assert judge(base + 'x' * (10_001 - len(base))) == 'not_prescribed'
    astral = chr(0x1F600)                                               # one code point, two UTF-16 units
    assert judge(base + 'x' * (10_000 - len(base) - 2) + astral) == 'prescribed'
    assert judge(base + 'x' * (10_000 - len(base) - 1) + astral) == 'not_prescribed'


def test_a_parser_out_of_memory_is_refused_not_a_controller_failure(registered, monkeypatch):
    import native_command_policy as ncp
    _, _, policy = registered
    python = policy['python']
    real = ncp.program_key

    def exhausted(program):
        if 'EXHAUSTED' in program:
            raise MemoryError('Parser stack overflowed')
        return real(program)
    monkeypatch.setattr(ncp, 'program_key', exhausted)
    verdict, basis = classify_program_command(shlex.join([python, '-c', 'EXHAUSTED = 1']), python, set(), policy)
    assert (verdict, basis) == ('not_prescribed', 'an invalid inline Python program')


def test_the_guidance_names_when_a_refusal_carries_the_spelling(registered):
    _, _, policy = registered
    assert 'where the call keeps the registered interpreter and command, it names the registered spelling' \
        in command_guidance(policy)


# --- #2443: a read-only lookup the runtime would refuse is refused first ---------------------------

def test_a_lookup_the_runtime_refuses_is_refused_first_without_disqualifying(registered):
    from run_native_canary import _classify_command
    base, job, policy = registered
    python, bundle = policy['python'], job['bundle']
    escaped = 'grep -n Data\\ Use ' + shlex.quote(bundle)
    verdict, basis = _classify_command(escaped, python, set(), policy)
    assert verdict == 'not_prescribed' and 'does not disqualify the attempt' in basis, basis
    assert denial_problems(classify(policy, escaped)) == []
    # A version-5 recording replays exactly as it was registered.
    assert _classify_command(escaped, python, set(), {k: v for k, v in policy.items()
                                                      if k != 'lookup_literal_admission'})[0] == 'prescribed'
    for admitted in ('grep -n ' + shlex.quote('Data Use') + ' ' + shlex.quote(bundle) + ' | head -5',
                     "sed -n '1,20p' " + shlex.quote(bundle), 'wc -l ' + shlex.quote(bundle)):
        assert _classify_command(admitted, python, set(), policy)[0] == 'prescribed', admitted


# --- #2444: a helper called with other arguments is refused before it runs ------------------------

def _helper_spec(job):
    from prepare_registration import spec_for
    return spec_for(job)


def test_a_helper_with_other_arguments_is_refused_first_and_named_its_registered_spelling(phased):
    base, job, policy = phased
    python = policy['python']
    spellings = policy['helper_arguments']['spellings']
    assert set(spellings) >= {'receipts', 'derive'}
    for command in (line for lines in spellings.values() for line in lines):
        assert classify_program_command(command, python, set(), policy)[0] == 'prescribed', command
    bare = shlex.join([python, '-m', 'data_sheets_schema.cli', 'receipts', 'check', '--strict'])
    derived = shlex.join([python, '-m', 'data_sheets_schema.cli', 'derive', 'core',
                          '--full', job['outputs']['full'], '--out', '/elsewhere/core.yaml'])
    for command, kind in ((bare, 'receipts'), (derived, 'derive')):
        verdict, basis = classify_program_command(command, python, set(), policy)
        assert verdict == 'not_prescribed' and 'does not disqualify the attempt' in basis, basis
        assert basis.endswith('run a registered spelling exactly: ' + ' or '.join(spellings[kind]))
        assert denial_problems(classify(policy, command)) == []
        # A recording without the helper arguments replays unchanged.
        assert classify_program_command(command, python, set(), _legacy(policy))[0] == 'prescribed'
    guidance = command_guidance(policy)
    assert '## Registered helper commands' in guidance
    assert all(line in guidance for lines in spellings.values() for line in lines)
    assert '## Registered helper commands' not in command_guidance(_legacy(policy))


def test_the_phase_history_no_longer_stops_on_a_helper_the_controller_refuses(phased):
    from native_phase_history import PhaseHistory
    base, job, policy = phased
    bare = shlex.join([policy['python'], '-m', 'data_sheets_schema.cli', 'receipts', 'check', '--strict'])
    event = {'type': 'assistant', 'message': {'content': [
        {'type': 'tool_use', 'id': 'variant', 'name': 'Bash', 'input': {'command': bare}}]}}
    current = PhaseHistory(_helper_spec(job), repository=base['repository'], command_policy=policy)
    current.observe(event)
    assert current.report()['problems'] == []
    legacy = PhaseHistory(_helper_spec(job), repository=base['repository'], command_policy=_legacy(policy))
    legacy.observe(event)
    assert any('helper arguments differ' in problem for problem in legacy.report()['problems'])


def test_a_launcher_spec_that_disagrees_with_the_rendered_paths_fails_preparation(phased, monkeypatch):
    import prepare_registration
    base, job, _ = phased
    real = prepare_registration.spec_for
    def moved(value):
        spec = real(value)
        spec._agentic_artifact_paths = {**spec._agentic_artifact_paths, 'core': '/elsewhere/core.yaml'}
        return spec
    monkeypatch.setattr(prepare_registration, 'spec_for', moved)
    with pytest.raises(ValueError, match="launcher's run specification"):
        build_command_policy(job, base['python'], base['repository'])



# --- the second review of policy 6 (#2483, #2485) ------------------------------------------------

def test_double_quoted_lookup_patterns_the_runtime_runs_stay_admitted(registered):
    """Replayed 2.1.272 transcripts ran these; only the runtime's own pre-parse checks refuse (#2483)."""
    from run_native_canary import _classify_command
    base, job, policy = registered
    bundle = shlex.quote(job['bundle'])
    for command in ('grep -n -E "audit\\.json|receipt" ' + bundle, 'grep -n "^MIT$\\|License" ' + bundle,
                    "grep -n 'Data Use' " + bundle + ' | head -5'):
        assert _classify_command(command, policy['python'], set(), policy)[0] == 'prescribed', command
    for refused in ('grep -n Data\\ Use ' + bundle, "grep -n '/proc/self/environ' " + bundle):
        verdict, basis = _classify_command(refused, policy['python'], set(), policy)
        assert verdict == 'not_prescribed' and 'or use the Read tool' in basis, refused
    # The environ check reads each argument, as the runtime does.
    assert _classify_command('grep -n /proc/ ' + bundle + ' | grep /environ', policy['python'], set(),
                             policy)[0] == 'prescribed'
    guidance = command_guidance(policy)
    assert ('\nQuote each lookup pattern and path with single quotes, or use the Read tool; a spelling the '
            'runtime cannot read literally is refused before it runs, and that refusal does not disqualify '
            'the attempt.\n') in guidance


def test_renderers_without_phase_history_keep_their_helper_admission(registered):
    base, job, policy = registered
    assert 'helper_arguments' not in policy and policy['lookup_literal_admission'] == 1
    bare = shlex.join([policy['python'], '-m', 'data_sheets_schema.cli', 'receipts', 'check', '--strict'])
    assert classify_program_command(bare, policy['python'], set(), policy)[0] == 'prescribed'
    assert '## Registered helper commands' not in command_guidance(policy)


def test_a_helper_the_run_does_not_register_is_refused_without_an_empty_spelling(phased):
    base, job, policy = phased
    view = copy.deepcopy(policy)
    view['helper_arguments']['spellings'].pop('receipts')
    bare = shlex.join([policy['python'], '-m', 'data_sheets_schema.cli', 'receipts', 'check', '--strict'])
    verdict, basis = classify_program_command(bare, policy['python'], set(), view)
    assert verdict == 'not_prescribed' and basis.endswith('this run registers no call to this helper; do not call it')
    assert '--write' in command_guidance(policy)


def test_helper_paths_resolve_against_the_registered_repository(phased, tmp_path, monkeypatch):
    """A relative spelling matches only as the child, whose cwd is the repository, would resolve it."""
    base, job, policy = phased
    receipts = policy['helper_arguments']['spellings']['receipts'][0]
    words = shlex.split(receipts)
    bundle = words.index('--bundle') + 1
    relative = os.path.relpath(words[bundle], base['repository'])
    words[bundle] = relative
    command = shlex.join(words)
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert classify_program_command(command, policy['python'], set(), policy)[0] == 'prescribed'


def test_a_rendered_receipt_path_the_launcher_does_not_share_fails_preparation(phased):
    base, job, _ = phased
    job['render_spec']['agentic_artifact_paths']['receipt'] = '/elsewhere/receipt.yaml'
    with pytest.raises(ValueError, match="launcher's run specification"):
        build_command_policy(job, base['python'], base['repository'])


def test_the_evidence_protocol_version_is_read_from_the_recorded_policy(phased, monkeypatch):
    """A later commit that remaps renderers to protocols does not change a recorded policy's verdicts (#2490)."""
    import data_sheets_schema.evidence_assertions as evidence
    base, job, policy = phased
    assert policy['helper_arguments']['protocol_version'] == evidence.protocol_for_renderer(15)
    registered = policy['helper_arguments']['spellings'].get('evidence')
    assert registered
    monkeypatch.setattr(evidence, 'protocol_for_renderer', lambda version: 999)
    for command in registered:
        assert classify_program_command(command, policy['python'], set(), policy)[0] == 'prescribed', command



# --- the third review (#2494) --------------------------------------------------------------------

def test_the_helper_check_starts_where_the_launchers_review_phase_history(external, tmp_path, monkeypatch):
    import run_native_canary
    from native_command_policy import PHASE_HISTORY_RENDERER
    assert run_native_canary.PHASE_HISTORY_RENDERER is PHASE_HISTORY_RENDERER == 13
    _, _, at = _registered(external, tmp_path, monkeypatch, PHASE_HISTORY_RENDERER)
    assert 'helper_arguments' in at


def test_a_launcher_spec_naming_another_interpreter_fails_preparation(phased, monkeypatch):
    import prepare_registration
    base, job, _ = phased
    real = prepare_registration.spec_for
    def elsewhere(value):
        spec = real(value)
        spec._agentic_toolchain = {**spec._agentic_toolchain, 'python': '/elsewhere/python'}
        return spec
    monkeypatch.setattr(prepare_registration, 'spec_for', elsewhere)
    with pytest.raises(ValueError, match='another interpreter'):
        build_command_policy(job, base['python'], base['repository'])
