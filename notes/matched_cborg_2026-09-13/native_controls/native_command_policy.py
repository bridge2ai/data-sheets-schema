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


POLICY_VERSION = 6

#: A policy carrying this marker has the controller refuse, before
#: execution, a prescribed call the runtime's own permission rules would not
#: admit as written (#2369). Recorded policies without it (versions 1 to 4,
#: and the audit, evaluation and finalization policies) replay unchanged.
LITERAL_ADMISSION = 1

#: A policy carrying this marker applies the same check to the registered
#: read-only lookups, which the runtime admits by argument rules too (#2443).
LOOKUP_LITERAL_ADMISSION = 1


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


def _runtime_rules(policy):
    """The job's Bash permission rules as the pinned runtime reads them
    (Claude Code 2.1.272, #2369): the rule envelope's escapes decoded in the
    runtime's order, `\\(` and `\\)` before `\\\\`. A rule ending ` *`
    admits its text alone or followed by a space and anything, with runs of
    spaces and tabs read as one space and `\\\\` and `\\*` read as escapes;
    any other rule admits exactly its text."""
    exact, prefixes = set(), []
    for rule in policy.get('allowed_tools') or ():
        if not (isinstance(rule, str) and rule.startswith('Bash(') and rule.endswith(')')):
            continue
        content = rule[5:-1].replace('\\(', '(').replace('\\)', ')').replace('\\\\', '\\')
        if content.endswith(' *'):
            prefix = re.sub(r'\\([\\*])', r'\1', content[:-2])
            prefixes.append(re.sub(r'[ \t]+', ' ', prefix))
        else:
            exact.add(content)
    return exact, prefixes


#: Whitespace the runtime's parser treats as too complex to match literally.
_UNICODE_SPACES = frozenset('\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008'
                            '\u2009\u200a\u200b\u2028\u2029\u202f\u205f\u3000\ufeff')


def _unread_shell(text):
    """Why the runtime would not read `text` literally, else None (#2369).

    The pinned runtime parses a command before matching it, and a command it
    finds too complex is admitted only by an exact rule equal to it: any `$`
    expansion or variable, a backtick, a backslash escape or continuation, a
    comment, a glob, brace or tilde, a control character or non-ASCII
    whitespace. The shell's own quoting decides which characters count: none
    inside single quotes, `$`, backtick and backslash inside double quotes.
    Registered spellings never contain any of these outside single quotes:
    `shlex.join` quotes every such character."""
    quote = None
    word_start = True
    for ch in text:
        if (ord(ch) < 0x20 and ch not in '\t\n') or ch == '\x7f' or ch in _UNICODE_SPACES:
            return 'a control character or non-ASCII whitespace'
        if quote == "'":
            quote = None if ch == "'" else quote
            continue
        if ch == '$':
            return 'a $ variable or expansion'
        if ch == '`':
            return 'a backtick'
        if ch == '\\':
            return 'a backslash escape or line continuation'
        if quote == '"':
            quote = None if ch == '"' else quote
            continue
        if ch == '\n':
            return 'a line break outside quotes'
        if ch == '#' and word_start:
            return 'a comment'
        if ch in '{}*?[]~':
            return 'a glob, brace or tilde expansion'
        if ch in '\'"':
            quote = ch
        word_start = ch in ' \t'
    return 'an unterminated quote' if quote else None


