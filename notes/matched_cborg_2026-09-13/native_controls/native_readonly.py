"""Recognize a deliberately small read-only shell grammar; never execute it.

This is an instruction-conformance check, not a filesystem sandbox. File
identities and phase ordering still require the registered acceptance review.
"""
from pathlib import Path
import re


PROGRAMS = ('cat', 'grep', 'head', 'tail', 'wc', 'sed')


def _literal_arguments(command):
    """Do not resolve shell expansions as if they were literal filenames.

    Quoted regex metacharacters and escaped characters remain data. In
    particular, an output-directory glob could follow an unregistered symlink
    even though the unexpanded word appears to be inside the output directory.
    """
    quote = None
    i = 0
    while i < len(command):
        ch = command[i]
        if ch == '\0':
            return False
        if quote == "'":
            if ch == "'":
                quote = None
        elif ch == '\\':
            i += 1
        elif ch in "'\"" and (quote is None or quote == ch):
            quote = None if quote else ch
        elif ch == '`':
            return False
        elif ch == '$':
            following = command[i + 1:i + 2]
            if re.match(r'[A-Za-z0-9_({\[?*!@#$\-]', following) or (quote is None and following in ("'", '"')):
                return False
        elif quote is None and ch in '*?[]{}~':
            return False
        i += 1
    return quote is None


def pipeline_parts(command):
    """Split unquoted single pipes without interpreting quoted patterns."""
    parts = []
    quote = None
    start = i = 0
    while i < len(command):
        ch = command[i]
        if quote == "'":
            if ch == "'":
                quote = None
        elif ch == '\\':
            i += 1
        elif ch in "'\"" and (quote is None or quote == ch):
            quote = None if quote else ch
        elif ch == '|' and quote is None:
            parts.append(command[start:i])
            start = i + 1
        i += 1
    parts.append(command[start:])
    return parts


def _paths(words):
    """Return file operands for the supported options, or None for other forms.

    Options may follow operands, as they do in the native runtime's grep
    commands. A double dash ends option parsing. Recursive traversal, pattern
    files, follow mode and sed programs other than numeric print ranges are
    outside this grammar.
    """
    program, args = words[0], words[1:]
    files = []
    pattern = None
    options = True
    quiet_sed = False
    i = 0
    while i < len(args):
        word = args[i]
        if options and word == '--':
            options = False
        elif options and word.startswith('-') and word != '-':
            if program == 'grep':
                if re.fullmatch(r'-[nEiFivxoclHhqs]+', word):
                    pass
                elif re.fullmatch(r'-[ABCm][0-9]+', word):
                    pass
                elif word in ('-A', '-B', '-C', '-m'):
                    i += 1
                    if i >= len(args) or not re.fullmatch(r'[0-9]+', args[i]):
                        return None
                elif word == '-e' and pattern is None:
                    i += 1
                    if i >= len(args):
                        return None
                    pattern = args[i]
                else:
                    return None
            elif program in ('head', 'tail'):
                if re.fullmatch(r'-[0-9]+', word):
                    pass
                elif word in ('-n', '-c'):
                    i += 1
                    if i >= len(args) or not re.fullmatch(r'[0-9]+', args[i]):
                        return None
                else:
                    return None
            elif program == 'wc' and re.fullmatch(r'-[lwmcL]+', word):
                pass
            elif program == 'cat' and re.fullmatch(r'-[nbs]+', word):
                pass
            elif program == 'sed' and word == '-n':
                quiet_sed = True
            else:
                return None
        elif program in ('grep', 'sed') and pattern is None:
            pattern = word
        else:
            files.append(word)
        i += 1
    if program == 'grep' and pattern is None:
        return None
    if program == 'sed' and (not quiet_sed or pattern is None or
                            not re.fullmatch(r'[1-9][0-9]*(?:,[1-9][0-9]*)?p', pattern)):
        return None
    return files


def lookup_command(command, policy, simple_command):
    """True only for supported inspections of exact registered input paths or
    paths inside the job's output directories. Later pipeline stages may read
    stdin. The existing shell scanner rejects redirects, substitutions and
    extra commands in every stage; no shell evaluation is performed here.
    """
    if not policy or not _literal_arguments(command):
        return False
    try:
        root = Path(policy['repository'])
        inputs = {Path(p) for p in policy['inputs']}
        outputs = [Path(p) for p in policy['output_directories']]
        for position, part in enumerate(pipeline_parts(command)):
            words, _ = simple_command(part)
            if not words or words[0] not in PROGRAMS:
                return False
            files = _paths(words)
            if files is None or (position == 0 and (not files or '-' in files)):
                return False
            for name in files:
                if name == '-' and position:
                    continue
                candidate = Path(name)
                target = (candidate if candidate.is_absolute() else root / candidate).resolve()
                if target not in inputs and not any(folder in target.parents for folder in outputs):
                    return False
        return True
    except (KeyError, TypeError, ValueError, OSError, RuntimeError):
        return False


def registered_input_paths(job):
    """Only files the instruction reaches, not every hashed agent definition."""
    from data_sheets_schema.agentic_runtime import SCHEMAS
    from data_sheets_schema.provenance import AGENT_PLAYBOOKS
    readable = set(SCHEMAS) | {str(p) for p in AGENT_PLAYBOOKS}
    identity = job.get('input_identity') or {}
    paths = [job.get('bundle'), job.get('chunks'), job.get('manifest'), job.get('instruction')]
    paths += [(identity.get(k) or {}).get('path') for k in ('bundle', 'source_manifest', 'chunks')]
    spec = (identity.get('instruction') or {}).get('spec') or job.get('render_spec') or {}
    resources = (spec.get('agentic_toolchain') or {}).get('resources') or {}
    paths += [value for key, value in resources.items() if key in readable]
    return [x for x in paths if isinstance(x, str) and x]


def lookup_policy(job, repository):
    root = Path(repository).resolve()
    def resolve(value):
        candidate = Path(value)
        return str((candidate if candidate.is_absolute() else root / candidate).resolve())
    return {'version': 1, 'repository': str(root),
            'inputs': sorted({resolve(p) for p in registered_input_paths(job)}),
            'output_directories': sorted({resolve(p) for p in job.get('output_directories', [])})}


def lookup_guidance():
    return (
        '\n\n## Registered read-only shell lookups\n\n'
        'You may inspect exact registered input paths and files inside this job\'s '
        'output directories with these shell forms: cat [-nbs] FILE...; '
        'grep [-nEiFivxoclHhqs] [-A N] [-B N] [-C N] [-m N] PATTERN FILE... '
        '(or -e PATTERN); head/tail [-n N|-c N|-N] FILE...; wc [-lwmcL] FILE...; '
        'sed -n \'START[,END]p\' FILE.... N is a nonnegative integer and sed '
        'line numbers are positive integers. Use literal, shell-quoted paths. '
        'Single pipes may connect only these lookup commands; later stages may '
        'read stdin. Other options, recursive searches, pattern files, follow '
        'mode, redirection, substitutions, command chains and other programs '
        'are outside this permission. Use the Read tool for unsupported '
        'lookups. These inspections do not replace ordered source-chunk reads, '
        'immediate receipt writes or any required validation command. '
        'Successful tool admission is checked against this contract.\n')
