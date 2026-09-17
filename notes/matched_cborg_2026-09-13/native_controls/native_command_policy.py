"""Job-specific Bash rules and Python identities for the native controller.

The runtime's Bash matcher treats every asterisk as a wildcard, including
inside quoted Python. Never put a wildcard in a program's rule. The only
wildcards we append admit arguments to a named CLI/module or validator;
these permissions are not a filesystem sandbox.
"""
import ast
import json
from pathlib import Path
import re
import shlex
import textwrap

from data_sheets_schema.agentic_runtime import playbook_text, validate_toolchain
from prepare_overlay_roster import PLAYBOOK_COMMANDS, MODULE_ENTRY_POINTS
from native_readonly import PROGRAMS, lookup_policy, lookup_guidance
from native_control import CONTRACT


POLICY_VERSION = 3


def program_key(program):
    """Compare Python syntax without executing it or treating code as a glob."""
    return ast.dump(ast.parse(textwrap.dedent(program).strip()), include_attributes=False)


def python_commands(text, python):
    """Read complete inline Python commands, including Markdown indentation.

    A fenced block nested in a list has indentation that is not part of the
    command. Remove that indentation before parsing its quoted multiline
    program. A shell continuation is likewise not part of an argument.
    """
    heads = sorted({python, shlex.quote(python)}, key=len, reverse=True)
    pattern = re.compile(r'(?m)^(?P<indent>[ \t]*)(?:' +
                         '|'.join(re.escape(p) for p in heads) + r') -c ')
    for match in pattern.finditer(text):
        start = match.start()
        end = text.find('\n', match.end())
        while True:
            command = text[start:end if end >= 0 else len(text)]
            indent = match['indent']
            if indent:
                command = '\n'.join(line[len(indent):] if line.startswith(indent) else line
                                    for line in command.split('\n'))
            try:
                tokens = shlex.split(command.replace('\\\n', ''), comments=True)
            except ValueError:
                if end < 0:
                    raise ValueError('unterminated prescribed Python command')
                end = text.find('\n', end + 1)
                continue
            if len(tokens) < 3 or tokens[:2] != [python, '-c']:
                raise ValueError('malformed prescribed Python command')
            yield tokens
            break


def _bind_program(program, replacements):
    """Bind placeholder string literals as data, including paths with quotes."""
    source = textwrap.dedent(program)
    changed = False

    class Bind(ast.NodeTransformer):
        def visit_Constant(self, node):
            nonlocal changed
            if isinstance(node.value, str):
                value = node.value
                for placeholder, replacement in replacements.items():
                    value = value.replace(placeholder, replacement)
                if re.search(r'<[a-z_]+>', value):
                    raise ValueError('unbound placeholder in a prescribed Python program')
                changed = changed or value != node.value
                return ast.copy_location(ast.Constant(value=value), node)
            return node

    parsed = ast.parse(source.strip())
    bound = Bind().visit(parsed)
    # Preserve concrete programs exactly, including the freeze's final newline.
    return ast.unparse(bound) if changed else source


def _literal_rule(command, arguments=False):
    if '*' in command:
        raise ValueError('a prescribed command contains a literal asterisk the runtime treats as a wildcard')
    # Escape the tool-rule envelope separately from shell quoting. The
    # runtime decodes these escapes before matching the command text.
    encoded = command.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    return 'Bash(' + encoded + (' *' if arguments else '') + ')'


def permission_arguments(policy):
    """The CLI's --allowedTools list splitter loses complex Python rules.

    Inline JSON settings retain each complete rule as one array element and
    avoid a mutable settings file in the child workspace.
    """
    return ['--input-format', 'stream-json', '--settings', json.dumps({'permissions': {'allow': policy['allowed_tools']}},
                                    separators=(',', ':'))]