#: What the pinned runtime (Claude Code 2.1.272) checks on the raw command
#: text before it parses, whatever the quoting (`oEe`, copied from the
#: binary; #2369, #2398 review). Any match makes the command too complex, and
#: a too-complex command is admitted only by an exact rule equal to it.
_RAW_TOO_COMPLEX = (
    (re.compile('[\ud800-\udfff]'), 'a lone surrogate'),
    (re.compile(r'[\x00-\x08\x0B-\x1F\x7F]'), 'a control character'),
    (re.compile('[\u00a0\u1680\u2000-\u200b\u2028\u2029\u202f\u205f\u3000\ufeff]'), 'non-ASCII whitespace'),
    (re.compile(r'\\[ \t]|(?:^|[^ \t\\])(?:\\\\)*\\\n|[ \t](?:\\\\)+\\\n'), 'backslash-escaped whitespace'),
    (re.compile(r'~\['), 'a zsh ~[ expansion'),
    (re.compile(r'(?:^|[\s;&|])=[a-zA-Z_]'), 'a zsh =command expansion'),
    (re.compile(r'<\d*-\d*>'), 'a zsh <N-M> range'),
)
#: The runtime does not parse a command longer than this many UTF-16 units.
_RUNTIME_PARSE_LIMIT = 10_000
#: `Gm`, tested on the text with quoted braces masked (`Hm`).
_BRACE_WITH_QUOTE = re.compile('\\{[^}]*[\'"]')
#: `ii`, tested on the raw text of an argument joined from adjacent pieces:
#: a quoted JSON object written `--opt='{…,…}'`, or one an apostrophe splits
#: into `'…'"'"'…'`, is read as brace expansion. The #2308 refusal. The class
#: is JavaScript's `\s`, spelled out: Python's also matches U+0085 (#2398).
_JS_SPACE = '\\t\\n\\v\\f\\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff'
_CONCATENATED_BRACE = re.compile('\\{[^' + _JS_SPACE + ']*(,|\\.\\.)[^' + _JS_SPACE + ']*\\}')
#: `si` and `ai`: a joined argument whose brace body carries an escaped brace.
_CONCATENATED_ESCAPED_BRACE = (re.compile(r'\{[^{]*\\}'), re.compile(r'\{[^}]*\\\{'))
#: `oin` and `sin`, tested again on a joined argument's value with its quotes
#: removed (post-collapse).
_COLLAPSED_TOO_COMPLEX = ((re.compile(r'~\['), 'a zsh ~[ expansion once quotes are removed'),
                          (re.compile(r'(?:^|[\s;&|])=[a-zA-Z_]'), 'a zsh =command expansion once quotes are removed'))
#: `t6n`: an argument naming a process environment is a semantics failure.
_PROC_ENVIRON = re.compile(r'/proc/.*/environ')

#: Text the runtime re-quotes from its arguments before matching an argument
#: rule (`ep`): a newline, or `$` and a name, even inside single quotes.
_REBUILT_FROM_ARGUMENTS = re.compile(r'\$[A-Za-z_]')
#: What JavaScript's `trim()` removes, which is not Python's `strip()`.
_JS_TRIM = '\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff'


def _mask_quoted_braces(text):
    """The runtime's `Hm`: braces inside quotes, backticks or comments hidden."""
    if '{' not in text:
        return text
    out = []
    single = double = backtick = False
    word_start = True
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if backtick:
            if ch == '\\' and nxt in ('`', '\\', '$'):
                out += [ch, nxt]; i += 2
            else:
                if ch == '`':
                    backtick = False
                out.append(' ' if ch == '{' else ch); i += 1
        elif single:
            if ch == "'":
                single = False
            out.append(' ' if ch == '{' else ch); i += 1
        elif double:
            if ch == '\\' and nxt in ('"', '\\', '`'):
                out += [ch, nxt]; i += 2
            elif ch == '`':
                backtick = True; out.append(ch); i += 1
            else:
                if ch == '"':
                    double = False
                out.append(' ' if ch == '{' else ch); i += 1
        elif ch == '\\' and i + 1 < len(text):
            out += [ch, nxt]
            if nxt != '\n':
                word_start = False
            i += 2
        elif ch == '#' and word_start:
            while i < len(text) and text[i] != '\n':
                out.append(text[i]); i += 1
            word_start = True
        elif ch == '`':
            backtick = True; word_start = False; out.append(ch); i += 1
        else:
            if ch == "'":
                single = True
            elif ch == '"':
                double = True
            word_start = ch in ' \t\n;|&()<>'
            out.append(ch); i += 1
    return ''.join(out)


def _raw_words(text):
    """Each word's raw text, quotes included, the number of adjacent pieces
    (an unquoted run, a single- or double-quoted string) it joins, and its
    value with the quotes removed."""
    words, current, value, pieces, piece, quote = [], [], [], 0, None, None
    for ch in text:
        if quote:
            current.append(ch)
            if ch == quote:
                quote, piece = None, None
            else:
                value.append(ch)
            continue
        if ch in ' \t\n':
            if current:
                words.append((''.join(current), pieces, ''.join(value)))
            current, value, pieces, piece = [], [], 0, None
            continue
        if ch in '\'"':
            quote, pieces = ch, pieces + 1
        else:
            if piece != 'bare':
                piece, pieces = 'bare', pieces + 1
            value.append(ch)
        current.append(ch)
    if current:
        words.append((''.join(current), pieces, ''.join(value)))
    return words


def _utf16_length(text):
    """The length JavaScript reports, without encoding: a lone surrogate
    cannot be encoded, and the runtime refuses it rather than failing."""
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in text)


