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


POLICY_VERSION = 4


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
    # The parent also enforces Read/Write targets. Helper arguments, receipt
    # timing and source support still need independent review.
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
        lookup_guidance() +
        '\n\n## File tools\n\n'
        'The parent checks every Read and Write target before execution. Read '
        'only the registered inputs below, your files inside the output directories, '
        'or an unchanged persisted tool output advertised by this native session. '
        'A provenance hash inventory is not a list of files to consult. Write '
        'only inside the output directories; never overwrite an input. Do not '
        'consult other agent definitions or prior records.\n\n' +
        '\n'.join('- ' + path for path in policy['readonly_lookups']['inputs']) +
        '\n\nOutput directories:\n' +
        '\n'.join('- ' + path for path in policy['readonly_lookups']['output_directories']) + '\n')


def validated_command_policy(overlay, base, job):
    """Refuse missing, widened or stale policies before credentials or spending."""
    expected = build_command_policy(job, base['python'], base['repository'])
    recorded = (overlay.get('per_job_command_policy') or {}).get(job['id'])
    if recorded != expected or 'allowed_tools' in overlay:
        raise ValueError('native command policy differs from the registered job or retains global rules')
    return expected


#: Characters bash reads as control or redirection operators when they are
#: unquoted, alone or merged (`>|`, `&>>`, `<>`, `)|`). The system prompt
#: forbids chaining unlisted programs, heredocs and writes outside the output
#: directories, and no command the instruction prescribes uses any of them.
OPERATOR_CHARS = frozenset(';&|<>()')


def _shell_tokens(command, bash_words=False):
    """shlex words. With bash_words, for text `_simple_command` has already
    scanned: no comment character, and only a space or tab separates words
    (bash keeps a carriage return inside the word)."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        if bash_words:
            lexer.commenters = ''
            lexer.whitespace = ' \t'
        return list(lexer)
    except ValueError:
        return None


FORBIDDEN_SHELL = 'shell operators, redirection or substitution the system prompt forbids'


def _simple_command(command):
    """The command's words when bash would read one simple command, else
    (None, reason).

    shlex alone does not see how bash splits a command line (#2031): with
    whitespace_split a newline is whitespace, a run of operator characters is
    one token, and a `#` inside a word hides the rest of the line. So the
    text is scanned first with bash's quoting. A backslash-newline joins two
    lines. A `#` starts a comment only at the start of a word. A newline
    ends the command, so any word after it, outside a comment, is a second
    command. An unquoted operator character, a backtick or `$(` (also inside
    double quotes) means the text is not one simple command."""
    out = []
    quote = None
    word_start = True
    ended = False
    i, n = 0, len(command)
    while i < n:
        ch = command[i]
        if quote == "'":
            out.append(ch)
            quote = None if ch == "'" else quote
            i += 1
            continue
        if ch == '\\' and command[i + 1:i + 2] == '\n':
            i += 2
            continue
        if quote is None:
            if ch in ' \t':
                out.append(ch)
                word_start = True
                i += 1
                continue
            if ch == '\n':
                ended = ended or bool(''.join(out).strip())
                out.append(' ')
                word_start = True
                i += 1
                continue
            if ch == '#' and word_start:
                end = command.find('\n', i)
                i = n if end < 0 else end
                continue
            if ended:
                return None, FORBIDDEN_SHELL
        if ch == '`' or command.startswith('$(', i):
            return None, FORBIDDEN_SHELL
        if ch == '\\':
            out.append(command[i:i + 2])
            word_start = False
            i += 2
            continue
        if quote == '"':
            out.append(ch)
            quote = None if ch == '"' else quote
            i += 1
            continue
        if ch in OPERATOR_CHARS:
            return None, FORBIDDEN_SHELL
        if ch in '\'"':
            quote = ch
        out.append(ch)
        word_start = False
        i += 1
    tokens = None if quote else _shell_tokens(''.join(out), bash_words=True)
    if not tokens:
        return None, 'shell text that does not parse'
    return tokens, None


def _roster_command(args):
    """The roster command `args` begins with, matched word by word (a roster
    command may have three words: `api prompts check`)."""
    for command in sorted(PLAYBOOK_COMMANDS, key=lambda c: -len(c.split())):
        words = command.split()
        if args[:len(words)] == words:
            return command
    return None


# This classifier is pure: path-based lookups stay in the timed controller worker.
def classify_program_command(command, python, programs, command_policy=None):
    tokens, reason = _simple_command(command)
    if tokens is None:
        return 'not_prescribed', reason
    if tokens[0] != python or len(tokens) < 3:
        return 'not_prescribed', 'a program the instruction does not prescribe'
    rest = tokens[3:] if tokens[1] == '-c' else tokens[1:]
    if any(t in ('--help', '-h') for t in rest):
        return 'not_prescribed', '--help exploration the system prompt forbids'
    if tokens[1] == '-c':
        if command_policy is not None:
            try:
                key = program_key(tokens[2])
            except (SyntaxError, ValueError, TypeError):
                return 'not_prescribed', 'an invalid inline Python program'
            for program in command_policy['programs']:
                if key == program_key(program['code']):
                    if tokens[3:] and not program['arguments']:
                        return 'not_prescribed', 'extra arguments to a fixed registered program'
                    return 'prescribed', 'a Python program from the registered instruction or selected playbook'
            return 'not_prescribed', 'an ad-hoc -c script the system prompt forbids'
        if tokens[2].strip() in programs:
            return 'prescribed', 'a -c program the instruction prescribes verbatim'
        return 'not_prescribed', 'an ad-hoc -c script the system prompt forbids'
    if tokens[1] != '-m':
        return 'not_prescribed', 'an interpreter form the instruction does not prescribe'
    module = tokens[2]
    if module == 'data_sheets_schema.cli':
        args = tokens[3:]
        if args[:1] == ['--manifest']:
            if command_policy is not None and (len(args) < 2 or args[1] not in command_policy['manifest_paths']):
                return 'not_prescribed', 'a manifest outside the registered job'
            args = args[2:]
        roster = _roster_command(args)
        if roster:
            return 'prescribed', f"the roster command '{roster}'"
        return 'not_prescribed', 'a CLI command outside the prescribed roster'
    if module.startswith('data_sheets_schema.') and module.split('.', 1)[1] in MODULE_ENTRY_POINTS:
        return 'prescribed', f"the registered module entry point '{module}'"
    return 'not_prescribed', 'a module the instruction does not prescribe'