def build_command_policy(job, python, repository):
    """Freeze one policy from the actual instruction and its selected playbook."""
    spec = job['render_spec']
    environment = validate_toolchain(spec['agentic_toolchain'])
    if environment['python'] != python:
        raise ValueError('registered Python and agentic toolchain disagree')
    artifacts = spec['agentic_artifact_paths']
    if any(job['outputs'][key] != artifacts[key] for key in ('full', 'core', 'report')):
        raise ValueError('registered outputs and agentic artifact paths disagree')
    replacements = {
        '<full_file>': artifacts['full'], '<full>': artifacts['full'],
        '<core_file>': artifacts['core'], '<core>': artifacts['core'],
        '<report_file>': artifacts['report'], '<bundle>': job['bundle'],
    }
    instruction = Path(job['instruction']).read_text(encoding='utf-8')
    programs = {}
    examples = set()
    for source in (instruction, playbook_text(environment)):
        for tokens in python_commands(source, python):
            program = _bind_program(tokens[2], replacements)
            tail = [replacements.get(arg, arg) for arg in tokens[3:]]
            if any(re.search(r'<[a-z_]+>', arg) for arg in tail):
                raise ValueError('unbound placeholder in prescribed Python arguments')
            prefix = shlex.join([python, '-c', program])
            # Reject unsafe rule text even for a program that takes arguments.
            _literal_rule(prefix)
            previous = programs.get(program, False)
            programs[program] = previous or bool(tail)
            examples.add(shlex.join([python, '-c', program, *tail]))

    manifest = Path(job['manifest'])
    root = Path(repository).resolve()
    absolute = (manifest if manifest.is_absolute() else root / manifest).resolve()
    manifests = {str(absolute)}
    if absolute.is_relative_to(root):
        manifests.add(str(absolute.relative_to(root)))
    cli = [python, '-m', 'data_sheets_schema.cli']
    rules = ['Read', 'Write']
    # Built-in read-only admission varies with the pattern (#2052). These
    # grants provide the named capabilities. The parent PreToolUse callback
    # checks the same grammar before execution; command_history checks again.
    # Helper arguments and Read/Write still need independent review.
    for program in PROGRAMS:
        rules.append(_literal_rule('sed -n' if program == 'sed' else program, arguments=True))
    for command in PLAYBOOK_COMMANDS:
        rules.append(_literal_rule(shlex.join([*cli, *command.split()]), arguments=True))
        for path in sorted(manifests):
            rules.append(_literal_rule(shlex.join([*cli, '--manifest', path, *command.split()]), arguments=True))
    for module in MODULE_ENTRY_POINTS:
        rules.append(_literal_rule(shlex.join([python, '-m', f'data_sheets_schema.{module}']), arguments=True))
    for program, arguments in sorted(programs.items()):
        rules.append(_literal_rule(shlex.join([python, '-c', program]), arguments=arguments))
    return {'version': POLICY_VERSION, 'pretool_control': dict(CONTRACT),
            'python': python, 'manifest_paths': sorted(manifests),
            'programs': [{'code': code, 'arguments': arguments} for code, arguments in sorted(programs.items())],
            'command_examples': sorted(examples), 'allowed_tools': rules,
            'readonly_lookups': lookup_policy(job, repository)}


def command_guidance(policy):
    """Give the runtime the exact shell spellings its permissions admit."""
    return (
        '\n\n## Registered inline Python commands\n\n'
        'Use the exact commands below for the instruction and executable playbook\'s '
        'inline Python checks and original freeze. Their paths have already been '
        'bound to this job. Copy their shell quoting and Python text exactly; do '
        'not rewrite the programs. Schema and term validator arguments may be '
        'adjusted for the registered full/core paths and schemas only. Other '
        'Python programs are not permitted. CLI roster commands retain the '
        'instruction\'s arguments; a root --manifest option must name this job\'s '
        'registered manifest.\n\n' +
        '\n\n'.join('```bash\n' + command + '\n```' for command in policy['command_examples']) + '\n' +
        lookup_guidance())


def validated_command_policy(overlay, base, job):
    """Refuse missing, widened or stale policies before credentials or spending."""
    expected = build_command_policy(job, base['python'], base['repository'])
    recorded = (overlay.get('per_job_command_policy') or {}).get(job['id'])
    if recorded != expected or 'allowed_tools' in overlay:
        raise ValueError('native command policy differs from the registered job or retains global rules')
    return expected