def _too_complex(text):
    """Why the runtime would find `text` too complex to match by an argument
    rule, from its own pre-parse and argument checks, else None."""
    if _utf16_length(text) > _RUNTIME_PARSE_LIMIT:
        return 'longer than the runtime parses (10,000 characters)'
    for pattern, reason in _RAW_TOO_COMPLEX:
        if pattern.search(text):
            return reason
    if _BRACE_WITH_QUOTE.search(_mask_quoted_braces(text)):
        return 'a brace followed by a quote'
    for word, pieces, value in _raw_words(text):
        if pieces == 1 and word == '=':
            return 'a bare = argument the runtime cannot parse'
        if pieces > 1:
            if _CONCATENATED_BRACE.search(word):
                return 'a brace pattern in an argument joined from quoted pieces'
            if any(pattern.search(word) for pattern in _CONCATENATED_ESCAPED_BRACE):
                return 'an escaped brace in an argument joined from quoted pieces'
            for pattern, reason in _COLLAPSED_TOO_COMPLEX:
                if pattern.search(value):
                    return reason
    return None


def runtime_literal_problem(command, policy):
    """Why the runtime's permission rules would not admit `command` as
    written, else None (#2369). Mirrors the pinned runtime's matcher and the
    checks before it closely enough to refuse whatever it refuses; where
    fidelity is uncertain it refuses too, which costs the model one retry and
    never disqualifies the run. An exact rule admits its own text even when
    the runtime finds that text too complex; an argument rule admits only
    text it parses and does not re-quote."""
    text = command.strip(_JS_TRIM)
    exact, prefixes = _runtime_rules(policy)
    if text in exact:
        return None
    reason = _too_complex(command) or _unread_shell(text)
    if reason:
        return reason
    if '\n' in text or _REBUILT_FROM_ARGUMENTS.search(text):
        return 'text the runtime re-quotes from its arguments before matching an argument rule'
    tokens, _ = _simple_command(text)
    if any(_PROC_ENVIRON.search(token) for token in tokens or ()):
        return 'an argument naming a process environment, which the runtime refuses'
    normal = re.sub(r'[ \t]+', ' ', text)
    if any(normal == prefix or normal.startswith(prefix + ' ') for prefix in prefixes):
        return None
    return 'a spelling no registered permission rule admits'


def _registered_spelling(tokens, python, policy):
    """The registered spelling of the command `tokens` means, for a refusal
    to name (#2369)."""
    if tokens[1] == '-c':
        key = program_key(tokens[2])
        codes = [p['code'] for p in policy['programs'] if program_key(p['code']) == key]
        spellings = [e for e in policy['command_examples']
                     if (lambda words: len(words) > 2 and words[2] in codes)(shlex.split(e))]
        return ' or '.join(spellings) if spellings else shlex.join([python, '-c', *codes[:1]])
    if tokens[2] == 'data_sheets_schema.cli':
        args = tokens[3:]
        root = args[:2] if args[:1] == ['--manifest'] else []
        roster = _roster_command(args[len(root):])
        return shlex.join([python, '-m', 'data_sheets_schema.cli', *root, *roster.split()]) + ' …'
    return shlex.join([python, '-m', tokens[2]]) + ' …'


def build_command_policy(job, python, repository):
    """Freeze one policy from the actual instruction and its selected playbook."""
    from native_phase_history import helper_argument_problem, helper_expectations
    from prepare_registration import spec_for
    spec = job['render_spec']
    environment = validate_toolchain(spec['agentic_toolchain'])
    if environment['python'] != python:
        raise ValueError('registered Python and agentic toolchain disagree')
    artifacts = spec['agentic_artifact_paths']
    if any(job['outputs'][key] != artifacts[key] for key in ('full', 'core', 'report')):
        raise ValueError('registered outputs and agentic artifact paths disagree')
    # The launcher reviews phase history against spec_for(job); its helper
    # expectations are the ones the controller enforces (#2444).
    launched = spec_for(job)
    compared = ('full', 'core', 'report', *(('receipt',) if 'receipt' in artifacts else ()))
    if any(str(launched._agentic_artifact_paths.get(key)) != artifacts[key] for key in compared):
        raise ValueError("the launcher's run specification and the registered artifact paths disagree")
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
    policy = {'version': POLICY_VERSION, 'literal_admission': LITERAL_ADMISSION,
              'pretool_control': dict(CONTRACT),
              'python': python, 'manifest_paths': sorted(manifests),
              'programs': [{'code': code, 'arguments': arguments} for code, arguments in sorted(programs.items())],
              'command_examples': sorted(examples), 'allowed_tools': rules,
              'readonly_lookups': lookup_policy(job, repository),
              'lookup_literal_admission': LOOKUP_LITERAL_ADMISSION,
              'helper_arguments': helper_expectations(launched, repository)}
    # Every registered spelling must be admitted as written, or the run would
    # be refused at that step after the spend before it (#2282, #2369): the
    # bound inline programs, and every command line of the instruction that
    # begins with the registered interpreter. Inline programs and lines with
    # a placeholder are covered by the bound examples.
    heads = sorted({python, shlex.quote(python)}, key=len, reverse=True)
    lines = [line.strip() for line in instruction.splitlines()]
    candidates = sorted(examples) + [
        line for line in lines
        if any(line.startswith(head + ' ') for head in heads)
        and not any(line.startswith(head + ' -c ') for head in heads)
        and not re.search(r'<[a-z_]+>', line)]
    spellings = {}
    for command in candidates:
        kind, problem = helper_argument_problem(command, policy)
        if kind and not problem:
            spellings.setdefault(kind, set()).add(command)
    policy['helper_arguments']['spellings'] = {kind: sorted(lines) for kind, lines in sorted(spellings.items())}
    for command in candidates:
        verdict, basis = classify_program_command(command, python, set(), policy)
        if verdict != 'prescribed':
            raise ValueError(f'a registered command is not admitted as written ({basis}): {command[:200]}')
    return policy


