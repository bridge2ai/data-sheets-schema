"""Read-only admission is distinct from conformance to the frozen instruction."""
from pathlib import Path
import shlex

import pytest

from native_readonly import lookup_command, lookup_policy
from run_native_canary import _simple_command, classify_denials, command_history, denial_problems


@pytest.fixture
def policy(tmp_path):
    source = tmp_path / "children's source.txt"
    source.write_text('A neutral clinical cohort.\nA second line.\n')
    out = tmp_path / 'out'
    out.mkdir()
    job = {'bundle': str(source), 'output_directories': [str(out)]}
    return {'python': '/test/python', 'programs': [], 'manifest_paths': [],
            'readonly_lookups': lookup_policy(job, tmp_path)}


def substitute(command, policy):
    source = shlex.quote(policy['readonly_lookups']['inputs'][0])
    return command.replace('SOURCE', source)


@pytest.mark.parametrize('command', [
    "grep -n 'cohort' SOURCE | head -1",
    "grep -n 'cohort|trial' SOURCE | grep -e 'clinical' | wc -l",
    "grep -n 'cohort' -B 3 SOURCE | head -120",
    "grep -Ei -A2 -B 1 -C0 -m 3 -- 'cohort' SOURCE",
    "sed -n '1,2p' SOURCE", "sed -n '1p' SOURCE | cat -n",
    'wc -lm SOURCE', 'head -n 2 SOURCE | tail -n 1',
    'cat SOURCE SOURCE | head -c 8', 'cat SOURCE | wc -l -',
    "grep -e '-leading-dash' SOURCE", "grep -n '#literal' SOURCE",
    "grep -n '$(literal)|;<>`' SOURCE", "grep -n \"cohort$\" SOURCE",
])
def test_lookup_of_registered_bytes_is_prescribed_and_denial_disqualifies(policy, command):
    command = substitute(command, policy)
    assert lookup_command(command, policy['readonly_lookups'], _simple_command)
    denied = classify_denials([{'tool_name': 'Bash', 'tool_use_id': 'one',
                               'tool_input': {'command': command}}],
        instruction_text='', python=policy['python'], repository='/',
        output_directories=[], readable_inputs=[], command_policy=policy)
    assert denied[0]['classification'] == 'prescribed'
    assert len(denial_problems(denied)) == 1


@pytest.mark.parametrize('command', [
    'cat /unregistered/source.txt', 'grep -n x SOURCE /unregistered/source.txt',
    'grep -r x SOURCE', 'grep -f SOURCE SOURCE', 'grep --include=x x SOURCE',
    'head SOURCE > /tmp/another', 'cat SOURCE; echo extra',
    'cat SOURCE && wc -l SOURCE', 'cat SOURCE || wc -l SOURCE',
    'cat SOURCE |', '| cat SOURCE', 'cat SOURCE | cat /unregistered/source.txt',
    'cat SOURCE | python -c pass', 'cat SOURCE\necho extra',
    'cat SOURCE &', 'wc -l < SOURCE', 'cat $(echo SOURCE)', 'cat `echo SOURCE`',
    'grep "$(echo injected)" SOURCE', 'cat <(cat SOURCE)',
    'tail -f SOURCE', "sed -i '1p' SOURCE", "sed -n '1p;w /tmp/out' SOURCE",
    "sed -n 'e' SOURCE", 'sed -n 0p SOURCE', 'grep SOURCE', 'wc -l',
    'head -n -2 SOURCE', 'cat SOURCE | grep -f SOURCE',
    'cat -', "grep 'unterminated SOURCE", 'cat SOURCE | | head -1',
    'cat out/*', 'cat out/record?.yaml', 'cat out/[ab].yaml',
    'cat out/{source,prior}.yaml', 'cat ~/source.txt',
    'cat "$SOURCE"', 'cat "${SOURCE}"', "cat $'out/record.yaml'",
    'grep "$PATTERN" SOURCE', 'cat out/$((1+1)).yaml',
])
def test_unregistered_reads_and_other_shell_forms_are_outside_contract(policy, command):
    assert not lookup_command(substitute(command, policy), policy['readonly_lookups'], _simple_command)


def test_output_read_is_bounded_after_symlink_resolution(policy, tmp_path):
    out = tmp_path / 'out'
    artifact = out / 'record.yaml'
    artifact.write_text('description: neutral\n')
    assert lookup_command(shlex.join(['cat', str(artifact)]), policy['readonly_lookups'], _simple_command)
    outside = tmp_path / 'prior.yaml'
    outside.write_text('description: historical\n')
    (out / 'link.yaml').symlink_to(outside)
    for path in (out, out / 'link.yaml', out / '../prior.yaml', tmp_path / 'out-other/a.yaml'):
        assert not lookup_command(shlex.join(['cat', str(path)]), policy['readonly_lookups'], _simple_command)
    literal = out / 'literal*.yaml'
    literal.write_text('description: literal name\n')
    assert lookup_command(shlex.join(['cat', str(literal)]), policy['readonly_lookups'], _simple_command)


def transcript(command, error=False):
    return [
        {'message': {'content': [{'type': 'tool_use', 'name': 'Bash', 'id': 'one',
                                  'input': {'command': command}}]}},
        {'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'one',
                                  'is_error': error, 'content': 'observed'}]}}]


@pytest.mark.parametrize('error', [False, True])
def test_executed_command_errors_do_not_mask_nonconformance(policy, error):
    assert command_history(transcript('echo unregistered', error), policy, [])['problems']
    good = substitute('grep -n absent SOURCE', policy)
    assert not command_history(transcript(good, error), policy, [])['problems']


def test_known_denial_is_separate_from_executed_command_review(policy):
    result = command_history(transcript('echo unregistered', True), policy, [{'tool_use_id': 'one'}])
    assert not result['problems']
    assert result['calls'][0]['classification'] == 'denied_not_executed'


def test_a_denial_cannot_mask_a_successful_result(policy):
    result = command_history(transcript('echo unregistered', False), policy, [{'tool_use_id': 'one'}])
    assert result['problems']


@pytest.mark.parametrize('change', ['missing_result', 'duplicate_result', 'duplicate_call',
                                   'empty_command', 'bad_input', 'bad_id', 'early_result'])
def test_ambiguous_executed_command_evidence_cannot_pass(policy, change):
    events = transcript(substitute('cat SOURCE', policy))
    if change == 'missing_result': events.pop()
    elif change == 'duplicate_result': events.append(events[1])
    elif change == 'duplicate_call': events.append(events[0])
    elif change == 'early_result': events.reverse()
    elif change == 'empty_command': events[0]['message']['content'][0]['input']['command'] = ''
    elif change == 'bad_input': events[0]['message']['content'][0]['input'] = []
    elif change == 'bad_id': events[0]['message']['content'][0]['id'] = None
    assert command_history(events, policy, [])['problems']


def test_missing_lookup_contract_does_not_reinterpret_historical_policy(policy):
    command = substitute('cat SOURCE', policy)
    legacy = {k: v for k, v in policy.items() if k != 'readonly_lookups'}
    assert command_history(transcript(command), legacy, [])['problems']