def command_guidance(policy):
    """Give the runtime the exact shell spellings its permissions admit."""
    literal = ('Any other spelling of a registered command (a double-quoted or '
               'reflowed program, a $ variable or expansion, a line continuation, '
               'a comment) is refused before it runs. That refusal does not '
               'disqualify the attempt; where the call keeps the registered '
               'interpreter and command, it names the registered spelling, so run '
               'the command again exactly as registered. '
               if policy.get('literal_admission') == LITERAL_ADMISSION else '')
    helpers = (policy.get('helper_arguments') or {}).get('spellings') or {}
    helper_guidance = ((
        '\n\n## Registered helper commands\n\n'
        'The receipt check, core derivation, source review and evidence '
        'assertion helpers run only with the instruction\'s registered '
        'arguments, spelled as below. Other arguments, including the executable '
        'playbook\'s generic forms, are refused before they run; that refusal '
        'does not disqualify the attempt.\n\n' +
        '\n\n'.join('```bash\n' + command + '\n```' for kind in sorted(helpers) for command in helpers[kind]) + '\n')
        if helpers else '')
    return (
        '\n\n## Registered inline Python commands\n\n'
        'Use the exact commands below for the instruction and executable playbook\'s '
        'inline Python checks and original freeze. Their paths have already been '
        'bound to this job. Copy their shell quoting and Python text exactly; do '
        'not rewrite the programs. Schema and term validator arguments may be '
        'adjusted for the registered full/core paths and schemas only. Other '
        'Python programs are not permitted. CLI roster commands retain the '
        'instruction\'s arguments; a root --manifest option must name this job\'s '
        'registered manifest. ' + literal + '\n\n' +
        '\n\n'.join('```bash\n' + command + '\n```' for command in policy['command_examples']) + '\n' +
        helper_guidance +
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
    verdict, basis = _classify_by_meaning(command, python, programs, command_policy)
    if (verdict == 'prescribed' and isinstance(command_policy, dict)
            and command_policy.get('literal_admission') == LITERAL_ADMISSION):
        # The meaning is registered, but the runtime admits only the
        # registered text (#2369). A refusal here is the controller's, which
        # does not disqualify the run and lets the model copy the spelling.
        problem = runtime_literal_problem(command, command_policy)
        if problem:
            spelling = _registered_spelling(_simple_command(command)[0], python, command_policy)
            return 'not_prescribed', (f'{basis}, respelled: {problem}. This refusal does not disqualify '
                                      f'the attempt; run the registered spelling exactly: {spelling}')
    if verdict == 'prescribed' and isinstance(command_policy, dict) and 'helper_arguments' in command_policy:
        # The phase history stops a run on a helper called with arguments
        # other than the selected run's. Under a policy that records those
        # arguments, the controller refuses the call before it runs (#2444).
        from native_phase_history import helper_argument_problem
        kind, problem = helper_argument_problem(command, command_policy)
        if problem:
            spellings = command_policy['helper_arguments'].get('spellings', {}).get(kind) or []
            return 'not_prescribed', (f'{basis}, {problem}. This refusal does not disqualify the attempt; '
                                      'run a registered spelling exactly: ' + ' or '.join(spellings))
    return verdict, basis


def _classify_by_meaning(command, python, programs, command_policy=None):
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
            except (SyntaxError, ValueError, TypeError, RecursionError, MemoryError):
                # A program nested too deeply to parse is refused, not a
                # controller failure that stops the run (#2398 review).
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
